"""Agent 业务逻辑：触发评估、查询进度、确认结果"""

import asyncio
import logging
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, JobStatus
from app.models.user import User, UserRole
from app.schemas.agent import (
    ConfirmRequest,
    EvaluateResponse,
    TaskStatusResponse,
)
from app.services.agent.state import EvaluationState

logger = logging.getLogger(__name__)


async def trigger_evaluation(
    db: AsyncSession,
    job_id: str,
    current_user: User,
    request: Any,
) -> EvaluateResponse:
    """触发评估工作流"""
    # 校验角色
    if current_user.role != UserRole.RECRUITER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅招聘者可以触发评估",
        )

    # 校验岗位
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="岗位不存在",
        )
    if job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权评估此岗位",
        )
    if job.status != JobStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="岗位未处于活跃状态",
        )

    # 并发控制：检查是否有 pending/running 的任务
    job_uuid = uuid.UUID(job_id)
    existing_stmt = select(EvaluationTask).where(
        EvaluationTask.job_id == job_uuid,
        EvaluationTask.status.in_([EvalTaskStatus.PENDING, EvalTaskStatus.RUNNING]),
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该岗位已有正在进行的评估任务",
        )

    # 统计 pending 申请数
    count_stmt = select(Application).where(
        Application.job_id == job_uuid,
        Application.status == ApplicationStatus.PENDING,
    )
    pending_count = len(list((await db.execute(count_stmt)).scalars().all()))

    # 创建评估任务
    task_id = uuid.uuid4()
    eval_task = EvaluationTask(
        id=task_id,
        job_id=job_uuid,
        triggered_by=current_user.id,
        status=EvalTaskStatus.PENDING,
        total_count=pending_count,
    )
    db.add(eval_task)
    await db.commit()
    await db.refresh(eval_task)

    # 启动后台工作流
    asyncio.create_task(
        _run_workflow_background(
            str(task_id), str(job_id), str(current_user.id),
        )
    )

    return EvaluateResponse(
        task_id=str(task_id),
        status="pending",
        total_count=pending_count,
    )


async def _run_workflow_background(
    task_id: str,
    job_id: str,
    triggered_by: str,
) -> None:
    """后台执行评估工作流（通过 LangGraph 图引擎）"""
    from app.database import async_session
    from app.services.agent.graph import run_evaluation_workflow

    async with async_session() as db:
        try:
            initial_state: EvaluationState = {
                "job_id": job_id,
                "triggered_by": triggered_by,
                "task_id": task_id,
                "errors": [],
            }
            await run_evaluation_workflow(initial_state, db)
        except Exception as exc:
            logger.exception("评估工作流异常: task_id=%s", task_id)
            task = await db.get(EvaluationTask, task_id)
            if task and task.status not in (
                EvalTaskStatus.COMPLETED,
                EvalTaskStatus.CONFIRMED,
                EvalTaskStatus.FAILED,
            ):
                task.status = EvalTaskStatus.FAILED
                task.error_message = f"工作流异常: {exc}"
                await db.commit()


async def get_task_status(
    db: AsyncSession,
    task_id: str,
    current_user: User,
) -> TaskStatusResponse:
    """查询评估任务状态"""
    task = await db.get(EvaluationTask, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评估任务不存在",
        )

    # 校验权限：只有触发者可以查看
    if task.triggered_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此评估任务",
        )

    return TaskStatusResponse(
        task_id=str(task.id),
        job_id=str(task.job_id),
        status=task.status,
        total_count=task.total_count,
        evaluated_count=task.evaluated_count,
        result_summary=task.result_summary,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def confirm_evaluation(
    db: AsyncSession,
    task_id: str,
    current_user: User,
    request: ConfirmRequest,
) -> Any:
    """确认评估结果，更新 Application 状态"""
    from app.schemas.agent import ConfirmResponse

    # 校验任务
    task = await db.get(EvaluationTask, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评估任务不存在",
        )

    if task.triggered_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权确认此评估任务",
        )

    if task.status != EvalTaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"评估任务状态为 {task.status.value}，无法确认（需 completed）",
        )

    # 查询该岗位下有 ai_decision 的申请
    stmt = select(Application).where(
        Application.job_id == task.job_id,
        Application.ai_decision.is_not(None),
    )
    applications = list((await db.execute(stmt)).scalars().all())

    if not applications:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有可确认的评估结果",
        )

    # 构建 decision override 映射
    override_map: dict[str, str] = {}
    for d in request.decisions:
        override_map[d.application_id] = d.final_decision

    # 更新每个 Application 的状态
    updated_count = 0
    for app in applications:
        app_id_str = str(app.id)
        if app_id_str in override_map:
            # 使用人工覆盖的决策
            final_decision = override_map[app_id_str]
        else:
            # 使用 AI 建议的决策
            final_decision = app.ai_decision if app.ai_decision else "reject"

        if final_decision == "recommend" or final_decision == "interview":
            app.status = ApplicationStatus.INTERVIEW
        else:
            app.status = ApplicationStatus.REJECTED

        updated_count += 1

    # 标记任务已确认
    task.status = EvalTaskStatus.CONFIRMED
    await db.commit()

    return ConfirmResponse(
        updated_count=updated_count,
        message=f"已确认 {updated_count} 份申请的评估结果",
    )

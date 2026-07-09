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

    # 根据 mode 统计申请数
    mode = getattr(request, "mode", "new_only")
    count_stmt = select(Application).where(
        Application.job_id == job_uuid,
    )
    if mode == "new_only":
        count_stmt = count_stmt.where(Application.ai_decision.is_(None))
    all_apps = list((await db.execute(count_stmt)).scalars().all())
    total_count = len(all_apps)

    if mode == "new_only" and total_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有新的简历投递，无需触发评估",
        )

    # 创建评估任务
    task_id = uuid.uuid4()
    eval_task = EvaluationTask(
        id=task_id,
        job_id=job_uuid,
        triggered_by=current_user.id,
        status=EvalTaskStatus.PENDING,
        mode=mode,
        total_count=total_count,
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
        total_count=total_count,
    )


async def get_job_tasks(
    db: AsyncSession,
    job_id: str,
    current_user: User,
) -> Any:
    """获取岗位的评估任务列表"""
    from app.schemas.agent import JobEvaluationTasksResponse, JobTaskItem

    # 校验岗位权限
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    if job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此岗位")

    stmt = (
        select(EvaluationTask)
        .where(EvaluationTask.job_id == uuid.UUID(job_id))
        .order_by(EvaluationTask.created_at.desc())
    )
    tasks = list((await db.execute(stmt)).scalars().all())

    items = [
        JobTaskItem(
            task_id=str(t.id),
            status=t.status,
            mode=t.mode,
            total_count=t.total_count,
            evaluated_count=t.evaluated_count,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]
    return JobEvaluationTasksResponse(tasks=items)


async def export_evaluation_to_excel(
    db: AsyncSession,
    task_id: str,
    current_user: User,
) -> bytes:
    """导出评估结果为 Excel 文件"""
    from io import BytesIO
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill

    task = await db.get(EvaluationTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评估任务不存在")
    if task.triggered_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权导出此任务")

    result_summary = task.result_summary or {}
    details = result_summary.get("evaluation_details", [])

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None, "工作表创建失败"
    ws.title = "评估结果"

    # Header style
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font_white = Font(bold=True, size=11, color="FFFFFF")

    # Headers
    headers = ["序号", "姓名", "AI 总分", "AI 决策", "技能匹配", "经验相关性", "学历达标", "综合印象", "决策理由"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # Data rows
    for i, detail in enumerate(details, 1):
        dims = {}
        for dim in detail.get("ai_evaluation", []):
            dims[dim.get("name", "")] = dim.get("score", 0)

        ws.cell(row=i + 1, column=1, value=i).alignment = Alignment(horizontal="center")
        ws.cell(row=i + 1, column=2, value=detail.get("applicant_name", ""))
        ws.cell(row=i + 1, column=3, value=detail.get("ai_score", 0))
        ws.cell(row=i + 1, column=4, value="推荐" if detail.get("ai_decision") == "recommend" else "淘汰")
        ws.cell(row=i + 1, column=5, value=dims.get("技能匹配", ""))
        ws.cell(row=i + 1, column=6, value=dims.get("经验相关性", ""))
        ws.cell(row=i + 1, column=7, value=dims.get("学历达标", ""))
        ws.cell(row=i + 1, column=8, value=dims.get("综合印象", ""))
        ws.cell(row=i + 1, column=9, value=detail.get("ai_decision_reason", ""))

    # Auto-adjust column widths
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[chr(64 + col)].width = max(15, len(str(headers[col - 1])) + 4)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


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
            # 从数据库读取任务的 mode
            task = await db.get(EvaluationTask, task_id)
            mode = task.mode if task else "new_only"

            initial_state: EvaluationState = {
                "job_id": job_id,
                "triggered_by": triggered_by,
                "task_id": task_id,
                "mode": mode,
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

from fastapi import APIRouter, Depends, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_required_user
from app.database import get_db
from app.models.user import User
from app.schemas.agent import (
    ConfirmRequest,
    ConfirmResponse,
    EvaluateRequest,
    EvaluateResponse,
    JobEvaluationTasksResponse,
    TaskStatusResponse,
)
from app.services import agent_service

router = APIRouter(prefix="/agent", tags=["智能评估"])


@router.post(
    "/evaluate/{job_id}",
    response_model=EvaluateResponse,
    summary="触发评估工作流",
    status_code=201,
)
async def trigger_evaluation(
    job_id: str = Path(..., description="岗位ID"),
    data: EvaluateRequest = EvaluateRequest(mode="new_only"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> EvaluateResponse:
    """触发对指定岗位的 AI 评估"""
    return await agent_service.trigger_evaluation(db, job_id, current_user, data)


@router.get(
    "/tasks/{job_id}",
    response_model=JobEvaluationTasksResponse,
    summary="获取岗位评估任务列表",
)
async def get_job_tasks(
    job_id: str = Path(..., description="岗位ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> JobEvaluationTasksResponse:
    """获取指定岗位的评估任务列表"""
    result = await agent_service.get_job_tasks(db, job_id, current_user)
    return result  # type: ignore[no-any-return]


@router.get(
    "/export/{task_id}",
    summary="导出评估结果为 Excel",
)
async def export_evaluation(
    task_id: str = Path(..., description="任务ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> StreamingResponse:
    """导出评估结果为 Excel (.xlsx) 文件"""
    excel_bytes = await agent_service.export_evaluation_to_excel(db, task_id, current_user)
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="evaluation_{task_id[:8]}.xlsx"'},
    )


@router.get(
    "/task/{task_id}",
    response_model=TaskStatusResponse,
    summary="查询评估任务状态",
)
async def get_task_status(
    task_id: str = Path(..., description="任务ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> TaskStatusResponse:
    """查询评估任务的进度和结果"""
    return await agent_service.get_task_status(db, task_id, current_user)


@router.post(
    "/confirm/{task_id}",
    response_model=ConfirmResponse,
    summary="确认评估结果",
)
async def confirm_evaluation(
    task_id: str = Path(..., description="任务ID"),
    data: ConfirmRequest = ConfirmRequest(decisions=[]),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ConfirmResponse:
    """确认评估结果，更新申请状态"""
    result: ConfirmResponse = await agent_service.confirm_evaluation(db, task_id, current_user, data)
    return result

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_required_user
from app.database import get_db
from app.models.user import User
from app.schemas.agent import (
    ConfirmRequest,
    ConfirmResponse,
    EvaluateRequest,
    EvaluateResponse,
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
    data: EvaluateRequest = EvaluateRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> EvaluateResponse:
    """触发对指定岗位下所有待处理申请的 AI 评估"""
    return await agent_service.trigger_evaluation(db, job_id, current_user, data)


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

import json

from fastapi import APIRouter, BackgroundTasks, Body, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_required_user
from app.database import get_db
from app.models.user import User
from app.services.evaluation import run_batch_evaluation
from app.services.placeholder_ai import (
    batch_screening_placeholder,
    chat_placeholder,
    evaluate_placeholder,
)

router = APIRouter(prefix="/agent", tags=["智能体"])


@router.post("/chat")
async def agent_chat(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """单智能体对话接口（SSE流式，占位实现）"""

    async def event_generator():
        result = await chat_placeholder(payload, current_user.role.value, str(current_user.id))
        yield f"data: {json.dumps({'type': 'final', 'content': result['content']}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/batch-screening")
async def start_batch_screening(
    job_id: str = Body(..., description="目标岗位ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """HR启动批量筛选（占位实现）"""
    return await batch_screening_placeholder(job_id=job_id, candidates_count=0)


@router.post("/evaluate/{job_id}")
async def manual_evaluate(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_required_user),
):
    """招聘者手动触发智能评估（占位实现）"""
    background_tasks.add_task(run_batch_evaluation, job_id)
    return await evaluate_placeholder(job_id)

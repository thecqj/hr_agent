import json
from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.database import get_db
from app.api.deps import get_required_user
from app.models.user import User
from app.services.agent.graph import agent_graph
from app.services.agent.state import AgentState
from app.models.job import Job
from fastapi import BackgroundTasks

router = APIRouter(prefix="/agent", tags=["智能体"])


@router.post("/chat")
async def agent_chat(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """单智能体对话接口（SSE流式）"""
    initial_state = AgentState(
        messages=[HumanMessage(content=payload.get("message", ""))],
        user_role=current_user.role.value,
        user_id=str(current_user.id),
        current_page=payload.get("current_page", "/"),
        context=payload.get("context", {}),
        user_profile=None,
        next_action="continue",
        pending_tool_calls=[],
        iteration_count=0,
        final_response=None,
    )
    config = {
        "configurable": {
            "thread_id": payload.get("conversation_id", str(current_user.id))
        }
    }

    async def event_generator():
        try:
            async for event in agent_graph.astream_events(
                initial_state, config=config, version="v1"
            ):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {json.dumps({'type': 'text', 'content': content}, ensure_ascii=False)}\n\n"
                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_call', 'tool': event['name']}, ensure_ascii=False)}\n\n"
                elif kind == "on_tool_end":
                    output = str(event["data"].get("output", ""))[:200]
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': event['name'], 'output': output}, ensure_ascii=False)}\n\n"
            final_state = agent_graph.get_state(config)
            if final_state and final_state.values.get("final_response"):
                yield f"data: {json.dumps({'type': 'final', 'content': final_state.values['final_response']}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/batch-screening")
async def start_batch_screening(
    job_id: str = Body(..., description="目标岗位ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
):
    """HR启动批量筛选"""
    # 1. 从数据库获取该岗位的所有投递
    from app.services import application_service
    applications, _ = await application_service.get_applications_for_job(
        db, job_id, current_user
    )
    candidates = []
    for app in applications:
        candidates.append({
            "id": app.id,
            "name": app.applicant.name if app.applicant else "未知",
            "resume_text": app.resume_text,
            "structured_resume": app.structured_resume,
            "status": app.status.value if app.status else "pending",
        })

    # 2. 初始化多智能体状态
    from app.services.agent.multi_agent_graph import multi_agent_graph
    from app.services.agent.state import MultiAgentState

    initial_state = MultiAgentState(
        messages=[],
        user_id=str(current_user.id),
        job_id=job_id,
        candidates=candidates,
        structured_candidates=[],
        scores=[],
        recommendations=[],
        hr_decision=None,
        next_action="parse",
        iteration_count=0,
        error=None,
    )

    # 3. 同步执行多智能体流程（实际可能用后台任务，这里简化）
    try:
        final_state = multi_agent_graph.invoke(initial_state)
        recommendations = final_state.get("recommendations", [])
        return {
            "status": "completed",
            "recommendations": recommendations,
            "message": f"已筛选出 {len(recommendations)} 名候选人，请确认"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    
@router.post("/evaluate/{job_id}")
async def manual_evaluate(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_required_user),
):
    """招聘者手动触发智能评估"""
    from app.services.evaluation import run_batch_evaluation

    # 验证权限：使用独立会话
    async with async_session() as db:
        job = await db.get(Job, job_id)
        if not job or job.recruiter_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权操作此岗位")

    background_tasks.add_task(run_batch_evaluation, job_id)
    return {"message": "评估任务已启动，请稍后刷新查看评分"}
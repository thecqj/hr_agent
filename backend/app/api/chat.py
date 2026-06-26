"""Chat API — 对话助手端点"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig

from app.api.deps import get_required_user
from app.database import async_session, get_checkpointer
from app.models.user import User, UserRole
from app.schemas.chat import ChatRequest
from app.services.conversation.state import ConversationState

router = APIRouter(prefix="/chat", tags=["对话助手"])


@router.post(
    "/send",
    summary="发送消息（SSE 流式响应）",
)
async def send_chat_message(
    data: ChatRequest,
    current_user: User = Depends(get_required_user),
) -> StreamingResponse:
    """发送消息，返回 SSE 流式响应。

    事件类型：thinking, intent, progress, result, error, done
    """
    if current_user.role != UserRole.RECRUITER:
        return StreamingResponse(
            _error_stream("仅招聘者可使用对话助手"),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _run_conversation_stream(data.message, str(current_user.id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _run_conversation_stream(
    message: str,
    user_id: str,
) -> AsyncGenerator[str, None]:
    """运行对话图并产出 SSE 事件流"""
    from app.services.conversation.graph import build_conversation_graph

    checkpointer = get_checkpointer()
    graph = build_conversation_graph(checkpointer)

    initial_state: ConversationState = {
        "user_message": message,
        "current_user_id": user_id,
        "errors": [],
    }

    thread_id = str(uuid.uuid4())

    async with async_session() as db:
        config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id,
                "db": db,
            }
        }

        try:
            async for event in graph.astream_events(
                initial_state, config=config, version="v2"
            ):
                if event.get("event") == "on_custom_event":
                    event_name = event.get("name", "")
                    event_data = event.get("data", {})

                    sse_event = _map_custom_event(event_name, event_data)
                    if sse_event:
                        yield sse_event

            # 获取最终状态用于 result 事件
            state_result = await graph.aget_state(config)
            final_state: ConversationState = state_result.values  # type: ignore[assignment]

            if final_state.get("reply_message"):
                result_data: dict[str, object] = {
                    "reply_message": final_state["reply_message"],
                }
                if final_state.get("reply_cards"):
                    result_data["cards"] = final_state["reply_cards"]

                yield f"event: result\ndata: {json.dumps(result_data, ensure_ascii=False)}\n\n"

            yield "event: done\ndata: {}\n\n"

        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': str(exc), 'recoverable': False}, ensure_ascii=False)}\n\n"
            yield "event: done\ndata: {}\n\n"


def _map_custom_event(name: str, data: dict[str, object] | Any) -> str | None:
    """将 LangGraph 自定义事件映射为 SSE 事件字符串"""
    if name in ("thinking", "intent", "progress"):
        return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    return None


async def _error_stream(message: str) -> AsyncGenerator[str, None]:
    """产出一个错误 SSE 事件流"""
    yield f"event: error\ndata: {json.dumps({'message': message, 'recoverable': False}, ensure_ascii=False)}\n\n"
    yield "event: done\ndata: {}\n\n"

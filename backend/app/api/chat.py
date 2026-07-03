"""Chat API — 对话助手端点"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select

from app.api.deps import get_required_user
from app.database import async_session, get_checkpointer
from app.models.conversation import Conversation
from app.models.user import User, UserRole
from app.schemas.chat import ChatRequest, SessionCloseRequest, SessionResponse, HistoryResponse

router = APIRouter(prefix="/chat", tags=["对话助手"])

# Summary 触发阈值：每 10 轮（20 条消息）触发一次滚动压缩
_SUMMARY_MESSAGE_THRESHOLD = 20


@router.post(
    "/send",
    summary="发送消息（SSE 流式响应）",
)
async def send_chat_message(
    data: ChatRequest,
    current_user: User = Depends(get_required_user),
) -> StreamingResponse:
    """发送消息，返回 SSE 流式响应。

    事件类型：session, tool_start, tool_end, text_delta, progress, result, error, done
    """
    if current_user.role != UserRole.RECRUITER:
        return StreamingResponse(
            _error_stream("仅招聘者可使用对话助手"),
            media_type="text/event-stream",
        )

    # Resolve or create session_id
    session_id = data.session_id
    if not session_id:
        session_id = str(uuid.uuid4())

    return StreamingResponse(
        _run_conversation_stream(data.message, str(current_user.id), session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/session/close",
    summary="关闭会话",
)
async def close_session(
    data: SessionCloseRequest,
    current_user: User = Depends(get_required_user),
) -> dict[str, str]:
    """关闭会话 — 仅做资源清理，不触发摘要生成"""
    async with async_session() as db:
        stmt = select(Conversation).where(
            Conversation.session_id == data.session_id,
            Conversation.user_id == current_user.id,
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            return {"message": "会话不存在"}

        # 不再设置 is_active = False
        # 不再触发摘要生成（摘要已在对话中滚动生成）
        # 保留 conversation 记录（用于历史查询）

    return {"message": "会话已关闭"}


@router.get(
    "/session",
    summary="查询会话",
)
async def get_session(
    session_id: str | None = Query(None, description="要检查的会话 ID"),
    current_user: User = Depends(get_required_user),
) -> SessionResponse:
    """查询当前用户的会话信息 — 通过 session_id 判断是否存在历史"""
    async with async_session() as db:
        if session_id:
            # Check specific session by session_id
            stmt = select(Conversation).where(
                Conversation.session_id == session_id,
                Conversation.user_id == current_user.id,
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()

            if conversation:
                return SessionResponse(
                    session_id=conversation.session_id,
                    has_history=True,
                )

            return SessionResponse(
                session_id=session_id,
                has_history=False,
            )
        else:
            # No session_id provided — no active session
            return SessionResponse(
                session_id="",
                has_history=False,
            )


@router.get(
    "/history",
    summary="获取对话历史消息",
)
async def get_chat_history(
    session_id: str = Query(..., description="会话 ID"),
    current_user: User = Depends(get_required_user),
) -> HistoryResponse:
    """从 LangGraph checkpoint 读取消息列表"""
    # Verify the conversation belongs to the current user
    async with async_session() as db:
        stmt = select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == current_user.id,
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

    if not conversation:
        return HistoryResponse(session_id=session_id, messages=[])

    # Load messages from LangGraph checkpoint
    from app.services.conversation.graph import build_conversation_graph

    checkpointer = get_checkpointer()
    graph = build_conversation_graph(checkpointer)
    config: RunnableConfig = {"configurable": {"thread_id": session_id}}

    try:
        state_result = await graph.aget_state(config)
        messages = state_result.values.get("messages", [])
    except Exception:
        messages = []

    from app.schemas.chat import HistoryMessage

    history_messages: list[HistoryMessage] = []
    for msg in messages:
        # Messages from LangGraph checkpoint can be either dict or
        # LangChain message objects (HumanMessage, AIMessage, etc.)
        if isinstance(msg, dict):
            msg_type = msg.get("type", "")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")
        else:
            msg_type = getattr(msg, "type", "")
            content = getattr(msg, "content", "")
            tool_calls = getattr(msg, "tool_calls", None)

        # Map LangGraph message types to user/assistant
        if msg_type in ("human", "user"):
            role: Literal["user", "assistant"] = "user"
        elif msg_type in ("ai", "assistant"):
            # Skip AI messages with tool_calls (intermediate reasoning steps)
            # These contain thinking text like "好的，我先查一下..." before
            # calling a tool — they should not appear as chat bubbles in history
            if tool_calls:
                continue
            role = "assistant"
        else:
            continue  # Skip system, tool messages

        history_messages.append(HistoryMessage(
            role=role,
            content=str(content),
            timestamp=0.0,  # LangGraph messages don't carry timestamps
        ))

    return HistoryResponse(session_id=session_id, messages=history_messages)


def _extract_history_from_messages(messages: list[Any]) -> list[dict[str, str]]:
    """从 LangGraph messages 中提取 user/assistant 文本对话列表"""
    history: list[dict[str, str]] = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("type", "")
            content = msg.get("content", "")
        else:
            role = getattr(msg, "type", "")
            content = getattr(msg, "content", "")
        if role in ("user", "ai", "assistant", "human"):
            role_key = "user" if role in ("user", "human") else "assistant"
            history.append({"role": role_key, "content": str(content)})
    return history


async def _run_conversation_stream(
    message: str,
    user_id: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """运行 ReAct Agent 并产出 SSE 事件流"""
    from app.services.conversation.graph import build_conversation_graph

    checkpointer = get_checkpointer()

    # ── 会话索引管理 ──────────────────────────────────────
    async with async_session() as db:
        stmt = select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == uuid.UUID(user_id),
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        # Security: if conversation exists but belongs to another user
        if conversation and conversation.user_id != uuid.UUID(user_id):
            session_id = str(uuid.uuid4())
            conversation = None

        if not conversation:
            # New session — no seed injection from previous sessions
            conversation = Conversation(
                user_id=uuid.UUID(user_id),
                session_id=session_id,
                summary=None,
            )
            db.add(conversation)
            await db.commit()

    # ── Build context for state_modifier ────────────────────
    context: dict[str, Any] = {}
    if conversation.summary:
        context["session_summary"] = conversation.summary

    # ── Emit session event first ─────────────────────────
    yield f"event: session\ndata: {json.dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"

    config: RunnableConfig = {
        "configurable": {
            "thread_id": session_id,
            "user_id": user_id,
        }
    }

    # Build graph with context injection
    graph = build_conversation_graph(checkpointer, context=context)

    # Input to the ReAct agent: a single HumanMessage
    input_messages = {"messages": [("user", message)]}

    try:
        async for event in graph.astream_events(
            input_messages, config=config, version="v2"
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk is None:
                    continue
                # Tool call chunks — we skip, tool_start/tool_end handle this
                if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                    continue
                # Text content — emit as text_delta
                if chunk.content:
                    # Normalize: content can be str or list[dict] (multimodal)
                    if isinstance(chunk.content, str):
                        text = chunk.content
                    elif isinstance(chunk.content, list):
                        text = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in chunk.content
                        )
                    else:
                        text = str(chunk.content)
                    if text:
                        yield f"event: text_delta\ndata: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                yield f"event: tool_start\ndata: {json.dumps({'tool': tool_name}, ensure_ascii=False)}\n\n"

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                yield f"event: tool_end\ndata: {json.dumps({'tool': tool_name}, ensure_ascii=False)}\n\n"

            elif kind == "on_custom_event":
                event_name = event.get("name", "")
                event_data = event.get("data", {})
                if event_name == "progress":
                    yield f"event: progress\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"

        # Get final state for result event and summary update
        state_result = await graph.aget_state(config)
        messages = state_result.values.get("messages", [])

        # The last AI message is the final reply
        final_reply = ""
        for msg in reversed(messages):
            if isinstance(msg, dict):
                if msg.get("type") == "ai":
                    content = msg.get("content", "")
                    if content and not msg.get("tool_calls"):
                        final_reply = content
                        break
            else:
                if getattr(msg, "type", None) == "ai":
                    content = getattr(msg, "content", "")
                    if content and not getattr(msg, "tool_calls", None):
                        final_reply = content
                        break

        if not final_reply:
            # Fallback: get last AI message with text content
            for msg in reversed(messages):
                if isinstance(msg, dict):
                    msg_type = msg.get("type", "")
                    if msg_type not in ("ai", "assistant"):
                        continue
                    content = msg.get("content", "")
                else:
                    msg_type = getattr(msg, "type", "")
                    if msg_type not in ("ai", "assistant"):
                        continue
                    content = getattr(msg, "content", "")
                if content:
                    final_reply = content
                    break

        # Always emit result event
        if not final_reply:
            final_reply = "抱歉，我暂时无法回复，请重试。"
        yield f"event: result\ndata: {json.dumps({'reply_message': final_reply}, ensure_ascii=False)}\n\n"

        # ── Rolling summary: every 10 turns (20 messages) ─────
        if len(messages) >= _SUMMARY_MESSAGE_THRESHOLD and len(messages) % _SUMMARY_MESSAGE_THRESHOLD == 0 and conversation:
            async with async_session() as update_db:
                update_stmt = select(Conversation).where(
                    Conversation.session_id == session_id,
                )
                update_result = await update_db.execute(update_stmt)
                conv = update_result.scalar_one_or_none()
                if conv:
                    # Rolling compression: old summary + all messages → new summary
                    from app.llm.deepseek import DeepSeekProvider

                    provider = None
                    try:
                        provider = DeepSeekProvider()

                        # Extract history for summarization
                        history_for_summary = _extract_history_from_messages(messages)

                        if history_for_summary:
                            new_summary = await provider.summarize_conversation(
                                history_for_summary,
                                existing_summary=conv.summary,
                            )
                            if len(new_summary) > 500:
                                new_summary = new_summary[:500]
                            conv.summary = new_summary
                    except Exception:
                        # Summary failure: keep existing summary, don't overwrite with error
                        pass
                    finally:
                        if provider is not None:
                            await provider.close()

                    await update_db.commit()

        yield "event: done\ndata: {}\n\n"

    except Exception as exc:
        yield f"event: error\ndata: {json.dumps({'message': str(exc), 'recoverable': False}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"


async def _error_stream(message: str) -> AsyncGenerator[str, None]:
    """产出一个错误 SSE 事件流"""
    yield f"event: error\ndata: {json.dumps({'message': message, 'recoverable': False}, ensure_ascii=False)}\n\n"
    yield "event: done\ndata: {}\n\n"

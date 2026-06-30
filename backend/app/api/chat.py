"""Chat API — 对话助手端点"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select

from app.api.deps import get_required_user
from app.database import async_session, get_checkpointer
from app.models.conversation import Conversation
from app.models.user import User, UserRole
from app.schemas.chat import ChatRequest, SessionCloseRequest, SessionResponse
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

    事件类型：session, thinking, intent, progress, result, error, done
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
    """关闭会话，将 is_active 设为 False，触发摘要生成"""
    async with async_session() as db:
        stmt = select(Conversation).where(
            Conversation.session_id == data.session_id,
            Conversation.user_id == current_user.id,
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            return {"message": "会话不存在"}

        if not conversation.is_active:
            return {"message": "会话已关闭"}

        conversation.is_active = False

        # Generate final summary if there's history in LangGraph Checkpoint
        from app.services.conversation.graph import build_conversation_graph

        checkpointer = get_checkpointer()
        graph = build_conversation_graph(checkpointer)
        config: RunnableConfig = {
            "configurable": {"thread_id": data.session_id}
        }
        try:
            state_result = await graph.aget_state(config)
            final_state: ConversationState = state_result.values  # type: ignore[assignment]

            chat_history = final_state.get("chat_history")
            # Generate summary only for substantial conversations
            if chat_history and len(chat_history) > 10:
                from app.services.conversation.nodes import _get_llm_provider

                provider = None
                try:
                    provider = _get_llm_provider()
                    existing_summary = final_state.get("session_summary")
                    summary = await provider.summarize_conversation(
                        [{"role": t["role"], "content": t["content"]} for t in chat_history],
                        existing_summary=existing_summary,
                    )
                    if len(summary) > 500:
                        summary = summary[:500]
                    conversation.summary = summary
                except Exception:
                    pass  # Summary failure is non-blocking
                finally:
                    if provider is not None:
                        await provider.close()

            # Always save context_entities
            context_entities = final_state.get("context_entities")
            if context_entities:
                conversation.context_entities = context_entities
        except Exception:
            pass  # Checkpoint read failure is non-blocking

        await db.commit()

    return {"message": "会话已关闭"}


@router.get(
    "/session",
    summary="查询当前活跃会话",
)
async def get_session(
    session_id: str | None = Query(None, description="要检查的会话 ID"),
    current_user: User = Depends(get_required_user),
) -> SessionResponse:
    """查询当前用户的活跃会话信息"""
    async with async_session() as db:
        if session_id:
            # Check specific session
            stmt = select(Conversation).where(
                Conversation.session_id == session_id,
                Conversation.user_id == current_user.id,
            )
        else:
            # Find most recent active session
            stmt = select(Conversation).where(
                Conversation.user_id == current_user.id,
                Conversation.is_active.is_(True),
            ).order_by(Conversation.updated_at.desc()).limit(1)

        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if conversation and conversation.is_active:
            return SessionResponse(
                session_id=conversation.session_id,
                has_history=True,
            )

        return SessionResponse(
            session_id=session_id or "",
            has_history=False,
        )


async def _run_conversation_stream(
    message: str,
    user_id: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """运行对话图并产出 SSE 事件流"""
    from app.services.conversation.graph import build_conversation_graph

    checkpointer = get_checkpointer()
    graph = build_conversation_graph(checkpointer)

    # ── 会话索引管理 ──────────────────────────────────────
    async with async_session() as db:
        stmt = select(Conversation).where(
            Conversation.session_id == session_id,
            Conversation.user_id == uuid.UUID(user_id),
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        # Security: if conversation exists but belongs to another user, generate new session
        if conversation and conversation.user_id != uuid.UUID(user_id):
            session_id = str(uuid.uuid4())
            conversation = None

        if not conversation:
            # New session — check for seed from previous session
            seed_summary: str | None = None
            seed_entities: dict[str, Any] | None = None

            prev_stmt = select(Conversation).where(
                Conversation.user_id == uuid.UUID(user_id),
                Conversation.is_active.is_(False),
            ).order_by(Conversation.updated_at.desc()).limit(1)
            prev_result = await db.execute(prev_stmt)
            prev_conversation = prev_result.scalar_one_or_none()

            if prev_conversation:
                seed_summary = prev_conversation.summary
                seed_entities = prev_conversation.context_entities

            conversation = Conversation(
                user_id=uuid.UUID(user_id),
                session_id=session_id,
                summary=seed_summary,
                context_entities=seed_entities,
                is_active=True,
            )
            db.add(conversation)
            await db.commit()

    # ── 构建 initial_state ────────────────────────────────
    # If there's a seed summary/entities, inject them into initial state
    seed_summary = conversation.summary if conversation else None
    seed_entities = conversation.context_entities if conversation else None

    initial_state: ConversationState = {
        "user_message": message,
        "current_user_id": user_id,
        "errors": [],
    }
    if seed_summary:
        initial_state["session_summary"] = seed_summary
    if seed_entities:
        initial_state["context_entities"] = seed_entities

    # ── Emit session event first ─────────────────────────
    yield f"event: session\ndata: {json.dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"

    async with async_session() as db:
        config: RunnableConfig = {
            "configurable": {
                "thread_id": session_id,
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

            # ── 更新 conversations 表的摘要/实体 ────────────
            if conversation:
                async with async_session() as update_db:
                    update_stmt = select(Conversation).where(
                        Conversation.session_id == session_id,
                    )
                    update_result = await update_db.execute(update_stmt)
                    conv = update_result.scalar_one_or_none()
                    if conv:
                        if final_state.get("session_summary"):
                            conv.summary = final_state["session_summary"]
                        if final_state.get("context_entities"):
                            conv.context_entities = final_state["context_entities"]
                        await update_db.commit()

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

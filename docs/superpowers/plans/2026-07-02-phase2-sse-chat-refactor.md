# Phase 2: SSE Adaptation + Chat API Refactoring

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt the Chat API (`chat.py`) to work with the new ReAct agent, replacing the old SSE event mapping (thinking/intent → tool_start/tool_end/text_delta) and updating conversation state management to work with `create_react_agent`'s message-based state.

**Architecture:** The `_run_conversation_stream()` generator is rewritten to call `create_react_agent` instead of the 14-node graph. SSE events are mapped from `astream_events()` v2 output: `on_chat_model_stream` → `text_delta`, `on_tool_start` → `tool_start`, `on_tool_end` → `tool_end`, `on_custom_event` → `progress`. The `close_session` and `get_chat_history` endpoints are adapted to read from the agent's message-based state instead of the old `ConversationState` TypedDict.

**Tech Stack:** LangGraph `astream_events` v2, FastAPI `StreamingResponse`, SSE protocol

## Global Constraints

- Same as Phase 1: strict type hints, mypy --strict, parameterized queries
- SSE event format remains `event: <type>\ndata: <json>\n\n`
- Backward-compatible: `session`, `progress`, `result`, `error`, `done` events unchanged
- New events: `tool_start`, `tool_end`, `text_delta` replace removed `thinking`, `intent`
- `result` event now only carries `reply_message` (Markdown text), no `cards`
- Conversation SQL table and its fields (`session_id`, `summary`, `context_entities`, `is_active`) unchanged
- `close_session` must still work for summary generation
- `get_chat_history` must still work for history restoration

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `backend/app/api/chat.py` | SSE event mapping + agent invocation |
| Modify | `backend/app/schemas/chat.py` | Add `ToolStartEvent`, `ToolEndEvent`, `TextDeltaEvent`; deprecate `ThinkingEvent`, `IntentEvent` |
| Modify | `backend/app/services/conversation/__init__.py` | Export context helper if needed |

---

### Task 1: Update SSE event schemas

**Files:**
- Modify: `backend/app/schemas/chat.py`

**Interfaces:**
- Consumes: Existing `ChatRequest`, `SessionCloseRequest`, etc.
- Produces: `ToolStartEvent`, `ToolEndEvent`, `TextDeltaEvent` (new); `ThinkingEvent`, `IntentEvent` kept but marked deprecated

- [ ] **Step 1: Add new event schemas and deprecate old ones**

In `backend/app/schemas/chat.py`, after `ProgressEvent` (line ~39), add:

```python
class ToolStartEvent(BaseModel):
    """tool_start 事件 — Tool 开始执行"""

    tool: str = Field(..., description="Tool 名称")


class ToolEndEvent(BaseModel):
    """tool_end 事件 — Tool 执行完毕"""

    tool: str = Field(..., description="Tool 名称")


class TextDeltaEvent(BaseModel):
    """text_delta 事件 — LLM 流式输出 token"""

    content: str = Field(..., description="增量文本内容")
```

Mark `ThinkingEvent` and `IntentEvent` as deprecated by adding a comment:

```python
class ThinkingEvent(BaseModel):
    """thinking 事件 — DEPRECATED: ReAct agent 无此阶段"""

    status: str


class IntentEvent(BaseModel):
    """intent 事件 — DEPRECATED: 不再有意图分类步骤"""

    intent: str
    params: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 2: Update `ResultEvent` — remove `cards` field**

The ReAct agent returns Markdown text directly; `cards` are no longer emitted in the result event. Change `ResultEvent` to:

```python
class ResultEvent(BaseModel):
    """result 事件"""

    reply_message: str
```

- [ ] **Step 3: Update `HistoryMessage` — remove `cards` field**

Chat history no longer stores cards. Change `HistoryMessage` to:

```python
class HistoryMessage(BaseModel):
    """历史消息条目"""

    role: Literal["user", "assistant"] = Field(..., description="角色")
    content: str = Field("", description="消息内容")
    timestamp: float = Field(..., description="时间戳")
```

- [ ] **Step 4: Verify mypy passes**

Run: `cd backend && uv run mypy --strict app/schemas/chat.py`

Expected: `Success: no issues found`

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/chat.py
git commit -m "feat: add tool_start/tool_end/text_delta SSE events, deprecate thinking/intent, remove cards from result"
```

---

### Task 2: Rewrite `_run_conversation_stream` for ReAct agent

**Files:**
- Modify: `backend/app/api/chat.py`

**Interfaces:**
- Consumes: `build_conversation_graph` (new signature from Phase 1), `ConversationContext` from `conversation.state`, `json` for SSE serialization
- Produces: Updated SSE stream with `tool_start`, `tool_end`, `text_delta` events

- [ ] **Step 1: Rewrite `_run_conversation_stream`**

Replace the entire `_run_conversation_stream` function (lines 220-342) with:

```python
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

    # ── Build context for state_modifier ────────────────────
    context: dict[str, Any] = {}
    if conversation.summary:
        context["session_summary"] = conversation.summary
    if conversation.context_entities:
        context["context_entities"] = conversation.context_entities

    # ── Emit session event first ─────────────────────────
    yield f"event: session\ndata: {json.dumps({'session_id': session_id}, ensure_ascii=False)}\n\n"

    async with async_session() as db:
        config: RunnableConfig = {
            "configurable": {
                "thread_id": session_id,
                "db": db,
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
                        yield f"event: text_delta\ndata: {json.dumps({'content': chunk.content}, ensure_ascii=False)}\n\n"

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

            # Get final state for result event and context update
            state_result = await graph.aget_state(config)
            messages = state_result.values.get("messages", [])

            # The last AI message is the final reply
            final_reply = ""
            for msg in reversed(messages):
                if hasattr(msg, "type") and msg.type == "ai":
                    content = getattr(msg, "content", "")
                    if content and not getattr(msg, "tool_calls", None):
                        final_reply = content
                        break
                elif isinstance(msg, dict) and msg.get("type") == "ai":
                    content = msg.get("content", "")
                    if content and not msg.get("tool_calls"):
                        final_reply = content
                        break

            if not final_reply:
                # Fallback: get last message content that's not a tool call
                for msg in reversed(messages):
                    content = getattr(msg, "content", "") if hasattr(msg, "content") else msg.get("content", "")
                    if content and not (hasattr(msg, "tool_calls") and msg.tool_calls):
                        final_reply = content
                        break

            if final_reply:
                yield f"event: result\ndata: {json.dumps({'reply_message': final_reply}, ensure_ascii=False)}\n\n"

            # ── Update conversations table ────────────────────
            if conversation:
                async with async_session() as update_db:
                    update_stmt = select(Conversation).where(
                        Conversation.session_id == session_id,
                    )
                    update_result = await update_db.execute(update_stmt)
                    conv = update_result.scalar_one_or_none()
                    if conv:
                        # History compression: if too many messages, generate summary
                        if len(messages) > 20:
                            from app.llm.deepseek import DeepSeekProvider

                            provider = None
                            try:
                                provider = DeepSeekProvider()
                                history_for_summary: list[dict[str, str]] = []
                                for msg in messages:
                                    role = getattr(msg, "type", msg.get("type", ""))
                                    content = getattr(msg, "content", msg.get("content", ""))
                                    if role in ("user", "ai", "assistant", "human"):
                                        role_key = "user" if role in ("user", "human") else "assistant"
                                        history_for_summary.append({"role": role_key, "content": str(content)})

                                if history_for_summary:
                                    new_summary = await provider.summarize_conversation(
                                        history_for_summary,
                                        existing_summary=conv.summary,
                                    )
                                    if len(new_summary) > 500:
                                        new_summary = new_summary[:500]
                                    conv.summary = new_summary
                            except Exception:
                                pass
                            finally:
                                if provider is not None:
                                    await provider.close()

                        # Update context_entities from final state
                        context_entities = state_result.values.get("context_entities")
                        if context_entities:
                            conv.context_entities = context_entities

                        await update_db.commit()

            yield "event: done\ndata: {}\n\n"

        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': str(exc), 'recoverable': False}, ensure_ascii=False)}\n\n"
            yield "event: done\ndata: {}\n\n"
```

- [ ] **Step 2: Update `send_chat_message` docstring**

Update the docstring of `send_chat_message` (line ~31) to reflect new events:

```python
    """发送消息，返回 SSE 流式响应。

    事件类型：session, tool_start, tool_end, text_delta, progress, result, error, done
    """
```

- [ ] **Step 3: Remove old `_map_custom_event` function**

Delete the `_map_custom_event` function (lines 344-348) — it's no longer used. The SSE event mapping is now inline in `_run_conversation_stream`.

- [ ] **Step 4: Clean up imports in chat.py**

Remove the now-unused import:

```python
from app.services.conversation.state import ConversationState
```

Add the import for `RunnableConfig` if not already present (it is, line 10).

- [ ] **Step 5: Verify mypy passes**

Run: `cd backend && uv run mypy --strict app/api/chat.py`

Expected: `Success: no issues found`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: rewrite _run_conversation_stream for ReAct agent SSE events"
```

---

### Task 3: Update `close_session` endpoint for ReAct agent state

**Files:**
- Modify: `backend/app/api/chat.py` (close_session function, lines 57-125)

**Interfaces:**
- Consumes: `build_conversation_graph` (new signature), message-based agent state
- Produces: Working session close with summary generation

- [ ] **Step 1: Rewrite `close_session` for message-based state**

Replace the `close_session` function with:

```python
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

        # Generate final summary from LangGraph checkpoint messages
        from app.services.conversation.graph import build_conversation_graph

        checkpointer = get_checkpointer()
        graph = build_conversation_graph(checkpointer)
        config: RunnableConfig = {
            "configurable": {"thread_id": data.session_id}
        }
        try:
            state_result = await graph.aget_state(config)
            messages = state_result.values.get("messages", [])

            # Generate summary only for substantial conversations
            if len(messages) > 10:
                from app.llm.deepseek import DeepSeekProvider

                provider = None
                try:
                    provider = DeepSeekProvider()
                    history_for_summary: list[dict[str, str]] = []
                    for msg in messages:
                        role = getattr(msg, "type", msg.get("type", ""))
                        content = getattr(msg, "content", msg.get("content", ""))
                        if role in ("user", "ai", "assistant", "human"):
                            role_key = "user" if role in ("user", "human") else "assistant"
                            history_for_summary.append({"role": role_key, "content": str(content)})

                    if history_for_summary:
                        summary = await provider.summarize_conversation(
                            history_for_summary,
                            existing_summary=conversation.summary,
                        )
                        if len(summary) > 500:
                            summary = summary[:500]
                        conversation.summary = summary
                except Exception:
                    pass  # Summary failure is non-blocking
                finally:
                    if provider is not None:
                        await provider.close()

            # Update context_entities if present in state
            context_entities = state_result.values.get("context_entities")
            if context_entities:
                conversation.context_entities = context_entities
        except Exception:
            pass  # Checkpoint read failure is non-blocking

        await db.commit()

    return {"message": "会话已关闭"}
```

- [ ] **Step 2: Verify mypy passes**

Run: `cd backend && uv run mypy --strict app/api/chat.py`

Expected: `Success: no issues found`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: update close_session for ReAct agent message-based state"
```

---

### Task 4: Update `get_chat_history` for message-based state

**Files:**
- Modify: `backend/app/api/chat.py` (get_chat_history function, lines 166-217)

**Interfaces:**
- Consumes: `build_conversation_graph` (new signature), message-based agent state
- Produces: Working chat history from LangGraph checkpoint messages

- [ ] **Step 1: Rewrite `get_chat_history` for message-based state**

Replace the `get_chat_history` function with:

```python
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
        msg_type = getattr(msg, "type", msg.get("type", ""))
        content = getattr(msg, "content", msg.get("content", ""))

        # Map LangGraph message types to user/assistant
        if msg_type in ("human", "user"):
            role: Literal["user", "assistant"] = "user"
        elif msg_type in ("ai", "assistant"):
            # Skip AI messages that are pure tool calls (no visible content)
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls and not content:
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
```

- [ ] **Step 2: Add `Literal` import if missing**

Check that `Literal` is imported at the top of `chat.py`. If not, add:

```python
from typing import Any, Literal
```

(Merge with existing `from typing import Any` line.)

- [ ] **Step 3: Verify mypy passes**

Run: `cd backend && uv run mypy --strict app/api/chat.py`

Expected: `Success: no issues found`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: update get_chat_history for ReAct agent message-based state"
```

---

### Task 5: Clean up `BaseLLMProvider` — remove `recognize_intent`

**Files:**
- Modify: `backend/app/llm/base.py`
- Modify: `backend/app/llm/deepseek.py`

**Interfaces:**
- Consumes: None
- Produces: `BaseLLMProvider` without `recognize_intent`; `DeepSeekProvider` without `recognize_intent`

- [ ] **Step 1: Remove `recognize_intent` from `BaseLLMProvider`**

In `backend/app/llm/base.py`, remove the `recognize_intent` abstract method (lines 31-41). The class should now have 3 abstract methods: `evaluate_resume`, `review_borderline`, `summarize_conversation`, and `close`.

Also remove the `IntentResult` import:

```python
from app.schemas.agent import BorderlineReview, ResumeEvaluation
```

- [ ] **Step 2: Remove `recognize_intent` from `DeepSeekProvider`**

In `backend/app/llm/deepseek.py`, remove the `recognize_intent` method (lines 118-139).

Also remove the `IntentResult` import:

```python
from app.schemas.agent import BorderlineReview, ResumeEvaluation
```

- [ ] **Step 3: Verify mypy passes on llm module**

Run: `cd backend && uv run mypy --strict app/llm/`

Expected: `Success: no issues found`

- [ ] **Step 4: Commit**

```bash
git add backend/app/llm/base.py backend/app/llm/deepseek.py
git commit -m "refactor: remove recognize_intent from LLM provider (replaced by ReAct agent)"
```

---

### Task 6: Delete old conversation test files

**Files:**
- Delete: `backend/tests/test_conversation_nodes.py`
- Delete: `backend/tests/test_intent_recognition.py`

**Interfaces:**
- Consumes: None (cleanup)
- Produces: No stale test references to old graph

- [ ] **Step 1: Delete old test files**

```bash
rm backend/tests/test_conversation_nodes.py
rm backend/tests/test_intent_recognition.py
```

- [ ] **Step 2: Verify remaining tests still pass**

Run: `cd backend && uv run pytest tests/ -v --ignore=tests/test_react_tools.py 2>&1 | tail -20`

Expected: All non-react-tool tests pass. (The react tools tests require DB, may fail without test DB.)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: delete old conversation_nodes and intent_recognition tests (replaced by ReAct agent)"
```

---

### Task 7: Rewrite Chat API tests for ReAct agent

**Files:**
- Create: `backend/tests/test_chat_api_v2.py`

**Interfaces:**
- Consumes: `conftest.py` fixtures, new SSE event types
- Produces: Test coverage for new SSE stream

- [ ] **Step 1: Write new Chat API tests**

```python
"""Chat API 测试 — ReAct Agent 版本"""

import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import AsyncClient


async def aiter(items: list[Any]) -> AsyncGenerator[Any, None]:
    """Helper: create an async iterator from a list"""
    for item in items:
        yield item


class TestChatSendEndpoint:
    """POST /api/chat/send 测试"""

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, client: AsyncClient) -> None:
        """未登录不能发送消息"""
        response = await client.post("/api/chat/send", json={"message": "测试"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_requires_recruiter(
        self,
        client: AsyncClient,
        auth_headers_seeker: dict[str, str],
    ) -> None:
        """求职者不能使用对话助手"""
        response = await client.post(
            "/api/chat/send",
            json={"message": "测试"},
            headers=auth_headers_seeker,
        )
        assert response.status_code == 200
        content = response.text
        assert "error" in content or "仅招聘者" in content

    @pytest.mark.asyncio
    async def test_chat_message_validation(
        self,
        client: AsyncClient,
        auth_headers_recruiter: dict[str, str],
    ) -> None:
        """消息不能为空"""
        response = await client.post(
            "/api/chat/send",
            json={"message": ""},
            headers=auth_headers_recruiter,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_returns_sse_stream_with_new_events(
        self,
        client: AsyncClient,
        auth_headers_recruiter: dict[str, str],
    ) -> None:
        """对话应返回 SSE 流，包含新事件类型"""
        # Mock the ReAct agent graph
        mock_state = MagicMock()
        mock_state.values = {
            "messages": [MagicMock(type="ai", content="你好！", tool_calls=None)],
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=aiter([]))
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_async_session = MagicMock(return_value=mock_session_ctx)

        with patch(
            "app.services.conversation.graph.build_conversation_graph",
            return_value=mock_graph,
        ), patch(
            "app.api.chat.get_checkpointer",
        ), patch(
            "app.api.chat.async_session",
            mock_async_session,
        ):
            response = await client.post(
                "/api/chat/send",
                json={"message": "你好"},
                headers=auth_headers_recruiter,
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            assert "event: session" in response.text

    @pytest.mark.asyncio
    async def test_sse_no_thinking_or_intent_events(
        self,
        client: AsyncClient,
        auth_headers_recruiter: dict[str, str],
    ) -> None:
        """SSE 流不应包含 thinking 或 intent 事件"""
        mock_state = MagicMock()
        mock_state.values = {
            "messages": [MagicMock(type="ai", content="回复", tool_calls=None)],
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=aiter([]))
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_async_session = MagicMock(return_value=mock_session_ctx)

        with patch(
            "app.services.conversation.graph.build_conversation_graph",
            return_value=mock_graph,
        ), patch(
            "app.api.chat.get_checkpointer",
        ), patch(
            "app.api.chat.async_session",
            mock_async_session,
        ):
            response = await client.post(
                "/api/chat/send",
                json={"message": "测试"},
                headers=auth_headers_recruiter,
            )
            content = response.text
            assert "event: thinking" not in content
            assert "event: intent" not in content


class TestSSEEventSerialization:
    """SSE 事件序列化测试"""

    def test_tool_start_event_serialization(self) -> None:
        """tool_start 事件序列化"""
        from app.schemas.chat import ToolStartEvent

        event = ToolStartEvent(tool="query_jobs")
        data = json.loads(event.model_dump_json())
        assert data["tool"] == "query_jobs"

    def test_tool_end_event_serialization(self) -> None:
        """tool_end 事件序列化"""
        from app.schemas.chat import ToolEndEvent

        event = ToolEndEvent(tool="query_jobs")
        data = json.loads(event.model_dump_json())
        assert data["tool"] == "query_jobs"

    def test_text_delta_event_serialization(self) -> None:
        """text_delta 事件序列化"""
        from app.schemas.chat import TextDeltaEvent

        event = TextDeltaEvent(content="你好")
        data = json.loads(event.model_dump_json())
        assert data["content"] == "你好"

    def test_result_event_no_cards(self) -> None:
        """result 事件不再包含 cards"""
        from app.schemas.chat import ResultEvent

        event = ResultEvent(reply_message="测试回复")
        data = json.loads(event.model_dump_json())
        assert "cards" not in data
        assert data["reply_message"] == "测试回复"
```

- [ ] **Step 2: Run the new tests**

Run: `cd backend && uv run pytest tests/test_chat_api_v2.py -v`

Expected: Unit tests (serialization) pass. Integration tests (SSE stream) may need proper mocking.

- [ ] **Step 3: Delete old test_chat_api.py**

```bash
rm backend/tests/test_chat_api.py
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: rewrite Chat API tests for ReAct agent SSE events"
```

---

### Task 8: Verify Phase 2 — full mypy + test suite

**Files:**
- No new files

- [ ] **Step 1: Run mypy on the full project**

Run: `cd backend && uv run mypy --strict app/`

Expected: `Success: no issues found in ... source files`

- [ ] **Step 2: Run remaining tests**

Run: `cd backend && uv run pytest tests/ -v --ignore=tests/test_react_tools.py 2>&1 | tail -30`

Expected: All pass (auth, jobs, applications, agent API tests).

- [ ] **Step 3: Commit any fixups if needed**

```bash
git add -A
git commit -m "fix: Phase 2 verification adjustments"
```

---

**Phase 2 Complete.** The Chat API now uses the ReAct agent, SSE events are adapted, and all old conversation node code paths are removed. Phase 3 will handle frontend adaptation and final test cleanup.

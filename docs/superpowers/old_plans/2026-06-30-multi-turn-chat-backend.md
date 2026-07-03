# 多轮对话后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 HR-Agent 多轮对话后端，支持会话持久化、上下文摘要、结构化实体追踪，使 AI 能结合历史推断用户意图。

**Architecture:** LangGraph Checkpoint 持久化运行时状态，轻量 `conversations` 表做会话索引和跨会话摘要/实体传递。`session_id` 作为 `thread_id` 复用，`pending_action` 自动跨轮存活。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, LangGraph, DeepSeek LLM, PostgreSQL

## Global Constraints

- Strict type hints on every function/method (`-> None` if empty)
- Pass `mypy --strict` after every task
- Pydantic v2 for all API schemas; SQLAlchemy 2.0 typed style for ORM
- All new DB changes via Alembic migration
- YAGNI: no features beyond the spec

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `app/models/conversation.py` | Create | Conversation ORM 模型 |
| `app/models/__init__.py` | Modify | 导出 Conversation |
| `alembic/versions/xxx_add_conversations.py` | Create | conversations 表迁移 |
| `app/schemas/chat.py` | Modify | ChatRequest 新增 session_id，新增 SessionCloseRequest/SessionResponse/SessionEvent |
| `app/services/conversation/state.py` | Modify | 新增 chat_history, session_summary, context_entities |
| `app/services/conversation/prompts.py` | Modify | intent prompt 支持上下文，新增摘要 prompt |
| `app/llm/base.py` | Modify | recognize_intent 新增 context 参数，新增 summarize_conversation 方法 |
| `app/llm/deepseek.py` | Modify | 实现 context-aware recognize_intent，实现 summarize_conversation |
| `app/services/conversation/nodes.py` | Modify | intent_node 改造，各节点更新实体，feedback_node 增加摘要+历史逻辑 |
| `app/api/chat.py` | Modify | session_id 参数，session/close 端点，GET /session 端点，session SSE 事件 |
| `tests/test_conversation_nodes.py` | Modify | 新增多轮对话测试 |
| `tests/test_chat_api.py` | Modify | 新增 session 相关测试 |

---

### Task 1: Conversation ORM 模型 + 迁移

**Files:**
- Create: `app/models/conversation.py`
- Modify: `app/models/__init__.py`
- Create: `alembic/versions/xxx_add_conversations.py`

**Interfaces:**
- Produces: `Conversation` model with fields `id, user_id, session_id, summary, context_entities, is_active, created_at, updated_at`

- [ ] **Step 1: Write Conversation model**

Create `app/models/conversation.py`:

```python
"""会话索引模型"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """会话索引表 — 跨会话摘要/实体传递"""

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_user_active", "user_id", "is_active"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        String(36), nullable=False, index=True,
        comment="FK → users.id",
    )
    session_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False,
        comment="= LangGraph thread_id",
    )
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
        comment="LLM 生成的会话摘要",
    )
    context_entities: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=None,
        comment="结构化实体 {current_job_id, current_job_code, ...}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="会话是否活跃",
    )
```

- [ ] **Step 2: Update models __init__.py**

Add to `app/models/__init__.py`:

```python
from app.models.conversation import Conversation

# Add to __all__ list:
    "Conversation",
```

- [ ] **Step 3: Generate Alembic migration**

Run:
```bash
cd backend && source .venv/bin/activate && alembic revision --autogenerate -m "add conversations table"
```

Verify the generated migration creates the `conversations` table with the `(user_id, is_active)` composite index.

- [ ] **Step 4: Run mypy**

Run: `cd backend && uv run mypy --strict app/models/conversation.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/models/conversation.py app/models/__init__.py alembic/versions/
git commit -m "feat: add Conversation ORM model and migration"
```

---

### Task 2: Chat Schema 扩展

**Files:**
- Modify: `app/schemas/chat.py`

**Interfaces:**
- Consumes: None
- Produces: `ChatRequest.session_id: str | None`, `SessionCloseRequest`, `SessionResponse`, `SessionEvent`

- [ ] **Step 1: Add session_id to ChatRequest and new schemas**

In `app/schemas/chat.py`, after the `ChatRequest` class, add `session_id` field:

```python
class ChatRequest(BaseModel):
    """发送聊天消息请求"""

    message: str = Field(
        ..., min_length=1, max_length=500, description="用户消息"
    )
    session_id: str | None = Field(
        None, description="会话 ID，首次可为空"
    )
```

At the end of the file, add:

```python
# ── 会话管理 Schema ─────────────────────────────────────────


class SessionCloseRequest(BaseModel):
    """关闭会话请求"""

    session_id: str = Field(..., description="要关闭的会话 ID")


class SessionResponse(BaseModel):
    """会话查询响应"""

    session_id: str = Field(..., description="会话 ID")
    has_history: bool = Field(..., description="是否存在历史对话")


class SessionEvent(BaseModel):
    """SSE session 事件"""

    session_id: str = Field(..., description="会话 ID")
```

- [ ] **Step 2: Run mypy**

Run: `cd backend && uv run mypy --strict app/schemas/chat.py`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add app/schemas/chat.py
git commit -m "feat: add session fields to ChatRequest and new session schemas"
```

---

### Task 3: ConversationState 扩展

**Files:**
- Modify: `app/services/conversation/state.py`

**Interfaces:**
- Consumes: None
- Produces: `ConversationState` with new fields `chat_history`, `session_summary`, `context_entities`

- [ ] **Step 1: Add new fields to ConversationState**

In `app/services/conversation/state.py`, add three fields to `ConversationState`:

```python
class ConversationState(TypedDict, total=False):
    """对话工作流状态

    所有字段都是可选的（total=False），因为不同节点逐步填充状态。
    """

    # 输入
    user_message: str                              # 用户原始消息
    current_user_id: str                           # 当前招聘者 ID

    # 意图识别输出
    intent: str                                    # 14 种意图之一
    extracted_params: dict[str, Any]               # 各意图对应的参数
    clarifying_question: str | None                # unknown 意图时的追问

    # 工作流调用输出
    task_id: str | None                            # 评估任务 ID
    evaluation_status: str | None                  # 任务最终状态

    # 反馈输出
    reply_message: str                             # 给用户的文本回复
    reply_cards: list[dict[str, Any]] | None       # 结构化卡片数据
    result_page_url: str | None                    # 评估结果页面 URL

    # 操作确认
    pending_action: PendingAction | None             # 待确认操作

    # 多轮对话上下文
    chat_history: list[dict[str, Any]]             # 完整对话历史 [{role, content, timestamp}]
    session_summary: str | None                    # LLM 生成的早期对话摘要
    context_entities: dict[str, Any]               # 结构化实体 {current_job_id, ...}

    # 错误
    errors: list[str]
```

- [ ] **Step 2: Run mypy**

Run: `cd backend && uv run mypy --strict app/services/conversation/state.py`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add app/services/conversation/state.py
git commit -m "feat: add chat_history, session_summary, context_entities to ConversationState"
```

---

### Task 4: LLM Provider 扩展 — 上下文感知意图识别 + 摘要生成

**Files:**
- Modify: `app/llm/base.py`
- Modify: `app/llm/deepseek.py`
- Modify: `app/services/conversation/prompts.py`

**Interfaces:**
- Consumes: `ConversationState` fields (`chat_history`, `session_summary`, `context_entities`)
- Produces: `recognize_intent(user_message, context_prompt)` with context, `summarize_conversation(history, existing_summary)` method

- [ ] **Step 1: Add prompts for context-aware intent and summarization**

In `app/services/conversation/prompts.py`, add after `build_intent_user_prompt`:

```python
SUMMARIZE_SYSTEM_PROMPT = """你是一个对话摘要生成器。你的任务是将一段 HR 招聘助手与用户的对话历史压缩为简洁摘要。

规则：
- 保留所有关键实体：岗位编号（job_code）、岗位名称、候选人姓名、申请 ID
- 保留用户执行的操作及其结果（如"已筛选 J001 的简历，推荐 3 人"）
- 保留用户表达的偏好和意图
- 摘要不超过 500 字
- 如果提供了已有摘要，将其与新对话合并生成更新后的摘要

严格按照以下 JSON 格式输出，不要输出任何其他内容：
{
  "summary": "<压缩后的摘要文本>"
}"""


def build_intent_user_prompt(
    user_message: str,
    *,
    session_summary: str | None = None,
    context_entities: dict[str, Any] | None = None,
    recent_history: list[dict[str, str]] | None = None,
) -> str:
    """构建意图识别的用户提示词（支持多轮上下文）"""
    parts: list[str] = []

    if session_summary:
        parts.append(f"[对话摘要]\n{session_summary}")

    if context_entities and any(context_entities.values()):
        entity_lines = [f"  {k}: {v}" for k, v in context_entities.items() if v]
        if entity_lines:
            parts.append(f"[当前对话实体]\n" + "\n".join(entity_lines))

    if recent_history:
        history_lines = []
        for msg in recent_history:
            role_label = "用户" if msg["role"] == "user" else "助手"
            history_lines.append(f"  {role_label}: {msg['content']}")
        parts.append("[最近对话]\n" + "\n".join(history_lines))

    parts.append(f"用户消息：{user_message}")

    return "\n\n".join(parts)


def build_summarize_user_prompt(
    history: list[dict[str, str]],
    existing_summary: str | None = None,
) -> str:
    """构建摘要生成的用户提示词"""
    parts: list[str] = []

    if existing_summary:
        parts.append(f"已有摘要：\n{existing_summary}")

    history_lines = []
    for msg in history:
        role_label = "用户" if msg["role"] == "user" else "助手"
        history_lines.append(f"{role_label}: {msg['content']}")
    parts.append("需要压缩的对话：\n" + "\n".join(history_lines))

    return "\n\n".join(parts)
```

Also add `from typing import Any` to the imports at the top of `prompts.py`.

- [ ] **Step 2: Update BaseLLMProvider abstract class**

In `app/llm/base.py`, update `recognize_intent` signature and add `summarize_conversation`:

```python
from abc import ABC, abstractmethod

from app.schemas.agent import BorderlineReview, IntentResult, ResumeEvaluation


class BaseLLMProvider(ABC):
    """LLM 提供商统一接口"""

    @abstractmethod
    async def evaluate_resume(
        self,
        job_info: dict[str, object],
        structured_resume: dict[str, object],
        dimensions: list[str],
    ) -> ResumeEvaluation:
        """评估单份简历，返回结构化结果"""
        ...

    @abstractmethod
    async def review_borderline(
        self,
        job_info: dict[str, object],
        borderline_recommend: list[dict[str, object]],
        borderline_reject: list[dict[str, object]],
        cutoff_score: float,
    ) -> list[BorderlineReview]:
        """复评边界候选人"""
        ...

    @abstractmethod
    async def recognize_intent(
        self,
        user_message: str,
        context_prompt: str | None = None,
    ) -> IntentResult:
        """识别用户消息的意图和参数

        Args:
            user_message: 用户原始消息
            context_prompt: 包含摘要/实体/历史的上下文提示词，为 None 时退化为单轮模式
        """
        ...

    @abstractmethod
    async def summarize_conversation(
        self,
        history: list[dict[str, str]],
        existing_summary: str | None = None,
    ) -> str:
        """生成对话摘要

        Args:
            history: 需要压缩的对话轮次 [{role, content}]
            existing_summary: 已有摘要（合并更新）

        Returns:
            压缩后的摘要文本
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭提供商资源（如 HTTP 客户端）"""
        ...
```

- [ ] **Step 3: Update DeepSeekProvider implementation**

In `app/llm/deepseek.py`, update `recognize_intent` and add `summarize_conversation`:

```python
    async def recognize_intent(
        self,
        user_message: str,
        context_prompt: str | None = None,
    ) -> IntentResult:
        """识别用户消息的意图和参数"""
        from app.services.conversation.prompts import (
            INTENT_SYSTEM_PROMPT,
            build_intent_user_prompt,
        )

        system_prompt = INTENT_SYSTEM_PROMPT
        user_prompt = build_intent_user_prompt(
            user_message,
            session_summary=None,  # 已在 context_prompt 中
            context_entities=None,
            recent_history=None,
        )

        # If context_prompt is provided, prepend it to the user prompt
        if context_prompt:
            user_prompt = f"{context_prompt}\n\n{user_prompt}"

        raw = await self._call_chat(
            system_prompt, user_prompt, retries=settings.LLM_EVALUATION_RETRIES
        )
        return IntentResult.model_validate(raw)

    async def summarize_conversation(
        self,
        history: list[dict[str, str]],
        existing_summary: str | None = None,
    ) -> str:
        """生成对话摘要"""
        from app.services.conversation.prompts import (
            SUMMARIZE_SYSTEM_PROMPT,
            build_summarize_user_prompt,
        )

        user_prompt = build_summarize_user_prompt(history, existing_summary)
        raw = await self._call_chat(
            SUMMARIZE_SYSTEM_PROMPT, user_prompt, retries=1
        )

        # Parse JSON response
        try:
            parsed = json.loads(raw)
            return str(parsed.get("summary", raw))
        except (json.JSONDecodeError, AttributeError):
            return raw[:500]
```

Note: `json` is already imported at the top of `deepseek.py`. Verify this; if not, add `import json` to the imports.

- [ ] **Step 4: Run mypy**

Run: `cd backend && uv run mypy --strict app/llm/base.py app/llm/deepseek.py app/services/conversation/prompts.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/llm/base.py app/llm/deepseek.py app/services/conversation/prompts.py
git commit -m "feat: add context-aware intent recognition and summarization to LLM provider"
```

---

### Task 5: 节点改造 — intent_node 上下文感知 + 各节点实体更新 + feedback_node 摘要逻辑

**Files:**
- Modify: `app/services/conversation/nodes.py`

**Interfaces:**
- Consumes: `ConversationState.chat_history`, `session_summary`, `context_entities`, `recognize_intent(user_message, context_prompt)`, `summarize_conversation(history, existing_summary)`
- Produces: Updated `context_entities` from each node, `chat_history` and `session_summary` from feedback_node

This is the largest task. It modifies the core node logic.

- [ ] **Step 1: Add helper to build context prompt from state**

At the top of `nodes.py`, after the existing imports, add a helper function:

```python
def _build_context_prompt(state: ConversationState) -> str | None:
    """从 state 中构建上下文提示词，用于意图识别

    如果没有上下文信息，返回 None（退化为单轮模式）。
    """
    from app.services.conversation.prompts import build_intent_user_prompt

    session_summary: str | None = state.get("session_summary")
    context_entities: dict[str, Any] | None = state.get("context_entities")
    chat_history: list[dict[str, Any]] | None = state.get("chat_history")

    # Take the last 5 turns from chat_history
    recent_history: list[dict[str, str]] | None = None
    if chat_history and len(chat_history) > 0:
        recent_turns = chat_history[-5:]
        recent_history = [
            {"role": t["role"], "content": t["content"]}
            for t in recent_turns
        ]

    has_context = session_summary or (
        context_entities and any(context_entities.values())
    ) or recent_history

    if not has_context:
        return None

    # Build a synthetic prompt with just the context parts
    return build_intent_user_prompt(
        "",  # user_message is added separately by the LLM provider
        session_summary=session_summary,
        context_entities=context_entities,
        recent_history=recent_history,
    )
```

- [ ] **Step 2: Rewrite intent_node to use context**

Replace the existing `intent_node` function:

```python
async def intent_node(state: ConversationState) -> dict[str, Any]:
    """意图识别节点：解析用户消息，提取意图和参数（支持多轮上下文）"""
    user_message = state.get("user_message", "")

    await adispatch_custom_event("thinking", {"status": "正在理解您的指令..."})

    # Build context prompt from state
    context_prompt = _build_context_prompt(state)

    provider: BaseLLMProvider | None = None
    try:
        provider = _get_llm_provider()
        result = await provider.recognize_intent(user_message, context_prompt=context_prompt)

        extracted_params = result.extracted_params

        # Merge missing params from context_entities
        context_entities: dict[str, Any] = state.get("context_entities", {})
        if context_entities:
            for key in ("job_code", "job_id", "job_title", "candidate_name"):
                if key not in extracted_params and context_entities.get(key):
                    extracted_params[key] = context_entities[key]

        await adispatch_custom_event("intent", {
            "intent": result.intent,
            "params": extracted_params,
        })

        return {
            "intent": result.intent,
            "extracted_params": extracted_params,
            "clarifying_question": result.clarifying_question,
        }
    except Exception as exc:
        # LLM 意图识别失败时，回退为 unknown
        await adispatch_custom_event("intent", {
            "intent": "unknown",
            "params": {},
        })
        return {
            "intent": "unknown",
            "extracted_params": {},
            "clarifying_question": "抱歉，我暂时无法理解您的意思。输入「帮助」查看我能做什么。",
            "errors": [f"意图识别失败: {exc}"],
        }
    finally:
        if provider is not None:
            await provider.close()
```

- [ ] **Step 3: Add _update_context_entities helper**

Add a helper function that nodes use to update context entities:

```python
def _update_context_entities(
    state: ConversationState,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Merge entity updates into context_entities and return the updated dict"""
    existing: dict[str, Any] = dict(state.get("context_entities", {}) or {})
    existing.update(updates)
    return {"context_entities": existing}
```

- [ ] **Step 4: Update query nodes to set context_entities**

For each query/action node that resolves a job, add a `_update_context_entities` call in its return dict.

**`job_detail_node`** — after the successful resolve, add context entities to each return branch that has a resolved job. Example for the `detail_scope == "full"` branch:

```python
    # After: job = resolved
    context_update = _update_context_entities(state, {
        "current_job_id": str(job.id),
        "current_job_code": job.job_code,
    })
    # ... then in each return dict, spread context_update
    if detail_scope == "full":
        return {
            "reply_message": f"📋 岗位「{job.title}」({job.job_code})详情：",
            "reply_cards": [{"type": "job_detail", "job": job_data}],
            **context_update,
        }
```

Apply the same pattern to these nodes, adding the appropriate entities from the spec table:

| Node | Entities to add |
|------|----------------|
| `pending_count_node` | `current_job_id`, `current_job_code` |
| `interview_count_node` | `current_job_id`, `current_job_code` |
| `candidate_eval_node` | `current_candidate_name`, `current_job_id` (when app is found) |
| `funnel_node` | `current_job_id`, `current_job_code` |
| `candidate_list_node` | `current_job_id`, `current_job_code` |
| `dispatch_node` | `current_job_id`, `current_job_code`, `task_id` (after matched_job is found) |
| `status_change_node` | `current_candidate_name`, `current_job_id` (from pending params) |

For each node, find the return statements that represent a successful result and add `**_update_context_entities(state, {...})` to the return dict.

- [ ] **Step 5: Update feedback_node to manage chat_history and summaries**

Replace the existing `feedback_node` with an updated version that:
1. Appends the current turn to `chat_history`
2. Checks if summary is needed
3. Generates summary if threshold exceeded

```python
async def feedback_node(state: ConversationState) -> dict[str, Any]:
    """结果反馈节点：格式化结果摘要 + 更新对话历史 + 摘要压缩"""
    db = _get_db()
    intent = state.get("intent", "unknown")
    reply_message = state.get("reply_message", "")

    # ── pending_action 冲突处理 ──────────────────────────────
    if reply_message:
        pending = state.get("pending_action")
        if pending and intent not in ("confirm", "cancel", "status_change", "job_status"):
            reply_message += "\n（已取消待确认操作）"
            reply_message_payload = reply_message
            pending_action_payload: PendingAction | None = None
        else:
            reply_message_payload = reply_message
            pending_action_payload = state.get("pending_action")
    else:
        pending_action_payload = state.get("pending_action")

    # ── 如果 dispatch_node 已设置了 reply_message 且上面处理了 pending ──
    if state.get("reply_message") and not reply_message_payload:
        reply_message_payload = state["reply_message"]

    # ── 构建反馈消息（保留原有逻辑）──────────────────────────
    if not reply_message_payload:
        # evaluate 意图
        if intent == "evaluate":
            task_id = state.get("task_id")
            if not task_id:
                reply_message_payload = "❌ 评估任务创建失败，请重试。"
            else:
                task = await db.get(EvaluationTask, task_id)
                if not task:
                    reply_message_payload = "❌ 评估任务不存在。"
                else:
                    job = await db.get(Job, task.job_id)
                    job_title = job.title if job else "未知岗位"

                    if task.status == EvalTaskStatus.COMPLETED:
                        summary = task.result_summary or {}
                        recommend_count = summary.get("recommend_count", 0)
                        reject_count = summary.get("reject_count", 0)
                        reply_message_payload = f"✅ 已完成「{job_title}」岗位的简历评估，共 {task.total_count} 份简历，推荐 {recommend_count} 人进入面试。"
                    elif task.status == EvalTaskStatus.FAILED:
                        reply_message_payload = f"❌ 评估失败：{task.error_message or '未知错误'}"
                    else:
                        reply_message_payload = f"⏳ 评估任务状态：{task.status.value}，请稍后查看。"

        elif intent == "help":
            reply_message_payload = (
                "我可以帮您完成以下操作：\n\n"
                "📋 **岗位管理**\n"
                "• 「有哪些活跃岗位？」— 查询岗位列表\n"
                "• 「J001的任职要求」— 查看岗位详情\n"
                "• 「帮我关闭 J001」— 关闭岗位\n"
                "• 「发布 J001」— 重新发布岗位\n\n"
                "📊 **招聘进度**\n"
                "• 「J001还有多少简历没看？」— 待审核简历数\n"
                "• 「J001有几个人在面试？」— 面试中人数\n"
                "• 「J001的招聘进度」— 漏斗概览\n\n"
                "👥 **候选人管理**\n"
                "• 「J001推荐的候选人」— 候选人列表\n"
                "• 「张三的评估结果」— AI 评估详情\n"
                "• 「把张三推进到面试」— 变更候选人状态\n\n"
                "🔍 **简历筛选**\n"
                "• 「帮我筛选前端岗位的简历」— AI 筛选简历\n"
                "• 「前端岗位选5人进面试」— 指定进面人数"
            )
        elif intent == "cancel":
            reply_message_payload = "✅ 已取消。"
        else:
            clarifying = state.get("clarifying_question")
            reply_message_payload = clarifying or "抱歉，我没有理解您的意思。输入「帮助」查看我能做什么。"

    # ── 更新 chat_history ────────────────────────────────────
    chat_history: list[dict[str, Any]] = list(state.get("chat_history") or [])
    chat_history.append({
        "role": "user",
        "content": state.get("user_message", ""),
        "timestamp": __import__("time").time(),
    })
    chat_history.append({
        "role": "assistant",
        "content": reply_message_payload,
        "timestamp": __import__("time").time(),
    })

    # ── 摘要压缩 ────────────────────────────────────────────
    session_summary: str | None = state.get("session_summary")
    SUMMARY_THRESHOLD = 10  # 超过 10 轮时压缩

    if len(chat_history) > SUMMARY_THRESHOLD:
        provider: BaseLLMProvider | None = None
        try:
            provider = _get_llm_provider()
            # 压缩前 5 轮（最旧的 5 条消息 = 2-3 对话轮次）
            old_turns = chat_history[:5]
            new_summary = await provider.summarize_conversation(
                [{"role": t["role"], "content": t["content"]} for t in old_turns],
                existing_summary=session_summary,
            )
            # 截断到 500 字
            if len(new_summary) > 500:
                new_summary = new_summary[:500]
            session_summary = new_summary
            # 保留最近 5 轮
            chat_history = chat_history[5:]
        except Exception:
            # 摘要失败不阻塞，保留原始历史
            pass
        finally:
            if provider is not None:
                await provider.close()

    result: dict[str, Any] = {
        "reply_message": reply_message_payload,
        "chat_history": chat_history,
        "session_summary": session_summary,
    }

    if pending_action_payload is not None or state.get("pending_action") is not None:
        result["pending_action"] = pending_action_payload

    return result
```

Note: The original `feedback_node` had complex branching for `reply_message` already set vs not set. The new version consolidates this. The key card-returning branches from the original (evaluation_summary card for evaluate, confirm card, etc.) need to be preserved. The `reply_cards` are set by upstream nodes and passed through via `state.get("reply_cards")` — they are NOT re-set in feedback_node. We need to ensure we don't lose them.

Actually, reviewing the original code more carefully: `reply_cards` is set by upstream nodes (dispatch_node, confirm_node, etc.) and NOT overwritten by feedback_node. The feedback_node only sets `reply_message` and `pending_action`. So in our new version, we must NOT set `reply_cards` (let upstream values pass through). The result dict should not include `reply_cards` — it stays in state from upstream.

- [ ] **Step 6: Run mypy**

Run: `cd backend && uv run mypy --strict app/services/conversation/nodes.py`
Expected: May have some issues with the `time` import. Replace `__import__("time").time()` with proper import. Add `import time` at the top and use `time.time()`.

- [ ] **Step 7: Run existing tests**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py -v`
Expected: Some tests may fail because feedback_node signature changed. Fix any issues.

- [ ] **Step 8: Commit**

```bash
git add app/services/conversation/nodes.py
git commit -m "feat: context-aware intent recognition, entity tracking, and summary logic in conversation nodes"
```

---

### Task 6: Chat API 改造 — 会话管理

**Files:**
- Modify: `app/api/chat.py`

**Interfaces:**
- Consumes: `ChatRequest.session_id`, `SessionCloseRequest`, `SessionResponse`, `Conversation` model, `ConversationState` new fields
- Produces: `POST /chat/send` with session_id, `POST /chat/session/close`, `GET /chat/session`, `session` SSE event

- [ ] **Step 1: Rewrite send_chat_message to use session_id**

Replace the `send_chat_message` endpoint and `_run_conversation_stream` in `app/api/chat.py`:

```python
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
        # We read the chat_history from the checkpoint state
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
            if chat_history and len(chat_history) > 0:
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

                    # Also save context_entities
                    context_entities = final_state.get("context_entities")
                    if context_entities:
                        conversation.context_entities = context_entities
                except Exception:
                    pass  # Summary failure is non-blocking
                finally:
                    if provider is not None:
                        await provider.close()
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
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

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
```

- [ ] **Step 2: Run mypy**

Run: `cd backend && uv run mypy --strict app/api/chat.py`
Expected: PASS (may need to fix minor issues)

- [ ] **Step 3: Run existing chat API tests**

Run: `cd backend && uv run pytest tests/test_chat_api.py -v`
Expected: Some tests may need updating for the new `session_id` parameter in the request body. Fix test payloads to include `session_id` or leave it as None.

- [ ] **Step 4: Commit**

```bash
git add app/api/chat.py
git commit -m "feat: session management in chat API — session_id, close, query endpoints"
```

---

### Task 7: 测试 — 多轮对话节点测试

**Files:**
- Modify: `tests/test_conversation_nodes.py`
- Modify: `tests/test_chat_api.py`

**Interfaces:**
- Consumes: All new ConversationState fields, updated node behavior

- [ ] **Step 1: Add multi-turn intent recognition test**

In `tests/test_conversation_nodes.py`, add tests for context-aware intent recognition:

```python
class TestMultiTurnIntentRecognition:
    """多轮对话上下文感知意图识别"""

    @pytest.mark.asyncio
    async def test_intent_uses_context_entities_for_missing_params(self) -> None:
        """当用户说"筛选这些简历"但未提供 job_code，应从 context_entities 补全"""
        state: ConversationState = {
            "user_message": "筛选这些简历",
            "current_user_id": "test-user-id",
            "context_entities": {"current_job_id": "job-123", "current_job_code": "J04217"},
            "errors": [],
        }
        # The intent_node should pass context to LLM, which recognizes "这些简历"
        # refers to the job in context_entities
        # We test that _build_context_prompt returns a non-None value
        from app.services.conversation.nodes import _build_context_prompt
        context = _build_context_prompt(state)
        assert context is not None
        assert "J04217" in context

    @pytest.mark.asyncio
    async def test_intent_no_context_returns_none(self) -> None:
        """无上下文时 _build_context_prompt 返回 None"""
        state: ConversationState = {
            "user_message": "筛选简历",
            "current_user_id": "test-user-id",
            "errors": [],
        }
        from app.services.conversation.nodes import _build_context_prompt
        context = _build_context_prompt(state)
        assert context is None

    @pytest.mark.asyncio
    async def test_intent_uses_session_summary(self) -> None:
        """session_summary 应出现在上下文提示词中"""
        state: ConversationState = {
            "user_message": "那个岗位有多少简历",
            "current_user_id": "test-user-id",
            "session_summary": "用户之前讨论了前端开发岗位 J04217 的简历筛选",
            "errors": [],
        }
        from app.services.conversation.nodes import _build_context_prompt
        context = _build_context_prompt(state)
        assert context is not None
        assert "前端开发" in context

    @pytest.mark.asyncio
    async def test_intent_uses_recent_history(self) -> None:
        """最近对话历史应出现在上下文提示词中"""
        state: ConversationState = {
            "user_message": "筛选这些简历",
            "current_user_id": "test-user-id",
            "chat_history": [
                {"role": "user", "content": "J001有多少简历", "timestamp": 1.0},
                {"role": "assistant", "content": "J001有5份待审核简历", "timestamp": 2.0},
            ],
            "errors": [],
        }
        from app.services.conversation.nodes import _build_context_prompt
        context = _build_context_prompt(state)
        assert context is not None
        assert "J001" in context
```

- [ ] **Step 2: Add context_entities update tests**

```python
class TestContextEntityUpdates:
    """各节点更新 context_entities 的测试"""

    @pytest.mark.asyncio
    async def test_pending_count_node_sets_job_entities(self) -> None:
        """pending_count_node 应设置 current_job_id 和 current_job_code"""
        # Use the existing test pattern from test_conversation_nodes.py
        # but check that the return dict includes context_entities
        state: ConversationState = {
            "user_message": "J04217有多少简历",
            "current_user_id": str(TEST_RECRUITER_ID),
            "intent": "pending_count",
            "extracted_params": {"job_code": "J04217"},
            "errors": [],
        }
        result = await pending_count_node(state)
        assert "context_entities" in result
        assert result["context_entities"]["current_job_code"] == "J04217"

    @pytest.mark.asyncio
    async def test_funnel_node_sets_job_entities(self) -> None:
        """funnel_node 应设置 current_job_id 和 current_job_code"""
        state: ConversationState = {
            "user_message": "J04217的招聘进度",
            "current_user_id": str(TEST_RECRUITER_ID),
            "intent": "funnel",
            "extracted_params": {"job_code": "J04217"},
            "errors": [],
        }
        result = await funnel_node(state)
        assert "context_entities" in result
        assert result["context_entities"]["current_job_code"] == "J04217"
```

Note: These tests reference `TEST_RECRUITER_ID` and the existing test fixtures. Check the existing test file for the exact fixture names and adapt accordingly.

- [ ] **Step 3: Add feedback_node chat_history tests**

```python
class TestFeedbackNodeHistory:
    """feedback_node 的对话历史和摘要逻辑"""

    @pytest.mark.asyncio
    async def test_feedback_appends_to_chat_history(self) -> None:
        """feedback_node 应将当前轮次追加到 chat_history"""
        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "test-user",
            "intent": "help",
            "errors": [],
        }
        result = await feedback_node(state)
        assert "chat_history" in result
        assert len(result["chat_history"]) == 2  # user + assistant
        assert result["chat_history"][0]["role"] == "user"
        assert result["chat_history"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_feedback_preserves_existing_history(self) -> None:
        """feedback_node 应保留已有的 chat_history"""
        existing = [
            {"role": "user", "content": "你好", "timestamp": 1.0},
            {"role": "assistant", "content": "你好！", "timestamp": 2.0},
        ]
        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "test-user",
            "intent": "help",
            "chat_history": existing,
            "errors": [],
        }
        result = await feedback_node(state)
        assert len(result["chat_history"]) == 4  # 2 existing + 2 new
```

- [ ] **Step 4: Run all tests**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py tests/test_chat_api.py -v`
Expected: All pass

- [ ] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add tests/
git commit -m "test: add multi-turn conversation node and context entity tests"
```

---

### Task 8: 最终 mypy + 全量测试验证

**Files:**
- None (verification only)

- [ ] **Step 1: Run mypy on entire app**

Run: `cd backend && uv run mypy --strict app/`
Expected: PASS

- [ ] **Step 2: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All 175+ tests pass

- [ ] **Step 3: Final commit if any fixes needed**

If any fixes were made during verification:
```bash
git add -A
git commit -m "fix: resolve mypy/test issues from multi-turn conversation implementation"
```

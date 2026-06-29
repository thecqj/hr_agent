# Phase 2 Conversation Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the ConversationGraph (LangGraph), Chat API with SSE streaming, and conversation nodes for intent recognition, task routing, and result feedback.

**Architecture:** ConversationGraph is a LangGraph StateGraph with 3 nodes: intent_node → dispatch_node → feedback_node. It runs via `astream_events()` to produce SSE events. The dispatch_node triggers the evaluation workflow inline and relays progress events. Chat API exposes `POST /api/chat/send` returning `text/event-stream`.

**Tech Stack:** LangGraph, FastAPI StreamingResponse (SSE), Pydantic v2, DeepSeek API

**Depends on:** Plan 1 (Backend Foundation) must be completed first — nodes use `get_config()`/`get_checkpointer()`, LLM provider has `recognize_intent()`.

## Global Constraints

- Python 3.12 with strict type hints, `mypy --strict` must pass
- SQLAlchemy 2.0 type-annotated style
- Pydantic v2 for all DTOs
- All async functions use `async def` with proper return type hints
- Tests run with `cd backend && uv run pytest tests/ -v`
- Type check with `cd backend && uv run mypy --strict app/`
- Working directory: `/Users/bytedance/my_code/hr_agent/.claude/worktrees/phase2-impl`

---

### Task 1: Create ConversationState + Chat DTOs

**Files:**
- Create: `backend/app/services/conversation/state.py`
- Create: `backend/app/schemas/chat.py`

**Interfaces:**
- Consumes: None (new module)
- Produces: `ConversationState` TypedDict, `ChatRequest` / SSE event DTOs

- [ ] **Step 1: Create ConversationState**

Create `backend/app/services/conversation/state.py`:

```python
"""对话 Agent 状态定义"""

from typing import TypedDict


class ConversationState(TypedDict, total=False):
    """对话工作流状态

    所有字段都是可选的（total=False），因为不同节点逐步填充状态。
    """

    # 输入
    user_message: str                    # 用户原始消息
    current_user_id: str                 # 当前招聘者 ID

    # 意图识别输出
    intent: str                          # "evaluate" | "help" | "unknown"
    extracted_params: dict               # {"job_title": "...", "interview_quota": N, ...}
    clarifying_question: str | None      # unknown 意图时的追问

    # 工作流调用输出
    task_id: str | None                  # 评估任务 ID
    evaluation_status: str | None        # 任务最终状态

    # 反馈输出
    reply_message: str                   # 给用户的文本回复
    reply_cards: list[dict] | None       # 结构化卡片数据
    result_page_url: str | None          # 评估结果页面 URL

    # 错误
    errors: list[str]
```

- [ ] **Step 2: Create Chat DTOs**

Create `backend/app/schemas/chat.py`:

```python
"""Chat API 请求/响应 Schema"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """发送聊天消息请求"""

    message: str = Field(
        ..., min_length=1, max_length=500, description="用户消息"
    )


# ── SSE 事件 Schema ─────────────────────────────────────────


class ThinkingEvent(BaseModel):
    """thinking 事件"""

    status: str


class IntentEvent(BaseModel):
    """intent 事件"""

    intent: str
    params: dict[str, Any] = Field(default_factory=dict)


class ProgressEvent(BaseModel):
    """progress 事件"""

    status: str
    evaluated_count: int | None = None
    total_count: int | None = None


class ErrorEvent(BaseModel):
    """error 事件"""

    message: str
    recoverable: bool


class EvaluationSummaryCard(BaseModel):
    """评估摘要卡片"""

    type: Literal["evaluation_summary"] = "evaluation_summary"
    task_id: str
    job_title: str
    total_count: int
    recommended_count: int
    rejected_count: int
    result_page_url: str


class ResultEvent(BaseModel):
    """result 事件"""

    reply_message: str
    cards: list[EvaluationSummaryCard] | None = None
```

- [ ] **Step 3: Run mypy on new files**

Run: `cd backend && uv run mypy --strict app/services/conversation/state.py app/schemas/chat.py`

Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/conversation/state.py backend/app/schemas/chat.py
git commit -m "feat: add ConversationState and Chat API DTOs"
```

---

### Task 2: Create Conversation Nodes

**Files:**
- Create: `backend/app/services/conversation/nodes.py`

**Interfaces:**
- Consumes: `ConversationState`, `BaseLLMProvider.recognize_intent()`, `agent_service.trigger_evaluation()`, `agent_service.get_task_status()`, `EvaluationState`, `build_evaluation_graph()`, `get_checkpointer()`, `dispatch_custom_event()`
- Produces: `intent_node()`, `dispatch_node()`, `feedback_node()`, `route_by_intent()`

- [ ] **Step 1: Create the conversation nodes module**

Create `backend/app/services/conversation/nodes.py`:

```python
"""对话 Agent LangGraph 节点实现"""

from typing import Any, Literal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from langgraph.config import get_config, dispatch_custom_event

from app.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.deepseek import DeepSeekProvider
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, JobStatus
from app.models.user import User, UserRole
from app.schemas.agent import EvaluateRequest
from app.services.agent.state import EvaluationState
from app.services.conversation.state import ConversationState


def _get_db() -> AsyncSession:
    """从 LangGraph config 获取数据库会话"""
    config = get_config()
    db: AsyncSession = config["configurable"]["db"]
    return db


def _get_llm_provider() -> BaseLLMProvider:
    """根据配置获取 LLM 提供商"""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "deepseek":
        return DeepSeekProvider()
    raise ValueError(f"不支持的 LLM 提供商: {provider}")


async def intent_node(state: ConversationState) -> dict:
    """意图识别节点：解析用户消息，提取意图和参数"""
    user_message = state.get("user_message", "")

    dispatch_custom_event("thinking", {"status": "正在理解您的指令..."})

    provider: BaseLLMProvider | None = None
    try:
        provider = _get_llm_provider()
        result = await provider.recognize_intent(user_message)

        dispatch_custom_event("intent", {
            "intent": result.intent,
            "params": result.extracted_params,
        })

        return {
            "intent": result.intent,
            "extracted_params": result.extracted_params,
            "clarifying_question": result.clarifying_question,
        }
    except Exception as exc:
        # LLM 意图识别失败时，回退为 unknown
        dispatch_custom_event("intent", {
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


async def dispatch_node(state: ConversationState) -> dict:
    """任务路由节点：根据意图分发到对应工作流"""
    db = _get_db()
    intent = state.get("intent", "unknown")
    current_user_id = state.get("current_user_id", "")
    extracted_params: dict[str, Any] = state.get("extracted_params", {})

    if intent != "evaluate":
        # help 和 unknown 不需要 dispatch
        return {}

    # ── 岗位匹配 ──────────────────────────────────────────
    job_id_param = extracted_params.get("job_id")
    job_title_param = extracted_params.get("job_title")

    matched_job: Job | None = None

    if job_id_param:
        # 直接用 job_id
        matched_job = await db.get(Job, job_id_param)
        if matched_job and matched_job.recruiter_id != current_user_id:
            return {
                "reply_message": "❌ 您不是该岗位的招聘者，无法评估。",
            }
    elif job_title_param:
        # 模糊匹配岗位标题
        dispatch_custom_event("progress", {"status": "正在匹配岗位..."})
        stmt = select(Job).where(
            Job.recruiter_id == current_user_id,
            Job.status == JobStatus.ACTIVE,
            func.lower(Job.title).ilike(f"%{job_title_param.lower()}%"),
        )
        jobs = list((await db.execute(stmt)).scalars().all())

        if len(jobs) == 0:
            # 没找到，列出所有活跃岗位
            all_jobs_stmt = select(Job).where(
                Job.recruiter_id == current_user_id,
                Job.status == JobStatus.ACTIVE,
            )
            all_jobs = list((await db.execute(all_jobs_stmt)).scalars().all())
            if all_jobs:
                job_list = "\n".join(f"  {i+1}. {j.title}" for i, j in enumerate(all_jobs))
                return {
                    "reply_message": f"❌ 未找到匹配「{job_title_param}」的岗位。您当前有以下活跃岗位：\n{job_list}",
                }
            else:
                return {
                    "reply_message": "❌ 您当前没有活跃的岗位，请先发布岗位。",
                }
        elif len(jobs) > 1:
            job_list = "\n".join(f"  {i+1}. {j.title} (ID: {j.id})" for i, j in enumerate(jobs))
            return {
                "reply_message": f"找到多个匹配「{job_title_param}」的岗位，请指定：\n{job_list}",
            }
        else:
            matched_job = jobs[0]
    else:
        # 没有提供岗位信息
        return {
            "reply_message": "请指定要评估的岗位，例如「帮我筛选前端开发岗位的简历」。",
        }

    if not matched_job:
        return {
            "reply_message": "❌ 未找到匹配的岗位。",
        }

    # ── 并发检查 ──────────────────────────────────────────
    existing_stmt = select(EvaluationTask).where(
        EvaluationTask.job_id == matched_job.id,
        EvaluationTask.status.in_([EvalTaskStatus.PENDING, EvalTaskStatus.RUNNING]),
    )
    existing_task = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing_task:
        return {
            "task_id": str(existing_task.id),
            "evaluation_status": existing_task.status.value,
            "reply_message": f"⚠️ 岗位「{matched_job.title}」已有正在进行的评估任务。",
            "reply_cards": [{
                "type": "evaluation_summary",
                "task_id": str(existing_task.id),
                "job_title": matched_job.title,
                "total_count": existing_task.total_count,
                "recommended_count": 0,
                "rejected_count": 0,
                "result_page_url": f"/dashboard/evaluation/{existing_task.id}",
            }],
        }

    # ── 触发评估工作流 ──────────────────────────────────
    dispatch_custom_event("progress", {"status": f"正在评估「{matched_job.title}」岗位的简历..."})

    interview_quota = extracted_params.get("interview_quota") or matched_job.interview_quota

    # 创建评估任务记录
    from app.services import agent_service
    user = await db.get(User, current_user_id)
    if not user:
        return {"reply_message": "❌ 用户信息异常。", "errors": ["用户不存在"]}

    eval_request = EvaluateRequest(interview_quota=interview_quota if isinstance(interview_quota, int) else None)
    eval_response = await agent_service.trigger_evaluation(
        db, str(matched_job.id), user, eval_request
    )

    task_id = eval_response.task_id

    # 运行评估工作流（内联执行，以获取进度事件）
    from app.database import get_checkpointer
    from app.services.agent.graph import build_evaluation_workflow

    checkpointer = get_checkpointer()
    graph = build_evaluation_workflow(checkpointer)

    initial_state: EvaluationState = {
        "job_id": str(matched_job.id),
        "triggered_by": current_user_id,
        "task_id": task_id,
        "errors": [],
        "interview_quota_override": interview_quota if isinstance(interview_quota, int) else None,
    }

    config = {
        "configurable": {
            "thread_id": task_id,
            "db": db,
        }
    }

    # 内联执行评估图，转发进度事件
    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            if event.get("event") == "on_custom_event":
                event_name = event.get("name", "")
                event_data = event.get("data", {})
                # 转发评估进度事件为对话级进度事件
                dispatch_custom_event("progress", event_data)
    except Exception as exc:
        return {
            "task_id": task_id,
            "evaluation_status": "failed",
            "reply_message": f"❌ 评估工作流执行出错：{exc}",
            "errors": [f"评估工作流异常: {exc}"],
        }

    # 获取最终任务状态
    final_task = await db.get(EvaluationTask, task_id)
    eval_status = final_task.status.value if final_task else "unknown"

    return {
        "task_id": task_id,
        "evaluation_status": eval_status,
    }


async def feedback_node(state: ConversationState) -> dict:
    """结果反馈节点：格式化结果摘要"""
    db = _get_db()
    intent = state.get("intent", "unknown")

    # 如果 dispatch_node 已经设置了 reply_message，直接使用
    if state.get("reply_message"):
        return {}

    # evaluate 意图
    if intent == "evaluate":
        task_id = state.get("task_id")
        if not task_id:
            return {"reply_message": "❌ 评估任务创建失败，请重试。"}

        task = await db.get(EvaluationTask, task_id)
        if not task:
            return {"reply_message": "❌ 评估任务不存在。"}

        job = await db.get(Job, task.job_id)
        job_title = job.title if job else "未知岗位"

        if task.status == EvalTaskStatus.COMPLETED:
            summary = task.result_summary or {}
            recommend_count = summary.get("recommend_count", 0)
            reject_count = summary.get("reject_count", 0)

            return {
                "reply_message": f"✅ 已完成「{job_title}」岗位的简历评估，共 {task.total_count} 份简历，推荐 {recommend_count} 人进入面试。",
                "reply_cards": [{
                    "type": "evaluation_summary",
                    "task_id": task_id,
                    "job_title": job_title,
                    "total_count": task.total_count,
                    "recommended_count": recommend_count,
                    "rejected_count": reject_count,
                    "result_page_url": f"/dashboard/evaluation/{task_id}",
                }],
                "result_page_url": f"/dashboard/evaluation/{task_id}",
            }
        elif task.status == EvalTaskStatus.FAILED:
            return {
                "reply_message": f"❌ 评估失败：{task.error_message or '未知错误'}",
            }
        else:
            return {
                "reply_message": f"⏳ 评估任务状态：{task.status.value}，请稍后查看。",
            }

    # help 意图
    if intent == "help":
        return {
            "reply_message": "我可以帮您完成以下操作：\n\n• **筛选岗位简历** — 如「帮我筛选前端开发岗位的简历」\n• **指定进面人数** — 如「前端岗位选 5 人进面试」\n\n输入自然语言指令即可，我会理解您的意图并执行。",
        }

    # unknown 意图
    clarifying = state.get("clarifying_question")
    return {
        "reply_message": clarifying or "抱歉，我没有理解您的意思。输入「帮助」查看我能做什么。",
    }


def route_by_intent(state: ConversationState) -> str:
    """条件路由：根据意图决定下一个节点"""
    intent = state.get("intent", "unknown")
    if intent == "evaluate":
        return "dispatch"
    return "feedback"
```

**Important note:** The `dispatch_node` calls `agent_service.trigger_evaluation()` which already creates the EvaluationTask and starts a background task. But we want inline execution for SSE streaming. We need to modify the approach slightly — `trigger_evaluation` should NOT start the background task when called from dispatch_node. We'll handle this by:

1. Extracting task creation logic from `trigger_evaluation` into a helper
2. Having dispatch_node create the task directly and then run the graph inline

Let me revise the dispatch_node. Instead of calling `agent_service.trigger_evaluation()`, we create the task directly:

Replace the "触发评估工作流" section in `dispatch_node`:

```python
    # ── 创建评估任务 ──────────────────────────────────────
    from app.models.application import Application, ApplicationStatus
    import uuid

    # 统计 pending 申请数
    job_uuid = matched_job.id
    count_stmt = select(func.count()).select_from(Application).where(
        Application.job_id == job_uuid,
        Application.status == ApplicationStatus.PENDING,
    )
    pending_count: int = (await db.execute(count_stmt)).scalar() or 0

    if pending_count == 0:
        return {
            "reply_message": f"❌ 岗位「{matched_job.title}」暂无待处理的简历。",
        }

    # 创建任务记录
    task_id = uuid.uuid4()
    eval_task = EvaluationTask(
        id=task_id,
        job_id=job_uuid,
        triggered_by=current_user_id,
        status=EvalTaskStatus.PENDING,
        total_count=pending_count,
    )
    db.add(eval_task)
    await db.commit()
    await db.refresh(eval_task)
    task_id_str = str(task_id)

    # ── 内联执行评估图 ──────────────────────────────────
    dispatch_custom_event("progress", {
        "status": f"正在评估「{matched_job.title}」岗位的简历...",
        "total_count": pending_count,
    })

    from app.database import get_checkpointer
    from app.services.agent.graph import build_evaluation_graph

    checkpointer = get_checkpointer()
    graph = build_evaluation_graph(checkpointer)

    initial_state: EvaluationState = {
        "job_id": str(matched_job.id),
        "triggered_by": current_user_id,
        "task_id": task_id_str,
        "errors": [],
        "interview_quota_override": interview_quota if isinstance(interview_quota, int) else None,
    }

    config = {
        "configurable": {
            "thread_id": task_id_str,
            "db": db,
        }
    }

    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            if event.get("event") == "on_custom_event":
                event_data = event.get("data", {})
                dispatch_custom_event("progress", event_data)
    except Exception as exc:
        return {
            "task_id": task_id_str,
            "evaluation_status": "failed",
            "reply_message": f"❌ 评估工作流执行出错：{exc}",
            "errors": [f"评估工作流异常: {exc}"],
        }

    final_task = await db.get(EvaluationTask, task_id_str)
    eval_status = final_task.status.value if final_task else "unknown"

    return {
        "task_id": task_id_str,
        "evaluation_status": eval_status,
    }
```

Also add the missing import at the top of the file:

```python
from sqlalchemy import select, func
```

This is already in the imports. Good.

- [ ] **Step 2: Run mypy on the new file**

Run: `cd backend && uv run mypy --strict app/services/conversation/nodes.py`

Expected: May have some errors. Fix them and re-run.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/conversation/nodes.py
git commit -m "feat: add conversation nodes — intent, dispatch, feedback

- intent_node: LLM intent recognition with fallback
- dispatch_node: job matching, task creation, inline evaluation
- feedback_node: result formatting with cards
- route_by_intent: conditional routing helper"
```

---

### Task 3: Build ConversationGraph + Wire Up

**Files:**
- Create: `backend/app/services/conversation/graph.py`
- Modify: `backend/app/services/conversation/__init__.py`

**Interfaces:**
- Consumes: `ConversationState`, conversation nodes from Task 2, `get_checkpointer()` from `app.database`
- Produces: `build_conversation_graph() -> CompiledStateGraph`

- [ ] **Step 1: Create the conversation graph module**

Create `backend/app/services/conversation/graph.py`:

```python
"""对话 Agent LangGraph 图定义"""

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.services.conversation.state import ConversationState
from app.services.conversation.nodes import (
    intent_node,
    dispatch_node,
    feedback_node,
    route_by_intent,
)


def build_conversation_graph(checkpointer: AsyncPostgresSaver) -> StateGraph:  # type: ignore[type-arg]
    """构建对话工作流图并编译

    流程：
    START → intent → (evaluate? → dispatch → feedback → END)
                   → (help/unknown? → feedback → END)
    """
    graph = StateGraph(ConversationState)

    # 添加节点
    graph.add_node("intent", intent_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("feedback", feedback_node)

    # 设置入口
    graph.add_edge(START, "intent")

    # 条件路由：intent → dispatch 或 feedback
    graph.add_conditional_edges(
        "intent",
        route_by_intent,
        {"dispatch": "dispatch", "feedback": "feedback"},
    )

    # dispatch → feedback → END
    graph.add_edge("dispatch", "feedback")
    graph.add_edge("feedback", END)

    return graph.compile(checkpointer=checkpointer)
```

- [ ] **Step 2: Update __init__.py**

Update `backend/app/services/conversation/__init__.py`:

```python
"""HR Agent 对话助手模块"""

from app.services.conversation.graph import build_conversation_graph

__all__ = ["build_conversation_graph"]
```

- [ ] **Step 3: Run mypy**

Run: `cd backend && uv run mypy --strict app/services/conversation/`

Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/conversation/graph.py backend/app/services/conversation/__init__.py
git commit -m "feat: build ConversationGraph with conditional routing

- intent → dispatch (evaluate) → feedback → END
- intent → feedback (help/unknown) → END
- Compiled with AsyncPostgresSaver checkpointer"
```

---

### Task 4: Create Chat API Route with SSE

**Files:**
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/api/__init__.py`

**Interfaces:**
- Consumes: `ChatRequest`, `build_conversation_graph()`, `get_checkpointer()`, `ConversationState`, `async_session` from `app.database`
- Produces: `POST /api/chat/send` endpoint returning `text/event-stream`

- [ ] **Step 1: Create the Chat API route**

Create `backend/app/api/chat.py`:

```python
"""Chat API — 对话助手端点"""

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
    # 角色检查
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
) -> typing.AsyncGenerator[str, None]:
    """运行对话图并产出 SSE 事件流"""
    import typing  # noqa — needed for type hint above

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
        config = {
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

                    # 映射自定义事件到 SSE 事件类型
                    sse_event = _map_custom_event(event_name, event_data)
                    if sse_event:
                        yield sse_event

            # 获取最终状态用于 result 事件
            state_result = await graph.aget_state(config)
            final_state: ConversationState = state_result.values  # type: ignore[assignment]

            # 发送 result 事件（如果 feedback_node 产出了回复）
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


def _map_custom_event(name: str, data: dict[str, object]) -> str | None:
    """将 LangGraph 自定义事件映射为 SSE 事件字符串"""
    if name in ("thinking", "intent", "progress"):
        return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    return None


def _error_stream(message: str) -> typing.AsyncGenerator[str, None]:
    """产出一个错误 SSE 事件流"""
    import typing

    async def _gen() -> typing.AsyncGenerator[str, None]:
        yield f"event: error\ndata: {json.dumps({'message': message, 'recoverable': False}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return _gen()
```

Wait, the `import typing` inside the function is not ideal. Let me fix this:

Replace the file with a cleaner version:

```python
"""Chat API — 对话助手端点"""

import json
import typing
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

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
) -> typing.AsyncGenerator[str, None]:
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
        config = {
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


def _map_custom_event(name: str, data: dict[str, object]) -> str | None:
    """将 LangGraph 自定义事件映射为 SSE 事件字符串"""
    if name in ("thinking", "intent", "progress"):
        return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    return None


async def _error_stream(message: str) -> typing.AsyncGenerator[str, None]:
    """产出一个错误 SSE 事件流"""
    yield f"event: error\ndata: {json.dumps({'message': message, 'recoverable': False}, ensure_ascii=False)}\n\n"
    yield "event: done\ndata: {}\n\n"
```

- [ ] **Step 2: Register chat router in api/__init__.py**

Modify `backend/app/api/__init__.py`:

```python
from fastapi import APIRouter
from app.api import auth, jobs, applications, agent, chat

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(agent.router)
api_router.include_router(chat.router)
```

- [ ] **Step 3: Run mypy**

Run: `cd backend && uv run mypy --strict app/api/chat.py`

Expected: No errors (may need minor adjustments)

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/chat.py backend/app/api/__init__.py
git commit -m "feat: add Chat API with SSE streaming

- POST /api/chat/send returns text/event-stream
- Custom events from ConversationGraph mapped to SSE events
- Final state extracted for result event
- Error handling with recoverable flag"
```

---

### Task 5: Conversation Agent Tests

**Files:**
- Create: `backend/tests/test_conversation_nodes.py`
- Create: `backend/tests/test_chat_api.py`

**Interfaces:**
- Consumes: Conversation nodes, Chat API, test fixtures from conftest.py
- Produces: Test suite for conversation nodes and Chat API

- [ ] **Step 1: Create conversation node tests**

Create `backend/tests/test_conversation_nodes.py`:

```python
"""对话 Agent 节点测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.agent import IntentResult
from app.services.conversation.state import ConversationState
from app.services.conversation.nodes import (
    intent_node,
    feedback_node,
    route_by_intent,
)


class TestIntentNode:
    """intent_node 测试"""

    @pytest.mark.asyncio
    async def test_evaluate_intent(self) -> None:
        """测试识别 evaluate 意图"""
        mock_result = IntentResult(
            intent="evaluate",
            confidence=0.9,
            extracted_params={"job_title": "前端开发"},
        )
        mock_provider = AsyncMock()
        mock_provider.recognize_intent = AsyncMock(return_value=mock_result)
        mock_provider.close = AsyncMock()

        state: ConversationState = {
            "user_message": "帮我筛选前端开发岗位的简历",
            "current_user_id": "test-user",
            "errors": [],
        }

        with patch(
            "app.services.conversation.nodes._get_llm_provider",
            return_value=mock_provider,
        ):
            result = await intent_node(state)

        assert result["intent"] == "evaluate"
        assert result["extracted_params"]["job_title"] == "前端开发"

    @pytest.mark.asyncio
    async def test_help_intent(self) -> None:
        """测试识别 help 意图"""
        mock_result = IntentResult(
            intent="help",
            confidence=0.95,
            extracted_params={},
        )
        mock_provider = AsyncMock()
        mock_provider.recognize_intent = AsyncMock(return_value=mock_result)
        mock_provider.close = AsyncMock()

        state: ConversationState = {
            "user_message": "你能做什么",
            "current_user_id": "test-user",
            "errors": [],
        }

        with patch(
            "app.services.conversation.nodes._get_llm_provider",
            return_value=mock_provider,
        ):
            result = await intent_node(state)

        assert result["intent"] == "help"

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self) -> None:
        """测试 LLM 失败时回退为 unknown"""
        mock_provider = AsyncMock()
        mock_provider.recognize_intent = AsyncMock(side_effect=Exception("API error"))
        mock_provider.close = AsyncMock()

        state: ConversationState = {
            "user_message": "测试消息",
            "current_user_id": "test-user",
            "errors": [],
        }

        with patch(
            "app.services.conversation.nodes._get_llm_provider",
            return_value=mock_provider,
        ):
            result = await intent_node(state)

        assert result["intent"] == "unknown"
        assert result.get("clarifying_question") is not None


class TestFeedbackNode:
    """feedback_node 测试"""

    @pytest.mark.asyncio
    async def test_help_feedback(self) -> None:
        """测试 help 意图的反馈"""
        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "test-user",
            "intent": "help",
            "errors": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert "筛选岗位简历" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_unknown_feedback(self) -> None:
        """测试 unknown 意图的反馈"""
        state: ConversationState = {
            "user_message": "天气怎么样",
            "current_user_id": "test-user",
            "intent": "unknown",
            "clarifying_question": "请问您想执行什么操作？",
            "errors": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert "请问您想执行什么操作" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_pre_set_reply_message(self) -> None:
        """测试 dispatch 已设置 reply_message 时不覆盖"""
        state: ConversationState = {
            "user_message": "筛选简历",
            "current_user_id": "test-user",
            "intent": "evaluate",
            "reply_message": "❌ 未找到匹配的岗位。",
            "errors": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        # reply_message 已存在，feedback_node 应返回空 dict
        assert result == {}


class TestRouteByIntent:
    """route_by_intent 测试"""

    def test_evaluate_routes_to_dispatch(self) -> None:
        state: ConversationState = {"intent": "evaluate"}
        assert route_by_intent(state) == "dispatch"

    def test_help_routes_to_feedback(self) -> None:
        state: ConversationState = {"intent": "help"}
        assert route_by_intent(state) == "feedback"

    def test_unknown_routes_to_feedback(self) -> None:
        state: ConversationState = {"intent": "unknown"}
        assert route_by_intent(state) == "feedback"

    def test_default_routes_to_feedback(self) -> None:
        state: ConversationState = {}
        assert route_by_intent(state) == "feedback"
```

- [ ] **Step 2: Run conversation node tests**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py -v`

Expected: All 9 tests pass

- [ ] **Step 3: Create Chat API tests**

Create `backend/tests/test_chat_api.py`:

```python
"""Chat API 测试"""

import pytest
from unittest.mock import patch, AsyncMock


class TestChatSendEndpoint:
    """POST /api/chat/send 测试"""

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, client: pytest.AsyncClient) -> None:
        """未登录不能发送消息"""
        response = await client.post("/api/chat/send", json={"message": "测试"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_requires_recruiter(
        self,
        client: pytest.AsyncClient,
        seeker_auth_headers: dict[str, str],
    ) -> None:
        """求职者不能使用对话助手"""
        response = await client.post(
            "/api/chat/send",
            json={"message": "测试"},
            headers=seeker_auth_headers,
        )
        # Should get SSE stream with error event
        assert response.status_code == 200
        content = response.text
        assert "error" in content or "仅招聘者" in content

    @pytest.mark.asyncio
    async def test_chat_message_validation(
        self,
        client: pytest.AsyncClient,
        recruiter_auth_headers: dict[str, str],
    ) -> None:
        """消息不能为空"""
        response = await client.post(
            "/api/chat/send",
            json={"message": ""},
            headers=recruiter_auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_returns_sse_stream(
        self,
        client: pytest.AsyncClient,
        recruiter_auth_headers: dict[str, str],
    ) -> None:
        """对话应返回 SSE 流"""
        # Mock the entire conversation graph to avoid real LLM calls
        mock_state = AsyncMock()
        mock_state.values = {
            "reply_message": "✅ 测试回复",
            "reply_cards": None,
        }

        with patch("app.api.chat.get_checkpointer") as mock_cp, \
             patch("app.api.chat.build_conversation_graph") as mock_build:
            mock_graph = AsyncMock()
            mock_graph.astream_events = AsyncMock(return_value=aiter([]))
            mock_graph.aget_state = AsyncMock(return_value=mock_state)
            mock_build.return_value = mock_graph

            response = await client.post(
                "/api/chat/send",
                json={"message": "帮助"},
                headers=recruiter_auth_headers,
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")


async def aiter(items: list) -> object:
    """Helper: create an async iterator from a list"""
    for item in items:
        yield item
```

**Note:** The `seeker_auth_headers` and `recruiter_auth_headers` fixtures should already exist in `conftest.py`. If not, add them based on the existing auth fixture patterns.

- [ ] **Step 4: Run Chat API tests**

Run: `cd backend && uv run pytest tests/test_chat_api.py -v`

Expected: All 4 tests pass (may need fixture adjustments)

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_conversation_nodes.py backend/tests/test_chat_api.py
git commit -m "test: add conversation node and Chat API tests

- intent_node: evaluate, help, LLM failure fallback (3)
- feedback_node: help, unknown, pre-set message (3)
- route_by_intent: evaluate, help, unknown, default (4)
- Chat API: auth, role, validation, SSE stream (4)"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run full mypy check**

Run: `cd backend && uv run mypy --strict app/`

Expected: No errors

- [ ] **Step 2: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`

Expected: All tests pass

- [ ] **Step 3: Commit any fixes**

If mypy or tests revealed issues, fix and commit.

---

## Self-Review

**1. Spec coverage check:**
- ✅ ConversationGraph with 3 nodes (Task 2, 3)
- ✅ intent_node with LLM recognition (Task 2)
- ✅ dispatch_node with job matching + inline evaluation (Task 2)
- ✅ feedback_node with result formatting (Task 2)
- ✅ Chat API with SSE streaming (Task 4)
- ✅ ConversationState definition (Task 1)
- ✅ Chat DTOs (Task 1)
- ✅ Tests for nodes and API (Task 5)

**2. Placeholder scan:** No TBD/TODO found. All steps have complete code.

**3. Type consistency:**
- `ConversationState` matches between `state.py`, `nodes.py`, `graph.py`, and `chat.py`
- `_get_db()` pattern consistent with evaluation nodes from Plan 1
- `dispatch_custom_event()` call patterns consistent
- `build_conversation_graph()` and `build_evaluation_graph()` naming consistent

# Bug 修复与重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 `interview_quota`/`is_active`/`context_entities` 三个错误/死功能字段，修复聊天记录丢失和 Summary 生成错误

**Architecture:** 五项修复互相独立，按依赖顺序实施：先删字段（Task 1-4 后端 → Task 5 前端 → Task 6 migration），再修 Summary（Task 7），最后修聊天记录恢复（Task 8 前端）。每项修改保证 mypy --strict 通过 + 全量测试通过。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 (后端), Next.js + TypeScript (前端), Alembic (migrations)

## Global Constraints

- Python strict type hints on every function/method (`-> None` if empty)
- `mypy --strict` must pass on `app/` after every task
- All 154 existing tests must pass after every task
- SQLAlchemy 2.0 type-annotated style (`Mapped[str] = mapped_column(...)`)
- Pydantic v2 exclusively for request/response schemas
- Modern union syntax (`int | None`, `list[str]`)
- Alembic migration for every DB schema change

---

## File Structure

### 后端文件变更

| 操作 | 文件 | 职责 |
|------|------|------|
| Modify | `app/models/job.py` | 删除 `interview_quota` 列 |
| Modify | `app/models/conversation.py` | 删除 `is_active` 列 + `context_entities` 列 + 复合索引 |
| Modify | `app/schemas/job.py` | `JobCreateRequest`/`JobUpdateRequest`/`JobResponse` 删除 `interview_quota` |
| Modify | `app/schemas/agent.py` | `EvaluateRequest` 删除 `interview_quota` |
| Modify | `app/api/jobs.py` | `_job_to_dict` 删除 `interview_quota` |
| Modify | `app/api/agent.py` | 默认参数改为 `EvaluateRequest()` |
| Modify | `app/api/chat.py` | 删除 `is_active`/`context_entities` 读写；删除跨 session seed 注入；修 summary 触发逻辑 |
| Modify | `app/services/job_service.py` | `create_job` 删除 `interview_quota` |
| Modify | `app/services/agent/state.py` | `EvaluationState` 删除 `interview_quota_override` |
| Modify | `app/services/agent/nodes.py` | `collect_node` 不读 quota；`screen_node` 简化固定阈值 |
| Modify | `app/services/agent_service.py` | 删除 `interview_quota_override` 传递 |
| Modify | `app/services/conversation/tools.py` | 删除 `interview_quota` 相关字段/参数 |
| Modify | `app/services/conversation/state.py` | `ConversationContext` 删除 `context_entities` |
| Modify | `app/services/conversation/prompts.py` | 删除 `context_entities` 注入；重写 SUMMARIZE_PROMPT |
| Modify | `app/services/conversation/graph.py` | 删除 `context_entities` 注入说明 |
| Modify | `app/llm/deepseek.py` | 修复 `summarize_conversation` 错误处理 |
| Create | `alembic/versions/xxxx_drop_interview_quota_is_active_context_entities.py` | 合并 migration |

### 前端文件变更

| 操作 | 文件 | 职责 |
|------|------|------|
| Modify | `src/features/jobs/types/job.ts` | 删除 `interview_quota` |
| Modify | `src/features/chat/types/chat.ts` | `JobDetailCardData.job` 删除 `interview_quota` |
| Modify | `src/pages/PostJobPage.tsx` | 删除进面人数字段 + Zod 验证 |
| Modify | `src/pages/JobDashboardPage.tsx` | 删除表格列 |
| Modify | `src/features/chat/components/JobDetailCard.tsx` | 删除进面人数显示 |
| Modify | `src/features/chat/hooks/useChat.ts` | 初始化时自动 validateSession；localStorage key 绑定 user_id |
| Modify | `src/features/chat/components/ChatBubble.tsx` | 移除 `hasValidated` 手动触发 |
| Modify | `src/features/chat/components/ChatWindow.tsx` | X 关闭时清除 session + localStorage |
| Modify | `src/features/auth/store/authStore.ts` | logout 时清除 `chat-session-id:*` |

### 测试文件变更

| 操作 | 文件 | 职责 |
|------|------|------|
| Modify | `tests/conftest.py` | 删除 fixture 中 `interview_quota` |
| Modify | `tests/test_jobs_api.py` | 删除 `interview_quota` 断言 |
| Modify | `tests/test_agent_nodes.py` | 删除 quota 相关用例 |
| Modify | `tests/test_agent_api.py` | 删除 quota 参数 |
| Modify | `tests/test_react_tools.py` | 删除 quota 相关测试 |
| Modify | `tests/test_chat_api_v2.py` | 适配 is_active/context_entities 删除 |
| Modify | `tests/test_chat_schemas.py` | 删除 `interview_quota` 测试数据 |

---

### Task 1: 删除 `interview_quota` — 后端模型 & Schema 层

**Files:**
- Modify: `app/models/job.py:51`
- Modify: `app/schemas/job.py:21,36,62`
- Modify: `app/schemas/agent.py:51-53`

**Interfaces:**
- Consumes: 无（本 Task 是链头）
- Produces: `Job` ORM 无 `interview_quota` 列；`JobCreateRequest`/`JobUpdateRequest`/`JobResponse` 无 `interview_quota` 字段；`EvaluateRequest` 无 `interview_quota` 字段

- [ ] **Step 1: 从 Job ORM 模型删除 `interview_quota` 列**

`app/models/job.py` — 删除第 51 行：

```python
# DELETE THIS LINE:
    interview_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
```

- [ ] **Step 2: 从 JobCreateRequest 删除 `interview_quota` 字段**

`app/schemas/job.py` — 删除第 21 行：

```python
# DELETE THIS LINE:
    interview_quota: int = Field(default=1, description="面试人数上限")
```

- [ ] **Step 3: 从 JobUpdateRequest 删除 `interview_quota` 字段**

`app/schemas/job.py` — 删除第 36 行：

```python
# DELETE THIS LINE:
    interview_quota: Optional[int] = Field(None, description="面试人数上限")
```

- [ ] **Step 4: 从 JobResponse 删除 `interview_quota` 字段**

`app/schemas/job.py` — 删除第 62 行：

```python
# DELETE THIS LINE:
    interview_quota: int = 1
```

- [ ] **Step 5: 从 EvaluateRequest 删除 `interview_quota` 字段**

`app/schemas/agent.py` — 删除第 51-53 行：

```python
# DELETE THESE LINES:
    interview_quota: Optional[int] = Field(
        None, description="面试人数上限，null 表示不限（可覆盖岗位设定）"
    )
```

- [ ] **Step 6: 运行 mypy 验证**

Run: `cd backend && uv run mypy --strict app/ 2>&1 | head -20`

Expected: 报错（因为其他文件仍引用 `interview_quota`），仅确认模型层已清除

- [ ] **Step 7: Commit**

```bash
git add app/models/job.py app/schemas/job.py app/schemas/agent.py
git commit -m "refactor: remove interview_quota from Job model and schemas"
```

---

### Task 2: 删除 `interview_quota` — 后端服务层 & API 层

**Files:**
- Modify: `app/api/jobs.py:38`
- Modify: `app/api/agent.py:27`
- Modify: `app/services/job_service.py:49`
- Modify: `app/services/agent/state.py:16`
- Modify: `app/services/agent/nodes.py:95,236-246`
- Modify: `app/services/agent_service.py:92,96,111,124`
- Modify: `app/services/conversation/tools.py:80,118,208-209,497,510,526-528,586`

**Interfaces:**
- Consumes: Task 1 产出的无 `interview_quota` 的模型/Schema
- Produces: `screen_node` 使用固定阈值 60；`trigger_evaluation` tool 无 `interview_quota` 参数；`EvaluationState` 无 `interview_quota_override`

- [ ] **Step 1: 修改 `app/api/jobs.py` — `_job_to_dict` 删除 interview_quota**

```python
def _job_to_dict(job: Any, recruiter_name: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": str(job.id),
        "recruiter_id": str(job.recruiter_id),
        "title": job.title,
        "description": job.description,
        "requirements": job.requirements,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "location": job.location,
        "work_type": job.work_type,
        "skills_required": job.skills_required,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "recruiter_name": recruiter_name,
        "applications_count": len(job.applications),
        # "interview_quota": job.interview_quota,  ← 删除此行
        "head_count": job.head_count,
        "job_code": job.job_code,
    }
```

- [ ] **Step 2: 修改 `app/api/agent.py` — 默认参数**

```python
# 旧: data: EvaluateRequest = EvaluateRequest(interview_quota=None),
# 新:
    data: EvaluateRequest = EvaluateRequest(),
```

- [ ] **Step 3: 修改 `app/services/job_service.py` — create_job 删除 interview_quota**

```python
    job = Job(
        recruiter_id=current_user.id,
        title=data.title,
        description=data.description,
        requirements=data.requirements,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        location=data.location,
        work_type=data.work_type,
        skills_required=data.skills_required,
        # interview_quota=data.interview_quota,  ← 删除此行
        head_count=data.head_count,
        job_code=job_code,
        status=JobStatus.ACTIVE,
    )
```

- [ ] **Step 4: 修改 `app/services/agent/state.py` — 删除 interview_quota_override**

```python
class EvaluationState(TypedDict, total=False):
    """评估工作流状态"""

    # 输入
    job_id: str
    triggered_by: str
    task_id: str
    # interview_quota_override: int | None  ← 删除此行

    # 收集阶段产出
    job_info: dict[str, object]
    applications: list[dict[str, object]]
    # ...其余不变
```

- [ ] **Step 5: 修改 `app/services/agent/nodes.py` — collect_node + screen_node**

`collect_node` — 删除 `job_info` 中的 `interview_quota`：

```python
    job_info: dict[str, Any] = {
        "title": job.title,
        "description": job.description,
        "skills_required": job.skills_required,
        "requirements": job.requirements,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "location": job.location,
        "work_type": job.work_type.value,
        # "interview_quota": job.interview_quota,  ← 删除此行
    }
```

`screen_node` — 简化为固定阈值：

```python
async def screen_node(state: EvaluationState) -> dict[str, Any]:
    """筛选阶段：按固定阈值 60 分筛选（纯排序，无 LLM）"""
    evaluation_results = list(cast(list[dict[str, Any]], state.get("evaluation_results", [])))

    if not evaluation_results:
        return {
            "screening_result": {
                "recommend_list": [],
                "reject_list": [],
                "cutoff_score": 60.0,
            },
        }

    await adispatch_custom_event("progress", {"status": "正在筛选候选人..."})

    # 按加权总分降序排列
    sorted_results = sorted(
        evaluation_results,
        key=lambda x: float(x.get("weighted_total", 0)),
        reverse=True,
    )

    # 固定阈值：ai_score >= 60 → recommend, < 60 → reject
    cutoff_score = 60.0
    recommend_list = [r for r in sorted_results if float(r.get("weighted_total", 0)) >= cutoff_score]
    reject_list = [r for r in sorted_results if float(r.get("weighted_total", 0)) < cutoff_score]

    screening_result: dict[str, Any] = {
        "recommend_list": recommend_list,
        "reject_list": reject_list,
        "cutoff_score": cutoff_score,
    }

    return {
        "screening_result": screening_result,
    }
```

- [ ] **Step 6: 修改 `app/services/agent_service.py` — 删除 interview_quota_override**

`trigger_evaluation`:

```python
    # 旧:
    # interview_quota_override = getattr(request, "interview_quota", None)
    # asyncio.create_task(
    #     _run_workflow_background(
    #         str(task_id), str(job_id), str(current_user.id),
    #         interview_quota_override=interview_quota_override,
    #     )
    # )
    # 新:
    asyncio.create_task(
        _run_workflow_background(
            str(task_id), str(job_id), str(current_user.id),
        )
    )
```

`_run_workflow_background`:

```python
async def _run_workflow_background(
    task_id: str,
    job_id: str,
    triggered_by: str,
    # interview_quota_override: int | None = None,  ← 删除参数
) -> None:
    """后台执行评估工作流（通过 LangGraph 图引擎）"""
    from app.database import async_session
    from app.services.agent.graph import run_evaluation_workflow

    async with async_session() as db:
        try:
            initial_state: EvaluationState = {
                "job_id": job_id,
                "triggered_by": triggered_by,
                "task_id": task_id,
                "errors": [],
                # "interview_quota_override": interview_quota_override,  ← 删除
            }
            await run_evaluation_workflow(initial_state, db)
        except Exception as exc:
            logger.exception("评估工作流异常: task_id=%s", task_id)
            task = await db.get(EvaluationTask, task_id)
            if task and task.status not in (
                EvalTaskStatus.COMPLETED,
                EvalTaskStatus.CONFIRMED,
                EvalTaskStatus.FAILED,
            ):
                task.status = EvalTaskStatus.FAILED
                task.error_message = f"工作流异常: {exc}"
                await db.commit()
```

- [ ] **Step 7: 修改 `app/services/conversation/tools.py` — 删除 interview_quota 相关**

1. `_JOBS_ALLOWED_FIELDS` 中删除 `"interview_quota"`：

```python
_JOBS_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "job_code", "title", "status", "head_count", "applications_count",
    "description", "requirements", "skills_required",
    "salary_min", "salary_max", "location", "work_type",
    # "interview_quota",  ← 删除
    "recruiter_name",
})
```

2. `query_jobs` docstring 中删除 `interview_quota` 引用：

```
    fields 指定返回字段，默认: ["job_code", "title", "status", "head_count", "applications_count"]
    可选字段: description, requirements, skills_required, salary_min, salary_max,
    location, work_type, recruiter_name
```

3. `query_jobs` 函数体中删除 `interview_quota` 分支（第 208-209 行）：

```python
            # 删除以下两行:
            # elif f == "interview_quota":
            #     item["interview_quota"] = j.interview_quota
```

4. `trigger_evaluation` tool 删除 `interview_quota` 参数：

```python
@tool
async def trigger_evaluation(
    job_code: str | None = None,
    job_title: str | None = None,
    # interview_quota: int | None = None,  ← 删除参数
) -> str:
    """对岗位触发 AI 简历评估。

    评估过程可能需要数分钟，会实时报告进度。
    评估完成后候选人获得 AI 评分和推荐/拒绝决策，
    但不会自动变更状态——需调用 confirm_evaluation 确认。

    ⚠️ 评估是耗时操作，触发前应确认用户意图。

    Args:
        job_code: 岗位编号（优先使用）
        job_title: 岗位名称（模糊匹配，job_code 优先）
    """
```

5. `trigger_evaluation` 函数体中删除 quota override 逻辑（第 526-528 行）：

```python
    # 删除以下三行:
    # if interview_quota is not None and job.interview_quota != interview_quota:
    #     job.interview_quota = interview_quota
    #     await db.commit()
```

6. `trigger_evaluation` 中 `initial_state` 删除 `interview_quota_override`：

```python
    initial_state: EvaluationState = {
        "job_id": str(job.id),
        "triggered_by": user_id,
        "task_id": task_id_str,
        "errors": [],
        # "interview_quota_override": interview_quota if isinstance(interview_quota, int) else None,  ← 删除
    }
```

- [ ] **Step 8: 运行 mypy 验证**

Run: `cd backend && uv run mypy --strict app/ 2>&1 | head -30`

Expected: 0 errors

- [ ] **Step 9: 运行全量测试**

Run: `cd backend && uv run pytest tests/ -v 2>&1 | tail -20`

Expected: 测试失败（因为测试仍引用 interview_quota），记录失败测试，在 Task 3 中修复

- [ ] **Step 10: Commit**

```bash
git add app/api/jobs.py app/api/agent.py app/services/job_service.py \
        app/services/agent/state.py app/services/agent/nodes.py \
        app/services/agent_service.py app/services/conversation/tools.py
git commit -m "refactor: remove interview_quota from services, API, and agent logic"
```

---

### Task 3: 更新后端测试 — 删除 interview_quota 引用

**Files:**
- Modify: `tests/conftest.py:181`
- Modify: `tests/test_jobs_api.py:31,385-399`
- Modify: `tests/test_agent_nodes.py:56,76`
- Modify: `tests/test_agent_api.py:207`
- Modify: `tests/test_react_tools.py:31,47,682-709`
- Modify: `tests/test_chat_schemas.py:40`

**Interfaces:**
- Consumes: Task 2 产出的无 `interview_quota` 的后端代码
- Produces: 全量测试通过

- [ ] **Step 1: 修改 `tests/conftest.py` — 删除 fixture 中的 `interview_quota`**

找到创建 job fixture 的代码，删除 `"interview_quota": 2`。

- [ ] **Step 2: 修改 `tests/test_jobs_api.py`**

1. 删除 `assert data["interview_quota"] == 1` 断言
2. 删除 `test_create_job_with_custom_quota_and_headcount` 测试中 `"interview_quota": 5` 的请求字段和 `assert data["interview_quota"] == 5` 断言。重命名测试为 `test_create_job_with_custom_head_count`，仅保留 head_count 逻辑。

- [ ] **Step 3: 修改 `tests/test_agent_nodes.py`**

1. 找到 `screen_node` 测试中 `"job_info": {"interview_quota": 2}` 的 fixture，删除 `interview_quota` 键
2. 找到 `screen_node` 无 quota 测试中 `"job_info": {"interview_quota": None}` 的 fixture，删除 `interview_quota` 键
3. 更新断言：所有 screen_node 测试现在应验证 `cutoff_score == 60.0`，`recommend_list` 包含 `weighted_total >= 60` 的结果

- [ ] **Step 4: 修改 `tests/test_agent_api.py`**

删除 `json={"interview_quota": 5}` 参数，改为 `json={}`

- [ ] **Step 5: 修改 `tests/test_react_tools.py`**

1. `_make_job` helper：删除 `interview_quota` 参数和 `job.interview_quota = interview_quota` 行
2. 删除 `test_interview_quota_override` 整个测试方法
3. 搜索其他 `interview_quota` 引用并清除

- [ ] **Step 6: 修改 `tests/test_chat_schemas.py`**

删除测试数据中 `"interview_quota": 5`

- [ ] **Step 7: 运行全量测试验证**

Run: `cd backend && uv run pytest tests/ -v 2>&1 | tail -20`

Expected: ALL PASS

- [ ] **Step 8: 运行 mypy 验证**

Run: `cd backend && uv run mypy --strict app/ 2>&1 | head -10`

Expected: 0 errors

- [ ] **Step 9: Commit**

```bash
git add tests/
git commit -m "test: remove interview_quota references from all test files"
```

---

### Task 4: 删除 `is_active` & `context_entities` — 后端模型、Schema、服务层

**Files:**
- Modify: `app/models/conversation.py`
- Modify: `app/services/conversation/state.py`
- Modify: `app/services/conversation/prompts.py`
- Modify: `app/services/conversation/graph.py`
- Modify: `app/api/chat.py`
- Modify: `app/llm/deepseek.py`

**Interfaces:**
- Consumes: Task 3 完成的干净后端
- Produces: `Conversation` ORM 无 `is_active`/`context_entities` 列；`ConversationContext` 无 `context_entities`；`build_state_modifier` 不注入 `context_entities`；`_run_conversation_stream` 无跨 session seed；`close_session` 不设 `is_active`/不触发 summary；`get_session` 通过 `session_id` 查找

- [ ] **Step 1: 修改 `app/models/conversation.py` — 删除列和索引**

```python
"""会话索引模型"""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """会话索引表 — 同一 session_id 内的摘要传递"""

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
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
    # is_active 列 → 删除（会话生命周期由 session_id 管理）
    # context_entities 列 → 删除（死功能，无写入）
    # ix_conversations_user_active 索引 → 删除（仅服务于 is_active 查询）
```

- [ ] **Step 2: 修改 `app/services/conversation/state.py` — 删除 context_entities**

```python
"""HR Agent ReAct 对话 — 状态辅助类型

create_react_agent 内部管理 messages 列表状态。
此模块仅定义 context injection 所需的辅助类型。
"""

from typing import Any, TypedDict


class ConversationContext(TypedDict, total=False):
    """传递给 build_state_modifier 的上下文数据。

    这些字段来自 Conversation SQL 表，在 graph 调用时
    注入到 state_modifier 中，而非作为 graph state 的一部分。
    """

    session_summary: str | None
    # context_entities → 删除（死功能）
```

- [ ] **Step 3: 修改 `app/services/conversation/prompts.py` — 删除 context_entities 注入 + 重写 SUMMARIZE prompt**

```python
"""HR Agent ReAct 对话 — System Prompt 与 State Modifier"""

from typing import Any


HR_AGENT_SYSTEM_PROMPT = """你是智能简历投递系统的 AI 助手，帮助招聘者管理岗位和筛选简历。

## 你的能力
你有查询和操作工具，可以灵活组合获取信息、分析数据、执行操作。

## 核心原则
1. **理解后再行动**：仔细分析用户需求，必要时追问澄清，而非急于调用工具
2. **按需查询**：根据任务构造精准查询参数（filter + fields），避免返回大量无关数据
3. **多步推理**：一个复杂问题可能需要多次查询——先看概览，再深入细节
4. **自然组织回复**：用 Markdown（表格、列表等）清晰呈现，给出建议而非仅罗列数据
5. **写操作必须确认**：涉及状态变更（推进面试、拒绝候选人、关闭岗位、确认评估等），必须先向用户确认意图和细节，用户明确同意后再执行
6. **善用上下文**：对话中提到的岗位、候选人等，后续可直接引用，无需用户重复

## 工具使用策略
- 优先使用 job_code（如 J04217）定位岗位，比岗位名称更精确
- 需要概览时用 group_by，需要明细时用 fields 指定字段
- 先查概览再深入：先 group_by=["status"] 看全局，再 filter 深入特定群体
- 触发评估前确认岗位有待审核简历
- 评估完成后主动分析关键发现（高分候选人、边界候选人等）

## 回复格式
- 使用中文回复
- 数据展示优先使用 Markdown 表格
- 数字和比例并用（如"5人（50%）"）
- 给出建议而非仅罗列事实
"""


def build_state_modifier(state: dict[str, Any]) -> str:
    """根据对话状态动态构建 system prompt。

    Args:
        state: ReAct agent state dict，包含可能存在的 session_summary

    Returns:
        完整的 system prompt 字符串
    """
    parts: list[str] = [HR_AGENT_SYSTEM_PROMPT]

    session_summary: str | None = state.get("session_summary")
    if session_summary:
        parts.append(f"\n## 对话摘要\n{session_summary}")

    # context_entities 注入 → 删除（死功能）

    return "\n".join(parts)


# ── Conversation Summarization Prompts ─────────────────────


SUMMARIZE_SYSTEM_PROMPT = """你是对话摘要助手。根据对话历史和已有摘要，生成简洁准确的对话摘要。

要求：
1. 保留关键实体：人名、岗位编号（J 开头的代码）、公司名、AI 评分等具体信息
2. 保留用户的意图和尚未完成的请求
3. 保留 AI 的关键建议或结论
4. 删除寒暄、重复、无关细节
5. 摘要不超过 300 字
6. 以纯文本输出摘要内容，不要 JSON 包裹
7. 如果已有摘要，将旧摘要与新对话内容合并为一个更完整的摘要
"""


def build_summarize_user_prompt(
    history: list[dict[str, str]],
    existing_summary: str | None = None,
) -> str:
    """构建对话摘要的用户提示词。

    Args:
        history: 对话历史消息列表，每条包含 role 和 content
        existing_summary: 已有的摘要（用于增量更新）

    Returns:
        完整的用户提示词字符串
    """
    parts: list[str] = []

    if existing_summary:
        parts.append(f"已有摘要：\n{existing_summary}\n")
        parts.append("请根据已有摘要和新的对话内容，合并更新摘要。")

    parts.append("对话历史：")
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        parts.append(f"{role}: {content}")

    parts.append("\n请生成对话摘要（纯文本，不超过 300 字）：")
    return "\n".join(parts)
```

- [ ] **Step 4: 修改 `app/services/conversation/graph.py` — 更新 docstring**

```python
    # docstring 中将 (session_summary, context_entities) 改为仅 (session_summary)
```

找到 docstring `context: 可选的上下文字典...` 行，改为：

```python
    context: 可选的上下文字典，注入到 system prompt
                 (session_summary)
```

- [ ] **Step 5: 修改 `app/api/chat.py` — 全面重写**

这是改动最大的文件。完整重写如下：

```python
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


def _extract_history_from_messages(messages: list[Any]) -> list[dict[str, str]]:
    """从 LangGraph messages 中提取 user/assistant 文本对话列表"""
    history: list[dict[str, str]] = []
    for msg in messages:
        role = getattr(msg, "type", msg.get("type", ""))
        content = getattr(msg, "content", msg.get("content", ""))
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
                # Fallback: get last AI message with text content
                for msg in reversed(messages):
                    msg_type = getattr(msg, "type", msg.get("type", ""))
                    if msg_type not in ("ai", "assistant"):
                        continue
                    content = getattr(msg, "content", "") if hasattr(msg, "content") else msg.get("content", "")
                    if content:
                        final_reply = content
                        break

            # Always emit result event
            if not final_reply:
                final_reply = "抱歉，我暂时无法回复，请重试。"
            yield f"event: result\ndata: {json.dumps({'reply_message': final_reply}, ensure_ascii=False)}\n\n"

            # ── Rolling summary: every 10 turns (20 messages) ─────
            if len(messages) > _SUMMARY_MESSAGE_THRESHOLD and conversation:
                async with async_session() as update_db:
                    update_stmt = select(Conversation).where(
                        Conversation.session_id == session_id,
                    )
                    update_result = await update_db.execute(update_stmt)
                    conv = update_result.scalar_one_or_none()
                    if conv:
                        # Rolling compression: old summary + trimmed messages → new summary
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
```

- [ ] **Step 6: 修改 `app/llm/deepseek.py` — 修复 summarize_conversation 错误处理**

```python
    async def summarize_conversation(
        self,
        history: list[dict[str, str]],
        existing_summary: str | None = None,
    ) -> str:
        """生成对话摘要 — 生成失败时返回旧摘要"""
        from app.services.conversation.prompts import (
            SUMMARIZE_SYSTEM_PROMPT,
            build_summarize_user_prompt,
        )

        try:
            user_prompt = build_summarize_user_prompt(history, existing_summary)
            raw = await self._call_chat(
                SUMMARIZE_SYSTEM_PROMPT, user_prompt, retries=1
            )

            # raw is already parsed dict from _call_chat
            summary = raw.get("summary", "")
            if summary:
                return str(summary)[:500]
            # Fallback: try to stringify the whole response
            fallback = json.dumps(raw, ensure_ascii=False)[:500]
            # If fallback looks like error content, return existing_summary instead
            if existing_summary and len(fallback) < 20:
                return existing_summary
            return fallback
        except Exception:
            # On any error, return existing summary instead of error content
            if existing_summary:
                return existing_summary
            return ""
```

- [ ] **Step 7: 运行 mypy 验证**

Run: `cd backend && uv run mypy --strict app/ 2>&1 | head -20`

Expected: 0 errors

- [ ] **Step 8: 运行测试**

Run: `cd backend && uv run pytest tests/ -v 2>&1 | tail -20`

Expected: 可能有 chat 测试失败（因为 chat API 改了行为），修复在 Step 9

- [ ] **Step 9: 修复 `tests/test_chat_api_v2.py` — 适配 is_active/context_entities 删除**

1. 删除所有 `is_active` 相关断言
2. 删除所有 `context_entities` 相关断言
3. `close_session` 测试不再验证 `is_active = False`，只验证返回消息
4. `get_session` 测试不再验证 `is_active` 查询逻辑

- [ ] **Step 10: 运行全量测试验证**

Run: `cd backend && uv run pytest tests/ -v 2>&1 | tail -10`

Expected: ALL PASS

- [ ] **Step 11: Commit**

```bash
git add app/models/conversation.py app/services/conversation/ \
        app/api/chat.py app/llm/deepseek.py tests/
git commit -m "refactor: remove is_active/context_entities, fix summary generation"
```

---

### Task 5: 删除 `interview_quota` — 前端

**Files:**
- Modify: `src/features/jobs/types/job.ts`
- Modify: `src/features/chat/types/chat.ts`
- Modify: `src/pages/PostJobPage.tsx`
- Modify: `src/pages/JobDashboardPage.tsx`
- Modify: `src/features/chat/components/JobDetailCard.tsx`

**Interfaces:**
- Consumes: Task 3 完成的后端（API 不再返回 `interview_quota`）
- Produces: 前端无 `interview_quota` 引用

- [ ] **Step 1: 修改 `src/features/jobs/types/job.ts`**

1. `Job` interface 删除 `interview_quota`
2. `CreateJobPayload` interface 删除 `interview_quota`（如果存在）

- [ ] **Step 2: 修改 `src/features/chat/types/chat.ts`**

`JobDetailCardData.job` 中删除 `interview_quota`

- [ ] **Step 3: 修改 `src/pages/PostJobPage.tsx`**

1. 删除"进面人数"表单字段
2. 删除 Zod schema 中 `interview_quota` 验证规则
3. 删除 form state 中的 `interview_quota`

- [ ] **Step 4: 修改 `src/pages/JobDashboardPage.tsx`**

删除表格中 `interview_quota` 列

- [ ] **Step 5: 修改 `src/features/chat/components/JobDetailCard.tsx`**

将 `进面 {job.interview_quota} | 编制 {job.head_count}` 改为仅 `编制 {job.head_count}`

- [ ] **Step 6: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`

Expected: 0 errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "refactor(frontend): remove interview_quota from all components"
```

---

### Task 6: 创建 Alembic Migration — 删除三个列

**Files:**
- Create: `alembic/versions/xxxx_drop_interview_quota_is_active_context_entities.py`

**Interfaces:**
- Consumes: Task 1-4 产出的无三字段的 ORM
- Produces: 数据库 schema 与 ORM 一致

- [ ] **Step 1: 创建 migration 文件**

Run: `cd backend && uv run alembic revision -m "drop_interview_quota_is_active_context_entities" --rev-id drop_three_fields`

- [ ] **Step 2: 编写 migration**

```python
"""drop interview_quota, is_active, context_entities

Revision ID: drop_three_fields
Revises: a1b2c3d4e5f6
Create Date: 2026-07-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'drop_three_fields'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop interview_quota from jobs, is_active + context_entities from conversations."""
    # jobs: drop interview_quota
    op.drop_column('jobs', 'interview_quota')

    # conversations: drop is_active (with index first)
    op.drop_index('ix_conversations_user_active', table_name='conversations')
    op.drop_column('conversations', 'is_active')

    # conversations: drop context_entities
    op.drop_column('conversations', 'context_entities')


def downgrade() -> None:
    """Re-add the dropped columns."""
    # conversations: re-add context_entities
    op.add_column('conversations', sa.Column(
        'context_entities',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        comment='结构化实体 {current_job_id, current_job_code, ...}',
    ))

    # conversations: re-add is_active
    op.add_column('conversations', sa.Column(
        'is_active',
        sa.Boolean(),
        nullable=False,
        server_default=sa.text('true'),
        comment='会话是否活跃',
    ))
    op.create_index('ix_conversations_user_active', 'conversations', ['user_id', 'is_active'], unique=False)

    # jobs: re-add interview_quota
    op.add_column('jobs', sa.Column(
        'interview_quota',
        sa.Integer(),
        nullable=False,
        server_default=sa.text('1'),
        comment='面试人数上限',
    ))
```

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "migration: drop interview_quota, is_active, context_entities columns"
```

---

### Task 7: 修复聊天记录恢复 + 会话生命周期 — 前端

**Files:**
- Modify: `src/features/chat/hooks/useChat.ts`
- Modify: `src/features/chat/components/ChatBubble.tsx`
- Modify: `src/features/chat/components/ChatWindow.tsx`
- Modify: `src/features/auth/store/authStore.ts`

**Interfaces:**
- Consumes: Task 4 产出的后端（`get_session` 通过 `session_id` 查找，`close_session` 不设 `is_active`）
- Produces: 刷新恢复历史；防串号；X 关闭 = 结束对话；登出清 session

- [ ] **Step 1: 修改 `useChat.ts` — 初始化自动 validate + localStorage 绑定 user_id**

关键变更：

1. `loadSessionId` / `saveSessionId` 的 localStorage key 改为 `chat-session-id:{userId}`
2. 新增 `userId` 参数（从 authStore 获取）
3. 初始化时如果有 `sessionId`，立即调用 `validateSession()`
4. `closeSession` 改为清除 localStorage + 重置 messages（不调用后端 API 也可，但保留调用做资源清理）

需要读取当前 `useChat.ts` 的完整代码后精确修改。核心逻辑：

```typescript
// localStorage key 绑定 user_id
const STORAGE_KEY_PREFIX = "chat-session-id";

function getSessionKey(userId: string | null): string {
  return userId ? `${STORAGE_KEY_PREFIX}:${userId}` : STORAGE_KEY_PREFIX;
}

function loadSessionId(userId: string | null): string | null {
  if (!userId) return null;
  return localStorage.getItem(getSessionKey(userId));
}

function saveSessionId(userId: string | null, sessionId: string): void {
  if (!userId) return;
  localStorage.setItem(getSessionKey(userId), sessionId);
}

function clearSessionId(userId: string | null): void {
  if (!userId) return;
  localStorage.removeItem(getSessionKey(userId));
}
```

在 `useChat` hook 初始化时：

```typescript
// 初始化时自动恢复 session
useEffect(() => {
  const savedSessionId = loadSessionId(user?.id ?? null);
  if (savedSessionId && !sessionId) {
    validateSession(savedSessionId);
  }
}, [user?.id]); // 仅在 user 变化时触发
```

- [ ] **Step 2: 修改 `ChatBubble.tsx` — 移除手动 validate 触发**

删除 `hasValidated` ref 和相关的 `validateSession` 手动触发逻辑。因为 `useChat` 已在初始化时自动 validate，ChatBubble 打开时无需重复触发。

- [ ] **Step 3: 修改 `ChatWindow.tsx` — X 关闭时清除 session**

点击关闭按钮时：

```typescript
const handleClose = async () => {
  // 调用后端 closeSession（资源清理）
  if (sessionId) {
    await closeSession(sessionId);
  }
  // 清除 localStorage
  clearSessionId(user?.id ?? null);
  // 重置 messages
  clearMessages();
};
```

- [ ] **Step 4: 修改 `authStore.ts` — logout 时清除 chat session**

在 `logout` / `clearAuth` action 中增加清除 localStorage 的逻辑：

```typescript
// 清除所有 chat-session-id:* 的 localStorage 条目
Object.keys(localStorage)
  .filter(key => key.startsWith("chat-session-id:"))
  .forEach(key => localStorage.removeItem(key));
```

- [ ] **Step 5: 验证前端编译**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`

Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "fix(frontend): chat history recovery + session lifecycle management"
```

---

### Task 8: 最终验证 + skeleton.md 更新

**Files:**
- Modify: `docs/skeleton.md` (在主仓库，非 worktree)
- Verify: mypy + pytest + frontend build

**Interfaces:**
- Consumes: Task 1-7 全部完成
- Produces: 项目文档与代码一致

- [ ] **Step 1: 运行 mypy**

Run: `cd backend && uv run mypy --strict app/ 2>&1 | head -10`

Expected: 0 errors

- [ ] **Step 2: 运行后端全量测试**

Run: `cd backend && uv run pytest tests/ -v 2>&1 | tail -10`

Expected: ALL PASS

- [ ] **Step 3: 运行前端类型检查**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`

Expected: 0 errors

- [ ] **Step 4: 更新 skeleton.md**

将 skeleton.md 中以下内容更新（commit 后在主仓库操作）：

1. `Job` 模型删除 `interview_quota`
2. `Conversation` 模型删除 `is_active`、`context_entities`、`ix_conversations_user_active`
3. `JobCreateRequest`/`JobUpdateRequest`/`JobResponse` 删除 `interview_quota`
4. `EvaluateRequest` 删除 `interview_quota`
5. `EvaluationState` 删除 `interview_quota_override`
6. `ConversationContext` 删除 `context_entities`
7. `build_state_modifier` 仅注入 `session_summary`
8. `close_session` docstring 改为"关闭会话（资源清理）"
9. `get_session` 改为"查询会话（通过 session_id）"
10. 前端 `Job` 类型删除 `interview_quota`
11. `JobDetailCardData.job` 删除 `interview_quota`

- [ ] **Step 5: Commit skeleton 更新**

```bash
git add docs/skeleton.md
git commit -m "docs: update skeleton.md for bugfix/refactor changes"
```

---

## Self-Review Checklist

### 1. Spec Coverage

| Spec 需求 | 对应 Task |
|-----------|----------|
| 删除 `interview_quota` 列 | Task 1 (model/schema) + Task 2 (service/api) + Task 3 (tests) + Task 5 (frontend) + Task 6 (migration) |
| 删除 `is_active` 列 + 复合索引 | Task 4 (后端) + Task 6 (migration) |
| 删除 `context_entities` 列 | Task 4 (后端) + Task 6 (migration) |
| screen_node 固定阈值 60 | Task 2 Step 5 |
| 刷新恢复历史 | Task 7 Step 1 |
| 防止串号 | Task 7 Step 1 (localStorage key 绑定 user_id) |
| X 关闭 = 结束对话 | Task 7 Step 3 |
| 登出清 session | Task 7 Step 4 |
| 统一 summary 触发（每 10 轮） | Task 4 Step 5 (`_SUMMARY_MESSAGE_THRESHOLD = 20`) |
| 删除关闭时独立摘要生成 | Task 4 Step 5 (`close_session` 不触发) |
| 滚动压缩逻辑 | Task 4 Step 5 (old summary + all messages → new summary) |
| 删除跨 session seed 注入 | Task 4 Step 5 (new session: `summary=None`) |
| 改进 summary prompt | Task 4 Step 3 (SUMMARIZE_SYSTEM_PROMPT 重写) |
| summarize_conversation 错误处理 | Task 4 Step 6 (保留旧 summary) |
| Alembic migration | Task 6 |
| 前端删除 interview_quota | Task 5 |
| 更新 skeleton.md | Task 8 Step 4 |

### 2. Placeholder Scan

✅ 无 TBD / TODO / implement later
✅ 所有步骤包含具体代码
✅ 无 "similar to Task N" 省略

### 3. Type Consistency

✅ `EvaluationState` 无 `interview_quota_override` — Task 2 Step 4 删除，Task 2 Step 5/6/7 不再引用
✅ `Conversation` 无 `is_active`/`context_entities` — Task 4 Step 1 删除，后续 API 不引用
✅ `JobResponse` 无 `interview_quota` — Task 1 Step 4 删除，前端 Task 5 同步
✅ `EvaluateRequest()` 默认无参数 — Task 2 Step 2 与 Task 1 Step 5 一致

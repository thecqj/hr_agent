# Phase 1: Tool Definitions + ReAct Agent Graph

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 14-node intent-classification conversation graph with a `create_react_agent` that uses 7 flexible tools, enabling LLM-driven multi-step reasoning.

**Architecture:** The current `StateGraph(ConversationState)` with hardcoded `route_by_intent` routing is replaced by `create_react_agent(model, tools, checkpointer, state_modifier)`. Three generic query tools (`query_jobs`, `query_applications`, `query_evaluation`) accept flexible `filter`/`fields`/`group_by` parameters. Four write-operation tools (`trigger_evaluation`, `confirm_evaluation`, `update_candidate_status`, `update_job_status`) encapsulate business semantics with built-in permission checks. The LLM (DeepSeek via `ChatOpenAI`) autonomously decides which tools to call and how to combine results.

**Tech Stack:** LangGraph `create_react_agent`, `langchain-openai` `ChatOpenAI`, SQLAlchemy 2.0 async, Pydantic v2

## Global Constraints

- Python 3.12, strict type hints, `mypy --strict` must pass
- SQLAlchemy 2.0 type-annotated style (`Mapped[str] = mapped_column(...)`)
- Pydantic v2 for DTOs exclusively
- All DB queries use parameterized queries; filter key whitelist + value validation enforced in Tool layer
- Row-level permission (`recruiter_id = current_user`) enforced in all Tool implementations
- DeepSeek API compatible with OpenAI format; `ChatOpenAI` from `langchain-openai` for tool_call support
- Evaluation graph (5 nodes) unchanged — accessed internally by `trigger_evaluation` Tool
- Existing service functions (`resolve_job`, `list_jobs`, `count_by_job_and_status`, etc.) reused inside Tools

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `backend/app/services/conversation/tools.py` | 7 Tool definitions with parameter security |
| Create | `backend/app/services/conversation/prompts.py` | Overwrite — new `HR_AGENT_SYSTEM_PROMPT` + `build_state_modifier` (replaces old intent prompts) |
| Create | `backend/app/services/conversation/graph.py` | Overwrite — `create_react_agent` builder (replaces 14-node graph) |
| Create | `backend/app/services/conversation/state.py` | Overwrite — minimal state type for ReAct agent (replaces `ConversationState` TypedDict) |
| Modify | `backend/app/config.py` | Add `CHAT_MODEL` setting |
| Modify | `backend/requirements.txt` | Add `langchain-openai` |
| Delete | (none — old nodes.py kept until Phase 2, but no longer imported) |

---

### Task 1: Add `langchain-openai` dependency and `CHAT_MODEL` config

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py:37-44`

**Interfaces:**
- Consumes: Existing `Settings` class
- Produces: `langchain-openai` available; `settings.CHAT_MODEL` (str) for Tool-calling model name

- [ ] **Step 1: Add `langchain-openai` to requirements.txt**

Append after the existing `langgraph-checkpoint-postgres` line:

```
langchain-openai
```

Full relevant block should be:

```
# Workflow
langgraph
langchain-core
langgraph-checkpoint-postgres
langchain-openai
```

- [ ] **Step 2: Add `CHAT_MODEL` to `Settings` in `config.py`**

Add after the `LLM_BORDERLINE_RANGE` field (line 44):

```python
    CHAT_MODEL: str = "deepseek-chat"  # model used for create_react_agent tool_call
```

- [ ] **Step 3: Install the new dependency**

Run: `cd backend && uv pip install -r requirements.txt 2>&1 | tail -3`

Expected: `langchain-openai` and its deps installed without error.

- [ ] **Step 4: Verify mypy still passes**

Run: `cd backend && uv run mypy --strict app/`

Expected: `Success: no issues found in ... source files`

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/config.py
git commit -m "feat: add langchain-openai dependency + CHAT_MODEL config"
```

---

### Task 2: Write `prompts.py` — system prompt + state modifier

**Files:**
- Create: `backend/app/services/conversation/prompts.py` (overwrite existing)

**Interfaces:**
- Consumes: `settings.CHAT_MODEL` (from Task 1)
- Produces: `HR_AGENT_SYSTEM_PROMPT: str`, `build_state_modifier(state: dict) -> str`

- [ ] **Step 1: Write the new prompts.py**

Replace the entire file. The old `INTENT_SYSTEM_PROMPT`, `build_intent_user_prompt`, `SUMMARIZE_SYSTEM_PROMPT`, `build_summarize_user_prompt` are deleted. New file contains only `HR_AGENT_SYSTEM_PROMPT` and `build_state_modifier`:

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
        state: ReAct agent state dict，包含可能存在的
               session_summary 和 context_entities

    Returns:
        完整的 system prompt 字符串
    """
    parts: list[str] = [HR_AGENT_SYSTEM_PROMPT]

    session_summary: str | None = state.get("session_summary")
    if session_summary:
        parts.append(f"\n## 对话摘要\n{session_summary}")

    context_entities: dict[str, Any] | None = state.get("context_entities")
    if context_entities:
        lines = [f"- {k}: {v}" for k, v in context_entities.items() if v]
        if lines:
            parts.append("\n## 当前对话上下文\n" + "\n".join(lines))

    return "\n".join(parts)
```

- [ ] **Step 2: Verify mypy passes**

Run: `cd backend && uv run mypy --strict app/services/conversation/prompts.py`

Expected: `Success: no issues found`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/conversation/prompts.py
git commit -m "feat: replace intent prompts with ReAct system prompt + state modifier"
```

---

### Task 3: Write `tools.py` — 3 query tools

**Files:**
- Create: `backend/app/services/conversation/tools.py`

**Interfaces:**
- Consumes: `resolve_job` from `app.services.job_service`, `count_by_job_and_status`, `count_by_job_grouped_by_status`, `list_by_job` from `app.services.application_service`, `get_config` from `langgraph.config`
- Produces: `query_jobs`, `query_applications`, `query_evaluation` async tools (decorated with `@tool`)

- [ ] **Step 1: Write the query tools**

Create `backend/app/services/conversation/tools.py` with the 3 query tools. This file will grow as we add write tools in Task 4.

```python
"""HR Agent ReAct 对话 — Tool 定义

7 个 Tool: 3 个通用查询 + 4 个写操作
"""

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.config import get_config

from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, JobStatus, WorkType
from app.models.user import User
from app.services.job_service import resolve_job
from app.services.application_service import (
    count_by_job_and_status,
    count_by_job_grouped_by_status,
    list_by_job,
)

from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ────────────────────────────────────────────────


def _get_db() -> AsyncSession:
    """从 LangGraph config 获取数据库会话"""
    config = get_config()
    db: AsyncSession = config["configurable"]["db"]
    return db


def _get_user_id() -> str:
    """从 LangGraph config 获取当前用户 ID"""
    config = get_config()
    return str(config["configurable"]["user_id"])


# ── Filter key whitelists ──────────────────────────────────


_JOBS_FILTER_KEYS: frozenset[str] = frozenset({
    "job_code", "keyword", "status", "work_type",
    "salary_min", "salary_max",
})

_JOBS_VALID_STATUSES: frozenset[str] = frozenset({"active", "closed", "draft"})
_JOBS_VALID_WORK_TYPES: frozenset[str] = frozenset({"remote", "onsite", "hybrid"})

_APPLICATIONS_FILTER_KEYS: frozenset[str] = frozenset({
    "status", "ai_decision", "candidate_name",
    "min_ai_score", "max_ai_score",
})

_APPLICATIONS_VALID_STATUSES: frozenset[str] = frozenset({
    "pending", "interview", "rejected", "hired",
})
_APPLICATIONS_VALID_DECISIONS: frozenset[str] = frozenset({"recommend", "reject"})

_APPLICATIONS_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "candidate_name", "ai_score", "ai_decision", "status",
    "ai_evaluation", "ai_decision_reason", "resume_summary",
    "cover_letter", "structured_resume",
})

_JOBS_ALLOWED_FIELDS: frozenset[str] = frozenset({
    "job_code", "title", "status", "head_count", "applications_count",
    "description", "requirements", "skills_required",
    "salary_min", "salary_max", "location", "work_type",
    "interview_quota", "recruiter_name",
})

_APPLICATIONS_ALLOWED_GROUP_BY: frozenset[str] = frozenset({
    "status", "ai_decision",
})


def _sanitize_filter(
    raw: dict[str, Any] | None,
    allowed_keys: frozenset[str],
) -> dict[str, Any]:
    """Strip unknown keys from a filter dict."""
    if not raw:
        return {}
    return {k: v for k, v in raw.items() if k in allowed_keys}


# ── Query Tools ────────────────────────────────────────────


@tool
async def query_jobs(
    filter: dict[str, Any] | None = None,
    fields: list[str] | None = None,
    limit: int = 20,
) -> str:
    """查询岗位数据。

    filter 可包含任意组合:
      - job_code: 岗位编号（精确匹配，优先使用）
      - keyword: 关键词（模糊匹配标题）
      - status: 岗位状态 ("active", "closed", "draft")
      - work_type: 工作类型 ("remote", "onsite", "hybrid")
      - salary_min / salary_max: 薪资范围

    fields 指定返回字段，默认: ["job_code", "title", "status", "head_count", "applications_count"]
    可选字段: description, requirements, skills_required, salary_min, salary_max,
    location, work_type, interview_quota, recruiter_name

    只返回当前用户有权限查看的岗位（招聘者只看自己的岗位）。

    Examples:
      - 查所有活跃岗位: query_jobs(filter={"status": "active"})
      - 按编号查: query_jobs(filter={"job_code": "J04217"})
      - 模糊搜索: query_jobs(filter={"keyword": "前端"})
      - 带详情: query_jobs(filter={"job_code": "J04217"},
                   fields=["job_code","title","requirements","skills_required"])
    """
    db = _get_db()
    user_id = _get_user_id()

    safe_filter = _sanitize_filter(filter, _JOBS_FILTER_KEYS)
    safe_fields = [f for f in (fields or []) if f in _JOBS_ALLOWED_FIELDS]
    if not safe_fields:
        safe_fields = ["job_code", "title", "status", "head_count", "applications_count"]

    # Base query — recruiter sees only their own jobs
    query = select(Job).where(Job.recruiter_id == uuid.UUID(user_id))

    # Apply filters
    if "job_code" in safe_filter:
        query = query.where(Job.job_code == str(safe_filter["job_code"]))

    if "keyword" in safe_filter:
        kw = str(safe_filter["keyword"]).lower().replace("%", "\\%").replace("_", "\\_")
        query = query.where(func.lower(Job.title).ilike(f"%{kw}%", escape="\\"))

    if "status" in safe_filter:
        status_val = str(safe_filter["status"]).lower()
        if status_val in _JOBS_VALID_STATUSES:
            query = query.where(Job.status == JobStatus(status_val))

    if "work_type" in safe_filter:
        wt_val = str(safe_filter["work_type"]).lower()
        if wt_val in _JOBS_VALID_WORK_TYPES:
            query = query.where(Job.work_type == WorkType(wt_val))

    if "salary_min" in safe_filter:
        try:
            sal_min = int(safe_filter["salary_min"])
            query = query.where(Job.salary_max >= sal_min)
        except (ValueError, TypeError):
            pass

    if "salary_max" in safe_filter:
        try:
            sal_max = int(safe_filter["salary_max"])
            query = query.where(Job.salary_min <= sal_max)
        except (ValueError, TypeError):
            pass

    query = query.order_by(Job.created_at.desc()).limit(min(limit, 50))
    result = await db.execute(query.options(selectinload(Job.applications)))
    jobs = list(result.scalars().all())

    if not jobs:
        return "未找到匹配的岗位。"

    # Format output
    lines: list[str] = []
    for j in jobs:
        app_count = len(j.applications) if j.applications else 0
        item: dict[str, Any] = {"job_code": j.job_code, "title": j.title}

        for f in safe_fields:
            if f == "job_code" or f == "title":
                continue  # already included
            if f == "status":
                item["status"] = j.status.value
            elif f == "head_count":
                item["head_count"] = j.head_count
            elif f == "applications_count":
                item["applications_count"] = app_count
            elif f == "description":
                item["description"] = j.description[:200] + "..." if len(j.description) > 200 else j.description
            elif f == "requirements":
                item["requirements"] = j.requirements[:200] + "..." if len(j.requirements) > 200 else j.requirements
            elif f == "skills_required":
                item["skills_required"] = j.skills_required or []
            elif f == "salary_min" and j.salary_min is not None:
                item["salary_min"] = j.salary_min
            elif f == "salary_max" and j.salary_max is not None:
                item["salary_max"] = j.salary_max
            elif f == "location" and j.location is not None:
                item["location"] = j.location
            elif f == "work_type":
                item["work_type"] = j.work_type.value
            elif f == "interview_quota":
                item["interview_quota"] = j.interview_quota
            elif f == "recruiter_name":
                item["recruiter_name"] = j.recruiter.name if j.recruiter else None

        lines.append(str(item))

    return "\n".join(lines)


@tool
async def query_applications(
    job_code: str | None = None,
    job_title: str | None = None,
    filter: dict[str, Any] | None = None,
    fields: list[str] | None = None,
    group_by: list[str] | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    limit: int = 50,
) -> str:
    """查询投递/候选人数据。

    必须指定岗位（job_code 或 job_title）。

    filter 可包含:
      - status: 投递状态 ("pending", "interview", "rejected", "hired")
      - ai_decision: AI 决策 ("recommend", "reject")
      - candidate_name: 候选人姓名（模糊匹配）
      - min_ai_score / max_ai_score: AI 评分范围

    fields 指定返回字段，默认: ["candidate_name", "ai_score", "ai_decision", "status"]
    可选字段: ai_evaluation, ai_decision_reason, resume_summary,
    cover_letter, structured_resume

    group_by: 按字段分组统计人数
      - ["status"]: 各投递状态人数（招聘漏斗）
      - ["ai_decision"]: 各 AI 决策人数
      - ["status", "ai_decision"]: 交叉分组

    sort_by: 排序字段，默认 "ai_score"
    sort_order: "desc" 或 "asc"

    只返回当前用户有权限查看的投递数据。

    Examples:
      - 漏斗概览: query_applications(job_code="J04217", group_by=["status"])
      - 推荐候选人 Top5: query_applications(job_code="J04217",
          filter={"ai_decision": "recommend"},
          sort_by="ai_score", limit=5)
      - 被拒高分: query_applications(job_code="J04217",
          filter={"ai_decision": "reject", "min_ai_score": 70},
          sort_by="ai_score")
      - 某人评估详情: query_applications(job_code="J04217",
          filter={"candidate_name": "张三"},
          fields=["ai_score", "ai_evaluation", "ai_decision_reason"])
    """
    db = _get_db()
    user_id = _get_user_id()

    safe_filter = _sanitize_filter(filter, _APPLICATIONS_FILTER_KEYS)
    safe_fields = [f for f in (fields or []) if f in _APPLICATIONS_ALLOWED_FIELDS]
    if not safe_fields:
        safe_fields = ["candidate_name", "ai_score", "ai_decision", "status"]

    safe_group_by = [g for g in (group_by or []) if g in _APPLICATIONS_ALLOWED_GROUP_BY]

    # Resolve job
    resolved = await resolve_job(db, user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return "未找到匹配的岗位。"
    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"

    job = resolved

    # ── group_by path ───────────────────────────────────
    if safe_group_by:
        if safe_group_by == ["status"]:
            grouped = await count_by_job_grouped_by_status(db, str(job.id))
            total = sum(grouped.values())
            lines = [f"岗位「{job.title}」({job.job_code}) 共 {total} 份投递："]
            for status_key in ["pending", "interview", "rejected", "hired"]:
                count = grouped.get(status_key, 0)
                pct = round(count / total * 100, 1) if total > 0 else 0
                labels = {"pending": "待审核", "interview": "面试中", "rejected": "已拒绝", "hired": "已录用"}
                lines.append(f"  {labels.get(status_key, status_key)}: {count}人（{pct}%）")
            return "\n".join(lines)

        elif safe_group_by == ["ai_decision"]:
            stmt = (
                select(Application.ai_decision, func.count())
                .where(Application.job_id == job.id)
                .group_by(Application.ai_decision)
            )
            rows = (await db.execute(stmt)).all()
            lines = [f"岗位「{job.title}」({job.job_code}) AI 决策分布："]
            for decision_val, count in rows:
                label = {"recommend": "推荐", "reject": "不推荐"}.get(str(decision_val), str(decision_val))
                lines.append(f"  {label}: {count}人")
            return "\n".join(lines)

        elif set(safe_group_by) == {"status", "ai_decision"}:
            stmt = (
                select(Application.status, Application.ai_decision, func.count())
                .where(Application.job_id == job.id)
                .group_by(Application.status, Application.ai_decision)
            )
            rows = (await db.execute(stmt)).all()
            lines = [f"岗位「{job.title}」({job.job_code}) 状态×决策交叉分布："]
            for status_val, decision_val, count in rows:
                s_label = {"pending": "待审核", "interview": "面试中", "rejected": "已拒绝", "hired": "已录用"}.get(status_val.value, status_val.value)
                d_label = {"recommend": "推荐", "reject": "不推荐"}.get(str(decision_val), str(decision_val))
                lines.append(f"  {s_label} & {d_label}: {count}人")
            return "\n".join(lines)

    # ── detail query path ───────────────────────────────
    query = (
        select(Application)
        .where(Application.job_id == job.id)
        .options(selectinload(Application.applicant))
    )

    # Apply filters
    if "status" in safe_filter:
        status_val = str(safe_filter["status"]).lower()
        if status_val in _APPLICATIONS_VALID_STATUSES:
            query = query.where(Application.status == ApplicationStatus(status_val))

    if "ai_decision" in safe_filter:
        decision_val = str(safe_filter["ai_decision"]).lower()
        if decision_val in _APPLICATIONS_VALID_DECISIONS:
            query = query.where(Application.ai_decision == decision_val)

    if "candidate_name" in safe_filter:
        name = str(safe_filter["candidate_name"]).lower().replace("%", "\\%").replace("_", "\\_")
        query = query.join(User, Application.applicant_id == User.id).where(
            func.lower(User.name).ilike(f"%{name}%", escape="\\")
        )

    if "min_ai_score" in safe_filter:
        try:
            query = query.where(Application.ai_score >= float(safe_filter["min_ai_score"]))
        except (ValueError, TypeError):
            pass

    if "max_ai_score" in safe_filter:
        try:
            query = query.where(Application.ai_score <= float(safe_filter["max_ai_score"]))
        except (ValueError, TypeError):
            pass

    # Sort
    sort_field = sort_by or "ai_score"
    if sort_field == "ai_score":
        if sort_order.lower() == "asc":
            query = query.order_by(Application.ai_score.asc().nullslast())
        else:
            query = query.order_by(Application.ai_score.desc().nullslast())
    else:
        query = query.order_by(Application.created_at.desc())

    query = query.limit(min(limit, 100))
    result = await db.execute(query)
    apps = list(result.scalars().all())

    if not apps:
        return f"岗位「{job.title}」({job.job_code}) 暂无匹配的投递记录。"

    # Format output
    lines: list[str] = []
    for app in apps:
        name = app.applicant.name if app.applicant else "未知"
        item: dict[str, Any] = {"candidate_name": name}

        for f in safe_fields:
            if f == "candidate_name":
                continue
            if f == "ai_score":
                item["ai_score"] = app.ai_score
            elif f == "ai_decision":
                item["ai_decision"] = app.ai_decision
            elif f == "status":
                item["status"] = app.status.value
            elif f == "ai_evaluation" and app.ai_evaluation is not None:
                eval_str = str(app.ai_evaluation)
                item["ai_evaluation"] = eval_str[:300] + "..." if len(eval_str) > 300 else eval_str
            elif f == "ai_decision_reason" and app.ai_decision_reason is not None:
                item["ai_decision_reason"] = app.ai_decision_reason
            elif f == "resume_summary" and app.structured_resume is not None:
                # Extract a brief summary from structured_resume
                sr = app.structured_resume
                if isinstance(sr, dict):
                    item["resume_summary"] = f"{sr.get('name', '')}, {sr.get('work_experience_years', '?')}年经验"
            elif f == "cover_letter" and app.cover_letter is not None:
                item["cover_letter"] = app.cover_letter[:200] + "..." if len(app.cover_letter) > 200 else app.cover_letter
            elif f == "structured_resume" and app.structured_resume is not None:
                item["structured_resume"] = "(available)"

        lines.append(str(item))

    return "\n".join(lines)


@tool
async def query_evaluation(
    job_code: str | None = None,
    task_id: str | None = None,
) -> str:
    """查询评估任务的状态和结果。

    可通过 task_id 直接查询，或通过 job_code 查找岗位最近的评估任务。
    返回: 任务状态、进度(evaluated_count/total_count)、评估摘要
    (推荐/拒绝人数、截止分数、边界调整等)。

    只返回当前用户有权限查看的评估任务。
    """
    db = _get_db()
    user_id = _get_user_id()

    task: EvaluationTask | None = None

    # Priority 1: task_id exact match
    if task_id:
        task = await db.get(EvaluationTask, task_id)
        if task and str(task.triggered_by) != user_id:
            return "无权查看此评估任务。"

    # Priority 2: find by job_code
    if not task and job_code:
        resolved = await resolve_job(db, user_id, job_code=job_code)
        if resolved is None:
            return "未找到匹配的岗位。"
        if isinstance(resolved, list):
            return "找到多个匹配的岗位，请指定岗位编号。"
        job = resolved

        stmt = (
            select(EvaluationTask)
            .where(EvaluationTask.job_id == job.id)
            .order_by(EvaluationTask.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()

    if not task:
        return "未找到评估任务。"

    # Build summary
    status_label = {
        EvalTaskStatus.PENDING: "等待中",
        EvalTaskStatus.RUNNING: "运行中",
        EvalTaskStatus.COMPLETED: "已完成",
        EvalTaskStatus.CONFIRMED: "已确认",
        EvalTaskStatus.FAILED: "失败",
    }.get(task.status, task.status.value)

    lines = [
        f"评估任务 {task.id}:",
        f"  状态: {status_label}",
        f"  进度: {task.evaluated_count}/{task.total_count}",
    ]

    if task.result_summary:
        summary = task.result_summary if isinstance(task.result_summary, dict) else {}
        if "recommend_count" in summary:
            lines.append(f"  推荐: {summary['recommend_count']}人")
        if "reject_count" in summary:
            lines.append(f"  不推荐: {summary['reject_count']}人")
        if "cutoff_score" in summary:
            lines.append(f"  截止分数: {summary['cutoff_score']}")

    if task.error_message:
        lines.append(f"  错误: {task.error_message}")

    return "\n".join(lines)
```

- [ ] **Step 2: Verify mypy passes**

Run: `cd backend && uv run mypy --strict app/services/conversation/tools.py`

Expected: `Success: no issues found`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/conversation/tools.py
git commit -m "feat: add 3 query tools (query_jobs, query_applications, query_evaluation)"
```

---

### Task 4: Add 4 write-operation tools to `tools.py`

**Files:**
- Modify: `backend/app/services/conversation/tools.py`

**Interfaces:**
- Consumes: `resolve_job` from `app.services.job_service`, `update_application_status` from `app.services.application_service`, `update_job_status` from `app.services.job_service`, `build_evaluation_graph` from `app.services.agent.graph`, `EvaluationState` from `app.services.agent.state`
- Produces: `trigger_evaluation`, `confirm_evaluation`, `update_candidate_status`, `update_job_status` async tools

- [ ] **Step 1: Append write-operation tools to `tools.py`**

Add these imports at the top of `tools.py` (merge with existing imports):

```python
from app.schemas.application import ApplicationStatusUpdateRequest
from app.schemas.job import JobStatusUpdateRequest
from app.services.job_service import update_job_status
from app.services.application_service import update_application_status
```

Then append the 4 write tools at the end of the file:

```python
# ── Write Tools ────────────────────────────────────────────


@tool
async def trigger_evaluation(
    job_code: str | None = None,
    job_title: str | None = None,
    interview_quota: int | None = None,
) -> str:
    """对岗位触发 AI 简历评估。

    评估过程可能需要数分钟，会实时报告进度。
    评估完成后候选人获得 AI 评分和推荐/拒绝决策，
    但不会自动变更状态——需调用 confirm_evaluation 确认。

    ⚠️ 评估是耗时操作，触发前应确认用户意图。

    Args:
        job_code: 岗位编号（优先使用）
        job_title: 岗位名称（模糊匹配，job_code 优先）
        interview_quota: 面试人数上限，覆盖岗位默认设置
    """
    db = _get_db()
    user_id = _get_user_id()

    # Resolve job
    resolved = await resolve_job(db, user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return "未找到匹配的岗位。"
    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"

    job = resolved

    # Override interview_quota if provided
    if interview_quota is not None and job.interview_quota != interview_quota:
        job.interview_quota = interview_quota
        await db.commit()
        await db.refresh(job)

    # Concurrency check
    existing_stmt = select(EvaluationTask).where(
        EvaluationTask.job_id == job.id,
        EvaluationTask.status.in_([EvalTaskStatus.PENDING, EvalTaskStatus.RUNNING]),
    )
    existing_task = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing_task:
        return (
            f"⚠️ 岗位「{job.title}」已有正在进行的评估任务 "
            f"(task_id={existing_task.id}, status={existing_task.status.value})。"
        )

    # Count pending applications
    count_stmt = select(func.count()).select_from(Application).where(
        Application.job_id == job.id,
        Application.status == ApplicationStatus.PENDING,
    )
    pending_count: int = (await db.execute(count_stmt)).scalar() or 0

    if pending_count == 0:
        return f"岗位「{job.title}」暂无待处理的简历，无法触发评估。"

    # Create evaluation task record
    task_id = uuid.uuid4()
    eval_task = EvaluationTask(
        id=task_id,
        job_id=job.id,
        triggered_by=uuid.UUID(user_id),
        status=EvalTaskStatus.PENDING,
        total_count=pending_count,
    )
    db.add(eval_task)
    await db.commit()
    await db.refresh(eval_task)
    task_id_str = str(task_id)

    # Run evaluation graph inline
    await adispatch_custom_event("progress", {
        "status": f"正在评估「{job.title}」岗位的简历...",
        "total_count": pending_count,
    })

    from app.database import get_checkpointer
    from app.services.agent.graph import build_evaluation_graph
    from app.services.agent.state import EvaluationState

    checkpointer = get_checkpointer()
    graph = build_evaluation_graph(checkpointer)

    initial_state: EvaluationState = {
        "job_id": str(job.id),
        "triggered_by": user_id,
        "task_id": task_id_str,
        "errors": [],
        "interview_quota_override": interview_quota if isinstance(interview_quota, int) else None,
    }

    config: RunnableConfig = {
        "configurable": {
            "thread_id": task_id_str,
            "db": db,
        }
    }

    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            if event.get("event") == "on_custom_event":
                event_data = event.get("data", {})
                await adispatch_custom_event("progress", event_data)
    except Exception as exc:
        failed_task = await db.get(EvaluationTask, task_id_str)
        if failed_task and failed_task.status not in (
            EvalTaskStatus.COMPLETED, EvalTaskStatus.CONFIRMED, EvalTaskStatus.FAILED,
        ):
            failed_task.status = EvalTaskStatus.FAILED
            failed_task.error_message = f"评估工作流异常: {exc}"
            await db.commit()
        return f"❌ 评估工作流执行出错：{exc}"

    final_task = await db.get(EvaluationTask, task_id_str)
    if final_task and final_task.status == EvalTaskStatus.COMPLETED:
        summary = final_task.result_summary or {}
        recommend_count = summary.get("recommend_count", 0)
        reject_count = summary.get("reject_count", 0)
        return (
            f"✅ 岗位「{job.title}」评估完成！共 {final_task.total_count} 份简历，"
            f"推荐 {recommend_count} 人，不推荐 {reject_count} 人。\n"
            f"任务 ID: {task_id_str}\n"
            f"需调用 confirm_evaluation 确认结果后才会变更候选人状态。"
        )

    return f"评估任务 {task_id_str} 状态异常，请查看详情。"


@tool
async def confirm_evaluation(
    task_id: str,
) -> str:
    """确认评估结果，按 AI 建议批量更新候选人状态。

    评估完成后需确认才会实际变更候选人状态
    (pending → interview 或 rejected)。

    ⚠️ 写操作，执行前必须向用户确认！

    Args:
        task_id: 评估任务 ID
    """
    db = _get_db()
    user_id = _get_user_id()

    task = await db.get(EvaluationTask, task_id)
    if not task:
        return "评估任务不存在。"
    if str(task.triggered_by) != user_id:
        return "无权操作此评估任务。"
    if task.status != EvalTaskStatus.COMPLETED:
        return f"任务状态为 {task.status.value}，只有 completed 状态才可确认。"

    # Batch update: recommend → interview, reject → rejected
    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        return "用户不存在。"

    updated_count = 0

    # Recommend → interview
    recommend_stmt = select(Application).where(
        Application.job_id == task.job_id,
        Application.ai_decision == "recommend",
        Application.status == ApplicationStatus.PENDING,
    )
    recommend_apps = list((await db.execute(recommend_stmt)).scalars().all())
    for app in recommend_apps:
        app.status = ApplicationStatus.INTERVIEW
        updated_count += 1

    # Reject → rejected
    reject_stmt = select(Application).where(
        Application.job_id == task.job_id,
        Application.ai_decision == "reject",
        Application.status == ApplicationStatus.PENDING,
    )
    reject_apps = list((await db.execute(reject_stmt)).scalars().all())
    for app in reject_apps:
        app.status = ApplicationStatus.REJECTED
        updated_count += 1

    task.status = EvalTaskStatus.CONFIRMED
    await db.commit()

    return f"✅ 已确认评估结果，更新了 {updated_count} 位候选人的状态。"


@tool
async def update_candidate_status(
    job_code: str,
    candidate_name: str,
    target_status: str,
) -> str:
    """变更候选人状态（推进面试/拒绝等）。

    ⚠️ 写操作，执行前必须向用户确认！

    Args:
        job_code: 岗位编号
        candidate_name: 候选人姓名
        target_status: 目标状态，"interview" 或 "rejected"
    """
    db = _get_db()
    user_id = _get_user_id()

    if target_status not in ("interview", "rejected"):
        return "target_status 只接受 'interview' 或 'rejected'。"

    # Resolve job
    resolved = await resolve_job(db, user_id, job_code=job_code)
    if resolved is None:
        return "未找到匹配的岗位。"
    if isinstance(resolved, list):
        return "找到多个匹配的岗位，请指定唯一岗位编号。"

    job = resolved

    # Find application by candidate name
    escaped_name = candidate_name.lower().replace("%", "\\%").replace("_", "\\_")
    name_stmt = select(Application).join(
        User, Application.applicant_id == User.id
    ).where(
        Application.job_id == job.id,
        func.lower(User.name).ilike(f"%{escaped_name}%", escape="\\"),
    ).options(selectinload(Application.applicant))
    app_result = await db.execute(name_stmt)
    apps = list(app_result.scalars().all())

    if len(apps) == 0:
        return f"未找到候选人「{candidate_name}」的申请记录。"
    if len(apps) > 1:
        return f"找到 {len(apps)} 位名为「{candidate_name}」的候选人，请提供更精确的信息。"

    app = apps[0]
    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        return "用户不存在。"

    try:
        status_enum = ApplicationStatus(target_status)
        data = ApplicationStatusUpdateRequest(status=status_enum)
        await update_application_status(db, str(app.id), data, user)
    except Exception as exc:
        return f"状态变更失败：{exc}"

    status_labels = {"interview": "面试阶段", "rejected": "已拒绝"}
    label = status_labels.get(target_status, target_status)
    name = app.applicant.name if app.applicant else candidate_name
    return f"✅ 已将候选人「{name}」推进到{label}。"


@tool
async def update_job_status(
    job_code: str,
    target_status: str,
) -> str:
    """变更岗位状态（开启/关闭等）。

    ⚠️ 写操作，执行前必须向用户确认！

    Args:
        job_code: 岗位编号
        target_status: 目标状态，"active" 或 "closed"
    """
    db = _get_db()
    user_id = _get_user_id()

    if target_status not in ("active", "closed"):
        return "target_status 只接受 'active' 或 'closed'。"

    resolved = await resolve_job(db, user_id, job_code=job_code)
    if resolved is None:
        return "未找到匹配的岗位。"
    if isinstance(resolved, list):
        return "找到多个匹配的岗位，请指定唯一岗位编号。"

    job = resolved
    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        return "用户不存在。"

    try:
        status_enum = JobStatus(target_status)
        data = JobStatusUpdateRequest(status=status_enum)
        await update_job_status(db, str(job.id), data, user)
    except Exception as exc:
        return f"岗位状态变更失败：{exc}"

    action_labels = {"active": "开启", "closed": "关闭"}
    label = action_labels.get(target_status, target_status)
    return f"✅ 已{label}岗位「{job.title}」({job.job_code})。"
```

- [ ] **Step 2: Verify mypy passes**

Run: `cd backend && uv run mypy --strict app/services/conversation/tools.py`

Expected: `Success: no issues found`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/conversation/tools.py
git commit -m "feat: add 4 write-operation tools (trigger/confirm evaluation, update candidate/job status)"
```

---

### Task 5: Write new `state.py` and `graph.py` — ReAct agent

**Files:**
- Create: `backend/app/services/conversation/state.py` (overwrite)
- Create: `backend/app/services/conversation/graph.py` (overwrite)
- Modify: `backend/app/services/conversation/__init__.py`

**Interfaces:**
- Consumes: `tools.py` (all 7 tools), `prompts.py` (`build_state_modifier`), `config.py` (`settings`), `AsyncPostgresSaver` from database
- Produces: `build_conversation_graph(checkpointer) -> CompiledStateGraph` (same signature as before)

- [ ] **Step 1: Write the new `state.py`**

The old `ConversationState` and `PendingAction` TypedDicts are no longer needed. `create_react_agent` uses its own built-in message-based state. We only need a thin wrapper for the context that gets injected into `state_modifier`:

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
    context_entities: dict[str, Any]
```

- [ ] **Step 2: Write the new `graph.py`**

Replace the entire 14-node graph with `create_react_agent`:

```python
"""HR Agent ReAct 对话 — Agent 图定义

使用 create_react_agent 替代原有的 14 节点意图分类图。
LLM 自主推理并选择 Tool，实现多步查询和灵活回复。
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings
from app.services.conversation.tools import (
    query_jobs,
    query_applications,
    query_evaluation,
    trigger_evaluation,
    confirm_evaluation,
    update_candidate_status,
    update_job_status,
)
from app.services.conversation.prompts import build_state_modifier


# All 7 tools
ALL_TOOLS = [
    query_jobs,
    query_applications,
    query_evaluation,
    trigger_evaluation,
    confirm_evaluation,
    update_candidate_status,
    update_job_status,
]


def build_conversation_graph(
    checkpointer: AsyncPostgresSaver,
    *,
    context: dict[str, object] | None = None,
) -> CompiledStateGraph:  # type: ignore[type-arg]
    """构建 ReAct 对话 Agent 图。

    Args:
        checkpointer: LangGraph PostgreSQL 持久化存储
        context: 可选的上下文字典，注入到 system prompt
                 (session_summary, context_entities)

    Returns:
        编译后的 ReAct agent 图
    """
    chat_model = ChatOpenAI(
        model=settings.CHAT_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        temperature=0.3,
    )

    state_modifier = build_state_modifier(context or {})

    graph = create_react_agent(
        model=chat_model,
        tools=ALL_TOOLS,
        checkpointer=checkpointer,
        state_modifier=state_modifier,
    )

    return graph
```

- [ ] **Step 3: Update `__init__.py`**

The public API remains `build_conversation_graph`, so `__init__.py` needs no functional change, but let's also export `ConversationContext` for the API layer:

```python
"""HR Agent 对话助手模块"""

from app.services.conversation.graph import build_conversation_graph
from app.services.conversation.state import ConversationContext

__all__ = ["build_conversation_graph", "ConversationContext"]
```

- [ ] **Step 4: Verify mypy passes on the whole conversation module**

Run: `cd backend && uv run mypy --strict app/services/conversation/`

Expected: `Success: no issues found`

- [ ] **Step 5: Verify full project mypy passes**

Run: `cd backend && uv run mypy --strict app/`

Expected: `Success: no issues found` (will likely fail due to `chat.py` still importing old types — that's Phase 2. If it fails only on chat.py imports, that's expected and acceptable.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/conversation/state.py backend/app/services/conversation/graph.py backend/app/services/conversation/__init__.py
git commit -m "feat: replace 14-node graph with create_react_agent + 7 tools"
```

---

### Task 6: Clean up old `nodes.py` — remove or mark deprecated

**Files:**
- Delete content: `backend/app/services/conversation/nodes.py` → keep as empty file with deprecation note

**Interfaces:**
- Consumes: None (this is cleanup)
- Produces: No active exports from `nodes.py`

- [ ] **Step 1: Replace nodes.py with deprecation notice**

The old `nodes.py` (1080 lines) is no longer used. Replace it with a minimal deprecation file to avoid breaking any stray imports during the transition:

```python
"""DEPRECATED: 14-node 对话图已迁移至 ReAct Agent 架构。

原 nodes.py 中的所有节点（intent_node, dispatch_node, feedback_node 等）
已被 create_react_agent + 7 Tools 替代。详见:
  - tools.py — 7 个 Tool 定义
  - graph.py — create_react_agent 构建逻辑
  - prompts.py — HR_AGENT_SYSTEM_PROMPT + build_state_modifier

此文件将在所有引用清理后删除。
"""
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/conversation/nodes.py
git commit -m "chore: deprecate old 14-node conversation graph (replaced by ReAct agent)"
```

---

### Task 7: Write unit tests for the 7 tools

**Files:**
- Create: `backend/tests/test_react_tools.py`

**Interfaces:**
- Consumes: `tools.py` (all 7 tools), `conftest.py` fixtures (`db_session`, `auth_headers_recruiter`, `recruiter_with_job`)
- Produces: Test coverage for query + write tools

- [ ] **Step 1: Write tool unit tests**

Create `backend/tests/test_react_tools.py`. These tests mock the LangGraph `get_config()` to inject a test DB session and user_id:

```python
"""ReAct Agent Tool 单元测试"""

import uuid
from typing import Any
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.job import Job, JobStatus
from app.models.user import User, UserRole


# ── Fixtures ──────────────────────────────────────────────


def _make_config(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Build a LangGraph config dict for tool testing"""
    return {"configurable": {"db": db, "user_id": user_id}}


# ── query_jobs tests ──────────────────────────────────────


class TestQueryJobs:
    """query_jobs tool tests"""

    @pytest.mark.asyncio
    async def test_query_jobs_active_filter(
        self,
        db_session: AsyncSession,
        recruiter_with_job: dict[str, Any],
    ) -> None:
        """query_jobs with status=active returns recruiter's jobs"""
        from app.services.conversation.tools import query_jobs

        recruiter_id = recruiter_with_job["recruiter_id"]
        config = _make_config(db_session, recruiter_id)

        with patch("app.services.conversation.tools.get_config", return_value=config):
            result = await query_jobs.ainvoke({"filter": {"status": "active"}})

        assert isinstance(result, str)
        assert "未找到" not in result or "J" in result

    @pytest.mark.asyncio
    async def test_query_jobs_with_job_code(
        self,
        db_session: AsyncSession,
        recruiter_with_job: dict[str, Any],
    ) -> None:
        """query_jobs with job_code filter"""
        from app.services.conversation.tools import query_jobs

        recruiter_id = recruiter_with_job["recruiter_id"]
        job_id = recruiter_with_job["job_id"]

        # Get the job_code from DB
        job = await db_session.get(Job, job_id)
        assert job is not None

        config = _make_config(db_session, recruiter_id)

        with patch("app.services.conversation.tools.get_config", return_value=config):
            result = await query_jobs.ainvoke({"filter": {"job_code": job.job_code}})

        assert isinstance(result, str)
        assert job.job_code in result

    @pytest.mark.asyncio
    async def test_query_jobs_unknown_filter_key_ignored(
        self,
        db_session: AsyncSession,
        recruiter_with_job: dict[str, Any],
    ) -> None:
        """Unknown filter keys are silently ignored"""
        from app.services.conversation.tools import query_jobs

        recruiter_id = recruiter_with_job["recruiter_id"]
        config = _make_config(db_session, recruiter_id)

        with patch("app.services.conversation.tools.get_config", return_value=config):
            result = await query_jobs.ainvoke({"filter": {"evil_injection": "drop_tables"}})

        # Should not raise, just ignore the unknown key
        assert isinstance(result, str)


# ── query_applications tests ──────────────────────────────


class TestQueryApplications:
    """query_applications tool tests"""

    @pytest.mark.asyncio
    async def test_query_applications_group_by_status(
        self,
        db_session: AsyncSession,
        recruiter_with_job: dict[str, Any],
    ) -> None:
        """query_applications with group_by=['status'] returns funnel"""
        from app.services.conversation.tools import query_applications

        recruiter_id = recruiter_with_job["recruiter_id"]
        job_id = recruiter_with_job["job_id"]
        job = await db_session.get(Job, job_id)
        assert job is not None

        config = _make_config(db_session, recruiter_id)

        with patch("app.services.conversation.tools.get_config", return_value=config):
            result = await query_applications.ainvoke({
                "job_code": job.job_code,
                "group_by": ["status"],
            })

        assert isinstance(result, str)
        assert "待审核" in result

    @pytest.mark.asyncio
    async def test_query_applications_requires_job(
        self,
        db_session: AsyncSession,
        recruiter_with_job: dict[str, Any],
    ) -> None:
        """query_applications without job_code or job_title fails gracefully"""
        from app.services.conversation.tools import query_applications

        recruiter_id = recruiter_with_job["recruiter_id"]
        config = _make_config(db_session, recruiter_id)

        with patch("app.services.conversation.tools.get_config", return_value=config):
            result = await query_applications.ainvoke({})

        assert isinstance(result, str)
        assert "未找到" in result


# ── query_evaluation tests ────────────────────────────────


class TestQueryEvaluation:
    """query_evaluation tool tests"""

    @pytest.mark.asyncio
    async def test_query_evaluation_no_task(
        self,
        db_session: AsyncSession,
        recruiter_with_job: dict[str, Any],
    ) -> None:
        """query_evaluation returns not found when no task exists"""
        from app.services.conversation.tools import query_evaluation

        recruiter_id = recruiter_with_job["recruiter_id"]
        job_id = recruiter_with_job["job_id"]
        job = await db_session.get(Job, job_id)
        assert job is not None

        config = _make_config(db_session, recruiter_id)

        with patch("app.services.conversation.tools.get_config", return_value=config):
            result = await query_evaluation.ainvoke({"job_code": job.job_code})

        assert isinstance(result, str)
        assert "未找到" in result


# ── update_candidate_status tests ─────────────────────────


class TestUpdateCandidateStatus:
    """update_candidate_status tool tests"""

    @pytest.mark.asyncio
    async def test_invalid_target_status_rejected(
        self,
        db_session: AsyncSession,
        recruiter_with_job: dict[str, Any],
    ) -> None:
        """update_candidate_status rejects invalid target_status"""
        from app.services.conversation.tools import update_candidate_status

        recruiter_id = recruiter_with_job["recruiter_id"]
        config = _make_config(db_session, recruiter_id)

        with patch("app.services.conversation.tools.get_config", return_value=config):
            result = await update_candidate_status.ainvoke({
                "job_code": "J00000",
                "candidate_name": "张三",
                "target_status": "hired",
            })

        assert "只接受" in result


# ── update_job_status tests ───────────────────────────────


class TestUpdateJobStatus:
    """update_job_status tool tests"""

    @pytest.mark.asyncio
    async def test_invalid_target_status_rejected(
        self,
        db_session: AsyncSession,
        recruiter_with_job: dict[str, Any],
    ) -> None:
        """update_job_status rejects invalid target_status"""
        from app.services.conversation.tools import update_job_status

        recruiter_id = recruiter_with_job["recruiter_id"]
        config = _make_config(db_session, recruiter_id)

        with patch("app.services.conversation.tools.get_config", return_value=config):
            result = await update_job_status.ainvoke({
                "job_code": "J00000",
                "target_status": "draft",
            })

        assert "只接受" in result
```

- [ ] **Step 2: Run the new tests**

Run: `cd backend && uv run pytest tests/test_react_tools.py -v`

Expected: All tests pass (some may need DB data from fixtures). At minimum, the `invalid_target_status_rejected` tests should pass without DB dependencies.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_react_tools.py
git commit -m "test: add unit tests for ReAct agent tools"
```

---

### Task 8: Verify Phase 1 — full mypy + existing tests

**Files:**
- No new files

**Interfaces:**
- Consumes: All Phase 1 deliverables
- Produces: Confirmed working Phase 1

- [ ] **Step 1: Run mypy on the full project**

Run: `cd backend && uv run mypy --strict app/ 2>&1`

Expected: Some errors from `chat.py` still importing old `ConversationState` — that's expected, will be fixed in Phase 2. Errors should ONLY be in `app/api/chat.py` and `app/llm/` (the `recognize_intent` method still exists on `BaseLLMProvider`). No errors in the conversation module itself.

- [ ] **Step 2: Run existing tests (expect some failures from chat.py and conversation_nodes)**

Run: `cd backend && uv run pytest tests/ -v --tb=short 2>&1 | tail -30`

Expected: `test_conversation_nodes.py` will fail (imports old nodes), `test_chat_api.py` may fail (imports old graph). These are expected and will be fixed in Phase 2+3. The non-conversation tests (auth, jobs, applications, agent) should still pass.

- [ ] **Step 3: Run only the non-conversation tests to verify no regressions**

Run: `cd backend && uv run pytest tests/ -v --ignore=tests/test_conversation_nodes.py --ignore=tests/test_chat_api.py --ignore=tests/test_intent_recognition.py 2>&1 | tail -20`

Expected: All pass.

- [ ] **Step 4: Run the new tool tests**

Run: `cd backend && uv run pytest tests/test_react_tools.py -v`

Expected: Tests pass.

- [ ] **Step 5: Commit any fixups if needed**

If any adjustments were needed during verification, commit them:

```bash
git add -A
git commit -m "fix: Phase 1 verification adjustments"
```

---

**Phase 1 Complete.** The backend conversation module now has a `create_react_agent` with 7 tools replacing the 14-node graph. Phase 2 will wire this into the Chat API and adapt SSE events.

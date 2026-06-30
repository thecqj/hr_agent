# Phase 2: 后端对话图与节点 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 9 个新意图的对话图节点、confirm/cancel 确认流、图路由扩展、SSE 事件适配，使后端完整支持所有新 HR 业务意图的对话交互。

**Architecture:** 在现有 LangGraph 对话图中新增 9 个业务节点 + 1 个 confirm 节点，扩展 route_by_intent 路由到所有新节点。每个节点遵循统一模式：读取 params → 调用 service → 写入 reply_message/reply_cards。操作类意图走 confirm → execute 两步流程。

**Tech Stack:** Python 3.12, LangGraph, SQLAlchemy 2.0, Pydantic v2, pytest + pytest-asyncio

## Global Constraints

- Strict type hints, pass `mypy --strict`
- ConversationState from Phase 1 with `pending_action` field
- IntentResult from Phase 1 with 14 intent Literal
- ChatCard union type from Phase 1 with 6 card types
- All new nodes use `_get_db()` and `_get_llm_provider()` helpers from existing nodes.py
- `current_user_id` is `str` (UUID string)
- `resolve_job()` returns `Job | list[Job] | None` — callers must handle all 3 cases
- PendingAction TypedDict: `{"intent": str, "params": dict}`
- Write operations (status_change, job_status) must go through confirm flow

---

### Task 1: Add Query Intent Nodes (7 nodes)

**Files:**
- Modify: `backend/app/services/conversation/nodes.py`
- Test: `backend/tests/test_conversation_nodes.py`

**Interfaces:**
- Consumes: `ConversationState`, `resolve_job` from `job_service`, `count_by_job_and_status`, `count_by_job_grouped_by_status`, `list_by_job` from `application_service`, `ChatCard` types from `schemas/chat`
- Produces: 7 async node functions: `list_jobs_node`, `job_detail_node`, `pending_count_node`, `interview_count_node`, `candidate_eval_node`, `funnel_node`, `candidate_list_node`; each returns `dict[str, Any]` with `reply_message` and optional `reply_cards`

- [ ] **Step 1: Write failing tests for the 7 query nodes**

Add to `backend/tests/test_conversation_nodes.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.job import Job, JobStatus
from app.models.application import Application, ApplicationStatus
from app.services.conversation.state import ConversationState
from app.services.conversation.nodes import (
    list_jobs_node,
    job_detail_node,
    pending_count_node,
    interview_count_node,
    candidate_eval_node,
    funnel_node,
    candidate_list_node,
)


def _make_job(
    job_code: str = "J04217",
    title: str = "前端开发",
    status: JobStatus = JobStatus.ACTIVE,
) -> MagicMock:
    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.job_code = job_code
    job.title = title
    job.status = status
    job.recruiter_id = uuid.uuid4()
    job.description = "负责前端开发"
    job.requirements = "3年经验"
    job.skills_required = ["React", "TypeScript"]
    job.salary_min = 20000
    job.salary_max = 40000
    job.location = "北京"
    job.work_type = "hybrid"
    job.head_count = 3
    job.interview_quota = 5
    return job


class TestListJobsNode:
    @pytest.mark.asyncio
    async def test_list_active_jobs(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        state: ConversationState = {
            "user_message": "有哪些活跃岗位？",
            "current_user_id": recruiter_id,
            "intent": "list_jobs",
            "extracted_params": {"status_filter": "active"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.list_jobs", new_callable=AsyncMock, return_value=([job], 1)):
            result = await list_jobs_node(state)

        assert "前端开发" in result["reply_message"]
        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "job_list"


class TestJobDetailNode:
    @pytest.mark.asyncio
    async def test_job_detail_full(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217详情",
            "current_user_id": recruiter_id,
            "intent": "job_detail",
            "extracted_params": {"job_code": "J04217", "detail_scope": "full"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job):
            result = await job_detail_node(state)

        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "job_detail"

    @pytest.mark.asyncio
    async def test_job_detail_not_found(self) -> None:
        recruiter_id = str(uuid.uuid4())
        state: ConversationState = {
            "user_message": "J99999详情",
            "current_user_id": recruiter_id,
            "intent": "job_detail",
            "extracted_params": {"job_code": "J99999"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=None):
            result = await job_detail_node(state)

        assert "未找到" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_job_detail_disambiguation(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job1 = _make_job(job_code="J04217", title="前端开发工程师")
        job2 = _make_job(job_code="J04218", title="前端架构师")
        state: ConversationState = {
            "user_message": "前端岗位详情",
            "current_user_id": recruiter_id,
            "intent": "job_detail",
            "extracted_params": {"job_title": "前端"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=[job1, job2]):
            result = await job_detail_node(state)

        assert "多个" in result["reply_message"] or "指定" in result["reply_message"]


class TestPendingCountNode:
    @pytest.mark.asyncio
    async def test_pending_count(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217还有多少简历没看？",
            "current_user_id": recruiter_id,
            "intent": "pending_count",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.count_by_job_and_status", new_callable=AsyncMock, return_value=7):
            result = await pending_count_node(state)

        assert "7" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_pending_count_zero(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217还有多少简历没看？",
            "current_user_id": recruiter_id,
            "intent": "pending_count",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.count_by_job_and_status", new_callable=AsyncMock, return_value=0):
            result = await pending_count_node(state)

        assert "0" in result["reply_message"] or "没有" in result["reply_message"]


class TestInterviewCountNode:
    @pytest.mark.asyncio
    async def test_interview_count(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217有几个人在面试？",
            "current_user_id": recruiter_id,
            "intent": "interview_count",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.count_by_job_and_status", new_callable=AsyncMock, return_value=3):
            result = await interview_count_node(state)

        assert "3" in result["reply_message"]


class TestCandidateEvalNode:
    @pytest.mark.asyncio
    async def test_candidate_eval_found(self) -> None:
        recruiter_id = str(uuid.uuid4())
        mock_app = MagicMock(spec=Application)
        mock_app.ai_score = 85.5
        mock_app.ai_decision = "recommend"
        mock_app.ai_decision_reason = "技术能力强"
        mock_app.ai_evaluation = {"summary": "优秀候选人"}
        mock_app.status = ApplicationStatus.PENDING
        applicant = MagicMock()
        applicant.username = "张三"
        mock_app.applicant = applicant

        state: ConversationState = {
            "user_message": "张三的评估结果",
            "current_user_id": recruiter_id,
            "intent": "candidate_eval",
            "extracted_params": {"candidate_name": "张三", "application_id": "app-123"},
        }

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_app)
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db):
            result = await candidate_eval_node(state)

        assert "85.5" in result["reply_message"] or "推荐" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_candidate_eval_not_found(self) -> None:
        recruiter_id = str(uuid.uuid4())
        state: ConversationState = {
            "user_message": "某某的评估结果",
            "current_user_id": recruiter_id,
            "intent": "candidate_eval",
            "extracted_params": {"candidate_name": "某某", "application_id": "nonexistent"},
        }

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db):
            result = await candidate_eval_node(state)

        assert "未找到" in result["reply_message"]


class TestFunnelNode:
    @pytest.mark.asyncio
    async def test_funnel(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217招聘进度",
            "current_user_id": recruiter_id,
            "intent": "funnel",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        grouped = {"pending": 10, "interview": 3, "rejected": 5}
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.count_by_job_grouped_by_status", new_callable=AsyncMock, return_value=grouped):
            result = await funnel_node(state)

        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "funnel"


class TestCandidateListNode:
    @pytest.mark.asyncio
    async def test_candidate_list(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        mock_app = MagicMock(spec=Application)
        mock_app.ai_score = 85.5
        mock_app.ai_decision = "recommend"
        mock_app.status = ApplicationStatus.PENDING
        applicant = MagicMock()
        applicant.username = "张三"
        mock_app.applicant = applicant

        state: ConversationState = {
            "user_message": "J04217推荐的候选人",
            "current_user_id": recruiter_id,
            "intent": "candidate_list",
            "extracted_params": {"job_code": "J04217", "decision_filter": "recommended"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.list_by_job", new_callable=AsyncMock, return_value=[mock_app]):
            result = await candidate_list_node(state)

        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "candidate_list"

    @pytest.mark.asyncio
    async def test_candidate_list_empty(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217推荐的候选人",
            "current_user_id": recruiter_id,
            "intent": "candidate_list",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.list_by_job", new_callable=AsyncMock, return_value=[]):
            result = await candidate_list_node(state)

        assert "暂无" in result["reply_message"] or "没有" in result["reply_message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py -v -k "list_jobs_node or job_detail_node or pending_count_node or interview_count_node or candidate_eval_node or funnel_node or candidate_list_node"`
Expected: FAIL — import errors for new node functions

- [ ] **Step 3: Implement the 7 query nodes**

Add the following imports at the top of `backend/app/services/conversation/nodes.py` (append to existing imports):

```python
from app.services.job_service import resolve_job, list_jobs as svc_list_jobs
from app.services.application_service import (
    count_by_job_and_status,
    count_by_job_grouped_by_status,
    list_by_job,
)
```

Add the 7 node functions after `dispatch_node` and before `feedback_node`:

```python
# ── 查询类节点 ─────────────────────────────────────────────


async def list_jobs_node(state: ConversationState) -> dict[str, Any]:
    """岗位列表查询节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    status_filter = params.get("status_filter", "active")
    if status_filter == "all":
        status_filter = None  # list_jobs 默认无 status 过滤时查全部活跃

    from app.models.user import User
    user = await db.get(User, uuid.UUID(current_user_id))

    jobs, total = await svc_list_jobs(
        db=db,
        status=status_filter,
        current_user=user,
    )

    if not jobs:
        return {
            "reply_message": f"当前没有{'活跃' if status_filter == 'active' else ''}岗位。",
        }

    job_items = [
        {
            "job_code": j.job_code,
            "title": j.title,
            "status": j.status.value,
            "head_count": j.head_count,
        }
        for j in jobs
    ]

    return {
        "reply_message": f"共 {total} 个岗位：",
        "reply_cards": [{"type": "job_list", "jobs": job_items}],
    }


async def job_detail_node(state: ConversationState) -> dict[str, Any]:
    """岗位详情查询节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")
    detail_scope = params.get("detail_scope", "full")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved

    if detail_scope == "full":
        job_data = {
            "job_code": job.job_code,
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
            "skills_required": job.skills_required or [],
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "location": job.location,
            "work_type": job.work_type.value,
            "head_count": job.head_count,
            "interview_quota": job.interview_quota,
            "status": job.status.value,
        }
        return {
            "reply_message": f"📋 岗位「{job.title}」({job.job_code})详情：",
            "reply_cards": [{"type": "job_detail", "job": job_data}],
        }

    # Scoped detail
    scope_map: dict[str, tuple[str, str]] = {
        "responsibilities": ("岗位职责", job.description),
        "requirements": ("任职要求", job.requirements),
        "skills": ("技能要求", ", ".join(job.skills_required or [])),
        "quota": ("招聘指标", f"编制 {job.head_count} 人，进面名额 {job.interview_quota} 人"),
    }
    label, content = scope_map.get(detail_scope, ("详情", job.description))
    return {"reply_message": f"📋 {job.title}({job.job_code}) — {label}：\n{content}"}


async def pending_count_node(state: ConversationState) -> dict[str, Any]:
    """待审核简历计数节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved
    count = await count_by_job_and_status(db, str(job.id), "pending")

    if count == 0:
        return {"reply_message": f"📋 岗位「{job.title}」({job.job_code})暂无待审核简历。"}
    return {"reply_message": f"📋 岗位「{job.title}」({job.job_code})有 {count} 份待审核简历。"}


async def interview_count_node(state: ConversationState) -> dict[str, Any]:
    """面试中候选人计数节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved
    count = await count_by_job_and_status(db, str(job.id), "interview")

    if count == 0:
        return {"reply_message": f"📋 岗位「{job.title}」({job.job_code})暂无面试中的候选人。"}
    return {"reply_message": f"📋 岗位「{job.title}」({job.job_code})有 {count} 位候选人正在面试中。"}


async def candidate_eval_node(state: ConversationState) -> dict[str, Any]:
    """候选人 AI 评估结果查询节点"""
    db = _get_db()
    params: dict[str, Any] = state.get("extracted_params", {})

    application_id = params.get("application_id")
    candidate_name = params.get("candidate_name", "")

    app: Application | None = None
    if application_id:
        app = await db.get(Application, application_id)

    if not app:
        # 尝试按候选人姓名 + job_code 查找
        job_code = params.get("job_code")
        if job_code:
            job_resolved = await resolve_job(db, state.get("current_user_id", ""), job_code=job_code)
            if job_resolved and not isinstance(job_resolved, list):
                from sqlalchemy import select as sql_select
                from app.models.user import User
                name_stmt = sql_select(Application).join(
                    User, Application.applicant_id == User.id
                ).where(
                    Application.job_id == job_resolved.id,
                    User.username.ilike(f"%{candidate_name}%"),
                ).options(selectinload(Application.applicant))
                app_result = await db.execute(name_stmt)
                apps = list(app_result.scalars().all())
                if len(apps) == 1:
                    app = apps[0]
                elif len(apps) > 1:
                    return {"reply_message": f"找到 {len(apps)} 位名为「{candidate_name}」的候选人，请指定申请 ID。"}

        if not app:
            return {"reply_message": f"❌ 未找到候选人「{candidate_name}」的申请记录。"}

    # Build response
    name = app.applicant.username if app.applicant else candidate_name
    score_str = f"{app.ai_score}" if app.ai_score is not None else "未评估"
    decision_str = {"recommend": "推荐", "reject": "不推荐"}.get(str(app.ai_decision), str(app.ai_decision or "未评估"))
    reason_str = app.ai_decision_reason or "无"
    status_str = {"pending": "待审核", "interview": "面试中", "rejected": "已拒绝"}.get(app.status.value, app.status.value)

    return {
        "reply_message": f"📋 候选人「{name}」评估结果：\n• AI 评分：{score_str}\n• AI 决策：{decision_str}\n• 决策原因：{reason_str}\n• 当前状态：{status_str}",
    }


async def funnel_node(state: ConversationState) -> dict[str, Any]:
    """招聘漏斗/进度概览节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved
    grouped = await count_by_job_grouped_by_status(db, str(job.id))

    total = sum(grouped.values())
    if total == 0:
        return {"reply_message": f"📋 岗位「{job.title}」({job.job_code})暂无投递记录。"}

    stages = []
    status_labels = {"pending": "待审核", "interview": "面试中", "rejected": "已拒绝"}
    for status_key in ["pending", "interview", "rejected"]:
        count = grouped.get(status_key, 0)
        stages.append({
            "status": status_labels.get(status_key, status_key),
            "count": count,
            "percentage": round(count / total * 100, 1),
        })

    return {
        "reply_message": f"📋 岗位「{job.title}」({job.job_code})招聘进度：共收到 {total} 份简历",
        "reply_cards": [{
            "type": "funnel",
            "job_code": job.job_code,
            "job_title": job.title,
            "stages": stages,
        }],
    }


async def candidate_list_node(state: ConversationState) -> dict[str, Any]:
    """候选人列表查询节点"""
    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    job_code = params.get("job_code")
    job_title = params.get("job_title")
    decision_filter = params.get("decision_filter", "recommended")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。"}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}"}

    job = resolved
    apps = await list_by_job(db, str(job.id), decision_filter=decision_filter if decision_filter != "all" else None)

    if not apps:
        filter_label = "AI 推荐" if decision_filter == "recommended" else ""
        return {"reply_message": f"📋 岗位「{job.title}」({job.job_code})暂无{filter_label}候选人。"}

    candidates = [
        {
            "name": a.applicant.username if a.applicant else "未知",
            "ai_score": a.ai_score,
            "ai_decision": a.ai_decision,
            "status": a.status.value,
        }
        for a in apps
    ]

    filter_label = "AI 推荐" if decision_filter == "recommended" else "全部"
    return {
        "reply_message": f"📋 岗位「{job.title}」({job.job_code}){filter_label}候选人 {len(candidates)} 人：",
        "reply_cards": [{
            "type": "candidate_list",
            "job_code": job.job_code,
            "job_title": job.title,
            "candidates": candidates,
        }],
    }
```

Also add the missing import for `selectinload` at the top of nodes.py (it's already imported via the existing `from sqlalchemy.orm import selectinload` — check; if not present, add it).

Add `import uuid` at top of nodes.py if not already there.

- [ ] **Step 4: Run tests for the 7 query nodes**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py -v -k "TestListJobsNode or TestJobDetailNode or TestPendingCountNode or TestInterviewCountNode or TestCandidateEvalNode or TestFunnelNode or TestCandidateListNode"`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/services/conversation/nodes.py tests/test_conversation_nodes.py
git commit -m "feat: add 7 query intent nodes for HR business tasks"
```

---

### Task 2: Add Confirm Flow and Action Nodes

**Files:**
- Modify: `backend/app/services/conversation/nodes.py`
- Test: `backend/tests/test_conversation_nodes.py`

**Interfaces:**
- Consumes: `ConversationState.pending_action` from Phase 1 Task 2; `ApplicationStatus` from models; `update_application_status` from application_service; `update_job_status` from job_service
- Produces: `confirm_node`, `cancel_node`, `status_change_node`, `job_status_action_node` async functions; confirm flow: operation intent → confirm_node (sets pending_action) → user confirms → confirm intent → status_change_node/job_status_action_node → feedback

- [ ] **Step 1: Write failing tests for confirm flow and action nodes**

Add to `backend/tests/test_conversation_nodes.py`:

```python
from app.services.conversation.nodes import (
    confirm_node,
    cancel_node,
    status_change_node,
    job_status_action_node,
)


class TestConfirmNode:
    @pytest.mark.asyncio
    async def test_confirm_sets_pending_action(self) -> None:
        state: ConversationState = {
            "user_message": "把张三推进到面试阶段",
            "current_user_id": str(uuid.uuid4()),
            "intent": "status_change",
            "extracted_params": {"candidate_name": "张三", "target_status": "interview"},
        }

        with patch("app.services.conversation.nodes.adispatch_custom_event", new_callable=AsyncMock):
            result = await confirm_node(state)

        assert result.get("pending_action") is not None
        assert result["pending_action"]["intent"] == "status_change"
        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "confirm"

    @pytest.mark.asyncio
    async def test_confirm_for_job_status(self) -> None:
        state: ConversationState = {
            "user_message": "关闭J04217",
            "current_user_id": str(uuid.uuid4()),
            "intent": "job_status",
            "extracted_params": {"job_code": "J04217", "action": "close"},
        }

        with patch("app.services.conversation.nodes.adispatch_custom_event", new_callable=AsyncMock):
            result = await confirm_node(state)

        assert result.get("pending_action") is not None
        assert result["pending_action"]["intent"] == "job_status"


class TestCancelNode:
    @pytest.mark.asyncio
    async def test_cancel_clears_pending_action(self) -> None:
        state: ConversationState = {
            "user_message": "取消",
            "current_user_id": str(uuid.uuid4()),
            "intent": "cancel",
            "pending_action": {"intent": "status_change", "params": {"candidate_name": "张三", "target_status": "interview"}},
        }

        result = await cancel_node(state)
        assert result.get("pending_action") is None
        assert "取消" in result["reply_message"]


class TestStatusChangeNode:
    @pytest.mark.asyncio
    async def test_status_change_executes(self) -> None:
        recruiter_id = str(uuid.uuid4())
        mock_app = MagicMock(spec=Application)
        mock_app.id = uuid.uuid4()
        mock_app.status = ApplicationStatus.INTERVIEW
        applicant = MagicMock()
        applicant.username = "张三"
        mock_app.applicant = applicant

        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": recruiter_id,
            "intent": "confirm",
            "pending_action": {
                "intent": "status_change",
                "params": {"application_id": str(mock_app.id), "target_status": "interview"},
            },
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.update_application_status", new_callable=AsyncMock, return_value=mock_app):
            result = await status_change_node(state)

        assert "面试" in result["reply_message"]


class TestJobStatusActionNode:
    @pytest.mark.asyncio
    async def test_job_close(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        job.status = JobStatus.CLOSED

        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": recruiter_id,
            "intent": "confirm",
            "pending_action": {
                "intent": "job_status",
                "params": {"job_code": "J04217", "action": "close"},
            },
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.update_job_status", new_callable=AsyncMock, return_value=job):
            result = await job_status_action_node(state)

        assert "关闭" in result["reply_message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py -v -k "TestConfirmNode or TestCancelNode or TestStatusChangeNode or TestJobStatusActionNode"`
Expected: FAIL — import errors

- [ ] **Step 3: Implement confirm_node, cancel_node, status_change_node, job_status_action_node**

Add to `backend/app/services/conversation/nodes.py` after the query nodes:

```python
# ── 操作确认节点 ─────────────────────────────────────────────


async def confirm_node(state: ConversationState) -> dict[str, Any]:
    """操作确认节点：生成确认消息，保存待执行操作"""
    intent = state.get("intent", "")
    params: dict[str, Any] = state.get("extracted_params", {})

    if intent == "status_change":
        name = params.get("candidate_name", "")
        target = params.get("target_status", "")
        target_label = {"interview": "面试阶段", "rejected": "已拒绝"}.get(target, target)
        action_text = f"将候选人「{name}」推进到{target_label}"
    elif intent == "job_status":
        job_code = params.get("job_code", "")
        action = params.get("action", "")
        action_label = {"open": "发布", "close": "关闭"}.get(action, action)
        action_text = f"{action_label}岗位 {job_code}"
    else:
        action_text = "执行操作"

    return {
        "reply_message": f"⚠️ 请确认：{action_text}？\n回复「确认」执行，「取消」放弃。",
        "reply_cards": [{
            "type": "confirm",
            "action": action_text,
            "params": params,
        }],
        "pending_action": {"intent": intent, "params": params},
    }


async def cancel_node(state: ConversationState) -> dict[str, Any]:
    """取消操作节点"""
    return {
        "reply_message": "✅ 已取消操作。",
        "pending_action": None,
    }


async def status_change_node(state: ConversationState) -> dict[str, Any]:
    """候选人状态变更执行节点"""
    from app.schemas.application import ApplicationStatusUpdateRequest
    from app.services.application_service import update_application_status
    from app.models.user import User

    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    pending: dict[str, Any] = state.get("pending_action", {}) or {}
    params: dict[str, Any] = pending.get("params", {})

    application_id = params.get("application_id")
    target_status = params.get("target_status", "interview")
    candidate_name = params.get("candidate_name", "")

    if not application_id:
        return {
            "reply_message": f"❌ 缺少申请 ID，无法变更候选人「{candidate_name}」的状态。",
            "pending_action": None,
        }

    user = await db.get(User, uuid.UUID(current_user_id))
    status_update = ApplicationStatusUpdateRequest(status=ApplicationStatus(target_status))

    try:
        app = await update_application_status(db, application_id, status_update, user)
        status_labels = {"interview": "面试中", "rejected": "已拒绝"}
        return {
            "reply_message": f"✅ 候选人「{candidate_name}」已推进到{status_labels.get(target_status, target_status)}。",
            "pending_action": None,
        }
    except Exception as exc:
        return {
            "reply_message": f"❌ 状态变更失败：{exc}",
            "pending_action": None,
            "errors": [f"status_change failed: {exc}"],
        }


async def job_status_action_node(state: ConversationState) -> dict[str, Any]:
    """岗位发布/关闭执行节点"""
    from app.schemas.job import JobStatusUpdateRequest
    from app.services.job_service import update_job_status
    from app.models.user import User

    db = _get_db()
    current_user_id = state.get("current_user_id", "")
    pending: dict[str, Any] = state.get("pending_action", {}) or {}
    params: dict[str, Any] = pending.get("params", {})

    job_code = params.get("job_code")
    job_title_keyword = params.get("job_title")
    action = params.get("action", "close")

    resolved = await resolve_job(db, current_user_id, job_code=job_code, job_title_keyword=job_title_keyword)

    if resolved is None:
        return {"reply_message": "❌ 未找到匹配的岗位。", "pending_action": None}

    if isinstance(resolved, list):
        job_list = "\n".join(f"  {j.job_code} - {j.title}" for j in resolved)
        return {"reply_message": f"找到多个匹配的岗位，请指定岗位编号：\n{job_list}", "pending_action": None}

    job = resolved
    user = await db.get(User, uuid.UUID(current_user_id))

    new_status = JobStatus.ACTIVE if action == "open" else JobStatus.CLOSED
    status_update = JobStatusUpdateRequest(status=new_status)

    try:
        updated_job = await update_job_status(db, str(job.id), status_update, user)
        action_labels = {"open": "已发布", "close": "已关闭"}
        return {
            "reply_message": f"✅ 岗位「{updated_job.title}」({updated_job.job_code}){action_labels.get(action, action)}。",
            "pending_action": None,
        }
    except Exception as exc:
        return {
            "reply_message": f"❌ 操作失败：{exc}",
            "pending_action": None,
            "errors": [f"job_status_action failed: {exc}"],
        }
```

- [ ] **Step 4: Run tests for confirm flow**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py -v -k "TestConfirmNode or TestCancelNode or TestStatusChangeNode or TestJobStatusActionNode"`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/services/conversation/nodes.py tests/test_conversation_nodes.py
git commit -m "feat: add confirm flow and action nodes for status_change and job_status"
```

---

### Task 3: Update feedback_node for All Intents

**Files:**
- Modify: `backend/app/services/conversation/nodes.py` (feedback_node function)
- Test: `backend/tests/test_conversation_nodes.py`

**Interfaces:**
- Consumes: All node outputs from Task 1 and Task 2; `ConversationState.pending_action`
- Produces: Updated `feedback_node` that handles all 14 intents and the pending_action edge case (user sends new intent while pending_action is set)

- [ ] **Step 1: Write failing test for new intent feedback**

Add to `backend/tests/test_conversation_nodes.py`:

```python
class TestFeedbackNodeExtended:
    @pytest.mark.asyncio
    async def test_list_jobs_feedback(self) -> None:
        """list_jobs 已在节点中设置 reply_message，feedback 不覆盖"""
        state: ConversationState = {
            "user_message": "有哪些岗位？",
            "current_user_id": "u1",
            "intent": "list_jobs",
            "reply_message": "共 3 个岗位：",
            "reply_cards": [{"type": "job_list", "jobs": []}],
        }
        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_pending_action_cleared_on_new_intent(self) -> None:
        """当 pending_action 存在但用户发出新意图时，feedback 应附加提示"""
        state: ConversationState = {
            "user_message": "有哪些岗位？",
            "current_user_id": "u1",
            "intent": "list_jobs",
            "pending_action": {"intent": "status_change", "params": {}},
            "reply_message": "共 3 个岗位：",
        }
        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)
        # Should not override reply_message but should clear pending_action
        assert result.get("pending_action") is None

    @pytest.mark.asyncio
    async def test_help_feedback_updated(self) -> None:
        """help 意图的反馈应包含所有新功能"""
        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "u1",
            "intent": "help",
        }
        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)
        assert "岗位" in result["reply_message"]
        assert "候选人" in result["reply_message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py::TestFeedbackNodeExtended -v`
Expected: FAIL — help feedback doesn't mention new features, pending_action not cleared

- [ ] **Step 3: Update feedback_node**

Replace the `feedback_node` function in `backend/app/services/conversation/nodes.py`:

```python
async def feedback_node(state: ConversationState) -> dict[str, Any]:
    """结果反馈节点：格式化结果摘要"""
    db = _get_db()
    intent = state.get("intent", "unknown")

    # 如果节点已设置了 reply_message，直接使用
    if state.get("reply_message"):
        result: dict[str, Any] = {}
        # 边界情况：pending_action 存在但用户发出新意图 → 隐式取消
        if state.get("pending_action") and intent not in ("confirm", "cancel", "status_change", "job_status"):
            result["pending_action"] = None
            # 附加取消提示
            existing_msg = state["reply_message"]
            result["reply_message"] = existing_msg + "\n（已取消待确认操作）"
        return result

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
            "reply_message": (
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
            ),
        }

    # cancel 意图（无 pending_action 时的兜底）
    if intent == "cancel":
        return {"reply_message": "✅ 已取消。"}

    # unknown 意图
    clarifying = state.get("clarifying_question")
    return {
        "reply_message": clarifying or "抱歉，我没有理解您的意思。输入「帮助」查看我能做什么。",
    }
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py::TestFeedbackNodeExtended -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/services/conversation/nodes.py tests/test_conversation_nodes.py
git commit -m "feat: update feedback_node for all 14 intents with pending_action edge case"
```

---

### Task 4: Update Graph Routing and Build

**Files:**
- Modify: `backend/app/services/conversation/graph.py`
- Modify: `backend/app/services/conversation/nodes.py` (route_by_intent function)
- Test: `backend/tests/test_conversation_nodes.py`

**Interfaces:**
- Consumes: All node functions from Task 1 and Task 2
- Produces: `build_conversation_graph` with expanded routing; `route_by_intent` returns node name strings for all 14 intents

- [ ] **Step 1: Write failing tests for new route mappings**

Add to `backend/tests/test_conversation_nodes.py` in `TestRouteByIntent`:

```python
def test_list_jobs_routes_to_list_jobs(self) -> None:
    state: ConversationState = {"intent": "list_jobs"}
    assert route_by_intent(state) == "list_jobs"

def test_job_detail_routes_to_job_detail(self) -> None:
    state: ConversationState = {"intent": "job_detail"}
    assert route_by_intent(state) == "job_detail"

def test_pending_count_routes_to_pending_count(self) -> None:
    state: ConversationState = {"intent": "pending_count"}
    assert route_by_intent(state) == "pending_count"

def test_interview_count_routes_to_interview_count(self) -> None:
    state: ConversationState = {"intent": "interview_count"}
    assert route_by_intent(state) == "interview_count"

def test_candidate_eval_routes_to_candidate_eval(self) -> None:
    state: ConversationState = {"intent": "candidate_eval"}
    assert route_by_intent(state) == "candidate_eval"

def test_funnel_routes_to_funnel(self) -> None:
    state: ConversationState = {"intent": "funnel"}
    assert route_by_intent(state) == "funnel"

def test_candidate_list_routes_to_candidate_list(self) -> None:
    state: ConversationState = {"intent": "candidate_list"}
    assert route_by_intent(state) == "candidate_list"

def test_status_change_routes_to_confirm(self) -> None:
    state: ConversationState = {"intent": "status_change"}
    assert route_by_intent(state) == "confirm"

def test_job_status_routes_to_confirm(self) -> None:
    state: ConversationState = {"intent": "job_status"}
    assert route_by_intent(state) == "confirm"

def test_confirm_routes_to_execute(self) -> None:
    state: ConversationState = {"intent": "confirm", "pending_action": {"intent": "status_change", "params": {}}}
    assert route_by_intent(state) == "execute_action"

def test_confirm_without_pending_routes_to_feedback(self) -> None:
    state: ConversationState = {"intent": "confirm"}
    assert route_by_intent(state) == "feedback"

def test_cancel_routes_to_cancel(self) -> None:
    state: ConversationState = {"intent": "cancel"}
    assert route_by_intent(state) == "cancel"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py::TestRouteByIntent -v`
Expected: FAIL — new intent values not handled in route_by_intent

- [ ] **Step 3: Update route_by_intent**

Replace the `route_by_intent` function in `backend/app/services/conversation/nodes.py`:

```python
# 查询类意图，直接路由到对应节点
_QUERY_INTENTS = frozenset({
    "list_jobs",
    "job_detail",
    "pending_count",
    "interview_count",
    "candidate_eval",
    "funnel",
    "candidate_list",
})

# 操作类意图，需要先确认
_CONFIRM_REQUIRED_INTENTS = frozenset({
    "status_change",
    "job_status",
})


def route_by_intent(state: ConversationState) -> str:
    """条件路由：根据意图决定下一个节点"""
    intent = state.get("intent", "unknown")

    # 简历评估 → dispatch
    if intent == "evaluate":
        return "dispatch"

    # 查询类意图 → 对应节点名
    if intent in _QUERY_INTENTS:
        return intent

    # 操作类意图 → 确认节点
    if intent in _CONFIRM_REQUIRED_INTENTS:
        return "confirm"

    # 用户确认 → 执行节点（若有待确认操作）或反馈
    if intent == "confirm":
        pending = state.get("pending_action")
        if pending:
            return "execute_action"
        return "feedback"

    # 用户取消 → 取消节点
    if intent == "cancel":
        return "cancel"

    # help / unknown → 反馈
    return "feedback"


def route_by_pending_action(state: ConversationState) -> str:
    """根据 pending_action 的 intent 类型路由到具体执行节点"""
    pending: dict[str, Any] = state.get("pending_action") or {}
    action_intent = pending.get("intent", "")

    if action_intent == "status_change":
        return "status_change"
    elif action_intent == "job_status":
        return "job_status_action"
    return "feedback"
```

- [ ] **Step 4: Update graph.py**

Replace `backend/app/services/conversation/graph.py`:

```python
"""对话 Agent LangGraph 图定义"""

from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.services.conversation.state import ConversationState
from app.services.conversation.nodes import (
    intent_node,
    dispatch_node,
    feedback_node,
    route_by_intent,
    route_by_pending_action,
    list_jobs_node,
    job_detail_node,
    pending_count_node,
    interview_count_node,
    candidate_eval_node,
    funnel_node,
    candidate_list_node,
    confirm_node,
    cancel_node,
    status_change_node,
    job_status_action_node,
)


def build_conversation_graph(checkpointer: AsyncPostgresSaver) -> CompiledStateGraph:  # type: ignore[type-arg]
    """构建对话工作流图并编译

    流程：
    START → intent → route_by_intent →
      evaluate?       → dispatch → feedback → END
      <query_intent>? → <query_node> → feedback → END
      status_change / job_status? → confirm → feedback → END
      confirm? → execute_action → route_by_pending_action →
        status_change? → status_change → feedback → END
        job_status?    → job_status_action → feedback → END
      cancel? → cancel → feedback → END
      help/unknown? → feedback → END
    """
    graph = StateGraph(ConversationState)

    # ── 添加节点 ──────────────────────────────────────────
    graph.add_node("intent", intent_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("feedback", feedback_node)

    # 查询类节点
    graph.add_node("list_jobs", list_jobs_node)
    graph.add_node("job_detail", job_detail_node)
    graph.add_node("pending_count", pending_count_node)
    graph.add_node("interview_count", interview_count_node)
    graph.add_node("candidate_eval", candidate_eval_node)
    graph.add_node("funnel", funnel_node)
    graph.add_node("candidate_list", candidate_list_node)

    # 操作确认节点
    graph.add_node("confirm", confirm_node)
    graph.add_node("cancel", cancel_node)
    graph.add_node("execute_action", _noop_passthrough)
    graph.add_node("status_change", status_change_node)
    graph.add_node("job_status_action", job_status_action_node)

    # ── 设置入口 ──────────────────────────────────────────
    graph.add_edge(START, "intent")

    # ── 条件路由：intent → 各节点 ─────────────────────────
    intent_routes = {
        "dispatch": "dispatch",
        "feedback": "feedback",
        # 查询类
        "list_jobs": "list_jobs",
        "job_detail": "job_detail",
        "pending_count": "pending_count",
        "interview_count": "interview_count",
        "candidate_eval": "candidate_eval",
        "funnel": "funnel",
        "candidate_list": "candidate_list",
        # 操作确认
        "confirm": "confirm",
        "cancel": "cancel",
    }
    graph.add_conditional_edges("intent", route_by_intent, intent_routes)

    # ── 查询类节点 → feedback ────────────────────────────
    for node_name in [
        "list_jobs", "job_detail", "pending_count", "interview_count",
        "candidate_eval", "funnel", "candidate_list",
    ]:
        graph.add_edge(node_name, "feedback")

    # ── dispatch → feedback ───────────────────────────────
    graph.add_edge("dispatch", "feedback")

    # ── 确认节点 → feedback ──────────────────────────────
    graph.add_edge("confirm", "feedback")

    # ── 取消节点 → feedback ──────────────────────────────
    graph.add_edge("cancel", "feedback")

    # ── 用户确认 → execute_action → 按类型路由 ──────────
    graph.add_conditional_edges(
        "execute_action",
        route_by_pending_action,
        {
            "status_change": "status_change",
            "job_status_action": "job_status_action",
            "feedback": "feedback",
        },
    )

    # ── 操作执行节点 → feedback ──────────────────────────
    graph.add_edge("status_change", "feedback")
    graph.add_edge("job_status_action", "feedback")

    # ── feedback → END ───────────────────────────────────
    graph.add_edge("feedback", END)

    return graph.compile(checkpointer=checkpointer)


async def _noop_passthrough(state: ConversationState) -> dict[str, Any]:
    """空透传节点：用于 execute_action 路由中间层，不修改状态"""
    return {}
```

- [ ] **Step 5: Run route tests**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py::TestRouteByIntent -v`
Expected: ALL PASS

- [ ] **Step 6: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 7: Run mypy**

Run: `cd backend && uv run mypy --strict app/`
Expected: No errors

- [ ] **Step 8: Commit**

```bash
cd backend
git add app/services/conversation/nodes.py app/services/conversation/graph.py tests/test_conversation_nodes.py
git commit -m "feat: expand conversation graph with 9 new intent routes and confirm flow"
```

---

### Task 5: Update SSE Chat API for New Card Types

**Files:**
- Modify: `backend/app/api/chat.py`
- Test: `backend/tests/test_chat_api.py` (new file)

**Interfaces:**
- Consumes: `ChatCard` union type from Phase 1; new card types serialized via Pydantic
- Produces: SSE `result` event with `cards` field containing any of the 6 card types (properly serialized)

- [ ] **Step 1: Write test for card serialization in SSE result**

Create `backend/tests/test_chat_api.py`:

```python
"""Chat API SSE 序列化测试"""

import json

from app.schemas.chat import (
    JobListCard,
    JobDetailCard,
    FunnelCard,
    FunnelStage,
    CandidateListCard,
    CandidateItem,
    ConfirmCard,
    ResultEvent,
)


class TestCardSerialization:
    def test_job_list_card_serialization(self) -> None:
        card = JobListCard(jobs=[{"job_code": "J04217", "title": "前端", "status": "active", "head_count": 3}])
        event = ResultEvent(reply_message="岗位列表", cards=[card])
        data = json.loads(event.model_dump_json())
        assert data["cards"][0]["type"] == "job_list"

    def test_funnel_card_serialization(self) -> None:
        card = FunnelCard(
            job_code="J04217",
            job_title="前端",
            stages=[FunnelStage(status="待审核", count=10, percentage=50.0)],
        )
        event = ResultEvent(reply_message="漏斗", cards=[card])
        data = json.loads(event.model_dump_json())
        assert data["cards"][0]["type"] == "funnel"

    def test_confirm_card_serialization(self) -> None:
        card = ConfirmCard(action="确认操作", params={"key": "value"})
        event = ResultEvent(reply_message="请确认", cards=[card])
        data = json.loads(event.model_dump_json())
        assert data["cards"][0]["type"] == "confirm"
```

- [ ] **Step 2: Run test to verify it passes (serialization should already work)**

Run: `cd backend && uv run pytest tests/test_chat_api.py -v`
Expected: ALL PASS (Pydantic v2 handles union serialization automatically)

- [ ] **Step 3: Update chat.py to use model_dump for cards**

The key change in `backend/app/api/chat.py` is ensuring `reply_cards` are properly serialized. Update the result event section:

Replace the result generation block in `_run_conversation_stream` (around line 92-99):

```python
            if final_state.get("reply_message"):
                result_data: dict[str, object] = {
                    "reply_message": final_state["reply_message"],
                }
                if final_state.get("reply_cards"):
                    # reply_cards are already plain dicts from nodes, serialize directly
                    result_data["cards"] = final_state["reply_cards"]

                yield f"event: result\ndata: {json.dumps(result_data, ensure_ascii=False)}\n\n"
```

This is actually unchanged — `reply_cards` from nodes are already plain dicts. The test confirms serialization works.

- [ ] **Step 4: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/api/chat.py tests/test_chat_api.py
git commit -m "test: add SSE card serialization tests for new card types"
```

---

### Task 6: Update intent_node for pending_action Edge Case

**Files:**
- Modify: `backend/app/services/conversation/nodes.py` (intent_node function)
- Test: `backend/tests/test_conversation_nodes.py`

**Interfaces:**
- Consumes: `ConversationState.pending_action`
- Produces: When `pending_action` exists and user input is not confirm/cancel, the intent_node should pass through but the feedback_node will handle the implicit cancel (already done in Task 3). No changes needed in intent_node itself — the edge case is handled in feedback_node.

- [ ] **Step 1: Verify the edge case is already handled**

The `intent_node` always classifies the user's message. If `pending_action` exists and the classified intent is not `confirm`/`cancel`, the `feedback_node` (updated in Task 3) detects this and clears `pending_action` with an additional message. This is already working.

Write a test to confirm:

```python
class TestPendingActionEdgeCase:
    @pytest.mark.asyncio
    async def test_new_intent_clears_pending_action(self) -> None:
        """用户有待确认操作时发出新意图，应隐式取消"""
        state: ConversationState = {
            "user_message": "有哪些岗位？",
            "current_user_id": "u1",
            "intent": "list_jobs",
            "extracted_params": {"status_filter": "active"},
            "pending_action": {"intent": "status_change", "params": {"candidate_name": "张三"}},
            "reply_message": "共 2 个岗位：",
        }
        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert result.get("pending_action") is None
        assert "已取消待确认操作" in result.get("reply_message", "")
```

- [ ] **Step 2: Run the test**

Run: `cd backend && uv run pytest tests/test_conversation_nodes.py::TestPendingActionEdgeCase -v`
Expected: ALL PASS (already handled by Task 3's feedback_node update)

- [ ] **Step 3: Commit (test only)**

```bash
cd backend
git add tests/test_conversation_nodes.py
git commit -m "test: add pending_action edge case test for new-intent-during-confirmation"
```

# Phase 1: 后端数据与意图基础 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展意图识别体系和数据服务层，为 9 个新 HR 业务意图提供数据基础和意图识别能力。

**Architecture:** 在现有 IntentResult schema 中扩展 intent 枚举至 14 个值；在 ConversationState 中新增 pending_action 字段；在 application_service 和 job_service 中新增查询方法；重写 INTENT_SYSTEM_PROMPT 覆盖所有新意图。

**Tech Stack:** Python 3.12, Pydantic v2, SQLAlchemy 2.0, pytest + pytest-asyncio

## Global Constraints

- Strict type hints on every function/method, pass `mypy --strict`
- SQLAlchemy 2.0 type-annotated style (`Mapped[str] = mapped_column(...)`)
- Pydantic v2 exclusively for request/response schemas and API boundaries
- Intent enum: `evaluate | list_jobs | job_detail | pending_count | interview_count | candidate_eval | funnel | candidate_list | status_change | job_status | confirm | cancel | help | unknown`
- Application statuses: `pending | interview | rejected | hired` (existing enum)
- Job statuses: `draft | active | closed` (existing enum)
- `current_user_id` in ConversationState is `str` (UUID string)

---

### Task 1: Expand IntentResult Schema

**Files:**
- Modify: `backend/app/schemas/agent.py:44-59`
- Test: `backend/tests/test_intent_recognition.py`

**Interfaces:**
- Consumes: Nothing new
- Produces: `IntentResult` with expanded `intent` Literal accepting all 14 intent values; `extracted_params` dict with new param keys per intent

- [ ] **Step 1: Write failing tests for new intent values**

Add to `backend/tests/test_intent_recognition.py` in `TestIntentResultSchema`:

```python
def test_list_jobs_intent(self) -> None:
    result = IntentResult(
        intent="list_jobs",
        confidence=0.9,
        extracted_params={"status_filter": "active"},
    )
    assert result.intent == "list_jobs"
    assert result.extracted_params["status_filter"] == "active"

def test_job_detail_intent(self) -> None:
    result = IntentResult(
        intent="job_detail",
        confidence=0.88,
        extracted_params={"job_code": "J04217", "detail_scope": "requirements"},
    )
    assert result.intent == "job_detail"

def test_pending_count_intent(self) -> None:
    result = IntentResult(
        intent="pending_count",
        confidence=0.92,
        extracted_params={"job_code": "J04217"},
    )
    assert result.intent == "pending_count"

def test_interview_count_intent(self) -> None:
    result = IntentResult(
        intent="interview_count",
        confidence=0.91,
        extracted_params={"job_title": "前端开发"},
    )
    assert result.intent == "interview_count"

def test_candidate_eval_intent(self) -> None:
    result = IntentResult(
        intent="candidate_eval",
        confidence=0.87,
        extracted_params={"candidate_name": "张三", "job_code": "J04217"},
    )
    assert result.intent == "candidate_eval"

def test_funnel_intent(self) -> None:
    result = IntentResult(
        intent="funnel",
        confidence=0.90,
        extracted_params={"job_code": "J04217"},
    )
    assert result.intent == "funnel"

def test_candidate_list_intent(self) -> None:
    result = IntentResult(
        intent="candidate_list",
        confidence=0.89,
        extracted_params={"job_code": "J04217", "decision_filter": "recommended"},
    )
    assert result.intent == "candidate_list"

def test_status_change_intent(self) -> None:
    result = IntentResult(
        intent="status_change",
        confidence=0.85,
        extracted_params={"candidate_name": "张三", "target_status": "interview"},
    )
    assert result.intent == "status_change"

def test_job_status_intent(self) -> None:
    result = IntentResult(
        intent="job_status",
        confidence=0.93,
        extracted_params={"job_code": "J04217", "action": "close"},
    )
    assert result.intent == "job_status"

def test_confirm_intent(self) -> None:
    result = IntentResult(
        intent="confirm",
        confidence=0.95,
        extracted_params={},
    )
    assert result.intent == "confirm"

def test_cancel_intent(self) -> None:
    result = IntentResult(
        intent="cancel",
        confidence=0.95,
        extracted_params={},
    )
    assert result.intent == "cancel"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_intent_recognition.py::TestIntentResultSchema -v`
Expected: FAIL — `IntentResult` rejects new intent values because Literal only allows `"evaluate" | "help" | "unknown"`

- [ ] **Step 3: Expand IntentResult intent Literal**

In `backend/app/schemas/agent.py`, replace the `IntentResult` class:

```python
class IntentResult(BaseModel):
    """意图识别结果"""

    intent: Literal[
        "evaluate",
        "list_jobs",
        "job_detail",
        "pending_count",
        "interview_count",
        "candidate_eval",
        "funnel",
        "candidate_list",
        "status_change",
        "job_status",
        "confirm",
        "cancel",
        "help",
        "unknown",
    ] = Field(
        ..., description="识别出的意图类型"
    )
    confidence: float = Field(
        ..., ge=0, le=1, description="置信度 0-1"
    )
    extracted_params: dict[str, Any] = Field(
        default_factory=dict,
        description="提取的参数（各意图对应不同参数键）",
    )
    clarifying_question: str | None = Field(
        None, description="置信度低时的追问（仅 unknown 时）"
    )
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_intent_recognition.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run mypy type check**

Run: `cd backend && uv run mypy --strict app/`
Expected: No errors related to IntentResult

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/schemas/agent.py tests/test_intent_recognition.py
git commit -m "feat: expand IntentResult schema with 9 new HR business intents"
```

---

### Task 2: Expand ConversationState with pending_action

**Files:**
- Modify: `backend/app/services/conversation/state.py`
- Test: `backend/tests/test_conversation_state.py` (new file)

**Interfaces:**
- Consumes: Nothing new
- Produces: `ConversationState` with `pending_action: dict[str, Any] | None` field; `PendingAction` TypedDict for type safety inside nodes

- [ ] **Step 1: Write failing test for pending_action field**

Create `backend/tests/test_conversation_state.py`:

```python
"""ConversationState 扩展字段测试"""

from app.services.conversation.state import ConversationState, PendingAction


class TestConversationState:
    def test_pending_action_field_optional(self) -> None:
        state: ConversationState = {"user_message": "test", "current_user_id": "u1"}
        assert state.get("pending_action") is None

    def test_pending_action_field_set(self) -> None:
        action: PendingAction = {
            "intent": "status_change",
            "params": {"candidate_name": "张三", "target_status": "interview"},
        }
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": "u1",
            "pending_action": action,
        }
        assert state["pending_action"]["intent"] == "status_change"

    def test_pending_action_clear(self) -> None:
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": "u1",
            "pending_action": {"intent": "job_status", "params": {"job_code": "J04217", "action": "close"}},
        }
        # Clearing is represented by returning None from a node
        cleared: ConversationState = {**state, "pending_action": None}
        assert cleared["pending_action"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_conversation_state.py -v`
Expected: FAIL — `PendingAction` not imported, `pending_action` not in ConversationState

- [ ] **Step 3: Add pending_action and PendingAction to ConversationState**

Replace `backend/app/services/conversation/state.py`:

```python
"""对话 Agent 状态定义"""

from typing import Any, TypedDict


class PendingAction(TypedDict, total=False):
    """待确认操作的上下文"""

    intent: str                    # 待执行的操作意图
    params: dict[str, Any]         # 操作参数


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
    pending_action: dict[str, Any] | None          # 待确认操作：{"intent": str, "params": dict}

    # 错误
    errors: list[str]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_conversation_state.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS (same 84 tests)

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/services/conversation/state.py tests/test_conversation_state.py
git commit -m "feat: add pending_action field to ConversationState for write-operation confirmation"
```

---

### Task 3: Add Application Service Query Methods

**Files:**
- Modify: `backend/app/services/application_service.py`
- Test: `backend/tests/test_application_service.py` (new file)

**Interfaces:**
- Consumes: `Application`, `ApplicationStatus` from `app.models.application`; `AsyncSession`
- Produces: `count_by_job_and_status(db, job_id, status) -> int`, `count_by_job_grouped_by_status(db, job_id) -> dict[str, int]`, `list_by_job(db, job_id, decision_filter) -> list[Application]`

- [ ] **Step 1: Write failing tests for the three new service methods**

Create `backend/tests/test_application_service.py`:

```python
"""Application Service 新增查询方法测试"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.services.application_service import (
    count_by_job_and_status,
    count_by_job_grouped_by_status,
    list_by_job,
)


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.get = AsyncMock()
    return db


class TestCountByJobAndStatus:
    @pytest.mark.asyncio
    async def test_returns_count_for_specific_status(self, mock_db: AsyncMock) -> None:
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = 5
        mock_db.execute.return_value = mock_scalar

        result = await count_by_job_and_status(mock_db, str(uuid.uuid4()), "pending")
        assert result == 5

    @pytest.mark.asyncio
    async def test_returns_zero_when_none(self, mock_db: AsyncMock) -> None:
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = None
        mock_db.execute.return_value = mock_scalar

        result = await count_by_job_and_status(mock_db, str(uuid.uuid4()), "interview")
        assert result == 0


class TestCountByJobGroupedByStatus:
    @pytest.mark.asyncio
    async def test_returns_grouped_counts(self, mock_db: AsyncMock) -> None:
        mock_db.execute.return_value = [
            MagicMock(**{"__iter__": lambda self: iter([ApplicationStatus.PENDING, 10])}),
            MagicMock(**{"__iter__": lambda self: iter([ApplicationStatus.INTERVIEW, 3])}),
            MagicMock(**{"__iter__": lambda self: iter([ApplicationStatus.REJECTED, 2])}),
        ]

        result = await count_by_job_grouped_by_status(mock_db, str(uuid.uuid4()))
        assert "pending" in result
        assert "interview" in result
        assert "rejected" in result


class TestListByJob:
    @pytest.mark.asyncio
    async def test_returns_applications_without_filter(self, mock_db: AsyncMock) -> None:
        mock_app = MagicMock(spec=Application)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_app]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await list_by_job(mock_db, str(uuid.uuid4()))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self, mock_db: AsyncMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await list_by_job(mock_db, str(uuid.uuid4()), decision_filter="recommended")
        assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_application_service.py -v`
Expected: FAIL — `cannot import name 'count_by_job_and_status'`

- [ ] **Step 3: Implement the three new methods**

Add to the end of `backend/app/services/application_service.py`:

```python
async def count_by_job_and_status(
    db: AsyncSession,
    job_id: str,
    status: str,
) -> int:
    """统计某岗位指定状态的申请数量"""
    try:
        app_status = ApplicationStatus(status)
    except ValueError:
        return 0

    stmt = select(func.count()).select_from(Application).where(
        Application.job_id == job_id,
        Application.status == app_status,
    )
    result = (await db.execute(stmt)).scalar()
    return result or 0


async def count_by_job_grouped_by_status(
    db: AsyncSession,
    job_id: str,
) -> dict[str, int]:
    """按状态分组统计某岗位的申请数量"""
    stmt = (
        select(Application.status, func.count())
        .where(Application.job_id == job_id)
        .group_by(Application.status)
    )
    rows = (await db.execute(stmt)).all()
    return {row[0].value: row[1] for row in rows}


async def list_by_job(
    db: AsyncSession,
    job_id: str,
    decision_filter: str | None = None,
) -> list[Application]:
    """列出某岗位的申请，可选按 AI decision 过滤"""
    stmt = (
        select(Application)
        .where(Application.job_id == job_id)
        .options(selectinload(Application.applicant))
    )

    if decision_filter:
        stmt = stmt.where(Application.ai_decision == decision_filter)

    stmt = stmt.order_by(Application.ai_score.desc().nullslast(), Application.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

Also ensure the import of `func` and `select` are present at the top (they already are).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_application_service.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Run mypy**

Run: `cd backend && uv run mypy --strict app/`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/services/application_service.py tests/test_application_service.py
git commit -m "feat: add application query methods for conversation nodes"
```

---

### Task 4: Add Job Service resolve_job Helper

**Files:**
- Modify: `backend/app/services/job_service.py`
- Test: `backend/tests/test_job_service_resolve.py` (new file)

**Interfaces:**
- Consumes: `Job`, `JobStatus` from `app.models.job`; `AsyncSession`; `uuid.UUID`
- Produces: `resolve_job(db, recruiter_id, job_code, job_title_keyword) -> Job | list[Job] | None`

- [ ] **Step 1: Write failing test for resolve_job**

Create `backend/tests/test_job_service_resolve.py`:

```python
"""Job Service resolve_job 辅助方法测试"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job_service import resolve_job


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    return db


class TestResolveJob:
    @pytest.mark.asyncio
    async def test_exact_match_by_job_code(self, mock_db: AsyncMock) -> None:
        mock_job = MagicMock()
        mock_job.recruiter_id = uuid.uuid4()
        mock_job.job_code = "J04217"
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_scalar

        result = await resolve_job(mock_db, str(mock_job.recruiter_id), job_code="J04217")
        assert result == mock_job

    @pytest.mark.asyncio
    async def test_fuzzy_match_by_title_single_result(self, mock_db: AsyncMock) -> None:
        recruiter_id = uuid.uuid4()
        mock_job = MagicMock()
        mock_job.recruiter_id = recruiter_id
        mock_job.title = "前端开发工程师"
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_job]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await resolve_job(mock_db, str(recruiter_id), job_title_keyword="前端")
        assert result == mock_job

    @pytest.mark.asyncio
    async def test_fuzzy_match_multiple_results(self, mock_db: AsyncMock) -> None:
        recruiter_id = uuid.uuid4()
        mock_job1 = MagicMock()
        mock_job1.recruiter_id = recruiter_id
        mock_job2 = MagicMock()
        mock_job2.recruiter_id = recruiter_id
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_job1, mock_job2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await resolve_job(mock_db, str(recruiter_id), job_title_keyword="开发")
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_no_match_returns_none(self, mock_db: AsyncMock) -> None:
        recruiter_id = uuid.uuid4()
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_scalar

        # job_code path
        result = await resolve_job(mock_db, str(recruiter_id), job_code="J99999")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_params_returns_none(self, mock_db: AsyncMock) -> None:
        recruiter_id = uuid.uuid4()
        result = await resolve_job(mock_db, str(recruiter_id))
        assert result is None

    @pytest.mark.asyncio
    async def test_job_code_wrong_recruiter_returns_none(self, mock_db: AsyncMock) -> None:
        mock_job = MagicMock()
        mock_job.recruiter_id = uuid.uuid4()  # different recruiter
        mock_job.job_code = "J04217"
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_scalar

        result = await resolve_job(mock_db, str(uuid.uuid4()), job_code="J04217")
        assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_job_service_resolve.py -v`
Expected: FAIL — `cannot import name 'resolve_job'`

- [ ] **Step 3: Implement resolve_job**

Add to the end of `backend/app/services/job_service.py`:

```python
async def resolve_job(
    db: AsyncSession,
    recruiter_id: str,
    job_code: str | None = None,
    job_title_keyword: str | None = None,
) -> Job | list[Job] | None:
    """精确匹配 job_code，或模糊匹配 job_title。

    Args:
        db: 数据库会话
        recruiter_id: 招聘者 ID (UUID 字符串)
        job_code: 岗位编号（优先级最高，精确匹配）
        job_title_keyword: 岗位名称关键词（模糊匹配）

    Returns:
        单个 Job（精确匹配或唯一模糊匹配）
        list[Job]（模糊匹配多个，需消歧）
        None（未找到）
    """
    # Priority 1: job_code exact match
    if job_code:
        result = await db.execute(
            select(Job).where(Job.job_code == job_code)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None
        if str(job.recruiter_id) != recruiter_id:
            return None
        return job

    # Priority 2: job_title fuzzy match
    if job_title_keyword:
        escaped_keyword = job_title_keyword.lower().replace("%", "\\%").replace("_", "\\_")
        stmt = select(Job).where(
            Job.recruiter_id == uuid.UUID(recruiter_id),
            Job.status == JobStatus.ACTIVE,
            func.lower(Job.title).ilike(f"%{escaped_keyword}%", escape="\\"),
        )
        matching_jobs = list((await db.execute(stmt)).scalars().all())

        if len(matching_jobs) == 0:
            return None
        elif len(matching_jobs) == 1:
            return matching_jobs[0]
        else:
            return matching_jobs

    return None
```

Ensure `uuid` is imported at the top of the file (add `import uuid` if not present).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_job_service_resolve.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Run mypy**

Run: `cd backend && uv run mypy --strict app/`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/services/job_service.py tests/test_job_service_resolve.py
git commit -m "feat: add resolve_job helper for conversation node job resolution"
```

---

### Task 5: Rewrite INTENT_SYSTEM_PROMPT for 14 Intents

**Files:**
- Modify: `backend/app/services/conversation/prompts.py`
- Test: `backend/tests/test_intent_recognition.py` (add provider-level tests)

**Interfaces:**
- Consumes: `IntentResult` expanded schema (from Task 1)
- Produces: `INTENT_SYSTEM_PROMPT` covering all 14 intents with parameter extraction rules; `build_intent_user_prompt` unchanged

- [ ] **Step 1: Write failing tests for new intent recognition scenarios**

Add to `backend/tests/test_intent_recognition.py` in `TestIntentRecognitionProvider`:

```python
@pytest.mark.asyncio
async def test_recognize_list_jobs_intent(self) -> None:
    """测试识别 list_jobs 意图"""
    from app.llm.deepseek import DeepSeekProvider

    mock_response = {
        "intent": "list_jobs",
        "confidence": 0.9,
        "extracted_params": {"status_filter": "active"},
    }

    provider = DeepSeekProvider()
    with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.recognize_intent("现在有哪些活跃岗位？")
        assert result.intent == "list_jobs"
        assert result.extracted_params.get("status_filter") == "active"
    await provider.close()

@pytest.mark.asyncio
async def test_recognize_job_detail_intent(self) -> None:
    """测试识别 job_detail 意图"""
    from app.llm.deepseek import DeepSeekProvider

    mock_response = {
        "intent": "job_detail",
        "confidence": 0.88,
        "extracted_params": {"job_code": "J04217", "detail_scope": "requirements"},
    }

    provider = DeepSeekProvider()
    with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.recognize_intent("J04217的任职要求是什么？")
        assert result.intent == "job_detail"
    await provider.close()

@pytest.mark.asyncio
async def test_recognize_status_change_intent(self) -> None:
    """测试识别 status_change 意图"""
    from app.llm.deepseek import DeepSeekProvider

    mock_response = {
        "intent": "status_change",
        "confidence": 0.85,
        "extracted_params": {"candidate_name": "张三", "target_status": "interview"},
    }

    provider = DeepSeekProvider()
    with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.recognize_intent("把张三推进到面试阶段")
        assert result.intent == "status_change"
    await provider.close()

@pytest.mark.asyncio
async def test_recognize_confirm_intent(self) -> None:
    """测试识别 confirm 意图"""
    from app.llm.deepseek import DeepSeekProvider

    mock_response = {
        "intent": "confirm",
        "confidence": 0.95,
        "extracted_params": {},
    }

    provider = DeepSeekProvider()
    with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.recognize_intent("确认")
        assert result.intent == "confirm"
    await provider.close()

@pytest.mark.asyncio
async def test_recognize_cancel_intent(self) -> None:
    """测试识别 cancel 意图"""
    from app.llm.deepseek import DeepSeekProvider

    mock_response = {
        "intent": "cancel",
        "confidence": 0.95,
        "extracted_params": {},
    }

    provider = DeepSeekProvider()
    with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.recognize_intent("取消")
        assert result.intent == "cancel"
    await provider.close()
```

- [ ] **Step 2: Run tests to verify they pass (they should — mock-based)**

Run: `cd backend && uv run pytest tests/test_intent_recognition.py -v`
Expected: ALL PASS (these are mock-based; the real prompt hasn't changed yet but the schema accepts the new intents)

- [ ] **Step 3: Rewrite INTENT_SYSTEM_PROMPT**

Replace the `INTENT_SYSTEM_PROMPT` in `backend/app/services/conversation/prompts.py`:

```python
INTENT_SYSTEM_PROMPT = """你是一个 HR 招聘助手的意图识别模块。根据用户消息，判断其意图并提取参数。

支持的意图：
1. evaluate - 触发简历评估工作流
   参数：job_code (str, 岗位编号，如 J04217，优先级最高), job_title (str, 岗位名称), job_id (str, 可选), interview_quota (int, 可选)

2. list_jobs - 查询岗位列表
   参数：status_filter (str, "active"|"closed"|"all"，默认 "active")

3. job_detail - 查询岗位详细信息
   参数：job_code (str, 优先), job_title (str), detail_scope (str, "full"|"responsibilities"|"requirements"|"skills"|"quota"，默认 "full")

4. pending_count - 查询待审核简历数量
   参数：job_code (str, 优先), job_title (str)

5. interview_count - 查询面试中候选人数量
   参数：job_code (str, 优先), job_title (str)

6. candidate_eval - 查询候选人 AI 评估结果
   参数：candidate_name (str, 候选人姓名), application_id (str, 可选), job_code (str, 可选，消歧用)

7. funnel - 查询岗位招聘漏斗/进度概览
   参数：job_code (str, 优先), job_title (str)

8. candidate_list - 查询候选人列表
   参数：job_code (str, 优先), job_title (str), decision_filter (str, "recommended"|"all"，默认 "recommended")

9. status_change - 变更候选人状态
   参数：candidate_name (str, 优先), application_id (str, 可选), target_status (str, "interview"|"rejected"), job_code (str, 可选，消歧用)

10. job_status - 发布/关闭岗位
    参数：job_code (str, 优先), job_title (str), action (str, "open"|"close")

11. confirm - 用户确认执行操作
    参数：无

12. cancel - 用户取消操作
    参数：无

13. help - 查询使用帮助
    参数：无

14. unknown - 无法识别的意图
    参数：clarifying_question (str, 追问)

规则：
- confidence 低于 0.7 时，intent 设为 unknown 并提供 clarifying_question
- 用户提到"筛选"、"评估"、"筛选简历"、"看简历"、"帮我选"→ evaluate
- 用户提到"有哪些岗位"、"岗位列表"、"活跃岗位"、"关闭岗位"(列表语境) → list_jobs
- 用户提到"岗位详情"、"岗位信息"、"任职要求"、"岗位职责" → job_detail
- 用户提到"多少简历"、"几份简历"、"还没看"(简历语境) → pending_count
- 用户提到"几个面试"、"面试中"(人数语境) → interview_count
- 用户提到"评估结果"、"AI评分"、"推荐原因" → candidate_eval
- 用户提到"招聘进度"、"漏斗"、"进展" → funnel
- 用户提到"候选人名单"、"推荐的人" → candidate_list
- 用户提到"推进"、"进入面试"、"淘汰"、"拒绝"(候选人语境) → status_change
- 用户提到"发布岗位"、"关闭岗位"(操作语境)、"暂停招聘" → job_status
- 用户回复"确认"、"好的"、"是"、"执行" → confirm
- 用户回复"取消"、"算了"、"不要" → cancel
- 用户提到"帮助"、"能做什么"、"怎么用" → help
- job_code: 岗位编号，格式 J+5位数字(如 J04217)。用户提到时必须提取，优先级高于 job_title
- 如果用户提到岗位但未提供 job_code，提取 job_title 用于模糊匹配
- 当候选人姓名可能有歧义时，提取 job_code 用于消歧

严格按照以下 JSON 格式输出，不要输出任何其他内容：
{
  "intent": "<意图ID>",
  "confidence": 0.0-1.0,
  "extracted_params": {},
  "clarifying_question": "..." // 仅 unknown 时提供
}"""
```

- [ ] **Step 4: Run all tests**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Run mypy**

Run: `cd backend && uv run mypy --strict app/`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/services/conversation/prompts.py tests/test_intent_recognition.py
git commit -m "feat: rewrite INTENT_SYSTEM_PROMPT for 14-intent recognition with parameter extraction"
```

---

### Task 6: Expand Chat Schemas for New Card Types

**Files:**
- Modify: `backend/app/schemas/chat.py`
- Test: `backend/tests/test_chat_schemas.py` (new file)

**Interfaces:**
- Consumes: Nothing new
- Produces: `JobListCard`, `JobDetailCard`, `FunnelCard`, `CandidateListCard`, `ConfirmCard` Pydantic models; `ResultEvent.cards` type expanded to `list[EvaluationSummaryCard | JobListCard | JobDetailCard | FunnelCard | CandidateListCard | ConfirmCard] | None`

- [ ] **Step 1: Write failing tests for new card schemas**

Create `backend/tests/test_chat_schemas.py`:

```python
"""Chat Card Schema 测试"""

from app.schemas.chat import (
    EvaluationSummaryCard,
    JobListCard,
    JobDetailCard,
    FunnelCard,
    CandidateListCard,
    ConfirmCard,
    ResultEvent,
)


class TestJobListCard:
    def test_create_job_list_card(self) -> None:
        card = JobListCard(
            jobs=[
                {"job_code": "J04217", "title": "前端开发", "status": "active", "head_count": 3},
                {"job_code": "J04218", "title": "产品经理", "status": "closed", "head_count": 1},
            ]
        )
        assert card.type == "job_list"
        assert len(card.jobs) == 2

class TestJobDetailCard:
    def test_create_job_detail_card(self) -> None:
        card = JobDetailCard(
            job={
                "job_code": "J04217",
                "title": "前端开发",
                "description": "负责前端开发",
                "requirements": "3年经验",
                "skills_required": ["React", "TypeScript"],
                "salary_min": 20000,
                "salary_max": 40000,
                "location": "北京",
                "work_type": "hybrid",
                "head_count": 3,
                "interview_quota": 5,
                "status": "active",
            }
        )
        assert card.type == "job_detail"

class TestFunnelCard:
    def test_create_funnel_card(self) -> None:
        card = FunnelCard(
            job_code="J04217",
            job_title="前端开发",
            stages=[
                {"status": "pending", "count": 10, "percentage": 50.0},
                {"status": "interview", "count": 5, "percentage": 25.0},
                {"status": "rejected", "count": 5, "percentage": 25.0},
            ]
        )
        assert card.type == "funnel"
        assert len(card.stages) == 3

class TestCandidateListCard:
    def test_create_candidate_list_card(self) -> None:
        card = CandidateListCard(
            job_code="J04217",
            job_title="前端开发",
            candidates=[
                {"name": "张三", "ai_score": 85.5, "ai_decision": "recommend", "status": "pending"},
                {"name": "李四", "ai_score": 72.0, "ai_decision": "recommend", "status": "interview"},
            ]
        )
        assert card.type == "candidate_list"
        assert len(card.candidates) == 2

class TestConfirmCard:
    def test_create_confirm_card(self) -> None:
        card = ConfirmCard(
            action="将候选人 张三 推进到面试阶段",
            params={"candidate_name": "张三", "target_status": "interview"},
        )
        assert card.type == "confirm"

class TestResultEventWithNewCards:
    def test_result_event_with_job_list_card(self) -> None:
        card = JobListCard(jobs=[])
        event = ResultEvent(reply_message="岗位列表", cards=[card])
        assert event.cards is not None
        assert len(event.cards) == 1

    def test_result_event_with_no_cards(self) -> None:
        event = ResultEvent(reply_message="简单文本回复")
        assert event.cards is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_chat_schemas.py -v`
Expected: FAIL — `JobListCard` etc. not found

- [ ] **Step 3: Implement new card schemas**

Replace `backend/app/schemas/chat.py`:

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


# ── 卡片 Schema ─────────────────────────────────────────────


class EvaluationSummaryCard(BaseModel):
    """评估摘要卡片"""

    type: Literal["evaluation_summary"] = "evaluation_summary"
    task_id: str
    job_title: str
    total_count: int
    recommended_count: int
    rejected_count: int
    result_page_url: str


class JobListCard(BaseModel):
    """岗位列表卡片"""

    type: Literal["job_list"] = "job_list"
    jobs: list[dict[str, Any]] = Field(
        ..., description="岗位列表，每项含 job_code/title/status/head_count"
    )


class JobDetailCard(BaseModel):
    """岗位详情卡片"""

    type: Literal["job_detail"] = "job_detail"
    job: dict[str, Any] = Field(
        ..., description="岗位完整信息"
    )


class FunnelStage(BaseModel):
    """漏斗阶段"""

    status: str = Field(..., description="阶段状态名称")
    count: int = Field(..., description="该阶段数量")
    percentage: float = Field(..., description="占总量百分比")


class FunnelCard(BaseModel):
    """招聘漏斗卡片"""

    type: Literal["funnel"] = "funnel"
    job_code: str = Field(..., description="岗位编号")
    job_title: str = Field(..., description="岗位名称")
    stages: list[FunnelStage] = Field(..., description="各阶段数据")


class CandidateItem(BaseModel):
    """候选人条目"""

    name: str = Field(..., description="候选人姓名")
    ai_score: float | None = Field(None, description="AI 评分")
    ai_decision: str | None = Field(None, description="AI 决策: recommend/reject")
    status: str = Field(..., description="当前状态")


class CandidateListCard(BaseModel):
    """候选人列表卡片"""

    type: Literal["candidate_list"] = "candidate_list"
    job_code: str = Field(..., description="岗位编号")
    job_title: str = Field(..., description="岗位名称")
    candidates: list[CandidateItem] = Field(..., description="候选人列表")


class ConfirmCard(BaseModel):
    """操作确认卡片"""

    type: Literal["confirm"] = "confirm"
    action: str = Field(..., description="操作描述")
    params: dict[str, Any] = Field(..., description="操作参数")


# 联合类型：所有卡片类型的 Union
ChatCard = (
    EvaluationSummaryCard
    | JobListCard
    | JobDetailCard
    | FunnelCard
    | CandidateListCard
    | ConfirmCard
)


class ResultEvent(BaseModel):
    """result 事件"""

    reply_message: str
    cards: list[ChatCard] | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_chat_schemas.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Run mypy**

Run: `cd backend && uv run mypy --strict app/`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/schemas/chat.py tests/test_chat_schemas.py
git commit -m "feat: add chat card schemas for job list, detail, funnel, candidate list, and confirm"
```

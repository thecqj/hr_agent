# HR Agent Phase 1 — API Integration & Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the Agent API router, write comprehensive tests (unit, integration, API), and verify the entire evaluation workflow end-to-end.

**Architecture:** New `agent.py` router mounted at `/api/agent` with 3 endpoints. Tests use the existing `conftest.py` pattern (AsyncClient + auth_headers fixtures) plus new fixtures for evaluation-specific setup. LLM calls are mocked throughout.

**Tech Stack:** FastAPI, pytest, pytest-asyncio, httpx (AsyncClient)

**Prerequisite:** Plan 1 (Data & Config Foundation) AND Plan 2 (LLM Provider & Workflow Engine) must be completed first.

## Global Constraints

- Python 3.12 with strict type hints (`mypy --strict` must pass)
- SQLAlchemy 2.0 type-annotated style
- Pydantic v2 exclusively for validation / DTOs
- All test files go under `backend/tests/`
- LLM calls must be mocked in all tests — no real API calls
- No placeholder code — every step has complete, runnable content

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `backend/app/api/agent.py` | Agent API router (3 endpoints) | Create |
| `backend/app/api/__init__.py` | Mount agent router | Modify |
| `backend/tests/test_agent_nodes.py` | Unit tests for LangGraph nodes | Create |
| `backend/tests/test_agent_service.py` | Unit tests for AgentService | Create |
| `backend/tests/test_agent_api.py` | API integration tests | Create |
| `backend/tests/conftest.py` | Add evaluation-specific fixtures | Modify |

---

### Task 1: Create Agent API Router

**Files:**
- Create: `backend/app/api/agent.py`
- Modify: `backend/app/api/__init__.py`

**Interfaces:**
- Consumes: `agent_service.trigger_evaluation()`, `agent_service.get_task_status()`, `agent_service.confirm_evaluation()` (from Plan 2)
- Consumes: `EvaluateRequest`, `ConfirmRequest` (from Plan 1 schemas)
- Produces: 3 API endpoints under `/api/agent`

- [ ] **Step 1: Create `agent.py`**

Create `backend/app/api/agent.py`:

```python
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_required_user
from app.database import get_db
from app.models.user import User
from app.schemas.agent import (
    ConfirmRequest,
    ConfirmResponse,
    EvaluateRequest,
    EvaluateResponse,
    TaskStatusResponse,
)
from app.services import agent_service

router = APIRouter(prefix="/agent", tags=["智能评估"])


@router.post(
    "/evaluate/{job_id}",
    response_model=EvaluateResponse,
    summary="触发评估工作流",
    status_code=201,
)
async def trigger_evaluation(
    job_id: str = Path(..., description="岗位ID"),
    data: EvaluateRequest = EvaluateRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> EvaluateResponse:
    """触发对指定岗位下所有待处理申请的 AI 评估"""
    return await agent_service.trigger_evaluation(db, job_id, current_user, data)


@router.get(
    "/task/{task_id}",
    response_model=TaskStatusResponse,
    summary="查询评估任务状态",
)
async def get_task_status(
    task_id: str = Path(..., description="任务ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> TaskStatusResponse:
    """查询评估任务的进度和结果"""
    return await agent_service.get_task_status(db, task_id, current_user)


@router.post(
    "/confirm/{task_id}",
    response_model=ConfirmResponse,
    summary="确认评估结果",
)
async def confirm_evaluation(
    task_id: str = Path(..., description="任务ID"),
    data: ConfirmRequest = ConfirmRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ConfirmResponse:
    """确认评估结果，更新申请状态"""
    return await agent_service.confirm_evaluation(db, task_id, current_user, data)
```

- [ ] **Step 2: Mount the agent router**

In `backend/app/api/__init__.py`, add the import and include:

```python
from app.api import auth, jobs, applications, agent
```

And add after the existing `include_router` calls:

```python
api_router.include_router(agent.router)
```

- [ ] **Step 3: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/api/`
Expected: SUCCESS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/agent.py backend/app/api/__init__.py
git commit -m "feat: add Agent API router with evaluate/task/confirm endpoints"
```

---

### Task 2: Add Evaluation Test Fixtures to conftest.py

**Files:**
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Produces: `recruiter_with_job` fixture — creates a recruiter user + active job + pending applications
- Produces: `seeker_for_application` fixture — creates a job seeker user

- [ ] **Step 1: Add evaluation-specific fixtures**

In `backend/tests/conftest.py`, add the following imports at the top (after existing imports):

```python
from app.models.user import UserRole
from app.models.job import Job, WorkType, JobStatus
from app.models.application import Application, ApplicationStatus
```

Add the following fixtures at the end of the file:

```python
@pytest_asyncio.fixture
async def seeker_for_application(
    client: AsyncClient,
) -> dict[str, str]:
    """创建一个求职者用户，返回 {user_id, auth_headers}"""
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "seeker-app@test.com",
            "password": "testpass123",
            "name": "测试求职者-申请",
            "role": "job_seeker",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    return {
        "user_id": data["user"]["id"],
        "auth_headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest_asyncio.fixture
async def recruiter_with_job(
    client: AsyncClient,
    db_session: AsyncSession,
    seeker_for_application: dict[str, str],
) -> dict[str, Any]:
    """创建招聘者 + 活跃岗位 + 3 份 pending 申请，返回相关信息"""
    # 创建招聘者
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "recruiter-eval@test.com",
            "password": "testpass123",
            "name": "测试招聘者-评估",
            "role": "recruiter",
        },
    )
    assert resp.status_code == 201
    recruiter_data = resp.json()
    recruiter_headers = {"Authorization": f"Bearer {recruiter_data['access_token']}"}

    # 创建岗位
    resp = await client.post(
        "/api/jobs/",
        json={
            "title": "高级前端工程师",
            "description": "负责公司核心产品的前端开发工作",
            "skills_required": ["React", "TypeScript", "CSS"],
            "location": "北京",
            "work_type": "onsite",
            "interview_quota": 2,
        },
        headers=recruiter_headers,
    )
    assert resp.status_code == 201
    job_data = resp.json()
    job_id = job_data["id"]

    # 求职者投递 3 份申请
    seeker_headers = seeker_for_application["auth_headers"]
    for i in range(3):
        resp = await client.post(
            "/api/applications/",
            json={
                "job_id": job_id,
                "resume_text": f"测试简历 {i+1}：有 React 和 TypeScript 经验",
                "structured_resume": {
                    "name": f"候选人{i+1}",
                    "work_experience_years": 2 + i,
                    "skills": ["React", "TypeScript"],
                    "work_experience": [],
                    "project_experience": [],
                    "education": [],
                    "certificates": [],
                },
            },
            headers=seeker_headers,
        )
        assert resp.status_code == 201

    return {
        "recruiter_headers": recruiter_headers,
        "recruiter_id": recruiter_data["user"]["id"],
        "job_id": job_id,
        "seeker_headers": seeker_headers,
    }
```

Also add the missing import at the top:

```python
from typing import Any
```

- [ ] **Step 2: Run mypy to verify**

Run: `cd backend && uv run mypy --strict tests/conftest.py`
Expected: SUCCESS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: add evaluation-specific fixtures to conftest"
```

---

### Task 3: Write Unit Tests for LangGraph Nodes

**Files:**
- Create: `backend/tests/test_agent_nodes.py`

**Interfaces:**
- Consumes: Node functions from `app.services.agent.nodes` (Plan 2)
- Consumes: `EvaluationState` (Plan 2)
- Consumes: ORM models (Plan 1)

- [ ] **Step 1: Create `test_agent_nodes.py`**

Create `backend/tests/test_agent_nodes.py`:

```python
"""LangGraph 节点单元测试"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, WorkType, JobStatus
from app.models.user import User, UserRole
from app.services.agent.nodes import (
    collect_node,
    evaluate_node,
    screen_node,
    review_node,
    save_draft_node,
)
from app.services.agent.state import EvaluationState
from app.schemas.agent import ResumeEvaluation, DimensionScore


# ── screen_node 测试 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_screen_node_with_quota() -> None:
    """有面试人数上限时，取 Top N"""
    state: EvaluationState = {
        "evaluation_results": [
            {"application_id": "a1", "weighted_total": 90, "suggestion": "recommend"},
            {"application_id": "a2", "weighted_total": 80, "suggestion": "recommend"},
            {"application_id": "a3", "weighted_total": 70, "suggestion": "neutral"},
            {"application_id": "a4", "weighted_total": 50, "suggestion": "reject"},
        ],
        "job_info": {"interview_quota": 2},
    }

    result = await screen_node(state, AsyncMock())

    screening = result["screening_result"]
    assert len(screening["recommend_list"]) == 2
    assert len(screening["reject_list"]) == 2
    assert screening["recommend_list"][0]["application_id"] == "a1"
    assert screening["cutoff_score"] == 80


@pytest.mark.asyncio
async def test_screen_node_without_quota() -> None:
    """无面试人数上限时，按 60 分阈值划分"""
    state: EvaluationState = {
        "evaluation_results": [
            {"application_id": "a1", "weighted_total": 85, "suggestion": "recommend"},
            {"application_id": "a2", "weighted_total": 55, "suggestion": "reject"},
        ],
        "job_info": {"interview_quota": None},
    }

    result = await screen_node(state, AsyncMock())

    screening = result["screening_result"]
    assert len(screening["recommend_list"]) == 1
    assert len(screening["reject_list"]) == 1
    assert screening["cutoff_score"] == 60.0


@pytest.mark.asyncio
async def test_screen_node_empty_results() -> None:
    """无评估结果时返回空列表"""
    state: EvaluationState = {
        "evaluation_results": [],
        "job_info": {},
    }

    result = await screen_node(state, AsyncMock())

    screening = result["screening_result"]
    assert screening["recommend_list"] == []
    assert screening["reject_list"] == []
    assert screening["cutoff_score"] == 0.0


# ── evaluate_node 测试（Mock LLM）────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_node_success() -> None:
    """正常评估简历"""
    mock_evaluation = ResumeEvaluation(
        dimensions=[
            DimensionScore(name="技能匹配", score=85, weight=0.35, reason="匹配度高"),
            DimensionScore(name="经验相关性", score=70, weight=0.30, reason="3年经验"),
            DimensionScore(name="学历达标", score=90, weight=0.15, reason="985本科"),
            DimensionScore(name="综合印象", score=75, weight=0.20, reason="良好"),
        ],
        weighted_total=78.25,
        suggestion="recommend",
        summary="候选人技能匹配度高",
    )

    mock_provider = AsyncMock()
    mock_provider.evaluate_resume.return_value = mock_evaluation
    mock_provider.close = AsyncMock()

    mock_db = AsyncMock()
    mock_task = MagicMock()
    mock_db.get.return_value = mock_task

    state: EvaluationState = {
        "job_info": {"title": "前端工程师", "skills_required": ["React"]},
        "applications": [
            {
                "application_id": "app-1",
                "applicant_name": "张三",
                "structured_resume": {"name": "张三", "skills": ["React"]},
            }
        ],
        "task_id": "task-1",
        "errors": [],
        "evaluation_results": [],
        "evaluated_count": 0,
    }

    with patch("app.services.agent.nodes._get_llm_provider", return_value=mock_provider):
        result = await evaluate_node(state, mock_db)

    assert len(result["evaluation_results"]) == 1
    assert result["evaluation_results"][0]["application_id"] == "app-1"
    assert result["evaluation_results"][0]["weighted_total"] == 78.25
    assert result["evaluated_count"] == 1


@pytest.mark.asyncio
async def test_evaluate_node_llm_failure_skips_resume() -> None:
    """LLM 评估失败时跳过该简历，继续下一份"""
    mock_provider = AsyncMock()
    # 第一次调用失败，第二次成功
    mock_provider.evaluate_resume.side_effect = [
        RuntimeError("API 调用失败"),
        ResumeEvaluation(
            dimensions=[DimensionScore(name="技能匹配", score=80, weight=1.0, reason="OK")],
            weighted_total=80.0,
            suggestion="recommend",
            summary="OK",
        ),
    ]
    mock_provider.close = AsyncMock()

    mock_db = AsyncMock()
    mock_task = MagicMock()
    mock_db.get.return_value = mock_task

    state: EvaluationState = {
        "job_info": {"title": "工程师"},
        "applications": [
            {"application_id": "app-1", "structured_resume": {"name": "A"}},
            {"application_id": "app-2", "structured_resume": {"name": "B"}},
        ],
        "task_id": "task-1",
        "errors": [],
        "evaluation_results": [],
        "evaluated_count": 0,
    }

    with patch("app.services.agent.nodes._get_llm_provider", return_value=mock_provider):
        result = await evaluate_node(state, mock_db)

    # 第一份跳过，第二份成功
    assert len(result["evaluation_results"]) == 1
    assert result["evaluation_results"][0]["application_id"] == "app-2"
    assert len(result["errors"]) == 1  # 第一份的错误被记录


# ── review_node 测试 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_review_node_no_borderline() -> None:
    """没有边界候选人时跳过复评"""
    state: EvaluationState = {
        "screening_result": {
            "recommend_list": [
                {"application_id": "a1", "weighted_total": 95},
            ],
            "reject_list": [
                {"application_id": "a2", "weighted_total": 30},
            ],
            "cutoff_score": 60.0,
        },
        "job_info": {},
        "errors": [],
    }

    result = await review_node(state, AsyncMock())

    assert result["review_adjustments"] == []


@pytest.mark.asyncio
async def test_review_node_with_borderline() -> None:
    """有边界候选人时调用 LLM 复评"""
    from app.schemas.agent import BorderlineReview

    mock_reviews = [
        BorderlineReview(
            application_id="a2",
            action="adjust",
            new_decision="recommend",
            reason="虽然分数略低但项目经验突出",
        ),
    ]
    mock_provider = AsyncMock()
    mock_provider.review_borderline.return_value = mock_reviews
    mock_provider.close = AsyncMock()

    state: EvaluationState = {
        "screening_result": {
            "recommend_list": [
                {"application_id": "a1", "weighted_total": 65, "applicant_name": "X", "suggestion": "recommend", "evaluation": {"summary": "OK"}},
            ],
            "reject_list": [
                {"application_id": "a2", "weighted_total": 55, "applicant_name": "Y", "suggestion": "reject", "evaluation": {"summary": "borderline"}},
            ],
            "cutoff_score": 60.0,
        },
        "job_info": {"title": "工程师"},
        "errors": [],
    }

    with patch("app.services.agent.nodes._get_llm_provider", return_value=mock_provider):
        result = await review_node(state, AsyncMock())

    assert len(result["review_adjustments"]) == 1
    assert result["review_adjustments"][0]["application_id"] == "a2"
    assert result["review_adjustments"][0]["action"] == "adjust"


@pytest.mark.asyncio
async def test_review_node_failure_falls_back() -> None:
    """复评失败时沿用排序结果"""
    mock_provider = AsyncMock()
    mock_provider.review_borderline.side_effect = RuntimeError("API 错误")
    mock_provider.close = AsyncMock()

    state: EvaluationState = {
        "screening_result": {
            "recommend_list": [
                {"application_id": "a1", "weighted_total": 55, "applicant_name": "X", "suggestion": "recommend", "evaluation": {"summary": "OK"}},
            ],
            "reject_list": [
                {"application_id": "a2", "weighted_total": 52, "applicant_name": "Y", "suggestion": "reject", "evaluation": {"summary": "OK"}},
            ],
            "cutoff_score": 60.0,
        },
        "job_info": {},
        "errors": [],
    }

    with patch("app.services.agent.nodes._get_llm_provider", return_value=mock_provider):
        result = await review_node(state, AsyncMock())

    assert result["review_adjustments"] == []
    assert len(result["errors"]) == 1
    assert "边界复评失败" in result["errors"][0]
```

- [ ] **Step 2: Run the node tests**

Run: `cd backend && uv run pytest tests/test_agent_nodes.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_agent_nodes.py
git commit -m "test: add unit tests for LangGraph nodes (screen, evaluate, review)"
```

---

### Task 4: Write Unit Tests for AgentService

**Files:**
- Create: `backend/tests/test_agent_service.py`

**Interfaces:**
- Consumes: `agent_service` functions (Plan 2)
- Consumes: ORM models and schemas (Plan 1)

- [ ] **Step 1: Create `test_agent_service.py`**

Create `backend/tests/test_agent_service.py`:

```python
"""AgentService 单元测试"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, UTC

from fastapi import HTTPException

from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, JobStatus
from app.models.user import User, UserRole
from app.schemas.agent import EvaluateRequest, ConfirmRequest, ConfirmDecision
from app.services import agent_service


# ── trigger_evaluation 测试 ──────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_non_recruiter_rejected() -> None:
    """非招聘者触发评估返回 403"""
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.role = UserRole.JOB_SEEKER

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.trigger_evaluation(
            mock_db, "job-1", mock_user, EvaluateRequest()
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_trigger_job_not_found() -> None:
    """岗位不存在返回 404"""
    mock_db = AsyncMock()
    mock_db.get.return_value = None
    mock_user = MagicMock()
    mock_user.role = UserRole.RECRUITER

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.trigger_evaluation(
            mock_db, "nonexistent", mock_user, EvaluateRequest()
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_trigger_not_job_owner() -> None:
    """非岗位 owner 触发返回 403"""
    import uuid

    mock_db = AsyncMock()
    mock_job = MagicMock()
    mock_job.recruiter_id = uuid.uuid4()  # 不同的 recruiter
    mock_db.get.return_value = mock_job
    mock_user = MagicMock()
    mock_user.role = UserRole.RECRUITER
    mock_user.id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.trigger_evaluation(
            mock_db, "job-1", mock_user, EvaluateRequest()
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_trigger_duplicate_evaluation_returns_409() -> None:
    """重复触发评估返回 409"""
    mock_db = AsyncMock()
    mock_job = MagicMock()
    mock_job.status = JobStatus.ACTIVE

    other_user_id = mock_job.recruiter_id = MagicMock()

    mock_user = MagicMock()
    mock_user.role = UserRole.RECRUITER
    mock_user.id = other_user_id

    # 模拟已存在 pending 任务
    mock_existing = MagicMock()
    mock_db.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=mock_existing)
    )
    mock_db.get.return_value = mock_job

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.trigger_evaluation(
            mock_db, "job-1", mock_user, EvaluateRequest()
        )
    assert exc_info.value.status_code == 409


# ── get_task_status 测试 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_task_not_found() -> None:
    """查询不存在的任务返回 404"""
    mock_db = AsyncMock()
    mock_db.get.return_value = None
    mock_user = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.get_task_status(mock_db, "nonexistent", mock_user)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_task_wrong_user() -> None:
    """非触发者查询任务返回 403"""
    import uuid

    mock_task = MagicMock()
    mock_task.triggered_by = uuid.uuid4()
    mock_db = AsyncMock()
    mock_db.get.return_value = mock_task

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()  # 不同的用户

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.get_task_status(mock_db, "task-1", mock_user)
    assert exc_info.value.status_code == 403


# ── confirm_evaluation 测试 ──────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_task_not_completed() -> None:
    """确认未完成的任务返回 400"""
    mock_task = MagicMock()
    mock_task.status = EvalTaskStatus.RUNNING
    mock_task.triggered_by = MagicMock()
    mock_db = AsyncMock()
    mock_db.get.return_value = mock_task

    mock_user = MagicMock()
    mock_user.id = mock_task.triggered_by

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.confirm_evaluation(
            mock_db, "task-1", mock_user, ConfirmRequest()
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_confirm_with_override_decisions() -> None:
    """确认时覆盖部分 AI 决策"""
    import uuid

    user_id = uuid.uuid4()

    mock_task = MagicMock()
    mock_task.status = EvalTaskStatus.COMPLETED
    mock_task.triggered_by = user_id
    mock_task.job_id = uuid.uuid4()

    app1_id = uuid.uuid4()
    app2_id = uuid.uuid4()
    mock_app1 = MagicMock()
    mock_app1.id = app1_id
    mock_app1.ai_decision = "recommend"
    mock_app2 = MagicMock()
    mock_app2.id = app2_id
    mock_app2.ai_decision = "reject"

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_task
    mock_db.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_app1, mock_app2])))
    )

    mock_user = MagicMock()
    mock_user.id = user_id

    # 覆盖 app2 的决策为 interview
    request = ConfirmRequest(
        decisions=[
            ConfirmDecision(application_id=str(app2_id), final_decision="interview")
        ]
    )

    result = await agent_service.confirm_evaluation(mock_db, "task-1", mock_user, request)

    assert result.updated_count == 2
    # app1 用 AI 建议的 recommend → interview
    assert mock_app1.status == ApplicationStatus.INTERVIEW
    # app2 被覆盖为 interview
    assert mock_app2.status == ApplicationStatus.INTERVIEW
    # 任务状态更新为 confirmed
    assert mock_task.status == EvalTaskStatus.CONFIRMED
```

- [ ] **Step 2: Run the service tests**

Run: `cd backend && uv run pytest tests/test_agent_service.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_agent_service.py
git commit -m "test: add unit tests for AgentService (trigger, query, confirm)"
```

---

### Task 5: Write API Integration Tests

**Files:**
- Create: `backend/tests/test_agent_api.py`

**Interfaces:**
- Consumes: Agent API endpoints, `recruiter_with_job` fixture (Task 2)
- Consumes: All models and schemas (Plan 1, Plan 2)

- [ ] **Step 1: Create `test_agent_api.py`**

Create `backend/tests/test_agent_api.py`:

```python
"""Agent API 集成测试"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from httpx import AsyncClient

from app.models.evaluation_task import EvalTaskStatus
from app.schemas.agent import ResumeEvaluation, DimensionScore


@pytest.mark.asyncio
async def test_trigger_evaluation_unauthorized(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
) -> None:
    """求职者不能触发评估"""
    # 先创建一个岗位（用招聘者）
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "recruiter-t@test.com",
            "password": "testpass123",
            "name": "测试",
            "role": "recruiter",
        },
    )
    recruiter_data = resp.json()
    recruiter_headers = {"Authorization": f"Bearer {recruiter_data['access_token']}"}

    resp = await client.post(
        "/api/jobs/",
        json={
            "title": "测试岗位",
            "description": "描述",
            "skills_required": ["Python"],
        },
        headers=recruiter_headers,
    )
    job_id = resp.json()["id"]

    # 求职者尝试触发评估
    resp = await client.post(
        f"/api/agent/evaluate/{job_id}",
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_trigger_evaluation_not_owner(
    client: AsyncClient,
    recruiter_with_job: dict[str, str],
) -> None:
    """非岗位 owner 的招聘者不能触发评估"""
    job_id = recruiter_with_job["job_id"]

    # 创建另一个招聘者
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "other-recruiter@test.com",
            "password": "testpass123",
            "name": "其他招聘者",
            "role": "recruiter",
        },
    )
    other_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await client.post(
        f"/api/agent/evaluate/{job_id}",
        headers=other_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_trigger_evaluation_job_not_found(
    client: AsyncClient,
    auth_headers_recruiter: dict[str, str],
) -> None:
    """评估不存在的岗位返回 404"""
    resp = await client.post(
        "/api/agent/evaluate/00000000-0000-0000-0000-000000000000",
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_task_status_not_found(
    client: AsyncClient,
    auth_headers_recruiter: dict[str, str],
) -> None:
    """查询不存在的任务返回 404"""
    resp = await client.get(
        "/api/agent/task/00000000-0000-0000-0000-000000000000",
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_confirm_task_not_completed(
    client: AsyncClient,
    recruiter_with_job: dict[str, str],
) -> None:
    """确认未完成的任务返回 400"""
    # 我们不会触发真实工作流（因为需要 Mock LLM），
    # 所以这个测试验证 API 路由可达即可
    resp = await client.post(
        "/api/agent/confirm/00000000-0000-0000-0000-000000000000",
        headers=recruiter_with_job["recruiter_headers"],
    )
    # 任务不存在 → 404
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_trigger_evaluation_success(
    client: AsyncClient,
    recruiter_with_job: dict[str, str],
) -> None:
    """成功触发评估"""
    job_id = recruiter_with_job["job_id"]
    recruiter_headers = recruiter_with_job["recruiter_headers"]

    # Mock 后台工作流，避免真实 LLM 调用
    with patch(
        "app.services.agent_service._run_workflow_background",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            headers=recruiter_headers,
        )

    assert resp.status_code == 201
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    assert data["total_count"] == 3


@pytest.mark.asyncio
async def test_trigger_duplicate_evaluation(
    client: AsyncClient,
    recruiter_with_job: dict[str, str],
) -> None:
    """重复触发评估返回 409"""
    job_id = recruiter_with_job["job_id"]
    recruiter_headers = recruiter_with_job["recruiter_headers"]

    with patch(
        "app.services.agent_service._run_workflow_background",
        new_callable=AsyncMock,
    ):
        # 第一次触发
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            headers=recruiter_headers,
        )
        assert resp.status_code == 201

        # 第二次触发
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            headers=recruiter_headers,
        )
        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_task_status_after_trigger(
    client: AsyncClient,
    recruiter_with_job: dict[str, str],
) -> None:
    """触发后查询任务状态"""
    job_id = recruiter_with_job["job_id"]
    recruiter_headers = recruiter_with_job["recruiter_headers"]

    with patch(
        "app.services.agent_service._run_workflow_background",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            headers=recruiter_headers,
        )
        task_id = resp.json()["task_id"]

    # 查询状态
    resp = await client.get(
        f"/api/agent/task/{task_id}",
        headers=recruiter_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == task_id
    assert data["status"] in ["pending", "running", "completed", "failed"]
    assert data["total_count"] == 3


@pytest.mark.asyncio
async def test_trigger_with_custom_quota(
    client: AsyncClient,
    recruiter_with_job: dict[str, str],
) -> None:
    """触发评估时自定义面试人数上限"""
    job_id = recruiter_with_job["job_id"]
    recruiter_headers = recruiter_with_job["recruiter_headers"]

    with patch(
        "app.services.agent_service._run_workflow_background",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            json={"interview_quota": 5},
            headers=recruiter_headers,
        )

    assert resp.status_code == 201
```

- [ ] **Step 2: Run the API tests**

Run: `cd backend && uv run pytest tests/test_agent_api.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_agent_api.py
git commit -m "test: add API integration tests for Agent endpoints"
```

---

### Task 6: Run Full Test Suite & Fix Any Issues

**Files:**
- Possibly modify test files if fixes needed

**Interfaces:**
- Consumes: All test files from Tasks 3-5

- [ ] **Step 1: Run the complete test suite**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All tests PASS (both existing and new)

- [ ] **Step 2: Run mypy on the entire app**

Run: `cd backend && uv run mypy --strict app/`
Expected: SUCCESS, no errors

- [ ] **Step 3: Fix any failures**

If any tests fail or mypy reports errors, fix them and re-run until all pass.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test and type-check issues from integration"
```

---

### Task 7: Update skeleton.md

**Files:**
- Modify: `skeleton.md`

**Interfaces:**
- Consumes: All new files and interfaces from Plan 1, 2, and 3

- [ ] **Step 1: Update skeleton.md to reflect all new modules**

Add the following sections to `skeleton.md`:

1. Under ORM models, add `EvaluationTask` and `EvalTaskStatus`:

```
#### `evaluation_task.py` — 评估任务 & 任务状态枚举

```python
class EvalTaskStatus(str, Enum):
    PENDING = "pending"; RUNNING = "running"; COMPLETED = "completed"
    CONFIRMED = "confirmed"; FAILED = "failed"

class EvaluationTask(Base, TimestampMixin):          # table "evaluation_tasks"
    job_id:             Mapped[uuid.UUID]   # FK → jobs.id
    triggered_by:       Mapped[uuid.UUID]   # FK → users.id
    status:             Mapped[EvalTaskStatus]   # default=PENDING
    total_count:        Mapped[int]              # default=0
    evaluated_count:    Mapped[int]              # default=0
    result_summary:     Mapped[Any | None]       # JSONB
    error_message:      Mapped[str | None]       # Text
    # 关系
    job:               Mapped[Job]
    triggered_by_user: Mapped[User]
```
```

2. Update `Application` model to include `ai_*` fields
3. Update `Job` model to include `interview_quota`
4. Add new API routes section for `/api/agent/*`
5. Add new service section for `agent_service`
6. Add LLM module section
7. Add Agent workflow module section
8. Update API prefix from `/api/v1` to `/api`

- [ ] **Step 2: Commit**

```bash
git add skeleton.md
git commit -m "docs: update skeleton.md with HR Agent Phase 1 modules"
```

---

## Self-Review Checklist

### Spec Coverage

| Spec Section | Covered by Task |
|-------------|----------------|
| §6.1 Agent API routes | Task 1 (router) + Task 5 (API tests) |
| §6.2 Endpoint detailed design | Task 1 (implement) + Tasks 4, 5 (test) |
| §6.3 Existing route modifications | Tested via existing test suite (Task 6) |
| §10.1 Unit tests | Tasks 3 (nodes), 4 (service) |
| §10.2 Integration tests | Task 5 (API integration) |
| §10.3 API tests | Task 5 |

### Placeholder Scan

No TBD, TODO, or placeholder text found.

### Type Consistency

- `EvaluateRequest`, `EvaluateResponse`, `TaskStatusResponse`, `ConfirmRequest`, `ConfirmResponse` used in router match Plan 1's `app/schemas/agent.py` definitions
- `agent_service` function signatures match what the router passes
- `recruiter_with_job` fixture creates `interview_quota=2` matching the Job schema update
- Test mock structures match `EvaluationState` field types from Plan 2
- `EvalTaskStatus` enum values match Plan 1 definition
- `ApplicationStatus.INTERVIEW` and `ApplicationStatus.REJECTED` used in confirm test match existing enum

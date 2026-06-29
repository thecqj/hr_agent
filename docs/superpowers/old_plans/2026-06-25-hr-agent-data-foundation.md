# HR Agent Phase 1 — Data & Config Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay the data layer foundation for the HR Agent evaluation workflow — ORM models, DB migration, config, and all Pydantic schemas.

**Architecture:** Extend existing SQLAlchemy 2.0 models with `ai_*` fields on `Application`, add `interview_quota` to `Job`, create new `EvaluationTask` model + enum, and update `Settings` with LLM configuration. Pydantic schemas cover both LLM structured output and Agent API DTOs.

**Tech Stack:** SQLAlchemy 2.0 (Mapped annotations), Alembic, Pydantic v2, pydantic-settings

## Global Constraints

- Python 3.12 with strict type hints (`mypy --strict` must pass)
- SQLAlchemy 2.0 type-annotated style (`Mapped[str] = mapped_column(...)`)
- Pydantic v2 exclusively for validation / DTOs
- All new files go under `backend/app/`
- No placeholder code — every step has complete, runnable content

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `backend/app/config.py` | Application settings | Modify: add LLM config fields |
| `backend/app/models/evaluation_task.py` | EvaluationTask ORM model + EvalTaskStatus enum | Create |
| `backend/app/models/application.py` | Application ORM model | Modify: add `ai_*` fields |
| `backend/app/models/job.py` | Job ORM model | Modify: add `interview_quota` |
| `backend/app/models/__init__.py` | Model exports | Modify: export new model |
| `backend/app/schemas/agent.py` | Agent API request/response DTOs | Create |
| `backend/app/schemas/job.py` | Job DTOs | Modify: add `interview_quota` |
| `backend/app/schemas/application.py` | Application DTOs | Modify: add `ai_*` fields |
| `backend/.env.example` | Environment template | Modify: add LLM config |
| `backend/alembic/versions/xxx_add_hr_agent_fields.py` | DB migration | Create |
| `backend/alembic/env.py` | Alembic env | Modify: import new model |

---

### Task 1: Add LLM Configuration to Settings

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`

**Interfaces:**
- Produces: `Settings.LLM_PROVIDER`, `Settings.DEEPSEEK_API_KEY`, `Settings.DEEPSEEK_BASE_URL`, `Settings.DEEPSEEK_MODEL`, `Settings.LLM_REQUESTS_PER_MINUTE`, `Settings.LLM_EVALUATION_RETRIES`, `Settings.LLM_BORDERLINE_RANGE`

- [ ] **Step 1: Add LLM config fields to Settings class**

In `backend/app/config.py`, add the following fields after the `CORS_ORIGINS` field:

```python
    # LLM Configuration
    LLM_PROVIDER: str = "deepseek"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    LLM_REQUESTS_PER_MINUTE: int = 30
    LLM_EVALUATION_RETRIES: int = 1
    LLM_BORDERLINE_RANGE: float = 10.0
```

- [ ] **Step 2: Add LLM config to `.env.example`**

Append to `backend/.env.example`:

```env

# LLM Configuration
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
LLM_REQUESTS_PER_MINUTE=30
LLM_EVALUATION_RETRIES=1
LLM_BORDERLINE_RANGE=10.0
```

- [ ] **Step 3: Run mypy to verify type correctness**

Run: `cd backend && uv run mypy --strict app/config.py`
Expected: SUCCESS, no errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "feat: add LLM configuration fields to Settings"
```

---

### Task 2: Create EvaluationTask Model

**Files:**
- Create: `backend/app/models/evaluation_task.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Produces: `EvalTaskStatus` enum, `EvaluationTask` ORM model with fields: `id`, `job_id`, `triggered_by`, `status`, `total_count`, `evaluated_count`, `result_summary`, `error_message`, `created_at`, `updated_at`
- Produces: relationships `EvaluationTask.job` → `Job`, `EvaluationTask.triggered_by_user` → `User`

- [ ] **Step 1: Write the EvaluationTask model**

Create `backend/app/models/evaluation_task.py`:

```python
import enum
import uuid
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy import String, Integer, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, TimestampMixin


class EvalTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class EvaluationTask(Base, TimestampMixin):
    __tablename__ = "evaluation_tasks"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[EvalTaskStatus] = mapped_column(
        Enum(EvalTaskStatus),
        default=EvalTaskStatus.PENDING,
    )
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    evaluated_count: Mapped[int] = mapped_column(Integer, default=0)
    result_summary: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关联
    job: Mapped["Job"] = relationship("Job", foreign_keys=[job_id])
    triggered_by_user: Mapped["User"] = relationship(
        "User", foreign_keys=[triggered_by]
    )

    def __repr__(self) -> str:
        return f"<EvaluationTask job={self.job_id} status={self.status.value}>"


# 处理循环引用
if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.user import User
```

- [ ] **Step 2: Update models `__init__.py` to export new model**

In `backend/app/models/__init__.py`, add the import and export:

Add import line after the `application` import:
```python
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
```

Add to `__all__` list:
```python
    "EvaluationTask",
    "EvalTaskStatus",
```

- [ ] **Step 3: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/models/`
Expected: SUCCESS, no errors

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/evaluation_task.py backend/app/models/__init__.py
git commit -m "feat: add EvaluationTask ORM model and EvalTaskStatus enum"
```

---

### Task 3: Add `ai_*` Fields to Application Model

**Files:**
- Modify: `backend/app/models/application.py`

**Interfaces:**
- Produces: `Application.ai_score` (Float), `Application.ai_evaluation` (JSONB), `Application.ai_decision` (String(20)), `Application.ai_decision_reason` (Text), `Application.ai_evaluated_at` (DateTime)

- [ ] **Step 1: Add new fields to Application model**

In `backend/app/models/application.py`, add the necessary imports at the top — add `Float` and `DateTime` to the `sqlalchemy` import line:

```python
from sqlalchemy import String, Text, Enum, ForeignKey, Float, DateTime
```

Add after the `status` field (before the `# 关联` comment):

```python
    # AI 评估结果（草稿字段，确认前不影响业务状态）
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_evaluation: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    ai_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ai_decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

Also update the `datetime` import — it already exists via `from datetime import datetime` in the TYPE_CHECKING import line, but we need a runtime import. Check the current imports; if `datetime` is not imported at runtime, add:

```python
from datetime import datetime
```

at the top (after `import uuid`).

- [ ] **Step 2: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/models/application.py`
Expected: SUCCESS

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/application.py
git commit -m "feat: add ai_* evaluation fields to Application model"
```

---

### Task 4: Add `interview_quota` to Job Model

**Files:**
- Modify: `backend/app/models/job.py`

**Interfaces:**
- Produces: `Job.interview_quota` (Integer, nullable)

- [ ] **Step 1: Add `interview_quota` field to Job model**

In `backend/app/models/job.py`, add after the `status` field (before the `# 关联` comment):

```python
    interview_quota: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 2: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/models/job.py`
Expected: SUCCESS

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/job.py
git commit -m "feat: add interview_quota field to Job model"
```

---

### Task 5: Create Agent API Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/agent.py`

**Interfaces:**
- Consumes: `EvalTaskStatus` from `app.models.evaluation_task`
- Produces: `EvaluateRequest`, `EvaluateResponse`, `TaskStatusResponse`, `ConfirmDecision`, `ConfirmRequest`, `ConfirmResponse`
- Produces: `DimensionScore`, `ResumeEvaluation`, `BorderlineReview` (LLM output schemas used by later plans)

- [ ] **Step 1: Create the agent schemas file**

Create `backend/app/schemas/agent.py`:

```python
import uuid
from datetime import datetime
from typing import Optional, Any, Literal

from pydantic import BaseModel, Field, field_serializer

from app.models.evaluation_task import EvalTaskStatus


# ── LLM 输出结构化 Schema ──────────────────────────────────


class DimensionScore(BaseModel):
    """单个评估维度评分"""

    name: str = Field(..., description="维度名称")
    score: float = Field(..., ge=0, le=100, description="0-100 分")
    weight: float = Field(..., ge=0, le=1, description="权重 0-1")
    reason: str = Field(..., description="评估理由")


class ResumeEvaluation(BaseModel):
    """单份简历评估结果"""

    dimensions: list[DimensionScore] = Field(..., description="各维度评分")
    weighted_total: float = Field(..., ge=0, le=100, description="加权总分")
    suggestion: Literal["recommend", "reject", "neutral"] = Field(
        ..., description="AI 建议决策"
    )
    summary: str = Field(..., description="一句话总结")


class BorderlineReview(BaseModel):
    """边界候选人复评结果"""

    application_id: str = Field(..., description="申请 ID")
    action: Literal["keep", "adjust"] = Field(..., description="维持或调整")
    new_decision: Optional[Literal["recommend", "reject"]] = Field(
        None, description="调整后的决策（action=adjust 时必填）"
    )
    reason: str = Field(..., description="调整理由")


# ── Agent API 请求/响应 Schema ──────────────────────────────


class EvaluateRequest(BaseModel):
    """触发评估请求"""

    interview_quota: Optional[int] = Field(
        None, description="面试人数上限，null 表示不限（可覆盖岗位设定）"
    )


class EvaluateResponse(BaseModel):
    """触发评估响应"""

    task_id: str
    status: str = "pending"
    total_count: int = 0

    @field_serializer("task_id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""

    task_id: str
    job_id: str
    status: EvalTaskStatus
    total_count: int = 0
    evaluated_count: int = 0
    result_summary: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("task_id", "job_id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class ConfirmDecision(BaseModel):
    """单个申请的确认决策"""

    application_id: str = Field(..., description="申请 ID")
    final_decision: Literal["interview", "reject"] = Field(
        ..., description="最终决策"
    )
    override_reason: Optional[str] = Field(
        None, description="覆盖 AI 决策时的理由"
    )


class ConfirmRequest(BaseModel):
    """确认评估结果请求"""

    decisions: list[ConfirmDecision] = Field(
        default_factory=list,
        description="逐个覆盖 AI 决策；为空则按 AI 建议批量更新",
    )


class ConfirmResponse(BaseModel):
    """确认评估结果响应"""

    updated_count: int
    message: str
```

- [ ] **Step 2: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/schemas/agent.py`
Expected: SUCCESS

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/agent.py
git commit -m "feat: add Agent API and LLM output Pydantic schemas"
```

---

### Task 6: Update Existing Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/job.py`
- Modify: `backend/app/schemas/application.py`

**Interfaces:**
- Consumes: `Application.ai_score`, `Application.ai_decision`, etc. (from Task 3)
- Consumes: `Job.interview_quota` (from Task 4)
- Produces: Updated `JobCreateRequest`, `JobUpdateRequest`, `JobResponse` with `interview_quota`; Updated `ApplicationResponse` with `ai_*` fields

- [ ] **Step 1: Add `interview_quota` to Job schemas**

In `backend/app/schemas/job.py`:

1. Add to `JobCreateRequest`:
```python
    interview_quota: Optional[int] = Field(None, description="面试人数上限")
```

2. Add to `JobUpdateRequest`:
```python
    interview_quota: Optional[int] = Field(None, description="面试人数上限")
```

3. Add to `JobResponse` (after `applications_count`):
```python
    interview_quota: Optional[int] = None
```

- [ ] **Step 2: Add `ai_*` fields to ApplicationResponse**

In `backend/app/schemas/application.py`:

Add to `ApplicationResponse` (after the `status` field, before `created_at`):

```python
    # AI 评估结果
    ai_score: Optional[float] = None
    ai_evaluation: Optional[dict[str, Any]] = None
    ai_decision: Optional[str] = None
    ai_decision_reason: Optional[str] = None
    ai_evaluated_at: Optional[datetime] = None
```

- [ ] **Step 3: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/schemas/`
Expected: SUCCESS

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/job.py backend/app/schemas/application.py
git commit -m "feat: add interview_quota and ai_* fields to Pydantic schemas"
```

---

### Task 7: Update Job API Helper and Service for `interview_quota`

**Files:**
- Modify: `backend/app/api/jobs.py`
- Modify: `backend/app/services/job_service.py`

**Interfaces:**
- Consumes: `Job.interview_quota` (from Task 4), `JobCreateRequest.interview_quota`, `JobUpdateRequest.interview_quota` (from Task 6)
- Produces: `_job_to_dict` includes `interview_quota`; service passes `interview_quota` through

- [ ] **Step 1: Add `interview_quota` to `_job_to_dict` in `jobs.py`**

In `backend/app/api/jobs.py`, add to the `_job_to_dict` function's return dict:

```python
        "interview_quota": job.interview_quota,
```

(Insert after the `"applications_count": len(job.applications),` line.)

- [ ] **Step 2: Add `interview_quota` handling in `job_service.py`**

In `backend/app/services/job_service.py`, find the `create_job` function. In the `Job(...)` constructor call, add:

```python
        interview_quota=data.interview_quota,
```

Find the `update_job` function. In the update logic that sets fields from `data`, add:

```python
    if data.interview_quota is not None:
        job.interview_quota = data.interview_quota
```

- [ ] **Step 3: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/api/jobs.py app/services/job_service.py`
Expected: SUCCESS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/jobs.py backend/app/services/job_service.py
git commit -m "feat: wire interview_quota through Job API and service"
```

---

### Task 8: Update Application API Helper for `ai_*` Fields

**Files:**
- Modify: `backend/app/api/applications.py`

**Interfaces:**
- Consumes: `Application.ai_score`, etc. (from Task 3), `ApplicationResponse` updated schema (from Task 6)

- [ ] **Step 1: Find and update the application response builder in `applications.py`**

Read `backend/app/api/applications.py` to find where `ApplicationResponse` objects are constructed. The existing code likely uses `ApplicationResponse.model_validate(application)` with `from_attributes=True`.

If the file uses `model_validate` with `from_attributes=True`, the new `ai_*` fields will be auto-populated from the ORM model — no code change needed. Verify by reading the file.

If there is a manual dict construction (like `_job_to_dict` pattern), add the `ai_*` fields:

```python
        "ai_score": application.ai_score,
        "ai_evaluation": application.ai_evaluation,
        "ai_decision": application.ai_decision,
        "ai_decision_reason": application.ai_decision_reason,
        "ai_evaluated_at": application.ai_evaluated_at,
```

- [ ] **Step 2: Run mypy to verify**

Run: `cd backend && uv run mypy --strict app/api/applications.py`
Expected: SUCCESS

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/applications.py
git commit -m "feat: expose ai_* evaluation fields in Application API responses"
```

---

### Task 9: Create Alembic Migration

**Files:**
- Create: `backend/alembic/versions/<auto>_add_hr_agent_evaluation_fields.py`
- Modify: `backend/alembic/env.py`

**Interfaces:**
- Consumes: All model changes from Tasks 2-4

- [ ] **Step 1: Update `alembic/env.py` to import new model**

In `backend/alembic/env.py`, add after the existing model imports:

```python
import app.models.evaluation_task  # noqa: F401
```

- [ ] **Step 2: Generate the migration**

Run: `cd backend && uv run alembic revision --autogenerate -m "add_hr_agent_evaluation_fields"`

- [ ] **Step 3: Review and fix the generated migration**

Open the generated migration file. Verify it contains:

1. **`evaluation_tasks` table creation** with all columns
2. **`applications` table alterations**: add `ai_score`, `ai_evaluation`, `ai_decision`, `ai_decision_reason`, `ai_evaluated_at`
3. **`jobs` table alteration**: add `interview_quota`
4. **Rename** `applications.match_score` → `applications.ai_score` (if the column exists in the DB; if not, just add `ai_score`)

**Important:** If `match_score` column exists in the DB but is removed from the ORM, the autogenerate may try to drop it. Instead, we want to *rename* it. Replace the `op.drop_column` + `op.add_column` for `match_score`/`ai_score` with:

```python
    op.alter_column('applications', 'match_score', new_column_name='ai_score')
```

Also check for `ai_suggestions` column — if it exists in the DB, add:

```python
    op.drop_column('applications', 'ai_suggestions')
```

If the autogenerate did not detect `match_score`/`ai_suggestions` (because they were already removed from ORM), that's fine — the migration just adds the new columns.

- [ ] **Step 4: Run the migration**

Run: `cd backend && uv run alembic upgrade head`
Expected: SUCCESS

- [ ] **Step 5: Run mypy on the migration**

Run: `cd backend && uv run mypy --strict alembic/`
Expected: May have warnings for auto-generated code — acceptable if only about `Union` usage in revision headers. Fix any real errors.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/ backend/app/alembic/env.py
git commit -m "feat: add Alembic migration for HR Agent evaluation fields"
```

---

### Task 10: Change API Router Prefix from `/api/v1` to `/api`

**Files:**
- Modify: `backend/app/api/__init__.py`

**Interfaces:**
- Produces: All routes now accessible under `/api/*` instead of `/api/v1/*`

- [ ] **Step 1: Update the prefix**

In `backend/app/api/__init__.py`, change:

```python
api_router = APIRouter(prefix="/api/v1")
```

to:

```python
api_router = APIRouter(prefix="/api")
```

- [ ] **Step 2: Update test conftest URL references**

In `backend/tests/conftest.py`, update the register URLs in `auth_headers_seeker` and `auth_headers_recruiter`:

Change:
```python
        "/api/v1/auth/register",
```

to:
```python
        "/api/auth/register",
```

(Both fixtures have this URL.)

- [ ] **Step 3: Update all test files that use `/api/v1`**

Run: `grep -rn "api/v1" backend/tests/`

Update every occurrence to `/api`. This affects `test_auth_api.py`, `test_jobs_api.py`, `test_applications_api.py`.

- [ ] **Step 4: Update frontend API client base URL**

In `frontend/src/shared/api/client.ts`, change the `baseURL` from `/api/v1` to `/api`.

- [ ] **Step 5: Run existing tests to verify nothing is broken**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/__init__.py backend/tests/ frontend/src/shared/api/client.ts
git commit -m "refactor: change API prefix from /api/v1 to /api"
```

---

## Self-Review Checklist

### Spec Coverage

| Spec Section | Covered by Task |
|-------------|----------------|
| §3.2 Application ai_* fields | Task 3 (model) + Task 6 (schema) + Task 8 (API) |
| §3.3 Job interview_quota | Task 4 (model) + Task 6 (schema) + Task 7 (service/API) |
| §3.4 EvaluationTask table | Task 2 (model) + Task 9 (migration) |
| §3.5 ai_evaluation JSONB structure | Task 5 (DimensionScore schema) |
| §3.6 ORM migration strategy | Task 9 |
| §5.3 Structured output Pydantic schema | Task 5 |
| §6.2 API endpoint schemas | Task 5 |
| §6.3 Existing route modifications | Tasks 6, 7, 8, 10 |
| §9 Configuration items | Task 1 |

### Placeholder Scan

No TBD, TODO, or placeholder text found.

### Type Consistency

- `EvalTaskStatus` values (`pending`, `running`, `completed`, `confirmed`, `failed`) match spec §3.4
- `ai_decision` uses `String(20)` matching spec's `String(20)`
- `ai_score` is `Float` (nullable) matching spec
- `interview_quota` is `Integer, nullable` matching spec
- `DimensionScore.weight` validated `ge=0, le=1`; LLM must ensure sum=1.0 (enforced in prompt, not schema)
- `ResumeEvaluation.suggestion` uses `Literal["recommend", "reject", "neutral"]` matching spec
- `BorderlineReview.action` uses `Literal["keep", "adjust"]` matching spec §4.3

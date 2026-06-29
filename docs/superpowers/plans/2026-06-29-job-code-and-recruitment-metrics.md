# 岗位编号 & 招聘指标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `job_code` (J + 5-digit random unique identifier) and `head_count` (required recruitment headcount) to the Job model, display them in the HR dashboard, show `job_code` to seekers, and update the conversation assistant to support `job_code`-based matching and `interview_quota` write-back.

**Architecture:** Add two new columns to the `jobs` table via Alembic migration, generate `job_code` randomly at creation time, expose through existing API schemas, update frontend types/components, and enhance conversation dispatch logic.

**Tech Stack:** SQLAlchemy 2.0, Alembic, Pydantic v2, FastAPI, React 19, TypeScript, shadcn/ui

## Global Constraints

- Python strict type hints, `mypy --strict` must pass
- SQLAlchemy 2.0 type-annotated style (`Mapped[...] = mapped_column(...)`)
- Pydantic v2 for all DTO/API schemas
- `interview_quota` and `head_count` are required fields (NOT NULL, DEFAULT 1)
- `job_code` format: `J` + 5-digit zero-padded number (J10000–J99999), randomly generated, globally unique, immutable after creation
- Seeker-facing pages show `job_code` but NOT `interview_quota` or `head_count`
- Conversation assistant matches by `job_code` with highest priority

---

### Task 1: Add `job_code` and `head_count` to Job ORM Model

**Files:**
- Modify: `backend/app/models/job.py`

**Interfaces:**
- Produces: `Job.job_code: Mapped[str]`, `Job.head_count: Mapped[int]`; `interview_quota` changes from `Mapped[Optional[int]]` to `Mapped[int]`

- [ ] **Step 1: Update the Job model in `backend/app/models/job.py`**

Change `interview_quota` from nullable to NOT NULL with default 1, add `job_code` and `head_count`:

```python
# After the `status` field (line 44), add:
job_code: Mapped[str] = mapped_column(
    String(6), unique=True, nullable=False, index=True
)   # 格式: J10000 ~ J99999，全局唯一

head_count: Mapped[int] = mapped_column(
    Integer, nullable=False, default=1
)   # 最终招聘人数
```

Change `interview_quota` (line 45) from:
```python
interview_quota: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```
to:
```python
interview_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
```

Ensure the import of `String` is present at the top (it should already be there from the `title` field).

- [ ] **Step 2: Verify model loads without syntax errors**

Run: `cd backend && uv run python -c "from app.models.job import Job; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/job.py
git commit -m "feat: add job_code and head_count to Job model, make interview_quota required"
```

---

### Task 2: Create Alembic Migration

**Files:**
- Create: `backend/alembic/versions/<auto>_add_job_code_and_head_count.py`

**Interfaces:**
- Consumes: `Job` model from Task 1
- Produces: Database schema with `job_code`, `head_count`, NOT NULL `interview_quota`

- [ ] **Step 1: Generate the migration skeleton**

Run: `cd backend && uv run alembic revision --autogenerate -m "add job_code and head_count to jobs"`
This creates a new migration file in `alembic/versions/`.

- [ ] **Step 2: Edit the generated migration to fill existing rows**

Open the generated migration file and edit the `upgrade()` function to:

```python
def upgrade() -> None:
    # 1. Add job_code column (nullable first)
    op.add_column("jobs", sa.Column("job_code", sa.String(6), nullable=True))
    op.add_column("jobs", sa.Column("head_count", sa.Integer(), nullable=True))

    # 2. Assign random unique job_code to existing rows
    import random
    conn = op.get_bind()
    existing_jobs = conn.execute(
        sa.text("SELECT id FROM jobs ORDER BY created_at")
    ).fetchall()
    used_codes: set[str] = set()
    for row in existing_jobs:
        while True:
            num = random.randint(10000, 99999)
            code = f"J{num:05d}"
            if code not in used_codes:
                used_codes.add(code)
                break
        conn.execute(
            sa.text("UPDATE jobs SET job_code = :code WHERE id = :jid"),
            {"code": code, "jid": str(row[0])},
        )

    # 3. Set head_count and interview_quota defaults for existing rows
    conn.execute(
        sa.text("UPDATE jobs SET head_count = 1 WHERE head_count IS NULL")
    )
    conn.execute(
        sa.text("UPDATE jobs SET interview_quota = 1 WHERE interview_quota IS NULL")
    )

    # 4. Make columns NOT NULL
    op.alter_column("jobs", "job_code", nullable=False)
    op.alter_column("jobs", "head_count", nullable=False)
    op.alter_column("jobs", "interview_quota", nullable=False)

    # 5. Add unique constraint and index
    op.create_unique_constraint("uq_jobs_job_code", "jobs", ["job_code"])
    op.create_index("ix_jobs_job_code", "jobs", ["job_code"], unique=False)

    # 6. Set server defaults for future inserts
    op.alter_column("jobs", "head_count", server_default=sa.text("1"))
    op.alter_column("jobs", "interview_quota", server_default=sa.text("1"))
```

Edit `downgrade()`:
```python
def downgrade() -> None:
    op.drop_index("ix_jobs_job_code", table_name="jobs")
    op.drop_constraint("uq_jobs_job_code", "jobs", type_="unique")
    op.alter_column("jobs", "interview_quota", nullable=True, server_default=None)
    op.alter_column("jobs", "head_count", nullable=True, server_default=None)
    op.drop_column("jobs", "head_count")
    op.drop_column("jobs", "job_code")
```

- [ ] **Step 3: Verify migration is syntactically valid**

Run: `cd backend && uv run python -c "import importlib; import alembic.config; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: add migration for job_code, head_count, and required interview_quota"
```

---

### Task 3: Add `job_code` Generation Logic in `job_service.py`

**Files:**
- Modify: `backend/app/services/job_service.py`

**Interfaces:**
- Consumes: `Job` model with `job_code` field from Task 1
- Produces: `create_job()` auto-generates `job_code`; `head_count` and `interview_quota` handled as required fields

- [ ] **Step 1: Add `job_code` generation helper and update `create_job`**

Add this helper function before `create_job` in `backend/app/services/job_service.py`:

```python
import random

async def _generate_job_code(db: AsyncSession) -> str:
    """Generate a random unique job_code (J10000–J99999)."""
    while True:
        num = random.randint(10000, 99999)
        code = f"J{num:05d}"
        result = await db.execute(
            select(Job).where(Job.job_code == code)
        )
        if result.scalar_one_or_none() is None:
            return code
```

Note: `select` and `Job` should already be imported. Add `import random` at the top.

Update the `create_job` function. Currently it creates a Job like:

```python
job = Job(
    recruiter_id=current_user.id,
    title=data.title,
    ...
)
```

Add `job_code` and `head_count` to the Job constructor. The `interview_quota` field should already be there; ensure it's using the required field. The updated Job creation block:

```python
job_code = await _generate_job_code(db)

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
    interview_quota=data.interview_quota,
    head_count=data.head_count,
    job_code=job_code,
)
```

- [ ] **Step 2: Verify syntax**

Run: `cd backend && uv run python -c "from app.services.job_service import create_job; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/job_service.py
git commit -m "feat: auto-generate job_code in create_job service"
```

---

### Task 4: Update Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/job.py`

**Interfaces:**
- Consumes: `Job` model from Task 1
- Produces: `JobCreateRequest.head_count`, `JobCreateRequest.interview_quota` (both required `int`); `JobResponse.job_code`, `JobResponse.head_count`; `JobUpdateRequest.head_count`

- [ ] **Step 1: Update `JobCreateRequest`**

In `backend/app/schemas/job.py`, change `interview_quota` from Optional to required and add `head_count`:

```python
class JobCreateRequest(BaseModel):
    title: str
    description: str
    requirements: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    location: Optional[str] = None
    work_type: Optional[WorkType] = None
    skills_required: list[str] = []
    interview_quota: int = Field(default=1, description="面试人数上限")
    head_count: int = Field(default=1, description="最终招聘人数")
```

- [ ] **Step 2: Update `JobUpdateRequest`**

Add `head_count` as Optional (interview_quota is already Optional there):

```python
class JobUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    location: Optional[str] = None
    work_type: Optional[WorkType] = None
    skills_required: Optional[list[str]] = None
    interview_quota: Optional[int] = None
    head_count: Optional[int] = None
```

- [ ] **Step 3: Update `JobResponse`**

Add `job_code` and `head_count`, change `interview_quota` from Optional to `int`:

```python
class JobResponse(BaseModel):
    id: str
    recruiter_id: str
    title: str
    description: str
    requirements: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    location: Optional[str] = None
    work_type: Optional[WorkType] = None
    skills_required: list[str] = []
    status: Optional[JobStatus] = None
    interview_quota: int = 1
    head_count: int = 1
    job_code: str
    recruiter_name: Optional[str] = None
    applications_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("id", "recruiter_id")
    def serialize_uuids(self, value: Any) -> str:
        return str(value)
```

- [ ] **Step 4: Verify schema loads**

Run: `cd backend && uv run python -c "from app.schemas.job import JobCreateRequest, JobResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/job.py
git commit -m "feat: update job schemas with job_code, head_count, required interview_quota"
```

---

### Task 5: Update `_job_to_dict` in API Layer

**Files:**
- Modify: `backend/app/api/jobs.py`

**Interfaces:**
- Consumes: `JobResponse` schema from Task 4 (expects `job_code`, `head_count`, `interview_quota` as `int`)
- Produces: API responses with all new fields

- [ ] **Step 1: Add `job_code` and `head_count` to `_job_to_dict`**

In `backend/app/api/jobs.py`, update the `_job_to_dict` function to include the new fields:

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
        "interview_quota": job.interview_quota,
        "head_count": job.head_count,
        "job_code": job.job_code,
    }
```

- [ ] **Step 2: Update `job_service.update_job` to handle `head_count`**

In `backend/app/services/job_service.py`, the `update_job` function currently sets fields from `JobUpdateRequest`. Verify it handles `head_count`. The pattern is:

```python
if data.head_count is not None:
    job.head_count = data.head_count
```

Add this alongside the existing `interview_quota` update pattern if not already present.

- [ ] **Step 3: Verify API module loads**

Run: `cd backend && uv run python -c "from app.api.jobs import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/jobs.py backend/app/services/job_service.py
git commit -m "feat: add job_code and head_count to API response, handle head_count in update"
```

---

### Task 6: Update Conversation Assistant — Intent Prompt & Dispatch

**Files:**
- Modify: `backend/app/services/conversation/prompts.py`
- Modify: `backend/app/services/conversation/nodes.py`

**Interfaces:**
- Consumes: `Job.job_code` from Task 1
- Produces: `dispatch_node` supports `job_code` matching with highest priority; `interview_quota` write-back on mismatch; disambiguation messages use `job_code`

- [ ] **Step 1: Update `INTENT_SYSTEM_PROMPT` in `prompts.py`**

In the `extracted_params` description section, add `job_code` as the primary parameter for the `evaluate` intent. Find the section that describes `extracted_params` and add:

```
- job_code: 岗位编号，格式为 J + 5位数字（如 J04217）。如果用户提到岗位编号，必须提取此参数，优先级高于 job_title。
```

Also update the `job_title` description to mention it's secondary to `job_code`:

```
- job_title: 岗位名称（模糊匹配），仅在用户未提供 job_code 时使用。
```

- [ ] **Step 2: Add `job_code` matching in `dispatch_node` in `nodes.py`**

In `backend/app/services/conversation/nodes.py`, update `dispatch_node`. Currently it checks `job_id_param` then `job_title_param`. Add `job_code` matching as the highest priority:

After extracting params (around the existing `job_id_param` and `job_title_param` extraction), add:

```python
job_code_param: str | None = extracted_params.get("job_code")
```

Then add the `job_code` matching branch **before** the `job_id_param` branch:

```python
matched_job = None

# Priority 1: job_code (exact match)
if job_code_param:
    result = await db.execute(
        select(Job).where(Job.job_code == job_code_param)
    )
    matched_job = result.scalar_one_or_none()
    if matched_job and str(matched_job.recruiter_id) != current_user_id:
        return {
            "reply_message": f"你没有岗位 {job_code_param} 的权限。",
            "errors": [],
        }
    if not matched_job:
        return {
            "reply_message": f"未找到编号为 {job_code_param} 的岗位。",
            "errors": [],
        }

# Priority 2: job_id (UUID exact match) — existing logic
if not matched_job and job_id_param:
    # ... existing job_id matching code ...
```

Wrap the existing `job_id_param` and `job_title_param` branches with `if not matched_job and ...` to create the priority chain.

- [ ] **Step 3: Update disambiguation message to show `job_code`**

In the `job_title_param` branch where multiple jobs match (the `len(matching_jobs) > 1` case), change the disambiguation message from showing UUID to showing `job_code`:

Replace the existing list formatting (which shows `title (ID: uuid)`) with:

```python
job_list = "\n".join(
    f"  {i+1}. {j.title} ({j.job_code})"
    for i, j in enumerate(matching_jobs)
)
return {
    "reply_message": f"找到多个匹配岗位，请指定岗位编号：\n{job_list}",
    "errors": [],
}
```

- [ ] **Step 4: Add `interview_quota` write-back before evaluation**

In the dispatch logic, after matching the job and before triggering the evaluation workflow, add write-back logic:

```python
# Write back interview_quota if user specified a different value
user_quota = extracted_params.get("interview_quota")
if user_quota is not None and matched_job.interview_quota != user_quota:
    matched_job.interview_quota = user_quota
    await db.commit()
    await db.refresh(matched_job)
```

Place this after the job is matched and ownership is verified, but before creating the `EvaluationTask`.

- [ ] **Step 5: Update the "no job specified" fallback to show `job_code`**

In the branch where neither `job_code`, `job_id`, nor `job_title` is provided, update the job listing to include `job_code`:

```python
active_jobs = await db.execute(
    select(Job).where(
        Job.recruiter_id == current_user_id,
        Job.status == JobStatus.ACTIVE,
    ).order_by(Job.created_at.desc())
)
jobs_list = active_jobs.scalars().all()
if not jobs_list:
    return {
        "reply_message": "你当前没有活跃的岗位。",
        "errors": [],
    }
job_list = "\n".join(
    f"  {j.job_code} - {j.title}"
    for j in jobs_list
)
return {
    "reply_message": f"请指定要筛选的岗位：\n{job_list}",
    "errors": [],
}
```

- [ ] **Step 6: Verify module loads**

Run: `cd backend && uv run python -c "from app.services.conversation.nodes import dispatch_node; print('OK')"`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/conversation/prompts.py backend/app/services/conversation/nodes.py
git commit -m "feat: conversation assistant supports job_code matching, quota write-back, code-based disambiguation"
```

---

### Task 7: Update Frontend TypeScript Types

**Files:**
- Modify: `frontend/src/features/jobs/types/job.ts`

**Interfaces:**
- Consumes: Backend `JobResponse` schema from Task 4
- Produces: `Job.job_code`, `Job.interview_quota`, `Job.head_count`; `CreateJobPayload.interview_quota`, `CreateJobPayload.head_count`

- [ ] **Step 1: Update `Job` interface**

In `frontend/src/features/jobs/types/job.ts`, add the missing fields to the `Job` interface:

```typescript
export interface Job {
  id: string;
  recruiter_id: string;
  title: string;
  description: string;
  requirements: string;
  salary_min: number | null;
  salary_max: number | null;
  location: string | null;
  work_type: WorkType;
  skills_required: string[];
  status: JobStatus;
  created_at: string;
  updated_at: string;
  recruiter_name?: string;
  applications_count?: number;
  job_code: string;              // 新增：岗位编号
  interview_quota: number;       // 补齐：进面人数
  head_count: number;            // 新增：招聘人数
}
```

- [ ] **Step 2: Update `CreateJobPayload` interface**

Add `interview_quota` and `head_count`:

```typescript
export interface CreateJobPayload {
  title: string;
  description: string;
  requirements: string;
  location?: string;
  work_type?: string;
  salary_min?: number;
  salary_max?: number;
  skills_required: string[];
  interview_quota?: number;      // 新增
  head_count?: number;           // 新增
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: Errors may appear in components using the `Job` type (they don't pass `job_code` etc.) — this is expected and will be fixed in Tasks 8-10. No errors in the type file itself.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/jobs/types/job.ts
git commit -m "feat: add job_code, interview_quota, head_count to frontend Job type"
```

---

### Task 8: Update HR Dashboard — Add Table Columns

**Files:**
- Modify: `frontend/src/pages/JobDashboardPage.tsx`

**Interfaces:**
- Consumes: `Job.job_code`, `Job.interview_quota`, `Job.head_count` from Task 7

- [ ] **Step 1: Add columns to the job table**

In `JobDashboardPage.tsx`, find the table header and body section (around lines 229-236). Add three new columns.

In the table header (`<TableHead>` row), add after the "岗位名称" column:

```tsx
<TableHead className="w-[100px]">岗位编号</TableHead>
```

After the "状态" column:

```tsx
<TableHead className="text-center w-[90px]">进面人数</TableHead>
<TableHead className="text-center w-[90px]">招聘人数</TableHead>
```

In the table body (`<TableCell>` row), add the corresponding cells:

After the title cell (`job.title`):
```tsx
<TableCell className="font-mono text-muted-foreground text-sm">
  {job.job_code}
</TableCell>
```

After the status cell (`<JobStatusBadge>`):
```tsx
<TableCell className="text-center">{job.interview_quota}</TableCell>
<TableCell className="text-center">{job.head_count}</TableCell>
```

- [ ] **Step 2: Verify the page compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "JobDashboardPage" || echo "No errors in JobDashboardPage"`
Expected: No errors related to JobDashboardPage

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/JobDashboardPage.tsx
git commit -m "feat: add job_code, interview_quota, head_count columns to HR dashboard"
```

---

### Task 9: Update JobCard (Seeker) — Show `job_code`

**Files:**
- Modify: `frontend/src/shared/ui/JobCard.tsx`

**Interfaces:**
- Consumes: `Job.job_code` from Task 7

- [ ] **Step 1: Add `job_code` display to JobCard**

In `frontend/src/shared/ui/JobCard.tsx`, add the job code next to the job title. After the `<h3>` line (line 31):

```tsx
<h3 className="text-lg font-semibold">{job.title}</h3>
<p className="text-xs text-muted-foreground font-mono">{job.job_code}</p>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/shared/ui/JobCard.tsx
git commit -m "feat: show job_code in seeker JobCard"
```

---

### Task 10: Update JobDetailPage — Show `job_code`

**Files:**
- Modify: `frontend/src/pages/JobDetailPage.tsx`

**Interfaces:**
- Consumes: `Job.job_code` from Task 7

- [ ] **Step 1: Add `job_code` display to JobDetailPage**

In `frontend/src/pages/JobDetailPage.tsx`, in the header section (around line 126), after the `<h1>` tag showing `job.title`, add the job code:

```tsx
<h1 className="text-2xl font-bold">{job.title}</h1>
<p className="text-sm text-muted-foreground font-mono">{job.job_code}</p>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/JobDetailPage.tsx
git commit -m "feat: show job_code in JobDetailPage"
```

---

### Task 11: Update PostJobPage — Add `interview_quota` and `head_count` Fields

**Files:**
- Modify: `frontend/src/pages/PostJobPage.tsx`

**Interfaces:**
- Consumes: `CreateJobPayload` from Task 7

- [ ] **Step 1: Update the Zod schema to include `interview_quota` and `head_count`**

In `PostJobPage.tsx`, add to the `jobSchema`:

```typescript
const jobSchema = z.object({
  title: z.string().min(1, "岗位名称不能为空"),
  description: z.string().min(10, "岗位描述至少10字"),
  requirements: z.string().min(1, "任职要求不能为空"),
  location: z.string().optional(),
  work_type: z.enum(["remote", "onsite", "hybrid"]).optional(),
  salary_min: z.number({ message: "请输入数字" }).optional(),
  salary_max: z.number({ message: "请输入数字" }).optional(),
  interview_quota: z.number({ message: "请输入数字" }).min(1, "至少为1").default(1),
  head_count: z.number({ message: "请输入数字" }).min(1, "至少为1").default(1),
});
```

- [ ] **Step 2: Add default values for the new fields**

In the `useForm` defaultValues, add:

```typescript
defaultValues: {
  work_type: "onsite",
  requirements: "",
  interview_quota: 1,
  head_count: 1,
},
```

- [ ] **Step 3: Add form fields in the "基本信息" Card section**

After the salary grid (around line 196), add a new grid row:

```tsx
<div className="grid grid-cols-2 gap-4">
  <div>
    <Label htmlFor="interview_quota">
      进面人数 <span className="text-destructive">*</span>
    </Label>
    <Input
      id="interview_quota"
      type="number"
      {...register("interview_quota", { valueAsNumber: true })}
      className="mt-1.5"
      placeholder="例如：5"
      min={1}
    />
    {formState.errors.interview_quota && (
      <p className="text-sm text-destructive mt-1">{formState.errors.interview_quota.message}</p>
    )}
  </div>
  <div>
    <Label htmlFor="head_count">
      招聘人数 <span className="text-destructive">*</span>
    </Label>
    <Input
      id="head_count"
      type="number"
      {...register("head_count", { valueAsNumber: true })}
      className="mt-1.5"
      placeholder="例如：2"
      min={1}
    />
    {formState.errors.head_count && (
      <p className="text-sm text-destructive mt-1">{formState.errors.head_count.message}</p>
    )}
  </div>
</div>
```

- [ ] **Step 4: Update the `onSubmit` payload**

The `onSubmit` already spreads `...data`, which now includes `interview_quota` and `head_count`. The payload construction should still work:

```typescript
const payload = {
  ...data,
  skills_required: skills,
};
```

- [ ] **Step 5: Verify the page compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -i "PostJobPage" || echo "No errors in PostJobPage"`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PostJobPage.tsx
git commit -m "feat: add interview_quota and head_count fields to PostJobPage form"
```

---

### Task 12: Update Backend Tests

**Files:**
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_jobs_api.py`

**Interfaces:**
- Consumes: Required `interview_quota` and `head_count` fields from Tasks 3-4

- [ ] **Step 1: Update `conftest.py` job creation payloads**

In the `recruiter_with_job` fixture (line 172-183), the existing job creation payload already includes `interview_quota: 2`. Add `head_count: 1`:

```python
resp = await client.post(
    "/api/jobs/",
    json={
        "title": "高级前端工程师",
        "description": "负责公司核心产品的前端开发工作",
        "skills_required": ["React", "TypeScript", "CSS"],
        "location": "北京",
        "work_type": "onsite",
        "interview_quota": 2,
        "head_count": 1,
    },
    headers=recruiter_headers,
)
```

- [ ] **Step 2: Update `test_jobs_api.py` job creation payloads**

Find all `json={...}` blocks that create jobs and ensure they include `interview_quota` and `head_count`. Since both have defaults (1), they are optional in the API request — but add them explicitly for clarity in test assertions:

In `test_create_job_as_recruiter` (line 10-22), add assertions:

```python
assert data["job_code"].startswith("J")
assert len(data["job_code"]) == 6
assert data["interview_quota"] == 1  # default
assert data["head_count"] == 1       # default
```

- [ ] **Step 3: Add a test for `job_code` uniqueness**

Add a new test:

```python
@pytest.mark.asyncio
async def test_job_code_is_unique_and_auto_generated(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """Two jobs should get different job_codes"""
    resp1 = await client.post(
        "/api/jobs/",
        json={
            "title": "岗位A",
            "description": "描述A，至少十个字",
            "skills_required": [],
        },
        headers=auth_headers_recruiter,
    )
    resp2 = await client.post(
        "/api/jobs/",
        json={
            "title": "岗位B",
            "description": "描述B，至少十个字",
            "skills_required": [],
        },
        headers=auth_headers_recruiter,
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    code1 = resp1.json()["job_code"]
    code2 = resp2.json()["job_code"]
    assert code1 != code2
    assert code1.startswith("J") and len(code1) == 6
    assert code2.startswith("J") and len(code2) == 6
```

- [ ] **Step 4: Add a test for `head_count` and `interview_quota` as required**

```python
@pytest.mark.asyncio
async def test_create_job_with_custom_quota_and_headcount(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """Creating a job with explicit interview_quota and head_count"""
    resp = await client.post(
        "/api/jobs/",
        json={
            "title": "岗位C",
            "description": "描述C，至少十个字",
            "interview_quota": 5,
            "head_count": 3,
        },
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["interview_quota"] == 5
    assert data["head_count"] == 3
```

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_jobs_api.py -v 2>&1 | tail -20`
Expected: New tests pass. Pre-existing failures may still occur (MissingGreenlet issues).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_jobs_api.py
git commit -m "test: add tests for job_code uniqueness, head_count, and interview_quota"
```

---

### Task 13: Update `skeleton.md`

**Files:**
- Modify: `skeleton.md`

**Interfaces:**
- Consumes: All changes from Tasks 1-6

- [ ] **Step 1: Update Job model section**

In `skeleton.md`, find the `Job` model definition and add:

```python
job_code:          Mapped[str]             # String(6), unique, indexed; 格式 J10000~J99999
head_count:        Mapped[int]             # 最终招聘人数, default=1
```

Change `interview_quota` line from:
```
interview_quota:   Mapped[int | None]  # 面试人数上限
```
to:
```
interview_quota:   Mapped[int]            # 面试人数上限, default=1
```

- [ ] **Step 2: Update Job DTO section**

In the `job.py` schemas table, update:
- `JobCreateRequest`: add `head_count?`, note `interview_quota` is now required with default
- `JobUpdateRequest`: add `head_count?`
- `JobResponse`: add `job_code`, `head_count`; change `interview_quota` to non-optional

- [ ] **Step 3: Update TypeScript type section**

In the frontend `job.ts` types, update the `Job` interface to include `job_code`, `interview_quota`, `head_count`.

- [ ] **Step 4: Commit**

```bash
git add skeleton.md
git commit -m "docs: update skeleton.md with job_code, head_count, required interview_quota"
```

---

### Task 14: Run mypy and Final Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run mypy strict check**

Run: `cd backend && uv run mypy --strict app/ 2>&1`
Expected: No errors related to our changes. Pre-existing warnings may exist.

- [ ] **Step 2: Run all backend tests**

Run: `cd backend && uv run pytest tests/ -v 2>&1 | tail -30`
Expected: Our new tests pass. Pre-existing failures are documented and known.

- [ ] **Step 3: Run frontend TypeScript check**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: No errors

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: address type check and test issues from job_code implementation"
```

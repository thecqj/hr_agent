# Card Alignment & Applicant Count Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two frontend bugs — job card buttons misaligned due to uneven content height, and HR dashboard always showing 0 applicants.

**Architecture:** Issue 1 is a single-line CSS fix (`flex-1` on CardContent). Issue 2 requires eager-loading the `applications` relationship in the job service queries and replacing the hardcoded `0` in `_job_to_dict` with `len(job.applications)`.

**Tech Stack:** React 19 + Tailwind CSS v4 (frontend), FastAPI + SQLAlchemy async (backend)

## Global Constraints

- `applications_count` field in `JobResponse` schema (`backend/app/schemas/job.py:54`) defaults to `0` — the schema default stays, but the API must return the real count
- `Job.applications` relationship already exists on the model (`backend/app/models/job.py:47-51`)
- `Card` base component uses `flex flex-col` (`frontend/src/components/ui/card.tsx:15`)
- Backend tests use `pytest-asyncio` with PostgreSQL test database at `postgresql+psycopg://app:password@localhost:5432/jobboard_test`

---

### Task 1: Fix JobCard button alignment

**Files:**
- Modify: `frontend/src/shared/ui/JobCard.tsx:30`

**Interfaces:**
- Consumes: `Card` component with `h-full flex flex-col` layout (from shadcn/ui)
- Produces: JobCard with aligned buttons across all cards in the same grid row

- [ ] **Step 1: Add `flex-1` to CardContent**

In `frontend/src/shared/ui/JobCard.tsx`, change line 30:

```diff
- <CardContent className="p-6">
+ <CardContent className="p-6 flex-1">
```

This makes the content area grow to fill remaining vertical space in the `flex flex-col` Card, pushing the button `<div>` to the bottom of every card. Since the CSS Grid (`grid gap-6 md:grid-cols-2 lg:grid-cols-3` in `JobMarketPage.tsx:118`) already makes all cards in a row equal height, `flex-1` ensures buttons align at the same vertical position.

- [ ] **Step 2: Verify with TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Visual verification**

Run: `cd frontend && npm run dev`
Open the Job Market page in browser. Verify that all "立即投递" / "已投递" buttons align at the same height within each row, regardless of whether cards have salary, skills, or description content.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/ui/JobCard.tsx
git commit -m "fix: align job card buttons by adding flex-1 to CardContent"
```

---

### Task 2: Fix applications_count always returning 0

**Files:**
- Modify: `backend/app/services/job_service.py:38-44,60`
- Modify: `backend/app/api/jobs.py:21-37`

**Interfaces:**
- Consumes: `Job.applications` relationship (defined in `backend/app/models/job.py:47-51`), `selectinload` from `sqlalchemy.orm`
- Produces: `_job_to_dict` returns real `applications_count` value; service queries eager-load the relationship

- [ ] **Step 1: Add selectinload to job_service.py queries**

In `backend/app/services/job_service.py`, add the import and eager-load the `applications` relationship in both `get_job` and `list_jobs`:

At the top of the file, add to the existing imports (after line 4):

```python
from sqlalchemy.orm import selectinload
```

In `get_job` (line 40), change the query to eager-load applications:

```diff
-     result = await db.execute(select(Job).where(Job.id == job_id))
+     result = await db.execute(select(Job).where(Job.id == job_id).options(selectinload(Job.applications)))
```

In `list_jobs` (line 60), add `.options(selectinload(Job.applications))` after `select(Job)`:

```diff
-     query = select(Job)
+     query = select(Job).options(selectinload(Job.applications))
```

- [ ] **Step 2: Replace hardcoded 0 in _job_to_dict**

In `backend/app/api/jobs.py`, change line 36 in `_job_to_dict`:

```diff
-         "applications_count": 0,
+         "applications_count": len(job.applications) if hasattr(job, "applications") and job.applications is not None else 0,
```

The `hasattr`/`None` guard handles edge cases where `selectinload` was not applied (e.g., `create_job` returns a fresh job before applications are loaded — in that case, the relationship may not be populated, so we safely fall back to `0`).

- [ ] **Step 3: Write a backend test for applications_count**

Add the following test to `backend/tests/test_jobs_api.py`:

```python
@pytest.mark.asyncio
async def test_applications_count_reflects_real_count(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """岗位的 applications_count 应反映实际投递数"""
    # 1. 招聘者创建岗位
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "计数测试", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]
    # 新建岗位 applications_count 应为 0
    assert create_resp.json()["applications_count"] == 0

    # 2. 注册求职者并投递
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "count_seeker@test.com",
            "password": "testpass123",
            "name": "计数求职者",
            "role": "job_seeker",
        },
    )
    seeker_token = reg_resp.json()["access_token"]
    seeker_headers = {"Authorization": f"Bearer {seeker_token}"}

    apply_resp = await client.post(
        "/api/v1/applications/",
        json={"job_id": job_id, "resume_text": "测试简历"},
        headers=seeker_headers,
    )
    assert apply_resp.status_code == 201

    # 3. 招聘者再次查询岗位列表，applications_count 应为 1
    list_resp = await client.get(
        "/api/v1/jobs/",
        params={"status": "all"},
        headers=auth_headers_recruiter,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    target = next((j for j in items if j["id"] == job_id), None)
    assert target is not None
    assert target["applications_count"] == 1

    # 4. 查询岗位详情，applications_count 也应为 1
    detail_resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["applications_count"] == 1
```

- [ ] **Step 4: Run backend tests**

Run: `cd backend && python3 -m pytest tests/test_jobs_api.py -v`
Expected: All tests pass, including the new `test_applications_count_reflects_real_count`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/job_service.py backend/app/api/jobs.py backend/tests/test_jobs_api.py
git commit -m "fix: return real applications_count instead of hardcoded 0"
```

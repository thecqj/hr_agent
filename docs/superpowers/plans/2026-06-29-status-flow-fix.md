# Status Flow Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the unused `reviewed` application status (replacing with `interview`) and block re-application for rejected candidates.

**Architecture:** Backend enum removal + Alembic data migration + frontend type/tab/button updates + backend 403 guard for rejected re-applications. The two changes are loosely coupled (they touch different code paths) but share the `ApplicationStatus` type, so they're sequenced: remove `reviewed` first, then add the rejected guard.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.0 / Alembic / Pydantic v2 (backend); React 19 / TypeScript / react-hook-form / TanStack Query / Tailwind CSS (frontend)

## Global Constraints

- ApplicationStatus enum values after this change: `pending`, `interview`, `rejected`, `hired` (4 values, no `reviewed`)
- All existing `status='reviewed'` database rows migrate to `status='interview'`
- HR manual "通过" button sets status to `interview` (not `reviewed`)
- Rejected applicants receive HTTP 403 on re-apply attempt; other statuses still get HTTP 409 (force-overwrite allowed)
- Frontend `APPLICATION_STATUS_MAP` has 4 entries (no `reviewed`)
- ApplicantsPage filter tabs: 全部 / 待审核 / 面试中 / 已拒绝 / 已录用
- MyApplicationsPage filter tabs: same set, auto-generated from `APPLICATION_STATUS_MAP`
- JobDetailPage: rejected applicants see disabled red "已拒绝" button; other applied statuses see disabled grey "已投递"
- ApplyPage: HTTP 403 → toast error, no override dialog; HTTP 409 → existing override dialog unchanged
- Alembic `down_revision = '9d45e7aca4fb'` (latest existing migration)

---

### Task 1: Backend — Remove `REVIEWED` from ApplicationStatus enum + Alembic migration

**Files:**
- Modify: `backend/app/models/application.py:13-18`
- Create: `backend/alembic/versions/a1b2c3d4e5f6_remove_reviewed_status.py`

**Interfaces:**
- Consumes: Existing `ApplicationStatus` enum
- Produces: `ApplicationStatus` with 4 values (`pending`, `interview`, `rejected`, `hired`); Alembic migration that converts `reviewed` → `interview`

- [ ] **Step 1: Remove `REVIEWED` from the enum**

In `backend/app/models/application.py`, change the `ApplicationStatus` enum from:

```python
class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"        # 待查看
    REVIEWED = "reviewed"      # 已查看
    INTERVIEW = "interview"    # 面试中
    REJECTED = "rejected"      # 不合适
    HIRED = "hired"            # 已录用
```

to:

```python
class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"        # 待审核
    INTERVIEW = "interview"    # 面试中
    REJECTED = "rejected"      # 已拒绝
    HIRED = "hired"            # 已录用
```

- [ ] **Step 2: Create Alembic migration**

Create `backend/alembic/versions/a1b2c3d4e5f6_remove_reviewed_status.py`:

```python
"""remove reviewed status

Revision ID: a1b2c3d4e5f6
Revises: 9d45e7aca4fb
Create Date: 2026-06-29 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9d45e7aca4fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate existing reviewed records to interview
    op.execute("UPDATE applications SET status = 'interview' WHERE status = 'reviewed'")


def downgrade() -> None:
    # Cannot automatically reverse — reviewed status has been removed
    pass
```

- [ ] **Step 3: Verify no other backend code references `"reviewed"` or `REVIEWED`**

Run: `grep -rn "reviewed\|REVIEWED" backend/app/ --include="*.py"`
Expected: No hits (the enum value is gone, and no other code hardcodes `"reviewed"`)

- [ ] **Step 4: Run mypy type check**

Run: `cd backend && uv run mypy --strict app/`
Expected: No errors related to `ApplicationStatus`

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/application.py backend/alembic/versions/a1b2c3d4e5f6_remove_reviewed_status.py
git commit -m "feat: remove reviewed status from ApplicationStatus enum, migrate to interview"
```

---

### Task 2: Frontend — Remove `reviewed` from status types and UI tabs

**Files:**
- Modify: `frontend/src/shared/constants/applicationStatus.ts`
- Modify: `frontend/src/pages/ApplicantsPage.tsx:45-50,367`
- Modify: `frontend/src/pages/MyApplicationsPage.tsx:27-33`

**Interfaces:**
- Consumes: `ApplicationStatus` type from `applicationStatus.ts`
- Produces: Updated `ApplicationStatus` type (4 values), `APPLICATION_STATUS_MAP` (4 entries), updated filter tabs

- [ ] **Step 1: Update `applicationStatus.ts`**

In `frontend/src/shared/constants/applicationStatus.ts`, change from:

```typescript
export type ApplicationStatus = "pending" | "reviewed" | "interview" | "rejected" | "hired";
```

to:

```typescript
export type ApplicationStatus = "pending" | "interview" | "rejected" | "hired";
```

And remove the `reviewed` entry from `APPLICATION_STATUS_MAP`:

```typescript
export const APPLICATION_STATUS_MAP: Record<ApplicationStatus, StatusStyle> = {
  pending: {
    label: "待审核",
    className: "bg-amber-100 text-amber-800 hover:bg-amber-100/80",
  },
  interview: {
    label: "面试中",
    className: "bg-indigo-100 text-indigo-800 hover:bg-indigo-100/80",
  },
  rejected: {
    label: "已拒绝",
    className: "bg-red-100 text-red-800 hover:bg-red-100/80",
  },
  hired: {
    label: "已录用",
    className: "bg-green-100 text-green-800 hover:bg-green-100/80",
  },
};
```

- [ ] **Step 2: Update ApplicantsPage filter tabs and "通过" button**

In `frontend/src/pages/ApplicantsPage.tsx`, change `STATUS_CATEGORIES` (lines 45-50) from:

```typescript
const STATUS_CATEGORIES = [
  { key: "all", label: "全部" },
  { key: "pending", label: "待审核" },
  { key: "reviewed", label: "已审阅" },
  { key: "rejected", label: "已拒绝" },
];
```

to:

```typescript
const STATUS_CATEGORIES = [
  { key: "all", label: "全部" },
  { key: "pending", label: "待审核" },
  { key: "interview", label: "面试中" },
  { key: "rejected", label: "已拒绝" },
  { key: "hired", label: "已录用" },
];
```

Change the "通过" button (line 367) from:

```tsx
onClick={() => updateStatus(app.id, "reviewed")}
```

to:

```tsx
onClick={() => updateStatus(app.id, "interview")}
```

- [ ] **Step 3: Verify MyApplicationsPage auto-updates**

`MyApplicationsPage.tsx` generates its `STATUS_CATEGORIES` from `APPLICATION_STATUS_MAP` (lines 27-33):

```typescript
const STATUS_CATEGORIES = [
  { key: "all" as const, label: "全部" },
  ...Object.entries(APPLICATION_STATUS_MAP).map(([key, val]) => ({
    key: key as ApplicationStatus,
    label: val.label,
  })),
];
```

Since this is derived from `APPLICATION_STATUS_MAP`, removing the `reviewed` entry in Step 1 automatically removes the "已审阅" tab. No code change needed here.

- [ ] **Step 4: Verify no other frontend code references `"reviewed"`**

Run: `grep -rn '"reviewed"' frontend/src/ --include="*.ts" --include="*.tsx"`
Expected: No hits

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/constants/applicationStatus.ts frontend/src/pages/ApplicantsPage.tsx
git commit -m "feat: remove reviewed status from frontend types, tabs, and buttons"
```

---

### Task 3: Backend — Add 403 guard for rejected re-applications

**Files:**
- Modify: `backend/app/services/application_service.py:36-41`

**Interfaces:**
- Consumes: `ApplicationStatus.REJECTED` from updated enum (Task 1)
- Produces: `create_application` returns HTTP 403 when existing app status is `REJECTED`

- [ ] **Step 1: Add rejected-status check in `create_application`**

In `backend/app/services/application_service.py`, replace lines 36-41:

```python
    if existing_app:
        if not force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="您已投递过该岗位，是否覆盖原简历？",
            )
```

with:

```python
    if existing_app:
        if existing_app.status == ApplicationStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="该岗位已拒绝您的投递，无法再次申请",
            )
        if not force:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="您已投递过该岗位，是否覆盖原简历？",
            )
```

The logic order matters: check rejected FIRST (hard block), then check force flag (soft block with override).

- [ ] **Step 2: Run mypy type check**

Run: `cd backend && uv run mypy --strict app/`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/application_service.py
git commit -m "feat: block re-application for rejected candidates (HTTP 403)"
```

---

### Task 4: Frontend — Differentiate rejected vs applied button on JobDetailPage + handle 403 on ApplyPage

**Files:**
- Modify: `frontend/src/pages/JobDetailPage.tsx:35-42,182-192`
- Modify: `frontend/src/pages/ApplyPage.tsx:228-234`

**Interfaces:**
- Consumes: `MyApplication` type from `features/applications/types/application`; `createApplication` API that may return 403
- Produces: JobDetailPage shows distinct button for rejected applications; ApplyPage shows toast for 403

- [ ] **Step 1: Update JobDetailPage to find the specific application and check status**

In `frontend/src/pages/JobDetailPage.tsx`, change the `hasApplied` logic (lines 35-42) from:

```typescript
  const isJobSeeker = user?.role === "job_seeker";
  const { data: applicationsData } = useMyApplicationsQuery(
    { page: 1, page_size: 100 },
    { enabled: isJobSeeker }
  );
  const hasApplied = isJobSeeker
    ? (applicationsData?.items ?? []).some((app) => app.job_id === id)
    : false;
```

to:

```typescript
  const isJobSeeker = user?.role === "job_seeker";
  const { data: applicationsData } = useMyApplicationsQuery(
    { page: 1, page_size: 100 },
    { enabled: isJobSeeker }
  );
  const myApplication = isJobSeeker
    ? (applicationsData?.items ?? []).find((app) => app.job_id === id)
    : undefined;
  const hasApplied = myApplication != null;
  const isRejected = myApplication?.status === "rejected";
```

Then change the button section (lines 182-192) from:

```tsx
              {!isRecruiter && (
                hasApplied ? (
                  <Button size="lg" variant="secondary" disabled>
                    已投递
                  </Button>
                ) : (
                  <Button size="lg" onClick={handleApply}>
                    立即投递
                  </Button>
                )
              )}
```

to:

```tsx
              {!isRecruiter && (
                isRejected ? (
                  <Button size="lg" variant="destructive" disabled>
                    已拒绝
                  </Button>
                ) : hasApplied ? (
                  <Button size="lg" variant="secondary" disabled>
                    已投递
                  </Button>
                ) : (
                  <Button size="lg" onClick={handleApply}>
                    立即投递
                  </Button>
                )
              )}
```

- [ ] **Step 2: Update ApplyPage to handle 403 response**

In `frontend/src/pages/ApplyPage.tsx`, change the catch block (around lines 228-234) from:

```typescript
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        setShowConfirm(true);
      } else {
        toast.error(getApiErrorMessage(error, "投递失败"));
      }
    }
```

to:

```typescript
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        setShowConfirm(true);
      } else if (axios.isAxiosError(error) && error.response?.status === 403) {
        toast.error(error.response.data?.detail || "该岗位已拒绝您的投递，无法再次申请");
      } else {
        toast.error(getApiErrorMessage(error, "投递失败"));
      }
    }
```

- [ ] **Step 3: Verify no other frontend code references the old 409-only pattern**

Run: `grep -n "409" frontend/src/pages/ApplyPage.tsx`
Expected: Only the existing 409 check remains (now alongside 403)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/JobDetailPage.tsx frontend/src/pages/ApplyPage.tsx
git commit -m "feat: show rejected button on JobDetailPage, handle 403 on ApplyPage"
```

---

### Task 5: Update skeleton.md and design spec

**Files:**
- Modify: `docs/skeleton.md` (if it references `reviewed` status)

**Interfaces:**
- Consumes: All previous tasks
- Produces: Updated documentation

- [ ] **Step 1: Check skeleton.md for reviewed references**

Run: `grep -n "reviewed" docs/skeleton.md`
If hits found, update those references to reflect the 4-value enum (`pending`, `interview`, `rejected`, `hired`).

- [ ] **Step 2: Commit**

```bash
git add docs/skeleton.md
git commit -m "docs: update skeleton.md to reflect reviewed status removal"
```

(If no changes needed, skip this commit.)

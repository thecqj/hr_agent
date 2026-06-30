# HR Agent — Detail Polish Design

**Date:** 2026-06-27
**Scope:** 8 UI/UX fixes and feature enhancements across HR and Job-Seeker interfaces

---

## Overview

This spec covers detail-level improvements to the HR Agent application, split across two user roles:

| # | Role | Item | Nature |
|---|------|------|--------|
| HR-1 | HR | 已审阅 tab always empty | Bug fix |
| HR-2 | HR | 任职要求 (requirements) — required field, shown everywhere, feeds AI evaluation | Full-stack feature |
| HR-3 | HR | Resume dialog — sticky header (name + status + close) | UI fix |
| HR-4 | HR | Chat bubble draggable (snap-to-edge), chat window resizable + freely movable | UX enhancement |
| SK-1 | Seeker | My Applications detail — show full structured resume instead of summary | Frontend fix |
| SK-2 | Seeker | Job detail page — show actual requirements field (same as HR-2) | Covered by HR-2 |
| SK-3 | Seeker | Already-applied jobs still clickable from market; detail page shows disabled "已投递" | Frontend fix |
| SK-4a | Seeker | Tech stack input loses focus on every keystroke | Bug fix |
| SK-4b | Seeker | Education field required (min 1 entry) | Validation change |

**Implementation strategy:** Single pass, ordered by dependency (backend → data layer → UI).

---

## Section 1: Backend — `requirements` Field & 已审阅 Fix

### 1.1 `requirements` (任职要求) — New Text Field

**DB Migration** (`add_requirements_to_jobs.py`):
- Add `requirements` column: `sa.Column('requirements', sa.Text(), nullable=True)`
- Backfill existing rows with empty string: `op.execute("UPDATE jobs SET requirements = '' WHERE requirements IS NULL")`
- Make NOT NULL: `op.alter_column('jobs', 'requirements', nullable=False)`

**ORM Model** (`backend/app/models/job.py`):
```python
requirements: Mapped[str] = mapped_column(Text, nullable=False, default="")
```

**Pydantic Schemas** (`backend/app/schemas/job.py`):
- `JobCreateRequest`: `requirements: str = Field(..., min_length=1, description="任职要求")`
- `JobUpdateRequest`: `requirements: Optional[str] = Field(None, min_length=1, description="任职要求")`
- `JobResponse`: `requirements: str`

**API** (`backend/app/api/jobs.py`):
- `POST /jobs` — Pydantic enforces `requirements` is non-empty
- `PUT /jobs/{id}` — accepts optional `requirements` updates

**AI Evaluation Integration:**
- Update the evaluation prompt in `backend/app/services/agent/prompts.py` to inject `job.requirements` as the primary evaluation standard
- Keep `skills_required` as supplementary context
- The `requirement_vector` (pgvector embedding) should be updated to embed `requirements` text instead of just `skills_required`

### 1.2 已审阅 Tab Bug

**Root cause investigation:**
The frontend filter logic (`ApplicantsPage.tsx:70-73`) is correct — it filters `allApplicants` by `status === "reviewed"`. The bug is likely in the API layer:
- `GET /applications/job/{job_id}` may not be returning applications with `status="reviewed"`, OR
- The status update to `"reviewed"` (via "通过" button) is not persisting correctly

**Fix approach:** Read the API endpoint query in `backend/app/api/applications.py` during implementation, identify the filter/query issue, and fix it.

---

## Section 2: Frontend — `requirements` Field Integration

### Type Update

`frontend/src/features/jobs/types/job.ts`:
- Add `requirements: string` to the `Job` type

### PostJobPage (`pages/PostJobPage.tsx`)

- Register the "任职要求" textarea with react-hook-form (currently commented out: "no register — this field is not in the current API")
- Mark as required with `*` indicator
- Add `requirements` to `CreateJobPayload` type

### JobDetailPage (`pages/JobDetailPage.tsx`)

- Replace the current fake requirements rendering:
  ```
  熟悉或掌握以下技能：${job.skills_required.join("、")}
  ```
  with actual `job.requirements` text
- Fallback: if `requirements` is empty, show skills_required as a secondary list

### JobDashboardPage (`pages/JobDashboardPage.tsx`)

- Add "任职要求" section to the job detail dialog (alongside existing description and skills display)

### EvaluationResultPage

No change needed — this page shows candidate evaluation results, not job requirements.

---

## Section 3: Resume Dialog — Sticky Header

### ApplicantsPage (`pages/ApplicantsPage.tsx`)

**Current:** The entire dialog content (including `DialogHeader` with name + StatusBadge) scrolls together inside `DialogContent` with `overflow-y-auto`.

**Fix:** Restructure the dialog so the header stays fixed at the top while the body scrolls:

```
DialogContent (flex-col, max-h-[85vh])
├── DialogHeader (sticky top, border-b, shrink-0) — name + StatusBadge
└── Scrollable div (overflow-y-auto, flex-1) — all resume sections
```

- The close button is already handled by shadcn's `DialogContent` (X button in top-right), which stays fixed automatically
- Add `shrink-0` to header, `flex-1 overflow-y-auto` to body container

---

## Section 4: Chat Widget — Drag + Resize + Move

### 4.1 ChatBubble — Draggable with Snap-to-Edge

**Current:** Fixed at `bottom-6 right-6`

**New behavior:**
- User can drag the bubble horizontally along the screen edges (left/right)
- On release: smooth CSS transition to snap to the nearest edge (left or right)
- Only horizontal dragging — Y position stays at bottom
- Position persisted in `localStorage` (key: `chat-bubble-position`)
- On page load: read from localStorage, default to right-6

**Implementation:**
- State: `position: { x: number }` (relative to viewport)
- Mouse handlers: `onMouseDown` on the bubble → track `isDragging`, update `x` on `mousemove`, snap on `mouseup`
- Touch handlers: same pattern for mobile (`touchstart` / `touchmove` / `touchend`)
- Snap animation: CSS `transition: left 0.3s ease` applied only on release (not during drag)
- Constraint: `x` clamped to `[24, viewportWidth - 24 - buttonSize]`

### 4.2 ChatWindow — Freely Movable + Resizable

**Current:** 380×520px popup, `absolute bottom-16 right-0`, positioned relative to bubble

**New behavior:**
- Window can be dragged anywhere on screen by its title bar
- Window can be resized via a bottom-right corner handle
- Size constraints: min 320×400, max 800×700
- Position/size persisted in `localStorage` (key: `chat-window-state`)
- Default position: above the bubble
- Window must stay within viewport bounds

**Implementation:**
- Change from `absolute` to `position: fixed` — window positions relative to viewport
- State: `position: { x, y }`, `size: { width, height }`
- Move: `onMouseDown` on header → track drag delta, update position
- Resize: `onMouseDown` on corner handle → track delta, update size (clamped to min/max)
- Touch support for both move and resize
- Boundary constraint: position adjusted so window never goes off-screen

---

## Section 5: Seeker-Side Fixes

### 5.1 My Applications Detail — Full Structured Resume

**MyApplicationsPage** (`pages/MyApplicationsPage.tsx`):

**Current:** Detail dialog shows `resume_text` (plain text) with `line-clamp-6` truncation.

**New:** Render `structured_resume` using the same sectioned layout as the HR ApplicantsPage resume dialog:
- 基本信息 (name, work years, education level)
- 联系方式 (phone/email/wechat/other)
- 工作经历 (company, position, dates, description)
- 项目经历 (name, role, dates, description, technologies badges)
- 教育经历 (school, major, degree, dates)
- 资格证书 (badge list)
- 专业技能 (badge list)
- 自我评价 (plain text)
- Fallback: if `structured_resume` is null, show `resume_text` as before
- Keep "查看岗位详情" button at the bottom

The `MyApplication` type already includes `structured_resume` — no API changes needed.

### 5.2 Already-Applied Jobs in Job Market

**Current behavior (JobCard):** The card body (`<Link>`) is always clickable and navigates to `/jobs/${id}`. The bottom button changes to a disabled "已投递" when `applied=true`. **This already works as requested.**

**Missing piece (JobDetailPage):** The detail page does not check whether the user has already applied. The "立即投递" button is always enabled.

**Fix:**
- In `JobDetailPage`, fetch the user's application data (same pattern as `JobMarketPage` — `useMyApplicationsQuery`)
- Check if `appliedJobIds.has(job.id)`
- If already applied: replace "立即投递" button with disabled "已投递" button (same style as JobCard)
- Do NOT allow re-application

### 5.3 Tech Stack Input — Fix Focus Loss

**Root cause:** `ApplyPage.tsx:443-449` uses `defaultValue` + `form.setValue` for the technology input. Each keystroke triggers `form.setValue` → re-render → input loses focus because `defaultValue` only applies on mount and React re-reconciles the element.

**Fix:** Replace with React Hook Form `Controller` for proper controlled component behavior:

```tsx
import { Controller } from "react-hook-form";

<Controller
  control={form.control}
  name={`project_experience.${index}.technologies`}
  render={({ field }) => (
    <Input
      placeholder="React, TypeScript, Node.js"
      value={field.value?.join(", ") ?? ""}
      onChange={(e) => {
        field.onChange(e.target.value.split(",").map(s => s.trim()).filter(Boolean));
      }}
    />
  )}
/>
```

Apply the same fix to the "专业技能" input (step 3, `skills` field, line 549-556).

### 5.4 Education — Required (min 1 entry)

**Zod schema** (`ApplyPage.tsx`):
```ts
// Before:
education: z.array(educationSchema),

// After:
education: z.array(educationSchema).min(1, "请至少添加一条教育经历"),
```

**UI:** Add a required indicator (`*`) to the "教育经历" section header. Show the Zod error message below the section when validation fails. Update the step-3 validation trigger to include `education`.

---

## Implementation Order

1. **Backend**: DB migration (requirements column), ORM model update, schema update, API update, AI prompt update, 已审阅 bug investigation & fix
2. **Frontend data layer**: Job type update (requirements), API hooks/types
3. **Frontend HR**: PostJobPage (requirements field), JobDetailPage (requirements display), JobDashboardPage (requirements in detail dialog), ApplicantsPage (sticky header + 已审阅 fix if frontend-side)
4. **Frontend Chat**: ChatBubble (drag + snap), ChatWindow (move + resize)
5. **Frontend Seeker**: MyApplicationsPage (full resume), JobDetailPage (applied state), ApplyPage (tech stack Controller + education required)

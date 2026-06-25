# Frontend UI Redesign — Design Spec

## Overview

Redesign the HR Agent (智能简历投递系统) frontend from the current default shadcn neutral theme to a professional recruitment website and HR backend system style. All 8 pages will be rebuilt with a cohesive design system.

### Design Decisions

- **Dual-role design**: Job seeker pages follow recruitment website style; HR pages follow backend management style
- **Visual direction**: Recruitment website — brand presence, trust, warmth
- **Brand color**: Classic Blue (#2563EB / blue-600)
- **HR layout**: Sidebar navigation pattern
- **Login page**: Left-right split layout
- **Device**: Desktop only, no mobile adaptation
- **Approach**: Design system first, then page-by-page implementation

---

## 1. Design Token System

### 1.1 Color System

**Brand Primary (Blue gradient):**

| Token | Value | Usage |
|-------|-------|-------|
| `--primary` | blue-600 | Buttons, links, selected states |
| Primary hover | blue-700 | Button hover |
| Primary foreground | white | Text on primary backgrounds |
| Primary / 10%~20% | blue with alpha | Tag backgrounds, row selection |

**Semantic colors:**

| Token | Color | Usage |
|-------|-------|-------|
| Success | Green | Application accepted, positive feedback |
| Warning | Amber | Pending review, upcoming deadlines |
| Destructive | Red | Errors, rejections |
| Muted | Slate gray | Secondary text, placeholders |

**Neutral palette:** oklch-based slate gradient (slate-50 to slate-900). Cooler than pure neutral — harmonizes with blue primary. Used for backgrounds, borders, and text hierarchy.

**Application status colors:**

| Status | Color | Badge style |
|--------|-------|-------------|
| 待审核 (pending) | Amber/Warning | `bg-amber-100 text-amber-800` |
| 已通过 (accepted) | Green/Success | `bg-green-100 text-green-800` |
| 已拒绝 (rejected) | Red/Destructive | `bg-red-100 text-red-800` |

### 1.2 Typography

**Font family:** Geist Variable (retained)

**Type scale:**

| Role | Class | Size | Weight |
|------|-------|------|--------|
| Page title | `text-2xl font-bold` | 24px | 700 |
| Section title | `text-xl font-semibold` | 20px | 600 |
| Card title | `text-lg font-semibold` | 18px | 600 |
| Body text | `text-sm` | 14px | 400 |
| Auxiliary text | `text-xs text-muted-foreground` | 12px | 400 |

**Line height:** Headings 1.3, body 1.6.

### 1.3 Spacing & Border Radius

**Spacing base:** 4px multiples (4 / 8 / 12 / 16 / 24 / 32 / 48)

| Context | Padding |
|---------|---------|
| Card inner | `p-6` (24px) |
| Page content | `py-8` vertical, `max-w-7xl` centered |
| Section gap | `gap-6` (24px) between major sections |

**Border radius:**

| Element | Class | Radius |
|---------|-------|--------|
| Cards | `rounded-lg` | 8px |
| Buttons | `rounded-md` | 6px |
| Inputs | `rounded-md` | 6px |
| Badges | `rounded-full` | pill |

### 1.4 Shadow Elevation

| Level | Class | Usage |
|-------|-------|-------|
| `shadow-sm` | Light | Card default state |
| `shadow-md` | Medium | Card hover state |
| `shadow-lg` | Heavy | Popovers, dialogs |

---

## 2. Layout System

### 2.1 SeekerLayout (Job Seeker)

```
┌─────────────────────────────────────────────────┐
│  [Logo] 智能投递    岗位市场  我的投递    [头像▼] │
├─────────────────────────────────────────────────┤
│                                                 │
│   Page content (max-w-7xl centered)             │
│                                                 │
└─────────────────────────────────────────────────┘
```

- **Top bar**: 64px height, white background, `border-b`
- **Logo area**: Brand icon + "智能投递" text (`font-bold text-primary`)
- **Nav items**: Ghost buttons, active state `text-primary font-medium`
- **User area**: Avatar + dropdown menu (profile placeholder / logout)
- **Content area**: `max-w-7xl` centered, `py-8`

### 2.2 RecruiterLayout (HR)

```
┌──────┬──────────────────────────────────────────┐
│      │  [Breadcrumb]                [头像▼]      │
│ LOGO ├──────────────────────────────────────────┤
│      │                                          │
│ 我的 │                                          │
│ 岗位 │  Page content                             │
│      │                                          │
│ 发布 │                                          │
│ 新岗 │                                          │
│ 位   │                                          │
│      │                                          │
│ ──── │                                          │
│ 退出 │                                          │
│ 登录 │                                          │
└──────┴──────────────────────────────────────────┘
```

- **Sidebar**: 240px width, white background, `border-r`
- **Logo area**: Top center, brand icon + "招聘管理"
- **Nav items**: Icon + label, selected state `bg-primary/10 text-primary font-medium`
- **Divider**: `Separator` component before logout
- **Top bar**: 56px height, `bg-muted/50`, breadcrumb left, avatar right
- **Content area**: `p-6`

### 2.3 LoginPage (No layout wrapper)

```
┌──────────────────────┬───────────────────────────┐
│                      │                           │
│                      │     欢迎回来               │
│   [Brand illustration│                           │
│    + tagline]         │     邮箱                   │
│                      │     [_______________]      │
│   智能简历投递系统     │                           │
│   让求职更高效         │     密码                   │
│                      │     [_______________]      │
│                      │                           │
│                      │     [  登  录  ]           │
│   Blue gradient bg   │     White background       │
└──────────────────────┴───────────────────────────┘
```

- **Left panel**: Blue gradient background (`bg-gradient-to-br from-blue-600 to-blue-800`) + brand illustration (SVG placeholder) + tagline
- **Right panel**: White background, centered form (`max-w-sm`)
- **Form**: Email input, password input, login button (primary filled)
- **Full viewport**: `h-screen`, no scroll

---

## 3. Component Inventory

### 3.1 Existing shadcn components to retain (14)

avatar, badge, button, card, checkbox, dialog, dropdown-menu, form, input, label, select, separator, tabs, textarea

### 3.2 New shadcn components to add

| Component | Usage |
|-----------|-------|
| **Table** | HR dashboard job list, applicant list |
| **Skeleton** | Loading states (replace text-only "加载中...") |
| **Breadcrumb** | HR page navigation hierarchy |
| **Pagination** | Job market page pagination |
| **Sheet** | Future mobile drawer (optional, add now for extensibility) |

### 3.3 Custom shared components to build

| Component | Usage |
|-----------|-------|
| `SeekerLayout` | Top-bar layout wrapper for job seeker pages |
| `RecruiterLayout` | Sidebar layout wrapper for HR pages |
| `StatCard` | Dashboard statistic card (icon + number + label) |
| `StatusBadge` | Application status badge with semantic color |
| `JobCard` | Job listing card for market and dashboard |
| `SearchBar` | Job market search input with button |
| `CategoryTabs` | Filter tabs for job categories and application status |
| `StepForm` | Multi-step form with progress indicator |

---

## 4. Page Designs

### 4.1 LoginPage

- Left-right split, full viewport height
- Left: Blue gradient + SVG brand illustration + "智能简历投递系统" + "让求职更高效"
- Right: White panel with centered form
  - Heading: "欢迎回来" (`text-2xl font-bold`)
  - Subheading: "登录您的账户" (`text-muted-foreground`)
  - Email input with label
  - Password input with label
  - Primary button "登录"
- No registration link (no registration API currently)

### 4.2 JobMarketPage (SeekerLayout)

- **Search section**: Large rounded search input + primary search button
- **Category filter**: Row of Badge/tag buttons — 全部 / 技术 / 产品 / 设计 / 运营 / etc. Selected state: `bg-primary text-primary-foreground`
- **Job grid**: 3-column card grid (`grid gap-6 md:grid-cols-2 lg:grid-cols-3`)
  - Each `JobCard`:
    - White background, `shadow-sm`, `hover:shadow-md` transition
    - Job title (`text-lg font-semibold`)
    - Company · City (`text-sm text-muted-foreground`)
    - Salary range (`text-primary font-bold`)
    - Skill tags (Badge variant="secondary")
- **Pagination**: Bottom pagination controls
- **Empty state**: When no results — illustration + "暂无匹配岗位"
- **Loading state**: Skeleton cards (3x3 grid of Skeleton rectangles)

### 4.3 JobDetailPage (SeekerLayout)

- **Back link**: "← 返回岗位市场" (`text-primary hover:underline`)
- **Header section**: Job title (`text-2xl font-bold`), company · city · salary subtitle row, skill tags
- **Content sections**:
  - "岗位描述" section with `Separator` divider
  - "任职要求" section with `Separator` divider
- **Action area**: Right-aligned "立即投递" primary button, sticky at bottom on long pages
- **Loading state**: Skeleton layout matching the page structure

### 4.4 ApplyPage (SeekerLayout)

- **Step indicator**: 4 steps with labels — 基本信息 / 工作经历 / 项目经历 / 教育与技能
- **Step content**: Form fields for each step in a Card
  - Step 1: 姓名, 手机, 邮箱
  - Step 2: Work experience entries (add/remove)
  - Step 3: Project experience entries (add/remove)
  - Step 4: Education, certificates, skills, self-evaluation
- **Navigation**: "上一步" (outline) + "下一步"/"提交投递" (primary) buttons
- **Validation**: react-hook-form + zod (existing pattern)

### 4.5 MyApplicationsPage (SeekerLayout)

- **Page title**: "我的投递" (`text-2xl font-bold`)
- **Status filter**: Badge tabs — 全部 / 待审核 / 已通过 / 已拒绝
- **Application list**: Stacked list-cards
  - Each card: Job title + company name (left), StatusBadge (right)
  - Below: Application date (`text-xs text-muted-foreground`)
- **Empty state**: "暂无投递记录" with briefcase illustration

### 4.6 JobDashboardPage (RecruiterLayout)

- **Breadcrumb**: 首页 > 我的岗位
- **Page title**: "我的岗位" (`text-2xl font-bold`)
- **Stats row**: 4 `StatCard` components in a grid
  - 在线岗位 (blue icon)
  - 已关闭岗位 (gray icon)
  - 总申请数 (green icon)
  - 本周新增 (amber icon)
- **Job table**: `Table` component
  - Columns: 岗位名称, 状态 (StatusBadge), 申请人数, 发布时间, 操作
  - Actions dropdown: 查看申请人 / 编辑 / 关闭岗位
- **Empty state**: "暂未发布岗位" with "发布新岗位" CTA button

### 4.7 PostJobPage (RecruiterLayout)

- **Breadcrumb**: 首页 > 发布新岗位
- **Page title**: "发布新岗位" (`text-2xl font-bold`)
- **Form in Card**:
  - Section "基本信息": 岗位名称, 公司名称, 工作地点, 薪资范围 (min-max inputs)
  - Section "岗位详情": 岗位描述 (Textarea), 任职要求 (Textarea)
  - Section "技能标签": Tag input with add/remove
- **Action**: "发布岗位" primary button, full-width at bottom

### 4.8 ApplicantsPage (RecruiterLayout)

- **Breadcrumb**: 首页 > 我的岗位 > [Job Title] > 申请人
- **Header**: Job title + applicant count
- **Status filter**: Badge tabs — 全部 / 待审核 / 已通过 / 已拒绝
- **Applicant table**: `Table` component
  - Columns: 姓名, 状态 (StatusBadge), 投递时间, 操作
  - Actions: "查看简历" (opens Dialog), status change buttons (通过/拒绝)
- **Resume dialog**: Full Dialog showing structured resume info
- **Empty state**: "暂无申请人"

---

## 5. Interaction & UX Details

### 5.1 Loading States

Replace all text-only "加载中..." with Skeleton components:
- Card grids: Skeleton rectangles matching card dimensions
- Tables: Skeleton rows matching column widths
- Detail pages: Skeleton layout matching page structure

### 5.2 Transitions

- Card hover: `transition-shadow duration-200`, `shadow-sm` → `shadow-md`
- Button hover: `transition-colors duration-150`
- Page transitions: No animation (keep it simple and fast)

### 5.3 Empty States

Each list page has a custom empty state:
- Muted icon (lucide-react) or simple illustration
- Description text (`text-muted-foreground`)
- Optional CTA button when relevant

### 5.4 Toast Notifications

Retain existing `sonner` toast setup (positioned top-right, rich colors).

### 5.5 Confirmation Dialogs

Use shadcn `Dialog` for destructive actions (close job, reject applicant).

---

## 6. Technical Implementation Notes

### 6.1 File Structure Changes

```
frontend/src/
  components/
    ui/                    # shadcn components (existing + new Table, Skeleton, Breadcrumb, Pagination)
  features/
    auth/                  # Unchanged
    jobs/                  # Unchanged
    applications/          # Unchanged
  shared/
    ui/
      layout/
        SeekerLayout.tsx   # NEW: Top-bar layout for job seekers
        RecruiterLayout.tsx # NEW: Sidebar layout for HR
      StatCard.tsx         # NEW: Dashboard stat card
      StatusBadge.tsx      # NEW: Application status badge
      JobCard.tsx          # NEW: Job listing card
      SearchBar.tsx        # NEW: Job market search
      CategoryTabs.tsx     # NEW: Filter tabs
      StepForm.tsx         # NEW: Multi-step form
  pages/                   # All 8 pages redesigned
```

### 6.2 CSS Token Changes

Update `index.css`:
- Replace neutral oklch tokens with slate-tinted tokens harmonized with blue-600 primary
- Set `--primary` to blue-600 value
- Set `--primary-foreground` to white
- Update `--ring` to primary color
- Update sidebar tokens for RecruiterLayout

### 6.3 Component Upgrades

Add via `npx shadcn@latest add`:
- table
- skeleton
- breadcrumb
- pagination

### 6.4 Routing Changes

Update `App.tsx` route structure to use layout wrappers:
- Seeker routes wrapped in `SeekerLayout`
- Recruiter routes wrapped in `RecruiterLayout`
- Login page standalone (no layout)

---

## 7. Scope & Out of Scope

### In Scope
- Design token system overhaul
- 2 new layout components (SeekerLayout, RecruiterLayout)
- 7 new shared UI components
- 4 new shadcn components
- All 8 pages fully redesigned
- Skeleton loading states
- Empty state designs

### Out of Scope
- Mobile/responsive design
- Dark mode (keep token structure but don't design for it)
- New features or API changes
- Brand illustration assets (use SVG placeholders)
- Animation library (use Tailwind transitions only)
- Accessibility audit (follow shadcn defaults)

---

## 8. Build Task Decomposition

The implementation is split into 5 sequential build tasks, each with its own implementation plan.

### Task 1: Design Token & CSS Foundation
- Update `index.css` with blue-600 primary color tokens
- Replace neutral oklch palette with slate-tinted palette harmonized with blue
- Update semantic tokens (success/warning/destructive)
- Update typography, spacing, radius, shadow tokens
- **Deliverable**: New CSS token system, visually verifiable via existing pages

### Task 2: Component Infrastructure
- Add 4 new shadcn components: Table, Skeleton, Breadcrumb, Pagination
- Build SeekerLayout (top-bar layout wrapper)
- Build RecruiterLayout (sidebar layout wrapper)
- Build 7 shared UI components: StatCard, StatusBadge, JobCard, SearchBar, CategoryTabs, StepForm, EmptyState
- Update App.tsx routing to use layout wrappers
- **Deliverable**: All new components available, routing uses layouts, pages render in correct layouts (content unchanged)

### Task 3: Login Page
- Redesign LoginPage with left-right split layout
- Left panel: blue gradient + brand illustration (SVG placeholder) + tagline
- Right panel: login form with improved styling
- **Deliverable**: Professional login page matching design spec

### Task 4: Job Seeker Pages (4 pages)
- Redesign JobMarketPage: search bar, category tabs, job card grid, pagination, skeleton loading
- Redesign JobDetailPage: header section, content sections, sticky apply button, skeleton loading
- Redesign ApplyPage: step indicator, grouped form cards, improved form styling
- Redesign MyApplicationsPage: status filter tabs, application list cards, empty state
- **Deliverable**: All 4 seeker pages redesigned matching design spec

### Task 5: HR Pages (3 pages)
- Redesign JobDashboardPage: stat cards row, job table, actions dropdown, empty state
- Redesign PostJobPage: grouped form sections, improved form styling
- Redesign ApplicantsPage: breadcrumb, status filter, applicant table, resume dialog
- **Deliverable**: All 3 HR pages redesigned matching design spec

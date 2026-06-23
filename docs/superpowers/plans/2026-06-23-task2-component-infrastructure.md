# Task 2: Component Infrastructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build all new layout components, shared UI components, and shadcn primitives needed for the page redesign (Tasks 3-5), then wire them into the routing so pages render inside their correct layout shell.

**Architecture:** Layout route pattern — SeekerLayout and RecruiterLayout are React Router `<Route element={…}>` wrappers that provide a persistent header/sidebar around `<Outlet />`. Shared components (StatCard, StatusBadge, JobCard, SearchBar, CategoryTabs, StepForm, EmptyState) are leaf components with no cross-dependencies. Breadcrumb state flows from child pages to RecruiterLayout via a React context. After all components are built, App.tsx routes are restructured and per-page header rendering is removed.

**Tech Stack:** React 19, TypeScript, react-router-dom v7, shadcn/ui (radix-nova), Tailwind CSS v4, lucide-react, zustand

## Global Constraints

- Brand primary: blue-600 = `oklch(54.6% 0.245 262.881)` (set in Task 1 index.css)
- Design spec: `docs/superpowers/specs/2026-06-23-frontend-ui-redesign-design.md`
- All new components use Tailwind utility classes referencing CSS custom properties (never hardcoded hex colors)
- Desktop only — no responsive/mobile breakpoints needed
- SeekerLayout: 64px top-bar, `max-w-7xl` centered content, `py-8 px-6`
- RecruiterLayout: 240px sidebar, 56px top-bar, `p-6` content area
- Application status colors: pending→amber, reviewed→blue, interview→indigo, rejected→red, hired→green
- shadcn CLI: `npx shadcn@latest add <component>` (v4.7.0, radix-nova style)
- TypeScript strict: all components must pass `npx tsc --noEmit`
- Page content must remain unchanged — only structure/layout changes in this task

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/components/ui/table.tsx` | Create (shadcn) | Table primitive for HR dashboard |
| `frontend/src/components/ui/skeleton.tsx` | Create (shadcn) | Loading state placeholder |
| `frontend/src/components/ui/breadcrumb.tsx` | Create (shadcn) | Breadcrumb navigation |
| `frontend/src/components/ui/pagination.tsx` | Create (shadcn) | Pagination controls |
| `frontend/src/shared/ui/layout/SeekerLayout.tsx` | Create | Top-bar layout wrapper for seeker pages |
| `frontend/src/shared/ui/layout/RecruiterLayout.tsx` | Create | Sidebar layout wrapper for HR pages |
| `frontend/src/shared/ui/layout/breadcrumb-context.tsx` | Create | Breadcrumb state context for RecruiterLayout |
| `frontend/src/shared/ui/StatCard.tsx` | Create | Dashboard stat card (icon + number + label) |
| `frontend/src/shared/ui/StatusBadge.tsx` | Create | Status badge with semantic colors |
| `frontend/src/shared/ui/JobCard.tsx` | Create | Job listing card |
| `frontend/src/shared/ui/SearchBar.tsx` | Create | Search input with button |
| `frontend/src/shared/ui/CategoryTabs.tsx` | Create | Filter tab buttons |
| `frontend/src/shared/ui/StepForm.tsx` | Create | Multi-step form progress indicator |
| `frontend/src/shared/ui/feedback/EmptyState.tsx` | Modify | Add icon + action props |
| `frontend/src/App.tsx` | Modify | Route structure with layout wrappers |
| `frontend/src/pages/*.tsx` (7 files) | Modify | Remove header rendering |
| `frontend/src/shared/ui/layout/AppHeader.tsx` | Delete | Replaced by SeekerLayout |
| `frontend/src/shared/ui/layout/SeekerHeader.tsx` | Delete | Replaced by SeekerLayout |
| `frontend/src/shared/ui/layout/RecruiterHeader.tsx` | Delete | Replaced by RecruiterLayout |

---

### Task 1: Install shadcn Components

**Files:**
- Create: `frontend/src/components/ui/table.tsx`
- Create: `frontend/src/components/ui/skeleton.tsx`
- Create: `frontend/src/components/ui/breadcrumb.tsx`
- Create: `frontend/src/components/ui/pagination.tsx`

**Interfaces:**
- Consumes: shadcn CLI (components.json already configured)
- Produces: Table, Skeleton, Breadcrumb, Pagination components at `@/components/ui/`

- [ ] **Step 1: Install all four shadcn components**

Run from the worktree root:

```bash
cd frontend && npx shadcn@latest add table skeleton breadcrumb pagination
```

Accept defaults when prompted. This creates four files under `src/components/ui/`.

- [ ] **Step 2: Verify build passes**

```bash
cd frontend && npx tsc --noEmit 2>&1 | tail -5
```

Expected: No errors

- [ ] **Step 3: Verify the component files exist**

```bash
ls -1 frontend/src/components/ui/table.tsx frontend/src/components/ui/skeleton.tsx frontend/src/components/ui/breadcrumb.tsx frontend/src/components/ui/pagination.tsx
```

Expected: All four files listed

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/table.tsx frontend/src/components/ui/skeleton.tsx frontend/src/components/ui/breadcrumb.tsx frontend/src/components/ui/pagination.tsx
git commit -m "feat(ui): add shadcn table, skeleton, breadcrumb, pagination components"
```

---

### Task 2: Build SeekerLayout

**Files:**
- Create: `frontend/src/shared/ui/layout/SeekerLayout.tsx`

**Interfaces:**
- Consumes: `useAuthStore` from `@/features/auth/store/authStore`, `useLogout` from `@/features/auth/hooks/useLogout`, `Outlet`/`useLocation`/`useNavigate` from react-router-dom, `Avatar`/`DropdownMenu`/`Button` from shadcn
- Produces: `<SeekerLayout />` — a layout route element that renders a top-bar + `<Outlet />`. No props (reads auth state and navigation internally).

The SeekerLayout replaces the per-page `<SeekerHeader>` pattern. It provides:
- 64px sticky top bar with brand logo, nav items (active state highlighted), and user avatar dropdown (or "登录" button when unauthenticated)
- Content area: `max-w-7xl mx-auto py-8 px-6`
- `<Outlet />` for child route rendering

- [ ] **Step 1: Create SeekerLayout.tsx**

Write the following to `frontend/src/shared/ui/layout/SeekerLayout.tsx`:

```tsx
import { Fragment } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Briefcase } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useLogout } from "@/features/auth/hooks/useLogout";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "岗位市场", path: "/jobs" },
  { label: "我的投递", path: "/my-applications" },
] as const;

export default function SeekerLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useLogout();
  const user = useAuthStore((s) => s.user);

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  return (
    <div className="min-h-screen bg-background">
      <header className="h-16 bg-card border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div
              className="flex items-center gap-2 cursor-pointer"
              onClick={() => navigate("/jobs")}
            >
              <Briefcase className="h-5 w-5 text-primary" />
              <span className="font-bold text-primary text-lg">智能投递</span>
            </div>
            <Separator orientation="vertical" className="h-6" />
            <nav className="flex items-center gap-1">
              {NAV_ITEMS.map((item) => (
                <Button
                  key={item.path}
                  variant="ghost"
                  onClick={() => navigate(item.path)}
                  className={cn(isActive(item.path) && "text-primary font-medium")}
                >
                  {item.label}
                </Button>
              ))}
            </nav>
          </div>
          <div>
            {user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="text-xs">
                        {user.name.charAt(0)}
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem className="text-muted-foreground text-xs cursor-default">
                    {user.name}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={logout}>退出登录</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Button variant="outline" size="sm" onClick={() => navigate("/login")}>
                登录
              </Button>
            )}
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-8 px-6">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compilation**

```bash
cd frontend && npx tsc --noEmit 2>&1 | tail -5
```

Expected: No errors

- [ ] **Step 3: Verify Vite build**

```bash
cd frontend && npx vite build 2>&1 | tail -5
```

Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/ui/layout/SeekerLayout.tsx
git commit -m "feat(ui): add SeekerLayout top-bar layout component"
```

---

### Task 3: Build RecruiterLayout

**Files:**
- Create: `frontend/src/shared/ui/layout/breadcrumb-context.tsx`
- Create: `frontend/src/shared/ui/layout/RecruiterLayout.tsx`

**Interfaces:**
- Consumes: `useAuthStore` from `@/features/auth/store/authStore`, `useLogout` from `@/features/auth/hooks/useLogout`, `Outlet`/`useLocation`/`useNavigate` from react-router-dom, Breadcrumb/Avatar/Separator from shadcn
- Produces:
  - `<RecruiterLayout />` — a layout route element with sidebar + top-bar + `<Outlet />`
  - `useBreadcrumb()` — a hook that child pages call to set breadcrumb items: `({ items, setItems }) => void`

The RecruiterLayout provides:
- 240px white sidebar: brand logo, nav items with icons (active state = `bg-primary/10 text-primary font-medium`), separator, logout button
- 56px top-bar: breadcrumb (left), avatar (right)
- Content area: `flex-1 p-6`
- Breadcrumb context: pages call `setItems([{ label, href? }])` in useEffect to populate the breadcrumb

- [ ] **Step 1: Create breadcrumb context**

Write the following to `frontend/src/shared/ui/layout/breadcrumb-context.tsx`:

```tsx
import { createContext, useContext, useState } from "react";
import type { Dispatch, SetStateAction } from "react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbContextType {
  items: BreadcrumbItem[];
  setItems: Dispatch<SetStateAction<BreadcrumbItem[]>>;
}

const BreadcrumbContext = createContext<BreadcrumbContextType>({
  items: [],
  setItems: () => {},
});

export function BreadcrumbProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<BreadcrumbItem[]>([]);
  return (
    <BreadcrumbContext.Provider value={{ items, setItems }}>
      {children}
    </BreadcrumbContext.Provider>
  );
}

export function useBreadcrumb() {
  return useContext(BreadcrumbContext);
}
```

- [ ] **Step 2: Create RecruiterLayout.tsx**

Write the following to `frontend/src/shared/ui/layout/RecruiterLayout.tsx`:

```tsx
import { Fragment } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Briefcase, LogOut, PlusCircle } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useLogout } from "@/features/auth/hooks/useLogout";
import { cn } from "@/lib/utils";
import { BreadcrumbProvider, useBreadcrumb } from "./breadcrumb-context";

const SIDEBAR_ITEMS = [
  { label: "我的岗位", icon: Briefcase, path: "/dashboard" },
  { label: "发布新岗位", icon: PlusCircle, path: "/dashboard/post" },
] as const;

function RecruiterLayoutInner() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useLogout();
  const user = useAuthStore((s) => s.user);
  const { items: breadcrumbItems } = useBreadcrumb();

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside className="w-60 bg-card border-r flex flex-col shrink-0">
        <div
          className="h-16 flex items-center justify-center border-b cursor-pointer"
          onClick={() => navigate("/dashboard")}
        >
          <Briefcase className="h-5 w-5 text-primary mr-2" />
          <span className="font-bold text-primary text-lg">招聘管理</span>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {SIDEBAR_ITEMS.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                isActive(item.path)
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:bg-muted"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="p-4">
          <Separator className="mb-4" />
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-muted transition-colors"
          >
            <LogOut className="h-4 w-4" />
            退出登录
          </button>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-muted/50 border-b flex items-center justify-between px-6 shrink-0">
          <Breadcrumb>
            <BreadcrumbList>
              {breadcrumbItems.map((item, i) => (
                <Fragment key={i}>
                  {i > 0 && <BreadcrumbSeparator />}
                  <BreadcrumbItem>
                    {item.href ? (
                      <BreadcrumbLink
                        onClick={() => navigate(item.href!)}
                        className="cursor-pointer"
                      >
                        {item.label}
                      </BreadcrumbLink>
                    ) : (
                      <BreadcrumbPage>{item.label}</BreadcrumbPage>
                    )}
                  </BreadcrumbItem>
                </Fragment>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs">
              {user?.name.charAt(0) ?? ""}
            </AvatarFallback>
          </Avatar>
        </header>

        {/* Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function RecruiterLayout() {
  return (
    <BreadcrumbProvider>
      <RecruiterLayoutInner />
    </BreadcrumbProvider>
  );
}
```

- [ ] **Step 3: Verify TypeScript compilation**

```bash
cd frontend && npx tsc --noEmit 2>&1 | tail -5
```

Expected: No errors

- [ ] **Step 4: Verify Vite build**

```bash
cd frontend && npx vite build 2>&1 | tail -5
```

Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shared/ui/layout/breadcrumb-context.tsx frontend/src/shared/ui/layout/RecruiterLayout.tsx
git commit -m "feat(ui): add RecruiterLayout sidebar layout with breadcrumb context"
```

---

### Task 4: Build Shared UI Components

**Files:**
- Create: `frontend/src/shared/ui/StatCard.tsx`
- Create: `frontend/src/shared/ui/StatusBadge.tsx`
- Create: `frontend/src/shared/ui/JobCard.tsx`
- Create: `frontend/src/shared/ui/SearchBar.tsx`
- Create: `frontend/src/shared/ui/CategoryTabs.tsx`
- Create: `frontend/src/shared/ui/StepForm.tsx`
- Modify: `frontend/src/shared/ui/feedback/EmptyState.tsx`

**Interfaces:**
- Consumes: `Card`/`CardContent` from `@/components/ui/card`, `Badge` from `@/components/ui/badge`, `Button` from `@/components/ui/button`, `Input` from `@/components/ui/input`, `ApplicationStatus` from `@/shared/constants/applicationStatus`, `Job` from `@/features/jobs/types/job`, lucide-react icons
- Produces: Seven leaf components with no cross-dependencies. Each is independently importable.

- [ ] **Step 1: Create StatCard.tsx**

Write the following to `frontend/src/shared/ui/StatCard.tsx`:

```tsx
import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  icon: LucideIcon;
  value: string | number;
  label: string;
  iconColor?: string;
}

export function StatCard({
  icon: Icon,
  value,
  label,
  iconColor = "text-primary",
}: StatCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center gap-4">
          <div className={cn("p-2.5 rounded-lg bg-primary/10", iconColor)}>
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-sm text-muted-foreground">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Create StatusBadge.tsx**

Write the following to `frontend/src/shared/ui/StatusBadge.tsx`:

```tsx
import { cn } from "@/lib/utils";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";

interface StatusBadgeProps {
  status: ApplicationStatus;
}

const STATUS_STYLES: Record<ApplicationStatus, { label: string; className: string }> = {
  pending: {
    label: "待审核",
    className: "bg-amber-100 text-amber-800 hover:bg-amber-100/80",
  },
  reviewed: {
    label: "已审阅",
    className: "bg-blue-100 text-blue-800 hover:bg-blue-100/80",
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

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_STYLES[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors",
        config.className
      )}
    >
      {config.label}
    </span>
  );
}
```

- [ ] **Step 3: Create JobCard.tsx**

Write the following to `frontend/src/shared/ui/JobCard.tsx`:

```tsx
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Job } from "@/features/jobs/types/job";

interface JobCardProps {
  job: Job;
  onClick?: () => void;
}

export function JobCard({ job, onClick }: JobCardProps) {
  const hasSalary = job.salary_min != null || job.salary_max != null;
  const locationParts = [job.recruiter_name, job.location].filter(Boolean);

  return (
    <Card
      className="shadow-sm hover:shadow-md transition-shadow duration-200 cursor-pointer"
      onClick={onClick}
    >
      <CardContent className="p-6">
        <h3 className="text-lg font-semibold">{job.title}</h3>
        {locationParts.length > 0 && (
          <p className="text-sm text-muted-foreground mt-1">
            {locationParts.join(" · ")}
          </p>
        )}
        {hasSalary && (
          <p className="text-primary font-bold mt-2">
            {job.salary_min != null ? `${job.salary_min}k` : ""}
            {job.salary_min != null && job.salary_max != null ? " - " : ""}
            {job.salary_max != null ? `${job.salary_max}k` : ""}
          </p>
        )}
        {job.skills_required.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {job.skills_required.map((skill) => (
              <Badge key={skill} variant="secondary">
                {skill}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Create SearchBar.tsx**

Write the following to `frontend/src/shared/ui/SearchBar.tsx`:

```tsx
import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
  placeholder?: string;
}

export function SearchBar({
  value,
  onChange,
  onSearch,
  placeholder = "搜索岗位...",
}: SearchBarProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch();
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="pl-9 h-10 rounded-lg"
        />
      </div>
      <Button type="submit" className="h-10 px-6">
        搜索
      </Button>
    </form>
  );
}
```

- [ ] **Step 5: Create CategoryTabs.tsx**

Write the following to `frontend/src/shared/ui/CategoryTabs.tsx`:

```tsx
import { Button } from "@/components/ui/button";

interface Category<T extends string> {
  key: T;
  label: string;
}

interface CategoryTabsProps<T extends string> {
  categories: Category<T>[];
  activeKey: T;
  onSelect: (key: T) => void;
}

export function CategoryTabs<T extends string = string>({
  categories,
  activeKey,
  onSelect,
}: CategoryTabsProps<T>) {
  return (
    <div className="flex flex-wrap gap-2">
      {categories.map((cat) => (
        <Button
          key={cat.key}
          variant={activeKey === cat.key ? "default" : "outline"}
          size="sm"
          onClick={() => onSelect(cat.key)}
        >
          {cat.label}
        </Button>
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Create StepForm.tsx**

Write the following to `frontend/src/shared/ui/StepForm.tsx`:

```tsx
import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

interface Step {
  label: string;
}

interface StepFormProps {
  steps: Step[];
  currentStep: number;
}

export function StepForm({ steps, currentStep }: StepFormProps) {
  return (
    <div className="flex items-center justify-center mb-8">
      {steps.map((step, index) => (
        <div key={step.label} className="flex items-center">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium border-2 transition-colors",
                index < currentStep && "bg-primary border-primary text-primary-foreground",
                index === currentStep && "border-primary text-primary",
                index > currentStep && "border-muted-foreground/30 text-muted-foreground"
              )}
            >
              {index < currentStep ? <Check className="h-4 w-4" /> : index + 1}
            </div>
            <span
              className={cn(
                "text-sm whitespace-nowrap",
                index <= currentStep
                  ? "text-foreground font-medium"
                  : "text-muted-foreground"
              )}
            >
              {step.label}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div
              className={cn(
                "mx-2 h-0.5 w-8",
                index < currentStep ? "bg-primary" : "bg-muted-foreground/30"
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: Enhance EmptyState.tsx**

Replace the entire contents of `frontend/src/shared/ui/feedback/EmptyState.tsx` with:

```tsx
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon?: LucideIcon;
  message: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export default function EmptyState({
  icon: Icon,
  message,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      {Icon && <Icon className="h-12 w-12 text-muted-foreground/40 mb-4" />}
      <p className="text-muted-foreground text-sm">{message}</p>
      {action && (
        <Button onClick={action.onClick} className="mt-4">
          {action.label}
        </Button>
      )}
    </div>
  );
}
```

This is backward-compatible: the existing `message` prop still works. The `icon` and `action` props are optional additions.

- [ ] **Step 8: Verify TypeScript compilation**

```bash
cd frontend && npx tsc --noEmit 2>&1 | tail -5
```

Expected: No errors

- [ ] **Step 9: Verify Vite build**

```bash
cd frontend && npx vite build 2>&1 | tail -5
```

Expected: Build succeeds

- [ ] **Step 10: Commit**

```bash
git add frontend/src/shared/ui/StatCard.tsx frontend/src/shared/ui/StatusBadge.tsx frontend/src/shared/ui/JobCard.tsx frontend/src/shared/ui/SearchBar.tsx frontend/src/shared/ui/CategoryTabs.tsx frontend/src/shared/ui/StepForm.tsx frontend/src/shared/ui/feedback/EmptyState.tsx
git commit -m "feat(ui): add shared UI components (StatCard, StatusBadge, JobCard, SearchBar, CategoryTabs, StepForm, EmptyState)"
```

---

### Task 5: Update App.tsx Routing and Remove Per-Page Headers

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/JobMarketPage.tsx`
- Modify: `frontend/src/pages/JobDetailPage.tsx`
- Modify: `frontend/src/pages/ApplyPage.tsx`
- Modify: `frontend/src/pages/MyApplicationsPage.tsx`
- Modify: `frontend/src/pages/JobDashboardPage.tsx`
- Modify: `frontend/src/pages/PostJobPage.tsx`
- Modify: `frontend/src/pages/ApplicantsPage.tsx`
- Delete: `frontend/src/shared/ui/layout/AppHeader.tsx`
- Delete: `frontend/src/shared/ui/layout/SeekerHeader.tsx`
- Delete: `frontend/src/shared/ui/layout/RecruiterHeader.tsx`

**Interfaces:**
- Consumes: `SeekerLayout` from `@/shared/ui/layout/SeekerLayout`, `RecruiterLayout` from `@/shared/ui/layout/RecruiterLayout`
- Produces: Routes wrapped in layout elements, pages no longer render their own headers

This task:
1. Restructures App.tsx routes to use `<Route element={<SeekerLayout />}>` and `<Route element={<RecruiterLayout />}>` wrappers
2. Removes header imports and rendering from all 7 pages
3. Removes `useNavigate()` / `useLogout()` calls that were only used for header props
4. Deletes the three old header files (AppHeader, SeekerHeader, RecruiterHeader)

**Important:** Each page currently wraps its content in `<div className="min-h-screen bg-gray-50">` with the header inside. After this change, pages only render their `<main>` content — the layout provides the outer shell. The `bg-gray-50` class is replaced by `bg-background` from the layout.

- [ ] **Step 1: Replace App.tsx with layout-wrapped routes**

Write the following to `frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { useAuthStore } from "@/features/auth/store/authStore";
import ApplicantsPage from "@/pages/ApplicantsPage";
import ApplyPage from "@/pages/ApplyPage";
import JobDashboardPage from "@/pages/JobDashboardPage";
import JobDetailPage from "@/pages/JobDetailPage";
import JobMarketPage from "@/pages/JobMarketPage";
import LoginPage from "@/pages/LoginPage";
import MyApplicationsPage from "@/pages/MyApplicationsPage";
import PostJobPage from "@/pages/PostJobPage";
import RecruiterLayout from "@/shared/ui/layout/RecruiterLayout";
import SeekerLayout from "@/shared/ui/layout/SeekerLayout";

function ProtectedRoute({
  children,
  role,
}: {
  children: React.ReactNode;
  role?: "job_seeker" | "recruiter";
}) {
  const hydrated = useAuthStore.persist.hasHydrated();
  const user = useAuthStore((s) => s.user);

  if (!hydrated) {
    return <div className="flex justify-center py-20 text-muted-foreground">加载中...</div>;
  }

  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Seeker routes — top-bar layout */}
        <Route element={<SeekerLayout />}>
          <Route path="/jobs" element={<JobMarketPage />} />
          <Route path="/jobs/:id" element={<JobDetailPage />} />
          <Route
            path="/apply/:jobId"
            element={
              <ProtectedRoute role="job_seeker">
                <ApplyPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/my-applications"
            element={
              <ProtectedRoute role="job_seeker">
                <MyApplicationsPage />
              </ProtectedRoute>
            }
          />
        </Route>

        {/* Recruiter routes — sidebar layout */}
        <Route element={<RecruiterLayout />}>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute role="recruiter">
                <JobDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/post"
            element={
              <ProtectedRoute role="recruiter">
                <PostJobPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/applicants/:jobId"
            element={
              <ProtectedRoute role="recruiter">
                <ApplicantsPage />
              </ProtectedRoute>
            }
          />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

Key changes from current App.tsx:
- Import `SeekerLayout` and `RecruiterLayout`
- Seeker routes (`/jobs`, `/jobs/:id`, `/apply/:jobId`, `/my-applications`) nested under `<Route element={<SeekerLayout />}>`
- Recruiter routes (`/dashboard`, `/dashboard/post`, `/dashboard/applicants/:jobId`) nested under `<Route element={<RecruiterLayout />}>`
- ProtectedRoute loading text changed from `text-gray-500` to `text-muted-foreground` (use design token)

- [ ] **Step 2: Update JobMarketPage.tsx — remove header**

Remove these lines from JobMarketPage.tsx:
- Line 16: `import { useLogout } from "@/features/auth/hooks/useLogout";`
- Line 20: `import SeekerHeader from "@/shared/ui/layout/SeekerHeader";`
- Line 25: `const navigate = useNavigate();` (navigate is not used elsewhere — pages uses `<Link>`)
- Line 26: `const logout = useLogout();`
- Line 2: Remove `useNavigate` from the import: `import { Link } from "react-router-dom";`
- Lines 37-38: Remove `<div className="min-h-screen bg-gray-50">` and `<SeekerHeader onNavigate={navigate} onLogout={logout} />`

Also remove the closing `</div>` that matches the removed wrapper div.

The JSX return should start with `<main …>` and end with `</main>` (no wrapper div).

- [ ] **Step 3: Update JobDetailPage.tsx — remove header**

Remove these lines from JobDetailPage.tsx:
- Line 16: `import { useLogout } from "@/features/auth/hooks/useLogout";`
- Lines 23-24: `import RecruiterHeader…` and `import SeekerHeader…`
- Line 29: `const logout = useLogout();` (logout is only used for header)
- Lines 61-66: The entire conditional header rendering block:
  ```tsx
  {isRecruiter ? (
    <RecruiterHeader onNavigate={navigate} onLogout={logout} />
  ) : (
    <SeekerHeader onNavigate={navigate} onLogout={logout} />
  )}
  ```
- Line 60: `<div className="min-h-screen bg-gray-50">` and its matching closing `</div>`

Keep: `const navigate = useNavigate()` (used for handleBack, handleApply, fallbackPath navigation).
Keep: `const { user } = useAuthStore()` and `const isRecruiter = …` (used for conditional UI within the page content).

The JSX return should start with `<main …>` and end with `</main>`.

- [ ] **Step 4: Update ApplyPage.tsx — remove header**

Remove these lines from ApplyPage.tsx:
- Line 24: `import { useLogout } from "@/features/auth/hooks/useLogout";`
- Line 26: `import SeekerHeader from "@/shared/ui/layout/SeekerHeader";`
- Line 83: `const logout = useLogout();`
- Line 217: `<SeekerHeader onNavigate={navigate} onLogout={logout} />`
- Line 216: `<div className="min-h-screen bg-gray-50">` and its matching closing `</div>`

Keep: `const navigate = useNavigate()` (used for redirect after success).

The JSX return should start with `<main …>` and end with `</main>`.

- [ ] **Step 5: Update MyApplicationsPage.tsx — remove header**

Remove these lines from MyApplicationsPage.tsx:
- Line 1: Remove `useNavigate` from import: `import { } from "react-router-dom";` — actually navigate IS used on line 39 and 51, 71, so keep it. Change to: `import { useNavigate } from "react-router-dom";` (keep useNavigate only)
- Line 7: `import { useLogout } from "@/features/auth/hooks/useLogout";`
- Line 13: `import SeekerHeader from "@/shared/ui/layout/SeekerHeader";`
- Line 17: `const logout = useLogout();`
- Line 24: `<SeekerHeader onNavigate={navigate} onLogout={logout} />`
- Line 23: `<div className="min-h-screen bg-gray-50">` and its matching closing `</div>`

Keep: `const navigate = useNavigate()` (used for clicking job titles and "去看看岗位" button).

The JSX return should start with `<main …>` and end with `</main>`.

- [ ] **Step 6: Update JobDashboardPage.tsx — remove header**

Remove these lines from JobDashboardPage.tsx:
- Line 24: `import { useLogout } from "@/features/auth/hooks/useLogout";`
- Line 35: `import RecruiterHeader from "@/shared/ui/layout/RecruiterHeader";`
- Line 42: `const logout = useLogout();`
- Line 73: `<RecruiterHeader onNavigate={navigate} onLogout={logout} />`
- Line 72: `<div className="min-h-screen bg-gray-50">` and its matching closing `</div>`

Keep: `const navigate = useNavigate()` (used for clicking jobs and applicants).
Keep: `const { user } = useAuthStore()` (used for user?.id in the query).

The JSX return should start with `<main …>` and end with `</main>`.

- [ ] **Step 7: Update PostJobPage.tsx — remove header**

Remove these lines from PostJobPage.tsx:
- Line 19: `import { useLogout } from "@/features/auth/hooks/useLogout";`
- Line 22: `import RecruiterHeader from "@/shared/ui/layout/RecruiterHeader";`
- Line 38: `const logout = useLogout();`
- Line 67: `<RecruiterHeader onNavigate={navigate} onLogout={logout} />`
- Line 66: `<div className="min-h-screen bg-gray-50">` and its matching closing `</div>`

Keep: `const navigate = useNavigate()` (used for redirect after submit).

The JSX return should start with `<main …>` and end with `</main>`.

- [ ] **Step 8: Update ApplicantsPage.tsx — remove header**

Remove these lines from ApplicantsPage.tsx:
- Line 24: `import { useLogout } from "@/features/auth/hooks/useLogout";`
- Line 30: `import RecruiterHeader from "@/shared/ui/layout/RecruiterHeader";`
- Line 35: `const logout = useLogout();`
- Line 62: `<RecruiterHeader onNavigate={navigate} onLogout={logout} />`
- Line 61: `<div className="min-h-screen bg-gray-50">` and its matching closing `</div>`

Check if `navigate` is used elsewhere in ApplicantsPage. If not, also remove:
- `const navigate = useNavigate();`
- The `useNavigate` import (but `useParams` is still needed, so keep: `import { useParams } from "react-router-dom";`)

The JSX return should start with `<main …>` and end with `</main>`.

- [ ] **Step 9: Delete old header files**

```bash
rm frontend/src/shared/ui/layout/AppHeader.tsx frontend/src/shared/ui/layout/SeekerHeader.tsx frontend/src/shared/ui/layout/RecruiterHeader.tsx
```

- [ ] **Step 10: Verify TypeScript compilation**

```bash
cd frontend && npx tsc --noEmit 2>&1 | tail -10
```

Expected: No errors. If there are import errors from the deleted header files, find and remove any remaining references.

- [ ] **Step 11: Verify Vite build**

```bash
cd frontend && npx vite build 2>&1 | tail -10
```

Expected: Build succeeds

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat(ui): wire layout routes, remove per-page headers, delete old layout files"
```

---

## Self-Review

**1. Spec coverage:**

| Spec requirement | Task |
|-----------------|------|
| Add shadcn Table | Task 1 ✅ |
| Add shadcn Skeleton | Task 1 ✅ |
| Add shadcn Breadcrumb | Task 1 ✅ |
| Add shadcn Pagination | Task 1 ✅ |
| Build SeekerLayout (64px top-bar, brand logo, nav with active state, avatar dropdown) | Task 2 ✅ |
| Build RecruiterLayout (240px sidebar, breadcrumb top-bar, avatar) | Task 3 ✅ |
| Build StatCard (icon + number + label) | Task 4 ✅ |
| Build StatusBadge (semantic colors: amber/blue/indigo/red/green) | Task 4 ✅ |
| Build JobCard (title, company·city, salary, skill tags) | Task 4 ✅ |
| Build SearchBar (input + search button) | Task 4 ✅ |
| Build CategoryTabs (filter buttons, active state) | Task 4 ✅ |
| Build StepForm (step indicator with progress) | Task 4 ✅ |
| Enhance EmptyState (icon, message, optional action button) | Task 4 ✅ |
| Update App.tsx routing with layout wrappers | Task 5 ✅ |
| Seeker routes under SeekerLayout | Task 5 ✅ |
| Recruiter routes under RecruiterLayout | Task 5 ✅ |
| JobDetailPage always under SeekerLayout (per spec §4.3) | Task 5 ✅ |
| Delete old header files | Task 5 ✅ |

**2. Placeholder scan:** No TBD/TODO/vague references found. All code is complete. All token values reference CSS custom properties.

**3. Type consistency:**

| Type | Defined in | Used by |
|------|-----------|---------|
| `BreadcrumbItem` | `breadcrumb-context.tsx` | `RecruiterLayout.tsx`, pages via `useBreadcrumb()` |
| `ApplicationStatus` | `shared/constants/applicationStatus.ts` (existing) | `StatusBadge.tsx` imports it |
| `Job` | `features/jobs/types/job.ts` (existing) | `JobCard.tsx` imports it |
| `LucideIcon` | `lucide-react` (external) | `StatCard.tsx`, `EmptyState.tsx` |
| `StatCardProps.iconColor` | `StatCard.tsx` | default value `"text-primary"` is a Tailwind class string |
| `CategoryTabsProps<T>` | `CategoryTabs.tsx` | generic over string keys |

All type names and signatures are consistent across tasks. No naming conflicts.

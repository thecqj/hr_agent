# Task 5: HR Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign all 3 HR recruiter pages (JobDashboardPage, PostJobPage, ApplicantsPage) to match the design spec's HR backend management style.

**Architecture:** Each page gets a full rewrite inside the existing RecruiterLayout (sidebar + breadcrumb top bar). Pages use shared components built in Task 2 (StatCard, StatusBadge, CategoryTabs, EmptyState, LoadingState) and shadcn Table/Pagination/Skeleton/Dialog. Breadcrumbs are set via `useBreadcrumb()` following the same pattern as the seeker pages.

**Tech Stack:** React 18, TypeScript, shadcn/ui (Table, Pagination, Skeleton, Dialog, Select, DropdownMenu), @tanstack/react-query, react-hook-form + zod, lucide-react icons, Tailwind CSS v4.

## Global Constraints

- **Layout:** All HR pages render inside `RecruiterLayout` (sidebar 240px + top bar 56px with breadcrumb). Content area is `p-6`.
- **Breadcrumb:** Every HR page MUST call `useBreadcrumb()` and set items in a `useEffect`. Import from `@/shared/ui/layout/breadcrumb-context`.
- **Page title:** `text-2xl font-bold` at the top of every page.
- **Card style:** `shadow-sm hover:shadow-md transition-shadow duration-200`.
- **StatCard:** Use existing `StatCard` from `@/shared/ui/StatCard` with `icon`, `value`, `label`, `iconColor` props.
- **StatusBadge:** Use `StatusBadge` from `@/shared/ui/StatusBadge` — reads from `APPLICATION_STATUS_MAP` for labels and colors. Do NOT duplicate status labels inline.
- **CategoryTabs:** Use `CategoryTabs<T>` from `@/shared/ui/CategoryTabs` — generic component with `categories`, `activeKey`, `onSelect` props. Categories type is `{ key: string; label: string }[]`.
- **EmptyState:** Use default export from `@/shared/ui/feedback/EmptyState` with `icon?`, `message`, `action?` props.
- **ErrorState:** Use default export from `@/shared/ui/feedback/ErrorState` with `message`, `onRetry?` props.
- **Loading states:** Use Skeleton components matching the page structure, NOT the generic `LoadingState` component for table/dashboard layouts. For stat cards: skeleton cards; for tables: skeleton rows; for forms: skeleton sections.
- **Table:** Use shadcn `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell` from `@/components/ui/table`.
- **DropdownMenu:** Use shadcn `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem` from `@/components/ui/dropdown-menu`.
- **JobStatus labels:** active → "活跃", draft → "草稿", closed → "已关闭". Consistent across all pages.
- **APPLICATION_STATUS_MAP labels (read-only, for display):** pending → "待审核", reviewed → "已审阅", interview → "面试中", rejected → "已拒绝", hired → "已录用".
- **Max width:** HR pages do NOT use `max-w-7xl` (RecruiterLayout content area is already constrained). PostJobPage uses `max-w-3xl` for the form.
- **Confirmation dialogs:** Use shadcn `Dialog` for destructive actions (delete job, close job, reject applicant).
- **Toast:** Use `sonner` toast for success/error feedback (existing pattern).
- **Mutations:** Use existing hooks from `@/features/jobs/hooks/useJobs` and `@/features/applications/hooks/useApplications`.
- **ApplicationStatus type:** Import from `@/shared/constants/applicationStatus`, NOT from the application types file.
- **WorkType labels:** remote → "远程", onsite → "现场", hybrid → "混合".

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/pages/JobDashboardPage.tsx` | Rewrite | Dashboard with stat cards, job table, actions dropdown, empty state |
| `src/pages/PostJobPage.tsx` | Rewrite | Grouped form with sections, tag input, breadcrumbs |
| `src/pages/ApplicantsPage.tsx` | Rewrite | Breadcrumb, status filter, applicant table, resume dialog |
| `src/shared/constants/applicationStatus.ts` | Add `JOB_STATUS_MAP` | Job status labels and badge classes for dashboard table |
| `src/shared/ui/JobStatusBadge.tsx` | Create | Job status badge component (distinct from application StatusBadge) |

---

### Task 1: Add JobStatusBadge shared component

The JobDashboardPage needs a badge for job status (active/draft/closed), which is a different domain from application status (pending/reviewed/etc). Create a `JOB_STATUS_MAP` constant and `JobStatusBadge` component.

**Files:**
- Modify: `src/shared/constants/applicationStatus.ts`
- Create: `src/shared/ui/JobStatusBadge.tsx`

**Interfaces:**
- Consumes: `JobStatus` type from `@/features/jobs/types/job` (`"draft" | "active" | "closed"`)
- Produces: `JOB_STATUS_MAP` constant, `JobStatusBadge` component with `status: JobStatus` prop

- [ ] **Step 1: Add JOB_STATUS_MAP to applicationStatus.ts**

Add the following after the existing `APPLICATION_STATUS_MAP` export in `src/shared/constants/applicationStatus.ts`:

```typescript
import type { JobStatus } from "@/features/jobs/types/job";

export const JOB_STATUS_MAP: Record<JobStatus, StatusStyle> = {
  active: {
    label: "活跃",
    className: "bg-green-100 text-green-800 hover:bg-green-100/80",
  },
  draft: {
    label: "草稿",
    className: "bg-slate-100 text-slate-800 hover:bg-slate-100/80",
  },
  closed: {
    label: "已关闭",
    className: "bg-red-100 text-red-800 hover:bg-red-100/80",
  },
};
```

- [ ] **Step 2: Create JobStatusBadge component**

Create `src/shared/ui/JobStatusBadge.tsx`:

```typescript
import { cn } from "@/lib/utils";
import { JOB_STATUS_MAP } from "@/shared/constants/applicationStatus";
import type { JobStatus } from "@/features/jobs/types/job";

interface JobStatusBadgeProps {
  status: JobStatus;
  className?: string;
}

export function JobStatusBadge({ status, className }: JobStatusBadgeProps) {
  const config = JOB_STATUS_MAP[status];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors",
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/shared/constants/applicationStatus.ts src/shared/ui/JobStatusBadge.tsx
git commit -m "feat(ui): add JOB_STATUS_MAP and JobStatusBadge component"
```

---

### Task 2: Redesign JobDashboardPage

Replace the current card-grid layout with a professional dashboard: stat cards row → job table with actions dropdown → empty state with CTA.

**Files:**
- Rewrite: `src/pages/JobDashboardPage.tsx`

**Interfaces:**
- Consumes:
  - `useRecruiterJobsQuery(recruiterId?)` from `@/features/jobs/hooks/useJobs` — returns `Job[]`
  - `useUpdateJobStatusMutation()` — `mutateAsync({ jobId, status: JobStatus })`
  - `useDeleteJobMutation()` — `mutateAsync(jobId: string)`
  - `useAuthStore` from `@/features/auth/store/authStore` — `{ user }`
  - `StatCard` from `@/shared/ui/StatCard` — props: `{ icon: LucideIcon, value: string|number, label: string, iconColor?: string }`
  - `JobStatusBadge` from `@/shared/ui/JobStatusBadge` — props: `{ status: JobStatus, className?: string }`
  - `EmptyState` from `@/shared/ui/feedback/EmptyState`
  - `ErrorState` from `@/shared/ui/feedback/ErrorState`
  - `useBreadcrumb()` from `@/shared/ui/layout/breadcrumb-context`
  - `Job` type from `@/features/jobs/types/job` — has `id, title, status: JobStatus, created_at, applications_count?`
  - `JobStatus` type from `@/features/jobs/types/job` — `"draft" | "active" | "closed"`
  - shadcn: `Table, TableHeader, TableBody, TableRow, TableHead, TableCell` from `@/components/ui/table`
  - shadcn: `DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem` from `@/components/ui/dropdown-menu`
  - shadcn: `Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle` from `@/components/ui/dialog`
  - shadcn: `Button` from `@/components/ui/button`
  - shadcn: `Skeleton` from `@/components/ui/skeleton`
- Produces: None (leaf page)

- [ ] **Step 1: Write the full page rewrite**

Replace the entire content of `src/pages/JobDashboardPage.tsx` with:

```typescript
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Briefcase,
  Eye,
  Pencil,
  Power,
  MoreHorizontal,
  TrendingUp,
  XCircle,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuthStore } from "@/features/auth/store/authStore";
import {
  useDeleteJobMutation,
  useRecruiterJobsQuery,
  useUpdateJobStatusMutation,
} from "@/features/jobs/hooks/useJobs";
import type { Job, JobStatus } from "@/features/jobs/types/job";
import { getApiErrorMessage } from "@/shared/api/error";
import { JobStatusBadge } from "@/shared/ui/JobStatusBadge";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { StatCard } from "@/shared/ui/StatCard";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";

export default function JobDashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null);
  const [closeTarget, setCloseTarget] = useState<Job | null>(null);

  const { data: jobs = [], isLoading, isError, refetch } = useRecruiterJobsQuery(user?.id);
  const updateStatusMutation = useUpdateJobStatusMutation();
  const deleteJobMutation = useDeleteJobMutation();

  // Compute stats from jobs array
  const activeJobs = jobs.filter((j) => j.status === "active").length;
  const closedJobs = jobs.filter((j) => j.status === "closed").length;
  const totalApplications = jobs.reduce((sum, j) => sum + (j.applications_count ?? 0), 0);

  useEffect(() => {
    setBreadcrumbItems([{ label: "首页" }, { label: "我的岗位" }]);
  }, [setBreadcrumbItems]);

  const handleCloseJob = async () => {
    if (!closeTarget) return;
    try {
      await updateStatusMutation.mutateAsync({ jobId: closeTarget.id, status: "closed" });
      toast.success("岗位已关闭");
      setCloseTarget(null);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "关闭岗位失败"));
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteJobMutation.mutateAsync(deleteTarget.id);
      toast.success("岗位已删除");
      setDeleteTarget(null);
    } catch (err) {
      toast.error(getApiErrorMessage(err, "删除失败"));
    }
  };

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">我的岗位</h1>
        {/* Skeleton stat cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
        {/* Skeleton table rows */}
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return <ErrorState message="获取岗位列表失败" onRetry={refetch} />;
  }

  if (jobs.length === 0) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">我的岗位</h1>
        <EmptyState
          icon={Briefcase}
          message="暂未发布岗位"
          action={{ label: "发布新岗位", onClick: () => navigate("/dashboard/post") }}
        />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">我的岗位</h1>

      {/* Stat cards row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard icon={Briefcase} value={activeJobs} label="在线岗位" iconColor="text-blue-600" />
        <StatCard icon={XCircle} value={closedJobs} label="已关闭岗位" iconColor="text-slate-500" />
        <StatCard icon={Users} value={totalApplications} label="总申请数" iconColor="text-green-600" />
        <StatCard icon={TrendingUp} value={0} label="本周新增" iconColor="text-amber-600" />
      </div>

      {/* Job table */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>岗位名称</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="text-center">申请人数</TableHead>
              <TableHead>发布时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id}>
                <TableCell className="font-medium">{job.title}</TableCell>
                <TableCell>
                  <JobStatusBadge status={job.status} />
                </TableCell>
                <TableCell className="text-center">
                  {job.applications_count ?? 0}
                </TableCell>
                <TableCell>
                  {new Date(job.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => navigate(`/dashboard/applicants/${job.id}`)}>
                        <Eye className="h-4 w-4 mr-2" />
                        查看申请人
                      </DropdownMenuItem>
                      {job.status === "active" && (
                        <DropdownMenuItem onClick={() => setCloseTarget(job)}>
                          <Pencil className="h-4 w-4 mr-2" />
                          编辑
                        </DropdownMenuItem>
                      )}
                      {job.status === "active" && (
                        <DropdownMenuItem onClick={() => setCloseTarget(job)}>
                          <Power className="h-4 w-4 mr-2" />
                          关闭岗位
                        </DropdownMenuItem>
                      )}
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => setDeleteTarget(job)}
                      >
                        <XCircle className="h-4 w-4 mr-2" />
                        删除
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Close job confirmation dialog */}
      <Dialog open={!!closeTarget} onOpenChange={() => setCloseTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认关闭岗位</DialogTitle>
            <DialogDescription>
              确定要关闭岗位「{closeTarget?.title}」吗？关闭后将不再接受新的投递。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseTarget(null)}>
              取消
            </Button>
            <Button onClick={handleCloseJob} disabled={updateStatusMutation.isPending}>
              确认关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要永久删除岗位「{deleteTarget?.title}」吗？此操作无法撤销，相关投递记录也会被删除。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteJobMutation.isPending}
            >
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/pages/JobDashboardPage.tsx
git commit -m "feat(ui): redesign JobDashboardPage with stat cards, table, and actions"
```

---

### Task 3: Redesign PostJobPage

Replace the flat single-section form with a grouped, sectioned form matching the spec: "基本信息" section, "岗位详情" section, "技能标签" section. Add breadcrumb. Add better form styling with proper labels and validation messages.

**Files:**
- Rewrite: `src/pages/PostJobPage.tsx`

**Interfaces:**
- Consumes:
  - `useCreateJobMutation()` from `@/features/jobs/hooks/useJobs` — `mutateAsync(payload: CreateJobPayload)`
  - `CreateJobPayload` from `@/features/jobs/types/job` — `{ title, description, location?, work_type?, salary_min?, salary_max?, skills_required: string[] }`
  - `WorkType` from `@/features/jobs/types/job` — `"remote" | "onsite" | "hybrid"`
  - `useBreadcrumb()` from `@/shared/ui/layout/breadcrumb-context`
  - shadcn: `Card, CardContent, CardHeader, CardTitle` from `@/components/ui/card`
  - shadcn: `Input` from `@/components/ui/input`
  - shadcn: `Label` from `@/components/ui/label`
  - shadcn: `Select, SelectContent, SelectItem, SelectTrigger, SelectValue` from `@/components/ui/select`
  - shadcn: `Textarea` from `@/components/ui/textarea`
  - shadcn: `Button` from `@/components/ui/button`
  - shadcn: `Separator` from `@/components/ui/separator`
  - `react-hook-form` with `zodResolver`
  - `zod` for validation
- Produces: None (leaf page)

- [ ] **Step 1: Write the full page rewrite**

Replace the entire content of `src/pages/PostJobPage.tsx` with:

```typescript
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { useCreateJobMutation } from "@/features/jobs/hooks/useJobs";
import type { WorkType } from "@/features/jobs/types/job";
import { getApiErrorMessage } from "@/shared/api/error";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";

const WORK_TYPE_OPTIONS: { value: WorkType; label: string }[] = [
  { value: "onsite", label: "现场" },
  { value: "remote", label: "远程" },
  { value: "hybrid", label: "混合" },
];

const jobSchema = z.object({
  title: z.string().min(1, "岗位名称不能为空"),
  description: z.string().min(10, "岗位描述至少10字"),
  location: z.string().optional(),
  work_type: z.enum(["remote", "onsite", "hybrid"]).optional(),
  salary_min: z.number({ invalid_type_error: "请输入数字" }).optional(),
  salary_max: z.number({ invalid_type_error: "请输入数字" }).optional(),
});

type JobForm = z.infer<typeof jobSchema>;

export default function PostJobPage() {
  const navigate = useNavigate();
  const createJobMutation = useCreateJobMutation();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [skillInput, setSkillInput] = useState("");
  const [skills, setSkills] = useState<string[]>([]);

  useEffect(() => {
    setBreadcrumbItems([
      { label: "首页", href: "/dashboard" },
      { label: "发布新岗位" },
    ]);
  }, [setBreadcrumbItems]);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm<JobForm>({
    resolver: zodResolver(jobSchema),
    defaultValues: {
      work_type: "onsite",
    },
  });

  const addSkill = () => {
    const trimmed = skillInput.trim();
    if (trimmed && !skills.includes(trimmed)) {
      setSkills([...skills, trimmed]);
      setSkillInput("");
    }
  };

  const removeSkill = (skill: string) => {
    setSkills(skills.filter((s) => s !== skill));
  };

  const handleSkillKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addSkill();
    }
  };

  const onSubmit = async (data: JobForm) => {
    const payload = {
      ...data,
      skills_required: skills,
    };

    try {
      await createJobMutation.mutateAsync(payload);
      toast.success("岗位发布成功");
      navigate("/dashboard");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "发布失败"));
    }
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold mb-6">发布新岗位</h1>

      <Card className="shadow-sm hover:shadow-md transition-shadow duration-200">
        <form onSubmit={handleSubmit(onSubmit)}>
          {/* 基本信息 */}
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="title">岗位名称</Label>
              <Input id="title" {...register("title")} className="mt-1.5" />
              {errors.title && (
                <p className="text-sm text-destructive mt-1">{errors.title.message}</p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="location">工作地点</Label>
                <Input id="location" {...register("location")} className="mt-1.5" placeholder="如：北京" />
              </div>
              <div>
                <Label>工作类型</Label>
                <Select
                  onValueChange={(value) => setValue("work_type", value as WorkType)}
                  defaultValue="onsite"
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WORK_TYPE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="salary_min">最低薪资 (K)</Label>
                <Input
                  id="salary_min"
                  type="number"
                  {...register("salary_min", { valueAsNumber: true })}
                  className="mt-1.5"
                  placeholder="如：15"
                />
                {errors.salary_min && (
                  <p className="text-sm text-destructive mt-1">{errors.salary_min.message}</p>
                )}
              </div>
              <div>
                <Label htmlFor="salary_max">最高薪资 (K)</Label>
                <Input
                  id="salary_max"
                  type="number"
                  {...register("salary_max", { valueAsNumber: true })}
                  className="mt-1.5"
                  placeholder="如：25"
                />
                {errors.salary_max && (
                  <p className="text-sm text-destructive mt-1">{errors.salary_max.message}</p>
                )}
              </div>
            </div>
          </CardContent>

          <Separator />

          {/* 岗位详情 */}
          <CardHeader>
            <CardTitle>岗位详情</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="description">岗位描述</Label>
              <Textarea
                id="description"
                {...register("description")}
                rows={6}
                className="mt-1.5"
                placeholder="请描述该岗位的主要职责和工作内容..."
              />
              {errors.description && (
                <p className="text-sm text-destructive mt-1">{errors.description.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="requirements">任职要求</Label>
              <Textarea
                id="requirements"
                rows={4}
                className="mt-1.5"
                placeholder="请描述该岗位的任职要求..."
                // Note: no register — this field is not in the current API.
                // It is included per spec for future use but not submitted.
              />
            </div>
          </CardContent>

          <Separator />

          {/* 技能标签 */}
          <CardHeader>
            <CardTitle>技能标签</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={handleSkillKeyDown}
                placeholder="输入技能后按回车添加"
                className="flex-1"
              />
              <Button type="button" variant="outline" onClick={addSkill}>
                <Plus className="h-4 w-4 mr-1" />
                添加
              </Button>
            </div>
            {skills.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {skills.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-3 py-1 text-sm font-medium"
                  >
                    {skill}
                    <button
                      type="button"
                      onClick={() => removeSkill(skill)}
                      className="text-primary/60 hover:text-primary"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </CardContent>

          <Separator />

          {/* Submit */}
          <CardContent className="pt-6">
            <Button
              type="submit"
              className="w-full"
              disabled={createJobMutation.isPending}
            >
              {createJobMutation.isPending ? "发布中..." : "发布岗位"}
            </Button>
          </CardContent>
        </form>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/pages/PostJobPage.tsx
git commit -m "feat(ui): redesign PostJobPage with grouped sections and tag input"
```

---

### Task 4: Redesign ApplicantsPage

Replace the card-grid layout with a professional table layout: breadcrumb → header with job title and count → status filter tabs → applicant table with status badge and actions → resume dialog. Add pagination support.

**Files:**
- Rewrite: `src/pages/ApplicantsPage.tsx`

**Interfaces:**
- Consumes:
  - `useApplicantsByJobQuery(jobId?)` from `@/features/applications/hooks/useApplications` — returns `PaginatedResponse<Applicant>` with `{ total, page, page_size, items: Applicant[] }`
  - `useUpdateApplicationStatusMutation(jobId?)` — `mutateAsync({ applicantId, status: ApplicationStatus })`
  - `useJobDetailQuery(jobId?)` from `@/features/jobs/hooks/useJobs` — returns `{ data: Job }`
  - `Applicant` from `@/features/applications/types/application` — `{ id, applicant_name, resume_text, cover_letter?, structured_resume?, status: ApplicationStatus }`
  - `StructuredResume`, `WorkExperience`, `ProjectExperience`, `Education`, `Certificate`, `Contact` from `@/features/applications/types/application`
  - `ApplicationStatus` from `@/shared/constants/applicationStatus` — `"pending" | "reviewed" | "interview" | "rejected" | "hired"`
  - `APPLICATION_STATUS_MAP` from `@/shared/constants/applicationStatus`
  - `StatusBadge` from `@/shared/ui/StatusBadge` — props: `{ status: ApplicationStatus, className?: string }`
  - `CategoryTabs` from `@/shared/ui/CategoryTabs`
  - `EmptyState` from `@/shared/ui/feedback/EmptyState`
  - `ErrorState` from `@/shared/ui/feedback/ErrorState`
  - `useBreadcrumb()` from `@/shared/ui/layout/breadcrumb-context`
  - shadcn: `Table, TableHeader, TableBody, TableRow, TableHead, TableCell` from `@/components/ui/table`
  - shadcn: `Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle` from `@/components/ui/dialog`
  - shadcn: `Button` from `@/components/ui/button`
  - shadcn: `Badge` from `@/components/ui/badge`
  - shadcn: `Skeleton` from `@/components/ui/skeleton`
  - shadcn: `Separator` from `@/components/ui/separator`
- Produces: None (leaf page)

- [ ] **Step 1: Write the full page rewrite**

Replace the entire content of `src/pages/ApplicantsPage.tsx` with:

```typescript
import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  CheckCircle,
  XCircle,
  FileText,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useApplicantsByJobQuery,
  useUpdateApplicationStatusMutation,
} from "@/features/applications/hooks/useApplications";
import type { Applicant } from "@/features/applications/types/application";
import { useJobDetailQuery } from "@/features/jobs/hooks/useJobs";
import { getApiErrorMessage } from "@/shared/api/error";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";
import { APPLICATION_STATUS_MAP } from "@/shared/constants/applicationStatus";
import { CategoryTabs } from "@/shared/ui/CategoryTabs";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";

const STATUS_CATEGORIES = [
  { key: "all", label: "全部" },
  ...Object.entries(APPLICATION_STATUS_MAP).map(([key, val]) => ({
    key,
    label: val.label,
  })),
];

function formatDate(dateStr?: string) {
  if (!dateStr) return "至今";
  return new Date(dateStr).toLocaleDateString();
}

export default function ApplicantsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedApplicant, setSelectedApplicant] = useState<Applicant | null>(null);

  const { data: job } = useJobDetailQuery(jobId);
  const { data, isLoading, isError, refetch } = useApplicantsByJobQuery(jobId);
  const updateStatusMutation = useUpdateApplicationStatusMutation(jobId);
  const allApplicants = data?.items ?? [];

  // Filter applicants by status
  const applicants = useMemo(() => {
    if (statusFilter === "all") return allApplicants;
    return allApplicants.filter((a) => a.status === statusFilter);
  }, [allApplicants, statusFilter]);

  useEffect(() => {
    setBreadcrumbItems([
      { label: "首页", href: "/dashboard" },
      { label: "我的岗位", href: "/dashboard" },
      ...(job ? [{ label: job.title }] : []),
      { label: "申请人" },
    ]);
  }, [setBreadcrumbItems, job]);

  const updateStatus = async (applicantId: string, newStatus: ApplicationStatus) => {
    try {
      await updateStatusMutation.mutateAsync({ applicantId, status: newStatus });
      toast.success("状态已更新");
      // Update selectedApplicant if it's the same one
      if (selectedApplicant?.id === applicantId) {
        setSelectedApplicant({
          ...selectedApplicant,
          status: newStatus,
        });
      }
    } catch (err) {
      toast.error(getApiErrorMessage(err, "状态更新失败"));
    }
  };

  const renderResumeDialog = () => {
    if (!selectedApplicant) return null;
    const resume = selectedApplicant.structured_resume;

    return (
      <Dialog open={!!selectedApplicant} onOpenChange={() => setSelectedApplicant(null)}>
        <DialogContent className="!max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              {selectedApplicant.applicant_name} 的简历
              <StatusBadge status={selectedApplicant.status} />
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-6 text-sm">
            {resume ? (
              <>
                {/* 基本信息 */}
                <div className="bg-muted/50 p-4 rounded-lg">
                  <h3 className="font-semibold mb-3 text-base border-b pb-2">基本信息</h3>
                  <div className="grid grid-cols-2 gap-y-2 gap-x-6">
                    <div>
                      <span className="font-medium">姓名：</span>
                      {resume.name}
                    </div>
                    <div>
                      <span className="font-medium">工作年限：</span>
                      {resume.work_experience_years}年
                    </div>
                    {resume.education_level && (
                      <div>
                        <span className="font-medium">最高学历：</span>
                        {resume.education_level}
                      </div>
                    )}
                  </div>
                </div>

                {/* 联系方式 */}
                {resume.contact && Object.values(resume.contact).some(Boolean) && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">联系方式</h3>
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                      {resume.contact.phone && (
                        <div><span className="font-medium">📱 手机：</span>{resume.contact.phone}</div>
                      )}
                      {resume.contact.email && (
                        <div><span className="font-medium">✉️ 邮箱：</span>{resume.contact.email}</div>
                      )}
                      {resume.contact.wechat && (
                        <div><span className="font-medium">💬 微信：</span>{resume.contact.wechat}</div>
                      )}
                      {resume.contact.other && (
                        <div><span className="font-medium">🔗 其他：</span>{resume.contact.other}</div>
                      )}
                    </div>
                  </div>
                )}

                {/* 工作经历 */}
                {resume.work_experience?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">工作经历</h3>
                    {resume.work_experience.map((exp, index) => (
                      <div key={index} className="mb-3 border-l-4 border-primary/30 pl-4 last:mb-0">
                        <p className="font-semibold">{exp.company}</p>
                        <p className="text-sm text-muted-foreground">
                          {exp.position} &nbsp;|&nbsp; {formatDate(exp.start_date)} ~ {formatDate(exp.end_date)}
                        </p>
                        <p className="mt-1 text-muted-foreground">{exp.description}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* 项目经历 */}
                {resume.project_experience?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">项目经历</h3>
                    {resume.project_experience.map((proj, index) => (
                      <div key={index} className="mb-3 border-l-4 border-primary/30 pl-4 last:mb-0">
                        <p className="font-semibold">{proj.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {proj.role} &nbsp;|&nbsp; {formatDate(proj.start_date)} ~ {formatDate(proj.end_date)}
                        </p>
                        <p className="mt-1 text-muted-foreground">{proj.description}</p>
                        {proj.technologies?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {proj.technologies.map((tech) => (
                              <Badge key={tech} variant="secondary" className="text-xs">
                                {tech}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* 教育经历 */}
                {resume.education?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">教育经历</h3>
                    {resume.education.map((edu, index) => (
                      <div key={index} className="flex justify-between items-center mb-2 border-b border-dashed pb-1 last:border-0 last:mb-0">
                        <span>
                          <span className="font-medium">{edu.school}</span> · {edu.major} · {edu.degree}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatDate(edu.start_date)} ~ {formatDate(edu.end_date)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* 资格证书 */}
                {resume.certificates?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">资格证书</h3>
                    <div className="flex flex-wrap gap-2">
                      {resume.certificates.map((cert, index) => (
                        <Badge key={index} variant="outline" className="text-sm py-1 px-3">
                          {cert.name}{cert.date ? ` (${cert.date})` : ""}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* 专业技能 */}
                {resume.skills?.length > 0 && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">专业技能</h3>
                    <div className="flex flex-wrap gap-2">
                      {resume.skills.map((skill, index) => (
                        <Badge key={index} variant="default" className="bg-primary/20 text-primary-foreground hover:bg-primary/30 text-sm py-1 px-3">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* 自我评价 */}
                {resume.self_evaluation && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <h3 className="font-semibold mb-3 text-base border-b pb-2">自我评价</h3>
                    <p className="whitespace-pre-wrap leading-relaxed">{resume.self_evaluation}</p>
                  </div>
                )}
              </>
            ) : (
              <div>
                <h3 className="font-semibold mb-2">简历内容（纯文本）</h3>
                <p className="whitespace-pre-wrap text-sm">
                  {selectedApplicant.resume_text || "无简历内容"}
                </p>
              </div>
            )}

            {/* 求职信 */}
            {selectedApplicant.cover_letter && (
              <div className="bg-muted/50 p-4 rounded-lg">
                <h3 className="font-semibold mb-2 text-base border-b pb-2">求职信</h3>
                <p className="whitespace-pre-wrap text-sm">{selectedApplicant.cover_letter}</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    );
  };

  if (isLoading) {
    return (
      <div>
        <Skeleton className="h-8 w-48 mb-6" />
        <Skeleton className="h-10 w-64 mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return <ErrorState message="获取投递列表失败" onRetry={refetch} />;
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            {job ? job.title : "岗位"} · 申请人
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            共 {data?.total ?? 0} 位申请人
          </p>
        </div>
      </div>

      {/* Status filter */}
      <div className="mb-6">
        <CategoryTabs
          categories={STATUS_CATEGORIES}
          activeKey={statusFilter}
          onSelect={setStatusFilter}
        />
      </div>

      {/* Content */}
      {applicants.length === 0 ? (
        <EmptyState
          icon={Users}
          message="暂无申请人"
        />
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>姓名</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>投递时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {applicants.map((app) => (
                <TableRow key={app.id}>
                  <TableCell className="font-medium">{app.applicant_name}</TableCell>
                  <TableCell>
                    <StatusBadge status={app.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">—</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedApplicant(app)}
                      >
                        <FileText className="h-4 w-4 mr-1" />
                        查看简历
                      </Button>
                      {app.status === "pending" && (
                        <>
                          <Button
                            size="sm"
                            onClick={() => updateStatus(app.id, "reviewed")}
                            disabled={updateStatusMutation.isPending}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            通过
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => updateStatus(app.id, "rejected")}
                            disabled={updateStatusMutation.isPending}
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            拒绝
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Resume dialog */}
      {renderResumeDialog()}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/pages/ApplicantsPage.tsx
git commit -m "feat(ui): redesign ApplicantsPage with table, status filter, and resume dialog"
```

---

### Task 5: Production build verification

Verify that the entire application builds successfully with all three redesigned HR pages.

**Files:**
- No changes

- [ ] **Step 1: Run TypeScript type check**

Run: `npx tsc --noEmit`
Expected: No errors

- [ ] **Step 2: Run production build**

Run: `npx vite build`
Expected: Build succeeds with no errors

- [ ] **Step 3: Final commit if any fixes were needed**

(Only if fixes were applied)

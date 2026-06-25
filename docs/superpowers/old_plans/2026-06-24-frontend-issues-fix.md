# Frontend Issues Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 known frontend issues in the HR recruitment system.

**Architecture:** Minimal precise fixes — no architecture changes, no new dependencies. Each task targets one or two files with a specific bug fix or feature addition. The plan follows a dependency order: simpler isolated fixes first, then features that build on prior changes.

**Tech Stack:** React 19, TypeScript, Vite 8, react-router-dom v7, zustand v5, @tanstack/react-query v5, react-hook-form + zod, shadcn/ui + Tailwind CSS v4, FastAPI (backend)

## Global Constraints

- Frontend source root: `frontend/src/`
- Backend source root: `backend/app/`
- All UI uses shadcn/ui components from `@/components/ui/`
- Styling via Tailwind CSS utility classes only — no inline styles
- Chinese (简体中文) for all user-facing text
- Form validation uses zod schemas with `zodResolver`
- State management: zustand for auth, react-query for server state
- Worktree path: `/Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix`
- Run commands from the worktree root: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix`

---

### Task 1: Fix sidebar active highlight (Problem 2)

**Files:**
- Modify: `frontend/src/shared/ui/layout/RecruiterLayout.tsx:32-33`

**Interfaces:**
- Consumes: `location.pathname` from react-router-dom
- Produces: Correct sidebar active state for all recruiter routes

The current `isActive` function at line 32-33 uses `startsWith(path + "/")` which causes `/dashboard/post` to match both `/dashboard` and `/dashboard/post`.

- [ ] **Step 1: Replace the `isActive` function with exact path matching**

In `RecruiterLayout.tsx`, replace the `isActive` function (lines 32-33):

```typescript
// BEFORE:
const isActive = (path: string) =>
  location.pathname === path || location.pathname.startsWith(path + "/");

// AFTER:
const isActive = (path: string) => {
  if (path === "/dashboard") {
    // "我的岗位" is active for /dashboard and /dashboard/applicants/*
    return (
      location.pathname === "/dashboard" ||
      location.pathname.startsWith("/dashboard/applicants/")
    );
  }
  return location.pathname === path;
};
```

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix
git add frontend/src/shared/ui/layout/RecruiterLayout.tsx
git commit -m "fix: sidebar active highlight for /dashboard/post route"
```

---

### Task 2: Fix post job page styling and hints (Problem 1)

**Files:**
- Modify: `frontend/src/pages/PostJobPage.tsx`

**Interfaces:**
- Consumes: Existing `useCreateJobMutation`, form schema, UI components
- Produces: Centered form with required/optional markers, format hints, Card-wrapped sections

- [ ] **Step 1: Replace the entire PostJobPage component**

Replace the full content of `frontend/src/pages/PostJobPage.tsx` with:

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
  salary_min: z.number({ message: "请输入数字" }).optional(),
  salary_max: z.number({ message: "请输入数字" }).optional(),
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
    formState,
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
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">发布新岗位</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* 基本信息 */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="title">
                岗位名称 <span className="text-destructive">*</span>
              </Label>
              <Input
                id="title"
                {...register("title")}
                className="mt-1.5"
                placeholder="例如：高级前端工程师"
              />
              {formState.errors.title && (
                <p className="text-sm text-destructive mt-1">{formState.errors.title.message}</p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="location">
                  工作地点 <span className="text-muted-foreground text-xs">(选填)</span>
                </Label>
                <Input
                  id="location"
                  {...register("location")}
                  className="mt-1.5"
                  placeholder="例如：北京市海淀区"
                />
              </div>
              <div>
                <Label>
                  工作类型 <span className="text-muted-foreground text-xs">(选填)</span>
                </Label>
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
                <Label htmlFor="salary_min">
                  最低薪资 <span className="text-muted-foreground text-xs">(选填)</span>
                </Label>
                <Input
                  id="salary_min"
                  type="number"
                  {...register("salary_min", { valueAsNumber: true })}
                  className="mt-1.5"
                  placeholder="例如：15000"
                />
                <p className="text-xs text-muted-foreground mt-1">请输入月薪范围（元/月）</p>
                {formState.errors.salary_min && (
                  <p className="text-sm text-destructive mt-1">{formState.errors.salary_min.message}</p>
                )}
              </div>
              <div>
                <Label htmlFor="salary_max">
                  最高薪资 <span className="text-muted-foreground text-xs">(选填)</span>
                </Label>
                <Input
                  id="salary_max"
                  type="number"
                  {...register("salary_max", { valueAsNumber: true })}
                  className="mt-1.5"
                  placeholder="例如：25000"
                />
                <p className="text-xs text-muted-foreground mt-1">请输入月薪范围（元/月）</p>
                {formState.errors.salary_max && (
                  <p className="text-sm text-destructive mt-1">{formState.errors.salary_max.message}</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 岗位详情 */}
        <Card>
          <CardHeader>
            <CardTitle>岗位详情</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="description">
                岗位描述 <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="description"
                {...register("description")}
                rows={6}
                className="mt-1.5"
                placeholder="请描述该岗位的主要职责和工作内容..."
              />
              {formState.errors.description && (
                <p className="text-sm text-destructive mt-1">{formState.errors.description.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="requirements">
                任职要求 <span className="text-muted-foreground text-xs">(选填)</span>
              </Label>
              <Textarea
                id="requirements"
                rows={4}
                className="mt-1.5"
                placeholder="请描述该岗位的任职要求..."
              />
            </div>
          </CardContent>
        </Card>

        {/* 技能标签 */}
        <Card>
          <CardHeader>
            <CardTitle>技能标签</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs text-muted-foreground mb-2">按 Enter 添加标签</p>
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
        </Card>

        {/* Submit */}
        <Button
          type="submit"
          className="w-full"
          disabled={formState.isSubmitting || createJobMutation.isPending}
        >
          {createJobMutation.isPending ? "发布中..." : "发布岗位"}
        </Button>
      </form>
    </div>
  );
}
```

Key changes from the original:
1. Outer div: `max-w-3xl` → `max-w-2xl mx-auto` (centered, narrower)
2. Single `Card` wrapping all sections → each section gets its own `Card`
3. Required fields (`title`, `description`): added red `*` after label
4. Optional fields (`location`, `work_type`, `salary_min/max`, `requirements`): added `(选填)` text
5. Salary placeholders: `"如：15"` → `"例如：15000"` with hint `"请输入月薪范围（元/月）"`
6. Location placeholder: `"如：北京"` → `"例如：北京市海淀区"`
7. Skill section: added `"按 Enter 添加标签"` hint text above the input
8. Form sections wrapped with `space-y-6` for spacing between cards
9. Removed the inner `Card` wrapper — each section is now an independent `Card`
10. Submit button outside cards with `w-full` and `mt` spacing from `space-y-6`

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix
git add frontend/src/pages/PostJobPage.tsx
git commit -m "fix: post job page styling, required markers, and format hints"
```

---

### Task 3: Add job detail dialog to dashboard (Problem 3)

**Files:**
- Modify: `frontend/src/pages/JobDashboardPage.tsx`

**Interfaces:**
- Consumes: `useJobDetailQuery(jobId)` from `@/features/jobs/hooks/useJobs`, `Job` type, existing Dialog/DropdownMenu components
- Produces: "查看详情" dropdown item + job detail dialog in dashboard

- [ ] **Step 1: Add imports and state for job detail dialog**

In `JobDashboardPage.tsx`, add the `FileText` icon import and the `useJobDetailQuery` import. Add a `detailTarget` state.

Replace the imports section (lines 1-50) with:

```typescript
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Briefcase,
  Eye,
  FileText,
  MapPin,
  MoreHorizontal,
  Power,
  TrendingUp,
  XCircle,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
  useJobDetailQuery,
  useRecruiterJobsQuery,
  useUpdateJobStatusMutation,
} from "@/features/jobs/hooks/useJobs";
import type { Job } from "@/features/jobs/types/job";
import { getApiErrorMessage } from "@/shared/api/error";
import { JobStatusBadge } from "@/shared/ui/JobStatusBadge";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { StatCard } from "@/shared/ui/StatCard";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
```

- [ ] **Step 2: Add `detailTarget` state and detail dialog component**

In the component body, after `const [closeTarget, setCloseTarget] = useState<Job | null>(null);` (around line 57), add:

```typescript
const [detailTarget, setDetailTarget] = useState<string | null>(null);
```

Then add a helper for work type labels and the detail dialog query/component. After the `handleDelete` function (around line 92), add:

```typescript
const WORK_TYPE_LABELS: Record<string, string> = {
  remote: "远程",
  onsite: "现场",
  hybrid: "混合",
};
```

- [ ] **Step 3: Add "查看详情" dropdown item**

In the `DropdownMenuContent` (around line 176-194), add a new `DropdownMenuItem` BEFORE the "查看申请人" item:

```typescript
<DropdownMenuItem onClick={() => setDetailTarget(job.id)}>
  <FileText className="h-4 w-4 mr-2" />
  查看详情
</DropdownMenuItem>
```

- [ ] **Step 4: Add job detail dialog after the delete confirmation dialog**

Add the following dialog after the closing `</Dialog>` of the delete confirmation dialog (around line 245), before the final `</div>`:

```typescript
{/* Job detail dialog */}
<Dialog open={!!detailTarget} onOpenChange={() => setDetailTarget(null)}>
  <DialogContent className="max-w-lg">
    <DialogHeader>
      <DialogTitle>岗位详情</DialogTitle>
      <DialogDescription>查看已发布岗位的完整信息</DialogDescription>
    </DialogHeader>
    {detailTarget && <JobDetailContent jobId={detailTarget} onClose={() => setDetailTarget(null)} />}
  </DialogContent>
</Dialog>
```

- [ ] **Step 5: Add the `JobDetailContent` helper component**

Add this component BEFORE the `export default function JobDashboardPage()` declaration:

```typescript
function JobDetailContent({ jobId, onClose }: { jobId: string; onClose: () => void }) {
  const { data: job, isLoading } = useJobDetailQuery(jobId);

  if (isLoading) {
    return <Skeleton className="h-48 w-full rounded-lg" />;
  }

  if (!job) {
    return <p className="text-muted-foreground">无法加载岗位信息</p>;
  }

  const hasSalary = job.salary_min != null || job.salary_max != null;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">{job.title}</h3>
        <div className="flex items-center gap-2 mt-1">
          <JobStatusBadge status={job.status} />
          {job.location && (
            <span className="text-sm text-muted-foreground flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {job.location}
            </span>
          )}
          {job.work_type && (
            <span className="text-sm text-muted-foreground">
              {WORK_TYPE_LABELS[job.work_type] ?? job.work_type}
            </span>
          )}
        </div>
      </div>

      {hasSalary && (
        <p className="text-primary font-bold">
          {job.salary_min != null ? `${job.salary_min}k` : ""}
          {job.salary_min != null && job.salary_max != null ? " - " : ""}
          {job.salary_max != null ? `${job.salary_max}k` : ""}
        </p>
      )}

      {job.skills_required.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {job.skills_required.map((skill) => (
            <Badge key={skill} variant="secondary">{skill}</Badge>
          ))}
        </div>
      )}

      {job.description && (
        <div>
          <h4 className="text-sm font-medium mb-1">岗位描述</h4>
          <p className="text-sm text-muted-foreground whitespace-pre-line">{job.description}</p>
        </div>
      )}

      <div className="text-xs text-muted-foreground space-y-0.5">
        <p>发布时间：{new Date(job.created_at).toLocaleString()}</p>
        <p>更新时间：{new Date(job.updated_at).toLocaleString()}</p>
      </div>
    </div>
  );
}

const WORK_TYPE_LABELS: Record<string, string> = {
  remote: "远程",
  onsite: "现场",
  hybrid: "混合",
};
```

Note: Remove the `WORK_TYPE_LABELS` that was added inside the component body in Step 2 — it should only exist once, outside both components.

- [ ] **Step 6: Verify build passes**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix
git add frontend/src/pages/JobDashboardPage.tsx
git commit -m "feat: add job detail dialog to dashboard page"
```

---

### Task 4: Add registration page (Problem 4)

**Files:**
- Create: `frontend/src/pages/RegisterPage.tsx`
- Modify: `frontend/src/pages/LoginPage.tsx:106-113`
- Modify: `frontend/src/App.tsx:38,9-11`

**Interfaces:**
- Consumes: `useRegisterMutation` from `@/features/auth/hooks/useAuthMutations`, `RegisterData` type, `useAuthStore`, `UserRole` type
- Produces: `/register` route with registration form, auto-login on success

- [ ] **Step 1: Create RegisterPage.tsx**

Create `frontend/src/pages/RegisterPage.tsx`:

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Briefcase } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRegisterMutation } from "@/features/auth/hooks/useAuthMutations";
import type { UserRole } from "@/features/auth/types/auth";
import { getApiErrorMessage } from "@/shared/api/error";

const registerSchema = z
  .object({
    email: z.string().email("请输入有效的邮箱地址"),
    password: z.string().min(6, "密码至少6个字符"),
    confirmPassword: z.string().min(1, "请确认密码"),
    name: z.string().min(1, "请输入姓名"),
    role: z.enum(["job_seeker", "recruiter"], { required_error: "请选择角色" }),
    phone: z.string().optional(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "两次输入的密码不一致",
    path: ["confirmPassword"],
  });

type RegisterForm = z.infer<typeof registerSchema>;

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: "job_seeker", label: "求职者" },
  { value: "recruiter", label: "招聘方" },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegisterMutation();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      role: "job_seeker",
    },
  });

  const onSubmit = async (data: RegisterForm) => {
    try {
      const { confirmPassword, ...registerData } = data;
      const res = await registerMutation.mutateAsync(registerData);
      navigate(res.user.role === "recruiter" ? "/dashboard" : "/jobs");
    } catch (err) {
      toast.error(getApiErrorMessage(err as AxiosError, "注册失败"));
    }
  };

  return (
    <div className="h-screen flex">
      {/* Left panel — brand illustration */}
      <div className="flex w-1/2 bg-gradient-to-br from-blue-600 to-blue-800 items-center justify-center p-12">
        <div className="max-w-md text-center text-white">
          <div className="mb-8 flex justify-center relative">
            <svg
              width="120"
              height="120"
              viewBox="0 0 120 120"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="opacity-90"
            >
              <rect x="20" y="30" width="80" height="60" rx="8" fill="white" fillOpacity="0.2" stroke="white" strokeOpacity="0.4" strokeWidth="2" />
              <rect x="30" y="40" width="60" height="8" rx="4" fill="white" fillOpacity="0.3" />
              <rect x="30" y="54" width="40" height="4" rx="2" fill="white" fillOpacity="0.2" />
              <rect x="30" y="64" width="50" height="4" rx="2" fill="white" fillOpacity="0.2" />
              <rect x="30" y="74" width="30" height="4" rx="2" fill="white" fillOpacity="0.2" />
            </svg>
            <Briefcase className="absolute top-0 right-0 text-white/80 w-6 h-6" />
          </div>
          <h1 className="text-3xl font-bold mb-3">智能简历投递系统</h1>
          <p className="text-blue-100 text-lg">让求职更高效</p>
        </div>
      </div>

      {/* Right panel — register form */}
      <div className="flex-1 flex items-center justify-center bg-background p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-bold">创建账户</h2>
            <p className="text-muted-foreground mt-1">注册以开始使用</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <Input
                id="email"
                type="email"
                placeholder="请输入邮箱"
                {...register("email")}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                placeholder="至少6个字符"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">确认密码</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="请再次输入密码"
                {...register("confirmPassword")}
              />
              {errors.confirmPassword && (
                <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">姓名</Label>
              <Input
                id="name"
                placeholder="请输入姓名"
                {...register("name")}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label>角色</Label>
              <Select
                onValueChange={(value) => setValue("role", value as UserRole)}
                defaultValue="job_seeker"
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.role && (
                <p className="text-sm text-destructive">{errors.role.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">
                手机号 <span className="text-muted-foreground text-xs">(选填)</span>
              </Label>
              <Input
                id="phone"
                placeholder="请输入手机号"
                {...register("phone")}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={registerMutation.isPending}
            >
              {registerMutation.isPending ? "注册中..." : "注册"}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-4">
            已有账号？{" "}
            <a href="/login" className="text-primary hover:underline">
              立即登录
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add register link to LoginPage**

In `LoginPage.tsx`, after the `</form>` closing tag (line 113) and before the closing `</div>` of the right panel, add:

```typescript
<p className="text-center text-sm text-muted-foreground mt-4">
  还没有账号？{" "}
  <a href="/register" className="text-primary hover:underline">
    立即注册
  </a>
</p>
```

- [ ] **Step 3: Add /register route to App.tsx**

In `App.tsx`, add the import for RegisterPage:

```typescript
import RegisterPage from "@/pages/RegisterPage";
```

Add the route after the `/login` route (line 38):

```typescript
<Route path="/register" element={<RegisterPage />} />
```

- [ ] **Step 4: Verify build passes**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix
git add frontend/src/pages/RegisterPage.tsx frontend/src/pages/LoginPage.tsx frontend/src/App.tsx
git commit -m "feat: add registration page with auto-login"
```

---

### Task 5: Fix backend — add job_title and status filter to my applications API (Problem 6, backend part)

**Files:**
- Modify: `backend/app/api/applications.py:54-65`
- Modify: `backend/app/services/application_service.py:97-112`

**Interfaces:**
- Consumes: `Application` model with `job` relationship, `ApplicationStatus` enum
- Produces: `GET /api/v1/applications/my` returns `job_title` and `company_name` fields, accepts `status` query parameter

The root causes of problem 6:
1. `get_my_applications` service only loads `Application.applicant` via `selectinload`, but does NOT load `Application.job` — so `job_title` is `None` in the response
2. The `/my` endpoint does not accept a `status` query parameter — frontend filtering is sent but ignored
3. The `_app_to_dict` helper in the API route is not called with `job_title` from the `my_applications` endpoint

- [ ] **Step 1: Fix the service to load the job relationship and support status filtering**

In `backend/app/services/application_service.py`, replace the `get_my_applications` function (lines 97-112):

```python
async def get_my_applications(
    db: AsyncSession,
    current_user: User,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[list[Application], int]:
    """求职者查看自己的投递记录"""
    query = select(Application).where(Application.applicant_id == current_user.id).options(
        selectinload(Application.applicant),
        selectinload(Application.job),
    )

    if status_filter:
        try:
            query = query.where(Application.status == ApplicationStatus(status_filter))
        except ValueError:
            pass

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    page_query = query.order_by(Application.created_at.desc()).offset(offset).limit(page_size)
    applications = list((await db.execute(page_query)).scalars().all())
    return applications, total
```

- [ ] **Step 2: Fix the API endpoint to pass status filter and job_title**

In `backend/app/api/applications.py`, replace the `my_applications` endpoint (lines 54-65):

```python
@router.get("/my", response_model=ApplicationListResponse, summary="我的投递记录")
async def my_applications(
    status: Optional[str] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> ApplicationListResponse:
    applications, total = await application_service.get_my_applications(
        db, current_user, status_filter=status, page=page, page_size=page_size
    )
    items = [
        ApplicationResponse.model_validate(
            _app_to_dict(
                app,
                applicant_name=current_user.name,
                job_title=app.job.title if app.job else None,
            )
        )
        for app in applications
    ]
    return ApplicationListResponse(total=total, page=page, page_size=page_size, items=items)
```

Key changes:
1. Added `status: Optional[str] = Query(None, ...)` parameter
2. Pass `status_filter=status` to the service
3. Load `app.job.title` from the eagerly-loaded relationship and pass it to `_app_to_dict`

- [ ] **Step 3: Verify backend starts**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix/backend && python -c "from app.api.applications import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix
git add backend/app/api/applications.py backend/app/services/application_service.py
git commit -m "fix: add job_title and status filter to my applications API"
```

---

### Task 6: Fix frontend — show applied status on job market (Problem 5)

**Files:**
- Modify: `frontend/src/shared/ui/JobCard.tsx`
- Modify: `frontend/src/pages/JobMarketPage.tsx`

**Interfaces:**
- Consumes: `useMyApplicationsQuery` from `@/features/applications/hooks/useApplications`, `useAuthStore`
- Produces: `applied` prop on `JobCard`, "已投递" badge + disabled button

- [ ] **Step 1: Add `applied` prop to JobCard**

Replace `frontend/src/shared/ui/JobCard.tsx` with:

```typescript
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Job } from "@/features/jobs/types/job";

const WORK_TYPE_LABELS: Record<string, string> = {
  remote: "远程",
  onsite: "现场",
  hybrid: "混合",
};

interface JobCardProps {
  job: Job;
  applied?: boolean;
}

export function JobCard({ job, applied = false }: JobCardProps) {
  const hasSalary = job.salary_min != null || job.salary_max != null;
  const locationParts = [job.recruiter_name, job.location].filter(Boolean);

  return (
    <Card className="h-full shadow-sm hover:shadow-md transition-shadow duration-200 relative">
      {applied && (
        <div className="absolute top-3 right-3">
          <Badge className="bg-green-100 text-green-800 hover:bg-green-100/80">已投递</Badge>
        </div>
      )}
      <Link to={`/jobs/${job.id}`} className="block hover:no-underline">
        <CardContent className="p-6">
          <h3 className="text-lg font-semibold">{job.title}</h3>
          <p className="text-sm text-muted-foreground mt-1">
            {locationParts.join(" · ")}
            {job.work_type && ` · ${WORK_TYPE_LABELS[job.work_type] ?? job.work_type}`}
          </p>
          {hasSalary && (
            <p className="text-primary font-bold mt-2">
              {job.salary_min != null ? `${job.salary_min}k` : ""}
              {job.salary_min != null && job.salary_max != null ? " - " : ""}
              {job.salary_max != null ? `${job.salary_max}k` : ""}
            </p>
          )}
          {job.skills_required.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {job.skills_required.slice(0, 3).map((skill) => (
                <Badge key={skill} variant="secondary">
                  {skill}
                </Badge>
              ))}
              {job.skills_required.length > 3 && (
                <Badge variant="outline">+{job.skills_required.length - 3}</Badge>
              )}
            </div>
          )}
          {job.description && (
            <p className="text-sm text-muted-foreground mt-3 line-clamp-2">
              {job.description}
            </p>
          )}
        </CardContent>
      </Link>
      <div className="px-6 pb-4">
        {applied ? (
          <Button variant="secondary" className="w-full" disabled>
            已投递
          </Button>
        ) : (
          <Link to={`/apply/${job.id}`}>
            <Button className="w-full">
              立即投递
            </Button>
          </Link>
        )}
      </div>
    </Card>
  );
}
```

Key changes:
1. Added `applied?: boolean` prop (default `false`)
2. When `applied=true`: green "已投递" badge in top-right corner, disabled "已投递" button at bottom
3. When `applied=false`: "立即投递" link button at bottom (same as before)
4. The `<Link>` wrapper now only wraps the content area, not the button — so the card is still clickable for viewing details, but the apply button is separate

- [ ] **Step 2: Update JobMarketPage to fetch applications and pass applied prop**

In `JobMarketPage.tsx`, add the applications query. Replace the entire file:

```typescript
import { useEffect, useState } from "react";
import { Briefcase } from "lucide-react";

import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useMyApplicationsQuery } from "@/features/applications/hooks/useApplications";
import type { WorkType } from "@/features/jobs/types/job";
import { useJobsQuery } from "@/features/jobs/hooks/useJobs";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import { CategoryTabs } from "@/shared/ui/CategoryTabs";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { JobCard } from "@/shared/ui/JobCard";
import { SearchBar } from "@/shared/ui/SearchBar";

const WORK_TYPE_CATEGORIES: { key: string; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "remote", label: "远程" },
  { key: "onsite", label: "现场" },
  { key: "hybrid", label: "混合" },
];

const PAGE_SIZE = 9;

export default function JobMarketPage() {
  const [keyword, setKeyword] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [workType, setWorkType] = useState<string>("all");
  const [page, setPage] = useState(1);
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    setBreadcrumbItems([{ label: "岗位市场" }]);
  }, [setBreadcrumbItems]);

  const params = {
    ...(keyword ? { keyword } : {}),
    ...(workType !== "all" ? { work_type: workType as WorkType } : {}),
    page,
    page_size: PAGE_SIZE,
  };

  const { data, isLoading, isError, refetch } = useJobsQuery(params);
  const jobs = data?.items ?? [];
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  // Fetch user's applications to determine which jobs they've already applied to
  const isJobSeeker = user?.role === "job_seeker";
  const { data: applicationsData } = useMyApplicationsQuery(
    isJobSeeker ? { page: 1, page_size: 100 } : {}
  );
  const appliedJobIds = isJobSeeker
    ? new Set((applicationsData?.items ?? []).map((app) => app.job_id))
    : new Set<string>();

  const handleSearch = () => {
    setKeyword(searchInput);
    setPage(1);
  };

  const handleWorkTypeChange = (key: string) => {
    setWorkType(key);
    setPage(1);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">岗位市场</h1>

      {/* Search bar */}
      <div className="mb-4">
        <SearchBar
          value={searchInput}
          onChange={setSearchInput}
          onSearch={handleSearch}
          placeholder="搜索岗位名称或描述..."
        />
      </div>

      {/* Category filter tabs */}
      <div className="mb-6">
        <CategoryTabs
          categories={WORK_TYPE_CATEGORIES}
          activeKey={workType}
          onSelect={handleWorkTypeChange}
        />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-40 w-full rounded-lg" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <ErrorState message="获取岗位列表失败" onRetry={refetch} />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          message="暂无匹配岗位"
          action={{ label: "清除筛选", onClick: () => { setWorkType("all"); setKeyword(""); setSearchInput(""); setPage(1); } }}
        />
      ) : (
        <>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                applied={appliedJobIds.has(job.id)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8">
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      text="上一页"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
                    .map((p, i, arr) => (
                      <PaginationItem key={p}>
                        {i > 0 && arr[i - 1] < p - 1 && (
                          <span className="px-1 text-muted-foreground">...</span>
                        )}
                        <PaginationLink
                          isActive={p === page}
                          onClick={() => setPage(p)}
                          className="cursor-pointer"
                        >
                          {p}
                        </PaginationLink>
                      </PaginationItem>
                    ))}
                  <PaginationItem>
                    <PaginationNext
                      text="下一页"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      className={page >= totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

Key changes:
1. Import `useAuthStore` and `useMyApplicationsQuery`
2. When user is a job_seeker, fetch their applications (page_size=100 to cover most cases)
3. Build `appliedJobIds` set from the applications response
4. Pass `applied={appliedJobIds.has(job.id)}` to each `JobCard`
5. When user is not a job_seeker, pass empty Set (no applied state shown)

- [ ] **Step 3: Verify build passes**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix
git add frontend/src/shared/ui/JobCard.tsx frontend/src/pages/JobMarketPage.tsx
git commit -m "feat: show applied status on job market cards"
```

---

### Task 7: Fix frontend — my applications page display and detail dialog (Problem 6, frontend part)

**Files:**
- Modify: `frontend/src/pages/MyApplicationsPage.tsx`

**Interfaces:**
- Consumes: `useMyApplicationsQuery`, `MyApplication` type (with `job_title`, `company_name`, `resume_text`, `status`, `created_at`), `APPLICATION_STATUS_MAP`
- Produces: Application cards with proper title display, working status filter, detail dialog on click

The backend fix from Task 5 ensures `job_title` is now returned. The frontend already has display code for `job_title` and `company_name` — we need to verify it works, add the status filter fix (it should work now that the backend accepts `status`), and add the detail dialog.

- [ ] **Step 1: Replace MyApplicationsPage.tsx with full fix**

Replace `frontend/src/pages/MyApplicationsPage.tsx`:

```typescript
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Briefcase, MapPin } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { ApplicationStatus } from "@/shared/constants/applicationStatus";
import { APPLICATION_STATUS_MAP } from "@/shared/constants/applicationStatus";
import type { MyApplication } from "@/features/applications/types/application";
import { useMyApplicationsQuery } from "@/features/applications/hooks/useApplications";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import { CategoryTabs } from "@/shared/ui/CategoryTabs";
import EmptyState from "@/shared/ui/feedback/EmptyState";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

const STATUS_CATEGORIES = [
  { key: "all" as const, label: "全部" },
  ...Object.entries(APPLICATION_STATUS_MAP).map(([key, val]) => ({
    key: key as ApplicationStatus,
    label: val.label,
  })),
];

export default function MyApplicationsPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [detailTarget, setDetailTarget] = useState<MyApplication | null>(null);
  const { setItems: setBreadcrumbItems } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumbItems([{ label: "我的投递" }]);
  }, [setBreadcrumbItems]);

  const params = {
    ...(statusFilter !== "all" ? { status: statusFilter as ApplicationStatus } : {}),
  };

  const { data, isLoading, isError, refetch } = useMyApplicationsQuery(params);
  const applications = data?.items ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">我的投递</h1>

      {/* Status filter tabs */}
      <div className="mb-6">
        <CategoryTabs
          categories={STATUS_CATEGORIES}
          activeKey={statusFilter}
          onSelect={setStatusFilter}
        />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState message="获取投递记录失败" onRetry={refetch} />
      ) : applications.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          message="暂无投递记录"
          action={{ label: "去看看岗位", onClick: () => navigate("/jobs") }}
        />
      ) : (
        <div className="space-y-4">
          {applications.map((app) => (
            <Card
              key={app.id}
              className="hover:shadow-md transition-shadow duration-200 cursor-pointer"
              onClick={() => setDetailTarget(app)}
            >
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold truncate">
                      {app.job_title || "未知岗位"}
                    </h3>
                    {app.company_name && (
                      <p className="text-sm text-muted-foreground mt-1">{app.company_name}</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-2">
                      投递时间：{new Date(app.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="ml-4 shrink-0">
                    <StatusBadge status={app.status} />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Application detail dialog */}
      <Dialog open={!!detailTarget} onOpenChange={() => setDetailTarget(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>投递详情</DialogTitle>
            <DialogDescription>查看投递的详细信息</DialogDescription>
          </DialogHeader>
          {detailTarget && (
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold">
                  {detailTarget.job_title || "未知岗位"}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <StatusBadge status={detailTarget.status} />
                  {detailTarget.company_name && (
                    <span className="text-sm text-muted-foreground flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {detailTarget.company_name}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">投递时间</h4>
                <p className="text-sm text-muted-foreground">
                  {new Date(detailTarget.created_at).toLocaleString()}
                </p>
              </div>

              {detailTarget.resume_text && (
                <div>
                  <h4 className="text-sm font-medium mb-1">简历摘要</h4>
                  <p className="text-sm text-muted-foreground line-clamp-6 whitespace-pre-line">
                    {detailTarget.resume_text}
                  </p>
                </div>
              )}

              <Button
                variant="outline"
                className="w-full"
                onClick={() => {
                  setDetailTarget(null);
                  navigate(`/jobs/${detailTarget.job_id}`);
                }}
              >
                查看岗位详情
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

Key changes from the original:
1. Added `detailTarget` state and dialog for viewing application details
2. Made cards clickable (`cursor-pointer` + `onClick`) to open detail dialog
3. Added fallback `|| "未知岗位"` for `job_title` in case backend still returns null
4. Removed the `navigate` on job title click — now the whole card opens detail dialog
5. Detail dialog shows: job title, status badge, company, submission time, resume summary, and a "查看岗位详情" button
6. The status filter now works because Task 5 added `status` parameter support to the backend API

- [ ] **Step 2: Verify build passes**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix
git add frontend/src/pages/MyApplicationsPage.tsx
git commit -m "feat: add application detail dialog and fix status filtering"
```

---

### Task 8: Final verification — build and type check

**Files:** None (verification only)

- [ ] **Step 1: Run full TypeScript check**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 2: Run production build**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix/frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 3: Verify all 6 commits exist**

Run: `cd /Users/bytedance/my_code/hr_agent/.claude/worktrees/frontend-issues-fix && git log --oneline -8`
Expected: All 7 implementation commits (Tasks 1-7) visible on top of the base commit

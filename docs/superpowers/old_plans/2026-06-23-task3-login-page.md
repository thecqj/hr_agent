# Task 3: Login Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign LoginPage as a professional left-right split layout with blue gradient brand panel and clean login form.

**Architecture:** Replace the current centered card + tabs (login/register) layout with a full-viewport split design. Left panel: blue gradient background with SVG brand illustration and tagline. Right panel: white background with centered login form. Registration tab is removed per design spec ("No registration link — no registration API currently").

**Tech Stack:** React, react-hook-form, zod, shadcn/ui (Button, Input, Label), Tailwind CSS v4, lucide-react icons

## Global Constraints

- Desktop only, no mobile adaptation (spec §1)
- Use design tokens from `index.css` (e.g., `bg-background`, `text-primary`, not raw `bg-gray-50`)
- Font: Geist Variable (already configured)
- No dark mode support for this page (spec §7: out of scope)
- No animation library — Tailwind transitions only (spec §7)
- Brand color: blue-600 primary (spec §1.1)
- Full viewport: `h-screen`, no scroll (spec §2.3)

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `frontend/src/pages/LoginPage.tsx` | Complete rewrite — split layout login page |
| Modify | `frontend/src/App.tsx` | Minor: ensure LoginPage route has no layout wrapper (already correct, verify) |

No new files needed. The SVG brand illustration will be inline JSX (not a separate asset file), keeping it simple per spec §7 ("use SVG placeholders").

---

### Task 1: Redesign LoginPage with split layout

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx` (complete rewrite)

**Interfaces:**
- Consumes: `useLoginMutation()` from `@/features/auth/hooks/useAuthMutations` — returns `{ mutateAsync, isPending }`
- Consumes: `useNavigate()` from `react-router-dom`
- Consumes: `getApiErrorMessage(err, fallback)` from `@/shared/api/error`
- Consumes: shadcn `Button`, `Input`, `Label` from `@/components/ui/*`
- Consumes: `toast` from `sonner`
- Consumes: `zod`, `zodResolver`, `useForm` from existing packages
- Produces: default export `LoginPage` component (consumed by `App.tsx` route)

**Design reference (spec §2.3 & §4.1):**

```
┌──────────────────────┬───────────────────────────┐
│                      │                           │
│                      │     欢迎回来               │
│                      │                           │
│   [Brand illustration│     登录您的账户            │
│    + tagline]         │                           │
│                      │     邮箱                   │
│   智能简历投递系统     │     [_______________]      │
│   让求职更高效         │                           │
│                      │     密码                   │
│                      │     [_______________]      │
│                      │                           │
│                      │     [  登  录  ]           │
│   Blue gradient bg   │     White background       │
└──────────────────────┴───────────────────────────┘
```

- [ ] **Step 1: Rewrite LoginPage.tsx with the split layout and login form**

Replace the entire file content with the new design. Key changes from current code:

1. **Remove** register tab, `registerSchema`, `registerForm`, `useRegisterMutation`, `Checkbox`, `Tabs` imports
2. **Add** left panel with blue gradient background, inline SVG illustration, brand name + tagline
3. **Add** right panel with centered login form showing validation errors
4. **Use design tokens** (`bg-background`, `text-primary`, etc.) instead of raw colors

```tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AxiosError } from "axios";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Briefcase } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLoginMutation } from "@/features/auth/hooks/useAuthMutations";
import { getApiErrorMessage } from "@/shared/api/error";

const loginSchema = z.object({
  email: z.string().email("请输入有效的邮箱地址"),
  password: z.string().min(6, "密码至少6个字符"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const loginMutation = useLoginMutation();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    try {
      const res = await loginMutation.mutateAsync(data);
      navigate(res.user.role === "recruiter" ? "/dashboard" : "/jobs");
    } catch (err) {
      toast.error(getApiErrorMessage(err as AxiosError, "登录失败"));
    }
  };

  return (
    <div className="h-screen flex">
      {/* Left panel — brand illustration */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-600 to-blue-800 items-center justify-center p-12">
        <div className="max-w-md text-center text-white">
          {/* SVG brand illustration placeholder */}
          <div className="mb-8 flex justify-center">
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
              <circle cx="90" cy="35" r="12" fill="white" fillOpacity="0.25" />
              <Briefcase className="text-white/80" x="82" y="28" width="16" height="16" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold mb-3">智能简历投递系统</h1>
          <p className="text-blue-100 text-lg">让求职更高效</p>
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="flex-1 flex items-center justify-center bg-background p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="text-2xl font-bold">欢迎回来</h2>
            <p className="text-muted-foreground mt-1">登录您的账户</p>
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
                placeholder="请输入密码"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={loginMutation.isPending}
            >
              {loginMutation.isPending ? "登录中..." : "登录"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run TypeScript type check to verify no errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS (no errors)

- [ ] **Step 3: Run the dev server and visually verify the login page**

Run: `cd frontend && npm run dev`

Verify in browser:
1. Navigate to `/login`
2. Left panel shows blue gradient with SVG illustration + "智能简历投递系统" + "让求职更高效"
3. Right panel shows "欢迎回来" heading, "登录您的账户" subtitle
4. Email and password inputs with labels and placeholder text
5. "登录" primary button
6. Form validation errors appear when submitting empty/invalid data
7. Login works with valid credentials and redirects correctly
8. Page fills full viewport height with no scrolling
9. No register tab is present

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "feat(ui): redesign LoginPage with left-right split layout (Task 3)

- Replace centered card + tabs layout with full-viewport split design
- Left panel: blue gradient background with SVG brand illustration and tagline
- Right panel: white background with centered login form
- Add form validation error display for email and password fields
- Remove register tab (no registration API per design spec)
- Use design tokens (bg-background, text-primary, etc.) instead of raw colors"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- ✅ Left-right split layout (spec §2.3)
- ✅ Left panel: blue gradient `bg-gradient-to-br from-blue-600 to-blue-800` (spec §2.3)
- ✅ SVG brand illustration placeholder (spec §2.3, §7 "use SVG placeholders")
- ✅ Tagline: "智能简历投递系统" + "让求职更高效" (spec §4.1)
- ✅ Right panel: white background, centered form, `max-w-sm` (spec §2.3)
- ✅ Heading: "欢迎回来" `text-2xl font-bold` (spec §4.1)
- ✅ Subheading: "登录您的账户" `text-muted-foreground` (spec §4.1)
- ✅ Email input with label (spec §4.1)
- ✅ Password input with label (spec §4.1)
- ✅ Primary button "登录" (spec §4.1)
- ✅ No registration link (spec §4.1)
- ✅ Full viewport: `h-screen`, no scroll (spec §2.3)
- ✅ Design tokens used (spec §1)
- ✅ No animation library (spec §7)

**2. Placeholder scan:**
- No TBD, TODO, "implement later", or "fill in details" found ✅
- No "add appropriate error handling" / "add validation" without code ✅
- No "similar to Task N" shortcuts ✅
- All steps have actual code ✅

**3. Type consistency:**
- `useLoginMutation()` returns `{ mutateAsync, isPending }` — matches usage ✅
- `loginSchema` infers `LoginForm` with `email: string, password: string` ✅
- `onSubmit` receives `LoginForm` — matches `handleSubmit` type ✅
- `getApiErrorMessage(err as AxiosError, "登录失败")` — matches existing signature ✅
- `navigate()` receives string path — matches react-router-dom v6 API ✅

**4. Gap check:**
- The design spec §4.1 mentions no password visibility toggle — not included, correct per spec
- No "remember me" checkbox — not in spec, not included ✅
- The register tab removal is explicitly per spec §4.1: "No registration link (no registration API currently)" ✅

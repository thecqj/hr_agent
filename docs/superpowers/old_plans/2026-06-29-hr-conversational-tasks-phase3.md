# Phase 3: 前端卡片组件与集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在前端实现 5 种新卡片组件（JobListCard、JobDetailCard、FunnelCard、CandidateListCard、ConfirmCard），扩展 ChatCard 类型联合，并更新 AssistantMessage 组件路由，使前端完整渲染所有新意图的响应。

**Architecture:** 扩展现有 `ChatCard` 接口为可辨识联合类型，新增 5 个卡片组件，在 `AssistantMessage` 中按 `card.type` 分发渲染。ConfirmCard 包含确认/取消按钮，点击后通过 `sendMessage` 发送消息。

**Tech Stack:** React 19, TypeScript, Tailwind CSS, lucide-react

## Global Constraints

- Follow existing component patterns (see `EvaluationCard.tsx`)
- Use shadcn/ui components (`Card`, `CardContent`, `Button`)
- Use lucide-react icons
- Tailwind CSS for styling — no new CSS libraries
- ChatCard discriminated union by `type` field
- ConfirmCard button clicks trigger `sendMessage("确认")` or `sendMessage("取消")`

---

### Task 1: Expand ChatCard Type Union

**Files:**
- Modify: `frontend/src/features/chat/types/chat.ts`
- Test: Visual (no unit tests for types)

**Interfaces:**
- Consumes: Existing `ChatCard` interface
- Produces: Expanded `ChatCard` discriminated union with 6 variants; new sub-types `JobListCardData`, `JobDetailCardData`, `FunnelCardData`, `FunnelStageData`, `CandidateListCardData`, `CandidateItemData`, `ConfirmCardData`

- [ ] **Step 1: Update ChatCard types**

Replace `frontend/src/features/chat/types/chat.ts`:

```ts
// ── 漏斗阶段 ─────────────────────────────────────────────

export interface FunnelStageData {
  status: string;
  count: number;
  percentage: number;
}

// ── 候选人条目 ─────────────────────────────────────────────

export interface CandidateItemData {
  name: string;
  ai_score: number | null;
  ai_decision: string | null;
  status: string;
}

// ── 卡片类型 ─────────────────────────────────────────────

export interface EvaluationSummaryCardData {
  type: "evaluation_summary";
  task_id: string;
  job_title: string;
  total_count: number;
  recommended_count: number;
  rejected_count: number;
  result_page_url: string;
}

export interface JobListCardData {
  type: "job_list";
  jobs: {
    job_code: string;
    title: string;
    status: string;
    head_count: number;
  }[];
}

export interface JobDetailCardData {
  type: "job_detail";
  job: {
    job_code: string;
    title: string;
    description: string;
    requirements: string;
    skills_required: string[];
    salary_min: number | null;
    salary_max: number | null;
    location: string | null;
    work_type: string;
    head_count: number;
    interview_quota: number;
    status: string;
  };
}

export interface FunnelCardData {
  type: "funnel";
  job_code: string;
  job_title: string;
  stages: FunnelStageData[];
}

export interface CandidateListCardData {
  type: "candidate_list";
  job_code: string;
  job_title: string;
  candidates: CandidateItemData[];
}

export interface ConfirmCardData {
  type: "confirm";
  action: string;
  params: Record<string, unknown>;
}

// ── 联合类型 ─────────────────────────────────────────────

export type ChatCard =
  | EvaluationSummaryCardData
  | JobListCardData
  | JobDetailCardData
  | FunnelCardData
  | CandidateListCardData
  | ConfirmCardData;

// ── 消息 & 进度 ─────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  cards?: ChatCard[];
  progress?: ProgressInfo;
  timestamp: number;
}

export interface ProgressInfo {
  status: string;
  evaluated_count?: number;
  total_count?: number;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/features/chat/types/chat.ts
git commit -m "feat: expand ChatCard type union with 5 new card types"
```

---

### Task 2: Implement JobListCard Component

**Files:**
- Create: `frontend/src/features/chat/components/JobListCard.tsx`
- Modify: `frontend/src/features/chat/components/AssistantMessage.tsx`

**Interfaces:**
- Consumes: `JobListCardData` from types/chat
- Produces: `<JobListCard card={JobListCardData} />` component

- [ ] **Step 1: Create JobListCard component**

Create `frontend/src/features/chat/components/JobListCard.tsx`:

```tsx
import { Briefcase } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { JobListCardData } from "@/features/chat/types/chat";

interface JobListCardProps {
  card: JobListCardData;
}

const statusLabels: Record<string, { label: string; className: string }> = {
  active: { label: "活跃", className: "bg-green-100 text-green-700" },
  closed: { label: "已关闭", className: "bg-gray-100 text-gray-600" },
  draft: { label: "草稿", className: "bg-yellow-100 text-yellow-700" },
};

export function JobListCard({ card }: JobListCardProps) {
  return (
    <Card className="mt-2">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-3">
          <Briefcase className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">岗位列表</span>
          <span className="text-xs text-muted-foreground">({card.jobs.length})</span>
        </div>
        <div className="space-y-2">
          {card.jobs.map((job) => {
            const statusInfo = statusLabels[job.status] || { label: job.status, className: "bg-gray-100 text-gray-600" };
            return (
              <div
                key={job.job_code}
                className="flex items-center justify-between py-1.5 px-2 rounded-md hover:bg-muted/50 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-muted-foreground">{job.job_code}</span>
                  <span>{job.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">{job.head_count}人</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${statusInfo.className}`}>
                    {statusInfo.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/features/chat/components/JobListCard.tsx
git commit -m "feat: add JobListCard component for chat card rendering"
```

---

### Task 3: Implement JobDetailCard Component

**Files:**
- Create: `frontend/src/features/chat/components/JobDetailCard.tsx`

**Interfaces:**
- Consumes: `JobDetailCardData` from types/chat
- Produces: `<JobDetailCard card={JobDetailCardData} />` component

- [ ] **Step 1: Create JobDetailCard component**

Create `frontend/src/features/chat/components/JobDetailCard.tsx`:

```tsx
import { useState } from "react";
import { ChevronDown, ChevronRight, FileText, MapPin, DollarSign, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { JobDetailCardData } from "@/features/chat/types/chat";

interface JobDetailCardProps {
  card: JobDetailCardData;
}

function CollapsibleSection({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t first:border-t-0">
      <button
        className="flex items-center gap-1.5 w-full py-2 text-sm font-medium text-left hover:text-primary"
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {title}
      </button>
      {open && <div className="pb-2 pl-5 text-sm text-muted-foreground whitespace-pre-wrap">{children}</div>}
    </div>
  );
}

const workTypeLabels: Record<string, string> = {
  remote: "远程",
  onsite: "坐班",
  hybrid: "混合",
};

export function JobDetailCard({ card }: JobDetailCardProps) {
  const { job } = card;

  return (
    <Card className="mt-2">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">{job.title}</span>
          <span className="font-mono text-xs text-muted-foreground">{job.job_code}</span>
        </div>

        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground mb-3">
          {job.location && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {job.location}
            </span>
          )}
          {job.salary_min != null && job.salary_max != null && (
            <span className="flex items-center gap-1">
              <DollarSign className="h-3 w-3" />
              {job.salary_min / 1000}k-{job.salary_max / 1000}k
            </span>
          )}
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            编制 {job.head_count} / 进面 {job.interview_quota}
          </span>
          <span>{workTypeLabels[job.work_type] || job.work_type}</span>
        </div>

        <CollapsibleSection title="岗位职责" defaultOpen>
          {job.description}
        </CollapsibleSection>

        <CollapsibleSection title="任职要求" defaultOpen>
          {job.requirements}
        </CollapsibleSection>

        <CollapsibleSection title="技能要求">
          <div className="flex flex-wrap gap-1.5">
            {job.skills_required.map((skill) => (
              <span key={skill} className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs">
                {skill}
              </span>
            ))}
          </div>
        </CollapsibleSection>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/features/chat/components/JobDetailCard.tsx
git commit -m "feat: add JobDetailCard component with collapsible sections"
```

---

### Task 4: Implement FunnelCard Component

**Files:**
- Create: `frontend/src/features/chat/components/FunnelCard.tsx`

**Interfaces:**
- Consumes: `FunnelCardData` from types/chat
- Produces: `<FunnelCard card={FunnelCardData} />` component

- [ ] **Step 1: Create FunnelCard component**

Create `frontend/src/features/chat/components/FunnelCard.tsx`:

```tsx
import { BarChart3 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { FunnelCardData } from "@/features/chat/types/chat";

interface FunnelCardProps {
  card: FunnelCardData;
}

const stageColors: Record<string, string> = {
  "待审核": "bg-blue-500",
  "面试中": "bg-green-500",
  "已拒绝": "bg-red-400",
};

const stageTextColors: Record<string, string> = {
  "待审核": "text-blue-700",
  "面试中": "text-green-700",
  "已拒绝": "text-red-600",
};

export function FunnelCard({ card }: FunnelCardProps) {
  return (
    <Card className="mt-2">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">
            {card.job_title} ({card.job_code})
          </span>
        </div>

        <div className="space-y-2.5">
          {card.stages.map((stage) => {
            const barColor = stageColors[stage.status] || "bg-gray-400";
            const textColor = stageTextColors[stage.status] || "text-gray-700";
            return (
              <div key={stage.status}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className={`font-medium ${textColor}`}>{stage.status}</span>
                  <span className="text-muted-foreground">
                    {stage.count} 人 ({stage.percentage}%)
                  </span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${barColor} transition-all`}
                    style={{ width: `${Math.max(stage.percentage, 2)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/features/chat/components/FunnelCard.tsx
git commit -m "feat: add FunnelCard component with progress bars"
```

---

### Task 5: Implement CandidateListCard Component

**Files:**
- Create: `frontend/src/features/chat/components/CandidateListCard.tsx`

**Interfaces:**
- Consumes: `CandidateListCardData` from types/chat
- Produces: `<CandidateListCard card={CandidateListCardData} />` component

- [ ] **Step 1: Create CandidateListCard component**

Create `frontend/src/features/chat/components/CandidateListCard.tsx`:

```tsx
import { Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { CandidateListCardData } from "@/features/chat/types/chat";

interface CandidateListCardProps {
  card: CandidateListCardData;
}

const decisionLabels: Record<string, { label: string; className: string }> = {
  recommend: { label: "推荐", className: "text-green-600" },
  reject: { label: "不推荐", className: "text-red-500" },
};

const statusLabels: Record<string, { label: string; className: string }> = {
  pending: { label: "待审核", className: "bg-yellow-100 text-yellow-700" },
  interview: { label: "面试中", className: "bg-green-100 text-green-700" },
  rejected: { label: "已拒绝", className: "bg-red-100 text-red-600" },
};

export function CandidateListCard({ card }: CandidateListCardProps) {
  return (
    <Card className="mt-2">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-3">
          <Users className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">
            {card.job_title} ({card.job_code})
          </span>
          <span className="text-xs text-muted-foreground">({card.candidates.length} 人)</span>
        </div>

        <div className="space-y-1.5">
          {card.candidates.map((candidate, i) => {
            const decisionInfo = decisionLabels[candidate.ai_decision || ""] || { label: "未评估", className: "text-gray-500" };
            const statusInfo = statusLabels[candidate.status] || { label: candidate.status, className: "bg-gray-100 text-gray-600" };
            return (
              <div
                key={i}
                className="flex items-center justify-between py-1.5 px-2 rounded-md hover:bg-muted/50 text-sm"
              >
                <span className="font-medium">{candidate.name}</span>
                <div className="flex items-center gap-2">
                  {candidate.ai_score != null && (
                    <span className="text-xs font-mono text-muted-foreground">{candidate.ai_score}分</span>
                  )}
                  <span className={`text-xs ${decisionInfo.className}`}>
                    {decisionInfo.label}
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${statusInfo.className}`}>
                    {statusInfo.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/features/chat/components/CandidateListCard.tsx
git commit -m "feat: add CandidateListCard component with decision and status badges"
```

---

### Task 6: Implement ConfirmCard Component

**Files:**
- Create: `frontend/src/features/chat/components/ConfirmCard.tsx`

**Interfaces:**
- Consumes: `ConfirmCardData` from types/chat; `sendMessage` from `useChat` hook (via props)
- Produces: `<ConfirmCard card={ConfirmCardData} onConfirm={() => void} onCancel={() => void} />` component

- [ ] **Step 1: Create ConfirmCard component**

Create `frontend/src/features/chat/components/ConfirmCard.tsx`:

```tsx
import { AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { ConfirmCardData } from "@/features/chat/types/chat";

interface ConfirmCardProps {
  card: ConfirmCardData;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmCard({ card, onConfirm, onCancel }: ConfirmCardProps) {
  return (
    <Card className="mt-2 border-yellow-200 bg-yellow-50/50">
      <CardContent className="p-3">
        <div className="flex items-start gap-2 mb-3">
          <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 shrink-0" />
          <span className="text-sm">{card.action}</span>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="outline" size="sm" onClick={onCancel}>
            取消
          </Button>
          <Button variant="default" size="sm" onClick={onConfirm}>
            确认
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/features/chat/components/ConfirmCard.tsx
git commit -m "feat: add ConfirmCard component with confirm/cancel buttons"
```

---

### Task 7: Update AssistantMessage for Card Routing

**Files:**
- Modify: `frontend/src/features/chat/components/AssistantMessage.tsx`

**Interfaces:**
- Consumes: All 6 card components; `ChatCard` union type; `sendMessage` from useChat (passed as prop)
- Produces: Updated `<AssistantMessage>` that renders all card types based on `card.type` discriminant

- [ ] **Step 1: Update AssistantMessage component**

Replace `frontend/src/features/chat/components/AssistantMessage.tsx`:

```tsx
import type { ChatCard, ConfirmCardData } from "@/features/chat/types/chat";
import { EvaluationCard } from "./EvaluationCard";
import { JobListCard } from "./JobListCard";
import { JobDetailCard } from "./JobDetailCard";
import { FunnelCard } from "./FunnelCard";
import { CandidateListCard } from "./CandidateListCard";
import { ConfirmCard } from "./ConfirmCard";
import { ProgressMessage } from "./ProgressMessage";

interface AssistantMessageProps {
  message: ChatMessage;
  onSendMessage?: (text: string) => void;
}

function renderCard(card: ChatCard, onSendMessage?: (text: string) => void) {
  switch (card.type) {
    case "evaluation_summary":
      return <EvaluationCard key={card.type} card={card} />;
    case "job_list":
      return <JobListCard key={card.type} card={card} />;
    case "job_detail":
      return <JobDetailCard key={card.type} card={card} />;
    case "funnel":
      return <FunnelCard key={card.type} card={card} />;
    case "candidate_list":
      return <CandidateListCard key={card.type} card={card} />;
    case "confirm":
      return (
        <ConfirmCard
          key={card.type}
          card={card as ConfirmCardData}
          onConfirm={() => onSendMessage?.("确认")}
          onCancel={() => onSendMessage?.("取消")}
        />
      );
  }
}

export function AssistantMessage({ message, onSendMessage }: AssistantMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] bg-muted rounded-2xl rounded-bl-sm px-3.5 py-2.5">
        {message.progress ? (
          <ProgressMessage progress={message.progress} />
        ) : (
          <>
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {message.content}
            </p>
            {message.cards?.map((card, i) => (
              <div key={i}>{renderCard(card, onSendMessage)}</div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/features/chat/components/AssistantMessage.tsx
git commit -m "feat: update AssistantMessage with card type routing for all 6 card types"
```

---

### Task 8: Wire sendMessage to ChatMessages

**Files:**
- Modify: `frontend/src/features/chat/components/ChatMessages.tsx` (or the parent component that renders AssistantMessage)
- Modify: `frontend/src/features/chat/components/ChatWindow.tsx` (if needed)

**Interfaces:**
- Consumes: `sendMessage` from `useChat` hook
- Produces: `onSendMessage` prop passed down to `AssistantMessage` → `ConfirmCard`

- [ ] **Step 1: Find the parent component that renders AssistantMessage**

Run: `grep -r "AssistantMessage" frontend/src/`
Expected: Find the component that maps over messages and renders `<AssistantMessage>`

- [ ] **Step 2: Pass sendMessage as onSendMessage prop**

In the component that renders `<AssistantMessage>`, pass the `sendMessage` function:

```tsx
<AssistantMessage message={msg} onSendMessage={sendMessage} />
```

This will typically be in `ChatMessages.tsx` or `ChatWindow.tsx`. The exact file depends on the current structure — find it and add the prop passthrough.

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 4: Verify the app starts**

Run: `cd frontend && npm run dev`
Expected: App starts without errors

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/features/chat/components/
git commit -m "feat: wire sendMessage prop to ConfirmCard for button-triggered confirm/cancel"
```

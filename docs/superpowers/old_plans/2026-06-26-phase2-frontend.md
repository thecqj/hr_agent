# Phase 2 Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the floating chat window (Copilot style), evaluation result page, and frontend type/API extensions for Phase 2.

**Architecture:** ChatBubble floats in RecruiterLayout (bottom-right), expands to ChatWindow with message list, input, and SSE event rendering. EvaluationResultPage at `/dashboard/evaluation/:taskId` shows per-candidate AI scores and decisions with confirm button. All new code organized under `src/features/chat/`.

**Tech Stack:** React 19 + TypeScript, TanStack Query, shadcn/ui, Zustand (auth only), EventSource API for SSE

**Depends on:** Plans 1 & 2 (backend must provide `/api/chat/send` and `/api/agent/task/:taskId` endpoints).

## Global Constraints

- TypeScript strict mode, no `any` types in production code
- Follow existing project patterns: feature-based folders, TanStack Query hooks, Zustand for auth only
- All components use shadcn/ui primitives where possible
- CSS via Tailwind utility classes (follow existing patterns)
- Frontend working directory: `/Users/bytedance/my_code/hr_agent/.claude/worktrees/phase2-impl/frontend`
- Frontend runs at port 3001, proxies `/api` → `:8000`

---

### Task 1: Extend Types + Add Agent API Functions

**Files:**
- Modify: `frontend/src/features/applications/types/application.ts`
- Modify: `frontend/src/features/applications/api/applications.ts`
- Modify: `frontend/src/shared/constants/queryKeys.ts`

**Interfaces:**
- Consumes: Existing `Applicant` type, `apiClient` from `shared/api/client`
- Produces: Extended `Applicant` with `ai_*` fields, `DimensionScore` type, `EvaluationDetail` type, `getEvaluationTask()`, `confirmEvaluation()`, `evaluation` query keys

- [ ] **Step 1: Extend application types**

Add the following types to `frontend/src/features/applications/types/application.ts`:

After the existing `Certificate` interface, add:

```ts
export interface DimensionScore {
  name: string;
  score: number;
  weight: number;
  reason: string;
}

export interface EvaluationDetail {
  application_id: string;
  applicant_name: string;
  ai_score: number;
  ai_evaluation: DimensionScore[];
  ai_decision: "recommend" | "reject" | "neutral";
  ai_decision_reason: string;
}
```

Extend the existing `Applicant` interface to add AI fields:

```ts
export interface Applicant {
  id: string;
  applicant_name: string;
  resume_text: string;
  cover_letter?: string;
  structured_resume?: StructuredResume;
  status: ApplicationStatus;
  // AI evaluation fields (Phase 2)
  ai_score?: number;
  ai_evaluation?: DimensionScore[];
  ai_decision?: string;
  ai_decision_reason?: string;
  ai_evaluated_at?: string;
}
```

- [ ] **Step 2: Add agent API functions**

Add to `frontend/src/features/applications/api/applications.ts`:

```ts
// ── Agent / Evaluation API ─────────────────────────────────

export interface TaskStatusResponse {
  task_id: string;
  job_id: string;
  status: "pending" | "running" | "completed" | "confirmed" | "failed";
  total_count: number;
  evaluated_count: number;
  result_summary?: {
    recommend_count: number;
    reject_count: number;
    cutoff_score: number;
    total_evaluated: number;
    borderline_adjustments: number;
  };
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ConfirmDecision {
  application_id: string;
  final_decision: "interview" | "reject";
  override_reason?: string;
}

export interface ConfirmResponse {
  updated_count: number;
  message: string;
}

export async function getEvaluationTask(taskId: string): Promise<TaskStatusResponse> {
  const res = await apiClient.get<TaskStatusResponse>(`/agent/task/${taskId}`);
  return res.data;
}

export async function confirmEvaluation(
  taskId: string,
  decisions: ConfirmDecision[] = [],
): Promise<ConfirmResponse> {
  const res = await apiClient.post<ConfirmResponse>(`/agent/confirm/${taskId}`, {
    decisions,
  });
  return res.data;
}
```

- [ ] **Step 3: Add evaluation query keys**

Add to `frontend/src/shared/constants/queryKeys.ts`:

```ts
export const queryKeys = {
  jobs: {
    all: ["jobs"] as const,
    list: (params?: object) => ["jobs", "list", params ?? {}] as const,
    detail: (id: string) => ["jobs", "detail", id] as const,
    recruiterList: (recruiterId?: string) => ["jobs", "recruiter", recruiterId ?? ""] as const,
  },
  applications: {
    mine: (params?: object) => ["applications", "mine", params ?? {}] as const,
    byJob: (jobId: string) => ["applications", "job", jobId] as const,
  },
  evaluation: {
    task: (taskId: string) => ["evaluation", "task", taskId] as const,
  },
} as const;
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/applications/types/application.ts frontend/src/features/applications/api/applications.ts frontend/src/shared/constants/queryKeys.ts
git commit -m "feat: extend Applicant type with AI fields, add agent API functions"
```

---

### Task 2: Add Evaluation Query Hooks

**Files:**
- Modify: `frontend/src/features/applications/hooks/useApplications.ts`

**Interfaces:**
- Consumes: `getEvaluationTask`, `confirmEvaluation` from applications API, `queryKeys.evaluation`
- Produces: `useEvaluationTaskQuery()`, `useConfirmEvaluationMutation()`

- [ ] **Step 1: Add evaluation hooks**

Add to `frontend/src/features/applications/hooks/useApplications.ts`:

```ts
import {
  getEvaluationTask,
  confirmEvaluation,
} from "@/features/applications/api/applications";
import type { ConfirmDecision } from "@/features/applications/api/applications";

// ... existing hooks ...

export function useEvaluationTaskQuery(taskId?: string) {
  return useQuery({
    queryKey: taskId ? queryKeys.evaluation.task(taskId) : ["evaluation", "task", "missing"],
    queryFn: () => getEvaluationTask(taskId!),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Auto-poll while running, stop when done
      if (status === "pending" || status === "running") return 2000;
      return false;
    },
  });
}

export function useConfirmEvaluationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ taskId, decisions }: { taskId: string; decisions: ConfirmDecision[] }) =>
      confirmEvaluation(taskId, decisions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluation"] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/applications/hooks/useApplications.ts
git commit -m "feat: add evaluation task query and confirm mutation hooks"
```

---

### Task 3: Create Chat Types + API + useChat Hook

**Files:**
- Create: `frontend/src/features/chat/types/chat.ts`
- Create: `frontend/src/features/chat/api/chat.ts`
- Create: `frontend/src/features/chat/hooks/useChat.ts`

**Interfaces:**
- Consumes: `useAuthStore` for token, EventSource API for SSE
- Produces: Chat types, `sendChatMessage()`, `useChat()` hook with messages/isProcessing/sendMessage/disconnect

- [ ] **Step 1: Create chat types**

Create `frontend/src/features/chat/types/chat.ts`:

```ts
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  cards?: ChatCard[];
  progress?: ProgressInfo;
  timestamp: number;
}

export interface ChatCard {
  type: "evaluation_summary";
  task_id: string;
  job_title: string;
  total_count: number;
  recommended_count: number;
  rejected_count: number;
  result_page_url: string;
}

export interface ProgressInfo {
  status: string;
  evaluated_count?: number;
  total_count?: number;
}
```

- [ ] **Step 2: Create chat API**

Create `frontend/src/features/chat/api/chat.ts`:

```ts
import { useAuthStore } from "@/features/auth/store/authStore";

const API_BASE = "/api";

/**
 * Send a chat message and return an EventSource for SSE streaming.
 * Uses native fetch + ReadableStream for POST-based SSE
 * (EventSource API only supports GET).
 */
export function sendChatMessage(
  message: string,
  onEvent: (eventType: string, data: Record<string, unknown>) => void,
  onError: (error: Error) => void,
  onDone: () => void,
): AbortController {
  const controller = new AbortController();
  const token = useAuthStore.getState().token;

  fetch(`${API_BASE}/chat/send`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify({ message }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(new Error(`HTTP ${response.status}`));
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError(new Error("No response body"));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr) as Record<string, unknown>;
              if (currentEvent === "done") {
                onDone();
              } else {
                onEvent(currentEvent, data);
              }
            } catch {
              // Skip malformed JSON
            }
            currentEvent = "";
          }
        }
      }

      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err);
      }
    });

  return controller;
}
```

- [ ] **Step 3: Create useChat hook**

Create `frontend/src/features/chat/hooks/useChat.ts`:

```ts
import { useState, useRef, useCallback } from "react";

import type { ChatMessage, ChatCard, ProgressInfo } from "@/features/chat/types/chat";
import { sendChatMessage } from "@/features/chat/api/chat";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback((text: string) => {
    if (isProcessing) return;

    // Add user message
    const userMsg: ChatMessage = {
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);

    // Track the current assistant message being built
    let assistantContent = "";
    let assistantCards: ChatCard[] | undefined;
    let assistantProgress: ProgressInfo | undefined;

    const controller = sendChatMessage(
      text,
      (eventType, data) => {
        switch (eventType) {
          case "thinking":
            assistantContent = (data.status as string) || "思考中...";
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  progress: { status: assistantContent },
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: assistantContent,
                  progress: { status: assistantContent },
                  timestamp: Date.now(),
                });
              }
              return updated;
            });
            break;

          case "intent":
            assistantContent = "正在处理您的请求...";
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  progress: { status: assistantContent },
                };
              }
              return updated;
            });
            break;

          case "progress":
            assistantProgress = {
              status: (data.status as string) || "处理中...",
              evaluated_count: data.evaluated_count as number | undefined,
              total_count: data.total_count as number | undefined,
            };
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantProgress.status,
                  progress: assistantProgress,
                };
              }
              return updated;
            });
            break;

          case "result":
            assistantContent = (data.reply_message as string) || "";
            assistantCards = data.cards as ChatCard[] | undefined;
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  cards: assistantCards,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              }
              return updated;
            });
            break;

          case "error":
            assistantContent = `❌ ${(data.message as string) || "发生错误"}`;
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              }
              return updated;
            });
            break;
        }
      },
      (error) => {
        const errorMsg: ChatMessage = {
          role: "assistant",
          content: `❌ 连接中断：${error.message}`,
          timestamp: Date.now(),
        };
        setMessages((prev) => {
          // Remove any in-progress assistant message
          const filtered = prev.filter(
            (m) => !(m.role === "assistant" && m.progress)
          );
          return [...filtered, errorMsg];
        });
        setIsProcessing(false);
      },
      () => {
        setIsProcessing(false);
        abortControllerRef.current = null;
      },
    );

    abortControllerRef.current = controller;
  }, [isProcessing]);

  const disconnect = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsProcessing(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isProcessing,
    sendMessage,
    disconnect,
    clearMessages,
  };
}
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/chat/types/chat.ts frontend/src/features/chat/api/chat.ts frontend/src/features/chat/hooks/useChat.ts
git commit -m "feat: add Chat types, SSE API client, and useChat hook"
```

---

### Task 4: Create Chat UI Components

**Files:**
- Create: `frontend/src/features/chat/components/ChatBubble.tsx`
- Create: `frontend/src/features/chat/components/ChatWindow.tsx`
- Create: `frontend/src/features/chat/components/ChatMessages.tsx`
- Create: `frontend/src/features/chat/components/ChatInput.tsx`
- Create: `frontend/src/features/chat/components/AssistantMessage.tsx`
- Create: `frontend/src/features/chat/components/ProgressMessage.tsx`
- Create: `frontend/src/features/chat/components/EvaluationCard.tsx`

**Interfaces:**
- Consumes: `useChat()` hook, `ChatMessage`/`ChatCard`/`ProgressInfo` types, shadcn/ui components, `useNavigate` from react-router
- Produces: `ChatBubble` component (mount in RecruiterLayout)

- [ ] **Step 1: Create EvaluationCard component**

Create `frontend/src/features/chat/components/EvaluationCard.tsx`:

```tsx
import { useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { ChatCard } from "@/features/chat/types/chat";

interface EvaluationCardProps {
  card: ChatCard;
}

export function EvaluationCard({ card }: EvaluationCardProps) {
  const navigate = useNavigate();

  return (
    <Card
      className="mt-2 cursor-pointer hover:bg-muted/50 transition-colors"
      onClick={() => navigate(card.result_page_url)}
    >
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">{card.job_title}</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
          <div>
            总计 <span className="font-medium text-foreground">{card.total_count}</span>
          </div>
          <div>
            推荐 <span className="font-medium text-green-600">{card.recommended_count}</span>
          </div>
          <div>
            淘汰 <span className="font-medium text-red-500">{card.rejected_count}</span>
          </div>
        </div>
        <p className="text-xs text-primary mt-2">点击查看详情 →</p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Create ProgressMessage component**

Create `frontend/src/features/chat/components/ProgressMessage.tsx`:

```tsx
import { Loader2 } from "lucide-react";

import type { ProgressInfo } from "@/features/chat/types/chat";

interface ProgressMessageProps {
  progress: ProgressInfo;
}

export function ProgressMessage({ progress }: ProgressMessageProps) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      <span>{progress.status}</span>
      {progress.evaluated_count != null && progress.total_count != null && (
        <span className="text-xs">
          ({progress.evaluated_count}/{progress.total_count})
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create AssistantMessage component**

Create `frontend/src/features/chat/components/AssistantMessage.tsx`:

```tsx
import type { ChatMessage } from "@/features/chat/types/chat";
import { EvaluationCard } from "./EvaluationCard";
import { ProgressMessage } from "./ProgressMessage";

interface AssistantMessageProps {
  message: ChatMessage;
}

export function AssistantMessage({ message }: AssistantMessageProps) {
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
              <EvaluationCard key={i} card={card} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create ChatMessages component**

Create `frontend/src/features/chat/components/ChatMessages.tsx`:

```tsx
import { useEffect, useRef } from "react";

import type { ChatMessage } from "@/features/chat/types/chat";
import { AssistantMessage } from "./AssistantMessage";

interface ChatMessagesProps {
  messages: ChatMessage[];
}

export function ChatMessages({ messages }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {messages.length === 0 && (
        <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
          输入指令开始，例如「帮我筛选前端开发岗位的简历」
        </div>
      )}
      {messages.map((msg, i) =>
        msg.role === "user" ? (
          <div key={i} className="flex justify-end">
            <div className="max-w-[85%] bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-3.5 py-2.5">
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ) : (
          <AssistantMessage key={i} message={msg} />
        )
      )}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 5: Create ChatInput component**

Create `frontend/src/features/chat/components/ChatInput.tsx`:

```tsx
import { useState, type KeyboardEvent } from "react";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t p-3">
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入指令，如「帮我筛选前端岗位简历」"
          disabled={disabled}
          className="text-sm"
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={disabled || !input.trim()}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create ChatWindow component**

Create `frontend/src/features/chat/components/ChatWindow.tsx`:

```tsx
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useChat } from "@/features/chat/hooks/useChat";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";

interface ChatWindowProps {
  onClose: () => void;
}

export function ChatWindow({ onClose }: ChatWindowProps) {
  const { messages, isProcessing, sendMessage } = useChat();

  return (
    <div className="absolute bottom-16 right-0 w-[380px] h-[520px] bg-card border rounded-xl shadow-xl flex flex-col overflow-hidden z-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-primary/5">
        <h3 className="font-semibold text-sm">HR 智能助手</h3>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <ChatMessages messages={messages} />

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isProcessing} />
    </div>
  );
}
```

- [ ] **Step 7: Create ChatBubble entry component**

Create `frontend/src/features/chat/components/ChatBubble.tsx`:

```tsx
import { useState } from "react";
import { MessageCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ChatWindow } from "./ChatWindow";

export function ChatBubble() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-40">
      {isOpen && <ChatWindow onClose={() => setIsOpen(false)} />}
      <Button
        size="icon"
        className="h-12 w-12 rounded-full shadow-lg"
        onClick={() => setIsOpen(!isOpen)}
      >
        <MessageCircle className="h-6 w-6" />
      </Button>
    </div>
  );
}
```

- [ ] **Step 8: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors

- [ ] **Step 9: Commit**

```bash
git add frontend/src/features/chat/components/
git commit -m "feat: add Chat UI components

- ChatBubble: floating entry point
- ChatWindow: main window with header/messages/input
- ChatMessages: scrollable message list
- ChatInput: text input with send button
- AssistantMessage: assistant bubble with cards
- ProgressMessage: loading indicator
- EvaluationCard: clickable evaluation summary card"
```

---

### Task 5: Create EvaluationResultPage

**Files:**
- Create: `frontend/src/pages/EvaluationResultPage.tsx`

**Interfaces:**
- Consumes: `useEvaluationTaskQuery`, `useConfirmEvaluationMutation`, `useParams` from react-router, shadcn/ui Table/Badge/Button, `DimensionScore` type
- Produces: `EvaluationResultPage` component

- [ ] **Step 1: Create EvaluationResultPage**

Create `frontend/src/pages/EvaluationResultPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Loader2,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  useEvaluationTaskQuery,
  useConfirmEvaluationMutation,
} from "@/features/applications/hooks/useApplications";
import { useJobDetailQuery } from "@/features/jobs/hooks/useJobs";
import { getApiErrorMessage } from "@/shared/api/error";
import ErrorState from "@/shared/ui/feedback/ErrorState";
import { useBreadcrumb } from "@/shared/ui/layout/breadcrumb-context";
import type { ConfirmDecision } from "@/features/applications/api/applications";

interface DecisionOverride {
  applicationId: string;
  decision: "interview" | "reject" | "ai";
  reason: string;
}

export default function EvaluationResultPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { setItems: setBreadcrumbItems } = useBreadcrumb();
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [overrides, setOverrides] = useState<Map<string, DecisionOverride>>(new Map());

  const { data: task, isLoading, isError, refetch } = useEvaluationTaskQuery(taskId);
  const { data: job } = useJobDetailQuery(task?.job_id);
  const confirmMutation = useConfirmEvaluationMutation();

  useEffect(() => {
    setBreadcrumbItems([
      { label: "首页", href: "/dashboard" },
      { label: "我的岗位", href: "/dashboard" },
      ...(job ? [{ label: job.title, href: `/dashboard/applicants/${task?.job_id}` }] : []),
      { label: "评估结果" },
    ]);
  }, [setBreadcrumbItems, job, task]);

  const toggleRow = (id: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleDecisionChange = (
    applicationId: string,
    decision: "interview" | "reject" | "ai",
  ) => {
    setOverrides((prev) => {
      const next = new Map(prev);
      if (decision === "ai") {
        next.delete(applicationId);
      } else {
        next.set(applicationId, {
          applicationId,
          decision,
          reason: next.get(applicationId)?.reason || "",
        });
      }
      return next;
    });
  };

  const handleReasonChange = (applicationId: string, reason: string) => {
    setOverrides((prev) => {
      const next = new Map(prev);
      const existing = next.get(applicationId);
      if (existing) {
        next.set(applicationId, { ...existing, reason });
      }
      return next;
    });
  };

  const handleConfirm = async () => {
    if (!taskId) return;

    const decisions: ConfirmDecision[] = [];
    for (const [_, override] of overrides) {
      decisions.push({
        application_id: override.applicationId,
        final_decision: override.decision,
        override_reason: override.reason || undefined,
      });
    }

    try {
      await confirmMutation.mutateAsync({ taskId, decisions });
      toast.success("评估结果已确认");
      if (task?.job_id) {
        navigate(`/dashboard/applicants/${task.job_id}`);
      }
    } catch (err) {
      toast.error(getApiErrorMessage(err, "确认失败"));
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError || !task) {
    return <ErrorState message="获取评估结果失败" onRetry={refetch} />;
  }

  if (task.status !== "completed") {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-muted-foreground">
          {task.status === "running"
            ? `评估进行中 (${task.evaluated_count}/${task.total_count})`
            : `任务状态：${task.status}`}
        </p>
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回
        </Button>
      </div>
    );
  }

  const summary = task.result_summary;
  const recommendCount = summary?.recommend_count ?? 0;
  const rejectCount = summary?.reject_count ?? 0;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">
            {job?.title ?? "岗位"} · 评估结果
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            任务 ID: {taskId}
          </p>
        </div>
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          返回
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">总评估数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{task.total_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">推荐进面</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">{recommendCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">建议淘汰</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-500">{rejectCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Candidate table */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead>姓名</TableHead>
              <TableHead>AI 总分</TableHead>
              <TableHead>AI 决策</TableHead>
              <TableHead>最终决策</TableHead>
              <TableHead>决策理由</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {task.result_summary?.evaluation_details?.map(
              (detail: Record<string, unknown>) => {
                const appId = String(detail.application_id);
                const isExpanded = expandedRows.has(appId);
                const override = overrides.get(appId);

                return (
                  <>
                    <TableRow key={appId}>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => toggleRow(appId)}
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronRight className="h-3.5 w-3.5" />
                          )}
                        </Button>
                      </TableCell>
                      <TableCell className="font-medium">
                        {String(detail.applicant_name ?? "—")}
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold">
                          {Number(detail.ai_score).toFixed(1)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            detail.ai_decision === "recommend"
                              ? "default"
                              : "destructive"
                          }
                        >
                          {detail.ai_decision === "recommend" ? (
                            <>
                              <CheckCircle className="h-3 w-3 mr-1" />
                              推荐
                            </>
                          ) : (
                            <>
                              <XCircle className="h-3 w-3 mr-1" />
                              淘汰
                            </>
                          )}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Select
                          value={override?.decision ?? "ai"}
                          onValueChange={(val) =>
                            handleDecisionChange(
                              appId,
                              val as "interview" | "reject" | "ai",
                            )
                          }
                        >
                          <SelectTrigger className="w-28 h-8 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="ai">保持 AI 建议</SelectItem>
                            <SelectItem value="interview">改为进面</SelectItem>
                            <SelectItem value="reject">改为淘汰</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">
                        {override ? (
                          <Textarea
                            value={override.reason}
                            onChange={(e) =>
                              handleReasonChange(appId, e.target.value)
                            }
                            placeholder="填写覆盖理由"
                            className="h-8 text-xs min-w-[160px]"
                          />
                        ) : (
                          String(detail.ai_decision_reason ?? "—")
                        )}
                      </TableCell>
                    </TableRow>
                    {isExpanded && (
                      <TableRow key={`${appId}-detail`}>
                        <TableCell colSpan={6} className="bg-muted/30 px-8 py-3">
                          <div className="space-y-2">
                            <p className="text-sm font-medium">维度评分</p>
                            {(
                              (detail.ai_evaluation as Array<Record<string, unknown>>) ?? []
                            ).map((dim, i) => (
                              <div
                                key={i}
                                className="flex items-center gap-3 text-sm"
                              >
                                <span className="w-20 text-muted-foreground">
                                  {String(dim.name)}
                                </span>
                                <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-primary rounded-full"
                                    style={{ width: `${Number(dim.score)}%` }}
                                  />
                                </div>
                                <span className="w-8 text-right font-medium">
                                  {Number(dim.score).toFixed(0)}
                                </span>
                                <span className="w-12 text-xs text-muted-foreground">
                                  权重 {Number(dim.weight).toFixed(2)}
                                </span>
                              </div>
                            ))}
                            {detail.ai_decision_reason && (
                              <p className="text-xs text-muted-foreground mt-2">
                                评估理由：{String(detail.ai_decision_reason)}
                              </p>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                );
              },
            )}
          </TableBody>
        </Table>
      </div>

      {/* Confirm button */}
      <div className="mt-6 flex justify-end">
        <Button
          size="lg"
          onClick={handleConfirm}
          disabled={confirmMutation.isPending}
        >
          {confirmMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              确认中...
            </>
          ) : (
            <>
              <CheckCircle className="h-4 w-4 mr-2" />
              确认评估结果
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
```

**Note:** This page relies on `task.result_summary.evaluation_details` containing per-candidate data. The backend's `save_draft_node` currently stores `recommend_count`, `reject_count`, etc. in `result_summary`, but doesn't include the per-candidate `evaluation_details`. We need to add this to the backend. Add a note that the backend `result_summary` must be extended to include evaluation details.

For now, the page handles the case where `evaluation_details` might not exist. The backend extension will be done as part of a small follow-up task.

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/EvaluationResultPage.tsx
git commit -m "feat: add EvaluationResultPage with candidate table and confirm

- Summary cards: total/recommended/rejected counts
- Candidate table with AI score, decision, and override dropdown
- Expandable rows showing dimension scores
- Confirm button with mutation hook"
```

---

### Task 6: Wire Up Routes + Layout + Backend result_summary Extension

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/shared/ui/layout/RecruiterLayout.tsx`
- Modify: `backend/app/services/agent/nodes.py` (extend result_summary)

**Interfaces:**
- Consumes: `EvaluationResultPage`, `ChatBubble`, existing route/layout patterns
- Produces: Working routes and ChatBubble in RecruiterLayout

- [ ] **Step 1: Add evaluation result route to App.tsx**

Modify `frontend/src/App.tsx` — add import and route:

Add import:
```tsx
import EvaluationResultPage from "@/pages/EvaluationResultPage";
```

Add route inside the RecruiterLayout routes, after the `/dashboard/applicants/:jobId` route:

```tsx
<Route
  path="/dashboard/evaluation/:taskId"
  element={
    <ProtectedRoute role="recruiter">
      <EvaluationResultPage />
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 2: Add ChatBubble to RecruiterLayout**

Modify `frontend/src/shared/ui/layout/RecruiterLayout.tsx` — add import and component:

Add import:
```tsx
import { ChatBubble } from "@/features/chat/components/ChatBubble";
```

Add `<ChatBubble />` just before the closing `</div>` of the root element:

```tsx
    </div>
    <ChatBubble />
  </div>
```

Specifically, after the `</aside>` and main content area, inside the root `div`:

Find the closing `</div>` that matches the root `<div className="min-h-screen bg-background flex">` and add `<ChatBubble />` before it.

- [ ] **Step 3: Extend backend result_summary with evaluation_details**

Modify `backend/app/services/agent/nodes.py` — in the `save_draft_node` function, extend the `result_summary` dict to include per-candidate evaluation details.

In `save_draft_node`, after building the `result_summary` dict, add the evaluation details:

Find the `task.result_summary = {` block and extend it:

```python
    # Build evaluation details for the result summary
    evaluation_details: list[dict[str, Any]] = []
    for app_id, decision in decision_map.items():
        eval_result = eval_map.get(app_id, {})
        evaluation_data = eval_result.get("evaluation", {})
        evaluation_details.append({
            "application_id": app_id,
            "applicant_name": eval_result.get("applicant_name"),
            "ai_score": eval_result.get("weighted_total"),
            "ai_evaluation": evaluation_data.get("dimensions", []),
            "ai_decision": decision,
            "ai_decision_reason": (
                f"边界复评调整: {adjustment_reasons[app_id]}"
                if app_id in adjustment_reasons
                else evaluation_data.get("summary", "") or
                    ("AI 建议进入面试" if decision == "recommend" else "AI 建议淘汰")
            ),
        })

    # Update evaluation_task status
    task = await db.get(EvaluationTask, task_id)
    if task:
        task.status = EvalTaskStatus.COMPLETED
        task.result_summary = {
            "recommend_count": recommend_count,
            "reject_count": reject_count,
            "cutoff_score": screening_result.get("cutoff_score", 0),
            "total_evaluated": len(evaluation_results),
            "borderline_adjustments": len(
                [a for a in review_adjustments if a.get("action") == "adjust"]
            ),
            "evaluation_details": evaluation_details,
        }
        if errors:
            task.error_message = "; ".join(errors)
```

This replaces the existing `task.result_summary = {...}` block in `save_draft_node`. The new block includes `evaluation_details`.

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors

- [ ] **Step 5: Run backend tests**

Run: `cd backend && uv run pytest tests/ -v`

Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx frontend/src/shared/ui/layout/RecruiterLayout.tsx backend/app/services/agent/nodes.py
git commit -m "feat: wire up evaluation route, ChatBubble in layout, extend result_summary

- Add /dashboard/evaluation/:taskId route
- Mount ChatBubble in RecruiterLayout
- Add evaluation_details to result_summary in save_draft_node"
```

---

### Task 7: Manual Verification

- [ ] **Step 1: Start the backend**

Run: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`

- [ ] **Step 2: Start the frontend**

Run: `cd frontend && npm run dev`

- [ ] **Step 3: Verify ChatBubble appears**

1. Login as recruiter
2. Navigate to dashboard
3. Confirm floating chat bubble appears in bottom-right
4. Click to expand — chat window should appear

- [ ] **Step 4: Verify chat interaction**

1. Type "帮助" in chat input
2. Verify response appears with help text
3. Type "帮我筛选前端开发岗位的简历"
4. Verify SSE events stream (thinking → progress → result)

- [ ] **Step 5: Verify evaluation result page**

1. After evaluation completes, click the evaluation card in chat
2. Verify result page shows candidate table with scores
3. Override a decision and confirm
4. Verify status updates

---

## Self-Review

**1. Spec coverage check:**
- ✅ Floating chat window (Copilot style) — Task 4
- ✅ ChatBubble in RecruiterLayout — Task 6
- ✅ Evaluation result page — Task 5
- ✅ Chat types + API + hook — Task 3
- ✅ Extended Applicant type with ai_* fields — Task 1
- ✅ Agent API functions — Task 1
- ✅ Evaluation query hooks — Task 2
- ✅ Route setup — Task 6
- ✅ SSE streaming consumption — Task 3 (chat API)
- ✅ result_summary extension with evaluation_details — Task 6

**2. Placeholder scan:** No TBD/TODO found. All steps have complete code.

**3. Type consistency:**
- `ChatMessage` / `ChatCard` / `ProgressInfo` types match between types, API, hook, and components
- `Applicant` extension fields match backend `Application` model field names
- `ConfirmDecision` type matches between frontend API and backend schema
- `TaskStatusResponse` type matches backend `TaskStatusResponse` schema
- `EvaluationResultPage` uses correct route param `taskId`

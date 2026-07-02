# Phase 3: Frontend Adaptation + Test Suite Finalization

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt the frontend to handle the new SSE event types (tool_start, tool_end, text_delta), render Markdown replies, and remove the Card-based rendering system. Finalize the backend test suite.

**Architecture:** The frontend `useChat` hook is updated to handle new SSE events and stream text deltas. The `AssistantMessage` component is simplified to render Markdown text instead of Card components. The `ConfirmCard` mechanism is removed — confirmations now flow through natural chat messages (user says "确认" → LLM calls write tool). Backend test suite gets final cleanup and the old `nodes.py` is deleted.

**Tech Stack:** React 19, TypeScript, Vite, ReactMarkdown (new dependency)

## Global Constraints

- Frontend: React 19 + TypeScript, no `any` types
- New SSE events: `tool_start`, `tool_end`, `text_delta` replace `thinking`, `intent`
- `result` event no longer carries `cards` — only `reply_message` (Markdown)
- Card components (`EvaluationCard`, `JobListCard`, etc.) are preserved in codebase but no longer rendered in the chat flow
- ConfirmCard removed — confirmation now via natural language ("确认"/"取消")
- Markdown rendering with `react-markdown` for rich formatting (tables, lists, bold)
- Backend: mypy --strict, all tests pass

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `frontend/src/features/chat/hooks/useChat.ts` | SSE event handling for tool_start/tool_end/text_delta |
| Modify | `frontend/src/features/chat/types/chat.ts` | Remove Card types from ChatMessage, add tool status |
| Modify | `frontend/src/features/chat/components/AssistantMessage.tsx` | Markdown rendering, remove Card rendering |
| Modify | `frontend/src/features/chat/components/ChatMessages.tsx` | Simplify message rendering |
| Modify | `frontend/src/features/chat/api/chat.ts` | No changes needed (SSE parsing is event-type agnostic) |
| Modify | `frontend/package.json` | Add `react-markdown` dependency |
| Delete | `backend/app/services/conversation/nodes.py` | Final removal of deprecated file |

---

### Task 1: Add `react-markdown` dependency

**Files:**
- Modify: `frontend/package.json`

**Interfaces:**
- Consumes: None
- Produces: `react-markdown` available for import

- [ ] **Step 1: Install react-markdown**

Run: `cd frontend && npm install react-markdown`

This adds `react-markdown` to `package.json` and `node_modules`.

- [ ] **Step 2: Verify install**

Run: `cd frontend && npm ls react-markdown`

Expected: `react-markdown@x.x.x` listed without errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat: add react-markdown dependency for Markdown chat rendering"
```

---

### Task 2: Update chat types

**Files:**
- Modify: `frontend/src/features/chat/types/chat.ts`

**Interfaces:**
- Consumes: None
- Produces: Updated `ChatMessage` type without `cards`, with `toolName` for tool status display

- [ ] **Step 1: Update the chat types file**

Replace the entire file with:

```typescript
// ── Tool Status ───────────────────────────────────────────

export interface ToolStatusInfo {
  tool: string;
  status: "started" | "ended";
}

// ── Message ──────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  /** Tool execution status (shows "正在查询..." during tool calls) */
  toolStatus?: ToolStatusInfo;
  /** Progress indicator for evaluation tasks */
  progress?: ProgressInfo;
  timestamp: number;
}

export interface ProgressInfo {
  status: string;
  evaluated_count?: number;
  total_count?: number;
}

// ── Session Management ────────────────────────────────────

export interface SessionInfo {
  session_id: string;
  has_history: boolean;
}
```

Key changes:
- Removed all Card types (`EvaluationSummaryCardData`, `JobListCardData`, etc.)
- Removed `ChatCard` union type
- Removed `FunnelStageData`, `CandidateItemData`
- Replaced `cards` field with `toolStatus` for showing tool execution state
- `content` is now always a string (may contain Markdown)

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`

Expected: Some errors from components still referencing old types — that's expected, will be fixed in Task 3-4.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/chat/types/chat.ts
git commit -m "feat: update chat types — remove Cards, add ToolStatus for ReAct agent"
```

---

### Task 3: Update `useChat` hook for new SSE events

**Files:**
- Modify: `frontend/src/features/chat/hooks/useChat.ts`

**Interfaces:**
- Consumes: Updated `ChatMessage`, `ProgressInfo` types from Task 2
- Produces: `useChat` hook handling `tool_start`, `tool_end`, `text_delta` events

- [ ] **Step 1: Rewrite the `sendMessage` callback's event handling**

Replace the entire `useChat.ts` file with:

```typescript
import { useState, useRef, useCallback } from "react";

import type { ChatMessage, ProgressInfo, ToolStatusInfo } from "@/features/chat/types/chat";
import { sendChatMessage, closeSession as apiCloseSession, getSession, getHistory } from "@/features/chat/api/chat";

const SESSION_STORAGE_KEY = "chat-session-id";

function generateSessionId(): string {
  return crypto.randomUUID();
}

function loadSessionId(): string | null {
  try {
    return localStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
}

function saveSessionId(id: string): void {
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, id);
  } catch {
    // localStorage may be unavailable
  }
}

function clearSessionId(): void {
  try {
    localStorage.removeItem(SESSION_STORAGE_KEY);
  } catch {
    // ignore
  }
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(() => loadSessionId());
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
    let assistantToolStatus: ToolStatusInfo | undefined;
    let assistantProgress: ProgressInfo | undefined;

    const controller = sendChatMessage(
      text,
      sessionId,
      (eventType, data) => {
        switch (eventType) {
          case "session": {
            const newSessionId = data.session_id as string;
            setSessionId(newSessionId);
            saveSessionId(newSessionId);
            break;
          }

          case "tool_start": {
            const toolName = data.tool as string;
            assistantToolStatus = { tool: toolName, status: "started" };
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent || `正在使用 ${toolName} 查询...`,
                  toolStatus: assistantToolStatus,
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: `正在使用 ${toolName} 查询...`,
                  toolStatus: assistantToolStatus,
                  timestamp: Date.now(),
                });
              }
              return updated;
            });
            break;
          }

          case "tool_end": {
            const toolName = data.tool as string;
            assistantToolStatus = { tool: toolName, status: "ended" };
            // Don't update UI on tool_end — wait for text_delta or result
            break;
          }

          case "text_delta": {
            const delta = data.content as string;
            assistantContent += delta;
            assistantToolStatus = undefined; // text output means tool is done
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  toolStatus: undefined,
                  progress: undefined,
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: assistantContent,
                  timestamp: Date.now(),
                });
              }
              return updated;
            });
            break;
          }

          case "progress": {
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
                  content: assistantProgress!.status,
                  progress: assistantProgress,
                };
              }
              return updated;
            });
            break;
          }

          case "result": {
            const replyMessage = (data.reply_message as string) || "";
            if (replyMessage) {
              assistantContent = replyMessage;
            }
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  toolStatus: undefined,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              } else {
                updated.push({
                  role: "assistant",
                  content: assistantContent,
                  timestamp: Date.now(),
                });
              }
              return updated;
            });
            break;
          }

          case "error": {
            assistantContent = `❌ ${(data.message as string) || "发生错误"}`;
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: assistantContent,
                  toolStatus: undefined,
                  progress: undefined,
                  timestamp: Date.now(),
                };
              }
              return updated;
            });
            break;
          }
        }
      },
      (error) => {
        const errorMsg: ChatMessage = {
          role: "assistant",
          content: `❌ 连接中断：${error.message}`,
          timestamp: Date.now(),
        };
        setMessages((prev) => {
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
  }, [isProcessing, sessionId]);

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

  const closeSession = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    if (sessionId) {
      try {
        await apiCloseSession(sessionId);
      } catch {
        // Non-blocking
      }
    }

    setMessages([]);
    setIsProcessing(false);

    const newId = generateSessionId();
    setSessionId(newId);
    saveSessionId(newId);
  }, [sessionId]);

  const validateSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const info = await getSession(sessionId);
      if (info.has_history) {
        try {
          const history = await getHistory(sessionId);
          if (history.messages.length > 0) {
            setMessages(history.messages.map((m) => ({
              role: m.role,
              content: m.content,
              timestamp: m.timestamp,
            })));
          }
        } catch {
          // History fetch failed — start with empty view
        }
      } else {
        const newId = generateSessionId();
        setSessionId(newId);
        saveSessionId(newId);
      }
    } catch {
      // Keep current session_id
    }
  }, [sessionId]);

  return {
    messages,
    isProcessing,
    sessionId,
    sendMessage,
    disconnect,
    clearMessages,
    closeSession,
    validateSession,
  };
}

export type UseChatReturn = ReturnType<typeof useChat>;
```

Key changes from old version:
- `thinking` event handler removed
- `intent` event handler removed
- `tool_start` event handler added — shows "正在使用 X 查询..."
- `tool_end` event handler added — silent (waiting for text_delta or result)
- `text_delta` event handler added — incremental content streaming
- `result` event no longer processes `cards`

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`

Expected: Errors only from `AssistantMessage.tsx` (still referencing old Card types). Will fix in Task 4.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/chat/hooks/useChat.ts
git commit -m "feat: update useChat hook for ReAct agent SSE events (tool_start/tool_end/text_delta)"
```

---

### Task 4: Simplify `AssistantMessage` — Markdown rendering

**Files:**
- Modify: `frontend/src/features/chat/components/AssistantMessage.tsx`

**Interfaces:**
- Consumes: Updated `ChatMessage` type (no `cards`, has `toolStatus`)
- Produces: Markdown-rendered assistant messages

- [ ] **Step 1: Rewrite `AssistantMessage` with Markdown rendering**

Replace the entire file:

```tsx
import ReactMarkdown from "react-markdown";

import type { ChatMessage } from "@/features/chat/types/chat";
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
        ) : message.toolStatus?.status === "started" ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <span>{message.content}</span>
          </div>
        ) : (
          <div className="text-sm leading-relaxed prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-table:text-xs">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
```

Key changes:
- Removed all Card imports and `renderCard` function
- Removed `ConfirmCard` and `onSendMessage` prop
- Added `ReactMarkdown` for rendering Markdown content
- Added spinner animation for `toolStatus === "started"` state
- Tailwind `prose` classes for Markdown styling

- [ ] **Step 2: Update `ChatMessages` — remove `onSendMessage` prop**

The `onSendMessage` was only used for `ConfirmCard`. Simplify `ChatMessages.tsx`:

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

- [ ] **Step 3: Update `ChatWindow` — remove `onSendMessage` prop chain**

Find where `ChatMessages` is used and remove the `onSendMessage` prop. In `ChatWindow.tsx`, the prop chain was: `ChatWindow → ChatMessages → AssistantMessage → ConfirmCard`. Now it's just `ChatWindow → ChatMessages`.

Find the `<ChatMessages>` usage in `ChatWindow.tsx` and remove `onSendMessage={onSendMessage}` if present.

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`

Expected: No errors (or only unrelated warnings). All chat-related type errors should be resolved.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/chat/components/AssistantMessage.tsx frontend/src/features/chat/components/ChatMessages.tsx frontend/src/features/chat/components/ChatWindow.tsx
git commit -m "feat: simplify AssistantMessage to Markdown rendering, remove Card system and ConfirmCard"
```

---

### Task 5: Final backend cleanup — delete `nodes.py`

**Files:**
- Delete: `backend/app/services/conversation/nodes.py`

**Interfaces:**
- Consumes: None
- Produces: Clean codebase with no deprecated files

- [ ] **Step 1: Verify nothing imports from nodes.py**

Run: `cd backend && grep -r "from app.services.conversation.nodes import\|from app.services.conversation.nodes import\|conversation.nodes" app/ tests/ 2>/dev/null || echo "NO_IMPORTS_FOUND"`

Expected: `NO_IMPORTS_FOUND`

- [ ] **Step 2: Delete nodes.py**

```bash
rm backend/app/services/conversation/nodes.py
```

- [ ] **Step 3: Verify mypy and tests**

Run: `cd backend && uv run mypy --strict app/ && uv run pytest tests/ -v --ignore=tests/test_react_tools.py -q 2>&1 | tail -10`

Expected: mypy passes, tests pass.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete deprecated nodes.py (ReAct agent migration complete)"
```

---

### Task 6: Update `skeleton.md` to reflect new architecture

**Files:**
- Modify: `skeleton.md`

**Interfaces:**
- Consumes: All Phase 1-3 changes
- Produces: Up-to-date architecture documentation

- [ ] **Step 1: Update the conversation module section in skeleton.md**

Find the `conversation/` section (around line 547-600) and replace it with:

```
conversation/ — LangGraph ReAct 对话助手（Phase 2 重构）

__init__.py   — 模块入口，导出 build_conversation_graph, ConversationContext

state.py      — ConversationContext(TypedDict): state_modifier 上下文
                session_summary, context_entities

prompts.py    — ReAct 对话 LLM 提示词
                HR_AGENT_SYSTEM_PROMPT: ReAct Agent 系统提示（6 条核心原则 + 工具策略 + 回复格式）
                build_state_modifier(state: dict) -> str
                  ↑ 动态注入 session_summary + context_entities

tools.py      — ReAct Agent 7 个 Tool 定义
                查询 Tool (3):
                  query_jobs(filter?, fields?, limit=20) -> str
                    ↑ filter: job_code/keyword/status/work_type/salary_min/salary_max
                    ↑ fields: 白名单字段选择
                  query_applications(job_code?, job_title?, filter?, fields?, group_by?, sort_by?, sort_order?, limit=50) -> str
                    ↑ filter: status/ai_decision/candidate_name/min_ai_score/max_ai_score
                    ↑ group_by: ["status"] / ["ai_decision"] / ["status","ai_decision"]
                  query_evaluation(job_code?, task_id?) -> str
                写操作 Tool (4):
                  trigger_evaluation(job_code?, job_title?, interview_quota?) -> str
                    ↑ 内嵌运行评估图，进度通过 adispatch_custom_event 冒泡
                  confirm_evaluation(task_id) -> str
                    ↑ 按 AI 建议批量更新候选人状态
                  update_candidate_status(job_code, candidate_name, target_status) -> str
                    ↑ target_status: "interview" | "rejected"
                  update_job_status(job_code, target_status) -> str
                    ↑ target_status: "active" | "closed"
                参数安全性: filter key 白名单 + value 校验 + 参数化查询 + 行级权限

graph.py      — ReAct Agent 图定义
                build_conversation_graph(checkpointer, context?) -> CompiledStateGraph
                  ↑ create_react_agent(model=ChatOpenAI, tools=ALL_TOOLS, state_modifier=...)
                ALL_TOOLS: [query_jobs, query_applications, query_evaluation,
                            trigger_evaluation, confirm_evaluation,
                            update_candidate_status, update_job_status]
```

Also update the SSE event types in the chat API section (around line 415):

```
SSE 事件类型：session, tool_start, tool_end, text_delta, progress, result, error, done
```

And update the chat DTO section to reflect removed cards and new events.

- [ ] **Step 2: Commit**

```bash
git add skeleton.md
git commit -m "docs: update skeleton.md — ReAct agent architecture, new SSE events, tool definitions"
```

---

### Task 7: Final end-to-end verification

**Files:**
- No new files

- [ ] **Step 1: Backend mypy**

Run: `cd backend && uv run mypy --strict app/`

Expected: `Success: no issues found`

- [ ] **Step 2: Backend tests**

Run: `cd backend && uv run pytest tests/ -v 2>&1 | tail -30`

Expected: All pass.

- [ ] **Step 3: Frontend TypeScript check**

Run: `cd frontend && npx tsc --noEmit`

Expected: No errors.

- [ ] **Step 4: Frontend build**

Run: `cd frontend && npm run build 2>&1 | tail -10`

Expected: Build succeeds.

- [ ] **Step 5: Final commit with any fixups**

```bash
git add -A
git commit -m "chore: Phase 3 final verification adjustments"
```

---

**Phase 3 Complete.** Frontend uses Markdown rendering with streaming text deltas, backend is fully migrated to ReAct agent with clean test suite. The entire HR Agent conversation system has been restructured from a rigid 14-node intent-classification graph to a flexible ReAct + Tool-Calling architecture.

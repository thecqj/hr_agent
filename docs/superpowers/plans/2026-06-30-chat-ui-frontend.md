# 小助手 UI 优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 HR 小助手前端 UI：最小化/关闭分离、气泡自由拖动+窗口跟随、拖动互不干扰、会话管理集成。

**Architecture:** 改造现有 `useBubbleDrag`/`useChatWindowDragResize` hooks 实现自由拖动和联动；`useChat` hook 增加 sessionId 管理；ChatWindow 增加 minimize/close 分离和确认弹窗。

**Tech Stack:** React 19, TypeScript, shadcn/ui, Lucide Icons, Pointer Events API

## Global Constraints

- TypeScript strict mode — no `any` unless unavoidable
- Follow existing component patterns (shadcn/ui, Lucide icons)
- All drag logic uses Pointer Events (not Mouse Events)
- No external drag libraries — pure React + pointer events
- YAGNI: only features from the spec

## Prerequisites

This plan depends on the backend plan being completed first (or at least the API endpoints being available). The frontend can be developed in parallel with mock API responses for initial development, but integration testing requires the backend.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `features/chat/types/chat.ts` | Modify | 新增 session 相关类型 |
| `features/chat/api/chat.ts` | Modify | sendChatMessage 新增 sessionId，新增 closeSession/getSession API |
| `features/chat/hooks/useChat.ts` | Modify | sessionId 管理，closeSession，session SSE 事件 |
| `features/chat/hooks/useDragResize.ts` | Modify | useBubbleDrag 自由拖动+垂直，窗口跟随气泡，偏移量追踪 |
| `features/chat/components/ChatBubble.tsx` | Modify | 最小化逻辑，点击行为变更 |
| `features/chat/components/ChatWindow.tsx` | Modify | 新增最小化按钮，关闭确认弹窗，header 改造 |

---

### Task 1: 类型定义 — Session 相关类型

**Files:**
- Modify: `features/chat/types/chat.ts`

**Interfaces:**
- Produces: `SessionInfo` type

- [ ] **Step 1: Add SessionInfo type**

In `features/chat/types/chat.ts`, add at the end:

```typescript
// ── 会话管理 ─────────────────────────────────────────────

export interface SessionInfo {
  session_id: string;
  has_history: boolean;
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors related to the new type

- [ ] **Step 3: Commit**

```bash
git add src/features/chat/types/chat.ts
git commit -m "feat: add SessionInfo type for chat session management"
```

---

### Task 2: API 层 — Session API + sendChatMessage 改造

**Files:**
- Modify: `features/chat/api/chat.ts`

**Interfaces:**
- Consumes: `SessionInfo` type
- Produces: `sendChatMessage(message, sessionId, onEvent, onError, onDone)`, `closeSession(sessionId)`, `getSession(sessionId?)`

- [ ] **Step 1: Update sendChatMessage to accept sessionId**

Replace the `sendChatMessage` function in `features/chat/api/chat.ts`:

```typescript
import { useAuthStore } from "@/features/auth/store/authStore";
import type { SessionInfo } from "@/features/chat/types/chat";

const API_BASE = "/api";

/**
 * Send a chat message and return an AbortController for SSE streaming.
 * Uses native fetch + ReadableStream for POST-based SSE
 * (EventSource API only supports GET).
 */
export function sendChatMessage(
  message: string,
  sessionId: string | null,
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
    body: JSON.stringify({ message, session_id: sessionId }),
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

/**
 * Close a chat session — marks it as inactive and triggers summary generation.
 */
export async function closeSession(sessionId: string): Promise<void> {
  const token = useAuthStore.getState().token;

  const response = await fetch(`${API_BASE}/chat/session/close`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
}

/**
 * Query the current active session for the user.
 * If session_id is provided, checks that specific session's status.
 * Otherwise, returns the most recent active session.
 */
export async function getSession(sessionId?: string): Promise<SessionInfo> {
  const token = useAuthStore.getState().token;
  const params = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";

  const response = await fetch(`${API_BASE}/chat/session${params}`, {
    method: "GET",
    headers: {
      Authorization: token ? `Bearer ${token}` : "",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json() as Promise<SessionInfo>;
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors (but useChat.ts may break since sendChatMessage signature changed — that's OK, fixed in Task 3)

- [ ] **Step 3: Commit**

```bash
git add src/features/chat/api/chat.ts
git commit -m "feat: add sessionId to sendChatMessage and new session API functions"
```

---

### Task 3: useChat Hook — Session 管理

**Files:**
- Modify: `features/chat/hooks/useChat.ts`

**Interfaces:**
- Consumes: `sendChatMessage(message, sessionId, ...)`, `closeSession(sessionId)`, `getSession(sessionId?)`
- Produces: `useChat()` returns `{ ..., sessionId, closeSession }`

- [ ] **Step 1: Rewrite useChat with sessionId management**

Replace `features/chat/hooks/useChat.ts`:

```typescript
import { useState, useRef, useCallback } from "react";

import type { ChatMessage, ChatCard, ProgressInfo } from "@/features/chat/types/chat";
import { sendChatMessage, closeSession as apiCloseSession, getSession } from "@/features/chat/api/chat";

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
    let assistantCards: ChatCard[] | undefined;
    let assistantProgress: ProgressInfo | undefined;

    const controller = sendChatMessage(
      text,
      sessionId,
      (eventType, data) => {
        switch (eventType) {
          case "session": {
            // Server confirms/assigns session_id
            const newSessionId = data.session_id as string;
            setSessionId(newSessionId);
            saveSessionId(newSessionId);
            break;
          }

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
                  content: assistantProgress!.status,
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
    // Abort any in-progress request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Call backend to close the session (triggers summary generation)
    if (sessionId) {
      try {
        await apiCloseSession(sessionId);
      } catch {
        // Non-blocking: session close failure doesn't prevent UI reset
      }
    }

    // Clear frontend state
    setMessages([]);
    setIsProcessing(false);

    // Generate new session_id for next conversation
    const newId = generateSessionId();
    setSessionId(newId);
    saveSessionId(newId);
  }, [sessionId]);

  /**
   * Check if the current session is still active (e.g., after page refresh).
   * If not, generate a new session ID.
   */
  const validateSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const info = await getSession(sessionId);
      if (!info.has_history) {
        // Session is no longer active or doesn't exist
        const newId = generateSessionId();
        setSessionId(newId);
        saveSessionId(newId);
      }
    } catch {
      // On error, keep current session_id — will be validated on next message
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
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: May have errors in ChatBubble/ChatWindow due to useChat() return type change — that's OK, fixed in later tasks

- [ ] **Step 3: Commit**

```bash
git add src/features/chat/hooks/useChat.ts
git commit -m "feat: add sessionId management and closeSession to useChat hook"
```

---

### Task 4: 拖动逻辑重写 — useBubbleDrag 自由拖动 + 窗口跟随

**Files:**
- Modify: `features/chat/hooks/useDragResize.ts`

**Interfaces:**
- Consumes: None
- Produces: `useBubbleDrag()` returns `{ style, handlers, side, top }`, `useChatWindowDragResize(bubbleSide, bubbleTop, onBubbleMove)` with bubble-follow support

This is the most complex task. The drag rewrite must:
1. Allow free (x+y) bubble dragging with horizontal edge-snap
2. Track vertical position in localStorage
3. Support window-follows-bubble with offset tracking
4. Ensure pointer events don't interfere between bubble, window, and text selection

- [ ] **Step 1: Rewrite useBubbleDrag with free dragging**

Replace the `useBubbleDrag` function in `features/chat/hooks/useDragResize.ts`:

```typescript
interface BubblePosition {
  side: "left" | "right";
  offset: number;  // horizontal offset from the edge
  top: number;     // vertical position from top of viewport
}

const BUBBLE_SIZE = 48;
const EDGE_MARGIN = 24;
const MIN_TOP = 24;
const DRAG_THRESHOLD = 5; // px to distinguish drag from click

const CHAT_WINDOW_MIN_SIZE: Size = { width: 320, height: 400 };
const CHAT_WINDOW_MAX_SIZE: Size = { width: 800, height: 700 };

function loadJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

/** Hook for draggable chat bubble — free drag, horizontal edge snap, vertical keep */
export function useBubbleDrag() {
  const defaultTop = typeof window !== "undefined"
    ? window.innerHeight - BUBBLE_SIZE - EDGE_MARGIN
    : 600;

  const [position, setPosition] = useState<BubblePosition>(
    () => loadJson("chat-bubble-position", {
      side: "right" as const,
      offset: EDGE_MARGIN,
      top: defaultTop,
    })
  );
  const [isDragging, setIsDragging] = useState(false);
  const startX = useRef(0);
  const startY = useRef(0);
  const startOffset = useRef(0);
  const startTop = useRef(0);

  // Callback for window position updates when bubble moves
  const onBubbleMoveRef = useRef<((dx: number, dy: number) => void) | null>(null);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    // Only respond to primary button on the bubble element itself
    if (e.button !== 0) return;
    setIsDragging(true);
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    startX.current = e.clientX;
    startY.current = e.clientY;
    startOffset.current = position.offset;
    startTop.current = position.top;
  }, [position.offset, position.top]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - startX.current;
    const dy = e.clientY - startY.current;

    // Use threshold to distinguish drag from click/text-selection
    if (Math.abs(dx) <= DRAG_THRESHOLD && Math.abs(dy) <= DRAG_THRESHOLD) return;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Calculate new horizontal offset
    let newOffset: number;
    if (position.side === "right") {
      newOffset = Math.max(EDGE_MARGIN, Math.min(
        viewportWidth - EDGE_MARGIN - BUBBLE_SIZE,
        startOffset.current - dx,
      ));
    } else {
      newOffset = Math.max(EDGE_MARGIN, Math.min(
        viewportWidth - EDGE_MARGIN - BUBBLE_SIZE,
        startOffset.current + dx,
      ));
    }

    // Calculate new vertical position (free)
    const newTop = Math.max(MIN_TOP, Math.min(
      viewportHeight - BUBBLE_SIZE - EDGE_MARGIN,
      startTop.current + dy,
    ));

    setPosition((prev) => ({ ...prev, offset: newOffset, top: newTop }));

    // Notify window to follow
    if (onBubbleMoveRef.current) {
      onBubbleMoveRef.current(
        newOffset - startOffset.current,
        newTop - startTop.current,
      );
    }
  }, [position.side, isDragging]);

  const handlePointerUp = useCallback(() => {
    if (!isDragging) return;
    setIsDragging(false);

    const viewportWidth = window.innerWidth;

    // Snap to nearest horizontal edge
    let newSide: "left" | "right";
    if (position.side === "right") {
      const distanceFromRight = position.offset;
      const distanceFromLeft = viewportWidth - position.offset - BUBBLE_SIZE;
      newSide = distanceFromLeft < distanceFromRight ? "left" : "right";
    } else {
      const distanceFromLeft = position.offset;
      const distanceFromRight = viewportWidth - position.offset - BUBBLE_SIZE;
      newSide = distanceFromRight < distanceFromLeft ? "right" : "left";
    }

    setPosition((prev) => ({
      ...prev,
      side: newSide,
      offset: EDGE_MARGIN,
    }));
  }, [position.side, position.offset, isDragging]);

  // Persist to localStorage on change
  useEffect(() => {
    localStorage.setItem("chat-bubble-position", JSON.stringify(position));
  }, [position]);

  const style: React.CSSProperties =
    position.side === "right"
      ? { position: "fixed", top: position.top, right: position.offset, zIndex: 40 }
      : { position: "fixed", top: position.top, left: position.offset, zIndex: 40 };

  const snapping = !isDragging;

  return {
    style: {
      ...style,
      transition: snapping ? "right 0.3s ease, left 0.3s ease" : "none",
    },
    handlers: {
      onPointerDown: handlePointerDown,
      onPointerMove: handlePointerMove,
      onPointerUp: handlePointerUp,
    },
    side: position.side,
    top: position.top,
    isDragging,
    onBubbleMoveRef,
  };
}
```

- [ ] **Step 2: Rewrite useChatWindowDragResize with bubble-follow support**

Replace the `useChatWindowDragResize` function:

```typescript
/** Hook for movable + resizable chat window, with bubble-follow support */
export function useChatWindowDragResize(
  bubbleSide: "left" | "right",
  bubbleTop: number,
  onBubbleMoveRef: React.MutableRefObject<((dx: number, dy: number) => void) | null>,
) {
  const [state, setState] = useState<{ position: Position; size: Size }>(() => {
    const saved = loadJson<{ position: Position; size: Size } | null>("chat-window-state", null);
    if (saved) return saved;
    const vw = typeof window !== "undefined" ? window.innerWidth : 1024;
    const vh = typeof window !== "undefined" ? window.innerHeight : 768;
    const defaultSize = { width: 380, height: 520 };
    const defaultPos: Position =
      bubbleSide === "right"
        ? { x: vw - defaultSize.width - EDGE_MARGIN, y: vh - defaultSize.height - BUBBLE_SIZE - EDGE_MARGIN * 2 - 16 }
        : { x: EDGE_MARGIN, y: vh - defaultSize.height - BUBBLE_SIZE - EDGE_MARGIN * 2 - 16 };
    return { position: defaultPos, size: defaultSize };
  });

  // Track the offset between window and bubble for follow behavior
  const windowBubbleOffset = useRef({ dx: 0, dy: 0 });

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem("chat-window-state", JSON.stringify(state));
  }, [state]);

  // Register bubble-move callback so window follows when bubble is dragged
  useEffect(() => {
    onBubbleMoveRef.current = (dx: number, dy: number) => {
      setState((prev) => {
        const newX = prev.position.x + dx;
        const newY = prev.position.y + dy;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        return {
          ...prev,
          position: {
            x: Math.max(0, Math.min(vw - prev.size.width, newX)),
            y: Math.max(0, Math.min(vh - prev.size.height, newY)),
          },
        };
      });
    };
    return () => {
      onBubbleMoveRef.current = null;
    };
  }, [onBubbleMoveRef]);

  // --- Move logic (window header drag) ---
  const moveDragging = useRef(false);
  const moveStart = useRef({ x: 0, y: 0 });

  const handleMoveStart = useCallback((e: React.PointerEvent) => {
    // Only respond to primary button
    if (e.button !== 0) return;
    moveDragging.current = true;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    moveStart.current = { x: e.clientX - state.position.x, y: e.clientY - state.position.y };

    // Track offset from bubble position
    const bubbleX = bubbleSide === "right"
      ? window.innerWidth - state.position.x
      : state.position.x;
    windowBubbleOffset.current = { dx: state.position.x, dy: state.position.y - bubbleTop };
  }, [state.position, bubbleSide, bubbleTop]);

  const handleMove = useCallback((e: React.PointerEvent) => {
    if (!moveDragging.current) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const newX = Math.max(0, Math.min(vw - state.size.width, e.clientX - moveStart.current.x));
    const newY = Math.max(0, Math.min(vh - state.size.height, e.clientY - moveStart.current.y));
    setState((prev) => ({ ...prev, position: { x: newX, y: newY } }));

    // Update offset for future bubble-follow
    windowBubbleOffset.current = { dx: newX, dy: newY - bubbleTop };
  }, [state.size, bubbleTop]);

  const handleMoveEnd = useCallback(() => {
    moveDragging.current = false;
  }, []);

  // --- Resize logic ---
  const resizeDragging = useRef(false);
  const resizeStart = useRef({ x: 0, y: 0, width: 0, height: 0 });

  const handleResizeStart = useCallback((e: React.PointerEvent) => {
    e.stopPropagation();
    resizeDragging.current = true;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    resizeStart.current = { x: e.clientX, y: e.clientY, width: state.size.width, height: state.size.height };
  }, [state.size]);

  const handleResize = useCallback((e: React.PointerEvent) => {
    if (!resizeDragging.current) return;
    const dx = e.clientX - resizeStart.current.x;
    const dy = e.clientY - resizeStart.current.y;
    const newWidth = Math.max(CHAT_WINDOW_MIN_SIZE.width, Math.min(CHAT_WINDOW_MAX_SIZE.width, resizeStart.current.width + dx));
    const newHeight = Math.max(CHAT_WINDOW_MIN_SIZE.height, Math.min(CHAT_WINDOW_MAX_SIZE.height, resizeStart.current.height + dy));
    setState((prev) => ({ ...prev, size: { width: newWidth, height: newHeight } }));
  }, []);

  const handleResizeEnd = useCallback(() => {
    resizeDragging.current = false;
  }, []);

  return {
    position: state.position,
    size: state.size,
    moveHandlers: {
      onPointerDown: handleMoveStart,
      onPointerMove: handleMove,
      onPointerUp: handleMoveEnd,
    },
    resizeHandlers: {
      onPointerDown: handleResizeStart,
      onPointerMove: handleResize,
      onPointerUp: handleResizeEnd,
    },
  };
}
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: ChatBubble and ChatWindow may have errors due to changed hook signatures — that's OK, fixed in next tasks

- [ ] **Step 4: Commit**

```bash
git add src/features/chat/hooks/useDragResize.ts
git commit -m "feat: rewrite useBubbleDrag for free dragging and useChatWindowDragResize with bubble-follow"
```

---

### Task 5: ChatBubble — 点击行为 + 最小化逻辑

**Files:**
- Modify: `features/chat/components/ChatBubble.tsx`

**Interfaces:**
- Consumes: `useBubbleDrag()` new return values (`isDragging`, `onBubbleMoveRef`, `top`)
- Produces: Passes `bubbleTop` and `onBubbleMoveRef` to ChatWindow

- [ ] **Step 1: Rewrite ChatBubble with minimize-on-click-when-open**

Replace `features/chat/components/ChatBubble.tsx`:

```typescript
import { useRef, useState, useEffect } from "react";
import { MessageCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ChatWindow } from "./ChatWindow";
import { useBubbleDrag } from "@/features/chat/hooks/useDragResize";
import { useChat } from "@/features/chat/hooks/useChat";

export function ChatBubble() {
  const [isOpen, setIsOpen] = useState(false);
  const {
    style,
    handlers,
    side,
    top,
    isDragging: bubbleIsDragging,
    onBubbleMoveRef,
  } = useBubbleDrag();

  const chat = useChat();

  // Validate session on first open
  const hasValidated = useRef(false);
  useEffect(() => {
    if (isOpen && !hasValidated.current) {
      hasValidated.current = true;
      chat.validateSession();
    }
  }, [isOpen, chat.validateSession]);

  const didDrag = useRef(false);
  const pointerStartPos = useRef({ x: 0, y: 0 });

  const handlePointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    // Prevent event from propagating to window underneath
    e.stopPropagation();
    didDrag.current = false;
    pointerStartPos.current = { x: e.clientX, y: e.clientY };
    handlers.onPointerDown(e);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    const dx = Math.abs(e.clientX - pointerStartPos.current.x);
    const dy = Math.abs(e.clientY - pointerStartPos.current.y);
    if (dx > 5 || dy > 5) didDrag.current = true;
    handlers.onPointerMove(e);
  };

  const handlePointerUp = () => {
    handlers.onPointerUp();
  };

  const handleClick = () => {
    if (!didDrag.current) {
      // Toggle: if window is open → minimize; if closed → open
      setIsOpen((prev) => !prev);
    }
  };

  return (
    <div
      style={style}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      className="touch-none"
    >
      {isOpen && (
        <ChatWindow
          onMinimize={() => setIsOpen(false)}
          onClose={chat.closeSession}
          bubbleSide={side}
          bubbleTop={top}
          onBubbleMoveRef={onBubbleMoveRef}
          chat={chat}
        />
      )}
      <Button
        size="icon"
        className="h-12 w-12 rounded-full shadow-lg touch-none"
        onClick={handleClick}
      >
        <MessageCircle className="h-6 w-6" />
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: ChatWindow errors due to new props — OK, fixed in next task

- [ ] **Step 3: Commit**

```bash
git add src/features/chat/components/ChatBubble.tsx
git commit -m "feat: ChatBubble minimize-on-click, session validation, stopPropagation"
```

---

### Task 6: ChatWindow — 最小化/关闭分离 + 确认弹窗

**Files:**
- Modify: `features/chat/components/ChatWindow.tsx`

**Interfaces:**
- Consumes: `onMinimize`, `onClose`, `bubbleTop`, `onBubbleMoveRef`, `chat` from ChatBubble
- Produces: Renders minimize ("—") and close ("✕") buttons with confirmation dialog

- [ ] **Step 1: Rewrite ChatWindow with minimize/close and confirmation dialog**

Replace `features/chat/components/ChatWindow.tsx`:

```typescript
import { useState } from "react";
import { Minus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";
import { useChatWindowDragResize } from "@/features/chat/hooks/useDragResize";
import type { UseChatReturn } from "@/features/chat/hooks/useChat";

interface ChatWindowProps {
  onMinimize: () => void;
  onClose: () => Promise<void>;
  bubbleSide: "left" | "right";
  bubbleTop: number;
  onBubbleMoveRef: React.MutableRefObject<((dx: number, dy: number) => void) | null>;
  chat: UseChatReturn;
}

export function ChatWindow({
  onMinimize,
  onClose,
  bubbleSide,
  bubbleTop,
  onBubbleMoveRef,
  chat,
}: ChatWindowProps) {
  const { messages, isProcessing, sendMessage } = chat;
  const { position, size, moveHandlers, resizeHandlers } = useChatWindowDragResize(
    bubbleSide,
    bubbleTop,
    onBubbleMoveRef,
  );
  const [showCloseDialog, setShowCloseDialog] = useState(false);

  const handleCloseClick = () => {
    setShowCloseDialog(true);
  };

  const handleConfirmClose = async () => {
    setShowCloseDialog(false);
    await onClose();
  };

  const handleCancelClose = () => {
    setShowCloseDialog(false);
  };

  return (
    <>
      <div
        className="fixed bg-card border rounded-xl shadow-xl flex flex-col overflow-hidden z-50"
        style={{
          left: position.x,
          top: position.y,
          width: size.width,
          height: size.height,
        }}
      >
        {/* Header — draggable */}
        <div
          className="flex items-center justify-between px-4 py-3 border-b bg-primary/5 cursor-grab active:cursor-grabbing touch-none shrink-0"
          onPointerDown={(e) => {
            e.stopPropagation();
            moveHandlers.onPointerDown(e);
          }}
          onPointerMove={(e) => {
            e.stopPropagation();
            moveHandlers.onPointerMove(e);
          }}
          onPointerUp={(e) => {
            e.stopPropagation();
            moveHandlers.onPointerUp(e);
          }}
        >
          <h3 className="font-semibold text-sm select-none">HR 智能助手</h3>
          <div className="flex items-center gap-1">
            {/* Minimize button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={(e) => {
                e.stopPropagation();
                onMinimize();
              }}
            >
              <Minus className="h-4 w-4" />
            </Button>
            {/* Close button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={(e) => {
                e.stopPropagation();
                handleCloseClick();
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Messages */}
        <ChatMessages messages={messages} onSendMessage={sendMessage} />

        {/* Input */}
        <ChatInput onSend={sendMessage} disabled={isProcessing} />

        {/* Resize handle */}
        <div
          className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize touch-none"
          onPointerDown={(e) => {
            e.stopPropagation();
            resizeHandlers.onPointerDown(e);
          }}
          onPointerMove={(e) => {
            e.stopPropagation();
            resizeHandlers.onPointerMove(e);
          }}
          onPointerUp={(e) => {
            e.stopPropagation();
            resizeHandlers.onPointerUp(e);
          }}
        >
          <svg className="w-3 h-3 text-muted-foreground/50 absolute bottom-0.5 right-0.5" viewBox="0 0 6 6" fill="currentColor">
            <circle cx="5" cy="1" r="0.7" />
            <circle cx="5" cy="3.5" r="0.7" />
            <circle cx="2.5" cy="3.5" r="0.7" />
            <circle cx="5" cy="6" r="0.7" />
            <circle cx="2.5" cy="6" r="0.7" />
            <circle cx="0" cy="6" r="0.7" />
          </svg>
        </div>
      </div>

      {/* Close confirmation dialog */}
      <Dialog open={showCloseDialog} onOpenChange={setShowCloseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>关闭对话</DialogTitle>
            <DialogDescription>
              {isProcessing
                ? "对话正在进行中，关闭将中断当前操作。AI 仍会记住之前讨论的内容。确定关闭吗？"
                : "关闭将清空当前对话记录，AI 仍会记住之前讨论的内容。确定关闭吗？"}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={handleCancelClose}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleConfirmClose}>
              确定关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

Note: This requires `Dialog` from shadcn/ui. Check if `components/ui/dialog.tsx` exists. If not, add it:

```bash
cd frontend && npx shadcn@latest add dialog
```

- [ ] **Step 2: Export UseChatReturn type from useChat**

In `features/chat/hooks/useChat.ts`, add the return type export:

```typescript
export type UseChatReturn = ReturnType<typeof useChat>;
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: PASS

- [ ] **Step 4: Manual UI test**

Run: `cd frontend && npm run dev`
- Open the recruiter dashboard
- Verify chat bubble appears in bottom-right
- Click bubble → window opens
- Click bubble again → window minimizes (equals "—")
- Click "—" → window minimizes
- Click "✕" → confirmation dialog appears
- "Cancel" → dialog closes, window stays
- "Confirm close" → window closes, messages cleared
- Reopen → empty messages, new session
- Drag bubble → window follows
- Drag window header → only window moves, bubble stays
- Select text in window → bubble doesn't move
- Drag bubble vertically → stays at new vertical position after release

- [ ] **Step 5: Commit**

```bash
git add src/features/chat/
git commit -m "feat: ChatWindow minimize/close separation, confirmation dialog, drag isolation"
```

---

### Task 7: 最终验证 — 全量编译 + 手动测试

**Files:**
- None (verification only)

- [ ] **Step 1: TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 2: Full manual test checklist**

Test each scenario from the spec:

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Click bubble (closed) | Window opens |
| 2 | Click bubble (open) | Window minimizes |
| 3 | Click "—" button | Window minimizes, messages preserved |
| 4 | Click bubble after minimize | Window reopens with messages |
| 5 | Click "✕" button | Confirmation dialog appears |
| 6 | Cancel close | Dialog closes, window stays |
| 7 | Confirm close | Window closes, messages cleared, new session_id |
| 8 | Confirm close while processing | Dialog shows "对话正在进行中" warning, confirm aborts + closes |
| 9 | Drag bubble horizontally | Bubble moves, window follows, snaps to edge on release |
| 10 | Drag bubble vertically | Bubble moves up/down, window follows, stays at new position on release |
| 11 | Drag window header | Only window moves, bubble doesn't move |
| 12 | Select text in window | Neither bubble nor window moves |
| 13 | Drag resize handle | Window resizes, bubble doesn't move |
| 14 | Page refresh | localStorage has session_id, reopen shows empty messages but AI has context |

- [ ] **Step 3: Commit any fixes**

If any issues found during testing:
```bash
git add -A
git commit -m "fix: resolve UI issues found during manual testing"
```

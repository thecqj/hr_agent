# HR Agent Bugfix & UX Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 HR-side bugs/UX issues: slow page load, unfriendly greeting, incomplete candidate queries, thinking process appearing as chat bubbles.

**Architecture:** Four independent fixes targeting frontend hooks, frontend components, backend prompts/tools, and backend chat history. No cross-task dependencies.

**Tech Stack:** React 19 + TypeScript + Zustand (frontend), FastAPI + LangGraph (backend)

## Global Constraints

- Strict type hints on all Python code; must pass `mypy --strict`
- Modern Python syntax: `int | None`, `list[str]`
- No database migrations needed
- No breaking changes to existing API contracts
- After all tasks: run `uv run mypy --strict app/` from `backend/` and `npm run build` from `frontend/`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/features/chat/hooks/useChat.ts` | Modify | Remove auto-mount useEffect, add `loadHistory()` method |
| `frontend/src/features/chat/components/ChatBubble.tsx` | Modify | Trigger `loadHistory()` on window open |
| `frontend/src/features/chat/components/ChatMessages.tsx` | Modify | Replace empty-state greeting text |
| `frontend/src/features/chat/components/ChatInput.tsx` | Modify | Replace placeholder text |
| `backend/app/services/conversation/prompts.py` | Modify | Add candidate query guidance to system prompt |
| `backend/app/services/conversation/tools.py` | Modify | Add docstring examples, add secondary sort order |
| `backend/app/api/chat.py` | Modify | Skip AI messages with tool_calls in history |

---

### Task 1: Lazy-load chat history (Fix Issue 1)

**Files:**
- Modify: `frontend/src/features/chat/hooks/useChat.ts:263-319`
- Modify: `frontend/src/features/chat/components/ChatBubble.tsx:17,52`

**Interfaces:**
- Consumes: `getSession`, `getHistory` from `@/features/chat/api/chat` (existing)
- Produces: `useChat()` return type gains `loadHistory: () => Promise<void>`

- [ ] **Step 1: Modify `useChat.ts` — remove auto-mount useEffect, add `loadHistory` method**

Replace lines 263–319 (from `const validateSession` through the end of the `useEffect`) with:

```ts
  const loadHistory = useCallback(async () => {
    const savedId = loadSessionId(userId);
    if (!savedId) return;
    setSessionId(savedId);
    try {
      const info = await getSession(savedId);
      if (info.has_history) {
        const history = await getHistory(savedId);
        if (history.messages.length > 0) {
          setMessages(history.messages.map((m) => ({
            role: m.role,
            content: m.content,
            timestamp: m.timestamp,
          })));
        }
      } else {
        clearSessionId(userId);
        setSessionId(null);
      }
    } catch {
      // Keep current state
    }
  }, [userId]);

  return {
    messages,
    isProcessing,
    sessionId,
    sendMessage,
    disconnect,
    clearMessages,
    closeSession,
    loadHistory,
  };
```

This removes the `validateSession` callback, the `hasValidated` ref, and the entire `useEffect` that auto-fetched history on mount. The new `loadHistory` is a public method that the caller invokes explicitly.

- [ ] **Step 2: Modify `ChatBubble.tsx` — trigger `loadHistory` when opening chat window**

Change the `setIsOpen` toggle in `handlePointerUp` (around line 52) to also call `loadHistory`:

```tsx
  const handlePointerUp = () => {
    if (!isOpen) {
      handlers.onPointerUp();
    }
    if (!didDrag.current) {
      setIsOpen((prev) => {
        const next = !prev;
        // Load history when opening the chat window
        if (next) {
          chat.loadHistory();
        }
        return next;
      });
    }
  };
```

- [ ] **Step 3: Run frontend type check**

Run: `cd /Users/bytedance/my_code/hr_agent/frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/chat/hooks/useChat.ts frontend/src/features/chat/components/ChatBubble.tsx
git commit -m "fix: lazy-load chat history on window open instead of mount

Moves session validation and history fetching from useChat's auto-mount
useEffect to an explicit loadHistory() method called when the user
opens the chat bubble. This eliminates 2 API calls that blocked page
rendering on every recruiter page load.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Update greeting and placeholder text (Fix Issue 2)

**Files:**
- Modify: `frontend/src/features/chat/components/ChatMessages.tsx:19-22`
- Modify: `frontend/src/features/chat/components/ChatInput.tsx:36`

**Interfaces:**
- Consumes: None (pure text change)
- Produces: None

- [ ] **Step 1: Replace empty-state text in `ChatMessages.tsx`**

Change line 21 from:
```
          输入指令开始，例如「帮我筛选前端开发岗位的简历」
```
to:
```
          👋 你好！我是 HR 智能助手，可以帮你查询岗位、筛选简历、评估候选人。有什么我能帮你的吗？
```

- [ ] **Step 2: Replace placeholder in `ChatInput.tsx`**

Change line 36 from:
```
          placeholder="输入指令，如「帮我筛选前端岗位简历」"
```
to:
```
          placeholder="问我任何招聘相关的问题…"
```

- [ ] **Step 3: Run frontend type check**

Run: `cd /Users/bytedance/my_code/hr_agent/frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/chat/components/ChatMessages.tsx frontend/src/features/chat/components/ChatInput.tsx
git commit -m "fix: replace command-style greeting with friendly chat prompt

ChatMessages empty state now shows a warm greeting. ChatInput
placeholder uses open-ended phrasing matching LLM natural conversation.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Fix incomplete candidate queries (Fix Issue 3)

**Files:**
- Modify: `backend/app/services/conversation/prompts.py:19-24`
- Modify: `backend/app/services/conversation/tools.py:257-269,369-376`

**Interfaces:**
- Consumes: None (prompt/tool docstring changes)
- Produces: None

- [ ] **Step 1: Add candidate query guidance to `HR_AGENT_SYSTEM_PROMPT` in `prompts.py`**

After the existing "工具使用策略" bullet `- 先查概览再深入：先 group_by=["status"] 看全局，再 filter 深入特定群体` (around line 23), add two new bullets:

```python
- 查询候选人列表时，默认不加 status/ai_decision filter，否则会遗漏已面试/已拒绝的候选人；只在用户明确要求特定状态时才加 filter
- 查询所有候选人时不传 filter 参数（或传 filter={}），让工具返回全部
```

- [ ] **Step 2: Add "all candidates" examples to `query_applications` docstring in `tools.py`**

In the `query_applications` docstring (around line 257–269), after the existing Examples, add:

```python
      - 查所有候选人: query_applications(job_code="J04217")
      - 查所有候选人(无过滤): query_applications(job_code="J04217", filter={})
```

- [ ] **Step 3: Add secondary sort to `query_applications` in `tools.py`**

After the existing sort logic (around lines 369–376), add a secondary `created_at desc` sort for `ai_score` sort to ensure stable ordering for NULL scores:

Change the sort block from:
```python
        sort_field = sort_by or "ai_score"
        if sort_field == "ai_score":
            if sort_order.lower() == "asc":
                query = query.order_by(Application.ai_score.asc().nullslast())
            else:
                query = query.order_by(Application.ai_score.desc().nullslast())
        else:
            query = query.order_by(Application.created_at.desc())
```

to:
```python
        sort_field = sort_by or "ai_score"
        if sort_field == "ai_score":
            if sort_order.lower() == "asc":
                query = query.order_by(Application.ai_score.asc().nullslast())
            else:
                query = query.order_by(Application.ai_score.desc().nullslast())
            # Secondary sort: stable order for equal/NULL ai_score
            query = query.order_by(Application.created_at.desc())
        else:
            query = query.order_by(Application.created_at.desc())
```

- [ ] **Step 4: Run mypy type check**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run mypy --strict app/`
Expected: No type errors

- [ ] **Step 5: Run existing tests**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run pytest tests/test_react_tools.py -v -k query_applications`
Expected: All tests pass (prompt/docstring changes don't affect test logic; sort change is additive)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/conversation/prompts.py backend/app/services/conversation/tools.py
git commit -m "fix: improve candidate query completeness

- Add prompt guidance: don't add status/ai_decision filter by default
- Add docstring examples for querying all candidates without filter
- Add secondary created_at desc sort for stable ordering with NULL ai_score

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Skip thinking messages in history recovery (Fix Issue 4)

**Files:**
- Modify: `backend/app/api/chat.py:176-178`

**Interfaces:**
- Consumes: None
- Produces: None

- [ ] **Step 1: Modify history skip logic in `get_chat_history`**

In `backend/app/api/chat.py`, change lines 176–178 from:
```python
            # Skip AI messages that are pure tool calls (no visible content)
            if tool_calls and not content:
                continue
```
to:
```python
            # Skip AI messages with tool_calls (intermediate reasoning steps)
            # These contain thinking text like "好的，我先查一下..." before
            # calling a tool — they should not appear as chat bubbles in history
            if tool_calls:
                continue
```

- [ ] **Step 2: Run mypy type check**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run mypy --strict app/`
Expected: No type errors

- [ ] **Step 3: Run existing chat API tests**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run pytest tests/test_chat_api_v2.py -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "fix: skip AI intermediate reasoning messages in chat history

Previously only pure tool-call messages (no content) were skipped.
Now all AI messages with tool_calls are skipped, preventing thinking
text like '好的，我先查一下...' from appearing as persistent
chat bubbles after page refresh.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run full backend type check**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run mypy --strict app/`
Expected: Success, no errors

- [ ] **Step 2: Run full backend test suite**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Run frontend type check**

Run: `cd /Users/bytedance/my_code/hr_agent/frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 4: Run frontend build**

Run: `cd /Users/bytedance/my_code/hr_agent/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Update skeleton.md if needed**

If any structural changes were made (new exports, changed interfaces), update `docs/skeleton.md` accordingly. For this change set:
- `useChat` return type now includes `loadHistory` — update the skeleton entry
- No other structural changes

- [ ] **Step 6: Commit**

```bash
git add docs/skeleton.md
git commit -m "docs: update skeleton for useChat loadHistory addition

Co-Authored-By: Claude <noreply@anthropic.com>"
```

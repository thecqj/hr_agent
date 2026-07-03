# HR Agent 问题修复 & 体验优化设计

> 日期：2026-07-03
> 范围：4 个 HR 端 bug 修复 / UX 改进

---

## 问题 1：「我的岗位」页面渲染慢

### 根因

`RecruiterLayout` 渲染 `<ChatBubble />`，`ChatBubble` 内的 `useChat()` 在 `useEffect` mount 时**无条件**发起 `getSession(savedId)` + `getHistory(savedId)` 两个串行网络请求恢复历史对话。即使聊天窗口未打开，这些请求也会在 HR 登录进入任何 recruiter 页面时触发，阻塞页面交互。

### 修复

**懒加载历史**：移除 `useChat` 中的自动 mount `useEffect`，改为导出 `loadHistory()` 方法。`ChatBubble` 在用户**实际打开聊天窗口**时才调用 `loadHistory()`。

**改动文件**：
- `frontend/src/features/chat/hooks/useChat.ts`
  - 删除第 290–319 行的 mount `useEffect`
  - 新增 `loadHistory` callback（包含原 `getSession` + `getHistory` 逻辑）
  - 返回值增加 `loadHistory`
- `frontend/src/features/chat/components/ChatBubble.tsx`
  - 在 `setIsOpen(true)` 时调用 `chat.loadHistory()`
  - 仅当 `sessionId` 为 null 且 `messages` 为空时触发加载

---

## 问题 2：聊天问候/提示文案不友好

### 根因

`ChatMessages.tsx` 空状态文案和 `ChatInput.tsx` placeholder 均为指令式表述，与 LLM 自然对话能力不匹配。

### 修复

| 位置 | 旧文案 | 新文案 |
|------|--------|--------|
| `ChatMessages.tsx:21` 空状态 | `输入指令开始，例如「帮我筛选前端开发岗位的简历」` | `👋 你好！我是 HR 智能助手，可以帮你查询岗位、筛选简历、评估候选人。有什么我能帮你的吗？` |
| `ChatInput.tsx:36` placeholder | `输入指令，如「帮我筛选前端岗位简历」` | `问我任何招聘相关的问题…` |

**改动文件**：
- `frontend/src/features/chat/components/ChatMessages.tsx`
- `frontend/src/features/chat/components/ChatInput.tsx`

---

## 问题 3：HR-Agent 只查到部分候选人

### 根因

两层问题：

1. **LLM 调用 `query_applications` 时传了不合适的 filter**：LLM 可能默认加 `filter={"status": "pending"}`，只查未审核的，遗漏了 `interview`/`rejected` 状态的候选人。这是 LLM 推理/prompt 约束问题。

2. **默认排序 `ai_score desc` + `nullslast`**：未评估候选人（`ai_score=NULL`）排到最后，若 LLM 传了小 `limit` 可能被截断。但默认 `limit=50` 通常够用，所以主因是 filter 问题。

### 修复

**1. Prompt 优化**（`prompts.py`）— 在 `HR_AGENT_SYSTEM_PROMPT` 的"工具使用策略"追加：

```
- 查询候选人列表时，默认不加 status/ai_decision filter（除非用户明确要求特定状态的候选人），否则会遗漏已面试/已拒绝的候选人
- 查询所有候选人时不传 filter 参数，让工具返回全部
```

**2. Tool docstring 优化**（`tools.py`）— 在 `query_applications` Examples 追加：

```python
- 查所有候选人: query_applications(job_code="J04217")
- 查所有候选人(显式无过滤): query_applications(job_code="J04217", filter={})
```

**3. 防御性排序改进**（`tools.py`）— `ai_score` 排序增加 `created_at desc` 作为次排序，确保 NULL score 记录不会被不稳定顺序导致意外截断：

```python
# 修改前
query = query.order_by(Application.ai_score.desc().nullslast())

# 修改后
query = query.order_by(Application.ai_score.desc().nullslast())
query = query.order_by(Application.created_at.desc())
```

**改动文件**：
- `backend/app/services/conversation/prompts.py`
- `backend/app/services/conversation/tools.py`

---

## 问题 4：思考过程作为回复气泡保留

### 根因

LangGraph `create_react_agent` 的 checkpoint 中保存了 AI 的中间推理消息，如：

```
AIMessage(content="好的，我先查一下相关的岗位信息。", tool_calls=[...])
```

后端 `get_chat_history`（`api/chat.py:177`）恢复历史时，跳过条件为 `if tool_calls and not content: continue`——只跳过**纯工具调用**消息。带文本+工具调用的中间消息不会被跳过，导致推理文本被当作对话历史恢复到前端。

**实时流中**：中间文本作为 `text_delta` 流出，但 `tool_start` 事件随后替换了 `assistantContent`，所以是一闪而过。**刷新/重新进入后**：历史恢复把这些中间文本永久显示为对话气泡。

### 修复

**后端历史恢复**（`api/chat.py`）— 修改跳过逻辑：

```python
# 旧：只跳过纯工具调用
if tool_calls and not content:
    continue

# 新：跳过所有带 tool_calls 的 AI 消息（中间推理步骤）
if tool_calls:
    continue
```

**实时流式保持不变** — 中间推理文本仍作为 `text_delta` 流出，保持"一闪而过"的实时体验。

**改动文件**：
- `backend/app/api/chat.py`

---

## 影响范围

| 问题 | 后端改动 | 前端改动 | 数据库/迁移 |
|------|---------|---------|------------|
| 1 页面渲染慢 | 无 | `useChat.ts`, `ChatBubble.tsx` | 无 |
| 2 问候文案 | 无 | `ChatMessages.tsx`, `ChatInput.tsx` | 无 |
| 3 候选人不全 | `prompts.py`, `tools.py` | 无 | 无 |
| 4 思考气泡 | `chat.py` | 无 | 无 |

无破坏性变更，无数据库迁移，向后兼容。

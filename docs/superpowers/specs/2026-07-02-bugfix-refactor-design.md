# HR-Agent Bug 修复与重构设计

日期: 2026-07-02

## 概述

五项修复：删除 `interview_quota` 字段、修复聊天记录丢失、删除 `is_active` 字段、删除 `context_entities` 字段、修复 Summary 生成错误。

---

## 1. 删除 interview_quota

### 背景

`interview_quota`（进面人数上限）是错误设计。AI 评估应仅基于 `ai_score` 固定阈值判断是否进面，无需人为设定人数上限。

### 筛选逻辑变更

**旧逻辑**（`screen_node` in `nodes.py`）：
- 有 quota → 取 top-N 候选人，cutoff = 第 N 名分数
- 无 quota → fallback 阈值 60 分

**新逻辑**：
- 固定阈值 `ai_score >= 60` → recommend
- `ai_score < 60` → reject
- `cutoff_score = 60`（用于 borderline 判定）

阈值从后端配置读取，无需前端输入。

### 变更清单

**后端**：

| 文件 | 变更 |
|------|------|
| `models/job.py` | 删除 `interview_quota` 列定义 |
| `schemas/job.py` | `JobCreateRequest`、`JobUpdateRequest`、`JobResponse` 删除字段 |
| `schemas/agent.py` | `EvaluateRequest` 删除 `interview_quota` |
| `services/agent/state.py` | `EvaluationState` 删除 `interview_quota_override` |
| `services/agent/nodes.py` | `collect_node` 不再读取 `job.interview_quota`；`screen_node` 简化为固定阈值 |
| `services/conversation/tools.py` | `trigger_evaluation` 删除 `interview_quota` 参数 |
| `api/jobs.py` | 不再序列化 `interview_quota` |
| `api/agent.py` | 不再传递 `interview_quota_override` |
| 新增 Alembic migration | `op.drop_column('jobs', 'interview_quota')` |

**前端**：

| 文件 | 变更 |
|------|------|
| `types/job.ts` | `Job` 和 `CreateJobPayload` 删除 `interview_quota` |
| `types/chat.ts` | `JobDetailCardData.job` 删除 `interview_quota` |
| `PostJobPage.tsx` | 删除"进面人数"表单字段及 Zod 验证 |
| `JobDashboardPage.tsx` | 删除表格列 |
| `JobDetailCard.tsx` | 删除 `进面 {job.interview_quota}`，改为仅 `编制 {job.head_count}` |

**测试**：更新 6 个引用 `interview_quota` 的测试文件，删除相关断言和 fixture 字段。

---

## 2. 聊天记录恢复 + 会话生命周期

### 问题

1. **刷新丢失**：`messages` 是纯 React `useState`，刷新后重置为 `[]`。`validateSession()` 仅在 `ChatBubble` 首次打开时触发。
2. **重新登录丢失**：`localStorage("chat-session-id")` 不与用户绑定，换账号可能串号。
3. **点击 "X" 关闭不彻底**：当前关闭仅收起窗口，session 仍然活跃，再次打开还是旧对话。

### 会话生命周期设计

```
打开聊天 → 创建 session (新 session_id)
    ↓
聊天中 → 刷新页面 → 同一 session_id → 从 checkpoint 恢复历史 ✅
    ↓
点击 "X" 关闭 → 清除 localStorage session_id → 下次打开 = 新 session_id → 全新对话
    ↓
登出 → 清除 localStorage session_id → 重新登录 = 新 session_id → 全新对话
```

**核心原则**：会话生命周期完全由 `session_id` 管理，无需 `is_active` 字段。同一个 `session_id` 就是同一个对话，新 `session_id` 就是新对话。

### 修复方案

**A. 刷新恢复**：`useChat` hook 初始化时，如果 localStorage 中有 `sessionId`，立即调用 `validateSession()`。用户打开聊天窗口时消息已加载完毕。

**B. 防止串号**：localStorage key 改为 `chat-session-id:{user_id}`，登出时清除当前用户的 key。

**C. 点击 "X" 关闭 = 结束对话**：
- 调用 `closeSession(sessionId)` 通知后端（可选，用于资源清理）
- 清除 localStorage 中的 `chat-session-id:{user_id}`
- 重置 `messages` 为空
- 下次打开自动生成新 `session_id`

**D. 登出清 session**：`authStore` 的 logout action 中清除 `chat-session-id:*` 相关 localStorage 条目。

### 变更清单

| 文件 | 变更 |
|------|------|
| `useChat.ts` | 初始化时自动 `validateSession()`；`saveSessionId`/`loadSessionId` key 绑定 `user_id` |
| `ChatBubble.tsx` | 移除 `hasValidated` 手动触发逻辑 |
| `ChatWindow.tsx` | 点击 "X" 时调用 `closeSession()` + 清除 localStorage + 重置状态 |
| `authStore.ts` | logout 时清除 `chat-session-id:*` localStorage |

---

## 3. 删除 is_active 字段

### 背景

`is_active` 字段当前用于：(1) 查找活跃会话、(2) 判断 `has_history`、(3) 跨 session 注入旧 summary。在新设计中，(3) 已删除，而 (1)(2) 完全由 `session_id` 管理：同一个 `session_id` → 有历史，新 `session_id` → 无历史。`is_active` 不再需要。

### 变更清单

| 文件 | 变更 |
|------|------|
| `models/conversation.py` | 删除 `is_active` 列定义及复合索引 `ix_conversations_user_active` |
| `api/chat.py` — `close_session` | 不再设置 `is_active = False`，简化为资源清理 |
| `api/chat.py` — `get_session` | 不再查询 `is_active`，改为通过 `session_id` 查找对话是否存在 |
| `api/chat.py` — `_run_conversation_stream` | 不再查询 `is_active` 查找旧对话注入 seed |
| 新增 Alembic migration | `op.drop_index('ix_conversations_user_active')` + `op.drop_column('conversations', 'is_active')` |

---

## 4. 删除 context_entities 字段

### 背景

`context_entities` 当前是死功能：没有任何工具或节点在对话中写回该字段，`state_result.values.get("context_entities")` 永远返回 None。唯一的数据来源是跨 session seed 注入（已决定删除）。删除 `context_entities` 可避免与 summary 的功能重叠和上下文膨胀风险。

### 变更清单

| 文件 | 变更 |
|------|------|
| `models/conversation.py` | 删除 `context_entities` 列定义 |
| `services/conversation/state.py` | `ConversationContext` 删除 `context_entities` 字段 |
| `api/chat.py` | 删除 `context_entities` 的读写代码（seed 注入、graph state 写回） |
| `services/conversation/prompts.py` | `build_state_modifier` 删除 `context_entities` 注入逻辑 |
| `services/conversation/graph.py` | 不再传递 `context_entities` |
| 新增 Alembic migration | `op.drop_column('conversations', 'context_entities')` |

---

## 5. 修复 Summary 功能

### 问题

1. **生成质量差**：所有对话 summary 为同一句错误内容
2. **触发时机不合理**：关闭时 >10 条、对话中 >20 条，逻辑分散
3. **跨 session 污染**：新对话注入旧 summary，AI 错误提及历史话题

### 数据架构

精简后的 `conversations` 表：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 用户外键 |
| session_id | String(36) | 会话标识（= LangGraph thread_id） |
| summary | Text | 每 10 轮滚动压缩摘要 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

全量消息历史存储在 LangGraph checkpoint 表（PostgreSQL），通过 `/api/chat/history` 读取。

### 修复方案

**A. 统一触发时机**：每 10 轮对话（20 条消息）触发一次滚动压缩，删除关闭时的独立摘要生成。

**B. 滚动压缩逻辑**（纯 Summary 方案）：

```
当消息数 > 20 时：
1. 取出当前 summary（可能为空）
2. 取出被裁掉的旧消息（除最近 20 条外的所有消息）
3. LLM 压缩: [旧 summary] + [被裁旧消息] → [新 summary]
4. 保存新 summary 到 Conversation.summary
```

每次压缩时将旧 summary 和被裁消息一起输入 LLM，生成新的单一 summary。信息量有界，不会膨胀。

**C. LLM 消息裁剪**：喂给 LLM 时只传最近 10 轮消息 + summary，而非全量消息。Checkpoint 仍存全量（用于历史查询），但 LLM 推理时不看超出 10 轮的旧消息。实现方式：在 graph 的消息预处理阶段截断。

**D. 删除跨 session 注入**：新对话创建时不注入 `seed_summary`，每个新对话从零开始。Summary 仅用于同一 session 内的消息压缩。

**E. 改进 summary 生成 prompt**：重写 `SUMMARIZE_SYSTEM_PROMPT`，加强信息保留指引和输出格式约束。

**F. 增加错误处理**：`summarize_conversation()` 生成失败时保留旧 summary 而非生成错误内容。

### 变更清单

| 文件 | 变更 |
|------|------|
| `chat.py` — `_run_conversation_stream` | 统一 summary 触发为每 10 轮；新对话不注入旧 summary；删除 `prev_conversation` 查询逻辑 |
| `chat.py` — `close_session` | 不再触发 summary 生成；简化为资源清理 |
| `prompts.py` | 重写 `SUMMARIZE_SYSTEM_PROMPT`；删除 `context_entities` 相关注入代码 |
| `deepseek.py` | 修复 `summarize_conversation()` 错误处理 |
| `services/conversation/graph.py` | `build_state_modifier` 中 summary 注入仅用于同一 session；增加消息截断逻辑（只传最近 10 轮 + summary） |

---

## 不在范围内

- 聊天窗口 UI 改造
- 对话历史列表页面（查看历史对话）

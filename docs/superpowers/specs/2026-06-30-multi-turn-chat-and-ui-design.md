# HR-Agent 多轮对话 & 小助手 UI 优化设计

> 日期：2026-06-30
> 状态：待实现

---

## 1. 概述

本次构建实现两个核心能力：

1. **多轮对话**：HR-Agent 可读取历史对话，结合上下文推断用户意图（如"筛选这些简历"→ 刚才讨论过的岗位）
2. **前端小助手 UI 优化**：最小化/关闭分离、拖动逻辑修复、气泡窗口联动

---

## 2. 后端 — 多轮对话架构

### 2.1 方案选型

**LangGraph Checkpoint + thread_id 复用 + 轻量 conversations 索引表**

- 运行时状态持久化靠 LangGraph Checkpoint（已有 AsyncPostgresSaver）
- 会话衔接靠 `conversations` 表（跨会话摘要/实体传递）
- thread_id 复用后 `pending_action` 自动跨轮存活，现有 confirm/cancel 流程无需额外修复

### 2.2 会话模型

前端维护 `session_id`（UUID，存 localStorage），每次发消息时通过请求带上。同一 session 下所有消息共享同一个 LangGraph `thread_id`。

| 用户行为 | session_id 变化 |
|----------|-----------------|
| 首次打开聊天 | 前端生成新 `session_id` |
| 正常对话 | `session_id` 不变 |
| 点 "—" 最小化 | `session_id` 不变，消息保留 |
| 点击气泡（窗口打开时） | `session_id` 不变，等同最小化 |
| 点 "X" 关闭 | 前端生成新 `session_id`，旧会话 `is_active=False` |
| 关闭浏览器再打开 | localStorage 中 `session_id` 仍在，恢复旧会话 |

### 2.3 conversations 表

```python
class Conversation(Base, TimestampMixin):       # table "conversations"
    user_id: Mapped[uuid.UUID]                   # FK → users.id, indexed
    session_id: Mapped[str]                      # unique, = LangGraph thread_id
    summary: Mapped[str | None]                  # Text, LLM 生成的会话摘要
    context_entities: Mapped[dict | None]        # JSONB, 结构化实体
    is_active: Mapped[bool]                      # default=True
```

索引：`(user_id, is_active)` 复合索引，用于快速查找用户当前活跃会话。

### 2.4 ConversationState 扩展

在现有 `ConversationState` 中新增字段：

```python
# 新增字段
chat_history: list[dict]          # 完整对话历史 [{role, content, cards_summary?, timestamp}]
session_summary: str | None       # LLM 生成的早期对话摘要
context_entities: dict            # 结构化实体 {current_job_id, current_job_code, current_candidate_name, ...}
```

### 2.5 上下文窗口策略

发送给意图识别 LLM 的内容 = **摘要段 + 结构化实体 + 最近 5 轮原文**

```
[系统提示]
[摘要] 之前对话的压缩摘要
[当前实体] 正在讨论的岗位: J10003 前端开发, 候选人: 张三
[最近5轮] user: ... / assistant: ...
[当前消息] user: 筛选这些简历
```

### 2.6 意图识别改造

`intent_node` 改造：
- 从 state 读取 `chat_history`、`session_summary`、`context_entities`
- 构建带上下文的 prompt，让 LLM 能推断指代（"这些简历" → 当前讨论的岗位）
- `extracted_params` 中缺失的参数优先从 `context_entities` 补全

### 2.7 各节点更新实体

每个查询/操作节点执行后，将关键结果写入 `context_entities`：

| 节点 | 更新的实体 |
|------|-----------|
| `list_jobs_node` | 无特定实体 |
| `job_detail_node` | `current_job_id`, `current_job_code` |
| `pending_count_node` | `current_job_id`, `current_job_code` |
| `interview_count_node` | `current_job_id`, `current_job_code` |
| `candidate_eval_node` | `current_candidate_name`, `current_job_id` |
| `funnel_node` | `current_job_id`, `current_job_code` |
| `candidate_list_node` | `current_job_id`, `current_job_code` |
| `status_change_node` | `current_candidate_name`, `current_job_id` |
| `dispatch_node` | `current_job_id`, `current_job_code`, `task_id` |

### 2.8 摘要生成策略

- **触发时机**：`feedback_node` 完成后，检查 `chat_history` 长度
- **阈值**：历史 > 10 轮时触发
- **压缩范围**：对前 5 轮（最旧的）生成摘要，保留最近 5 轮原文
- **LLM 调用**：用 DeepSeek 生成，prompt 要求保留关键实体（岗位、候选人、操作结果）
- **存储**：摘要写入 `Conversation.summary` + `ConversationState.session_summary`
- **会话关闭时**：无论历史长度，都生成最终摘要（确保 "X" 后新会话能拿到完整摘要）
- **摘要长度限制**：500 字以内，超出时递归压缩
- **摘要失败**：保留原始 `chat_history` 不压缩，下次重试，不影响当前回复

### 2.9 会话生命周期

```
用户打开聊天 → 前端有 session_id?
  ├── 有 → 发送 session_id 到后端
  │        后端查 conversations 表
  │        ├── 存在且 is_active=True → 继续该会话
  │        └── 不存在 → 创建新会话，查旧会话种子
  └── 无 → 后端生成新 session_id
           查该用户最近的 is_active=False 会话
           ├── 有 → 将其 summary + context_entities 作为新会话种子
           └── 无 → 全新空白会话

用户点 "X" 关闭 →
  1. 前端调 POST /api/chat/session/close
  2. 后端将当前会话 is_active=False
  3. 后端触发摘要生成（如果 chat_history 超过阈值）
  4. 前端生成新 session_id，清空消息

用户关闭浏览器 →
  session_id 在 localStorage，下次打开恢复旧会话
```

---

## 3. 后端 — API 变更

### 3.1 修改的端点

**`POST /api/chat/send`**

- Request body 新增 `session_id: str | None`
- 使用 `session_id` 作为 `thread_id`（不再每次生成新 UUID）
- SSE 流开头新增 `session` 事件：`{ session_id: "xxx" }`
- 前端首次无 session_id 时从该事件获取

### 3.2 新增的端点

**`POST /api/chat/session/close`**

- Request body：`{ session_id: str }`
- 将会话 `is_active` 设为 `False`
- 触发摘要生成（若历史 > 10 轮）
- 返回：`{ message: "会话已关闭" }`

**`GET /api/chat/session`**

- 查询参数：`session_id: str`（可选）
- 返回当前用户的活跃会话信息：`{ session_id, has_history: bool }`
- 若传入 `session_id`：检查该会话是否仍活跃，返回其状态
- 若未传入：返回该用户最近一条活跃会话
- 前端刷新页面后可调用，判断是否恢复旧会话

### 3.3 SSE 事件流变更

现有事件流不变，新增一个事件：

```
event: session
data: {"session_id": "uuid-xxx"}

event: thinking       ← 现有
data: {"status": "..."}

...（其余事件不变）
```

`session` 事件总是在流的最前面发出。

### 3.4 Schema 变更

```python
# chat.py 变更
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    session_id: str | None = None                    # 新增

# chat.py 新增
class SessionCloseRequest(BaseModel):
    session_id: str

class SessionResponse(BaseModel):
    session_id: str
    has_history: bool

class SessionEvent(BaseModel):
    session_id: str
```

---

## 4. 前端 — 小助手 UI 改造

### 4.1 窗口控制：最小化 + 关闭

**Header 区域**：

```
┌─────────────────────────────────────────┐
│  🤖 HR 智能助手         [ — ]  [ ✕ ]   │
└─────────────────────────────────────────┘
```

**"—" 最小化**：
- `setIsOpen(false)`，不触发任何清理
- 消息保留在 `useChat` 的 state 中
- 点气泡重新打开，消息完整恢复

**"✕" 关闭**：
- 弹出确认弹窗（shadcn Dialog）：
  > "关闭将清空当前对话记录，AI 仍会记住之前讨论的内容。确定关闭吗？"
  >
  > [取消]  [确定关闭]
- 确认后：
  1. 调用 `closeSession()`（POST `/api/chat/session/close`）
  2. 调用 `clearMessages()` 清空前端消息
  3. 生成新 `session_id`（存入 localStorage）
  4. `setIsOpen(false)` 关闭窗口

**气泡点击逻辑**：

| 窗口状态 | 点击气泡 |
|----------|---------|
| 窗口关闭 | 打开窗口 |
| 窗口打开 | 最小化（等同 "—"，消息保留） |

"X" 关闭只能通过窗口内按钮触发，避免误操作清空对话。

### 4.2 气泡拖动改造

**`useBubbleDrag()` 重写**：

| 行为 | 实现 |
|------|------|
| 自由拖动 | 同时追踪 dx 和 dy，更新 `left/right + top` |
| 水平吸附 | 松手后吸附到最近的左/右边缘（保持现有逻辑） |
| 垂直保持 | 松手后 top 值保持用户拖到的位置 |
| 仅 pointer 触发 | 拖动监听仅绑定在气泡元素上，不冒泡 |
| 文字选择不触发 | pointerdown 时检查 e.target 是气泡自身且 e.button === 0 |

状态持久化：localStorage 存 `{ side, offset, top }`（新增 `top`）

### 4.3 窗口跟随气泡移动

**核心规则**：
- 气泡拖动时 → 窗口跟随移动
- 窗口拖动时 → 只移动窗口，气泡不动
- 选择文字时 → 气泡和窗口都不动

**偏移量追踪**：
- 默认偏移：窗口在气泡正上方同侧
- 用户手动拖动窗口 → 记录新的偏移量（`windowPos - bubblePos`）
- 气泡再移动 → 按最新偏移量更新窗口位置

### 4.4 拖动互不干扰

| 操作 | 气泡 | 窗口 |
|------|------|------|
| 拖气泡 | 移动 | 跟随移动 |
| 拖窗口 header | 不动 | 移动 |
| 拖窗口 resize | 不动 | 调整大小 |
| 选择文字 | 不动 | 不动 |

**实现要点**：
- 气泡的 pointerdown 设 `stopPropagation()`，防止事件冒泡到窗口
- 窗口 header 的 pointerdown 设 `stopPropagation()`，防止冒泡到气泡
- 气泡拖动 hook 内部：只有 e.target 是气泡自身元素时才启动拖动
- 文字选择时用 `dx + dy > 5px` 的阈值过滤掉选择操作

---

## 5. 前端 — 数据流与状态管理

### 5.1 useChat Hook 改造

```typescript
interface UseChatReturn {
  messages: ChatMessage[]
  isProcessing: boolean
  sessionId: string | null
  sendMessage: (text: string) => Promise<void>
  disconnect: () => void
  clearMessages: () => void
  closeSession: () => Promise<void>    // 新增：调 /session/close + 清空 + 新 sessionId
}

// sessionId 管理
const [sessionId, setSessionId] = useState<string | null>(
  localStorage.getItem('chat-session-id')
)
```

### 5.2 sendChatMessage API 改造

```typescript
function sendChatMessage(
  message: string,
  sessionId: string | null,             // 新增
  onEvent: (type: string, data: any) => void,
  onError: (error: Error) => void,
  onDone: () => void
): AbortController
```

SSE 事件处理新增 `session` 类型：收到后更新 state + localStorage。

### 5.3 完整消息发送流程

```
用户输入 → useChat.sendMessage(text)
  ├─ 添加 user message 到 messages[]
  ├─ 读取 sessionId (from state / localStorage)
  └─ 调用 sendChatMessage(message, sessionId)
       ↓ POST /api/chat/send { message, session_id }

后端 send_chat_message()
  ├─ 查 conversations 表：session_id 存在？
  │   ├── 存在 → 恢复会话
  │   └── 不存在 → 创建新会话 + 查旧会话种子
  ├─ 用 session_id 作为 thread_id 调用 graph.astream_events()
  │   ├─ LangGraph 从 Checkpoint 恢复上一轮 state
  │   ├─ intent_node: 摘要 + 实体 + 最近5轮 + 当前消息 → LLM
  │   ├─ route_by_intent → 查询/操作节点
  │   ├─ 节点更新 context_entities
  │   ├─ feedback_node: 格式化回复 + 检查是否需要摘要压缩
  │   └─ State 自动写入 Checkpoint
  └─ SSE 流式返回事件
       session → thinking → intent → [progress] → result → done

前端 SSE 事件处理
  ├─ session: 存储 sessionId → state + localStorage
  ├─ thinking/intent/progress: 更新 assistant message 进度
  ├─ result: 更新 assistant message 最终内容 + cards
  └─ done: isProcessing = false
```

### 5.4 会话关闭流程

```
用户点 "X" → 弹窗确认
  ├─ 取消 → 什么都不做
  └─ 确定关闭
       ├─ POST /api/chat/session/close { session_id }
       │   后端: is_active=False + 生成最终摘要
       ├─ clearMessages() 清空前端消息
       ├─ 生成新 sessionId → state + localStorage
       └─ setIsOpen(false)
```

### 5.5 页面刷新/重新打开流程

```
用户刷新页面或关闭浏览器后重新打开
  ├─ localStorage 中有 sessionId
  ├─ 渲染气泡，气泡不自动打开窗口
  ├─ 用户点击气泡 → setIsOpen(true)
  │   ├─ messages 为空（内存状态丢失）
  │   ├─ GET /api/chat/session → 确认会话仍活跃
  │   │   ├── 活跃 → 用此 sessionId 继续
  │   │   └── 不活跃 → 生成新 sessionId
  │   └─ 后续 sendMessage 时，后端从 Checkpoint 恢复 state
  │       LLM 有摘要+实体上下文，可以自然接续对话
  └─ 前端消息列表为空——只显示新消息，不拉取历史
```

**关于历史消息恢复**：页面刷新后，前端消息列表为空（不主动拉取历史）。用户看到的是从刷新后开始的新消息，但 AI 后端有完整的上下文。这是有意为之——避免拉取历史带来延迟和复杂度，且 AI 的摘要+实体已足够保持上下文连贯。

---

## 6. 错误处理 & 边界情况

### 6.1 会话相关边界

| 场景 | 处理 |
|------|------|
| 前端 session_id 与后端不一致 | GET /api/chat/session 返回不活跃 → 前端生成新 session_id，不阻塞用户 |
| 用户在多标签页同时聊天 | 同一 session_id 的请求串行处理（LangGraph Checkpointer 自带锁），不会冲突 |
| session_id 对应的 Checkpoint 被清理 | 后端查不到 state → 当作新会话处理，用 conversations 表的摘要作为种子 |
| 摘要生成 LLM 失败 | 保留原始 chat_history 不压缩，下次重试。不影响当前回复 |

### 6.2 拖动相关边界

| 场景 | 处理 |
|------|------|
| 气泡拖到屏幕外 | top 值 clamp 到 [24, viewportHeight - 72]，气泡始终可见 |
| 窗口跟随气泡移出视口 | 窗口位置 clamp 到视口内，可能暂时脱离气泡对齐 |
| 窗口 resize 后比视口大 | 限制 max 尺寸不超过视口 90% |
| 用户快速连续拖气泡和窗口 | 每次 pointerdown 更新偏移量，以最后一次为准 |
| 触摸屏设备 | Pointer Events 同时覆盖鼠标和触摸，无需额外处理 |

### 6.3 多轮对话上下文边界

| 场景 | 处理 |
|------|------|
| 用户说"筛选这些简历"但从未提过岗位 | context_entities 中无 current_job_id → intent_node 返回 clarifying_question："请问您要筛选哪个岗位的简历？" |
| 用户跨会话引用（"上次那个岗位"） | 新会话的 session_summary 中包含岗位信息，LLM 可从摘要推断。若仍模糊 → 追问 |
| 对话过长导致摘要也很大 | 摘要限制 500 字以内，超出时递归压缩 |
| pending_action 跨轮存活后用户不再确认 | 下次用户发新消息时，feedback_node 检测到新意图 ≠ confirm/cancel → 自动清除 pending_action（现有逻辑已实现） |

### 6.4 确认弹窗边界

| 场景 | 处理 |
|------|------|
| 正在处理消息时点 "X" | 弹窗提示："对话正在进行中，确定关闭吗？"，确认后先 disconnect() 再走关闭流程 |
| 处理中点 "—" | 直接最小化，不中断处理。后台继续接收 SSE 事件，重新打开时消息已更新 |

---

## 7. 数据库迁移

新增 `conversations` 表，一个 Alembic 迁移文件：
- 创建 `conversations` 表及 `(user_id, is_active)` 复合索引
- 无需修改现有表

---

## 8. 变更文件预估

### 后端

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `app/models/conversation.py` | 新增 | Conversation ORM 模型 |
| `app/schemas/chat.py` | 修改 | ChatRequest 新增 session_id，新增 SessionCloseRequest/SessionResponse/SessionEvent |
| `app/services/conversation/state.py` | 修改 | 新增 chat_history, session_summary, context_entities 字段 |
| `app/services/conversation/prompts.py` | 修改 | intent prompt 支持上下文，新增摘要 prompt |
| `app/services/conversation/nodes.py` | 修改 | intent_node 改造，各节点更新实体，feedback_node 增加摘要逻辑 |
| `app/services/conversation/graph.py` | 无变更 | 路由逻辑不变 |
| `app/api/chat.py` | 修改 | session_id 参数，session/close 端点，session 查询端点，session SSE 事件 |
| `alembic/versions/xxx_add_conversations.py` | 新增 | conversations 表迁移 |

### 前端

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `features/chat/components/ChatBubble.tsx` | 修改 | 最小化逻辑，点击行为变更 |
| `features/chat/components/ChatWindow.tsx` | 修改 | 新增最小化按钮，关闭确认弹窗，header 改造 |
| `features/chat/hooks/useChat.ts` | 修改 | sessionId 管理，closeSession，session SSE 事件 |
| `features/chat/hooks/useDragResize.ts` | 修改 | useBubbleDrag 自由拖动+垂直，窗口跟随气泡，偏移量追踪 |
| `features/chat/api/chat.ts` | 修改 | sendChatMessage 新增 sessionId 参数，session/close API，GET /session API |
| `features/chat/types/chat.ts` | 修改 | 新增 session 相关类型 |

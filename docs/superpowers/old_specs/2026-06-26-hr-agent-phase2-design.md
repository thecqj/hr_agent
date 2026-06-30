# HR-Agent Phase 2 — 对话助手设计文档

> **阶段**：Phase 2 — HR-Agent 对话助手
> **日期**：2026-06-26
> **前置依赖**：Phase 1（智能招聘工作流）已完成

---

## 1. 目标与范围

### 目标

在招聘者端实现对话式交互入口，招聘者通过自然语言指令触发招聘工作流，并通过 SSE 流式推送获取实时进度反馈。

### 范围

| 包含 | 不包含 |
|------|--------|
| 对话 Agent（LangGraph ConversationGraph） | 多轮对话 / 上下文记忆（Phase 3） |
| LLM 意图识别 + 参数提取 | 意图微调分类模型 |
| SSE 流式进度推送 | WebSocket 双向通信 |
| EvaluationGraph 升级为真 LangGraph 执行 | 新增评估维度 / 评估逻辑变更 |
| LangGraph Checkpoint 持久化 | 断点续跑的自动恢复（仅保留能力） |
| 浮动聊天窗口（Copilot 风格） | 独立聊天页面 |
| 评估结果页面 + 确认流程 | 对话中直接确认 |
| 前端 ai_* 字段展示 | 求职者端 AI 相关展示 |

### 关键决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 服务架构 | 集成在同一 FastAPI 进程 | 与 Phase 1 一致，避免过早微服务化 |
| 对话 Agent 架构 | LangGraph ConversationGraph | 统一 Checkpoint + 流式事件，Phase 3 无缝扩展 |
| 评估工作流交互 | EvaluationGraph 作为子图 | 统一图架构，共享 Checkpointer |
| 意图识别 | LLM 意图识别 | 灵活，支持自然语言变化 |
| 交互模式 | 单轮指令式 | 复杂度后置，先跑通核心链路 |
| Chat UI | 浮动气泡窗口（Copilot 风格） | 不影响现有页面操作，随时可用 |
| 结果展示 | 聊天摘要卡片 + 跳转专属页面 | 简历多时不在聊天中堆砌 |
| 确认方式 | 结果页面直接确认 | 确认操作与审阅在同一页面完成 |
| 进度推送 | SSE（Server-Sent Events） | 架构简单，HTTP 原生支持，单向推送足够 |

---

## 2. 整体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                       FastAPI 进程                                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              ConversationGraph (LangGraph)                  │  │
│  │                                                             │  │
│  │  intent_node ──► dispatch_node ──► feedback_node ──► END   │  │
│  │                       │                                     │  │
│  │                       ▼ (subgraph call)                     │  │
│  │              ┌─────────────────────┐                        │  │
│  │              │  EvaluationGraph    │                        │  │
│  │              │  (真 LangGraph 执行)  │                        │  │
│  │              │                     │                        │  │
│  │              │  collect → evaluate │                        │  │
│  │              │  → screen → review  │                        │  │
│  │              │  → save_draft → END │                        │  │
│  │              └─────────────────────┘                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Checkpointer: AsyncPostgresSaver (共享)                          │
│  LLM Provider: DeepSeekProvider (共享，扩展意图识别方法)              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  /api/chat    │  │  /api/agent  │  │  /api/auth|jobs|apps  │  │
│  │  (Phase 2 新增)│  │  (Phase 1)   │  │  (既有)               │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. ConversationGraph 设计

### 3.1 对话状态

```python
class ConversationState(TypedDict, total=False):
    # 输入
    user_message: str                    # 用户原始消息
    current_user_id: str                 # 当前招聘者 ID

    # 意图识别输出
    intent: str                          # "evaluate" | "help" | "unknown"
    extracted_params: dict               # {"job_title": "...", "interview_quota": N, ...}

    # 工作流调用输出
    task_id: str | None                  # 评估任务 ID
    evaluation_status: str | None        # 任务最终状态

    # 反馈输出
    reply_message: str                   # 给用户的文本回复
    reply_cards: list[dict] | None       # 结构化卡片数据
    result_page_url: str | None          # 评估结果页面 URL

    # 错误
    errors: list[str]
```

### 3.2 图定义

```python
graph = StateGraph(ConversationState)
graph.add_node("intent", intent_node)
graph.add_node("dispatch", dispatch_node)
graph.add_node("feedback", feedback_node)

graph.add_edge(START, "intent")
graph.add_conditional_edges("intent", route_by_intent,
    {"evaluate": "dispatch", "help": "feedback", "unknown": "feedback"})
graph.add_edge("dispatch", "feedback")
graph.add_edge("feedback", END)

return graph.compile(checkpointer=checkpointer)
```

### 3.3 intent_node — 意图识别 + 参数提取

**输入**：`user_message`, `current_user_id`

**处理**：调用 `LLMProvider.recognize_intent()` 获取结构化意图。

**输出**：
```python
class IntentResult(BaseModel):
    intent: Literal["evaluate", "help", "unknown"]
    confidence: float          # 0-1 置信度
    extracted_params: dict     # evaluate 时包含 job_title, interview_quota 等
    clarifying_question: str | None  # confidence < 0.7 时的追问
```

**Prompt 设计要点**：
- 列出支持的意图类型和对应参数
- 要求返回 JSON，附带 `confidence` 字段
- 当 `confidence < 0.7` 时，生成 `clarifying_question`，`intent` 设为 `unknown`
- Few-shot 示例：
  - "帮我筛选前端开发岗位的简历" → `intent="evaluate", params={"job_title":"前端开发"}`
  - "前端岗位选 5 个人进面试" → `intent="evaluate", params={"job_title":"前端", "interview_quota":5}`
  - "你能做什么" → `intent="help"`

**条件路由**：
- `intent="evaluate"` → `dispatch_node`
- `intent="help"` → `feedback_node`（生成帮助文本）
- `intent="unknown"` → `feedback_node`（返回追问或默认提示）

### 3.4 dispatch_node — 任务路由

**输入**：`intent`, `extracted_params`, `current_user_id`

**处理**（evaluate 意图时）：

1. **岗位匹配**：
   - 若 `extracted_params` 包含 `job_id`，直接使用
   - 若包含 `job_title`，查询当前招聘者的 active 岗位列表，ILIKE 模糊匹配 `title`
   - 匹配到 0 个 → 写入 `reply_message`="未找到匹配岗位"，跳过子图
   - 匹配到多个 → 写入 `reply_message`="找到多个匹配岗位：[列表]，请指定"，跳过子图
   - 匹配到 1 个 → 继续执行

2. **进面人数**：
   - `extracted_params.interview_quota` 优先
   - 缺失时使用 Job 表的 `interview_quota`
   - 都无则默认不限（按 60 分阈值筛选）

3. **并发检查**：
   - 检查该岗位是否有 pending/running 的 EvaluationTask
   - 有 → 写入 `reply_message` + 现有 task_id 卡片，跳过子图

4. **执行评估子图**：
   - 通过 `agent_service.trigger_evaluation()` 创建 EvaluationTask 记录（状态 PENDING），获取 task_id
   - 调用 EvaluationGraph 子图（传入 job_id、triggered_by、task_id），子图执行完成后 task 自动更新状态
   - 子图完成后，task_id 和 evaluation_status 写入 ConversationState

**help 意图**：不进入此节点，直接路由到 feedback_node。

**unknown 意图**：不进入此节点，直接路由到 feedback_node。

### 3.5 feedback_node — 结果反馈

**输入**：`intent`, `reply_message`（可能已由 dispatch 设置）, `task_id`, `evaluation_status`, `errors`

**处理**：

- `evaluate` 成功时：
  ```
  reply_message: "✅ 已完成「前端开发」岗位的简历评估，共 12 份简历，推荐 5 人进入面试。"
  reply_cards: [{
    "type": "evaluation_summary",
    "task_id": "xxx",
    "job_title": "前端开发",
    "total_count": 12,
    "recommended_count": 5,
    "rejected_count": 7,
    "result_page_url": "/dashboard/evaluation/xxx"
  }]
  ```

- `evaluate` 失败时（岗位未找到、无简历等）：
  ```
  reply_message: "❌ 未找到匹配的「后端开发」岗位。您当前有以下活跃岗位：\n1. 前端开发\n2. 产品经理"
  ```

- `help` 意图：
  ```
  reply_message: "我可以帮您完成以下操作：\n• 筛选岗位简历 — 如「帮我筛选前端开发岗位的简历」\n• 指定进面人数 — 如「前端岗位选 5 人进面试」"
  ```

- `unknown` 意图：
  ```
  reply_message: clarifying_question 或 "抱歉，我没有理解您的意思。输入「帮助」查看我能做什么。"
  ```

---

## 4. EvaluationGraph 升级

### 4.1 从手动调用升级为真 LangGraph 图执行

**Phase 1 现状**：
```python
async def run_evaluation_workflow(state: EvaluationState, db: AsyncSession) -> EvaluationState:
    state = await collect_node(state, db)
    state = await evaluate_node(state, db)
    state = await screen_node(state, db)
    state = await review_node(state, db)
    state = await save_draft_node(state, db)
    return state
```

**Phase 2 升级**：
```python
def build_evaluation_graph(checkpointer: AsyncPostgresSaver) -> CompiledGraph:
    graph = StateGraph(EvaluationState)
    graph.add_node("collect", collect_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("screen", screen_node)
    graph.add_node("review", review_node)
    graph.add_node("save_draft", save_draft_node)

    graph.add_edge(START, "collect")
    graph.add_edge("collect", "evaluate")
    graph.add_edge("evaluate", "screen")
    graph.add_edge("screen", "review")
    graph.add_edge("review", "save_draft")
    graph.add_edge("save_draft", END)

    return graph.compile(checkpointer=checkpointer)
```

### 4.2 节点签名适配

LangGraph 节点函数签名改为 `node(state: EvaluationState) -> dict`，不再手动传入 `db`。DB 会话通过 `configurable` 传入：

```python
# 调用方
async for event in graph.astream_events(
    initial_state,
    config={
        "configurable": {
            "thread_id": str(task_id),
            "db": db_session,
        }
    },
    version="v2",
):
    ...

# 节点内部
async def collect_node(state: EvaluationState) -> dict:
    config = get_config()
    db: AsyncSession = config["configurable"]["db"]
    ...
    return {"job_info": ..., "applications": ...}  # 返回状态更新的 partial dict
```

### 4.3 Checkpoint 持久化

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 应用启动时初始化（FastAPI lifespan）
checkpointer = AsyncPostgresSaver.from_conn_string(DATABASE_URL)
await checkpointer.setup()  # 创建 checkpoint 表

# 图编译时注入
evaluation_graph = build_evaluation_graph(checkpointer)
conversation_graph = build_conversation_graph(checkpointer)
```

### 4.4 断点续跑能力

- `EvaluationTask` 记录关联的 `thread_id`（Phase 2 可在 result_summary 中存储）
- 恢复时通过 `graph.astream(None, config={"configurable": {"thread_id": thread_id}})` 续跑
- Phase 2 不实现自动恢复逻辑，仅保留架构能力

### 4.5 后台执行策略

保持 Phase 1 的 `asyncio.create_task()` 模式，但改用 `graph.astream_events()` 获取流式事件：

```python
async def _run_workflow_background(
    graph: CompiledGraph,
    initial_state: EvaluationState,
    task_id: str,
    db: AsyncSession,
    event_queue: asyncio.Queue,
) -> None:
    async for event in graph.astream_events(
        initial_state,
        config={"configurable": {"thread_id": task_id, "db": db}},
        version="v2",
    ):
        # 过滤并转发关键事件到 queue
        await event_queue.put(event)
```

---

## 5. SSE 流式推送 + Chat API

### 5.1 Chat API 端点

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/chat/send` | 必须（recruiter） | 发送消息，返回 SSE 流 |

**请求**：
```json
{
  "message": "帮我筛选前端开发岗位的简历"
}
```

**响应**：`text/event-stream`（SSE）

### 5.2 SSE 事件类型

| event | 触发时机 | data 内容 |
|-------|---------|----------|
| `thinking` | 开始意图识别 | `{"status": "正在理解您的指令..."}` |
| `intent` | 意图识别完成 | `{"intent": "evaluate", "params": {"job_title": "前端开发"}}` |
| `progress` | 评估进行中 | `{"status": "正在评估简历", "evaluated_count": 3, "total_count": 12}` |
| `error` | 出错 | `{"message": "...", "recoverable": true}` |
| `result` | 工作流完成或需反馈 | `{"reply_message": "...", "cards": [...]}` |
| `done` | 流结束 | `{}` |

### 5.3 SSE 事件流示例

```
event: thinking
data: {"status": "正在理解您的指令..."}

event: intent
data: {"intent": "evaluate", "params": {"job_title": "前端开发"}}

event: progress
data: {"status": "正在匹配岗位...", "job_title": "前端开发"}

event: progress
data: {"status": "正在评估简历", "evaluated_count": 3, "total_count": 12}

event: progress
data: {"status": "正在评估简历", "evaluated_count": 7, "total_count": 12}

event: progress
data: {"status": "正在筛选候选人..."}

event: result
data: {"reply_message": "✅ 已完成「前端开发」岗位的简历评估，共 12 份简历，推荐 5 人进入面试。", "cards": [{"type": "evaluation_summary", "task_id": "xxx", "job_title": "前端开发", "total_count": 12, "recommended_count": 5, "rejected_count": 7, "result_page_url": "/dashboard/evaluation/xxx"}]}

event: done
data: {}
```

### 5.4 流式事件来源

`ConversationGraph` 通过 `graph.astream_events()` 运行，在关键节点使用 `dispatch_custom_event()` 产出自定义事件：

```python
from langgraph.config import get_config, dispatch_custom_event

async def dispatch_node(state: ConversationState) -> dict:
    dispatch_custom_event("progress", {"status": "正在匹配岗位..."})
    # ... 匹配岗位逻辑
    dispatch_custom_event("progress", {"status": "正在评估简历...", "total_count": len(applications)})
    # ... 调用子图
    return {...}
```

Chat API 端点消费 `astream_events()` 输出，过滤 `on_custom_event` 事件，格式化为 SSE 推送。

### 5.5 Chat API 实现骨架

```python
@router.post("/chat/send")
async def send_chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    # 权限检查
    require_role("recruiter")(current_user)

    async def event_generator():
        try:
            initial_state = ConversationState(
                user_message=request.message,
                current_user_id=str(current_user.id),
            )
            async for event in conversation_graph.astream_events(
                initial_state,
                config={"configurable": {"thread_id": str(uuid4()), "db": db}},
                version="v2",
            ):
                if event["event"] == "on_custom_event":
                    name = event["name"]
                    data = event["data"]
                    yield f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                # 处理其他关键事件类型...
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e), 'recoverable': False})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 6. LLM Provider 扩展

### 6.1 新增意图识别方法

```python
class BaseLLMProvider(ABC):
    # ... 现有方法

    @abstractmethod
    async def recognize_intent(
        self,
        user_message: str,
        supported_intents: list[dict],
    ) -> IntentResult:
        """识别用户消息的意图和参数。"""
```

### 6.2 DeepSeek 实现

```python
class DeepSeekProvider(BaseLLMProvider):
    async def recognize_intent(
        self,
        user_message: str,
        supported_intents: list[dict],
    ) -> IntentResult:
        """调用 DeepSeek Chat API 做意图识别，要求 JSON 输出。"""
```

- 使用与 `evaluate_resume` 相同的 httpx AsyncClient 和重试逻辑
- System prompt 明确列出支持的意图和参数 schema
- Response format: `json_object`
- 低置信度时返回 `clarifying_question`

### 6.3 Intent 识别 Prompt 模板

```
你是一个 HR 招聘助手的意图识别模块。根据用户消息，判断其意图并提取参数。

支持的意图：
1. evaluate - 触发简历评估工作流
   参数：job_title (str, 岗位名称), job_id (str, 岗位ID，可选), interview_quota (int, 进面人数，可选)
2. help - 查询使用帮助
   参数：无
3. unknown - 无法识别的意图
   参数：clarifying_question (str, 追问)

规则：
- confidence 低于 0.7 时，intent 设为 unknown 并提供 clarifying_question
- 用户提到"筛选"、"评估"、"筛选简历"、"看简历"等均指向 evaluate
- 用户提到"帮助"、"能做什么"、"怎么用"等均指向 help

返回 JSON：
{
  "intent": "evaluate|help|unknown",
  "confidence": 0.0-1.0,
  "extracted_params": {...},
  "clarifying_question": "..." // 仅 unknown 时
}
```

---

## 7. Pydantic DTO（Chat 相关）

### `app/schemas/chat.py`

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="用户消息")

class ThinkingEvent(BaseModel):
    status: str

class IntentEvent(BaseModel):
    intent: str
    params: dict

class ProgressEvent(BaseModel):
    status: str
    evaluated_count: int | None = None
    total_count: int | None = None

class ErrorEvent(BaseModel):
    message: str
    recoverable: bool

class EvaluationSummaryCard(BaseModel):
    type: Literal["evaluation_summary"] = "evaluation_summary"
    task_id: str
    job_title: str
    total_count: int
    recommended_count: int
    rejected_count: int
    result_page_url: str

class ResultEvent(BaseModel):
    reply_message: str
    cards: list[EvaluationSummaryCard] | None = None

class IntentResult(BaseModel):
    intent: Literal["evaluate", "help", "unknown"]
    confidence: float = Field(ge=0, le=1)
    extracted_params: dict = Field(default_factory=dict)
    clarifying_question: str | None = None
```

---

## 8. 前端设计

### 8.1 浮动聊天窗口

**位置**：`RecruiterLayout` 内全局可用，右下角浮动气泡。

**组件层级**：
```
ChatBubble (入口组件，挂在 RecruiterLayout 中)
  ├─ ChatToggle          # 气泡按钮，点击展开/收起
  └─ ChatWindow          # 聊天窗口主体（约 380×520px）
       ├─ ChatHeader     # 标题 "HR 智能助手" + 收起按钮
       ├─ ChatMessages   # 消息列表（可滚动）
       │    ├─ UserMessage       # 用户消息气泡（右对齐）
       │    ├─ AssistantMessage  # 助手消息气泡（左对齐）
       │    │    ├─ TextContent    # 文本内容
       │    │    └─ CardContent    # 评估摘要卡片（可点击跳转）
       │    └─ ProgressMessage   # 进度指示消息
       └─ ChatInput        # 输入框 + 发送按钮
```

**交互行为**：
- 默认收起，点击气泡展开窗口
- 发送消息后，输入框禁用，显示"思考中..."动画
- SSE 事件逐步渲染：thinking → progress → result
- 评估摘要卡片可点击，跳转至结果页面（新路由）
- 发送期间不可再次发送（单轮指令式）
- 窗口收起后再展开，保留当前对话内容（内存状态，不持久化）
- 关闭/刷新页面后对话清空

### 8.2 评估结果页面

**路由**：`/dashboard/evaluation/:taskId`

**权限**：recruiter（需为任务触发者）

**组件**：
```
EvaluationResultPage
  ├─ ResultHeader        # 岗位名 + 评估概要统计（总人数 / 推荐 / 淘汰）
  ├─ CandidateTable      # 候选人评估列表（Table 组件）
  │    ├─ 列：姓名、AI总分、AI决策（badge）、维度评分（可展开行）、评估理由
  │    ├─ 每行决策下拉：保持AI建议 / 改为面试 / 改为淘汰
  │    └─ 覆盖决策时需填写理由（inline input，展开行内）
  ├─ ResultSummary       # 统计摘要卡片：总人数、推荐、淘汰、边界
  └─ ConfirmButton       # 底部固定"确认评估结果"按钮 → 调用 confirm API
```

**数据获取**：
- 页面加载时调用 `GET /api/agent/task/:taskId` 获取结果
- `result_summary` 包含完整评估数据

**确认逻辑**：
- 用户修改部分候选人决策后点"确认评估结果"
- 调用 `POST /api/agent/confirm/:taskId`，传入 `decisions` 数组
- 确认成功后显示 toast 提示，提供"返回申请人列表"链接

### 8.3 前端类型扩展

```typescript
// features/chat/types/chat.ts
interface ChatMessage {
  role: "user" | "assistant"
  content: string
  cards?: ChatCard[]
  progress?: ProgressInfo
  timestamp: number
}

interface ChatCard {
  type: "evaluation_summary"
  task_id: string
  job_title: string
  total_count: number
  recommended_count: number
  rejected_count: number
  result_page_url: string
}

interface ProgressInfo {
  status: string
  evaluated_count?: number
  total_count?: number
}

// features/applications/types/application.ts（扩展）
interface DimensionScore {
  name: string
  score: number
  weight: number
  reason: string
}

interface EvaluationDetail {
  application_id: string
  applicant_name: string
  ai_score: number
  ai_evaluation: DimensionScore[]
  ai_decision: "recommend" | "reject" | "neutral"
  ai_decision_reason: string
}

interface Applicant {
  // ... 现有字段
  ai_score?: number
  ai_evaluation?: DimensionScore[]
  ai_decision?: string
  ai_decision_reason?: string
  ai_evaluated_at?: string
}
```

### 8.4 新增 API 调用函数

```typescript
// features/chat/api/chat.ts
function sendChatMessage(message: string): EventSource

// features/applications/api/applications.ts（扩展）
function getEvaluationTask(taskId: string): Promise<TaskStatusResponse>
function confirmEvaluation(taskId: string, decisions: ConfirmDecision[]): Promise<ConfirmResponse>
```

### 8.5 Chat 状态管理

使用 React `useState` + `useRef` 管理聊天状态（不引入额外状态库，单轮指令式无需全局状态）：

```typescript
function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  function sendMessage(text: string) { ... }
  function handleSSEEvent(event: MessageEvent) { ... }
  function disconnect() { ... }

  return { messages, isProcessing, sendMessage, disconnect }
}
```

---

## 9. 错误处理与边界情况

### 9.1 后端错误场景

| 场景 | 处理方式 | SSE 事件 |
|-------|---------|----------|
| 意图无法识别 | 返回 `result` 事件，reply_message 为追问提示 | `result` (reply_message only) |
| 岗位未找到 | 返回文本提示 + 建议可用岗位列表 | `result` (reply_message only) |
| 多个岗位匹配 | 返回候选列表让用户指定 | `result` (reply_message only) |
| 岗位无 pending 申请 | 返回提示"该岗位暂无待处理简历" | `result` (reply_message only) |
| 岗位已有运行中任务 | 返回提示"该岗位正在评估中" + 现有 task_id 链接 | `result` (reply_message + card) |
| 岗位非 active 状态 | 返回提示"该岗位已关闭/草稿状态" | `result` (reply_message only) |
| LLM 调用失败 | 评估工作流内已有重试；全部失败则任务 FAILED | `error` + `result` |
| 非招聘者角色 | API 层 403 | HTTP 403 |
| 权限不足（非岗位拥有者） | API 层 403 | HTTP 403 |

### 9.2 前端错误场景

| 场景 | 处理方式 |
|-------|---------|
| SSE 连接断开 | 显示"连接中断，请重试"提示 + 重试按钮 |
| 评估结果页面 task 不存在 | 显示 ErrorState 组件 |
| 确认时任务状态非 completed | 显示 toast 提示 |
| 确认时部分决策无效 | 后端忽略无效项，返回实际更新数 |

### 9.3 数据一致性保障

- **任务并发控制**：保持 Phase 1 的 409 Conflict 策略——同一岗位同一时间只允许一个评估任务
- **Checkpoint 一致性**：LangGraph 的 AsyncPostgresSaver 保证状态写入的原子性
- **确认幂等性**：重复确认同一任务返回成功但不重复更新 Application 状态

---

## 10. 新增文件与修改清单

### 10.1 后端新增文件

| 文件 | 说明 |
|------|------|
| `app/services/conversation/__init__.py` | 对话 Agent 模块初始化 |
| `app/services/conversation/state.py` | `ConversationState` TypedDict |
| `app/services/conversation/graph.py` | `build_conversation_graph()`, `run_conversation()` |
| `app/services/conversation/nodes.py` | `intent_node`, `dispatch_node`, `feedback_node` |
| `app/services/conversation/prompts.py` | 意图识别 Prompt 模板 |
| `app/schemas/chat.py` | Chat API Pydantic DTO |
| `app/api/chat.py` | `/api/chat` 路由 |

### 10.2 后端修改文件

| 文件 | 变更 |
|------|------|
| `app/services/agent/graph.py` | 升级为真 LangGraph 图执行 + Checkpointer 注入 |
| `app/services/agent/nodes.py` | 适配 LangGraph 节点签名（db 通过 config 获取，返回 partial dict） |
| `app/services/agent_service.py` | 调整为通过 graph.astream 执行，支持流式事件 |
| `app/llm/base.py` | 新增 `recognize_intent()` 抽象方法 |
| `app/llm/deepseek.py` | 实现 `recognize_intent()` |
| `app/api/__init__.py` | 挂载 chat_router |
| `app/main.py` | 初始化 Checkpointer（lifespan event） |
| `app/config.py` | 新增 Checkpoint 相关配置（可选） |
| `requirements.txt` | 新增 `langgraph-checkpoint-postgres` 依赖 |

### 10.3 前端新增文件

| 文件 | 说明 |
|------|------|
| `src/features/chat/components/ChatBubble.tsx` | 浮动气泡入口组件 |
| `src/features/chat/components/ChatWindow.tsx` | 聊天窗口主体 |
| `src/features/chat/components/ChatMessages.tsx` | 消息列表 |
| `src/features/chat/components/ChatInput.tsx` | 输入框 + 发送按钮 |
| `src/features/chat/components/AssistantMessage.tsx` | 助手消息（含卡片） |
| `src/features/chat/components/ProgressMessage.tsx` | 进度指示消息 |
| `src/features/chat/components/EvaluationCard.tsx` | 评估摘要卡片 |
| `src/features/chat/api/chat.ts` | Chat API 调用函数 |
| `src/features/chat/hooks/useChat.ts` | 聊天状态管理 Hook |
| `src/features/chat/types/chat.ts` | Chat 类型定义 |
| `src/pages/EvaluationResultPage.tsx` | 评估结果页面 |

### 10.4 前端修改文件

| 文件 | 变更 |
|------|------|
| `src/features/applications/types/application.ts` | 扩展 `Applicant` 类型，增加 `ai_*` 字段 |
| `src/features/applications/api/applications.ts` | 新增 `getEvaluationTask`, `confirmEvaluation` |
| `src/features/applications/hooks/useApplications.ts` | 新增评估相关 hooks |
| `src/shared/constants/queryKeys.ts` | 新增 `evaluation` query keys |
| `src/App.tsx` | 新增 `/dashboard/evaluation/:taskId` 路由 |
| `src/shared/ui/layout/RecruiterLayout.tsx` | 集成 `ChatBubble` 组件 |

---

## 11. 依赖变更

### 后端新增依赖

| 包 | 用途 |
|----|------|
| `langgraph-checkpoint-postgres` | LangGraph PostgreSQL Checkpoint 持久化 |

注：`langgraph` 已在 Phase 1 安装。`sse-starlette` 或类似库可能用于 SSE 响应（FastAPI 内置 `StreamingResponse` 可满足基本需求，视实现情况决定是否引入）。

### 前端新增依赖

无。SSE 通过浏览器原生 `EventSource` API 或 `fetch` + `ReadableStream` 消费，无需额外库。

---

## 12. 测试策略

### 后端测试

| 测试文件 | 覆盖范围 | 预估用例数 |
|---------|---------|-----------|
| `test_conversation_nodes.py` | intent_node / dispatch_node / feedback_node 单元测试 | 8-10 |
| `test_conversation_graph.py` | ConversationGraph 端到端流程测试 | 3-4 |
| `test_chat_api.py` | Chat API SSE 流集成测试 | 5-6 |
| `test_evaluation_graph_upgrade.py` | 升级后的 EvaluationGraph 集成测试 | 3-4 |
| 更新 `test_agent_nodes.py` | 适配新节点签名的单元测试 | 调整现有用例 |

### 前端测试

Phase 2 前端以手动验证为主，不强制 E2E 测试。核心验证点：
- 浮动窗口展开/收起正常
- 发送消息后 SSE 事件正确渲染
- 评估摘要卡片点击跳转正确
- 评估结果页面数据展示正确
- 确认流程端到端可用

---

## 13. 风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM 意图识别准确率不足 | 误路由导致用户体验差 | Prompt 优化 + confidence 阈值兜底 + clarify 机制 |
| SSE 连接在代理/负载均衡下断开 | 进度推送中断 | 前端实现重连 + 降级到轮询（可选） |
| LangGraph Checkpoint 与现有事务冲突 | 数据不一致 | Checkpoint 使用独立连接，不与业务事务共享 |
| `astream_events()` API 变更 | 升级成本 | 锁定 langgraph 版本，关注 changelog |
| 浮动窗口在移动端体验差 | 不可用 | Phase 2 仅考虑桌面端，移动端后续优化 |

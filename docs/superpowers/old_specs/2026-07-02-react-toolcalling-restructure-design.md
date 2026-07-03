# HR Agent ReAct + Tool-Calling 重构设计

> 日期: 2026-07-02
> 状态: Draft

## 1. 动机与问题

当前 HR Agent 对话系统的架构是"意图分类器 + 硬编码路由 + 固定格式输出"：

```
用户消息 → LLM 分类为 14 种意图之一 → Python 硬编码路由到对应 node
→ node 内部固定查询 → Python f-string 拼接回复 → 固定 Card 渲染
```

**核心问题**：

1. **LLM 只当分类器用**：14 意图分类后 LLM 的职责结束，不参与推理、决策、回复生成
2. **查询能力固定**：每个 node 只能做一种固定查询，无法组合、无法按需调整
3. **回复僵硬**：格式由 Python 硬编码，用户无法指定表格/文字等展示偏好
4. **无法多步推理**：复杂问题（"待审里谁最合适"）需要先查数量再查详情，当前单次路由无法实现
5. **扩展成本高**：新查询需求 = 新 intent + 新 node + 新路由 + 新 Card

## 2. 设计目标

- LLM 成为推理中枢，自主决定查什么、怎么查、查几次
- 查询能力灵活：LLM 通过参数组合构造精准查询，而非从固定菜单选择
- 回复自然：LLM 根据用户需求和查询结果自行组织 Markdown 回复
- 权限安全：业务规则和行级权限在 Tool 层强制执行，LLM 无法绕过
- 评估图保留：5 节点评估流程不变，作为高延迟 Tool 被 Agent 调用

## 3. 架构概览

### 3.1 当前架构 vs 目标架构

```
当前:  StateGraph(14 nodes) + 条件路由 + 硬编码逻辑
目标:  create_react_agent(7 tools) + LLM 自主推理循环
```

### 3.2 整体流程

```
POST /api/chat/send (SSE)
  │
  ▼
chat.py: _run_conversation_stream()
  │
  ├── 加载/创建 Conversation 行
  ├── 注入上下文 (session_summary, context_entities)
  │
  ▼
create_react_agent(
    model = ChatOpenAI(model="deepseek-chat"),
    tools = [query_jobs, query_applications, query_evaluation,
             trigger_evaluation, confirm_evaluation,
             update_candidate_status, update_job_status],
    checkpointer = AsyncPostgresSaver,
    state_modifier = build_state_modifier(state)
)
  │
  ├── LLM 推理 → 选择 Tool / 直接回复
  │     │
  │     ├─ Tool call → 执行 → Observation → LLM 继续推理
  │     │                          │
  │     │              ┌───────────┴───────────┐
  │     │              │ 通用查询 Tool          │ 评估 Tool
  │     │              │ filter→SQL→结果        │ 内嵌评估图
  │     │              │ 权限自动过滤           │ 进度冒泡 SSE
  │     │              └───────────┬───────────┘
  │     │                          │
  │     │         LLM 继续推理 ←──┘
  │     │         (信息够吗？需要换个 filter 再查吗？)
  │     │
  │     └─ 不需要 Tool → 直接生成 Markdown 回复
  │
  ▼
SSE events → 前端渲染
```

## 4. Tool 设计

### 4.1 设计原则

- **查询 Tool 是接口不是报表**：Tool 接受灵活参数组合，返回原始数据，LLM 自行组织呈现
- **写操作 Tool 封装业务语义**：权限校验和业务规则在 Tool 内部强制执行
- **Tool 描述即文档**：LLM 通过 Tool 的 description 和参数描述理解能力边界

### 4.2 通用查询 Tool（3 个）

#### query_jobs

```python
@tool
async def query_jobs(
    filter: dict | None = None,
    fields: list[str] | None = None,
    limit: int = 20,
) -> str:
    """查询岗位数据。

    filter 可包含任意组合:
      - job_code: 岗位编号（精确匹配，优先使用）
      - keyword: 关键词（模糊匹配标题）
      - status: 岗位状态 ("active", "closed", "draft")
      - work_type: 工作类型 ("remote", "onsite", "hybrid")
      - salary_min / salary_max: 薪资范围

    fields 指定返回字段，默认: ["job_code", "title", "status", "head_count", "applications_count"]
    可选字段: description, requirements, skills_required, salary_min, salary_max,
    location, work_type, interview_quota, recruiter_name

    只返回当前用户有权限查看的岗位（招聘者只看自己的岗位）。

    Examples:
      - 查所有活跃岗位: query_jobs(filter={"status": "active"})
      - 按编号查: query_jobs(filter={"job_code": "J04217"})
      - 模糊搜索: query_jobs(filter={"keyword": "前端"})
      - 带详情: query_jobs(filter={"job_code": "J04217"},
                   fields=["job_code","title","requirements","skills_required"])
    """
```

#### query_applications

```python
@tool
async def query_applications(
    job_code: str | None = None,
    job_title: str | None = None,
    filter: dict | None = None,
    fields: list[str] | None = None,
    group_by: list[str] | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    limit: int = 50,
) -> str:
    """查询投递/候选人数据。

    必须指定岗位（job_code 或 job_title）。

    filter 可包含:
      - status: 投递状态 ("pending", "interview", "rejected", "hired")
      - ai_decision: AI 决策 ("recommend", "reject")
      - candidate_name: 候选人姓名（模糊匹配）
      - min_ai_score / max_ai_score: AI 评分范围

    fields 指定返回字段，默认: ["candidate_name", "ai_score", "ai_decision", "status"]
    可选字段: ai_evaluation, ai_decision_reason, resume_summary,
    cover_letter, structured_resume

    group_by: 按字段分组统计人数
      - ["status"]: 各投递状态人数（招聘漏斗）
      - ["ai_decision"]: 各 AI 决策人数
      - ["status", "ai_decision"]: 交叉分组

    sort_by: 排序字段，默认 "ai_score"
    sort_order: "desc" 或 "asc"

    只返回当前用户有权限查看的投递数据。

    Examples:
      - 漏斗概览: query_applications(job_code="J04217", group_by=["status"])
      - 推荐候选人 Top5: query_applications(job_code="J04217",
          filter={"ai_decision": "recommend"},
          sort_by="ai_score", limit=5)
      - 被拒高分: query_applications(job_code="J04217",
          filter={"ai_decision": "reject", "min_ai_score": 70},
          sort_by="ai_score")
      - 某人评估详情: query_applications(job_code="J04217",
          filter={"candidate_name": "张三"},
          fields=["ai_score", "ai_evaluation", "ai_decision_reason"])
    """
```

#### query_evaluation

```python
@tool
async def query_evaluation(
    job_code: str | None = None,
    task_id: str | None = None,
) -> str:
    """查询评估任务的状态和结果。

    可通过 task_id 直接查询，或通过 job_code 查找岗位最近的评估任务。
    返回: 任务状态、进度(evaluated_count/total_count)、评估摘要
    (推荐/拒绝人数、截止分数、边界调整等)。

    只返回当前用户有权限查看的评估任务。
    """
```

### 4.3 写操作 Tool（4 个）

#### trigger_evaluation

```python
@tool
async def trigger_evaluation(
    job_code: str | None = None,
    job_title: str | None = None,
    interview_quota: int | None = None,
) -> str:
    """对岗位触发 AI 简历评估。

    评估过程可能需要数分钟，会实时报告进度。
    评估完成后候选人获得 AI 评分和推荐/拒绝决策，
    但不会自动变更状态——需调用 confirm_evaluation 确认。

    ⚠️ 评估是耗时操作，触发前应确认用户意图。

    Args:
        job_code: 岗位编号（优先使用）
        job_title: 岗位名称（模糊匹配，job_code 优先）
        interview_quota: 面试人数上限，覆盖岗位默认设置
    """
```

**内部实现**：
1. `resolve_job()` 解析岗位（job_code > job_title 模糊匹配）
2. 权限校验（当前用户是否为岗位所有者）
3. 并发检查（是否已有 PENDING/RUNNING 任务）
4. 创建 EvaluationTask 记录
5. 内嵌运行评估图 `ainvoke()`，进度通过 `adispatch_custom_event` 冒泡
6. 返回评估结果摘要文本

#### confirm_evaluation

```python
@tool
async def confirm_evaluation(
    task_id: str,
) -> str:
    """确认评估结果，按 AI 建议批量更新候选人状态。

    评估完成后需确认才会实际变更候选人状态
    (pending → interview 或 rejected)。

    ⚠️ 写操作，执行前必须向用户确认！

    Args:
        task_id: 评估任务 ID
    """
```

#### update_candidate_status

```python
@tool
async def update_candidate_status(
    job_code: str,
    candidate_name: str,
    target_status: str,
) -> str:
    """变更候选人状态（推进面试/拒绝等）。

    ⚠️ 写操作，执行前必须向用户确认！

    Args:
        job_code: 岗位编号
        candidate_name: 候选人姓名
        target_status: 目标状态，"interview" 或 "rejected"
    """
```

#### update_job_status

```python
@tool
async def update_job_status(
    job_code: str,
    target_status: str,
) -> str:
    """变更岗位状态（开启/关闭等）。

    ⚠️ 写操作，执行前必须向用户确认！

    Args:
        job_code: 岗位编号
        target_status: 目标状态，"active" 或 "closed"
    """
```

### 4.4 写操作确认机制

采用双层保证：

**Layer 1 - System Prompt 约束**：
System prompt 明确要求"写操作必须确认"。LLM 在收到写操作指令时会先输出确认文本（如"确定要将张三推进到面试吗？"），等待用户明确同意后再调用 Tool。

**Layer 2 - Tool 层防御**（安全网）：
即使 LLM 误直接调用了写操作 Tool，Tool 内部可以检查是否经过确认上下文，未确认时返回提示而非执行变更。

不再使用 `pending_action` + `confirm_node` 硬编码机制。

### 4.5 权限保障

所有 Tool 内部强制执行行级权限：

- 查询 Tool：自动添加 `WHERE recruiter_id = current_user_id` 或等效过滤
- 写操作 Tool：校验资源所有权，非所有者返回权限错误
- 字段过滤：Tool 只返回白名单中的字段，敏感字段（如 password_hash）不可达

LLM 无法通过参数绕过这些限制。

### 4.6 参数安全性

`filter` 参数为 `dict` 类型，LLM 传入的 key 和 value 必须在 Tool 内部做白名单校验：

- **Key 白名单**：Tool 实现中定义允许的 filter key 集合（如 `query_applications` 只接受 `status`, `ai_decision`, `candidate_name`, `min_ai_score`, `max_ai_score`），未知 key 静默忽略
- **Value 校验**：枚举值校验（status 只接受 `pending`/`interview`/`rejected`/`hired`），数值范围校验
- **参数化查询**：所有 filter 参数通过 SQLAlchemy 参数化查询拼接，禁止字符串拼接 SQL，杜绝注入风险
- **行级权限**：所有查询自动附加 `recruiter_id = current_user_id` 条件，LLM 无法通过 filter 绕过

## 5. System Prompt 设计

```python
HR_AGENT_SYSTEM_PROMPT = """你是智能简历投递系统的 AI 助手，帮助招聘者管理岗位和筛选简历。

## 你的能力
你有查询和操作工具，可以灵活组合获取信息、分析数据、执行操作。

## 核心原则
1. **理解后再行动**：仔细分析用户需求，必要时追问澄清，而非急于调用工具
2. **按需查询**：根据任务构造精准查询参数（filter + fields），避免返回大量无关数据
3. **多步推理**：一个复杂问题可能需要多次查询——先看概览，再深入细节
4. **自然组织回复**：用 Markdown（表格、列表等）清晰呈现，给出建议而非仅罗列数据
5. **写操作必须确认**：涉及状态变更（推进面试、拒绝候选人、关闭岗位、确认评估等），必须先向用户确认意图和细节，用户明确同意后再执行
6. **善用上下文**：对话中提到的岗位、候选人等，后续可直接引用，无需用户重复

## 工具使用策略
- 优先使用 job_code（如 J04217）定位岗位，比岗位名称更精确
- 需要概览时用 group_by，需要明细时用 fields 指定字段
- 先查概览再深入：先 group_by=["status"] 看全局，再 filter 深入特定群体
- 触发评估前确认岗位有待审核简历
- 评估完成后主动分析关键发现（高分候选人、边界候选人等）

## 回复格式
- 使用中文回复
- 数据展示优先使用 Markdown 表格
- 数字和比例并用（如"5人（50%）"）
- 给出建议而非仅罗列事实
"""
```

## 6. 上下文注入

`state_modifier` 动态构建，将 session_summary 和 context_entities 注入 system prompt：

```python
def build_state_modifier(state: dict) -> str:
    parts = [HR_AGENT_SYSTEM_PROMPT]
    if state.get("session_summary"):
        parts.append(f"\n## 对话摘要\n{state['session_summary']}")
    if state.get("context_entities"):
        lines = [f"- {k}: {v}" for k, v in state["context_entities"].items() if v]
        if lines:
            parts.append("\n## 当前对话上下文\n" + "\n".join(lines))
    return "\n".join(parts)
```

## 7. SSE 事件流适配

### 7.1 事件序列变化

| 事件 | 变化 | 说明 |
|------|------|------|
| `session` | 不变 | 首个事件，发送 session_id |
| `thinking` | **移除** | create_react_agent 无此阶段 |
| `intent` | **移除** | 不再有意图分类步骤 |
| `tool_start` | **新增** | Tool 开始执行 |
| `progress` | 保留 | 评估 Tool 内部 adispatch_custom_event 冒泡 |
| `tool_end` | **新增** | Tool 执行完毕 |
| `text_delta` | **新增** | LLM 流式输出 token（可选增强） |
| `result` | 不变 | 最终 LLM 回复（Markdown 文本） |
| `done` | 不变 | 流结束 |

### 7.2 事件映射实现

```python
async for event in agent.astream_events(input, config, version="v2"):
    kind = event["event"]

    if kind == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        if chunk.tool_call_chunks:
            # LLM 正在生成 tool_call
            pass
        elif chunk.content:
            # LLM 流式文本输出 → emit text_delta
            await emit_sse("text_delta", {"content": chunk.content})

    elif kind == "on_tool_start":
        await emit_sse("tool_start", {"tool": event["name"]})

    elif kind == "on_tool_end":
        await emit_sse("tool_end", {"tool": event["name"]})

    elif kind == "on_custom_event":
        if event["name"] == "progress":
            await emit_sse("progress", event["data"])

# graph 完成后
final_state = await agent.aget_state(config)
final_message = final_state.values["messages"][-1].content
await emit_sse("result", {"reply_message": final_message})
await emit_sse("done", {})
```

### 7.3 评估图进度冒泡

评估图每个 node 内部的 `adispatch_custom_event("progress", ...)` 会通过 `astream_events()` 的 `on_custom_event` 自然冒泡，无需额外处理。

### 7.4 历史压缩

graph 执行完毕后，在 `_run_conversation_stream()` 中检查消息长度。超过 20 条消息时，调用 `summarize_conversation()` 压缩最早的一半为摘要，更新 Conversation 行。

## 8. LLM 提供商升级

### 8.1 当前 → 升级

```python
# 当前: 手动 httpx 调用 + response_format: json_object
# 升级: 使用 langchain-openai 的 ChatOpenAI，原生支持 tool_call

from langchain_openai import ChatOpenAI

chat_model = ChatOpenAI(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL,
    temperature=0.3,
)
```

DeepSeek Chat API 兼容 OpenAI 格式，`ChatOpenAI` 天然支持 `bind_tools()` 和 tool_call 解析。

### 8.2 两套模型实例共存

- **对话 Agent**：`ChatOpenAI`（tool_call 模式），用于 create_react_agent
- **评估图**：保持当前 `DeepSeekProvider`（纯 JSON 模式），evaluate_resume / review_borderline 不变

互不影响，渐进迁移。

### 8.3 新增依赖

```
langchain-openai  # ChatOpenAI + tool_call 支持
```

## 9. 前端适配

### 9.1 本次不变

- ChatCard 体系保留但暂不使用
- 回复以纯 Markdown 文本呈现
- ConfirmCard 等结构化 UI 后续迭代

### 9.2 SSE 事件处理变化

useChat hook 需要适配新的事件类型：

| 新事件 | 前端行为 |
|--------|---------|
| `tool_start` | 更新 assistant 消息为"正在查询..." |
| `tool_end` | 更新 assistant 消息状态 |
| `text_delta` | 逐步拼接 assistant 消息内容（流式） |
| `progress` | 保持当前行为（spinner + 计数） |

移除 `thinking` 和 `intent` 事件的处理。

## 10. 文件结构变更

### 新增

```
backend/app/services/conversation/
├── tools.py          # 7 个 Tool 定义
├── prompts.py        # HR_AGENT_SYSTEM_PROMPT + build_state_modifier
├── graph.py          # create_react_agent 构建逻辑
└── __init__.py
```

### 删除

```
conversation/state.py    # ConversationState TypedDict 不再需要
conversation/nodes.py    # 14 个硬编码 node 全部删除
```

### 修改

```
api/chat.py              # SSE 事件映射适配
config.py                # 新增 CHAT_MODEL 配置
requirements.txt         # 新增 langchain-openai
```

### 不变

```
services/agent/          # 评估图 5 节点流程完全不变
services/job_service.py  # 被 Tool 内部调用
services/application_service.py  # 被 Tool 内部调用
models/                  # ORM 模型不变
schemas/chat.py          # SSE schema 不变（新增事件类型）
```

## 11. 删除的概念

| 概念 | 原因 |
|------|------|
| `IntentResult` schema | 不再需要意图分类，LLM 自主选择 Tool |
| `route_by_intent` / `route_by_pending_action` | 不再需要硬编码路由 |
| `confirm_node` / `cancel_node` / `execute_action` | 不再需要 pending_action 机制 |
| `feedback_node` | LLM 自己生成回复 |
| `thinking` / `intent` SSE 事件 | create_react_agent 无此阶段 |
| `PendingAction` TypedDict | 确认流由 LLM 自主判断 |

## 12. 保留的概念

| 概念 | 说明 |
|------|------|
| `context_entities` | 注入 system prompt 作为对话上下文 |
| `session_summary` | 历史压缩摘要，注入 system prompt |
| 评估图 5 节点流程 | 作为 trigger_evaluation Tool 内部实现 |
| SSE 事件流 | 保留 session/progress/result/done，新增 tool_start/tool_end/text_delta |
| Conversation 表 + checkpoint 持久化 | 会话管理和状态持久化不变 |
| 评估图中的 DeepSeekProvider | evaluate_resume / review_borderline 不变 |

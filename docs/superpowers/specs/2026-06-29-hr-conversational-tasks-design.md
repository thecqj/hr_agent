# HR-Agent 对话式业务任务扩展设计

> 日期：2026-06-29
> 状态：已审批
> 范围：Phase 3 — 扩展对话式任务覆盖面

## 1. 背景与目标

HR-Agent 当前对话能力仅支持简历筛选（`evaluate` 意图）和通用帮助（`help`/`unknown`）。本设计将对话能力扩展至 HR 日常业务中的 9 项高频任务，使招聘人员可通过自然语言完成岗位查询、候选人管理、招聘进度跟踪等操作。

**目标**：
- 招聘人员通过对话即可完成常见的 HR 查询和操作
- 操作类任务通过二次确认机制防止误操作
- 查询结果通过卡片化展示提升信息可读性
- 改动最小化，复用现有对话图和服务层

## 2. 任务清单

### 查询类（7 项）

| # | 意图 ID | 描述 | 示例 |
|---|---------|------|------|
| 1 | `list_jobs` | 岗位列表查询 | "现在有哪些活跃岗位？" |
| 2 | `job_detail` | 岗位详情查询 | "J001 的任职要求是什么？" |
| 3 | `pending_count` | 待审核简历计数 | "J001 还有多少简历没看？" |
| 4 | `interview_count` | 面试中候选人计数 | "J001 有几个人在面试？" |
| 5 | `candidate_eval` | 候选人 AI 评估结果 | "张三的评估结果是什么？" |
| 6 | `funnel` | 招聘漏斗/进度概览 | "J001 的招聘进度怎么样？" |
| 7 | `candidate_list` | 候选人列表查询 | "J001 AI 推荐的候选人有哪些？" |

### 操作类（2 项，需二次确认）

| # | 意图 ID | 描述 | 示例 |
|---|---------|------|------|
| 8 | `status_change` | 候选人状态变更 | "把张三推进到面试阶段" |
| 9 | `job_status` | 岗位发布/关闭 | "帮我关闭 J001" |

### 兜底意图

| 意图 ID | 描述 |
|---------|------|
| `evaluate` | 简历筛选（已有） |
| `help` | 帮助（已有） |
| `unknown` | 未识别意图兜底（已有） |
| `confirm` | 用户确认执行操作（新增） |
| `cancel` | 用户取消操作（新增） |

## 3. 构建方案：单意图扩展

在现有 LangGraph 对话图基础上，将意图枚举从 3 个扩展至 14 个（含原有 `evaluate`、`help`、`unknown`，新增 9 个业务意图，及 `confirm`、`cancel` 两个确认流意图），每个意图对应一个处理节点。

**选择理由**：
- 9 个新意图数量可控，LLM 分类准确率不会明显下降
- 与现有架构完全对齐，改动最小、风险最低
- 操作类意图通过 `pending_action` 字段实现二次确认
- 后续如果意图增长到 15+，可迁移至两级意图路由

## 4. 意图体系 & 参数提取

### 参数定义

| 意图 ID | 提取参数 |
|---------|---------|
| `list_jobs` | `status_filter`: active/closed/all（默认 active） |
| `job_detail` | `job_code` 或 `job_title`，`detail_scope`: full/responsibilities/requirements/skills/quota（默认 full） |
| `pending_count` | `job_code` 或 `job_title` |
| `interview_count` | `job_code` 或 `job_title` |
| `candidate_eval` | `candidate_name` 或 `application_id`，`job_code`（可选，用于消歧） |
| `funnel` | `job_code` 或 `job_title` |
| `candidate_list` | `job_code` 或 `job_title`，`decision_filter`: recommended/all（默认 recommended） |
| `status_change` | `candidate_name` 或 `application_id`，`target_status`: interview/rejected，`job_code`（消歧） |
| `job_status` | `job_code` 或 `job_title`，`action`: open/close |

### 参数提取策略

参数提取与意图识别合并为一次 LLM 调用（沿用现有 `recognize_intent` 方法），不在意图识别后再做一次参数提取。`INTENT_SYSTEM_PROMPT` 中明确定义每个意图的参数 schema。

### 岗位定位消歧

统一处理流程：
1. 优先匹配 `job_code`（精确）
2. 其次模糊匹配 `job_title`（LLM 提取的关键词 → 数据库 LIKE 查询）
3. 匹配到多个结果时，返回消歧问题让用户选择
4. 匹配不到时，反馈未找到

## 5. Conversation Graph 扩展

### 新图结构

```
START → intent_node → route_by_intent →
  list_jobs?      → list_jobs_node       → feedback_node → END
  job_detail?     → job_detail_node      → feedback_node → END
  pending_count?  → pending_count_node   → feedback_node → END
  interview_count → interview_count_node → feedback_node → END
  candidate_eval? → candidate_eval_node  → feedback_node → END
  funnel?         → funnel_node          → feedback_node → END
  candidate_list? → candidate_list_node  → feedback_node → END
  status_change?  → confirm_node         → (confirm? → status_change_node → feedback_node) / (cancel? → feedback_node) → END
  job_status?     → confirm_node         → (confirm? → job_status_node → feedback_node) / (cancel? → feedback_node) → END
  evaluate?       → dispatch_node        → feedback_node → END
  help/unknown?   → feedback_node        → END
```

### 节点职责统一化

每个新节点遵循相同模式：
1. 从 `ConversationState` 读取 `extracted_params`
2. 调用对应的 service 层方法
3. 将结果写入 `state["reply_message"]` 和 `state["reply_cards"]`
4. 如果参数不足，写入 `state["clarifying_question"]` 并走 feedback 路径

### 操作类确认机制

写操作（`status_change`、`job_status`）先进入 `confirm_node`：
- `confirm_node` 生成确认消息，将待执行操作保存至 `state["pending_action"]`
- 用户回复"确认"时，`intent_node` 识别为 `confirm`，从 `pending_action` 恢复操作上下文并执行
- 用户回复"取消"时，`intent_node` 识别为 `cancel`，取消操作并反馈
- **边界情况**：当 `pending_action` 不为空且用户输入非确认/取消时，优先处理新意图并清除 `pending_action`（即用户发出新指令视为隐式取消待确认操作），feedback_node 中附加提示"已取消待确认操作"

### ConversationState 扩展

```python
class ConversationState(TypedDict, total=False):
    # 现有字段保持不变
    user_message: str
    current_user_id: int
    intent: str
    extracted_params: dict[str, Any]
    clarifying_question: str | None
    task_id: int | None
    evaluation_status: str | None
    reply_message: str
    reply_cards: list[dict[str, Any]]
    result_page_url: str | None
    errors: list[str]
    # 新增字段
    pending_action: dict[str, Any] | None  # 待确认操作：{"intent": str, "params": dict}
```

## 6. 响应卡片体系

### 卡片类型

| 卡片类型 | 用途 | 展示内容 |
|---------|------|---------|
| `EvaluationSummaryCard` | 简历筛选结果 | 已有 |
| `JobListCard` | 岗位列表 | 岗位代码、岗位名称、状态标签、编制人数 |
| `JobDetailCard` | 岗位详情 | 岗位全信息，可折叠分区（职责/要求/技能/编制） |
| `FunnelCard` | 招聘漏斗 | 各阶段数量 + 百分比，CSS 漏斗可视化 |
| `CandidateListCard` | 候选人列表 | 姓名、AI评分、AI决定、当前状态 |
| `ConfirmCard` | 操作确认 | 操作描述文本 + 确认/取消按钮 |

### 卡片与意图映射

| 意图 | 回复形式 | 卡片 |
|------|---------|------|
| `list_jobs` | 卡片 | `JobListCard` |
| `job_detail` | 卡片 | `JobDetailCard` |
| `pending_count` | 纯文本 | 无 |
| `interview_count` | 纯文本 | 无 |
| `candidate_eval` | 纯文本 | 无 |
| `funnel` | 卡片 | `FunnelCard` |
| `candidate_list` | 卡片 | `CandidateListCard` |
| `status_change` | 纯文本（确认+结果） | `ConfirmCard`（确认阶段） |
| `job_status` | 纯文本（确认+结果） | `ConfirmCard`（确认阶段） |
| `evaluate` | 卡片 | `EvaluationSummaryCard`（已有） |
| `help`/`unknown` | 纯文本 | 无 |

## 7. Service 层 & 数据查询

### 复用现有 Service

| 意图 | 依赖 Service | 调用方法 |
|------|-------------|---------|
| `list_jobs` | `job_service` | `list_jobs(recruiter_id, status_filter)` — 需扩展支持 status 过滤 |
| `job_detail` | `job_service` | `get_job(job_id)` — 已有 |
| `pending_count` | `application_service` | `count_by_job_and_status(job_id, "pending")` — 需新增 |
| `interview_count` | `application_service` | `count_by_job_and_status(job_id, "interview")` — 需新增 |
| `candidate_eval` | `application_service` | `get_application(app_id)` — 已有 |
| `funnel` | `application_service` | `count_by_job_grouped_by_status(job_id)` — 需新增 |
| `candidate_list` | `application_service` | `list_by_job(job_id, decision_filter)` — 需新增 |
| `status_change` | `application_service` | `update_application_status(app_id, new_status)` — 已有 |
| `job_status` | `job_service` | `update_job_status(job_id, action)` — 已有 |

### 需新增的 Service 方法（3 个）

```python
# application_service.py
async def count_by_job_and_status(job_id: int, status: str) -> int:
    """统计某岗位指定状态的申请数量"""

async def count_by_job_grouped_by_status(job_id: int) -> dict[str, int]:
    """按状态分组统计某岗位的申请数量，返回 {"pending": N, "interview": M, "rejected": K}"""

async def list_by_job(job_id: int, decision_filter: str | None = None) -> list[Application]:
    """列出某岗位的申请，可选按 AI decision 过滤"""
```

### 岗位定位辅助方法

```python
# job_service.py
async def resolve_job(
    recruiter_id: int,
    job_code: str | None = None,
    job_title_keyword: str | None = None,
) -> Job | list[Job] | None:
    """精确匹配 job_code，或模糊匹配 job_title。
    返回: 单个 Job / 多个候选列表(需消歧) / None(未找到)"""
```

## 8. SSE 事件流 & 前端适配

### SSE 事件流

沿用现有事件类型，无需新增：

| 事件 | 所有新意图中的使用 |
|------|------------------|
| `thinking` | 所有意图 |
| `intent` | 所有意图（扩展意图名展示） |
| `progress` | 可选，用于耗时操作 |
| `result` | 所有意图（文本 + 卡片） |
| `error` | 所有意图 |
| `done` | 所有意图 |

### ChatMessage 类型扩展

```typescript
type ChatCard =
  | { type: "evaluation_summary"; ... }       // 已有
  | { type: "job_list"; jobs: JobItem[] }
  | { type: "job_detail"; job: JobDetail }
  | { type: "funnel"; stages: FunnelStage[] }
  | { type: "candidate_list"; candidates: CandidateItem[] }
  | { type: "confirm"; action: string; params: Record<string, any> }
```

### 前端组件树变化

```
ChatMessages
  └── AssistantMessage
        ├── 文本回复（现有）
        └── 卡片区域
              ├── EvaluationCard（已有）
              ├── JobListCard（新增）
              ├── JobDetailCard（新增）
              ├── FunnelCard（新增）
              ├── CandidateListCard（新增）
              └── ConfirmCard（新增）
```

### ConfirmCard 交互

- 显示操作描述文本（如"确认将候选人 张三 推进到面试阶段？"）
- 两个按钮：确认 / 取消
- 点击确认 → 发送"确认"消息 → 触发 `confirm` 意图 → 执行操作
- 点击取消 → 发送"取消"消息 → 触发 `cancel` 意图 → 取消操作
- 也支持用户直接在输入框回复"确认"/"取消"

## 9. 文件变更清单

### 后端

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `backend/app/schemas/chat.py` | 修改 | 新增卡片 DTO 类型 |
| `backend/app/services/conversation/state.py` | 修改 | 新增 `pending_action` 字段 |
| `backend/app/services/conversation/prompts.py` | 修改 | 扩展意图枚举和参数 schema |
| `backend/app/services/conversation/nodes.py` | 修改 | 新增 9 个处理节点 + confirm/cancel 路由 |
| `backend/app/services/conversation/graph.py` | 修改 | 扩展路由条件，新增节点注册 |
| `backend/app/services/job_service.py` | 修改 | 新增 `resolve_job`、扩展 `list_jobs` status 过滤 |
| `backend/app/services/application_service.py` | 修改 | 新增 3 个查询方法 |
| `backend/app/llm/base.py` | 修改 | 扩展 `IntentResult` schema |
| `backend/app/llm/deepseek.py` | 修改 | 适配扩展后的 `recognize_intent` |

### 前端

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `frontend/src/features/chat/types.ts` | 修改 | 扩展 ChatCard 类型 |
| `frontend/src/features/chat/components/JobListCard.tsx` | 新增 | 岗位列表卡片 |
| `frontend/src/features/chat/components/JobDetailCard.tsx` | 新增 | 岗位详情卡片 |
| `frontend/src/features/chat/components/FunnelCard.tsx` | 新增 | 招聘漏斗卡片 |
| `frontend/src/features/chat/components/CandidateListCard.tsx` | 新增 | 候选人列表卡片 |
| `frontend/src/features/chat/components/ConfirmCard.tsx` | 新增 | 操作确认卡片 |
| `frontend/src/features/chat/components/AssistantMessage.tsx` | 修改 | 注册新卡片渲染 |

## 10. 不在本次范围内

- 批量操作（如"把所有推荐候选人都推进到面试"）
- 评估任务状态查询（通过独立 API 已可查）
- 重新评估（重新跑 AI 筛选）
- 跨岗位对比（流程未完善，无法比较进度）
- 长期记忆系统
- 多轮对话上下文管理（Phase 3 后续）

# Phase 1 设计文档：智能招聘评估工作流

> 日期：2026-06-24
> 状态：已确认
> 基于：HR_Agent_Explore.md 第一阶段规划

---

## 1. 概述

Phase 1 实现 HR-Agent 的核心工作流：**简历智能评估 → 候选人筛选 → 人工审核确认**。招聘者触发后，系统自动对岗位下所有待处理申请进行 LLM 评估、排序筛选和边界复评，结果以草稿形式暂存，经招聘者确认后更新申请状态。

### 关键决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 部署架构 | 集成到现有 FastAPI 后端 | 项目规模小，避免微服务复杂度 |
| LLM 提供商 | DeepSeek（首个实现） | 已有 API key，支持结构化输出 |
| Phase 1 范围 | 仅后端核心工作流 | 最小可验证单元，风险最低 |
| 评估模型 | 固定维度 + LLM 动态权重 | 平衡灵活性和可解释性 |
| 人机协作 | 默认人工审核 | 安全优先，AI 结果需确认后生效 |
| 工作流引擎 | LangGraph | 为 Phase 2/3 对话式多 Agent 做铺垫 |
| 集成方式 | 异步 Task 模式 | 不阻塞 API，无额外依赖（无 Redis） |
| 筛选策略 | 排序 + LLM 复评边界 | 确定性强，成本可控 |

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                现有 FastAPI 后端（同一进程）                │
│                                                          │
│  ┌─────────────────────┐  ┌──────────────────────────┐  │
│  │  现有业务 Router      │  │  Agent Router (新增)      │  │
│  │  /api/auth           │  │  /api/agent               │  │
│  │  /api/jobs           │  │    POST /evaluate/{job_id}│  │
│  │  /api/applications   │  │    GET  /task/{task_id}   │  │
│  └──────────┬──────────┘  │    POST /confirm/{task_id} │  │
│             │              └──────────┬───────────────┘  │
│             │                         │                  │
│             ▼                         ▼                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Service Layer                           │   │
│  │  ┌────────────┐  ┌────────────────────────────┐  │   │
│  │  │ 现有服务     │  │ AgentService (新增)         │  │   │
│  │  │ auth/job/   │  │  - trigger_evaluation()    │  │   │
│  │  │ application │  │  - get_task_status()       │  │   │
│  │  └────────────┘  │  - confirm_evaluation()     │  │   │
│  │                   └─────────┬──────────────────┘  │   │
│  │                             │                      │   │
│  │                   ┌─────────▼──────────────────┐  │   │
│  │                   │  LangGraph Workflow          │  │   │
│  │                   │  (evaluate_applicants graph) │  │   │
│  │                   │                              │  │   │
│  │                   │  ┌─ collect ──────────┐      │  │   │
│  │                   │  ├─ evaluate_resume ×N│      │  │   │
│  │                   │  ├─ screen (排序)     │      │  │   │
│  │                   │  ├─ review (LLM 复评) │      │  │   │
│  │                   │  └─ save_draft_results│      │  │   │
│  │                   └──────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  LLM Provider (抽象层)                        │   │   │
│  │  │  - BaseLLMProvider (接口)                     │   │   │
│  │  │  - DeepSeekProvider (首个实现)                 │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                             │                              │
│                             ▼                              │
│                    PostgreSQL (共享)                        │
│  - 现有表 + evaluation_tasks (新)                           │
│  - LangGraph Checkpoint 表 (新)                            │
└─────────────────────────────────────────────────────────────┘
```

### 设计原则

1. **Agent 代码物理隔离**：`backend/app/services/agent/` 独立目录，不侵入现有业务代码
2. **DB 直连**：工作流通过 SQLAlchemy session 直接读写数据，不走 HTTP 自调用
3. **异步 Task**：`POST /evaluate/{job_id}` 立即返回 `task_id`，工作流在 `asyncio.create_task` 后台执行
4. **Checkpoint 持久化**：LangGraph 用 PostgreSQL 做 Checkpoint，进程崩溃可恢复
5. **人工审核关口**：评估结果先写入草稿字段（`ai_*` 前缀），招聘者确认后才更新 `Application.status`

---

## 3. 数据模型

### 3.1 现有"幽灵字段"处理

数据库中存在但 ORM 模型已移除的字段：
- `applications.match_score` (Float) → **复用**，重命名为 `ai_score`
- `applications.ai_suggestions` (Text) → **删除**，结构化评估结果由 `ai_evaluation` JSONB 替代

### 3.2 新增字段：`applications` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `ai_score` | Float | 复用原 `match_score`，AI 综合评分 (0-100) |
| `ai_evaluation` | JSONB | 结构化评估结果（各维度评分 + 权重 + 理由） |
| `ai_decision` | String(20) | AI 建议决策：`recommend` / `reject` / `neutral` |
| `ai_decision_reason` | Text | AI 决策理由 |
| `ai_evaluated_at` | DateTime | 评估时间 |

### 3.3 新增字段：`jobs` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `interview_quota` | Integer, nullable | 面试人数上限，null 表示不限 |

### 3.4 新增表：`evaluation_tasks`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 任务 ID |
| `job_id` | UUID (FK → jobs) | 关联岗位 |
| `triggered_by` | UUID (FK → users) | 触发者（招聘者） |
| `status` | Enum | `pending` → `running` → `completed` / `failed` |
| `total_count` | Integer | 待评估简历总数 |
| `evaluated_count` | Integer | 已评估数量 |
| `result_summary` | JSONB | 评估结果摘要（推荐/淘汰人数等） |
| `error_message` | Text | 失败时的错误信息 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

### 3.5 `ai_evaluation` JSONB 结构

```json
{
  "dimensions": [
    {
      "name": "技能匹配",
      "score": 85,
      "weight": 0.35,
      "reason": "掌握 React/Vue/TypeScript 等核心技术栈..."
    },
    {
      "name": "经验相关性",
      "score": 70,
      "weight": 0.30,
      "reason": "3年前端经验，但有1年空窗期..."
    },
    {
      "name": "学历达标",
      "score": 90,
      "weight": 0.15,
      "reason": "985 计算机本科，符合要求"
    },
    {
      "name": "综合印象",
      "score": 75,
      "weight": 0.20,
      "reason": "项目经验丰富但缺乏大型团队协作经验..."
    }
  ],
  "weighted_total": 79.25,
  "model_used": "deepseek-chat",
  "evaluated_at": "2026-06-24T10:30:00Z"
}
```

### 3.6 ORM 迁移策略

1. 新建 Alembic 迁移：`rename match_score → ai_score` + 新增 `ai_evaluation`、`ai_decision`、`ai_decision_reason`、`ai_evaluated_at`
2. 删除已废弃的 `ai_suggestions` 列
3. 新增 `jobs.interview_quota` 列
4. 新建 `evaluation_tasks` 表
5. LangGraph Checkpoint 表由 LangGraph 自动创建（或通过迁移脚本）

---

## 4. LangGraph 工作流

### 4.1 图结构

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   collect   │  获取岗位下所有 pending 申请
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  evaluate   │  逐份评估简历（LLM × N）
                    │  (per-app)  │  输出多维评分 + 加权总分
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   screen    │  按加权总分排序，取 Top N 进面
                    │  (纯排序)   │  无需 LLM，确定性操作
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   review    │  LLM 复评边界候选人
                    │             │  检查进面名单有无不该进的
                    │             │  检查淘汰名单有无该进未进的
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ save_draft  │  写入 ai_* 草稿字段
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │     END     │
                    └─────────────┘
```

### 4.2 Graph State

```python
class EvaluationState(TypedDict):
    # 输入
    job_id: str
    triggered_by: str
    task_id: str

    # 收集阶段产出
    job_info: dict              # 岗位信息
    applications: list[dict]    # 待评估的申请列表（含 structured_resume）

    # 评估阶段产出
    evaluation_results: list[dict]  # 每份简历的评估结果
    evaluated_count: int            # 已评估数量（用于进度更新）

    # 筛选阶段产出
    screening_result: dict      # 排序结果 + cutoff_score

    # 复评阶段产出
    review_adjustments: list[dict]  # 边界候选人调整

    # 错误处理
    errors: list[str]           # 累积的错误信息
```

### 4.3 节点详细设计

**1. `collect` 节点**
- 通过 DB session 查询 `Job`（含 skills_required）和 `Application`（status=pending）
- 校验：岗位存在 + 有 pending 申请 + 调用者是岗位 owner
- 更新 `evaluation_tasks` 状态为 `running`
- 若无 pending 申请，设置 error 并跳转到 END

**2. `evaluate` 节点（循环执行）**
- 每次取一份 application，将 structured_resume + job_info + 评估维度提示词发给 LLM
- LLM 返回结构化 JSON：各维度评分 + 权重 + 理由 + 建议决策
- 校验 LLM 输出格式（Pydantic schema 验证），格式错误则重试一次
- 更新 `evaluation_tasks.evaluated_count`（供前端轮询进度）
- 将结果追加到 `evaluation_results`
- 遇到 LLM 调用失败：记录错误，跳过该份简历，继续下一份
- 每次调用后 `asyncio.sleep(0.5)`，避免触发 LLM rate limit

**3. `screen` 节点（纯排序，无 LLM）**
- 按加权总分降序排列所有评估结果
- 取 Top `interview_quota` 名为 `recommend`，其余为 `reject`
- 若 `interview_quota` 为 null，则设分数线（≥60 分 recommend，<60 reject）
- 输出：`recommend_list` + `reject_list` + `cutoff_score`（进面最低分）

**4. `review` 节点（LLM 复评）**

边界候选人定义：
- 进面名单中分数较低的（cutoff_score ± `LLM_BORDERLINE_RANGE` 分范围内的候选人）
- 即进面名单中靠近分数线的 + 淘汰名单中靠近分数线的

LLM 复评输入：
- 岗位要求
- 进面名单中边界候选人的评估摘要
- 淘汰名单中边界候选人的评估摘要

LLM 复评输出：
- 对每个边界候选人的调整建议：`keep`（维持原决策）或 `adjust`（修改决策 + 理由）

设计要点：
- 边界范围通过 `LLM_BORDERLINE_RANGE` 配置（默认 ±10 分）
- LLM 只看边界候选人，控制 token 消耗
- 复评结果只调整边界候选人，高分进面和低分淘汰不受影响
- 复评调整会覆盖 `screen` 步骤的初始决策

**5. `save_draft` 节点**
- 遍历最终决策结果，将每份申请的：
  - `ai_score`、`ai_evaluation`、`ai_decision`、`ai_decision_reason`、`ai_evaluated_at` 写入 Application 表
  - **不更新** `Application.status`（等招聘者确认）
- 更新 `evaluation_tasks` 状态为 `completed`，写入 `result_summary`

---

## 5. LLM 集成层

### 5.1 Provider 抽象

```python
class BaseLLMProvider(ABC):
    """LLM 提供商统一接口"""

    @abstractmethod
    async def evaluate_resume(
        self,
        job_info: dict,
        structured_resume: dict,
        dimensions: list[str],
    ) -> ResumeEvaluation:
        """评估单份简历，返回结构化结果"""
        ...

    @abstractmethod
    async def review_borderline(
        self,
        job_info: dict,
        borderline_recommend: list[dict],
        borderline_reject: list[dict],
        cutoff_score: float,
    ) -> list[BorderlineReview]:
        """复评边界候选人"""
        ...
```

### 5.2 DeepSeekProvider

首个实现选用 DeepSeek，理由：
- 已有 API key，可立即开发测试
- 支持 JSON Mode 结构化输出
- 中文能力强，适合简历评估场景

其他 Provider（Doubao、Qwen）后续按需实现，只需继承 `BaseLLMProvider`。

### 5.3 结构化输出 Pydantic Schema

```python
class DimensionScore(BaseModel):
    name: str              # 维度名称
    score: float           # 0-100
    weight: float          # 0-1，LLM 动态分配
    reason: str            # 评估理由

class ResumeEvaluation(BaseModel):
    dimensions: list[DimensionScore]
    weighted_total: float  # 加权总分
    suggestion: Literal["recommend", "reject", "neutral"]
    summary: str           # 一句话总结

class BorderlineReview(BaseModel):
    application_id: str
    action: Literal["keep", "adjust"]
    new_decision: Literal["recommend", "reject"] | None = None
    reason: str
```

### 5.4 输出校验与重试

- LLM 输出 → Pydantic 解析
- 解析失败 → 重试 1 次（附带格式纠正提示）
- 仍失败 → 跳过该简历，记录错误

### 5.5 评估维度

固定 4 个维度，LLM 根据岗位特点动态调整权重：

| 维度 | 含义 | 典型权重范围 |
|------|------|-------------|
| 技能匹配 | 候选人技能与岗位要求的匹配程度 | 0.25-0.40 |
| 经验相关性 | 工作经验与岗位职责的相关程度 | 0.20-0.35 |
| 学历达标 | 学历背景是否符合岗位要求 | 0.10-0.20 |
| 综合印象 | 项目深度、成长潜力、稳定性等 | 0.15-0.25 |

LLM 在评估时自行决定各维度权重，但要求权重之和 = 1.0。

### 5.6 Prompt 设计要点

- **角色设定**：你是一位资深 HR 顾问，擅长技术岗位简历评估
- **输入格式**：岗位要求（结构化）+ 简历（structured_resume JSON）
- **输出约束**：严格按 JSON Schema 输出，不要解释格式
- **偏见抑制**：明确要求不基于性别、年龄、婚育状态做评判
- **评分校准**：提示词中包含评分基准（如"90+ 仅限极优秀，60 以下有明显不足"）

---

## 6. API 端点

### 6.1 新增路由：`/api/agent/*`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/agent/evaluate/{job_id}` | Required (recruiter + owner) | 触发评估工作流，返回 task_id |
| GET | `/api/agent/task/{task_id}` | Required (recruiter) | 查询任务进度和结果 |
| POST | `/api/agent/confirm/{task_id}` | Required (recruiter + owner) | 确认评估结果，更新 Application 状态 |

### 6.2 端点详细设计

**POST `/api/agent/evaluate/{job_id}`**

```python
class EvaluateRequest(BaseModel):
    interview_quota: int | None = None  # 可覆盖岗位设定

class EvaluateResponse(BaseModel):
    task_id: str
    status: str          # "pending"
    total_count: int     # 待评估数量
```

- 校验：调用者是岗位 owner + 岗位状态为 active + 有 pending 申请
- 创建 `evaluation_task` 记录，`asyncio.create_task` 启动后台工作流
- 立即返回 task_id

**GET `/api/agent/task/{task_id}`**

```python
class TaskStatusResponse(BaseModel):
    task_id: str
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    total_count: int
    evaluated_count: int
    result_summary: dict | None   # completed 时有值
    error_message: str | None     # failed 时有值
    created_at: datetime
    updated_at: datetime
```

**POST `/api/agent/confirm/{task_id}`**

```python
class ConfirmRequest(BaseModel):
    decisions: list[ConfirmDecision]   # 可逐个覆盖 AI 决策

class ConfirmDecision(BaseModel):
    application_id: str
    final_decision: Literal["interview", "reject"]
    override_reason: str | None = None  # 覆盖 AI 决策时的理由

class ConfirmResponse(BaseModel):
    updated_count: int
    message: str
```

- 确认后：`recommend` → `Application.status = interview`，`reject` → `Application.status = rejected`
- `decisions` 为空时，按 AI 建议批量更新
- `decisions` 非空时，逐个按 `final_decision` 更新

### 6.3 现有路由修改

| 修改 | 说明 |
|------|------|
| `api_router` 前缀 | `/api/v1` → `/api` |
| `GET /api/applications/job/{job_id}` | 响应增加 `ai_score`、`ai_decision` 等字段 |
| `GET /api/jobs/{job_id}` | 响应增加 `interview_quota` 字段 |
| `POST /api/jobs` / `PUT /api/jobs/{job_id}` | 请求增加 `interview_quota` 字段 |

---

## 7. 错误处理与韧性

### 7.1 LLM 调用失败

| 场景 | 处理策略 |
|------|---------|
| 单份简历评估失败 | 重试 1 次，仍失败则跳过，记录到 `errors`，继续下一份 |
| 复评节点失败 | 不重试，沿用 `screen` 步骤的排序结果 |
| 所有简历评估失败 | `evaluation_task` 状态设为 `failed`，写入 `error_message` |
| LLM 输出格式错误 | 重试 1 次（附带格式纠正提示），仍失败则跳过 |

### 7.2 工作流中断恢复

- LangGraph Checkpoint 存储在 PostgreSQL 中
- 每个节点执行完毕后自动保存 Checkpoint
- **Phase 1 暂不实现自动恢复**，但 Checkpoint 基础设施到位，Phase 2 补充

### 7.3 并发控制

- 同一岗位同一时间只允许一个评估任务运行
- `POST /evaluate/{job_id}` 时检查是否有 `pending/running` 的任务，有则返回 409 Conflict
- 不同岗位可并行评估

### 7.4 数据一致性

- 评估结果写入 `ai_*` 字段是草稿性质，不影响业务状态
- 确认操作在事务中执行：更新 `Application.status` + 标记 `evaluation_task` 已确认
- 确认是不可逆操作（状态从 pending → interview/rejected）

### 7.5 速率限制

- 评估节点：每份简历调用后 `asyncio.sleep(0.5)`
- 复评节点：单次调用，无需限速
- DeepSeek API 限流：通过 `LLM_REQUESTS_PER_MINUTE` 配置控制，默认 30 RPM

---

## 8. 目录结构与文件规划

```
backend/app/
├── api/
│   ├── __init__.py          # 修改：api_router prefix /api/v1 → /api
│   ├── agent.py             # 新增：Agent API 路由
│   ├── auth.py              # 不变
│   ├── jobs.py              # 微调：interview_quota 字段
│   ├── applications.py      # 微调：响应增加 ai_* 字段
│   └── deps.py              # 不变
├── models/
│   ├── __init__.py          # 更新：导出新模型
│   ├── evaluation_task.py   # 新增：EvaluationTask 模型 + Enum
│   ├── application.py       # 修改：新增 ai_* 字段
│   └── job.py               # 修改：新增 interview_quota 字段
├── schemas/
│   ├── __init__.py
│   ├── agent.py             # 新增：评估请求/响应/确认 schema
│   ├── job.py               # 微调：interview_quota
│   └── application.py       # 微调：ai_* 字段
├── services/
│   ├── __init__.py          # 更新：导出新服务
│   ├── agent_service.py     # 新增：Agent 业务逻辑（触发/查询/确认）
│   └── agent/               # 新增：Agent 模块目录
│       ├── __init__.py
│       ├── graph.py         # LangGraph 图定义
│       ├── state.py         # EvaluationState 定义
│       ├── nodes.py         # 各节点实现
│       └── prompts.py       # LLM 提示词模板
├── llm/                     # 新增：LLM 抽象层
│   ├── __init__.py
│   ├── base.py              # BaseLLMProvider 抽象类
│   ├── deepseek.py          # DeepSeekProvider 实现
│   └── schemas.py           # LLM 输出 Pydantic schema
└── config.py                # 微调：新增 LLM 相关配置项
```

---

## 9. 配置项

所有配置通过 pydantic-settings 从 `.env` 文件读取，敏感配置无硬编码默认值。

```python
# LLM Configuration
LLM_PROVIDER: str                          # 必填：deepseek / doubao / qwen
DEEPSEEK_API_KEY: str                      # 必填：DeepSeek API Key
DEEPSEEK_BASE_URL: str                     # 可选：默认 https://api.deepseek.com
DEEPSEEK_MODEL: str                        # 可选：默认 deepseek-chat
LLM_REQUESTS_PER_MINUTE: int = 30          # 可选：RPM 限制
LLM_EVALUATION_RETRIES: int = 1            # 可选：评估失败重试次数
LLM_BORDERLINE_RANGE: float = 10.0         # 可选：边界候选人分数范围
```

`.env.example` 新增：

```env
# LLM Configuration
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
LLM_REQUESTS_PER_MINUTE=30
LLM_EVALUATION_RETRIES=1
LLM_BORDERLINE_RANGE=10.0
```

---

## 10. 测试策略

### 10.1 单元测试

| 测试对象 | 覆盖内容 |
|---------|---------|
| `DeepSeekProvider` | Mock HTTP 调用，验证结构化输出解析、格式错误重试 |
| `nodes.py` | Mock DB + LLM，验证各节点逻辑（collect 校验、screen 排序、review 边界处理） |
| `agent_service.py` | Mock 工作流，验证触发/查询/确认的业务逻辑 |
| `prompts.py` | 验证提示词模板渲染正确 |

### 10.2 集成测试

| 测试场景 | 验证点 |
|---------|--------|
| 完整评估工作流 | Mock LLM，端到端：触发 → collect → evaluate → screen → review → save_draft |
| 确认流程 | 验证确认后 Application 状态正确更新 |
| 并发控制 | 同一岗位重复触发返回 409 |
| 边界情况 | 无 pending 申请 / LLM 全部失败 / interview_quota 为 null |

### 10.3 API 测试

复用现有 `conftest.py` 的 `AsyncClient` + `auth_headers` fixture，新增：
- `test_trigger_evaluation` — 招聘者触发评估
- `test_get_task_status` — 查询任务进度
- `test_confirm_evaluation` — 确认评估结果
- `test_trigger_evaluation_unauthorized` — 非岗位 owner 触发返回 403
- `test_duplicate_evaluation` — 重复触发返回 409

---

## 11. 新增依赖

| 包 | 用途 |
|----|------|
| `langgraph` | 工作流图定义和执行 |
| `langchain-core` | LangGraph 核心依赖 |
| `httpx` | 调用 DeepSeek API（已安装） |

---

## 12. 变更汇总

| 类别 | 内容 |
|------|------|
| **新增文件** | agent API、agent_service、agent/ 模块（graph/state/nodes/prompts）、llm/ 模块、evaluation_task 模型 |
| **修改文件** | api_router prefix、Application 模型（+ai_* 字段）、Job 模型（+interview_quota）、相关 schema、.env.example |
| **DB 迁移** | rename match_score→ai_score、删 ai_suggestions、新增 ai_evaluation/ai_decision/ai_decision_reason/ai_evaluated_at、新增 evaluation_tasks 表、新增 jobs.interview_quota |
| **新依赖** | langgraph、langchain-core |

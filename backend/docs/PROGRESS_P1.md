# HR-Agent 第一阶段实现规划与进度看板

> 本文档用于跟踪 HR-Agent 第一阶段开发进度。
>
> 第一阶段目标：基于 `HR_AGENT_DESIGN.md` 的宏观规划，实现单个招聘环节 `job_application_screening` 工作流，由单个 HR-Agent 调用并完成招聘简历筛选环节的自动化闭环。

---

## 1. 阶段目标

第一阶段聚焦一个最小但完整的业务闭环：

```text
招聘者启动 AI 筛选
  ↓
HR-Agent 接收任务
  ↓
HR-Agent 启动 job_application_screening 工作流
  ↓
job_application_screening 工作流内部执行：
  ├── 读取岗位与候选人投递
  ├── 解析/整理候选人简历信息
  ├── 评估候选人与岗位匹配度
  ├── 生成筛选建议与理由
  ├── 等待招聘者确认
  ├── 确认后更新投递状态
  └── 保留执行记录与审计信息
```

其中，“读取岗位与候选人投递”“解析/整理候选人简历信息”“评估候选人与岗位匹配度”等步骤都属于 `job_application_screening` 工作流的内部节点，不是 HR-Agent 在工作流外部直接逐步调用。

第一阶段不追求复杂多智能体、不引入 LangChain / LangGraph，不要求真实 LLM 立即上线。评估逻辑可以先采用规则 + 占位 AI，重点是建立可控、可追踪、可恢复的工作流基础设施。这里的 `Workflow Runtime` 就是第一阶段要实现的“轻量图工作流执行器”，负责加载工作流定义、执行节点、记录状态、处理暂停/确认/恢复。

---

## 2. 阶段范围

## 2.1 包含范围

第一阶段包含：

- 新增 Agent Workflow 相关数据模型；
- 新增工作流运行记录、步骤记录、决策记录、待确认动作记录；
- 实现轻量工作流执行器；
- 实现工具注册表；
- 将现有岗位、投递、简历、状态更新服务封装为工具；
- 实现单个 `job_application_screening` 工作流；
- 实现单个 HR-Agent Manager，用于启动并查询该工作流；
- 实现候选人规则化/占位智能评估；
- 实现人工确认后批量更新候选人状态；
- 新增后端 API；
- 前端接入候选人列表页，支持启动筛选、查看报告、确认结果；
- 增加基础测试。

## 2.2 不包含范围

第一阶段暂不包含：

- 多智能体协同；
- 多工作流选择；
- 企业级策略引擎；
- 完整长期记忆系统；
- 向量检索；
- 定时任务；
- 自动发送邀约或拒信；
- 无需确认的自动拒绝候选人；
- LangChain / LangGraph 等外部编排框架。

---

## 3. 第一阶段架构

```text
Frontend ApplicantsPage
  ↓
/api/v1/agent/workflows/job_application_screening/runs
  ↓
HR-Agent Manager
  ↓
Workflow Runtime
  ↓
job_application_screening Workflow
  ↓
Tool Registry
  ├── get_job_detail
  ├── list_applications_by_job
  ├── parse_resume_document
  ├── evaluate_candidate_against_job
  └── batch_update_application_status
  ↓
Existing Services
  ├── job_service.py
  ├── application_service.py
  ├── resume_parser.py
  └── evaluation.py / placeholder_ai.py
```

第一阶段只有一个顶层 HR-Agent，不引入 Domain Agent 或多个 Task Agent。`job_application_screening` 内部的候选人评估节点可以先作为规则节点或简单 Agent Node 的雏形实现。

---

## 4. 工作流设计

## 4.1 工作流名称

```text
job_application_screening
```

## 4.2 默认模式

第一阶段建议默认使用：

```text
confirm_before_update
```

即：生成筛选建议后暂停，等待招聘者确认，确认后才更新投递状态。

## 4.3 工作流输入

```json
{
  "job_id": "job_001",
  "mode": "confirm_before_update",
  "thresholds": {
    "reject_below": 60,
    "interview_above": 85
  },
  "require_confirmation": true
}
```

## 4.4 工作流输出

```json
{
  "run_id": "run_001",
  "summary": {
    "total": 30,
    "recommended_interview": 8,
    "recommended_reject": 15,
    "need_manual_review": 7
  },
  "candidates": [
    {
      "application_id": "app_001",
      "score": 88,
      "recommendation": "interview",
      "target_status": "interview",
      "confidence": 0.84,
      "reason": "后端经验匹配，具备岗位要求的主要技术栈经验。",
      "evidence": ["Python", "FastAPI", "PostgreSQL"],
      "risk_flags": []
    }
  ],
  "pending_actions": [
    {
      "action_type": "batch_update_application_status",
      "status": "pending"
    }
  ]
}
```

## 4.5 节点规划

| 顺序 | 节点 key | 节点类型 | 说明 | 第一阶段实现方式 |
| --- | --- | --- | --- | --- |
| 1 | `load_context` | TOOL | 读取岗位详情，校验招聘者权限 | 调用岗位工具 |
| 2 | `collect_applications` | TOOL | 读取该岗位下所有投递 | 调用投递工具 |
| 3 | `prepare_candidates` | TOOL / SCRIPT | 整理候选人简历信息，缺失时走占位解析 | 调用简历工具或直接使用已有结构化数据 |
| 4 | `evaluate_candidates` | SCRIPT / AGENT | 为候选人打分并生成建议 | 规则 + 占位 AI |
| 5 | `aggregate_decisions` | SCRIPT | 汇总面试、拒绝、人工复核数量 | 确定性逻辑 |
| 6 | `create_pending_action` | HUMAN | 创建待确认动作 | 写入 pending action |
| 7 | `apply_updates` | TOOL | 用户确认后批量更新投递状态 | 调用状态更新工具 |
| 8 | `summarize` | SCRIPT | 写入最终报告和 run output | 确定性逻辑 |

---

## 5. 推荐目录规划

## 5.1 后端新增目录

```text
backend/app/services/agent/
├── manager.py
├── workflow_selector.py
├── runtime/
│   ├── executor.py
│   ├── context.py
│   ├── node.py
│   └── state.py
├── workflows/
│   ├── base.py
│   └── job_application_screening.py
├── tools/
│   ├── registry.py
│   ├── job_tools.py
│   ├── application_tools.py
│   ├── resume_tools.py
│   └── evaluation_tools.py
└── evaluators/
    └── candidate_screening.py
```

第一阶段可以暂不实现完整 `agents/` 子目录，避免过早多智能体化。

## 5.2 后端新增模型和 Schema

```text
backend/app/models/agent_workflow.py
backend/app/schemas/agent_workflow.py
```

可选拆分：

```text
backend/app/models/agent_decision.py
backend/app/schemas/agent_decision.py
```

若模型数量较少，第一阶段可以集中在 `agent_workflow.py`。

## 5.3 后端 API

优先复用并扩展：

```text
backend/app/api/v1/agent.py
```

第一阶段新增接口：

```text
POST /api/v1/agent/workflows/job_application_screening/runs
GET  /api/v1/agent/workflows/runs/{run_id}
GET  /api/v1/agent/workflows/runs/{run_id}/steps
GET  /api/v1/agent/pending-actions
POST /api/v1/agent/pending-actions/{action_id}/resolve
```

## 5.4 前端新增目录

```text
frontend/src/features/agent/
├── api/agent.ts
├── hooks/useAgentWorkflows.ts
├── hooks/usePendingActions.ts
├── types/agent.ts
└── components/
    ├── WorkflowRunTimeline.tsx
    ├── PendingActionList.tsx
    └── ScreeningReport.tsx
```

## 5.5 前端接入页面

第一阶段优先接入：

```text
frontend/src/pages/ApplicantsPage.tsx
```

页面新增能力：

- 启动 AI 筛选；
- 展示筛选运行状态；
- 展示候选人评分和建议；
- 展示待确认动作；
- 批量确认更新状态；
- 刷新候选人列表。

---

## 6. 数据模型规划

## 6.1 agent_workflow_runs

记录一次工作流执行。

字段建议：

```text
id
workflow_name
workflow_version
status
created_by
business_type
business_id
input JSON
output JSON nullable
summary TEXT nullable
started_at nullable
completed_at nullable
paused_at nullable
created_at
updated_at
```

第一阶段 `business_type` 固定为：

```text
job
```

`business_id` 存储：

```text
job_id
```

## 6.2 agent_workflow_steps

记录每个节点执行过程。

字段建议：

```text
id
run_id
node_key
node_name
node_type
status
input JSON nullable
output JSON nullable
error JSON nullable
retry_count
started_at nullable
completed_at nullable
created_at
updated_at
```

## 6.3 agent_decisions

记录候选人筛选决策。

字段建议：

```text
id
run_id
step_id nullable
target_type
target_id
decision
score
confidence
reason
evidence JSON
risk_flags JSON
requires_confirmation
confirmed_by nullable
confirmed_at nullable
created_at
```

第一阶段：

```text
target_type = application
target_id = application_id
```

## 6.4 agent_pending_actions

记录待用户确认的副作用动作。

字段建议：

```text
id
run_id
action_type
payload JSON
status
created_by_agent
approved_by nullable
rejected_by nullable
resolved_at nullable
created_at
updated_at
```

第一阶段主要 action：

```text
batch_update_application_status
```

---

## 7. 工具规划

## 7.1 工具清单

| 工具名 | 用途 | 来源服务 | 是否副作用 | 是否需确认 |
| --- | --- | --- | --- | --- |
| `get_job_detail` | 获取岗位详情并校验权限 | `job_service.py` | 否 | 否 |
| `list_applications_by_job` | 获取岗位候选人列表 | `application_service.py` | 否 | 否 |
| `parse_resume_document` | 解析简历 | `resume_parser.py` | 否 | 否 |
| `evaluate_candidate_against_job` | 评估候选人与岗位匹配度 | `evaluation.py` / 新 evaluator | 否 | 否 |
| `batch_update_application_status` | 批量更新投递状态 | `application_service.py` | 是 | 是 |

## 7.2 工具执行要求

每个工具必须具备：

- 明确输入；
- 明确输出；
- 当前用户上下文；
- 权限校验；
- 异常结构化返回；
- 可选审计记录。

第一阶段可以先在 workflow step 中记录工具输入输出，后续再拆独立 `agent_tool_calls` 表。

---

## 8. 评估规则规划

第一阶段评估逻辑可以采用规则 + 占位 AI 的混合方式。

## 8.1 推荐评分维度

| 维度 | 权重 | 说明 |
| --- | --- | --- |
| 技能匹配 | 40 | 简历技能与岗位要求/描述的匹配程度 |
| 经验匹配 | 25 | 工作年限、岗位相关经验 |
| 项目相关性 | 20 | 项目经历与岗位职责的相关度 |
| 稳定性/风险 | 10 | 频繁跳槽、信息缺失等风险 |
| 其他加分 | 5 | 教育、行业背景、亮点经历等 |

## 8.2 推荐动作规则

默认规则：

```text
score >= interview_above      → interview
score < reject_below          → reject
otherwise                     → manual_review
```

默认阈值：

```text
interview_above = 85
reject_below = 60
```

状态映射：

```text
interview     → ApplicationStatus.interview
reject        → ApplicationStatus.rejected
manual_review → ApplicationStatus.reviewed
```

## 8.3 输出要求

每个候选人必须输出：

- `application_id`；
- `score`；
- `recommendation`；
- `target_status`；
- `confidence`；
- `reason`；
- `evidence`；
- `risk_flags`；
- `needs_human_review`。

---

## 9. API 任务拆解

| 编号 | 任务 | 状态 | 说明 |
| --- | --- | --- | --- |
| B-01 | 新增 workflow run/step/decision/pending action 模型 | TODO | SQLAlchemy 模型 |
| B-02 | 新增 Alembic migration | TODO | 创建相关数据表 |
| B-03 | 新增 agent workflow schemas | TODO | 请求/响应结构 |
| B-04 | 实现 Tool Registry | TODO | 注册工具与统一调用 |
| B-05 | 封装 job tools | TODO | 岗位详情、权限校验 |
| B-06 | 封装 application tools | TODO | 候选人列表、批量状态更新 |
| B-07 | 封装 resume tools | TODO | 简历解析/结构化数据整理 |
| B-08 | 实现候选人评估 evaluator | TODO | 规则 + 占位 AI |
| B-09 | 实现 Workflow Runtime | TODO | 顺序执行、状态记录、失败处理 |
| B-10 | 实现 job_application_screening 工作流 | TODO | 第一阶段核心工作流 |
| B-11 | 实现 HR-Agent Manager | TODO | 启动工作流、查询状态 |
| B-12 | 新增启动工作流 API | TODO | `POST /agent/workflows/.../runs` |
| B-13 | 新增查询 run API | TODO | `GET /agent/workflows/runs/{run_id}` |
| B-14 | 新增查询 steps API | TODO | `GET /agent/workflows/runs/{run_id}/steps` |
| B-15 | 新增 pending actions API | TODO | 查询待确认动作 |
| B-16 | 新增 resolve pending action API | TODO | 确认后执行状态更新 |
| B-17 | 后端测试 | TODO | 覆盖工作流主路径和确认路径 |

---

## 10. 前端任务拆解

| 编号 | 任务 | 状态 | 说明 |
| --- | --- | --- | --- |
| F-01 | 新增 agent types | TODO | workflow run、step、decision、pending action 类型 |
| F-02 | 新增 agent API client | TODO | 调用后端 agent workflow API |
| F-03 | 新增 agent query keys | TODO | 接入 React Query key 体系 |
| F-04 | 新增 workflow hooks | TODO | 启动、查询 run、查询 steps |
| F-05 | 新增 pending action hooks | TODO | 查询、确认/拒绝 |
| F-06 | 新增 ScreeningReport 组件 | TODO | 展示候选人评分和建议 |
| F-07 | 新增 WorkflowRunTimeline 组件 | TODO | 展示执行步骤 |
| F-08 | 新增 PendingActionList 组件 | TODO | 展示待确认动作 |
| F-09 | ApplicantsPage 接入启动 AI 筛选 | TODO | 招聘者候选人列表页入口 |
| F-10 | ApplicantsPage 接入筛选报告展示 | TODO | 展示本岗位最近筛选结果 |
| F-11 | ApplicantsPage 接入批量确认 | TODO | 确认后刷新候选人列表 |
| F-12 | 前端基础测试/手动验收 | TODO | 关键交互验证 |

---

## 11. 联调与验收任务

| 编号 | 任务 | 状态 | 说明 |
| --- | --- | --- | --- |
| I-01 | 准备测试数据 | TODO | 招聘者、岗位、多个投递 |
| I-02 | 验证启动筛选 | TODO | 从前端启动工作流 |
| I-03 | 验证工作流步骤记录 | TODO | 每个节点有状态与输出 |
| I-04 | 验证候选人建议生成 | TODO | 有评分、推荐、理由 |
| I-05 | 验证 pending action 创建 | TODO | 需要确认的批量更新动作 |
| I-06 | 验证确认后状态更新 | TODO | 投递状态正确变更 |
| I-07 | 验证权限控制 | TODO | 非招聘者或非岗位 owner 不可操作 |
| I-08 | 验证失败路径 | TODO | 无投递、岗位不存在、无权限等情况 |
| I-09 | 验证前端刷新 | TODO | 确认后候选人列表刷新 |
| I-10 | 编写阶段总结 | TODO | 记录实现情况和后续优化点 |

---

## 12. 进度看板

## 12.1 总览

| 模块 | 状态 | 进度 | 备注 |
| --- | --- | --- | --- |
| 架构设计 | DONE | 100% | 已完成 `HR_AGENT_DESIGN.md` |
| 第一阶段规划 | IN_PROGRESS | 100% | 本文档用于跟踪后续实现 |
| 数据模型 | TODO | 0% | 待实现 |
| Tool Registry | TODO | 0% | 待实现 |
| Workflow Runtime | TODO | 0% | 待实现 |
| job_application_screening 工作流 | TODO | 0% | 待实现 |
| HR-Agent Manager | TODO | 0% | 待实现 |
| 后端 API | TODO | 0% | 待实现 |
| 前端接入 | TODO | 0% | 待实现 |
| 测试与联调 | TODO | 0% | 待实现 |

## 12.2 状态说明

```text
TODO         尚未开始
IN_PROGRESS 进行中
BLOCKED      阻塞中
DONE         已完成
DEFERRED     延后处理
```

---

## 13. 里程碑规划

## Milestone 1：后端基础设施

目标：建好工作流执行和审计的底座。

任务：

- B-01 ~ B-04；
- B-09；
- 基础单元测试。

完成标准：

- 可以创建 workflow run；
- 可以顺序执行简单节点；
- 可以记录 step 状态；
- 工具可以被注册和调用。

## Milestone 2：招聘筛选工作流

目标：跑通 `job_application_screening` 后端主流程。

任务：

- B-05 ~ B-11；
- B-12 ~ B-16；
- 后端主路径测试。

完成标准：

- 可以通过 API 启动岗位筛选；
- 可以生成候选人建议；
- 可以创建 pending action；
- 确认后可以更新状态。

## Milestone 3：前端接入

目标：招聘者可在候选人列表页使用 AI 筛选。

任务：

- F-01 ~ F-11。

完成标准：

- 页面可启动筛选；
- 页面可查看筛选报告；
- 页面可确认推荐动作；
- 确认后候选人列表刷新。

## Milestone 4：测试、联调与阶段验收

目标：达到第一阶段可交付状态。

任务：

- B-17；
- F-12；
- I-01 ~ I-10。

完成标准：

- 主路径通过；
- 权限路径通过；
- 失败路径可解释；
- 阶段总结完成。

---

## 14. 验收标准

第一阶段完成时，应满足：

1. 招聘者可以对自己发布的岗位启动 `job_application_screening`；
2. 非招聘者或无权限用户不能启动该工作流；
3. 工作流能读取岗位详情和候选人投递；
4. 工作流能为候选人生成评分、建议状态、理由和证据；
5. 工作流能汇总推荐面试、建议拒绝、人工复核数量；
6. 工作流在更新状态前创建待确认动作；
7. HR 确认后系统能批量更新投递状态；
8. 工作流 run、step、decision、pending action 均有记录；
9. 前端能展示筛选报告和执行状态；
10. 前端确认后候选人列表能刷新；
11. 无投递、无权限、岗位不存在等异常场景有清晰错误；
12. 后端测试覆盖核心主路径。

---

## 15. 后续延伸点

第一阶段完成后，可进入第二阶段：

- 将规则评估升级为真实 LLM 评估；
- 引入结构化 prompt 与 JSON schema 校验；
- 增加用户偏好和企业策略；
- 支持用户修改建议并沉淀为偏好；
- 支持工作流恢复和继续执行；
- 拆分更专业的 Agent Node；
- 扩展面试邀约、招聘日报等新工作流。

---

## 16. 当前进度记录

| 日期 | 事项 | 结果 |
| --- | --- | --- |
| 2026-06-06 | 完成 HR-Agent 宏观架构讨论 | 确认通用 HR-Agent + 自研轻量图工作流 + 第一阶段招聘筛选方向 |
| 2026-06-06 | 新增 `HR_AGENT_DESIGN.md` | 完成整体设计文档 |
| 2026-06-06 | 新增 `PROGRESS.md` | 完成第一阶段详细实现规划与进度看板 |

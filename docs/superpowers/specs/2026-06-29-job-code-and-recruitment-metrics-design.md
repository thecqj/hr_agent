# 岗位编号 & 招聘指标设计

> 日期：2026-06-29
> 状态：已批准

## 背景

HR 端岗位列表没有唯一人类可读标识，唯一区分靠岗位名称。重名岗位导致对话助手歧义（如"帮我筛选该岗位的简历"）。此外，`interview_quota`（进面人数）虽在后端存在但前端未展示，`head_count`（最终招聘人数）完全缺失。

## 目标

1. 新增 6 位岗位编号（`job_code`），全局唯一，HR 和求职者均可引用
2. 新增 `head_count` 字段，与 `interview_quota` 一同为必填项
3. HR 端岗位列表展示编号、进面人数、招聘人数
4. 求职者端展示编号，不展示 quota/head_count
5. 对话助手支持 `job_code` 精确匹配，消歧义消息用编号替代 UUID
6. 对话中临时修改 `interview_quota` 时写回数据库

## 设计详情

### 1. 数据模型

#### ORM 变更（`backend/app/models/job.py`）

```python
# 新增字段
job_code: Mapped[str] = mapped_column(
    String(6), unique=True, nullable=False, index=True
)  # 格式: J00001 ~ J99999

head_count: Mapped[int] = mapped_column(
    Integer, nullable=False, default=1
)  # 最终招聘人数
```

#### `job_code` 生成规则

- 格式：`J` + 5 位零填充数字
- 范围：`J10000` ~ `J99999`（首位数字 ≥ 1，9 万可用编号）
- **随机生成**，非递增（避免暴露业务信息）
- 唯一性：生成时检查数据库，冲突则重新随机
- 创建后不可修改，删除后编号不重用

#### `interview_quota` 变更

从 `Optional[int]` 改为 `int`（NOT NULL, DEFAULT 1）。创建岗位时必填。

### 2. 数据库迁移

新增迁移脚本，步骤：

1. 添加 `job_code` 列（VARCHAR(6), nullable）
2. 为已有岗位随机分配 `job_code`（确保唯一）
3. 设置 `job_code` 为 NOT NULL + UNIQUE + INDEX
4. 添加 `head_count` 列（Integer, nullable 先）
5. 为已有岗位设置 `head_count = 1`、`interview_quota` 为 NULL 的设为 1
6. 设置 `head_count` 为 NOT NULL DEFAULT 1
7. 设置 `interview_quota` 为 NOT NULL DEFAULT 1

### 3. Pydantic Schema 变更

| Schema | 变更 |
|--------|------|
| `JobCreateRequest` | 新增 `head_count: int`（必填）；`interview_quota` 改为 `int`（必填） |
| `JobUpdateRequest` | 新增 `head_count: Optional[int]`；`job_code` 不可修改 |
| `JobResponse` | 新增 `job_code: str`、`head_count: int`；`interview_quota` 从 Optional 改为 `int` |

### 4. 后端 API 变更

- 所有返回 `JobResponse` 的端点自动包含 `job_code` 和 `head_count`
- `create_job()` 服务中生成 `job_code`（随机 + 唯一性检查）
- `job_code` 不暴露在创建/更新请求中，完全由服务端管理

### 5. 前端变更

#### TypeScript 类型（`features/jobs/types/job.ts`）

```typescript
interface Job {
  id: string;
  job_code: string;              // 新增
  // ... 原有字段 ...
  interview_quota: number;       // 从 null 可选改为必填
  head_count: number;            // 新增
}
```

#### HR 端岗位列表（`JobDashboardPage.tsx`）

新增表格列：

| 列 | 字段 | 说明 |
|---|---|---|
| 岗位编号 | `job.job_code` | monospace 字体，如 `J04217` |
| 进面人数 | `job.interview_quota` | 数字 |
| 招聘人数 | `job.head_count` | 数字 |

#### 求职者端

- **`JobCard` 组件**：显示 `job_code`（岗位名称旁或下方）
- **岗位详情页**：显示 `job_code`
- **不显示** `interview_quota` 和 `head_count`

#### 创建/编辑岗位表单

- `interview_quota`：必填数字输入，默认值 1
- `head_count`：必填数字输入，默认值 1
- `CreateJobPayload` 类型补充这两个字段

### 6. 对话助手变更

#### 意图识别 prompt（`conversation/prompts.py`）

在 `INTENT_SYSTEM_PROMPT` 中补充：
- 岗位编号格式说明：`J` + 5 位数字（如 `J04217`）
- 引导提取 `job_code` 参数（优先级高于 `job_title`）

#### `dispatch_node` 匹配逻辑（`conversation/nodes.py`）

优先级：

1. `job_code` → `WHERE job_code = :code`（精确匹配）
2. `job_id` → `WHERE id = :uuid`（UUID 精确匹配，保持兼容）
3. `job_title` → ILIKE 模糊匹配（现有逻辑不变）
4. 无参数 → 列出该招聘者的所有岗位（含编号）

消歧义消息变更：多个 `job_title` 匹配时，显示 `job_code` 而非 UUID：
- 改前：`"前端开发工程师 (ID: 3f7a2b1c-...)"`
- 改后：`"前端开发工程师 (J00003)"`

#### `interview_quota` 写回

当用户通过对话指定了 `interview_quota`（与数据库中当前值不同），在触发评估工作流前更新数据库：

```
用户说: "筛选J04217的简历，进面5人"
→ dispatch_node:
  1. 匹配 job_code = J04217
  2. 检测 extracted_params.interview_quota = 5
  3. 若 5 ≠ job.interview_quota → UPDATE jobs SET interview_quota = 5
  4. 触发评估工作流（使用 quota = 5）
```

## 不在范围内

- `head_count` 的业务逻辑（如自动统计已 hired 人数）— 后续迭代
- 岗位编号的可自定义/可修改功能
- 前端岗位列表的排序/筛选变更

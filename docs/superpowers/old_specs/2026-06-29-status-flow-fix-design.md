# HR Agent 状态流程修正设计

> **日期**: 2026-06-29
> **范围**: 删除「已审阅」状态 + 禁止被拒岗位再次投递

---

## 1. 删除「已审阅」状态

### 背景

当前 `ApplicationStatus` 枚举包含 5 个值：`pending`、`reviewed`、`interview`、`rejected`、`hired`。

经验证，AI 评估流程中 **从不使用** `reviewed` 状态：
- `save_draft_node`：仅写入 `ai_decision` 字段，不修改 `Application.status`
- `confirm_evaluation`：直接设为 `INTERVIEW` 或 `REJECTED`

唯一设置 `REVIEWED` 的代码路径是 HR 手动点击「通过」按钮。但「通过」的语义是进入面试环节，对应 `INTERVIEW` 更准确。

### 变更

#### 后端

1. **`backend/app/models/application.py`**：从 `ApplicationStatus` 枚举中删除 `REVIEWED = "reviewed"`
2. **Alembic 迁移**：
   - `UPDATE applications SET status = 'interview' WHERE status = 'reviewed'` — 将现有已审阅记录迁移为面试中
   - 无需修改列定义（仍为 VARCHAR）
3. **`backend/app/schemas/application.py`**：`ApplicationStatusUpdateRequest` 的 status 字段自然不再接受 `"reviewed"`
4. **无需修改** `application_service.update_application_status` 或 `agent_service` — 它们不硬编码 `"reviewed"`

#### 前端

1. **`frontend/src/shared/constants/applicationStatus.ts`**：
   - 从 `ApplicationStatus` 类型中删除 `"reviewed"`
   - 从 `APPLICATION_STATUS_MAP` 中删除 `reviewed` 条目
2. **`frontend/src/pages/ApplicantsPage.tsx`**：
   - 「通过」按钮：`updateStatus(app.id, "interview")` 替代 `"reviewed"`
   - 筛选 tab：从「全部 / 待审核 / 已审阅 / 已拒绝」改为「全部 / 待审核 / 面试中 / 已拒绝 / 已录用」
3. **`frontend/src/pages/MyApplicationsPage.tsx`**：删除「已审阅」分类 tab

### 数据迁移策略

- 现有 `status='reviewed'` 记录 → 迁移为 `status='interview'`（语义一致：已审阅 = 人工通过 = 进入面试）
- 迁移在 Alembic migration 中执行，确保数据库一致性

---

## 2. 已拒绝岗位不允许再次投递

### 背景

当前逻辑：
- `application_service.create_application` 检测已有申请时返回 409（可覆盖），不区分状态
- JobDetailPage 对所有已投递岗位统一显示禁用「已投递」按钮
- ApplyPage 收到 409 后弹出覆盖确认对话框，`force=True` 可重置状态为 pending

问题：被拒绝的求职者仍可通过强制覆盖再次投递。

### 变更

#### 后端

1. **`backend/app/services/application_service.py`** — `create_application`：
   - 检测到已有申请且 `status == REJECTED` 时，返回 HTTP 403 + `"该岗位已拒绝您的投递，无法再次申请"`
   - 其他状态（pending / interview / hired）仍返回 409（可覆盖）

```python
if existing_app:
    if existing_app.status == ApplicationStatus.REJECTED:
        raise HTTPException(status_code=403, detail="该岗位已拒绝您的投递，无法再次申请")
    if not force:
        raise HTTPException(status_code=409, detail="您已投递过该岗位，是否覆盖原简历？")
    # force=True 覆盖逻辑（仅 pending/interview/hired）
```

#### 前端

1. **`frontend/src/pages/JobDetailPage.tsx`**：
   - 已投递（pending/interview/hired）：显示禁用「已投递」按钮（当前灰色）
   - 已拒绝（rejected）：显示禁用「已拒绝」按钮（红色调，明确告知被拒）

2. **`frontend/src/pages/ApplyPage.tsx`**：
   - API 返回 403 时：显示 toast/提示"该岗位已拒绝您的投递，无法再次申请"，不弹出覆盖确认对话框
   - API 返回 409 时：保持现有覆盖确认流程不变

---

## 影响范围

| 文件 | 变更类型 |
|------|---------|
| `backend/app/models/application.py` | 删除枚举值 |
| `backend/app/services/application_service.py` | 添加 403 拒绝逻辑 |
| `backend/alembic/versions/xxx_remove_reviewed_status.py` | 新建迁移 |
| `frontend/src/shared/constants/applicationStatus.ts` | 删除类型和映射 |
| `frontend/src/pages/ApplicantsPage.tsx` | 修改通过按钮 + 筛选 tab |
| `frontend/src/pages/MyApplicationsPage.tsx` | 删除已审阅 tab |
| `frontend/src/pages/JobDetailPage.tsx` | 区分已拒绝按钮 |
| `frontend/src/pages/ApplyPage.tsx` | 处理 403 响应 |

# 前端问题修复设计 — 卡片对齐 & 申请人数计数

**日期:** 2026-06-24
**范围:** 2 个 bug 修复

---

## 问题 1：岗位市场卡片按钮高低不齐

### 现象

求职者"岗位市场"页面中，多个职位卡片因内容高度不同，"立即投递"按钮位置参差不齐。

### 根因

`JobCard.tsx` 中 `Card` 组件已有 `h-full flex flex-col`（CSS Grid 保证同行卡片等高），但 `CardContent` 没有 `flex-1`，按钮 `<div>` 紧跟在可变高度内容之后而非被推到卡片底部。

可变高度的来源：
- 部分岗位无薪资 → 缺少一行
- 部分岗位无技能标签 → 缺少徽章区
- 部分岗位无描述 → 缺少两行描述文本

### 修复

**文件：** `frontend/src/shared/ui/JobCard.tsx`

给 `CardContent` 添加 `flex-1` 使其填满 Card 剩余空间，将按钮推到卡片底部：

```diff
- <CardContent className="p-6">
+ <CardContent className="p-6 flex-1">
```

一行改动。CSS Grid + flex-col + flex-1 三者配合确保同一行所有卡片的按钮对齐在同一位置。

---

## 问题 2：HR 后台申请人数始终为 0

### 现象

HR "我的岗位"页面中，每个岗位的申请人数始终显示 0，即使已有求职者投递。

### 根因

`backend/app/api/jobs.py` 的 `_job_to_dict` 函数硬编码 `"applications_count": 0`，从未查询 Application 表获取真实计数。

完整因果链：
1. 数据库 `applications` 表有 `job_id` 外键指向 `jobs` 表
2. `Job` ORM 模型有 `applications` 关系
3. 但 `job_service.py` 查询时未 eager-load 该关系
4. `_job_to_dict` 直接返回硬编码 `0`

### 修复

**文件 1：** `backend/app/services/job_service.py`

在 `list_jobs` 和 `get_job` 的查询中添加 `selectinload(Job.applications)`，确保 `job.applications` 集合已加载：

```python
from sqlalchemy.orm import selectinload

# list_jobs 查询添加 .options(selectinload(Job.applications))
# get_job 查询添加 .options(selectinload(Job.applications))
```

**文件 2：** `backend/app/api/jobs.py`

将 `_job_to_dict` 中硬编码的 `0` 替换为实际计数：

```python
"applications_count": len(job.applications) if hasattr(job, 'applications') and job.applications is not None else 0,
```

无需修改前端 — 前端已正确读取 `applications_count` 字段显示。

---

## 影响范围

| 问题 | 前端改动 | 后端改动 | 数据库迁移 |
|------|---------|---------|-----------|
| 卡片对齐 | 1 文件 1 行 | — | — |
| 申请人数 | — | 2 文件 | — |

无数据库迁移，无 API schema 变更，无破坏性改动。

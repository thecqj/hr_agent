# 前端系统问题修复设计文档

**日期：** 2026-06-24
**方案：** 逐问题精确修复（方案 A）

## 概述

本文档描述 HR 招聘系统中 6 个已知前端问题的修复设计。采用最小化精确修复策略，不改变现有架构，逐个问题解决。

---

## 问题 1：发布新岗位页面样式与提示

**文件：** `frontend/src/pages/PostJobPage.tsx`

### 现状

表单不居中，样式简陋，无必填/选填标记，无格式要求提示。

### 修改内容

1. **表单居中**：外层容器添加 `max-w-2xl mx-auto`，使表单在页面中央显示

2. **必填/选填标记**：
   - 必填字段（`title`、`description`）label 旁添加红色 `*` 标记
   - 选填字段 label 旁标注"(选填)"：工作地点、工作类型、薪资范围、技能标签

3. **格式提示**：
   - 薪资字段 placeholder `"例如：15000"`，hint `"请输入月薪范围（元/月）"`
   - 工作地点 placeholder `"例如：北京市海淀区"`
   - 技能标签 hint `"按 Enter 添加标签"`

4. **样式美化**：
   - 表单分区（基本信息/岗位详情/技能标签）使用 `Card` 包裹，增加视觉层次
   - 输入框统一宽度、间距
   - 提交按钮使用 `w-full` 并增加顶部间距

---

## 问题 2：侧边栏高亮错误

**文件：** `frontend/src/shared/ui/layout/RecruiterLayout.tsx`

### 现状

点击"发布新岗位" tab 后，"我的岗位" tab 仍然高亮。原因是 active 判断使用了 `startsWith` 匹配，导致 `/dashboard/post` 同时匹配了 `/dashboard`。

### 修改内容

将侧边栏 active 判断改为精确路径匹配：

- `/dashboard` → "我的岗位"高亮
- `/dashboard/post` → "发布新岗位"高亮
- `/dashboard/applicants/:jobId` → "我的岗位"高亮（属于岗位管理的子页面）

实现方式：将 `SIDEBAR_ITEMS` 中的路径匹配逻辑改为使用 `location.pathname === item.path` 精确匹配，对于 `/dashboard` 额外处理 `applicants` 子路径的归属。

---

## 问题 3：我的岗位无法查看岗位详情

**文件：** `frontend/src/pages/JobDashboardPage.tsx`

### 现状

"我的岗位"页面中，已发布岗位只有"查看申请人"、"关闭岗位"、"删除"操作，无法查看岗位本身的信息。

### 修改内容

1. **操作菜单增加"查看详情"选项**：在每行岗位的下拉菜单中新增"查看详情"

2. **弹窗展示岗位信息**：点击后弹出 `Dialog`，展示完整岗位信息：
   - 岗位名称、状态、工作地点、工作类型
   - 薪资范围
   - 技能标签（Tag 形式）
   - 岗位描述（完整文本）
   - 发布时间、更新时间

3. **复用现有 API**：使用已有的 `useJobDetailQuery(jobId)` 获取岗位详情数据

4. **组件放置**：弹窗直接在 `JobDashboardPage.tsx` 中内联实现，与页面已有弹窗风格一致

---

## 问题 4：登录页无注册功能

**文件：** 新增 `frontend/src/pages/RegisterPage.tsx` + 修改 `LoginPage.tsx` + 修改 `App.tsx`

### 现状

API 层已有 `registerUser` / `useRegisterMutation` / `RegisterData` 类型，但无注册页面，登录页无注册入口。

### 修改内容

1. **新增 `RegisterPage.tsx`**：
   - 复用登录页的左右分屏布局风格
   - 表单字段：邮箱、密码、确认密码、姓名、角色选择（求职者/HR）、手机号(选填)
   - 复用已有的 `useRegisterMutation` hook
   - zod 校验：邮箱格式、密码最少 6 位、确认密码一致性、角色必选
   - 注册成功后自动登录并跳转到对应系统首页（求职者→`/jobs`，HR→`/dashboard`）

2. **修改 `LoginPage.tsx`**：
   - 登录表单下方添加"还没有账号？立即注册"链接，跳转至 `/register`

3. **修改 `App.tsx`**：
   - 添加 `/register` 路由指向 `RegisterPage`

---

## 问题 5：岗位市场已投递无提示

**文件：** `frontend/src/pages/JobMarketPage.tsx` + `frontend/src/shared/ui/JobCard.tsx` + `frontend/src/features/applications/api/applications.ts`

### 现状

投递过的岗位没有任何已投递提示，且可以再次投递。

### 修改内容

1. **查询用户投递记录**：在 `JobMarketPage.tsx` 中，对已登录的求职者用户，额外调用 `useMyApplicationsQuery` 获取投递列表，提取已投递的 `job_id` 集合

2. **传递 applied 状态**：将已投递 job_id 集合传入 `JobCard` 组件的 `applied` prop

3. **JobCard 显示已投递状态**：
   - 已投递的岗位卡片显示"已投递"徽章（使用 `Badge` 组件，绿色背景）
   - "立即投递"按钮变为灰色不可点击状态，文案改为"已投递"

4. **未登录用户**：`JobCard` 不显示已投递状态，按钮正常展示

---

## 问题 6：我的投递页面问题

**文件：** `frontend/src/pages/MyApplicationsPage.tsx` + 可能涉及后端 API

### 现状

- 投递记录中没有标题，只显示投递时间和状态
- 选择不同类型（待审核/面试中/已拒绝）显示相同投递记录

### 问题分析

前端代码已包含 `job_title`、`company_name` 的展示逻辑，问题可能出在：
- 后端 `GET /api/v1/applications/my` 返回数据中 `job_title` 为空（未正确填充关联字段）
- 前端状态筛选未正确传递参数或 API 不支持筛选

### 修改内容

1. **排查并修复数据显示**：
   - 检查 `GET /api/v1/applications/my` 返回数据是否包含 `job_title`
   - 如果后端缺失，需修复后端在返回投递记录时关联查询岗位标题
   - 前端确保正确显示岗位标题、公司名称

2. **修复状态筛选**：
   - 检查 `useMyApplicationsQuery` 是否正确传递 `status` 参数
   - 如果 API 不支持 status 筛选，改为前端筛选（从全部投递中过滤）
   - 如果 API 支持但前端未传参，修复参数传递

3. **新增弹窗查看投递详情**：
   - 点击投递记录卡片后弹出 `Dialog`
   - 弹窗内容：岗位名称、公司、投递时间、当前状态、简历摘要
   - 与"我的岗位"弹窗风格一致

---

## 影响范围

| 文件 | 修改类型 |
|------|----------|
| `frontend/src/pages/PostJobPage.tsx` | 修改 |
| `frontend/src/shared/ui/layout/RecruiterLayout.tsx` | 修改 |
| `frontend/src/pages/JobDashboardPage.tsx` | 修改 |
| `frontend/src/pages/RegisterPage.tsx` | 新增 |
| `frontend/src/pages/LoginPage.tsx` | 修改 |
| `frontend/src/App.tsx` | 修改 |
| `frontend/src/pages/JobMarketPage.tsx` | 修改 |
| `frontend/src/shared/ui/JobCard.tsx` | 修改 |
| `frontend/src/pages/MyApplicationsPage.tsx` | 修改 |
| 后端 API (applications) | 可能修改 |

## 不涉及

- 不引入新的 UI 库或设计系统
- 不重构现有组件架构
- 不修改数据库 schema（除非后端 API 修复需要）

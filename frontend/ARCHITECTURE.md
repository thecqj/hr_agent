# Frontend Architecture

本文描述 `frontend/` 的当前代码架构与模块职责。

---

## 1. 总体架构

项目采用 **Feature-First + Shared Layer** 分层：

- `app/`：应用级装配（Provider 等）
- `features/`：业务域模块（auth/jobs/applications/resume）
- `shared/`：跨业务共享能力（HTTP 客户端、常量、通用反馈与布局）
- `pages/`：页面层（路由入口，组合 feature hooks + UI）
- `components/ui/`：基础 UI 原子组件
- `lib/`：通用工具

这是一个典型的“页面编排 + feature 业务逻辑 + shared 基础设施”架构。

---

## 2. 路由与访问控制

路由定义在 `src/App.tsx`：

- 公共：
  - `/login`
  - `/jobs`
  - `/jobs/:id`
- 求职者：
  - `/apply/:jobId`
  - `/my-applications`
- 招聘者：
  - `/dashboard`
  - `/dashboard/post`
  - `/dashboard/applicants/:jobId`

`ProtectedRoute` 基于 `useAuthStore` 中 `user.role` 做鉴权。

---

## 3. 数据流

### 3.1 请求链路

`Page -> feature hook (React Query) -> feature api -> shared/api/client -> backend`

- 页面不直接写 axios 请求
- 由 feature hooks 统一承接 query/mutation
- 由 `shared/api/client.ts` 统一注入 token、处理 401 刷新

### 3.2 状态分工

- **React Query**：服务端数据（岗位、投递记录、候选人列表等）
- **Zustand**：仅认证态（token / refreshToken / user）

---

## 4. 模块说明

## 4.1 app

- `src/main.tsx`：应用入口，挂载 `AppProviders` 和 `Toaster`
- `src/app/providers/AppProviders.tsx`：`QueryClientProvider` 装配与默认策略

## 4.2 features/auth

- `api/auth.ts`：登录/注册接口
- `hooks/useAuthMutations.ts`：登录注册 mutation
- `hooks/useLogout.ts`：统一退出逻辑
- `store/authStore.ts`：认证持久化状态
- `types/auth.ts`：认证与用户类型定义

## 4.3 features/jobs

- `api/jobs.ts`：岗位相关 API（列表、详情、发布、删除、状态变更、评估）
- `hooks/useJobs.ts`：岗位 query/mutation 与失效策略
- `types/job.ts`：岗位相关类型定义

## 4.4 features/applications

- `api/applications.ts`：投递与候选人相关 API
- `hooks/useApplications.ts`：投递列表、候选人列表、状态更新等 hooks
- `types/application.ts`：投递与结构化简历类型定义

## 4.5 features/resume

- `api/resume.ts`：简历解析上传接口

## 4.6 shared

- `api/client.ts`：axios 实例与拦截器
- `api/error.ts`：API 错误文案归一化
- `constants/queryKeys.ts`：React Query key 工厂
- `constants/applicationStatus.ts`：投递状态展示映射
- `ui/feedback/*`：加载/空态/错误组件
- `ui/layout/*`：求职者/招聘者顶部导航组件

## 4.7 pages

页面文件作为路由入口，只负责：
- 读取路由参数
- 调用 feature hooks
- 组织 UI 展示与交互

---

## 5. UI 层

- `components/ui/*`：基于 shadcn/radix 的可复用原子组件
- 样式由 `index.css` + Tailwind 实现
- 页面统一使用 `shared/ui/feedback` 控制 loading/empty/error 体验

---

## 6. 可维护性要点

- 新业务优先放入 `features/<domain>`
- 页面层不要直接调用 axios
- 新增请求必须配套 query key 与 invalidation 策略
- 非认证的全局状态优先使用 React Query，不落入 Zustand

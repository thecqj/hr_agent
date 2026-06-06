# Project Note（Frontend）

本文按模块给出更细粒度的实现说明，便于后续迭代与交接。

---

## 1) app 层

## 1.1 `src/main.tsx`
职责：
- React 根节点挂载
- 注入 `AppProviders`
- 注入全局 `Toaster`

注意：
- 全局 Provider 的新增（如 i18n、Theme）建议集中在 `AppProviders`，避免入口分散。

## 1.2 `src/app/providers/AppProviders.tsx`
职责：
- 初始化并提供 `QueryClient`

当前默认策略：
- `retry: 1`
- `refetchOnWindowFocus: false`

建议：
- 按业务调整 `staleTime`/`gcTime`，避免列表频繁请求。

---

## 2) auth 模块（`src/features/auth`）

## 2.1 `types/auth.ts`
定义：
- `UserRole`
- `User`
- `AuthResponse`
- `LoginData` / `RegisterData`

## 2.2 `store/authStore.ts`
职责：
- 维护认证态：`token`、`refreshToken`、`user`
- 提供 `setAuth`、`clearAuth`、`logout`
- 使用 `persist` 将认证态写入 localStorage

边界：
- 仅保存认证相关数据，不保存业务数据（业务数据由 React Query 管理）。

## 2.3 `api/auth.ts`
职责：
- 登录/注册 API 调用（返回业务数据）

## 2.4 `hooks/useAuthMutations.ts`
职责：
- 登录、注册 mutation
- 在 `onSuccess` 中统一写入 store

## 2.5 `hooks/useLogout.ts`
职责：
- 清理认证态
- 跳转 `/login`

---

## 3) jobs 模块（`src/features/jobs`）

## 3.1 `types/job.ts`
定义：
- 岗位实体、状态、工作类型
- 分页响应结构
- 列表过滤参数、创建岗位 payload

## 3.2 `api/jobs.ts`
接口能力：
- 获取岗位列表/详情
- 更新岗位状态
- 发布岗位
- 删除岗位
- 触发岗位评估

## 3.3 `hooks/useJobs.ts`
封装：
- `useJobsQuery`
- `useJobDetailQuery`
- `useRecruiterJobsQuery`
- `useUpdateJobStatusMutation`
- `useCreateJobMutation`
- `useDeleteJobMutation`
- `useEvaluateJobMutation`

缓存策略：
- 修改/删除后按 `queryKeys.jobs.*` 精准失效。

注意：
- 新增岗位相关接口时，优先补充 query key，再补 hooks。

---

## 4) applications 模块（`src/features/applications`）

## 4.1 `types/application.ts`
定义：
- 求职申请、候选人、结构化简历等类型
- 分页响应类型

## 4.2 `api/applications.ts`
接口能力：
- 创建投递（支持 `force`）
- 查询我的投递
- 查询岗位候选人列表
- 更新候选人状态

## 4.3 `hooks/useApplications.ts`
封装：
- `useMyApplicationsQuery`
- `useApplicantsByJobQuery`
- `useCreateApplicationMutation`
- `useUpdateApplicationStatusMutation`

缓存策略：
- 投递提交后刷新 `applications.mine`
- 带 `job_id` 时同步刷新 `applications.byJob(jobId)`

---

## 5) resume 模块（`src/features/resume`）

## 5.1 `api/resume.ts`
职责：
- 文件上传
- 调用 `/resume/parse` 获取结构化简历

注意：
- 上传失败时由页面层统一通过 `getApiErrorMessage` 兜底展示。

---

## 6) shared 层（`src/shared`）

## 6.1 `api/client.ts`
职责：
- 统一 axios 实例（`/api/v1`）
- request 拦截器注入 Bearer Token
- response 拦截器处理 401 + 刷新队列

关键点：
- 并发 401 时通过 `failedQueue` 排队，避免重复刷新。

## 6.2 `api/error.ts`
职责：
- 解析 AxiosError 中的 `detail`
- 输出统一错误文案

## 6.3 `constants/queryKeys.ts`
职责：
- 统一维护 query key，避免 key 字符串散落

## 6.4 `constants/applicationStatus.ts`
职责：
- 投递状态文案和 Badge variant 映射

## 6.5 `ui/feedback/*`
职责：
- 统一 loading / empty / error 展示

## 6.6 `ui/layout/*`
职责：
- 抽象求职者与招聘者头部导航

---

## 7) pages 层（`src/pages`）

页面与功能对应：
- `LoginPage.tsx`：登录/注册
- `JobMarketPage.tsx`：岗位列表（求职者）
- `JobDetailPage.tsx`：岗位详情
- `ApplyPage.tsx`：投递流程（含简历解析）
- `MyApplicationsPage.tsx`：我的投递
- `JobDashboardPage.tsx`：招聘者岗位总览
- `PostJobPage.tsx`：发布岗位
- `ApplicantsPage.tsx`：候选人列表与简历详情

页面层原则：
- 不直连 axios
- 只通过 feature hooks 获取数据
- 只负责展示、交互和路由跳转

---

## 8) UI 与样式

- `components/ui/*`：基础组件库
- `index.css`：Tailwind 与全局主题变量
- `lib/utils.ts`：`cn` 类名合并

---

## 9) 开发约定（建议）

1. 新 API 必须落在 feature 的 `api/`，并配套 `hooks/`。  
2. query key 统一在 `shared/constants/queryKeys.ts` 扩展。  
3. 错误提示优先走 `getApiErrorMessage`。  
4. 页面层只组合，不承载复杂业务逻辑。  
5. 认证外状态不要进 Zustand。  

---

## 10) 当前可优化项（后续迭代）

- 路由级懒加载（减小首屏包体积）
- React Query 按页面精细化 staleTime
- 增补测试（hooks 与关键页面交互）
- 为 feature 增加 `index.ts` 导出收敛

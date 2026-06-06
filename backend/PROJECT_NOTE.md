# PROJECT NOTE（模块接口与功能说明）

本文档面向开发者，说明各模块内部接口、核心函数及功能边界。

## 1. API 入口与路由组织

- 主入口：`app/main.py`
- v1 路由聚合：`app/api/v1/__init__.py`
- 基础前缀：`/api/v1`

路由模块：
- `auth.py`：认证
- `jobs.py`：岗位
- `applications.py`：投递
- `resume_parser.py`：简历解析（占位）
- `agent.py`：智能体（占位）

---

## 2. 认证模块（auth）

文件：`app/api/v1/auth.py` + `app/services/auth_service.py`

### 2.1 对外接口

- `POST /auth/register`
  - 入参：`UserRegisterRequest`
  - 功能：注册用户并创建对应 profile（求职者/招聘者）
  - 返回：token 对 + user 信息（dict）

- `POST /auth/login`
  - 入参：`UserLoginRequest`
  - 功能：账号密码登录
  - 返回：token 对 + user 信息（dict）

- `POST /auth/refresh`
  - 入参：`TokenRefreshRequest`
  - 功能：刷新 access token
  - 返回：新 token 对

- `GET /auth/me`
  - 功能：获取当前用户信息
  - 返回：`UserInfoResponse`

- `POST /auth/logout`
  - 功能：登出提示（JWT 无状态）
  - 返回：`MessageResponse`

### 2.2 Service 内部关键函数

- `register_user(db, data)`
- `login_user(db, email, password)`
- `refresh_access_token(db, refresh_token)`
- `get_current_user(db, token)`

依赖 `app/utils/security.py`：
- `hash_password`
- `verify_password`
- `create_access_token`
- `create_refresh_token`
- `decode_token`

---

## 3. 岗位模块（jobs）

文件：`app/api/v1/jobs.py` + `app/services/job_service.py`

### 3.1 对外接口

- `POST /jobs/`：创建岗位（招聘者）
- `GET /jobs/`：岗位列表（分页 + 过滤）
- `GET /jobs/{job_id}`：岗位详情
- `PUT /jobs/{job_id}`：更新岗位
- `DELETE /jobs/{job_id}`：删除岗位
- `PATCH /jobs/{job_id}/status`：修改岗位状态

### 3.2 Service 内部关键函数

- `create_job`
- `get_job`
- `list_jobs`
- `update_job`
- `delete_job`
- `update_job_status`

### 3.3 业务规则

- 仅 `recruiter` 可创建/维护岗位。
- 默认列表展示 `active` 岗位（招聘者可按状态过滤）。
- 支持关键词、地点、工作类型、薪资范围过滤。

---

## 4. 投递模块（applications）

文件：`app/api/v1/applications.py` + `app/services/application_service.py`

### 4.1 对外接口

- `POST /applications/`
  - 求职者投递，可 `force=true` 覆盖历史投递。

- `GET /applications/my`
  - 求职者查看我的投递。

- `GET /applications/job/{job_id}`
  - 招聘者查看岗位投递列表。

- `PATCH /applications/{application_id}/status`
  - 招聘者修改投递状态。

### 4.2 Service 内部关键函数

- `create_application`
- `get_my_applications`
- `get_applications_for_job`
- `update_application_status`

### 4.3 业务规则

- 仅 `job_seeker` 可投递。
- 非 `active` 岗位不可投递。
- 同一用户对同一岗位重复投递默认拒绝，`force` 才覆盖。

---

## 5. 简历解析模块（resume）

文件：`app/api/v1/resume_parser.py` + `app/services/resume_parser.py`

### 5.1 对外接口

- `POST /resume/parse`
  - 上传文件后返回结构化简历数据。

### 5.2 当前实现

- 调用 `parse_resume_document(content, filename)`。
- 实际由 `placeholder_ai.parse_resume_placeholder` 返回占位结构。
- 保持字段稳定：`name/work_experience_years/contact/skills/...`

---

## 6. 智能体模块（agent）

文件：`app/api/v1/agent.py` + `app/services/placeholder_ai.py` + `app/services/evaluation.py`

### 6.1 对外接口

- `POST /agent/chat`
  - SSE 返回占位消息流。

- `POST /agent/batch-screening`
  - 返回批量筛选占位结果。

- `POST /agent/evaluate/{job_id}`
  - 触发后台占位评估并返回占位信息。

### 6.2 当前实现

- `chat_placeholder`
- `batch_screening_placeholder`
- `evaluate_placeholder`
- `run_batch_evaluation(job_id)` 当前为占位任务链路。

---

## 7. 数据模型（models）

目录：`app/models/`

- `user.py`
  - `User`, `UserRole`
- `seeker_profile.py`
  - 求职者扩展信息
- `recruiter_profile.py`
  - 招聘者扩展信息
- `job.py`
  - `Job`, `WorkType`, `JobStatus`
- `application.py`
  - `Application`, `ApplicationStatus`
- `base.py`
  - `Base`, `TimestampMixin`

---

## 8. Schema（请求/响应契约）

目录：`app/schemas/`

- `auth.py`
  - `UserRegisterRequest`, `UserLoginRequest`, `TokenRefreshRequest`, `UserInfoResponse`, `MessageResponse`

- `job.py`
  - `JobCreateRequest`, `JobUpdateRequest`, `JobStatusUpdateRequest`, `JobResponse`, `JobListResponse`

- `application.py`
  - `ApplicationCreateRequest`, `ApplicationStatusUpdateRequest`, `ApplicationResponse`, `ApplicationListResponse`

- `resume.py`
  - `StructuredResume` 及其子结构

---

## 9. 依赖注入与权限控制

文件：`app/api/deps.py`、`app/api/v1/deps.py`

- `get_optional_user`：可选登录
- `get_required_user`：必须登录
- `require_role(*roles)`：角色校验工厂

---

## 10. 数据库与迁移

- DB 会话：`app/database.py`
  - `engine`
  - `async_session`
  - `get_db`

- 迁移：`alembic/`
  - 执行：`alembic upgrade head`

注意：数据库需先启用 `pgvector` extension（`CREATE EXTENSION IF NOT EXISTS vector;`）。

---

## 11. 当前约束与扩展点

1. AI 为占位实现，不依赖外部模型服务。
2. API 契约优先稳定：后续扩展尽量在 service 层完成。
3. 若恢复 AI，请优先替换：
   - `app/services/placeholder_ai.py`
   - `app/services/resume_parser.py`
   - `app/services/evaluation.py`
   - `app/api/v1/agent.py`（仅在确需修改协议时变更）

# Backend Architecture

本文档描述 `backend/` 的模块划分、职责边界和关键定义。

## 1. 架构总览

项目采用分层结构：

1. **API 层**：`app/api/`
   - 定义 HTTP 路由、参数校验、认证依赖、响应序列化。
2. **Service 层**：`app/services/`
   - 承载业务规则与流程编排。
3. **Model 层**：`app/models/`
   - SQLAlchemy ORM 模型，映射数据库结构。
4. **Schema 层**：`app/schemas/`
   - Pydantic 请求/响应模型，约束接口字段。
5. **基础设施层**：`app/config.py`、`app/database.py`、`alembic/`
   - 配置、数据库连接与迁移管理。

---

## 2. 请求处理链路

典型请求流程：

`Router -> Depends(鉴权/DB会话) -> Service -> Model(DB) -> Schema/Dict -> Response`

- DB 会话由 `get_db()` 提供，按请求级生命周期管理事务。
- 鉴权由 `get_required_user()` / `get_optional_user()` 提供。

---

## 3. 关键模块说明

## 3.1 入口与配置

- `app/main.py`
  - 创建 FastAPI 应用。
  - 挂载 CORS 中间件。
  - 挂载 `/api/v1` 路由。
  - 提供 `/`、`/health`。

- `app/config.py`
  - 使用 `BaseSettings` + `.env` 管理配置。
  - 包含应用信息、数据库、JWT、CORS、AI 占位开关。

## 3.2 数据库与迁移

- `app/database.py`
  - 创建 SQLAlchemy async engine（psycopg）。
  - 提供 `async_session` 与 `get_db()`。
  - 提供 `init_db()` / `drop_db()`（开发辅助）。

- `alembic/` + `alembic.ini`
  - 数据库 schema 版本管理。
  - 通过 `alembic upgrade head` 同步结构。

## 3.3 API 模块

- `app/api/v1/auth.py`
- `app/api/v1/jobs.py`
- `app/api/v1/applications.py`
- `app/api/v1/resume_parser.py`
- `app/api/v1/agent.py`

以上模块统一在 `app/api/v1/__init__.py` 聚合，统一前缀 `/api/v1`。

## 3.4 Service 模块

- `auth_service.py`：注册、登录、刷新 token、当前用户解析。
- `job_service.py`：岗位 CRUD、筛选分页、状态更新。
- `application_service.py`：投递创建/覆盖、查询、状态更新。
- `resume_parser.py`：简历解析占位流程。
- `evaluation.py`：批量评估占位流程。
- `placeholder_ai.py`：AI 占位实现集中管理。

## 3.5 Agent 子模块（占位）

- `app/services/agent/*`
  - 目前保留模块边界与接口形态。
  - 内部实现已替换为占位逻辑，避免真实 LLM 依赖。

---

## 4. 关键定义（Domain Enums）

- `UserRole`（`app/models/user.py`）
  - `job_seeker`, `recruiter`

- `WorkType`（`app/models/job.py`）
  - `remote`, `onsite`, `hybrid`

- `JobStatus`（`app/models/job.py`）
  - `draft`, `active`, `closed`

- `ApplicationStatus`（`app/models/application.py`）
  - `pending`, `reviewed`, `interview`, `rejected`, `hired`

---

## 5. 鉴权与安全

- `app/utils/security.py`
  - 密码哈希/校验（bcrypt）
  - JWT 生成/解析（python-jose）

- `app/api/deps.py` 与 `app/api/v1/deps.py`
  - 注入当前用户、可选用户、角色校验。

---

## 6. AI 占位策略

当前 AI 接口（`/api/v1/resume/*`, `/api/v1/agent/*`）均返回固定占位数据：

- 保持 API 契约稳定（路径 + 请求/响应字段）
- 不引入任何 LLM 运行时依赖
- 后续回填时优先替换 service 层实现，减少 API 层变更

---

## 7. 测试架构

- `tests/`
  - `test_auth_api.py`
  - `test_jobs_api.py`
  - `test_applications_api.py`
  - `test_ai_placeholder_api.py`

测试以 API 契约与路由行为为主，验证重构后接口可用性。

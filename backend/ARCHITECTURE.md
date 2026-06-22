# Backend Architecture

> 智能简历投递系统（HR Agent）后端 — 一份面向构建者和 AI 编程工具的全景参考。

## 技术栈

| 层面 | 选型 | 备注 |
|------|------|------|
| Web 框架 | FastAPI | 异步，自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.x (async) | 声明式 + `Mapped` 类型注解风格 |
| 数据库 | PostgreSQL + pgvector | pgvector 用于简历/岗位向量检索 |
| 迁移 | Alembic | 异步引擎 |
| 校验/DTO | Pydantic v2 | 请求/响应 schema，`BaseModel` |
| 配置 | pydantic-settings | `.env` → `Settings` 单例 |
| 认证 | JWT (python-jose) + bcrypt | 双令牌（access + refresh） |
| 测试 | pytest + pytest-asyncio | `TestClient` 同步风格，依赖覆盖 mock |

## 目录结构

```
backend/
├── app/                        # 应用主包
│   ├── main.py                 # FastAPI 实例、CORS、路由挂载
│   ├── config.py               # Settings（pydantic-settings，读 .env）
│   ├── database.py             # 异步引擎、会话工厂、init_db
│   ├── api/                    # 路由层（HTTP 入口）
│   │   ├── __init__.py         # api_router 统一注册 /api/v1 前缀
│   │   ├── deps.py             # 依赖注入：get_optional_user / get_required_user / require_role
│   │   ├── auth.py             # /api/v1/auth/*  注册/登录/刷新/我/登出
│   │   ├── jobs.py             # /api/v1/jobs/*   岗位 CRUD + 状态变更
│   │   └── applications.py     # /api/v1/applications/*  投递/列表/状态更新
│   ├── models/                 # ORM 层（数据库表定义）
│   │   ├── base.py             # DeclarativeBase + TimestampMixin（id/created_at/updated_at）
│   │   ├── user.py             # User + UserRole 枚举
│   │   ├── seeker_profile.py   # SeekerProfile（含 resume_vector pgvector 列）
│   │   ├── recruiter_profile.py# RecruiterProfile
│   │   ├── job.py              # Job + WorkType/JobStatus 枚举（含 requirement_vector）
│   │   ├── application.py      # Application + ApplicationStatus 枚举（含 structured_resume JSONB）
│   │   └── __init__.py         # 统一导出所有模型和枚举
│   ├── schemas/                # Pydantic DTO 层（请求/响应 schema）
│   │   ├── auth.py             # 注册/登录/令牌/用户信息 schema
│   │   ├── job.py              # 岗位创建/更新/状态/响应/列表 schema
│   │   └── application.py      # 投递创建/状态/响应/列表 + StructuredResume 子模型
│   ├── services/               # 业务逻辑层
│   │   ├── auth_service.py     # 注册/登录/刷新令牌/获取当前用户
│   │   ├── job_service.py      # 岗位 CRUD、搜索过滤分页、权限校验
│   │   └── application_service.py # 投递/列表/状态更新、权限校验
│   └── utils/
│       └── security.py         # bcrypt 哈希/验签 + JWT 生成/解码
├── alembic/                    # 数据库迁移
│   ├── env.py                  # 异步迁移环境
│   └── versions/               # 迁移脚本
├── tests/                      # 测试
├── alembic.ini                 # Alembic 配置（DB URL 等）
├── mypy.ini                    # mypy --strict 配置
├── requirements.txt            # Python 依赖
├── .env / .env.example         # 环境变量
├── init_db.py                  # 开发用：一键建表脚本
└── README.md                   # 项目说明
```

## 分层架构与数据流

```
请求 → FastAPI (main.py)
         │
         ├─ 中间件: CORS
         │
         ▼
      API 路由层 (app/api/)
      ├─ 依赖注入 (deps.py): 认证、角色校验
      ├─ 参数校验: Pydantic schema (app/schemas/)
      │
      ▼
      业务逻辑层 (app/services/)
      ├─ 权限校验、业务规则
      ├─ 调用 ORM 模型 (app/models/)
      │
      ▼
      数据访问层 (SQLAlchemy AsyncSession)
      ├─ 由 database.get_db() 注入
      ├─ 请求结束自动 commit / 异常 rollback
      │
      ▼
      PostgreSQL + pgvector
```

**核心规则：**
- **API 层**不写业务逻辑，仅做参数接收、服务调用、响应组装
- **Service 层**包含所有业务逻辑和权限校验，直接操作 ORM 模型
- **Models 层**纯 ORM 定义，不含业务方法
- **Schemas 层**纯 Pydantic 校验/序列化，不引用 ORM 对象的内部状态
- **Utils 层**无状态工具函数，不依赖数据库会话

## 数据模型与关系

```
User (users)                    ← 核心用户表
├── role: UserRole (job_seeker | recruiter)
├── 1:1 → SeekerProfile        ← 求职者档案（含 resume_vector pgvector）
├── 1:1 → RecruiterProfile     ← 招聘者档案（公司信息）
├── 1:N → Job                  ← 招聘者发布的岗位
└── 1:N → Application          ← 求职者的投递记录

Job (jobs)                      ← 岗位表
├── recruiter_id → User (FK)
├── status: JobStatus (draft | active | closed)
├── work_type: WorkType (remote | onsite | hybrid)
├── requirement_vector: Vector(1536)  ← pgvector，预留给 AI 匹配
├── skills_required: JSON
└── 1:N → Application

Application (applications)      ← 投递/申请表
├── job_id → Job (FK)
├── applicant_id → User (FK)
├── status: ApplicationStatus (pending | reviewed | interview | rejected | hired)
├── structured_resume: JSONB    ← 结构化简历（由 AI 解析填入）
└── resume_text: Text           ← 简历原文
```

**所有表共享** `TimestampMixin`：`id` (UUID4)、`created_at`、`updated_at`。

## API 路由总览

所有业务路由统一挂载 `/api/v1` 前缀。

| 前缀 | 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|------|
| `/auth` | POST | `/register` | 无 | 用户注册（自动创建对应 Profile） |
| | POST | `/login` | 无 | 登录，返回双令牌 |
| | POST | `/refresh` | 无 | 用 refresh_token 换新令牌 |
| | GET | `/me` | 必须登录 | 获取当前用户信息 |
| | POST | `/logout` | 必须登录 | 登出（客户端删令牌） |
| `/jobs` | POST | `/` | 必须登录 (recruiter) | 创建岗位 |
| | GET | `/` | 可选登录 | 岗位列表（支持关键词/地点/类型/薪资过滤） |
| | GET | `/{job_id}` | 无 | 岗位详情 |
| | PUT | `/{job_id}` | 必须登录 (本人) | 更新岗位 |
| | DELETE | `/{job_id}` | 必须登录 (本人) | 删除岗位 |
| | PATCH | `/{job_id}/status` | 必须登录 (本人) | 修改岗位状态 |
| `/applications` | POST | `/` | 必须登录 (job_seeker) | 投递简历（支持 `?force=true` 覆盖） |
| | GET | `/my` | 必须登录 (job_seeker) | 我的投递记录 |
| | GET | `/job/{job_id}` | 必须登录 (recruiter/本人) | 查看岗位投递列表 |
| | PATCH | `/{application_id}/status` | 必须登录 (recruiter/本人) | 更新申请状态 |

另有根路由：`GET /` → 应用信息，`GET /health` → 健康检查。

## 认证与授权

```
注册/登录 → bcrypt 哈希密码 → 返回 {access_token, refresh_token}
                                          │
请求带 Authorization: Bearer <token> ─────┘
    │
    ▼ deps.py
    ├─ get_optional_user()  → 无 token 返回 None（浏览岗位列表）
    ├─ get_required_user()  → 无/无效 token 返回 401
    └─ require_role("recruiter") → 角色不符返回 403
```

- **Access Token**：HS256 签名，默认 30 分钟过期，payload 含 `sub`(user_id) + `role`
- **Refresh Token**：同算法，默认 7 天过期，payload 额外含 `type: "refresh"`
- **密码限制**：bcrypt 最多 72 字节（UTF-8），由 schema 层和 security 层双重校验

## 数据库与迁移

- **引擎**：`postgresql+psycopg://` 异步驱动
- **连接池**：`pool_pre_ping=True`，`expire_on_commit=False`
- **迁移工具**：Alembic（异步模式，配置于 `alembic/env.py`）
- **现有迁移**：
  - `f6fec5160021` — 初始化所有表
  - `99186d2082a7` — 为 applications 添加 `structured_resume` JSONB 列
- **开发建表**：`python init_db.py`（直接 `create_all`，不走迁移）

## 配置

所有配置通过 `.env` 环境变量注入，由 `app/config.py` 的 `Settings` 单例管理：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_NAME` | 智能简历投递系统 | 应用名称 |
| `APP_VERSION` | 1.0.0 | 版本号 |
| `DEBUG` | false | 调试模式 |
| `DATABASE_URL` | `postgresql+psycopg://app:password@localhost:5432/jobboard` | 数据库连接串 |
| `DATABASE_ECHO` | false | SQL 日志 |
| `SECRET_KEY` | change-this-in-production | JWT 签名密钥（**生产必须更换**） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access Token 过期时间 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh Token 过期时间 |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | 允许的前端来源 |
| `AI_PLACEHOLDER_ENABLED` | — | AI 占位功能开关 |
| `AI_PLACEHOLDER_MESSAGE` | — | AI 占位响应消息 |

## 测试

- **框架**：`pytest` + `pytest-asyncio`，使用 `TestClient`（同步风格调用异步应用）
- **Mock 方式**：`app.dependency_overrides` 覆盖 `get_db`（返回 None）、`get_required_user`/`get_optional_user`（返回 fixture 用户）
- **Fixture**（`conftest.py`）：
  - `client` — FastAPI TestClient
  - `seeker_user` — 求职者 SimpleNamespace
  - `recruiter_user` — 招聘者 SimpleNamespace
  - `_reset_overrides` — autouse，每个测试前后清理依赖覆盖
- **运行**：`pytest -q`

## 按构建任务定位模块

| 构建任务 | 需改动的文件/目录 |
|----------|-------------------|
| 新增 API 端点 | `app/api/` (新路由文件) → `app/api/__init__.py` (注册) → `app/schemas/` (请求/响应) → `app/services/` (业务逻辑) |
| 修改数据表结构 | `app/models/` (ORM) → `alembic/versions/` (迁移脚本) → `app/schemas/` (DTO 适配) |
| 新增用户角色/权限 | `app/models/user.py` (UserRole) → `app/api/deps.py` (require_role) → 相关 service |
| 接入 AI 模型（向量匹配/简历解析） | `app/services/` (新增 AI service) → `app/models/` 中 pgvector 列已预留 (`resume_vector`, `requirement_vector`) → `app/schemas/application.py` 中 `StructuredResume` 已定义 |
| 修改认证逻辑 | `app/utils/security.py` (JWT/bcrypt) → `app/services/auth_service.py` → `app/api/deps.py` |
| 新增配置项 | `app/config.py` (Settings 字段) → `.env.example` (文档) |
| 新增测试 | `tests/` (新 test_*.py) → `tests/conftest.py` (如有公共 fixture) |
| 修改 API 响应格式 | `app/schemas/` (Pydantic Response 模型) → 对应 `app/api/` 中的 `_to_dict` 辅助函数 |

## 代码约定

- **类型注解**：全部函数必须有参数和返回类型注解，通过 `mypy --strict` 检查
- **ORM 风格**：SQLAlchemy 2.x `Mapped[]` + `mapped_column()` 类型注解风格，不用 `Column()`
- **DTO 风格**：Pydantic v2 `BaseModel`，请求/响应严格分离
- **UUID 主键**：所有表使用 UUID4，API 响应中序列化为字符串
- **异步优先**：数据库操作全部 `async`，session 由 `get_db()` 依赖注入自动管理事务
- **枚举**：角色/状态等使用 `str + enum.Enum`，数据库存枚举值字符串
- **循环引用**：ORM 模型间通过 `TYPE_CHECKING` 延迟导入处理类型提示

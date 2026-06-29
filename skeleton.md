# HR Agent — 架构概览（Skeleton）

> 智能简历投递系统：帮助求职者自动匹配岗位并投递简历。
> 技术栈：FastAPI + SQLAlchemy 2.0 + Pydantic v2（后端），React 19 + TypeScript + Vite（前端）。

---

## 目录结构

```
hr_agent/
├── CLAUDE.md                     # 项目规范 & 命令速查
├── HR_Agent_Explore.md           # 战略愿景 & 分阶段路线图
├── docs/
│   └── superpowers/
│       ├── plans/                # 实现计划（7 份）
│       └── specs/                # 设计规格（5 份）
├── backend/                      # ── 后端 ──
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── mypy.ini
│   ├── .env.example
│   ├── init_db.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/             # 3 个迁移文件
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/               # ORM 层
│   │   ├── schemas/              # Pydantic DTO 层
│   │   ├── api/                  # 路由 & 依赖注入
│   │   ├── llm/                 # LLM 提供商抽象层
│   │   ├── services/             # 业务逻辑
│   │   │   ├── agent/            # LangGraph 评估工作流
│   │   │   └── conversation/     # LangGraph 对话助手（Phase 2）
│   │   └── utils/                # 工具函数
│   └── tests/                    # 集成测试
└── frontend/                     # ── 前端 ──
    ├── package.json
    ├── vite.config.ts
    ├── components.json            # shadcn/ui 配置
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx                # 路由定义
    │   ├── index.css
    │   ├── features/             # 按业务域组织
    │   │   ├── auth/
    │   │   ├── jobs/
    │   │   ├── applications/
    │   │   └── chat/               # 对话助手（Phase 2）
    │   ├── pages/                # 页面组件
    │   ├── shared/               # 共享模块
    │   │   ├── api/
    │   │   ├── constants/
    │   │   └── ui/
    │   ├── components/ui/        # shadcn/ui 原子组件（18 个）
    │   ├── app/providers/
    │   └── lib/utils.ts
    └── public/
```

---

## 后端（Backend）

### `app/config.py` — 应用配置

从环境变量 / `.env` 加载全局设置。

```python
class Settings(BaseSettings):
    APP_NAME: str                       # "智能简历投递系统"
    APP_VERSION: str                    # "1.0.0"
    DEBUG: bool                         # False
    DATABASE_URL: str                   # PostgreSQL 连接串
    DATABASE_ECHO: bool                 # False
    SECRET_KEY: str                     # JWT 签名密钥
    ACCESS_TOKEN_EXPIRE_MINUTES: int    # 30
    REFRESH_TOKEN_EXPIRE_DAYS: int      # 7
    CORS_ORIGINS: list[str]             # 允许的前端源
    # LLM 配置
    LLM_PROVIDER: str                   # "deepseek"
    DEEPSEEK_API_KEY: str               # DeepSeek API 密钥
    DEEPSEEK_BASE_URL: str              # "https://api.deepseek.com"
    DEEPSEEK_MODEL: str                 # "deepseek-chat"
    LLM_REQUESTS_PER_MINUTE: int        # 30
    LLM_EVALUATION_RETRIES: int         # 1
    LLM_BORDERLINE_RANGE: float         # 10.0

settings: Settings  # 模块级单例
```

---

### `app/database.py` — 数据库引擎 & 会话 & Checkpointer

```python
engine: AsyncEngine
async_session: async_sessionmaker[AsyncSession]

async def get_db() -> AsyncGenerator[AsyncSession, None]
    """请求级会话，自动提交/回滚。"""

async def init_checkpointer() -> AsyncPostgresSaver
    """初始化 LangGraph PostgreSQL 持久化存储（AsyncConnectionPool）。"""

def get_checkpointer() -> AsyncPostgresSaver
    """返回已初始化的 checkpointer（需先调用 init_checkpointer）。"""

async def close_checkpointer() -> None
    """关闭连接池并重置 checkpointer（应用关闭时调用）。"""

async def init_db() -> None
    """从 metadata 创建全部表（仅开发用）。"""

async def drop_db() -> None
    """删除全部表（仅开发用）。"""
```

---

### `app/main.py` — FastAPI 应用入口

```python
app: FastAPI  # 挂载 CORS 中间件 + /api 路由 + lifespan（checkpointer 初始化/关闭）

GET  /        → root()         -> Dict[str, Any]   # 欢迎信息
GET  /health  → health_check() -> Dict[str, str]   # 健康检查
```

---

### ORM 模型（`app/models/`）

#### `base.py` — 声明基类 & 公共混入

```python
class Base(DeclarativeBase): ...

class TimestampMixin:
    """为子类提供 id / created_at / updated_at 列。"""
    id:         Mapped[uuid.UUID]   # PK, auto UUID
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]    # onupdate=now(UTC)
```

#### `user.py` — 用户 & 角色枚举

```python
class UserRole(str, Enum):
    JOB_SEEKER = "job_seeker"
    RECRUITER  = "recruiter"

class User(Base, TimestampMixin):          # table "users"
    email:         Mapped[str]             # unique, indexed
    password_hash: Mapped[str]
    role:          Mapped[UserRole]
    name:          Mapped[str]
    phone:         Mapped[str | None]
    avatar_url:    Mapped[str | None]
    is_active:     Mapped[bool]            # default=True
    # 关系
    seeker_profile:    Mapped[SeekerProfile | None]   # one-to-one
    recruiter_profile: Mapped[RecruiterProfile | None] # one-to-one
    applications:      Mapped[list[Application]]       # one-to-many
    jobs:              Mapped[list[Job]]               # one-to-many
```

#### `job.py` — 岗位 & 工作类型/状态枚举

```python
class WorkType(str, Enum):
    REMOTE = "remote"; ONSITE = "onsite"; HYBRID = "hybrid"

class JobStatus(str, Enum):
    DRAFT = "draft"; ACTIVE = "active"; CLOSED = "closed"

class Job(Base, TimestampMixin):           # table "jobs"
    recruiter_id:      Mapped[uuid.UUID]   # FK → users.id
    title:             Mapped[str]
    description:       Mapped[str]
    requirement_vector: Mapped[Any | None] # pgvector Vector(1536)
    salary_min:        Mapped[int | None]
    salary_max:        Mapped[int | None]
    location:          Mapped[str | None]
    work_type:         Mapped[WorkType]    # default=ONSITE
    skills_required:   Mapped[list[str]]   # JSON
    status:            Mapped[JobStatus]   # default=ACTIVE
    interview_quota:   Mapped[int | None]  # 面试人数上限
    # 关系
    recruiter:    Mapped[User]              # back_populates="jobs"
    applications: Mapped[list[Application]]  # cascade delete-orphan
```

#### `application.py` — 投递 & 状态枚举

```python
class ApplicationStatus(str, Enum):
    PENDING = "pending"; INTERVIEW = "interview"
    REJECTED = "rejected"; HIRED = "hired"

class Application(Base, TimestampMixin):    # table "applications"
    job_id:             Mapped[uuid.UUID]   # FK → jobs.id
    applicant_id:       Mapped[uuid.UUID]   # FK → users.id
    resume_text:        Mapped[str]
    cover_letter:       Mapped[str | None]
    structured_resume:  Mapped[Any | None]  # JSONB
    status:             Mapped[ApplicationStatus]  # default=PENDING
    ai_score:           Mapped[float | None]       # AI 加权总分
    ai_evaluation:      Mapped[Any | None]         # JSONB, AI 评估详情
    ai_decision:        Mapped[str | None]         # "recommend" / "reject"
    ai_decision_reason: Mapped[str | None]         # AI 决策理由
    ai_evaluated_at:    Mapped[datetime | None]    # AI 评估时间
    # 关系
    job:       Mapped[Job]   # back_populates="applications"
    applicant: Mapped[User]  # back_populates="applications"
```

#### `seeker_profile.py` — 求职者画像

```python
class SeekerProfile(Base, TimestampMixin):  # table "seeker_profiles"
    user_id:              Mapped[uuid.UUID]  # FK → users.id, unique
    resume_text:          Mapped[str | None]
    resume_vector:        Mapped[Any | None]  # pgvector Vector(1536)
    skills:               Mapped[list[str]]   # JSON
    experience_years:     Mapped[int]         # default=0
    education:            Mapped[list[Any]]   # JSON
    expected_salary_min:  Mapped[int | None]
    expected_salary_max:  Mapped[int | None]
    job_preferences:      Mapped[dict[str, Any]]  # JSON
```

#### `recruiter_profile.py` — 招聘者画像

```python
class RecruiterProfile(Base, TimestampMixin):  # table "recruiter_profiles"
    user_id:             Mapped[uuid.UUID]   # FK → users.id, unique
    company_name:        Mapped[str | None]
    company_description: Mapped[str | None]
    company_logo_url:    Mapped[str | None]
    verified:            Mapped[bool]         # default=False
```

#### `evaluation_task.py` — 评估任务 & 任务状态枚举

```python
class EvalTaskStatus(str, Enum):
    PENDING = "pending"; RUNNING = "running"; COMPLETED = "completed"
    CONFIRMED = "confirmed"; FAILED = "failed"

class EvaluationTask(Base, TimestampMixin):          # table "evaluation_tasks"
    job_id:             Mapped[uuid.UUID]   # FK → jobs.id
    triggered_by:       Mapped[uuid.UUID]   # FK → users.id
    status:             Mapped[EvalTaskStatus]   # default=PENDING
    total_count:        Mapped[int]              # default=0
    evaluated_count:    Mapped[int]              # default=0
    result_summary:     Mapped[Any | None]       # JSONB
    error_message:      Mapped[str | None]       # Text
    # 关系
    job:               Mapped[Job]
    triggered_by_user: Mapped[User]
```

---

### Pydantic 模式（`app/schemas/`）

#### `auth.py` — 认证 DTO

| 类名 | 关键字段 |
|------|---------|
| `UserRegisterRequest` | `email: EmailStr`, `password: str`, `name: str`, `role: UserRole`, `phone: str \| None` |
| `UserLoginRequest` | `email: EmailStr`, `password: str` |
| `TokenRefreshRequest` | `refresh_token: str` |
| `TokenResponse` | `access_token`, `refresh_token`, `token_type`, `expires_in` |
| `UserInfoResponse` | `id`, `email`, `name`, `role`, `phone`, `avatar_url`, `is_active` |
| `MessageResponse` | `message`, `detail` |

#### `job.py` — 岗位 DTO

| 类名 | 关键字段 |
|------|---------|
| `JobCreateRequest` | `title`, `description`, `salary_min/max`, `location`, `work_type`, `skills_required`, `interview_quota?` |
| `JobUpdateRequest` | 所有字段 Optional（部分更新，含 `interview_quota`） |
| `JobStatusUpdateRequest` | `status: JobStatus` |
| `JobResponse` | 全部字段 + `recruiter_name`, `applications_count`, `interview_quota`; `from_attributes=True` |
| `JobListResponse` | `total`, `page`, `page_size`, `items: list[JobResponse]` |

#### `application.py` — 投递 DTO

| 类名 | 关键字段 |
|------|---------|
| `StructuredResume` | `name`, `work_experience_years`, `contact: ContactInfo`, `work_experience`, `project_experience`, `education`, `certificates`, `skills`, `self_evaluation` |
| `ContactInfo` | `phone`, `email`, `wechat`, `other` |
| `WorkExperience` | `company`, `position`, `start_date`, `end_date?`, `description` |
| `ProjectExperience` | `name`, `role`, `start_date`, `end_date?`, `description`, `technologies` |
| `Education` | `school`, `major`, `degree`, `start_date`, `end_date?` |
| `Certificate` | `name`, `date?` |
| `ApplicationCreateRequest` | `job_id`, `resume_text`, `structured_resume?`, `cover_letter?` |
| `ApplicationStatusUpdateRequest` | `status: ApplicationStatus` |
| `ApplicationResponse` | 全字段 + `applicant_name?`, `job_title?`, `ai_score?`, `ai_evaluation?`, `ai_decision?`, `ai_decision_reason?`, `ai_evaluated_at?`; `from_attributes=True` |
| `ApplicationListResponse` | `total`, `page`, `page_size`, `items: list[ApplicationResponse]` |

#### `agent.py` — 智能评估 DTO

| 类名 | 关键字段 |
|------|---------|
| `DimensionScore` | `name: str`, `score: float (0-100)`, `weight: float (0-1)`, `reason: str` |
| `ResumeEvaluation` | `dimensions: list[DimensionScore]`, `weighted_total: float`, `suggestion: Literal["recommend","reject","neutral"]`, `summary: str` |
| `BorderlineReview` | `application_id: str`, `action: Literal["keep","adjust"]`, `new_decision?`, `reason: str` |
| `EvaluateRequest` | `interview_quota?: int` |
| `EvaluateResponse` | `task_id: str`, `status: str`, `total_count: int` |
| `TaskStatusResponse` | `task_id`, `job_id`, `status: EvalTaskStatus`, `total_count`, `evaluated_count`, `result_summary?`, `error_message?`, `created_at`, `updated_at` |
| `ConfirmDecision` | `application_id: str`, `final_decision: Literal["interview","reject"]`, `override_reason?` |
| `ConfirmRequest` | `decisions: list[ConfirmDecision]`（为空则按 AI 建议批量更新） |
| `ConfirmResponse` | `updated_count: int`, `message: str` |
| `IntentResult` | `intent: Literal["evaluate","help","unknown"]`, `confidence: float (0-1)`, `extracted_params: dict`, `clarifying_question?: str` |

#### `chat.py` — 对话助手 DTO（Phase 2）

| 类名 | 关键字段 |
|------|---------|
| `ChatRequest` | `message: str (1-500)` |
| `ThinkingEvent` | `status: str` |
| `IntentEvent` | `intent: str`, `params: dict` |
| `ProgressEvent` | `status: str`, `evaluated_count?: int`, `total_count?: int` |
| `ErrorEvent` | `message: str`, `recoverable: bool` |
| `EvaluationSummaryCard` | `type="evaluation_summary"`, `task_id`, `job_title`, `total_count`, `recommended_count`, `rejected_count`, `result_page_url` |
| `ResultEvent` | `reply_message: str`, `cards?: list[EvaluationSummaryCard]` |

---

### API 路由（`app/api/`）

所有业务端点挂载在 `/api` 下。

#### `auth.py` — `/api/auth`

| 方法 | 路径 | 认证 | 处理器 | 说明 |
|------|------|------|--------|------|
| POST | `/register` | 无 | `register()` | 用户注册 |
| POST | `/login` | 无 | `login()` | 用户登录 |
| POST | `/refresh` | 无 | `refresh_token()` | 刷新令牌 |
| GET | `/me` | 必须 | `get_me()` | 当前用户信息 |
| POST | `/logout` | 必须 | `logout()` | 退出登录 |

#### `jobs.py` — `/api/jobs`

| 方法 | 路径 | 认证 | 处理器 | 说明 |
|------|------|------|--------|------|
| POST | `/` | 必须 | `create_job()` | 创建岗位 |
| GET | `/` | 可选 | `list_jobs()` | 岗位列表（分页+筛选） |
| GET | `/{job_id}` | 无 | `get_job()` | 岗位详情 |
| PUT | `/{job_id}` | 必须 | `update_job()` | 更新岗位 |
| DELETE | `/{job_id}` | 必须 | `delete_job()` | 删除岗位 |
| PATCH | `/{job_id}/status` | 必须 | `update_job_status()` | 变更岗位状态 |

`list_jobs` 查询参数：`page`, `page_size`, `keyword`, `location`, `work_type`, `salary_min`, `salary_max`, `status`

#### `applications.py` — `/api/applications`

| 方法 | 路径 | 认证 | 处理器 | 说明 |
|------|------|------|--------|------|
| POST | `/` | 必须 | `apply()` | 投递简历（`?force=true` 可覆盖） |
| GET | `/my` | 必须 | `my_applications()` | 我的投递 |
| GET | `/job/{job_id}` | 必须 | `job_applications()` | 岗位的投递列表 |
| PATCH | `/{application_id}/status` | 必须 | `update_status()` | 更新投递状态 |

#### `agent.py` — `/api/agent`

| 方法 | 路径 | 认证 | 处理器 | 说明 |
|------|------|------|--------|------|
| POST | `/evaluate/{job_id}` | 必须 | `trigger_evaluation()` | 触发 AI 评估工作流 |
| GET | `/task/{task_id}` | 必须 | `get_task_status()` | 查询评估任务状态 |
| POST | `/confirm/{task_id}` | 必须 | `confirm_evaluation()` | 确认评估结果 |

#### `chat.py` — `/api/chat`（Phase 2）

| 方法 | 路径 | 认证 | 处理器 | 说明 |
|------|------|------|--------|------|
| POST | `/send` | 必须 | `send_chat_message()` | 发送消息，返回 SSE 流式响应（`text/event-stream`） |

SSE 事件类型：`thinking`, `intent`, `progress`, `result`, `error`, `done`

#### `deps.py` — 依赖注入

```python
async def get_optional_user(...) -> User | None
    """可选认证：无 token 时返回 None。"""

async def get_required_user(...) -> User
    """必须认证：无效/缺失 token 抛 401。"""

def require_role(*roles: str) -> Callable[..., Any]
    """角色检查工厂：当前用户角色不在允许列表则抛 403。"""
```

---

### 业务服务（`app/services/`）

#### `auth_service.py`

```python
async def register_user(db: AsyncSession, data: UserRegisterRequest) -> Dict[str, Any]
    """注册新用户，自动创建对应 Profile，返回令牌+用户信息。"""

async def login_user(db: AsyncSession, email: str, password: str) -> Dict[str, Any]
    """登录校验，返回令牌+用户信息；邮箱不存在/密码错误→401。"""

async def refresh_access_token(db: AsyncSession, refresh_token: str) -> Dict[str, Any]
    """刷新令牌对；无效/过期→401。"""

async def get_current_user(db: AsyncSession, token: str) -> User
    """解码 access token 返回 User ORM 对象。"""
```

#### `job_service.py`

```python
async def create_job(db: AsyncSession, data: JobCreateRequest, current_user: User) -> Job
    """创建岗位；仅招聘者可用，求职者→403。"""

async def get_job(db: AsyncSession, job_id: str) -> Job
    """获取单个岗位详情；不存在→404。"""

async def list_jobs(db, page, page_size, keyword?, location?, work_type?,
                    salary_min?, salary_max?, status?, current_user?) -> Tuple[list[Job], int]
    """分页+筛选的岗位列表；招聘者仅看到自己的岗位。"""

async def update_job(db: AsyncSession, job_id: str, data: JobUpdateRequest, current_user: User) -> Job
    """部分更新岗位；非拥有者→403。"""

async def delete_job(db: AsyncSession, job_id: str, current_user: User) -> None
    """删除岗位及其所有投递；非拥有者→403。"""

async def update_job_status(db: AsyncSession, job_id: str, data: JobStatusUpdateRequest, current_user: User) -> Job
    """变更岗位状态；非拥有者→403。"""
```

#### `application_service.py`

```python
async def create_application(db: AsyncSession, data: ApplicationCreateRequest,
                             current_user: User, force: bool = False) -> Application
    """求职者投递；招聘者→403，岗位不存在→404，已关闭→400，重复→409（force=True 可覆盖）。"""

async def get_applications_for_job(db, job_id, current_user, status_filter?, page?, page_size?) -> Tuple[list[Application], int]
    """招聘者查看自己岗位的投递；非拥有者→403。"""

async def get_my_applications(db, current_user, status_filter?, page?, page_size?) -> Tuple[list[Application], int]
    """求职者查看自己的投递历史。"""

async def update_application_status(db, application_id, data, current_user) -> Application
    """招聘者更新投递状态；非拥有者→403。"""
```

#### `agent_service.py`

```python
async def trigger_evaluation(db: AsyncSession, job_id: str, current_user: User, request: Any) -> EvaluateResponse
    """触发评估工作流；仅招聘者可用，岗位不存在→404，非拥有者→403，岗位非活跃→400，并发冲突→409。"""

async def get_task_status(db: AsyncSession, task_id: str, current_user: User) -> TaskStatusResponse
    """查询评估任务状态；任务不存在→404，非触发者→403。"""

async def confirm_evaluation(db: AsyncSession, task_id: str, current_user: User, request: ConfirmRequest) -> ConfirmResponse
    """确认评估结果；任务不存在→404，非触发者→403，状态非 completed→400；按 AI 建议或人工覆盖更新 Application 状态。"""
```

#### `agent/` — LangGraph 评估工作流

```
state.py      — EvaluationState(TypedDict): 工作流状态定义
                job_id, triggered_by, task_id (输入)
                job_info, applications (收集阶段)
                evaluation_results, evaluated_count (评估阶段)
                screening_result (筛选阶段)
                review_adjustments (复评阶段)
                errors (错误累积)

prompts.py    — LLM 提示词模板
                EVALUATION_SYSTEM_PROMPT: 简历评估系统提示（含维度、评分基准、偏见抑制）
                REVIEW_SYSTEM_PROMPT: 边界复评系统提示
                build_evaluation_user_prompt(job_info, structured_resume, dimensions) -> str
                build_review_user_prompt(job_info, borderline_recommend, borderline_reject, cutoff_score) -> str

nodes.py      — LangGraph 节点实现
                collect_node(state)  -> dict   # 收集 pending 申请（db 从 get_config 获取）
                evaluate_node(state) -> dict   # 逐份 LLM 评估，adispatch_custom_event 进度
                screen_node(state)   -> dict   # 按 quota/60 分阈值筛选
                review_node(state)   -> dict   # LLM 复评边界候选人
                save_draft_node(state) -> dict # 写入 ai_* 草稿字段，含 evaluation_details

graph.py      — 工作流图定义 & 运行
                build_evaluation_graph(checkpointer) -> CompiledStateGraph
                run_evaluation_workflow(state, db) -> EvaluationState
                流程：collect → evaluate → screen → review → save_draft → END
```

#### `conversation/` — LangGraph 对话助手（Phase 2）

```
__init__.py   — 模块入口，导出 build_conversation_graph

state.py      — ConversationState(TypedDict): 对话工作流状态
                user_message, current_user_id (输入)
                intent, extracted_params, clarifying_question (意图识别)
                task_id, evaluation_status (工作流调用)
                reply_message, reply_cards, result_page_url (反馈)
                errors (错误)

prompts.py    — 对话 LLM 提示词
                INTENT_SYSTEM_PROMPT: 意图识别系统提示（evaluate/help/unknown）
                build_intent_user_prompt(user_message) -> str

nodes.py      — 对话 LangGraph 节点
                intent_node(state)    -> dict   # LLM 意图识别，失败回退 unknown
                dispatch_node(state)  -> dict   # 岗位匹配 + 内联执行评估图 + 进度转发
                feedback_node(state)  -> dict   # 格式化结果摘要 + 评估卡片
                route_by_intent(state) -> str   # 条件路由：evaluate→dispatch, else→feedback

graph.py      — 对话图定义
                build_conversation_graph(checkpointer) -> CompiledStateGraph
                流程：START → intent → (evaluate? → dispatch → feedback → END)
                                        (help/unknown? → feedback → END)
```

---

### LLM 提供商（`app/llm/`）

#### `base.py` — 抽象基类

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def evaluate_resume(self, job_info: dict, structured_resume: dict, dimensions: list[str]) -> ResumeEvaluation: ...
    @abstractmethod
    async def review_borderline(self, job_info: dict, borderline_recommend: list[dict], borderline_reject: list[dict], cutoff_score: float) -> list[BorderlineReview]: ...
    @abstractmethod
    async def recognize_intent(self, user_message: str) -> IntentResult: ...
    @abstractmethod
    async def close(self) -> None: ...
```

#### `deepseek.py` — DeepSeek 实现

```python
class DeepSeekProvider(BaseLLMProvider):
    """基于 httpx.AsyncClient 调用 DeepSeek Chat API；支持 JSON response_format + 自动重试。"""
    async def evaluate_resume(...) -> ResumeEvaluation
    async def review_borderline(...) -> list[BorderlineReview]
    async def recognize_intent(...) -> IntentResult   # Phase 2: 意图识别
    async def close() -> None  # 关闭 HTTP 客户端
```

#### `schemas.py` — 重新导出

```python
# 从 app.schemas.agent 重新导出 DimensionScore, ResumeEvaluation, BorderlineReview
```

---

### 工具函数（`app/utils/`）

#### `security.py`

```python
MAX_BCRYPT_PASSWORD_BYTES: int  # 72

def hash_password(password: str) -> str
    """bcrypt 哈希；超 72 字节→ValueError。"""

def verify_password(plain_password: str, hashed_password: str) -> bool
    """校验密码哈希；不匹配或异常→False。"""

def create_access_token(data: Dict[str, Any], expires_delta?: timedelta) -> str
    """签发 JWT access token（HS256）。"""

def create_refresh_token(data: Dict[str, Any]) -> str
    """签发 JWT refresh token（含 "type":"refresh" 声明）。"""

def decode_token(token: str) -> Dict[str, Any]
    """解码并验证 JWT；失败→空字典。"""
```

---

### 数据库迁移（`alembic/`）

| 版本文件 | 说明 |
|---------|------|
| `f6fec5160021_init_database.py` | 初始建表：users, jobs, recruiter_profiles, seeker_profiles, applications |
| `99186d2082a7_add_structured_resume_to_applications.py` | 为 applications 添加 structured_resume JSONB 列 |
| `1ac3bbb5967e_add_hr_agent_evaluation_fields.py` | 新增 evaluation_tasks 表；为 applications 添加 ai_* 字段；为 jobs 添加 interview_quota |

---

### 测试（`tests/`）

| 文件 | 测试数 | 覆盖范围 |
|------|--------|---------|
| `conftest.py` | — | 提供 async engine / session / client / auth_headers 夹具 |
| `test_auth_api.py` | 11 | 注册、登录、令牌刷新、me、登出 |
| `test_jobs_api.py` | 12 | 岗位 CRUD、权限、筛选、申请计数 |
| `test_applications_api.py` | 8 | 投递、权限、状态更新 |
| `test_agent_nodes.py` | 8 | LangGraph 节点单元测试（mock get_config, adispatch_custom_event） |
| `test_agent_service.py` | 8 | AgentService 单元测试（trigger/get_status/confirm） |
| `test_agent_api.py` | 9 | Agent API 集成测试 |
| `test_intent_recognition.py` | 9 | IntentResult schema 验证 + DeepSeek recognize_intent mock 测试 |
| `test_conversation_nodes.py` | 10 | 对话节点测试（intent/help/unknown/dispatch/feedback/route） |
| `test_chat_api.py` | 4 | Chat API 测试（认证、角色、验证、SSE 流） |

---

## 前端（Frontend）

### 路由 & 页面

| 路由 | 页面组件 | 布局 | 权限 |
|------|---------|------|------|
| `/login` | `LoginPage` | 无 | 公开 |
| `/register` | `RegisterPage` | 无 | 公开 |
| `/jobs` | `JobMarketPage` | `SeekerLayout` | 公开 |
| `/jobs/:id` | `JobDetailPage` | `SeekerLayout` | 公开 |
| `/apply/:jobId` | `ApplyPage` | `SeekerLayout` | job_seeker |
| `/my-applications` | `MyApplicationsPage` | `SeekerLayout` | job_seeker |
| `/dashboard` | `JobDashboardPage` | `RecruiterLayout` | recruiter |
| `/dashboard/post` | `PostJobPage` | `RecruiterLayout` | recruiter |
| `/dashboard/applicants/:jobId` | `ApplicantsPage` | `RecruiterLayout` | recruiter |
| `/dashboard/evaluation/:taskId` | `EvaluationResultPage` | `RecruiterLayout` | recruiter |

**路由守卫**：`ProtectedRoute({ children, role? })` — 未登录→跳转 `/login`；角色不匹配→跳转 `/`。

---

### 类型定义（`features/*/types/`）

#### `auth.ts`

```ts
type UserRole = "job_seeker" | "recruiter"
interface User         { id, email, name, role, phone?, avatar_url?, is_active }
interface AuthResponse { access_token, refresh_token, token_type, expires_in, user }
interface LoginData    { email, password }
interface RegisterData { email, password, name, role, phone? }
```

#### `job.ts`

```ts
type WorkType = "remote" | "onsite" | "hybrid"
type JobStatus = "draft" | "active" | "closed"
interface Job              { id, recruiter_id, title, description, salary_min?, salary_max?,
                             location?, work_type, skills_required, status, created_at, updated_at,
                             recruiter_name?, applications_count? }
interface PaginatedResponse<T> { total, page, page_size, items: T[] }
interface JobListParams    { keyword?, work_type?, status?, page?, page_size? }
interface CreateJobPayload { title, description, location?, work_type?, salary_min?, salary_max?, skills_required }
```

#### `application.ts`

```ts
type ApplicationStatus = "pending" | "interview" | "rejected" | "hired"
interface StructuredResume  { name, work_experience_years, education_level?, contact, work_experience,
                              project_experience, education, certificates, skills, self_evaluation? }
interface Applicant         { id, applicant_name, resume_text, cover_letter?, structured_resume?, status,
                              ai_score?, ai_evaluation?, ai_decision?, ai_decision_reason?, ai_evaluated_at? }
interface MyApplication     { id, job_id, job_title, company_name?, resume_text, cover_letter?, status, created_at }
interface CreateApplicationPayload { job_id?, resume_text, structured_resume, cover_letter? }
interface DimensionScore    { name, score, weight, reason }                        // Phase 2
interface EvaluationDetail  { application_id, applicant_name, ai_score, ai_evaluation, ai_decision, ai_decision_reason } // Phase 2
```

---

### API 客户端（`features/*/api/`）

#### 认证

| 函数 | 方法 | 端点 |
|------|------|------|
| `loginUser(data: LoginData)` | POST | `/auth/login` |
| `registerUser(data: RegisterData)` | POST | `/auth/register` |

#### 岗位

| 函数 | 方法 | 端点 |
|------|------|------|
| `getJobs(params: JobListParams)` | GET | `/jobs/` |
| `getJobById(id: string)` | GET | `/jobs/{id}` |
| `updateJobStatus(jobId, status)` | PATCH | `/jobs/{jobId}/status` |
| `createJob(payload: CreateJobPayload)` | POST | `/jobs/` |
| `deleteJob(id: string)` | DELETE | `/jobs/{jobId}` |

#### 投递

| 函数 | 方法 | 端点 |
|------|------|------|
| `createApplication(payload, force?)` | POST | `/applications/` |
| `getMyApplications(params?)` | GET | `/applications/my` |
| `getApplicationsByJob(jobId)` | GET | `/applications/job/{jobId}` |
| `updateApplicationStatus(applicantId, status)` | PATCH | `/applications/{applicantId}/status` |

#### 对话助手（Phase 2）

| 函数 | 方法 | 端点 |
|------|------|------|
| `getEvaluationTask(taskId)` | GET | `/agent/task/{taskId}` |
| `confirmEvaluation(taskId, decisions?)` | POST | `/agent/confirm/{taskId}` |
| `sendChatMessage(message, onEvent, onError, onDone)` | POST | `/chat/send` (SSE) |

#### 共享 HTTP 层（`shared/api/`）

- **`client.ts`** — Axios 实例（baseURL=`/api`，60s 超时）；请求拦截器注入 Bearer token；响应拦截器实现 401 自动刷新 + 请求队列。
- **`error.ts`** — `getApiErrorMessage(error, fallback): string` 提取 API 错误信息。

---

### React Query Hooks（`features/*/hooks/`）

| Hook | 类型 | 说明 |
|------|------|------|
| `useJobsQuery(params?)` | Query | 岗位列表 |
| `useJobDetailQuery(jobId?)` | Query | 岗位详情（jobId 为空时 disabled） |
| `useRecruiterJobsQuery(recruiterId?)` | Query | 招聘者的岗位 |
| `useUpdateJobStatusMutation()` | Mutation | 变更岗位状态 → 刷新 jobs 缓存 |
| `useCreateJobMutation()` | Mutation | 创建岗位 → 刷新 jobs 缓存 |
| `useDeleteJobMutation()` | Mutation | 删除岗位 → 刷新 jobs 缓存 |
| `useMyApplicationsQuery(params?)` | Query | 我的投递 |
| `useApplicantsByJobQuery(jobId?)` | Query | 岗位投递者 |
| `useCreateApplicationMutation()` | Mutation | 投递简历 → 刷新 applications 缓存 |
| `useUpdateApplicationStatusMutation(jobId?)` | Mutation | 更新投递状态 → 刷新 applications 缓存 |
| `useEvaluationTaskQuery(taskId?)` | Query | 评估任务详情（running 时自动轮询 2s） |
| `useConfirmEvaluationMutation()` | Mutation | 确认评估结果 → 刷新 evaluation + applications 缓存 |
| `useLoginMutation()` | Mutation | 登录 → setAuth() |
| `useRegisterMutation()` | Mutation | 注册 → setAuth() |
| `useLogout()` | Helper | 清除认证 + 跳转 /login |

---

### 状态管理

**Zustand**（`features/auth/store/authStore.ts`）：

```ts
interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  setAuth: (token, refreshToken, user) => void
  clearAuth: () => void
  logout: () => void
}
// 持久化至 localStorage（key: "auth-storage"）
```

**面包屑上下文**（`shared/ui/layout/breadcrumb-context.tsx`）：

```ts
interface BreadcrumbItem { label: string; href?: string }
// BreadcrumbProvider + useBreadcrumb() — 各页面通过 useEffect 设置
```

---

### 共享 UI 组件（`shared/ui/`）

| 组件 | Props | 说明 |
|------|-------|------|
| `CategoryTabs<T>` | `categories, activeKey, onSelect` | 泛型标签页 |
| `SearchBar` | `value, onChange, onSearch, placeholder?` | 搜索栏 |
| `JobCard` | `job: Job, applied?` | 岗位卡片 |
| `JobStatusBadge` | `status: JobStatus, className?` | 岗位状态标签 |
| `StatusBadge` | `status: ApplicationStatus, className?` | 投递状态标签 |
| `StatCard` | `icon, value, label, iconColor?` | 统计卡片 |
| `StepForm` | `steps, currentStep` | 步骤表单指示器 |
| `EmptyState` | `icon?, message, action?` | 空状态反馈 |
| `ErrorState` | `message, onRetry?` | 错误状态反馈 |
| `LoadingState` | `message?, rows?` | 加载状态骨架屏 |
| `SeekerLayout` | 无（含面包屑 + 顶栏导航） | 求职者布局 |
| `RecruiterLayout` | 无（含面包屑 + 侧栏导航） | 招聘者布局 |

#### 对话助手组件（`features/chat/components/`，Phase 2）

| 组件 | Props | 说明 |
|------|-------|------|
| `ChatBubble` | 无 | 浮动气泡入口（右下角） |
| `ChatWindow` | `onClose` | 对话窗口（header + messages + input） |
| `ChatMessages` | `messages: ChatMessage[]` | 消息列表（自动滚动到底部） |
| `ChatInput` | `onSend, disabled` | 输入框 + 发送按钮 |
| `AssistantMessage` | `message: ChatMessage` | 助手消息气泡（含进度/卡片） |
| `ProgressMessage` | `progress: ProgressInfo` | 进度指示器（旋转 + 计数） |
| `EvaluationCard` | `card: ChatCard` | 可点击的评估摘要卡片 |

#### 对话助手 Hook（`features/chat/hooks/`）

| Hook | 说明 |
|------|------|
| `useChat()` | 管理 messages/isProcessing/sendMessage/disconnect/clearMessages；消费 SSE 事件流更新消息 |

#### 对话助手类型（`features/chat/types/chat.ts`）

```ts
interface ChatMessage  { role: "user"|"assistant", content, cards?: ChatCard[], progress?: ProgressInfo, timestamp }
interface ChatCard     { type: "evaluation_summary", task_id, job_title, total_count, recommended_count, rejected_count, result_page_url }
interface ProgressInfo { status, evaluated_count?, total_count? }
```

shadcn/ui 原子组件（`components/ui/`，18 个）：avatar, badge, breadcrumb, button, card, checkbox, dialog, dropdown-menu, form, input, label, pagination, select, separator, skeleton, table, tabs, textarea。

---

### 常量（`shared/constants/`）

| 文件 | 内容 |
|------|------|
| `applicationStatus.ts` | `ApplicationStatus` 类型 + `JOB_STATUS_MAP` / `APPLICATION_STATUS_MAP`（label + className 映射） |
| `queryKeys.ts` | TanStack Query key 工厂：`jobs.{all, list, detail, recruiterList}`, `applications.{mine, byJob}`, `evaluation.{task}` |

---

## 构建与开发命令

| 操作 | 命令 |
|------|------|
| 后端环境 | `cd backend && uv venv --python 3.12 && source .venv/bin/activate && uv pip install -r requirements.txt` |
| 前端环境 | `cd frontend && npm install` |
| 前端开发 | `cd frontend && npm run dev`（端口 3001，代理 /api → :8000） |
| 后端启动 | `cd backend && uvicorn app.main:app --reload --port 8000` |
| 类型检查 | `cd backend && uv run mypy --strict app/` |
| 运行测试 | `cd backend && uv run pytest tests/ -v` |

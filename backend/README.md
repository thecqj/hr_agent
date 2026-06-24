# HR Agent Backend

基于 **FastAPI + SQLAlchemy 2.x + PostgreSQL** 的后端服务，面向招聘/求职流程管理。当前版本已保留既有 API 契约（`/api/v1/*` 路径与请求/响应字段），AI 相关接口使用占位实现，便于后续平滑回填。

## 1. 主要功能

- 用户认证与角色管理（求职者 `job_seeker` / 招聘者 `recruiter`）
- 岗位发布、查询、更新、删除、状态变更
- 简历投递与投递状态流转
- 简历解析接口（占位）
- 智能体接口（占位，含 SSE chat）

## 2. 技术栈

- Web: FastAPI, Uvicorn
- DB: PostgreSQL, SQLAlchemy 2.x, psycopg
- Migration: Alembic
- Auth: JWT（python-jose）, bcrypt
- Validation/Config: pydantic, pydantic-settings
- Test: pytest, pytest-asyncio

---

## 3. 依赖安装（推荐 uv）

> 下面命令默认在 `backend/` 目录执行。

### 3.1 安装 uv

macOS（Homebrew）：

```bash
brew install uv
```

### 3.2 创建虚拟环境并安装依赖

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

## 4. 数据库配置

## 4.1 安装 PostgreSQL（macOS）

```bash
brew install postgresql@18
brew services start postgresql@18
```

## 4.2 安装 pgvector

```bash
brew install pgvector
```

> 若 Homebrew 安装后未自动可用，请确认 PostgreSQL 的 extension 目录配置正确。

## 4.3 创建数据库与账号（示例）

项目默认连接串：
`postgresql+psycopg://app:password@localhost:5432/jobboard`

可执行：

```bash
psql postgres -c "CREATE ROLE app WITH LOGIN PASSWORD 'password';"
psql postgres -c "CREATE DATABASE jobboard OWNER app;"
psql jobboard -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## 4.4 配置环境变量

```bash
cp .env.example .env
```

按需修改 `.env` 中的：
- `DATABASE_URL`
- `SECRET_KEY`
- 其他配置项

## 4.5 Alembic 同步数据库结构

```bash
alembic upgrade head
```

---

## 5. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

启动后可访问：
- 健康检查：`http://127.0.0.1:8000/health`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`

---

## 6. 运行测试

```bash
pytest -q
```

---

## 7. 说明

- AI 相关接口当前返回固定占位结果，不依赖外部大模型。
- 后续恢复 AI 能力时，优先替换 `app/services/placeholder_ai.py` 及相关 service 实现，尽量不改动 API 层契约。

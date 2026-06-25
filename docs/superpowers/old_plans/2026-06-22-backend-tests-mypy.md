# 后端单元测试 + mypy 修复 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为后端所有 API 接口新增集成测试，并修复 mypy --strict 配置问题

**Architecture:** 使用 pytest-asyncio + httpx.AsyncClient 对 FastAPI 进行 API 级集成测试。数据库采用本地 PostgreSQL 测试库（jobboard_test），每个测试用例通过事务回滚隔离。mypy 问题通过在 mypy.ini 中添加 `explicit_package_bases = True` 解决。

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), pytest, pytest-asyncio, httpx, PostgreSQL

## Global Constraints

- Python 版本 3.12，使用 `uv run` 执行命令
- 类型检查命令：`cd backend && uv run mypy --strict app/`
- 测试命令：`cd backend && uv run pytest tests/ -v`
- Strict Type Hints：所有代码必须有显式参数和返回类型注解
- Mypy Strict：代码必须通过 `mypy --strict`
- Layer Separation：DB 层用 SQLAlchemy 2.0 typed style，API 层用 Pydantic v2
- 数据库：本地 PostgreSQL，测试库名 `jobboard_test`

---

## File Structure

| 文件 | 职责 |
|------|------|
| `backend/tests/conftest.py` | 全局 fixtures：engine, db session, async client, auth helpers |
| `backend/tests/test_auth_api.py` | Auth API 5 个端点 11 个测试 |
| `backend/tests/test_jobs_api.py` | Jobs API 6 个端点 12 个测试 |
| `backend/tests/test_applications_api.py` | Applications API 4 个端点 8 个测试 |
| `backend/mypy.ini` | 添加 `explicit_package_bases = True` |
| `backend/.env.example` | 添加 `TEST_DATABASE_URL` 配置项 |

---

### Task 1: 测试基础设施 — conftest.py

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Modify: `backend/.env.example` (添加 TEST_DATABASE_URL)

**Interfaces:**
- Consumes: `app.main.app` (FastAPI 实例), `app.database.get_db` (依赖注入), `app.config.settings` (配置)
- Produces:
  - `engine` (session-scoped AsyncEngine) — 连接测试库的异步引擎
  - `db_tables` (session-scoped, None) — 确保表存在
  - `db_session` (function-scoped AsyncSession) — 事务回滚隔离的测试会话
  - `client` (function-scoped httpx.AsyncClient) — 注入测试会话的 HTTP 客户端
  - `auth_headers_seeker` (function-scoped dict) — 求职者 Bearer token headers
  - `auth_headers_recruiter` (function-scoped dict) — 招聘者 Bearer token headers

- [ ] **Step 1: 创建 tests/__init__.py**

```python
```

（空文件，使 tests 成为 Python 包）

- [ ] **Step 2: 创建 tests/conftest.py**

```python
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base

# 导入所有模型，确保 metadata 完整注册
import app.models.application  # noqa: F401
import app.models.job  # noqa: F401
import app.models.recruiter_profile  # noqa: F401
import app.models.seeker_profile  # noqa: F401
import app.models.user  # noqa: F401


TEST_DATABASE_URL: str = "postgresql+psycopg://app:password@localhost:5432/jobboard_test"


@pytest.fixture(scope="session")
def engine() -> AsyncEngine:
    """连接测试库的 async engine"""
    return create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db_tables(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """session 级：建表（仅一次）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """function 级：每个测试用事务回滚隔离"""
    connection = await engine.connect()
    transaction = await connection.begin()

    session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session

    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """注入测试会话的 httpx AsyncClient"""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _register_and_get_headers(client: AsyncClient, email: str, role: str) -> dict[str, str]:
    """同步辅助：注册用户并返回 Bearer headers（在测试中 await 调用）"""
    # 这个辅助不能是 async fixture，因为它需要 client 参数
    # 实际注册逻辑在下面的 async fixtures 中
    return {}


@pytest_asyncio.fixture
async def auth_headers_seeker(client: AsyncClient) -> dict[str, str]:
    """注册一个求职者，返回 Bearer token headers"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "seeker@test.com",
            "password": "testpass123",
            "name": "测试求职者",
            "role": "job_seeker",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest_asyncio.fixture
async def auth_headers_recruiter(client: AsyncClient) -> dict[str, str]:
    """注册一个招聘者，返回 Bearer token headers"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "recruiter@test.com",
            "password": "testpass123",
            "name": "测试招聘者",
            "role": "recruiter",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}
```

- [ ] **Step 3: 更新 .env.example，添加 TEST_DATABASE_URL**

在 `backend/.env.example` 末尾添加：

```
# Test Database
TEST_DATABASE_URL=postgresql+psycopg://app:password@localhost:5432/jobboard_test
```

- [ ] **Step 4: 确认测试库存在并运行一个冒烟测试**

运行: `cd /Users/bytedance/my_code/hr_agent/backend && uv run python -c "from tests.conftest import TEST_DATABASE_URL; print('OK:', TEST_DATABASE_URL)"`

Expected: `OK: postgresql+psycopg://app:password@localhost:5432/jobboard_test`

- [ ] **Step 5: 提交**

```bash
cd /Users/bytedance/my_code/hr_agent
git add backend/tests/__init__.py backend/tests/conftest.py backend/.env.example
git commit -m "feat: add test infrastructure with transaction-rollback conftest"
```

---

### Task 2: Auth API 测试

**Files:**
- Create: `backend/tests/test_auth_api.py`

**Interfaces:**
- Consumes: `client` fixture, `auth_headers_seeker` fixture
- Produces: 无（纯消费方）

- [ ] **Step 1: 编写 test_auth_api.py**

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_seeker(client: AsyncClient) -> None:
    """注册求职者成功"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "seeker_new@test.com",
            "password": "testpass123",
            "name": "新求职者",
            "role": "job_seeker",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "job_seeker"
    assert data["user"]["email"] == "seeker_new@test.com"


@pytest.mark.asyncio
async def test_register_recruiter(client: AsyncClient) -> None:
    """注册招聘者成功"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "recruiter_new@test.com",
            "password": "testpass123",
            "name": "新招聘者",
            "role": "recruiter",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["role"] == "recruiter"
    assert data["user"]["email"] == "recruiter_new@test.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    """重复邮箱注册失败"""
    payload = {
        "email": "dup@test.com",
        "password": "testpass123",
        "name": "重复用户",
        "role": "job_seeker",
    }
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    """登录成功"""
    # 先注册
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@test.com",
            "password": "testpass123",
            "name": "登录用户",
            "role": "job_seeker",
        },
    )
    # 再登录
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "login@test.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    """登录密码错误"""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpw@test.com",
            "password": "testpass123",
            "name": "密码测试",
            "role": "job_seeker",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@test.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """登录不存在的用户"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient) -> None:
    """刷新 token 成功"""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@test.com",
            "password": "testpass123",
            "name": "刷新测试",
            "role": "job_seeker",
        },
    )
    refresh_token = reg_resp.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient) -> None:
    """刷新 token 无效"""
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient) -> None:
    """获取当前用户信息"""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@test.com",
            "password": "testpass123",
            "name": "我的信息",
            "role": "job_seeker",
        },
    )
    token = reg_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@test.com"
    assert data["name"] == "我的信息"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient) -> None:
    """未登录访问 /me"""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient) -> None:
    """登出成功"""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@test.com",
            "password": "testpass123",
            "name": "登出用户",
            "role": "job_seeker",
        },
    )
    token = reg_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()
```

- [ ] **Step 2: 运行 auth 测试验证通过**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run pytest tests/test_auth_api.py -v`
Expected: 11 passed

- [ ] **Step 3: 提交**

```bash
cd /Users/bytedance/my_code/hr_agent
git add backend/tests/test_auth_api.py
git commit -m "test: add auth API integration tests (11 cases)"
```

---

### Task 3: Jobs API 测试

**Files:**
- Create: `backend/tests/test_jobs_api.py`

**Interfaces:**
- Consumes: `client` fixture, `auth_headers_seeker` fixture, `auth_headers_recruiter` fixture
- Produces: 无（纯消费方）

- [ ] **Step 1: 编写 test_jobs_api.py**

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_job_as_recruiter(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """招聘者创建职位成功"""
    resp = await client.post(
        "/api/v1/jobs/",
        json={
            "title": "Python 开发工程师",
            "description": "负责后端开发",
            "salary_min": 15,
            "salary_max": 30,
            "location": "北京",
            "work_type": "onsite",
            "skills_required": ["Python", "FastAPI"],
        },
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Python 开发工程师"
    assert data["status"] == "active"
    assert data["skills_required"] == ["Python", "FastAPI"]


@pytest.mark.asyncio
async def test_create_job_as_seeker_forbidden(
    client: AsyncClient, auth_headers_seeker: dict[str, str]
) -> None:
    """求职者创建职位失败"""
    resp = await client.post(
        "/api/v1/jobs/",
        json={
            "title": "不应该创建",
            "description": "测试",
            "work_type": "onsite",
        },
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_jobs_default_filter(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """列出职位 — 默认只返回 active"""
    # 创建一个 active 职位
    await client.post(
        "/api/v1/jobs/",
        json={"title": "Active Job", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    # 创建后关闭一个
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "To Close", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]
    await client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "closed"},
        headers=auth_headers_recruiter,
    )

    resp = await client.get("/api/v1/jobs/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    # 默认只返回 active
    for item in data["items"]:
        assert item["status"] == "active"


@pytest.mark.asyncio
async def test_list_jobs_keyword_search(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """列出职位 — 关键词搜索"""
    await client.post(
        "/api/v1/jobs/",
        json={"title": "Go 开发", "description": "云原生开发", "work_type": "remote"},
        headers=auth_headers_recruiter,
    )
    await client.post(
        "/api/v1/jobs/",
        json={"title": "Java 开发", "description": "企业级应用", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )

    resp = await client.get("/api/v1/jobs/", params={"keyword": "Go"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert "Go" in item["title"] or "Go" in item["description"]


@pytest.mark.asyncio
async def test_list_jobs_salary_filter(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """列出职位 — 薪资范围过滤"""
    await client.post(
        "/api/v1/jobs/",
        json={
            "title": "高薪岗位",
            "description": "desc",
            "salary_min": 30,
            "salary_max": 50,
            "work_type": "onsite",
        },
        headers=auth_headers_recruiter,
    )

    resp = await client.get("/api/v1/jobs/", params={"salary_min": 25, "salary_max": 55})
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        # 岗位 salary_max >= 过滤 salary_min 且 岗位 salary_min <= 过滤 salary_max
        if item["salary_min"] is not None and item["salary_max"] is not None:
            assert item["salary_max"] >= 25
            assert item["salary_min"] <= 55


@pytest.mark.asyncio
async def test_get_job_detail(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """获取单个职位"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "详情测试", "description": "详情desc", "work_type": "hybrid"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "详情测试"
    assert resp.json()["work_type"] == "hybrid"


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient) -> None:
    """获取不存在的职位"""
    resp = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_own_job(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """招聘者更新自己的职位"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "更新前", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/jobs/{job_id}",
        json={"title": "更新后"},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "更新后"


@pytest.mark.asyncio
async def test_update_other_job_forbidden(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """更新他人职位失败"""
    # 先用 recruiter 创建一个职位
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "别人的", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    # 注册另一个招聘者尝试更新
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "other_recruiter@test.com",
            "password": "testpass123",
            "name": "其他招聘者",
            "role": "recruiter",
        },
    )
    other_token = reg_resp.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    resp = await client.put(
        f"/api/v1/jobs/{job_id}",
        json={"title": "篡改"},
        headers=other_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_own_job(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """删除自己的职位"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "待删除", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers_recruiter)
    assert resp.status_code == 200

    # 确认已删除
    get_resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_job_forbidden(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """删除他人职位失败"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "不可删", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    # 注册另一个招聘者
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "deleter@test.com",
            "password": "testpass123",
            "name": "删除者",
            "role": "recruiter",
        },
    )
    other_headers = {"Authorization": f"Bearer {reg_resp.json()['access_token']}"}

    resp = await client.delete(f"/api/v1/jobs/{job_id}", headers=other_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_job_status(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """更新职位状态"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "状态测试", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "closed"},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"
```

- [ ] **Step 2: 运行 jobs 测试验证通过**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run pytest tests/test_jobs_api.py -v`
Expected: 12 passed

- [ ] **Step 3: 提交**

```bash
cd /Users/bytedance/my_code/hr_agent
git add backend/tests/test_jobs_api.py
git commit -m "test: add jobs API integration tests (12 cases)"
```

---

### Task 4: Applications API 测试

**Files:**
- Create: `backend/tests/test_applications_api.py`

**Interfaces:**
- Consumes: `client` fixture, `auth_headers_seeker` fixture, `auth_headers_recruiter` fixture
- Produces: 无（纯消费方）

- [ ] **Step 1: 编写 test_applications_api.py**

```python
import pytest
from httpx import AsyncClient


async def _create_job(client: AsyncClient, recruiter_headers: dict[str, str]) -> str:
    """辅助：创建一个 active 职位，返回 job_id"""
    resp = await client.post(
        "/api/v1/jobs/",
        json={
            "title": "测试岗位",
            "description": "测试描述",
            "work_type": "onsite",
        },
        headers=recruiter_headers,
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_apply_as_seeker(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """求职者投递申请成功"""
    job_id = await _create_job(client, auth_headers_recruiter)

    resp = await client.post(
        "/api/v1/applications/",
        json={
            "job_id": job_id,
            "resume_text": "我是求职者，有3年Python经验",
            "cover_letter": "期待加入",
        },
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["status"] == "pending"
    assert data["resume_text"] == "我是求职者，有3年Python经验"


@pytest.mark.asyncio
async def test_apply_as_recruiter_forbidden(
    client: AsyncClient,
    auth_headers_recruiter: dict[str, str],
) -> None:
    """招聘者投递失败"""
    # 先创建一个岗位（需要用 recruiter 自己来创建）
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "For apply test", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.post(
        "/api/v1/applications/",
        json={"job_id": job_id, "resume_text": "我不应该能投递"},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_apply_closed_job(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """投递已关闭的职位"""
    job_id = await _create_job(client, auth_headers_recruiter)

    # 关闭职位
    await client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "closed"},
        headers=auth_headers_recruiter,
    )

    resp = await client.post(
        "/api/v1/applications/",
        json={"job_id": job_id, "resume_text": "投递关闭的职位"},
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_apply_duplicate_job(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """重复投递同一职位"""
    job_id = await _create_job(client, auth_headers_recruiter)

    # 第一次投递
    resp1 = await client.post(
        "/api/v1/applications/",
        json={"job_id": job_id, "resume_text": "第一次投递"},
        headers=auth_headers_seeker,
    )
    assert resp1.status_code == 201

    # 第二次投递同一职位
    resp2 = await client.post(
        "/api/v1/applications/",
        json={"job_id": job_id, "resume_text": "第二次投递"},
        headers=auth_headers_seeker,
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_my_applications(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """查看自己的申请列表"""
    job_id = await _create_job(client, auth_headers_recruiter)

    await client.post(
        "/api/v1/applications/",
        json={"job_id": job_id, "resume_text": "我的简历"},
        headers=auth_headers_seeker,
    )

    resp = await client.get(
        "/api/v1/applications/my",
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_job_applications_as_owner(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """招聘者查看自己岗位的申请列表"""
    job_id = await _create_job(client, auth_headers_recruiter)

    await client.post(
        "/api/v1/applications/",
        json={"job_id": job_id, "resume_text": "投递申请"},
        headers=auth_headers_seeker,
    )

    resp = await client.get(
        f"/api/v1/applications/job/{job_id}",
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_job_applications_not_owner(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """非拥有者查看岗位申请列表失败"""
    job_id = await _create_job(client, auth_headers_recruiter)

    # 求职者尝试查看岗位的申请列表
    resp = await client.get(
        f"/api/v1/applications/job/{job_id}",
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_application_status(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """招聘者更新申请状态"""
    job_id = await _create_job(client, auth_headers_recruiter)

    apply_resp = await client.post(
        "/api/v1/applications/",
        json={"job_id": job_id, "resume_text": "状态更新测试"},
        headers=auth_headers_seeker,
    )
    application_id = apply_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "reviewed"},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "reviewed"
```

- [ ] **Step 2: 运行 applications 测试验证通过**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run pytest tests/test_applications_api.py -v`
Expected: 8 passed

- [ ] **Step 3: 提交**

```bash
cd /Users/bytedance/my_code/hr_agent
git add backend/tests/test_applications_api.py
git commit -m "test: add applications API integration tests (8 cases)"
```

---

### Task 5: 全量测试验证

**Files:**
- 无新增/修改

**Interfaces:**
- Consumes: 所有测试文件
- Produces: 无

- [ ] **Step 1: 运行全量测试**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run pytest tests/ -v`
Expected: 31 passed

- [ ] **Step 2: 检查测试间无状态泄漏**

再次运行确认结果一致：

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run pytest tests/ -v`
Expected: 31 passed（两次结果一致说明事务回滚隔离有效）

---

### Task 6: 修复 mypy --strict 配置

**Files:**
- Modify: `backend/mypy.ini`

**Interfaces:**
- Consumes: 无
- Produces: `cd backend && uv run mypy --strict app/` 零错误通过

- [ ] **Step 1: 修改 mypy.ini**

在 `[mypy]` 段添加 `explicit_package_bases = True`：

```ini
[mypy]
python_version = 3.12
explicit_package_bases = True
warn_unused_configs = True

# 忽略没有类型注解的第三方库
[mypy-pgvector.*]
ignore_missing_imports = True

[mypy-jose.*]
ignore_missing_imports = True
```

- [ ] **Step 2: 运行 mypy 验证**

Run: `cd /Users/bytedance/my_code/hr_agent/backend && uv run mypy --strict app/`
Expected: `Success: no issues found in 25 source files`

- [ ] **Step 3: 提交**

```bash
cd /Users/bytedance/my_code/hr_agent
git add backend/mypy.ini
git commit -m "fix: add explicit_package_bases to mypy.ini for strict mode"
```

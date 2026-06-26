from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import get_db
from app.main import app as fastapi_app
from app.models.application import Application, ApplicationStatus
from app.models.base import Base
from app.models.job import Job, JobStatus, WorkType
from app.models.user import UserRole

# 导入所有模型，确保 metadata 完整注册
import app.models.application  # noqa: F401
import app.models.job  # noqa: F401
import app.models.recruiter_profile  # noqa: F401
import app.models.seeker_profile  # noqa: F401
import app.models.user  # noqa: F401


TEST_DATABASE_URL: str = "postgresql+psycopg://app:password@localhost:5432/jobboard_test"


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """连接测试库的 async engine，session 结束后关闭"""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield eng
    await eng.dispose()


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
    """function 级：每个测试用事务回滚隔离

    使用 begin_nested() 创建 savepoint，使得服务层调用 db.commit()
    时仅释放 savepoint 而非提交真实事务，保证测试隔离。
    """
    async with engine.connect() as connection:
        transaction = await connection.begin()
        nested = await connection.begin_nested()

        session_maker = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with session_maker() as session:
            # 每次 session.commit() 后自动重新开启 savepoint
            from sqlalchemy import event

            @event.listens_for(session.sync_session, "after_commit")
            def _restart_savepoint(sync_session: object) -> None:
                nonlocal nested
                if transaction.is_active and not nested.is_active:
                    nested = connection.sync_connection.begin_nested()

            yield session

        await transaction.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """注入测试会话的 httpx AsyncClient"""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers_seeker(client: AsyncClient) -> dict[str, str]:
    """注册一个求职者，返回 Bearer token headers"""
    resp = await client.post(
        "/api/auth/register",
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
        "/api/auth/register",
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


@pytest_asyncio.fixture
async def seeker_for_application(
    client: AsyncClient,
) -> dict[str, Any]:
    """创建一个求职者用户，返回 {user_id, auth_headers}"""
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "seeker-app@test.com",
            "password": "testpass123",
            "name": "测试求职者-申请",
            "role": "job_seeker",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    return {
        "user_id": data["user"]["id"],
        "auth_headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


@pytest_asyncio.fixture
async def recruiter_with_job(
    client: AsyncClient,
    db_session: AsyncSession,
) -> dict[str, Any]:
    """创建招聘者 + 活跃岗位 + 3 份 pending 申请，返回相关信息"""
    # 创建招聘者
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "recruiter-eval@test.com",
            "password": "testpass123",
            "name": "测试招聘者-评估",
            "role": "recruiter",
        },
    )
    assert resp.status_code == 201
    recruiter_data = resp.json()
    recruiter_headers = {"Authorization": f"Bearer {recruiter_data['access_token']}"}

    # 创建岗位
    resp = await client.post(
        "/api/jobs/",
        json={
            "title": "高级前端工程师",
            "description": "负责公司核心产品的前端开发工作",
            "skills_required": ["React", "TypeScript", "CSS"],
            "location": "北京",
            "work_type": "onsite",
            "interview_quota": 2,
        },
        headers=recruiter_headers,
    )
    assert resp.status_code == 201
    job_data = resp.json()
    job_id = job_data["id"]

    # 创建 3 个不同求职者并各投递 1 份申请
    for i in range(3):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": f"seeker-eval-{i+1}@test.com",
                "password": "testpass123",
                "name": f"候选人{i+1}",
                "role": "job_seeker",
            },
        )
        assert resp.status_code == 201
        seeker_data = resp.json()
        seeker_headers = {"Authorization": f"Bearer {seeker_data['access_token']}"}

        resp = await client.post(
            "/api/applications/",
            json={
                "job_id": job_id,
                "resume_text": f"测试简历 {i+1}：有 React 和 TypeScript 经验",
                "structured_resume": {
                    "name": f"候选人{i+1}",
                    "work_experience_years": 2 + i,
                    "skills": ["React", "TypeScript"],
                    "work_experience": [],
                    "project_experience": [],
                    "education": [],
                    "certificates": [],
                },
            },
            headers=seeker_headers,
        )
        assert resp.status_code == 201

    return {
        "recruiter_headers": recruiter_headers,
        "recruiter_id": recruiter_data["user"]["id"],
        "job_id": job_id,
    }

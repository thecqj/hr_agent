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

from app.database import get_db
from app.main import app as fastapi_app
from app.models.base import Base

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

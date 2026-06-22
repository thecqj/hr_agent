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

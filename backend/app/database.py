from collections.abc import AsyncGenerator
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.base import Base

# 导入所有模型，确保 metadata 完整注册
import app.models.application  # noqa: F401
import app.models.job  # noqa: F401
import app.models.recruiter_profile  # noqa: F401
import app.models.seeker_profile  # noqa: F401
import app.models.user  # noqa: F401


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """依赖注入：请求级会话，自动提交或回滚。"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """初始化数据库（仅开发调试使用）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """删除数据库表（仅开发调试使用）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── LangGraph Checkpointer ──────────────────────────────────

_checkpointer: AsyncPostgresSaver | None = None
_pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] | None = None


async def init_checkpointer() -> AsyncPostgresSaver:
    """Initialize and return the LangGraph PostgreSQL checkpointer."""
    global _checkpointer, _pool
    # Strip SQLAlchemy driver from URL: postgresql+psycopg:// → postgresql://
    db_url = settings.DATABASE_URL.replace("+psycopg", "")
    _pool = AsyncConnectionPool(
        conninfo=db_url,
        kwargs={"row_factory": dict_row},
        open=True,
    )
    _checkpointer = AsyncPostgresSaver(conn=_pool)
    await _checkpointer.setup()
    return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer's connection pool (call on shutdown)."""
    global _checkpointer, _pool
    if _pool is not None:
        await _pool.close()
    _checkpointer = None
    _pool = None


def get_checkpointer() -> AsyncPostgresSaver:
    """Return the initialized checkpointer (call after init_checkpointer)."""
    if _checkpointer is None:
        raise RuntimeError("Checkpointer not initialized — call init_checkpointer() first")
    return _checkpointer

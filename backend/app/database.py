from collections.abc import AsyncGenerator

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

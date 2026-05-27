from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

# 从 models 中导入 Base，确保所有模型都已注册
from app.models.base import Base
# 导入所有模型，确保它们被注册到 Base.metadata
import app.models.user          # noqa: F401
import app.models.seeker_profile  # noqa: F401
import app.models.recruiter_profile  # noqa: F401
import app.models.job            # noqa: F401
import app.models.application    # noqa: F401


# 创建异步数据库引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
)

# 创建异步会话工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """依赖注入：获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """初始化数据库：创建所有表（仅开发环境使用）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """删除所有表（仅开发环境使用）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
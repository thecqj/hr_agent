from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础
    APP_NAME: str = "智能简历投递系统"
    DEBUG: bool = True
    
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://app:password@localhost:5432/jobboard"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT 认证
    SECRET_KEY: str = "dev-secret-key-change-in-production-abc123"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""
    AGENT_MODEL: str = "gpt-4o"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "resumes"
    MINIO_SECURE: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
print(f"API_KEY: {repr(settings.OPENAI_API_KEY[:10])}...")  # 只打印前10位，保护隐私
print(f"API_BASE: {repr(settings.OPENAI_API_BASE)}")
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置（本地优先，.env 覆盖）"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用基础
    APP_NAME: str = "智能简历投递系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 数据库（SQLAlchemy 2.x + psycopg）
    DATABASE_URL: str = "postgresql+psycopg://app:password@localhost:5432/jobboard"
    DATABASE_ECHO: bool = False

    # JWT 认证
    SECRET_KEY: str = "change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
        ]
    )

    # LLM Configuration
    LLM_PROVIDER: str = "deepseek"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    LLM_REQUESTS_PER_MINUTE: int = 30
    LLM_EVALUATION_RETRIES: int = 1
    LLM_BORDERLINE_RANGE: float = 10.0
    CHAT_MODEL: str = "deepseek-chat"  # model used for create_react_agent tool_call


settings = Settings()

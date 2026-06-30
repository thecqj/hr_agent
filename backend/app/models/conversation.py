"""会话索引模型"""

import uuid

from sqlalchemy import String, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """会话索引表 — 跨会话摘要/实体传递"""

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_user_active", "user_id", "is_active"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
        comment="FK → users.id",
    )
    session_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False,
        comment="= LangGraph thread_id",
    )
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
        comment="LLM 生成的会话摘要",
    )
    context_entities: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True, default=None,
        comment="结构化实体 {current_job_id, current_job_code, ...}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="会话是否活跃",
    )

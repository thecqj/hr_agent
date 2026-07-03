"""会话索引模型"""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """会话索引表 — 同一 session_id 内的摘要传递"""

    __tablename__ = "conversations"

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

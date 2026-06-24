import uuid
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy import String, Integer, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TimestampMixin


class SeekerProfile(Base, TimestampMixin):
    __tablename__ = "seeker_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    resume_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resume_vector: Mapped[Optional[Any]] = mapped_column(Vector(1536), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    education: Mapped[list[Any]] = mapped_column(JSON, default=list)
    expected_salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expected_salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    job_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # 关联
    user: Mapped["User"] = relationship("User", back_populates="seeker_profile")

    def __repr__(self) -> str:
        return f"<SeekerProfile user_id={self.user_id}>"


# 处理循环引用
if TYPE_CHECKING:
    from app.models.user import User

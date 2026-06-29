import enum
import uuid
from datetime import datetime
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy import String, Text, Enum, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, TimestampMixin


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"        # 待审核
    INTERVIEW = "interview"    # 面试中
    REJECTED = "rejected"      # 已拒绝
    HIRED = "hired"            # 已录用


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    cover_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_resume: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.PENDING,
    )

    # AI 评估结果（草稿字段，确认前不影响业务状态）
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_evaluation: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    ai_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ai_decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    applicant: Mapped["User"] = relationship("User", back_populates="applications", foreign_keys=[applicant_id])

    def __repr__(self) -> str:
        return f"<Application job={self.job_id} applicant={self.applicant_id}>"


# 处理循环引用
if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.user import User

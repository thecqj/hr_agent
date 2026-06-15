import enum
import uuid
from datetime import datetime
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy import String, Integer, Text, JSON, Enum, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TimestampMixin


class WorkType(str, enum.Enum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_vector: Mapped[Optional[Any]] = mapped_column(Vector(1536), nullable=True)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    work_type: Mapped[WorkType] = mapped_column(Enum(WorkType), default=WorkType.ONSITE)
    skills_required: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.ACTIVE)

    # 关联
    recruiter: Mapped["User"] = relationship("User", back_populates="jobs", foreign_keys=[recruiter_id])
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Job {self.title} ({self.status.value})>"


# 处理循环引用
if TYPE_CHECKING:
    from app.models.user import User
    from app.models.application import Application

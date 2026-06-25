import enum
import uuid
from typing import Optional, Any, TYPE_CHECKING

from sqlalchemy import Integer, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, TimestampMixin


class EvalTaskStatus(str, enum.Enum):
    PENDING = "pending"      # 待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    CONFIRMED = "confirmed"  # 已确认
    FAILED = "failed"        # 失败


class EvaluationTask(Base, TimestampMixin):
    __tablename__ = "evaluation_tasks"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[EvalTaskStatus] = mapped_column(
        Enum(EvalTaskStatus),
        default=EvalTaskStatus.PENDING,
    )
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    evaluated_count: Mapped[int] = mapped_column(Integer, default=0)
    result_summary: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关联
    job: Mapped["Job"] = relationship("Job", foreign_keys=[job_id])
    triggered_by_user: Mapped["User"] = relationship(
        "User", foreign_keys=[triggered_by]
    )

    def __repr__(self) -> str:
        return f"<EvaluationTask job={self.job_id} status={self.status.value}>"


# 处理循环引用
if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.user import User

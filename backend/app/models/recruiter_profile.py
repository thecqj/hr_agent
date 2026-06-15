import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class RecruiterProfile(Base, TimestampMixin):
    __tablename__ = "recruiter_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    company_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # 关联
    user: Mapped["User"] = relationship("User", back_populates="recruiter_profile")

    def __repr__(self) -> str:
        return f"<RecruiterProfile company={self.company_name}>"


# 处理循环引用
if TYPE_CHECKING:
    from app.models.user import User

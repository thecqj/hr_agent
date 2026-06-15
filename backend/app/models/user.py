import enum
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Enum, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    JOB_SEEKER = "job_seeker"    # 求职者
    RECRUITER = "recruiter"      # 招聘者


class User(Base, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 关联关系
    seeker_profile: Mapped[Optional["SeekerProfile"]] = relationship(
        "SeekerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    recruiter_profile: Mapped[Optional["RecruiterProfile"]] = relationship(
        "RecruiterProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="applicant",
        foreign_keys="Application.applicant_id",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="recruiter",
        foreign_keys="Job.recruiter_id",
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"


# 处理循环引用
if TYPE_CHECKING:
    from app.models.seeker_profile import SeekerProfile
    from app.models.recruiter_profile import RecruiterProfile
    from app.models.application import Application
    from app.models.job import Job

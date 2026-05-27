import enum
from sqlalchemy import Column, String, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    JOB_SEEKER = "job_seeker"    # 求职者
    RECRUITER = "recruiter"      # 招聘者


class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # 关联关系
    seeker_profile = relationship(
        "SeekerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    recruiter_profile = relationship(
        "RecruiterProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    applications = relationship(
        "Application",
        back_populates="applicant",
        foreign_keys="Application.applicant_id",
    )
    jobs = relationship(
        "Job",
        back_populates="recruiter",
        foreign_keys="Job.recruiter_id",
    )
    
    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"
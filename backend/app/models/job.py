import enum
from sqlalchemy import Column, String, Integer, Text, JSON, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
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
    
    recruiter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    requirement_vector = Column(Vector(1536), nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    location = Column(String(200), nullable=True)
    work_type = Column(Enum(WorkType), default=WorkType.ONSITE)
    skills_required = Column(JSON, default=list)
    status = Column(Enum(JobStatus), default=JobStatus.ACTIVE)
    
    # 关联
    recruiter = relationship("User", back_populates="jobs", foreign_keys=[recruiter_id])
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Job {self.title} ({self.status.value})>"
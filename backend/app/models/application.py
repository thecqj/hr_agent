import enum
from sqlalchemy import Column, String, Text, Float, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
from sqlalchemy.dialects.postgresql import JSONB

class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"        # 待查看
    REVIEWED = "reviewed"      # 已查看
    INTERVIEW = "interview"    # 面试中
    REJECTED = "rejected"      # 不合适
    HIRED = "hired"            # 已录用


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    applicant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_text = Column(Text, nullable=False)         # 投递时的简历快照
    cover_letter = Column(Text, nullable=True)         # 求职信
    match_score = Column(Float, nullable=True)         # 智能匹配度 0-1
    ai_suggestions = Column(Text, nullable=True)       # AI 优化建议
    structured_resume = Column(JSONB, nullable=True)  # 结构化简历数据
    status = Column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.PENDING,
    )
    
    # 关联
    job = relationship("Job", back_populates="applications")
    applicant = relationship("User", back_populates="applications", foreign_keys=[applicant_id])
    
    def __repr__(self):
        return f"<Application job={self.job_id} applicant={self.applicant_id}>"
from sqlalchemy import Column, String, Integer, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class SeekerProfile(Base, TimestampMixin):
    __tablename__ = "seeker_profiles"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    resume_text = Column(Text, nullable=True)                    # 简历原始文本
    resume_vector = Column(Vector(1536), nullable=True)  # pgvector 的 Vector# 简历向量
    skills = Column(JSON, default=list)                          # ["Python", "React"]
    experience_years = Column(Integer, default=0)
    education = Column(JSON, default=list)                       # 教育经历
    expected_salary_min = Column(Integer, nullable=True)
    expected_salary_max = Column(Integer, nullable=True)
    job_preferences = Column(JSON, default=dict)                 # {"city": "上海", "remote": True}
    
    # 关联
    user = relationship("User", back_populates="seeker_profile")
    
    def __repr__(self):
        return f"<SeekerProfile user_id={self.user_id}>"
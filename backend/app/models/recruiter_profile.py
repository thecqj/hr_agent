from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class RecruiterProfile(Base, TimestampMixin):
    __tablename__ = "recruiter_profiles"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    company_name = Column(String(200), nullable=True)
    company_description = Column(Text, nullable=True)
    company_logo_url = Column(String(500), nullable=True)
    verified = Column(Boolean, default=False)
    
    # 关联
    user = relationship("User", back_populates="recruiter_profile")
    
    def __repr__(self):
        return f"<RecruiterProfile company={self.company_name}>"
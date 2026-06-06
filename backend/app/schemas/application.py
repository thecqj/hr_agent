import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_serializer

from app.models.application import ApplicationStatus
from app.schemas.resume import StructuredResume


class ApplicationCreateRequest(BaseModel):
    """投递申请请求"""

    job_id: str = Field(..., description="岗位ID")
    resume_text: str = Field(..., min_length=1, description="简历文本内容")
    structured_resume: Optional[StructuredResume] = Field(None, description="结构化简历（可选）")
    cover_letter: Optional[str] = Field(None, description="求职信（可选）")


class ApplicationStatusUpdateRequest(BaseModel):
    """更新申请状态请求"""

    status: ApplicationStatus = Field(..., description="新状态")


class ApplicationResponse(BaseModel):
    """申请响应"""

    id: str
    job_id: str
    applicant_id: str
    applicant_name: Optional[str] = None
    job_title: Optional[str] = None
    resume_text: str
    cover_letter: Optional[str] = None
    match_score: Optional[float] = None
    ai_suggestions: Optional[str] = None
    structured_resume: Optional[dict] = None
    status: ApplicationStatus
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "job_id", "applicant_id")
    def serialize_uuid(self, value: uuid.UUID | str, _info) -> str:
        return str(value)


class ApplicationListResponse(BaseModel):
    """申请列表响应"""

    total: int
    items: list[ApplicationResponse]

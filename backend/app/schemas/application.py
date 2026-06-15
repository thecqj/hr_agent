import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, field_serializer

from app.models.application import ApplicationStatus


class ContactInfo(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    wechat: Optional[str] = None
    other: Optional[str] = None


class WorkExperience(BaseModel):
    company: str
    position: str
    start_date: str
    end_date: Optional[str] = None
    description: str


class ProjectExperience(BaseModel):
    name: str
    role: str
    start_date: str
    end_date: Optional[str] = None
    description: str
    technologies: list[str] = []


class Education(BaseModel):
    school: str
    major: str
    degree: str
    start_date: str
    end_date: Optional[str] = None


class Certificate(BaseModel):
    name: str
    date: Optional[str] = None


class StructuredResume(BaseModel):
    name: str
    work_experience_years: int = 0
    education_level: Optional[str] = None
    contact: ContactInfo = ContactInfo()
    work_experience: list[WorkExperience] = []
    project_experience: list[ProjectExperience] = []
    education: list[Education] = []
    certificates: list[Certificate] = []
    skills: list[str] = []
    self_evaluation: Optional[str] = None


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
    structured_resume: Optional[dict[str, Any]] = None
    status: ApplicationStatus
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "job_id", "applicant_id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class ApplicationListResponse(BaseModel):
    """申请列表响应"""

    total: int
    page: int
    page_size: int
    items: list[ApplicationResponse]

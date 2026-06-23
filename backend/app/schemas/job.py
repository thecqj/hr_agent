import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, field_serializer

from app.models.job import JobStatus, WorkType


class JobCreateRequest(BaseModel):
    """创建岗位请求"""

    title: str = Field(..., min_length=1, max_length=200, description="岗位标题")
    description: str = Field(..., min_length=1, description="岗位描述（JD）")
    salary_min: Optional[int] = Field(None, description="最低薪资（K）")
    salary_max: Optional[int] = Field(None, description="最高薪资（K）")
    location: Optional[str] = Field(None, description="工作地点")
    work_type: WorkType = Field(default=WorkType.ONSITE, description="工作类型")
    skills_required: list[str] = Field(default_factory=list, description="所需技能列表")


class JobUpdateRequest(BaseModel):
    """更新岗位请求"""

    title: Optional[str] = Field(None, min_length=1, max_length=200, description="岗位标题")
    description: Optional[str] = Field(None, min_length=1, description="岗位描述")
    salary_min: Optional[int] = Field(None, description="最低薪资")
    salary_max: Optional[int] = Field(None, description="最高薪资")
    location: Optional[str] = Field(None, description="工作地点")
    work_type: Optional[WorkType] = Field(None, description="工作类型")
    skills_required: Optional[list[str]] = Field(None, description="所需技能列表")


class JobStatusUpdateRequest(BaseModel):
    """修改岗位状态请求"""

    status: JobStatus = Field(..., description="岗位状态")


class JobResponse(BaseModel):
    id: str
    recruiter_id: str
    title: str
    description: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    location: Optional[str] = None
    work_type: WorkType
    skills_required: list[str]
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    recruiter_name: Optional[str] = None
    applications_count: int = 0

    model_config = {"from_attributes": True}

    @field_serializer("id", "recruiter_id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class JobListResponse(BaseModel):
    """岗位列表响应（带分页）"""

    total: int
    page: int
    page_size: int
    items: list[JobResponse]

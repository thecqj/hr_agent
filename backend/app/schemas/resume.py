import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer

from app.schemas.application import StructuredResume


class ResumeListItem(BaseModel):
    """简历列表项（不含文件数据和结构化数据）"""
    id: str
    name: str
    file_name: str
    file_type: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class ResumeResponse(BaseModel):
    """简历详情响应"""
    id: str
    user_id: str
    name: str
    file_name: str
    file_type: str
    parsed_text: Optional[str] = None
    structured_data: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("id", "user_id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class ResumeListResponse(BaseModel):
    """简历列表响应"""
    total: int
    items: list[ResumeListItem]


class ResumeCreateRequest(BaseModel):
    """创建简历请求（上传保存）"""
    name: str = Field(..., min_length=1, max_length=100, description="简历名称")


class ResumeUpdateRequest(BaseModel):
    """更新简历请求"""
    name: str = Field(..., min_length=1, max_length=100, description="简历名称")


class ParseResumeResponse(BaseModel):
    """简历解析响应（不保存，仅用于填充表单）"""
    parsed_text: str
    structured_data: StructuredResume
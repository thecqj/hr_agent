import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, BeforeValidator, Field
from typing_extensions import Annotated

from app.schemas.application import StructuredResume


def coerce_uuid(value: uuid.UUID | str) -> str:
    """将 UUID 对象或字符串统一转为 str，解决 Pydantic v2 from_attributes 校验问题"""
    return str(value)


ResumeId = Annotated[str, BeforeValidator(coerce_uuid)]
"""自动将 uuid.UUID → str 的字段类型"""


class ResumeListItem(BaseModel):
    """简历列表项（不含文件数据和结构化数据）"""
    id: ResumeId
    name: str
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeResponse(BaseModel):
    """简历详情响应"""
    id: ResumeId
    user_id: ResumeId
    name: str
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    parsed_text: Optional[str] = None
    structured_data: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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


class ResumeUpdateFullRequest(BaseModel):
    """更新简历完整信息请求"""
    name: str = Field(..., min_length=1, max_length=100, description="简历名称")
    parsed_text: Optional[str] = Field(None, description="解析后的纯文本")
    structured_data: Optional[dict[str, Any]] = Field(None, description="结构化简历数据")


class ParseResumeResponse(BaseModel):
    """简历解析响应（不保存，仅用于填充表单）"""
    parsed_text: str
    structured_data: StructuredResume
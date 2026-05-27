from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from app.models.user import UserRole


# ========== 请求模型 ==========

class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码（6-128位）")
    name: str = Field(..., min_length=1, max_length=100, description="姓名/昵称")
    role: UserRole = Field(..., description="用户角色：job_seeker（求职者）或 recruiter（招聘者）")
    phone: Optional[str] = Field(None, description="手机号（可选）")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if isinstance(v, str):
            try:
                return UserRole(v)
            except ValueError:
                raise ValueError(f'角色必须是 {[r.value for r in UserRole]} 之一')
        return v


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class TokenRefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


# ========== 响应模型 ==========

class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    id: str
    email: str
    name: str
    role: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}
    


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    detail: Optional[str] = None
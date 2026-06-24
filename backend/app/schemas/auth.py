from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.utils.security import MAX_BCRYPT_PASSWORD_BYTES


class UserRegisterRequest(BaseModel):
    """用户注册请求"""

    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码（6-128位）")
    name: str = Field(..., min_length=1, max_length=100, description="姓名/昵称")
    role: UserRole = Field(..., description="用户角色：job_seeker 或 recruiter")
    phone: Optional[str] = Field(None, description="手机号（可选）")

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
            raise ValueError(
                f"密码过长：bcrypt 最多支持 {MAX_BCRYPT_PASSWORD_BYTES} 字节（UTF-8）"
            )
        return value

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: object) -> UserRole:
        if isinstance(value, UserRole):
            return value
        try:
            return UserRole(str(value))
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"角色必须是 {[r.value for r in UserRole]} 之一") from exc


class UserLoginRequest(BaseModel):
    """用户登录请求"""

    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class TokenRefreshRequest(BaseModel):
    """刷新令牌请求"""

    refresh_token: str = Field(..., description="刷新令牌")


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


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str
    detail: Optional[str] = None

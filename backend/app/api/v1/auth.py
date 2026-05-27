from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserInfoResponse,
    MessageResponse,
)
from app.services import auth_service
from app.api.deps import get_required_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=dict, summary="用户注册")
async def register(
    data: UserRegisterRequest = Body(..., description="注册信息"),
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册接口
    
    - **email**: 邮箱地址（唯一）
    - **password**: 密码（6-128位）
    - **name**: 姓名/昵称
    - **role**: 角色，job_seeker（求职者）或 recruiter（招聘者）
    - **phone**: 手机号（可选）
    """
    return await auth_service.register_user(db, data)


@router.post("/login", response_model=dict, summary="用户登录")
async def login(
    data: UserLoginRequest = Body(..., description="登录信息"),
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录接口
    
    返回 access_token 和 refresh_token。
    access_token 用于访问其他接口，有效期 30 分钟。
    refresh_token 用于刷新令牌，有效期 7 天。
    """
    return await auth_service.login_user(db, data.email, data.password)


@router.post("/refresh", response_model=dict, summary="刷新令牌")
async def refresh_token(
    data: TokenRefreshRequest = Body(..., description="刷新令牌"),
    db: AsyncSession = Depends(get_db),
):
    """使用 refresh_token 获取新的令牌对"""
    return await auth_service.refresh_access_token(db, data.refresh_token)


@router.get("/me", response_model=UserInfoResponse, summary="获取当前用户信息")
async def get_me(
    current_user: User = Depends(get_required_user),
):
    """获取当前登录用户的信息"""
    return UserInfoResponse.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse, summary="退出登录")
async def logout(
    current_user: User = Depends(get_required_user),
):
    """
    退出登录
    
    注意：JWT 是无状态的，真正的登出需要客户端删除令牌。
    这里只是一个示意端点，未来可以加入黑名单机制。
    """
    return MessageResponse(
        message="已退出登录",
        detail="请在客户端删除存储的令牌"
    )
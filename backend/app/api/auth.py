from typing import Any, Dict

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_required_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    MessageResponse,
    TokenRefreshRequest,
    UserInfoResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=Dict[str, Any], summary="用户注册", status_code=201)
async def register(
    data: UserRegisterRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await auth_service.register_user(db, data)


@router.post("/login", response_model=Dict[str, Any], summary="用户登录")
async def login(
    data: UserLoginRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await auth_service.login_user(db, data.email, data.password)


@router.post("/refresh", response_model=Dict[str, Any], summary="刷新令牌")
async def refresh_token(
    data: TokenRefreshRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    return await auth_service.refresh_access_token(db, data.refresh_token)


@router.get("/me", response_model=UserInfoResponse, summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_required_user)) -> UserInfoResponse:
    return UserInfoResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        phone=current_user.phone,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
    )


@router.post("/logout", response_model=MessageResponse, summary="退出登录")
async def logout(current_user: User = Depends(get_required_user)) -> MessageResponse:
    return MessageResponse(
        message="已退出登录",
        detail="请在客户端删除存储的令牌",
    )

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import get_current_user
from app.models.user import User

# OAuth2 方案：从请求头 Authorization: Bearer <token> 中提取令牌
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,  # 允许未登录访问某些接口
)


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """获取当前用户（可选，未登录也不报错）"""
    if not token:
        return None
    
    try:
        return await get_current_user(db, token)
    except HTTPException:
        return None


async def get_required_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前用户（必须登录，否则报错）"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return await get_current_user(db, token)


def require_role(*roles: str):
    """角色权限装饰器工厂：限制只有指定角色才能访问"""
    async def role_checker(current_user: User = Depends(get_required_user)):
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要以下角色之一：{roles}"
            )
        return current_user
    return role_checker
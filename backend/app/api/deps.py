from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import get_current_user
from app.models.user import User

# 使用 HTTPBearer，Swagger 会出现简单的输入框
security = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """获取当前用户（可选，未登录也不报错）"""
    if not credentials:
        return None
    
    token = credentials.credentials
    try:
        return await get_current_user(db, token)
    except HTTPException:
        return None


async def get_required_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前用户（必须登录，否则报错）"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return await get_current_user(db, credentials.credentials)


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
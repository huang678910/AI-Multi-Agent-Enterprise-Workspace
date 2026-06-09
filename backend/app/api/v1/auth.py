"""认证 API — 注册 / 登录 / 刷新"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from app.services.auth_service import AuthService
from app.core.security import decode_access_token, create_access_token
from app.core.exceptions import UnauthorizedException
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册，返回 JWT token"""
    return await AuthService(db).register(request)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录，返回 JWT token"""
    return await AuthService(db).login(request)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """使用 Refresh Token 获取新的 Access Token"""
    try:
        payload = decode_access_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid refresh token")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token payload")
    except JWTError:
        raise UnauthorizedException("Invalid or expired refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or deactivated")

    access_token = create_access_token(str(user.id))
    return TokenResponse(access_token=access_token)

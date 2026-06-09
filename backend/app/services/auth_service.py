"""认证服务 — 注册 / 登录"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.exceptions import BadRequestException, UnauthorizedException


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, request: RegisterRequest) -> TokenResponse:
        # 检查邮箱是否已存在
        result = await self.db.execute(select(User).where(User.email == request.email))
        if result.scalar_one_or_none():
            raise BadRequestException("Email already registered")

        # 检查用户名是否已存在
        result = await self.db.execute(select(User).where(User.username == request.username))
        if result.scalar_one_or_none():
            raise BadRequestException("Username already taken")

        user = User(
            email=request.email,
            username=request.username,
            hashed_password=hash_password(request.password),
        )
        self.db.add(user)
        await self.db.flush()

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def login(self, request: LoginRequest) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(request.password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

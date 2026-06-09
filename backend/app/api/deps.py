"""FastAPI 依赖注入"""

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import User
from app.models.workspace import WorkspaceMember, MemberRole


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Authorization Header 解析 JWT 并返回当前用户"""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedException("Invalid authorization header format")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token payload")
    except JWTError:
        raise UnauthorizedException("Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException("User not found")
    if not user.is_active:
        raise UnauthorizedException("User account is deactivated")
    return user


async def require_workspace_role(
    workspace_id: str,
    current_user: User,
    min_role: str,
    db: AsyncSession,
) -> WorkspaceMember:
    """检查当前用户是否是工作区成员且角色级别满足要求

    Args:
        workspace_id: 工作区 ID
        current_user: 当前用户
        min_role: 最低角色要求 ("admin" | "member" | "viewer")
        db: 数据库会话

    Returns:
        用户的 WorkspaceMember 记录

    Raises:
        ForbiddenException: 权限不足
    """
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise ForbiddenException("You are not a member of this workspace")

    # 角色层级：admin > member > viewer
    role_hierarchy = {"admin": 3, "member": 2, "viewer": 1}
    user_level = role_hierarchy.get(member.role.name.lower(), 0)
    required_level = role_hierarchy.get(min_role.lower(), 0)

    if user_level < required_level:
        raise ForbiddenException(
            f"Requires '{min_role}' role. Your role is '{member.role.name.lower()}'."
        )

    return member

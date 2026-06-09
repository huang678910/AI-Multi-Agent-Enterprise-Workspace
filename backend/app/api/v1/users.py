"""用户 API — 搜索/查找用户"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserSearchResult, UserSearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/search", response_model=UserSearchResponse)
async def search_users(
    q: str = Query(..., min_length=1, description="搜索关键词（邮箱或用户名）"),
    limit: int = Query(default=10, ge=1, le=50, description="最大返回数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """搜索用户 — 按邮箱或用户名模糊匹配

    用于添加工作区成员时查找用户。
    返回活跃用户，按匹配质量排序。
    """
    # ILIKE 模糊搜索（不区分大小写）
    pattern = f"%{q}%"
    stmt = (
        select(User)
        .where(
            or_(
                User.email.ilike(pattern),
                User.username.ilike(pattern),
            ),
            User.is_active == True,
        )
        .order_by(User.username)
        .limit(limit)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()

    return UserSearchResponse(
        users=[
            UserSearchResult(
                id=u.id,
                email=u.email,
                username=u.username,
                is_active=u.is_active,
            )
            for u in users
        ],
        total=len(users),
    )

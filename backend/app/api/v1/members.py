"""成员管理 API — CRUD 成员"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.models.workspace import WorkspaceMember, MemberRole
from app.schemas.member import (
    MemberCreate, MemberUpdate, MemberResponse, MemberListResponse,
)
from app.core.exceptions import NotFoundException, BadRequestException, ForbiddenException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/members", tags=["Members"])


@router.get("", response_model=MemberListResponse)
async def list_members(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出工作区成员"""
    result = await db.execute(
        select(WorkspaceMember, User.username, User.email)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.created_at.desc())
    )
    rows = result.all()

    members = []
    for member, username, email in rows:
        members.append(MemberResponse(
            id=member.id,
            workspace_id=member.workspace_id,
            user_id=member.user_id,
            role=member.role.name.lower(),
            username=username,
            email=email,
            created_at=member.created_at,
        ))

    return MemberListResponse(members=members, total=len(members))


@router.post("", response_model=MemberResponse, status_code=201)
async def add_member(
    workspace_id: str,
    request: MemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加成员（需要 admin 权限）"""
    # 检查权限
    await require_workspace_role(workspace_id, current_user, "admin", db)

    # 检查是否已是成员
    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == request.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise BadRequestException("User is already a member of this workspace")

    # 检查用户是否存在
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise NotFoundException("User not found")

    # 验证角色
    try:
        role = MemberRole[request.role.upper()]
    except KeyError:
        raise BadRequestException(f"Invalid role '{request.role}'. Use: admin, member, viewer")

    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=request.user_id,
        role=role,
    )
    db.add(member)
    await db.flush()

    return MemberResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role.name.lower(),
        username=target_user.username,
        email=target_user.email,
        created_at=member.created_at,
    )


@router.patch("/{member_id}", response_model=MemberResponse)
async def update_member(
    workspace_id: str,
    member_id: str,
    request: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新成员角色（需要 admin 权限）"""
    await require_workspace_role(workspace_id, current_user, "admin", db)

    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundException("Member not found")

    try:
        member.role = MemberRole[request.role.upper()]
    except KeyError:
        raise BadRequestException(f"Invalid role '{request.role}'")

    await db.flush()

    # 获取用户信息
    user_result = await db.execute(select(User).where(User.id == member.user_id))
    target_user = user_result.scalar_one_or_none()

    return MemberResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role.name.lower(),
        username=target_user.username if target_user else "",
        email=target_user.email if target_user else "",
        created_at=member.created_at,
    )


@router.delete("/{member_id}", status_code=204)
async def remove_member(
    workspace_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """移除成员（需要 admin 权限）"""
    await require_workspace_role(workspace_id, current_user, "admin", db)

    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundException("Member not found")

    # 不允许移除自己
    if str(member.user_id) == str(current_user.id):
        raise BadRequestException("Cannot remove yourself")

    await db.delete(member)

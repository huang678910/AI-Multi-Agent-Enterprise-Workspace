"""Workspace CRUD API"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_workspace_role
from app.models.user import User
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceListResponse
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的所有 Workspace（自动按用户过滤）"""
    workspaces = await WorkspaceService(db).list_by_user(current_user.id)
    return WorkspaceListResponse(
        workspaces=[WorkspaceResponse.model_validate(w) for w in workspaces],
        total=len(workspaces),
    )


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    request: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新 Workspace（创建者自动成为 admin）"""
    workspace = await WorkspaceService(db).create(current_user.id, request)
    return WorkspaceResponse.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个 Workspace 详情（需要 viewer 以上权限）"""
    await require_workspace_role(workspace_id, current_user, "viewer", db)
    workspace = await WorkspaceService(db).get_by_id(workspace_id)
    return WorkspaceResponse.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    request: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新 Workspace（需要 admin 权限）"""
    await require_workspace_role(workspace_id, current_user, "admin", db)
    workspace = await WorkspaceService(db).update(workspace_id, request)
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除 Workspace（需要 admin 权限）"""
    await require_workspace_role(workspace_id, current_user, "admin", db)
    await WorkspaceService(db).delete(workspace_id)

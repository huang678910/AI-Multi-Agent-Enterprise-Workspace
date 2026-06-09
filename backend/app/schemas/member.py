"""成员管理 Pydantic Schemas"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class MemberCreate(BaseModel):
    """添加成员"""
    user_id: UUID = Field(..., description="用户 ID")
    role: str = Field(default="member", description="角色: admin | member | viewer")


class MemberUpdate(BaseModel):
    """更新成员角色"""
    role: str = Field(..., description="角色: admin | member | viewer")


class MemberResponse(BaseModel):
    """成员信息"""
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str
    username: str = ""
    email: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberListResponse(BaseModel):
    """成员列表"""
    members: list[MemberResponse]
    total: int

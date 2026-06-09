"""用户搜索 Schema"""

from uuid import UUID
from pydantic import BaseModel


class UserSearchResult(BaseModel):
    """用户搜索结果"""
    id: UUID
    email: str
    username: str
    is_active: bool


class UserSearchResponse(BaseModel):
    """用户搜索响应"""
    users: list[UserSearchResult]
    total: int

"""认证相关 Pydantic 模型"""
from uuid import UUID
from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    is_active: bool

    model_config = {"from_attributes": True}

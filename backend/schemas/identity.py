from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field

from backend.schemas._common import orm_config


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = "estudiante"
    role_id: Optional[int] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    xp: Optional[int] = None


class User(UserBase):
    id: int
    xp: int = 0
    is_active: bool = True
    is_email_verified: bool = False
    created_at: datetime
    model_config = orm_config


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class TokenUser(BaseModel):
    user_id: str
    username: str
    email: str
    role: str
    xp: int = 0


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# --- Roles and Permissions ---
class RoleBase(BaseModel):
    name: str
    permissions: List[str] = []


class RoleCreate(RoleBase):
    pass


class Role(RoleBase):
    role_id: int
    model_config = orm_config

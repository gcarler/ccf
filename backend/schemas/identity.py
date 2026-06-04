from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from backend.schemas._common import orm_config


class UserBase(BaseModel):
    username: str
    email: str  # EmailStr removed — DB has legacy emails without @
    role: str = "estudiante"
    role_id: Optional[int] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if v and "@" not in v:
            raise ValueError("Email inválido")
        return v


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    xp: Optional[int] = None


class UserSelfUpdate(BaseModel):
    """Schema para que un usuario edite su propio perfil.
    No permite cambiar role, role_id, is_active ni xp.
    """
    username: Optional[str] = None
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(default=None, min_length=8)

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: Optional[str]) -> Optional[str]:
        if v and "@" not in v:
            raise ValueError("Email inválido")
        return v


class User(UserBase):
    id: int
    xp: int = 0
    is_active: bool = True
    is_email_verified: bool = False
    created_at: datetime
    permissions: Optional[Dict[str, str]] = None
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

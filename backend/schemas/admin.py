"""Admin module schemas — typed request/response models.

Centraliza todos los Pydantic models que ``api/admin.py`` usaba inline.
Sigue el patrón Base/Create/Update/Read de ``schemas/_common.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field

from backend.schemas._common import orm_config

# ── Roles (consolidated) ────────────────────────────────────────────────────


class AdminRoleCreate(BaseModel):
    model_config = {"extra": "forbid"}

    key: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: str = Field(
        validation_alias=AliasChoices("name", "nombre"),
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = None
    permissions: dict[str, Any] | list[str] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("permissions", "permisos"),
    )


class AdminRoleUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("name", "nombre"),
        max_length=100,
    )
    description: Optional[str] = None
    permissions: dict[str, Any] | list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("permissions", "permisos"),
    )


class AdminRoleRead(BaseModel):
    model_config = orm_config

    id: UUID
    nombre: str
    permisos: Dict[str, Any] = Field(default_factory=dict)
    users_count: int = 0


# ── Users ───────────────────────────────────────────────────────────────────


class AdminUserCreate(BaseModel):
    model_config = {"extra": "forbid"}

    username: str = Field(min_length=3, max_length=64)
    email: str = Field(max_length=120)
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    role: str = Field(max_length=50)
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    email: Optional[str] = Field(default=None, max_length=120)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class AdminUserRead(BaseModel):
    model_config = orm_config

    id: UUID
    username: str
    email: str
    role: str = "MIEMBRO"
    role_id: Optional[UUID] = None
    role_name: Optional[str] = None
    sede_id: Optional[UUID] = None
    xp: int = 0
    is_active: bool = True
    is_email_verified: bool = False
    permissions: Dict[str, Any] = Field(default_factory=dict)
    role_permissions: Dict[str, Any] = Field(default_factory=dict)
    override_permissions: Dict[str, Any] = Field(default_factory=dict)


# ── Permissions ─────────────────────────────────────────────────────────────


class AdminPermissionModule(BaseModel):
    model_config = orm_config

    modules: Dict[str, List[str]]
    levels: Dict[str, List[str]]


class AdminUserPermissionsRead(BaseModel):
    model_config = orm_config

    user_id: UUID
    username: str
    email: str
    role: str
    role_permissions: Dict[str, Any] = Field(default_factory=dict)
    override_permissions: Dict[str, Any] = Field(default_factory=dict)
    module_roles: List[Dict[str, Any]] = Field(default_factory=list)
    effective_permissions: Dict[str, Any] = Field(default_factory=dict)


class AdminUserPermissionSet(BaseModel):
    model_config = {"extra": "forbid"}

    permissions: Dict[str, str]


# ── Module Roles ────────────────────────────────────────────────────────────


class AdminModuleRoleAssign(BaseModel):
    model_config = {"extra": "forbid"}

    user_id: str
    modulo: str
    rol_id: str


class AdminModuleRoleRead(BaseModel):
    model_config = orm_config

    id: UUID
    user_id: UUID
    modulo: str
    rol_id: UUID
    rol_nombre: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Locations ───────────────────────────────────────────────────────────────


class AdminLocationCreate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(min_length=1, max_length=200)
    address: Optional[str] = None
    phone: Optional[str] = None


class AdminLocationUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    address: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class AdminLocationRead(BaseModel):
    model_config = orm_config

    id: UUID
    name: str
    address: Optional[str] = None
    pastor: Optional[str] = None
    active: bool = True
    type: Optional[str] = None


# ── Social Channels ─────────────────────────────────────────────────────────


class AdminSocialCreate(BaseModel):
    model_config = {"extra": "forbid"}

    platform: str = Field(min_length=1, max_length=50)
    url: str = Field(min_length=1, max_length=255)
    is_visible: bool = True


class AdminSocialUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    platform: Optional[str] = Field(default=None, min_length=1, max_length=50)
    url: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_visible: Optional[bool] = None


class AdminSocialRead(BaseModel):
    model_config = orm_config

    id: UUID
    platform: str
    url: str
    visible: bool = True


# ── System Variables ────────────────────────────────────────────────────────


class AdminVariableCreate(BaseModel):
    model_config = {"extra": "forbid"}

    key: str
    value: str


class AdminVariableUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    value: str


class AdminVariableRead(BaseModel):
    model_config = orm_config

    key: str
    value: Optional[str] = None


# ── Stats ───────────────────────────────────────────────────────────────────


class AdminStatsRead(BaseModel):
    model_config = orm_config

    personas: int = 0
    usuarios_activos: int = 0
    donaciones_mes: float = 0.0
    donantes_mes: int = 0
    personas_nuevas_mes: int = 0
    diezmos_mes: float = 0.0
    ofrendas_mes: float = 0.0


# ── Personas ────────────────────────────────────────────────────────────────


class AdminPersonaRead(BaseModel):
    model_config = orm_config

    id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    church_role: Optional[str] = None


# ── Milestones / Badges ─────────────────────────────────────────────────────


class AdminMilestoneRead(BaseModel):
    model_config = orm_config

    id: UUID
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    xp: int = 0
    count: int = 0


class AdminMilestoneAward(BaseModel):
    model_config = {"extra": "forbid"}

    persona_id: str
    badge_id: str
    awarded_by: Optional[str] = None


# ── Donation Categories ─────────────────────────────────────────────────────


class AdminDonationCategoryCreate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class AdminDonationCategoryUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    color_code: Optional[str] = None
    is_active: Optional[bool] = None


class AdminDonationCategoryRead(BaseModel):
    model_config = orm_config

    id: UUID
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    active: bool = True


# ── Comments ────────────────────────────────────────────────────────────────


class AdminCommentRead(BaseModel):
    model_config = orm_config

    id: Any
    author: str = "Anónimo"
    text: Optional[str] = None
    context: str = "General"
    type: str = "Foro"
    created_at: Optional[str] = None


# ── Provision ───────────────────────────────────────────────────────────────


class AdminProvisionResult(BaseModel):
    model_config = orm_config

    created: int = 0
    skipped: int = 0
    truncated: bool = False
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    accounts: List[Dict[str, Any]] = Field(default_factory=list)
    message: str = ""


# ── Users with Roles (combined view) ────────────────────────────────────────


class AdminUserWithRolesRead(BaseModel):
    model_config = orm_config

    user_id: UUID
    username: str
    email: str
    nombre: str = "—"
    is_active: bool = True
    rol_plataforma: Optional[Dict[str, Any]] = None
    roles_modulares: List[Dict[str, Any]] = Field(default_factory=list)

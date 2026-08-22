"""Dashboard API — endpoint unificado por módulo.

Sirve datos de agregación en tiempo real para cada módulo de la plataforma.
Soporta filtros por sede_id y parámetros específicos de cada módulo.
"""

from __future__ import annotations

from inspect import signature
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import get_user_effective_permissions, normalize_role, require_active_user
from backend.crud.dashboard import (
    get_academy_dashboard,
    get_admin_dashboard,
    get_agenda_dashboard,
    get_cms_dashboard,
    get_crm_dashboard,
    get_evangelism_dashboard,
    get_finance_dashboard,
    get_projects_dashboard,
)
from backend.schemas.dashboard import (
    AcademyDashboard,
    AdminGlobalDashboard,
    AgendaDashboard,
    CmsDashboard,
    CrmDashboard,
    EvangelismDashboard,
    FinanceDashboard,
    ProjectsDashboard,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


MODULE_REGISTRY = {
    "crm": (get_crm_dashboard, CrmDashboard, "CRM Pastoral"),
    "academy": (get_academy_dashboard, AcademyDashboard, "Academia"),
    "evangelism": (get_evangelism_dashboard, EvangelismDashboard, "Evangelismo"),
    "finance": (get_finance_dashboard, FinanceDashboard, "Finanzas"),
    "agenda": (get_agenda_dashboard, AgendaDashboard, "Agenda"),
    "cms": (get_cms_dashboard, CmsDashboard, "CMS"),
    "projects": (get_projects_dashboard, ProjectsDashboard, "Proyectos"),
    "admin": (get_admin_dashboard, AdminGlobalDashboard, "Admin"),
}


@router.get("/{module}")
def get_module_dashboard(
    module: str,
    estrategia_id: Optional[UUID] = Query(None, description="Filtrar por estrategia (evangelism)"),
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Obtener dashboard de un módulo específico.

    Args:
        module: Nombre del módulo (crm, academy, evangelism, finance, agenda, cms, projects, admin)
        estrategia_id: Filtrar por estrategia — solo aplica a evangelism (opcional)
    """
    if module not in MODULE_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Módulo '{module}' no encontrado. Módulos disponibles: {list(MODULE_REGISTRY.keys())}",
        )

    fn, schema_cls, label = MODULE_REGISTRY[module]

    user_perms = get_user_effective_permissions(db, current_user)
    role = normalize_role(str(getattr(current_user, "role", "")))
    if not role and getattr(current_user, "rol_plataforma", None):
        role = normalize_role(current_user.rol_plataforma.nombre)
    is_super = role in {"admin", "administrador", "super administrador", "superadmin"}

    if module == "admin":
        if not is_super and "system:config" not in user_perms and "admin:read" not in user_perms:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
    elif module == "finance":
        if not is_super and "finance:read" not in user_perms and "finance:manage" not in user_perms:
            raise HTTPException(status_code=403, detail="Permisos insuficientes para acceder a finanzas")
        record_admin_action(db, current_user, "dashboard.finance.view", "dashboard", "finance")

    user_sede = getattr(current_user, "sede_id", None)
    kwargs = {}
    if "sede_id" in signature(fn).parameters:
        kwargs["sede_id"] = user_sede

    if module == "evangelism" and estrategia_id:
        kwargs["estrategia_id"] = estrategia_id

    data = fn(db, **kwargs)
    return data


@router.get("/modules/list")
def list_modules(_current_user=Depends(require_active_user)):
    """Listar módulos disponibles para dashboard."""
    return {
        "modules": [{"key": k, "label": v[2], "endpoint": f"/api/dashboard/{k}"} for k, v in MODULE_REGISTRY.items()]
    }

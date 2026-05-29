"""Dashboard API — endpoint unificado por módulo.

Sirve datos de agregación en tiempo real para cada módulo de la plataforma.
Soporta filtros por sede_id y parámetros específicos de cada módulo.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
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
    sede_id: Optional[int] = Query(None, description="Filtrar por sede"),
    estrategia_id: Optional[str] = Query(None, description="Filtrar por estrategia (evangelism)"),
    db: Session = Depends(get_db),
):
    """Obtener dashboard de un módulo específico.

    Args:
        module: Nombre del módulo (crm, academy, evangelism, finance, agenda, cms, projects, admin)
        sede_id: Filtrar por sede (opcional)
        estrategia_id: Filtrar por estrategia — solo aplica a evangelism (opcional)
    """
    if module not in MODULE_REGISTRY:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Módulo '{module}' no encontrado. Módulos disponibles: {list(MODULE_REGISTRY.keys())}",
        )

    fn, schema_cls, label = MODULE_REGISTRY[module]

    # Pasar kwargs según el módulo
    kwargs = {"sede_id": sede_id}
    if module == "evangelism":
        kwargs["estrategia_id"] = estrategia_id

    data = fn(db, **kwargs)
    return data


@router.get("/modules/list")
def list_modules():
    """Listar módulos disponibles para dashboard."""
    return {
        "modules": [
            {"key": k, "label": v[2], "endpoint": f"/api/dashboard/{k}"}
            for k, v in MODULE_REGISTRY.items()
        ]
    }

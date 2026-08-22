"""Superficie MCP dedicada para el módulo de Gobernanza Institucional CCF."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from backend.core.database import SessionLocal
from backend.crud import governance as gov_crud
from backend.mcp_auth import authenticated_mcp_app, get_mcp_current_user, require_mcp_permission

mcp_app = FastMCP(
    name="CCF Gobernanza",
    instructions="Herramientas para consulta de políticas eclesiales, resoluciones, actas y comités pastorales.",
    streamable_http_path="/",
    stateless_http=True,
)
governance_mcp = mcp_app


@mcp_app.tool()
def get_active_policies(category: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Consulta las políticas eclesiales institucionales activas y aprobadas."""
    with SessionLocal() as db:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "profile:manage")
        sede_id = getattr(user, "sede_id", None)
        policies, _ = gov_crud.list_policies(
            db, sede_id=sede_id, category=category, status="PUBLICADA", limit=limit
        )
        return [
            {
                "id": str(p.id),
                "code": p.code,
                "title": p.title,
                "category": p.category,
                "version": p.version,
                "effective_date": p.effective_date.isoformat() if p.effective_date else None,
            }
            for p in policies
        ]


@mcp_app.tool()
def get_official_resolutions(limit: int = 20) -> List[Dict[str, Any]]:
    """Consulta las actas y resoluciones ministeriales aprobadas y firmadas."""
    with SessionLocal() as db:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "profile:manage")
        sede_id = getattr(user, "sede_id", None)
        resolutions, _ = gov_crud.list_resolutions(
            db, sede_id=sede_id, status="FIRMADA", limit=limit
        )
        return [
            {
                "id": str(r.id),
                "number": r.number,
                "title": r.title,
                "summary": r.summary,
                "session_date": r.session_date.isoformat() if r.session_date else None,
                "status": r.status,
            }
            for r in resolutions
        ]


@mcp_app.tool()
def list_pastoral_committees(committee_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lista los comités institucionales y pastorales de la iglesia."""
    with SessionLocal() as db:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "profile:manage")
        sede_id = getattr(user, "sede_id", None)
        committees, _ = gov_crud.list_committees(
            db, sede_id=sede_id, committee_type=committee_type, limit=50
        )
        return [
            {
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "type": c.committee_type,
                "members_count": len(c.members),
            }
            for c in committees
        ]


@mcp_app.tool()
def get_governance_summary() -> Dict[str, Any]:
    """Obtiene el resumen estadístico de gobernanza eclesiástica."""
    with SessionLocal() as db:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "profile:manage")
        sede_id = getattr(user, "sede_id", None)
        stats = gov_crud.get_governance_stats(db, sede_id=sede_id)
        return stats.model_dump()


governance_mcp_app = authenticated_mcp_app(mcp_app)


def create_governance_mcp_app():
    return governance_mcp_app


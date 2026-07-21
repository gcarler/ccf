from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import get_current_user, normalize_role
from backend.crud.crm import get_user_sede_id
from backend.services.knowledge_graph import build_graph_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


# DECISION-GRAPH-SENTINEL-001 / PEND-GRAPH-007
#
# Cuando ``get_user_sede_id(db, current_user.id)`` retorna None (usuario sin
# sede asignada), la vista global agregada sólo se permite a roles de
# plataforma. Cualquier otro rol recibe 403 con detalle existence-leak safe.
# Roles cubiertos (post ``normalize_role``):
#   - ``"admin"``: cubre ``"ADMIN"`` y ``"Administrador"`` (via
#     ``ROLE_ALIASES`` en ``backend/core/permissions.py``).
#   - ``"super administrador"``: nombre canónico de ``DEFAULT_ROLES`` para
#     super-admin (rol con permisos ``system:config``).
#   - ``"platform_admin"``: sentinel explícito para cuentas de operación
#     cross-sede que aún no tengan ``rol_plataforma_id`` asignado.
#
# Ver ``docs/GRAPH_RBAC_MATRIX.md`` §6 para la justificación arquitectónica
# y §6.3 para los riesgos aceptados por esta política.
PLATFORM_ADMIN_ROLES = frozenset({"admin", "super administrador", "platform_admin"})


def _resolve_user_role(current_user) -> str:
    """Devuelve el rol normalizado del actor (post ``normalize_role``).

    Fuente primaria: atributo ``role`` en el modelo ``Usuario``. Fallback:
    ``rol_plataforma.nombre`` para compatibilidad con DEFAULT_ROLES que
    almacenan el nombre textual del rol (e.g. ``"ADMIN"``,
    ``"Super administrador"``).
    """
    role = normalize_role(str(getattr(current_user, "role", "")))
    if not role and hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
        role = normalize_role(current_user.rol_plataforma.nombre)
    return role


def _enforce_graph_rbac(current_user, user_sede) -> None:
    """Hardening PEND-GRAPH-007: vista global sólo para roles de plataforma.

    Si el actor tiene sede asignada, esta función retorna sin acción
    (Axioma 3 cubre el aislamiento). Sólo cuando ``user_sede`` es None
    se verifica el rol de plataforma: roles invitados reciben 403.
    """
    if user_sede is not None:
        return

    role = _resolve_user_role(current_user)
    if role in PLATFORM_ADMIN_ROLES:
        return

    logger.warning(
        "Graph API rechazo vista global: usuario %s sin sede asignada (rol=%s)",
        getattr(current_user, "id", None),
        role or "<sin-rol>",
    )
    raise HTTPException(
        status_code=403,
        detail=(
            "Vista global denegada: el usuario no tiene sede asignada "
            "y no es administrador de plataforma."
        ),
    )


@router.get("/snapshot")
def graph_snapshot(
    limit: int = 50,
    offset: int = 0,
    types: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return a lightweight knowledge graph view combining academy, CRM and assets data.
    
    Axioma 3: filtra por sede_id del usuario autenticado.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _enforce_graph_rbac(current_user, user_sede)
    safe_limit = max(1, min(limit, 500))
    safe_offset = max(offset, 0)
    type_list = [item.strip() for item in (types or "").split(",") if item.strip()]

    expanded_limit = min(safe_limit + safe_offset, 1500)
    snapshot = build_graph_snapshot(db, limit=expanded_limit, types=type_list, sede_id=user_sede)

    nodes = snapshot.get("nodes", [])
    total_nodes = len(nodes)
    paginated_nodes = nodes[safe_offset : safe_offset + safe_limit]
    allowed_node_ids = {node.get("id") for node in paginated_nodes}
    paginated_edges = [
        edge
        for edge in snapshot.get("edges", [])
        if edge.get("from") in allowed_node_ids and edge.get("to") in allowed_node_ids
    ]

    snapshot["nodes"] = paginated_nodes
    snapshot["edges"] = paginated_edges
    snapshot["meta"]["pagination"] = {
        "limit": safe_limit,
        "offset": safe_offset,
        "total_nodes": total_nodes,
        "returned_nodes": len(paginated_nodes),
    }
    snapshot["meta"]["requested_by"] = (
        str(getattr(current_user, "id", None) or getattr(current_user, "user_id", None))
        if current_user
        else None
    )
    return snapshot


@router.get("/connections/{node_id}")
def graph_connections(
    node_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Axioma 3: filtra por sede_id del usuario autenticado."""
    user_sede = get_user_sede_id(db, current_user.id)
    _enforce_graph_rbac(current_user, user_sede)
    safe_limit = max(1, min(limit, 500))
    snapshot = build_graph_snapshot(db, limit=1500, sede_id=user_sede)
    nodes = snapshot.get("nodes", [])
    edges = snapshot.get("edges", [])

    node = next((item for item in nodes if item.get("id") == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    outgoing = [edge for edge in edges if edge.get("from") == node_id][:safe_limit]
    incoming = [edge for edge in edges if edge.get("to") == node_id][:safe_limit]

    related_ids = {edge.get("to") for edge in outgoing} | {
        edge.get("from") for edge in incoming
    }
    related_nodes = [item for item in nodes if item.get("id") in related_ids]

    return {
        "node": node,
        "incoming": incoming,
        "outgoing": outgoing,
        "related_nodes": related_nodes,
        "meta": {
            "requested_by": (
                str(
                    getattr(current_user, "id", None)
                    or getattr(current_user, "user_id", None)
                )
                if current_user
                else None
            ),
            "limit": safe_limit,
        },
    }

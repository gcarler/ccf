from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import models
from backend.auth import get_current_user
from backend.core.database import get_db
from backend.services.knowledge_graph import build_graph_snapshot

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/snapshot")
def graph_snapshot(
    limit: int = 50,
    offset: int = 0,
    types: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return a lightweight knowledge graph view combining academy, CRM and assets data."""
    safe_limit = max(1, min(limit, 500))
    safe_offset = max(offset, 0)
    type_list = [item.strip() for item in (types or "").split(",") if item.strip()]

    expanded_limit = min(safe_limit + safe_offset, 1500)
    snapshot = build_graph_snapshot(db, limit=expanded_limit, types=type_list)

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
    safe_limit = max(1, min(limit, 500))
    snapshot = build_graph_snapshot(db, limit=1500)
    nodes = snapshot.get("nodes", [])
    edges = snapshot.get("edges", [])

    node = next((item for item in nodes if item.get("id") == node_id), None)
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

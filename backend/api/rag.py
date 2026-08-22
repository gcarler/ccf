"""Pastoral RAG API — Hybrid semantic and full-text retrieval with pgvector and RLS."""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.pgvector_compat import PGVECTOR_AVAILABLE
from backend.models_auth import Usuario
from backend.schemas.rag import PastoralSearchRequest, PastoralSearchResult
from backend.services.rag_service import PastoralRAGService

logger = logging.getLogger("CCF-RAG-API")
router = APIRouter(prefix="/rag", tags=["rag"])
settings = get_settings()


def _resolve_user_and_tenant(
    request: Request,
    db: Session,
    x_sede_id: Optional[str] = None,
    x_persona_id: Optional[str] = None,
) -> tuple[Optional[Usuario], Optional[UUID], Optional[str]]:
    """Extract authenticated user (if token present), effective sede_id, and user role."""
    auth_header = request.headers.get("Authorization") or ""
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    user: Optional[Usuario] = None
    user_sede_id: Optional[UUID] = None
    user_role: Optional[str] = None

    if token:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            subject = str(payload.get("sub") or "")
            if subject:
                user_id = uuid.UUID(subject)
                user = (
                    db.query(Usuario)
                    .options(joinedload(Usuario.rol_plataforma))
                    .filter(Usuario.id == user_id, Usuario.is_active.is_(True))
                    .first()
                )
                if user:
                    user_sede_id = user.sede_id
                    if user.rol_plataforma and user.rol_plataforma.nombre:
                        user_role = str(user.rol_plataforma.nombre)
                    elif hasattr(user, "role"):
                        user_role = str(user.role)
        except (JWTError, ValueError) as exc:
            logger.debug("Failed decoding JWT in RAG endpoint: %s", exc)

    # Header overrides (e.g. from AgentOrchestrator context propagation)
    if x_sede_id and (user is None or user_role in {"admin", "superadmin", "platform_admin"}):
        try:
            user_sede_id = UUID(x_sede_id.strip())
        except (ValueError, AttributeError):
            pass

    return user, user_sede_id, user_role


@router.post("/pastoral/search", response_model=List[PastoralSearchResult])
def search_pastoral_rag(
    payload: PastoralSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_sede_id: Optional[str] = Header(None, alias="X-Sede-ID"),
    x_persona_id: Optional[str] = Header(None, alias="X-Persona-ID"),
):
    """Execute hybrid retrieval combining FTS and cosine vector similarity.

    Restricted by Row-Level Security (RLS) and sede_id multi-tenant isolation.
    """
    user, user_sede_id, user_role = _resolve_user_and_tenant(
        request=request,
        db=db,
        x_sede_id=x_sede_id,
        x_persona_id=x_persona_id,
    )

    rag_service = PastoralRAGService(
        db=db,
        user_sede_id=user_sede_id,
        user_role=user_role,
    )

    results = rag_service.search(
        query=payload.query,
        limit=payload.limit,
        category=payload.category,
        alpha=payload.alpha,
    )
    return results


@router.get("/pastoral/health")
def rag_health(db: Session = Depends(get_db)):
    """Healthcheck for Pastoral RAG service and vector extension status."""
    is_pg = False
    try:
        bind = db.get_bind()
        is_pg = bind.dialect.name == "postgresql"
    except Exception:
        pass

    return {
        "status": "online",
        "service": "Pastoral RAG",
        "pgvector_installed": PGVECTOR_AVAILABLE,
        "is_postgresql": is_pg,
    }

"""Global Wiki API — standalone wiki documents (not tied to a single project).

Uses the ``project_documents`` table but allows ``project_id`` to reference any
project or be omitted for org-wide docs.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from backend import models, schemas
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.crud.projects import get_user_persona_id

router = APIRouter(prefix="/wiki", tags=["wiki"])


# ── search MUST be above /{doc_id} so "search" isn't captured as a doc_id ────


@router.get("/search", response_model=List[schemas.ProjectDocumentRead])
def search_wiki_docs(
    q: str = Query(..., min_length=2, description="Término de búsqueda"),
    project_id: Optional[UUID] = Query(None),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Búsqueda full-text simple en documentos wiki."""
    search_term = f"%{q}%"
    stmt = (
        db.query(models.ProjectDocument)
        .options(selectinload(models.ProjectDocument.author))
        .filter(models.ProjectDocument.deleted_at.is_(None))
        .filter(
            or_(
                models.ProjectDocument.title.ilike(search_term),
                models.ProjectDocument.content.ilike(search_term),
            )
        )
    )
    if project_id:
        stmt = stmt.filter(models.ProjectDocument.project_id == project_id)

    return stmt.order_by(models.ProjectDocument.updated_at.desc()).limit(limit).all()


# ── CRUD ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=List[schemas.ProjectDocumentRead])
def list_wiki_docs(
    project_id: Optional[UUID] = Query(None, description="Filtrar por proyecto"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Listar documentos wiki (globales o por proyecto)."""
    stmt = (
        db.query(models.ProjectDocument)
        .options(selectinload(models.ProjectDocument.author))
        .filter(models.ProjectDocument.deleted_at.is_(None))
    )
    if project_id:
        stmt = stmt.filter(models.ProjectDocument.project_id == project_id)

    return (
        stmt.order_by(models.ProjectDocument.updated_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


@router.get("/{doc_id}", response_model=schemas.ProjectDocumentRead)
def get_wiki_doc(
    doc_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtener un documento wiki."""
    doc = (
        db.query(models.ProjectDocument)
        .options(selectinload(models.ProjectDocument.author))
        .filter(models.ProjectDocument.id == doc_id, models.ProjectDocument.deleted_at.is_(None))
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


@router.post("", response_model=schemas.ProjectDocumentRead, status_code=status.HTTP_201_CREATED)
def create_wiki_doc(
    data: schemas.ProjectDocumentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crear documento wiki."""
    persona_id = get_user_persona_id(db, current_user.id)
    doc = models.ProjectDocument(
        title=data.title,
        content=data.content or "",
        project_id=data.project_id,
        author_id=persona_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/{doc_id}", response_model=schemas.ProjectDocumentRead)
def update_wiki_doc(
    doc_id: UUID,
    data: schemas.ProjectDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualizar documento wiki."""
    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if data.title is not None:
        doc.title = data.title
    if data.content is not None:
        doc.content = data.content

    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wiki_doc(
    doc_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Eliminar documento wiki (soft delete)."""
    from datetime import datetime, timezone

    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    doc.deleted_at = datetime.now(timezone.utc)
    db.commit()

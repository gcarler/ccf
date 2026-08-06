"""Glossary — CRUD de ``CmsGlossaryTerm`` enterprise CMS.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import _log_audit, require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import CmsGlossaryTerm
from backend.models_identity import User

router = APIRouter()


class GlossaryTermCreate(BaseModel):
    site_key: str
    term: str
    definition: str
    aliases: list[str] = []
    category: str | None = None
    language: str = "es"


@router.post("/glossary")
def create_glossary_term(
    body: GlossaryTermCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    t = CmsGlossaryTerm(
        site_key=body.site_key,
        term=body.term,
        definition=body.definition,
        aliases=body.aliases,
        category=body.category,
        language=body.language,
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(t)
    _log_audit(
        db,
        user,
        "glossary.create",
        "glossary_term",
        str(t.id),
        entity_slug=body.term,
        site_key=body.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": str(t.id), "status": "created"}


@router.get("/glossary")
def list_glossary_terms(
    site_key: str,
    search: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    q = db.query(CmsGlossaryTerm).filter(
        CmsGlossaryTerm.site_key == site_key,
        CmsGlossaryTerm.is_published == True,
    )
    if search:
        q = q.filter(
            or_(
                CmsGlossaryTerm.term.ilike(f"%{search}%"),
                CmsGlossaryTerm.definition.ilike(f"%{search}%"),
            )
        )
    if category:
        q = q.filter(CmsGlossaryTerm.category == category)
    terms = q.order_by(CmsGlossaryTerm.term).all()
    return [
        {
            "id": str(t.id),
            "term": t.term,
            "definition": t.definition,
            "aliases": t.aliases,
            "category": t.category,
            "language": t.language,
        }
        for t in terms
    ]

"""Custom Types — CRUD de ``CmsCustomType`` (post types personalizados).

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import _log_audit, require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import CmsCustomType
from backend.models_identity import User

router = APIRouter()


class CustomTypeCreate(BaseModel):
    site_key: str
    type_key: str
    label: str
    label_plural: str | None = None
    icon: str | None = None
    supports: list[str] = ["title", "editor"]
    fields_schema: dict = {}


@router.post("/custom-types")
def create_custom_type(
    body: CustomTypeCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    existing = (
        db.query(CmsCustomType)
        .filter(
            CmsCustomType.site_key == body.site_key,
            CmsCustomType.type_key == body.type_key,
        )
        .first()
    )
    if existing:
        raise HTTPException(409, "Custom type already exists")
    ct = CmsCustomType(
        site_key=body.site_key,
        type_key=body.type_key,
        label=body.label,
        label_plural=body.label_plural,
        icon=body.icon,
        supports=body.supports,
        fields_schema=body.fields_schema,
    )
    db.add(ct)
    _log_audit(
        db,
        user,
        "custom_type.create",
        "custom_type",
        str(ct.id),
        entity_slug=body.type_key,
        site_key=body.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": str(ct.id), "status": "created"}


@router.get("/custom-types")
def list_custom_types(
    site_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    types = (
        db.query(CmsCustomType)
        .filter(
            CmsCustomType.site_key == site_key,
            CmsCustomType.is_active == True,
        )
        .all()
    )
    return [
        {
            "id": str(t.id),
            "type_key": t.type_key,
            "label": t.label,
            "label_plural": t.label_plural,
            "icon": t.icon,
            "supports": t.supports,
            "fields_schema": t.fields_schema,
        }
        for t in types
    ]

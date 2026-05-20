from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_active_user
from backend.core.database import get_db


router = APIRouter(prefix="/content", tags=["content"])


BLOCK_REQUIRED_FIELDS: dict[str, list[str]] = {
    "faro_home_hero": ["eyebrow", "title_lead", "title_accent", "description"],
    "faro_events_hero": ["eyebrow", "title", "description"],
    "faro_testimonios_hero": ["eyebrow", "title_lead", "title_accent", "description"],
    "faro_sermons_hero": ["eyebrow", "title_lead", "title_accent", "description"],
    "faro_courses_hero": ["eyebrow", "title_lead", "title_accent", "description"],
    "faro_discover_hero": ["eyebrow", "title_lead", "title_accent", "description", "cta"],
    "faro_about_hero": ["eyebrow", "title_lead", "title_accent", "description"],
    "faro_locations_hero": ["eyebrow", "title", "search_placeholder"],
}

STRUCTURED_CONTENT_KEYS = set(BLOCK_REQUIRED_FIELDS) | {
    "faro_public_events",
    "faro_media_gallery",
    "faro_testimonials_feed",
    "faro_announcements_feed",
    "faro_nav_items",
}

PLAIN_TEXT_SUFFIXES = (
    "_body",
    "_body_html",
    "_copy",
    "_html",
    "_rich_text",
    "_text",
)


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"in_review", "archived"},
    "in_review": {"approved", "draft", "archived"},
    "approved": {"published", "draft", "archived"},
    "published": {"draft", "archived"},
    "archived": {"draft"},
}


def _allows_plain_text(page_key: str) -> bool:
    normalized = page_key.strip().lower()
    if normalized in STRUCTURED_CONTENT_KEYS:
        return False
    return "wiki" in normalized or normalized.endswith(PLAIN_TEXT_SUFFIXES)


def _parse_content_payload(page_key: str, payload: schemas.PageContentUpdate) -> Any:
    if payload.content is None:
        return None
    if _allows_plain_text(page_key):
        return payload.content
    try:
        return json.loads(payload.content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"JSON invalido: {exc.msg}") from exc


def _validate_content_shape(page_key: str, parsed: Any) -> None:
    if parsed is None:
        return
    if page_key in {"faro_public_events", "faro_media_gallery", "faro_testimonials_feed", "faro_announcements_feed"}:
        if not isinstance(parsed, list):
            raise HTTPException(status_code=422, detail=f"{page_key} debe ser una lista JSON")
        return

    if page_key == "faro_nav_items":
        if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), list):
            raise HTTPException(status_code=422, detail="faro_nav_items requiere objeto con lista 'items'")
        return

    required = BLOCK_REQUIRED_FIELDS.get(page_key)
    if required:
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=422, detail=f"{page_key} debe ser un objeto JSON")
        missing = [field for field in required if str(parsed.get(field, "")).strip() == ""]
        if missing:
            raise HTTPException(status_code=422, detail=f"Campos obligatorios faltantes: {', '.join(missing)}")


def _workflow_to_schema(item: models.ContentPublication) -> schemas.ContentWorkflowRead:
    return schemas.ContentWorkflowRead(
        page_key=item.page_key,
        status=item.status,
        publish_at=item.publish_at,
        expire_at=item.expire_at,
        last_published_at=item.last_published_at,
        notes=item.notes,
        updated_at=item.updated_at,
    )


@router.get("", response_model=List[schemas.PageContentRead])
def list_content_blocks(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.list_page_contents(db, limit=limit)


@router.get("/{page_key}", response_model=schemas.PageContentRead)
def get_content_block(
    page_key: str,
    db: Session = Depends(get_db),
):
    return crud.get_or_create_page_content(db, page_key)


@router.put("/{page_key}", response_model=schemas.PageContentRead)
def put_content_block(
    page_key: str,
    payload: schemas.PageContentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    parsed = _parse_content_payload(page_key, payload)
    _validate_content_shape(page_key, parsed)
    row = crud.update_page_content(db, page_key, payload)
    crud.update_content_publication(db, page_key, status="draft", updated_by=current_user.id)
    crud.create_admin_audit_log(
        db,
        actor_user_id=current_user.id,
        action="content_update",
        resource_type="content",
        resource_id=page_key,
        metadata={"method": "put"},
    )
    return row


@router.patch("/{page_key}", response_model=schemas.PageContentRead)
def patch_content_block(
    page_key: str,
    payload: schemas.PageContentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    parsed = _parse_content_payload(page_key, payload)
    _validate_content_shape(page_key, parsed)
    row = crud.update_page_content(db, page_key, payload)
    crud.update_content_publication(db, page_key, status="draft", updated_by=current_user.id)
    crud.create_admin_audit_log(
        db,
        actor_user_id=current_user.id,
        action="content_update",
        resource_type="content",
        resource_id=page_key,
        metadata={"method": "patch"},
    )
    return row


@router.post("/{page_key}", response_model=schemas.PageContentRead)
def post_content_block(
    page_key: str,
    payload: schemas.PageContentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    parsed = _parse_content_payload(page_key, payload)
    _validate_content_shape(page_key, parsed)
    row = crud.update_page_content(db, page_key, payload)
    crud.update_content_publication(db, page_key, status="draft", updated_by=current_user.id)
    crud.create_admin_audit_log(
        db,
        actor_user_id=current_user.id,
        action="content_create_or_update",
        resource_type="content",
        resource_id=page_key,
        metadata={"method": "post"},
    )
    return row


@router.get("/{page_key}/versions", response_model=List[schemas.PageContentVersionRead])
def get_content_versions(
    page_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    return crud.get_page_content_versions(db, page_key)


@router.post("/{page_key}/rollback/{version_id}", response_model=schemas.PageContentRead)
def rollback_content_version(
    page_key: str,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    row = crud.restore_page_content_version(db, page_key, version_id)
    if not row:
        raise HTTPException(status_code=404, detail="version not found")
    crud.update_content_publication(db, page_key, status="draft", updated_by=current_user.id)
    crud.create_admin_audit_log(
        db,
        actor_user_id=current_user.id,
        action="content_rollback",
        resource_type="content",
        resource_id=page_key,
        metadata={"version_id": version_id},
    )
    return row


@router.get("/{page_key}/workflow", response_model=schemas.ContentWorkflowRead)
def get_content_workflow(
    page_key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    row = crud.get_or_create_content_publication(db, page_key)
    return _workflow_to_schema(row)


@router.patch("/{page_key}/workflow", response_model=schemas.ContentWorkflowRead)
def patch_content_workflow(
    page_key: str,
    payload: schemas.ContentWorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    workflow = crud.get_or_create_content_publication(db, page_key)
    previous_status = workflow.status
    action = payload.action.strip().lower()

    action_to_status = {
        "submit_review": "in_review",
        "approve": "approved",
        "publish": "published",
        "archive": "archived",
        "revert_draft": "draft",
    }
    if action not in action_to_status:
        raise HTTPException(status_code=422, detail="accion invalida")

    next_status = action_to_status[action]
    allowed = ALLOWED_TRANSITIONS.get(previous_status, set())
    if next_status not in allowed and next_status != previous_status:
        raise HTTPException(status_code=409, detail=f"No se puede pasar de {previous_status} a {next_status}")

    updated = crud.update_content_publication(
        db,
        page_key,
        status=next_status,
        publish_at=payload.publish_at if payload.publish_at is not None else ...,
        expire_at=payload.expire_at if payload.expire_at is not None else ...,
        notes=payload.notes,
        updated_by=current_user.id,
    )
    crud.create_admin_audit_log(
        db,
        actor_user_id=current_user.id,
        action="content_workflow_transition",
        resource_type="content_workflow",
        resource_id=page_key,
        metadata={"from": previous_status, "to": next_status, "action": action},
    )
    return _workflow_to_schema(updated)


@router.get("/metrics/overview", response_model=schemas.CmsMetrics)
def get_content_metrics(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_active_user),
):
    publications = crud.list_content_publications(db)
    status_counter = {"draft": 0, "in_review": 0, "approved": 0, "published": 0, "archived": 0}
    for item in publications:
        status_counter[item.status] = status_counter.get(item.status, 0) + 1

    testimonials = crud.list_testimonials(db)
    announcements = crud.list_announcements(db)
    media = crud.list_cms_media_items(db, limit=500)

    return schemas.CmsMetrics(
        total_blocks=len(crud.list_page_contents(db, limit=500)),
        draft_blocks=status_counter.get("draft", 0),
        in_review_blocks=status_counter.get("in_review", 0),
        approved_blocks=status_counter.get("approved", 0),
        published_blocks=status_counter.get("published", 0),
        archived_blocks=status_counter.get("archived", 0),
        testimonials_total=len(testimonials),
        testimonials_approved=sum(1 for row in testimonials if row.is_approved),
        announcements_total=len(announcements),
        announcements_active=sum(1 for row in announcements if row.status == "published"),
        media_total=len(media),
        media_images=sum(1 for row in media if (row.mime_type or "").startswith("image/")),
        media_videos=sum(1 for row in media if (row.mime_type or "").startswith("video/")),
        media_audio=sum(1 for row in media if (row.mime_type or "").startswith("audio/")),
    )

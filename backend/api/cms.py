from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api._cms_helpers import (
    _actor_sede_or_none,
    _get_scoped_cms_media,
    _scope_cms_media_by_user_sede,
    collect_section_media_ids,
)
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.schemas import PaginatedResponse
from backend.services.cms_media_service import (
    delete_cms_media as _delete_cms_media,
)
from backend.services.cms_media_service import (
    optimize_cms_media as _optimize_cms_media,
)
from backend.services.cms_media_service import (
    upload_cms_media as _upload_cms_media,
)

# CMS endpoints — preferir /cms/v2/* en integraciones nuevas.
router = APIRouter(tags=["cms"])
logger = logging.getLogger(__name__)

settings = get_settings()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# NOTE: v1 testimonials and announcements endpoints removed.
# The frontend was fully migrated to the v2 API.
# Legacy schemas (TestimonialRead, AnnouncementRead, etc.) were deleted.


# ── CMS Media ───────────────────────────────────────────
# Axioma 3 — Multi-Tenant: CmsMediaItem tiene sede_id propio (migration
# 2026-07-01). Endpoints admin filtran estrictamente por sede. CmsImage
# upload deriva ``sede_id`` server-side desde el current_user.


@router.get("/cms/media", response_model=PaginatedResponse[schemas.CmsMediaRead])
def list_cms_media(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    query: str | None = Query(default=None),
    section: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Axioma 3 — Multi-Tenant: el listado admin filtra por sede del staff.
    Staff de sede_a SÓLO ve imágenes de sede_a (incluso si la URL del
    asset técnicamente sería pública)."""
    base_query = db.query(models.CmsMediaItem)
    base_query = _scope_cms_media_by_user_sede(db, current_user, base_query)
    if not include_archived:
        base_query = base_query.filter(models.CmsMediaItem.status != "archived")
    if section:
        base_query = base_query.filter(models.CmsMediaItem.section == section)
    if query:
        from sqlalchemy import or_ as _or

        like = f"%{query.strip()}%"
        base_query = base_query.filter(
            _or(
                models.CmsMediaItem.url.ilike(like),
                models.CmsMediaItem.alt_text.ilike(like),
                models.CmsMediaItem.filename.ilike(like),
            )
        )
    total = base_query.count()
    items = (
        base_query.order_by(models.CmsMediaItem.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return PaginatedResponse(
        items=[schemas.CmsMediaRead.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/cms/media", response_model=schemas.CmsMediaRead, status_code=201)
def create_cms_media(
    payload: schemas.CmsMediaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Axioma 3 — Multi-Tenant: ``sede_id`` se deriva server-side desde el
    current_user. Defense-in-depth CRUD lo re-valida pre-add."""
    return crud.create_cms_media_item(
        db,
        url=payload.url,
        alt_text=payload.alt_text,
        section=payload.section,
        tags=payload.tags,
        created_by=current_user.id,
        filename=payload.filename,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        width=payload.width,
        height=payload.height,
        dimensions=payload.dimensions,
        status=payload.status,
        actor_user_id=str(current_user.id),
    )


@router.get("/cms/media/{item_id}", response_model=schemas.CmsMediaRead)
def get_cms_media(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Axioma 3 — Multi-Tenant: 404 cross-sede existence-leak safe."""
    return _get_scoped_cms_media(db, current_user, item_id)


@router.patch("/cms/media/{item_id}", response_model=schemas.CmsMediaRead)
def patch_cms_media(
    item_id: uuid.UUID,
    payload: schemas.CmsMediaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Axioma 3 — Multi-Tenant: 404 cross-sede antes de mutar."""
    row = _get_scoped_cms_media(db, current_user, item_id)
    return crud.update_cms_media_item(
        db,
        row.id,
        url=payload.url,
        alt_text=payload.alt_text,
        section=payload.section,
        tags=payload.tags,
        filename=payload.filename,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        width=payload.width,
        height=payload.height,
        dimensions=payload.dimensions,
        status=payload.status,
        actor_user_id=str(current_user.id),
    )


@router.delete("/cms/media/{item_id}", status_code=204)
def delete_cms_media(
    item_id: uuid.UUID,
    permanent: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Delete media item. If permanent=true, deletes the file AND DB record.
    Otherwise soft-deletes (archives).

    Path traversal hardening (H-05): delegated to
    ``backend.services.cms_media_service``.
    """
    row = _get_scoped_cms_media(db, current_user, item_id)
    try:
        _delete_cms_media(
            db, row, permanent=permanent, actor_user_id=str(current_user.id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cms/media/{item_id}/optimize", response_model=schemas.CmsMediaRead)
def optimize_cms_media(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Optimize an existing image: re-encode to WebP, resize, compress.
    Returns updated media item with new URL and file_size."""
    row = _get_scoped_cms_media(db, current_user, item_id)
    try:
        return _optimize_cms_media(db, row, actor_user_id=str(current_user.id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cms/media/upload", response_model=schemas.CmsMediaRead, status_code=201)
async def upload_cms_media(
    file: UploadFile = File(...),
    section: str = Form(default="general"),
    alt_text: str = Form(default=""),
    tags: str = Form(default=""),
    optimize: bool = Form(default=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Hardened upload pipeline (Axioma 3 + Defense-in-Depth).

    El procesamiento real vive en ``backend.services.cms_media_service``
    para ser reutilizado por v1 y v2.
    """
    content = await file.read()
    parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    try:
        return _upload_cms_media(
            db,
            content=content,
            filename=file.filename or "asset.bin",
            content_type=file.content_type,
            section=section,
            alt_text=alt_text or file.filename or "",
            tags=parsed_tags,
            optimize=optimize,
            actor_user_id=str(current_user.id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── CMS Metrics ─────────────────────────────────────────
# Axioma 3 — Multi-Tenant: las métricas admin se acotan por sede. Se
# cuentan sólo testimonios / announcements / media de la sede del staff
# para que un pastor de sede_b no vea volúmenes agregados de sede_a.


@router.get("/cms/metrics", response_model=schemas.CmsMetrics)
def get_cms_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Axioma 3 — Multi-Tenant: pre-filtramos métricas por sede del staff.
    El superadmin canónico sin sede conserva totales globales."""

    # Axioma 3 — Multi-Tenant: pre-filtramos métricas por sede del staff.
    # Testimonials y announcements viven como CmsPost categorizados.
    # Las tablas legacy (testimonials, announcements) fueron eliminadas.
    actor_sede = _actor_sede_or_none(db, current_user)

    # Inline queries para testimonials y announcements (adapters v1 eliminados).
    def _cms_posts_by_category(slug: str) -> list[models.CmsPost]:
        q = db.query(models.CmsPost).join(models.CmsPost.categories).filter(
            models.CmsCategory.slug == slug
        )
        if actor_sede is not None:
            q = q.join(models.CmsSite).filter(
                models.CmsSite.sede_id == actor_sede
            )
        return q.distinct().order_by(models.CmsPost.created_at.desc()).all()

    cms_testimonials = _cms_posts_by_category("testimonials")
    cms_announcements = _cms_posts_by_category("announcements")

    m_query = db.query(models.CmsMediaItem)
    m_query = _scope_cms_media_by_user_sede(db, current_user, m_query)
    media = m_query.all()

    return schemas.CmsMetrics(
        testimonials_total=len(cms_testimonials),
        testimonials_approved=sum(
            1 for p in cms_testimonials if p.status == "published"
        ),
        announcements_total=len(cms_announcements),
        announcements_active=sum(
            1 for p in cms_announcements if p.status == "published"
        ),
        media_total=len(media),
        media_images=sum(
            1 for row in media if (row.mime_type or "").startswith("image/")
        ),
        media_videos=sum(
            1 for row in media if (row.mime_type or "").startswith("video/")
        ),
        media_audio=sum(
            1 for row in media if (row.mime_type or "").startswith("audio/")
        ),
    )


# ── F-10 (errorescms.md): limpieza de media items huerfanos ─────────
# Archiva (soft) o borra (hard) media_items activos de la sede del actor
# que no este referenciado por ninguna seccion de los sites de esa sede.
# El endpoint NO implementa cleanup a nivel plataforma (superadmin sin
# sede): el set de referenciados estaria mezclando sedes y podria
# archivar media que otra sede usa.  Acepta ``dry_run`` para preview y
# ``permanent`` (con guard de path traversal H-05) para hard-delete fisico.


@router.post("/cms/media/cleanup")
def cleanup_orphan_cms_media_endpoint(
    dry_run: bool = Query(default=False),
    permanent: bool = Query(default=False, description="Hard-delete files + rows (default: soft-archive)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Delete orphan media items (active but not referenced by any section).

    Scope (Axioma 3): opera sobre ``CmsMediaItem.sede_id == sede del
    actor``.  El set de IDs referenciados se construye escaneando los
    ``props_json`` de todas las secciones activas de los sites de esa
    sede via ``collect_section_media_ids``.  Un media item activo que no
    aparezca ahi es candidato a limpieza.

    ``dry_run=true`` retorna el count de candidatos sin mutar.  ``permanent=true``
    borra los archivos fisicos (con guards de path traversal H-05) y
    hard-deletea los rows; por defecto soft-archivea (``status=archived``).

    El superadmin sin sede no puede correr el cleanup a nivel plataforma
    (CRUD retorna 0): forzamos scope por sede.  Si el actor tiene sede,
    la operacion se ejecuta sobre esa sede.
    """
    actor_sede = _actor_sede_or_none(db, current_user)
    if actor_sede is None:
        # Superadmin canonico sin sede: no permitimos cleanup a nivel
        # plataforma para evitar mezclar referenciados de varias sedes.
        if dry_run:
            return {"purged": 0, "dry_run": True, "reason": "platform-scope disallowed"}
        raise HTTPException(
            status_code=400,
            detail="Cleanup requiere scope por sede; el superadmin sin sede no puede limpiar a nivel plataforma",
        )

    # Recolectar todos los sites de la sede y sus secciones activas.
    sites = (
        db.query(models.CmsSite)
        .filter(models.CmsSite.sede_id == actor_sede)
        .all()
    )
    referenced_ids: set[str] = set()
    for site in sites:
        # Secciones activas de TODAS las paginas del site (incluye draft
        # y published — un media referenciado por una pagina draft no es
        # huerfano todavia).
        sections = (
            db.query(models.CmsSection)
            .join(models.CmsPage, models.CmsPage.id == models.CmsSection.page_id)
            .filter(models.CmsPage.site_id == site.id)
            .filter(models.CmsSection.status != "archived")
            .filter(models.CmsSection.deleted_at.is_(None))
            .all()
        )
        for mid in collect_section_media_ids(sections):
            referenced_ids.add(mid)

    purged = crud.cleanup_orphan_cms_media(
        db,
        sede_id=actor_sede,
        referenced_media_ids=referenced_ids,
        actor_user_id=str(current_user.id),
        dry_run=dry_run,
        permanent=permanent,
    )
    return {"purged": purged, "dry_run": dry_run, "permanent": permanent}

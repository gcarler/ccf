from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api._cms_helpers import (
    _get_scoped_cms_announcement,
    _get_scoped_cms_media,
    _get_scoped_cms_testimonial,
    _scope_cms_announcements_by_user_sede,
    _scope_cms_media_by_user_sede,
    _scope_cms_testimonials_by_user_sede,
)
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.storage import storage_service
from backend.core.uploads import (
    ensure_allowed_extension,
    sanitize_filename,
    validate_mime_extension_alignment,
)
from backend.schemas import PaginatedResponse
from backend.services.image_optimizer import ImageOptimizer

# CMS endpoints — preferir /cms/v2/* en integraciones nuevas.
router = APIRouter(tags=["cms"])
logger = logging.getLogger(__name__)

settings = get_settings()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Testimonials (SQLAlchemy models) ────────────────────
# Axioma 3 — Multi-Tenant: Testimonial tiene sede_id propio (migration
# 2026-07-01). Endpoints admin filtran estrictamente por sede del staff;
# endpoints públicos (/cms/testimonials) siguen retornando sólo
# testimonios aprobados para preservar el feed público de la home.


@router.get("/cms/testimonials", response_model=list[schemas.TestimonialRead])
def list_cms_testimonials(db: Session = Depends(get_db)):
    """Public feed: testimonios aprobados son contenido visible en la home
    global de la plataforma (mismo tratamiento que announcements públicas).
    El filtro de aprobación (approved_only=True) protege el feed público.
    Los testimonios NO aprobados sólo aparecen en endpoints admin (filtrados
    por sede).
    """
    return crud.list_testimonials(db, approved_only=True)


@router.post(
    "/cms/testimonials", response_model=schemas.TestimonialRead, status_code=201
)
def create_cms_testimonial(
    payload: schemas.TestimonialCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Axioma 3 — Multi-Tenant: al crear un testimonial, derivamos su
    ``sede_id`` desde la persona del autor (si está presente) o el
    usuario actual. Esto permite que defense-in-depth en el CRUD layer
    valide que el target persona permanece en scope. Si el autor es NULL
    (testimonial anónimo creado por admin), se usa la sede del current_user.
    """
    # Derivar ``author_persona_id`` server-side cuando el payload no lo
    # especifica. NO asignar ``author_id`` (anterior int FK) porque
    # ``TestimonialCreate`` no expone ese campo: la única columna válida
    # es ``author_persona_id`` (UUID FK a personas). Body con
    # ``author_persona_id`` explícito del cliente pasa directo.
    if not payload.author_persona_id:
        resolved = crud.resolve_persona_id_for_user(
            db, getattr(current_user, "id", None)
        )
        if resolved:
            payload.author_persona_id = str(resolved)
    return crud.create_testimonial(
        db,
        payload,
        actor_user_id=str(current_user.id),
    )


@router.get("/admin/testimonials", response_model=list[schemas.TestimonialRead])
def list_admin_testimonials(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Axioma 3 — Multi-Tenant: filtro por sede del staff. Staff de sede_a
    ve SÓLO los testimonios de sede_a; staff sin sede (superadmin) ve
    todos (consistente con el resto del axioma)."""
    query = db.query(models.Testimonial)
    query = _scope_cms_testimonials_by_user_sede(db, current_user, query)
    return query.order_by(models.Testimonial.created_at.desc()).all()


@router.get(
    "/cms/testimonials/{testimonial_id}", response_model=schemas.TestimonialRead
)
def get_cms_testimonial(
    testimonial_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Public GET: mismo filtro dual que antes (approved_only +
    no-archived). NO se aplica scope de sede porque el testimonial
    aprobado es contenido público visible a cualquier visitante."""
    row = crud.get_testimonial(db, testimonial_id)
    if not row or not row.is_approved or row.status == "archived":
        raise HTTPException(status_code=404, detail="testimonial not found")
    return row


@router.get(
    "/admin/testimonials/{testimonial_id}", response_model=schemas.TestimonialRead
)
def get_admin_testimonial(
    testimonial_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Axioma 3 — Multi-Tenant: helper existence-leak-safe devuelve 404
    para cross-sede o inexistente."""
    return _get_scoped_cms_testimonial(db, current_user, testimonial_id)


@router.patch(
    "/admin/testimonials/{testimonial_id}", response_model=schemas.TestimonialRead
)
def patch_admin_testimonial(
    testimonial_id: uuid.UUID,
    payload: schemas.TestimonialUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Axioma 3 — Multi-Tenant: 404 cross-sede. Defense-in-depth CRUD
    re-valida scope sobre `author_persona_id` entrante si el body lo
    cambia."""
    row = _get_scoped_cms_testimonial(db, current_user, testimonial_id)
    return crud.update_testimonial(
        db,
        row,
        payload,
        actor_user_id=str(current_user.id),
    )


@router.delete("/admin/testimonials/{testimonial_id}", status_code=204)
def delete_admin_testimonial(
    testimonial_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Axioma 3 — Multi-Tenant: 404 cross-sede antes de soft-delete."""
    row = _get_scoped_cms_testimonial(db, current_user, testimonial_id)
    crud.delete_testimonial(
        db,
        row,
        actor_user_id=str(current_user.id),
    )


# ── Announcements (SQLAlchemy models) ───────────────────
# Axioma 3 — Multi-Tenant: Announcement tiene sede_id propio + FK a
# ``created_by_persona_id`` (migration 2026-07-01). Public feed sigue
# global para home; admin endpoints filtran estrictamente por sede.


@router.get("/cms/announcements", response_model=list[schemas.AnnouncementRead])
def list_cms_announcements(db: Session = Depends(get_db)):
    """Public feed: anuncios publicados son contenido visible en la home
    global de la plataforma, no se filtra por sede (un visitante de
    cualquier sede debe ver anuncios publicados). El filtro ``public_only``
    (status='published' AND published_at<=now) preserva el contrato."""
    return crud.list_announcements(db, public_only=True)


@router.post(
    "/cms/announcements", response_model=schemas.AnnouncementRead, status_code=201
)
def create_cms_announcement(
    payload: schemas.AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Axioma 3 — Multi-Tenant: ``sede_id`` y ``created_by_persona_id``
    se derivan server-side desde el current_user (no se aceptan del body
    para evitar que un editor fuerce sede_id distinto al suyo)."""
    return crud.create_announcement(
        db,
        payload,
        actor_user_id=str(current_user.id),
    )


@router.get("/admin/announcements", response_model=list[schemas.AnnouncementRead])
def list_admin_announcements(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Axioma 3 — Multi-Tenant: filtro por sede del staff."""
    query = db.query(models.Announcement)
    query = _scope_cms_announcements_by_user_sede(db, current_user, query)
    return query.order_by(models.Announcement.created_at.desc()).all()


@router.get(
    "/cms/announcements/{announcement_id}", response_model=schemas.AnnouncementRead
)
def get_cms_announcement(
    announcement_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Public GET: contrato previo preservado (status='published' AND
    published_at<=now). NO se aplica scope porque un anuncio publicado
    es contenido público."""
    row = crud.get_announcement(db, announcement_id)
    now = datetime.now(timezone.utc)
    if (
        not row
        or row.status != "published"
        or (row.published_at and row.published_at > now)
    ):
        raise HTTPException(status_code=404, detail="announcement not found")
    return row


@router.get(
    "/admin/announcements/{announcement_id}", response_model=schemas.AnnouncementRead
)
def get_admin_announcement(
    announcement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """Axioma 3 — Multi-Tenant: 404 cross-sede existence-leak safe."""
    return _get_scoped_cms_announcement(db, current_user, announcement_id)


@router.patch(
    "/admin/announcements/{announcement_id}", response_model=schemas.AnnouncementRead
)
def patch_admin_announcement(
    announcement_id: uuid.UUID,
    payload: schemas.AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Axioma 3 — Multi-Tenant: 404 cross-sede antes de mutar."""
    row = _get_scoped_cms_announcement(db, current_user, announcement_id)
    return crud.update_announcement(
        db,
        row,
        payload,
        actor_user_id=str(current_user.id),
    )


@router.delete("/admin/announcements/{announcement_id}", status_code=204)
def delete_admin_announcement(
    announcement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Axioma 3 — Multi-Tenant: 404 cross-sede antes de soft-delete."""
    row = _get_scoped_cms_announcement(db, current_user, announcement_id)
    crud.delete_announcement(
        db,
        row,
        actor_user_id=str(current_user.id),
    )


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

    Path traversal hardening (H-05): the resolved local path is normalised
    and restricted to the ``uploads`` root before any ``os.remove``. A
    malicious admin with ``cms:edit`` could otherwise store a crafted
    ``url`` (``../../etc/passwd``) and trigger an out-of-root delete via
    ``permanent=true``. Mirrors the guard already used by the optimize
    endpoint below.
    """
    row = _get_scoped_cms_media(db, current_user, item_id)
    if permanent:
        # Delete physical file first, then hard-delete DB row.
        if row.url:
            rel_path = row.url.lstrip("/").replace("uploads/", "", 1)
            full_path = os.path.normpath(os.path.join("/root/ccf/uploads", rel_path))
            if not full_path.startswith("/root/ccf/uploads"):
                raise HTTPException(status_code=400, detail="Invalid file path")
            if os.path.exists(full_path) and os.path.isfile(full_path):
                os.remove(full_path)
    crud.delete_cms_media_item(
        db,
        row.id,
        actor_user_id=str(current_user.id),
        permanent=permanent,
    )


@router.post("/cms/media/{item_id}/optimize", response_model=schemas.CmsMediaRead)
def optimize_cms_media(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Optimize an existing image: re-encode to WebP, resize, compress.
    Returns updated media item with new URL and file_size."""
    row = _get_scoped_cms_media(db, current_user, item_id)

    if not row.mime_type or not row.mime_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only images can be optimized")

    # Read original file from storage (path traversal guard)
    original_path = row.url.lstrip("/")
    full_path = os.path.normpath(os.path.join("/root/ccf/uploads", original_path.replace("uploads/", "")))
    if not full_path.startswith("/root/ccf/uploads"):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Original file not found")

    with open(full_path, "rb") as f:
        content = f.read()

    optimizer = ImageOptimizer()
    optimized_bytes, output_ext, width, height = optimizer.optimize(content, row.filename or "image.jpg")

    # Save optimized version (overwrite or new file)
    optimized_name = os.path.splitext(row.filename or "image.jpg")[0] + output_ext
    new_url = storage_service.save_file(optimized_bytes, optimized_name, subfolder="cms")

    # Update media item
    return crud.update_cms_media_item(
        db,
        row.id,
        url=new_url,
        mime_type=f"image/{output_ext.lstrip('.')}",
        file_size=len(optimized_bytes),
        filename=optimized_name,
        width=width,
        height=height,
        dimensions=f"{width}x{height}",
        actor_user_id=str(current_user.id),
    )


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
    """Hardened upload pipeline (Axioma 3 + Defense-in-Depth):

    1. **Size guardrail** — rejects uploads larger than ``MAX_UPLOAD_SIZE``
       (10 MiB). Evita OOM en storage_service con payloads arbitrarios.
    2. **Extension allow-list** — ``ensure_allowed_extension`` bloquea
       extensiones fuera de ``ALLOWED_EXTENSIONS`` (png/jpg/jpeg/gif/webp/
       pdf/mp4/mp3/wav/zip). Cierra el vector donde un cliente sube un
       ``.exe`` o ``.html`` que storage_service aceptaría sin filtro.
    3. **MIME/extension alignment** — ``validate_mime_extension_alignment``
       verifica que el ``Content-Type`` declarado por el cliente sea
       coherente con la extensión del archivo. Defense-in-depth sobre el
       allow-list: si el cliente sube ``malware.png`` con
       ``Content-Type: application/x-msdownload``, el allow-list lo
       aceptaría (extensión válida), pero el alignment check lo rechaza.
    4. **Filename sanitization** — ``sanitize_filename`` remueve chars
       no-seguros y previene path traversal antes de persistir.
    5. **Image optimization** — images are auto-optimized to WebP (max 1920px, quality 82%)
       unless optimize=false. Dramatically reduces file size.
    6. **Axioma 3** — ``actor_user_id`` se propaga al CRUD layer, donde
       ``create_cms_media_item`` resuelve ``sede_id`` server-side desde
       el actor (no del body) y previene cross-sede injection.
    """
    content = await file.read()
    original_name = sanitize_filename(file.filename or "asset.bin")

    # 1) Size guardrail
    from backend.core.uploads import MAX_UPLOAD_SIZE
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds maximum size")

    # 2) Extension allow-list (bloquea .exe, .html, .js, .sh, ...).
    try:
        ensure_allowed_extension(original_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 3) MIME/extension alignment (defense-in-depth sobre allow-list).
    try:
        validate_mime_extension_alignment(original_name, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 4) Image optimization (convert to WebP, resize, compress)
    mime_type = file.content_type
    width: int | None = None
    height: int | None = None
    dimensions: str | None = None
    if optimize:
        try:
            optimizer = ImageOptimizer()
            optimized_bytes, output_ext, width, height = optimizer.optimize(content, original_name)
            if output_ext != os.path.splitext(original_name)[1].lower():
                # Extension changed (e.g. .jpg → .webp)
                original_name = os.path.splitext(original_name)[0] + output_ext
                mime_type = f"image/{output_ext.lstrip('.')}"
            content = optimized_bytes
            if width and height:
                dimensions = f"{width}x{height}"
        except Exception as exc:
            logger.debug("Image optimization failed for %s, falling back to original: %s", original_name, exc)

    url = storage_service.save_file(content, original_name, subfolder="cms")
    parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return crud.create_cms_media_item(
        db,
        url=url,
        alt_text=alt_text or file.filename,
        section=section,
        tags=parsed_tags,
        created_by=current_user.id,
        filename=file.filename,
        mime_type=mime_type,
        file_size=len(content),
        width=width,
        height=height,
        dimensions=dimensions,
        actor_user_id=str(current_user.id),
    )


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

    # Scoped queries para User-Generated content:
    t_query = db.query(models.Testimonial)
    t_query = _scope_cms_testimonials_by_user_sede(db, current_user, t_query)
    testimonials = t_query.all()

    a_query = db.query(models.Announcement)
    a_query = _scope_cms_announcements_by_user_sede(db, current_user, a_query)
    announcements = a_query.all()

    m_query = db.query(models.CmsMediaItem)
    m_query = _scope_cms_media_by_user_sede(db, current_user, m_query)
    media = m_query.all()

    return schemas.CmsMetrics(
        testimonials_total=len(testimonials),
        testimonials_approved=sum(1 for row in testimonials if row.is_approved),
        announcements_total=len(announcements),
        announcements_active=sum(
            1 for row in announcements if row.status == "published"
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

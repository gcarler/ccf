"""CMS: Page content, media, CMS v2 (sites, themes, menus, pages, sections, versions).

Axioma 3 — Multi-Tenant (Fase 5 — CRUD Layer defense-in-depth): las
funciones mutantes de User-Generated Content (Testimonial, Announcement,
CmsMediaItem) y PastoralProfile re-validan scope Multi-Tenant antes de
persistir cambios, propagando actor_user_id desde el caller API. Esto
cierra el TOCTOU gap donde un caller no-API (worker async, script de
seeding, llamada directa al CRUD) podría crear/mutar registros sin
pasar por el helper API `_get_scoped_*` correspondiente.
"""

import datetime as dt
import logging
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, lazyload

from backend import models, schemas
from backend.crud._utils import _utcnow
from backend.crud.crm import (
    resolve_persona_id_for_user as resolve_persona_uuid_for_user,
)

_logger = logging.getLogger(__name__)


# ``resolve_persona_id_for_user`` (imported as ``resolve_persona_uuid_for_user``
# above) comes from ``backend.crud.crm`` which re-exports the canonical
# implementation in ``backend.crud.crm_.shared``. We call that directly
# throughout this module — the previous local wrapper added only
# indirection (M-10 in ``errorescms.md``).



from backend.core.cache_v2 import invalidate_cached_public, invalidate_cached_public_pattern
from backend.crud.cms._shared import _commit_or_conflict, resolve_site_key


def list_cms_pages(
    db: Session,
    site_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
):
    query = db.query(models.CmsPage).filter(models.CmsPage.site_id == site_id)
    if status:
        query = query.filter(models.CmsPage.status == status)
    total = query.count()
    items = query.order_by(models.CmsPage.updated_at.desc()).offset(skip).limit(limit).all()
    return items, total



def get_cms_page(db: Session, site_id: uuid.UUID, slug: str):
    return db.query(models.CmsPage).filter(models.CmsPage.site_id == site_id, models.CmsPage.slug == slug).first()



def create_cms_page(
    db: Session,
    site_id: uuid.UUID,
    payload: schemas.CmsPageCreate,
    user_id: uuid.UUID | None,
    *,
    commit_with_conflict_check: bool = False,
):
    row = models.CmsPage(
        site_id=site_id,
        slug=payload.slug.strip().lower(),
        title=payload.title.strip(),
        status=payload.status,
        seo_json=payload.seo_json or {},
        created_by_persona_id=resolve_persona_uuid_for_user(db, user_id),
        updated_by_persona_id=resolve_persona_uuid_for_user(db, user_id),
    )
    db.add(row)
    if commit_with_conflict_check and not _commit_or_conflict(db):
        return None
    elif not commit_with_conflict_check:
        db.commit()
    db.refresh(row)
    return row



def update_cms_page(
    db: Session,
    row: models.CmsPage,
    payload: schemas.CmsPageUpdate,
    user_id: uuid.UUID | None,
):
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        row.slug = str(data["slug"]).strip().lower()
    if "title" in data and data["title"] is not None:
        row.title = str(data["title"]).strip()
    if "status" in data and data["status"] is not None:
        row.status = str(data["status"]).strip()
    if "seo_json" in data and data["seo_json"] is not None:
        row.seo_json = data["seo_json"]
    # Scheduled publish + auto-archive (2026-07-06): scheduling fields. El
    # validador ``_validate_schedule_window`` corre en el PATCH endpoint,
    # pero aquí defendemos in-depth: si por alguna vía el ``expires_at``
    # queda anterior a ``publish_at``, se acepta (semánticamente: "auto
    # archive al mismo tiempo que publica") y se deja al editor la
    # responsabilidad operacional. El null es el reset explícito: borrar
    # fecha para que el scheduler no toque el row.
    if "publish_at" in data:
        row.publish_at = data["publish_at"]
    if "expires_at" in data:
        row.expires_at = data["expires_at"]
    if user_id is not None:
        row.updated_by_persona_id = resolve_persona_uuid_for_user(db, user_id)
    db.commit()
    db.refresh(row)
    # Cierre de staleness: slug/title/status/seo alteran la respuesta
    # pública cacheada de la página (detail) y el listado de páginas.
    _invalidate_public_page_cache(db, row)
    return row



def clone_cms_page(
    db: Session,
    source: models.CmsPage,
    new_slug: str,
    user_id: uuid.UUID | None,
    *,
    new_title: str | None = None,
):
    """Clone a CMS page with all its active sections (F-02).

    La página clonada siempre arranca como ``draft`` sin
    ``published_version_id`` y sin schedule (``publish_at``/``expires_at``
    en None).  Las secciones se duplican con nuevos IDs y nuevos
    ``section_key`` (UUID hex) para evitar colisiones de unique-key.

    El caller API es responsable de verificar scope (``_get_scoped_site_or_404``)
    y unicidad del slug destino.  Este helper asume que ``new_slug`` ya
    pasó por ``_slugify`` y no existe en el site.
    """
    persona_id = resolve_persona_uuid_for_user(db, user_id)
    cloned_page = models.CmsPage(
        site_id=source.site_id,
        slug=new_slug,
        title=(new_title or source.title).strip(),
        status="draft",
        seo_json=dict(source.seo_json or {}),
        published_version_id=None,
        locale=source.locale,
        publish_at=None,
        expires_at=None,
        created_by_persona_id=persona_id,
        updated_by_persona_id=persona_id,
    )
    db.add(cloned_page)
    db.flush()  # populate cloned_page.id for FK sections

    # Clone active sections (exclude archived/soft-deleted)
    sections, _ = list_cms_sections(db, source.id, limit=1000)
    active_sections = [s for s in sections if s.status != "archived" and s.deleted_at is None]
    for source_section in active_sections:
        cloned_section = models.CmsSection(
            page_id=cloned_page.id,
            section_key=uuid.uuid4().hex,
            type=source_section.type,
            props_json=dict(source_section.props_json or {}),
            sort_order=source_section.sort_order,
            is_visible=source_section.is_visible,
            status="active",
            is_global=source_section.is_global,
            global_key=None,  # don't clone global_key uniqueness
            locale=source_section.locale,
            created_by_persona_id=persona_id,
            updated_by_persona_id=persona_id,
        )
        db.add(cloned_section)

    if not _commit_or_conflict(db):
        return None
    db.refresh(cloned_page)
    return cloned_page



def delete_cms_page(db: Session, row: models.CmsPage) -> bool:
    # M-03 (errorescms.md): alinea pages con sections (H-04): ademas de
    # ``status="archived"``, fija ``deleted_at`` para que las queries que
    # filtren por ``deleted_at.is_(None)`` (patron sections) tambien
    # capturen las paginas archivadas.  Las queries existentes que filtran
    # por ``status != "archived"`` no se ven afectadas.
    row.status = "archived"
    row.deleted_at = _utcnow()
    db.commit()
    # Cierre de staleness: la página archivada deja de servirse en el
    # endpoint público de inmediato (404), sin esperar el TTL de 300s.
    _invalidate_public_page_cache(db, row)
    return True



def list_cms_sections(
    db: Session,
    page_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    section_type: str | None = None,
):
    # lazyload('*') evita el cascade de JOINs ``CmsSection.page`` (lazy joined)
    # → ``CmsPage.site`` → ``cms_sites.sede`` → ``personas`` + ``page_versions``
    # que inflaba cada query de secciones a ~10 JOINs. El consumidor
    # (public_page) solo serializa columnas planas de ``CmsSection`` (type,
    # props_json, sort_order, is_visible, status) — no toca relaciones.
    query = db.query(models.CmsSection).options(lazyload("*")).filter(models.CmsSection.page_id == page_id)
    if section_type:
        query = query.filter(models.CmsSection.type == section_type)
    total = query.count()
    items = (
        query.order_by(models.CmsSection.sort_order.asc(), models.CmsSection.id.asc()).offset(skip).limit(limit).all()
    )
    return items, total



def create_cms_section(
    db: Session,
    page_id: uuid.UUID,
    payload: schemas.CmsSectionCreate,
    *,
    commit_with_conflict_check: bool = False,
):
    row = models.CmsSection(
        page_id=page_id,
        section_key=(payload.section_key or uuid.uuid4().hex),
        type=payload.type,
        props_json=payload.props_json or {},
        sort_order=payload.sort_order,
        is_visible=payload.is_visible,
        status=(payload.status or "active").strip().lower(),
        is_global=getattr(payload, "is_global", False) or False,
    )
    db.add(row)
    if commit_with_conflict_check and not _commit_or_conflict(db):
        return None
    elif not commit_with_conflict_check:
        db.commit()
    db.refresh(row)
    # Cierre de staleness: una sección nueva cambia el render público de
    # la página padre cacheada.
    _invalidate_public_page_sections_cache(db, page_id)
    return row



def get_cms_section(
    db: Session,
    page_id: uuid.UUID,
    section_id: uuid.UUID,
    *,
    site_id: uuid.UUID | None = None,
):
    """Retrieve a CMS section by page and section id.

    When ``site_id`` is provided, an extra JOIN + WHERE guarantees that
    the parent ``CmsPage`` belongs to the requested site (Axioma 3
    defense-in-depth). Existing callers that already scoped the page
    can omit the parameter and keep the previous behavior.
    """
    query = db.query(models.CmsSection).filter(
        models.CmsSection.page_id == page_id,
        models.CmsSection.id == section_id,
    )
    if site_id is not None:
        query = query.join(models.CmsPage, models.CmsSection.page_id == models.CmsPage.id).filter(
            models.CmsPage.site_id == site_id
        )
    return query.first()



def update_cms_section(db: Session, row: models.CmsSection, payload: schemas.CmsSectionUpdate):
    from backend.schemas.cms_v2_sections import validate_section_props

    data = payload.model_dump(exclude_unset=True)
    for field in ["type", "sort_order", "is_visible", "status", "is_global", "global_key"]:
        if field in data and data[field] is not None:
            setattr(row, field, data[field])
    if "props_json" in data and data["props_json"] is not None:
        # Defense-in-depth: re-sanitise props_json on every update, even if
        # the caller already validated it. This protects direct CRUD callers.
        section_type = data.get("type") or row.type
        row.props_json = validate_section_props(section_type, data["props_json"])
    db.commit()
    db.refresh(row)
    # Cierre de staleness: type/sort_order/is_visible/status/props alteran
    # el render público cacheado de la página padre.
    _invalidate_public_page_sections_cache(db, row.page_id)
    return row



def delete_cms_section(db: Session, row: models.CmsSection) -> bool:
    return archive_cms_section(db, row) is not None



def archive_cms_section(db: Session, row: models.CmsSection) -> models.CmsSection:
    row.status = "archived"
    # H-04 (errorescms.md): al archivar de tambien se fija ``deleted_at``
    # para que las queries de readiness que filtran por
    # ``deleted_at.is_(None)`` (cms_v2.py:1181,1196,1205) y las que filtran
    # por ``status != "archived"`` queden alineadas semanticamente.  Sin
    # este seteo, archived_sections tenian status="archived" pero
    # ``deleted_at`` None; los OR-compuestos los capturaban de todas
    # formas (defense-in-depth), pero era una inconsistencia semantica
    # que podia romper queries futuras que usen solo ``deleted_at``.
    row.deleted_at = _utcnow()
    db.commit()
    db.refresh(row)
    # Cierre de staleness: archivar una sección la oculta del render
    # público cacheado de la página padre de inmediato.
    _invalidate_public_page_sections_cache(db, row.page_id)
    return row



def reorder_cms_sections(db: Session, page_id: uuid.UUID, items: list[schemas.CmsSectionReorderItem]):
    rows_by_id = {row.id: row for row in db.query(models.CmsSection).filter(models.CmsSection.page_id == page_id).all()}
    for item in items:
        row = rows_by_id.get(item.id)
        if not row:
            continue
        row.sort_order = item.sort_order
    db.commit()
    # Cierre de staleness: el orden de secciones afecta el render público
    # cacheado de la página padre.
    _invalidate_public_page_sections_cache(db, page_id)
    items_list, _ = list_cms_sections(db, page_id)
    return items_list



def _invalidate_public_page_cache(db: Session, row: models.CmsPage) -> None:
    """Invalida la caché pública de una página (detail + listado).

    Reconstruye la key del detalle con ``site_key`` + ``slug`` (los
    mismos kwargs serializables que ``public_page`` recibe) y borra todas
    las variantes del listado ``public_pages_list`` (skip/limit variables).
    """
    try:
        site_key = resolve_site_key(db, row.site_id)
        if not site_key:
            return
        invalidate_cached_public("public_page", site_key=site_key, slug=row.slug)
        invalidate_cached_public_pattern("public_pages_list")
        # El sitemap publica el conjunto de páginas publicadas del sitio.
        # Sin esta invalidación, una publicación/archivo podía permanecer
        # oculto o visible hasta que venciera el TTL de cinco minutos.
        invalidate_cached_public("public_sitemap", site_key=site_key)
    except Exception:  # la invalidación nunca debe romper la mutación
        _logger.debug("public page cache invalidation skipped", exc_info=True)



def _invalidate_public_page_sections_cache(db: Session, page_id: uuid.UUID) -> None:
    """Invalida la caché pública de la página que contiene una sección.

    El render público serializa las secciones activas de la página
    (``is_visible`` / ``status != archived``), así que crear/editar/
    archivar/reordenar una sección cambia la respuesta cacheada de su
    página padre.
    """
    try:
        page = (
            db.query(models.CmsPage)
            .filter(models.CmsPage.id == page_id)
            .first()
        )
        if page is not None:
            _invalidate_public_page_cache(db, page)
    except Exception:  # la invalidación nunca debe romper la mutación
        _logger.debug("public page sections cache invalidation skipped", exc_info=True)



def _build_page_snapshot(db: Session, page: models.CmsPage):
    # ``list_cms_sections`` returns a ``(items, total)`` tuple (paginated
    # contract). The previous code iterated the tuple unpacking its members;
    # ``for section in sections`` would yield the list *and* the int total,
    # causing ``section.section_key`` to AttributeError and crashing
    # ``create_cms_page_version`` in production.
    sections, _ = list_cms_sections(db, page.id)

    def _jsonable(value):
        # Convert SQLAlchemy/runtime types into JSON-serializable primitives.
        # UUID and datetime objects cannot be encoded by ``json.dumps`` which
        # is what SQLAlchemy uses for JSONB columns; this helper avoids the
        # ``TypeError: Object of type UUID is not JSON serializable`` that
        # crashed ``create_cms_page_version`` on first publish.
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, (dt.date, dt.datetime)):
            return value.isoformat()
        return value

    return {
        "page": {
            "id": _jsonable(page.id),
            "slug": _jsonable(page.slug),
            "title": _jsonable(page.title),
            "status": _jsonable(page.status),
            "seo_json": page.seo_json or {},
        },
        "sections": [
            {
                "id": _jsonable(section.id),
                "section_key": _jsonable(section.section_key),
                "type": _jsonable(section.type),
                "props_json": section.props_json or {},
                "sort_order": _jsonable(section.sort_order),
                "is_visible": _jsonable(section.is_visible),
                "status": _jsonable(getattr(section, "status", "active") or "active"),
            }
            for section in sections
        ],
    }



def create_cms_page_version(db: Session, page: models.CmsPage, user_id: uuid.UUID | None, notes: str | None = None):
    max_version = (
        db.query(func.max(models.CmsPageVersion.version_number))
        .filter(models.CmsPageVersion.page_id == page.id)
        .scalar()
        or 0
    )
    snapshot = _build_page_snapshot(db, page)
    row = models.CmsPageVersion(
        page_id=page.id,
        version_number=int(max_version) + 1,
        snapshot_json=snapshot,
        notes=notes,
        created_by_persona_id=resolve_persona_uuid_for_user(db, user_id),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def list_cms_page_versions(
    db: Session,
    page_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
):
    query = db.query(models.CmsPageVersion).filter(models.CmsPageVersion.page_id == page_id)
    total = query.count()
    items = query.order_by(models.CmsPageVersion.version_number.desc()).offset(skip).limit(limit).all()
    return items, total



def get_cms_page_version(db: Session, page_id: uuid.UUID, version_id: uuid.UUID):
    return (
        db.query(models.CmsPageVersion)
        .filter(
            models.CmsPageVersion.page_id == page_id,
            models.CmsPageVersion.id == version_id,
        )
        .first()
    )



def list_cms_publish_logs(
    db: Session,
    site_id: uuid.UUID,
    *,
    page_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
):
    query = db.query(models.CmsPublishLog).filter(models.CmsPublishLog.site_id == site_id)
    if page_id is not None:
        query = query.filter(models.CmsPublishLog.page_id == page_id)
    total = query.count()
    items = query.order_by(models.CmsPublishLog.created_at.desc()).offset(skip).limit(limit).all()
    return items, total



def restore_cms_page_version(
    db: Session,
    page: models.CmsPage,
    version: models.CmsPageVersion,
    user_id: uuid.UUID | None,
):
    snapshot = version.snapshot_json or {}
    page_data = snapshot.get("page") or {}
    sections_data = snapshot.get("sections") or []
    if isinstance(page_data, dict):
        page.slug = str(page_data.get("slug") or page.slug)
        page.title = str(page_data.get("title") or page.title)
        page.seo_json = page_data.get("seo_json") or {}
    page.status = "draft"
    page.updated_by_persona_id = resolve_persona_uuid_for_user(db, user_id)
    db.query(models.CmsSection).filter(models.CmsSection.page_id == page.id).delete(synchronize_session=False)
    for idx, section_data in enumerate(sections_data):
        if not isinstance(section_data, dict):
            continue
        db.add(
            models.CmsSection(
                page_id=page.id,
                section_key=str(section_data.get("section_key") or uuid.uuid4().hex),
                type=str(section_data.get("type") or "rich_text"),
                props_json=section_data.get("props_json") or {},
                sort_order=int(section_data.get("sort_order") or idx),
                is_visible=bool(section_data.get("is_visible", True)),
                status=str(section_data.get("status") or "active"),
            )
        )
    db.commit()
    db.refresh(page)
    # Cierre de staleness: un rollback devuelve la página a ``draft`` — si
    # estaba publicada, deja de servirse en el endpoint público de
    # inmediato (404), sin esperar el TTL de 300s.
    _invalidate_public_page_cache(db, page)
    return page



def transition_cms_page_status(
    db: Session,
    page: models.CmsPage,
    action: str,
    user_id: uuid.UUID | None,
    notes: str | None = None,
):
    action = action.strip().lower()
    action_map = {
        "submit_review": "in_review",
        "approve": "approved",
        "publish": "published",
        "archive": "archived",
        "revert_draft": "draft",
    }
    if action not in action_map:
        return None
    next_status = action_map[action]
    previous_status = page.status
    if action == "publish":
        # Sync the public pastors page with live pastoral profiles before
        # snapshotting, so the published version always reflects the current
        # pastoral team without requiring manual section edits.
        if page.slug == "pastors":
            from backend.crud import cms_pastors_sync

            cms_pastors_sync.update_pastors_section_from_profiles(db)
        version = create_cms_page_version(db, page, user_id=user_id, notes=notes)
        page.published_version_id = version.id
    page.status = next_status
    actor_persona_id = resolve_persona_uuid_for_user(db, user_id)
    page.updated_by_persona_id = actor_persona_id
    db.add(
        models.CmsPublishLog(
            site_id=page.site_id,
            page_id=page.id,
            entity_type="page",
            entity_id=str(page.id),
            action=action,
            from_status=previous_status,
            to_status=next_status,
            actor_persona_id=actor_persona_id,
            metadata_json={"notes": notes} if notes else {},
        )
    )
    db.commit()
    db.refresh(page)
    # Cierre de staleness: publish/archive/revert cambia la visibilidad y
    # el contenido publicado de la página en el endpoint público.
    _invalidate_public_page_cache(db, page)
    return page



def get_public_cms_page(db: Session, site_id: uuid.UUID, slug: str):
    return (
        db.query(models.CmsPage)
        .filter(
            models.CmsPage.site_id == site_id,
            models.CmsPage.slug == slug,
            models.CmsPage.status == "published",
        )
        .first()
    )



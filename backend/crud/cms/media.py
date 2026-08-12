"""CMS: Page content, media, CMS v2 (sites, themes, menus, pages, sections, versions).

Axioma 3 — Multi-Tenant (Fase 5 — CRUD Layer defense-in-depth): las
funciones mutantes de User-Generated Content (Testimonial, Announcement,
CmsMediaItem) y PastoralProfile re-validan scope Multi-Tenant antes de
persistir cambios, propagando actor_user_id desde el caller API. Esto
cierra el TOCTOU gap donde un caller no-API (worker async, script de
seeding, llamada directa al CRUD) podría crear/mutar registros sin
pasar por el helper API `_get_scoped_*` correspondiente.
"""

import logging
import os
import uuid
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models
from backend.core.config import get_settings
from backend.crud.crm import (
    resolve_persona_id_for_user as resolve_persona_uuid_for_user,
)

_logger = logging.getLogger(__name__)


# ``resolve_persona_id_for_user`` (imported as ``resolve_persona_uuid_for_user``
# above) comes from ``backend.crud.crm`` which re-exports the canonical
# implementation in ``backend.crud.crm_.shared``. We call that directly
# throughout this module — the previous local wrapper added only
# indirection (M-10 in ``errorescms.md``).



from backend.crud.cms._shared import (
    _actor_sede_or_none_cms,
    _crud_scope_re_check_cms_content_create,
    _crud_scope_re_check_cms_content_update,
)


def create_cms_media_item(
    db: Session,
    *,
    url: str,
    alt_text: str | None,
    section: str,
    tags: list[str] | None,
    created_by: str | uuid.UUID,
    filename: str | None = None,
    mime_type: str | None = None,
    file_size: int | None = None,
    width: int | None = None,
    height: int | None = None,
    dimensions: str | None = None,
    status: str = "active",
    actor_user_id: str | uuid.UUID,
):
    """Axioma 3 — Multi-Tenant: deriva ``sede_id`` de la persona creadora
    y re-valida scope Multi-Tenant pre-add via
    ``_crud_scope_re_check_cms_content_create``.

    Si el actor tiene sede asignada y el creator persona es de OTRA sede
    o es unresoluble, raise 404. Superadmin / anterior path (actor sin sede)
    bypassea — consistente con resto del axioma 3.
    """
    creator_persona_id = resolve_persona_uuid_for_user(db, created_by)
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    derived_sede = _crud_scope_re_check_cms_content_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        author_persona_id=creator_persona_id,
    )

    row = models.CmsMediaItem(
        url=url,
        alt_text=alt_text,
        section=section,
        tags=tags or [],
        created_by_persona_id=creator_persona_id,
        sede_id=derived_sede,
        filename=filename,
        mime_type=mime_type,
        file_size=file_size or 0,
        width=width,
        height=height,
        dimensions=dimensions,
        status=(status or "active").strip().lower(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def list_cms_media_items(
    db: Session,
    *,
    query: str | None = None,
    section: str | None = None,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
):
    q = db.query(models.CmsMediaItem)
    if not include_archived:
        q = q.filter(models.CmsMediaItem.status != "archived")
    if section:
        q = q.filter(models.CmsMediaItem.section == section)
    if query:
        like = f"%{query.strip()}%"
        q = q.filter(
            or_(
                models.CmsMediaItem.url.ilike(like),
                models.CmsMediaItem.alt_text.ilike(like),
                models.CmsMediaItem.filename.ilike(like),
            )
        )
    total = q.count()
    items = q.order_by(models.CmsMediaItem.updated_at.desc()).offset(skip).limit(limit).all()
    return items, total



def get_cms_media_item(db: Session, item_id: uuid.UUID):
    return db.query(models.CmsMediaItem).filter(models.CmsMediaItem.id == item_id).first()



def update_cms_media_item(
    db: Session,
    item_id: uuid.UUID,
    *,
    url: str | None = None,
    alt_text: str | None = None,
    section: str | None = None,
    tags: list[str] | None = None,
    filename: str | None = None,
    mime_type: str | None = None,
    file_size: int | None = None,
    width: int | None = None,
    height: int | None = None,
    dimensions: str | None = None,
    status: str | None = None,
    actor_user_id: str | uuid.UUID,
):
    """Axioma 3 — Multi-Tenant: defense-in-depth pre-mutation.

    El caller debe haber ya apuntado una fila via API-layer helper
    (``_get_scoped_cms_media``) que garantiza 404 cross-sede en retrieval.
    Este helper re-valida por si la fila fue movida cross-sede entre el
    fetch y el re-fetch (TOCTOU gap).
    """
    row = get_cms_media_item(db, item_id)
    if not row:
        return None
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.created_by_persona_id,
    )
    if url is not None:
        row.url = url
    if alt_text is not None:
        row.alt_text = alt_text
    if section is not None:
        row.section = section
    if tags is not None:
        row.tags = tags
    if filename is not None:
        row.filename = filename
    if mime_type is not None:
        row.mime_type = mime_type
    if file_size is not None:
        row.file_size = file_size
    if width is not None:
        row.width = width
    if height is not None:
        row.height = height
    if dimensions is not None:
        row.dimensions = dimensions
    if status is not None:
        row.status = status.strip().lower()
    db.commit()
    db.refresh(row)
    return row



def delete_cms_media_item(
    db: Session,
    item_id: uuid.UUID,
    *,
    actor_user_id: str | uuid.UUID,
    permanent: bool = False,
) -> bool:
    """Axioma 3 -- Multi-Tenant: defense-in-depth pre soft-delete.

    Retorna ``False`` tanto para inexistente como para cross-sede (llamada
    equivalente al ``_get_scoped_cms_media`` que ya hizo el API). El API
    layer traduce esto a ``HTTPException(404)``.

    Si ``permanent=True``, ejecuta hard delete (db.delete) en vez de
    soft delete (status='archived').
    """
    row = get_cms_media_item(db, item_id)
    if not row:
        return False
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    _crud_scope_re_check_cms_content_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(row.sede_id) if row.sede_id else None,
        incoming_author_persona_id=row.created_by_persona_id,
    )
    if permanent:
        db.delete(row)
    else:
        row.status = "archived"
    db.commit()
    return True



def cleanup_orphan_cms_media(
    db: Session,
    *,
    sede_id: uuid.UUID | str | None,
    referenced_media_ids: set[str],
    actor_user_id: str | uuid.UUID,
    dry_run: bool = False,
    permanent: bool = False,
) -> int:
    """F-10 (errorescms.md): archiva (o borra) media items activos de la
    sede del actor que NO esten referenciados por ninguna seccion.

    Args:
        db: ``Session`` de BD.
        sede_id: ``sede_id`` del actor.  ``None`` solo para superadmin
            canonico sin sede; en ese caso NO aplica la operacion (retorna 0)
            — la limpieza de orfanos esta scopeada por sede y no se permite
            ejecutar a nivel plataforma para evitar borrar media que otra
            sede podria estar usando.
        referenced_media_ids: set de IDs (como ``str`` canonico) que si
            estan referenciados por secciones.  El caller los arma via
            ``collect_section_media_ids``.  Un ID ausente de este set se
            considera huerfano.
        actor_user_id: Actor UUID del usuario autenticado (para la
            revalidacion de scope y la huella de auditoria).
        dry_run: Si True, solo retorna el count sin mutar.
        permanent: Si True, hard-deletea el archivo fisico (con guard
            H-05) y el row.  Si False, soft-archive (``status=archived``).

    Returns:
        Numero de items archivados/borrados (o que se procesarian en
        ``dry_run``).
    """
    if sede_id is None:
        # Superadmin sin sede no puede limpiar orfanos a nivel plataforma:
        # el set de referenciados estaria mezclando sedes y borraria media
        # ajena.  Forzar scope por sede.
        return 0

    txn_sede = str(sede_id)
    # Axioma 3 — defense-in-depth en CRUD: re-check de que el actor
    # efectivamente pertenece a ``sede_id`` (cubre callers no-API como
    # el scheduler via la variante ``*_scheduled``).  El API layer ya
    # pre-filtro por ``_actor_sede_or_none``; el re-check CRUD cierra
    # el TOCTOU gap donde un caller directo al CRUD podria pedir limpiar
    # otra sede pasando un ``sede_id`` ajeno + ``actor_user_id`` propio.
    actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
    if actor_sede is not None and str(actor_sede) != txn_sede:
        # El actor no pertenece a la sede que pretende limpiar.  No
        # muta nada; el API layer traduce segun contrato (normally 403).
        return 0

    return _apply_cleanup_orphan_cms_media(
        db,
        sede_id=sede_id,
        referenced_media_ids=referenced_media_ids,
        dry_run=dry_run,
        permanent=permanent,
    )



def cleanup_orphan_cms_media_scheduled(
    db: Session,
    *,
    sede_id: uuid.UUID | str,
    referenced_media_ids: set[str],
    dry_run: bool = False,
    permanent: bool = False,
) -> int:
    """F-10 — variante del cleanup para invocacion desde ``scheduler.py``.

    No requiere ``actor_user_id`` (operacion de mantenimiento operacional,
    no creacion/mutacion de UGC con autor); el scheduler corre sin sesion
    HTTP igual que ``process_due_content`` (user_id=None en CmsPublishLog).

    Axioma 3 sigue cubierto por el scope explicito ``sede_id``: la
    mutacion solo opera sobre ``CmsMediaItem.sede_id == sede_id`` y no
    hay forma de pasar una sede ajena desde el scheduler (la sede se
    itera dentro del scheduler a partir de ``models.Sede``).

    No expone ``actor_user_id`` porque no existe actor autenticado en
    el contexto del cron; cualquier caller que SI tenga actor debe usar
    ``cleanup_orphan_cms_media`` (API path) que aplica el defense-in-depth
    re-check.
    """
    if sede_id is None:
        return 0
    return _apply_cleanup_orphan_cms_media(
        db,
        sede_id=sede_id,
        referenced_media_ids=referenced_media_ids,
        dry_run=dry_run,
        permanent=permanent,
    )



def _apply_cleanup_orphan_cms_media(
    db: Session,
    *,
    sede_id: uuid.UUID | str,
    referenced_media_ids: set[str],
    dry_run: bool = False,
    permanent: bool = False,
) -> int:
    """Mutacion interna compartida por la API + la variante scheduled."""
    referenced = {str(mid) for mid in referenced_media_ids}
    active_media = (
        db.query(models.CmsMediaItem)
        .filter(models.CmsMediaItem.sede_id == sede_id)
        .filter(models.CmsMediaItem.status != "archived")
        .all()
    )
    orphans = [m for m in active_media if str(m.id) not in referenced]

    if dry_run:
        return len(orphans)

    purged = 0
    for row in orphans:
        if permanent:
            # Guard H-05: path traversal hardening antes de os.remove.
            if row.url:
                rel = row.url.lstrip("/").replace("uploads/", "", 1)
                uploads_root = os.path.abspath(get_settings().uploads_dir)
                full = os.path.normpath(os.path.join(uploads_root, rel))
                try:
                    Path(full).resolve(strict=False).relative_to(Path(uploads_root).resolve(strict=False))
                except ValueError:
                    # url malformado/posible traversal: no se borra el
                    # archivo fisico, pero se archiva el row (mas seguro
                    # que fallar el cleanup completo).
                    row.status = "archived"
                else:
                    if os.path.exists(full) and os.path.isfile(full):
                        os.remove(full)
                        db.delete(row)
                    else:
                        # Archivo fisico ya ausente: borra el row.
                        db.delete(row)
            else:
                db.delete(row)
        else:
            row.status = "archived"
        purged += 1

    if purged:
        db.commit()
    return purged




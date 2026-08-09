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

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm import (
    resolve_persona_id_for_user as resolve_persona_uuid_for_user,
)

_logger = logging.getLogger(__name__)


# ``resolve_persona_id_for_user`` (imported as ``resolve_persona_uuid_for_user``
# above) comes from ``backend.crud.crm`` which re-exports the canonical
# implementation in ``backend.crud.crm_.shared``. We call that directly
# throughout this module — the previous local wrapper added only
# indirection (M-10 in ``errorescms.md``).



def _commit_or_conflict(db: Session) -> bool:
    """Commit helper for create functions. Returns True on success.

    A **unique-key** ``IntegrityError`` is swallowed, the transaction is
    rolled back and the function returns ``False``. Callers can then
    translate the conflict into a 409.

    Other ``IntegrityError`` subclasses (NOT NULL, FK violations, check
    constraints) are re-raised after rollback so they surface as real
    500/validation errors instead of being silently converted into 409s.
    """
    try:
        db.commit()
        return True
    except IntegrityError as exc:
        # Always rollback: the SQLAlchemy session is unusable after a
        # failed commit until rollback is issued.
        db.rollback()
        # Only swallow unique-key violations (Postgres 23505 / SQLite
        # "UNIQUE constraint failed"). Everything else is a genuine bug
        # that should not be masked as a conflict.
        is_unique_violation = False
        orig = getattr(exc, "orig", None)
        if orig is not None:
            pgcode = getattr(orig, "pgcode", None)
            if pgcode == "23505":
                is_unique_violation = True
            # SQLite exposes unique violations via IntegrityError message
            elif "UNIQUE constraint failed" in str(orig):
                is_unique_violation = True
        if not is_unique_violation:
            raise
        _logger.debug("Swallowed concurrent create unique-key conflict: %s", exc)
        return False



def _actor_sede_or_none_cms(db: Session, actor_user_id: str | uuid.UUID) -> str | None:
    """Resolve la sede de un actor autenticado.

    ``None`` sólo representa un superadministrador canónico sin sede. La
    ausencia o malformación del actor es un error y nunca omite silenciosamente
    el control multi-tenant.
    """
    from fastapi import HTTPException as _HTTPException

    from backend.crud.crm import get_user_sede_id

    try:
        actor_uuid = uuid.UUID(str(actor_user_id))
    except (TypeError, ValueError, AttributeError):
        raise _HTTPException(status_code=401, detail="Authenticated actor required")
    if resolve_persona_uuid_for_user(db, actor_uuid) is None:
        raise _HTTPException(status_code=401, detail="Authenticated actor required")
    return get_user_sede_id(db, str(actor_uuid))



def _resolve_persona_sede(db: Session, persona_id) -> str | None:
    """Resuelve la ``sede_id`` de una persona target (UUID) o None.

    Helper usado por defense-in-depth de CMS User-Generated Content.
    Retorna:
      - ``None`` si la persona no existe.
      - ``None`` si la persona no tiene sede asignada (orphan).
      - La sede como ``str`` en caso contrario.
    """
    if persona_id is None:
        return None
    try:
        persona_uuid = uuid.UUID(str(persona_id))
    except (TypeError, ValueError, AttributeError):
        return None
    row = db.query(models.Persona.sede_id).filter(models.Persona.id == persona_uuid).first()
    if not row or row[0] is None:
        return None
    return str(row[0])



def _crud_scope_re_check_cms_content_create(
    db: Session,
    actor_user_id,
    *,
    actor_sede: str | None,
    author_persona_id,
) -> str | None:
    """Defense in depth para CMS create (Testimonial / Announcement / MediaItem).

    Política estricta sobre el estado de anclas tras la mutación:

      - Actor sin sede o persona autora no resoluble: REJECT 409.

      - **Actor con sede y ``author_persona_id`` resuelve a sede
        distinta de ``actor_sede``**: REJECT 404. Cross-sede leak:
        breach de Axioma 3. Logged at WARNING (no INFO). Mensaje neutro
        para no leakear info del anchor al caller.

      - **Match exacto**: retorna ``target_sede`` (que coincide con
        ``actor_sede``) para que el CRUD lo persista en
        ``row.sede_id = target_sede`` sin JOIN adicional.

    Retorna la sede validada. Ningún UGC puede persistirse sin owner+sede.
    """
    from fastapi import HTTPException as _HTTPException

    if not actor_sede or author_persona_id is None:
        raise _HTTPException(
            status_code=409,
            detail="CMS content requires an attributed persona and sede",
        )

    target_sede = _resolve_persona_sede(db, author_persona_id)
    if target_sede is None or target_sede != str(actor_sede):
        _logger.warning(
            "Axioma 3 scope violation: CMS content create cross-sede "
            "(actor_sede=%s actor_user_id=%s author_persona_id=%s "
            "target_sede=%s)",
            actor_sede,
            actor_user_id,
            author_persona_id,
            target_sede,
        )
        raise _HTTPException(status_code=404, detail="CMS content creation blocked")

    return target_sede



def _crud_scope_re_check_cms_content_update(
    db: Session,
    actor_user_id,
    *,
    actor_sede: str | None,
    current_row_sede: str | None,
    incoming_author_persona_id,
) -> None:
    """Defense in depth para CMS update (Testimonial / Announcement / MediaItem).

    Política OR-based sobre el estado FINAL del row:
      - Actor sin sede: bypass sin check.
      - Row tiene sede_id coherente con actor_sede y el body no introduce
        FK cross-sede: OK.
      - Cualquier vector cross-sede (row.move o incoming_FK.cross): REJECT
        404 con mensaje neutro (existence-leak safe).

    Casos:
      - Row.current_sede es None y actor con sede: REJECT 404 (orphan).
      - Incoming.author_persona_id resuelve a OTRA sede que ``actor_sede``:
        REJECT 404 (TOCTOU para fijar FK cross-sede vía API tras fetch).
    """
    from fastapi import HTTPException as _HTTPException

    if not actor_sede:
        return  # superadmin / anterior path

    if current_row_sede is None or str(current_row_sede) != str(actor_sede):
        _logger.warning(
            "Axioma 3 scope violation: CMS content update row cross-sede "
            "(actor_sede=%s actor_user_id=%s current_row_sede=%s)",
            actor_sede,
            actor_user_id,
            current_row_sede,
        )
        raise _HTTPException(status_code=404, detail="CMS content update blocked")

    if incoming_author_persona_id is not None:
        incoming_sede = _resolve_persona_sede(db, incoming_author_persona_id)
        if incoming_sede is None or incoming_sede != str(actor_sede):
            _logger.warning(
                "Axioma 3 scope violation: CMS content update FK cross-sede "
                "(actor_sede=%s actor_user_id=%s incoming=%s target_sede=%s)",
                actor_sede,
                actor_user_id,
                incoming_author_persona_id,
                incoming_sede,
            )
            raise _HTTPException(status_code=404, detail="CMS content update blocked")



def _resolve_site_sede(db: Session, site_id) -> str | None:
    """Resuelve la ``sede_id`` de un ``CmsSite`` (UUID) o None.

    Helper usado por defense-in-depth de CMS site-scoped content
    (CmsPost, CmsCategory, CmsTag). Retorna None si el site no existe
    o no tiene sede asignada (orphan).
    """
    if site_id is None:
        return None
    try:
        site_uuid = uuid.UUID(str(site_id))
    except (TypeError, ValueError, AttributeError):
        return None
    row = db.query(models.CmsSite.sede_id).filter(models.CmsSite.id == site_uuid).first()
    if not row or row[0] is None:
        return None
    return str(row[0])



def _crud_scope_re_check_cms_site_content(
    db: Session,
    actor_user_id,
    *,
    actor_sede: str | None,
    site_id,
) -> None:
    """Defense in depth para CMS site-scoped content (CmsPost / CmsCategory / CmsTag).

    Estas entidades no tienen ``sede_id`` propio — se scopean via
    ``site_id`` → ``CmsSite.sede_id``. El API layer ya valida el site
    via ``_get_scoped_site_or_404``, pero este helper re-valida para
    proteger callers no-API (workers, scripts, tests directos).

    Política:
      - Actor sin sede (superadmin): bypass.
      - Site no existe o no tiene sede (orphan): bypass (sin tenancy que
        aplicar; consistente con la tabla de Axioma 3 en ``errorescms.md``
        que marca CmsPost/CmsCategory/CmsTag como "OK by proxy" via
        ``site_id`` — si el site no sede, no hay filtro que aplicar).
      - Site.sede_id != actor_sede: REJECT 404 (cross-sede).
      - Match: OK.
    """
    from fastapi import HTTPException as _HTTPException

    if not actor_sede:
        return  # superadmin / anterior path

    site_sede = _resolve_site_sede(db, site_id)
    if site_sede is None:
        # Orphan site: sin tenancy — bypass, igual que un site global.
        # No hay sede_id que comparar, así que no puede haber cross-sede.
        return
    if site_sede != str(actor_sede):
        _logger.warning(
            "Axioma 3 scope violation: CMS site-scoped content cross-sede "
            "(actor_sede=%s actor_user_id=%s site_id=%s site_sede=%s)",
            actor_sede,
            actor_user_id,
            site_id,
            site_sede,
        )
        raise _HTTPException(status_code=404, detail="CMS site content blocked")



def _crud_scope_re_check_pastoral_profile(
    db: Session,
    actor_user_id,
    *,
    actor_sede: str | None,
    target_persona_id,
    target_persona_sede: str | None,
) -> None:
    """Defense in depth para ``update_pastoral_profile``.

    Cierra el IDOR crítico donde un editor CMS puede mutar cualquier
    ``Persona`` del platform via ``cms_pastoral_profile_update``. El helper
    API-layer ``_get_scoped_persona`` ya devuelve 404 cross-sede, pero el
    CRUD re-valida para proteger contra callers no-API (workers, scripts,
    tests directos).
    """
    from fastapi import HTTPException as _HTTPException

    if not actor_sede:
        return  # superadmin / anterior path

    if target_persona_sede is None or str(target_persona_sede) != str(actor_sede):
        _logger.warning(
            "Axioma 3 scope violation: update_pastoral_profile cross-sede "
            "(actor_sede=%s actor_user_id=%s target_persona_id=%s "
            "target_sede=%s)",
            actor_sede,
            actor_user_id,
            target_persona_id,
            target_persona_sede,
        )
        raise _HTTPException(status_code=404, detail="Pastoral profile update blocked")



def _now_utc() -> dt.datetime:
    """Now in UTC. Toler a naive vs aware: SQLAlchemy almacena tz-aware
    pero para comparaciones consistentes usamos UTC explícito.
    """
    return dt.datetime.now(dt.timezone.utc)




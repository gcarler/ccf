"""Axioma 3 — Multi-Tenant scope helpers for CMS routes (User-Generated Content).

Facilitadores de scope para entidades CMS que recientemente recibieron
``sede_id`` propio via la migración Alembic
``20260701_0001_cms_content_sede_id``:

  - ``Testimonial``     → ``sede_id`` (backfilled desde ``author_persona.sede_id``)
  - ``Announcement``    → ``sede_id`` + ``created_by_persona_id``
  - ``CmsMediaItem``    → ``sede_id`` (backfilled desde ``created_by_persona.sede_id``)

Patrón consistente con ``backend/api/crm/_shared.py``:

  - El helper SIEMPRE devuelve 404 (no 403) ante cross-sede o target
    inexistente. Esto evita existencia-leaks: el caller no puede distinguir
    "no existe" de "existe pero es de otra sede".
  - Si el staff actual no tiene sede (``_actor_sede_or_none`` retorna
    ``None`` → superadmin / anterior path), se omite el scope filter tal
    cual en el resto del axioma 3 — el actor ve TODO lo no-borrado,
    consistente con la API endurecida de CRM/messaging.

Caso especial:

  - **CmsSite / CmsPage / CmsTheme / CmsMenu / CmsSection** son entidades
    globales del site ("faro"). NO reciben scope check multi-tenant:
    permanecen accesibles para editoriales cross-sede. Esto preserva el
    diseño del frontend único y la consistencia de la home pública.
    Los User-Generated Content (Testimonial/Announcement/Media) sí son
    tenant-isolated para evitar que un editor de sede_a inyecte contenido
    en la home global apuntando a pastor/visitante de sede_b.

Cierre del IDOR crítico en ``cms_pastoral_profile_update`` (cms_v2.py):

  - Reemplazamos ``crud.get_persona_by_id(db, persona_id)`` por
    ``_get_scoped_persona(db, current_user, persona_id)`` (importada
    desde ``backend.api.crm._shared``). Mismo helper ya usado para el
    resto de CRM.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.api.crm._shared import _get_scoped_persona
from backend.crud.crm import get_user_sede_id


def _actor_sede_or_none(db: Session, current_user: models.User) -> Optional[str]:
    """Retorna la sede del actor o ``None`` para superadministración."""
    user_id = getattr(current_user, "id", None)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authenticated actor required")
    return get_user_sede_id(db, user_id)


def _scope_cms_testimonials_by_user_sede(
    db: Session, current_user: models.User, query
):
    """Filtra un query de ``models.Testimonial`` por ``sede_id == user_sede``.

    Si el actor canónico no tiene sede (superadmin), retorna el query sin
    modificar y conserva el alcance administrativo global.

    Testimonial exige ``sede_id`` propio desde la migración 2026-07-01. El
    scope se aplica de forma directa sin necesidad de JOIN.
    """
    user_sede = _actor_sede_or_none(db, current_user)
    if user_sede:
        query = query.filter(models.Testimonial.sede_id == user_sede)
    return query


def _scope_cms_announcements_by_user_sede(
    db: Session, current_user: models.User, query
):
    """Filtra un query de ``models.Announcement`` por ``sede_id == user_sede``.

    Announcement exige ``sede_id`` + ``created_by_persona_id`` no nulos.
    """
    user_sede = _actor_sede_or_none(db, current_user)
    if user_sede:
        query = query.filter(models.Announcement.sede_id == user_sede)
    return query


def _scope_cms_media_by_user_sede(
    db: Session, current_user: models.User, query
):
    """Filtra un query de ``models.CmsMediaItem`` por ``sede_id == user_sede``.

    CmsMediaItem exige ``sede_id`` propio desde la migración 2026-07-01 y
    permite filtrado directo, eficiente y consistente.
    """
    user_sede = _actor_sede_or_none(db, current_user)
    if user_sede:
        query = query.filter(models.CmsMediaItem.sede_id == user_sede)
    return query


def _scope_cms_pastoral_team_by_user_sede(
    db: Session, current_user: models.User, query
):
    """Filtra un query de pastoral-leaders por ``Persona.sede_id ==
    user_sede``. Si el actor canónico no tiene sede (superadmin), retorna el
    query sin modificar y conserva el alcance administrativo global.

    Política STRICT (no permisiva con NULL): las Personas sin sede son
    tratadas como orphan y NO se exponen a editoriales cross-sede. Esto
    cierra el vector donde un líder con ``sede_id=NULL`` sería visible para
    todas las sedes. El acceso global queda reservado al superadmin canónico.
    """
    user_sede = _actor_sede_or_none(db, current_user)
    if user_sede:
        query = query.filter(models.Persona.sede_id == user_sede)
    return query


def _get_scoped_cms_testimonial(
    db: Session, current_user: models.User, testimonial_id
) -> models.Testimonial:
    """Devuelve el Testimonial o raise ``HTTPException(404)``.

    Existence-leak safe: devuelve 404 tanto si el testimonial no existe
    como si pertenece a otra sede. Mismo patrón que
    ``_get_scoped_persona``.

    Si el actor es superadmin sin sede, retorna cualquier Testimonial no
    archivado (consistente con el resto de Axioma 3).
    """
    import uuid as _uuid
    try:
        tid = _uuid.UUID(str(testimonial_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Testimonial no encontrado")

    query = db.query(models.Testimonial).filter(models.Testimonial.id == tid)
    query = _scope_cms_testimonials_by_user_sede(db, current_user, query)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Testimonial no encontrado")
    return row


def _get_scoped_cms_announcement(
    db: Session, current_user: models.User, announcement_id
) -> models.Announcement:
    """Devuelve el Announcement o raise ``HTTPException(404)``.

    Existence-leak safe (mismo patrón que Testimonial).
    """
    import uuid as _uuid
    try:
        aid = _uuid.UUID(str(announcement_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Announcement no encontrado")

    query = db.query(models.Announcement).filter(models.Announcement.id == aid)
    query = _scope_cms_announcements_by_user_sede(db, current_user, query)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Announcement no encontrado")
    return row


def _get_scoped_cms_media(
    db: Session, current_user: models.User, media_id
) -> models.CmsMediaItem:
    """Devuelve el CmsMediaItem o raise ``HTTPException(404)``.

    Existence-leak safe (mismo patrón que Testimonial / Announcement).
    """
    import uuid as _uuid
    try:
        mid = _uuid.UUID(str(media_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Media item no encontrado")

    query = db.query(models.CmsMediaItem).filter(models.CmsMediaItem.id == mid)
    query = _scope_cms_media_by_user_sede(db, current_user, query)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Media item no encontrado")
    return row


# Re-export for convenience (so cms_v2.py can import ``_get_scoped_persona``
# from one place and keep the dependency direction clean: cms → crm).
__all__ = (
    "_actor_sede_or_none",
    "_get_scoped_cms_announcement",
    "_get_scoped_cms_media",
    "_get_scoped_cms_testimonial",
    "_get_scoped_persona",
    "_scope_cms_announcements_by_user_sede",
    "_scope_cms_media_by_user_sede",
    "_scope_cms_pastoral_team_by_user_sede",
    "_scope_cms_testimonials_by_user_sede",
)

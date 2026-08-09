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
import math
import os
import uuid

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
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



from backend.crud.cms._shared import (_now_utc)
def cleanup_old_publish_logs(
    db: Session,
    *,
    retention_days: int = 90,
    dry_run: bool = False,
    now: dt.datetime | None = None,
) -> int:
    """F-08 (errorescms.md): purga ``CmsPublishLog`` con ``created_at`` anterior
    a ``now - retention_days``.

    ``retention_days`` default 90 conserva ~3 meses de historico (suficiente
    para auditoria reciente y debugging). El cron job del scheduler lo
    invoca con el default; un operador puede llamarlo manualmente con
    otra ventana si necesita mas/menos retencion.

    Args:
        db: Session de BD.
        retention_days: Días a conservar desde ``now``. Default 90.
        dry_run: Si True, solo retorna el count sin borrar.
        now: Override opcional del timestamp (para tests deterministas).

    Returns:
        Número de logs purgados (o que se purgarían en dry_run).
    """
    cutoff = (now or _now_utc()) - dt.timedelta(days=max(1, retention_days))
    stale = db.query(models.CmsPublishLog).filter(models.CmsPublishLog.created_at < cutoff)
    if dry_run:
        return stale.count()
    deleted = stale.delete(synchronize_session=False)
    db.commit()
    return deleted




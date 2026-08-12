from __future__ import annotations

import datetime
import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar
from uuid import UUID

from sqlalchemy import inspect, or_
from sqlalchemy.orm import Session, load_only

from backend import models
from backend.schemas.evangelism import (
    ABSENT_STATES,
    ATTENDED_STATES,
    EXCUSED_STATES,
    FIRST_TIME_STATES,
    normalize_attendance_status,
)

logger = logging.getLogger(__name__)

ABSENTEES_PREVIEW_LIMIT = 50
ABSENCE_REASON_LABELS = {
    "weather": "Clima",
    "work": "Trabajo",
    "health": "Salud",
    "family": "Familia",
    "other": "Otro",
}

# ── Estados canónicos de asistencia ──
# Re-exportados desde schemas/evangelism.py (fuente de verdad única,
# junto al enum StatusAsistenciaCanonico). Esto rompe el ciclo
# schemas → api → schemas que existía cuando la normalización vivía
# en la capa API. Los callers existentes que importan desde aquí
# continúan funcionando sin cambios.

__all__ = [
    "ATTENDED_STATES",
    "ABSENT_STATES",
    "EXCUSED_STATES",
    "FIRST_TIME_STATES",
    "normalize_attendance_status",
    "is_attended_status",
    "is_absent_status",
    "is_excused_status",
    "ttl_cache",
    "invalidate_ttl_cache",
    "analytics_cache_scope",
]


# ── In-memory TTL cache shared by evangelismo endpoints ──
# Sigue la misma heurística del helper que vivía en evangelism_rankings.py,
# pero ahora en un solo lugar para que analytics, reports y rankings lo
# reutilicen. Cada worker de proceso mantiene su propia cache; si los
# analytics mutan vía asistencia/estrategia/grupos, el TTL corto (60 s
# por defecto) garantiza convergencia sin invalidación manual explícita.

_TTL_CACHE: dict = {}
TTL_DEFAULT_SECONDS = 60
F = TypeVar("F", bound=Callable[..., Any])


def analytics_cache_scope(current_user: Any) -> str:
    """Return a tenant-specific cache suffix without querying during keying.

    Aislar por ``sede_id`` evita que un usuario de la sede X reciba el
    resultado cacheado de un recurso que solo es visible por usuarios de la
    sede Y (Cross-Tenant defense-in-depth). Cuando no hay ``sede_id`` en el
    objeto User, cae a ``user:<id>`` para igualmente particionar y no romper
    el RBAC por_sede.
    """
    sede_id = getattr(current_user, "sede_id", None) if current_user is not None else None
    if sede_id:
        return str(sede_id)
    user_id = getattr(current_user, "id", None) if current_user is not None else None
    return f"user:{user_id or 'anonymous'}"


def ttl_cache(key_fn: Callable[..., str], ttl: int = TTL_DEFAULT_SECONDS) -> Callable[[F], F]:
    """Decorador de cache in-memory con TTL.

    ``key_fn`` recibe los mismos ``*args, **kwargs`` del endpoint decorado
    y debe retornar un string determinista (ej: ``f"alerts:{strategy_id}"``).
    Los valores no serializables (Session, User) se ignoran dentro de la
    función que construye la key — la responsabilidad recae en ``key_fn``.

    El tamaño máximo es 200 entradas; cuando se excede, se podan las 100
    entradas más stale para evitar crecimiento ilimitado en workers de
    larga duración.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = key_fn(*args, **kwargs)
            now = time.monotonic()
            cached = _TTL_CACHE.get(cache_key)
            if cached is not None:
                result, ts = cached
                if now - ts < ttl:
                    return result
            result = fn(*args, **kwargs)
            _TTL_CACHE[cache_key] = (result, now)
            if len(_TTL_CACHE) > 200:
                stale = [k for k, (_, ts) in _TTL_CACHE.items() if now - ts >= ttl]
                for k in stale[:100]:
                    _TTL_CACHE.pop(k, None)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def invalidate_ttl_cache(prefix: str | None = None) -> None:
    """Invalida entradas de la cache TTL.

    Si ``prefix`` es ``None``, vacía toda la cache. De lo contrario, elimina
    solo las claves que empiecen con ese prefijo (ej: ``invalidate_ttl_cache(f"full:{sid}")``).
    """
    if prefix is None:
        _TTL_CACHE.clear()
        return
    keys = [k for k in _TTL_CACHE if k.startswith(prefix)]
    for k in keys:
        _TTL_CACHE.pop(k, None)


# Backwards-compatible aliases for internal callers/tests from the previous
# rankings module. The canonical implementation lives in this shared module.
_ttl_cache = ttl_cache
_invalidate_cache = invalidate_ttl_cache


def sessions_grupo_has_estado_habilitacion(db: Session) -> bool:
    """Return whether the live schema exposes ``sesiones_grupo.estado_habilitacion``."""
    return "estado_habilitacion" in _sessions_grupo_live_column_names(db)


def _sessions_grupo_live_column_names(db: Session) -> set[str]:
    bind = db.get_bind()
    if bind is None:
        return set()
    try:
        columns = inspect(bind).get_columns("sesiones_grupo")
    except Exception as exc:
        logger.debug("Failed to inspect sesiones_grupo columns: %s", exc)
        return set()
    return {str(column.get("name")) for column in columns if column.get("name")}


def session_estado_habilitacion(session, default: str = "HABILITADO") -> str:
    """Read ``estado_habilitacion`` without triggering a deferred load."""
    value = session_read_value(session, "estado_habilitacion", default)
    return value or default


def session_read_value(session, field: str, default=None):
    """Read a mapped attribute from the loaded instance state only.

    This avoids deferred-load queries against columns that may not exist in
    the live schema while still returning a sensible default when the field
    is absent or not loaded.
    """
    return getattr(session, "__dict__", {}).get(field, default)


def session_read_only_options(db: Session):
    """Build a load_only option that tolerates older schemas safely."""
    from backend.models import SesionGrupo

    live_columns = _sessions_grupo_live_column_names(db)
    desired_columns = [
        "id",
        "grupo_id",
        "fecha_sesion",
        "estado",
        "motivo_cancelacion",
        "tema_estudio",
        "notas_lider",
        "offering_amount",
        "season_id",
        "created_at",
        "deleted_at",
        "reported_at",
        "novelty_type",
        "novelty_detail",
        "reported_by_persona_id",
        "report_deadline",
        "estado_habilitacion",
        "habilitado_por",
        "habilitado_en",
    ]
    columns = [
        getattr(SesionGrupo, column_name)
        for column_name in desired_columns
        if column_name in live_columns and hasattr(SesionGrupo, column_name)
    ]
    if not columns:
        columns = [SesionGrupo.id, SesionGrupo.grupo_id, SesionGrupo.fecha_sesion]
    return load_only(*columns)


def is_attended_status(value) -> bool:
    return normalize_attendance_status(value) in {"present", "first_time"}


def is_absent_status(value) -> bool:
    return normalize_attendance_status(value) == "absent"


def is_excused_status(value) -> bool:
    return normalize_attendance_status(value) == "excused"


def _is_crm_admin_or_pastor(user) -> bool:
    """Check if user has admin/pastor role (shared helper)."""
    from backend.core.permissions import normalize_role

    role = normalize_role(str(getattr(user, "role", "")))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)
    return role in {"admin", "administrador", "pastor", "coordinador"}


def _get_persona_for_user(db: Session, user_id) -> Optional[models.Persona]:
    """Resolve user_id to Persona record (shared helper)."""
    import uuid as _uuid

    try:
        uid = _uuid.UUID(str(user_id))
    except (TypeError, ValueError, AttributeError):
        return None
    return db.query(models.Persona).filter(models.Persona.id == uid).first()


def get_visible_strategy(db: Session, strategy_id: UUID, sede_id: str):
    """Resolve an active Evangelism strategy inside exactly one tenant.

    This is the canonical scope primitive for strategy-owned resources. Callers
    choose their compatible 404/403 response, while the query itself always
    applies soft-delete and sede isolation together.
    """
    return (
        db.query(models.EstrategiaEvangelismo)
        .filter(
            models.EstrategiaEvangelismo.id == strategy_id,
            models.EstrategiaEvangelismo.sede_id == sede_id,
            models.EstrategiaEvangelismo.deleted_at.is_(None),
        )
        .first()
    )


def get_visible_group(db: Session, grupo_id: UUID, sede_id: str):
    """Resolve a non-deleted group inside the caller's tenant."""
    return (
        db.query(models.GrupoEvangelismo)
        .filter(
            models.GrupoEvangelismo.id == grupo_id,
            models.GrupoEvangelismo.sede_id == sede_id,
            models.GrupoEvangelismo.deleted_at.is_(None),
        )
        .first()
    )


def get_visible_session(db: Session, session_id: UUID, sede_id: str):
    """Resolve a non-deleted session only through an active group in tenant."""
    return (
        db.query(models.SesionGrupo)
        .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == models.SesionGrupo.grupo_id)
        .filter(
            models.SesionGrupo.id == session_id,
            models.SesionGrupo.deleted_at.is_(None),
            models.GrupoEvangelismo.deleted_at.is_(None),
            models.GrupoEvangelismo.sede_id == sede_id,
        )
        .first()
    )


def _can_manage_grupo(db: Session, user, house) -> bool:
    """Check if user can manage a group (shared helper)."""
    if _is_crm_admin_or_pastor(user):
        return True
    persona = _get_persona_for_user(db, user.id)
    if not persona:
        return False
    return persona.id in {house.leader_persona_id, house.assistant_persona_id}


def _check_absence_trigger(db: Session, session_id: UUID, sede_id):
    """If a persona has 3 consecutive absences, create N2 task in Consolidation."""
    from backend.models import (
        Asistencia,
        GrupoEvangelismo,
        ParticipanteGrupo,
        SesionGrupo,
    )
    from backend.models_crm import Persona
    from backend.models_evangelism import EstadoAsistenciaEnum

    session = (
        db.query(SesionGrupo)
        .options(
            load_only(
                SesionGrupo.id,
                SesionGrupo.grupo_id,
                SesionGrupo.fecha_sesion,
                SesionGrupo.deleted_at,
            )
        )
        .join(GrupoEvangelismo, GrupoEvangelismo.id == SesionGrupo.grupo_id)
        .filter(
            SesionGrupo.id == session_id,
            GrupoEvangelismo.sede_id == sede_id,
            GrupoEvangelismo.deleted_at.is_(None),
            SesionGrupo.deleted_at.is_(None),
        )
        .first()
    )
    if not session:
        return

    house = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.id == session.grupo_id).first()
    if not house:
        return

    # Get last 3 sessions for this house
    recent_sessions = (
        db.query(SesionGrupo)
        .options(
            load_only(
                SesionGrupo.id,
                SesionGrupo.grupo_id,
                SesionGrupo.fecha_sesion,
                SesionGrupo.deleted_at,
            )
        )
        .filter(
            SesionGrupo.grupo_id == house.id,
            SesionGrupo.deleted_at.is_(None),
        )
        .order_by(SesionGrupo.fecha_sesion.desc())
        .limit(3)
        .all()
    )

    if len(recent_sessions) < 3:
        return  # Not enough data

    expected_personas = (
        db.query(ParticipanteGrupo.persona_id)
        .filter(
            ParticipanteGrupo.grupo_id == house.id,
            ParticipanteGrupo.deleted_at.is_(None),
            ParticipanteGrupo.activo.is_(True),
        )
        .all()
    )
    # Batch: count absences per persona in one query (N+1 fix — was
    # personas × sesiones individual queries).
    session_ids = [s.id for s in recent_sessions]
    persona_ids = [pid for (pid,) in expected_personas]
    absent_counts: dict = {}
    if persona_ids and session_ids:
        from sqlalchemy import func as _func

        rows = (
            db.query(Asistencia.persona_id, _func.count(Asistencia.id))
            .filter(
                Asistencia.sesion_id.in_(session_ids),
                Asistencia.persona_id.in_(persona_ids),
                Asistencia.deleted_at.is_(None),
                Asistencia.estado == EstadoAsistenciaEnum.FALTO.value,
            )
            .group_by(Asistencia.persona_id)
            .all()
        )
        absent_counts = {pid: cnt for pid, cnt in rows}

    for (persona_id,) in expected_personas:
        absent_count = absent_counts.get(persona_id, 0)

        if absent_count >= 3:
            # Create N2 task in Consolidation
            p = db.query(Persona).filter(Persona.id == persona_id).first()
            if not p:
                continue
            from backend.models_crm import SupportTicket

            ticket = SupportTicket(
                user_id=persona_id,
                sede_id=p.sede_id,
                subject=f"Inasistencia recurrente: {p.nombre_completo}",
                description=(
                    f"{p.nombre_completo} ha faltado 3 sesiones consecutivas en {house.name}. "
                    "Requiere contacto pastoral. Severidad sugerida: N2."
                ),
                status="open",
            )
            db.add(ticket)
            db.commit()


def _check_first_time_lead_trigger(db: Session, session_id: UUID):
    """If a first_time attendee is recorded, mark as LEAD_NUEVO in CRM."""
    from backend.models_crm import Persona
    from backend.models_evangelism import Asistencia

    first_timers = (
        db.query(Asistencia)
        .filter(
            Asistencia.sesion_id == session_id,
            or_(
                Asistencia.es_primera_vez.is_(True),
                Asistencia.estado.in_(FIRST_TIME_STATES),
            ),
        )
        .all()
    )

    if not first_timers:
        return

    # Batch-fetch all personas in one query instead of N queries in a loop
    persona_ids = [att.persona_id for att in first_timers if att.persona_id]
    personas_map = {p.id: p for p in db.query(Persona).filter(Persona.id.in_(persona_ids)).all()}

    for att in first_timers:
        p = personas_map.get(att.persona_id)
        if p and str(getattr(p, "church_role", "")).lower() not in ("lead", "lead_nuevo"):
            try:
                p.church_role = "lead_nuevo"
            except Exception as exc:
                logger.warning(
                    "Failed to update church_role to lead_nuevo for persona %s: %s",
                    att.persona_id,
                    exc,
                )
    db.commit()


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def parse_session_date(value: object) -> datetime.date:
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("session_date is required")
        try:
            return datetime.date.fromisoformat(raw[:10])
        except ValueError as exc:
            raise ValueError("Invalid session_date") from exc
    raise ValueError("Invalid session_date")


def normalize_role_scope_payload(payload: dict) -> dict:
    normalized = dict(payload)
    raw_role_ids = normalized.get("target_role_ids")
    raw_persona_ids = normalized.get("target_persona_ids")
    normalized_role_ids: list[str] = []
    normalized_persona_ids: list[str] = []
    if isinstance(raw_role_ids, list):
        for raw_role_id in raw_role_ids:
            try:
                normalized_role_ids.append(str(UUID(str(raw_role_id))))
            except (TypeError, ValueError):
                continue
    normalized_role_ids = list(dict.fromkeys(normalized_role_ids))
    if isinstance(raw_persona_ids, list):
        for raw_persona_id in raw_persona_ids:
            if isinstance(raw_persona_id, str) and raw_persona_id.strip():
                normalized_persona_ids.append(raw_persona_id.strip())
    normalized_persona_ids = list(dict.fromkeys(normalized_persona_ids))

    if normalized.get("target_audience") == "ROLE":
        if normalized_role_ids:
            normalized["target_role_ids"] = normalized_role_ids
            normalized["target_role_id"] = normalized_role_ids[0]
        elif normalized.get("target_role_id") is not None:
            try:
                normalized_role_id = str(UUID(str(normalized["target_role_id"])))
            except (TypeError, ValueError):
                normalized_role_id = None
            normalized["target_role_id"] = UUID(normalized_role_id) if normalized_role_id else None
            normalized["target_role_ids"] = [normalized_role_id] if normalized_role_id is not None else None
        else:
            normalized["target_role_ids"] = None
            normalized["target_role_id"] = None
        normalized["target_persona_ids"] = None
    elif normalized.get("target_audience") == "MANUAL":
        normalized["target_role_ids"] = None
        normalized["target_role_id"] = None
        normalized["target_persona_ids"] = normalized_persona_ids or None
    else:
        normalized["target_role_ids"] = None
        normalized["target_role_id"] = None
        normalized["target_persona_ids"] = None

    return normalized


def resolve_target_role_ids(event: models.CrmEvent) -> list[UUID]:
    role_ids = []
    if isinstance(event.target_role_ids, list):
        for raw_role_id in event.target_role_ids:
            try:
                role_ids.append(UUID(str(raw_role_id)))
            except (TypeError, ValueError):
                continue
    if not role_ids and event.target_role_id is not None:
        role_ids.append(UUID(str(event.target_role_id)))
    return list(dict.fromkeys(role_ids))


def get_expected_personas_for_event(db: Session, event: models.CrmEvent, sede_id=None) -> list[models.Persona]:
    event_sede_id = sede_id or getattr(event, "sede_id", None)
    if event.target_audience == "ROLE":
        role_ids = resolve_target_role_ids(event)
        if not role_ids:
            return []
        role_names = [
            row[0] for row in db.query(models.RoleDefinition.name).filter(models.RoleDefinition.id.in_(role_ids)).all()
        ]
        if not role_names:
            return []
        q = db.query(models.Persona).filter(models.Persona.church_role.in_(role_names))
        if event_sede_id:
            q = q.filter(models.Persona.sede_id == event_sede_id)
        return q.order_by(models.Persona.nombre_completo.asc()).all()
    if event.target_audience == "MANUAL":
        import uuid

        persona_ids = []
        if isinstance(event.target_persona_ids, list):
            for raw_persona_id in event.target_persona_ids:
                if isinstance(raw_persona_id, uuid.UUID):
                    persona_ids.append(raw_persona_id)
                elif isinstance(raw_persona_id, str) and raw_persona_id.strip():
                    try:
                        persona_ids.append(uuid.UUID(raw_persona_id.strip()))
                    except ValueError:
                        continue
        persona_ids = list(dict.fromkeys(persona_ids))
        if not persona_ids:
            return []
        q = db.query(models.Persona).filter(models.Persona.id.in_(persona_ids))
        if event_sede_id:
            q = q.filter(models.Persona.sede_id == event_sede_id)
        return q.order_by(models.Persona.nombre_completo.asc()).all()
    # Fallback: todas las personas de la sede del evento (Axioma 3)
    q = db.query(models.Persona)
    if event_sede_id:
        q = q.filter(models.Persona.sede_id == event_sede_id)
    return q.order_by(models.Persona.nombre_completo.asc()).all()


def expected_group_rows(db: Session, grupo_id: UUID):
    rows = (
        db.query(models.ParticipanteGrupo, models.Persona)
        .join(models.Persona, models.Persona.id == models.ParticipanteGrupo.persona_id)
        .filter(models.ParticipanteGrupo.grupo_id == grupo_id)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )
    grupo = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == grupo_id).first()
    seen_ids = {persona.id for _, persona in rows}
    extra_personas = []
    if grupo:
        for pid in [grupo.lider_persona_id, grupo.asistente_persona_id, grupo.anfitrion_persona_id]:
            if pid and pid not in seen_ids:
                p = db.query(models.Persona).filter(models.Persona.id == pid).first()
                if p:
                    extra_personas.append((None, p))
                    seen_ids.add(p.id)
    return rows + extra_personas


def persona_payload(
    persona: models.Persona,
    attended: bool,
    scanned_at=None,
    absence_reason=None,
    absence_reason_detail=None,
    estado=None,
    es_primera_vez=False,
):
    return {
        "persona_id": persona.id,
        "name": persona.nombre_completo,
        "role": persona.church_role_effective or "Miembro",
        "attended": attended,
        "absence_reason": absence_reason,
        "absence_reason_detail": absence_reason_detail,
        "scanned_at": scanned_at.isoformat() if scanned_at else None,
        "estado": estado,
        "es_primera_vez": es_primera_vez,
    }

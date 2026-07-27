"""Pastoral health scoring and updating logic."""

import contextlib
import contextvars
import threading
import time
import warnings
from datetime import date
from uuid import UUID

from sqlalchemy import event, update
from sqlalchemy.orm import Session, object_session
from sqlalchemy.orm.attributes import get_history

from backend import models
from backend.crud.crm_.shared import persona_query, prepare_persona_for_output

# Caché simple en memoria con TTL de 5 minutos para evitar recalcular el
# health score en cada request de lectura (P-03). Se invalida explícitamente
# mediante eventos SQLAlchemy cuando los datos subyacentes se confirman en la
# base de datos.
_HEALTH_CACHE_TTL_SECONDS = 300
_MAX_HEALTH_CACHE_ENTRIES = 1000
_health_cache: dict[UUID, tuple[float, int, str]] = {}
_health_cache_lock = threading.Lock()

# Bandera de contexto para evitar que los eventos de invalidación borren el
# caché mientras el propio módulo de salud está escribiendo resultados.
_health_update_ctx: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_health_update_ctx", default=False
)

# Guarda para evitar registrar los listeners más de una vez si el módulo se
# importa múltiples veces (por ejemplo, recargas en desarrollo o tests).
_LISTENERS_REGISTERED = False


@contextlib.contextmanager
def _suppress_health_invalidation():
    """Context manager que suprime la invalidación del caché de salud."""
    token = _health_update_ctx.set(True)
    try:
        yield
    finally:
        _health_update_ctx.reset(token)


def _get_cached_health(persona_id: UUID) -> tuple[int, str] | None:
    """Devuelve (score, status) si existe una entrada válida en caché."""
    with _health_cache_lock:
        entry = _health_cache.get(persona_id)
        if entry is None:
            return None
        expires_at, score, status = entry
        if time.time() < expires_at:
            return score, status
        del _health_cache[persona_id]
        return None


def _set_cached_health(persona_id: UUID, score: int, status: str) -> None:
    """Guarda (score, status) en caché bajo lock con límite FIFO."""
    with _health_cache_lock:
        if len(_health_cache) >= _MAX_HEALTH_CACHE_ENTRIES:
            try:
                _health_cache.pop(next(iter(_health_cache)))
            except StopIteration:
                pass
        _health_cache[persona_id] = (
            time.time() + _HEALTH_CACHE_TTL_SECONDS,
            score,
            status,
        )


def _invalidate_health_cache(persona_id: UUID | None) -> None:
    """Invalida la entrada de caché para ``persona_id``."""
    if persona_id is None:
        return
    with _health_cache_lock:
        _health_cache.pop(persona_id, None)


def _load_persona_for_health(db: Session, persona_id: UUID):
    return db.get(models.Persona, persona_id)


def _compute_pastoral_health_score(
    db: Session, persona: models.Persona
) -> tuple[int, str, bool]:
    """Calcula el score y status pastoral sin mutar la base de datos.

    Devuelve ``(score, status, update_baptized)``. ``update_baptized`` indica
    si se detectó un milestone de bautizo y la persona no está marcada como
    bautizada, por lo que el caller debe actualizar ``Persona.is_baptized``.
    """
    is_baptized = bool(getattr(persona, "is_baptized", False))
    persona_id = persona.id

    # 1. Attendance score
    opp_asistencias = (
        db.query(models.Asistencia)
        .filter(models.Asistencia.persona_id == persona_id, models.Asistencia.deleted_at.is_(None))
        .all()
    )
    opp_asistencias_count = len(opp_asistencias)
    attended_asistencias_count = sum(
        1
        for a in opp_asistencias
        if a.estado and a.estado.strip().lower() in {"asistio", "presente", "present", "primera_vez", "first_time"}
    )

    event_attendances = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.persona_id == persona_id,
            models.EventAttendance.deleted_at.is_(None),
        )
        .all()
    )
    opp_events_count = len(event_attendances)
    attended_events_count = sum(1 for e in event_attendances if e.attended is True)

    course_attendances = (
        db.query(models.CourseAttendance)
        .join(models.Enrollment, models.CourseAttendance.enrollment_id == models.Enrollment.id)
        .filter(models.Enrollment.persona_id == persona_id, models.Enrollment.deleted_at.is_(None))
        .all()
    )
    opp_courses_count = len(course_attendances)
    attended_courses_count = sum(1 for c in course_attendances if c.status and c.status.strip().lower() == "present")

    comm_logs = (
        db.query(models.CommunicationLog)
        .filter(
            models.CommunicationLog.persona_id == persona_id,
            models.CommunicationLog.deleted_at.is_(None),
        )
        .all()
    )
    comm_log_attend_count = 0
    for log in comm_logs:
        if log.content:
            content_lower = log.content.lower()
            if any(keyword in content_lower for keyword in ["attend", "asist", "session", "class", "culto", "grupo"]):
                comm_log_attend_count += 1

    opportunities = opp_asistencias_count + opp_events_count + opp_courses_count + comm_log_attend_count
    attended = attended_asistencias_count + attended_events_count + attended_courses_count + comm_log_attend_count

    if opportunities > 0:
        attendance_score = (attended / opportunities) * 50
    else:
        attendance_score = 0.0

    recent_score = 0.0
    today = date.today()
    if persona.last_meeting_attendance:
        last_meet = persona.last_meeting_attendance
        if hasattr(last_meet, "date") and callable(getattr(last_meet, "date")):
            last_meet = last_meet.date()
        if 0 <= (today - last_meet).days <= 30:
            recent_score = 40.0
    if persona.last_group_attendance:
        last_group = persona.last_group_attendance
        if hasattr(last_group, "date") and callable(getattr(last_group, "date")):
            last_group = last_group.date()
        if 0 <= (today - last_group).days <= 30:
            recent_score = 40.0

    attendance_score = max(attendance_score, recent_score)

    # 2. Milestone score
    all_milestones = (
        db.query(models.SpiritualMilestone)
        .filter(models.SpiritualMilestone.persona_id == persona_id, models.SpiritualMilestone.deleted_at.is_(None))
        .all()
    )
    active_milestones = [m for m in all_milestones if not (m.type and m.type.startswith("Health Status Change to"))]
    milestones_count = len(active_milestones)

    has_bapt_milestone = bool(
        any(m.type and any(kw in m.type.lower() for kw in ["bapt", "baut"]) for m in active_milestones)
    )
    update_baptized = has_bapt_milestone and not is_baptized and hasattr(models.Persona, "is_baptized")

    milestone_points = milestones_count
    if is_baptized or has_bapt_milestone:
        milestone_points += 1

    milestone_score = min(milestone_points * 10, 30)

    # 3. Communication score
    comm_logs_count = len(comm_logs)

    interactions_count = (
        db.query(models.InteraccionCRM)
        .join(models.CasoCRM, models.InteraccionCRM.caso_id == models.CasoCRM.id)
        .filter(models.CasoCRM.persona_id == persona_id, models.CasoCRM.deleted_at.is_(None))
        .count()
    )

    total_contacts = comm_logs_count + interactions_count
    communication_score = min(total_contacts * 5, 20)

    # 4. Donation score
    donation_count = (
        db.query(models.Donation)
        .filter(models.Donation.persona_id == persona_id, models.Donation.deleted_at.is_(None))
        .count()
    )
    if donation_count == 0:
        donation_score = 0.0
    elif donation_count == 1:
        donation_score = 50.0
    else:
        donation_score = 50.0 + min(40.0, (donation_count - 1) * 5.0)

    # Final score and status
    total_score = attendance_score + milestone_score + communication_score + donation_score
    clamped_score = max(0, min(100, int(round(total_score))))

    if clamped_score < 40:
        status = "EN_RIESGO"
    elif clamped_score < 80:
        status = "ESTABLE"
    else:
        status = "COMPROMETIDO"

    return clamped_score, status, update_baptized


def _persist_pastoral_health(
    db: Session,
    persona_id: UUID,
    score: int,
    status: str,
    previous_status: str | None,
    update_baptized: bool,
) -> None:
    """Persiste el resultado de salud pastoral en la base de datos.

    Escribe ``health_score``/``health_status`` en ``personas`` y crea un
    ``SpiritualMilestone`` cuando el status cambia.
    """
    if previous_status is not None and previous_status != status:
        milestone = models.SpiritualMilestone(
            persona_id=persona_id,
            type=f"Health Status Change to {status}",
            event_date=date.today(),
            notes=f"Health score updated to {score}",
        )
        db.add(milestone)

    update_values: dict = {}
    if hasattr(models.Persona, "health_score"):
        update_values["health_score"] = score
    if hasattr(models.Persona, "health_status"):
        update_values["health_status"] = status
    if update_baptized:
        update_values["is_baptized"] = True

    if update_values:
        db.execute(
            update(models.Persona)
            .where(models.Persona.id == persona_id)
            .values(**update_values)
        )


def recalculate_and_persist_pastoral_health(db: Session, persona_id: UUID) -> tuple[int, str]:
    """Recalcula y persiste el health score de una persona.

    La lógica de cálculo sin side effects está en ``_compute_pastoral_health_score``.
    """
    with _suppress_health_invalidation():
        persona = _load_persona_for_health(db, persona_id)
        if not persona:
            raise ValueError(f"Persona with ID {persona_id} not found")

        previous_status = getattr(persona, "health_status", None)
        score, status, update_baptized = _compute_pastoral_health_score(db, persona)
        _persist_pastoral_health(db, persona_id, score, status, previous_status, update_baptized)
    return score, status


# Backwards-compatible aliases used by tests and service modules.
def _deprecated_alias(name: str):
    def wrapper(db: Session, persona_id: UUID) -> tuple[int, str]:
        warnings.warn(
            f"{name} is deprecated; use recalculate_and_persist_pastoral_health instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return recalculate_and_persist_pastoral_health(db, persona_id)
    wrapper.__name__ = name
    wrapper.__doc__ = f"Deprecated: use ``recalculate_and_persist_pastoral_health``."
    return wrapper


calculate_pastoral_health = _deprecated_alias("calculate_pastoral_health")
calculate_pastoral_health_score = _deprecated_alias("calculate_pastoral_health_score")
calculate_health_score = _deprecated_alias("calculate_health_score")


def update_pastoral_health(db: Session, persona_id: UUID) -> models.Persona | None:
    """Devuelve la Persona con health_score/health_status actualizados.

    Si existe una entrada de caché vigente, devuelve la persona cargada
    directamente desde la base de datos sin hacer commit. Si no, recalcula,
    persiste, hace commit y refresca el caché.
    """
    with _suppress_health_invalidation():
        cached = _get_cached_health(persona_id)
        if cached is None:
            score, status = recalculate_and_persist_pastoral_health(db, persona_id)
            db.commit()
            _set_cached_health(persona_id, score, status)
        else:
            # En cache hit no se hace commit; esto evita persistir cambios
            # no relacionados que el caller pueda tener pendientes en la sesión.
            pass

    persona = persona_query(db).filter(models.Persona.id == persona_id).first()
    if persona:
        return prepare_persona_for_output(db, persona)
    return None


# ═══════════════════════════════════════════════════════════════════
# Invalidación del caché vía eventos SQLAlchemy
# ═══════════════════════════════════════════════════════════════════

def _persona_id_from_course_attendance(target) -> UUID | None:
    enrollment_id = getattr(target, "enrollment_id", None)
    if enrollment_id is None:
        return None
    session = object_session(target)
    if session is None:
        return None
    enrollment = session.get(models.Enrollment, enrollment_id)
    if enrollment is None:
        return None
    return getattr(enrollment, "persona_id", None)


def _persona_id_from_interaccion(target) -> UUID | None:
    caso_id = getattr(target, "caso_id", None)
    if caso_id is None:
        return None
    session = object_session(target)
    if session is None:
        return None
    caso = session.get(models.CasoCRM, caso_id)
    if caso is None:
        return None
    return getattr(caso, "persona_id", None)


def _after_insert_direct(mapper, connection, target):
    if _health_update_ctx.get():
        return
    _invalidate_health_cache(getattr(target, "persona_id", None))


def _after_update_direct(mapper, connection, target):
    if _health_update_ctx.get():
        return
    _invalidate_health_cache(getattr(target, "persona_id", None))


def _after_delete_direct(mapper, connection, target):
    if _health_update_ctx.get():
        return
    _invalidate_health_cache(getattr(target, "persona_id", None))


def _after_course_attendance_change(mapper, connection, target):
    if _health_update_ctx.get():
        return
    _invalidate_health_cache(_persona_id_from_course_attendance(target))


def _after_interaccion_change(mapper, connection, target):
    if _health_update_ctx.get():
        return
    _invalidate_health_cache(_persona_id_from_interaccion(target))


def _after_persona_update(mapper, connection, target):
    if _health_update_ctx.get():
        return
    for attr in ("is_baptized", "last_meeting_attendance", "last_group_attendance"):
        if hasattr(target, attr) and get_history(target, attr).has_changes():
            _invalidate_health_cache(target.id)
            return


def _register_health_event_listeners() -> None:
    """Registra los eventos SQLAlchemy para invalidar el caché de salud."""
    global _LISTENERS_REGISTERED
    if _LISTENERS_REGISTERED:
        return
    _LISTENERS_REGISTERED = True

    # Modelos con persona_id directa que afectan el score pastoral.
    _DIRECT_INVALIDATION_MODELS = (
        models.Asistencia,
        models.EventAttendance,
        models.Enrollment,
        models.CommunicationLog,
        models.CasoCRM,
        models.Donation,
        models.SpiritualMilestone,
    )

    for _model in _DIRECT_INVALIDATION_MODELS:
        event.listen(_model, "after_insert", _after_insert_direct)
        event.listen(_model, "after_update", _after_update_direct)
        event.listen(_model, "after_delete", _after_delete_direct)

    event.listen(models.CourseAttendance, "after_insert", _after_course_attendance_change)
    event.listen(models.CourseAttendance, "after_update", _after_course_attendance_change)
    event.listen(models.CourseAttendance, "after_delete", _after_course_attendance_change)

    event.listen(models.InteraccionCRM, "after_insert", _after_interaccion_change)
    event.listen(models.InteraccionCRM, "after_update", _after_interaccion_change)
    event.listen(models.InteraccionCRM, "after_delete", _after_interaccion_change)

    event.listen(models.Persona, "after_update", _after_persona_update)


_register_health_event_listeners()

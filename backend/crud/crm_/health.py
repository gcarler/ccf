"""Pastoral health scoring and updating logic."""

import contextlib
import contextvars
import json
import logging
import time
from datetime import date
from uuid import UUID

from sqlalchemy import case, event, func, or_, select, update
from sqlalchemy.orm import Session, object_session
from sqlalchemy.orm.attributes import get_history

from backend import models
from backend.core.cache import get_redis
from backend.crud.crm_.shared import persona_query, prepare_persona_for_output

# Caché simple en memoria con TTL de 5 minutos para evitar recalcular el
# health score en cada request de lectura (P-03). Se invalida explícitamente
# mediante eventos SQLAlchemy cuando los datos subyacentes se confirman en la
# base de datos.
_HEALTH_CACHE_TTL_SECONDS = 300

# Bandera de contexto para evitar que los eventos de invalidación borren el
# caché mientras el propio módulo de salud está escribiendo resultados.
_health_update_ctx: contextvars.ContextVar[bool] = contextvars.ContextVar("_health_update_ctx", default=False)

# Bandera de contexto para evitar re-entrada infinita cuando los listeners de
# invalidación bulk ejecutan sus propios SELECTs.
_bulk_invalidation_ctx: contextvars.ContextVar[bool] = contextvars.ContextVar("_bulk_invalidation_ctx", default=False)

# Guarda para evitar registrar los listeners más de una vez si el módulo se
# importa múltiples veces (por ejemplo, recargas en desarrollo o tests).
_LISTENERS_REGISTERED = False

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _suppress_health_invalidation():
    """Context manager que suprime la invalidación del caché de salud."""
    token = _health_update_ctx.set(True)
    try:
        yield
    finally:
        _health_update_ctx.reset(token)


def _normalize_persona_id(persona_id: UUID | str) -> UUID:
    """Normaliza un ID de persona a ``UUID`` para usar como clave de caché."""
    if isinstance(persona_id, str):
        # SQLite puede devolver UUIDs como strings; aceptamos tanto el formato
        # canónico con guiones como el formato hex sin guiones.
        if len(persona_id) == 32:
            persona_id = (
                f"{persona_id[:8]}-{persona_id[8:12]}-{persona_id[12:16]}-{persona_id[16:20]}-{persona_id[20:]}"
            )
        return UUID(persona_id)
    return persona_id


def _cache_key(persona_id: UUID | str) -> str:
    return f"health_cache:{_normalize_persona_id(persona_id)}"


def _get_cached_health(persona_id: UUID | str) -> tuple[int, str] | None:
    """Devuelve (score, status) si existe una entrada válida en caché."""
    try:
        redis = get_redis()
        val = redis.get(_cache_key(persona_id))
        if val:
            data = json.loads(val)
            return int(data["score"]), data["status"]
    except Exception as exc:
        logger.warning("Error reading health cache from Redis", extra={"error": str(exc)})
    return None


def _set_cached_health(persona_id: UUID | str, score: int, status: str) -> None:
    """Guarda (score, status) en caché con TTL."""
    try:
        redis = get_redis()
        key = _cache_key(persona_id)
        data = json.dumps({"score": score, "status": status})
        redis.setex(key, _HEALTH_CACHE_TTL_SECONDS, data)
    except Exception as exc:
        logger.warning("Error setting health cache in Redis", extra={"error": str(exc)})


def _invalidate_health_cache(persona_id: UUID | str | None) -> None:
    """Invalida la entrada de caché para ``persona_id``."""
    if persona_id is None:
        return
    try:
        redis = get_redis()
        redis.delete(_cache_key(persona_id))
    except Exception as exc:
        logger.warning("Error invalidating health cache in Redis", extra={"error": str(exc)})


def _load_persona_for_health(db: Session, persona_id: UUID):
    return db.get(models.Persona, persona_id)


def _compute_pastoral_health_score(db: Session, persona: models.Persona) -> tuple[int, str, bool]:
    """Calcula el score y status pastoral sin mutar la base de datos.

    Devuelve ``(score, status, update_baptized)``. ``update_baptized`` indica
    si se detectó un milestone de bautizo y la persona no está marcada como
    bautizada, por lo que el caller debe actualizar ``Persona.is_baptized``.
    """
    is_baptized = bool(getattr(persona, "is_baptized", False))
    persona_id = persona.id

    # 1. Attendance score (aggregate in DB to avoid N+1 / memory bloat)
    attended_asistencias_count, opp_asistencias_count = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (
                            func.lower(func.trim(models.Asistencia.estado)).in_(
                                {"asistio", "presente", "present", "primera_vez", "first_time"}
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.count(models.Asistencia.id),
        )
        .filter(
            models.Asistencia.persona_id == persona_id,
            models.Asistencia.deleted_at.is_(None),
        )
        .first()
    )
    attended_asistencias_count = int(attended_asistencias_count)
    opp_asistencias_count = int(opp_asistencias_count)

    attended_events_count, opp_events_count = (
        db.query(
            func.coalesce(func.sum(case((models.EventAttendance.attended.is_(True), 1), else_=0)), 0),
            func.count(models.EventAttendance.id),
        )
        .filter(
            models.EventAttendance.persona_id == persona_id,
            models.EventAttendance.deleted_at.is_(None),
        )
        .first()
    )
    attended_events_count = int(attended_events_count)
    opp_events_count = int(opp_events_count)

    attended_courses_count, opp_courses_count = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (func.lower(func.trim(models.CourseAttendance.status)) == "present", 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.count(models.CourseAttendance.id),
        )
        .join(models.Enrollment, models.CourseAttendance.enrollment_id == models.Enrollment.id)
        .filter(
            models.Enrollment.persona_id == persona_id,
            models.Enrollment.deleted_at.is_(None),
        )
        .first()
    )
    attended_courses_count = int(attended_courses_count)
    opp_courses_count = int(opp_courses_count)

    # Communication logs: aggregate count and keyword-matched count in DB.
    comm_log_keywords = ["attend", "asist", "session", "class", "culto", "grupo"]
    keyword_filters = [models.CommunicationLog.content.ilike(f"%{keyword}%") for keyword in comm_log_keywords]
    comm_log_attend_count, comm_logs_count = (
        db.query(
            func.coalesce(func.sum(case((or_(*keyword_filters), 1), else_=0)), 0),
            func.count(models.CommunicationLog.id),
        )
        .filter(
            models.CommunicationLog.persona_id == persona_id,
            models.CommunicationLog.deleted_at.is_(None),
        )
        .first()
    )
    comm_log_attend_count = int(comm_log_attend_count)
    comm_logs_count = int(comm_logs_count)

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

    # 2. Milestone score (aggregated in DB)
    milestones_count, has_bapt_milestone = (
        db.query(
            func.count(models.SpiritualMilestone.id),
            func.coalesce(
                func.sum(
                    case(
                        (
                            or_(
                                models.SpiritualMilestone.type.ilike("%bapt%"),
                                models.SpiritualMilestone.type.ilike("%baut%"),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .filter(
            models.SpiritualMilestone.persona_id == persona_id,
            models.SpiritualMilestone.deleted_at.is_(None),
            or_(
                models.SpiritualMilestone.type.is_(None),
                ~models.SpiritualMilestone.type.like("Health Status Change to%"),
            ),
        )
        .first()
    )
    milestones_count = int(milestones_count)
    has_bapt_milestone = (has_bapt_milestone or 0) > 0
    update_baptized = has_bapt_milestone and not is_baptized and hasattr(models.Persona, "is_baptized")

    milestone_points = milestones_count
    if is_baptized or has_bapt_milestone:
        milestone_points += 1

    milestone_score = min(milestone_points * 10, 30)

    # 3. Communication score
    # comm_logs_count was already computed via the aggregate query above

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
        logger.info(
            "Health status transitioned",
            extra={
                "persona_id": str(persona_id),
                "previous_status": previous_status,
                "new_status": status,
                "score": score,
            },
        )
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
        db.execute(update(models.Persona).where(models.Persona.id == persona_id).values(**update_values))


def recalculate_and_persist_pastoral_health(db: Session, persona_id: UUID) -> tuple[int, str]:
    """Recalcula y persiste el health score de una persona.

    La lógica de cálculo sin side effects está en ``_compute_pastoral_health_score``.
    """
    with _suppress_health_invalidation():
        persona = _load_persona_for_health(db, persona_id)
        if not persona:
            raise ValueError(f"Persona with ID {persona_id} not found")

        previous_status = getattr(persona, "health_status", None)
        start_time = time.perf_counter()
        score, status, update_baptized = _compute_pastoral_health_score(db, persona)
        _persist_pastoral_health(db, persona_id, score, status, previous_status, update_baptized)
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Pastoral health recalculated",
            extra={
                "persona_id": str(persona_id),
                "previous_status": previous_status,
                "score": score,
                "status": status,
                "latency_ms": round(latency_ms, 2),
            },
        )
    return score, status


def update_pastoral_health(db: Session, persona_id: UUID) -> models.Persona | None:
    """Devuelve la Persona con health_score/health_status actualizados.

    Si existe una entrada de caché vigente, devuelve la persona cargada
    directamente desde la base de datos sin hacer commit. Si no, recalcula,
    persiste, hace commit y refresca el caché.
    """
    with _suppress_health_invalidation():
        cached = _get_cached_health(persona_id)
        if cached is None:
            logger.debug(
                "Health cache miss",
                extra={"persona_id": str(persona_id), "cache_status": "miss"},
            )
            score, status = recalculate_and_persist_pastoral_health(db, persona_id)
            db.commit()
            _set_cached_health(persona_id, score, status)
        else:
            logger.debug(
                "Health cache hit",
                extra={
                    "persona_id": str(persona_id),
                    "cache_status": "hit",
                    "cached_score": cached[0],
                    "cached_status": cached[1],
                },
            )

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

    # Invalidación para operaciones bulk que bypassan los eventos de instancia.
    event.listen(Session, "do_orm_execute", _handle_bulk_orm_execute)


# ═══════════════════════════════════════════════════════════════════
# Invalidación de caché para operaciones bulk (bypass ORM)
# ═══════════════════════════════════════════════════════════════════

# Mapa de modelo -> columna de persona_id. Para modelos indirectos se usa la
# columna resultante de un JOIN (ver _affected_persona_ids_for_bulk).
_BULK_INVALIDATION_TABLES: dict = {
    models.Asistencia: models.Asistencia.persona_id,
    models.EventAttendance: models.EventAttendance.persona_id,
    models.Enrollment: models.Enrollment.persona_id,
    models.CommunicationLog: models.CommunicationLog.persona_id,
    models.CasoCRM: models.CasoCRM.persona_id,
    models.Donation: models.Donation.persona_id,
    models.SpiritualMilestone: models.SpiritualMilestone.persona_id,
    models.Persona: models.Persona.id,
}


def _affected_persona_ids_for_bulk(session: Session, statement, parameters: dict | None = None) -> list[UUID]:
    """Devuelve las persona_id afectadas por un UPDATE/DELETE bulk.

    Para modelos con ``persona_id`` directa se reutiliza la cláusula WHERE del
    statement original. Para ``CourseAttendance`` e ``InteraccionCRM`` se
    realiza el JOIN correspondiente para resolver la persona.

    ``parameters`` contiene los valores vinculados del statement original y se
    propagan al SELECT interno para que el WHERE resuelva correctamente.
    """
    table = getattr(statement, "table", None)

    # SQLAlchemy 2.0 almacena la colección de cláusulas WHERE en
    # _where_criteria; usamos whereclause solo como fallback.
    where_criteria = getattr(statement, "_where_criteria", ())
    if not where_criteria:
        whereclause = getattr(statement, "whereclause", None)
        if whereclause is not None:
            where_criteria = (whereclause,)

    if table is None or not where_criteria:
        return []

    def _execute(stmt):
        if parameters:
            return session.execute(stmt, parameters)
        return session.execute(stmt)

    table_name = getattr(table, "name", None)

    # CourseAttendance -> Enrollment.persona_id
    if table_name == models.CourseAttendance.__tablename__:
        stmt = (
            select(models.Enrollment.persona_id)
            .select_from(models.CourseAttendance)
            .join(models.Enrollment, models.CourseAttendance.enrollment_id == models.Enrollment.id)
            .where(*where_criteria)
            .distinct()
        )
        return [row[0] for row in _execute(stmt)]

    # InteraccionCRM -> CasoCRM.persona_id
    if table_name == models.InteraccionCRM.__tablename__:
        stmt = (
            select(models.CasoCRM.persona_id)
            .select_from(models.InteraccionCRM)
            .join(models.CasoCRM, models.InteraccionCRM.caso_id == models.CasoCRM.id)
            .where(*where_criteria)
            .distinct()
        )
        return [row[0] for row in _execute(stmt)]

    persona_id_col = _BULK_INVALIDATION_TABLES.get(models.Persona)
    for model, col in _BULK_INVALIDATION_TABLES.items():
        if table_name == model.__tablename__:
            persona_id_col = col
            break
    else:
        return []

    stmt = select(persona_id_col).where(*where_criteria).distinct()
    return [row[0] for row in _execute(stmt)]


def _handle_bulk_orm_execute(orm_execute_state):
    """Invalida el caché de salud tras operaciones bulk UPDATE/DELETE.

    Los eventos ``after_insert/update/delete`` solo se disparan para instancias
    ORM individuales. Las operaciones ``session.execute(update(Model).where(...))``,
    ``session.execute(delete(Model).where(...))`` y similares bypassan esos
    eventos. Este listener captura esos casos y borra las entradas de caché de
    las ``persona_id`` afectadas *antes* de que el motor ejecute la sentencia,
    asegurando que la próxima lectura vea los datos frescos.
    """
    if _bulk_invalidation_ctx.get() or _health_update_ctx.get():
        return
    if getattr(orm_execute_state, "is_select", False):
        return
    if not (getattr(orm_execute_state, "is_update", False) or getattr(orm_execute_state, "is_delete", False)):
        return

    statement = getattr(orm_execute_state, "statement", None)
    session = getattr(orm_execute_state, "session", None)
    if statement is None or session is None:
        return

    table = getattr(statement, "table", None)
    if table is None:
        return

    relevant_table_names = {m.__tablename__ for m in _BULK_INVALIDATION_TABLES} | {
        models.CourseAttendance.__tablename__,
        models.InteraccionCRM.__tablename__,
    }
    table_name = getattr(table, "name", None)
    if table_name not in relevant_table_names:
        return

    parameters = getattr(orm_execute_state, "parameters", None)
    token = _bulk_invalidation_ctx.set(True)
    try:
        persona_ids: list[UUID] = []
        if isinstance(parameters, list):
            seen: set[UUID] = set()
            for params in parameters:
                for pid in _affected_persona_ids_for_bulk(session, statement, params):
                    if pid not in seen:
                        seen.add(pid)
                        persona_ids.append(pid)
        else:
            persona_ids = _affected_persona_ids_for_bulk(session, statement, parameters)
    except Exception as exc:
        logger.warning("Failed to resolve affected persona_ids for bulk invalidation", extra={"error": str(exc)})
        return
    finally:
        _bulk_invalidation_ctx.reset(token)

    for persona_id in persona_ids:
        _invalidate_health_cache(persona_id)


_register_health_event_listeners()

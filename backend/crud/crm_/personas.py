"""Persona CRUD and search helpers."""
import datetime as dt
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, inspect, or_
from sqlalchemy.orm import Session, load_only, selectinload

from backend import models, schemas
from backend.crud._utils import _to_uuid, _utcnow
from backend.crud.crm_.shared import _audit_log


def _persona_live_column_names(db: Session) -> set[str]:
    bind = db.get_bind()
    if bind is None:
        return set()
    try:
        columns = inspect(bind).get_columns("personas")
    except Exception:
        return set()
    return {str(column.get("name")) for column in columns if column.get("name")}


def persona_query(db: Session):
    live_cols = _persona_live_column_names(db)
    live_attrs = [
        getattr(models.Persona, name)
        for name in live_cols
        if hasattr(models.Persona, name)
    ]
    query = db.query(models.Persona)
    if live_attrs:
        query = query.options(load_only(*live_attrs))
    return query


def prepare_persona_for_output(db: Session, persona: models.Persona):
    live_cols = _persona_live_column_names(db)
    for field_name in schemas.PersonaResponse.model_fields:
        if field_name == "nombre_completo" or field_name in live_cols:
            continue
        if hasattr(models.Persona, field_name):
            try:
                setattr(persona, field_name, None)
            except Exception:
                persona.__dict__[field_name] = None
    return persona


def create_persona(db: Session, payload: schemas.PersonaCreate) -> models.Persona:
    # Axioma 1 — Validación de Identidad Previa: buscar persona existente
    # por teléfono o documento antes de crear un duplicado.
    existing = _find_existing_persona(db, payload)
    if existing:
        # Si existe, devolver el registro existente (no crear duplicado)
        return existing

    import uuid as _uuid

    data = payload.model_dump(exclude_unset=True)
    data.setdefault("qr_token", _uuid.uuid4().hex[:16].upper())
    row = models.Persona(**data)
    db.add(row)
    db.commit()
    row = get_persona(db, row.id)
    if row is None:
        raise RuntimeError("Created persona could not be reloaded safely")
    _audit_log(
        db,
        "personas",
        str(row.id),
        "CREATE",
        detalles={
            "first_name": row.first_name,
            "last_name": row.last_name,
            "phone": row.phone,
            "church_role": row.church_role,
        },
    )

    # Inter-módulos: notificar registro de nuevo miembro/persona
    try:
        from backend.services.event_consumers import dispatch_event
        dispatch_event("persona_registered", {
            "persona_id": str(row.id),
            "name": f"{row.first_name} {row.last_name or ''}".strip(),
            "church_role": str(row.church_role) if row.church_role else "Visitante",
            "email": row.email,
        })
    except Exception:
        pass

    return row


def _find_existing_persona(db: Session, payload: schemas.PersonaCreate) -> Optional[models.Persona]:
    """Busca una persona existente por teléfono o número de documento.

    Axioma 1 — Person-Centric Kernel: anexar al UUID existente, no duplicar.
    """
    phones = [p for p in (payload.phone, payload.mobile_phone) if p]
    if phones:
        match = (
            persona_query(db)
            .filter(
                or_(
                    models.Persona.phone.in_(phones),
                    models.Persona.mobile_phone.in_(phones),
                )
            )
            .first()
        )
        if match:
            return match

    if payload.id_number:
        match = persona_query(db).filter(models.Persona.id_number == payload.id_number).first()
        if match:
            return match

    return None


def _build_persona_search_query(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    estado_vital: str | None = None,
    spiritual_status: str | None = None,
    sex: str | None = None,
    group_name: str | None = None,
    participation_type: str | None = None,
    id_type: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    family_id: UUID | None = None,
    sede_id: UUID | None = None,
):
    query = persona_query(db).options(
        selectinload(models.Persona.family),
        selectinload(models.Persona.positions),
    )
    # Axioma 3 — Multi-Tenant: filtrar por sede obligatoriamente
    if sede_id is not None:
        query = query.filter(models.Persona.sede_id == sede_id)
    if search:
        like = f"%{search}%"
        # NOTA: nombre_completo es @hybrid_property con expresión SQL, funciona en filter
        query = query.filter(
            or_(
                models.Persona.first_name.ilike(like),
                models.Persona.last_name.ilike(like),
                models.Persona.nombre_completo.ilike(like),
                models.Persona.email.ilike(like),
                models.Persona.id_number.ilike(like),
                models.Persona.phone.ilike(like),
                models.Persona.mobile_phone.ilike(like),
            )
        )
    if role:
        query = query.filter(models.Persona.church_role == role)
    if estado_vital:
        query = query.filter(models.Persona.estado_vital == estado_vital)
    if spiritual_status:
        query = query.filter(models.Persona.spiritual_status == spiritual_status)
    if sex:
        query = query.filter(models.Persona.sex == sex)
    if id_type:
        query = query.filter(models.Persona.id_type == id_type)
    if group_name:
        query = query.filter(models.Persona.group_name == group_name)
    if participation_type:
        query = query.filter(models.Persona.participation_type == participation_type)
    if min_age is not None:
        cutoff = dt.date.today() - dt.timedelta(days=min_age * 365)
        query = query.filter(models.Persona.birthday <= cutoff)
    if max_age is not None:
        cutoff = dt.date.today() - dt.timedelta(days=max_age * 365 + 1)
        query = query.filter(models.Persona.birthday >= cutoff)
    if family_id:
        query = query.filter(models.Persona.family_id == family_id)
    return query


def search_personas(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    estado_vital: str | None = None,
    spiritual_status: str | None = None,
    sex: str | None = None,
    group_name: str | None = None,
    participation_type: str | None = None,
    id_type: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    family_id: UUID | None = None,
    sede_id: UUID | None = None,
    skip: int = 0,
    limit: int = 1000,
    sort_by: str | None = None,
    sort_dir: str = "asc",
):
    query = _build_persona_search_query(
        db,
        search=search,
        role=role,
        estado_vital=estado_vital,
        spiritual_status=spiritual_status,
        sex=sex,
        group_name=group_name,
        participation_type=participation_type,
        id_type=id_type,
        min_age=min_age,
        max_age=max_age,
        family_id=family_id,
        sede_id=sede_id,
    )
    sort_col = getattr(models.Persona, sort_by or "nombre_completo", models.Persona.nombre_completo)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    personas = query.offset(skip).limit(limit).all()
    personas = [prepare_persona_for_output(db, p) for p in personas]
    return _enrich_personas_with_progress(db, personas)


def search_personas_page(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    estado_vital: str | None = None,
    spiritual_status: str | None = None,
    sex: str | None = None,
    group_name: str | None = None,
    participation_type: str | None = None,
    id_type: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    family_id: UUID | None = None,
    sede_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> dict:
    query = _build_persona_search_query(
        db,
        search=search,
        role=role,
        estado_vital=estado_vital,
        spiritual_status=spiritual_status,
        sex=sex,
        group_name=group_name,
        participation_type=participation_type,
        id_type=id_type,
        min_age=min_age,
        max_age=max_age,
        family_id=family_id,
        sede_id=sede_id,
    )
    total = query.order_by(None).count()
    available_groups = [
        row[0]
        for row in (
            query.with_entities(models.Persona.group_name)
            .order_by(models.Persona.group_name.asc())
            .distinct()
            .all()
        )
        if row[0]
    ]
    sort_col = getattr(models.Persona, sort_by or "nombre_completo", models.Persona.nombre_completo)
    personas = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc()).offset(skip).limit(limit).all()
    personas = [prepare_persona_for_output(db, p) for p in personas]
    return {
        "items": _enrich_personas_with_progress(db, personas),
        "total": total,
        "skip": skip,
        "limit": limit,
        "available_groups": available_groups,
    }


def get_persona(db: Session, persona_id: str) -> Optional[models.Persona]:
    persona = persona_query(db).filter(models.Persona.id == _to_uuid(persona_id)).first()
    return _attach_persona_detail_payload(db, prepare_persona_for_output(db, persona)) if persona else None


def list_mentor_candidates(
    db: Session,
    persona_id: str,
    search: str | None = None,
    limit: int = 20,
    sede_id: UUID | None = None,
) -> list[models.Persona]:
    query = persona_query(db)
    persona_uuid = _to_uuid(persona_id)
    if sede_id is not None:
        query = query.filter(models.Persona.sede_id == sede_id)
    query = query.filter(models.Persona.id != persona_uuid)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.Persona.first_name.ilike(like),
                models.Persona.last_name.ilike(like),
                models.Persona.nombre_completo.ilike(like),
                models.Persona.email.ilike(like),
                models.Persona.phone.ilike(like),
                models.Persona.mobile_phone.ilike(like),
            )
        )

    rows = query.order_by(models.Persona.nombre_completo.asc()).limit(max(limit * 3, limit)).all()
    rows = [prepare_persona_for_output(db, p) for p in rows]
    rows = _enrich_personas_with_progress(db, rows)

    candidates: list[models.Persona] = []
    for row in rows:
        if str(getattr(row, "estado_vital", "")).upper() == "INACTIVO":
            continue
        health_score = float(getattr(row, "health_score", 0) or 0)
        academy_progress = float(getattr(row, "academy_progress", 0) or 0)
        volunteer_commitment = float(getattr(row, "volunteer_commitment", 0) or 0)
        fit_score = int(round((health_score * 0.45) + (academy_progress * 0.35) + (volunteer_commitment * 0.2)))
        if fit_score < 40:
            continue
        row.fit_score = fit_score
        row.fit_reason = (
            f"Salud {health_score:.0f}%, academia {academy_progress:.0f}% y servicio {volunteer_commitment:.0f}%."
        )
        candidates.append(row)

    candidates.sort(
        key=lambda persona: (
            -int(getattr(persona, "fit_score", 0) or 0),
            -float(getattr(persona, "health_score", 0) or 0),
            getattr(persona, "nombre_completo", "") or "",
        )
    )
    return candidates[:limit]


def assign_persona_mentor(
    db: Session,
    mentee_persona_id: str,
    mentor_persona_id: str,
    *,
    assigned_by_user_id: str | None = None,
    notes: str | None = None,
) -> models.PersonaMentorship:
    mentee_uuid = _to_uuid(mentee_persona_id)
    mentor_uuid = _to_uuid(mentor_persona_id)
    if mentee_uuid == mentor_uuid:
        raise ValueError("Una persona no puede ser su propio mentor")

    mentee = persona_query(db).filter(models.Persona.id == mentee_uuid).first()
    mentor = persona_query(db).filter(models.Persona.id == mentor_uuid).first()
    if not mentee or not mentor:
        raise ValueError("Mentor o mentee no encontrado")

    if str(getattr(mentee, "sede_id", "") or "") != str(getattr(mentor, "sede_id", "") or ""):
        raise ValueError("Mentor y mentee deben pertenecer a la misma sede")

    active_assignment = _active_mentorship_query(db, mentee_uuid)
    if active_assignment and active_assignment.mentor_persona_id == mentor_uuid:
        active_assignment.notes = notes or active_assignment.notes
        active_assignment.assigned_by_user_id = _to_uuid(assigned_by_user_id) if assigned_by_user_id else active_assignment.assigned_by_user_id
        db.commit()
        db.refresh(active_assignment)
        return _decorate_mentorship(active_assignment)

    if active_assignment:
        active_assignment.status = "inactive"
        active_assignment.ended_at = _utcnow()

    assignment = models.PersonaMentorship(
        sede_id=getattr(mentee, "sede_id", None),
        mentee_persona_id=mentee_uuid,
        mentor_persona_id=mentor_uuid,
        assigned_by_user_id=_to_uuid(assigned_by_user_id) if assigned_by_user_id else None,
        status="active",
        notes=notes,
        started_at=_utcnow(),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _decorate_mentorship(assignment)


def update_persona(db: Session, persona_id: str, payload: schemas.PersonaUpdate) -> Optional[models.Persona]:
    row = persona_query(db).filter(models.Persona.id == _to_uuid(persona_id)).first()
    if not row:
        return None

    # Capturar valores anteriores para el trigger de embudo
    old_church_role = row.church_role
    old_estado_vital = row.estado_vital
    old_baptism_date = row.baptism_date

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)

    # Axioma 1 — Integridad de Embudo: registrar cambios en historial_embudo
    _track_funnel_changes(db, row, old_church_role, old_estado_vital, old_baptism_date)

    db.commit()
    row = get_persona(db, persona_id)
    if not row:
        return None
    _audit_log(
        db,
        "personas",
        str(row.id),
        "UPDATE",
        detalles={"church_role": row.church_role, "estado_vital": row.estado_vital},
    )

    # Inter-módulos: disparar eventos cuando cambia estado espiritual o rol
    try:
        from backend.services.event_consumers import dispatch_event
        if old_church_role != row.church_role:
            dispatch_event("persona_status_changed", {
                "persona_id": str(row.id),
                "from_role": str(old_church_role) if old_church_role else None,
                "to_role": str(row.church_role) if row.church_role else None,
            })
        if old_estado_vital != row.estado_vital:
            dispatch_event("spiritual_stage_transition", {
                "persona_id": str(row.id),
                "from_stage": old_estado_vital,
                "to_stage": row.estado_vital,
                "agent_id": str(row.id),
            })
    except Exception:
        pass  # eventos son best-effort, nunca bloquean la transacción

    return row


def _track_funnel_changes(db: Session, persona, old_church_role, old_estado_vital, old_baptism_date):
    """Registra cambios de rol, estado vital o fecha de bautismo."""
    from backend.models_evangelism import HistorialEmbudo

    now = _utcnow()
    pid = persona.id if hasattr(persona, "id") else persona.id

    # church_role
    if old_church_role and old_church_role != persona.church_role:
        days = _compute_days_in_state(db, pid, old_church_role)
        db.add(
            HistorialEmbudo(
                persona_id=pid,
                rol_anterior=str(old_church_role),
                rol_nuevo=str(persona.church_role),
                fecha_cambio=now,
                dias_en_estado_anterior=days,
            )
        )

    # estado_vital
    if old_estado_vital and old_estado_vital != persona.estado_vital:
        days = _compute_days_in_state(db, pid, old_estado_vital)
        db.add(
            HistorialEmbudo(
                persona_id=pid,
                rol_anterior=str(old_estado_vital),
                rol_nuevo=str(persona.estado_vital),
                fecha_cambio=now,
                dias_en_estado_anterior=days,
            )
        )

    # baptism_date (nuevo bautismo)
    if old_baptism_date is None and persona.baptism_date is not None:
        db.add(
            HistorialEmbudo(
                persona_id=pid,
                rol_anterior="NO_BAUTIZADO",
                rol_nuevo="BAUTIZADO",
                fecha_cambio=now,
                dias_en_estado_anterior=None,
            )
        )


def _compute_days_in_state(db: Session, persona_id, state_name: str) -> int | None:
    """Calcula cuántos días pasó la persona en el estado anterior."""
    from backend.models_evangelism import HistorialEmbudo

    last_entry = (
        db.query(HistorialEmbudo)
        .filter(HistorialEmbudo.persona_id == persona_id)
        .order_by(HistorialEmbudo.fecha_cambio.desc())
        .first()
    )
    if last_entry and last_entry.fecha_cambio:
        delta = _utcnow() - last_entry.fecha_cambio
        return delta.days
    return None


def delete_persona(db: Session, persona_id: str) -> bool:
    row = persona_query(db).filter(models.Persona.id == _to_uuid(persona_id)).first()
    if not row:
        return False
    # Soft-delete: nunca eliminar físicamente una Persona.
    # Axioma 1 — Person-Centric Kernel: solo se cambia estado_vital a INACTIVO.
    row.estado_vital = "INACTIVO"
    row.unregistration_date = _utcnow().date()
    db.commit()
    _audit_log(
        db,
        "personas",
        str(row.id),
        "SOFT_DELETE",
        detalles={"estado_vital": "INACTIVO", "unregistration_date": str(row.unregistration_date)},
    )
    return True


def get_persona_donations(db: Session, persona_id: str):
    return (
        db.query(models.Donation)
        .filter(models.Donation.persona_id == persona_id)
        .order_by(models.Donation.created_at.desc())
        .all()
    )


_MEMBER_SORT_FIELDS = {
    "first_name": models.Persona.first_name,
    "last_name": models.Persona.last_name,
    "email": models.Persona.email,
    "church_role": models.Persona.church_role,
    "spiritual_status": models.Persona.spiritual_status,
    "created_at": models.Persona.created_at,
}


def _enrich_personas_with_progress(
    db: Session,
    personas: List[models.Persona],
) -> List[models.Persona]:
    """Adjunta métricas operativas reales a cada persona in-place."""
    if not personas:
        return personas
    persona_ids = [p.id for p in personas]
    progress_data = (
        db.query(
            models.Enrollment.persona_id,
            func.avg(models.Enrollment.progress_percent),
        )
        .filter(models.Enrollment.persona_id.in_(persona_ids))
        .filter(models.Enrollment.deleted_at.is_(None))
        .group_by(models.Enrollment.persona_id)
        .all()
    )
    progress_map = {pid: float(avg or 0.0) for pid, avg in progress_data}
    volunteer_map = _volunteer_commitment_map(db, persona_ids)
    for p in personas:
        p.academy_progress = progress_map.get(p.id, 0.0)
        health_score = getattr(p, "health_score", None)
        p.spiritual_health = round(float(health_score or 80) / 100, 2) if health_score is not None else 0.8
        p.volunteer_commitment = volunteer_map.get(p.id, 0.0)
    return personas


def _normalize_token(value: str | None) -> str:
    if not value:
        return ""
    import unicodedata

    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).upper().strip()


def _attendance_rate_map(db: Session, persona_ids: List[UUID]) -> dict[UUID, float]:
    if not persona_ids:
        return {}

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
    rows = (
        db.query(models.Asistencia)
        .join(models.SesionGrupo, models.Asistencia.sesion_id == models.SesionGrupo.id)
        .filter(
            models.Asistencia.persona_id.in_(persona_ids),
            models.Asistencia.deleted_at.is_(None),
            models.SesionGrupo.fecha_sesion >= cutoff,
        )
        .all()
    )
    buckets: dict[UUID, list[models.Asistencia]] = {}
    for row in rows:
        buckets.setdefault(row.persona_id, []).append(row)

    rate_map: dict[UUID, float] = {}
    for persona_id, items in buckets.items():
        attended = sum(1 for item in items if getattr(item, "attended", False))
        rate_map[persona_id] = round((attended / len(items)) * 100, 1) if items else 0.0
    return rate_map


def _volunteer_commitment_map(db: Session, persona_ids: List[UUID]) -> dict[UUID, float]:
    if not persona_ids:
        return {}

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=90)

    def _as_aware_utc(value):
        # SQLite no persiste tzinfo en DateTime(timezone=True), aún cuando el
        # modelo lo declara. SQLAlchemy devuelve naive datetimes al recuperar,
        # lo que rompe la comparación contra un cutoff timezone-aware.
        # Normalizamos defensively: si llega naive, asumimos UTC (axioma CCF).
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=dt.timezone.utc)

    shifts = (
        db.query(models.VolunteerShift)
        .filter(
            models.VolunteerShift.persona_id.in_(persona_ids),
            models.VolunteerShift.deleted_at.is_(None),
        )
        .all()
    )
    buckets: dict[UUID, list[models.VolunteerShift]] = {}
    for shift in shifts:
        buckets.setdefault(shift.persona_id, []).append(shift)

    commitment_map: dict[UUID, float] = {}
    for persona_id, items in buckets.items():
        recent = [
            shift
            for shift in items
            if (_as_aware_utc(shift.shift_start) and _as_aware_utc(shift.shift_start) >= cutoff)
            or (_as_aware_utc(shift.shift_end) and _as_aware_utc(shift.shift_end) >= cutoff)
        ]
        recent_hours = 0.0
        for shift in recent:
            start = _as_aware_utc(shift.shift_start)
            end = _as_aware_utc(shift.shift_end)
            if start and end:
                recent_hours += max((end - start).total_seconds() / 3600, 0)
        unique_teams = {str(shift.team_name).strip().lower() for shift in recent if shift.team_name}
        score = min(100.0, (len(recent) * 20.0) + min(recent_hours * 2.0, 40.0) + (len(unique_teams) * 10.0))
        commitment_map[persona_id] = round(score, 1)
    return commitment_map


def _active_mentorship_query(db: Session, persona_id: UUID):
    return (
        db.query(models.PersonaMentorship)
        .filter(
            models.PersonaMentorship.mentee_persona_id == persona_id,
            models.PersonaMentorship.deleted_at.is_(None),
            models.PersonaMentorship.status == "active",
        )
        .order_by(models.PersonaMentorship.started_at.desc())
        .first()
    )


def _decorate_mentorship(row: models.PersonaMentorship | None) -> models.PersonaMentorship | None:
    if not row:
        return None
    mentor = getattr(row, "mentor", None)
    mentee = getattr(row, "mentee", None)
    row.mentor_name = (
        getattr(mentor, "nombre_completo", None)
        or (f"{getattr(mentor, 'first_name', '')} {getattr(mentor, 'last_name', '')}".strip() if mentor else None)
    )
    row.mentor_role = getattr(mentor, "church_role", None)
    row.mentee_name = (
        getattr(mentee, "nombre_completo", None)
        or (f"{getattr(mentee, 'first_name', '')} {getattr(mentee, 'last_name', '')}".strip() if mentee else None)
    )
    row.mentee_role = getattr(mentee, "church_role", None)
    return row


def _build_persona_mesh_insight(db: Session, persona: models.Persona) -> schemas.PersonaMeshInsight:
    attendance_rate = _attendance_rate_map(db, [persona.id]).get(persona.id, 0.0)
    volunteer_commitment = _volunteer_commitment_map(db, [persona.id]).get(persona.id, 0.0)
    academy_progress = float(getattr(persona, "academy_progress", 0.0) or 0.0)
    health_score = getattr(persona, "health_score", None)
    health_status = getattr(persona, "health_status", None)
    current_mentorship = _decorate_mentorship(_active_mentorship_query(db, persona.id))

    metrics = [
        schemas.PersonaMeshMetric(
            key="attendance",
            label="Asistencia Mensual",
            value=attendance_rate,
            display_value=f"{attendance_rate:.0f}%",
            detail="Basado en asistencias registradas en los últimos 30 días.",
            tone="emerald" if attendance_rate >= 80 else "amber" if attendance_rate >= 50 else "rose",
            has_data=attendance_rate > 0,
        ),
        schemas.PersonaMeshMetric(
            key="academy",
            label="Progreso Academia",
            value=academy_progress,
            display_value=f"{academy_progress:.0f}%",
            detail="Promedio de progreso en cursos activos.",
            tone="blue" if academy_progress >= 60 else "amber" if academy_progress >= 30 else "slate",
            has_data=getattr(persona, "academy_progress", None) is not None,
        ),
        schemas.PersonaMeshMetric(
            key="volunteer",
            label="Compromiso Voluntario",
            value=volunteer_commitment,
            display_value=f"{volunteer_commitment:.0f}%",
            detail="Turnos de servicio y horas recientes registradas.",
            tone="amber" if volunteer_commitment >= 70 else "blue" if volunteer_commitment >= 40 else "slate",
            has_data=volunteer_commitment > 0,
        ),
    ]

    if health_status == "COMPROMETIDO":
        summary = f"{persona.nombre_completo} mantiene un ritmo ministerial saludable y consistente."
        recommendation = "Mantener mentoría activa y abrir espacios de liderazgo progresivo."
    elif health_status == "ESTABLE":
        summary = f"{persona.nombre_completo} muestra base estable y señales de crecimiento."
        recommendation = "Consolidar seguimiento y reforzar hábitos de servicio y formación."
    elif health_status == "EN_RIESGO":
        summary = f"{persona.nombre_completo} requiere acompañamiento más cercano."
        recommendation = "Priorizar contacto pastoral y revisar barreras de asistencia o formación."
    else:
        summary = f"{persona.nombre_completo} todavía necesita más datos para evaluar su ritmo ministerial."
        recommendation = "Registrar asistencia, academia y servicio para obtener un panorama confiable."

    signals = []
    if attendance_rate > 0:
        signals.append(f"Asistencia reciente: {attendance_rate:.0f}%")
    if academy_progress > 0:
        signals.append(f"Academia: {academy_progress:.0f}%")
    if volunteer_commitment > 0:
        signals.append(f"Servicio: {volunteer_commitment:.0f}%")
    if current_mentorship and current_mentorship.mentor_name:
        signals.append(f"Mentoría actual: {current_mentorship.mentor_name}")

    return schemas.PersonaMeshInsight(
        summary=summary,
        recommendation=recommendation,
        health_score=health_score,
        health_status=health_status,
        attendance_rate=attendance_rate,
        academy_progress=academy_progress,
        volunteer_commitment=volunteer_commitment,
        metrics=metrics,
        signals=signals,
        current_mentorship=current_mentorship,
        generated_at=_utcnow(),
    )


def _attach_persona_detail_payload(db: Session, persona: models.Persona) -> models.Persona:
    _enrich_personas_with_progress(db, [persona])
    persona.current_mentorship = _decorate_mentorship(_active_mentorship_query(db, persona.id))
    persona.mesh_insight = _build_persona_mesh_insight(db, persona)
    return persona


def search_personas_paginated(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    spiritual_status: str | None = None,
    sede_id: UUID | None = None,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> dict:
    """Returns { items: [...], total: N } for server-side AG Grid pagination."""
    query = persona_query(db).options(
        selectinload(models.Persona.family),
        selectinload(models.Persona.positions),
    )
    # Axioma 3 — Multi-Tenant: filtrar por sede obligatoriamente
    if sede_id is not None:
        query = query.filter(models.Persona.sede_id == sede_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.Persona.first_name.ilike(like),
                models.Persona.last_name.ilike(like),
                models.Persona.email.ilike(like),
                models.Persona.church_role.ilike(like),
            )
        )
    if role:
        query = query.filter(models.Persona.church_role == role)
    if spiritual_status:
        query = query.filter(models.Persona.spiritual_status == spiritual_status)

    total = query.count()

    sort_col = _MEMBER_SORT_FIELDS.get(sort_by or "last_name", models.Persona.last_name)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    personas = query.offset(offset).limit(limit).all()
    return {"items": _enrich_personas_with_progress(db, personas), "total": total}


def get_personas(db: Session, search: str | None = None, role: str | None = None):
    return search_personas(db, search=search, role=role)


def get_talents(db: Session, search: str | None = None):
    return search_personas(db, search=search)

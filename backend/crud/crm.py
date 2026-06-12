"""CRM: Members, pipeline, events, tasks, counseling, prayer, grupos, etc."""

import datetime as dt
import uuid
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from backend import models, schemas
from backend.core.security import decrypt_data, encrypt_data
from backend.crud._utils import _utcnow
from backend.schemas.crm import CrmEventUpdate
from backend.schemas.legacy import CommunityBoardCardUpdate
from backend.schemas.notifications import CommunicationLogUpdate


def _is_uuid_like(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False


def resolve_persona_id_for_user(db: Session, user_id: int | str | None):
    if user_id is None:
        return None
    try:
        persona_uuid = uuid.UUID(str(user_id))
    except (TypeError, ValueError, AttributeError):
        return None
    persona = (
        db.query(models.Persona.id)
        .filter(models.Persona.id == persona_uuid)
        .first()
    )
    return persona[0] if persona else None


def resolve_persona_id_from_identity(db: Session, identity: int | str | None):
    if identity is None:
        return None
    if _is_uuid_like(identity):
        return uuid.UUID(str(identity))
    return resolve_persona_id_for_user(db, identity)


def legacy_user_id_from_identity(identity: int | str | None):
    if identity is None or _is_uuid_like(identity):
        return None
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def get_user_sede_id(db: Session, user_id: str) -> str | None:
    """Obtiene el sede_id de la Persona vinculada al usuario actual.

    Retorna None si el usuario no tiene persona asociada o la persona no tiene sede.
    Usado para imponer filtro Multi-Tenant (Axioma 3) en todas las queries.
    """
    from backend.core.tenant import get_user_sede_id as resolve_user_sede_id

    return resolve_user_sede_id(db, user_id)


def _audit_log(
    db: Session, tabla: str, registro_id: str, accion: str, detalles: dict | None = None, usuario_id: str | None = None
) -> None:
    """Registra una entrada en logs_auditoria (JSONB) para trazabilidad.

    Axioma 1 — Auditoría Estricta: toda mutación sensible debe dejar traza.
    """
    from backend.models_evangelism import LogAuditoria
    import uuid as _uuid

    db.add(
        LogAuditoria(
            tabla_afectada=tabla,
            registro_id=str(registro_id),
            accion=accion,
            detalles_cambio=detalles or {},
            usuario_id=_uuid.UUID(usuario_id) if usuario_id else None,
        )
    )


# ── Personas ────────────────────────────────────────────


def create_persona(db: Session, payload: schemas.PersonaCreate) -> models.Persona:
    # Axioma 1 — Validación de Identidad Previa: buscar persona existente
    # por teléfono o documento antes de crear un duplicado.
    existing = _find_existing_persona(db, payload)
    if existing:
        # Si existe, devolver el registro existente (no crear duplicado)
        return existing

    import uuid as _uuid

    data = payload.model_dump(exclude_unset=True)
    if "baptism_date" in data:
        data["fecha_bautismo"] = data.pop("baptism_date")
    data.setdefault("qr_token", _uuid.uuid4().hex[:16].upper())
    row = models.Persona(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
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
        dispatch_event("member_registered", {
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
            db.query(models.Persona)
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
        match = db.query(models.Persona).filter(models.Persona.id_number == payload.id_number).first()
        if match:
            return match

    return None


def search_personas(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    estado_vital: str | None = None,
    sex: str | None = None,
    group_name: str | None = None,
    membership_type: str | None = None,
    id_type: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    family_id: int | None = None,
    sede_id: str | None = None,
    skip: int = 0,
    limit: int = 1000,
    sort_by: str | None = None,
    sort_dir: str = "asc",
):
    query = db.query(models.Persona).options(
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
    if sex:
        query = query.filter(models.Persona.sex == sex)
    if id_type:
        query = query.filter(models.Persona.id_type == id_type)
    if group_name:
        query = query.filter(models.Persona.group_name == group_name)
    if membership_type:
        query = query.filter(models.Persona.membership_type == membership_type)
    if min_age is not None:
        from sqlalchemy import func as sa_func
        cutoff = dt.date.today() - dt.timedelta(days=min_age * 365)
        query = query.filter(models.Persona.birthday <= cutoff)
    if max_age is not None:
        cutoff = dt.date.today() - dt.timedelta(days=max_age * 365 + 1)
        query = query.filter(models.Persona.birthday >= cutoff)
    if family_id:
        query = query.filter(models.Persona.family_id == family_id)

    sort_col = getattr(models.Persona, sort_by or "nombre_completo", models.Persona.nombre_completo)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    return query.offset(skip).limit(limit).all()


def get_persona(db: Session, persona_id: str) -> Optional[models.Persona]:
    return db.query(models.Persona).filter(models.Persona.id == uuid.UUID(persona_id)).first()


def update_persona(db: Session, persona_id: str, payload: schemas.PersonaUpdate) -> Optional[models.Persona]:
    row = db.query(models.Persona).filter(models.Persona.id == uuid.UUID(persona_id)).first()
    if not row:
        return None

    # Capturar valores anteriores para el trigger de embudo
    old_church_role = row.church_role
    old_estado_vital = row.estado_vital
    old_fecha_bautismo = row.fecha_bautismo

    updates = payload.model_dump(exclude_unset=True)
    if "baptism_date" in updates:
        updates["fecha_bautismo"] = updates.pop("baptism_date")
    for key, value in updates.items():
        setattr(row, key, value)

    # Axioma 1 — Integridad de Embudo: registrar cambios en historial_embudo
    _track_funnel_changes(db, row, old_church_role, old_estado_vital, old_fecha_bautismo)

    db.commit()
    db.refresh(row)
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
            dispatch_event("member_status_changed", {
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


def _track_funnel_changes(db: Session, persona, old_church_role, old_estado_vital, old_fecha_bautismo):
    """Registra en HistorialEmbudo los cambios en church_role, estado_vital, o fecha_bautismo."""
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

    # fecha_bautismo (nuevo bautismo)
    if old_fecha_bautismo is None and persona.fecha_bautismo is not None:
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
    row = db.query(models.Persona).filter(models.Persona.id == uuid.UUID(persona_id)).first()
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


# ── Members ────────────────────────────────────────────


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


def search_members(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    spiritual_status: str | None = None,
    family_id: int | None = None,
    sede_id: int | None = None,
    skip: int = 0,
    limit: int = 1000,
    sort_by: str | None = None,
    sort_dir: str = "asc",
):
    query = db.query(models.Persona).options(
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
    if family_id:
        query = query.filter(models.Persona.family_id == family_id)

    # Sorting
    sort_col = _MEMBER_SORT_FIELDS.get(sort_by or "last_name", models.Persona.last_name)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    personas = query.offset(skip).limit(limit).all()

    user_ids = [p.user_id for p in personas if p.user_id]
    progress_map = {}
    if user_ids:
        progress_data = (
            db.query(models.Enrollment.user_id, func.avg(models.Enrollment.progress_percent))
            .filter(models.Enrollment.user_id.in_(user_ids))
            .group_by(models.Enrollment.user_id)
            .all()
        )
        progress_map = {uid: avg for uid, avg in progress_data}

    for p in personas:
        p.spiritual_health = 0.5 + (abs(hash(p.first_name)) % 50) / 100.0
        p.academy_progress = float(progress_map.get(p.user_id, 0.0))

    return personas


def search_members_paginated(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    spiritual_status: str | None = None,
    sede_id: int | None = None,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> dict:
    """Returns { items: [...], total: N } for server-side AG Grid pagination."""
    query = db.query(models.Persona).options(
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

    user_ids = [p.user_id for p in personas if p.user_id]
    progress_map = {}
    if user_ids:
        progress_data = (
            db.query(models.Enrollment.user_id, func.avg(models.Enrollment.progress_percent))
            .filter(models.Enrollment.user_id.in_(user_ids))
            .group_by(models.Enrollment.user_id)
            .all()
        )
        progress_map = {uid: avg for uid, avg in progress_data}

    for p in personas:
        p.spiritual_health = 0.5 + (abs(hash(p.first_name)) % 50) / 100.0
        p.academy_progress = float(progress_map.get(p.user_id, 0.0))

    return {"items": personas, "total": total}


def get_personas(db: Session, search: str | None = None, role: str | None = None):
    return search_members(db, search=search, role=role)


# ── CRM Events ─────────────────────────────────────────


def get_crm_events(db: Session, sede_id: str | None = None, skip: int = 0, limit: int = 100) -> List[models.CrmEvent]:
    q = db.query(models.CrmEvent)
    if sede_id:
        q = q.filter(models.CrmEvent.sede_id == sede_id)
    return q.order_by(models.CrmEvent.event_date.desc()).offset(skip).limit(limit).all()


def create_crm_event(db: Session, payload: schemas.CrmEventCreate) -> models.CrmEvent:
    try:
        payload_data = payload.model_dump()
        role_ids = payload_data.get("target_role_ids") or []
        payload_data["target_role_ids"] = role_ids or None
        if payload_data.get("target_audience") == "ROLE":
            payload_data["target_role_id"] = role_ids[0] if role_ids else payload_data.get("target_role_id")
        else:
            payload_data["target_role_id"] = None
            payload_data["target_role_ids"] = None
        row = models.CrmEvent(**payload_data)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear evento: {str(e)}")


# ── CRM Tasks ──────────────────────────────────────────


def get_crm_tasks(
    db: Session,
    assignee_persona_id: Optional[str] = None,
    persona_id: Optional[str] = None,
) -> List[models.CrmTask]:
    query = db.query(models.CrmTask)
    if assignee_persona_id:
        query = query.filter(models.CrmTask.assignee_id == assignee_persona_id)
    if persona_id:
        query = query.filter(models.CrmTask.persona_id == persona_id)
    return query.order_by(models.CrmTask.due_date.asc()).all()


def create_crm_task(db: Session, payload: schemas.CrmTaskCreate) -> models.CrmTask:
    data = payload.model_dump()
    assignee_identity = data.pop("assignee_id", None)
    data["assignee_id"] = resolve_persona_id_from_identity(db, assignee_identity)
    row = models.CrmTask(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_crm_task(db: Session, task_id: int, payload: schemas.CrmTaskUpdate) -> models.CrmTask:
    row = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_crm_task(db: Session, task_id: int) -> bool:
    row = db.query(models.CrmTask).filter(models.CrmTask.id == task_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Volunteers ─────────────────────────────────────────


def get_volunteer_shifts(db: Session, persona_id: Optional[str] = None) -> List[models.VolunteerShift]:
    query = db.query(models.VolunteerShift)
    if persona_id:
        query = query.filter(models.VolunteerShift.persona_id == persona_id)
    return query.order_by(models.VolunteerShift.shift_start.asc()).all()


def create_volunteer_shift(db: Session, payload: schemas.VolunteerShiftCreate) -> models.VolunteerShift:
    row = models.VolunteerShift(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Event Attendance ───────────────────────────────────


def create_event_attendance(db: Session, payload: schemas.EventAttendanceCreate) -> models.EventAttendance:
    try:
        row = models.EventAttendance(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar asistencia: {str(e)}")


# ── Counseling ─────────────────────────────────────────


def get_counseling_tickets(
    db: Session,
    status: str | None = None,
    persona_id: str | None = None,
    sede_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.CounselingTicket]:
    query = db.query(models.CounselingTicket).filter(models.CounselingTicket.deleted_at.is_(None))
    if sede_id is not None:
        query = query.join(models.Persona, models.CounselingTicket.persona_id == models.Persona.id).filter(
            models.Persona.sede_id == sede_id
        )
    if status:
        query = query.filter(models.CounselingTicket.status == status)
    if persona_id:
        query = query.filter(models.CounselingTicket.persona_id == persona_id)
    tickets = query.order_by(models.CounselingTicket.created_at.desc()).offset(skip).limit(limit).all()

    for t in tickets:
        if t.notes:
            t.notes = decrypt_data(t.notes)

    return tickets


def create_counseling_ticket(db: Session, payload: schemas.CounselingTicketCreate) -> models.CounselingTicket:
    from backend.crud._utils import analyze_pastoral_priority, analyze_pastoral_sentiment

    try:
        data = payload.model_dump()
        pastor_identity = data.pop("pastor_id", None)
        data["pastor_id"] = resolve_persona_id_from_identity(db, pastor_identity)
        raw_notes = data.get("notes", "")

        data["priority_level"] = analyze_pastoral_priority(raw_notes)
        score, label = analyze_pastoral_sentiment(raw_notes)
        data["sentiment_score"] = score
        data["sentiment_label"] = label

        if raw_notes:
            data["notes"] = encrypt_data(raw_notes)

        row = models.CounselingTicket(**data)
        db.add(row)
        db.commit()
        db.refresh(row)

        row.notes = decrypt_data(row.notes)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear ticket de consejería: {str(e)}")


# ── Prayer ─────────────────────────────────────────────


def get_prayer_requests(
    db: Session, status: str | None = None, skip: int = 0, limit: int = 100
) -> List[models.PrayerRequest]:
    query = db.query(models.PrayerRequest)
    if status:
        query = query.filter(models.PrayerRequest.status == status)
    return query.order_by(models.PrayerRequest.created_at.desc()).offset(skip).limit(limit).all()


def create_prayer_request(db: Session, payload: schemas.PrayerRequestCreate) -> models.PrayerRequest:
    try:
        row = models.PrayerRequest(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar petición de oración: {str(e)}")


# ── Grupos ───────────────────────────────────────


def get_cell_groups(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.CellGroup).offset(skip).limit(limit).all()


def _group_member_role_values(item):
    role = str(getattr(item, "role", "") or "participante").strip()
    custom_role_id = getattr(item, "rol_personalizado_id", None)
    if role.startswith("custom:"):
        try:
            custom_role_id = int(role.split(":", 1)[1])
        except (TypeError, ValueError):
            custom_role_id = None
        role = "personalizado"
    return role or "participante", custom_role_id


def create_cell_group(db: Session, payload: schemas.CellGroupCreate, sede_id: str | None = None):
    data = payload.model_dump(exclude={"base_attendee_ids", "base_attendees_with_roles"})
    # Map evangelism_strategy_id -> estrategia_id (CellGroup = GrupoEvangelismo uses estrategia_id)
    if data.get("evangelism_strategy_id") and not data.get("estrategia_id"):
        data["estrategia_id"] = data.pop("evangelism_strategy_id")
    # Infer sede_id from user if not provided in payload
    if sede_id and not data.get("sede_id"):
        data["sede_id"] = sede_id
    if not str(data.get("code") or "").strip():
        base = (str(data.get("name") or data.get("address") or "FARO").strip().upper().replace(" ", "-"))[
            :12
        ]  # truncate to leave room for suffix
        suffix = _utcnow().strftime("%m%d%H%M")  # 8 chars
        data["code"] = f"{base}-{suffix}"[:30]
    if not str(data.get("name") or "").strip():
        fallback_name = str(data.get("address") or data["code"]).strip()
        data["name"] = f"Faro pendiente - {fallback_name}"
    db_obj = models.CellGroup(**data)
    db.add(db_obj)

    base_attendees_with_roles = getattr(payload, "base_attendees_with_roles", None)
    if base_attendees_with_roles is not None:
        db.flush()  # Get the ID without committing
        for item in base_attendees_with_roles:
            role, custom_role_id = _group_member_role_values(item)
            attendee = models.CellGroupMember(
                cell_group_id=db_obj.id,
                persona_id=uuid.UUID(str(item.persona_id)) if isinstance(item.persona_id, str) else item.persona_id,
                role=role,
                rol_personalizado_id=custom_role_id,
            )
            db.add(attendee)
    elif payload.base_attendee_ids:
        db.flush()  # Get the ID without committing
        for persona_id in payload.base_attendee_ids:
            attendee = models.CellGroupMember(cell_group_id=db_obj.id, persona_id=persona_id, role="asistente")
            db.add(attendee)

    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_cell_group(db: Session, house_id: uuid.UUID, payload: schemas.CellGroupUpdate):
    house = db.query(models.CellGroup).filter(models.CellGroup.id == house_id).first()
    if not house:
        return None

    update_data = payload.model_dump(
        exclude_unset=True,
        exclude={"base_attendee_ids", "base_attendees_with_roles"},
    )
    if "code" in update_data and not str(update_data["code"] or "").strip():
        update_data["code"] = house.code or f"FARO-{house.id}"
    for key, value in update_data.items():
        setattr(house, key, value)

    members_updated = False
    if payload.base_attendees_with_roles is not None:
        db.query(models.CellGroupMember).filter(models.CellGroupMember.cell_group_id == house_id).update(
            {models.CellGroupMember.deleted_at: _utcnow(), models.CellGroupMember.activo: False},
            synchronize_session=False,
        )
        for item in payload.base_attendees_with_roles:
            role, custom_role_id = _group_member_role_values(item)
            p_id = uuid.UUID(str(item.persona_id)) if isinstance(item.persona_id, str) else item.persona_id
            existing = db.query(models.CellGroupMember).filter(
                models.CellGroupMember.cell_group_id == house_id,
                models.CellGroupMember.persona_id == p_id
            ).first()
            if existing:
                existing.deleted_at = None
                existing.activo = True
                existing.role = role
                existing.rol_personalizado_id = custom_role_id
            else:
                db.add(
                    models.CellGroupMember(
                        cell_group_id=house_id,
                        persona_id=p_id,
                        role=role,
                        rol_personalizado_id=custom_role_id,
                    )
                )
        members_updated = True
        # Sincronizar lider_persona_id desde el miembro con rol primario de líder
        _SUBORDINATE_TOKENS = {"co", "colider", "colíder", "asistente", "del"}
        db.flush()  # para que los nuevos CellGroupMember tengan IDs asignados
        for item in payload.base_attendees_with_roles:
            role_str = str(getattr(item, "role", "") or "").lower().strip()
            custom_id = getattr(item, "rol_personalizado_id", None)
            # Resolver nombre real: rol base o nombre del rol personalizado
            if role_str.startswith("custom:") and not custom_id:
                try:
                    custom_id = int(role_str.split(":", 1)[1])
                except (ValueError, TypeError):
                    pass
            if custom_id:
                custom_rol = db.query(models.RolPersonalizadoEstrategia).filter(
                    models.RolPersonalizadoEstrategia.id == custom_id
                ).first()
                role_str = (custom_rol.nombre_rol if custom_rol else role_str).lower().strip()
            tokens = set(role_str.replace("-", " ").replace("_", " ").split())
            is_leader = ("lider" in tokens or "líder" in tokens or "leader" in tokens) and not (tokens & _SUBORDINATE_TOKENS)
            if is_leader:
                new_lid = item.persona_id
                house.lider_persona_id = uuid.UUID(str(new_lid)) if isinstance(new_lid, str) else new_lid
                break
        else:
            # No member with leader role → clear the leader
            house.lider_persona_id = None
    elif payload.base_attendee_ids is not None:
        db.query(models.CellGroupMember).filter(models.CellGroupMember.cell_group_id == house_id).update(
            {models.CellGroupMember.deleted_at: _utcnow(), models.CellGroupMember.activo: False},
            synchronize_session=False,
        )
        for persona_id in payload.base_attendee_ids:
            p_id = uuid.UUID(str(persona_id)) if isinstance(persona_id, str) else persona_id
            existing = db.query(models.CellGroupMember).filter(
                models.CellGroupMember.cell_group_id == house_id,
                models.CellGroupMember.persona_id == p_id
            ).first()
            if existing:
                existing.deleted_at = None
                existing.activo = True
                existing.role = "miembro"
            else:
                db.add(
                    models.CellGroupMember(
                        cell_group_id=house_id,
                        persona_id=p_id,
                        role="miembro",
                    )
                )
        members_updated = True

    db.flush()
    house.members_count = (
        db.query(models.CellGroupMember)
        .filter(
            models.CellGroupMember.cell_group_id == house_id,
            models.CellGroupMember.deleted_at.is_(None),
        )
        .count()
    )

    db.commit()
    db.refresh(house)
    return house


# ── Talents & Families ─────────────────────────────────


def get_talents(db: Session, search: str | None = None):
    return search_members(db, search=search)


def get_families(db: Session, skip: int = 0, limit: int = 100):
    families = db.query(models.Family).offset(skip).limit(limit).all()
    for f in families:
        f.members_count = db.query(models.Persona).filter(models.Persona.family_id == f.id).count()
    return families


def create_family(db: Session, name: str):
    fam = models.Family(name=name)
    db.add(fam)
    db.commit()
    db.refresh(fam)
    return fam


# ── Persona Timeline ────────────────────────────────────


def get_persona_timeline(db: Session, persona_id: str):
    persona = db.query(models.Persona).filter(models.Persona.id == uuid.UUID(persona_id)).first()
    if not persona:
        return []

    timeline = []

    timeline.append(
        {
            "type": "membership",
            "title": "Ingreso a la Familia CCF",
            "description": f"Registro formal como {persona.church_role}.",
            "date": persona.created_at.isoformat(),
            "icon": "Sparkles",
            "color": "bg-purple-500",
        }
    )

    if persona.user_id:
        enrollments = db.query(models.Enrollment).filter(models.Enrollment.user_id == persona.user_id).all()
        for en in enrollments:
            timeline.append(
                {
                    "type": "academy",
                    "title": "Inscripción Academia",
                    "description": f"Inició el curso {en.course.title if en.course else 'de formación'}.",
                    "date": en.created_at.isoformat(),
                    "icon": "GraduationCap",
                    "color": "bg-emerald-500",
                }
            )
            if en.certificate_issued:
                timeline.append(
                    {
                        "type": "certificate",
                        "title": "Certificación Obtenida",
                        "description": f"Completó con éxito el curso: {en.course.title if en.course else 'de formación'}.",
                        "date": (en.created_at + dt.timedelta(days=30)).isoformat(),
                        "icon": "Award",
                        "color": "bg-amber-500",
                    }
                )

    ministries = db.query(models.MemberMinistry).filter(models.MemberMinistry.persona_id == persona_id).all()
    for mm in ministries:
        timeline.append(
            {
                "type": "ministry",
                "title": "Vinculación Ministerial",
                "description": f"Se integró al ministerio de {mm.name}.",
                "date": (mm.created_at.isoformat() if mm.created_at else persona.created_at.isoformat()),
                "icon": "ShieldCheck",
                "color": "bg-indigo-600",
            }
        )

    sessions = db.query(models.CounselingTicket).filter(models.CounselingTicket.persona_id == persona_id).all()
    for s in sessions:
        timeline.append(
            {
                "type": "counseling",
                "title": "Sesión Pastoral",
                "description": f"Atención espiritual: {s.subject}.",
                "date": s.created_at.isoformat(),
                "icon": "Heart",
                "color": "bg-rose-500",
            }
        )

    calls = db.query(models.CommunicationLog).filter(models.CommunicationLog.persona_id == persona_id).all()
    for c in calls:
        timeline.append(
            {
                "type": "communication",
                "title": "Seguimiento Pastoral",
                "description": f"Contacto vía {c.channel}: {c.content[:50]}...",
                "date": c.created_at.isoformat(),
                "icon": "Phone",
                "color": "bg-blue-500",
            }
        )

    timeline.sort(key=lambda x: x["date"], reverse=True)
    return timeline


# ── Communication Logs ─────────────────────────────────


def create_communication_log(db: Session, payload: schemas.CommunicationLogCreate):
    data = payload.model_dump()
    leader_identity = data.pop("leader_id", None)
    data["leader_id"] = resolve_persona_id_from_identity(db, leader_identity)
    row = models.CommunicationLog(**{k: v for k, v in data.items()
                                     if hasattr(models.CommunicationLog, k)})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_communication_logs(db: Session, limit: int = 50):
    return db.query(models.CommunicationLog).order_by(models.CommunicationLog.created_at.desc()).limit(limit).all()


# ── Notifications ────────────────────────────────────────


def get_user_notifications(db: Session, user_id: int | str, limit: int = 20) -> List[models.Notification]:
    notification_user_id = resolve_persona_id_for_user(db, user_id)
    if notification_user_id is None:
        return []
    notification_user_key = str(notification_user_id)
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == notification_user_key)
        .order_by(models.Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_notification_as_read(db: Session, notification_id: int):
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notification:
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_notifications_read(db: Session, user_id: int | str):
    notification_user_id = resolve_persona_id_for_user(db, user_id)
    if notification_user_id is None:
        return
    notification_user_key = str(notification_user_id)
    db.query(models.Notification).filter(
        models.Notification.user_id == notification_user_key,
        models.Notification.is_read.is_(False),
    ).update({models.Notification.is_read: True})
    db.commit()


# ── Donations ────────────────────────────────────────────


def create_donation(db: Session, payload: schemas.DonationCreate) -> models.Donation:
    row = models.Donation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_donations(db: Session, skip: int = 0, limit: int = 100) -> List[models.Donation]:
    return (
        db.query(models.Donation)
        .filter(models.Donation.deleted_at.is_(None))
        .order_by(models.Donation.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_total_donations_amount(db: Session) -> float:
    return db.query(func.sum(models.Donation.amount)).scalar() or 0


# ── Spiritual Milestones ─────────────────────────────────


def get_milestones(db: Session, persona_id) -> List[models.SpiritualMilestone]:
    persona_uuid = uuid.UUID(str(persona_id))
    return (
        db.query(models.SpiritualMilestone)
        .filter(
            models.SpiritualMilestone.persona_id == persona_uuid,
            models.SpiritualMilestone.deleted_at.is_(None),
        )
        .order_by(models.SpiritualMilestone.event_date.desc())
        .all()
    )


def create_milestone(
    db: Session,
    persona_id,
    type: str,
    event_date,
    minister_id: Optional[str] = None,
) -> models.SpiritualMilestone:
    persona_uuid = uuid.UUID(str(persona_id))
    minister_uuid = uuid.UUID(str(minister_id)) if minister_id else None
    row = models.SpiritualMilestone(
        persona_id=persona_uuid,
        type=type,
        event_date=event_date,
        minister_id=minister_uuid,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Family Members ──────────────────────────────────────


def get_family_members(db: Session, family_id: int):
    return (
        db.query(models.Persona)
        .filter(models.Persona.family_id == family_id)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )


# ── Support Tickets ─────────────────────────────────────


def create_support_ticket(db: Session, ticket: schemas.SupportTicketCreate) -> models.SupportTicket:
    row = models.SupportTicket(**ticket.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_support_tickets(
    db: Session, user_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100
) -> List[models.SupportTicket]:
    q = db.query(models.SupportTicket).order_by(models.SupportTicket.created_at.desc())
    if user_id is not None:
        q = q.filter(models.SupportTicket.user_id == user_id)
    return q.offset(skip).limit(limit).all()


def update_support_ticket(db: Session, ticket_id: int, new_status: str):
    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not ticket:
        return None
    ticket.status = new_status
    db.commit()
    db.refresh(ticket)
    return ticket


# ── Community Board ─────────────────────────────────────


def get_community_cards(db: Session, column_id: Optional[str] = None) -> List[models.CommunityBoardCard]:
    q = db.query(models.CommunityBoardCard).order_by(models.CommunityBoardCard.position.asc())
    if column_id:
        q = q.filter(models.CommunityBoardCard.column_id == column_id)
    return q.all()


def create_community_card(db: Session, card: schemas.CommunityBoardCardCreate) -> models.CommunityBoardCard:
    max_pos = db.query(func.max(models.CommunityBoardCard.position)).scalar() or 0
    row = models.CommunityBoardCard(**card.model_dump(), position=max_pos + 1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# --- Evangelism Strategies ---
# MOVED to crud/evangelism.py (EstrategiaEvangelismo with UUID PK)


# ── Missing CRUDs ──────────────────────────────────────

# ── Members ─────────────────────────────────────────────


# ── CRM Events ─────────────────────────────────────────


def get_crm_event(db: Session, event_id: int) -> Optional[models.CrmEvent]:
    return db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()


def update_crm_event(db: Session, event_id: int, payload: CrmEventUpdate) -> Optional[models.CrmEvent]:
    row = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_crm_event(db: Session, event_id: int) -> bool:
    row = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


def get_event_attendance(db: Session, event_id: int) -> List[models.EventAttendance]:
    return db.query(models.EventAttendance).filter(models.EventAttendance.event_id == event_id).all()


def delete_event_attendance(db: Session, attendance_id: int) -> bool:
    row = db.query(models.EventAttendance).filter(models.EventAttendance.id == attendance_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Volunteers ─────────────────────────────────────────


def get_volunteer_shift(db: Session, shift_id: int) -> Optional[models.VolunteerShift]:
    return db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id).first()


def update_volunteer_shift(
    db: Session, shift_id: int, payload: schemas.VolunteerShiftUpdate
) -> Optional[models.VolunteerShift]:
    row = db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_volunteer_shift(db: Session, shift_id: int) -> bool:
    row = db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Counseling ─────────────────────────────────────────


def get_counseling_ticket(db: Session, ticket_id: int) -> Optional[models.CounselingTicket]:
    row = (
        db.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.id == ticket_id,
            models.CounselingTicket.deleted_at.is_(None),
        )
        .first()
    )
    if row and row.notes:
        row.notes = decrypt_data(row.notes)
    return row


def update_counseling_ticket(
    db: Session, ticket_id: int, payload: schemas.CounselingTicketUpdate
) -> Optional[models.CounselingTicket]:
    row = db.query(models.CounselingTicket).filter(models.CounselingTicket.id == ticket_id).first()
    if not row:
        return None
    data = payload.model_dump(exclude_unset=True)
    if "pastor_id" in data:
        pastor_identity = data.pop("pastor_id")
        row.pastor_id = resolve_persona_id_from_identity(db, pastor_identity)
    for key, value in data.items():
        if key == "notes" and value:
            setattr(row, key, encrypt_data(value))
        else:
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    if row.notes:
        row.notes = decrypt_data(row.notes)
    return row


def delete_counseling_ticket(db: Session, ticket_id: int) -> bool:
    row = (
        db.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.id == ticket_id,
            models.CounselingTicket.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Prayer ─────────────────────────────────────────────


def get_prayer_request(db: Session, request_id: int) -> Optional[models.PrayerRequest]:
    return db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()


def update_prayer_request(
    db: Session, request_id: int, payload: schemas.PrayerRequestUpdate
) -> Optional[models.PrayerRequest]:
    row = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_prayer_request(db: Session, request_id: int) -> bool:
    row = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Grupos ───────────────────────────────────────


def get_cell_group(db: Session, house_id: uuid.UUID) -> Optional[models.CellGroup]:
    return db.query(models.CellGroup).filter(models.CellGroup.id == house_id).first()


def delete_cell_group(db: Session, house_id: uuid.UUID) -> bool:
    row = db.query(models.CellGroup).filter(models.CellGroup.id == house_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Families ───────────────────────────────────────────


def get_family(db: Session, family_id: int) -> Optional[models.Family]:
    return db.query(models.Family).filter(models.Family.id == family_id).first()


def update_family(db: Session, family_id: int, name: str) -> Optional[models.Family]:
    row = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not row:
        return None
    row.name = name
    db.commit()
    db.refresh(row)
    return row


def delete_family(db: Session, family_id: int) -> bool:
    row = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Consolidation ──────────────────────────────────────


def _emit_mesh_event(event_type: str, case_id: str, persona_id: str | None = None, extra: dict | None = None) -> None:
    """Emite un evento asíncrono al motor Mesh vía Redis PubSub.

    No bloquea el request HTTP. El motor Mesh consume estos eventos para
    calcular SLAs, asignar alertas Overdue, y actualizar dashboards en tiempo real.
    """
    try:
        from backend.core.cache import get_redis
        from backend.core.config import get_settings
        import json

        redis_client = get_redis()
        if redis_client is None:
            return

        settings = get_settings()
        channel = f"{settings.environment}:ws"
        payload = {
            "event": event_type,
            "case_id": case_id,
            "persona_id": persona_id,
            "timestamp": _utcnow().isoformat(),
            **(extra or {}),
        }
        redis_client.publish(channel, json.dumps(payload, default=str))
    except Exception:
        pass  # Fire-and-forget: no bloquear el request si Redis no está disponible


# ── Communication Logs ─────────────────────────────────


def get_communication_log(db: Session, log_id: int) -> Optional[models.CommunicationLog]:
    return db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()


def update_communication_log(
    db: Session, log_id: int, payload: CommunicationLogUpdate
) -> Optional[models.CommunicationLog]:
    row = db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_communication_log(db: Session, log_id: int) -> bool:
    row = db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Donations ───────────────────────────────────────────


def get_donation(db: Session, donation_id: int) -> Optional[models.Donation]:
    return (
        db.query(models.Donation)
        .filter(
            models.Donation.id == donation_id,
            models.Donation.deleted_at.is_(None),
        )
        .first()
    )


def update_donation(db: Session, donation_id: int, payload: schemas.DonationUpdate) -> Optional[models.Donation]:
    row = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_donation(db: Session, donation_id: int) -> bool:
    row = (
        db.query(models.Donation)
        .filter(
            models.Donation.id == donation_id,
            models.Donation.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Spiritual Milestones ─────────────────────────────────


def update_milestone(db: Session, milestone_id: int, **kwargs) -> Optional[models.SpiritualMilestone]:
    row = db.query(models.SpiritualMilestone).filter(models.SpiritualMilestone.id == milestone_id).first()
    if not row:
        return None
    for key, value in kwargs.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_milestone(db: Session, milestone_id: int) -> bool:
    row = (
        db.query(models.SpiritualMilestone)
        .filter(
            models.SpiritualMilestone.id == milestone_id,
            models.SpiritualMilestone.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Support Tickets ─────────────────────────────────────


def get_support_ticket(db: Session, ticket_id: int) -> Optional[models.SupportTicket]:
    return db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()


def delete_support_ticket(db: Session, ticket_id: int) -> bool:
    row = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Community Board ─────────────────────────────────────


def get_community_card(db: Session, card_id: int) -> Optional[models.CommunityBoardCard]:
    return db.query(models.CommunityBoardCard).filter(models.CommunityBoardCard.id == card_id).first()


def update_community_card(
    db: Session, card_id: int, payload: CommunityBoardCardUpdate
) -> Optional[models.CommunityBoardCard]:
    row = db.query(models.CommunityBoardCard).filter(models.CommunityBoardCard.id == card_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_community_card(db: Session, card_id: int) -> bool:
    row = db.query(models.CommunityBoardCard).filter(models.CommunityBoardCard.id == card_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Consolidation Cases ─────────────────────────────────


def get_consolidation_case(db: Session, case_id: str):
    return db.query(models.CasoCRM).filter(models.CasoCRM.id == case_id).first()


def create_consolidation_case(db: Session, payload: schemas.CasoCRMCreate) -> models.CasoCRM:
    row = models.CasoCRM(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    _emit_mesh_event(
        "consolidation.case.created",
        str(row.id),
        persona_id=str(row.persona_id) if row.persona_id else None,
        extra={"status": row.status},
    )
    return row


def update_consolidation_case(db: Session, case_id: str, payload: schemas.CasoCRMUpdate) -> Optional[models.CasoCRM]:
    row = db.query(models.CasoCRM).filter(models.CasoCRM.id == case_id).first()
    if not row:
        return None
    old_status = row.status
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    if old_status != row.status:
        _emit_mesh_event(
            "consolidation.case.updated",
            str(row.id),
            persona_id=str(row.persona_id) if row.persona_id else None,
            extra={"old_status": old_status, "new_status": row.status},
        )
    return row


def delete_consolidation_case(db: Session, case_id: str) -> bool:
    row = db.query(models.CasoCRM).filter(models.CasoCRM.id == case_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Evangelism Strategies ──────────────────────────────────────────────
# MOVED to crud/evangelism.py (EstrategiaEvangelismo with UUID PK)

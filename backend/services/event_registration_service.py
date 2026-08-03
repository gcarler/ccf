"""Servicio de pre-registro a eventos masivos (plan_de_preregistro).

Centraliza la lógica de negocio de EventRegistration: validaciones de aforo,
lista de espera, generación de QR/verify tokens, promoción automática de
waitlist al cancelar, envío de email de confirmación con QR.

Axioma 3 (Multi-Tenant): no añade ``sede_id`` a ``EventRegistration`` — el
scope se hereda vía JOIN ``event_registrations.event_id → crm_events.sede_id``.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import logging
import os
import secrets
import uuid
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas

log = logging.getLogger(__name__)

QR_PREFIX = "CCF-EVT-"
VERIFY_PREFIX = "CCF-VER-"
CANCEL_PREFIX = "CCF-CXL-"
QR_EXPIRY_DAYS = 365
VERIFY_EXPIRY_HOURS = 24

REGISTRATION_STATUS = {
    "PENDING": "PENDING",
    "CONFIRMED": "CONFIRMED",
    "CHECKED_IN": "CHECKED_IN",
    "ABSENT": "ABSENT",
    "WAITLIST": "WAITLIST",
    "CANCELLED": "CANCELLED",
}


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _as_utc(value) -> _dt.datetime:
    if value is None:
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=_dt.timezone.utc)
    return value


def generate_qr_token(event_id, persona_id) -> Tuple[str, str]:
    secret = secrets.token_hex(16)
    token = f"{QR_PREFIX}{event_id}-{persona_id}-{secret}"
    return token, hashlib.sha256(secret.encode()).hexdigest()


def generate_verify_token(registration_id) -> Tuple[str, str]:
    secret = secrets.token_hex(16)
    token = f"{VERIFY_PREFIX}{registration_id}-{secret}"
    return token, hashlib.sha256(secret.encode()).hexdigest()


def hash_token(token: str) -> str:
    if "-" not in token:
        return ""
    return hashlib.sha256(token.rsplit("-", 1)[1].encode()).hexdigest()


def is_qr_token_expired(reg: models.EventRegistration) -> bool:
    if not reg.qr_generated_at:
        return True
    return _as_utc(reg.qr_generated_at) + _dt.timedelta(days=QR_EXPIRY_DAYS) < _utcnow()


def upsert_persona(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    sede_id=None,
) -> models.Persona:
    from sqlalchemy import or_

    persona = None
    conditions = []
    if email:
        conditions.append(models.Persona.email == email)
    if phone:
        conditions.append(models.Persona.phone == phone)
    if conditions:
        persona = db.query(models.Persona).filter(or_(*conditions)).first()
    if persona is None:
        persona = models.Persona(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            sede_id=sede_id,
            church_role="Visitante",
            spiritual_status="Nuevo",
        )
        db.add(persona)
        db.flush()
    return persona


class RegistrationError(Exception):
    def __init__(self, code: str, detail: str, status_code: int = 409):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def assert_registration_window_open(event: models.CrmEvent, now=None):
    now = now or _utcnow()
    if not event.requires_registration:
        return
    if event.status and event.status.upper() in {"CANCELLED", "CANCELED"}:
        raise RegistrationError("EVENT_CANCELLED", "El evento está cancelado", 410)
    opens = _as_utc(event.registration_opens_at)
    closes = _as_utc(event.registration_closes_at)
    if opens and now < opens:
        raise RegistrationError("NOT_YET_OPEN", "La inscripción aún no está abierta", 409)
    if closes and now > closes:
        raise RegistrationError("REGISTRATION_CLOSED", "La inscripción ya cerró", 410)


def count_active_registrations(db: Session, event_id) -> Tuple[int, int]:
    counts = (
        db.query(models.EventRegistration.registration_status, func.count().label("n"))
        .filter(
            models.EventRegistration.event_id == event_id,
            models.EventRegistration.deleted_at.is_(None),
        )
        .group_by(models.EventRegistration.registration_status)
        .all()
    )
    by_status = {row[0]: row[1] for row in counts}
    return (
        int(by_status.get("CONFIRMED", 0)) + int(by_status.get("CHECKED_IN", 0)),
        int(by_status.get("WAITLIST", 0)),
    )


def capacity_remaining(db: Session, event: models.CrmEvent) -> Optional[int]:
    if event.capacity_max is None:
        return None
    slots_taken, _ = count_active_registrations(db, event.id)
    return max(0, event.capacity_max - slots_taken)


def _event_row_lock(db: Session, event: models.CrmEvent):
    return (
        db.query(models.CrmEvent)
        .with_for_update()
        .filter(models.CrmEvent.id == event.id)
        .first()
    )


def _set_event_persona_origin(persona: models.Persona, event: models.CrmEvent) -> None:
    """Conserva el primer origen y añade una etiqueta idempotente por evento."""
    if persona.origen_evento_id is None:
        persona.origen_evento_id = event.id
        persona.origen_fecha = _utcnow()
    tags = list(persona.tags or [])
    event_tag = f"evento:{event.id}"
    if event_tag not in tags:
        tags.append(event_tag)
    if "nuevo_evento" not in tags and persona.origen_evento_id == event.id:
        tags.append("nuevo_evento")
    persona.tags = tags


def _followup_task(db: Session, case, persona: models.Persona, *, attended: bool):
    from backend.models_crm_pipeline import TareaCRM

    title = (
        f"Seguimiento post-evento: {persona.first_name} {persona.last_name}"
        if attended
        else f"Contactar ausente de evento: {persona.first_name} {persona.last_name}"
    )
    existing = (
        db.query(TareaCRM)
        .filter(
            TareaCRM.caso_id == case.id,
            TareaCRM.categoria == "EVENTO",
            TareaCRM.titulo == title,
            TareaCRM.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        return existing
    task = TareaCRM(
        caso_id=case.id,
        persona_id=persona.id,
        titulo=title,
        descripcion=(
            "Agradecer la asistencia y registrar el siguiente paso pastoral."
            if attended
            else "Contactar para conocer la razón de la ausencia y ofrecer seguimiento."
        ),
        categoria="EVENTO",
        estado="pending",
        prioridad="high" if not attended else "medium",
        fecha_vencimiento=_utcnow() + _dt.timedelta(days=2 if attended else 1),
    )
    db.add(task)
    return task


def ensure_event_crm_followup(
    db: Session,
    event: models.CrmEvent,
    persona: models.Persona,
    registration: Optional[models.EventRegistration] = None,
    *,
    attended: bool = False,
    commit: bool = True,
):
    """Asegura origen, caso y tarea de seguimiento para una inscripción.

    La consulta previa + índice único de migración serializa el caso por
    persona/evento. ``commit=False`` permite usarlo dentro del cierre atómico.
    """
    from backend.models_crm_pipeline import CasoCRM
    from backend.services.evangelism_crm_bridge import crear_caso_nuevo_visitante

    _set_event_persona_origin(persona, event)
    case = None
    if registration and registration.crm_case_id:
        case = db.query(CasoCRM).filter(CasoCRM.id == registration.crm_case_id).first()
    if case is None:
        case = (
            db.query(CasoCRM)
            .filter(
                CasoCRM.persona_id == persona.id,
                CasoCRM.origen_evento_id == event.id,
                CasoCRM.deleted_at.is_(None),
            )
            .with_for_update()
            .first()
        )
    if case is None:
        case = crear_caso_nuevo_visitante(
            db,
            persona,
            event.sede_id,
            titulo_prefix=f"Evento: {event.name}",
            origen_evento_id=event.id,
            commit=False,
        )
    if case is not None:
        if registration:
            registration.crm_case_id = case.id
        _followup_task(db, case, persona, attended=attended)
    db.flush()
    if commit:
        db.commit()
        if registration:
            db.refresh(registration)
    return case


def admit_walk_in(
    db: Session,
    event: models.CrmEvent,
    persona: models.Persona,
    *,
    source: str = "walk_in",
) -> models.EventRegistration | None:
    """Admite un walk-in respetando aforo bajo el lock del evento.

    Los eventos ilimitados y sin pre-registro pueden seguir usando solamente
    ``EventAttendance``; cuando hay aforo o pre-registro se crea la inscripción
    CHECKED_IN para que la taquilla y los KPIs compartan la misma fuente.
    """
    if event.capacity_max is None and not event.requires_registration:
        return None
    _event_row_lock(db, event)
    existing = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.persona_id == persona.id,
            models.EventRegistration.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        if existing.registration_status in {"CONFIRMED", "CHECKED_IN"}:
            return existing
        raise RegistrationError(
            "REGISTRATION_NOT_ADMISSIBLE",
            f"La inscripción no puede admitir a la persona (estado: {existing.registration_status})",
            409,
        )
    slots_taken, _ = count_active_registrations(db, event.id)
    if event.capacity_max is not None and slots_taken >= event.capacity_max:
        raise RegistrationError("EVENT_FULL", "El evento alcanzó su aforo máximo", 409)
    registration = models.EventRegistration(
        event_id=event.id,
        persona_id=persona.id,
        registration_status="CHECKED_IN",
        source=source,
        confirmed_at=_utcnow(),
        check_in_at=_utcnow(),
    )
    db.add(registration)
    db.flush()
    return registration


def register(
    db: Session,
    event: models.CrmEvent,
    payload: schemas.PublicEventRegister,
    *,
    public_base_url: str = "",
) -> models.EventRegistration:
    if not event.requires_registration:
        raise RegistrationError("NOT_REGISTRATION_EVENT", "Este evento no requiere pre-inscripción", 403)
    assert_registration_window_open(event)
    _event_row_lock(db, event)
    persona = upsert_persona(
        db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        sede_id=event.sede_id,
    )
    existing = (
        db.query(models.EventRegistration)
        .filter(models.EventRegistration.event_id == event.id, models.EventRegistration.persona_id == persona.id)
        .order_by(models.EventRegistration.created_at.desc())
        .first()
    )
    if existing and existing.registration_status in {"CONFIRMED", "CHECKED_IN", "WAITLIST"}:
        return existing
    slots_taken, waitlist_count = count_active_registrations(db, event.id)
    capacity_full = event.capacity_max is not None and slots_taken >= event.capacity_max
    if capacity_full and not event.waiting_list_enabled:
        raise RegistrationError("EVENT_FULL", "El evento alcanzó su aforo máximo", 409)
    if existing and existing.registration_status == "CANCELLED":
        existing.deleted_at = None
        existing.cancelled_at = None
        existing.qr_token = None
        existing.qr_token_hash = None
        existing.qr_generated_at = None
        existing.confirmed_at = None
        existing.check_in_at = None
        existing.check_out_at = None
        existing.registration_status = "WAITLIST" if capacity_full else ("PENDING" if event.requires_email_verification else "CONFIRMED")
        existing.waiting_list_position = waitlist_count + 1 if capacity_full else None
        extras = dict(existing.extras or {})
        for key in [key for key in extras if key.startswith("_")]:
            extras.pop(key)
        existing.extras = extras
        db.flush()
        reg = existing
    else:
        reg = models.EventRegistration(
            event_id=event.id,
            persona_id=persona.id,
            registration_status="WAITLIST" if capacity_full else ("PENDING" if event.requires_email_verification else "CONFIRMED"),
            waiting_list_position=waitlist_count + 1 if capacity_full else None,
            extras=payload.extras or {},
            source="public_form",
        )
        db.add(reg)
        db.flush()
    if reg.registration_status == "CONFIRMED":
        reg.confirmed_at = _utcnow()
        qr_token_plain = _issue_qr(db, reg)
        cancel_token_plain = _issue_cancel_token(db, reg)
    else:
        qr_token_plain = cancel_token_plain = None
    db.commit()
    db.refresh(reg)
    try:
        ensure_event_crm_followup(db, event, persona, reg)
    except Exception:
        db.rollback()
        log.exception("CRM follow-up failed for event registration %s", reg.id)
    if reg.registration_status == "CONFIRMED":
        _send_confirmation_email(db, event, reg, persona, public_base_url, qr_token_plain=qr_token_plain, cancel_token_plain=cancel_token_plain)
    elif reg.registration_status == "PENDING":
        verify_token, _ = generate_verify_token(reg.id)
        extras = dict(reg.extras or {})
        extras["_verify_token_hash"] = hash_token(verify_token)
        extras["_verify_expires_at"] = (_utcnow() + _dt.timedelta(hours=VERIFY_EXPIRY_HOURS)).isoformat()
        reg.extras = extras
        db.commit()
        db.refresh(reg)
        _send_verification_email(db, event, reg, persona, public_base_url, verify_token)
    return reg


def _issue_qr(db: Session, reg: models.EventRegistration) -> str:
    token, token_hash = generate_qr_token(reg.event_id, reg.persona_id)
    reg.qr_token_hash = token_hash
    reg.qr_generated_at = _utcnow()
    reg._qr_token_transient = token
    db.flush()
    return token


def _issue_cancel_token(db: Session, reg: models.EventRegistration) -> str:
    secret = secrets.token_hex(16)
    cancel_token = f"{CANCEL_PREFIX}{reg.id}-{secret}"
    extras = dict(reg.extras or {})
    extras["_cancel_token_hash"] = hashlib.sha256(secret.encode()).hexdigest()
    reg.extras = extras
    reg._cancel_token_transient = cancel_token
    db.flush()
    return cancel_token


def _send_confirmation_email(db, event, reg, persona, public_base_url, *, qr_token_plain=None, cancel_token_plain=None):
    if not persona.email:
        return
    try:
        from html import escape
        from backend.services.email import send_email
        cancel_param = f"&cancel={cancel_token_plain}" if cancel_token_plain else ""
        qr_link = f"{public_base_url}/public/events/{event.id}/qr?token={qr_token_plain}{cancel_param}" if qr_token_plain else ""
        cancel_link = f"{public_base_url}/public/events/{event.id}/cancel?token={cancel_token_plain}" if cancel_token_plain else ""
        event_date_str = event.event_date.strftime("%d/%m/%Y %H:%M") if event.event_date else "Por confirmar"
        html = f"<h2>¡Inscripción confirmada: {escape(event.name)}!</h2><p>Hola <strong>{escape(persona.first_name or '')}</strong>,</p><p>Fecha: {escape(event_date_str)}</p>{f'<p>Tu QR: <a href=\"{escape(qr_link)}\">ver ticket</a></p>' if qr_link else ''}{f'<p><a href=\"{escape(cancel_link)}\">Cancelar inscripción</a></p>' if cancel_link else ''}"
        send_email(to=persona.email, subject=f"Confirmación: {event.name}", html=html)
    except Exception as exc:
        log.warning("Failed to send confirmation email for registration %s: %s", reg.id, exc)


def _send_verification_email(db, event, reg, persona, public_base_url, verify_token):
    if not persona.email:
        return
    try:
        from html import escape
        from backend.services.email import send_email
        verify_url = f"{public_base_url}/public/events/{event.id}/verify?token={verify_token}"
        html = f"<h2>Verifica tu inscripción: {escape(event.name)}</h2><p><a href=\"{escape(verify_url)}\">Verificar inscripción</a></p>"
        send_email(to=persona.email, subject=f"Verifica tu inscripción: {event.name}", html=html)
    except Exception as exc:
        log.warning("Failed to send verification email for registration %s: %s", reg.id, exc)


def verify(db: Session, event: models.CrmEvent, token: str, *, public_base_url: str = "") -> models.EventRegistration:
    if not token.startswith(VERIFY_PREFIX):
        raise RegistrationError("INVALID_TOKEN", "Token de verificación inválido", 400)
    payload = token.removeprefix(VERIFY_PREFIX)
    if "-" not in payload:
        raise RegistrationError("INVALID_TOKEN", "Token malformado", 400)
    try:
        reg_id = uuid.UUID(payload.rsplit("-", 1)[0])
    except (ValueError, TypeError):
        raise RegistrationError("INVALID_TOKEN", "Token malformado", 400) from None
    reg = db.query(models.EventRegistration).filter(models.EventRegistration.id == reg_id).first()
    if not reg or reg.event_id != event.id or reg.deleted_at is not None:
        raise RegistrationError("NOT_FOUND", "Inscripción no encontrada", 404)
    stored_hash = (reg.extras or {}).get("_verify_token_hash")
    if not stored_hash or not secrets.compare_digest(hash_token(token), stored_hash):
        raise RegistrationError("INVALID_TOKEN", "Token inválido", 403)
    expires_at_str = (reg.extras or {}).get("_verify_expires_at")
    if not expires_at_str:
        raise RegistrationError("INVALID_TOKEN", "Token sin expiración", 403)
    try:
        expires_at = _as_utc(_dt.datetime.fromisoformat(expires_at_str))
    except (ValueError, TypeError):
        raise RegistrationError("INVALID_TOKEN", "Expiración malformada", 403) from None
    if expires_at < _utcnow():
        raise RegistrationError("TOKEN_EXPIRED", "Token expirado", 403)
    if reg.registration_status != "PENDING":
        return reg
    _event_row_lock(db, event)
    slots_taken, _ = count_active_registrations(db, event.id)
    capacity_full = event.capacity_max is not None and slots_taken >= event.capacity_max
    if capacity_full and not event.waiting_list_enabled:
        raise RegistrationError("EVENT_FULL", "El evento se llenó antes de tu verificación", 409)
    qr_token_plain = cancel_token_plain = None
    if capacity_full:
        reg.registration_status = "WAITLIST"
        reg.waiting_list_position = reg.waiting_list_position or 0
    else:
        reg.registration_status = "CONFIRMED"
        reg.confirmed_at = _utcnow()
        qr_token_plain = _issue_qr(db, reg)
        cancel_token_plain = _issue_cancel_token(db, reg)
    extras = dict(reg.extras or {})
    extras.pop("_verify_token_hash", None)
    extras.pop("_verify_expires_at", None)
    reg.extras = extras
    db.commit()
    db.refresh(reg)
    if reg.registration_status == "CONFIRMED":
        try:
            ensure_event_crm_followup(db, event, reg.persona, reg)
        except Exception:
            db.rollback()
            log.exception("CRM follow-up failed while verifying registration %s", reg.id)
        _send_confirmation_email(db, event, reg, reg.persona, public_base_url, qr_token_plain=qr_token_plain, cancel_token_plain=cancel_token_plain)
    return reg


def cancel(db: Session, event: models.CrmEvent, reg: models.EventRegistration) -> models.EventRegistration:
    if reg.registration_status == "CANCELLED":
        return reg
    _event_row_lock(db, event)
    was_confirmed_or_checked_in = reg.registration_status in {"CONFIRMED", "CHECKED_IN"}
    reg.registration_status = "CANCELLED"
    reg.cancelled_at = _utcnow()
    reg.deleted_at = _utcnow()
    reg.waiting_list_position = None
    db.flush()
    if was_confirmed_or_checked_in:
        _promote_first_waitlist(db, event)
    db.commit()
    db.refresh(reg)
    return reg


def _promote_first_waitlist(db: Session, event: models.CrmEvent) -> None:
    next_in_line = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.registration_status == "WAITLIST",
            models.EventRegistration.deleted_at.is_(None),
        )
        .order_by(models.EventRegistration.waiting_list_position.asc())
        .first()
    )
    if not next_in_line:
        return
    next_in_line.registration_status = "CONFIRMED"
    next_in_line.confirmed_at = _utcnow()
    next_in_line.waiting_list_position = None
    qr_token_plain = _issue_qr(db, next_in_line)
    cancel_token_plain = _issue_cancel_token(db, next_in_line)
    remaining = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.registration_status == "WAITLIST",
            models.EventRegistration.deleted_at.is_(None),
        )
        .order_by(models.EventRegistration.waiting_list_position.asc())
        .all()
    )
    for idx, row in enumerate(remaining, start=1):
        row.waiting_list_position = idx
    try:
        if next_in_line.persona and next_in_line.persona.email:
            from html import escape
            from backend.services.email import send_email
            public_base_url = os.environ.get("CCF_PUBLIC_BASE_URL", "https://ccf.co")
            qr_link = f"{public_base_url}/public/events/{event.id}/qr?token={qr_token_plain}"
            if cancel_token_plain:
                qr_link += f"&cancel={cancel_token_plain}"
            html = f"<h2>¡Tu inscripción a {escape(event.name)} fue confirmada!</h2><p>Tu QR: <a href=\"{escape(qr_link)}\">ver ticket</a></p>"
            send_email(to=next_in_line.persona.email, subject=f"Cupo confirmado: {event.name}", html=html)
    except Exception as exc:
        log.warning("Failed to send promotion email for reg %s: %s", next_in_line.id, exc)


def find_by_email_or_phone(db: Session, event_id, email: Optional[str] = None, phone: Optional[str] = None) -> Optional[models.EventRegistration]:
    if not email and not phone:
        return None
    from sqlalchemy import or_
    q = (
        db.query(models.EventRegistration)
        .join(models.Persona, models.EventRegistration.persona_id == models.Persona.id)
        .filter(models.EventRegistration.event_id == event_id, models.EventRegistration.deleted_at.is_(None))
    )
    conditions = []
    if email:
        conditions.append(models.Persona.email == email)
    if phone:
        conditions.append(models.Persona.phone == phone)
    return q.filter(or_(*conditions)).order_by(models.EventRegistration.created_at.desc()).first()


def is_event_open_for_registration(event: models.CrmEvent, now=None) -> bool:
    now = now or _utcnow()
    if not event.requires_registration:
        return False
    if event.status and event.status.upper() in {"CANCELLED", "CANCELED"}:
        return False
    opens = _as_utc(event.registration_opens_at)
    closes = _as_utc(event.registration_closes_at)
    if opens and now < opens:
        return False
    if closes and now > closes:
        return False
    return True


def close_event_attendance(
    db: Session,
    event: models.CrmEvent,
    *,
    session_date: Optional[_dt.date] = None,
    closed_by=None,
):
    """Cierra una vez la taquilla lógica y marca ausentes de forma atómica."""
    _event_row_lock(db, event)
    if event.attendance_closed_at is not None:
        return {"closed": True, "idempotent": True, "absent": 0, "event_id": str(event.id)}
    session_date = session_date or (_as_utc(event.event_date).date() if event.event_date else _utcnow().date())
    registrations = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.registration_status == "CONFIRMED",
            models.EventRegistration.deleted_at.is_(None),
        )
        .with_for_update()
        .all()
    )
    absent = 0
    for registration in registrations:
        if registration.check_in_at is not None:
            continue
        registration.registration_status = "ABSENT"
        extras = dict(registration.extras or {})
        extras["_last_status_change"] = {
            "from": "CONFIRMED",
            "to": "ABSENT",
            "at": _utcnow().isoformat(),
            "reason": "attendance_closed",
        }
        registration.extras = extras
        ensure_event_crm_followup(
            db,
            event,
            registration.persona,
            registration,
            attended=False,
            commit=False,
        )
        absent += 1
    event.attendance_closed_at = _utcnow()
    event.attendance_closed_by = closed_by
    db.flush()
    db.commit()
    return {"closed": True, "idempotent": False, "absent": absent, "event_id": str(event.id), "session_date": session_date.isoformat()}

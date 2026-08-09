from __future__ import annotations

import datetime
import hashlib
import logging
import secrets
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.api.evangelism_events._shared import require_event_access
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_edit
from backend.core.tenant import require_user_sede_id

router = APIRouter()
logger = logging.getLogger(__name__)


class VisitorCreate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None


@router.post("/events/{event_id}/sessions/{session_date}/visitors")
def fast_checkin_visitor(
    event_id: UUID,
    session_date: str,
    visitor: VisitorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    event = require_event_access(db, current_user, event_id)
    user_sede_id = require_user_sede_id(db, current_user)

    try:
        session_day = datetime.datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

    role_name = "Visitante Servicios"
    role = db.query(models.RoleDefinition).filter(models.RoleDefinition.name == role_name).first()
    if not role:
        role = models.RoleDefinition(name=role_name, is_system_locked=True)
        db.add(role)
        db.commit()
        db.refresh(role)

    attendance_lookup = (
        db.query(models.EventAttendance)
        .join(models.Persona)
        .filter(
            models.EventAttendance.event_id == event_id,
            models.EventAttendance.session_date == session_day,
        )
    )
    identifiers = []
    if visitor.email:
        identifiers.append(models.Persona.email == visitor.email)
    if visitor.phone:
        identifiers.append(models.Persona.phone == visitor.phone)
    if identifiers and attendance_lookup.filter(or_(*identifiers)).first():
        existing_attendance = attendance_lookup.filter(or_(*identifiers)).first()
        return {
            "status": "success",
            "visitor_id": existing_attendance.persona_id,
            "message": "Visitante ya registrado. Asistencia actualizada.",
            "is_duplicate": True,
        }

    existing_persona = None
    if visitor.email:
        candidate = db.query(models.Persona).filter(models.Persona.email == visitor.email).first()
        if candidate and str(candidate.sede_id) == str(user_sede_id):
            existing_persona = candidate
    if not existing_persona and visitor.phone:
        candidate = db.query(models.Persona).filter(models.Persona.phone == visitor.phone).first()
        if candidate and str(candidate.sede_id) == str(user_sede_id):
            existing_persona = candidate

    if existing_persona:
        new_visitor = existing_persona
        is_new_visitor = False
    else:
        is_new_visitor = True
        sede_id = event.sede_id or user_sede_id
        new_visitor = models.Persona(
            first_name=visitor.first_name,
            last_name=visitor.last_name,
            phone=visitor.phone,
            email=visitor.email,
            sede_id=sede_id,
            church_role=role_name,
        )
        db.add(new_visitor)
        db.commit()
        db.refresh(new_visitor)

    # La idempotencia es de asistencia, no de persona: un miembro ya existente
    # puede asistir por primera vez a esta sesión.
    if is_new_visitor and role:
        db.add(models.PersonaRoleLink(persona_id=new_visitor.id, role_id=role.id))

    attendance = models.EventAttendance(
        event_id=event_id,
        session_date=session_day,
        persona_id=new_visitor.id,
        attended=True,
    )
    db.add(attendance)
    # Persist the core check-in before the optional CRM bridge. A bridge
    # integration failure must never make a successful attendance disappear.
    db.commit()

    # Create CRM follow-up records for new visitors.
    # This is auxiliary: if the CRM bridge is temporarily out of sync with
    # production schema, we keep the visitor registration successful.
    from backend.services.evangelism_crm_bridge import crear_caso_nuevo_visitante

    if is_new_visitor:
        try:
            crear_caso_nuevo_visitante(db, new_visitor, new_visitor.sede_id)
        except Exception as exc:
            logger.warning("Failed to create CRM follow-up for evangelism event visitor %s: %s", new_visitor.id, exc)

    return {
        "status": "success",
        "visitor_id": new_visitor.id,
        "message": "Visitante registrado y marcado como presente",
        "is_duplicate": False,
    }


# =============================================================================
# CHECK-IN UNIFICADO (plan_de_preregistro, Fase 4)
# =============================================================================


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _qr_token_secret_hash(qr_token: str) -> str:
    """Reusa el patrón de ``event_registration_service.hash_token``."""
    if "-" not in qr_token:
        return ""
    secret = qr_token.rsplit("-", 1)[1]
    return hashlib.sha256(secret.encode()).hexdigest()


def _parse_evt_qr_payload(payload_str: str):
    """Parsea ``{event_uuid}-{persona_uuid}-{secret}`` de un QR ``CCF-EVT-``.

    Los UUID contienen guiones, así que NO se puede ``split("-", N)`` (truncaría
    el primer UUID a su primer bloque). Los UUIDs son de 36 chars fijos:
    evento [0:36], dash [36], persona [37:73], dash [73], secret [74:].
    """
    if len(payload_str) < 74:
        return None
    try:
        event_uuid = UUID(payload_str[:36])
        persona_uuid = UUID(payload_str[37:73])
    except (ValueError, TypeError):
        return None
    return event_uuid, persona_uuid


def _parse_per_qr_payload(payload_str: str):
    """Parsea ``{persona_uuid}-{secret}`` de un QR ``CCF-PER-`` (UUID fijo 36)."""
    if len(payload_str) < 37:
        return None
    try:
        persona_uuid = UUID(payload_str[:36])
    except (ValueError, TypeError):
        return None
    return persona_uuid


def _upsert_attendance(
    db: Session,
    event_id: UUID,
    session_date: datetime.date,
    persona_id: UUID,
    *,
    source: str = "qr",
    role_at_event: Optional[str] = None,
) -> tuple[models.EventAttendance, bool]:
    """Crea o actualiza EventAttendance(event_id, session_date, persona_id) attended=True.

    ``role_at_event`` (plan_clasificador_contextual) persiste el rol contextual
    de la inscripción en la asistencia del día del evento.

    Returns (attendance, was_created). Idempotente por la UNIQUE constraint
    ``uq_event_attendance`` (``models_crm.py:143``).
    """
    existing = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event_id,
            models.EventAttendance.session_date == session_date,
            models.EventAttendance.persona_id == persona_id,
        )
        .first()
    )
    now = _utcnow()
    if existing:
        existing.attended = True
        existing.status = "present"
        existing.source = source
        if role_at_event:
            existing.role_at_event = role_at_event
        existing.scanned_at = now
        existing.check_in_at = now or existing.check_in_at
        return existing, False
    attendance = models.EventAttendance(
        event_id=event_id,
        session_date=session_date,
        persona_id=persona_id,
        attended=True,
        status="present",
        source=source,
        role_at_event=role_at_event or "attendee",
        scanned_at=now,
        check_in_at=now,
    )
    db.add(attendance)
    return attendance, True


@router.post("/events/{event_id}/sessions/{session_date}/checkin", response_model=dict)
def unified_checkin(
    event_id: UUID,
    session_date: str,
    payload: schemas.CheckinPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Check-in unificado: QR de EventRegistration (``CCF-EVT-``), QR de Persona
    (``CCF-PER-``), ``persona_id`` manual, o walk-in (first_name + last_name).

    Idempotente: si la persona ya tiene EventAttendance(attended=True) para esta
    sesión, retorna ``is_duplicate=True`` (no crea filas nuevas).
    """
    event = require_event_access(db, current_user, event_id)

    if str(event.status or "").upper() in {"CANCELLED", "CANCELED"}:
        raise HTTPException(status_code=409, detail="No se puede hacer check-in en eventos cancelados")

    try:
        session_day = datetime.datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, esperado YYYY-MM-DD")

    persona: Optional[models.Persona] = None
    registration: Optional[models.EventRegistration] = None
    source = "manual"
    qr_kind: Optional[str] = None

    if payload.qr_token:
        token = payload.qr_token.strip()
        if token.startswith("CCF-EVT-"):
            qr_kind = "CCF-EVT"
            source = "qr_event_registration"
            payload_str = token.removeprefix("CCF-EVT-")
            parsed = _parse_evt_qr_payload(payload_str)
            if parsed is None:
                raise HTTPException(status_code=400, detail="QR malformado")
            event_uuid, persona_uuid = parsed

            reg = (
                db.query(models.EventRegistration)
                .filter(
                    models.EventRegistration.event_id == event_uuid,
                    models.EventRegistration.persona_id == persona_uuid,
                    models.EventRegistration.deleted_at.is_(None),
                )
                .first()
            )
            if not reg:
                raise HTTPException(status_code=404, detail="Inscripción no encontrada")
            # Validar solo contra el hash persistido (fix seguridad #2 + timing attack #12):
            # el token plano nunca se persiste; comparaci\u00f3n de hashes con
            # secrets.compare_digest evita timing attacks.
            token_hash = _qr_token_secret_hash(token)
            if not token_hash or not secrets.compare_digest(str(reg.qr_token_hash or ""), token_hash):
                raise HTTPException(status_code=403, detail="QR inv\u00e1lido")
            if reg.registration_status not in {"CONFIRMED", "CHECKED_IN"}:
                raise HTTPException(
                    status_code=409,
                    detail=f"Inscripción no confirmada (estado: {reg.registration_status})",
                )
            registration = reg
            persona = reg.persona

        elif token.startswith("CCF-PER-"):
            qr_kind = "CCF-PER"
            source = "qr_persona"
            # Reuso del scanner existente (evangelism.py:84) que valida hash+expiry.
            from backend.api.evangelism import _get_scoped_scanner_persona

            payload_str = token.removeprefix("CCF-PER-")
            parsed = _parse_per_qr_payload(payload_str)
            if parsed is None:
                raise HTTPException(status_code=400, detail="QR malformado")
            persona_id = parsed
            persona = _get_scoped_scanner_persona(persona_id, db, current_user)
            # Validar hash + expiry alineado con evangelism.py:105-117.
            if not persona.scanner_token_hash:
                raise HTTPException(status_code=403, detail="La persona no tiene token activo")
            expires_at = persona.scanner_token_expires_at
            if expires_at:
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
                if expires_at < _utcnow():
                    raise HTTPException(status_code=403, detail="Token expirado")
            secret = payload_str.rsplit("-", 1)[1] if "-" in payload_str else ""
            computed = hashlib.sha256(secret.encode()).hexdigest()
            if not secrets.compare_digest(computed, persona.scanner_token_hash):
                raise HTTPException(status_code=403, detail="Token de seguridad inválido")
        else:
            raise HTTPException(status_code=400, detail="Prefijo de QR desconocido")

    elif payload.persona_id:
        persona = db.query(models.Persona).filter(models.Persona.id == payload.persona_id).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        # Si el evento requiere pre-registro, validar inscripción CONFIRMED.
        if event.requires_registration:
            reg_existing = (
                db.query(models.EventRegistration)
                .filter(
                    models.EventRegistration.event_id == event.id,
                    models.EventRegistration.persona_id == persona.id,
                    models.EventRegistration.deleted_at.is_(None),
                )
                .first()
            )
            if reg_existing and reg_existing.registration_status not in {"CONFIRMED", "CHECKED_IN"}:
                raise HTTPException(
                    status_code=409,
                    detail=f"Inscripción no confirmada (estado: {reg_existing.registration_status})",
                )
            registration = reg_existing
        source = "manual_persona_id"

    else:
        # Walk-in: first_name + last_name (+ phone opcional)
        if not (payload.first_name and payload.last_name):
            raise HTTPException(status_code=422, detail="Se requiere qr_token, persona_id, o first_name+last_name")
        user_sede_id = require_user_sede_id(db, current_user)
        existing_persona = None
        if payload.email:
            existing_persona = db.query(models.Persona).filter(models.Persona.email == payload.email).first()
        if not existing_persona and payload.phone:
            existing_persona = db.query(models.Persona).filter(models.Persona.phone == payload.phone).first()
        if existing_persona and str(existing_persona.sede_id) == str(user_sede_id):
            persona = existing_persona
        else:
            persona = models.Persona(
                first_name=payload.first_name,
                last_name=payload.last_name,
                phone=payload.phone,
                email=payload.email,
                sede_id=event.sede_id or user_sede_id,
                church_role="Visitante",
                spiritual_status="Nuevo",
            )
            db.add(persona)
            db.flush()
        source = "walk_in"

    # Idempotencia: verificar si ya tiene EventAttendance(attended=True).
    is_duplicate = bool(
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_day,
            models.EventAttendance.persona_id == persona.id,
            models.EventAttendance.attended.is_(True),
        )
        .first()
    )

    attendance, _created = _upsert_attendance(
        db,
        event.id,
        session_day,
        persona.id,
        source=source,
        role_at_event=registration.participant_role_code if registration else None,
    )

    if registration and registration.registration_status != "CHECKED_IN":
        registration.registration_status = "CHECKED_IN"
        registration.check_in_at = _utcnow()
        registration.checked_in_by = current_user.id

    db.commit()
    return {
        "status": "success",
        "is_duplicate": is_duplicate,
        "persona_id": str(persona.id),
        "persona_name": persona.nombre_completo,
        "source": source,
        "qr_kind": qr_kind,
        # plan_clasificador_contextual: rol efectivo + rol persistido en asistencia.
        "participant_role_code": (registration.participant_role_code if registration else None),
        "role_at_event": attendance.role_at_event,
        "checked_in_at": attendance.check_in_at.isoformat() if attendance.check_in_at else None,
    }


@router.post("/events/{event_id}/sessions/{session_date}/ccf-evt-checkin", response_model=dict)
def ccf_evt_checkin(
    event_id: UUID,
    session_date: str,
    payload: schemas.CheckinPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Check-in por QR de inscripción (``CCF-EVT-``) con rol contextual.

    plan_clasificador_contextual §7: el scanner de eventos escanea el QR de la
    inscripción y este endpoint registra la asistencia persistiendo el rol
    contextual de la inscripción en ``role_at_event``. Devuelve
    ``participant_role_code`` (rol efectivo) y ``role_at_event`` (persistido).
    Idempotente: repeticiones retornan ``is_duplicate=True`` sin duplicar.
    """
    event = require_event_access(db, current_user, event_id)

    if str(event.status or "").upper() in {"CANCELLED", "CANCELED"}:
        raise HTTPException(status_code=409, detail="No se puede hacer check-in en eventos cancelados")

    try:
        session_day = datetime.datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, esperado YYYY-MM-DD")

    token = (payload.qr_token or "").strip()
    if not token.startswith("CCF-EVT-"):
        raise HTTPException(status_code=400, detail="Se requiere un QR de inscripción CCF-EVT-")
    payload_str = token.removeprefix("CCF-EVT-")
    parsed = _parse_evt_qr_payload(payload_str)
    if parsed is None:
        raise HTTPException(status_code=400, detail="QR malformado")
    event_uuid, persona_uuid = parsed
    if event_uuid != event.id:
        raise HTTPException(status_code=404, detail="El QR no corresponde a este evento")

    reg = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.persona_id == persona_uuid,
            models.EventRegistration.deleted_at.is_(None),
        )
        .first()
    )
    if not reg:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")

    # Validar solo contra el hash persistido (fix seguridad #2 + timing attack #12).
    token_hash = _qr_token_secret_hash(token)
    if not token_hash or not secrets.compare_digest(str(reg.qr_token_hash or ""), token_hash):
        raise HTTPException(status_code=403, detail="QR inválido")
    if reg.registration_status not in {"CONFIRMED", "CHECKED_IN"}:
        raise HTTPException(
            status_code=409,
            detail=f"Inscripción no confirmada (estado: {reg.registration_status})",
        )

    persona = reg.persona
    is_duplicate = bool(
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_day,
            models.EventAttendance.persona_id == persona.id,
            models.EventAttendance.attended.is_(True),
        )
        .first()
    )

    attendance, _created = _upsert_attendance(
        db,
        event.id,
        session_day,
        persona.id,
        source="qr_event_registration",
        role_at_event=reg.participant_role_code,
    )

    if reg.registration_status != "CHECKED_IN":
        reg.registration_status = "CHECKED_IN"
        reg.check_in_at = _utcnow()
        reg.checked_in_by = current_user.id

    db.commit()
    return {
        "status": "success",
        "is_duplicate": is_duplicate,
        "persona_id": str(persona.id),
        "persona_name": persona.nombre_completo,
        "source": "qr_event_registration",
        # plan_clasificador_contextual: rol efectivo + rol persistido en asistencia.
        "participant_role_code": reg.participant_role_code,
        "role_at_event": attendance.role_at_event,
        "checked_in_at": attendance.check_in_at.isoformat() if attendance.check_in_at else None,
    }


@router.post("/events/{event_id}/sessions/{session_date}/checkout", response_model=dict)
def unified_checkout(
    event_id: UUID,
    session_date: str,
    payload: schemas.CheckoutPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Marca la salida (``check_out_at``) de una persona para la sesión."""
    event = require_event_access(db, current_user, event_id)
    try:
        session_day = datetime.datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, esperado YYYY-MM-DD")

    if not payload.qr_token and not payload.persona_id:
        raise HTTPException(status_code=422, detail="Se requiere qr_token o persona_id")

    persona = None
    if payload.persona_id:
        persona = db.query(models.Persona).filter(models.Persona.id == payload.persona_id).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
    elif payload.qr_token:
        token = payload.qr_token.strip()
        if token.startswith("CCF-EVT-"):
            payload_str = token.removeprefix("CCF-EVT-")
            parsed = _parse_evt_qr_payload(payload_str)
            if parsed is None:
                raise HTTPException(status_code=400, detail="QR malformado")
            _event_uuid, persona_uuid = parsed
            persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
        elif token.startswith("CCF-PER-"):
            payload_str = token.removeprefix("CCF-PER-")
            parsed = _parse_per_qr_payload(payload_str)
            if parsed is None:
                raise HTTPException(status_code=400, detail="QR malformado")
            persona = db.query(models.Persona).filter(models.Persona.id == parsed).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada")

    attendance = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_day,
            models.EventAttendance.persona_id == persona.id,
        )
        .first()
    )
    if not attendance:
        raise HTTPException(status_code=404, detail="No hay check-in previo para esta persona/sesión")
    attendance.check_out_at = _utcnow()
    db.commit()
    return {
        "status": "success",
        "persona_id": str(persona.id),
        "check_out_at": attendance.check_out_at.isoformat(),
    }

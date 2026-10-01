from __future__ import annotations

import datetime
import hashlib
import logging
import secrets
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.api.evangelism_events._shared import (
    _get_persona_for_user,
    require_event_access,
)
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_edit, require_evangelism_read
from backend.core.rate_limit import academy_limiter
from backend.core.tenant import require_user_sede_id
from backend.services.event_registration_service import is_qr_token_expired

router = APIRouter()
logger = logging.getLogger(__name__)


class VisitorCreate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None


class CheckinBatchItem(BaseModel):
    """Elemento individual de un check-in en lote (sincronización offline).

    TKT-EVANGELISM-OFFLINE-SYNC-01: la cola offline del Scanner QR acumula
    credenciales escaneadas sin conexión y las sincroniza en lote. Cada item
    solo admite identidad por QR (``qr_token``) o constatación manual
    (``persona_id``); los walk-ins exigen interacción del operador y no se
    aceptan en modo offline.
    """

    model_config = ConfigDict(extra="forbid")

    qr_token: Optional[str] = None
    persona_id: Optional[UUID] = None

    @model_validator(mode="after")
    def _require_qr_or_persona(self):
        has_qr = bool(self.qr_token and self.qr_token.strip())
        has_persona = self.persona_id is not None
        if not (has_qr or has_persona):
            raise ValueError("Cada item requiere qr_token o persona_id")
        return self


class CheckinBatchPayload(BaseModel):
    """Lote de check-ins diferidos desde la cola offline del Scanner QR.

    Deduplicación por identidad del participante en tres capas:
    1. Cola local (hash de identidad en el cliente, ``offlineQueue.ts``).
    2. Este modelo, que descarta tokens/UUIDs repetidos dentro del lote.
    3. El endpoint, idempotente contra ``EventAttendance`` ya registrada.
    """

    model_config = ConfigDict(extra="forbid")

    items: list[CheckinBatchItem] = Field(..., min_length=1, max_length=200)

    @model_validator(mode="after")
    def _dedupe_items(self):
        seen: set = set()
        unique_items: list[CheckinBatchItem] = []
        for item in self.items:
            key = ("qr", item.qr_token.strip()) if item.qr_token else ("pid", str(item.persona_id))
            if key in seen:
                continue
            seen.add(key)
            unique_items.append(item)
        if not unique_items:
            raise ValueError("El lote no contiene items válidos")
        object.__setattr__(self, "items", unique_items)
        return self


@router.post("/events/{event_id}/sessions/{session_date}/visitors")
@academy_limiter.limit("30/minute")
def fast_checkin_visitor(
    request: Request,
    event_id: UUID,
    session_date: str,
    visitor: VisitorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    require_event_access(db, current_user, event_id)
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
        # Sede del usuario autenticado, NO del evento (que puede estar contaminado).
        # El visitante se asigna a la sede del operador que hace el check-in.
        sede_id = user_sede_id
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

    try:
        from backend.services.event_post_followup_service import enroll_in_post_event_followup

        enroll_in_post_event_followup(
            db=db,
            event=event,
            persona=new_visitor,
            current_user=current_user,
            auto_assign_mentor=True,
        )
        db.commit()
    except Exception as exc:
        logger.warning("Failed to auto-enroll visitor in post-event followup %s: %s", new_visitor.id, exc)

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


def _get_user_display_name(db: Session, user_id) -> str:
    if not user_id:
        return "Operador de Puerta"
    persona = _get_persona_for_user(db, user_id)
    if persona and persona.nombre_completo:
        return persona.nombre_completo
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            return user.username or user.email or str(user.id)
    except Exception:
        pass
    return "Operador de Puerta"


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


@academy_limiter.limit("30/minute")
@router.post("/events/{event_id}/sessions/{session_date}/checkin", response_model=dict)
def unified_checkin(
    request: Request,
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
            # plan_clasificador_contextual §4.3: el QR de inscripción expira a los 365 días.
            if is_qr_token_expired(reg):
                raise HTTPException(status_code=410, detail="El QR expiró")
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
        user_sede_id = require_user_sede_id(db, current_user)
        persona = (
            db.query(models.Persona)
            .filter(
                models.Persona.id == payload.persona_id,
                models.Persona.sede_id == user_sede_id,
            )
            .first()
        )
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
                sede_id=user_sede_id,
                church_role="Visitante",
                spiritual_status="Nuevo",
            )
            db.add(persona)
            db.flush()
        source = "walk_in"

    # Idempotencia y validación de doble acceso
    existing_attendance = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_day,
            models.EventAttendance.persona_id == persona.id,
            models.EventAttendance.attended.is_(True),
        )
        .first()
    )
    is_duplicate = bool(existing_attendance)

    if qr_kind == "CCF-EVT" and registration:
        if (
            registration.check_in_at is not None
            or is_duplicate
            or (existing_attendance is not None and existing_attendance.check_in_at is not None)
            or registration.registration_status == "CHECKED_IN"
        ):
            first_checkin_dt = (
                registration.check_in_at
                or (existing_attendance.check_in_at if existing_attendance else None)
                or (existing_attendance.scanned_at if existing_attendance else None)
                or _utcnow()
            )
            first_checkin_iso = (
                first_checkin_dt.isoformat()
                if hasattr(first_checkin_dt, "isoformat")
                else str(first_checkin_dt)
            )
            checked_by_id = registration.checked_in_by
            checked_by_name = _get_user_display_name(db, checked_by_id)
            reg_code = (
                f"#CCF-EVT-{registration.registration_number:04d}"
                if getattr(registration, "registration_number", None)
                else f"#CCF-EVT-{str(registration.id)[:8].upper()}"
            )

            raise HTTPException(
                status_code=409,
                detail={
                    "status": "duplicate_access",
                    "message": f"Acceso duplicado: {persona.nombre_completo} ya ingresó previamente a este evento",
                    "first_checkin_at": first_checkin_iso,
                    "checked_by_name": checked_by_name,
                    "persona_id": str(persona.id),
                    "persona_name": persona.nombre_completo,
                    "first_name": persona.first_name,
                    "last_name": persona.last_name,
                    "registration_code": reg_code,
                },
            )

    attendance, _created = _upsert_attendance(
        db,
        event.id,
        session_day,
        persona.id,
        source=source,
        role_at_event=registration.participant_role_code if registration else None,
    )

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if registration:
        registration.registration_status = "CHECKED_IN"
        registration.check_in_at = now_utc
        registration.checked_in_by = current_user.id

    attendance.check_in_at = now_utc
    attendance.scanned_at = now_utc

    db.commit()
    record_admin_action(db, current_user, action="event_checkin", resource_type="event", resource_id=str(event_id))

    try:
        from backend.services.event_post_followup_service import enroll_in_post_event_followup

        enroll_in_post_event_followup(
            db=db,
            event=event,
            persona=persona,
            registration=registration,
            current_user=current_user,
            auto_assign_mentor=True,
        )
        db.commit()
    except Exception as exc:
        logger.warning("Failed to auto-enroll attendee in post-event followup %s: %s", persona.id, exc)

    reg_code = (
        f"#CCF-EVT-{registration.registration_number:04d}"
        if registration and getattr(registration, "registration_number", None)
        else (f"#CCF-EVT-{str(registration.id)[:8].upper()}" if registration else None)
    )

    attendance_count = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_day,
            models.EventAttendance.attended.is_(True),
        )
        .count()
    )
    capacity = event.capacity_max or 0
    percentage = round((attendance_count / capacity * 100), 1) if capacity > 0 else 0.0

    return {
        "status": "success",
        "message": f"Acceso autorizado: {persona.nombre_completo}",
        "is_duplicate": False,
        "persona_id": str(persona.id),
        "persona_name": persona.nombre_completo,
        "first_name": persona.first_name,
        "last_name": persona.last_name,
        "email": persona.email,
        "phone": persona.phone or persona.mobile_phone,
        "registration_code": reg_code,
        "registration_id": str(registration.id) if registration else None,
        "source": source,
        "qr_kind": qr_kind,
        "participant_role_code": (registration.participant_role_code if registration else None),
        "role_at_event": attendance.role_at_event,
        "check_in_at": attendance.check_in_at.isoformat() if attendance.check_in_at else None,
        "checked_in_at": attendance.check_in_at.isoformat() if attendance.check_in_at else None,
        "checked_in_by": str(current_user.id),
        "checked_by_name": _get_user_display_name(db, current_user.id),
        "occupancy": {
            "count": attendance_count,
            "capacity_max": capacity,
            "percentage": percentage,
        },
    }

@academy_limiter.limit("30/minute")
@router.post("/events/{event_id}/sessions/{session_date}/ccf-evt-checkin", response_model=dict)
def ccf_evt_checkin(
    request: Request,
    event_id: UUID,
    session_date: str,
    payload: schemas.CheckinPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Check-in por QR de inscripción (``CCF-EVT-``) con rol contextual y bloqueo anti-fraude.

    TKT-EVT-GATEKEEPER-02:
    - Valida QRs CCF-EVT- e inscripciones.
    - Si la persona ya ingresó (check_in_at establecido o asistencia previa en la sesión),
      bloquea el reingreso con status 'duplicate_access' y HTTP 409 con detalle del
      primer ingreso (first_checkin_at, checked_by_name) para prevenir fraude.
    - Si es válido, registra check_in_at=datetime.now(timezone.utc),
      checked_in_by=current_user.id y devuelve status 'success' con PII y registration_code.
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
    # plan_clasificador_contextual §4.3: el QR de inscripción expira a los 365 días.
    if is_qr_token_expired(reg):
        raise HTTPException(status_code=410, detail="El QR expiró")

    persona = reg.persona
    if not persona:
        persona = db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada")

    existing_attendance = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_day,
            models.EventAttendance.persona_id == persona.id,
            models.EventAttendance.attended.is_(True),
        )
        .first()
    )

    is_duplicate = bool(
        existing_attendance
        or reg.check_in_at is not None
        or reg.registration_status == "CHECKED_IN"
    )

    if is_duplicate:
        first_checkin_dt = (
            reg.check_in_at
            or (existing_attendance.check_in_at if existing_attendance else None)
            or (existing_attendance.scanned_at if existing_attendance else None)
            or _utcnow()
        )
        first_checkin_iso = (
            first_checkin_dt.isoformat()
            if hasattr(first_checkin_dt, "isoformat")
            else str(first_checkin_dt)
        )
        checked_by_id = reg.checked_in_by
        checked_by_name = _get_user_display_name(db, checked_by_id)
        reg_code = (
            f"#CCF-EVT-{reg.registration_number:04d}"
            if getattr(reg, "registration_number", None)
            else f"#CCF-EVT-{str(reg.id)[:8].upper()}"
        )

        raise HTTPException(
            status_code=409,
            detail={
                "status": "duplicate_access",
                "message": f"Acceso duplicado: {persona.nombre_completo} ya ingresó previamente a este evento",
                "first_checkin_at": first_checkin_iso,
                "checked_by_name": checked_by_name,
                "persona_id": str(persona.id),
                "persona_name": persona.nombre_completo,
                "first_name": persona.first_name,
                "last_name": persona.last_name,
                "registration_code": reg_code,
            },
        )

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    reg.registration_status = "CHECKED_IN"
    reg.check_in_at = now_utc
    reg.checked_in_by = current_user.id

    attendance, _created = _upsert_attendance(
        db,
        event.id,
        session_day,
        persona.id,
        source="qr_event_registration",
        role_at_event=reg.participant_role_code,
    )
    attendance.check_in_at = now_utc
    attendance.scanned_at = now_utc

    db.commit()
    record_admin_action(db, current_user, action="event_checkin", resource_type="event", resource_id=str(event_id))

    try:
        from backend.services.event_post_followup_service import enroll_in_post_event_followup

        enroll_in_post_event_followup(
            db=db,
            event=event,
            persona=persona,
            registration=reg,
            current_user=current_user,
            auto_assign_mentor=True,
        )
        db.commit()
    except Exception as exc:
        logger.warning("Failed to auto-enroll attendee in post-event followup %s: %s", persona.id, exc)

    reg_code = (
        f"#CCF-EVT-{reg.registration_number:04d}"
        if getattr(reg, "registration_number", None)
        else f"#CCF-EVT-{str(reg.id)[:8].upper()}"
    )

    attendance_count = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_day,
            models.EventAttendance.attended.is_(True),
        )
        .count()
    )
    capacity = event.capacity_max or 0
    percentage = round((attendance_count / capacity * 100), 1) if capacity > 0 else 0.0

    return {
        "status": "success",
        "message": f"Acceso autorizado: {persona.nombre_completo}",
        "is_duplicate": False,
        "persona_id": str(persona.id),
        "persona_name": persona.nombre_completo,
        "first_name": persona.first_name,
        "last_name": persona.last_name,
        "email": persona.email,
        "phone": persona.phone or persona.mobile_phone,
        "registration_code": reg_code,
        "registration_id": str(reg.id),
        "source": "qr_event_registration",
        # plan_clasificador_contextual: rol efectivo + rol persistido en asistencia.
        "participant_role_code": reg.participant_role_code,
        "role_at_event": attendance.role_at_event,
        "check_in_at": reg.check_in_at.isoformat(),
        "checked_in_at": attendance.check_in_at.isoformat(),
        "checked_in_by": str(current_user.id),
        "checked_by_name": _get_user_display_name(db, current_user.id),
        "occupancy": {
            "count": attendance_count,
            "capacity_max": capacity,
            "percentage": percentage,
        },
    }


@router.get("/events/{event_id}/sessions/{session_date}/occupancy", response_model=dict)
def get_session_occupancy(
    event_id: UUID,
    session_date: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Monitor de aforo en vivo: contador en tiempo real y porcentaje de capacidad."""
    event = require_event_access(db, current_user, event_id)
    try:
        session_day = datetime.datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, esperado YYYY-MM-DD")

    attendance_count = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_day,
            models.EventAttendance.attended.is_(True),
        )
        .count()
    )
    capacity = event.capacity_max or 0
    percentage = round((attendance_count / capacity * 100), 1) if capacity > 0 else 0.0

    return {
        "event_id": str(event.id),
        "event_name": event.name,
        "session_date": session_date,
        "checked_in_count": attendance_count,
        "capacity_max": capacity,
        "percentage": percentage,
        "is_full": capacity > 0 and attendance_count >= capacity,
    }


@router.get("/events/{event_id}/occupancy", response_model=dict)
def get_event_occupancy(
    event_id: UUID,
    session_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Monitor de aforo en vivo para el evento (fecha de hoy o sesión especificada)."""
    today_str = session_date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return get_session_occupancy(event_id, today_str, db, current_user)


@academy_limiter.limit("30/minute")
@router.post("/events/{event_id}/sessions/{session_date}/checkout", response_model=dict)
def unified_checkout(
    request: Request,
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
    record_admin_action(db, current_user, action="event_checkin", resource_type="event", resource_id=str(event_id))
    return {
        "status": "success",
        "persona_id": str(persona.id),
        "check_out_at": attendance.check_out_at.isoformat(),
    }


# =============================================================================
# CHECK-IN EN LOTE (sincronización diferida offline, TKT-EVANGELISM-OFFLINE-SYNC-01)
# =============================================================================


def _resolve_batch_persona_by_qr(
    db: Session,
    token: str,
    event: models.CrmEvent,
    current_user: models.User,
) -> tuple[Optional[models.Persona], Optional[models.EventRegistration], str]:
    """Resuelve la persona detrás de un QR para el lote offline.

    Reusa los mismos invariantes del check-in individual: hash persistido +
    ``secrets.compare_digest`` (sin timing attacks), expiry y estados válidos.
    Los códigos de error se propagan como excepciones para que el caller
    decida si aborta el lote (4xx estructural) o marca el item como error.
    """
    if token.startswith("CCF-EVT-"):
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
        token_hash = _qr_token_secret_hash(token)
        if not token_hash or not secrets.compare_digest(str(reg.qr_token_hash or ""), token_hash):
            raise HTTPException(status_code=403, detail="QR inválido")
        if reg.registration_status not in {"CONFIRMED", "CHECKED_IN"}:
            raise HTTPException(
                status_code=409,
                detail=f"Inscripción no confirmada (estado: {reg.registration_status})",
            )
        if is_qr_token_expired(reg):
            raise HTTPException(status_code=410, detail="El QR expiró")
        persona = reg.persona or db.query(models.Persona).filter(models.Persona.id == persona_uuid).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        return persona, reg, "qr_event_registration"

    if token.startswith("CCF-PER-"):
        from backend.api.evangelism import _get_scoped_scanner_persona

        payload_str = token.removeprefix("CCF-PER-")
        parsed = _parse_per_qr_payload(payload_str)
        if parsed is None:
            raise HTTPException(status_code=400, detail="QR malformado")
        persona = _get_scoped_scanner_persona(parsed, db, current_user)
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
        return persona, None, "qr_persona"

    raise HTTPException(status_code=400, detail="Prefijo de QR desconocido")


@academy_limiter.limit("30/minute")
@router.post("/events/{event_id}/sessions/{session_date}/checkin-batch", response_model=dict)
def checkin_batch(
    request: Request,
    event_id: UUID,
    session_date: str,
    payload: CheckinBatchPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Sincroniza en lote la cola offline del Scanner QR (Gatekeeper).

    Contrato TKT-EVANGELISM-OFFLINE-SYNC-01:
    - Idempotente: los items cuya asistencia ya existe se reportan como
      ``duplicate`` (HTTP 200, nunca duplican filas; la UNIQUE
      ``uq_event_attendance`` respalda la garantía ante carreras).
    - Los items con QR inválido/no encontrado se reportan como ``error``
      sin abortar el resto del lote.
    - Un fallo estructural (permisos, evento cancelado, fecha inválida)
      aborta con 4xx como en el check-in individual.
    """
    event = require_event_access(db, current_user, event_id)

    if str(event.status or "").upper() in {"CANCELLED", "CANCELED"}:
        raise HTTPException(status_code=409, detail="No se puede hacer check-in en eventos cancelados")

    try:
        session_day = datetime.datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, esperado YYYY-MM-DD")

    results: list[dict] = []
    synced = duplicates = errors = 0
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    touched_registrations: list[models.EventRegistration] = []

    for index, item in enumerate(payload.items):
        persona: Optional[models.Persona] = None
        registration: Optional[models.EventRegistration] = None
        source = "manual_persona_id"
        try:
            if item.qr_token:
                persona, registration, source = _resolve_batch_persona_by_qr(
                    db, item.qr_token.strip(), event, current_user
                )
            elif item.persona_id:
                user_sede_id = require_user_sede_id(db, current_user)
                persona = (
                    db.query(models.Persona)
                    .filter(
                        models.Persona.id == item.persona_id,
                        models.Persona.sede_id == user_sede_id,
                    )
                    .first()
                )
                if not persona:
                    raise HTTPException(status_code=404, detail="Persona no encontrada")

            if persona is None:  # defensive: schema garantiza qr_token o persona_id
                raise HTTPException(status_code=422, detail="Item sin identidad válida")

            existing_attendance = (
                db.query(models.EventAttendance)
                .filter(
                    models.EventAttendance.event_id == event.id,
                    models.EventAttendance.session_date == session_day,
                    models.EventAttendance.persona_id == persona.id,
                    models.EventAttendance.attended.is_(True),
                )
                .first()
            )

            if existing_attendance:
                duplicates += 1
                results.append(
                    {
                        "index": index,
                        "status": "duplicate",
                        "persona_id": str(persona.id),
                        "persona_name": persona.nombre_completo,
                        "check_in_at": (
                            existing_attendance.check_in_at.isoformat()
                            if existing_attendance.check_in_at
                            else None
                        ),
                    }
                )
                continue

            attendance, _created = _upsert_attendance(
                db,
                event.id,
                session_day,
                persona.id,
                source=source,
                role_at_event=registration.participant_role_code if registration else None,
            )
            attendance.check_in_at = now_utc
            attendance.scanned_at = now_utc

            if registration:
                registration.registration_status = "CHECKED_IN"
                registration.check_in_at = now_utc
                registration.checked_in_by = current_user.id
                touched_registrations.append(registration)

            synced += 1
            results.append(
                {
                    "index": index,
                    "status": "synced",
                    "persona_id": str(persona.id),
                    "persona_name": persona.nombre_completo,
                    "check_in_at": attendance.check_in_at.isoformat(),
                }
            )
        except HTTPException as exc:
            errors += 1
            results.append(
                {
                    "index": index,
                    "status": "error",
                    "detail": exc.detail if isinstance(exc.detail, str) else "Error de validación del item",
                    "code": exc.status_code,
                }
            )

    db.commit()
    record_admin_action(
        db,
        current_user,
        action="event_checkin_batch",
        resource_type="event",
        resource_id=str(event_id),
        metadata={
            "synced": synced,
            "duplicates": duplicates,
            "errors": errors,
            "batch_size": len(payload.items),
        },
    )

    attendance_count = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_day,
            models.EventAttendance.attended.is_(True),
        )
        .count()
    )
    capacity = event.capacity_max or 0
    percentage = round((attendance_count / capacity * 100), 1) if capacity > 0 else 0.0

    return {
        "status": "success",
        "message": f"Lote procesado: {synced} sincronizados, {duplicates} duplicados, {errors} errores",
        "synced": synced,
        "duplicates": duplicates,
        "errors": errors,
        "results": results,
        "occupancy": {
            "count": attendance_count,
            "capacity_max": capacity,
            "percentage": percentage,
        },
    }

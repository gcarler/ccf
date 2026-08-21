"""Admin endpoints for EventRegistration (plan_de_preregistro, Fase 3).

Axioma 3 (Multi-Tenant): todo endpoint aplica ``require_event_access`` que
valida ``CrmEvent.sede_id`` vs la sede del actor. Las inscripciones se filtran
por ``event_id`` (que ya está scoped), así que el aislamiento por sede se
hereda transitivamente sin añadir ``sede_id`` a ``event_registrations``.

RBAC:
    - read:  ``require_evangelism_read``
    - edit:  ``require_evangelism_edit`` (mark check-in/out manual, resend QR)
    - manage: ``require_evangelism_manage`` (alta manual, import, delete)
"""

from __future__ import annotations

import csv
import io
import re
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.api.evangelism_events._shared import require_event_access
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import (
    require_evangelism_edit,
    require_evangelism_manage,
    require_evangelism_read,
)
from backend.services.event_registration_service import (
    RegistrationError,
    _issue_cancel_token,
    _issue_qr,
    _utcnow,
    count_active_registrations,
    normalize_participant_role,
    resolve_participant_role,
    upsert_persona,
)
from backend.services.event_registration_service import (
    cancel as cancel_registration,
)

router = APIRouter()


# ── Serialización ────────────────────────────────────────────────────────────


def _settings_public_base_url() -> str:
    """Resuelve la URL pública base (configurable via settings.public_base_url).

    Fix #11: usado por send_campaign_now/broadcast en lugar del query param
    ``public_base_url`` que se eliminó — previene que un admin inyecte dominios
    arbitrarios para phishing via plantillas ``{{qr_url}}``.
    Orden: ``settings.public_base_url`` → ``settings.frontend_url`` (dominio
    canónico) → fallback. Antes caía siempre al placeholder ``https://ccf.co``.
    """
    try:
        s = get_settings()
        return (getattr(s, "public_base_url", None) or s.frontend_url or "https://ccf.co").rstrip("/")
    except Exception:
        return "https://ccf.co"


def _serialize(reg: models.EventRegistration, persona: Optional[models.Persona]) -> schemas.EventRegistrationRead:
    extras_clean = {k: v for k, v in (reg.extras or {}).items() if not k.startswith("_")}
    return schemas.EventRegistrationRead(
        id=reg.id,
        event_id=reg.event_id,
        persona_id=reg.persona_id,
        persona_name=(persona.nombre_completo if persona else None),
        persona_email=(persona.email if persona else None),
        persona_phone=(persona.phone if persona else None),
        registration_status=reg.registration_status,
        # qr_token nunca se persiste (fix seguridad #2): se emite por email
        # al usuario, no se devuelve en la API admin ni pública.
        qr_token=None,
        qr_generated_at=reg.qr_generated_at,
        registered_at=reg.registered_at,
        confirmed_at=reg.confirmed_at,
        cancelled_at=reg.cancelled_at,
        check_in_at=reg.check_in_at,
        check_out_at=reg.check_out_at,
        checked_in_by=reg.checked_in_by,
        source=reg.source,
        extras=extras_clean,
        # plan_clasificador_contextual: rol efectivo de la inscripción.
        participant_role_code=reg.participant_role_code,
        waiting_list_position=reg.waiting_list_position,
        reminder_sent_count=reg.reminder_sent_count,
        last_reminder_sent_at=reg.last_reminder_sent_at,
    )


def _get_or_404(db: Session, event_id: UUID, reg_id: UUID) -> models.EventRegistration:
    reg = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.id == reg_id,
            models.EventRegistration.event_id == event_id,
            models.EventRegistration.deleted_at.is_(None),
        )
        .first()
    )
    if not reg:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    return reg


# ── Listado ───────────────────────────────────────────────────────────────────


@router.get("/events/{event_id}/registrations", response_model=List[schemas.EventRegistrationRead])
def list_registrations(
    event_id: UUID,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Lista paginada de inscripciones con filtros por estado y búsqueda."""
    event = require_event_access(db, current_user, event_id)

    q = (
        db.query(models.EventRegistration)
        .join(models.Persona)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
        )
    )
    if status:
        valid_statuses = {"PENDING", "CONFIRMED", "CHECKED_IN", "ABSENT", "WAITLIST", "CANCELLED"}
        if status not in valid_statuses:
            raise HTTPException(status_code=422, detail=f"status inválido: {status}")
        q = q.filter(models.EventRegistration.registration_status == status)

    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                models.Persona.first_name.ilike(term),
                models.Persona.last_name.ilike(term),
                models.Persona.email.ilike(term),
                models.Persona.phone.ilike(term),
            )
        )

    rows = (
        q.order_by(models.EventRegistration.registered_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return [_serialize(r, r.persona) for r in rows]


# ── KPIs ─────────────────────────────────────────────────────────────────────


@router.get("/events/{event_id}/registrations/stats", response_model=schemas.EventRegistrationStats)
def registrations_stats(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """KPIs de pre-registro del evento."""
    event = require_event_access(db, current_user, event_id)

    counts = (
        db.query(models.EventRegistration.registration_status)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
        )
        .all()
    )
    by_status = {"PENDING": 0, "CONFIRMED": 0, "CHECKED_IN": 0, "ABSENT": 0, "WAITLIST": 0, "CANCELLED": 0}
    for (s,) in counts:
        if s in by_status:
            by_status[s] += 1

    slots_taken = by_status["CONFIRMED"] + by_status["CHECKED_IN"]
    capacity_remaining = None
    if event.capacity_max is not None:
        capacity_remaining = max(0, event.capacity_max - slots_taken)

    attendance_rate = None
    expected = by_status["CONFIRMED"] + by_status["CHECKED_IN"] + by_status["ABSENT"]
    if expected > 0:
        attendance_rate = round((by_status["CHECKED_IN"] / expected) * 100, 1)

    return schemas.EventRegistrationStats(
        total=sum(by_status.values()),
        pending=by_status["PENDING"],
        confirmed=by_status["CONFIRMED"],
        checked_in=by_status["CHECKED_IN"],
        absent=by_status["ABSENT"],
        waitlist=by_status["WAITLIST"],
        cancelled=by_status["CANCELLED"],
        capacity_max=event.capacity_max,
        capacity_remaining=capacity_remaining,
        attendance_rate=attendance_rate,
    )


# ── Export CSV ───────────────────────────────────────────────────────────────


@router.get("/events/{event_id}/registrations/export.csv")
def export_registrations_csv(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Exporta CSV con todas las inscripciones (nocancelled)."""
    event = require_event_access(db, current_user, event_id)
    rows = (
        db.query(models.EventRegistration)
        .join(models.Persona)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
        )
        .order_by(models.EventRegistration.registered_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=",", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Nombre", "Email", "Teléfono", "Estado", "Registrado el", "Check-in"])
    for r in rows:
        p = r.persona
        writer.writerow(
            [
                (p.nombre_completo if p else ""),
                (p.email if p else ""),
                (p.phone if p else ""),
                r.registration_status,
                r.registered_at.isoformat() if r.registered_at else "",
                r.check_in_at.isoformat() if r.check_in_at else "",
            ]
        )

    # Fix #10: sanitizar el filename del CSV — event.name puede contener
    # caracteres peligrosos para Content-Disposition (/, \, ", ;, \r, \n).
    # Solo permitimos alphanumerics, guiones y guiones bajos; lo demás
    # se reemplaza por _ (espacios incluidos).
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", event.name or "").strip("_") or "evento"
    filename = f"inscripciones_{safe_name}_{_utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Alta manual ──────────────────────────────────────────────────────────────


@router.post("/events/{event_id}/registrations", response_model=schemas.EventRegistrationRead, status_code=201)
def create_registration(
    event_id: UUID,
    payload: schemas.EventRegistrationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Alta manual de una inscripción (admin). Crea Persona si no existe."""
    event = require_event_access(db, current_user, event_id)

    # Race de aforo (plan §7): serializa conteo+insert bloqueando la fila del
    # evento (no-op en SQLite; efectivo en Postgres).
    db.query(models.CrmEvent).with_for_update().filter(models.CrmEvent.id == event.id).first()

    persona = None
    if payload.persona_id:
        persona = db.query(models.Persona).filter(models.Persona.id == payload.persona_id).first()
        if not persona:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
    else:
        if not (payload.first_name and payload.last_name):
            raise HTTPException(status_code=422, detail="Se requiere persona_id o first_name+last_name")
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
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.persona_id == persona.id,
        )
        .order_by(models.EventRegistration.created_at.desc())
        .first()
    )
    if existing and existing.registration_status in {"CONFIRMED", "CHECKED_IN", "WAITLIST", "PENDING"}:
        return _serialize(existing, existing.persona)

    slots_taken, waitlist_count = count_active_registrations(db, event.id)
    capacity_full = event.capacity_max is not None and slots_taken >= event.capacity_max

    target_status = payload.registration_status
    if capacity_full and target_status == "CONFIRMED" and not event.waiting_list_enabled:
        raise HTTPException(status_code=409, detail="Evento lleno y sin waitlist habilitada")
    if capacity_full and target_status == "CONFIRMED" and event.waiting_list_enabled:
        target_status = "WAITLIST"

    # plan_clasificador_contextual: override admin (validado) o rol del evento.
    try:
        role_code = resolve_participant_role(event, requested=payload.participant_role_code)
    except RegistrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "detail": exc.detail}) from None

    reg = models.EventRegistration(
        event_id=event.id,
        persona_id=persona.id,
        registration_status=target_status,
        source=payload.source or "admin",
        extras=payload.extras or {},
        waiting_list_position=(waitlist_count + 1) if target_status == "WAITLIST" else None,
        participant_role_code=role_code,
    )
    db.add(reg)
    db.flush()

    if reg.registration_status == "CONFIRMED":
        _issue_qr(db, reg)
        _issue_cancel_token(db, reg)
        reg.confirmed_at = _utcnow()

    db.commit()
    db.refresh(reg)
    return _serialize(reg, reg.persona)


# ── Edición de estado ─────────────────────────────────────────────────────────


@router.patch("/events/{event_id}/registrations/{reg_id}", response_model=schemas.EventRegistrationRead)
def update_registration(
    event_id: UUID,
    reg_id: UUID,
    payload: schemas.EventRegistrationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Edita el estado o extras de una inscripción (transiciones legales)."""
    event = require_event_access(db, current_user, event_id)
    reg = _get_or_404(db, event.id, reg_id)

    if payload.registration_status is not None:
        new_status = payload.registration_status
        legal = {
            "PENDING": {"CONFIRMED", "CANCELLED"},
            "CONFIRMED": {"CHECKED_IN", "ABSENT", "CANCELLED"},
            "WAITLIST": {"CONFIRMED", "CANCELLED"},
            # Fix #9: un CHECKED_IN puede revertirse a ABSENT (check-in erróneo)
            # o CANCELLED (anular inscripción), pero no a CONFIRMED (ya pasó).
            "CHECKED_IN": {"CHECKED_IN", "ABSENT", "CANCELLED"},
            "ABSENT": {"ABSENT", "CONFIRMED", "CANCELLED"},
            "CANCELLED": {"CANCELLED"},
        }
        allowed = legal.get(reg.registration_status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"Transición ilegal: {reg.registration_status} → {new_status}",
            )

        if new_status == "CONFIRMED" and reg.registration_status == "WAITLIST":
            reg.confirmed_at = _utcnow()
            reg.waiting_list_position = None
            _issue_qr(db, reg)
            _issue_cancel_token(db, reg)
        elif new_status == "CANCELLED":
            cancel_registration(db, event, reg)
        elif new_status == "CHECKED_IN":
            reg.check_in_at = _utcnow()
            # Fix #8: registrar el actor admin que hizo el check-in manual.
            # El path de checkin/checkout via QR (events_checkin.py) también
            # setea este campo desde ``current_user``.
            reg.checked_in_by = current_user.id
        elif new_status == "ABSENT":
            # Fix #9: registrar auditoría mínima de quien marcó ausente.
            # No hay tabla dédiada, pero ``extras["_last_status_change"]``
            # deja trail sin añadir modelo nuevo (low-overhead audit).
            _extras = dict(reg.extras or {})
            _extras["_last_status_change"] = {
                "from": reg.registration_status,
                "to": new_status,
                "by": str(current_user.id),
                "at": _utcnow().isoformat(),
            }
            reg.extras = _extras
            reg.registration_status = "ABSENT"

        if new_status != "CANCELLED" and new_status != "ABSENT":
            reg.registration_status = new_status

    if payload.extras is not None:
        # preservar campos internos
        internal = {k: v for k, v in (reg.extras or {}).items() if k.startswith("_")}
        reg.extras = {**internal, **payload.extras}

    # plan_clasificador_contextual: override del rol por admin autorizado.
    if payload.participant_role_code is not None:
        try:
            reg.participant_role_code = resolve_participant_role(event, requested=payload.participant_role_code)
        except RegistrationError as exc:
            raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "detail": exc.detail}) from None

    db.commit()
    db.refresh(reg)
    return _serialize(reg, reg.persona)


# ── Reenviar QR ──────────────────────────────────────────────────────────────


@router.post(
    "/events/{event_id}/registrations/{reg_id}/resend-confirmation",
    response_model=dict,
)
def resend_confirmation(
    event_id: UUID,
    reg_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Reenviar email con QR al inscrito (solo si CONFIRMED o CHECKED_IN)."""
    event = require_event_access(db, current_user, event_id)
    reg = _get_or_404(db, event.id, reg_id)
    if reg.registration_status not in {"CONFIRMED", "CHECKED_IN"}:
        raise HTTPException(status_code=409, detail="La inscripción no está CONFIRMED")

    # Regenerar tokens (volatile, nunca persistidos): al reemitir el QR,
    # invalidamos cualquier token anterior (el hash se reescribe).
    qr_token_plain = _issue_qr(db, reg)
    cancel_token_plain = _issue_cancel_token(db, reg)
    db.flush()

    from backend.services.event_registration_service import _send_confirmation_email

    # El dominio base se resuelve del setting canónico — antes se pasaba ""
    # y el QR del email reenviado salía como URL relativa (inutilizable).
    _send_confirmation_email(
        db,
        event,
        reg,
        reg.persona,
        public_base_url=_settings_public_base_url(),
        qr_token_plain=qr_token_plain,
        cancel_token_plain=cancel_token_plain,
    )

    db.commit()
    return {"status": "ok", "message": "Email reenviado"}


# ── Bulk import ───────────────────────────────────────────────────────────────


@router.post("/events/{event_id}/registrations/import", response_model=dict)
def bulk_import(
    event_id: UUID,
    payload: schemas.EventRegistrationBulkImport,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Importa una lista de inscripciones (upsert Persona + EventRegistration).

    Respeta ``capacity_max`` y ``waiting_list_enabled`` como el path público:
    - Si el evento tiene ``capacity_max`` y se supera, las filas extra se
      derivan a WAITLIST (si ``waiting_list_enabled``) o se omiten con error.
    - Toma ``with_for_update`` sobre CrmEvent para serializar el conteo+
      insert (fix #4) y no sobrevender el aforo en cargas masivas paralelas.
    - Los tokens QR/cancel emitidos a CONFIRMED son volatile (no persistidos).
    """
    event = require_event_access(db, current_user, event_id)
    # Race de aforo (fix #4): bloquear la fila del evento para que el
    # bulk import vea un conteo estable y no sobrevenda capacity_max.
    db.query(models.CrmEvent).with_for_update().filter(models.CrmEvent.id == event.id).first()

    # Slots activos al iniciar el bulk — contamos una sola vez para todo el lote.
    slots_taken, _ = count_active_registrations(db, event.id)
    capacity_max = event.capacity_max
    waiting_list_enabled = bool(event.waiting_list_enabled)

    created, skipped = 0, 0
    errors: list[dict] = []
    for idx, row in enumerate(payload.rows):
        try:
            persona = upsert_persona(
                db,
                first_name=row.first_name or "",
                last_name=row.last_name or "",
                email=row.email,
                phone=row.phone,
                sede_id=event.sede_id,
            )
            existing = (
                db.query(models.EventRegistration)
                .filter(
                    models.EventRegistration.event_id == event.id,
                    models.EventRegistration.persona_id == persona.id,
                )
                .first()
            )
            if existing and existing.registration_status in {"CONFIRMED", "CHECKED_IN", "WAITLIST", "PENDING"}:
                skipped += 1
                continue

            # Si el admin pidió CONFIRMED pero el aforo está lleno, derivar a
            # WAITLIST (siempre que el evento lo permita) o rechazar la fila.
            target_status = row.registration_status
            if target_status == "CONFIRMED" and capacity_max is not None and slots_taken >= capacity_max:
                if waiting_list_enabled:
                    target_status = "WAITLIST"
                else:
                    errors.append({"row": idx, "error": "Aforo lleno y evento sin lista de espera"})
                    continue

            reg = models.EventRegistration(
                event_id=event.id,
                persona_id=persona.id,
                registration_status=target_status,
                source=row.source or "admin_import",
                extras=row.extras or {},
                # plan_clasificador_contextual: override por fila o rol del evento.
                participant_role_code=resolve_participant_role(event, requested=row.participant_role_code),
            )
            if target_status == "WAITLIST":
                # Adjuntar al final de la cola: position = (slotsTaken en cola) + 1.
                wl_count = (
                    db.query(models.EventRegistration)
                    .filter(
                        models.EventRegistration.event_id == event.id,
                        models.EventRegistration.registration_status == "WAITLIST",
                        models.EventRegistration.deleted_at.is_(None),
                    )
                    .count()
                )
                reg.waiting_list_position = wl_count + 1
            db.add(reg)
            db.flush()
            if reg.registration_status == "CONFIRMED":
                _issue_qr(db, reg)
                _issue_cancel_token(db, reg)
                reg.confirmed_at = _utcnow()
                slots_taken += 1
            created += 1
        except Exception as exc:
            errors.append({"row": idx, "error": str(exc)})

    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}


# ── Soft-delete ──────────────────────────────────────────────────────────────


@router.delete("/events/{event_id}/registrations/{reg_id}", status_code=204)
def delete_registration(
    event_id: UUID,
    reg_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Soft-delete (cancela la inscripción)."""
    event = require_event_access(db, current_user, event_id)
    reg = _get_or_404(db, event.id, reg_id)
    cancel_registration(db, event, reg)
    return None


# ── Configuración del evento (flags de pre-registro) ────────────────────────


@router.patch("/events/{event_id}/preregistration-config", response_model=dict)
def update_preregistration_config(
    event_id: UUID,
    payload: schemas.CrmEventPreregistrationConfig,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Actualiza los flags de pre-registro de un evento existente."""
    event = require_event_access(db, current_user, event_id)
    event.requires_registration = payload.requires_registration
    event.requires_email_verification = payload.requires_email_verification
    event.registration_opens_at = payload.registration_opens_at
    event.registration_closes_at = payload.registration_closes_at
    event.capacity_max = payload.capacity_max
    event.waiting_list_enabled = payload.waiting_list_enabled
    event.qr_mode = payload.qr_mode
    event.contact_person = payload.contact_person
    event.settings_json = payload.settings_json
    # plan_clasificador_contextual: rol por defecto del evento (override admin).
    if payload.participant_role_code is not None:
        try:
            event.participant_role_code = normalize_participant_role(payload.participant_role_code)
        except RegistrationError as exc:
            raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "detail": exc.detail}) from None
    db.commit()
    return {
        "id": str(event.id),
        "requires_registration": event.requires_registration,
        "qr_mode": event.qr_mode,
        "capacity_max": event.capacity_max,
        "participant_role_code": event.participant_role_code,
    }


# =============================================================================
# CAMPAÑAS DE MENSAJERÍA (plan_de_preregistro, Fase 5)
# =============================================================================


@router.get("/events/{event_id}/campaigns", response_model=List[schemas.EventCampaignRead])
def list_campaigns(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_read),
):
    """Lista las campañas de mensajería ligadas a un evento."""
    event = require_event_access(db, current_user, event_id)
    rows = (
        db.query(models.EventCampaign)
        .filter(
            models.EventCampaign.event_id == event.id,
            models.EventCampaign.deleted_at.is_(None),
        )
        .order_by(models.EventCampaign.created_at.desc())
        .all()
    )
    return rows


@router.post("/events/{event_id}/campaigns", response_model=schemas.EventCampaignRead, status_code=201)
def create_campaign(
    event_id: UUID,
    payload: schemas.EventCampaignCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Crea una campaña ligada al evento."""
    event = require_event_access(db, current_user, event_id)

    # Validar plantilla pertenece a la sede del evento.
    plantilla = db.query(models.PlantillaMensaje).filter(models.PlantillaMensaje.id == payload.plantilla_id).first()
    if not plantilla:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    if plantilla.sede_id and str(plantilla.sede_id) != str(event.sede_id):
        raise HTTPException(status_code=403, detail="Plantilla no pertenece a la sede del evento")

    persona = db.query(models.Persona).filter(models.Persona.id == current_user.id).first()

    campaign = models.EventCampaign(
        event_id=event.id,
        name=payload.name,
        plantilla_id=payload.plantilla_id,
        canal=payload.canal,
        trigger_type=payload.trigger_type,
        trigger_offset_minutes=payload.trigger_offset_minutes,
        target_status=payload.target_status,
        is_active=payload.is_active,
        created_by_id=(persona.id if persona else None),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.patch("/events/{event_id}/campaigns/{campaign_id}", response_model=schemas.EventCampaignRead)
def update_campaign(
    event_id: UUID,
    campaign_id: UUID,
    payload: schemas.EventCampaignUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Edita una campaña existente."""
    event = require_event_access(db, current_user, event_id)
    campaign = (
        db.query(models.EventCampaign)
        .filter(
            models.EventCampaign.id == campaign_id,
            models.EventCampaign.event_id == event.id,
            models.EventCampaign.deleted_at.is_(None),
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    if payload.name is not None:
        campaign.name = payload.name
    if payload.plantilla_id is not None:
        plantilla = db.query(models.PlantillaMensaje).filter(models.PlantillaMensaje.id == payload.plantilla_id).first()
        if not plantilla:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        if plantilla.sede_id and str(plantilla.sede_id) != str(event.sede_id):
            raise HTTPException(status_code=403, detail="Plantilla no pertenece a la sede del evento")
        campaign.plantilla_id = payload.plantilla_id
    if payload.canal is not None:
        campaign.canal = payload.canal
    if payload.trigger_type is not None:
        campaign.trigger_type = payload.trigger_type
    if payload.trigger_offset_minutes is not None:
        campaign.trigger_offset_minutes = payload.trigger_offset_minutes
    if payload.target_status is not None:
        campaign.target_status = payload.target_status
    if payload.is_active is not None:
        campaign.is_active = payload.is_active

    db.commit()
    db.refresh(campaign)
    return campaign


@router.delete("/events/{event_id}/campaigns/{campaign_id}", status_code=204)
def delete_campaign(
    event_id: UUID,
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    """Soft-delete de una campaña."""
    event = require_event_access(db, current_user, event_id)
    campaign = (
        db.query(models.EventCampaign)
        .filter(
            models.EventCampaign.id == campaign_id,
            models.EventCampaign.event_id == event.id,
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    campaign.deleted_at = _utcnow()
    db.commit()
    return None


@router.post("/events/{event_id}/campaigns/{campaign_id}/send", response_model=dict)
def send_campaign_now(
    event_id: UUID,
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
    dry_run: bool = Query(False),
    limit: Optional[int] = Query(None, ge=1, le=10000),
):
    """Dispara la campaña inmediatamente (manual).

    ``dry_run=True`` no envía, sólo retorna preview del primer mensaje.

    Fix #11: ``public_base_url`` ya no se acepta como query — se usa el
    setting canónico ``settings.public_base_url`` (default ``https://ccf.co``)
    para hidratar ``{{qr_url}}``/``{{qr_link}}``. Antes, un admin podía
    inyectar dominios arbitrarios → fishing a los inscritos.
    """
    event = require_event_access(db, current_user, event_id)
    campaign = (
        db.query(models.EventCampaign)
        .filter(
            models.EventCampaign.id == campaign_id,
            models.EventCampaign.event_id == event.id,
            models.EventCampaign.deleted_at.is_(None),
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    from backend.services.event_campaign_service import send_campaign

    return send_campaign(db, campaign, public_base_url=_settings_public_base_url(), dry_run=dry_run, limit=limit)


@router.post("/events/{event_id}/registrations/broadcast", response_model=dict)
def broadcast_campaign(
    event_id: UUID,
    payload: schemas.EventRegistrationBroadcast,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_edit),
):
    """Dispara una campaña a las inscripciones filtradas por status.

    Fix #11: ``public_base_url`` se eliminó como query param (pishing risk).
    Se usa el setting can \u00f3nico ``settings.public_base_url``.
    """
    event = require_event_access(db, current_user, event_id)
    campaign = (
        db.query(models.EventCampaign)
        .filter(
            models.EventCampaign.id == payload.campaign_id,
            models.EventCampaign.event_id == event.id,
            models.EventCampaign.deleted_at.is_(None),
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    if payload.target_status is not None:
        campaign.target_status = payload.target_status
        db.flush()

    from backend.services.event_campaign_service import send_campaign

    return send_campaign(db, campaign, public_base_url=_settings_public_base_url())

"""Servicio de pre-registro a eventos masivos (plan_de_preregistro).

Centraliza la lógica de negocio de EventRegistration: validaciones de aforo,
lista de espera, generación de QR/verify tokens, promoción automática de
waitlist al cancelar, envío de email de confirmación con QR.

Reusos intencionales:
    - Patrón de scanner token (``Persona.scanner_token_hash`` en
      ``models_crm.py:452``): mismo formato ``CCF-<scope>-<uuid>-<secret>``
      con hash sha256 y expiry 365 días.
    - ``services/email.send_email`` para salida SMTP.
    - ``secrets.token_hex`` + ``hashlib.sha256`` para tokens.

Axioma 3 (Multi-Tenant): no añade ``sede_id`` a ``EventRegistration`` — el
scope se hereda vía JOIN ``event_registrations.event_id → crm_events.sede_id``.
Las funciones aceptan ``event`` ya cargado y validado por el caller (que
ejecuta ``require_event_access`` en el router admin).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import logging
import secrets
import uuid
from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend import models, schemas

log = logging.getLogger(__name__)


# ── Constantes ───────────────────────────────────────────────────────────────

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


# ── Generadores de token ─────────────────────────────────────────────────────


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _as_utc(value) -> _dt.datetime:
    """Axioma — atacha UTC a datetimes naive (REGLAS.md §6).

    SQLite persiste ``DateTime(timezone=True)`` como datetimes NAIVE aunque el
    ORM declare timezone-aware, lo que rompe comparaciones contra
    ``_utcnow()`` (aware). Mismo patrón que ``AwareDateTime`` en
    ``backend/schemas/_common.py``.
    """
    if value is None:
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=_dt.timezone.utc)
    return value


def generate_qr_token(event_id, persona_id) -> Tuple[str, str]:
    """Genera (token_plano, hash) para el QR de una inscripción.

    Returns:
        (qr_token, qr_token_hash) — el token plano se guarda SOLO en
        ``qr_token`` (para debug/display), el hash en ``qr_token_hash``
        se usa para todas las búsquedas de check-in.
    """
    secret = secrets.token_hex(16)
    token = f"{QR_PREFIX}{event_id}-{persona_id}-{secret}"
    token_hash = hashlib.sha256(secret.encode()).hexdigest()
    return token, token_hash


def generate_verify_token(registration_id) -> Tuple[str, str]:
    """Genera token de verificación de email (24h de validez por convención)."""
    secret = secrets.token_hex(16)
    token = f"{VERIFY_PREFIX}{registration_id}-{secret}"
    token_hash = hashlib.sha256(secret.encode()).hexdigest()
    return token, token_hash


def hash_token(token: str) -> str:
    """Extrae el secret del token (último segmento tras '-') y lo hashea."""
    if "-" not in token:
        return ""
    secret = token.rsplit("-", 1)[1]
    return hashlib.sha256(secret.encode()).hexdigest()


def is_qr_token_expired(reg: models.EventRegistration) -> bool:
    """Un QR se considera expirado a los QR_EXPIRY_DAYS desde generación."""
    if not reg.qr_generated_at:
        return True
    expires_at = reg.qr_generated_at + _dt.timedelta(days=QR_EXPIRY_DAYS)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=_dt.timezone.utc)
    return expires_at < _utcnow()


# ── Resolución de Persona (upsert) ────────────────────────────────────────────


def upsert_persona(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    sede_id=None,
) -> models.Persona:
    """Busca o crea una Persona. Alineado con ``api/public.py:35``.

    Busca primero por email; si no, por phone. Si no existe, crea una nueva
    Persona con ``church_role='Visitante'`` y ``spiritual_status='Nuevo'``.
    """
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
        log.info("Persona creada desde pre-registro: %s %s", first_name, last_name)
    return persona


# ── Validaciones de pre-registro ─────────────────────────────────────────────


class RegistrationError(Exception):
    """Error de negocio de pre-registro (409 / 403 / 410)."""

    def __init__(self, code: str, detail: str, status_code: int = 409):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def assert_registration_window_open(event: models.CrmEvent, now=None):
    """Valida que el evento permita inscripción en este momento."""
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
    """Retorna (confirmadas_o_checked_in, waitlist_count) para el evento.

    El aforo se calcula solo sobre estados que ocupan slot:
    CONFIRMED y CHECKED_IN. WAITLIST no ocupa slot.
    """
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
    slots_taken = int(by_status.get("CONFIRMED", 0)) + int(by_status.get("CHECKED_IN", 0))
    waitlist = int(by_status.get("WAITLIST", 0))
    return slots_taken, waitlist


def capacity_remaining(db: Session, event: models.CrmEvent) -> Optional[int]:
    """Devuelve cuántos slots quedan. None si capacity_max es NULL (ilimitado)."""
    if event.capacity_max is None:
        return None
    slots_taken, _ = count_active_registrations(db, event.id)
    return max(0, event.capacity_max - slots_taken)


# ── Flujo principal de pre-registro ──────────────────────────────────────────


def register(
    db: Session,
    event: models.CrmEvent,
    payload: schemas.PublicEventRegister,
    *,
    public_base_url: str = "",
) -> models.EventRegistration:
    """Crea o actualiza una EventRegistration.

    Lanza ``RegistrationError`` si:
        - Evento sin ``requires_registration`` (403 NOT_REGISTRATION_EVENT)
        - Fuera de ventana (409/410)
        - Aforo lleno sin waitlist (409 EVENT_FULL)
        - Ya existe una inscripción CANCELLED (reactivable)
    """
    if not event.requires_registration:
        raise RegistrationError(
            "NOT_REGISTRATION_EVENT",
            "Este evento no requiere pre-inscripción",
            status_code=403,
        )

    assert_registration_window_open(event)

    # Race de aforo (plan §7): serializa conteo+insert por evento bloqueando la
    # fila del CrmEvent (no-op en SQLite; efectivo en Postgres). Sin este lock,
    # dos peticiones concurrentes podrían leer slots_taken=0 y sobrevender.
    db.query(models.CrmEvent).with_for_update().filter(models.CrmEvent.id == event.id).first()

    persona = upsert_persona(
        db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        sede_id=event.sede_id,
    )

    # ¿Ya existe una inscripción activa para esta persona en este evento?
    existing = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.persona_id == persona.id,
        )
        .order_by(models.EventRegistration.created_at.desc())
        .first()
    )
    # Si ya está CONFIRMED/CHECKED_IN/WAITLIST,regresamos esa fila (idempotente).
    if existing and existing.registration_status in {"CONFIRMED", "CHECKED_IN", "WAITLIST"}:
        return existing

    slots_taken, waitlist_count = count_active_registrations(db, event.id)
    capacity_full = event.capacity_max is not None and slots_taken >= event.capacity_max

    if capacity_full and not event.waiting_list_enabled:
        raise RegistrationError("EVENT_FULL", "El evento alcanzó su aforo máximo", 409)

    if existing and existing.registration_status == "CANCELLED":
        # Reactivación: la fila existe pero estaba cancelada. Se resetea el
        # ciclo de vida para emitir un QR/cancel token frescos.
        existing.deleted_at = None
        existing.cancelled_at = None
        existing.qr_token = None
        existing.qr_token_hash = None
        existing.qr_generated_at = None
        existing.confirmed_at = None
        existing.check_in_at = None
        existing.check_out_at = None
        existing.registration_status = (
            "WAITLIST" if capacity_full else
            ("PENDING" if event.requires_email_verification else "CONFIRMED")
        )
        existing.waiting_list_position = waitlist_count + 1 if capacity_full else None
        # Limpia tokens internos previos (verify/cancel) para emitir otros nuevos.
        _extras = dict(existing.extras or {})
        for _k in [k for k in _extras if k.startswith("_")]:
            _extras.pop(_k)
        existing.extras = _extras
        db.flush()
        reg = existing
    else:
        reg = models.EventRegistration(
            event_id=event.id,
            persona_id=persona.id,
            registration_status=(
                "WAITLIST" if capacity_full else
                ("PENDING" if event.requires_email_verification else "CONFIRMED")
            ),
            waiting_list_position=waitlist_count + 1 if capacity_full else None,
            extras=payload.extras or {},
            source="public_form",
        )
        db.add(reg)
        db.flush()

    # Generar QR solo si está CONFIRMED (no WAITLIST ni PENDING sin verificar).
    if reg.registration_status == "CONFIRMED":
        reg.confirmed_at = _utcnow()
        _issue_qr(db, reg)
        _issue_cancel_token(db, reg)

    db.commit()
    db.refresh(reg)

    # Email de confirmación (siempre).
    if reg.registration_status == "CONFIRMED":
        _send_confirmation_email(db, event, reg, persona, public_base_url)
    elif reg.registration_status == "PENDING":
        verify_token, _ = generate_verify_token(reg.id)
        extras = dict(reg.extras or {})
        extras["_verify_token_hash"] = hash_token(verify_token)
        extras["_verify_expires_at"] = (
            _utcnow() + _dt.timedelta(hours=VERIFY_EXPIRY_HOURS)
        ).isoformat()
        reg.extras = extras
        # Persiste el hash ANTES del envío: un flush sin commit se pierde al
        # cerrar la sesión del request y la verificación nunca podría resolverse.
        db.commit()
        db.refresh(reg)
        _send_verification_email(db, event, reg, persona, public_base_url, verify_token)

    return reg


def _issue_qr(db: Session, reg: models.EventRegistration) -> None:
    """Genera QR token + hash + marca qr_generated_at. Idempotente."""
    if reg.qr_token and reg.qr_token_hash:
        return  # ya tiene QR
    token, token_hash = generate_qr_token(reg.event_id, reg.persona_id)
    reg.qr_token = token
    reg.qr_token_hash = token_hash
    reg.qr_generated_at = _utcnow()
    db.flush()


def _issue_cancel_token(db: Session, reg: models.EventRegistration) -> None:
    """Genera token de cancelación embebido en el QR link. Idempotente."""
    if (reg.extras or {}).get("_cancel_token_hash"):
        return
    secret = secrets.token_hex(16)
    cancel_token = f"{CANCEL_PREFIX}{reg.id}-{secret}"
    cancel_hash = hashlib.sha256(secret.encode()).hexdigest()
    extras = dict(reg.extras or {})
    extras["_cancel_token_hash"] = cancel_hash
    extras["_cancel_token"] = cancel_token
    reg.extras = extras
    db.flush()


def _send_confirmation_email(
    db: Session,
    event: models.CrmEvent,
    reg: models.EventRegistration,
    persona: models.Persona,
    public_base_url: str,
) -> None:
    """Envía el email de confirmación con el QR (visible inline via token)."""
    if not persona.email:
        return
    try:
        from backend.services.email import send_email
        from html import escape

        qr_link = ""
        cancel_link = ""
        if reg.qr_token:
            # El token de cancelación va embebido en el QR link (plan §4.1):
            # la página pública de ticket lo usa para la auto-cancelación.
            cancel_token = (reg.extras or {}).get("_cancel_token", "")
            cancel_param = f"&cancel={cancel_token}" if cancel_token else ""
            qr_link = f"{public_base_url}/public/events/{event.id}/qr?token={reg.qr_token}{cancel_param}".strip()
            if cancel_token:
                cancel_link = f"{public_base_url}/public/events/{event.id}/cancel?token={cancel_token}".strip()

        event_date_str = event.event_date.strftime("%d/%m/%Y %H:%M") if event.event_date else "Por confirmar"
        location_str = event.location or "Por confirmar"
        html = f"""
        <h2>¡Inscripción confirmada: {escape(event.name)}!</h2>
        <p>Hola <strong>{escape(persona.first_name or "")}</strong>,</p>
        <p>Tu inscripción al evento fue confirmada. Guarda este QR para el día del evento:</p>
        <ul>
            <li><strong>Fecha:</strong> {escape(event_date_str)}</li>
            <li><strong>Lugar:</strong> {escape(location_str)}</li>
        </ul>
        {f'<p>Tu QR: <a href="{escape(qr_link)}">descargar</a></p>' if qr_link else ''}
        {f'<p style="font-size:12px;color:#9ca3af;">¿No podrás asistir? <a href="{escape(cancel_link)}">Cancela tu inscripción</a>.</p>' if cancel_link else ''}
        <p>¡Te esperamos!</p>
        """
        send_email(to=persona.email, subject=f"Confirmación: {event.name}", html=html)
    except Exception as exc:
        log.warning("Failed to send confirmation email for registration %s: %s", reg.id, exc)


def _send_verification_email(
    db: Session,
    event: models.CrmEvent,
    reg: models.EventRegistration,
    persona: models.Persona,
    public_base_url: str,
    verify_token: str,
) -> None:
    """Envía el email con el link de verificación (24h de validez)."""
    if not persona.email:
        return
    try:
        from backend.services.email import send_email
        from html import escape

        verify_url = f"{public_base_url}/public/events/{event.id}/verify?token={verify_token}".strip()
        event_date_str = event.event_date.strftime("%d/%m/%Y %H:%M") if event.event_date else "Por confirmar"
        html = f"""
        <h2>Verifica tu inscripción: {escape(event.name)}</h2>
        <p>Hola <strong>{escape(persona.first_name or "")}</strong>,</p>
        <p>Para confirmar tu inscripción al evento del <strong>{escape(event_date_str)}</strong>,
        haz clic en el siguiente enlace (válido por {VERIFY_EXPIRY_HOURS}h):</p>
        <p><a href="{escape(verify_url)}">{escape(verify_url)}</a></p>
        """
        send_email(to=persona.email, subject=f"Verifica tu inscripción: {event.name}", html=html)
    except Exception as exc:
        log.warning("Failed to send verification email for registration %s: %s", reg.id, exc)


# ── Verificación de email ────────────────────────────────────────────────────


def verify(
    db: Session,
    event: models.CrmEvent,
    token: str,
    *,
    public_base_url: str = "",
) -> models.EventRegistration:
    """Verifica una inscripción con el token enviado por email.

    Lanza RegistrationError si token inválido/expirado. Al confirmar envía el
    email con el QR (si hay email en la persona).
    """
    if not token.startswith(VERIFY_PREFIX):
        raise RegistrationError("INVALID_TOKEN", "Token de verificación inválido", 400)
    payload = token.removeprefix(VERIFY_PREFIX)
    # El secret es el ÚLTIMO segmento; el id es todo lo anterior. Los UUID
    # contienen guiones, así que NO se puede split por el primer '-'
    # (truncaría el UUID a su primer bloque y la búsqueda fallaría).
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
        expires_at = _dt.datetime.fromisoformat(expires_at_str)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=_dt.timezone.utc)
        if expires_at < _utcnow():
            raise RegistrationError("TOKEN_EXPIRED", "Token expirado", 403)
    except (ValueError, TypeError) as exc:
        raise RegistrationError("INVALID_TOKEN", "Expiración malformada", 403) from exc

    if reg.registration_status != "PENDING":
        # ya verificada o cancelada
        return reg

    slots_taken, _ = count_active_registrations(db, event.id)
    capacity_full = event.capacity_max is not None and slots_taken >= event.capacity_max

    if capacity_full and not event.waiting_list_enabled:
        # El slot se llenó mientras esperaba verificación — waitlist forzado.
        raise RegistrationError("EVENT_FULL", "El evento se llenó antes de tu verificación", 409)

    if capacity_full and event.waiting_list_enabled:
        reg.registration_status = "WAITLIST"
        reg.waiting_list_position = (reg.waiting_list_position or 0)
    else:
        reg.registration_status = "CONFIRMED"
        reg.confirmed_at = _utcnow()
        _issue_qr(db, reg)
        _issue_cancel_token(db, reg)

    # Limpieza de campos de verificación usados.
    extras = dict(reg.extras or {})
    extras.pop("_verify_token_hash", None)
    extras.pop("_verify_expires_at", None)
    reg.extras = extras

    db.commit()
    db.refresh(reg)

    # Email con el QR tras verificar (best-effort), igual que el path auto-confirmado.
    if reg.registration_status == "CONFIRMED":
        _send_confirmation_email(db, event, reg, reg.persona, public_base_url)
    return reg


# ── Cancelación (con promoción automática de waitlist) ──────────────────────


def cancel(db: Session, event: models.CrmEvent, reg: models.EventRegistration) -> models.EventRegistration:
    """Marca una inscripción como CANCELLED (soft-delete).

    Si el evento tenía aforo lleno y existe waitlist, promueve
    automáticamente al primero de la cola a CONFIRMED + genera QR + email.
    """
    if reg.registration_status == "CANCELLED":
        return reg

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
    """Promueve al primer inscrito en WAITLIST (menor waiting_list_position)."""
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
    _issue_qr(db, next_in_line)
    _issue_cancel_token(db, next_in_line)
    db.flush()

    # Re-numerar la cola restante (mantener positions consecutivos).
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
    for idx, r in enumerate(remaining, start=1):
        r.waiting_list_position = idx

    # Email al promovido (best-effort).
    try:
        if next_in_line.persona and next_in_line.persona.email:
            from backend.services.email import send_email
            from html import escape
            html = f"""
            <h2>¡Tu inscripción a {escape(event.name)} fue confirmada!</h2>
            <p>Hola <strong>{escape(next_in_line.persona.first_name or '')}</strong>,</p>
            <p>Se liberó un cupo. Ya estás confirmado para el evento.</p>
            """
            send_email(to=next_in_line.persona.email, subject=f"Cupo confirmado: {event.name}", html=html)
    except Exception as exc:
        log.warning("Failed to send promotion email for reg %s: %s", next_in_line.id, exc)


# ── Consulta pública de estado ───────────────────────────────────────────────


def find_by_email_or_phone(
    db: Session, event_id, email: Optional[str] = None, phone: Optional[str] = None
) -> Optional[models.EventRegistration]:
    """Encuentra la inscripción activa más reciente por email o phone."""
    if not email and not phone:
        return None
    q = (
        db.query(models.EventRegistration)
        .join(models.Persona, models.EventRegistration.persona_id == models.Persona.id)
        .filter(
            models.EventRegistration.event_id == event_id,
            models.EventRegistration.deleted_at.is_(None),
        )
    )
    from sqlalchemy import or_
    conditions = []
    if email:
        conditions.append(models.Persona.email == email)
    if phone:
        conditions.append(models.Persona.phone == phone)
    return q.filter(or_(*conditions)).order_by(models.EventRegistration.created_at.desc()).first()


def is_event_open_for_registration(event: models.CrmEvent, now=None) -> bool:
    """Indica window abierta al público. False si evento no requiere registration."""
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

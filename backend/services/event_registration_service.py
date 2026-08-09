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
import os
import secrets
import uuid
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas

log = logging.getLogger(__name__)


# ── Constantes ───────────────────────────────────────────────────────────────

QR_PREFIX = "CCF-EVT-"
VERIFY_PREFIX = "CCF-VER-"
CANCEL_PREFIX = "CCF-CXL-"
QR_EXPIRY_DAYS = 365
VERIFY_EXPIRY_HOURS = 24
CANCEL_EXPIRY_HOURS = 72

# ── Rol contextual por evento (plan_clasificador_contextual) ─────────────────
DEFAULT_PARTICIPANT_ROLE = "VISITANTE_EVENTO"
PARTICIPANT_ROLES = frozenset(
    {
        "VISITANTE_EVENTO",  # Visitante o participante general
        "CONTACTO_EVANGELISTICO",  # Contacto captado en contexto evangelístico
        "MIEMBRO",  # Miembro participante
        "SERVIDOR",  # Persona que presta servicio
        "INVITADO",  # Persona invitada especialmente
        "VOLUNTARIO",  # Persona que colabora voluntariamente
    }
)

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


def is_cancel_token_expired(reg: models.EventRegistration) -> bool:
    """El token de cancelación expira a las ``CANCEL_EXPIRY_HOURS`` (72h).

    El token se emite junto al QR en el momento de la confirmación, así que
    la expiración se ancla a ``qr_generated_at`` (el QR link embebe el token
    de cancelación; el plan §4.3 fija 72h de validez).
    """
    if not (reg.extras or {}).get("_cancel_token_hash"):
        return True
    if not reg.qr_generated_at:
        return True
    expires_at = reg.qr_generated_at + _dt.timedelta(hours=CANCEL_EXPIRY_HOURS)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=_dt.timezone.utc)
    return expires_at < _utcnow()


def find_by_qr_token(db: Session, qr_token_plain: str) -> Optional[models.EventRegistration]:
    """Busca la inscripción activa cuyo ``qr_token_hash`` coincide con el QR plano.

    El token plano nunca se persiste (``qr_token`` queda NULL en DB): la
    búsqueda deriva el sha256 del secret y compara contra el hash — mismo
    patrón que ``Persona.scanner_token_hash`` (``models_crm.py:452``).
    """
    if not qr_token_plain or not qr_token_plain.startswith(QR_PREFIX):
        return None
    token_hash = hash_token(qr_token_plain)
    if not token_hash:
        return None
    return (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.qr_token_hash == token_hash,
            models.EventRegistration.deleted_at.is_(None),
        )
        .first()
    )


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

    Prioridad email > phone para evitar ambigüedad cuando dos personas
    distintas comparten el mismo email/phone (orden determinístico).
    """
    persona = None
    if email:
        persona = db.query(models.Persona).filter(models.Persona.email == email).first()
    if persona is None and phone:
        persona = db.query(models.Persona).filter(models.Persona.phone == phone).first()

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


# ── Rol contextual por evento (plan_clasificador_contextual) ─────────────────


def normalize_participant_role(role_code: Optional[str]) -> str:
    """Normaliza y valida un código de rol contextual.

    - ``None`` / vacío → ``DEFAULT_PARTICIPANT_ROLE`` (VISITANTE_EVENTO).
    - Trim + upper (``" visitante_evento "`` → ``"VISITANTE_EVENTO"``).
    - Códigos fuera del catálogo → ``RegistrationError`` 422 (contrato §3).
    """
    if not role_code or not role_code.strip():
        return DEFAULT_PARTICIPANT_ROLE
    code = role_code.strip().upper()
    if code not in PARTICIPANT_ROLES:
        raise RegistrationError(
            "INVALID_PARTICIPANT_ROLE",
            f"Rol contextual desconocido: {role_code}",
            status_code=422,
        )
    return code


def resolve_participant_role(
    event: models.CrmEvent,
    reg: Optional[models.EventRegistration] = None,
    requested: Optional[str] = None,
) -> str:
    """Resuelve el rol contextual efectivo de una participación.

    Prioridad (de mayor a menor):
        1. ``requested`` — override explícito (solo usuarios autorizados).
        2. ``reg.participant_role_code`` — rol ya persistido en la inscripción.
        3. ``event.participant_role_code`` — rol por defecto del evento.
        4. ``DEFAULT_PARTICIPANT_ROLE`` (``VISITANTE_EVENTO``).
    """
    if requested is not None:
        return normalize_participant_role(requested)
    if reg is not None and reg.participant_role_code:
        return normalize_participant_role(reg.participant_role_code)
    if event.participant_role_code:
        return normalize_participant_role(event.participant_role_code)
    return DEFAULT_PARTICIPANT_ROLE


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
            "WAITLIST" if capacity_full else ("PENDING" if event.requires_email_verification else "CONFIRMED")
        )
        existing.waiting_list_position = waitlist_count + 1 if capacity_full else None
        # plan_clasificador_contextual: hereda el rol por defecto del evento
        # en la reactivación (la inscripción se trata como nueva).
        existing.participant_role_code = normalize_participant_role(event.participant_role_code)
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
                "WAITLIST" if capacity_full else ("PENDING" if event.requires_email_verification else "CONFIRMED")
            ),
            waiting_list_position=waitlist_count + 1 if capacity_full else None,
            extras=payload.extras or {},
            source="public_form",
            # plan_clasificador_contextual: toda inscripción pública hereda el
            # rol contextual por defecto del evento.
            participant_role_code=normalize_participant_role(event.participant_role_code),
        )
        db.add(reg)
        db.flush()

    # Generar QR solo si está CONFIRMED (no WAITLIST ni PENDING sin verificar).
    qr_token_plain = None
    cancel_token_plain = None
    if reg.registration_status == "CONFIRMED":
        reg.confirmed_at = _utcnow()
        qr_token_plain = _issue_qr(db, reg)
        cancel_token_plain = _issue_cancel_token(db, reg)

    db.commit()
    db.refresh(reg)

    # Email de confirmación (siempre).
    if reg.registration_status == "CONFIRMED":
        _send_confirmation_email(
            db,
            event,
            reg,
            persona,
            public_base_url,
            qr_token_plain=qr_token_plain,
            cancel_token_plain=cancel_token_plain,
        )
    elif reg.registration_status == "PENDING":
        verify_token, _ = generate_verify_token(reg.id)
        extras = dict(reg.extras or {})
        extras["_verify_token_hash"] = hash_token(verify_token)
        extras["_verify_expires_at"] = (_utcnow() + _dt.timedelta(hours=VERIFY_EXPIRY_HOURS)).isoformat()
        reg.extras = extras
        # Persiste el hash ANTES del envío: un flush sin commit se pierde al
        # cerrar la sesión del request y la verificación nunca podría resolverse.
        db.commit()
        db.refresh(reg)
        _send_verification_email(db, event, reg, persona, public_base_url, verify_token)

    return reg


def _issue_qr(db: Session, reg: models.EventRegistration) -> str:
    """Genera QR token + hash + marca qr_generated_at. Idempotente.

    Por seguridad (regla de "no persistir secrets planos en DB"):
    - persiste ``qr_token_hash`` (sha256 del secret) — usado por check-in.
    - NO persiste ``qr_token`` plano en la columna DB.
    - ``qr_token`` en DB queda ``None`` permanentemente; el check-in
      valida solo el ``qr_token_hash`` (con ``secrets.compare_digest``).

    El token plano se retorna al caller para el email de confirmación.
    Además se guarda en ``reg._qr_token_transient`` (atributo Python no
    persistido) para que tests / helpers de la misma sesión puedan
    recuperarlo sin reproducir el envío — útil para verificar el flujo
    end-to-end sin exponer el token en disco.

    Retorna el token plano (volatile, never persisted).
    """
    token, token_hash = generate_qr_token(reg.event_id, reg.persona_id)
    reg.qr_token_hash = token_hash
    reg.qr_generated_at = _utcnow()
    reg._qr_token_transient = token  # transient — nunca persistido en DB
    db.flush()
    return token


def _issue_cancel_token(db: Session, reg: models.EventRegistration) -> str:
    """Genera token de cancelación embebido en el QR link. Idempotente.

    Persiste solo ``_cancel_token_hash`` (regex sha256 del secret) en
    ``reg.extras``; el token plano se retorna al caller para el email.
    Nunca se persiste el token plano en DB.
    """
    secret = secrets.token_hex(16)
    cancel_token = f"{CANCEL_PREFIX}{reg.id}-{secret}"
    cancel_hash = hashlib.sha256(secret.encode()).hexdigest()
    extras = dict(reg.extras or {})
    extras["_cancel_token_hash"] = cancel_hash
    reg.extras = extras
    reg._cancel_token_transient = cancel_token  # transient — nunca persistido
    db.flush()
    return cancel_token


def _send_confirmation_email(
    db: Session,
    event: models.CrmEvent,
    reg: models.EventRegistration,
    persona: models.Persona,
    public_base_url: str,
    *,
    qr_token_plain: str | None = None,
    cancel_token_plain: str | None = None,
) -> None:
    """Envía el email de confirmación con el QR (visible inline via token).

    Los tokens se inyectan desde el caller como kwargs (volatile, nunca leídos
    de DB) — el email se construye con el token plano del momento, no persistido.
    """
    if not persona.email:
        return
    try:
        from html import escape

        from backend.services.email import send_email

        qr_link = ""
        cancel_link = ""
        if qr_token_plain:
            # El token de cancelación va embebido en el QR link (plan §4.1):
            # la página pública de ticket lo usa para la auto-cancelación.
            cancel_param = f"&cancel={cancel_token_plain}" if cancel_token_plain else ""
            qr_link = f"{public_base_url}/public/events/{event.id}/qr?token={qr_token_plain}{cancel_param}".strip()
            if cancel_token_plain:
                cancel_link = f"{public_base_url}/public/events/{event.id}/cancel?token={cancel_token_plain}".strip()

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
        {f'<p>Tu QR: <a href="{escape(qr_link)}">descargar</a></p>' if qr_link else ""}
        {f'<p style="font-size:12px;color:#9ca3af;">¿No podrás asistir? <a href="{escape(cancel_link)}">Cancela tu inscripción</a>.</p>' if cancel_link else ""}
        <p>¡Te esperamos!</p>
        """
        send_email(to=persona.email, subject=f"Confirmación: {event.name}", html=html)
    except (OSError, ConnectionError, RuntimeError) as exc:
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
        from html import escape

        from backend.services.email import send_email

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
    except (OSError, ConnectionError, RuntimeError) as exc:
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

    # Race de aforo (plan §7, fix #3): serializa conteo+update por evento
    # bloqueando la fila del CrmEvent (no-op en SQLite; efectivo en Postgres).
    # Sin este lock, dos verificaciones concurrentes pueden leer
    # slots_taken < capacity y sobrevender el aforo.
    db.query(models.CrmEvent).with_for_update().filter(models.CrmEvent.id == event.id).first()

    slots_taken, _ = count_active_registrations(db, event.id)
    capacity_full = event.capacity_max is not None and slots_taken >= event.capacity_max

    if capacity_full and not event.waiting_list_enabled:
        # El slot se llenó mientras esperaba verificación — waitlist forzado.
        raise RegistrationError("EVENT_FULL", "El evento se llenó antes de tu verificación", 409)

    qr_token_plain = None
    cancel_token_plain = None
    if capacity_full and event.waiting_list_enabled:
        reg.registration_status = "WAITLIST"
        reg.waiting_list_position = reg.waiting_list_position or 0
    else:
        reg.registration_status = "CONFIRMED"
        reg.confirmed_at = _utcnow()
        qr_token_plain = _issue_qr(db, reg)
        cancel_token_plain = _issue_cancel_token(db, reg)

    # plan_clasificador_contextual: backfill del rol para inscripciones creadas
    # antes de la migración (participant_role_code NULL → hereda el del evento).
    if not reg.participant_role_code:
        reg.participant_role_code = normalize_participant_role(event.participant_role_code)

    # Limpieza de campos de verificación usados.
    extras = dict(reg.extras or {})
    extras.pop("_verify_token_hash", None)
    extras.pop("_verify_expires_at", None)
    reg.extras = extras

    db.commit()
    db.refresh(reg)

    # Email con el QR tras verificar (best-effort), igual que el path auto-confirmado.
    if reg.registration_status == "CONFIRMED":
        _send_confirmation_email(
            db,
            event,
            reg,
            reg.persona,
            public_base_url,
            qr_token_plain=qr_token_plain,
            cancel_token_plain=cancel_token_plain,
        )
    return reg


# ── Cancelación (con promoción automática de waitlist) ──────────────────────


def cancel(db: Session, event: models.CrmEvent, reg: models.EventRegistration) -> models.EventRegistration:
    """Marca una inscripción como CANCELLED (soft-delete).

    Si el evento tenía aforo lleno y existe waitlist, promueve
    automáticamente al primero de la cola a CONFIRMED + genera QR + email.
    """
    if reg.registration_status == "CANCELLED":
        return reg

    # Race de aforo (plan §7, fix #3): bloquear la fila del evento para
    # serializar la promoción del waitlist — sin lock, dos cancelaciones
    # concurrentes podrían promover al mismo waitlister dos veces.
    db.query(models.CrmEvent).with_for_update().filter(models.CrmEvent.id == event.id).first()

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
    """Promueve al primer inscrito en WAITLIST (menor waiting_list_position).

    Caller ya debe haber tomado ``with_for_update`` sobre el CrmEvent
    (ver ``cancel``) para evitar races entre dos promociones concurrentes.
    """
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

    # Email al promovido (best-effort) — incluye el QR para que el usuario
    # pueda presentarlo al evento.
    try:
        if next_in_line.persona and next_in_line.persona.email:
            from html import escape

            from backend.services.email import send_email

            public_base_url = os.environ.get("CCF_PUBLIC_BASE_URL", "https://ccf.co")
            qr_link = f"{public_base_url}/public/events/{event.id}/qr?token={qr_token_plain}"
            if cancel_token_plain:
                qr_link += f"&cancel={cancel_token_plain}"
            html = f"""
            <h2>¡Tu inscripción a {escape(event.name)} fue confirmada!</h2>
            <p>Hola <strong>{escape(next_in_line.persona.first_name or "")}</strong>,</p>
            <p>Se liberó un cupo. Ya estás confirmado para el evento.</p>
            <p>Tu QR: <a href="{escape(qr_link)}">ver ticket</a></p>
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


# ── Funciones recuperadas de e0ddb8b0 (cierre, walk-in, followup CRM) ──


def _event_row_lock(db: Session, event: models.CrmEvent):
    return db.query(models.CrmEvent).with_for_update().filter(models.CrmEvent.id == event.id).first()


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
        sede_id=case.sede_id,
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
    return {
        "closed": True,
        "idempotent": False,
        "absent": absent,
        "event_id": str(event.id),
        "session_date": session_date.isoformat(),
    }

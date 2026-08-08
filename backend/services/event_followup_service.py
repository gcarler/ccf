"""Seguimiento persistente por inscripción para campañas de eventos."""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets
from html import escape

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import models

ACTIVE_STATUSES = {"PENDING", "CONFIRMED", "WAITLIST", "CHECKED_IN", "ABSENT"}

# Catálogo contractual inicial del plan de eventos. Las plantillas se clonan
# por evento: una edición administrativa no afecta a otro evento de la sede.
DEFAULT_EVENT_CAMPAIGNS = (
    {
        "key": "confirmation",
        "name": "Confirmación de inscripción",
        "trigger_type": "RELATIVE_TO_REGISTRATION",
        "offset": 0,
        "statuses": ["CONFIRMED"],
        "communication_type": "OPERATIONAL",
        "content": "Hola {{nombre}}, tu inscripción a {{evento_nombre}} está confirmada. Fecha: {{evento_fecha}}. Lugar: {{evento_lugar}}.",
    },
    {
        "key": "reminder_7d",
        "name": "Recordatorio 7 días",
        "trigger_type": "RELATIVE_TO_EVENT",
        "offset": -10080,
        "statuses": ["PENDING", "CONFIRMED", "WAITLIST", "CHECKED_IN"],
        "communication_type": "ROUTINE",
        "content": "Te esperamos en {{evento_nombre}} el {{evento_fecha}}. Lugar: {{evento_lugar}}.",
    },
    {
        "key": "reminder_24h",
        "name": "Recordatorio 24 horas",
        "trigger_type": "RELATIVE_TO_EVENT",
        "offset": -1440,
        "statuses": ["PENDING", "CONFIRMED", "WAITLIST", "CHECKED_IN"],
        "communication_type": "ROUTINE",
        "content": "Mañana es {{evento_nombre}}. Fecha: {{evento_fecha}}. Lugar: {{evento_lugar}}.",
    },
    {
        "key": "operational_update",
        "name": "Aviso de cambio operativo",
        "trigger_type": "MANUAL",
        "offset": None,
        "statuses": list(ACTIVE_STATUSES),
        "communication_type": "OPERATIONAL",
        "content": "Actualización importante de {{evento_nombre}}: {{evento_descripcion}}. Fecha: {{evento_fecha}}. Lugar: {{evento_lugar}}.",
    },
    {
        "key": "welcome",
        "name": "Bienvenida al evento",
        "trigger_type": "RELATIVE_TO_EVENT",
        "offset": 0,
        "statuses": ["CONFIRMED", "CHECKED_IN"],
        "communication_type": "PASTORAL",
        "content": "¡Bienvenido a {{evento_nombre}}! Te esperamos en {{evento_lugar}}.",
    },
    {
        "key": "post_event_thanks",
        "name": "Agradecimiento y resumen",
        "trigger_type": "RELATIVE_TO_EVENT",
        "offset": 1440,
        "statuses": ["CHECKED_IN"],
        "communication_type": "PASTORAL",
        "content": "Gracias por acompañarnos en {{evento_nombre}}. Esperamos verte nuevamente.",
    },
    {
        "key": "absence_followup",
        "name": "Contacto por ausencia",
        "trigger_type": "MANUAL",
        "offset": None,
        "statuses": ["ABSENT"],
        "communication_type": "PASTORAL",
        "content": "Te extrañamos en {{evento_nombre}}. Si necesitas ayuda o deseas conocer el siguiente paso, estamos para acompañarte.",
    },
)


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _as_utc(value: dt.datetime) -> dt.datetime:
    """Normaliza datetimes de PostgreSQL/SQLite al mismo contrato UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _canonical_identifier_type(identifier_type: str) -> str:
    normalized = identifier_type.strip().lower()
    return "email" if normalized == "email" else normalized.upper()


def _mask_recipient(persona: models.Persona | None, channel: str) -> str | None:
    if not persona:
        return None
    if channel == "EMAIL" and persona.email:
        local, _, domain = persona.email.partition("@")
        return f"{(local[:1] or '*')}***@{domain}" if domain else "***"
    phone = persona.phone or persona.mobile_phone
    if phone:
        return f"***{phone[-4:]}"
    return None


def _eligible_statuses(campaign: models.EventCampaign) -> set[str]:
    statuses = campaign.target_status or ["CONFIRMED"]
    if not isinstance(statuses, list):
        statuses = [statuses]
    return {str(value).upper() for value in statuses}


def _communication_key(campaign: models.EventCampaign, event_update_id: str | None = None) -> str:
    suffix = event_update_id or "base"
    return f"event-campaign:{campaign.id}:{suffix}"


def materialize_campaign_for_registration(
    db: Session,
    registration: models.EventRegistration,
    *,
    event_update_id: str | None = None,
) -> list[models.EventCommunicationDelivery]:
    """Crea las entregas aplicables sin duplicarlas.

    La unicidad de la tabla protege además contra dos peticiones concurrentes;
    la consulta previa evita objetos duplicados en la misma sesión.
    """
    if registration.deleted_at is not None or registration.registration_status == "CANCELLED":
        return []
    campaigns = (
        db.query(models.EventCampaign)
        .filter(
            models.EventCampaign.event_id == registration.event_id,
            models.EventCampaign.is_active.is_(True),
            models.EventCampaign.deleted_at.is_(None),
        )
        .all()
    )
    created: list[models.EventCommunicationDelivery] = []
    for campaign in campaigns:
        if registration.registration_status not in _eligible_statuses(campaign):
            continue
        key = _communication_key(campaign, event_update_id)
        existing = (
            db.query(models.EventCommunicationDelivery)
            .filter(
                models.EventCommunicationDelivery.registration_id == registration.id,
                models.EventCommunicationDelivery.campaign_id == campaign.id,
                models.EventCommunicationDelivery.communication_key == key,
            )
            .first()
        )
        if existing:
            continue
        persona = registration.persona
        channel = str(campaign.canal or "EMAIL").upper()
        communication_type = str(campaign.communication_type or "ROUTINE").upper()
        consent_rule = {
            "OPERATIONAL": "REQUIRED_OPERATIONAL",
            "PASTORAL": "CONSENTED_PASTORAL",
        }.get(communication_type, "ROUTINE_TRANSACTIONAL")
        channel_available = bool(
            persona
            and ((channel == "EMAIL" and persona.email) or (channel in {"WHATSAPP", "SMS"} and (persona.phone or persona.mobile_phone)))
        )
        preferred = {str(value).upper() for value in (registration.preferred_channels or [])}
        channel_allowed = not preferred or channel in preferred
        consent_allowed = communication_type == "OPERATIONAL" or (
            communication_type == "ROUTINE" and registration.transactional_notifications_enabled
        ) or (
            communication_type == "PASTORAL" and registration.communication_consent and not registration.marketing_opt_out_at
        )
        if not consent_allowed:
            status, skip_reason = "SKIPPED", "OPT_OUT"
        elif not channel_allowed:
            status, skip_reason = "SKIPPED", "PREFERRED_CHANNEL"
        elif not channel_available:
            status, skip_reason = "SKIPPED", "NO_CHANNEL"
        else:
            status, skip_reason = "QUEUED", None
        delivery = models.EventCommunicationDelivery(
            registration_id=registration.id,
            campaign_id=campaign.id,
            event_update_id=event_update_id,
            communication_key=key,
            channel=channel,
            recipient_masked=_mask_recipient(persona, channel),
            status=status,
            skip_reason=skip_reason,
            consent_rule_applied=consent_rule,
            next_attempt_at=_utcnow() if status == "QUEUED" else None,
            payload_version=event_update_id or "base",
        )
        # La consulta previa evita trabajo en la misma sesión, pero la
        # restricción única es la autoridad ante dos workers concurrentes.
        # Un savepoint permite absorber el IntegrityError sin invalidar la
        # transacción exterior y volver a usar la entrega ya materializada.
        try:
            with db.begin_nested():
                db.add(delivery)
                db.flush()
        except IntegrityError:
            existing = (
                db.query(models.EventCommunicationDelivery)
                .filter(
                    models.EventCommunicationDelivery.registration_id == registration.id,
                    models.EventCommunicationDelivery.campaign_id == campaign.id,
                    models.EventCommunicationDelivery.communication_key == key,
                )
                .first()
            )
            if existing is None:
                raise
            continue
        created.append(delivery)
    return created


def materialize_campaign_for_event(
    db: Session,
    event: models.CrmEvent,
    *,
    event_update_id: str | None = None,
) -> int:
    registrations = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
            models.EventRegistration.registration_status != "CANCELLED",
        )
        .all()
    )
    count = 0
    for registration in registrations:
        count += len(materialize_campaign_for_registration(db, registration, event_update_id=event_update_id))
    return count


def materialize_campaign_deliveries(
    db: Session,
    campaign: models.EventCampaign,
    *,
    event_update_id: str | None = None,
) -> int:
    registrations = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == campaign.event_id,
            models.EventRegistration.deleted_at.is_(None),
            models.EventRegistration.registration_status.in_(list(_eligible_statuses(campaign))),
        )
        .all()
    )
    count = 0
    for registration in registrations:
        count += len(materialize_campaign_for_registration(db, registration, event_update_id=event_update_id))
    return count


def _ensure_default_category(db: Session) -> models.CategoriaRecurso:
    category = db.query(models.CategoriaRecurso).filter(models.CategoriaRecurso.nombre == "Eventos").first()
    if category:
        return category
    category = models.CategoriaRecurso(nombre="Eventos", activo=True)
    try:
        with db.begin_nested():
            db.add(category)
            db.flush()
    except IntegrityError:
        category = db.query(models.CategoriaRecurso).filter(models.CategoriaRecurso.nombre == "Eventos").first()
        if category is None:
            raise
    return category


def _ensure_default_template(
    db: Session,
    event: models.CrmEvent,
    category: models.CategoriaRecurso,
    definition: dict,
) -> models.PlantillaMensaje:
    title = f"Evento {event.id} · {definition['key']}"
    template = (
        db.query(models.PlantillaMensaje)
        .filter(
            models.PlantillaMensaje.sede_id == event.sede_id,
            models.PlantillaMensaje.titulo == title,
        )
        .first()
    )
    if template:
        if not template.activo:
            template.activo = True
        return template
    template = models.PlantillaMensaje(
        sede_id=event.sede_id,
        categoria_id=category.id,
        titulo=title,
        canal=models.CanalEnvio.EMAIL,
        contenido_texto=definition["content"],
        variables_requeridas=["nombre", "evento_nombre", "evento_fecha", "evento_lugar"],
        activo=True,
    )
    db.add(template)
    db.flush()
    return template


def ensure_default_event_campaigns(
    db: Session,
    event: models.CrmEvent,
) -> list[models.EventCampaign]:
    """Crea/reutiliza el catálogo estándar sin tocar campañas personalizadas.

    El lock del evento serializa dos configuraciones concurrentes para que la
    consulta de plantillas/campañas y sus inserts formen una operación única.
    Las campañas soft-deleted no forman parte del catálogo activo y se recrean
    con una nueva fila, preservando el histórico.
    """
    if not event.requires_registration or event.sede_id is None:
        return []
    locked_event = (
        db.query(models.CrmEvent)
        .with_for_update()
        .filter(models.CrmEvent.id == event.id)
        .first()
    )
    if locked_event is None:
        return []
    event = locked_event
    category = _ensure_default_category(db)
    existing = {
        campaign.default_key: campaign
        for campaign in db.query(models.EventCampaign)
        .filter(
            models.EventCampaign.event_id == event.id,
            models.EventCampaign.default_key.isnot(None),
            models.EventCampaign.deleted_at.is_(None),
        )
        .all()
        if campaign.default_key
    }
    result = []
    for definition in DEFAULT_EVENT_CAMPAIGNS:
        if definition["key"] in existing:
            result.append(existing[definition["key"]])
            continue
        template = _ensure_default_template(db, event, category, definition)
        campaign = models.EventCampaign(
            event_id=event.id,
            name=definition["name"],
            default_key=definition["key"],
            plantilla_id=template.id,
            canal="EMAIL",
            communication_type=definition["communication_type"],
            trigger_type=definition["trigger_type"],
            trigger_offset_minutes=definition["offset"],
            target_status=definition["statuses"],
            is_active=True,
        )
        try:
            with db.begin_nested():
                db.add(campaign)
                db.flush()
        except IntegrityError:
            campaign = (
                db.query(models.EventCampaign)
                .filter(
                    models.EventCampaign.event_id == event.id,
                    models.EventCampaign.default_key == definition["key"],
                    models.EventCampaign.deleted_at.is_(None),
                )
                .first()
            )
            if campaign is None:
                raise
        result.append(campaign)
    for campaign in result:
        materialize_campaign_deliveries(db, campaign)
    return result


def delivery_communication_key(campaign_id, event_update_id: str | None = None) -> str:
    suffix = event_update_id or "base"
    return f"event-campaign:{campaign_id}:{suffix}"


def normalize_identifier(value: str | None, *, identifier_type: str) -> str:
    identifier_type = _canonical_identifier_type(identifier_type)
    raw = (value or "").strip().lower() if identifier_type == "email" else "".join((value or "").split()).upper()
    return raw


def identifier_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def mask_identifier(value: str, identifier_type: str) -> str:
    if identifier_type == "email":
        local, _, domain = value.partition("@")
        return f"{local[:1]}***@{domain}" if domain else "***"
    return f"***{value[-4:]}"


def _find_persona(db: Session, event: models.CrmEvent, identifier_type: str, normalized: str):
    query = db.query(models.Persona).filter(models.Persona.sede_id == event.sede_id)
    if identifier_type == "email":
        query = query.filter(models.Persona.email == normalized)
    else:
        query = query.filter(
            models.Persona.id_type == identifier_type,
            models.Persona.id_number == normalized,
        )
    matches = query.limit(2).all()
    if len(matches) > 1:
        raise ValueError("IDENTITY_AMBIGUOUS")
    return matches[0] if matches else None


def request_identity_challenge(
    db: Session,
    event: models.CrmEvent,
    *,
    identifier_type: str,
    identifier_value: str,
) -> dict:
    """Genera un código de posesión sin revelar si hay coincidencia."""
    identifier_type = _canonical_identifier_type(identifier_type)
    normalized = normalize_identifier(identifier_value, identifier_type=identifier_type)
    persona = _find_persona(db, event, identifier_type, normalized)
    # Nunca se persiste el valor identificador ni el código en claro.
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = models.EventIdentityChallenge(
        event_id=event.id,
        identifier_type=identifier_type,
        identifier_hash=identifier_hash(normalized),
        challenge_hash=identifier_hash(code),
        persona_id=persona.id if persona else None,
        expires_at=_utcnow() + dt.timedelta(minutes=10),
        max_attempts=5,
    )
    db.add(challenge)
    db.flush()
    if persona and persona.email:
        try:
            from backend.services.email import send_email

            send_email(
                to=persona.email,
                subject=f"Código de verificación — {event.name}",
                html=(
                    f"<p>Tu código para continuar con la inscripción a "
                    f"<strong>{escape(event.name)}</strong> es:</p>"
                    f"<p style='font-size:24px'><strong>{code}</strong></p>"
                    "<p>Válido durante 10 minutos. Si no lo solicitaste, ignora este mensaje.</p>"
                ),
            )
        except Exception:
            # El desafío existe, pero no se filtra el fallo al usuario.
            pass
    # Deliberadamente no se diferencia MATCH/NO_MATCH en la respuesta pública:
    # el desafío se entrega solo al canal verificable de una persona encontrada.
    return {
        "result": "VERIFICATION_REQUIRED",
        # No revelar siquiera un contacto enmascarado: la respuesta debe ser
        # indistinguible exista o no una persona coincidente.
        "masked_contact": None,
        # El identificador permite correlacionar el código con la solicitud,
        # pero no es suficiente para verificarlo ni contiene PII.
        "challenge_id": str(challenge.id),
    }


def verify_identity_challenge(
    db: Session,
    event: models.CrmEvent,
    *,
    identifier_type: str,
    identifier_value: str,
    code: str,
    challenge_id,
) -> dict:
    identifier_type = _canonical_identifier_type(identifier_type)
    normalized = normalize_identifier(identifier_value, identifier_type=identifier_type)
    filters = [
        models.EventIdentityChallenge.event_id == event.id,
        models.EventIdentityChallenge.identifier_type == identifier_type,
        models.EventIdentityChallenge.identifier_hash == identifier_hash(normalized),
        models.EventIdentityChallenge.consumed_at.is_(None),
        models.EventIdentityChallenge.verified_at.is_(None),
    ]
    filters.append(models.EventIdentityChallenge.id == challenge_id)
    row = (
        db.query(models.EventIdentityChallenge)
        .join(
            models.Persona,
            models.Persona.id == models.EventIdentityChallenge.persona_id,
        )
        .filter(
            *filters,
            models.Persona.sede_id == event.sede_id,
        )
        .order_by(models.EventIdentityChallenge.created_at.desc())
        .with_for_update()
        .first()
    )
    now = _utcnow()
    if not row or _as_utc(row.expires_at) <= now or row.attempt_count >= row.max_attempts:
        raise ValueError("IDENTITY_VERIFICATION_FAILED")
    if not secrets.compare_digest(row.challenge_hash, identifier_hash(code)):
        row.attempt_count += 1
        db.flush()
        raise ValueError("IDENTITY_VERIFICATION_FAILED")
    if not row.persona_id:
        raise ValueError("IDENTITY_VERIFICATION_FAILED")
    persona = row.persona
    if not persona or persona.sede_id != event.sede_id:
        raise ValueError("IDENTITY_VERIFICATION_FAILED")
    token = secrets.token_urlsafe(32)
    row.verified_identity_token_hash = identifier_hash(token)
    row.verified_at = now
    db.flush()
    return {
        "verified_identity_token": token,
        "persona": persona,
        "fields": {
            "first_name": persona.first_name,
            "last_name": persona.last_name,
            "email": persona.email,
            "phone": persona.phone,
            "id_type": persona.id_type,
            "id_number": persona.id_number,
        },
    }


def resolve_verified_identity_token(db: Session, event: models.CrmEvent, token: str):
    row = (
        db.query(models.EventIdentityChallenge)
        .join(
            models.Persona,
            models.Persona.id == models.EventIdentityChallenge.persona_id,
        )
        .filter(
            models.EventIdentityChallenge.event_id == event.id,
            models.EventIdentityChallenge.verified_identity_token_hash == identifier_hash(token),
            models.EventIdentityChallenge.consumed_at.is_(None),
            models.Persona.sede_id == event.sede_id,
        )
        .with_for_update()
        .first()
    )
    if not row or not row.verified_at or _as_utc(row.expires_at) <= _utcnow() or not row.persona_id:
        raise ValueError("IDENTITY_TOKEN_INVALID")
    if not row.persona or row.persona.sede_id != event.sede_id:
        raise ValueError("IDENTITY_TOKEN_INVALID")
    return row.persona, row


def consume_verified_identity_token(db: Session, event: models.CrmEvent, token: str):
    persona, row = resolve_verified_identity_token(db, event, token)
    row.consumed_at = _utcnow()
    db.flush()
    return persona

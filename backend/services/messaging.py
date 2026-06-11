"""Gateway unificado para comunicaciones ministeriales.

Arquitectura:
  - MessagingGateway: clase base con lógica real (SMTP para email).
  - StubMessagingGateway: reemplazo para testing/testing — registra en
    CommunicationLog pero NUNCA envía al exterior, excepto si el destinatario
    coincide con TEST_EMAIL_OVERRIDE (para pruebas controladas).
  - get_messaging_gateway(): factory FastAPI Depends que retorna una ú otra
    según settings.stub_comms.
"""

from __future__ import annotations

import logging
import smtplib
import uuid
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from backend import models
from backend.core.config import get_settings

if TYPE_CHECKING:
    from backend.core.config import Settings

logger = logging.getLogger(__name__)


def _create_log(
    db: Session,
    *,
    persona_id: str,
    channel: str,
    content: str,
    leader_id: uuid.UUID | int | str | None,
    outcome: str = "sent",
    recipient_phone: str | None = None,
    campaign_name: str | None = None,
    external_id: str | None = None,
):
    leader_uuid = None
    if leader_id is not None:
        if isinstance(leader_id, uuid.UUID):
            leader_uuid = leader_id
        else:
            try:
                leader_uuid = uuid.UUID(str(leader_id))
            except (ValueError, TypeError):
                try:
                    leader_int = int(leader_id)
                    from backend.crud.crm import resolve_persona_id_for_user
                    leader_uuid = resolve_persona_id_for_user(db, leader_int)
                except (ValueError, TypeError):
                    pass

    log = models.CommunicationLog(
        persona_id=persona_id,
        channel=channel,
        campaign_name=campaign_name,
        recipient_phone=recipient_phone,
        content=content,
        leader_id=leader_uuid,
        outcome=outcome,
        external_id=external_id or f"{channel[:2].upper()}-{uuid.uuid4().hex[:12]}",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ──────────────────────────────────────────────────────────────────────
#  MessagingGateway  (real — intenta SMTP si configurado)
# ──────────────────────────────────────────────────────────────────────

class MessagingGateway:
    """Gateway real para comunicaciones ministeriales.

    En producción, send_email() intenta entregar vía SMTP. Si SMTP no está
    configurado o falla, registra la comunicación con outcome descriptivo.
    send_whatsapp() y send_sms() registran en CommunicationLog (sin API real).
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    # -- helpers --------------------------------------------------------

    def _resolve_to_uuid(self, persona_id: str) -> uuid.UUID:
        return uuid.UUID(str(persona_id))

    def _persona_or_raise(self, db: Session, persona_id: str, *, require_email: bool = False):
        pid = self._resolve_to_uuid(persona_id)
        persona = db.query(models.Persona).filter(models.Persona.id == pid).first()
        if not persona:
            raise ValueError("Persona no encontrada")
        if require_email and not persona.email:
            raise ValueError("Persona sin correo electronico")
        return persona

    # -- public API -----------------------------------------------------

    async def send_whatsapp(
        self,
        db: Session,
        persona_id: str,
        content: str,
        leader_id: uuid.UUID | int | str | None,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        """Simula integración con API de Meta/Twilio para WhatsApp."""
        persona = self._persona_or_raise(db, persona_id)
        if not persona.phone:
            raise ValueError("Persona sin numero de telefono")

        return _create_log(
            db,
            persona_id=persona_id,
            channel="WhatsApp",
            recipient_phone=persona.phone,
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"WA-{uuid.uuid4().hex[:12]}",
        )

    async def send_sms(
        self,
        db: Session,
        persona_id: str,
        content: str,
        leader_id: uuid.UUID | int | str | None,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        """Simula integración con proveedor de SMS."""
        persona = self._persona_or_raise(db, persona_id)
        if not persona.phone:
            raise ValueError("Persona sin numero celular")

        return _create_log(
            db,
            persona_id=persona_id,
            channel="SMS",
            recipient_phone=persona.phone,
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"SMS-{uuid.uuid4().hex[:12]}",
        )

    async def send_email(
        self,
        db: Session,
        persona_id: str,
        content: str,
        leader_id: uuid.UUID | int | str | None,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        """Envía email real vía SMTP (si configurado).

        Si SMTP está configurado intenta la entrega real y registra el outcome.
        Si no, registra como ``pending_smtp_config``.
        """
        persona = self._persona_or_raise(db, persona_id, require_email=True)

        smtp_host = getattr(self._settings, "smtp_host", None)
        smtp_port = getattr(self._settings, "smtp_port", 587)
        smtp_user = getattr(self._settings, "smtp_user", None)
        smtp_pass = getattr(self._settings, "smtp_password", None)
        outcome = "sent"

        if smtp_host and smtp_user and smtp_pass:
            try:
                msg = MIMEText(content, "plain", "utf-8")
                msg["Subject"] = campaign_name or "Comunicacion CCF"
                msg["From"] = smtp_user
                msg["To"] = persona.email

                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)

                outcome = "sent_real"
                logger.info("Email real enviado a %s", persona.email)
            except Exception as exc:
                logger.warning("SMTP fallido, registrando como pending: %s", exc)
                outcome = "smtp_failed"
        else:
            outcome = "pending_smtp_config"
            logger.info("SMTP no configurado, registrando comunicacion")

        return _create_log(
            db,
            persona_id=persona_id,
            channel="Email",
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"EM-{uuid.uuid4().hex[:12]}",
            outcome=outcome,
        )


# ──────────────────────────────────────────────────────────────────────
#  StubMessagingGateway  (testing / staging — nunca envía al exterior)
# ──────────────────────────────────────────────────────────────────────

class StubMessagingGateway(MessagingGateway):
    """Gateway **stub** que NUNCA envía comunicaciones reales al exterior.

    - Todos los métodos registran en CommunicationLog con outcome ``stub``.
    - **Excepción**: si ``TEST_EMAIL_OVERRIDE`` está configurado y el email
      de la persona coincide exactamente, se delega al método padre (real).
    - Ideal para staging, CI, y entornos de prueba donde no queremos molestar
      a las personas de la iglesia.
    """

    STUB_OUTCOME = "stub"

    async def send_whatsapp(
        self,
        db: Session,
        persona_id: str,
        content: str,
        leader_id: uuid.UUID | int | str | None,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        pid = self._resolve_to_uuid(persona_id)
        persona = db.query(models.Persona).filter(models.Persona.id == pid).first()
        phone = persona.phone if persona else None

        logger.info(
            "[STUB WhatsApp] would send to persona=%s phone=%s: %.80s",
            persona_id, phone, content,
        )
        return _create_log(
            db,
            persona_id=persona_id,
            channel="WhatsApp",
            recipient_phone=phone,
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"STUB-WA-{uuid.uuid4().hex[:12]}",
            outcome=self.STUB_OUTCOME,
        )

    async def send_sms(
        self,
        db: Session,
        persona_id: str,
        content: str,
        leader_id: uuid.UUID | int | str | None,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        pid = self._resolve_to_uuid(persona_id)
        persona = db.query(models.Persona).filter(models.Persona.id == pid).first()
        phone = persona.phone if persona else None

        logger.info(
            "[STUB SMS] would send to persona=%s phone=%s: %.80s",
            persona_id, phone, content,
        )
        return _create_log(
            db,
            persona_id=persona_id,
            channel="SMS",
            recipient_phone=phone,
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"STUB-SMS-{uuid.uuid4().hex[:12]}",
            outcome=self.STUB_OUTCOME,
        )

    async def send_email(
        self,
        db: Session,
        persona_id: str,
        content: str,
        leader_id: uuid.UUID | int | str | None,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        pid = self._resolve_to_uuid(persona_id)
        persona = db.query(models.Persona).filter(models.Persona.id == pid).first()
        email = persona.email if persona else None

        # ── Excepción: TEST_EMAIL_OVERRIDE ──────────────────────────
        override = getattr(self._settings, "test_email_override", "") or ""
        if override.strip() and email and email.strip().lower() == override.strip().lower():
            logger.info(
                "[STUB] TEST_EMAIL_OVERRIDE coincide — enviando email real a %s",
                email,
            )
            return await super().send_email(
                db, persona_id, content, leader_id,
                campaign_name=campaign_name, external_id=external_id,
            )

        logger.info(
            "[STUB Email] would send to persona=%s email=%s: %.80s",
            persona_id, email, content,
        )
        return _create_log(
            db,
            persona_id=persona_id,
            channel="Email",
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"STUB-EM-{uuid.uuid4().hex[:12]}",
            outcome=self.STUB_OUTCOME,
        )


# ──────────────────────────────────────────────────────────────────────
#  Factory para FastAPI DI
# ──────────────────────────────────────────────────────────────────────

_gateway_instance: MessagingGateway | None = None
"""Singleton cache — recrear sólo si settings cambian (no debería en runtime)."""


def get_messaging_gateway() -> MessagingGateway:
    """FastAPI Depends factory.

    Retorna:
      - ``StubMessagingGateway`` si ``settings.stub_comms`` es ``True``
      - ``MessagingGateway`` en caso contrario.

    Uso en endpoints::

        from backend.services.messaging import get_messaging_gateway
        from backend.services.messaging import MessagingGateway

        @router.post("/send")
        async def send(
            ...,
            gateway: MessagingGateway = Depends(get_messaging_gateway),
        ):
            await gateway.send_email(db, persona_id, content, leader_id)
    """
    global _gateway_instance
    settings = get_settings()
    if settings.stub_comms:
        if not isinstance(_gateway_instance, StubMessagingGateway):
            _gateway_instance = StubMessagingGateway(settings)
        return _gateway_instance
    if not isinstance(_gateway_instance, MessagingGateway):
        _gateway_instance = MessagingGateway(settings)
    return _gateway_instance


def reset_gateway_singleton() -> None:
    """Útil en tests para forzar recreación entre pruebas."""
    global _gateway_instance
    _gateway_instance = None

import logging
import smtplib
import uuid
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from backend import models
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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
    leader_int = None
    if leader_id is not None:
        if isinstance(leader_id, uuid.UUID):
            leader_uuid = leader_id
        else:
            try:
                leader_uuid = uuid.UUID(str(leader_id))
            except (ValueError, TypeError):
                try:
                    leader_int = int(leader_id)
                except (ValueError, TypeError):
                    pass

    log = models.CommunicationLog(
        persona_id=persona_id,
        channel=channel,
        campaign_name=campaign_name,
        recipient_phone=recipient_phone,
        content=content,
        leader_id=leader_uuid,
        leader_user_id=leader_int,
        outcome=outcome,
        external_id=external_id or f"{channel[:2].upper()}-{uuid.uuid4().hex[:12]}",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


class MessagingGateway:
    """Gateway unificado para comunicaciones ministeriales."""

    @staticmethod
    async def send_whatsapp(
        db: Session,
        persona_id: str,
        content: str,
        leader_id: uuid.UUID | int | str | None,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        """Simula integracion con API de Meta/Twilio para WhatsApp."""
        persona = db.query(models.Persona).filter(models.Persona.id == uuid.UUID(str(persona_id))).first()
        if not persona or not persona.phone:
            raise ValueError("Persona no encontrada o sin numero de telefono")

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

    @staticmethod
    async def send_sms(
        db: Session,
        persona_id: str,
        content: str,
        leader_id: uuid.UUID | int | str | None,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        """Simula integracion con proveedor de SMS."""
        persona = db.query(models.Persona).filter(models.Persona.id == uuid.UUID(str(persona_id))).first()
        if not persona or not persona.phone:
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

    @staticmethod
    async def send_email(
        db: Session,
        persona_id: str,
        content: str,
        leader_id: uuid.UUID | int | str | None,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        """Envia email real via SMTP (si configurado)."""
        persona = db.query(models.Persona).filter(
            models.Persona.id == uuid.UUID(str(persona_id)),
        ).first()
        if not persona or not persona.email:
            raise ValueError("Persona sin correo electronico")

        smtp_host = getattr(settings, "smtp_host", None)
        smtp_port = getattr(settings, "smtp_port", 587)
        smtp_user = getattr(settings, "smtp_user", None)
        smtp_pass = getattr(settings, "smtp_password", None)
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

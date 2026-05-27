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
    member_id: int,
    channel: str,
    content: str,
    leader_id: int,
    outcome: str = "sent",
    recipient_phone: str | None = None,
    campaign_name: str | None = None,
    external_id: str | None = None,
):
    log = models.CommunicationLog(
        member_id=member_id,
        channel=channel,
        campaign_name=campaign_name,
        recipient_phone=recipient_phone,
        content=content,
        leader_id=leader_id,
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
        member_id: int,
        content: str,
        leader_id: int,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        """Simula integraciÃ³n con API de Meta/Twilio para WhatsApp."""
        persona = db.query(models.Persona).filter(models.Persona.id == member_id).first()
        if not member or not member.phone:
            raise ValueError("Miembro no encontrado o sin nÃºmero de telÃ©fono")

        # LOGICA REAL (MOCK PARA MVP)
        # AquÃ­ irÃ­a el POST a https://graph.facebook.com/v17.0/{{PHONE_ID}}/messages
        return _create_log(
            db,
            member_id=member_id,
            channel="WhatsApp",
            recipient_phone=member.phone,
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"WA-{uuid.uuid4().hex[:12]}",
        )

    @staticmethod
    async def send_sms(
        db: Session,
        member_id: int,
        content: str,
        leader_id: int,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        """Simula integraciÃ³n con proveedor de SMS."""
        persona = db.query(models.Persona).filter(models.Persona.id == member_id).first()
        if not member or not member.phone:
            raise ValueError("Miembro sin nÃºmero celular")

        return _create_log(
            db,
            member_id=member_id,
            channel="SMS",
            recipient_phone=member.phone,
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"SMS-{uuid.uuid4().hex[:12]}",
        )

    @staticmethod
    async def send_email(
        db: Session,
        member_id: int,
        content: str,
        leader_id: int,
        campaign_name: str | None = None,
        external_id: str | None = None,
    ):
        """Envía email real vía SMTP (si configurado)."""
        persona = db.query(models.Persona).filter(
            models.Persona.id == member_id,
        ).first()
        if not member or not member.email:
            raise ValueError("Miembro sin correo electrónico")

        # Intentar envío real SMTP
        smtp_host = getattr(settings, "smtp_host", None)
        smtp_port = getattr(settings, "smtp_port", 587)
        smtp_user = getattr(settings, "smtp_user", None)
        smtp_pass = getattr(settings, "smtp_password", None)
        outcome = "sent"

        if smtp_host and smtp_user and smtp_pass:
            try:
                msg = MIMEText(content, "plain", "utf-8")
                msg["Subject"] = campaign_name or "Comunicación CCF"
                msg["From"] = smtp_user
                msg["To"] = member.email

                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)

                outcome = "sent_real"
                logger.info("Email real enviado a %s", member.email)
            except Exception as exc:
                logger.warning("SMTP fallido, registrando como pending: %s", exc)
                outcome = "smtp_failed"
        else:
            outcome = "pending_smtp_config"
            logger.info("SMTP no configurado, registrando comunicación")

        return _create_log(
            db,
            member_id=member_id,
            channel="Email",
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"EM-{uuid.uuid4().hex[:12]}",
            outcome=outcome,
        )

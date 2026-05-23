import logging
import uuid

from sqlalchemy.orm import Session

from backend import models

logger = logging.getLogger(__name__)


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
        member = db.query(models.Member).filter(models.Member.id == member_id).first()
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
        member = db.query(models.Member).filter(models.Member.id == member_id).first()
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
        """Simula integraciÃ³n con proveedor de email."""
        member = db.query(models.Member).filter(models.Member.id == member_id).first()
        if not member or not member.email:
            raise ValueError("Miembro sin correo electrÃ³nico")

        return _create_log(
            db,
            member_id=member_id,
            channel="Email",
            content=content,
            leader_id=leader_id,
            campaign_name=campaign_name,
            external_id=external_id or f"EM-{uuid.uuid4().hex[:12]}",
        )

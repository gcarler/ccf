from sqlalchemy.orm import Session
from backend import models, schemas
import uuid
import logging

logger = logging.getLogger(__name__)

class MessagingGateway:
    """Gateway unificado para comunicaciones ministeriales."""
    
    @staticmethod
    async def send_whatsapp(db: Session, member_id: int, content: str, leader_id: int):
        """Simula integración con API de Meta/Twilio para WhatsApp."""
        member = db.query(models.Member).filter(models.Member.id == member_id).first()
        if not member or not member.phone:
            raise ValueError("Miembro no encontrado o sin número de teléfono")

        # LOGICA REAL (MOCK PARA MVP)
        # Aquí iría el POST a https://graph.facebook.com/v17.0/{{PHONE_ID}}/messages
        external_id = f"WA-{uuid.uuid4().hex[:12]}"
        
        log = models.CommunicationLog(
            member_id=member_id,
            channel="WhatsApp",
            recipient_phone=member.phone,
            content=content,
            leader_id=leader_id,
            outcome="sent",
            external_id=external_id
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    async def send_sms(db: Session, member_id: int, content: str, leader_id: int):
        """Simula integración con proveedor de SMS."""
        member = db.query(models.Member).filter(models.Member.id == member_id).first()
        if not member or not member.phone:
            raise ValueError("Miembro sin número celular")

        external_id = f"SMS-{uuid.uuid4().hex[:12]}"
        
        log = models.CommunicationLog(
            member_id=member_id,
            channel="SMS",
            recipient_phone=member.phone,
            content=content,
            leader_id=leader_id,
            outcome="sent",
            external_id=external_id
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

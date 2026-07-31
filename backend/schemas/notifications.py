"""Schemas Pydantic para el módulo de mensajería.

Modelos de entrada/salida para:
  - ``Notification``: bandeja de notificaciones por usuario ( ``auth_notifications`` ).
  - ``CommunicationLog``: historial de comunicaciones internas/externas.
  - ``MessagingChannel``: enum de canales válidos (M-04).

Auditoría Fase 1:
  - A-03: ``CommunicationLog`` extenedido con ``campaign_name``, ``recipient_phone``,
    ``is_read``, ``external_id`` (campos que ya existían en el ORM).
  - A-04: ``MessagingChannel`` como ``Literal`` type para validación.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from backend.schemas._common import orm_config
from backend.services.messaging_outcomes import CommunicationOutcome


class Notification(BaseModel):
    id: UUID
    persona_id: UUID
    title: str
    content: Optional[str] = None
    is_read: bool = False
    created_at: datetime
    model_config = orm_config


# A-04: Channel validado con valores canónicos.
MessagingChannel = Literal["internal", "WhatsApp", "SMS", "Email"]


class CommunicationLogCreate(BaseModel):
    persona_id: UUID
    channel: str
    content: str
    leader_id: Optional[UUID] = None
    outcome: str = CommunicationOutcome.INTERNAL_LOG.value


class CommunicationLogUpdate(BaseModel):
    channel: Optional[str] = None
    content: Optional[str] = None
    outcome: Optional[str] = None


class CommunicationLog(BaseModel):
    """A-03: Schema extendido con campos faltantes del modelo ORM."""

    id: UUID
    persona_id: UUID
    channel: str
    content: str
    leader_id: Optional[UUID] = None
    outcome: str = CommunicationOutcome.INTERNAL_LOG.value
    campaign_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    is_read: bool = False
    external_id: Optional[str] = None
    created_at: datetime
    model_config = orm_config

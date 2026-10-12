"""Modelo NotificationDelivery — registro de entregas externas (Fase 2).

Cada fila registra el intento de entrega de una notificación a un canal
externo (email). El Notification Hub escribe ``pending`` y el worker la
transiciona a ``sent`` / ``failed`` / ``suppressed`` según el resultado del
proveedor y las preferencias del usuario.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime as _datetime
from datetime import timezone as _timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped

from backend.models_shared import Base  # declarative base canónico de auth


def _utcnow() -> _datetime:
    return _datetime.now(_timezone.utc)


class NotificationDelivery(Base):
    """Trazabilidad de entrega de una notificación a un canal externo.

    Ciclo de vida:
      pending  → sent       (worker entregó al proveedor)
      pending  → failed     (agotó reintentos)
      pending  → suppressed (usuario leyó antes del envío / preferencia OFF / dedupe)
    """

    __tablename__ = "notification_deliveries"
    __table_args__ = (
        Index("ix_notif_deliv_notification_id", "notification_id"),
        Index("ix_notif_deliv_status", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    notification_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth_notifications.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    channel = Column(String(20), nullable=False)  # email
    recipient = Column(String(320), nullable=False)  # email del destinatario
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    provider_message_id = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    event_type = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_before_send = Column(Boolean, nullable=False, default=False)

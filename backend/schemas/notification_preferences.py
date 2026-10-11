"""Schemas Pydantic para preferencias de notificación (Fase 1).

Expone:
  - ``NotificationPreferenceRead``: fila individual.
  - ``NotificationPreferenceUpdate``: payload de PATCH por evento/canal.
  - ``NotificationPreferencesBulkRead``: respuesta de listado.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel

from backend.schemas._common import orm_config

NotificationChannel = Literal["in_app", "email"]


class NotificationPreferenceRead(BaseModel):
    id: UUID
    user_id: UUID
    channel: NotificationChannel
    event_type: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    model_config = orm_config


class NotificationPreferenceUpdate(BaseModel):
    channel: NotificationChannel
    event_type: str
    enabled: bool


class NotificationPreferencesBulkRead(BaseModel):
    preferences: list[NotificationPreferenceRead]

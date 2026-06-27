"""CommunicationOutcome — Enum estable para ``CommunicationLog.outcome``.

Archivo leaf (sin imports de ``backend.models``, ``backend.schemas`` o
``backend.api``) que define el contrato canónico de outcomes. Se mantiene
separado de ``backend.services.messaging`` para evitar circular imports:

    backend.schemas.notifications → backend.services.messaging
        → backend.models → backend.schemas.* (carga eager desde __init__)

re-evalúa la cadena cuando se importa el Enum desde el nivel de schemas
al cargar la app.

Los ``.value`` son los literales históricos para mantener compatibilidad
con filas existentes en BD — no requiere migración Alembic. Cuando
``messaging_outcomes`` cambie un valor, los reportes y filtros que lo
referencien vía ``Enum.value`` se actualizan en una sola edición.
"""

from __future__ import annotations

from enum import Enum


class CommunicationOutcome(str, Enum):
    """Valores canónicos para ``CommunicationLog.outcome``.

    - ``INTERNAL_LOG``: entrada de chat interno (``POST /messaging/send``).
      Actúa como sentinela histórica (= "logged", no "delivered").

    - ``SENT_REAL``: envío real completado (SMTP OK, WhatsApp/SMS entregado).
    - ``PENDING_SMTP_CONFIG``: email registrado sin SMTP configurado.
    - ``SMTP_FAILED``: intento de envío SMTP que falló.
    - ``STUB``: StubMessagingGateway (nunca envía al exterior, salvo
      ``TEST_EMAIL_OVERRIDE``).
    - ``FAILED``: fallback para errores en endpoints de envío (persona sin
      teléfono, email inválido, excepción no controlada).
    """

    INTERNAL_LOG = "sent"
    SENT_REAL = "sent_real"
    PENDING_SMTP_CONFIG = "pending_smtp_config"
    SMTP_FAILED = "smtp_failed"
    STUB = "stub"
    FAILED = "failed"


# Conjunto de outcomes que sí son entrega outbound real (vs log interno).
# Usar en reportes/filtros cuando se requiera contar mensajería real.
OUTBOUND_OUTCOMES: frozenset[CommunicationOutcome] = frozenset(
    {
        CommunicationOutcome.SENT_REAL,
        CommunicationOutcome.PENDING_SMTP_CONFIG,
        CommunicationOutcome.SMTP_FAILED,
        CommunicationOutcome.STUB,
    }
)

# Conjunto usado por heurísticas de "delivered count" (UX histórica).
# Preserva semántica actual: incluye INTERNAL_LOG y "delivered" legacy.
# ATENCIÓN: incluye INTERNAL_LOG (= "logged") — perpetúa un conteo
# inflado en ``_serialize_message_group``. Reportes nuevos de "delivered
# real" deberían usar ``OUTBOUND_OUTCOMES`` directamente.
DELIVERED_OUTCOMES: frozenset[str] = frozenset(
    {
        CommunicationOutcome.INTERNAL_LOG.value,
        CommunicationOutcome.SENT_REAL.value,
        "delivered",  # legacy sentinel no migrado al Enum
    }
)

__all__ = [
    "CommunicationOutcome",
    "OUTBOUND_OUTCOMES",
    "DELIVERED_OUTCOMES",
]

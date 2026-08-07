"""Calidad del pre-registro contextual — expiración de cancel y rutas públicas.

Reconstruido desde su bytecode (restauración de trabajo perdido): valida que
el token de cancelación expire a las 72h (anclado al QR) y que el QR del
ticket esté hash-bound (el token plano nunca se persiste), más la existencia
de las rutas públicas ``/ticket`` y ``/cancel``.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from backend import models
from backend.api.public import router
from backend.services.event_registration_service import (
    _issue_cancel_token,
    _issue_qr,
    _utcnow,
    is_cancel_token_expired,
)


def test_cancel_token_expires_and_qr_ticket_is_hash_bound():
    """El token de cancelación vence a las 72h; el QR se resuelve por hash."""

    class _FakeDB:
        """Suficiente para _issue_*: solo necesitan flush()."""

        def flush(self):
            return None

    reg = models.EventRegistration(
        id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        persona_id=uuid.uuid4(),
    )
    _issue_qr(_FakeDB(), reg)
    _issue_cancel_token(_FakeDB(), reg)

    # Recién emitido: el token de cancelación NO está expirado.
    assert is_cancel_token_expired(reg) is False

    # QR hash-bound: el token plano nunca se persiste en la columna; el hash sí.
    assert reg.qr_token is None
    assert reg.qr_token_hash
    assert (reg.extras or {}).get("_cancel_token_hash")

    # 73h después de la emisión (anclada a qr_generated_at): expirado.
    reg.qr_generated_at = _utcnow() - timedelta(hours=73)
    assert is_cancel_token_expired(reg) is True


def test_public_ticket_and_cancel_routes_exist():
    """Las rutas públicas /ticket (GET) y /cancel (POST) están registradas."""
    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/events/{event_id}/ticket" in paths
    assert "/events/{event_id}/cancel" in paths

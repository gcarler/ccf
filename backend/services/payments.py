"""
MercadoPago Payment Service

Integración con la API de MercadoPago para procesar donaciones y diezmos.
Requiere MERCADOPAGO_ACCESS_TOKEN en el .env (credentials de producción).

Uso:
    from backend.services.payments import create_donation_preference
    pref = create_donation_preference(amount=50.0, title="Diezmo", email="donante@ejemplo.com")
    # pref["init_point"] -> URL de checkout
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import mercadopago
from backend.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


@dataclass
class PaymentPreference:
    """Datos para crear una preferencia de pago en MercadoPago."""
    amount: float
    title: str
    email: Optional[str] = None
    description: Optional[str] = None
    donor_name: Optional[str] = None
    payment_type_id: str = "ticket"  # ticket, atm, credit_card, debit_card, prepaid_card
    installments: int = 1
    metadata: dict = field(default_factory=dict)


@dataclass
class PaymentResult:
    """Resultado de un pago procesado."""
    payment_id: int
    status: str
    status_detail: str
    amount: float
    email: Optional[str] = None
    donor_name: Optional[str] = None
    raw: dict = field(default_factory=dict)


def _get_sdk() -> mercadopago.SDK:
    """Retorna instancia del SDK de MercadoPago."""
    if not settings.mercadopago_access_token:
        raise RuntimeError(
            "MERCADOPAGO_ACCESS_TOKEN no configurado. "
            "Agrega la variable en el archivo .env"
        )
    return mercadopago.SDK(settings.mercadopago_access_token)


def create_donation_preference(pref: PaymentPreference) -> dict:
    """
    Crea una preferencia de pago en MercadoPago y retorna el objeto
    con init_point (URL de checkout) y id de la preferencia.

    Ejemplo de retorno:
        {
            "id": "123456789",
            "init_point": "https://www.mercadopago.com.co/checkout/v1/...",
            "sandbox_init_point": "https://sandbox.mercadopago.com.co/..."
        }
    """
    sdk = _get_sdk()

    items = [
        {
            "title": pref.title,
            "quantity": 1,
            "unit_price": round(pref.amount, 2),
            "currency_id": "COP",
        }
    ]

    payer: dict = {}
    if pref.email:
        payer["email"] = pref.email
    if pref.donor_name:
        payer["name"] = pref.donor_name

    back_urls = {
        "success": f"{settings.frontend_url}/donate?status=success",
        "failure": f"{settings.frontend_url}/donate?status=failure",
        "pending": f"{settings.frontend_url}/donate?status=pending",
    }

    preference_data: dict = {
        "items": items,
        "payer": payer,
        "back_urls": back_urls,
        "auto_return": "approved",
        "statement_descriptor": "CCF MINISTERIO",
        "notification_url": f"{settings.frontend_url}/api/donations/mercadopago/webhook",
        "metadata": {
            "source": "ccf-donate-web",
            **(pref.metadata or {}),
        },
    }

    if pref.description:
        preference_data["description"] = pref.description

    try:
        result = sdk.preference().create(preference_data)
        response = result.get("response", {})
        logger.info(
            "Preferencia MP creada: id=%s amount=%s",
            response.get("id"),
            pref.amount,
        )
        return response
    except Exception as exc:
        logger.error("Error creando preferencia MP: %s", exc)
        raise


def get_payment_status(payment_id: int) -> PaymentResult:
    """
    Consulta el estado de un pago en MercadoPago por su ID.
    Útil para verificar webhooks o consultar pagos manualmente.
    """
    sdk = _get_sdk()
    try:
        result = sdk.payment().get(payment_id)
        payment = result.get("response", {})
        logger.info(
            "Pago MP consultado: id=%s status=%s", payment_id, payment.get("status")
        )
        return PaymentResult(
            payment_id=payment.get("id", payment_id),
            status=payment.get("status", "unknown"),
            status_detail=payment.get("status_detail", ""),
            amount=float(payment.get("transaction_amount", 0)),
            email=payment.get("payer", {}).get("email"),
            donor_name=payment.get("payer", {}).get("name"),
            raw=payment,
        )
    except Exception as exc:
        logger.error("Error consultando pago MP %s: %s", payment_id, exc)
        raise


def process_webhook_notification(data: dict) -> Optional[PaymentResult]:
    """
    Procesa una notificación webhook de MercadoPago.

    El webhook envía notificaciones con estructura:
        {
            "action": "payment.created",
            "api_version": "v1",
            "data": { "id": "12345" },
            "date_created": "...",
            "id": "...",
            "live_mode": true,
            "type": "payment",
            "user_id": "..."
        }

    Retorna PaymentResult si es un pago, None si es otro tipo de notificación.
    """
    notification_type = data.get("type", "")
    action = data.get("action", "")
    resource_id = None

    if notification_type == "payment":
        resource_id = data.get("data", {}).get("id")
    elif "payment" in action:
        resource_id = data.get("data", {}).get("id")

    if resource_id:
        return get_payment_status(int(resource_id))

    logger.info("Notificación MP ignorada: type=%s action=%s", notification_type, action)
    return None

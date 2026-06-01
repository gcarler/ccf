from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import require_admin, require_module_access
from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/donations", tags=["donations"])


@router.post(
    "",
    response_model=schemas.Donation,
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
def create_donation(
    payload: schemas.DonationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
    created = crud.create_donation(db, payload)
    return created


@router.get("", response_model=List[schemas.Donation])
def list_donations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.get_donations(db, skip=skip, limit=limit)


@router.get("/total")
def donations_total(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return {"total": crud.get_total_donations_amount(db)}


@router.get("/summary")
def donations_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Resumen mensual de donaciones calculado desde la base de datos."""
    from backend.crud.crm import get_user_sede_id
    sede_id = get_user_sede_id(db, current_user.id)
    from datetime import timezone as dt_timezone
    now = datetime.now(dt_timezone.utc)
    monthly = (
        db.query(
            func.extract("month", models.Donation.created_at).label("month_num"),
            func.sum(models.Donation.amount).label("total"),
        )
        .filter(
            models.Donation.created_at
            >= now.replace(year=now.year, month=1, day=1, tzinfo=None),
            models.Donation.sede_id == sede_id,
        )
        .group_by("month_num")
        .order_by("month_num")
        .all()
    )

    month_names = {
        1: "Ene",
        2: "Feb",
        3: "Mar",
        4: "Abr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dic",
    }
    return [
        {"month": month_names.get(int(r[0]), r[0]), "amount": round(r[1])}
        for r in monthly
    ]


@router.get("/{donation_id}/certificate")
def download_certificate(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    donation = (
        db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    )
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    return {
        "certificate_id": f"CERT-DON-{donation.id}",
        "donor": donation.donor_name,
        "amount": donation.amount,
        "date": donation.created_at.isoformat(),
        "type": donation.donation_type,
        "verification_url": f"https://ccf.org/verify/don/{donation.id}",
    }


# ─── MercadoPago Integration ────────────────────────────────────────────────


class CreatePreferenceRequest(BaseModel):
    amount: float
    title: str = "Donación"
    description: Optional[str] = None
    donor_name: Optional[str] = None
    email: Optional[str] = None


@router.post("/mercadopago/create-preference")
def mercadopago_create_preference(
    payload: CreatePreferenceRequest,
    request: Request,
):
    """
    Crea una preferencia de pago en MercadoPago.
    Retorna la URL de checkout (init_point) para redirigir al donante.
    """
    try:
        from backend.services.payments import PaymentPreference, create_donation_preference

        pref = PaymentPreference(
            amount=payload.amount,
            title=payload.title,
            description=payload.description,
            donor_name=payload.donor_name,
            email=payload.email,
        )
        result = create_donation_preference(pref)
        return {
            "id": result.get("id"),
            "init_point": result.get("init_point"),
            "sandbox_init_point": result.get("sandbox_init_point"),
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        logger.error("Error creating MP preference: %s", exc)
        raise HTTPException(status_code=500, detail="Error al crear preferencia de pago")


@router.post("/mercadopago/webhook")
async def mercadopago_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook para recibir notificaciones de pago de MercadoPago.
    Configurar en el panel de MercadoPago → Webhooks → URL de notificación.

    Cuando un pago es aprobado, registra la donación en la base de datos.
    """
    try:
        data = await request.json()
    except Exception:
        data = {}

    logger.info("Webhook MP recibido: %s", json.dumps(data)[:500])

    try:
        from backend.services.payments import process_webhook_notification

        result = process_webhook_notification(data)
        if result and result.status == "approved":
            # Registrar donación en BD
            donation = models.Donation(
                amount=result.amount,
                donation_type="Diezmo",
                donor_name=result.donor_name or result.email or "Web - MercadoPago",
                notes=f"MercadoPago payment #{result.payment_id}",
            )
            db.add(donation)
            db.commit()
            logger.info(
                "Donación registrada por webhook MP: payment_id=%s amount=%s",
                result.payment_id,
                result.amount,
            )
    except Exception as exc:
        logger.error("Error procesando webhook MP: %s", exc)

    # MercadoPago espera 200 OK siempre (incluso si hay error interno)
    return {"status": "ok"}


@router.get("/mercadopago/payments/{payment_id}")
def mercadopago_payment_status(payment_id: int):
    """Consulta el estado de un pago en MercadoPago."""
    try:
        from backend.services.payments import get_payment_status

        result = get_payment_status(payment_id)
        return {
            "payment_id": result.payment_id,
            "status": result.status,
            "status_detail": result.status_detail,
            "amount": result.amount,
            "email": result.email,
            "donor_name": result.donor_name,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        logger.error("Error consultando pago MP: %s", exc)
        raise HTTPException(status_code=500, detail="Error al consultar pago")

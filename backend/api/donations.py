from __future__ import annotations

import json
import logging
from datetime import datetime
from datetime import timezone as dt_timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import get_db
from backend.core.permissions import require_admin, require_module_access
from backend.core.rate_limit import rate_limiter
from backend.core.tenant import get_user_sede_id
from backend.schemas.finance_suite import CreatePreferenceRequest

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
    # FIN-C06: Permiso correcto — antes era "read", ahora "edit"
    current_user: models.User = Depends(require_module_access("finance", "edit")),
):
    created = crud.create_donation(db, payload)
    return created


@router.get("", response_model=List[schemas.Donation])
def list_donations(
    skip: int = 0,
    limit: int = Query(100, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    sede_id = get_user_sede_id(db, current_user.id)
    return crud.get_donations(db, skip=skip, limit=limit, sede_id=sede_id)


@router.get("/total")
def donations_total(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    sede_id = get_user_sede_id(db, current_user.id)
    return {"total": crud.get_total_donations_amount(db, sede_id=sede_id)}


@router.get("/summary")
def donations_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Resumen mensual de donaciones calculado desde la base de datos."""
    sede_id = get_user_sede_id(db, current_user.id)
    now = datetime.now(dt_timezone.utc)

    # FIN-C11: Compatible con SQLite y PostgreSQL
    dialect = db.bind.dialect.name
    if dialect == "sqlite":
        month_expr = func.strftime("%m", models.Donation.created_at)
    else:
        month_expr = func.extract("month", models.Donation.created_at)

    monthly = (
        db.query(
            month_expr.label("month_num"),
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
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
    }
    return [
        {"month": month_names.get(int(r[0]), r[0]), "amount": round(r[1])}
        for r in monthly
    ]


@router.get("/{donation_id}/certificate")
def download_certificate(
    donation_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    # FIN-H11: Agregar sede check
    sede_id = get_user_sede_id(db, current_user.id)
    donation = (
        db.query(models.Donation)
        .filter(models.Donation.id == donation_id)
        .first()
    )
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    if sede_id and donation.sede_id and str(donation.sede_id) != sede_id:
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


@router.post(
    "/mercadopago/create-preference",
    dependencies=[Depends(rate_limiter(limit=5, window_seconds=60))],
)
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
    except Exception as exc:
        logger.debug("Failed to parse MercadoPago webhook JSON: %s", exc)
        data = {}

    logger.info("Webhook MP recibido: %s", json.dumps(data)[:500])

    try:
        from backend.services.payments import process_webhook_notification

        result = process_webhook_notification(data)
        if result and result.status == "approved":
            # FIN-C07: Webhook no tiene contexto de sede — sede_id=None explícito
            # La donación será visible globalmente hasta que se implemente
            # un mecanismo de match por email o preference metadata.
            donation = models.Donation(
                amount=result.amount,
                donation_type="Diezmo",
                donor_name=result.donor_name or result.email or "Web - MercadoPago",
                notes=f"MercadoPago payment #{result.payment_id}",
                sede_id=None,
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
def mercadopago_payment_status(
    payment_id: str,
    # FIN-C08: Agregar auth — antes era endpoint público
    current_user: models.User = Depends(require_module_access("finance", "read")),
):
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

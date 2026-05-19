from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend import crud, schemas, models
from backend.auth import require_admin, require_active_user
from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter


router = APIRouter(prefix="/donations", tags=["donations"])


@router.post("/", response_model=schemas.Donation, dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))])
def create_donation(
    payload: schemas.DonationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    created = crud.create_donation(db, payload)
    return created


@router.get("/", response_model=List[schemas.Donation])
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
    monthly = db.query(
        func.strftime("%m", models.Donation.created_at).label("month_num"),
        func.sum(models.Donation.amount).label("total"),
    ).filter(
        models.Donation.created_at >= datetime(timezone.utc).replace(year=datetime.now(timezone.utc).year, month=1, day=1, tzinfo=None)
    ).group_by("month_num").order_by("month_num").all()

    month_names = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
                   7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}
    return [{"month": month_names.get(int(r[0]), r[0]), "amount": round(r[1])} for r in monthly]


@router.get("/{donation_id}/certificate")
def download_certificate(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    donation = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    
    return {
        "certificate_id": f"CERT-DON-{donation.id}",
        "donor": donation.donor_name,
        "amount": donation.amount,
        "date": donation.created_at.isoformat(),
        "type": donation.donation_type,
        "verification_url": f"https://ccf.org/verify/don/{donation.id}"
    }

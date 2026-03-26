from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import crud, schemas, models
from backend.auth import require_admin
from backend.core.database import get_db


router = APIRouter(prefix="/donations", tags=["donations"])


@router.post("/", response_model=schemas.Donation)
def create_donation(
    payload: schemas.DonationCreate,
    db: Session = Depends(get_db),
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
    # Simulated monthly summary for now
    return [
        {"month": "Ene", "amount": 10500},
        {"month": "Feb", "amount": 11200},
        {"month": "Mar", "amount": 12450}
    ]


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

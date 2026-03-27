from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from backend import crud, schemas, models
from backend.core.database import get_db
from backend.auth import require_admin

router = APIRouter(prefix="/finance", tags=["Finance"])

@router.get("/funds")
def get_ministerial_funds(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Lista los fondos ministeriales. Solo para admin."""
    return crud.get_funds(db)

@router.get("/transactions")
def get_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Obtiene el historial de transacciones contables."""
    return crud.get_treasury_transactions(db)

@router.post("/donations")
def register_donation(
    person_id: Optional[uuid.UUID], 
    fund_id: int, 
    amount: float, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Registra una ofrenda. Solo para admin."""
    return crud.create_donation(db, person_id=person_id, fund_id=fund_id, amount=amount)

@router.get("/impact")
def get_mission_impact(db: Session = Depends(get_db)):
    """Muestra el impacto social. Publico."""
    return crud.get_mission_impact(db)

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend import crud, schemas, models
from backend.database import get_db
from backend.auth import get_current_user, require_admin
from backend.core.audit import record_admin_action

router = APIRouter(prefix="/finance", tags=["finance"])

@router.get("/summary")
def read_treasury_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.get_treasury_summary(db)

@router.get("/transactions", response_model=List[schemas.TreasuryTransaction])
def read_transactions(
    type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.get_treasury_transactions(db, skip=skip, limit=limit, type=type)

@router.post("/transactions", response_model=schemas.TreasuryTransaction)
def create_transaction(
    transaction: schemas.TreasuryTransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    db_tx = crud.create_treasury_transaction(db, transaction)
    
    record_admin_action(
        db,
        current_user,
        action="create_treasury_transaction",
        resource_type="treasury_transaction",
        resource_id=str(db_tx.id),
        metadata=transaction.model_dump()
    )
    
    return db_tx

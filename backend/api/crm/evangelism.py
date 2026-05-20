from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.schemas.crm import EvangelismStrategy, EvangelismStrategyCreate, EvangelismStrategyUpdate
from backend.crud.crm import (
    get_evangelism_strategies,
    create_evangelism_strategy,
    update_evangelism_strategy,
    delete_evangelism_strategy
)
from backend.api.deps import get_current_user

router = APIRouter()

@router.get("/strategies", response_model=List[EvangelismStrategy])
def read_evangelism_strategies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_evangelism_strategies(db, skip=skip, limit=limit)

@router.post("/strategies", response_model=EvangelismStrategy)
def create_strategy(strategy: EvangelismStrategyCreate, db: Session = Depends(get_db)):
    return create_evangelism_strategy(db=db, strategy=strategy)

@router.put("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def update_strategy(strategy_id: int, strategy: EvangelismStrategyUpdate, db: Session = Depends(get_db)):
    db_obj = update_evangelism_strategy(db=db, strategy_id=strategy_id, strategy=strategy)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    return db_obj

@router.delete("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    db_obj = delete_evangelism_strategy(db=db, strategy_id=strategy_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    return db_obj

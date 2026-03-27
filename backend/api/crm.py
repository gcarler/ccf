from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from backend import crud, schemas, models
from backend.core.database import get_db
from backend.auth import get_current_user, require_admin

router = APIRouter(prefix="/crm", tags=["CRM"])

@router.get("/members", response_model=List[dict])
def list_members(
    search: Optional[str] = None, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Lista miembros con filtro de busqueda ministerial."""
    return crud.get_talents(db, search=search)

@router.get("/family/{family_id}", response_model=List[dict])
def get_family(
    family_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene los miembros del nucleo familiar."""
    return crud.get_family_members(db, family_id=family_id)

@router.get("/talents", response_model=List[dict])
def search_talents(
    q: Optional[str] = None, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Buscador avanzado de talentos y habilidades."""
    return crud.get_talents(db, search=q)

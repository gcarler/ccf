from datetime import timedelta
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend import crud
from backend import models
from backend import schemas
from backend.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    normalize_role,
    record_session,
    require_active_user,
    require_admin,
    role_in,
    VALID_ROLES,
)
from backend.core.audit import record_admin_action
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter


settings = get_settings()

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limiter(limit=5, window_seconds=60)),
):
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    payload = {"sub": str(user.id), "role": normalize_role(str(user.role))}
    access_token = create_access_token(data=payload, expires_delta=timedelta(minutes=settings.access_token_expire_minutes))
    refresh_token = create_refresh_token(db, user_id=int(getattr(user, "id", 0)))
    record_session(int(getattr(user, "id", 0)), access_token)
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user.role = "estudiante"
    return crud.create_user(db=db, user=user)


@router.get("/me", response_model=schemas.TokenUser)
def me(current_user: models.User = Depends(require_active_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": normalize_role(str(current_user.role)),
    }


@router.post("/users", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    normalized_role = normalize_role(user.role)
    if normalized_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = normalized_role
    created = crud.create_user(db=db, user=user)
    record_admin_action(
        db,
        current_user,
        action="create_user",
        resource_type="user",
        resource_id=str(created.id),
        metadata={"email": created.email, "role": created.role},
    )
    return created


@router.post("/refresh", response_model=schemas.Token)
def refresh_access_token(
    payload: schemas.TokenRefreshRequest,
    db: Session = Depends(get_db),
):
    stored = crud.verify_refresh_token(db, payload.refresh_token)
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    stored_user_id = cast(int, getattr(stored, "user_id", 0))
    user_id = int(stored_user_id)
    user = crud.get_user(db, user_id)
    if not user or not getattr(user, "is_active", False):
        crud.revoke_refresh_token(db, payload.refresh_token)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive or not found")
    crud.revoke_refresh_token(db, payload.refresh_token)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": normalize_role(str(user.role))},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    new_refresh = create_refresh_token(db, user_id=int(getattr(user, "id", 0)))
    record_session(int(getattr(user, "id", 0)), access_token)
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": new_refresh}


@router.get("/enrollments/{user_id}", response_model=list[schemas.Enrollment])
def read_user_enrollments(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    current_id = int(getattr(current_user, "id", 0))
    if normalize_role(str(current_user.role)) != "admin" and current_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return crud.get_enrollments_by_user(db, user_id)

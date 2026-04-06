"""
CCF MESH - ROUTER DE AUTENTICACION V3.9 (ESTANDAR DE CALIDAD)
Maneja el inicio de sesion, registro y gestion de tokens con UUID.
"""

import logging
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend import crud, schemas, models
from backend.auth import (
    create_access_token,
    create_refresh_token,
    normalize_role,
    require_active_user,
    require_admin,
)
from backend.core.config import get_settings
from backend.core.database import get_db

settings = get_settings()
log = logging.getLogger(__name__)

router = APIRouter(tags=["Autenticacion"])


@router.post("/login", response_model=schemas.Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Inicio de sesion ministerial. Soporta Email o Username."""
    from backend.auth import verify_password  # Import local para evitar circularidad

    log.info(f"[AUTH DEBUG] Attempting login for: {form_data.username}")
    user = None
    if "@" in form_data.username:
        user = crud.get_user_by_email(db, email=form_data.username)
    else:
        user = crud.get_user_by_username(db, username=form_data.username)

    if not user:
        log.warning(f"[AUTH DEBUG] User NOT FOUND: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales ministeriales incorrectas"
        )

    log.info(f"[AUTH DEBUG] User found: {user.username} (ID: {user.id})")
    if not verify_password(form_data.password, user.password_hash):
        log.warning(f"[AUTH DEBUG] Password mismatch for: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales ministeriales incorrectas"
        )

    log.info(f"[AUTH DEBUG] Password verified. Generating token for ID: {user.id}")
    payload = {"sub": str(user.id), "role": normalize_role(str(user.role))}
    access_token = create_access_token(
        data=payload,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    refresh_token = create_refresh_token(db, int(user.id))

    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.access_token_cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )

    log.info(f"[AUTH DEBUG] Login successful for: {user.username}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


@router.post("/refresh", response_model=schemas.Token)
def refresh_access_token(
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    token_row = crud.get_valid_refresh_token(db, payload.refresh_token)
    if not token_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = crud.get_user(db, int(token_row.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    crud.revoke_refresh_token(db, payload.refresh_token)
    new_refresh_token = create_refresh_token(db, int(user.id))
    new_access_token = create_access_token(
        data={"sub": str(user.id), "role": normalize_role(str(user.role))},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh_token,
    }


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(settings.access_token_cookie_name)


@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registro de nuevos miembros."""
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya esta registrado en el ministerio")

    user.role = "estudiante"
    return crud.create_user(db=db, user=user)


@router.get("/me", response_model=schemas.TokenUser)
def get_current_ministerial_user(current_user: models.User = Depends(require_active_user)):
    """Obtiene el perfil del usuario autenticado cruzando con el perfil de miembro."""
    profile = getattr(current_user, "member_profile", None)
    return {
        "user_id": str(current_user.id),
        "username": current_user.username,
        "email": profile.email if profile and profile.email else current_user.email,
        "role": normalize_role(str(current_user.role)),
        "xp": current_user.xp or 0
    }


@router.get("/user-list", response_model=List[schemas.User])
def list_ministerial_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Lista de usuarios. Solo para administradores."""
    return crud.get_users(db, skip=skip, limit=limit)


@router.patch("/users/{user_id}", response_model=schemas.User)
def update_ministerial_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza un usuario ministerial (rol, estado, etc)."""
    user = crud.update_user(db, user_id=user_id, payload=payload)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_ministerial_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina un usuario del sistema."""
    success = crud.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return None

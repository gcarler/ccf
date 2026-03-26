import logging
import secrets
from datetime import datetime, timedelta
from typing import cast, List

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
log = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")


def _issue_password_reset_token(db: Session, user_id: int) -> None:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.password_reset_expire_minutes)
    crud.create_password_reset_token(db, user_id=user_id, token=token, expires_at=expires_at)
    log.info("Password reset token for user %s: %s", user_id, token)


def _issue_email_verification_token(db: Session, user_id: int) -> None:
    token = secrets.token_urlsafe(40)
    expires_at = datetime.utcnow() + timedelta(hours=settings.email_verification_expire_hours)
    crud.create_email_verification_token(db, user_id=user_id, token=token, expires_at=expires_at)
    log.info("Email verification token for user %s: %s", user_id, token)


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limiter(limit=5, window_seconds=60)),
):
    # Try authenticating by email first, then username
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        # Fallback search by username if email fail
        db_user = crud.get_user_by_username(db, username=form_data.username)
        if db_user and verify_password(form_data.password, db_user.password_hash):
            user = db_user
            
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    payload = {"sub": str(user.user_id), "role": normalize_role(str(user.role))}
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
    created = crud.create_user(db=db, user=user)
    _issue_email_verification_token(db, int(getattr(created, "id", 0)))
    return created


@router.get("/me", response_model=schemas.TokenUser)
def me(current_user: models.User = Depends(require_active_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": normalize_role(str(current_user.role)),
        "is_email_verified": getattr(current_user, "is_email_verified", False),
    }


@router.get("/user-list", response_model=List[schemas.User])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.get_users(db, skip=skip, limit=limit)


@router.get("/users/count")
def read_users_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return {"count": crud.get_users_count(db)}


@router.get("/stats/summary")
def read_stats_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return {
        "users": crud.get_users_count(db),
        "donations": crud.get_donations_total(db),
        "attendance": crud.get_attendance_avg(db)
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


@router.get("/enrollments/{user_id}", response_model=List[schemas.Enrollment])
def read_user_enrollments(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    current_id = int(getattr(current_user, "id", 0))
    if normalize_role(str(current_user.role)) != "admin" and current_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return crud.get_enrollments_by_user(db, user_id)


@router.post("/forgot-password")
def forgot_password(payload: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=payload.email)
    if user:
        _issue_password_reset_token(db, int(getattr(user, "id", 0)))
    return {"detail": "If the email exists we sent reset instructions"}


@router.post("/reset-password")
def reset_password(payload: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    entry = crud.get_password_reset_token(db, payload.token)
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    expires_at = getattr(entry, "expires_at", None)
    if not isinstance(expires_at, datetime) or expires_at <= datetime.utcnow():
        crud.mark_password_reset_used(db, entry)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")
    user = crud.get_user(db, int(getattr(entry, "user_id", 0)))
    if not user:
        crud.mark_password_reset_used(db, entry)
        raise HTTPException(status_code=404, detail="User not found")
    crud.update_user_password(db, user, payload.password)
    crud.mark_password_reset_used(db, entry)
    return {"detail": "Password updated"}


@router.post("/verify-email")
def verify_email(payload: schemas.EmailVerificationConfirm, db: Session = Depends(get_db)):
    entry = crud.get_email_verification_token(db, payload.token)
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    expires_at = getattr(entry, "expires_at", None)
    if not isinstance(expires_at, datetime) or expires_at <= datetime.utcnow():
        crud.mark_email_verification_used(db, entry)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")
    user = crud.get_user(db, int(getattr(entry, "user_id", 0)))
    if not user:
        crud.mark_email_verification_used(db, entry)
        raise HTTPException(status_code=404, detail="User not found")
    crud.mark_user_verified(db, user)
    crud.mark_email_verification_used(db, entry)
    return {"detail": "Email verified"}


@router.post("/resend-verification")
def resend_verification(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    if getattr(current_user, "is_email_verified", False):
        return {"detail": "Email already verified"}
    _issue_email_verification_token(db, int(getattr(current_user, "id", 0)))
    return {"detail": "Verification email sent"}


# -----------------
# UI Preferences API
# -----------------
@router.get("/me/preferences")
def get_my_preferences(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    prefs = crud.get_ui_preferences(db, str(current_user.user_id))
    return prefs.settings if prefs else {}


@router.patch("/me/preferences")
def update_my_preferences(
    settings: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user)
):
    crud.update_ui_preferences(db, str(current_user.user_id), settings)
    return {"status": "updated"}

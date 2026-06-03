"""User, auth, badges, XP, and UI preferences CRUD."""

import secrets
from typing import Optional

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import get_password_hash
from backend.crud._utils import _utcnow

# ── Users ──────────────────────────────────────────────


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    from backend.models_identity import Role

    # Look up role_id from role name to keep both fields in sync
    role_id = None
    if user.role:
        role = db.query(Role).filter(
            Role.name.ilike(user.role.replace("_", " "))
        ).first()
        if role:
            role_id = role.role_id

    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
        role_id=role_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, payload: schemas.UserUpdate):
    row = db.query(models.User).filter(models.User.id == user_id).first()
    if not row:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))

    for key, value in update_data.items():
        setattr(row, key, value)

    db.commit()
    db.refresh(row)
    return row


def delete_user(db: Session, user_id: int) -> bool:
    row = db.query(models.User).filter(models.User.id == user_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Refresh Tokens ─────────────────────────────────────


def create_refresh_token(
    db: Session,
    user_id: int,
    token: str,
    expires_at,
    ip_address: str = None,
    user_agent: str = None,
):
    row = models.RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        revoked=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_valid_refresh_token(db: Session, token: str):
    row = (
        db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    )
    if not row:
        return None
    if row.revoked:
        return None
    if row.expires_at <= _utcnow():
        return None
    return row


def revoke_refresh_token(db: Session, token: str):
    row = (
        db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    )
    if not row:
        return None
    row.revoked = True
    db.commit()
    db.refresh(row)
    return row


# ── Verification & Reset Tokens ───────────────────────────────────


def _generate_token() -> str:
    return secrets.token_urlsafe(48)


def create_verification_token(db: Session, user_id: int) -> models.VerificationToken:
    """Crea un token de verificación de email con expiración."""
    from datetime import timedelta

    from backend.models_identity import VerificationToken

    expires_at = _utcnow() + timedelta(hours=48)
    row = VerificationToken(
        user_id=user_id, token=_generate_token(), expires_at=expires_at, used=False
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def use_verification_token(db: Session, token: str) -> Optional[int]:
    """Usa un token de verificación. Retorna user_id si es válido, None si no."""
    from backend.models_identity import User, VerificationToken

    row = db.query(VerificationToken).filter(VerificationToken.token == token).first()
    if not row or row.used or row.expires_at <= _utcnow():
        return None
    row.used = True

    user = db.query(User).filter(User.id == row.user_id).first()
    if user:
        user.is_email_verified = True
    db.commit()
    return row.user_id


def create_reset_token(db: Session, user_id: int) -> models.ResetToken:
    """Crea un token de restablecimiento de contraseña."""
    from datetime import timedelta

    from backend.models_identity import ResetToken

    expires_at = _utcnow() + timedelta(minutes=60)
    row = ResetToken(
        user_id=user_id, token=_generate_token(), expires_at=expires_at, used=False
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def use_reset_token(db: Session, token: str, new_password: str) -> bool:
    """Usa un token de reset. Retorna True si se cambió la contraseña."""
    from backend.models_identity import ResetToken, User

    row = db.query(ResetToken).filter(ResetToken.token == token).first()
    if not row or row.used or row.expires_at <= _utcnow():
        return False
    if len(new_password) < 8:
        return False
    row.used = True

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        return False
    user.password_hash = get_password_hash(new_password)
    db.commit()
    return True


# ── XP & Badges ────────────────────────────────────────


def grant_xp(db: Session, user_id: int, amount: int) -> Optional[models.User]:
    user = get_user(db, user_id)
    if not user:
        return None
    user.xp = (user.xp or 0) + amount
    next_level = (
        db.query(models.Level)
        .filter(models.Level.min_xp <= user.xp)
        .order_by(models.Level.min_xp.desc())
        .first()
    )
    if next_level and user.current_level_id != next_level.id:
        user.current_level_id = next_level.id
    db.commit()
    db.refresh(user)
    return user


def award_badge(db: Session, user_id: int, badge_name: str):
    badge = db.query(models.Badge).filter(models.Badge.name == badge_name).first()
    if not badge:
        return None
    existing = (
        db.query(models.UserBadge)
        .filter(
            models.UserBadge.user_id == user_id, models.UserBadge.badge_id == badge.id
        )
        .first()
    )
    if existing:
        return existing
    row = models.UserBadge(user_id=user_id, badge_id=badge.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── UI Preferences ─────────────────────────────────────


def update_ui_preferences(db: Session, user_id: int, settings: dict):
    prefs = (
        db.query(models.UserUIPreference)
        .filter(models.UserUIPreference.user_id == user_id)
        .first()
    )
    if not prefs:
        prefs = models.UserUIPreference(user_id=user_id, settings=settings)
        db.add(prefs)
    else:
        prefs.settings = settings
    db.commit()
    db.refresh(prefs)
    return prefs


def get_ui_preferences(db: Session, user_id: int):
    prefs = (
        db.query(models.UserUIPreference)
        .filter(models.UserUIPreference.user_id == user_id)
        .first()
    )
    if not prefs:
        prefs = models.UserUIPreference(user_id=user_id, settings={})
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def ensure_ui_preferences(db: Session, user_id: int):
    """Explicitly create UI preferences if they don't exist (write variant of get_ui_preferences)."""
    return get_ui_preferences(db, user_id)

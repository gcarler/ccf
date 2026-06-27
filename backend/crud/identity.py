"""Canonical Auth v3 identity, token, gamification, and preference CRUD."""

from __future__ import annotations

import secrets
from datetime import timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import get_password_hash
from backend.crud._utils import _utcnow


def _utc_compare(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_user(db: Session, user_id: UUID):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email.strip().lower()).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def update_user(db: Session, user_id: UUID, payload: schemas.UserUpdate):
    user = get_user(db, user_id)
    if not user:
        return None
    values = payload.model_dump(exclude_unset=True)
    if "password" in values:
        values["password_hash"] = get_password_hash(values.pop("password"))
    editable = {"username", "email", "password_hash", "is_active", "is_email_verified"}
    for key, value in values.items():
        if key in editable:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: UUID) -> bool:
    user = get_user(db, user_id)
    if not user:
        return False
    user.is_active = False
    db.commit()
    return True


def create_refresh_token(
    db: Session,
    user_id: UUID,
    token: str,
    expires_at,
    ip_address: str | None = None,
    user_agent: str | None = None,
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
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    expires_at = _utc_compare(row.expires_at) if row else None
    if not row or row.revoked or expires_at is None or expires_at <= _utcnow():
        return None
    return row


def revoke_refresh_token(db: Session, token: str):
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    if not row:
        return None
    row.revoked = True
    db.commit()
    db.refresh(row)
    return row


def _generate_token() -> str:
    return secrets.token_urlsafe(48)


def create_verification_token(db: Session, user_id: UUID) -> models.VerificationToken:
    row = models.VerificationToken(
        user_id=user_id,
        token=_generate_token(),
        expires_at=_utcnow() + timedelta(hours=48),
        used=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def use_verification_token(db: Session, token: str) -> UUID | None:
    row = db.query(models.VerificationToken).filter(
        models.VerificationToken.token == token
    ).first()
    expires_at = _utc_compare(row.expires_at) if row else None
    if not row or row.used or expires_at is None or expires_at <= _utcnow():
        return None
    row.used = True
    user = get_user(db, row.user_id)
    if user:
        user.is_email_verified = True
    db.commit()
    return row.user_id


def create_reset_token(db: Session, user_id: UUID) -> models.ResetToken:
    row = models.ResetToken(
        user_id=user_id,
        token=_generate_token(),
        expires_at=_utcnow() + timedelta(minutes=60),
        used=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def use_reset_token(db: Session, token: str, new_password: str) -> bool:
    row = db.query(models.ResetToken).filter(models.ResetToken.token == token).first()
    expires_at = _utc_compare(row.expires_at) if row else None
    if not row or row.used or expires_at is None or expires_at <= _utcnow():
        return False
    if len(new_password) < 8:
        return False
    user = get_user(db, row.user_id)
    if not user:
        return False
    row.used = True
    user.password_hash = get_password_hash(new_password)
    db.commit()
    return True


def grant_xp(db: Session, user_id: UUID, amount: int):
    user = get_user(db, user_id)
    if not user:
        return None
    user.xp = (user.xp or 0) + amount
    level = db.query(models.Level).filter(
        models.Level.min_xp <= user.xp
    ).order_by(models.Level.min_xp.desc()).first()
    if level:
        user.current_level_id = level.id
    db.commit()
    db.refresh(user)
    return user


def award_badge(db: Session, user_id: UUID, badge_name: str):
    badge = db.query(models.Badge).filter(models.Badge.name == badge_name).first()
    if not badge:
        return None
    existing = db.query(models.UserBadge).filter(
        models.UserBadge.user_id == user_id,
        models.UserBadge.badge_id == badge.id,
    ).first()
    if existing:
        return existing
    row = models.UserBadge(user_id=user_id, badge_id=badge.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_ui_preferences(db: Session, user_id: UUID, settings: dict):
    prefs = db.query(models.UserUIPreference).filter(
        models.UserUIPreference.user_id == user_id
    ).first()
    if not prefs:
        prefs = models.UserUIPreference(user_id=user_id, settings=settings)
        db.add(prefs)
    else:
        prefs.settings = settings
    db.commit()
    db.refresh(prefs)
    return prefs


def get_ui_preferences(db: Session, user_id: UUID):
    return db.query(models.UserUIPreference).filter(
        models.UserUIPreference.user_id == user_id
    ).first()


def ensure_ui_preferences(db: Session, user_id: UUID):
    prefs = get_ui_preferences(db, user_id)
    return prefs or update_ui_preferences(db, user_id, {})

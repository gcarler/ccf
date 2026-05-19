"""User, auth, badges, XP, and UI preferences CRUD."""
from typing import Optional

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import get_password_hash, encrypt_data, decrypt_data
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
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
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


def delete_user(db: Session, user_id: int):
    row = db.query(models.User).filter(models.User.id == user_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Refresh Tokens ─────────────────────────────────────

def create_refresh_token(db: Session, user_id: int, token: str, expires_at):
    row = models.RefreshToken(user_id=user_id, token=token, expires_at=expires_at, revoked=False)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_valid_refresh_token(db: Session, token: str):
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    if not row:
        return None
    if row.revoked:
        return None
    if row.expires_at <= _utcnow():
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
        .filter(models.UserBadge.user_id == user_id, models.UserBadge.badge_id == badge.id)
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
    prefs = db.query(models.UserUIPreference).filter(models.UserUIPreference.user_id == user_id).first()
    if not prefs:
        prefs = models.UserUIPreference(user_id=user_id, settings=settings)
        db.add(prefs)
    else:
        prefs.settings = settings
    db.commit()
    db.refresh(prefs)
    return prefs


def get_ui_preferences(db: Session, user_id: int):
    prefs = db.query(models.UserUIPreference).filter(models.UserUIPreference.user_id == user_id).first()
    if not prefs:
        prefs = models.UserUIPreference(user_id=user_id, settings={})
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs

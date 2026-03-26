from datetime import datetime, timedelta
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import os
from backend import crud, schemas, database
from backend.core.cache import get_redis
from backend.core.config import get_settings
from backend.core.security import verify_password

settings = get_settings()

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

ROLE_ALIASES = {
    "student": "estudiante",
    "leader": "coordinador",
    "staff": "docente",
}

VALID_ROLES = {"aspirante", "estudiante", "docente", "coordinador", "admin"}


def normalize_role(role: str) -> str:
    role_value = str(role or "").strip().lower()
    return ROLE_ALIASES.get(role_value, role_value)


def role_in(user_role: str, allowed_roles: set[str]) -> bool:
    return normalize_role(user_role) in allowed_roles

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "iat": datetime.utcnow().timestamp()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(db: Session = Depends(database.get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = str(payload.get("sub") or "")
        if not subject:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = None
    if subject.isdigit():
        user = crud.get_user(db, int(subject))
    else:
        user = crud.get_user_by_email(db, email=subject)

    if user is None:
        raise credentials_exception
    return user


def create_refresh_token(db: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    crud.create_refresh_token(db, user_id=user_id, token=token, expires_at=expires_at)
    return token


def record_session(user_id: int, token: str) -> None:
    redis_client = get_redis()
    ttl = settings.access_token_expire_minutes * 60
    redis_client.setex(f"session:{user_id}:{token}", ttl, "active")

async def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: schemas.User = Depends(get_current_active_user)):
    if normalize_role(current_user.role) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

# Additional required by main.py
def authenticate_user(db: Session, email: str, password: str):
    user = crud.get_user_by_email(db, email=email)
    if not user:
        return False
    hashed_password = str(getattr(user, "password_hash", ""))
    if not verify_password(password, hashed_password):  # type: ignore[arg-type]
        return False
    return user

require_active_user = get_current_active_user
require_admin = get_current_admin_user

async def require_staff_or_admin(current_user: schemas.User = Depends(get_current_active_user)):
    if not role_in(current_user.role, {"admin", "coordinador", "docente"}):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

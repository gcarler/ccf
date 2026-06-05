"""CRUD asíncrono — wrappers para migración progresiva a SQLAlchemy async.

Cada función replica la firma de su equivalente síncrono en ``backend/crud/``
pero acepta ``AsyncSession`` en lugar de ``Session``.

Uso en un endpoint async::

    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.crud.async_ import get_user_async
    from backend.core.database import get_db_async

    @router.get("/users/{user_id}")
    async def get_user(user_id: int, db: AsyncSession = Depends(get_db_async)):
        user = await get_user_async(db, user_id)
        ...

Migración paso a paso:
    1. Convierte el endpoint: ``def`` → ``async def``
    2. Cambia la dependency: ``Depends(get_db)`` → ``Depends(get_db_async)``
    3. Importa el CRUD async desde ``backend.crud.async_``
    4. Añade ``await`` a cada llamada CRUD
    5. Ejecuta los tests y verifica que todo funciona
"""

from __future__ import annotations

from typing import Optional
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models, schemas
from backend.core.security import get_password_hash


def _utc_compare(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

# ── Identity / Auth ───────────────────────────────────────────────────


async def get_user_async(db: AsyncSession, user_id: int) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email_async(
    db: AsyncSession, email: str
) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username_async(
    db: AsyncSession, username: str
) -> Optional[models.User]:
    result = await db.execute(
        select(models.User).where(models.User.username == username)
    )
    return result.scalar_one_or_none()


async def get_users_async(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[models.User]:
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_user_async(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


# ── Refresh Tokens ────────────────────────────────────────────────────


async def create_refresh_token_async(
    db: AsyncSession, user_id: int, token: str, expires_at
):
    from backend.models_identity import RefreshToken

    row = RefreshToken(
        user_id=user_id, token=token, expires_at=expires_at, revoked=False
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_valid_refresh_token_async(db: AsyncSession, token: str):
    from backend.crud._utils import _utcnow
    from backend.models_identity import RefreshToken

    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    row = result.scalar_one_or_none()
    if not row:
        return None
    if row.revoked:
        return None
    expires_at = _utc_compare(row.expires_at)
    if expires_at is None or expires_at <= _utcnow():
        return None
    return row


async def revoke_refresh_token_async(db: AsyncSession, token: str):
    from backend.models_identity import RefreshToken

    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    row = result.scalar_one_or_none()
    if not row:
        return None
    row.revoked = True
    await db.commit()
    await db.refresh(row)
    return row


# ── Verification & Reset Tokens ────────────────────────────────────────


async def create_verification_token_async(
    db: AsyncSession, user_id: int, token: str, expires_at
):
    from backend.models_identity import VerificationToken

    row = VerificationToken(
        user_id=user_id, token=token, expires_at=expires_at, used=False
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def use_verification_token_async(db: AsyncSession, token: str) -> Optional[int]:
    """Usa un token de verificación.

    Returns:
        user_id si el token es válido y no expirado, None en otro caso.
    """
    from backend.crud._utils import _utcnow
    from backend.models_identity import VerificationToken

    result = await db.execute(
        select(VerificationToken).where(VerificationToken.token == token)
    )
    row = result.scalar_one_or_none()
    expires_at = _utc_compare(row.expires_at) if row else None
    if not row or row.used or expires_at is None or expires_at <= _utcnow():
        return None
    row.used = True
    await db.commit()

    # Marcar usuario como verificado
    from backend.models_identity import User

    user_result = await db.execute(select(User).where(User.id == row.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.is_email_verified = True
        await db.commit()
    return row.user_id


async def create_reset_token_async(
    db: AsyncSession, user_id: int, token: str, expires_at
):
    from backend.models_identity import ResetToken

    row = ResetToken(user_id=user_id, token=token, expires_at=expires_at, used=False)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def use_reset_token_async(
    db: AsyncSession, token: str, new_password: str
) -> bool:
    """Usa un token de reset para cambiar la contraseña.

    Returns:
        True si se cambió, False si el token es inválido/expirado.
    """
    from backend.core.security import get_password_hash
    from backend.crud._utils import _utcnow
    from backend.models_identity import ResetToken, User

    result = await db.execute(select(ResetToken).where(ResetToken.token == token))
    row = result.scalar_one_or_none()
    expires_at = _utc_compare(row.expires_at) if row else None
    if not row or row.used or expires_at is None or expires_at <= _utcnow():
        return False
    row.used = True

    user_result = await db.execute(select(User).where(User.id == row.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return False
    user.password_hash = get_password_hash(new_password)
    await db.commit()
    return True

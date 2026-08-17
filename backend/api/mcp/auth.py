"""Authentication helpers for embedded MCP tools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.api.cms_v2._shared import _assert_role
from backend.core.database import SessionLocal
from backend.core.permissions import (
    _has_permission,
    get_current_user,
    get_user_effective_permissions,
    normalize_role,
)


def _request_bearer_token(ctx) -> str:
    request = getattr(getattr(ctx, "request_context", None), "request", None)
    return _request_bearer_token_from_request(request)


def _request_bearer_token_from_request(request) -> str:
    headers = getattr(request, "headers", None)
    authorization = headers.get("authorization", "") if headers is not None else ""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MCP requires a CCF Bearer access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


async def _authenticate(ctx, db: Session):
    token = _request_bearer_token(ctx)
    return await _authenticate_token(token, db)


async def _authenticate_request(request, db: Session):
    token = _request_bearer_token_from_request(request)
    return await _authenticate_token(token, db)


async def _authenticate_token(token: str, db: Session):
    user = await get_current_user(db=db, token=token)
    if not getattr(user, "is_active", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


@asynccontextmanager
async def authorized_cms_context(
    ctx,
    permission: str = "cms:read",
    allowed_roles: set[str] | None = None,
) -> AsyncIterator[tuple[Session, object]]:
    """Yield a CCF user/session with the same CMS guards as the REST API."""
    db = SessionLocal()
    try:
        user = await _authenticate(ctx, db)
        role = normalize_role(getattr(user, "role", ""))
        if not role and getattr(user, "rol_plataforma", None):
            role = normalize_role(user.rol_plataforma.nombre)
        permissions = get_user_effective_permissions(db, user)
        if not _has_permission(role, permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere: {permission}",
            )
        if allowed_roles is not None:
            _assert_role(user, allowed_roles)
        yield db, user
    finally:
        db.close()

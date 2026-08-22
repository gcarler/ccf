"""Autenticación común para superficies MCP privadas de CCF.

El MCP público no usa este módulo: su contrato es únicamente contenido CMS
publicado. Las superficies privadas reutilizan el mismo JWT de Auth v3 y la
misma matriz RBAC del backend, sin crear una identidad alternativa.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from mcp.server.auth.middleware.auth_context import AuthContextMiddleware, auth_context_var
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend, RequireAuthMiddleware
from mcp.server.auth.provider import AccessToken, TokenVerifier
from sqlalchemy.orm import Session
from starlette.middleware.authentication import AuthenticationMiddleware

from backend import models
from backend.core.config import get_settings
from backend.core.database import SessionLocal
from backend.core.permissions import (
    PERMISSIONS,
    _has_permission,
    get_user_effective_permissions,
    normalize_role,
    role_allows_permission,
)

settings = get_settings()


class CcfJwtTokenVerifier(TokenVerifier):
    """Valida un access JWT de CCF y lo convierte al contrato MCP.

    Los tokens existentes no son OAuth tokens completos, pero sí contienen el
    mismo `sub` y `exp` que necesita el servidor. Las scopes se calculan desde
    la fuente de verdad RBAC de CCF para que un cambio de permisos se aplique
    al siguiente llamado MCP y no dependa de claims obsoletos.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            subject = str(payload.get("sub") or "")
            user_id = UUID(subject)
        except (JWTError, TypeError, ValueError):
            return None

        db = SessionLocal()
        try:
            user = (
                db.query(models.Usuario)
                .filter(models.Usuario.id == user_id, models.Usuario.is_active.is_(True))
                .first()
            )
            if not user:
                return None

            scopes = _effective_user_scopes(db, user)
            expires_at = payload.get("exp")
            return AccessToken(
                token=token,
                client_id="ccf-auth-v3",
                subject=subject,
                scopes=sorted(scopes),
                expires_at=int(expires_at) if expires_at is not None else None,
                claims=payload,
            )
        finally:
            db.close()


def _user_role(user: Any) -> str:
    role = normalize_role(str(getattr(user, "role", "")))
    if not role and getattr(user, "rol_plataforma", None):
        role = normalize_role(user.rol_plataforma.nombre)
    return role


def _effective_user_scopes(db: Session, user: Any) -> set[str]:
    """Calcula scopes MCP del usuario autenticado.

    Combina los permisos efectivos (rol_plataforma, roles modulares y
    overrides) con los allowances por rol que REST concede vía
    ``role_allows_permission``, de modo que ambas superficies resuelvan la
    misma matriz RBAC para todos los módulos (evangelismo, CRM, academia,
    proyectos, wiki, etc.).
    """
    role = _user_role(user)
    permissions = set(get_user_effective_permissions(db, user).keys())
    for permission in PERMISSIONS:
        if role_allows_permission(role, permission):
            permissions.add(permission)
    return permissions


def get_mcp_current_user(db: Session) -> models.Usuario:
    """Resuelve el usuario autenticado por el middleware MCP actual."""
    authenticated = auth_context_var.get()
    access_token = getattr(authenticated, "access_token", None)
    subject = getattr(access_token, "subject", None)
    if not subject:
        raise PermissionError("Se requiere autenticación Bearer para este MCP")

    try:
        user_id = UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise PermissionError("Token MCP inválido") from exc

    user = (
        db.query(models.Usuario)
        .filter(models.Usuario.id == user_id, models.Usuario.is_active.is_(True))
        .first()
    )
    if not user:
        raise PermissionError("Usuario MCP no encontrado o inactivo")
    return user


def require_mcp_permission(db: Session, user: models.Usuario, permission: str) -> None:
    """Aplica la misma jerarquía RBAC que los endpoints REST."""
    role = _user_role(user)
    if not _has_permission(role, _effective_user_scopes(db, user), permission):
        # Allowance por rol (misma matriz que require_permission en REST).
        if not role_allows_permission(role, permission):
            raise PermissionError(f"Permisos insuficientes. Se requiere: {permission}")


def has_mcp_execute_permission(db: Session, user: Any) -> bool:
    """Determina si el usuario cuenta con el permiso 'mcp:execute'."""
    role = _user_role(user)
    if role in {"admin", "administrador", "super administrador"}:
        return True
    scopes = _effective_user_scopes(db, user)
    if _has_permission(role, scopes, "mcp:execute") or role_allows_permission(role, "mcp:execute"):
        return True
    return False


def require_mcp_execute(db: Session, user: Any) -> None:
    """Valida el permiso mcp:execute o lanza PermissionError."""
    if not has_mcp_execute_permission(db, user):
        raise PermissionError("Permisos insuficientes. Se requiere: mcp:execute")


def set_mcp_auth_context(
    token: str,
    user_id: UUID | str,
    scopes: list[str] | None = None,
    claims: dict[str, Any] | None = None,
):
    """Establece explícitamente el contexto de autenticación MCP (útil para orquestadores y gateway)."""
    from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser

    access_token = AccessToken(
        token=token,
        client_id="ccf-auth-v3",
        subject=str(user_id),
        scopes=scopes or [],
        claims=claims or {},
    )
    return auth_context_var.set(AuthenticatedUser(access_token))


def authenticated_mcp_app(mcp_server):
    """Protege una app Streamable HTTP MCP con el JWT de Auth v3.

    Se usa un wrapper ASGI explícito porque CCF no opera aún un Authorization
    Server OAuth independiente. El cliente MCP debe enviar el access token
    vigente en `Authorization: Bearer <JWT>`.
    """
    protected = RequireAuthMiddleware(mcp_server.streamable_http_app(), required_scopes=[])
    with_context = AuthContextMiddleware(protected)
    return AuthenticationMiddleware(with_context, backend=BearerAuthBackend(CcfJwtTokenVerifier()))


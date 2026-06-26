"""
Auth v3 — Google SSO, Password Init, ABAC LECTOR.

Usa platform_role_definitions como fuente única de roles (Dimensión C).
Flujo:
  - Google SSO: /v3/auth/google → login directo para @gmail.com
  - Traditional: /v3/auth/login → email+password
  - Init password: /v3/auth/initialize-password → token de un solo uso
  - Change password: /v3/auth/change-password → con validación de anterior
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.security import get_password_hash, verify_password
from backend.models_auth import (
    HistorialContrasena,
    LogSeguridad,
    RolPlataforma,
    TokenResetContrasena,
    Usuario,
)
from backend.models_kernel import PlatformRoleDefinition
from backend.core.rate_limit import rate_limiter

settings = get_settings()
log = logging.getLogger(__name__)

router = APIRouter(prefix="/v3/auth", tags=["Auth v3"])

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _create_access_token(user_id: str, platform_role: str, sede_id: str = "") -> str:
    to_encode = {
        "sub": user_id,
        "role": platform_role,
        "platform_role": platform_role,
        "sede_id": sede_id,
        "jti": secrets.token_hex(8),
    }
    expire = _utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire, "iat": _utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _create_refresh_token(db: Session, user_id: uuid.UUID) -> str:
    import secrets

    token = secrets.token_urlsafe(48)
    expires_at = _utcnow() + timedelta(days=settings.refresh_token_expire_days)
    from backend.models_auth import TokenSesion

    rt = TokenSesion(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        ip_address=None,
        user_agent=None,
    )
    db.add(rt)
    db.commit()
    return token


def _log_security(db, user_id, evento, ip=None, ua=None, detalles=None):
    if user_id is None:
        return
    try:
        ls = LogSeguridad(
            user_id=user_id,
            evento=evento,
            ip_address=ip,
            user_agent=ua,
            detalles=detalles or {},
        )
        db.add(ls)
        db.commit()
    except Exception:
        db.rollback()


def _set_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.access_token_cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.access_token_cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )


def _build_public_welcome_redirect(frontend_url: str, *, name: str | None = None, email: str | None = None) -> str:
    base = frontend_url.rstrip("/")
    params: dict[str, str] = {"reason": "no_account"}
    if name:
        params["name"] = name
    if email:
        params["email"] = email
    return f"{base}/bienvenida?{urlencode(params)}"


# ─── Schemas ──────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str
    password: str


class InitPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)
    password_confirm: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    auth_user_id: str
    email: str
    platform_role: str
    needs_password_init: bool = False


# ─── Helper: resolve user ─────────────────────────────────────────────────


def _resolve_user(db: Session, email: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.email == email).first()


def _resolve_persona_default_role(db: Session) -> RolPlataforma:
    role = db.query(RolPlataforma).filter(RolPlataforma.nombre == "MIEMBRO").first()
    if role:
        return role

    role = RolPlataforma(
        nombre="MIEMBRO",
        permisos={
            "academy:study": "allow",
            "profile:manage": "allow",
        },
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def _resolve_token(db: Session, token: str) -> TokenResetContrasena | None:
    return (
        db.query(TokenResetContrasena)
        .filter(
            TokenResetContrasena.token == token,
            TokenResetContrasena.used.is_(False),
            TokenResetContrasena.expires_at > _utcnow(),
        )
        .first()
    )


# ═══════════════════════════════════════════════════════════════════════
# 1. GOOGLE SSO LOGIN
# ═══════════════════════════════════════════════════════════════════════


@router.get("/google")
def google_login(request: Request):
    """Redirige a pantalla de consentimiento de Google."""
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth no configurado")

    redirect_uri = settings.google_redirect_uri or request.url_for("google_callback")
    from urllib.parse import urlencode

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(
    code: str,
    error: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    response: Response = None,
):
    import httpx

    if error or not code:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")

    redirect_uri = settings.google_redirect_uri or (request.url_for("google_callback") if request else "")

    # 1. Exchange code for tokens
    try:
        token_resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Error exchanging Google code: {exc}")

    access_token_google = token_data.get("access_token")
    if not access_token_google:
        raise HTTPException(status_code=400, detail="No se recibió token de Google")

    # 2. Get user info
    try:
        userinfo_resp = httpx.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token_google}"},
            timeout=15,
        )
        userinfo_resp.raise_for_status()
        google_user = userinfo_resp.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Error getting Google user info: {exc}")

    google_email = google_user.get("email", "")

    if not google_email:
        raise HTTPException(status_code=400, detail="Google no proporcionó un email")

    # 3. Find or create auth_user (linking to personas)
    user = _resolve_user(db, google_email)

    if not user:
        # Create silent auth_user linked to persona
        from backend import models

        persona = db.query(models.Persona).filter(models.Persona.email == google_email).first()
        if not persona:
            frontend_url = getattr(settings, "frontend_url", "http://localhost:3000")
            return RedirectResponse(
                url=_build_public_welcome_redirect(
                    frontend_url,
                    name=google_user.get("name") or google_email.split("@")[0],
                    email=google_email,
                )
            )

        from backend.models_kernel import PlatformRole as PlatformRoleEnum
        lector_role = db.query(PlatformRoleDefinition).filter(
            PlatformRoleDefinition.role == PlatformRoleEnum.LECTOR
        ).first()
        if not lector_role:
            raise HTTPException(status_code=500, detail="Rol LECTOR no configurado. Contacta al administrador.")
        persona_default_role = _resolve_persona_default_role(db)

        # sede_id es NOT NULL en Usuario — usar la sede del sistema si la Persona no tiene
        if not persona.sede_id:
            from backend import models as _models
            fallback_sede = db.query(_models.Sede).first()
            if not fallback_sede:
                raise HTTPException(status_code=500, detail="No hay sedes configuradas en el sistema.")
            persona_sede_id = fallback_sede.id
        else:
            persona_sede_id = persona.sede_id

        user = Usuario(
            id=persona.id,
            sede_id=persona_sede_id,
            username=google_email.split("@")[0].replace(".", "_")[:50],
            email=google_email,
            password_hash=None,
            platform_role_id=lector_role.id,
            rol_plataforma_id=persona_default_role.id,
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    log.info("Nuevo auth_user creado via Google SSO")

    # 4. Verify user is active
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Cuenta desactivada")

    # 5. Ensure email verified for Gmail users
    if not user.is_email_verified:
        user.is_email_verified = True
        db.commit()

    # 6. Get platform role name
    platform_role_name = "LECTOR"
    if user.platform_role_id:
        pr = db.query(PlatformRoleDefinition).filter(PlatformRoleDefinition.id == user.platform_role_id).first()
        if pr:
            platform_role_name = pr.role

    # 7. Get sede_id from user persona
    sede_id = ""
    try:
        from backend import models

        persona = db.query(models.Persona).filter(models.Persona.id == user.id).first()
        if persona and persona.sede_id:
            sede_id = str(persona.sede_id)
    except Exception:
        pass

    # 8. Generate tokens with sede_id
    access_token = _create_access_token(str(user.id), platform_role_name, sede_id)
    refresh_token = _create_refresh_token(db, user.id)

    # 8. Set httpOnly cookies + redirect
    _set_cookies(response, access_token, refresh_token)
    _log_security(
        db,
        user.id,
        "GOOGLE_LOGIN_EXITOSO",
        ip=request.client.host if request and request.client else None,
        ua=request.headers.get("user-agent") if request else None,
    )

    # Redirect to frontend with token in hash
    frontend_url = getattr(settings, "frontend_url", "http://localhost:3000")
    return RedirectResponse(url=f"{frontend_url}/auth/callback?token={access_token}")


# ═══════════════════════════════════════════════════════════════════════
# 2. TRADITIONAL LOGIN (email + password)
# ═══════════════════════════════════════════════════════════════════════


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Inicio de sesión con email + contraseña."""
    user = _resolve_user(db, payload.email)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if not user:
        _log_security(
            db,
            None,
            "LOGIN_FALLIDO_NO_EXISTE",
            ip=ip,
            ua=ua,
            detalles={"email": payload.email},
        )
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # Check if user has a password at all
    if not user.password_hash:
        _log_security(db, user.id, "LOGIN_SIN_CONTRASENA", ip=ip, ua=ua)
        raise HTTPException(
            status_code=400,
            detail="CONTRASENA_NO_INICIALIZADA",
            headers={"X-Needs-Password-Init": "true"},
        )

    # Verify password
    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts += 1
        db.commit()
        _log_security(db, user.id, "LOGIN_FALLIDO_CONTRASENA", ip=ip, ua=ua)
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # Check lockout
    if user.locked_until and user.locked_until > _utcnow():
        raise HTTPException(status_code=423, detail="Cuenta temporalmente bloqueada. Intenta más tarde.")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Cuenta desactivada")

    # Reset failed attempts
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    # Get platform role
    platform_role_name = "LECTOR"
    if user.platform_role_id:
        pr = db.query(PlatformRoleDefinition).filter(PlatformRoleDefinition.id == user.platform_role_id).first()
        if pr:
            platform_role_name = pr.role

    # Resolve sede_id (from user record, fallback to persona)
    sede_id = str(user.sede_id) if user.sede_id else ""
    if not sede_id:
        from backend import models as _m
        persona = db.query(_m.Persona).filter(_m.Persona.id == user.id).first()
        if persona and persona.sede_id:
            sede_id = str(persona.sede_id)

    # Generate tokens
    access_token = _create_access_token(str(user.id), platform_role_name, sede_id)
    refresh_token = _create_refresh_token(db, user.id)

    _set_cookies(response, access_token, refresh_token)
    _log_security(db, user.id, "LOGIN_EXITOSO", ip=ip, ua=ua)

    return TokenResponse(
        access_token=access_token,
        auth_user_id=str(user.id),
        email=user.email,
        platform_role=platform_role_name,
        needs_password_init=False,
    )


# ═══════════════════════════════════════════════════════════════════════
# 3. INITIALIZE PASSWORD (for non-Gmail users)
# ═══════════════════════════════════════════════════════════════════════


@router.post("/initialize-password", response_model=dict)
def initialize_password(
    payload: InitPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Configura la contraseña por primera vez usando un token de un solo uso."""
    if payload.password != payload.password_confirm:
        raise HTTPException(status_code=400, detail="Las contraseñas no coinciden")

    token_record = _resolve_token(db, payload.token)
    if not token_record:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    user = db.query(Usuario).filter(Usuario.id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Hash and set password
    hashed = get_password_hash(payload.password)
    user.password_hash = hashed
    user.is_email_verified = True
    token_record.used = True

    # Save to password history
    history = HistorialContrasena(user_id=user.id, password_hash=hashed)
    db.add(history)
    db.commit()

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    _log_security(db, user.id, "CONTRASENA_INICIALIZADA", ip=ip, ua=ua)

    return {
        "status": "success",
        "message": "Contraseña configurada exitosamente. Ya puedes iniciar sesión.",
    }


# ═══════════════════════════════════════════════════════════════════════
# 4. CHANGE PASSWORD (self-service)
# ═══════════════════════════════════════════════════════════════════════


def require_auth_dep(request: Request, db: Session = Depends(get_db)):
    return _require_auth(request, db)


@router.post("/change-password", response_model=dict)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(require_auth_dep),
):
    """Cambio de contraseña para usuarios autenticados."""
    user = db.query(Usuario).filter(Usuario.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not user.password_hash:
        raise HTTPException(status_code=400, detail="Debes inicializar tu contraseña primero")

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    hashed = get_password_hash(payload.new_password)
    user.password_hash = hashed

    history = HistorialContrasena(user_id=user.id, password_hash=hashed)
    db.add(history)
    db.commit()

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    _log_security(db, user.id, "CONTRASENA_CAMBIADA", ip=ip, ua=ua)

    return {"status": "success", "message": "Contraseña cambiada exitosamente"}


# ═══════════════════════════════════════════════════════════════════════
# 5. AUTH CHECK (verify token + return user info)
# ═══════════════════════════════════════════════════════════════════════


@router.get("/me")
def auth_me(request: Request, db: Session = Depends(get_db)):
    """Verifica el token actual y retorna información del usuario.

    Incluye permisos RBAC y sede_id del JWT.
    """
    token = request.cookies.get(settings.access_token_cookie_name) or ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub", "")
        platform_role = payload.get("platform_role", "LECTOR")
        sede_id = payload.get("sede_id", "")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(Usuario).filter(Usuario.id == user_uuid).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    # Resolve effective permissions: prefer auth_roles granular perms for persona access,
    # and fall back to PlatformRoleDefinition only when no granular role exists.
    permissions = {}
    try:
        from backend.models_kernel import PlatformRoleDefinition
        from sqlalchemy.orm import joinedload

        user_with_rol = db.query(Usuario).options(joinedload(Usuario.rol_plataforma)).filter(Usuario.id == user_uuid).first()
        if user_with_rol and user_with_rol.rol_plataforma:
            rol_perms = user_with_rol.rol_plataforma.permisos or {}
            if isinstance(rol_perms, dict):
                for k, v in rol_perms.items():
                    if v:  # cualquier valor truthy ("read", "edit", "manage", "allow", True)
                        permissions[k] = "allow"
        else:
            # Base permissions from PlatformRoleDefinition for users without persona override
            pr = db.query(PlatformRoleDefinition).filter(PlatformRoleDefinition.id == user.platform_role_id).first()
            if pr and pr.permissions:
                if isinstance(pr.permissions, dict):
                    if "*" in pr.permissions:
                        from backend.core.permissions import PERMISSIONS
                        for p_key in PERMISSIONS:
                            permissions[p_key] = "allow"
                    else:
                        for module, levels in pr.permissions.items():
                            if module == "profile":
                                for level in levels or []:
                                    if level == "manage":
                                        permissions["profile:manage"] = "allow"
                                continue
                            if module == "academy":
                                for level in levels or []:
                                    if level in {"read", "study", "edit", "manage"}:
                                        permissions[f"academy:{level}"] = "allow"
                                continue
                            if module == "messaging":
                                for level in levels or []:
                                    if level in {"read", "edit"}:
                                        permissions[f"messaging:{level}"] = "allow"
                                continue
                else:
                    for p in pr.permissions:
                        permissions[p] = "allow"
    except Exception:
        pass

    return {
        "auth_user_id": str(user.id),
        "email": user.email,
        "username": user.username,
        "is_verified": user.is_email_verified,
        "platform_role": platform_role,
        "sede_id": sede_id,
        "permissions": permissions,
        "has_password": user.password_hash is not None,
        "is_gmail": user.email.lower().endswith("@gmail.com") if user.email else False,
    }


# ═══════════════════════════════════════════════════════════════════════
# 5b. UPDATE PROFILE (PATCH /me)
# ═══════════════════════════════════════════════════════════════════════


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


@router.patch("/me")
def update_profile(
    payload: UpdateProfileRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Actualiza username, email, o contraseña del usuario autenticado."""
    token = request.cookies.get(settings.access_token_cookie_name) or ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")

    try:
        payload_jwt = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload_jwt.get("sub", "")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(Usuario).filter(Usuario.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if payload.username:
        existing = db.query(Usuario).filter(Usuario.username == payload.username, Usuario.id != user_uuid).first()
        if existing:
            raise HTTPException(status_code=400, detail="Nombre de usuario ya existe")
        user.username = payload.username

    if payload.email:
        existing = db.query(Usuario).filter(Usuario.email == payload.email, Usuario.id != user_uuid).first()
        if existing:
            raise HTTPException(status_code=400, detail="Correo ya registrado")
        user.email = payload.email
        user.is_email_verified = False

    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="Se requiere la contraseña actual")
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=403, detail="Contraseña actual incorrecta")
        user.password_hash = get_password_hash(payload.new_password)
        history = HistorialContrasena(user_id=user.id, password_hash=user.password_hash)
        db.add(history)

    db.commit()
    db.refresh(user)

    return {
        "auth_user_id": str(user.id),
        "email": user.email,
        "username": user.username,
        "is_email_verified": user.is_email_verified,
    }


# ═══════════════════════════════════════════════════════════════════════
# 6. CHECK EMAIL (for login page — determine if needs password)
# ═══════════════════════════════════════════════════════════════════════


@router.get("/check-email")
def check_email(email: str, db: Session = Depends(get_db)):
    """Verifica si un email existe y cómo debe iniciar sesión."""
    user = _resolve_user(db, email)
    is_gmail = email.lower().endswith("@gmail.com") if email else False

    if not user:
        return {"exists": False, "is_gmail": is_gmail}

    return {
        "exists": True,
        "is_gmail": is_gmail,
        "needs_password_init": user.password_hash is None,
        "has_password": user.password_hash is not None,
    }


# ─── Dependency ─────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════
# 7. REFRESH TOKEN (unified for v3)
# ═══════════════════════════════════════════════════════════════════════


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=dict)
def refresh_token(
    payload: RefreshRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Refresca el access token usando un refresh token válido."""
    from backend.models_auth import TokenSesion

    rt = (
        db.query(TokenSesion)
        .filter(
            TokenSesion.token == payload.refresh_token,
            TokenSesion.revoked.is_(False),
        )
        .first()
    )

    if not rt:
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    expires_at = _as_aware(rt.expires_at)
    if expires_at is None or expires_at < _utcnow():
        rt.revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expirado")

    user = db.query(Usuario).filter(Usuario.id == rt.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    # Get platform role
    platform_role_name = "LECTOR"
    sede_id = ""
    if user.platform_role_id:
        pr = db.query(PlatformRoleDefinition).filter(PlatformRoleDefinition.id == user.platform_role_id).first()
        if pr:
            platform_role_name = pr.role

    # Get sede_id
    try:
        from backend import models

        persona = db.query(models.Persona).filter(models.Persona.id == user.id).first()
        if persona and persona.sede_id:
            sede_id = str(persona.sede_id)
    except Exception:
        pass

    # Rotate refresh token (security best practice)
    rt.revoked = True
    db.commit()

    new_access = _create_access_token(str(user.id), platform_role_name, sede_id)
    new_refresh = _create_refresh_token(db, user.id)

    _set_cookies(response, new_access, new_refresh)

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    _log_security(db, user.id, "TOKEN_REFRESH", ip=ip, ua=ua)

    return {
        "access_token": new_access,
        "token_type": "bearer",
        "refresh_token": new_refresh,
    }


def _require_auth(request: Request, db: Session = Depends(get_db)):
    """FastAPI dependency: require valid JWT."""
    token = request.cookies.get(settings.access_token_cookie_name) or ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub", "")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


# ═══════════════════════════════════════════════════════════════════════
# 8. VERIFY EMAIL
# ═══════════════════════════════════════════════════════════════════════


@router.post("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verifica el correo electrónico usando un token enviado por email."""
    from backend.models_auth import TokenVerificacionEmail

    row = db.query(TokenVerificacionEmail).filter(TokenVerificacionEmail.token == token).first()
    if not row or row.used:
        raise HTTPException(status_code=400, detail="Token de verificación inválido o expirado")

    expires_at = _as_aware(row.expires_at)
    if expires_at is None or expires_at <= _utcnow():
        raise HTTPException(status_code=400, detail="Token de verificación inválido o expirado")

    row.used = True
    user = db.query(Usuario).filter(Usuario.id == row.user_id).first()
    if user:
        user.is_email_verified = True
    db.commit()

    return {"status": "success", "message": "Correo verificado exitosamente"}


# ═══════════════════════════════════════════════════════════════════════
# 9. FORGOT PASSWORD (sends email with reset token)
# ═══════════════════════════════════════════════════════════════════════


@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    """Solicita restablecimiento de contraseña. Envía email con token si el correo existe."""
    from datetime import timedelta

    from backend.models_auth import TokenResetContrasena
    from backend.services.email import render_reset_password, send_email

    user = _resolve_user(db, email)
    if not user:
        return {"status": "success", "message": "Si el correo existe, recibirás instrucciones"}

    expires_at = _utcnow() + timedelta(minutes=60)
    token_row = TokenResetContrasena(
        user_id=user.id,
        token=secrets.token_urlsafe(48),
        expires_at=expires_at,
        used=False,
    )
    db.add(token_row)
    db.commit()
    db.refresh(token_row)

    subject, html = render_reset_password(token_row.token)
    send_email(to=user.email, subject=subject, html=html)

    return {"status": "success", "message": "Si el correo existe, recibirás instrucciones"}


# ═══════════════════════════════════════════════════════════════════════
# 10. RESET PASSWORD
# ═══════════════════════════════════════════════════════════════════════


@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    """Restablece la contraseña usando un token enviado por email."""
    from backend.models_auth import TokenResetContrasena

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")

    row = db.query(TokenResetContrasena).filter(TokenResetContrasena.token == token).first()
    if not row or row.used:
        raise HTTPException(status_code=400, detail="Token de restablecimiento inválido, expirado o ya utilizado")

    expires_at = _as_aware(row.expires_at)
    if expires_at is None or expires_at <= _utcnow():
        raise HTTPException(status_code=400, detail="Token de restablecimiento inválido, expirado o ya utilizado")

    row.used = True
    user = db.query(Usuario).filter(Usuario.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.password_hash = get_password_hash(new_password)
    db.commit()

    return {"status": "success", "message": "Contraseña restablecida exitosamente"}


# ─── Include this in the main app router ────────────────────────────
# app.include_router(auth_v3_router)

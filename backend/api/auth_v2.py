"""
Auth 2.0 — RBAC, MFA, Forensics, Gamification.

Convive parallelamente con /api/auth (v1 legacy).
Tablas: auth_roles, auth_users, auth_refresh_tokens, etc.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.security import get_password_hash, verify_password
from backend.models_auth import (
    HistorialContrasena, LogSeguridad, Medalla, MedallaUsuario,
    NivelGamificado, NotificacionUsuario, PreferenciaUI,
    RecordatorioUsuario, RolPlataforma, TokenResetContrasena,
    TokenSesion, TokenVerificacionEmail, Usuario, UsuarioRolModulo)
from backend.schemas.auth_v2 import (
    CambioPasswordRequest, ForgotPasswordRequest, LogSeguridadRead,
    MedallaCreate, MedallaRead, MedallaUsuarioRead, MfaRecoveryResponse,
    MfaSetupResponse, MfaVerifyRequest, NivelGamificadoCreate,
    NivelGamificadoRead, NotificacionRead, PreferenciaUIRead,
    PreferenciaUIUpdate, RecordatorioCreate, RecordatorioRead,
    ResetPasswordRequest, RolPlataformaCreate, RolPlataformaRead,
    RolPlataformaUpdate, TokenResponse, TokenSesionRead, UsuarioCreate,
    UsuarioLogin, UsuarioRead, UsuarioSelfUpdate, UsuarioUpdate,
    UsuarioRolModuloCreate, UsuarioRolModuloRead)

settings = get_settings()
log = logging.getLogger(__name__)

router = APIRouter(tags=["Auth v2"])

oauth2_scheme_v2 = OAuth2PasswordBearer(tokenUrl="/api/auth/v2/login", auto_error=False)

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    to_encode = {"sub": user_id}
    now = _utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _create_refresh_token(db: Session, user_id: uuid.UUID, ip: str | None = None, ua: str | None = None) -> str:
    import secrets
    token = secrets.token_urlsafe(48)
    expires_at = _utcnow() + timedelta(days=settings.refresh_token_expire_days)
    rt = TokenSesion(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(rt)
    db.commit()
    return token


def _get_usuario_o_404(user_id: str, db: Session) -> Usuario:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ID de usuario inválido")
    user = db.query(Usuario).filter(Usuario.id == uid).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


def _resolve_current_user(token: str, db: Session) -> Usuario | None:
    """Resolve the current user from a JWT token for auth v2 endpoints."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub", "")
        if not sub:
            return None
        uid = uuid.UUID(sub)
        return db.query(Usuario).filter(Usuario.id == uid, Usuario.is_active.is_(True)).first()
    except (JWTError, ValueError):
        return None


def _require_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Dependency: require an authenticated auth v2 user."""
    token = request.cookies.get(settings.access_token_cookie_name) or ""
    # Also check Authorization header as fallback
    auth_header = request.headers.get("Authorization", "")
    if not token and auth_header.startswith("Bearer "):
        token = auth_header[7:]
    user = _resolve_current_user(token, db)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return user


def _log_security(db: Session, user_id: uuid.UUID, evento: str, ip: str | None = None, ua: str | None = None, detalles: dict | None = None):
    log_entry = LogSeguridad(
        user_id=user_id,
        evento=evento,
        ip_address=ip,
        user_agent=ua,
        detalles=detalles,
    )
    db.add(log_entry)
    db.commit()


# ── Autenticación ───────────────────────────────────────────────────────────

@router.post("/v2/login", response_model=TokenResponse)
def login(
    payload: UsuarioLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Inicio de sesión. Soporta username o email."""
    user: Usuario | None = None
    if "@" in payload.username:
        user = db.query(Usuario).filter(Usuario.email == payload.username).first()
    else:
        user = db.query(Usuario).filter(Usuario.username == payload.username).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    # Check lockout
    if user.locked_until and user.locked_until > _utcnow():
        raise HTTPException(status.HTTP_423_LOCKED, detail="Cuenta temporalmente bloqueada")

    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Cuenta desactivada")

    # Reset failed attempts on success
    if user.failed_login_attempts > 0:
        user.failed_login_attempts = 0
        user.locked_until = None

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    access_token = _create_access_token(str(user.id))
    refresh_token = _create_refresh_token(db, user.id, ip, ua)

    # HttpOnly cookies
    response.set_cookie(
        key=settings.access_token_cookie_name, value=access_token,
        httponly=True, secure=settings.access_token_cookie_secure, samesite="lax",
    )
    response.set_cookie(
        key=settings.refresh_token_cookie_name, value=refresh_token,
        httponly=True, secure=settings.access_token_cookie_secure, samesite="lax",
    )

    db.commit()
    _log_security(db, user.id, "LOGIN_EXITOSO", ip, ua)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/v2/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Refresca el access token con rotación."""
    refresh_token_val = request.cookies.get(settings.refresh_token_cookie_name, "")
    if not refresh_token_val:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token de refresco requerido")

    token_row = db.query(TokenSesion).filter(
        TokenSesion.token == refresh_token_val,
        TokenSesion.revoked.is_(False),
        TokenSesion.expires_at > _utcnow(),
    ).first()
    if not token_row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")

    # Rotación: revocar el anterior
    token_row.revoked = True

    user = db.query(Usuario).filter(Usuario.id == token_row.user_id, Usuario.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")

    ip = request.client.host if request.client else token_row.ip_address
    ua = request.headers.get("user-agent") or token_row.user_agent

    new_access = _create_access_token(str(user.id))
    new_refresh = _create_refresh_token(db, user.id, ip, ua)

    response.set_cookie(
        key=settings.access_token_cookie_name, value=new_access,
        httponly=True, secure=settings.access_token_cookie_secure, samesite="lax",
    )
    response.set_cookie(
        key=settings.refresh_token_cookie_name, value=new_refresh,
        httponly=True, secure=settings.access_token_cookie_secure, samesite="lax",
    )

    db.commit()
    return TokenResponse(access_token=new_access, refresh_token=new_refresh, user=user)


@router.post("/v2/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Cierra sesión eliminando cookies y revocando el refresh token."""
    refresh_token_val = request.cookies.get(settings.refresh_token_cookie_name, "")
    if refresh_token_val:
        token_row = db.query(TokenSesion).filter(TokenSesion.token == refresh_token_val).first()
        if token_row:
            token_row.revoked = True
            _log_security(db, token_row.user_id, "LOGOUT", request.client.host if request.client else None, request.headers.get("user-agent"))
            db.commit()

    response.delete_cookie(key=settings.access_token_cookie_name, httponly=True, samesite="lax")
    response.delete_cookie(key=settings.refresh_token_cookie_name, httponly=True, samesite="lax")


# ── Sesiones activas ────────────────────────────────────────────────────────

@router.get("/v2/sessions", response_model=list[TokenSesionRead])
def list_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Lista las sesiones activas del usuario autenticado."""
    sessions = db.query(TokenSesion).filter(
        TokenSesion.user_id == current_user.id,
        TokenSesion.revoked.is_(False),
    ).order_by(TokenSesion.last_active.desc()).all()
    return sessions


@router.post("/v2/sessions/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Revoca una sesión específica."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ID de sesión inválido")
    session = db.query(TokenSesion).filter(
        TokenSesion.id == sid,
        TokenSesion.user_id == current_user.id,
        TokenSesion.revoked.is_(False),
    ).first()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")
    session.revoked = True
    db.commit()


# ── Perfil de usuario ───────────────────────────────────────────────────────

@router.get("/v2/me", response_model=UsuarioRead)
def get_me(
    current_user: Usuario = Depends(_require_user),
):
    """Obtiene el perfil del usuario autenticado."""
    return current_user


@router.patch("/v2/me", response_model=UsuarioRead)
def update_me(
    payload: UsuarioSelfUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Actualiza el perfil del usuario autenticado."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if payload.username is not None and payload.username != current_user.username:
        existing = db.query(Usuario).filter(Usuario.username == payload.username).first()
        if existing:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya está en uso")
        current_user.username = payload.username

    if payload.email is not None and payload.email != current_user.email:
        existing = db.query(Usuario).filter(Usuario.email == payload.email).first()
        if existing:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El correo ya está registrado")
        current_user.email = payload.email
        current_user.is_email_verified = False

    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Se requiere la contraseña actual")
        if not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Contraseña actual incorrecta")
        current_user.password_hash = get_password_hash(payload.new_password)

        # Guardar en historial
        db.add(HistorialContrasena(user_id=current_user.id, password_hash=current_user.password_hash))

    db.commit()
    db.refresh(current_user)
    _log_security(db, current_user.id, "PERFIL_ACTUALIZADO", ip, ua)
    return current_user


# ── Gestión de usuarios (admin) ─────────────────────────────────────────────

@router.get("/v2/users", response_model=list[UsuarioRead])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Lista usuarios. Requiere autenticación."""
    return db.query(Usuario).offset(skip).limit(limit).all()


@router.get("/v2/users/{user_id}", response_model=UsuarioRead)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Obtiene un usuario por ID."""
    return _get_usuario_o_404(user_id, db)


@router.patch("/v2/users/{user_id}", response_model=UsuarioRead)
def update_user(
    user_id: str,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Actualiza un usuario (admin)."""
    user = _get_usuario_o_404(user_id, db)
    update_data = payload.model_dump(exclude_unset=True, exclude={"password"})
    if payload.password:
        update_data["password_hash"] = get_password_hash(payload.password)
    for key, val in update_data.items():
        setattr(user, key, val)
    db.commit()
    db.refresh(user)
    return user


@router.post("/v2/register", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
):
    """Registro de nuevo usuario."""
    if db.query(Usuario).filter(Usuario.email == payload.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El correo ya está registrado")
    if db.query(Usuario).filter(Usuario.username == payload.username).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya está en uso")

    user = Usuario(
        id=uuid.uuid4(),
        sede_id=payload.sede_id,
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        rol_plataforma_id=payload.rol_plataforma_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Roles ───────────────────────────────────────────────────────────────────

@router.get("/v2/roles", response_model=list[RolPlataformaRead])
def list_roles(db: Session = Depends(get_db)):
    return db.query(RolPlataforma).all()  # Catálogo < 100 registros — excepción permitida


@router.post("/v2/roles", response_model=RolPlataformaRead, status_code=status.HTTP_201_CREATED)
def create_role(payload: RolPlataformaCreate, db: Session = Depends(get_db)):
    if db.query(RolPlataforma).filter(RolPlataforma.nombre == payload.nombre).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El rol ya existe")
    role = RolPlataforma(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.patch("/v2/roles/{role_id}", response_model=RolPlataformaRead)
def update_role(role_id: str, payload: RolPlataformaUpdate, db: Session = Depends(get_db)):
    try:
        rid = uuid.UUID(role_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ID de rol inválido")
    role = db.query(RolPlataforma).filter(RolPlataforma.id == rid).first()
    if not role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Rol no encontrado")
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(role, key, val)
    db.commit()
    db.refresh(role)
    return role


# ── Roles modulares ─────────────────────────────────────────────────────────

@router.get("/v2/module-roles", response_model=list[UsuarioRolModuloRead])
def list_module_roles(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    return db.query(UsuarioRolModulo).filter(
        UsuarioRolModulo.user_id == current_user.id,
    ).all()


@router.post("/v2/module-roles", response_model=UsuarioRolModuloRead, status_code=status.HTTP_201_CREATED)
def assign_module_role(
    payload: UsuarioRolModuloCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    mr = UsuarioRolModulo(user_id=current_user.id, **payload.model_dump())
    db.add(mr)
    db.commit()
    db.refresh(mr)
    return mr


# ── Seguridad / Forense ─────────────────────────────────────────────────────

@router.get("/v2/security-log", response_model=list[LogSeguridadRead])
def list_security_log(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    return db.query(LogSeguridad).filter(
        LogSeguridad.user_id == current_user.id,
    ).order_by(LogSeguridad.created_at.desc()).limit(limit).all()


@router.post("/v2/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: CambioPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Cambio de contraseña con verificación de la actual."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Contraseña actual incorrecta")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.add(HistorialContrasena(user_id=current_user.id, password_hash=current_user.password_hash))
    db.commit()
    _log_security(db, current_user.id, "CAMBIO_CONTRASENA", request.client.host if request.client else None, request.headers.get("user-agent"))


@router.post("/v2/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Solicita restablecimiento de contraseña."""
    user = db.query(Usuario).filter(Usuario.email == payload.email).first()
    if not user:
        return {"status": "success", "message": "Si el correo existe, recibirás instrucciones"}

    import secrets
    token = secrets.token_urlsafe(32)
    expires_at = _utcnow() + timedelta(hours=1)
    db.add(TokenResetContrasena(user_id=user.id, token=token, expires_at=expires_at))
    db.commit()

    # Send the reset email (not just log the token)
    from backend.services.email import render_reset_password, send_email

    subject, html = render_reset_password(token)
    send_email(to=user.email, subject=subject, html=html)
    return {"status": "success", "message": "Si el correo existe, recibirás instrucciones"}


@router.post("/v2/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Restablece la contraseña usando un token."""
    if len(payload.new_password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="La contraseña debe tener al menos 8 caracteres")

    token_row = db.query(TokenResetContrasena).filter(
        TokenResetContrasena.token == payload.token,
        TokenResetContrasena.used.is_(False),
        TokenResetContrasena.expires_at > _utcnow(),
    ).first()
    if not token_row:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Token inválido, expirado o ya utilizado")

    user = db.query(Usuario).filter(Usuario.id == token_row.user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    user.password_hash = get_password_hash(payload.new_password)
    token_row.used = True
    db.add(HistorialContrasena(user_id=user.id, password_hash=user.password_hash))
    db.commit()
    return {"status": "success", "message": "Contraseña restablecida exitosamente"}


# ── MFA ─────────────────────────────────────────────────────────────────────

@router.post("/v2/mfa/setup", response_model=MfaSetupResponse)
def setup_mfa(
    current_user: Usuario = Depends(_require_user),
):
    """Configura MFA/TOTP para el usuario."""
    import base64
    import struct

    try:
        import pyotp
    except ImportError:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="MFA no disponible (pyotp no instalado)")

    secret = pyotp.random_base32()
    current_user.mfa_secret = secret
    issuer = "CCF El Faro"
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=current_user.email, issuer_name=issuer)

    return MfaSetupResponse(secret=secret, qr_code_url=uri)


@router.post("/v2/mfa/verify")
def verify_mfa(
    payload: MfaVerifyRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Verifica y activa MFA con un código TOTP."""
    if not current_user.mfa_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="MFA no configurado. Ejecuta /mfa/setup primero")
    try:
        import pyotp
    except ImportError:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="MFA no disponible")
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(payload.token):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Código TOTP inválido")
    current_user.is_mfa_enabled = True
    db.commit()
    return {"status": "success", "message": "MFA activado exitosamente"}


@router.post("/v2/mfa/disable")
def disable_mfa(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Desactiva MFA."""
    current_user.mfa_secret = None
    current_user.is_mfa_enabled = False
    current_user.mfa_backup_codes = []
    db.commit()
    return {"status": "success", "message": "MFA desactivado"}


@router.get("/v2/mfa/backup-codes", response_model=MfaRecoveryResponse)
def get_backup_codes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    """Genera y retorna códigos de respaldo MFA."""
    import secrets
    codes = [secrets.token_hex(4) for _ in range(8)]
    current_user.mfa_backup_codes = codes
    db.commit()
    return MfaRecoveryResponse(backup_codes=codes)


# ── Niveles / Gamificación ──────────────────────────────────────────────────

@router.get("/v2/levels", response_model=list[NivelGamificadoRead])
def list_levels(db: Session = Depends(get_db)):
    return db.query(NivelGamificado).order_by(NivelGamificado.min_xp).all()  # Catálogo — excepción permitida


@router.post("/v2/levels", response_model=NivelGamificadoRead, status_code=status.HTTP_201_CREATED)
def create_level(payload: NivelGamificadoCreate, db: Session = Depends(get_db)):
    level = NivelGamificado(**payload.model_dump())
    db.add(level)
    db.commit()
    db.refresh(level)
    return level


# ── Medallas ────────────────────────────────────────────────────────────────

@router.get("/v2/badges", response_model=list[MedallaRead])
def list_badges(db: Session = Depends(get_db)):
    return db.query(Medalla).all()  # Catálogo — excepción permitida


@router.post("/v2/badges", response_model=MedallaRead, status_code=status.HTTP_201_CREATED)
def create_badge(payload: MedallaCreate, db: Session = Depends(get_db)):
    badge = Medalla(**payload.model_dump())
    db.add(badge)
    db.commit()
    db.refresh(badge)
    return badge


@router.get("/v2/user-badges", response_model=list[MedallaUsuarioRead])
def list_user_badges(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    return db.query(MedallaUsuario).filter(
        MedallaUsuario.user_id == current_user.id,
    ).all()


# ── Notificaciones ──────────────────────────────────────────────────────────

@router.get("/v2/notifications", response_model=list[NotificacionRead])
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    q = db.query(NotificacionUsuario).filter(NotificacionUsuario.user_id == current_user.id)
    if unread_only:
        q = q.filter(NotificacionUsuario.is_read.is_(False))
    return q.order_by(NotificacionUsuario.created_at.desc()).limit(limit).all()


@router.post("/v2/notifications/{notif_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notification_read(
    notif_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    try:
        nid = uuid.UUID(notif_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ID inválido")
    notif = db.query(NotificacionUsuario).filter(
        NotificacionUsuario.id == nid,
        NotificacionUsuario.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    notif.is_read = True
    db.commit()


@router.post("/v2/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    db.query(NotificacionUsuario).filter(
        NotificacionUsuario.user_id == current_user.id,
        NotificacionUsuario.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()


# ── Recordatorios ───────────────────────────────────────────────────────────

@router.get("/v2/reminders", response_model=list[RecordatorioRead])
def list_reminders(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    return db.query(RecordatorioUsuario).filter(
        RecordatorioUsuario.user_id == current_user.id,
        RecordatorioUsuario.is_dismissed.is_(False),
    ).order_by(RecordatorioUsuario.remind_at).all()


@router.post("/v2/reminders", response_model=RecordatorioRead, status_code=status.HTTP_201_CREATED)
def create_reminder(
    payload: RecordatorioCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    reminder = RecordatorioUsuario(user_id=current_user.id, **payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.post("/v2/reminders/{reminder_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    try:
        rid = uuid.UUID(reminder_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ID inválido")
    reminder = db.query(RecordatorioUsuario).filter(
        RecordatorioUsuario.id == rid,
        RecordatorioUsuario.user_id == current_user.id,
    ).first()
    if not reminder:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Recordatorio no encontrado")
    reminder.is_dismissed = True
    db.commit()


# ── Preferencias UI ─────────────────────────────────────────────────────────

@router.get("/v2/preferences", response_model=PreferenciaUIRead)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    pref = db.query(PreferenciaUI).filter(PreferenciaUI.user_id == current_user.id).first()
    if not pref:
        pref = PreferenciaUI(user_id=current_user.id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.patch("/v2/preferences", response_model=PreferenciaUIRead)
def update_preferences(
    payload: PreferenciaUIUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_require_user),
):
    pref = db.query(PreferenciaUI).filter(PreferenciaUI.user_id == current_user.id).first()
    if not pref:
        pref = PreferenciaUI(user_id=current_user.id, settings=payload.settings)
        db.add(pref)
    else:
        pref.settings = payload.settings
    db.commit()
    db.refresh(pref)
    return pref

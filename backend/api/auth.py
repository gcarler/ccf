"""
CCF MESH - ROUTER DE AUTENTICACION V3.9 (ESTANDAR DE CALIDAD)
Maneja el inicio de sesion, registro y gestion de tokens con UUID.
"""

import logging
from datetime import timedelta
from typing import List

from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     status)
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.auth import (create_access_token, create_refresh_token,
                          normalize_role, require_active_user, require_admin)
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import get_user_effective_permissions, record_session
from backend.core.rate_limit import rate_limiter

settings = get_settings()
log = logging.getLogger(__name__)

router = APIRouter(tags=["Autenticacion"])


def _ensure_default_permissions(db: Session, user: models.User) -> None:
    """Asigna permisos por defecto al usuario según su rol si no tiene."""
    from backend.core.permissions import DEFAULT_ROLES
    from backend.models_identity import UserPermission

    existing = db.query(UserPermission).filter(UserPermission.user_id == user.id).first()
    if existing:
        return

    role = normalize_role(str(getattr(user, "role", "")))
    default_perms = {}

    for role_def in DEFAULT_ROLES:
        if role_def["name"].lower() == role:
            for p in role_def["permissions"]:
                default_perms[p] = "allow"
            break

    # Even if no exact role match, grant basic profile access
    if not default_perms:
        default_perms = {"profile:manage": "allow"}

    up = UserPermission(user_id=user.id, permissions=default_perms)
    db.add(up)
    db.commit()


@router.post(
    "/login",
    response_model=schemas.Token,
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Inicio de sesion ministerial. Soporta Email o Username."""
    from backend.core.security import \
        verify_password  # Import local para evitar circularidad

    user = None
    if "@" in form_data.username:
        user = crud.get_user_by_email(db, email=form_data.username)
    else:
        user = crud.get_user_by_username(db, username=form_data.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales ministeriales incorrectas",
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales ministeriales incorrectas",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cuenta desactivada. Contacta al administrador.",
        )

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    payload = {"sub": str(user.id), "role": normalize_role(str(user.role))}
    access_token = create_access_token(
        data=payload,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token = create_refresh_token(
        db, int(user.id), ip_address=ip_address, user_agent=user_agent
    )

    record_session(int(user.id), access_token)

    # Access Token Cookie (session-only: expires on browser close)
    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.access_token_cookie_secure,
        samesite="lax",
    )

    # Refresh Token Cookie (session-only: expires on browser close)
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.access_token_cookie_secure,
        samesite="lax",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


@router.post("/refresh", response_model=schemas.Token)
def refresh_access_token(
    request: Request,
    response: Response,
    payload: schemas.RefreshTokenRequest = None,
    db: Session = Depends(get_db),
):
    """Refresca el access token usando rotación de tokens y cookies seguras."""
    # Intentar obtener el refresh token de la cookie, fallback al payload
    refresh_token = request.cookies.get(settings.refresh_token_cookie_name)
    if not refresh_token and payload:
        refresh_token = payload.refresh_token

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )

    token_row = crud.get_valid_refresh_token(db, refresh_token)
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = crud.get_user(db, int(token_row.user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Rotación: Invalidar el anterior
    crud.revoke_refresh_token(db, refresh_token)

    # Capturar info actual
    ip_address = request.client.host if request.client else token_row.ip_address
    user_agent = request.headers.get("user-agent") or token_row.user_agent

    # Crear nuevos tokens
    new_refresh_token = create_refresh_token(
        db, int(user.id), ip_address=ip_address, user_agent=user_agent
    )
    new_access_token = create_access_token(
        data={"sub": str(user.id), "role": normalize_role(str(user.role))},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    record_session(int(user.id), new_access_token)

    # Actualizar cookies (session-only)
    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=new_access_token,
        httponly=True,
        secure=settings.access_token_cookie_secure,
        samesite="lax",
    )
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=new_refresh_token,
        httponly=True,
        secure=settings.access_token_cookie_secure,
        samesite="lax",
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh_token,
    }


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cierra sesión eliminando las cookies y revocando el refresh token."""
    # Revoke refresh token if present in cookie
    refresh_token_cookie = request.cookies.get(settings.refresh_token_cookie_name)
    if refresh_token_cookie:
        crud.revoke_refresh_token(db, refresh_token_cookie)

    response.delete_cookie(
        key=settings.access_token_cookie_name,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        httponly=True,
        samesite="lax",
    )


@router.get("/sessions")
def get_sessions(
    current_user: models.User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """Lista las sesiones activas del usuario autenticado."""
    from backend.models_identity import RefreshToken
    sessions = db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked.is_(False)
    ).order_by(RefreshToken.last_active.desc()).all()
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "last_active": s.last_active.isoformat() if s.last_active else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "is_current": True,  # Will be refined client-side
        })
    return result


@router.post("/sessions/{session_id}/revoke", status_code=204)
def revoke_session(
    session_id: int,
    current_user: models.User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """Revoca una sesión específica del usuario autenticado."""
    from backend.models_identity import RefreshToken
    session = db.query(RefreshToken).filter(
        RefreshToken.id == session_id,
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked.is_(False)
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    session.revoked = True
    db.commit()


@router.post(
    "/register",
    response_model=schemas.User,
    dependencies=[Depends(rate_limiter(limit=5, window_seconds=60))],
)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registro de nuevos miembros. Envía email de verificación automáticamente."""
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400, detail="El correo ya esta registrado en el ministerio"
        )

    user.role = "estudiante"
    created = crud.create_user(db=db, user=user)

    # Asignar permisos por defecto según rol
    _ensure_default_permissions(db, created)

    # Auto-enviar email de verificación post-registro
    try:
        from backend.crud.identity import create_verification_token
        from backend.services.email import render_verify_email, send_email

        token_row = create_verification_token(db, created.id)
        subject, html = render_verify_email(token_row.token)
        send_email(to=created.email, subject=subject, html=html)
    except Exception as exc:
        log.warning("No se pudo enviar email de verificación: %s", exc)

    return created


@router.get("/me", response_model=schemas.User)
def get_current_ministerial_user(
    current_user: models.User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene el perfil del usuario autenticado con sus permisos."""
    current_user.permissions = get_user_effective_permissions(db, current_user)
    return current_user


@router.patch("/me", response_model=schemas.User)
def update_current_user(
    payload: schemas.UserSelfUpdate,
    current_user: models.User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """Actualiza el perfil del usuario autenticado (username, email, password)."""
    from backend.core.security import verify_password

    # If changing email, check not taken
    if payload.email is not None and payload.email != current_user.email:
        existing = crud.get_user_by_email(db, payload.email)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="El correo ya está registrado en el ministerio",
            )

    # If changing username, check not taken
    if payload.username is not None and payload.username != current_user.username:
        existing = crud.get_user_by_username(db, payload.username)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="El nombre de usuario ya está en uso",
            )

    # Password change requires current_password
    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(
                status_code=400,
                detail="Se requiere la contraseña actual para cambiarla",
            )
        if not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=403,
                detail="La contraseña actual es incorrecta",
            )

    # Build update data
    update_data: dict = {}
    if payload.username is not None:
        update_data["username"] = payload.username
    email_changed = payload.email is not None and payload.email != current_user.email
    if payload.email is not None:
        update_data["email"] = payload.email
        if email_changed:
            update_data["is_email_verified"] = False
    if payload.new_password:
        update_data["password"] = payload.new_password

    if not update_data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    user = crud.update_user(db, current_user.id, schemas.UserUpdate(**update_data))

    # Auto-send verification email if email changed
    if email_changed:
        try:
            from backend.crud.identity import create_verification_token
            from backend.services.email import render_verify_email, send_email
            token_row = create_verification_token(db, user.id)
            subject, html = render_verify_email(token_row.token)
            send_email(to=user.email, subject=subject, html=html)
        except Exception as exc:
            log.warning("No se pudo enviar email de verificación tras cambio de email: %s", exc)

    return user


@router.get("/me/permissions", response_model=dict)
def get_current_user_permissions(
    current_user: models.User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """Obtiene los permisos efectivos del usuario autenticado."""
    perms = get_user_effective_permissions(db, current_user)
    return {"permissions": perms}


@router.get("/user-list", response_model=List[schemas.User])
def list_ministerial_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Lista de usuarios. Requiere autenticación."""
    return crud.get_users(db, skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=schemas.User)
def get_ministerial_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Obtiene un usuario por ID."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}", response_model=schemas.User)
def update_ministerial_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Actualiza un usuario ministerial (rol, estado, etc)."""
    user = crud.update_user(db, user_id=user_id, payload=payload)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_ministerial_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina un usuario del sistema."""
    success = crud.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return None


@router.post("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verifica el correo electrónico usando un token enviado por email."""
    user_id = crud.use_verification_token(db, token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificación inválido o expirado",
        )
    return {"status": "success", "message": "Correo verificado exitosamente"}


@router.post("/send-verification-email")
def send_verification_email(
    email: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Envía el email de verificación al usuario."""
    from backend.services.email import render_verify_email, send_email

    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.is_email_verified:
        return {"status": "success", "message": "El correo ya está verificado"}

    token_row = crud.create_verification_token(db, user.id)
    subject, html = render_verify_email(token_row.token)
    send_email(to=user.email, subject=subject, html=html)
    return {"status": "success", "message": "Email de verificación enviado"}


@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    """Solicita restablecimiento de contraseña. Envía email con token si el correo existe."""
    from backend.services.email import render_reset_password, send_email

    user = crud.get_user_by_email(db, email)
    # No revelar si el email existe o no (seguridad)
    if not user:
        return {
            "status": "success",
            "message": "Si el correo existe, recibirás instrucciones",
        }

    token_row = crud.create_reset_token(db, user.id)
    subject, html = render_reset_password(token_row.token)
    send_email(to=user.email, subject=subject, html=html)
    return {
        "status": "success",
        "message": "Si el correo existe, recibirás instrucciones",
    }


@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    """Restablece la contraseña usando un token enviado por email."""
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400, detail="La contraseña debe tener al menos 8 caracteres"
        )

    success = crud.use_reset_token(db, token, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de restablecimiento inválido, expirado o ya utilizado",
        )
    return {"status": "success", "message": "Contraseña restablecida exitosamente"}


@router.get("/google/login")
def google_login(request: Request):
    """Redirige al usuario a la pantalla de consentimiento de Google OAuth."""
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth no está configurado")

    redirect_uri = request.url_for("google_callback")
    if settings.google_redirect_uri:
        redirect_uri = settings.google_redirect_uri

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    from urllib.parse import urlencode

    google_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=google_url)


@router.get("/google/callback")
def google_callback(
    code: str,
    error: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Callback de Google OAuth. Intercambia el code por tokens, crea/logea al usuario."""
    import httpx

    if error or not code:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")

    redirect_uri = request.url_for("google_callback") if request else ""
    if settings.google_redirect_uri:
        redirect_uri = settings.google_redirect_uri

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
        raise HTTPException(
            status_code=400, detail=f"Error exchanging Google code: {exc}"
        )

    id_token = token_data.get("id_token")
    access_token_google = token_data.get("access_token")
    if not id_token and not access_token_google:
        raise HTTPException(status_code=400, detail="No se recibió token de Google")

    # 2. Get user info from Google
    try:
        userinfo_resp = httpx.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token_google}"},
            timeout=15,
        )
        userinfo_resp.raise_for_status()
        google_user = userinfo_resp.json()
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Error getting Google user info: {exc}"
        )

    google_email = google_user.get("email", "")
    google_name = google_user.get("name", "")
    _google_id = google_user.get("id", "")
    _google_picture = google_user.get("picture", "")

    if not google_email:
        raise HTTPException(status_code=400, detail="Google no proporcionó un email")

    # 3. Find or create user
    user = crud.get_user_by_email(db, google_email)
    if not user:
        # Create new user from Google data
        import secrets

        from backend.core.security import get_password_hash

        user = models.User(
            username=google_email.split("@")[0],
            email=google_email,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            role="estudiante",
            is_active=True,
            is_email_verified=True,  # Google already verified the email
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Assign default permissions
        _ensure_default_permissions(db, user)

        # Try to create member profile
        try:
            persona = models.Persona(
                user_id=user.id,
                first_name=(
                    google_name.split(" ")[0]
                    if google_name
                    else google_email.split("@")[0]
                ),
                last_name=(
                    " ".join(google_name.split(" ")[1:])
                    if google_name and len(google_name.split(" ")) > 1
                    else ""
                ),
                email=google_email,
                church_role="Miembro",
                spiritual_status="Nuevo",
            )
            db.add(persona)
            db.commit()
        except Exception:
            db.rollback()
    else:
        # Existing user — ensure active
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Cuenta desactivada")

    # 4. Generate JWT tokens
    from backend.auth import create_access_token, create_refresh_token

    payload = {"sub": str(user.id), "role": normalize_role(str(user.role))}
    access_token = create_access_token(
        data=payload,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token = create_refresh_token(db, int(user.id))

    # 5. Redirect to frontend with tokens (fragment to avoid server logs)
    frontend_url = settings.frontend_url.rstrip("/")
    redirect_target = (
        f"{frontend_url}/auth/callback"
        f"#token={access_token}"
        f"&refresh={refresh_token}"
    )
    return RedirectResponse(url=redirect_target)


@router.get("/stats/summary", response_model=dict)
def auth_stats_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Resumen estadistico de autenticacion para el dashboard."""
    total = db.query(models.User).count()
    active = db.query(models.User).filter(models.User.is_active.is_(True)).count()
    verified = (
        db.query(models.User).filter(models.User.is_email_verified.is_(True)).count()
    )
    roles = (
        db.query(models.User.role, func.count(models.User.id))
        .group_by(models.User.role)
        .all()
    )
    return {
        "total_users": total,
        "active_users": active,
        "verified_users": verified,
        "by_role": {role: count for role, count in roles},
    }

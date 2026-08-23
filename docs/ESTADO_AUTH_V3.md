# Estado del Módulo Auth v3

**Actualizado:** 2026-07-18

---

## Resumen

Sistema de autenticación de la plataforma CCF. Maneja login, registro, verificación de email, recuperación de contraseña y gestión de sesiones. Es la puerta de entrada a toda la plataforma.

| Métrica | Valor |
|---|---|
| Router | `backend/api/auth_v3.py` |
| CRUD | `backend/crud/identity.py`, `backend/crud/kernel.py` |
| Modelos | `backend/models_auth.py`, `backend/models_identity.py`, `backend/models_kernel.py` |
| Schemas | `backend/schemas/auth_v3.py`, `backend/schemas/identity.py` |
| Frontend | `frontend/src/app/plataforma/account/`, `frontend/src/app/plataforma/settings/` |
| Tests | Sin archivo de cobertura dedicado |
| Docs | `docs/PLATAFORMA_AUTH_RBAC_API_UI.md`, `docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md` |

---

## Contrato canónico

- `auth_users.id == personas.id` (mismo UUID)
- Autenticación via JWT
- Soporte para Google OAuth (código listo, faltan credenciales)
- Roles de plataforma via `RolPlataforma` + roles modulares via `UsuarioRolModulo`
- Permisos via `MODULE_PERMISSION_MAP`

---

## Backend

| Aspecto | Detalle |
|---|---|
| Router | `backend/api/auth_v3.py` |
| Schemas | `backend/schemas/auth_v3.py`, `backend/schemas/identity.py` |
| Modelos | `backend/models_auth.py`, `backend/models_identity.py`, `backend/models_kernel.py` |
| CRUD | `backend/crud/identity.py`, `backend/crud/kernel.py` |

### Endpoints principales

- `POST /api/v3/auth/login` — Inicio de sesión
- `GET /api/v3/auth/google` — Login con Google (crea `Usuario` + `Persona` si el correo no existe)
- `POST /api/v3/auth/initialize-password` — Configurar contraseña inicial (token de un solo uso)
- `POST /api/v3/auth/change-password` — Cambiar contraseña autenticado
- `POST /api/v3/auth/forgot-password` — Recuperación
- `POST /api/v3/auth/reset-password` — Restablecer contraseña
- `GET /api/v3/auth/me` — Perfil del usuario autenticado
- `PATCH /api/v3/auth/me` — Actualizar perfil
- `POST /api/v3/auth/verify-email` — Verificar correo
- `POST /api/v3/auth/send-verification-email` — Reenviar correo de verificación
- `GET /api/v3/auth/check-email` — Verificar disponibilidad de email

> No existe un endpoint público de registro (`POST /api/v3/auth/register`):
> las cuentas se crean vía Google SSO o aprovisionamiento administrativo con
> `initialize-password`.

---

## Permisos

| Endpoint | Permiso |
|---|---|
| `/api/v3/auth/login` | Público |
| `/api/v3/auth/initialize-password` | Público (token de un solo uso) |
| `/api/v3/auth/forgot-password` | Público |
| `/api/v3/auth/reset-password` | Público |
| `/api/v3/auth/me` (GET/PATCH) | Usuario autenticado |
| `/api/v3/auth/check-email` | Público |

---

## Issues conocidos

- 5 imports locales dentro de funciones en `auth_v3.py`
- Google OAuth pendiente de configuración (GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en .env)

# Contrato Runtime — Auth Compartida CCF

> **Objetivo:** fijar el contrato operativo real entre backend Auth v3, `apiFetch`, `AuthContext` y pantallas públicas/auth para que login, refresh y OAuth Google no vuelvan a degradarse por drift entre capas.

## 1. Leer primero

```bash
cat /root/ccf/docs/ESTADO_PLATAFORMA_COMPARTIDA.md
cat /root/ccf/docs/PLATAFORMA_AUTH_RBAC_API_UI.md
cat /root/ccf/docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md
```

## 2. Owner y superficie

Owner: plataforma compartida.

Archivos canónicos:

- `backend/api/auth_v3.py`
- `backend/models_auth.py`
- `backend/core/permissions.py`
- `frontend/src/lib/http.ts`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/app/login/page.tsx`
- `frontend/src/app/register/page.tsx`
- `frontend/src/app/auth/**`
- `frontend/src/app/plataforma/account/page.tsx`

## 3. Endpoints canónicos

Base única: `/api/v3/auth/*`

Contrato vigente:

- `POST /api/v3/auth/login`
- `POST /api/v3/auth/register`
- `GET /api/v3/auth/me`
- `PATCH /api/v3/auth/me`
- `POST /api/v3/auth/refresh`
- `POST /api/v3/auth/logout`
- `GET /api/v3/auth/sessions`
- `POST /api/v3/auth/sessions/{session_id}/revoke`
- `POST /api/v3/auth/sessions/revoke-all`
- `GET /api/v3/auth/google`
- `GET /api/v3/auth/google/callback`
- `GET /api/v3/auth/check-email`
- `POST /api/v3/auth/initialize-password`
- `POST /api/v3/auth/change-password`
- `POST /api/v3/auth/verify-email`
- `POST /api/v3/auth/forgot-password`
- `POST /api/v3/auth/reset-password`
- `POST /api/v3/auth/send-verification-email`

## 4. Transporte de sesión

El runtime actual es dual y eso debe tratarse como contrato explícito, no como accidente:

1. El backend emite `access_token` y `refresh_token`.
2. El backend también persiste cookies `HttpOnly` para access/refresh.
3. El frontend guarda `ccf_token` y `ccf_refresh_token` en `sessionStorage`.
4. `apiFetch` adjunta `Authorization: Bearer <access_token>` cuando existe token en memoria/sessionStorage.
5. Si una llamada recibe `401`, `apiFetch` intenta un único refresh.
6. `AuthContext` puede bootstrapear sesión desde cookies llamando `POST /api/v3/auth/refresh` sin body.

Implicación:

- el backend debe aceptar refresh tanto por body JSON como por cookie
- el frontend no puede asumir una sola fuente de sesión
- cualquier cambio aquí exige testear login, refresh y una ruta autenticada real

## 5. Contrato de payloads

`POST /api/v3/auth/login`

```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

`POST /api/v3/auth/register`

```json
{
  "email": "user@example.com",
  "password": "secret",
  "first_name": "Nombre",
  "last_name": "Apellido"
}
```

`POST /api/v3/auth/forgot-password`

```json
{
  "email": "user@example.com"
}
```

`POST /api/v3/auth/verify-email`

```json
{
  "token": "..."
}
```

`POST /api/v3/auth/reset-password`

Acepta JSON canónico:

```json
{
  "token": "...",
  "new_password": "NuevaClave123"
}
```

Compatibilidad tolerada hoy:

```json
{
  "token": "...",
  "password": "NuevaClave123"
}
```

`POST /api/v3/auth/send-verification-email`

```json
{
  "email": "user@example.com"
}
```

Regla:

- payload JSON es el contrato canónico para frontend nuevo
- query params viejos solo sobreviven como compatibilidad transitoria backend

## 6. Reglas de frontend

- `apiFetch` es obligatorio para auth UI y rutas `/plataforma/**`
- código nuevo no debe consumir `/api/auth/*`
- pantallas públicas/auth no deben hardcodear `/auth/register`, `/auth/me`, `/auth/refresh`, `/auth/logout`
- `AuthContext` y `http.ts` son la única capa autorizada para refresh compartido

## 7. Compatibilidad legacy aún activa

Esto no es contrato nuevo; es deuda explícita a eliminar:

- la ruta mock frontend conserva aliases `/auth/me` y `/auth/logout`

Clasificación:

- owner: plataforma compartida
- estado: drift activo
- no reusar esos paths en código nuevo

Contrato cruzado ya consolidado el **2026-07-16**:

- dashboard admin usa `/api/dashboard/admin`
- sesiones del usuario actual usan `/api/v3/auth/sessions*`

## 8. Gates obligatorios

```bash
cd /root/ccf
./venv/bin/python scripts/test_platform_quality.py
./venv/bin/python -m py_compile backend/api/auth_v3.py
./venv/bin/python -m pytest -q -o addopts='' tests/test_auth_me.py tests/test_auth_v3_deep.py tests/test_structural_contracts.py
cd /root/ccf/frontend && npm run build
```

Checks manuales mínimos:

- login con email/password
- refresh sin loop infinito
- callback Google resuelve o falla con error controlado
- `/plataforma/account` puede leer perfil y reenviar verificación

## 9. Criterio de no aprobación

- reaparece consumo nuevo de `/api/auth/*`
- se duplica lógica de refresh fuera de `http.ts` y `AuthContext.tsx`
- backend acepta payload distinto al documentado sin compatibilidad explícita
- se rompe el bootstrap por cookies o el refresh por body

## 10. Estado

`PEND-DRIFT-AUTH-001` queda parcialmente cerrado el **2026-07-16**: el contrato runtime ya está documentado, se migraron consumidores públicos críticos a `/api/v3/auth/*`, el dashboard admin quedó consolidado en `/api/dashboard/admin` y las sesiones propias en `/api/v3/auth/sessions*`. Quedan aliases mock de compatibilidad por revisar.

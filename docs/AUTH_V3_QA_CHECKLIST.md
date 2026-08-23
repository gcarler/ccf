# QA Checklist — Módulo Auth v3

**Fecha:** 2026-07-18

---

## Backend

### Autenticación
- [ ] `POST /api/v3/auth/login` con credenciales válidas → 200 + token JWT
- [ ] `POST /api/v3/auth/login` con credenciales inválidas → 401
- [ ] `GET /api/v3/auth/google` (y callback) crea usuario + persona cuando el correo no existe
- [ ] `POST /api/v3/auth/initialize-password` configura la contraseña inicial con token de un solo uso
- [ ] `POST /api/v3/auth/initialize-password` con token inválido o expirado → 400
- [ ] `POST /api/v3/auth/forgot-password` envía email
- [ ] `POST /api/v3/auth/reset-password` con token válido

### Perfil
- [ ] `GET /api/v3/auth/me` retorna perfil del usuario autenticado
- [ ] `PATCH /api/v3/auth/me` actualiza perfil
- [ ] `GET /api/v3/auth/me` sin token → 401

### Multi-tenant
- [ ] Auth es global (no aplica sede_id)

---

## Tests

- [ ] Tests de auth pasan
- [ ] Smoke script `scripts/test_auth_v3_quality.py` pasa

# QA Checklist — Módulo Auth v3

**Fecha:** 2026-07-18

---

## Backend

### Autenticación
- [ ] `POST /api/v3/auth/login` con credenciales válidas → 200 + token JWT
- [ ] `POST /api/v3/auth/login` con credenciales inválidas → 401
- [ ] `POST /api/v3/auth/register` crea usuario + persona
- [ ] `POST /api/v3/auth/register` con email duplicado → 409
- [ ] `POST /api/v3/auth/forgot-password` envía email
- [ ] `POST /api/v3/auth/reset-password` con token válido

### Perfil
- [ ] `GET /api/v3/auth/me` retorna perfil del usuario autenticado
- [ ] `PUT /api/v3/auth/me` actualiza perfil
- [ ] `GET /api/v3/auth/me` sin token → 401

### Multi-tenant
- [ ] Auth es global (no aplica sede_id)

---

## Tests

- [ ] Tests de auth pasan
- [ ] Smoke script `scripts/test_auth_v3_quality.py` pasa

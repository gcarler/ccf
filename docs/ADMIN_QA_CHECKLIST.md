# QA Checklist — Módulo Administración

**Fecha:** 2026-07-18

---

## Backend

### Roles
- [ ] `GET /api/admin/roles` retorna lista con usuarios_count
- [ ] `POST /api/admin/roles` crea rol con nombre único
- [ ] `PATCH /api/admin/roles/{id}` actualiza permisos
- [ ] `DELETE /api/admin/roles/{id}` sin usuarios → 204
- [ ] `DELETE /api/admin/roles/{id}` con usuarios → 409
- [ ] `DELETE /api/admin/roles/{id}` inexistente → 404

### Usuarios
- [ ] `GET /api/admin/users` retorna lista
- [ ] `GET /api/admin/users/{id}` retorna detalle
- [ ] `GET /api/admin/users/{id}` inválido → 400
- [ ] `POST /api/admin/users` crea usuario + persona
- [ ] `POST /api/admin/users` duplicado → 409
- [ ] `PATCH /api/admin/users/{id}` actualiza campos
- [ ] `DELETE /api/admin/users/{id}` desactiva (is_active=false) → 204
- [ ] `PATCH /api/admin/users/{id}/role` asigna rol

### Personas
- [ ] `GET /api/admin/personas` filtra por sede del admin
- [ ] No retorna personas de otras sedes

### Variables
- [ ] `POST /api/admin/variables` con body JSON crea/actualiza variable
- [ ] `GET /api/admin/variables` retorna todas

### Stats
- [ ] `GET /api/admin/stats` retorna métricas reales
- [ ] Stats incluyen personas, donaciones, diezmos, ofrendas

### Automatizaciones
- [ ] `POST /api/admin/automations` crea regla
- [ ] `PATCH /api/admin/automations/{id}` actualiza
- [ ] `DELETE /api/admin/automations/{id}` soft delete

### Roles modulares
- [ ] `POST /api/admin/auth-role-definitions` crea rol
- [ ] `DELETE /api/admin/auth-role-definitions/{id}` sin usuarios → 204
- [ ] `DELETE /api/admin/auth-role-definitions/{id}` con usuarios → 409

### Multi-tenant
- [ ] Todas las consultas de personas filtran por sede
- [ ] Stats consideran sede del admin
- [ ] Operaciones cross-sede retornan 404

---

## Frontend

- [ ] Dashboard carga sin errores
- [ ] Dashboard muestra KPIs reales (no mock)
- [ ] Página de usuarios carga y permite operaciones CRUD
- [ ] Página de roles carga y permite editar permisos
- [ ] Página de personas carga con búsqueda
- [ ] Página de finanzas carga con datos reales

---

## Tests

- [ ] `test_admin_coverage.py` — 53/53 passed
- [ ] `scripts/test_admin_quality.py` — all gates pass

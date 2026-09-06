# QA Checklist — Módulo Administración

**Fecha:** 2026-09-06 (Auditoría Forense Integral — Certificación 100/100 A+)
**Estado:** 100/100 (A+) — CERTIFICADO ([docs/AUDITORIA_FORENSE_ADMIN_2026-09-06.md](./AUDITORIA_FORENSE_ADMIN_2026-09-06.md))
**Tests Ejecutados:** 314 pasados, 0 fallidos en 12 suites backend canónicas.

---

## Backend — Roles (consolidados)

- [x] `GET /api/admin/roles` retorna lista con `AdminRoleRead` + `users_count`
- [x] `POST /api/admin/roles` crea rol con nombre único → 201
- [x] `POST /api/admin/roles` nombre duplicado → 409
- [x] `POST /api/admin/roles` nombre vacío → 400
- [x] `PATCH /api/admin/roles/{id}` actualiza permisos → `AdminRoleRead`
- [x] `PATCH /api/admin/roles/{id}` inexistente → 404
- [x] `DELETE /api/admin/roles/{id}` sin usuarios → 204
- [x] `DELETE /api/admin/roles/{id}` con usuarios → 409
- [x] `POST /api/admin/roles` con `permissions` como lista → funciona

## Backend — Usuarios

- [x] `GET /api/admin/users` retorna `List[AdminUserRead]`
- [x] `GET /api/admin/users/{id}` retorna `AdminUserRead`
- [x] `GET /api/admin/users/{id}` UUID inválido → 400
- [x] `GET /api/admin/users/{id}` inexistente → 404
- [x] `POST /api/admin/users` crea usuario + persona → 201
- [x] `POST /api/admin/users` duplicado → 409
- [x] `PATCH /api/admin/users/{id}` actualiza campos → `AdminUserRead`
- [x] `PATCH /api/admin/users/{id}` inexistente → 404
- [x] `DELETE /api/admin/users/{id}` desactiva → 204
- [x] `DELETE /api/admin/users/{id}` inexistente → 404
- [x] `PATCH /api/admin/users/{id}/role` asigna rol → 200
- [x] `PATCH /api/admin/users/{id}/role` sin role_id → 400

## Backend — Permisos de usuario

- [x] `GET /api/admin/users/{id}/permissions` retorna `AdminUserPermissionsRead`
- [x] `GET /api/admin/users/{id}/permissions` inexistente → 404
- [x] `PUT /api/admin/users/{id}/permissions` con módulo válido → 200
- [x] `PUT /api/admin/users/{id}/permissions` módulo inválido → 400
- [x] `PUT /api/admin/users/{id}/permissions` nivel inválido → 400

## Backend — Ubicaciones

- [x] `GET /api/admin/locations` retorna `List[AdminLocationRead]`
- [x] `POST /api/admin/locations` crea ubicación → 201
- [x] `POST /api/admin/locations` nombre vacío → 400
- [x] `PATCH /api/admin/locations/{id}` actualiza → `AdminLocationRead`
- [x] `PATCH /api/admin/locations/{id}` inexistente → 404
- [x] `DELETE /api/admin/locations/{id}` elimina → 204
- [x] `DELETE /api/admin/locations/{id}` inexistente → 404

## Backend — Canales sociales

- [x] `GET /api/admin/socials` retorna `List[AdminSocialRead]`
- [x] `POST /api/admin/socials` crea canal → 201
- [x] `PATCH /api/admin/socials/{id}` actualiza → `AdminSocialRead`
- [x] `PATCH /api/admin/socials/{id}` inexistente → 404
- [x] `DELETE /api/admin/socials/{id}` elimina → 204
- [x] `DELETE /api/admin/socials/{id}` inexistente → 404

## Backend — Variables de sistema

- [x] `GET /api/admin/variables` retorna dict key→value
- [x] `POST /api/admin/variables` crea/actualiza variable
- [x] `DELETE /api/admin/variables/{key}` elimina → 204
- [x] `DELETE /api/admin/variables/{key}` inexistente → 404

## Backend — Stats

- [x] `GET /api/admin/stats` retorna `AdminStatsRead`
- [x] Stats incluyen personas, donaciones, diezmos, ofrendas

## Backend — Personas

- [x] `GET /api/admin/personas` filtra por sede del admin
- [x] No retorna personas de otras sedes

## Backend — Auditoría

- [x] `GET /api/admin/audit?limit=100` retorna lista
- [x] Cada mutación genera entrada de audit

## Backend — Comentarios

- [x] `GET /api/admin/comments` retorna `List[AdminCommentRead]`
- [x] `DELETE /api/admin/comments/{id}` soft delete → 200
- [x] `DELETE /api/admin/comments/{id}` inexistente → 404

## Backend — Hitos espirituales

- [x] `GET /api/admin/milestones` retorna `List[AdminMilestoneRead]`
- [x] `POST /api/admin/milestones/award` otorga badge → 200
- [x] `POST /api/admin/milestones/award` badge inexistente → 404

## Backend — Categorías de donación

- [x] `GET /api/admin/donation-categories` retorna `List[AdminDonationCategoryRead]`
- [x] `POST /api/admin/donation-categories` crea → 201
- [x] `POST /api/admin/donation-categories` nombre vacío → 400
- [x] `PATCH /api/admin/donation-categories/{id}` actualiza → `AdminDonationCategoryRead`
- [x] `PATCH /api/admin/donation-categories/{id}` inexistente → 404
- [x] `DELETE /api/admin/donation-categories/{id}` elimina → 204
- [x] `DELETE /api/admin/donation-categories/{id}` inexistente → 404

## Backend — Automatizaciones

- [x] `GET /api/admin/automations` retorna `List[AutomationRuleRead]`
- [x] `POST /api/admin/automations` crea regla → 200
- [x] `PATCH /api/admin/automations/{id}` actualiza → `AutomationRuleRead`
- [x] `PATCH /api/admin/automations/{id}` inexistente → 404
- [x] `DELETE /api/admin/automations/{id}` soft delete → 200
- [x] `DELETE /api/admin/automations/{id}` inexistente → 404

## Backend — Roles modulares

- [x] `GET /api/admin/user-module-roles` retorna `List[AdminModuleRoleRead]`
- [x] `POST /api/admin/user-module-roles` asigna rol → 200
- [x] `POST /api/admin/user-module-roles` UUID inválido → 400
- [x] `DELETE /api/admin/user-module-roles/{id}` soft remove → 204
- [x] `DELETE /api/admin/user-module-roles/{id}` inexistente → 404

## Backend — Usuarios con roles

- [x] `GET /api/admin/users-with-roles` retorna `List[AdminUserWithRolesRead]`

## Backend — Provisionamiento

- [x] `POST /api/admin/provision-accounts` crea cuentas → 200
- [x] Respuesta incluye created, skipped, truncated, accounts

## Multi-tenant

- [x] Admin de sede A no ve personas de sede B
- [x] Global admin ve todas las sedes
- [x] User listing filtra por sede (excepto global admin)
- [x] Module role removal verifica sede

## Arquitectura

- [x] 0 queries SQLAlchemy inline en api/admin.py
- [x] Todos los endpoints tienen `response_model` definido
- [x] Todas las respuestas usan schemas de `schemas/admin.py`
- [x] CRUD layer centralizado en `crud/admin.py`
- [x] Roles consolidados (un solo sistema canónico)
- [x] Raw SQL eliminado de provision
- [x] Tests compilan sin errores

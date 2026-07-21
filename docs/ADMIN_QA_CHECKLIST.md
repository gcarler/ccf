# QA Checklist — Módulo Administración

**Fecha:** 2026-07-21 (refactorización completa)

---

## Backend — Roles (consolidados)

- [ ] `GET /api/admin/roles` retorna lista con `AdminRoleRead` + `users_count`
- [ ] `POST /api/admin/roles` crea rol con nombre único → 201
- [ ] `POST /api/admin/roles` nombre duplicado → 409
- [ ] `POST /api/admin/roles` nombre vacío → 400
- [ ] `PATCH /api/admin/roles/{id}` actualiza permisos → `AdminRoleRead`
- [ ] `PATCH /api/admin/roles/{id}` inexistente → 404
- [ ] `DELETE /api/admin/roles/{id}` sin usuarios → 204
- [ ] `DELETE /api/admin/roles/{id}` con usuarios → 409
- [ ] `POST /api/admin/roles` con `permissions` como lista → funciona

## Backend — Usuarios

- [ ] `GET /api/admin/users` retorna `List[AdminUserRead]`
- [ ] `GET /api/admin/users/{id}` retorna `AdminUserRead`
- [ ] `GET /api/admin/users/{id}` UUID inválido → 400
- [ ] `GET /api/admin/users/{id}` inexistente → 404
- [ ] `POST /api/admin/users` crea usuario + persona → 201
- [ ] `POST /api/admin/users` duplicado → 409
- [ ] `PATCH /api/admin/users/{id}` actualiza campos → `AdminUserRead`
- [ ] `PATCH /api/admin/users/{id}` inexistente → 404
- [ ] `DELETE /api/admin/users/{id}` desactiva → 204
- [ ] `DELETE /api/admin/users/{id}` inexistente → 404
- [ ] `PATCH /api/admin/users/{id}/role` asigna rol → 200
- [ ] `PATCH /api/admin/users/{id}/role` sin role_id → 400

## Backend — Permisos de usuario

- [ ] `GET /api/admin/users/{id}/permissions` retorna `AdminUserPermissionsRead`
- [ ] `GET /api/admin/users/{id}/permissions` inexistente → 404
- [ ] `PUT /api/admin/users/{id}/permissions` con módulo válido → 200
- [ ] `PUT /api/admin/users/{id}/permissions` módulo inválido → 400
- [ ] `PUT /api/admin/users/{id}/permissions` nivel inválido → 400

## Backend — Ubicaciones

- [ ] `GET /api/admin/locations` retorna `List[AdminLocationRead]`
- [ ] `POST /api/admin/locations` crea ubicación → 201
- [ ] `POST /api/admin/locations` nombre vacío → 400
- [ ] `PATCH /api/admin/locations/{id}` actualiza → `AdminLocationRead`
- [ ] `PATCH /api/admin/locations/{id}` inexistente → 404
- [ ] `DELETE /api/admin/locations/{id}` elimina → 204
- [ ] `DELETE /api/admin/locations/{id}` inexistente → 404

## Backend — Canales sociales

- [ ] `GET /api/admin/socials` retorna `List[AdminSocialRead]`
- [ ] `POST /api/admin/socials` crea canal → 201
- [ ] `PATCH /api/admin/socials/{id}` actualiza → `AdminSocialRead`
- [ ] `PATCH /api/admin/socials/{id}` inexistente → 404
- [ ] `DELETE /api/admin/socials/{id}` elimina → 204
- [ ] `DELETE /api/admin/socials/{id}` inexistente → 404

## Backend — Variables de sistema

- [ ] `GET /api/admin/variables` retorna dict key→value
- [ ] `POST /api/admin/variables` crea/actualiza variable
- [ ] `DELETE /api/admin/variables/{key}` elimina → 204
- [ ] `DELETE /api/admin/variables/{key}` inexistente → 404

## Backend — Stats

- [ ] `GET /api/admin/stats` retorna `AdminStatsRead`
- [ ] Stats incluyen personas, donaciones, diezmos, ofrendas

## Backend — Personas

- [ ] `GET /api/admin/personas` filtra por sede del admin
- [ ] No retorna personas de otras sedes

## Backend — Auditoría

- [ ] `GET /api/admin/audit?limit=100` retorna lista
- [ ] Cada mutación genera entrada de audit

## Backend — Comentarios

- [ ] `GET /api/admin/comments` retorna `List[AdminCommentRead]`
- [ ] `DELETE /api/admin/comments/{id}` soft delete → 200
- [ ] `DELETE /api/admin/comments/{id}` inexistente → 404

## Backend — Hitos espirituales

- [ ] `GET /api/admin/milestones` retorna `List[AdminMilestoneRead]`
- [ ] `POST /api/admin/milestones/award` otorga badge → 200
- [ ] `POST /api/admin/milestones/award` badge inexistente → 404

## Backend — Categorías de donación

- [ ] `GET /api/admin/donation-categories` retorna `List[AdminDonationCategoryRead]`
- [ ] `POST /api/admin/donation-categories` crea → 201
- [ ] `POST /api/admin/donation-categories` nombre vacío → 400
- [ ] `PATCH /api/admin/donation-categories/{id}` actualiza → `AdminDonationCategoryRead`
- [ ] `PATCH /api/admin/donation-categories/{id}` inexistente → 404
- [ ] `DELETE /api/admin/donation-categories/{id}` elimina → 204
- [ ] `DELETE /api/admin/donation-categories/{id}` inexistente → 404

## Backend — Automatizaciones

- [ ] `GET /api/admin/automations` retorna `List[AutomationRuleRead]`
- [ ] `POST /api/admin/automations` crea regla → 200
- [ ] `PATCH /api/admin/automations/{id}` actualiza → `AutomationRuleRead`
- [ ] `PATCH /api/admin/automations/{id}` inexistente → 404
- [ ] `DELETE /api/admin/automations/{id}` soft delete → 200
- [ ] `DELETE /api/admin/automations/{id}` inexistente → 404

## Backend — Roles modulares

- [ ] `GET /api/admin/user-module-roles` retorna `List[AdminModuleRoleRead]`
- [ ] `POST /api/admin/user-module-roles` asigna rol → 200
- [ ] `POST /api/admin/user-module-roles` UUID inválido → 400
- [ ] `DELETE /api/admin/user-module-roles/{id}` soft remove → 204
- [ ] `DELETE /api/admin/user-module-roles/{id}` inexistente → 404

## Backend — Usuarios con roles

- [ ] `GET /api/admin/users-with-roles` retorna `List[AdminUserWithRolesRead]`

## Backend — Provisionamiento

- [ ] `POST /api/admin/provision-accounts` crea cuentas → 200
- [ ] Respuesta incluye created, skipped, truncated, accounts

## Multi-tenant

- [ ] Admin de sede A no ve personas de sede B
- [ ] Global admin ve todas las sedes
- [ ] User listing filtra por sede (excepto global admin)
- [ ] Module role removal verifica sede

## Arquitectura

- [ ] 0 queries SQLAlchemy inline en api/admin.py
- [ ] Todos los endpoints tienen `response_model` definido
- [ ] Todas las respuestas usan schemas de `schemas/admin.py`
- [ ] CRUD layer centralizado en `crud/admin.py`
- [ ] Roles consolidados (un solo sistema canónico)
- [ ] Raw SQL eliminado de provision
- [ ] Tests compilan sin errores

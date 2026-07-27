# Changelog

## v1.0.1-crm (2026-07-27)

### Fixes
- **fix(crm):** corrige `AttributeError: module 'backend.models' has no attribute 'persona_familias'` en `backend/api/crm/pastoral.py` — reemplaza join con tabla de asociación inexistente por join directo `Persona.family_id -> Family.id`.
- **fix(crm):** corrige deduplicación de personas cuando `sede_id=None` — cambia filtro `Persona.sede_id.is_(None)` a `true()` para que busque globalmente.
- **fix(tests):** corrige endpoint obsoleto `/api/admin/auth-role-definitions` a canónico `/api/admin/roles` en 5 test suites.
- **fix(tests):** agrega autenticación en `test_crm_automations_challenger.py` vía fixture `client_auth_for_automations`.
- **fix(tests):** corrige `alembic upgrade head` → `upgrade 20260710_0002` en tests de migración para evitar dependencias rotas.
- **fix(tests):** agrega `seed_admin` + `auth_headers` a tests adversariales y de stress que fallaban con 401.
- **fix(tests):** cambia expectativa de 403 → 404 en cross-sede template access/deletion, alineado con la convención de existencia-leak.
- **fix(docs):** actualiza `docs/MODULO_ADMIN.md` — reemplaza sección obsoleta de `/auth-role-definitions` por aviso de consolidación.
- **fix(docs):** actualiza `tests/test_mass_get_coverage.py` — cambia URL obsoleta a `/api/admin/roles`.

### Quality
- **Suite CRM completa:** 1006 tests passed, 0 failures.
- **Referencias `auth-role-definitions` eliminadas:** tests (5/5), docs (2/2), comentarios como históricos.

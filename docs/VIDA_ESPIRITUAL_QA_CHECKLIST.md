# QA Checklist — Módulo Vida Espiritual y Discipulado

**Fecha de Certificación:** 2026-09-06  
**Módulo:** Vida Espiritual y Discipulado (`backend/api/spiritual_life.py`, `frontend/src/app/plataforma/spiritual-life`)  
**Veredicto:** 100/100 (A+) — CERTIFICADO ([`docs/AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md`](./AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md))

---

## Backend

### Smoke y CRUD Completo
- [x] `GET /api/spiritual-life/milestones` retorna 200 con lista de hitos filtrados por sede
- [x] `POST /api/spiritual-life/milestones` crea un hito (rol con `spiritual_life:manage`)
- [x] `GET /api/spiritual-life/milestones/{persona_id}` retorna lista de hitos de la persona
- [x] `GET /api/spiritual-life/milestone/{id}` retorna detalle individual de hito
- [x] `PATCH /api/spiritual-life/milestone/{id}` actualiza hito (`spiritual_life:edit`)
- [x] `DELETE /api/spiritual-life/milestone/{id}` elimina hito lógicamente vía soft delete (`deleted_at`)

### Permisos RBAC Canónicos
- [x] Editor no puede crear hitos (HTTP 403 en POST)
- [x] Lector puede leer pero no crear ni editar (HTTP 403 en POST, PATCH, DELETE)
- [x] Gestor y Admin pueden crear, leer, actualizar y eliminar
- [x] Validación de retrocompatibilidad y coherencia en `kernel_rbac.py` y `permissions.py`

### Multi-Tenant y Aislamiento (Axioma 3)
- [x] Hitos creados en Sede A son invisibles para Sede B
- [x] Consulta de hito de otra sede retorna HTTP 404 neutro (BOLA safe)
- [x] Actualización de hito de otra sede retorna HTTP 404 neutro
- [x] Eliminación de hito de otra sede retorna HTTP 404 neutro
- [x] Creación de hito para persona de otra sede retorna HTTP 404 neutro

### Validaciones e Invariantes
- [x] Tipo de hito inválido retorna HTTP 422 (validación Pydantic regex)
- [x] Catálogo canónico estricto: `Decision_Fe`, `Bautismo_Aguas`, `Bautismo_Espiritu`, `Persona_Oficial`, `Liderazgo`
- [x] 0 llamadas destructivas a `db.delete(` en todo el módulo
- [x] 0 marcas de tiempo naive (`datetime.utcnow()`), uso estricto de timezone UTC

---

## Frontend

- [x] Página `/plataforma/spiritual-life` carga sin errores e interactúa con `apiFetch`
- [x] **Ruta de Discipulado (`DISCIPULADO_STEPS`)**: 100% conectada a datos reales, calculando dinámicamente el progreso
- [x] Componente `SpiritualTimelinePanel` soporta claves UUID (`id`) y `milestone_id`
- [x] Timeline de hitos espirituales se renderiza correctamente con `cache: 'no-store'` y `AbortController`
- [x] Certificados vinculados y descargables desde `/academy/me/certificates`
- [x] Compilación TypeScript estricta: `npx tsc --noEmit` con 0 errores
- [x] Linter estricto: ESLint con 0 warnings y 0 errores
- [x] 0 clases Tailwind prohibidas (p. ej. `bg-red-50`)
- [x] 0 modales prohibidos (diseño modular con Drawer/Shell)

---

## Tests Automatizados

- [x] `tests/test_spiritual_life_api.py` pasa 10/10
- [x] `tests/test_spiritual_life_extended.py` pasa 15/15
- [x] `tests/test_spiritual_life_gap.py` pasa 12/12
- [x] `tests/test_admin_milestones_uuid.py` pasa 4/4
- [x] **Total suite canónica:** 41/41 tests aprobados (100% pass rate)
- [x] Cobertura de backend: `spiritual_life.py` 91%, `crud/crm_/milestones.py` 95%, schemas 100%
- [x] Suite de calidad frontend `workspaceAccess.test.ts`: 51/51 tests aprobados

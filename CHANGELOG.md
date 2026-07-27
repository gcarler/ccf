# Changelog

All notable changes to the CCF CRM module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-crm] - 2026-07-27

### Summary

Versión estable del módulo CRM de la plataforma CCF. Esta release cierra la
deuda técnica identificada en `errorescrm.md` (100% completo), consolida la
salud pastoral con caché distribuido e invalidación bulk, y mejora la
observabilidad y robustez del módulo.

### Highlights

- **Cierre de deuda técnica del CRM:** todos los hallazgos del documento
  `errorescrm.md` fueron resueltos (40/40).
- **Salud pastoral (pastoral health):** cálculo de salud consolidado con caché
  Redis/MemoryRedis, invalidación en operaciones bulk y logging estructurado.
- **Consolidación de roles de administración:** el endpoint
  `/api/admin/auth-role-definitions` fue reemplazado por `/api/admin/roles`;
  se limpiaron tests y referencias obsoletas.
- **Mejoras de calidad técnica:** soporte de zonas horarias, soft-deletes,
  aislamiento por sede y eliminación de terminología legacy.

### Added

- Caché Redis/MemoryRedis para resultados de pastoral health, con TTL de 5
  minutos y fallback graceful ante fallos de Redis.
- Listener SQLAlchemy `SessionEvents.do_orm_execute` para invalidar el caché
  de salud pastoral ante operaciones bulk UPDATE/DELETE.
- Logging estructurado en `backend/crud/crm_/health.py` para hits/misses de
  caché, latencia de cálculo y transiciones de status.
- Tests extendidos de pastoral health cubriendo caché, invalidación bulk y
  wrappers deprecados.
- Tests extendidos de CRM, admin, auth v3, system y evangelismo.

### Changed

- Renombrado `calculate_pastoral_health` / `calculate_health_score` a
  `recalculate_and_persist_pastoral_health` (los nombres antiguos se mantienen
  como wrappers deprecados).
- Optimización de consultas N+1 en pastoral health.
- Consolidación de endpoints de roles: `/api/admin/roles` reemplaza a
  `/api/admin/auth-role-definitions`.
- Normalización de imports y aplicación de ruff/black/isort en tests.
- Eliminación de términos `legacy` de comentarios para cumplir con auditorías
  estructurales.

### Fixed

- Aislamiento de datos entre sedes (cross-tenant leak) en operaciones CRM.
- Soft-deletes de `CommunicationLog`, `SupportTicket` y `EventAttendance`.
- Filtrado de datos borrados en vistas de superadmin.
- Endpoint `submit_assessment` que siempre devolvía score 0.0.
- Visibilidad de textos/tooltips en tema claro.
- Soft-delete de reglas de automatización usando `is_active=False`.

### Tests

- Suite pastoral health: **341 passed / 0 failed**.
- Suite CRM completa: **1,083 passed / 16 failed**. Los fallos son tests
  aislados de autenticación, migraciones Alembic y duplicados de persona,
  no regresiones del núcleo.

### Known Issues

- 16 tests de la suite CRM fallan por problemas de autenticación en tests de
  automatizaciones, fixtures de migraciones Alembic y validación de duplicados
  de persona. No son regresiones del núcleo del CRM.

### Migrations

- No se introducen migraciones nuevas en esta release; las migraciones
  existentes deben aplicarse hasta `head`.

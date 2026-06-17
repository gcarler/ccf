# Agentes Operativos CCF

**Fecha:** 2026-06-15  
**Propósito:** Definir la capa operativa para agentes que trabajan sobre la plataforma sin romper UI, backend ni arquitectura.

La documentación existente ya cubre reglas duras y contratos:

- `REGLAS.md`
- `docs/PROTOCOLO_CAMBIOS_SEGUROS_CCF.md`
- `docs/ESTANDARES_DESARROLLO.md`
- `AGENTS_FRONTEND.md`

Lo que faltaba era una guía breve de uso por dominio. Esta capa divide el trabajo en cuatro skills:

1. `ccf-ui-guard` para frontend, vistas, temas, CMS, drawers y rutas públicas.
2. `ccf-backend-guard` para FastAPI, SQLAlchemy, schemas, CRUD, servicios y migraciones.
3. `ccf-cms-guard` para CMS, recursos, themes, page builder y render público.
4. `ccf-architecture-guard` para decidir alcance, orden de cambio, reversibilidad y validación.

## Regla de uso

- Usar un solo skill por vez cuando el cambio tenga un dueño claro.
- Usar `ccf-architecture-guard` primero cuando el trabajo cruce capas o haya duda de alcance.
- No mezclar frontend, backend y migraciones en el mismo microcambio salvo que el cambio sea inseparable.

## Regla de seguridad

- Inspeccionar el estado real antes de editar.
- Corregir solo lo necesario.
- Validar el cambio en el nivel más pequeño posible.
- Documentar cualquier deuda o compatibilidad que se conserve.

## Orden de autoridad

1. `docs/PROTOCOLO_CAMBIOS_SEGUROS_CCF.md`
2. `REGLAS.md`
3. `AGENTS_FRONTEND.md`
4. `docs/ESTANDARES_DESARROLLO.md`
5. `docs/AGENTES_OPERATIVOS_CCF.md`

Este documento no reemplaza las reglas duras. Solo las convierte en un flujo operativo simple para agentes.

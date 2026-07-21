# Estado del Módulo Tables

**Actualizado:** 2026-07-19
**Montaje:** `backend/app.py:90` — `(tables.router, "/api", ["tables"])`
**Estado de cobertura:** Fase 3 — sólo ESTADO + auditoría (`AUDITORIA_FORENSE_MODULOS_MENORES.md`)

---

## Resumen

Módulo de **persistencia de esquemas de tabla y vistas guardadas** ("Saved Views"). Permite que cada persona guarde configuraciones reutilizables (columnas, filtros, agrupación, formato condicional) sobre listados de la plataforma y las recupere más tarde. Es una utilidad transversal: no renderiza tablas por sí mismo, sólo guarda y restaura la configuración que el frontend aplica sobre vistas ya existentes de otros módulos (CRM, Projects, Academy, etc.).

---

## Métricas

| Métrica | Valor |
|---|---|
| Router | `backend/api/tables.py` (143 líneas) |
| Modelo | `backend.models_shared.SavedView` |
| Frontend | Sin página dedicada (consumido transversalmente) |
| Tests | Sin archivo dedicado (cobertura compartida con Support) |

---

## Backend

> Prefijo del router: `/api/tables`. Auth: `require_active_user`.

| Método | Ruta | Body | Respuesta | Propósito |
|---|---|---|---|---|
| `GET` | `/api/tables/schemas` | — | `[{id, name, schema, filters, grouping, created_at}]` | Listar vistas guardadas de la persona actual |
| `POST` | `/api/tables/schemas` | `{name, schema, filters, grouping, conditional_format}` | `{id, name}` (201) | Guardar una nueva vista |
| `PATCH` | `/api/tables/schemas/{view_id}` | campos parciales (`name`, `schema`, `filters`, `grouping`) | `{id, name}` | Actualizar una vista existente |
| `DELETE` | `/api/tables/schemas/{view_id}` | — | `{ok: true}` | Soft-delete de una vista (`deleted_at = utcnow()`) |

**Notas del contrato:**

- `DELETE` es **soft-delete**, no borrado físico.
- `GET` filtra también por `deleted_at IS NULL`.
- `PATCH` y `DELETE` verifican que la vista pertenezca a la `persona.id` del actor — si no, `404`.
- `conditional_format` se persiste en `POST` pero no se expone en `GET` ni se puede actualizar en `PATCH` ⇒ asimetría de contrato.
- `view_id` viaja como `str` en la URL; no se valida como UUID.

---

## Multi-tenant

| Dimensión | Estado |
|---|---|
| Scope (`sede_id`) | No presente — el módulo no usa `get_user_sede_id` (0 referencias) |
| Aislamiento real | Por-persona vía `resolve_persona_id_for_user` + filtro `SavedView.persona_id == persona.id` |
| Validación cruzada | `PATCH`/`DELETE` chequean pertenencia antes de mutar (404 si no pertenece) |
| Defensa en profundidad | **Ninguna** — no hay segunda capa por sede |

**Implicación operativa:** si en producción se observa fuga entre personas, no es porque el módulo no filtre — es porque el resolver de persona upstream está retornando el identificador equivocado.

---

## Hallazgos

| ID | Severidad | Hallazgo |
|---|---|---|
| TBL-C1 | Crítico | 6/6 artefactos documentales faltan — sólo cubierto por la auditoría agregada `AUDITORIA_FORENSE_MODULOS_MENORES.md` |
| TBL-T1 | Alto | Sin archivo de tests dedicado — cobertura compartida con Support (regresiones silenciosas posibles) |
| TBL-T2 | Alto | Payloads de entrada/salida son `Dict[str, Any]` sin validación Pydantic — el contrato sólo vive en el frontend |
| TBL-S1 | Alto | **Fuga potencial en GET cuando `_resolve_persona()` retorna `None`**: la query ejecuta `SavedView.persona_id == None`, que SQLAlchemy traduce a `IS NULL`. Cualquier usuario sin persona resuelta vería todas las `SavedView` huérfanas con `persona_id NULL`. `POST`/`PATCH`/`DELETE` sí bloquean este caso con 404, pero `GET` no |
| TBL-T3 | Medio | `conditional_format_json` se persiste en `POST` pero ni se devuelve en `GET` ni se permite en `PATCH` — asimetría |
| TBL-T4 | Medio | Aislamiento sólo por-persona, sin segunda capa (`sede_id`) |
| TBL-T5 | Medio | `view_id` en `PATCH`/`DELETE` no se valida como UUID — input crudo |
| TBL-C2 | Bajo | Clase local `TableSchema` en el router nunca se usa como `response_model` — código confuso |
| TBL-F1 | Bajo | Sin frontend dedicado — consumido transversalmente |

---

## Modelo de datos

El módulo no introduce un modelo propio. Reusa `SavedView` (en `backend/models_shared.py`):

| Columna | Tipo | Notas |
|---|---|---|
| `id` | UUID (PK) | Identificador de la vista |
| `persona_id` | UUID (FK → `personas.id`) | Scope multi-tenant per-persona |
| `name` | str | Nombre legible |
| `schema_json` | JSON | Definición de columnas |
| `filters_json` | JSON | Filtros aplicados |
| `grouping_json` | JSON | Agrupaciones aplicadas |
| `conditional_format_json` | JSON | Reglas de formato (sólo escritura en POST) |
| `created_at` | timestamp | — |
| `deleted_at` | timestamp (nullable) | Marker de soft-delete |

⚠️ No existe `sede_id`. Dos pastores en la misma sede **no comparten** vistas (intencional).

---

## Artefactos del módulo

Cobertura general: ver `docs/MATRIZ_COBERTURA_MODULAR_CCF.md` (posición 1/6 artefactos).

Estado local de los pendientes documentales:

- `PEND-TBL-001` Crear `docs/TABLES_API_CONTRACTS.md`
- `PEND-TBL-002` Crear `docs/TABLES_QA_CHECKLIST.md`
- `PEND-TBL-003` Crear `docs/TABLES_RBAC_MATRIX.md`
- `PEND-TBL-004` Crear `scripts/test_tables_quality.py`
- `PEND-TBL-005` Crear `tests/test_tables_api.py`
- `PEND-TBL-006` Definir schemas Pydantic en `backend/schemas/tables.py`
- `PEND-TBL-007` Resolver asimetría de `conditional_format`
- `PEND-TBL-008` Tipar `view_id` como `UUID`
- `PEND-TBL-009` Eliminar `TableSchema` local o conectarla como `response_model`
- `PEND-TBL-010` Mitigar `TBL-S1` (decidir entre forzar persona o filtrar `IS NULL` explícitamente)
- `PARCIAL-TBL-001` Smoke script propio — actualmente heredado de Fase 3

---

## Riesgos abiertos (resumen)

1. **Regresión silenciosa**: sin tests dedicados, un cambio en `models_shared.SavedView` puede romper el módulo sin que CI lo detecte.
2. **Fuga por NULL persona_id**: ver `TBL-S1` arriba — único endpoint sin guardia cuando `_resolve_persona` retorna `None`.
3. **Confusión de scope**: cualquier futuro lector podría asumir multi-tenant por `sede_id` y romper el aislamiento buscando mecanismos que no existen.

---

## Documentación relacionada

- `docs/ESTADO_MODULOS_MENORES.md` — entrada agrupada donde Tables vivía antes de este handover
- `docs/AUDITORIA_FORENSE_MODULOS_MENORES.md` — hallazgos base (TBL-C1)
- `docs/MATRIZ_COBERTURA_MODULAR_CCF.md` — cobertura 6/6 del módulo
- `backend/models_shared.py` — definición de `SavedView`
- `backend/app.py:90` — montaje del router

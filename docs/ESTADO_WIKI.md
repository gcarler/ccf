# Estado del Módulo Wiki

**Actualizado:** 2026-07-18

---

## Resumen

Módulo de wiki/documentación colaborativa. Permite páginas con versionado, categorías, etiquetas y búsqueda, con aislamiento multi-tenant por sede.

| Métrica | Valor |
|---|---|
| Router | `backend/api/wiki.py` (11 endpoints) |
| CRUD | `backend/crud/wiki.py` |
| Modelos | `backend/models_wiki.py` |
| Schemas | `backend/schemas/wiki.py` |
| Frontend | `frontend/src/app/plataforma/wiki/` (docs, page) |
| Tests | 30 — cobertura 100% de api/wiki.py y crud/wiki.py |
| Smoke script | `scripts/test_wiki_quality.py` |

---

## Contrato canónico

- Páginas identificadas por `page_key` (string unique por sede)
- `sede_id` para aislamiento multi-tenant
- `author_id` referenciando `personas.id`
- Soft delete via `deleted_at`
- Versionado automático con `WikiPageVersion`
- Categorías y tags para organización

---

## Backend

| Aspecto | Detalle |
|---|---|
| Router | `backend/api/wiki.py` |
| CRUD | `backend/crud/wiki.py` |
| Schemas | `backend/schemas/wiki.py` |
| Modelos | `backend/models_wiki.py` |

### Endpoints (11)

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/wiki/pages` | Listar páginas (con búsqueda, categoría, paginación) |
| GET | `/wiki/pages/count` | Contar páginas |
| GET | `/wiki/pages/{page_key}` | Obtener página (o virtual si no existe) |
| GET | `/wiki/pages/{page_key}/versions` | Historial de versiones |
| POST | `/wiki/pages/{page_key}` | Crear página |
| PATCH | `/wiki/pages/{page_key}` | Actualizar página (incrementa versión) |
| DELETE | `/wiki/pages/{page_key}` | Soft delete |
| GET | `/wiki/categories` | Listar categorías |

---

## Frontend

| Ruta | Propósito |
|---|---|
| `/plataforma/wiki` | Listado/docs |
| `/plataforma/wiki/page` | Editor/visor de página |

---

## Tests

| Métrica | Valor |
|---|---|
| Archivo | `tests/test_wiki.py` |
| Tests | 30 |
| Cobertura api/wiki.py | 100% |
| Cobertura crud/wiki.py | 100% |
| Última ejecución | 30/30 passed |

---

## Documentación relacionada

- `docs/wiki/MODULO_WIKI.md` — Documentación del módulo
- `docs/wiki/PLAN_DE_TRABAJO_WIKI.md` — Plan de trabajo histórico
- `docs/WIKI_API_CONTRACTS.md` — Contratos de API
- `docs/WIKI_QA_CHECKLIST.md` — Checklist de calidad
- `docs/WIKI_RBAC_MATRIX.md` — Matriz de permisos
- `scripts/test_wiki_quality.py` — Smoke script canónico

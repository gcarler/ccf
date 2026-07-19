# Estado del Módulo Graph

**Actualizado:** 2026-07-19

---

## Resumen

Módulo de grafo de conocimiento. Genera visualizaciones de relaciones entre personas, cursos, proyectos y recursos de la plataforma.

| Métrica | Valor |
|---|---|
| Router | `backend/api/graph.py` |
| Frontend | `frontend/src/app/plataforma/graph/` |
| Tests | `tests/test_graph_api.py` (4 xfailed, 1 xpassed) |
| Smoke | `scripts/test_fase3_quality.py` |

---

## Backend

| Endpoint | Propósito |
|---|---|
| `GET /api/graph/data` | Datos del grafo de conocimiento |

---

## Multi-tenant

✅ 3 referencias a scope

## Documentación relacionada

- `docs/ESTADO_MODULOS_MENORES.md`
- `docs/AUDITORIA_FORENSE_MODULOS_MENORES.md`

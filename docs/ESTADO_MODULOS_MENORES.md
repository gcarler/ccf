# Estado de Módulos Menores

**Actualizado:** 2026-07-18
**Cubre:** Graph, Analytics, Enterprise CMS, Governance, Tables, Youtube

---

## Graph

| Métrica | Valor |
|---|---|
| Router | `backend/api/graph.py` |
| Frontend | `frontend/src/app/plataforma/graph/` |
| Tests | `tests/test_graph_api.py` (4 xfailed, 1 xpassed) |
| Multi-tenant | ✅ 3 referencias |

## Analytics

| Métrica | Valor |
|---|---|
| Router | `backend/api/analytics.py` |
| Tests | `tests/test_analytics_pipeline.py`, `test_analytics_pastoral_helpers.py` |
| Multi-tenant | ✅ 3 referencias |

## Enterprise CMS

| Métrica | Valor |
|---|---|
| Router | `backend/api/enterprise_cms.py` |
| Tests | `tests/test_enterprise_cms.py` (51 passed) |
| Multi-tenant | ⚠️ 0 referencias |
| Smoke | `scripts/test_fase3_quality.py` |

## Governance

| Métrica | Valor |
|---|---|
| Router | `backend/api/governance.py` |
| CRUD | `backend/crud/governance.py` |
| Modelos | `backend/models_governance.py` |
| Schemas | `backend/schemas/governance.py` |
| Tests | Sin archivo dedicado |

## Tables

| Métrica | Valor |
|---|---|
| Router | `backend/api/tables.py` |
| Tests | Comparte con Support |

## Youtube

| Métrica | Valor |
|---|---|
| Router | `backend/api/youtube.py` |
| Tests | Sin archivo dedicado |

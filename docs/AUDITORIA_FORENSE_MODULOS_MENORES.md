# Auditoría Forense — Módulos menores (Graph, Analytics, Enterprise CMS, Governance, Tables, Youtube)

**Fecha:** 2026-07-18

---

## Graph

| Dimensión | Resultado |
|---|---|
| Router | `backend/api/graph.py` |
| Frontend | `frontend/src/app/plataforma/graph/` |
| Tests | `tests/test_graph_api.py` (4 xfailed, 1 xpassed) |
| Multi-tenant | 3 referencias ✅ |
| D1 — Artefactos | 0/6 |

**Hallazgo:** GPH-C1 — 6/6 artefactos faltan

---

## Analytics

| Dimensión | Resultado |
|---|---|
| Router | `backend/api/analytics.py` |
| Tests | `tests/test_analytics_pipeline.py`, `test_analytics_pastoral_helpers.py` |
| Multi-tenant | 3 referencias ✅ |
| D1 — Artefactos | 0/6 |

**Hallazgo:** ANL-C1 — 6/6 artefactos faltan

---

## Enterprise CMS

| Dimensión | Resultado |
|---|---|
| Router | `backend/api/enterprise_cms.py` |
| Tests | `tests/test_enterprise_cms.py` (51 passed) |
| Multi-tenant | 0 referencias |
| D1 — Artefactos | 0/6 |

**Hallazgo:** ECM-C1 — 6/6 artefactos faltan; ECM-M1 — sin multi-tenant

---

## Governance

| Dimensión | Resultado |
|---|---|
| Router | `backend/api/governance.py` |
| CRUD | `backend/crud/governance.py` |
| Modelos | `backend/models_governance.py` |
| Schemas | `backend/schemas/governance.py` |
| Tests | Sin archivo dedicado |
| D1 — Artefactos | 0/6 |

**Hallazgo:** GOV-C1 — 6/6 artefactos faltan

---

## Tables

| Dimensión | Resultado |
|---|---|
| Router | `backend/api/tables.py` |
| Tests | (comparte con support) |
| D1 — Artefactos | 0/6 |

**Hallazgo:** TBL-C1 — 6/6 artefactos faltan

---

## Youtube

| Dimensión | Resultado |
|---|---|
| Router | `backend/api/youtube.py` |
| Tests | Sin archivo dedicado |
| D1 — Artefactos | 0/6 |

**Hallazgo:** YTB-C1 — 6/6 artefactos faltan

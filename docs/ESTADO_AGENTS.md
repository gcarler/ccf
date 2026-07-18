# Estado del Módulo Agents

**Actualizado:** 2026-07-18

---

## Resumen

Módulo de agentes de IA. Gestiona tareas automatizadas, insights y operaciones de inteligencia artificial en la plataforma.

| Métrica | Valor |
|---|---|
| Router | `backend/api/agents.py` |
| CRUD | `backend/crud/agents.py` |
| Modelos | `backend/models_agents.py` |
| Schemas | `backend/schemas/agents.py` |
| Frontend | `frontend/src/app/plataforma/agents/` |
| Tests | `tests/test_agents.py` (2 passed) |
| Docs | `docs/AUDITORIA_FORENSE_AGENTS.md` |

---

## Backend

| Endpoint | Propósito |
|---|---|
| `GET /api/agents/tasks` | Listar tareas de agente |
| `GET /api/agents/insights` | Insights generados por IA |
| `GET /api/agents/kb/stats` | Estadísticas de base de conocimiento |

---

## Multi-tenant

✅ 4 referencias a scope

## Tests

| Métrica | Valor |
|---|---|
| Tests | 2/2 passed |
| Smoke | `scripts/test_fase3_quality.py` |

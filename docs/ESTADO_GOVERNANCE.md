# Estado del Módulo Governance

**Actualizado:** 2026-07-19

---

## Resumen

Módulo de gobernanza. Gestiona auditoría, logs de administración y cumplimiento normativo de la plataforma.

| Métrica | Valor |
|---|---|
| Router | `backend/api/governance.py` (11 líneas) |
| CRUD | `backend/crud/governance.py` |
| Modelos | `backend/models_governance.py` |
| Schemas | `backend/schemas/governance.py` |
| Tests | Sin archivo de cobertura dedicado |
| Cobertura | 100% (api/governance.py) |

---

## Backend

| Endpoint | Propósito |
|---|---|
| `GET /api/governance/audit-logs` | Listar logs de auditoría con filtros |

---

## Documentación relacionada

- `docs/AUDITORIA_FORENSE_MODULOS_MENORES.md`

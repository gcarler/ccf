# Estado del Módulo Analytics

**Actualizado:** 2026-07-19

---

## Resumen

Módulo de analítica y métricas de la plataforma. Proporciona endpoints para consultar datos agregados de pastoral, academia, proyectos y evangelismo.

| Métrica | Valor |
|---|---|
| Router | `backend/api/analytics.py` |
| Frontend | Sin página dedicada (datos consumidos por dashboards) |
| Tests | `tests/test_analytics_pipeline.py`, `tests/test_analytics_pastoral_helpers.py` |
| Docs | `docs/AUDITORIA_FORENSE_MODULOS_MENORES.md` |

---

## Backend

| Endpoint | Propósito |
|---|---|
| `GET /api/analytics/overview` | Vista general de métricas |
| `GET /api/analytics/pastoral` | Métricas pastorales |
| `GET /api/analytics/academy` | Métricas de academia |

---

## Multi-tenant

✅ 3 referencias a scope (get_user_sede_id)

## Hallazgos

| ID | Severidad | Hallazgo |
|---|---|---|
| ANL-C1 | Crítico | 6/6 artefactos documentales faltan (cubierto en `ESTADO_MODULOS_MENORES.md`) |

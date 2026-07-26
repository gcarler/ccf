# QA Checklist — Analytics

**Creado:** 2026-07-26

---

## 1. Preflight

```bash
cd /root/ccf
git status --short
python3 --version
```

## 2. Smoke canónico

```bash
cd /root/ccf
python3 -m pytest tests/test_analytics_api.py tests/test_analytics_coverage.py -q --no-cov --tb=short
```

## 3. Endpoints cubiertos

| Endpoint | Propósito | Auth |
|---|---|---|
| `GET /api/analytics/radar` | Métricas del Radar del Pastor | `require_pastor_or_admin` |
| `GET /api/analytics/dashboard-metrics` | Métricas del dashboard académico | `require_pastor_or_admin` |
| `GET /api/analytics/events/summary` | Resumen de eventos (totales, próximos, asistentes) | `require_pastor_or_admin` |

## 4. Validaciones

- [ ] Los 3 endpoints requieren autenticación
- [ ] Usuarios sin rol pastoral/admin reciben 403
- [ ] Multi-tenant: datos aislados por `sede_id`
- [ ] Respuestas siguen el contrato del schema (PastorRadarSchema, DashboardMetrics)
- [ ] Sin datos: devuelven 0/empty, no 500

## 5. Contratos

Los schemas de respuesta están definidos en:
- `backend/schemas/operational.py` → `PastorRadarSchema`
- `backend/schemas/academy.py` → `DashboardMetrics`
- `backend/api/analytics.py` → events/summary (dict inline)

Ver `docs/ANALYTICS_API_CONTRACTS.md` para el detalle de cada contrato.

## 6. Hallazgos Conocidos

| ID | Severidad | Hallazgo | Tracking |
|---|---|---|---|
| ANL-XF1 | Baja | `test_analytics_api` tiene 1 test con `@pytest.mark.xfail`. Evaluar si la condición que causaba el fallo ya fue corregida en iteraciones recientes. | Pendiente de re-evaluación — target: próxima iteración de calidad |

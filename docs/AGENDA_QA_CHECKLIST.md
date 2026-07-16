# QA Checklist — Agenda / Calendar

## 1. Antes de tocar codigo

- Leer `ESTADO_AGENDA.md`.
- Leer `AGENDA_RBAC_MATRIX.md` si el fallo involucra acceso, 401, 403 o visibilidad por rol.
- Leer `SYSTEM_CALENDAR_CONTRACT.md` si el cambio toca `/api/system/calendar`, `/plataforma/calendar` o `UniversalCalendarView`.
- Clasificar el fallo: `agenda CRUD`, `calendar UI`, `system/calendar`, `RBAC` o `plataforma`.
- Si el cambio afecta componentes de calendario reusables o auth, tratarlo como plataforma compartida.

## 2. Validacion backend minima

```bash
cd /root/ccf
./venv/bin/python scripts/test_agenda_quality.py
```

## 3. Validacion ampliada segun cambio

- si toca agregacion general: `tests/test_api_massive.py`
- si toca rutas confirmadas: `tests/test_fixed_routes.py`
- si toca schemas/modelos: `tests/test_permissions_and_more.py`

## 4. Checks manuales obligatorios

- `/plataforma/calendar` carga sin 401/404/500 inesperados.
- crear evento manual desde agenda funciona y luego aparece en agenda.
- editar evento mantiene serializacion y fechas correctas.
- crear participante cross-sede falla.
- crear reserva duplicada/conflictiva no rompe el flujo.
- el rol probado coincide con la matriz `spiritual_life:*` documentada.

## 5. No aprobar si pasa esto

- eventos de otra sede visibles en agenda autenticada
- respuestas con fechas no serializables
- UI de calendar depende de shape no documentado y rompe silenciosamente
- nuevo `fetch()` directo en lugar de `apiFetch`
- drift entre guard real de `agenda.py` y la matriz RBAC del modulo

## 6. Backlog QA

- `PEND-CALENDAR-EVENTS-CONTRACT-001` cerrada el 2026-07-16 con `docs/SYSTEM_CALENDAR_CONTRACT.md`
- `PEND-AGENDA-RBAC-001` cerrada el 2026-07-16 con `docs/AGENDA_RBAC_MATRIX.md`
- `PEND-AGENDA-SMOKE-001` cerrada el 2026-07-16 con `scripts/test_agenda_quality.py`
- `PEND-FRONTEND-E2E-AGENDA-001` cerrada el 2026-07-16 con `frontend/tests/e2e/agenda/smoke.spec.ts`
- `PEND-FRONTEND-E2E-AGENDA-DEEP-001` cerrada el 2026-07-16 con `frontend/tests/e2e/agenda/calendar-events.spec.ts`

## 7. Smoke frontend dedicado

```bash
cd /root/ccf/frontend
npm run test:e2e:agenda
npm run test:e2e:agenda:deep
```

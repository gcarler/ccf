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
- el rol probado coincide con la matriz `agenda:*` documentada.
- crear un evento con repeticion semanal genera ocurrencias visibles en `by-date-range` y en `/plataforma/calendar`, cada una navegable al owner route del evento.
- editar una serie sin tocar el campo repeticion la preserva; elegir "No se repite" sobre una serie activa la elimina; `recurrence_rule` invalida responde 422.
- editar una ocurrencia concreta desde el calendario (detalle con `?occurrence=`) la convierte en evento independiente y la fecha desaparece de la serie; "Toda la serie" vuelve a los valores del ancla.
- eliminar una ocurrencia concreta solo excluye esa fecha; el resto de la serie sigue visible en `by-date-range` y en calendar.

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
- `AUDITORIA-FORENSE-AGENDA-2026-09-05` cerrada el 2026-09-05 con `docs/AUDITORIA_FORENSE_AGENDA_2026-09-05.md` (47 tests backend OK, 0 hard deletes, 0 legacy/naive datetime, 0 bg-red-50, 0 modales banned, 100% apiFetch)
- `CERRADO-AGENDA-RBAC-001` cerrada el 2026-09-05 con la creación y desacople de la taxonomía `agenda:*` al 100/100 (A+)
- `AUDITORIA-FORENSE-AGENDA-2026-09-06` cerrada el 2026-09-06 con `docs/AUDITORIA_FORENSE_AGENDA_2026-09-06.md` (357 tests ejecutados y aprobados al 100%, VICTORY CONFIRMED por auditoría independiente)
- `PEND-AGENDA-RRULE-001` cerrada el 2026-09-07 con eventos recurrentes RFC 5545: `backend/services/agenda_recurrence.py`, expansión en `by-date-range` y agregador calendar, selector de repetición en `agenda/events` y `tests/test_agenda_recurrence.py` (14 tests)
- `PEND-AGENDA-RRULE-OCCURRENCE-001` cerrada el 2026-09-07 con la edición por ocurrencia (v2): `PUT`/`DELETE /agenda/events/{id}?occurrence_date=` con semántica RFC 5545 de excepciones, evento derivado con proveniencia `derived_from`, selector de alcance en el detalle (`?occurrence=`), href del agregador con `?occurrence=`, y suite ampliada a 22 tests

## 7. Smoke frontend dedicado

```bash
cd /root/ccf/frontend
npm run test:e2e:agenda
npm run test:e2e:agenda:deep
```

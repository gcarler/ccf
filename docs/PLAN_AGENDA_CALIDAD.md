# Plan de Calidad — Modulo de Agenda / Calendar CCF

> **Objetivo:** cerrar agenda y calendar como modulo operativo con ownership claro entre CRUD propietario y calendario agregado, evitando correcciones superficiales sobre vistas cruzadas.

## 1. Regla de trabajo

- No corregir `/plataforma/calendar` desde un modulo consumidor si el origen real vive en `agenda.py` o `system/calendar`.
- Cada cambio debe mapearse a un ID estable de `docs/ESTADO_AGENDA.md`.
- Si el cambio toca `UniversalCalendarView`, auth, `apiFetch` o `system/calendar`, tratarlo como plataforma compartida.
- No introducir taxonomia `agenda:*` parcial mientras el backend siga usando `spiritual_life:*`; eso requiere migracion planificada.
- Si se toca serializacion de eventos, validar agenda y calendar juntos.

## 2. Fase 0 — Diagnostico base

**ID:** `AGENDA-FASE0-DIAG`

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_AGENDA.md
grep -nE "PARCIAL-|PEND-" docs/ESTADO_AGENDA.md
./venv/bin/python scripts/test_agenda_quality.py
```

Validacion minima ampliada:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_api_massive.py \
  tests/test_api_comprehensive.py \
  tests/test_fixed_routes.py
```

Criterio de salida:

- El primer fallo real queda clasificado como `agenda CRUD`, `calendar aggregation`, `RBAC`, `serializacion`, `sede isolation` o `frontend state`.
- No se toca la UI antes de confirmar si el backend o el agregador ya estan rotos.

## 3. Fase 1 — CRUD de eventos

**IDs:** `PEND-AGENDA-SMOKE-001`, `PARCIAL-CALENDAR-AGGREGATION-001`

Orden:

1. Validar `GET /api/agenda/events`.
2. Validar `POST /api/agenda/events`.
3. Validar `GET/PUT/DELETE /api/agenda/events/{event_id}`.
4. Validar `GET /api/agenda/events/by-date-range` con rango correcto.
5. Confirmar que todo acceso autenticado queda tenant-scoped.

Criterio de salida:

- CRUD manual de eventos es estable.
- `404`, `409` y validaciones de fecha son consistentes.
- No se filtran eventos de otra sede.

## 4. Fase 2 — Participantes, recursos y reservas

**ID:** `AGENDA-RESOURCES-001`

Orden:

1. Validar CRUD de recursos.
2. Validar participantes por evento y persona de misma sede.
3. Validar reservas con conflictos de horario.
4. Confirmar `409` en colisiones y `404` en recursos/eventos inexistentes.

Criterio de salida:

- Participantes y reservas respetan `sede_id`.
- El flujo operativo no se rompe por conflictos previsibles.

## 5. Fase 3 — Calendar agregado

**ID:** `PEND-CALENDAR-EVENTS-CONTRACT-001`

Orden:

1. Validar `GET /api/system/calendar`.
2. Confirmar `view` soportadas y shape serializable.
3. Verificar `href`, `type`, `start`, `end`, `location`, `allDay`.
4. Confirmar que no reaparezcan aliases legacy.
5. Revisar consumo real de `/plataforma/calendar`.

Criterio de salida:

- El agregador queda estable por contrato, no por suposiciones visuales.
- Un fallo en calendar puede trazarse al owner correcto.

## 6. Fase 4 — Permisos y taxonomia heredada

**IDs:** `PEND-AGENDA-RBAC-001`, `PARCIAL-AGENDA-RBAC-001`

Orden:

1. Confirmar guards reales de lectura y mutacion.
2. Mantener sincronizadas docs y permisos mientras siga vigente `spiritual_life:*`.
3. Si se decide migrar a `agenda:*`, abrir trabajo estructural separado con rollout.

Criterio de salida:

- No hay drift entre `agenda.py` y `AGENDA_RBAC_MATRIX.md`.
- La deuda de taxonomia queda visible y controlada, no escondida.

## 7. Fase 5 — Smoke frontend dedicado

**ID:** `AGENDA-FASE5-FRONTEND`

Rutas minimas:

- `/plataforma/calendar`
- `/plataforma/agenda/events`

Smoke frontend dedicado:

```bash
cd /root/ccf/frontend
npm run test:e2e:agenda
```

Checks manuales obligatorios complementarios:

- consola limpia de `401`, `403`, `404`, `500`
- agenda lista eventos sin romper layout
- crear/editar evento mantiene fechas correctas
- calendar agregado carga sin shape roto

Cobertura automatizada vigente:

- `frontend/tests/e2e/agenda/smoke.spec.ts`
- `frontend/tests/e2e/agenda/calendar-events.spec.ts`
- `npm run test:e2e:agenda`
- `npm run test:e2e:agenda:deep`

Criterio de salida:

- Existe smoke frontend dedicado y el checklist manual queda como cobertura complementaria.

## 8. Fase 6 — QA final y release

**ID:** `AGENDA-FASE6-QA`

Comandos minimos:

```bash
cd /root/ccf
./venv/bin/python scripts/test_agenda_quality.py
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_api_massive.py \
  tests/test_api_comprehensive.py \
  tests/test_fixed_routes.py
```

Si se toca `system/calendar` o frontend reusable:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_structural_contracts.py
cd /root/ccf/frontend
npm run build
```

Criterio de salida:

- `docs/ESTADO_AGENDA.md` se actualiza si cambia backlog o estado.
- La correccion queda en la capa propietaria.
- No se aprueba un fix de agenda que rompa calendar compartido o viceversa.

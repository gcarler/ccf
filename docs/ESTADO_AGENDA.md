# Estado del Modulo Agenda / Calendar — CCF

> **TL;DR (una linea):** Agenda es el modulo operativo de eventos, participantes y reservas fisicas sobre `/api/agenda/*`, mientras `calendar` es la vista agregada de calendario que cruza agenda, proyectos, CRM y evangelismo.

**Proposito.** Handover canonico para trabajar agenda como modulo propio y `calendar` como superficie compartida, sin arreglar fallos de calendario desde proyectos o evangelismo si el origen real vive en `agenda.py`, `system/calendar` o en la serializacion de eventos.

**Regla de uso.**

- `agenda` es backend propietario de eventos manuales y recursos.
- `calendar` frontend agrega datos cross-modulo; si falla la agregacion, puede ser plataforma compartida.
- Si el cambio toca `system/calendar`, `UniversalCalendarView`, auth, permisos o `apiFetch`, tratarlo como plataforma compartida.

---

## 1. Leer primero (cualquier agente)

```bash
cat /root/ccf/docs/ESTADO_AGENDA.md
cat /root/ccf/docs/AGENDA_API_CONTRACTS.md
cat /root/ccf/docs/AGENDA_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_ARQUITECTURA_MODULAR_CCF.md
```

## 2. Verificar entorno

```bash
python3 --version && node --version
```

## 3. Recontar superficie vigente (por si drift)

```bash
wc -l /root/ccf/backend/api/agenda.py /root/ccf/backend/crud/agenda.py /root/ccf/backend/schemas/agenda.py /root/ccf/backend/models_agenda.py | tail -1
wc -l /root/ccf/frontend/src/app/plataforma/agenda/**/*.tsx /root/ccf/frontend/src/app/plataforma/agenda/*.tsx /root/ccf/frontend/src/app/plataforma/calendar/**/*.tsx /root/ccf/frontend/src/app/plataforma/calendar/*.tsx /root/ccf/frontend/src/components/calendar/*.tsx /root/ccf/frontend/src/components/ui/UniversalCalendarView.tsx 2>/dev/null | tail -1
```

Referencia observada el **2026-07-16**:

- Superficie frontend contada por archivos: **8**
- Superficie backend contada por archivos: **4**

## 4. Smoke test canonico

```bash
cd /root/ccf
./venv/bin/python scripts/test_agenda_quality.py
```

Smoke ampliado, si se toca agregacion cross-modulo:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_api_massive.py \
  tests/test_api_comprehensive.py \
  tests/test_fixed_routes.py
```

## 5. Ownership tecnico

| Area | Archivos | Responsabilidad |
|---|---|---|
| API agenda | `backend/api/agenda.py` | CRUD de eventos, participantes, recursos y reservas |
| CRUD agenda | `backend/crud/agenda.py` | filtros por sede y persistencia |
| Schemas agenda | `backend/schemas/agenda.py` | shape de request/response |
| UI agenda | `frontend/src/app/plataforma/agenda/**` | detalle/lista de eventos |
| UI calendar | `frontend/src/app/plataforma/calendar/**`, `frontend/src/components/calendar/**` | vista unificada de calendario |
| Vista reusable | `frontend/src/components/ui/UniversalCalendarView.tsx` | render calendar reusable |

## 6. Contratos vigentes

- Prefijo backend propietario: `/api/agenda/*`
- Permisos actuales: `spiritual_life:read` para lectura y `spiritual_life:edit` para mutacion.
- `AgendaEventCreate` se transforma al modelo `EventoAgenda` con `modulo_origen="MANUAL"`.
- Todo acceso a `agenda` autenticada debe respetar `sede_id` del actor.
- `calendar` no es un modulo totalmente aislado: agrega eventos de varias fuentes para la UI.

## 7. Dependencias compartidas criticas

- `system/calendar`
- `EventoAgenda`
- `apiFetch`
- `WorkspaceLayout`
- `spiritual_life:*` en `permissions.py`

## 8. Riesgos estructurales activos

1. **Agenda vs calendario agregado** `[PARCIAL-CALENDAR-AGGREGATION-001]` — la vista `/plataforma/calendar` depende de una agregacion cross-modulo; un fallo visual no implica automaticamente bug en `agenda.py`.
2. **Permisos heredados de spiritual_life** `[PARCIAL-AGENDA-RBAC-001]` — agenda hoy no tiene taxonomia propia; usa `spiritual_life:*`.

## 9. Pendientes formales

1. **Contrato de eventos agregados** `[PEND-CALENDAR-EVENTS-CONTRACT-001]` — documentar `system/calendar` y los tipos de evento que consume la UI.
2. **Matriz RBAC agenda** `[PEND-AGENDA-RBAC-001]` — documentar por rol real lectura/edicion de eventos, recursos y reservas.
3. **Script canonico del modulo** `[PEND-AGENDA-SMOKE-001]` — cerrada el 2026-07-16 con `scripts/test_agenda_quality.py`.

## 10. Archivos a revisar primero si falla

1. `backend/api/agenda.py`
2. `backend/crud/agenda.py`
3. `frontend/src/app/plataforma/calendar/page.tsx`
4. `frontend/src/components/calendar/InlineEventPopover.tsx`
5. `frontend/src/components/ui/UniversalCalendarView.tsx`

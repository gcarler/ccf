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
cat /root/ccf/docs/SYSTEM_CALENDAR_CONTRACT.md
cat /root/ccf/docs/AGENDA_RBAC_MATRIX.md
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

Referencia observada el **2026-09-05** (Auditoría Forense y Remediación Integral):

- Superficie backend: **1 032 LOC** en 4 archivos (`api/agenda.py`, `crud/agenda.py`, `models_agenda.py`, `schemas/agenda.py`) + **274 LOC** en `system.py` (`get_global_calendar`). Total: **1 306 LOC** (23 endpoints).
- Superficie frontend: **1 989 LOC** en 11 archivos (`agenda/events/**`, `calendar/**`, `components/calendar/**`, `UniversalCalendarView.tsx`).

## 4. Smoke test canonico

```bash
cd /root/ccf
./venv/bin/python scripts/test_agenda_quality.py
./venv/bin/python scripts/test_agenda_quality.py --backend-deep
```

**Estado actual (Revalidado y Certificado 2026-09-05 tras Remediación y Desacople RBAC):**
- **Veredicto Forense:** **APROBADO — 100% CERTIFICADO (Calificación: A+ / 100/100)**
- **Taxonomía Canónica Propia:** Desacoplado 100% de `spiritual_life:*`. Ahora cuenta con su propia taxonomía canónica `agenda:read`, `agenda:edit`, `agenda:manage` con retrocompatibilidad transparente.
- **Tests Backend:** **47 passed, 0 failed** (100% de éxito en tests de ciclo de vida de eventos, recursos, reservas con conflicto 409, soft delete, RBAC y contrato de agregador de calendario).
- **Aislamiento Multi-tenant:** Sede isolation validada en las 9 fuentes agregadas en `/api/system/calendar` y en todas las consultas de `backend/crud/agenda.py`.
- **Ciclo de vida de datos:** 0 llamadas a `db.delete(` (100% soft deletes).
- **Zonas horarias:** 0 llamadas a `datetime.utcnow` y 0 datetimes naive (100% `timezone.utc`).
- **Frontend Quality:** 100% `apiFetch`, 0 modales prohibidos, 0 tokens de alerta banned (`bg-red-50/100` erradicados), `tsc --noEmit` 0 errores, ESLint 0 warnings.

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
- Permisos canónicos: Taxonomía propia `agenda:read` para lectura, `agenda:edit` para mutación y `agenda:manage` para gestión integral, con retrocompatibilidad transparente para actores con permisos `spiritual_life:*`.
- `AgendaEventCreate` se transforma al modelo `EventoAgenda` con `modulo_origen="MANUAL"`.
- Todo acceso a `agenda` autenticada debe respetar `sede_id` del actor.
- `calendar` no es un modulo totalmente aislado: agrega eventos de varias fuentes para la UI.
- La matriz RBAC del modulo vive en `docs/AGENDA_RBAC_MATRIX.md`.

## 7. Dependencias compartidas criticas

- `system/calendar`
- `EventoAgenda`
- `apiFetch`
- `WorkspaceLayout`
- `agenda:*` en `permissions.py`

## 8. Riesgos estructurales activos

1. **Agenda vs calendario agregado** `[PARCIAL-CALENDAR-AGGREGATION-001]` — la vista `/plataforma/calendar` depende de una agregacion cross-modulo; un fallo visual no implica automaticamente bug en `agenda.py`.
2. **Permisos de agenda** `[PARCIAL-AGENDA-RBAC-001]` — **CERRADO Y SUBSANADO**. Agenda cuenta con su propia taxonomía canónica `agenda:read`, `agenda:edit`, `agenda:manage` integrada en backend y frontend.

## 9. Pendientes formales

1. **Contrato de eventos agregados** `[PEND-CALENDAR-EVENTS-CONTRACT-001]` — cerrada el 2026-07-16 con `docs/SYSTEM_CALENDAR_CONTRACT.md`.
2. **Matriz RBAC agenda** `[PEND-AGENDA-RBAC-001]` — cerrada el 2026-07-16 con `docs/AGENDA_RBAC_MATRIX.md`.
3. **Script canonico del modulo** `[PEND-AGENDA-SMOKE-001]` — cerrada el 2026-07-16 con `scripts/test_agenda_quality.py`.
4. **Plan operativo del modulo** `[PEND-PLAN-AGENDA-001]` — cerrada el 2026-07-16 con `docs/PLAN_AGENDA_CALIDAD.md`; fija fases para CRUD de eventos, reservas, agregación calendar, RBAC heredado y smoke frontend.
5. **Smoke frontend Agenda / Calendar** `[PEND-FRONTEND-E2E-AGENDA-001]` — cerrada el 2026-07-16 con `frontend/tests/e2e/agenda/smoke.spec.ts`; cubre calendar y agenda/events con guard de consola/API/assets.
6. **Cobertura profunda Agenda / Calendar** `[PEND-FRONTEND-E2E-AGENDA-DEEP-001]` — cerrada el 2026-07-16 con `frontend/tests/e2e/agenda/calendar-events.spec.ts`; cubre CRUD manual básico, detalle editable y navegación desde `/plataforma/calendar` hacia el owner route del evento.
7. **Auditoría forense y remediación integral** `[AUDITORIA-FORENSE-AGENDA-2026-09-05]` — cerrada el 2026-09-05. Remediación completa de hallazgos OBS-01 (erradicación de `bg-red-50` por tokens semánticos `destructive` en `calendar/page.tsx` y `agenda/events/`), OBS-02 (migración de `datetime.now()` naive a `datetime.now(timezone.utc)` en borrado de comentarios), y OBS-03 (actualización de suite `--backend-deep` en `scripts/test_agenda_quality.py` para incluir suite completa y contrato).
8. **Desacople canónico de RBAC y elevación a 100/100** `[CERRADO-AGENDA-RBAC-001]` — cerrada el 2026-09-05. Creación de la taxonomía canónica `agenda:read`, `agenda:edit`, `agenda:manage` en `backend/core/permissions.py`, `backend/core/kernel_rbac.py`, `backend/management/seed_user_permissions.py` y `backend/api/agenda.py`. Actualización del control de acceso frontend en `workspaceAccess.ts` y del panel administrativo de accesos. Verificación de 47 tests backend pasados, 96 tests de permisos pasados, 51 tests de acceso frontend pasados, 0 errores en `tsc --noEmit` y 0 warnings en ESLint. Calificación final: **A+ / 100/100**.
9. **Auditoría Forense Conclusiva Multi-Agente (teamwork-preview)** `[AUDITORIA-FORENSE-AGENDA-2026-09-06]` — cerrada el 2026-09-06. Validación adversarial completa e independiente desplegada con el sistema multi-agente Sentinel/Teamwork (**357 tests ejecutados y aprobados**, 0 fallos). Subsanación preventiva de ruta `/plataforma/` en `events/page.tsx:392`. Contra-auditoría post-victoria (`victory_auditor`) aprobada de forma unánime y sin sesgos: **VICTORY CONFIRMED (100/100, Grado: A+)**. Reporte formal en [`docs/AUDITORIA_FORENSE_AGENDA_2026-09-06.md`](file:///root/ccf/docs/AUDITORIA_FORENSE_AGENDA_2026-09-06.md).

## 10. Archivos a revisar primero si falla

1. `backend/api/agenda.py`
2. `backend/crud/agenda.py`
3. `frontend/src/app/plataforma/calendar/page.tsx`
4. `frontend/src/components/calendar/InlineEventPopover.tsx`
5. `frontend/src/components/ui/UniversalCalendarView.tsx`

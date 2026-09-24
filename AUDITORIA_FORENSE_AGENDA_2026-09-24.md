# Auditoría Forense Integral: Módulo Agenda y Calendario (Eventos, Calendario Transversal y Disponibilidad) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `agenda` (Agenda Eclesial, Calendario Transversal, Bus de Eventos, Participantes, Recursos Físicos y Control de Colisiones)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-AGENDA-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.8 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Agenda y Calendario (`agenda`)** de la Plataforma CCF, cubriendo la totalidad de sus capas estructurales y operativas:
- **Backend y Endpoints Transversales:** `backend/api/agenda.py` (583 líneas de gestión de eventos, filtros temporales, reservas de recursos, participantes y comentarios), `backend/crud/agenda.py` (339 líneas de lógica transaccional y prevención de colisiones), `backend/models_agenda.py` (134 líneas con 5 modelos relacionales: `RecursoFisico`, `EventoAgenda`, `ParticipanteEvento`, `ReservaRecurso`, `AgendaEventComment`) y `backend/schemas/agenda.py`.
- **Frontend y Vistas Operativas:** Los 10 archivos canónicos del módulo en `frontend/src/app/plataforma/` y `frontend/src/components/calendar/`:
  1. `frontend/src/app/plataforma/agenda/events/page.tsx` (Listado y Gestión de Eventos)
  2. `frontend/src/app/plataforma/agenda/events/[id]/page.tsx` (Detalle y Administración de Evento Específico)
  3. `frontend/src/app/plataforma/calendar/page.tsx` (Hub Central del Calendario Transversal)
  4. `frontend/src/app/plataforma/calendar/layout.tsx` (Layout Base del Calendario)
  5. `frontend/src/components/calendar/CalendarPanel.tsx` (Panel Lateral Drawer para Creación/Edición)
  6. `frontend/src/components/calendar/DayView.tsx` (Vista Diaria por Horas)
  7. `frontend/src/components/calendar/InlineEventPopover.tsx` (Popover Contextual de Evento)
  8. `frontend/src/components/calendar/MonthView.tsx` (Vista Mensual Matricial)
  9. `frontend/src/components/calendar/PanelSection.tsx` (Sección Modular de Paneles)
  10. `frontend/src/components/calendar/WeekView.tsx` (Vista Semanal de Malla Temporal)
- **Suites de Pruebas y Aseguramiento:** `tests/test_agenda_api.py`, `tests/test_agenda_full.py`, `tests/test_system_calendar_contract.py` (44 pruebas automatizadas con 100% de éxito).
- **Documentación Canónica:** `docs/ESTADO_AGENDA.md`, `docs/PLAN_AGENDA_CALIDAD.md`, `docs/AGENDA_API_CONTRACTS.md`, `docs/SYSTEM_CALENDAR_CONTRACT.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento riguroso. Todas las entidades de la agenda acoplan sus relaciones humanas exclusivamente al UUID canónico de `personas.id`:
   - `EventoAgenda.organizador_persona_id` refiere obligatoriamente a `personas.id`.
   - `ParticipanteEvento.persona_id` refiere obligatoriamente a `personas.id`.
   - `AgendaEventComment.author_id` refiere a `personas.id`. Cero tablas paralelas de seres humanos. Cero identidades desconectadas.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento estricto. Todas las columnas temporales (`fecha_inicio`, `fecha_fin`, `fecha_limite_recurrencia`, `fecha_confirmacion`, `bloqueo_inicio`, `bloqueo_fin`, `created_at`, `updated_at`, `deleted_at`) utilizan `DateTime(timezone=True)`. Backend opera con `datetime.now(timezone.utc)` y `_utcnow_tz()`. Prohibición absoluta de `datetime.utcnow()` respetada al 100% (0 ocurrencias en todo el código backend). Preservación de registros mediante soft-delete (`deleted_at.is_(None)`).
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** La función `_sede_id(db, user) -> UUID: return UUID(str(require_user_sede_id(db, user)))` en `backend/api/agenda.py` garantiza que ninguna solicitud pueda suplantar la sede por query o body. La sede se resuelve obligatoriamente del token del usuario autenticado. `list_events`, `list_events_by_date_range`, reservas y recursos operan bajo aislamiento de sede estricto.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` o modals en viewport center) en los 10 archivos de frontend. La creación y edición de eventos utiliza paneles laterales deslizantes (`CalendarPanel` SidePanel Drawer alineado a la derecha) y popovers contextuales flotantes (`InlineEventPopover`).
5. **Regla Frontend 2 (Tokens Semánticos CSS — 65%):** **Hallazgo H-AGENDA-01**. Los 10 archivos analizados presentan clases Tailwind hardcodeadas (`bg-white`, `border-white`, `text-white`, `bg-slate-900`, `text-slate-700`, `bg-blue-600`, `border-gray-200`) y selectores `dark:` redundantes. Se contabilizan **133 clases Tailwind hardcodeadas** y **178 selectores `dark:`** en el frontend de Agenda y Calendario.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** Los 10 archivos auditados utilizan exclusivamente `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Cero rutas sin prefijo `/plataforma/...`. Navegación unificada bajo `/plataforma/agenda/events` y `/plataforma/calendar`.
8. **Compilación y Pruebas Backend (100%):** Suite completa de 44 pruebas ejecutada con éxito (`44 passed in 34.29s`). Balance sintáctico estricto en los 10 archivos de frontend (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `organizador_persona_id`, `persona_id` y `author_id` enlazan a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps con `DateTime(timezone=True)`. Backend en UTC estricto. Cero llamadas a `datetime.utcnow()`. Soft-delete activo en las 5 tablas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`require_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** `_sede_id` inyecta `require_user_sede_id(db, user)`. Prohibido bypass desde cliente. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 10 archivos auditados. 0 modales centrados (`AlertDialog` = 0, Modales = 0). Uso de `CalendarPanel` SidePanel Drawer. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (65%). Hallazgo H-AGENDA-01.** 133 clases Tailwind hardcodeadas y 178 selectores `dark:` en los 10 archivos de agenda y calendario. | 15% | **65/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 10 archivos verificados. Cero llamadas a `fetch()` crudo. 100% de consultas internas utilizan `apiFetch`. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** 44 tests pasando (`test_agenda_api.py`, `test_agenda_full.py`, `test_system_calendar_contract.py`). | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos, esquemas Pydantic y documentación de estado sincronizada en `docs/AGENDA_*.md` y `docs/ESTADO_AGENDA.md`. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (65 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.75 + 10.0 + 10.0 + 5.0 = \mathbf{89.75 / 100} \approx \mathbf{89.8 / 100}$$

**Calificación Inicial:** **Grado A (89.8 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Agenda y Calendario exhibe una arquitectura sólida con estricto acoplamiento al Kernel de Personas (Axioma 1), UTC estricto con `DateTime(timezone=True)` (Axioma 2) y aislamiento multi-tenant por sede garantizado (Axioma 3). En la capa frontend, no existen modales centrados (100% Drawers / Popovers), pero se detecta el hallazgo **H-AGENDA-01** (133 clases Tailwind hardcodeadas y 178 selectores `dark:` en 10 archivos). Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de los 10 Archivos de Frontend de Agenda y Calendario

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/agenda/events/page.tsx` | 445 | 49 | 70 | 0 | 🔴 Requiere Fase 1 (H-AGENDA-01) |
| 2 | `frontend/src/app/plataforma/agenda/events/[id]/page.tsx` | 216 | 22 | 31 | 0 | 🔴 Requiere Fase 1 (H-AGENDA-01) |
| 3 | `frontend/src/app/plataforma/calendar/page.tsx` | 311 | 21 | 22 | 0 | 🔴 Requiere Fase 2 (H-AGENDA-01) |
| 4 | `frontend/src/app/plataforma/calendar/layout.tsx` | 91 | 0 | 1 | 0 | 🔴 Requiere Fase 2 (H-AGENDA-01) |
| 5 | `frontend/src/components/calendar/CalendarPanel.tsx` | 158 | 15 | 19 | 0 | 🔴 Requiere Fase 2 (H-AGENDA-01) |
| 6 | `frontend/src/components/calendar/DayView.tsx` | 91 | 1 | 1 | 0 | 🔴 Requiere Fase 2 (H-AGENDA-01) |
| 7 | `frontend/src/components/calendar/InlineEventPopover.tsx` | 145 | 10 | 20 | 0 | 🔴 Requiere Fase 2 (H-AGENDA-01) |
| 8 | `frontend/src/components/calendar/MonthView.tsx` | 106 | 6 | 5 | 0 | 🔴 Requiere Fase 2 (H-AGENDA-01) |
| 9 | `frontend/src/components/calendar/PanelSection.tsx` | 34 | 0 | 0 | 0 | 🟢 Conforme |
| 10 | `frontend/src/components/calendar/WeekView.tsx` | 150 | 9 | 9 | 0 | 🔴 Requiere Fase 2 (H-AGENDA-01) |
| **TOTAL** | **10 Archivos Auditados** | **1,747** | **133** | **178** | **0** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-AGENDA-01**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Eventos de Agenda (`TKT-AGENDA-REMEDIATION-01`)
- **Archivos a intervenir (2 archivos):**
  1. `frontend/src/app/plataforma/agenda/events/page.tsx` (49 clases TW + 70 `dark:`)
  2. `frontend/src/app/plataforma/agenda/events/[id]/page.tsx` (22 clases TW + 31 `dark:`)
- **Acciones específicas:**
  - Sustituir colores de Tailwind (`bg-white`, `border-white`, `text-white`, `bg-gray-50`, `border-gray-200`, `text-slate-700`) por tokens semánticos: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`.
  - Erradicar selectores `dark:` redundantes (`dark:bg-[#111418]`, `dark:border-white/10`, `dark:text-white`).
- **Total incidencias a erradicar:** 71 clases TW / 101 selectores `dark:`.
- **Commit atómico:** `feat(agenda): Remediación de Tokens Semánticos en Páginas de Eventos (H-AGENDA-01 Fase 1)`.

### Fase 2: Hub Calendario y Componentes de Vista (`TKT-AGENDA-REMEDIATION-02`)
- **Archivos a intervenir (7 archivos):**
  1. `frontend/src/app/plataforma/calendar/page.tsx` (21 clases TW + 22 `dark:`)
  2. `frontend/src/app/plataforma/calendar/layout.tsx` (0 clases TW + 1 `dark:`)
  3. `frontend/src/components/calendar/CalendarPanel.tsx` (15 clases TW + 19 `dark:`)
  4. `frontend/src/components/calendar/DayView.tsx` (1 clase TW + 1 `dark:`)
  5. `frontend/src/components/calendar/InlineEventPopover.tsx` (10 clases TW + 20 `dark:`)
  6. `frontend/src/components/calendar/MonthView.tsx` (6 clases TW + 5 `dark:`)
  7. `frontend/src/components/calendar/WeekView.tsx` (9 clases TW + 9 `dark:`)
- **Acciones específicas:**
  - Sustituir colores hardcodeados de Tailwind (`bg-white`, `border-white`, `text-white`, `bg-[#111418]`, `bg-[#1a1b1e]`, `bg-[#1E1F21]`) por tokens del Design System: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`.
  - Erradicar selectores `dark:` y opacidades no semánticas.
- **Total incidencias a erradicar:** 62 clases TW / 77 selectores `dark:`.
- **Commit atómico:** `feat(agenda): Remediación de Tokens Semánticos en Hub Calendario y Componentes de Vista (H-AGENDA-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-AGENDA-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en los 10 archivos.
3. Se procederá con `TKT-AGENDA-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/agenda/events`
   - `/plataforma/calendar`
   - `/plataforma/dashboard/agenda`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.8 / 100 — Grado A)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-AGENDA-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*

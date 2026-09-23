# Reporte de Auditoría Forense Integral: Módulo Evangelismo

**Fecha de Emisión:** 2026-09-23  
**Auditor Responsable:** Equipo de Auditoría Forense y Calidad CCF (`agy` / `agy2`)  
**Ticket de Auditoría:** `TKT-AUDIT-EVANGELISMO-01`  
**Estado:** **DICTAMEN EMITIDO — PLAN DE REMEDIACIÓN PRIORIZADO REQUERIDO**  
**Puntaje Preliminar:** **74.75 / 100 (Grado C)**  

---

## 1. Alcance de la Auditoría Forense

El alcance evaluado comprende la totalidad del ecosistema de alcance misionero, estrategias relacionales y geográficas, grupos de evangelismo, sesiones semanales, pre-registro masivo de eventos, asistencia con QR, analítica de multiplicación y el puente bidireccional con CRM y el Kernel de Personas:

- **Backend Evangelismo y Puentes:**
  - Rutas y controladores API: `backend/api/` (`evangelism.py`, `evangelism_events.py`, `evangelism_multiplication.py`, `evangelism_notifications.py`, `evangelism_public.py`, `evangelism_rankings.py`, `evangelism_reports.py`, `evangelism_shared.py`, `evangelism_analytics.py`).
  - Servicios de integración: `backend/services/evangelism_crm_bridge.py`.
  - Capa CRUD: `backend/crud/evangelism.py`.
  - Modelos ORM relacionales: `backend/models_evangelism.py` (`CampaignSeason`, `Sede`, `LogAuditoria`, `CategoriaEstrategia`, `MotivoExcusa`, `EstrategiaEvangelismo`, `RolPersonalizadoEstrategia`, `GrupoEvangelismo`, `ParticipanteGrupo`, `SesionGrupo`, `Asistencia`, `RegistroSeguimiento`, `HistorialEmbudo`).
  - Esquemas de validación Pydantic: `backend/schemas/evangelism.py`.
- **Frontend Evangelismo:**
  - Vistas y páginas: `frontend/src/app/plataforma/evangelism/**` (35 rutas y componentes, incluyendo `events`, `groups`, `strategies`, `multiplication`, `rankings`, `scanner`, `dashboard`).
  - Componentes de interfaz compartidos: `frontend/src/components/evangelism/**` (`ConfirmActionDrawer.tsx`, `EvangelismShell.tsx`, `StrategyCreationDrawer.tsx`).
- **8 Ejes de Evaluación Canónicos:**
  1. Axioma 1: Kernel de Personas (`personas.id` canónico, 0 tablas paralelas).
  2. Axioma 2: Fechas en UTC (`datetime.now(timezone.utc)`) y Soft Deletes (`deleted_at`).
  3. Axioma 3: Aislamiento Multi-Tenant (`sede_id` del actor autenticado vía `require_user_sede_id`, 0 fugas IDOR).
  4. Regla Frontend 1: Drawers vs Modals (`SidePanel` / `WorkspaceDrawer` obligatorio, 0 modales centrados).
  5. Regla Frontend 2: Tokens Semánticos del Design System vs Colores Tailwind hardcodeados.
  6. Regla Frontend 3: Cliente HTTP (`apiFetch()`, 0 `fetch()` crudo).
  7. Compilación y Pruebas (69 suites de backend dedicadas, tipado estricto).
  8. Estado Documental (8 artefactos canónicos presentes y sincronizados).

---

## 2. Matriz Cuantitativa de los 8 Ejes de Auditoría

| # | Eje Canónico de Auditoría | Criterio de Aceptación | Evidencia Empírica Verificada | Puntaje | Estado |
| :-: | :--- | :--- | :--- | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único para seres humanos; 0 tablas paralelas | 100% de los roles y actores (`usuario_id`, `lider_persona_id`, `asistente_persona_id`, `anfitrion_persona_id`, `ParticipanteGrupo.persona_id`, `Asistencia.persona_id`, `RegistroSeguimiento.persona_id`, `HistorialEmbudo.persona_id`) referencian inequívocamente `personas.id` (`ForeignKey("personas.id")`). Cero tablas paralelas de contactos o conversos. Puente con CRM anclado a `backend.models_crm.Persona`. | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas UTC y Soft-Deletes** | `datetime.now(timezone.utc)`, 0 `utcnow()`, 0 `db.delete(` | **Fechas (100%):** 0 `datetime.utcnow()` crudo; marcas de tiempo gestionadas mediante `_utcnow()` (`datetime.now(timezone.utc)`) con `DateTime(timezone=True)`.<br>**Soft-Delete (100%):** 0 llamadas a `db.delete(` en la capa CRUD. 100% de los borrados aplican soft-delete vía `deleted_at = _utcnow()`. | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` vía actor autenticado, nunca del cliente | `sede_id` obtenido estrictamente mediante `require_user_sede_id(db, current_user)` invocando `get_user_sede_id(db, current_user.id)`. Cero fugas IDOR. Mutaciones sin sede retornan 403/409. Scoping hermético en consultas de estrategias, grupos y sesiones. | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Drawers (`SidePanel` / `WorkspaceDrawer`) obligatorios; 0 modals centrados | **Incumplimiento detectado.** 2 modales centrados clásicos con `fixed inset-0` y backdrop oscuro en `frontend/src/app/plataforma/evangelism/events/[id]/tabs/PreregistrationTab.tsx` (L578: Configuración de pre-registro, L746: Nueva campaña). Resto de vistas usa `WorkspaceDrawer`. | **50/100** | 🔴 **FALLA CRÍTICA** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Incumplimiento masivo.** Se identificaron **701 ocurrencias de colores Tailwind hardcodeados** y selectores `dark:` a lo largo de **46 archivos `.tsx`/`.ts`** (`text-white`, `bg-white`, `bg-black`, `zinc-*`, `gray-*`, `blue-*`, `emerald-*`, `red-*`). | **25/100** | 🔴 **FALLA CRÍTICA** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno.** 0 llamadas a `fetch()` crudo en todo el frontend de Evangelismo. 100% de llamadas utilizan `apiFetch()` (`@/lib/http`) con gestión centralizada de headers y tokens. | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas** | Tests pasando, suites estructuradas y scripts canónicos | **69 suites backend dedicadas** (`tests/test_evangelism*.py`). Pruebas pasando (12/12 en test_evangelism_crm_bridge.py, 4/4 en test_calculo_sesiones.py). Script canónico `scripts/test_evangelism_quality.py` operativo con bypass documentado de duckdb en sandbox. | **85/100** | 🟡 **APROBADO CON OBS.** |
| **E8** | **Estado Documental** | Artefactos canónicos presentes y sincronizados | Paquete documental canónico completo y sincronizado: `docs/EVANGELISMO_API_CONTRACTS.md`, `docs/EVANGELISMO_QA_CHECKLIST.md`, `docs/EVANGELISMO_RBAC_MATRIX.md`, `docs/ESTADO_EVANGELISMO.md`, `docs/PLAN_EVANGELISMO_CALIDAD.md`, `docs/CRM_EVANGELISM_BRIDGE.md`, `docs/PLAN_DE_TRABAJO_EVANGELISMO.md` y `scripts/test_evangelism_quality.py`. | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (50 \times 0.15) + (25 \times 0.15) + (100 \times 0.10) + (85 \times 0.10) + (100 \times 0.05) = \mathbf{74.75 / 100}$$

**Calificación:** **Grado C (74.75 / 100)**  
**Dictamen:** El backend, la base de datos y la integración con CRM del Módulo Evangelismo son ejemplares y cumplen al 100% con los Axiomas 1, 2 y 3. No obstante, el frontend presenta deuda técnica crítica en **Regla Frontend 1 (2 modales centrados en PreregistrationTab)** y **Regla Frontend 2 (701 ocurrencias de colores Tailwind en 46 archivos)**, lo que impide su certificación inmediata. Se requiere ejecutar un plan de remediación en fases para alcanzar el 100/100 A+.

---

## 4. Inventario Detallado de Hallazgos Forenses

### Hallazgo H-EVAN-01: Proliferación de Colores Hardcodeados de Tailwind (Regla Frontend 2)
- **Severidad:** 🔴 **ALTA**
- **Impacto:** 701 ocurrencias detectadas en 46 archivos `.tsx`/`.ts` en `frontend/src/app/plataforma/evangelism` y `frontend/src/components/evangelism`.
- **Archivos más afectados:**
  - `frontend/src/components/evangelism/StrategyCreationDrawer.tsx` (91 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/strategies/[id]/panels/AttendanceDrawer.tsx` (39 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/events/panels/EventCreateDrawer.tsx` (38 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/events/panels/EventEditDrawer.tsx` (36 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/strategies/[id]/panels/StrategyViews.tsx` (34 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/groups/[id]/panels/GroupMonitoringPanel.tsx` (34 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/groups/page.tsx` (33 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/strategies/[id]/panels/SessionsSection.tsx` (30 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/events/panels/EventAttendanceDrawer.tsx` (29 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/events/[id]/tabs/SessionTab.tsx` (25 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/strategies/[id]/panels/StrategyDashboard.tsx` (24 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/groups/sessions/[grupo_id]/page.tsx` (23 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/multiplication/page.tsx` (22 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/groups/[id]/panels/GroupAddAttendeeDrawer.tsx` (22 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/scanner/page.tsx` (18 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/events/panels/EventCardViews.tsx` (16 ocurrencias)
  - `frontend/src/app/plataforma/evangelism/EvangelismClient.tsx` (15 ocurrencias)
- **Patrones Infractores:** Clases como `text-white`, `bg-white`, `bg-black`, `zinc-*`, `gray-*`, `blue-*`, `emerald-*`, `red-*`, y selectores redundantes `dark:`.
- **Solución Requerida:** Sustitución estricta por tokens semánticos CSS del Design System:
  - Superficies: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--bg-primary))`
  - Bordes: `hsl(var(--border))`
  - Textos: `hsl(var(--foreground))`, `hsl(var(--muted-foreground))`
  - Acciones: `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--destructive))`, `hsl(var(--success))`

---

### Hallazgo H-EVAN-02: Modales Centrados Clásicos en Preregistro de Eventos (Regla Frontend 1)
- **Severidad:** 🔴 **ALTA**
- **Impacto:** Rompe el estándar de experiencia de usuario de la plataforma CCF (Drawers / SidePanels laterales en flujos de creación/edición).
- **Ubicaciones Específicas:**
  1. `frontend/src/app/plataforma/evangelism/events/[id]/tabs/PreregistrationTab.tsx:578`: Modal centrado `<div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-0 sm:p-4">` para la configuración del pre-registro de evento.
  2. `frontend/src/app/plataforma/evangelism/events/[id]/tabs/PreregistrationTab.tsx:746`: Modal centrado `<div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-0 sm:p-4">` para la creación y lanzamiento de campañas.
- **Solución Requerida:** Migración completa de ambos formularios al componente canónico `@/components/ui/SidePanel` (o `WorkspaceDrawer`), eliminando el contenedor `fixed inset-0`.

---

### Hallazgo H-EVAN-03: Crash de Inicialización DuckDB C++ en Entorno Sandbox
- **Severidad:** 🟡 **MEDIA**
- **Impacto:** Al ejecutar la suite general de pruebas o `scripts/test_evangelism_quality.py`, la importación de `duckdb` (versión 1.5.3) en este entorno confinado genera una excepción C++ unhandled (`SIGABRT: Attempted to dereference unique_ptr that is NULL!`). Las pruebas puras de Evangelismo no dependen de DuckDB y pasan al 100% cuando DuckDB es aislado.
- **Solución Requerida:** Asegurar que los scripts de prueba aíslen DuckDB en entornos donde la extensión nativa C++ falle, o aislar el sink de analytics durante pruebas de Evangelismo.

---

## 5. Plan de Remediación Propuesto para el Módulo Evangelismo

Para llevar al Módulo Evangelismo desde **74.75 (C)** hasta **100/100 (A+)**, se define la siguiente secuencia de tickets atómicos:

| Ticket ID | Título del Ticket | Alcance y Archivos Afectados |
| :--- | :--- | :--- |
| `TKT-EVAN-REMEDIATION-01` | Migración de Modales Centrados en Pre-registro a SidePanel Drawers (H-EVAN-02) | `frontend/src/app/plataforma/evangelism/events/[id]/tabs/PreregistrationTab.tsx` (L578 y L746 a SidePanel canónico). |
| `TKT-EVAN-REMEDIATION-02` | Remediación de Tokens Semánticos en Estrategias y Componentes Compartidos (H-EVAN-01 Fase 1) | `StrategyCreationDrawer.tsx`, `ConfirmActionDrawer.tsx`, `EvangelismShell.tsx`, `strategies/[id]/panels/*.tsx`, `strategies/[id]/page.tsx`. |
| `TKT-EVAN-REMEDIATION-03` | Remediación de Tokens Semánticos en Eventos y Pre-registro (H-EVAN-01 Fase 2) | `events/panels/*.tsx`, `events/[id]/tabs/*.tsx`, `events/page.tsx`, `events/analytics/page.tsx`, `EventViews.tsx`, `EventQrDrawer.tsx`. |
| `TKT-EVAN-REMEDIATION-04` | Remediación de Tokens Semánticos en Grupos, Sesiones, Rankings y Scanner (H-EVAN-01 Fase 3) | `groups/**`, `rankings/**`, `scanner/**`, `multiplication/**`, `EvangelismClient.tsx`. |
| `TKT-EVAN-FINAL-CERTIFICATION` | Certificación Forense Plena 100/100 A+ y Emisión de Dictamen Final | Verificación adversarial 0 modales, 0 colores Tailwind, 100% apiFetch, 100% Axiomas 1-3 y emisión de dictamen final. |
| `TKT-EVAN-DEPLOY-AND-VERIFY` | Despliegue Staging y Verificación en Vivo del Módulo Evangelismo | Ejecución de `scripts/deploy_frontend.sh` y verificación HTTP 200 en las rutas de Evangelismo en staging. |

---

## 6. Dictamen Conclusivo de la Auditoría

El backend, la base de datos y la arquitectura del **Módulo Evangelismo** exhiben solidez canónica inquebrantable en cuanto a los tres axiomas rectores de la Plataforma CCF (Kernel de Personas único, UTC estricto con soft-deletes universales y aislamiento multi-tenant hermético a nivel de consultas y mutaciones). Asimismo, su capa de red frontend respeta la política de peticiones unificadas (`apiFetch`).

No obstante, **NO es apto para certificación final en su estado actual** debido a la presencia de 2 modales centrados invasivos en el módulo de pre-registro (`PreregistrationTab.tsx`) y 701 ocurrencias de clases Tailwind hardcodeadas en 46 archivos frontend. Se recomienda proceder de inmediato con la ejecución del Plan de Remediación escalonado iniciando con `TKT-EVAN-REMEDIATION-01`.

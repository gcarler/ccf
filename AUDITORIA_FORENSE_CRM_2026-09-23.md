# Reporte de Auditoría Forense Integral: Módulo CRM y Evangelismo

**Fecha de Emisión:** 2026-09-23  
**Auditor Responsable:** Equipo de Auditoría Forense y Calidad CCF (`agy` / `agy2`)  
**Ticket de Auditoría:** `TKT-AUDIT-CRM-01`  
**Estado:** **DICTAMEN EMITIDO — PLAN DE REMEDIACIÓN PRIORIZADO REQUERIDO**  
**Puntaje Preliminar:** **78.75 / 100 (Grado C+)**  

---

## 1. Alcance de la Auditoría Forense

El alcance evaluado comprende la totalidad del ecosistema de gestión pastoral, relaciones y consolidación ministerial de la Plataforma CCF (CRM) y su puente bidireccional con Evangelismo:

- **Backend CRM y Puentes:**
  - Rutas y controladores API: `backend/api/crm/` (`pastoral.py`, `personas.py`, `persona_relations.py`, `pipelines.py`, `resources.py`, `_shared.py`).
  - Servicios de integración: `backend/services/evangelism_crm_bridge.py`.
  - Capa CRUD: `backend/crud/crm.py`, `backend/crud/crm_/` (`personas.py`, `pipeline.py`, `tasks.py`, `counseling.py`, `prayer.py`, `groups.py`, `resources.py`, `donations.py`, `events.py`, `families.py`, `volunteers.py`, `milestones.py`, `communication.py`, `support.py`, `extended.py`, `health.py`, `shared.py`).
  - Modelos ORM relacionales: `backend/models_crm.py`, `backend/models_crm_pipeline.py`.
- **Frontend CRM:**
  - Vistas y páginas: `frontend/src/app/plataforma/crm/**` (34 rutas, incluyendo `contacts`, `personas`, `pipeline`, `tasks`, `counseling`, `prayers`, `volunteers`, `messaging`, `resources`, `settings`, `analytics`, `groups`).
  - Componentes de interfaz y builder: `frontend/src/components/crm/**` (sidebars, kanban, tablas, detalles y email-builder).
- **8 Ejes de Evaluación Canónicos:**
  1. Axioma 1: Kernel de Personas (`personas.id` canónico, 0 tablas paralelas).
  2. Axioma 2: Fechas en UTC (`datetime.now(timezone.utc)`) y Soft Deletes (`deleted_at`).
  3. Axioma 3: Aislamiento Multi-Tenant (`sede_id` del actor, 0 fugas IDOR).
  4. Regla Frontend 1: Drawers vs Modals (`SidePanel` obligatorio, 0 modales centrados).
  5. Regla Frontend 2: Tokens Semánticos del Design System vs Colores Tailwind hardcodeados.
  6. Regla Frontend 3: Cliente HTTP (`apiFetch()`, 0 `fetch()` crudo).
  7. Compilación y Pruebas (`tsc --noEmit`, 66 suites de backend CRM, scripts canónicos).
  8. Estado Documental (6 artefactos canónicos presentes y sincronizados).

---

## 2. Matriz Cuantitativa de los 8 Ejes de Auditoría

| # | Eje Canónico de Auditoría | Criterio de Aceptación | Evidencia Empírica Verificada | Puntaje | Estado |
| :-: | :--- | :--- | :--- | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único para seres humanos; 0 tablas paralelas | 100% de los roles y actores humanos (`persona_id`, `leader_id`, `pastor_id`, `minister_id`, `creado_por_id`, `destinatario_id`, `asignado_a_id`, etc.) referencian inequívocamente `personas.id` (`ForeignKey("personas.id")`). Cero tablas paralelas de contactos o leads. `auth_users.id` comparte UUID canónico. Puente con Evangelismo anclado a `Persona`. | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas UTC y Soft-Deletes** | `datetime.now(timezone.utc)`, 0 `utcnow()`, 0 `db.delete(` | **Fechas (100%):** 0 `datetime.utcnow()`; 100% de marcas de tiempo gestionadas mediante `_utcnow()` / `utc_now()` retornando `datetime.now(timezone.utc)` con `DateTime(timezone=True)`.<br>**Soft-Delete (100%):** 0 `db.delete(` en capa CRUD. Todos los borrados implementan soft-delete vía `deleted_at = _utcnow()` o `activo = False`. | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` vía actor `get_user_sede_id()`, nunca del cliente | `sede_id` obtenido estrictamente mediante `get_user_sede_id(db, current_user.id)`. Scoping helpers dedicados en `_shared.py` (`_get_scoped_persona`, `_get_scoped_family`, `_get_scoped_task`, etc.) previenen IDOR retornando 404 neutro (*existence-leak safe*). Mutaciones sin sede retornan 409. | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Drawers (`SidePanel`) obligatorios; 0 modals centrados | **Incumplimiento detectado.** 3 modales centrados (`settings/templates/page.tsx:148`, `ResourceBankGallery.tsx:121`, `HtmlPreview.tsx:15`). Múltiples paneles laterales artesanales `fixed right-0` con backdrops oscuros manuales en vez de usar el componente canónico `@/components/ui/SidePanel`. | **45/100** | 🔴 **FALLA CRÍTICA** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Incumplimiento masivo.** Se identificaron **1.512 ocurrencias de colores Tailwind hardcodeados** en **68 archivos** del frontend de CRM (`text-white`, `bg-white`, `bg-black`, `zinc-*`, `gray-*`, `blue-*`, `emerald-*`, `red-*`, `dark:bg-[#1E1F21]`, `dark:bg-[#15171c]`). | **20/100** | 🔴 **FALLA CRÍTICA** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno.** 0 llamadas a `fetch()` crudo en toda la plataforma CRM. 100% de llamadas utilizan `apiFetch()` (`@/lib/http`) con control centralizado de cabeceras y JWT. | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas** | Tests pasando, suites estructuradas y scripts canónicos | **66 suites de backend dedicadas** (`tests/test_crm*.py`) cubriendo dominio, aislamiento, seguridad runtime, RBAC HTTP-level y concurrencia. Script canónico `scripts/test_crm_quality.py` operativo. Observación: requiere bandera `-o addopts=` en entornos locales para evitar conflicto con `.coverage`. | **90/100** | 🟡 **APROBADO CON OBS.** |
| **E8** | **Estado Documental** | 6 artefactos canónicos presentes y sincronizados | Paquete documental canónico completo y sincronizado: `docs/CRM_ARCHITECTURE.md`, `docs/ESTADO_CRM.md`, `docs/CRM_API_CONTRACTS.md`, `docs/CRM_QA_CHECKLIST.md`, `docs/CRM_RBAC_MATRIX.md`, `docs/PLAN_CRM_CALIDAD.md`, `docs/CRM_EVANGELISM_BRIDGE.md` y `scripts/test_crm_quality.py`. | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (45 \times 0.15) + (20 \times 0.15) + (100 \times 0.10) + (90 \times 0.10) + (100 \times 0.05) = \mathbf{78.75 / 100}$$

**Calificación:** **Grado C+**  
**Dictamen:** El backend y la base de datos de CRM cumplen con el 100% de los estándares arquitectónicos de la plataforma CCF (Axiomas 1, 2 y 3). No obstante, el frontend presenta deuda técnica sustancial en el cumplimiento de la **Regla 1 (Modales a SidePanel)** y la **Regla 2 (Tokens Semánticos vs Tailwind)**, requiriendo un plan de remediación en fases para alcanzar la certificación 100/100 A+.

---

## 4. Inventario Detallado de Hallazgos Forenses

### Hallazgo H-CRM-01: Proliferación Crítica de Colores Hardcodeados de Tailwind (Regla Frontend 2)
- **Severidad:** 🔴 **ALTA**
- **Impacto:** 1.512 ocurrencias detectadas a lo largo de 68 archivos `.tsx`/`.ts` en `frontend/src/app/plataforma/crm` y `frontend/src/components/crm`.
- **Archivos más afectados:**
  - `frontend/src/app/plataforma/crm/resources/page.tsx` (134 ocurrencias)
  - `frontend/src/app/plataforma/crm/counseling/page.tsx` (109 ocurrencias)
  - `frontend/src/app/plataforma/crm/messaging/page.tsx` (74 ocurrencias)
  - `frontend/src/app/plataforma/crm/personas/[id]/page.tsx` (70 ocurrencias)
  - `frontend/src/app/plataforma/crm/contacts/page.tsx` (68 ocurrencias)
  - `frontend/src/app/plataforma/crm/personas/page.tsx` (62 ocurrencias)
  - `frontend/src/app/plataforma/crm/prayers/page.tsx` (60 ocurrencias)
  - `frontend/src/components/crm/PersonaDetailSidebar.tsx` (57 ocurrencias)
  - `frontend/src/app/plataforma/crm/tasks/page.tsx` (53 ocurrencias)
  - `frontend/src/app/plataforma/crm/pipeline/page.tsx` (45 ocurrencias)
  - `frontend/src/app/plataforma/crm/settings/page.tsx` (44 ocurrencias)
  - `frontend/src/app/plataforma/crm/analytics/page.tsx` (41 ocurrencias)
  - `frontend/src/app/plataforma/crm/contacts/[id]/page.tsx` (40 ocurrencias)
  - `frontend/src/components/crm/CounselingDetailSidebar.tsx` (40 ocurrencias)
  - `frontend/src/app/plataforma/crm/newsletter-leads/page.tsx` (38 ocurrencias)
  - `frontend/src/app/plataforma/crm/volunteers/page.tsx` (34 ocurrencias)
  - `frontend/src/components/crm/CrmViews.tsx` (34 ocurrencias)
  - `frontend/src/app/plataforma/crm/settings/templates/page.tsx` (33 ocurrencias)
  - `frontend/src/app/plataforma/crm/messaging/automations/page.tsx` (33 ocurrencias)
  - `frontend/src/app/plataforma/crm/settings/automations/builder/page.tsx` (29 ocurrencias)
  - `frontend/src/app/plataforma/crm/my-card/page.tsx` (27 ocurrencias)
  - `frontend/src/app/plataforma/crm/groups/page.tsx` (25 ocurrencias)
  - `frontend/src/components/crm/PipelineLeadSidebar.tsx` (23 ocurrencias)
  - `frontend/src/app/plataforma/crm/resources/ResourceBankGallery.tsx` (22 ocurrencias)
  - `frontend/src/app/plataforma/crm/tasks/assign/page.tsx` (21 ocurrencias)
- **Patrones Infractores:** Clases como `text-white`, `bg-white`, `bg-black`, `zinc-*`, `gray-*`, `blue-*`, `emerald-*`, `red-*`, y literales hex `dark:bg-[#1E1F21]`, `dark:bg-[#15171c]`.
- **Solución Requerida:** Sustitución exhaustiva por tokens semánticos:
  - Superficies: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--bg-primary))`
  - Bordes: `hsl(var(--border))`
  - Textos: `hsl(var(--foreground))`, `hsl(var(--muted-foreground))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`
  - Estados/Acción: `hsl(var(--primary))`, `hsl(var(--destructive))`, `hsl(var(--success))`

---

### Hallazgo H-CRM-02: Modales Centrados y Paneles Artesanales sin `SidePanel` (Regla Frontend 1)
- **Severidad:** 🔴 **ALTA**
- **Impacto:** Rompe el estándar de experiencia de usuario de la plataforma (Drawers laterales deslizantes en vez de modales invasivos centrados).
- **Ubicaciones Específicas:**
  1. `frontend/src/app/plataforma/crm/settings/templates/page.tsx:148`: Modal centrado clásico `<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">` para crear y editar plantillas.
  2. `frontend/src/app/plataforma/crm/resources/ResourceBankGallery.tsx:121`: Modal flotante centrado `<div className="fixed inset-x-4 top-[5vh] bottom-[5vh] ...">`.
  3. `frontend/src/components/crm/email-builder/HtmlPreview.tsx:15`: Modal flotante centrado `<div className="fixed inset-x-4 top-[5vh] bottom-[5vh] ...">`.
  4. Paneles deslizantes en `resources/page.tsx` (plantillas, categorías, campañas) y en `volunteers/[id]/page.tsx` construidos con divs artesanales `fixed right-0` y backdrops oscuros manuales `bg-black/40` en lugar de usar el componente canónico `@/components/ui/SidePanel`.
- **Solución Requerida:** Migración completa al componente canónico `SidePanel`, garantizando accesibilidad, cierre con Escape/backdrop, animaciones fluidas y consistencia visual.

---

### Hallazgo H-CRM-03: Fricción Operativa en Invocación de Cobertura Pytest
- **Severidad:** 🟡 **MEDIA**
- **Impacto:** En entornos con múltiples usuarios de sistema, el archivo `.coverage` preexistente en la raíz genera `PermissionError: [Errno 13] Permission denied: '/root/ccf/.coverage'` al invocar pytest directamente sin banderas de override.
- **Solución Requerida:** Asegurar que los scripts de prueba (`scripts/test_crm_quality.py`) y llamadas pytest utilicen `-o addopts=` para aislar o desactivar la escritura sobre archivos bloqueados de cobertura.

---

## 5. Plan de Remediación Propuesto para el Módulo CRM

Para llevar al Módulo CRM desde **78.75 (C+)** hasta **100/100 (A+)**, se propone la siguiente secuencia de tickets atómicos:

| Ticket ID | Título del Ticket | Alcance y Archivos Afectados |
| :--- | :--- | :--- |
| `TKT-CRM-REMEDIATION-01` | Migración de Modales Centrados a `SidePanel` Drawers | `settings/templates/page.tsx`, `ResourceBankGallery.tsx`, `HtmlPreview.tsx` y drawers artesanales de `resources/page.tsx`. |
| `TKT-CRM-REMEDIATION-02` | Remediación de Tokens Semánticos en CRM Settings y Recursos | Erradicación de Tailwind hardcodeado en `resources/page.tsx`, `ResourceBankGallery.tsx`, `settings/page.tsx`, `settings/templates/page.tsx`, `settings/automations/builder/page.tsx`. |
| `TKT-CRM-REMEDIATION-03` | Remediación de Tokens Semánticos en CRM Personas y Contactos | Erradicación de Tailwind hardcodeado en `personas/page.tsx`, `personas/[id]/page.tsx`, `contacts/page.tsx`, `contacts/[id]/page.tsx` y `PersonaDetailSidebar.tsx`. |
| `TKT-CRM-REMEDIATION-04` | Remediación de Tokens Semánticos en Consejería, Oraciones y Voluntariado | Erradicación de Tailwind hardcodeado en `counseling/page.tsx`, `CounselingDetailSidebar.tsx`, `prayers/page.tsx`, `volunteers/page.tsx`, `volunteers/[id]/page.tsx`. |
| `TKT-CRM-REMEDIATION-05` | Remediación de Tokens Semánticos en Pipeline, Tareas, Mensajería y Analytics | Erradicación de Tailwind hardcodeado en `pipeline/page.tsx`, `tasks/page.tsx`, `tasks/assign/page.tsx`, `messaging/page.tsx`, `messaging/automations/page.tsx`, `analytics/page.tsx`, `CrmViews.tsx`. |
| `TKT-CRM-FINAL-CERTIFICATION` | Certificación Forense Plena 100/100 A+ y Emisión de Dictamen Final | Verificación exhaustiva 0 hard-deletes, 0 modales, 0 colores Tailwind, 100% apiFetch, 100% tests pasando y cierre formal de auditoría. |

---

## 6. Dictamen Conclusivo de la Auditoría

El Módulo CRM de la Plataforma CCF exhibe una arquitectura de backend ejemplar y robusta en cuanto a los tres axiomas del sistema (Kernel de Personas único, fechas UTC con soft-deletes universales y aislamiento multi-tenant a prueba de fugas IDOR). Su frontend implementa correctamente la política de peticiones HTTP (`apiFetch`).

No obstante, **NO es apto para certificación final en su estado actual** debido a las infracciones de diseño frontend (modales centrados remanentes y 1.512 ocurrencias de colores Tailwind hardcodeados). Se recomienda proceder de inmediato con la ejecución del Plan de Remediación escalonado iniciando con `TKT-CRM-REMEDIATION-01`.

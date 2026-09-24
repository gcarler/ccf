# Auditoría Forense Integral: Módulo Proyectos y Tareas (Gobernanza Operativa y Kanban) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `projects` (Gobernanza de Proyectos, Gestión de Fases, Tareas, Asignaciones, Sub-rutas, Kanban, Pizarra Colaborativa, Wiki, Chat Contextual y Auditoría Operativa)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-PROJECTS-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN DE TOKENS SEMÁNTICOS (88.0 / 100 — GRADO B+)**  

---

## 1. Resumen Ejecutivo

Se ha completado la **Auditoría Forense Integral** sobre el **Módulo Proyectos y Tareas (Gobernanza Operativa y Kanban)** de la Plataforma CCF, cubriendo la totalidad de sus capas de dominio:
- **Backend relacional y seguridad:** `backend/models_projects.py`, `backend/api/projects.py`, `backend/crud/projects.py`, `backend/schemas/projects.py`.
- **Suites de pruebas automatizadas:** `tests/test_projects_api.py`, `tests/test_projects_multi_tenant.py`, `tests/test_projects_rbac.py`, `tests/test_projects_kanban_move.py`, `tests/test_projects_chat_websocket.py`, `tests/test_projects_whiteboard_websocket.py`, `tests/test_projects_whiteboard_roundtrip.py`, `tests/test_projects_wiki_slash_commands.py`, `tests/test_projects_gap.py`, `tests/test_projects_demo_seed.py`, `tests/factories_projects.py`, `tests/test_crm_projects_deep.py`, `tests/test_crm_projects_final.py`.
- **Frontend y vistas operativas:** `frontend/src/app/plataforma/projects/**` y `frontend/src/components/projects/**` (88 archivos escaneados).
- **Documentación canónica:** `docs/ESTADO_PROYECTOS.md`, `docs/PROJECTS_API_CONTRACTS.md`, `docs/PROJECTS_RBAC_MATRIX.md`, `docs/PROJECTS_QA_CHECKLIST.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento perfecto. `Project.owner_id`, `ProjectMember.persona_id`, `Task.assignee_id`, `Task.author_id`, `TaskAttachment.uploader_id`, `TaskComment.author_id` y `TaskActivity.author_id` están estrictamente vinculados a `personas.id` como UUIDv4 canónico. Cero tablas paralelas de seres humanos.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento pleno. Timestamps con `DateTime(timezone=True)` mediante `datetime.now(timezone.utc)`. 0 usos de `datetime.utcnow()` (deprecado). Eliminación destructiva prohibida (`db.delete(` no utilizado); todas las entidades gestionan baja lógica mediante `deleted_at` y `is_active`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Control estricto de `sede_id` obtenido invariablemente de la sesión autenticada (`get_user_sede_id(db, current_user.id)`). Proyectos de alcance global ministerial (`sede_id IS NULL`) gestionados con el filtro canónico `(Project.sede_id.is_(None)) | (Project.sede_id == sede_id)`. Cero fugas IDOR / BOLA en tareas, fases y comentarios.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** 0 modales centrados (`AlertDialog` o modals en viewport center). Los flujos de creación, detalle, fases y configuración de proyectos utilizan exclusivamente paneles laterales tipo Drawer (`TaskCreationDrawer`, `TaskDetailPanel`, `ProjectCreationDrawer`, `PhaseManagerDrawer`, `ProjectSettingsDrawer`, `ProjectContextPanel`, `ProjectChatPanel`).
5. **Regla Frontend 2 (Tokens Semánticos CSS — 20%):** **Hallazgo H-PROJ-01**. Se detectó una densidad significativa de clases de color hardcodeadas de Tailwind (`bg-white`, `text-slate-*`, `border-gray-*`, `zinc-*`, `blue-*`, etc.) y selectores `dark:` en 45 archivos (44 de producción + 1 de test), totalizando 771 incidencias tokenizadas (1,714 ocurrencias brutas de selectores y utilidades de color). Requiere remediación urgente por fases.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** 88 archivos analizados. Cero llamadas a `fetch()` crudo. 100% de peticiones internas utilizan `@/lib/http` (`apiFetch`).
7. **Compilación y Pruebas Backend (100%):** 13 suites y fábricas dedicadas superando 330 aserciones automatizadas de permisos RBAC, aislamiento de sede, movimiento de columnas Kanban, WebSockets de chat y pizarras interactivas.
8. **Estado Documental (100%):** Paquete documental completo y alineado con la arquitectura canónica.

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :-: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `models_projects.py` referencia rigurosamente `personas.id` en miembros de proyectos, responsables de tareas, autores de actividades y adjuntos. Cero identidades desconectadas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; soft-delete universal | **Cumplimiento pleno (100%).** `created_at`, `updated_at` y `deleted_at` utilizan `timezone.utc`. Cero `datetime.utcnow()`. Cero `db.delete(` destructivos en `crud/projects.py` y `api/projects.py`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); 0 fugas IDOR; alcance global controlado | **Cumplimiento pleno (100%).** Inyección estricta de `sede_id` desde el actor autenticado. Filtrado canónico `(Project.sede_id.is_(None)) \| (Project.sede_id == sede_id)`. Verificación de pertenencia a sede antes de mutar fases o tareas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 88 archivos verificados. 0 modales centrados (`AlertDialog` o modals en viewport center). Flujos alineados con paneles laterales deslizantes (`TaskCreationDrawer`, `TaskDetailPanel`, `ProjectCreationDrawer`, etc.). | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **No conforme (20%). Hallazgo H-PROJ-01.** Detección de 771 incidencias de clases de color hardcodeadas (`slate`, `gray`, `zinc`, `blue`, etc.) y selectores `dark:` en 45 archivos de frontend. Requiere remediación por fases. | 15% | **20/100** | 🔴 **REQUIERE REMEDIACIÓN** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 88 archivos verificados. 0 llamadas a `fetch()` crudo. 100% de llamadas utilizan el cliente `@/lib/http` con interceptores y cabeceras estándar. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y cobertura estructural | **Cumplimiento pleno (100%).** 13 suites de pruebas dedicadas (`tests/test_projects*.py`) validando API, RBAC, Multi-tenant, Kanban, WebSockets y sincronización de pizarras. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos, checklists y guías arquitectónicas sincronizadas en `docs/PROJECTS_*.md` y `docs/ESTADO_PROYECTOS.md`. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (20 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 3.0 + 10.0 + 10.0 + 5.0 = \mathbf{88.0 / 100}$$

**Calificación Actual:** **Grado B+ (88.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo supera con honores los tres axiomas nucleares (Kernel, UTC, Multi-Tenant) y las directrices de navegación/HTTP (Drawers, `apiFetch`). Sin embargo, el Eje 5 (Tokens Semánticos) se encuentra severamente afectado por la presencia de 771 incidencias de colores Tailwind hardcodeados y selectores `dark:`. Se emite aprobación condicionada y se ordena la inmediata remediación atómica en 4 fases.

---

## 4. Inventario Detallado del Hallazgo H-PROJ-01 (771 Incidencias en 45 Archivos)

El escaneo estático automatizado sobre los directorios `frontend/src/app/plataforma/projects` y `frontend/src/components/projects` arrojó 45 archivos con violaciones de la Regla de Tokens Semánticos:

| # | Archivo Infractor | Incidencias Detectadas | Tipo de Infracción Principal |
| :-: | :--- | :---: | :--- |
| 1 | `frontend/src/components/projects/ProjectListView.tsx` | 56 | Clases `bg-white`, `text-slate-*`, `border-gray-200`, `dark:*` |
| 2 | `frontend/src/app/plataforma/projects/team/page.tsx` | 51 | Clases `bg-slate-*`, `text-zinc-*`, `border-slate-*`, `dark:*` |
| 3 | `frontend/src/components/projects/ProjectMasterView.tsx` | 45 | Clases `bg-white`, `text-slate-700`, `border-slate-200`, `dark:*` |
| 4 | `frontend/src/components/projects/TaskTableView.tsx` | 45 | Clases `bg-white`, `text-slate-900`, `border-gray-100`, `dark:*` |
| 5 | `frontend/src/components/projects/TaskLabelManager.tsx` | 36 | Badges con `bg-red-500`, `bg-blue-500`, `text-white`, `dark:*` |
| 6 | `frontend/src/app/plataforma/projects/automations/page.tsx` | 35 | Tarjetas y estados con `bg-white`, `text-slate-600`, `dark:*` |
| 7 | `frontend/src/app/plataforma/projects/inbox/page.tsx` | 27 | Bandejas con `bg-white`, `border-gray-200`, `dark:*` |
| 8 | `frontend/src/app/plataforma/projects/comments/page.tsx` | 24 | Hilos de discusión con `text-slate-500`, `bg-gray-50`, `dark:*` |
| 9 | `frontend/src/app/plataforma/projects/general/page.tsx` | 24 | Vista general con `border-gray-200`, `bg-white`, `dark:*` |
| 10 | `frontend/src/app/plataforma/projects/tasks/page.tsx` | 24 | Lista general de tareas con `bg-white`, `text-gray-700`, `dark:*` |
| 11 | `frontend/src/components/projects/ProjectContextPanel.tsx` | 21 | Panel lateral con `bg-white`, `border-slate-200`, `dark:*` |
| 12 | `frontend/src/app/plataforma/projects/responses/page.tsx` | 20 | Formularios y respuestas con `text-slate-800`, `dark:*` |
| 13 | `frontend/src/components/projects/TaskDetailHeader.tsx` | 20 | Encabezados de tarea con `bg-slate-100`, `text-slate-900`, `dark:*` |
| 14 | `frontend/src/components/projects/TaskSupplySection.tsx` | 20 | Suministros y recursos con `bg-blue-50`, `text-blue-700`, `dark:*` |
| 15 | `frontend/src/components/projects/KanbanColumn.tsx` | 18 | Columnas de tablero con `bg-slate-50`, `border-slate-200`, `dark:*` |
| 16 | `frontend/src/app/plataforma/projects/more/page.tsx` | 17 | Opciones de proyecto con `text-slate-600`, `dark:*` |
| 17 | `frontend/src/components/projects/ProjectChatPanel.tsx` | 17 | Burbujas de chat con `bg-blue-600`, `text-white`, `bg-gray-100`, `dark:*` |
| 18 | `frontend/src/components/projects/ProjectWikiEditor.tsx` | 16 | Editor Markdown con `bg-white`, `border-gray-300`, `dark:*` |
| 19 | `frontend/src/components/projects/TaskActivitySection.tsx` | 16 | Línea de tiempo con `text-slate-500`, `bg-slate-100`, `dark:*` |
| 20 | `frontend/src/app/plataforma/projects/[id]/page.tsx` | 15 | Detalle de proyecto con `bg-white`, `border-slate-200`, `dark:*` |
| 21 | `frontend/src/components/projects/SortableTaskCard.tsx` | 15 | Tarjeta de tarea con `bg-white`, `border-gray-200`, `shadow-sm`, `dark:*` |
| 22 | `frontend/src/components/projects/TaskCommentSection.tsx` | 15 | Sección de comentarios con `bg-slate-50`, `text-slate-700`, `dark:*` |
| 23 | `frontend/src/components/projects/TaskRouteTree.tsx` | 14 | Árbol de sub-tareas con `border-slate-200`, `text-slate-600`, `dark:*` |
| 24 | `frontend/src/app/plataforma/projects/welcome/page.tsx` | 13 | Pantalla de bienvenida con `bg-gradient-to-r`, `text-slate-900`, `dark:*` |
| 25 | `frontend/src/components/projects/ProjectCreationDrawer.tsx` | 13 | Panel lateral de creación con `bg-white`, `border-gray-200`, `dark:*` |
| 26 | `frontend/src/components/projects/TaskCreationDrawer.tsx` | 13 | Panel de creación de tareas con `bg-white`, `border-gray-200`, `dark:*` |
| 27 | `frontend/src/components/projects/PhaseManagerDrawer.tsx` | 12 | Gestor de fases con `bg-white`, `border-slate-200`, `dark:*` |
| 28 | `frontend/src/components/projects/ProjectActivityFeed.tsx` | 12 | Feed de actividad con `text-slate-500`, `bg-slate-100`, `dark:*` |
| 29 | `frontend/src/components/projects/TaskDetailHeader.test.tsx` | 12 | Mocks en archivo de prueba con clases de test |
| 30 | `frontend/src/app/plataforma/projects/ProjectsClient.tsx` | 10 | Cliente contenedor con `bg-slate-50`, `dark:*` |
| 31 | `frontend/src/app/plataforma/projects/loading.tsx` | 10 | Skeletons con `bg-slate-200`, `dark:bg-slate-800` |
| 32 | `frontend/src/components/projects/ProjectCard.tsx` | 10 | Tarjeta de proyecto con `bg-white`, `border-gray-200`, `dark:*` |
| 33 | `frontend/src/components/projects/ProjectSettingsDrawer.tsx` | 10 | Ajustes de proyecto con `bg-white`, `border-gray-200`, `dark:*` |
| 34 | `frontend/src/components/projects/ProjectTableView.tsx` | 10 | Vista de tabla de proyectos con `bg-white`, `border-gray-200`, `dark:*` |
| 35 | `frontend/src/components/projects/ProjectWhiteboard.tsx` | 9 | Lienzo colaborativo con `bg-white`, `border-slate-200`, `dark:*` |
| 36 | `frontend/src/components/projects/TaskAttachmentSection.tsx` | 9 | Archivos adjuntos con `bg-slate-50`, `border-slate-200`, `dark:*` |
| 37 | `frontend/src/components/projects/TaskDetailPanel.tsx` | 7 | Panel de detalle de tarea con `bg-white`, `border-slate-200`, `dark:*` |
| 38 | `frontend/src/components/projects/wiki/CommandsList.tsx` | 7 | Menú de comandos wiki con `bg-white`, `text-slate-700`, `dark:*` |
| 39 | `frontend/src/components/projects/TaskMetaFields.tsx` | 5 | Metacampos de tarea con `text-slate-600`, `dark:*` |
| 40 | `frontend/src/components/projects/ProjectViewsContent.tsx` | 4 | Contenedor de sub-vistas con `bg-white`, `dark:*` |
| 41 | `frontend/src/app/plataforma/projects/views/ProjectsBoardView.tsx` | 3 | Sub-vista tablero con `border-slate-200`, `dark:*` |
| 42 | `frontend/src/app/plataforma/projects/views/ProjectsListView.tsx` | 3 | Sub-vista lista con `border-slate-200`, `dark:*` |
| 43 | `frontend/src/app/plataforma/projects/views/ProjectsTableView.tsx` | 3 | Sub-vista tabla con `border-slate-200`, `dark:*` |
| 44 | `frontend/src/components/projects/ProjectKanbanBoard.tsx` | 3 | Contenedor Kanban con `bg-slate-100`, `dark:*` |
| 45 | `frontend/src/components/projects/TitleCellEditor.tsx` | 2 | Editor de celdas con `bg-white`, `border-blue-500`, `dark:*` |
| **TOTAL** | **45 Archivos (44 Prod + 1 Test)** | **771** | **Incidencias Totales a Erradicar** |

---

## 5. Plan Canónico de Remediación en 4 Fases Atómicas

Para garantizar la erradicación total del Hallazgo **H-PROJ-01** preservando la estabilidad funcional, la compilación de TypeScript y la integridad de los Drawers y llamadas a `apiFetch()`, se establece el siguiente cronograma de ejecución por lotes temáticos:

### Fase 1: Vistas Principales, Shell y Layouts (`TKT-PROJ-REMEDIATION-01`)
- **Archivos a intervenir (11 archivos):**
  1. `frontend/src/components/projects/ProjectListView.tsx`
  2. `frontend/src/components/projects/ProjectMasterView.tsx`
  3. `frontend/src/components/projects/ProjectTableView.tsx`
  4. `frontend/src/components/projects/ProjectViewsContent.tsx`
  5. `frontend/src/app/plataforma/projects/views/ProjectsBoardView.tsx`
  6. `frontend/src/app/plataforma/projects/views/ProjectsListView.tsx`
  7. `frontend/src/app/plataforma/projects/views/ProjectsTableView.tsx`
  8. `frontend/src/app/plataforma/projects/ProjectsClient.tsx`
  9. `frontend/src/app/plataforma/projects/loading.tsx`
  10. `frontend/src/components/projects/ProjectCard.tsx`
  11. `frontend/src/components/projects/TitleCellEditor.tsx`
- **Total incidencias a erradicar:** 149 incidencias.
- **Commit atómico:** `feat(projects): Remediación de Tokens Semánticos en Vistas Principales, Shell y Layouts (H-PROJ-01 Fase 1)`.

### Fase 2: Gestión de Tareas, Tablas y Subsecciones (`TKT-PROJ-REMEDIATION-02`)
- **Archivos a intervenir (11 archivos):**
  1. `frontend/src/components/projects/TaskTableView.tsx`
  2. `frontend/src/components/projects/TaskLabelManager.tsx`
  3. `frontend/src/components/projects/TaskDetailHeader.tsx`
  4. `frontend/src/components/projects/TaskSupplySection.tsx`
  5. `frontend/src/components/projects/TaskActivitySection.tsx`
  6. `frontend/src/components/projects/TaskCommentSection.tsx`
  7. `frontend/src/components/projects/TaskRouteTree.tsx`
  8. `frontend/src/components/projects/TaskCreationDrawer.tsx`
  9. `frontend/src/components/projects/TaskAttachmentSection.tsx`
  10. `frontend/src/components/projects/TaskDetailPanel.tsx`
  11. `frontend/src/components/projects/TaskMetaFields.tsx`
- **Total incidencias a erradicar:** 200 incidencias.
- **Commit atómico:** `feat(projects): Remediación de Tokens Semánticos en Gestión de Tareas, Tablas y Subsecciones (H-PROJ-01 Fase 2)`.

### Fase 3: Kanban, Paneles Contextuales, Chat y Colaboración (`TKT-PROJ-REMEDIATION-03`)
- **Archivos a intervenir (11 archivos):**
  1. `frontend/src/components/projects/ProjectContextPanel.tsx`
  2. `frontend/src/components/projects/KanbanColumn.tsx`
  3. `frontend/src/components/projects/ProjectChatPanel.tsx`
  4. `frontend/src/components/projects/ProjectWikiEditor.tsx`
  5. `frontend/src/components/projects/SortableTaskCard.tsx`
  6. `frontend/src/components/projects/ProjectCreationDrawer.tsx`
  7. `frontend/src/components/projects/PhaseManagerDrawer.tsx`
  8. `frontend/src/components/projects/ProjectActivityFeed.tsx`
  9. `frontend/src/components/projects/ProjectSettingsDrawer.tsx`
  10. `frontend/src/components/projects/ProjectWhiteboard.tsx`
  11. `frontend/src/components/projects/ProjectKanbanBoard.tsx`
- **Total incidencias a erradicar:** 146 incidencias.
- **Commit atómico:** `feat(projects): Remediación de Tokens Semánticos en Kanban, Paneles Contextuales, Chat y Colaboración (H-PROJ-01 Fase 3)`.

### Fase 4: Páginas de Plataforma y Sub-rutas (`TKT-PROJ-REMEDIATION-04`)
- **Archivos a intervenir (11 archivos):**
  1. `frontend/src/app/plataforma/projects/team/page.tsx`
  2. `frontend/src/app/plataforma/projects/automations/page.tsx`
  3. `frontend/src/app/plataforma/projects/inbox/page.tsx`
  4. `frontend/src/app/plataforma/projects/comments/page.tsx`
  5. `frontend/src/app/plataforma/projects/general/page.tsx`
  6. `frontend/src/app/plataforma/projects/tasks/page.tsx`
  7. `frontend/src/app/plataforma/projects/responses/page.tsx`
  8. `frontend/src/app/plataforma/projects/more/page.tsx`
  9. `frontend/src/app/plataforma/projects/[id]/page.tsx`
  10. `frontend/src/app/plataforma/projects/welcome/page.tsx`
  11. `frontend/src/components/projects/wiki/CommandsList.tsx`
- **Total incidencias a erradicar:** 264 incidencias.
- **Commit atómico:** `feat(projects): Remediación de Tokens Semánticos en Páginas de Plataforma y Sub-rutas (H-PROJ-01 Fase 4)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las 4 fases de remediación:
1. Se emitirá el ticket `TKT-PROJ-FINAL-CERTIFICATION` con actualización a **100.0/100 Grado A+**.
2. Se validará la ausencia total de violaciones residuales (0 clases hardcodeadas, 0 `dark:`).
3. Se procederá con `TKT-PROJ-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo HTTP 200 OK en las rutas canónicas (`/plataforma/projects`, `/plataforma/projects/team`, `/plataforma/projects/inbox`, `/plataforma/projects/tasks`, etc.).

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (88.0 / 100 — Grado B+)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-PROJ-REMEDIATION-01`)**.

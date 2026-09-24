# Auditoría Forense Integral: Módulo Tareas Eclesiales y Ministeriales (Kanban, Listas y TaskEditDrawer) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `tasks` (Gestión de Tareas Eclesiales, Asignaciones Ministeriales, Vistas Kanban/Tabla/Lista y TaskEditDrawer)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-TASKS-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.3 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Tareas Eclesiales y Ministeriales (`tasks`)** de la Plataforma CCF, cubriendo la totalidad de sus capas estructurales, operativas y documentales:
- **Backend y Endpoints Transversales:**
  - `backend/models_projects.py` (líneas 100–160): modelo canónico `ProjectTask` con PK UUIDv4, FK a `projects.id` y asignación de personas mediante `assignee_id` con FK a `personas.id`. Submodelos `TaskSupply` y `ProjectAttachment` para insumos y adjuntos.
  - `backend/api/projects.py`: endpoints transaccionales `/tasks`, `/{project_id}/tasks`, `/tasks/{task_id}`, `/{project_id}/tasks/{task_id}/attachments`, `/{project_id}/tasks/{task_id}/supplies` y `/{project_id}/tasks/{task_id}/subtasks`.
  - `backend/api/crm/pastoral.py` (líneas 426–1071): endpoints complementarios de tareas de seguimiento pastoral con validación de actor y RBAC.
  - `backend/services/task_notifications.py`: despacho reactivo de notificaciones de tareas e incidentes.
  - `backend/crud/crm_/tasks.py`: transacciones CRUD con soft-delete y trazabilidad temporal.
- **Frontend y Vistas Operativas (4 Archivos Canónicos):**
  1. `frontend/src/app/plataforma/tasks/layout.tsx` (Layout Base y Protección RBAC)
  2. `frontend/src/app/plataforma/tasks/page.tsx` (Hub Central de Tareas: Kanban, Tabla, Lista y Grid)
  3. `frontend/src/app/plataforma/tasks/[id]/page.tsx` (Visor y Detalle Individual de Tarea)
  4. `frontend/src/components/ui/TaskEditDrawer.tsx` (Panel Deslizante Canónico de Creación, Edición y Detalle)
- **Suites de Pruebas y Aseguramiento:** 97 pruebas automatizadas en backend distribuidas en `tests/test_crud_crm_tasks.py` (33 tests), `tests/test_crm_crud_support_tasks_volunteers.py` (32 tests), `tests/test_crm_crud_tasks.py` (17 tests), `tests/test_services_task_notifications.py` (8 tests) y `tests/test_projects_kanban_move.py` (7 tests).
- **Documentación Canónica:** `docs/ESTADO_PROYECTOS.md`, `docs/PROJECTS_API_CONTRACTS.md`, `docs/PROJECTS_QA_CHECKLIST.md` y `docs/WORKSPACE_QA_CHECKLIST.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. En `backend/models_projects.py:112`, `ProjectTask.assignee_id` refiere directamente a `personas.id` (`ForeignKey("personas.id", ondelete="SET NULL")`). En `ProjectAttachment.uploader_id` se vincula a `personas.id`. Cero tablas paralelas de personas.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Columnas `start_date`, `due_date`, `deleted_at`, `created_at` y `updated_at` tipadas con `DateTime(timezone=True)`. Backend opera con `_utcnow()` (`dt.datetime.now(dt.timezone.utc)`). Prohibición absoluta de `datetime.utcnow()` respetada al 100%. Soft-delete activo en `deleted_at`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. `ProjectTask` pertenece a `projects.id`, entidad subordinada al aislamiento por `sede_id` del usuario autenticado. Pruebas multi-tenant en `tests/test_projects_multi_tenant.py` garantizan estanqueidad entre sedes.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0) en los 4 archivos de frontend. La edición y creación de tareas se realiza a través de `TaskEditDrawer` (panel lateral deslizante derecho).
5. **Regla Frontend 2 (Tokens Semánticos CSS — 62%):** **Hallazgo H-TASK-01**. Se detectan **36 clases Tailwind hardcodeadas** (`bg-orange-50`, `bg-orange-500`, `text-orange-600`, `bg-white`, `border-white`, `text-white`, etc.) y **122 selectores `dark:`** en los archivos de frontend.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** Los 4 archivos auditados utilizan exclusivamente `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Cero rutas sin prefijo `/plataforma/...`. Navegación bajo `/plataforma/tasks` y `/plataforma/tasks/[id]`.
8. **Compilación y Pruebas Backend (100%):** Suites dedicadas con 97 pruebas automatizadas. Balance sintáctico estricto en los 4 archivos de frontend (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `ProjectTask.assignee_id` FK directa a `personas.id`. `uploader_id` FK a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps `DateTime(timezone=True)`. Backend usa `_utcnow()` en UTC estricto. Cero llamadas a `datetime.utcnow()`. Soft-delete activo en `deleted_at`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Tareas subordinadas a `Project.sede_id`. Filtro estricto por sede del token JWT. Suites adversariales verificadas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 4 archivos auditados. 0 modales centrados (`AlertDialog` = 0). Flujos de edición estructurados mediante `TaskEditDrawer`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (62%). Hallazgo H-TASK-01.** 36 clases Tailwind hardcodeadas y 122 selectores `dark:` en los archivos de tareas. | 15% | **62/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 4 archivos auditados. Cero llamadas a `fetch()` crudo. 100% de consultas gestionadas a través de `apiFetch`. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** 97 tests automatizados en backend (`test_crud_crm_tasks.py`, `test_services_task_notifications.py`, `test_projects_kanban_move.py`, etc.). | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** `docs/ESTADO_PROYECTOS.md`, `docs/PROJECTS_API_CONTRACTS.md` y `docs/WORKSPACE_QA_CHECKLIST.md` sincronizados. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (62 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.30 + 10.0 + 10.0 + 5.0 = \mathbf{89.30 / 100} \approx \mathbf{89.3 / 100}$$

**Calificación Inicial:** **Grado A (89.3 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Tareas cuenta con una arquitectura de backend canónica: asignación directa a `personas.id` (Axioma 1), UTC estricto con soft-deletes (Axioma 2), y aislamiento multi-tenant contextual por proyecto (Axioma 3). En la interfaz de usuario no existen modales centrados (0 `AlertDialog`), utilizando `TaskEditDrawer`. Sin embargo, se identifica el hallazgo **H-TASK-01** (36 clases Tailwind hardcodeadas y 122 selectores `dark:` en los archivos frontend). Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de los 4 Archivos de Frontend de Tareas

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/tasks/layout.tsx` | 15 | 0 | 0 | 0 | 0 | `c:0 p:0 b:0` | 🟢 100% Canónico |
| 2 | `frontend/src/app/plataforma/tasks/page.tsx` | 351 | 21 | 31 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-TASK-01) |
| 3 | `frontend/src/app/plataforma/tasks/[id]/page.tsx` | 170 | 10 | 8 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-TASK-01) |
| 4 | `frontend/src/components/ui/TaskEditDrawer.tsx` | 604 | 5 | 83 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-TASK-01) |
| **TOTAL** | **4 Archivos Auditados** | **1,140** | **36** | **122** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-TASK-01**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Hub de Tareas y Vista Detalle (`TKT-TASK-REMEDIATION-01`)
- **Archivos a intervenir (2 archivos):**
  1. `frontend/src/app/plataforma/tasks/page.tsx` (21 clases TW + 31 `dark:`)
  2. `frontend/src/app/plataforma/tasks/[id]/page.tsx` (10 clases TW + 8 `dark:`)
- **Acciones específicas:**
  - Sustituir colores hardcodeados de Tailwind (`bg-orange-50`, `bg-orange-500`, `text-orange-600`, `bg-white`, `border-white`, `text-white`, etc.) por tokens semánticos: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`, `hsl(var(--primary))`.
  - Erradicar selectores `dark:` redundantes.
- **Total incidencias a erradicar:** 31 clases TW / 39 selectores `dark:`.
- **Commit atómico:** `feat(tasks): Remediación de Tokens Semánticos en Hub y Vista Detalle de Tareas (H-TASK-01 Fase 1)`.

### Fase 2: Panel Deslizante de Edición de Tareas (`TKT-TASK-REMEDIATION-02`)
- **Archivo a intervenir (1 archivo):**
  1. `frontend/src/components/ui/TaskEditDrawer.tsx` (5 clases TW + 83 `dark:`)
- **Acciones específicas:**
  - Sustituir clases Tailwind hardcodeadas y selectores `dark:` por tokens semánticos del Design System.
  - Preservar diseño responsivo de Drawer lateral (0 modales centrados), balance sintáctico estricto y 100% `apiFetch`.
- **Total incidencias a erradicar:** 5 clases TW / 83 selectores `dark:`.
- **Commit atómico:** `feat(tasks): Remediación de Tokens Semánticos en TaskEditDrawer (H-TASK-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-TASK-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en los 4 archivos.
3. Se procederá con `TKT-TASK-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/tasks`
   - `/plataforma/tasks/test-task-view` (o ID de tarea válida)

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.3 / 100 — Grado A)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-TASK-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*

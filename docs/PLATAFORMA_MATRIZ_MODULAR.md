# Matriz Modular — Plataforma Compartida

## 1. Proposito

Esta matriz traduce la plataforma compartida a reglas operativas por modulo. Responde tres preguntas:

1. que modulo consume cada pieza compartida
2. que smoke minimo debe correr segun el cambio
3. cuando un bug aparente de modulo en realidad pertenece a plataforma

No reemplaza los handovers por modulo. Los conecta.

## 2. Matriz por superficie compartida

| Superficie compartida | Archivos canonicos | Modulos impactados | Validacion minima |
|---|---|---|---|
| Auth v3 | `backend/api/auth_v3.py`, `backend/models_auth.py` | todos los modulos autenticados | `scripts/test_platform_quality.py` + CRM + Projects + Evangelism |
| Permisos / taxonomia | `backend/core/permissions.py`, `backend/core/kernel_rbac.py` | CRM, Academy, Projects, CMS, Messaging, Evangelism, Community, Agenda, Admin | `scripts/test_platform_quality.py` + suites del modulo afectado |
| Admin / asignacion modular | `backend/api/admin.py`, `backend/management/seed_user_permissions.py` | todos los modulos con guards por rol | `scripts/test_platform_quality.py` + `tests/test_permissions_and_more.py` |
| Identidad base persona | `backend/models_kernel.py` | CRM, Auth, Academy, Community, Evangelism, Projects | `scripts/test_platform_quality.py` + suite del modulo que use `personas.id` |
| Cliente HTTP compartido | `frontend/src/lib/http.ts` | todas las rutas `/plataforma/**` | `scripts/test_platform_quality.py` + `cd frontend && npm run build` |
| Shell de workspace | `frontend/src/components/WorkspaceLayout.tsx` | CRM, Projects, Evangelism, Agenda, Academy, CMS, Community, Admin, Support, Inbox | `scripts/test_platform_quality.py` + `cd frontend && npm run build` + check manual de CRM / Projects / Evangelism |
| Grid base AG Grid | `frontend/src/components/ui/TableView.tsx`, `frontend/src/components/ui/UniversalTableView.tsx` | CRM, Projects, Evangelism, Support, Tasks y cualquier modulo que consuma grids base | `scripts/test_platform_quality.py` + `cd frontend && npm run build` + check manual de grids |
| Calendar / Gantt base | `frontend/src/components/ui/UniversalCalendarView.tsx`, `frontend/src/components/ui/UniversalGanttView.tsx` | Projects, Agenda, Academy y vistas temporales futuras | `cd frontend && npm run build` + smoke del modulo afectado |
| Inline editors | `frontend/src/components/ui/inline-editors/*.tsx` | Projects, CRM, Academy y cualquier detalle editable embebido | `cd frontend && npm run build` + smoke del modulo afectado |

## 3. Matriz por modulo consumidor

| Modulo | Handover canonico | Dependencias compartidas prioritarias | Smoke canonico del modulo | Ruta minima a revisar |
|---|---|---|---|---|
| CRM | `docs/ESTADO_CRM.md` | `personas.id`, `apiFetch`, `WorkspaceLayout`, `TableView`, permisos `crm:*` | `scripts/test_crm_quality.py` | `/plataforma/crm/personas` |
| Projects | `docs/ESTADO_PROYECTOS.md` | `WorkspaceLayout`, `UniversalTableView`, `inline-editors`, permisos `projects:*` | `scripts/test_projects_quality.py` | `/plataforma/projects` |
| Evangelism | `docs/ESTADO_EVANGELISMO.md` | `WorkspaceLayout`, `UniversalTableView`, `apiFetch`, permisos `evangelism:*` | `scripts/test_evangelism_quality.py` | `/plataforma/evangelism` |
| Academy | `docs/ESTADO_ACADEMY.md` | `WorkspaceLayout`, `apiFetch`, permisos `academy:*`, `personas.id` | `scripts/test_academy_quality.py` | `/plataforma/academy` |
| CMS | `docs/ESTADO_CMS.md` | `WorkspaceLayout`, `apiFetch`, permisos `cms:*` | `scripts/test_cms_quality.py` | `/plataforma/cms` |
| Messaging / Community | `docs/ESTADO_MESSAGING_COMMUNITY.md` | `WorkspaceLayout`, `apiFetch`, permisos `messaging:*` y `community:*` | `scripts/test_messaging_quality.py` | `/plataforma/community` o `/plataforma/inbox` |
| Agenda / Calendar | `docs/ESTADO_AGENDA.md` | `WorkspaceLayout`, calendar shared, alias `agenda -> spiritual_life` | `scripts/test_agenda_quality.py` | `/plataforma/calendar` o `/plataforma/agenda/events` |
| Plataforma compartida | `docs/ESTADO_PLATAFORMA_COMPARTIDA.md` | auth, RBAC, `apiFetch`, layout, AG Grid, primitives UI | `scripts/test_platform_quality.py` | `/plataforma/admin` o `/plataforma` |

## 4. Regla de decision rapida

Si el bug afecta:

- login, refresh o sesiones: owner `plataforma compartida`
- acceso por rol o menu lateral: owner `plataforma compartida`
- varias pantallas con el mismo grid o editor: owner `plataforma compartida`
- una sola pantalla pero el bug nace en router/schema/CRUD del modulo: owner `modulo`
- una vista CRM/Academy/Evangelism que falla por `personas.id`, token o `apiFetch`: owner `plataforma compartida`

## 5. Gates minimos por tipo de cambio

| Tipo de cambio | Gate obligatorio |
|---|---|
| solo docs de un modulo | smoke canonico rapido del modulo si cambia contrato o checklist operativo |
| docs de plataforma compartida | `scripts/test_platform_quality.py` |
| permisos / RBAC | `scripts/test_platform_quality.py` + `tests/test_permissions_and_more.py` |
| auth / sesiones | `scripts/test_platform_quality.py` |
| `apiFetch` o shell `/plataforma/**` | `scripts/test_platform_quality.py` + `cd frontend && npm run build` |
| AG Grid / `TableView` / `UniversalTableView` | `scripts/test_platform_quality.py` + `cd frontend && npm run build` + check manual CRM / Projects / Evangelism |
| cambio en un modulo sin tocar shared | smoke canonico del modulo |

## 6. Uso obligatorio

Antes de tocar plataforma compartida:

1. leer `docs/ESTADO_PLATAFORMA_COMPARTIDA.md`
2. leer `docs/PLATAFORMA_AUTH_RBAC_API_UI.md`
3. leer `docs/PLATAFORMA_UI_BASE_PROTEGIDA.md`
4. leer esta matriz
5. leer el handover del modulo visible para el usuario final

## 7. Estado

Esta matriz cierra el pendiente operativo de matrices modulares de plataforma compartida el `2026-07-16`.

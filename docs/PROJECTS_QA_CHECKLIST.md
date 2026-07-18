# QA Checklist — Projects

## 1. Antes de tocar código

- Leer `ESTADO_PROYECTOS.md`.
- Leer `PROJECTS_API_CONTRACTS.md`.
- Leer `PROJECTS_RBAC_MATRIX.md` si el cambio toca permisos, guards o visibilidad por rol.
- Clasificar el cambio: `backend projects`, `frontend projects`, `RBAC`, `Axioma 3`, `shared UI`, `platform`.
- Si toca `TableView`, `UniversalCalendarView`, `WorkspaceLayout`, `apiFetch` o permisos base, tratarlo como plataforma compartida.

## 2. Smoke canónico

```bash
cd /root/ccf
./venv/bin/python scripts/test_projects_quality.py
```

## 3. Validación ampliada según cambio

### Si toca API o contratos

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_projects_api.py \
  tests/test_projects_multi_tenant.py \
  tests/test_projects_rbac.py
```

### Si toca sincronización entre vistas

```bash
cd /root/ccf/frontend
npx vitest run src/lib/__tests__/projects-views-integration.test.tsx
```

### Si toca hook compartido

```bash
cd /root/ccf/frontend
npx vitest run src/lib/__tests__/useProjectTasks.test.tsx
```

### Smoke frontend dedicado

```bash
cd /root/ccf/frontend
npm run test:e2e:projects
npm run test:e2e:projects:detail
```

Nota operativa:

- `test:e2e:projects:detail` levanta el frontend con `webServer` administrado por Playwright.
- `test:e2e:projects` ejecuta primero el smoke modular normal y luego la cobertura seeded del detalle sobre ese runner administrado.

## 4. Checks manuales obligatorios

- `/plataforma/projects` lista proyectos sin errores de consola.
- `/plataforma/projects/[id]` carga dashboard, tabla, kanban, calendar, gantt y wiki sin perder estado.
- crear tarea desde una vista aparece en las otras vistas sin recarga.
- cambiar fases no deja tareas huérfanas.
- inbox de proyectos responde y `mark read` funciona.
- `Editor` puede mutar donde aplica y sigue bloqueado en `DELETE /projects/{id}` (política confirmada: requiere `academy:manage`).

## 5. No aprobar si pasa esto

- fuga cross-sede de proyecto, tarea o comentario
- `Miembro` gana acceso sin decisión explícita de RBAC
- `status` de tarea queda fuera del set de fases del proyecto
- una vista muta localmente sin pasar por `useProjectTasks` / `ProjectUpdateContext`
- cambios en `/projects/inbox` sin revalidar `tests/test_projects_rbac.py`
- aceptar persistencia de tarea o proyecto con `title=""` (o solo whitespace)
- aceptar items de `/projects/inbox` de proyectos soft-deleted, o upsert ciego ante `item_id` arbitrario en `/inbox/{item_id}/read`

## 6. Superficies sensibles

- `backend/api/projects.py`
- `frontend/src/app/plataforma/projects/[id]/page.tsx`
- `frontend/src/hooks/useProjectTasks.ts`
- `frontend/src/context/ProjectUpdateContext.tsx`
- `frontend/src/components/projects/PhaseManagerDrawer.tsx`
- `frontend/src/components/projects/ProjectViewsContent.tsx`

## 7. Deuda documentada que sigue viva

- ~~asimetría `DELETE /projects/{id}` vs `PATCH /projects/{id}`~~ → resuelta como **política confirmada** el 2026-07-16 (ver `PROJECTS_RBAC_MATRIX.md` §6.1 y `PROJECTS_API_CONTRACTS.md` §11)
- ~~gap RBAC de `PUT /projects/{id}/phases`~~ → cerrado el 2026-07-16 y reforzado el 2026-07-17; el guard es `require_project_access("manage")`, `Editor` recibe 403 para proyecto existente en su sede y 404 para project_id inexistente/cross-sede (Axioma 3). Ver `PROJECTS_RBAC_MATRIX.md` §4.2 y §10.2
- la matriz compacta vive en `docs/PROJECTS_RBAC_MATRIX.md` y debe mantenerse sincronizada con `tests/test_projects_rbac.py`
- `PEND-FRONTEND-E2E-PROJECTS-001` cerrada el 2026-07-16 con `frontend/tests/e2e/projects/smoke.spec.ts`
- `PEND-FRONTEND-E2E-PROJECTS-DETAIL-001` cerrada el 2026-07-16 con `frontend/tests/e2e/projects/detail.spec.ts`

# QA Checklist — Projects

## 1. Antes de tocar código

- Leer `ESTADO_PROYECTOS.md`.
- Leer `PROJECTS_API_CONTRACTS.md`.
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

## 4. Checks manuales obligatorios

- `/plataforma/projects` lista proyectos sin errores de consola.
- `/plataforma/projects/[id]` carga dashboard, tabla, kanban, calendar, gantt y wiki sin perder estado.
- crear tarea desde una vista aparece en las otras vistas sin recarga.
- cambiar fases no deja tareas huérfanas.
- inbox de proyectos responde y `mark read` funciona.
- `Editor` puede mutar donde aplica y sigue bloqueado en `DELETE /projects/{id}` mientras el gap siga abierto.

## 5. No aprobar si pasa esto

- fuga cross-sede de proyecto, tarea o comentario
- `Miembro` gana acceso sin decisión explícita de RBAC
- `status` de tarea queda fuera del set de fases del proyecto
- una vista muta localmente sin pasar por `useProjectTasks` / `ProjectUpdateContext`
- cambios en `/projects/inbox` sin revalidar `tests/test_projects_rbac.py`

## 6. Superficies sensibles

- `backend/api/projects.py`
- `frontend/src/app/plataforma/projects/[id]/page.tsx`
- `frontend/src/hooks/useProjectTasks.ts`
- `frontend/src/context/ProjectUpdateContext.tsx`
- `frontend/src/components/projects/PhaseManagerDrawer.tsx`
- `frontend/src/components/projects/ProjectViewsContent.tsx`

## 7. Deuda documentada que sigue viva

- asimetría `DELETE /projects/{id}` vs `PATCH /projects/{id}`
- gap RBAC de `PUT /projects/{id}/phases`
- falta una matriz RBAC compacta separada del handover

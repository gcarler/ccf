# QA Checklist — CRM CCF

> **Objetivo:** validar CRM como módulo aislado antes de cerrar una tarea, commit o despliegue.

## 1. Preflight

```bash
cd /root/ccf
git status --short
python3 --version && node --version
grep -nE "PARCIAL-|PEND-" docs/ESTADO_CRM.md
```

Confirmar:

- La ruta afectada está identificada.
- El rol/usuario con el que se prueba está claro.
- La matriz a usar quedó identificada en `docs/CRM_RBAC_MATRIX.md`.
- Si el cambio toca `Persona`, auth, permisos, `apiFetch` o componentes UI base, se trata como cambio de plataforma.

## 2. Smoke mínimo backend

Smoke canonico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_crm_quality.py
```

Smoke mínimo bruto:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_domain.py \
  tests/test_crm_sede_isolation.py \
  tests/test_crm_runtime_security.py
```

Usarlo siempre que se toque:

- `backend/api/crm/**`
- `backend/models_crm.py`
- `backend/models_crm_pipeline.py`
- `backend/crud/crm*`

## 3. Smoke ampliado backend

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_crm_persona_mentorship.py \
  tests/test_crm_resource_bank.py \
  tests/test_crm_automations_dag.py \
  tests/test_crm_concurrency_adversarial.py
```

Ejecutar si se toca:

- mentoría
- resource bank / plantillas
- automations / flow builder
- reorder / kanban / concurrencia

## 4. Frontend

No existe todavía suite e2e dedicada de CRM.

Hasta que exista `PEND-FRONTEND-E2E-CRM-001`, hacer QA manual con consola abierta sobre:

| Ruta | Validar |
|---|---|
| `/plataforma/crm` | dashboard carga, sin 401/404/500 |
| `/plataforma/crm/personas` | listado, filtros, paginación, búsqueda |
| `/plataforma/crm/personas/{id}` | detalle, timeline, mentoría |
| `/plataforma/crm/pipeline` | columnas, cards, reorder, carga inicial |
| `/plataforma/crm/tasks` | listado y actualización |
| `/plataforma/crm/counseling` | tickets y detalle |
| `/plataforma/crm/resources` | plantillas, categorías, bitácora |
| `/plataforma/crm/volunteers` | listado y edición |
| `/plataforma/crm/groups` | contrato cruzado con grupos |

## 5. Consola del navegador

No cerrar tarea si aparece:

- `401 Unauthorized` no explicado por el rol
- `403 Forbidden` en acción que el rol sí debe poder hacer
- `404 Not Found` en assets `_next/static`
- `404 Not Found` en endpoints existentes
- `500 Internal Server Error`
- errores AG Grid
- errores de hidratación React
- `TypeError` por response shape inesperada

## 6. Network/API

Para cada endpoint tocado:

- request sale por `/api/crm` o `/dashboard/crm` si aplica
- token presente cuando es ruta privada
- `persona_id`, `case_id`, `pipeline_id`, `task_id` son UUID string
- cross-sede devuelve `404` donde ese es el contrato
- la respuesta coincide con `docs/CRM_API_CONTRACTS.md`

## 7. Casos funcionales mínimos

### Personas

- listar personas
- abrir detalle de una persona
- editar un campo permitido
- validar timeline / donations / mentor candidates

### Pipeline

- listar pipelines
- abrir kanban
- mover caso de etapa si el flujo lo permite
- validar que el reorder no produce error de scope

### Counseling y tasks

- abrir ticket
- crear o actualizar tarea
- validar `tasks/mine`

### Recursos

- listar plantillas
- crear o editar plantilla
- revisar bitácora o campaña si el cambio toca envíos

## 8. Roles mínimos

Validar al menos:

| Rol | Esperado |
|---|---|
| ADMIN | acceso completo |
| GESTOR/EDITOR | acceso operativo según contrato real |
| MIEMBRO | no debe acceder a administración CRM |

Notas obligatorias:

- revisar `docs/CRM_RBAC_MATRIX.md` antes de tocar pipeline o automations
- recordar que pipeline/kanban no usa el mismo guard que personas/resources
- si se toca `backend/api/crm/pipelines.py`, validar también helpers sin auth explícita documentados en la matriz

## 9. Criterio de cierre

Una tarea de CRM queda cerrada cuando:

- smoke backend relevante pasa
- rutas afectadas fueron probadas manualmente
- consola no presenta errores nuevos
- si el cambio altera contratos, `CRM_API_CONTRACTS.md` se actualiza
- si cambia estado o backlog, `ESTADO_CRM.md` se actualiza
- el commit incluye solo la unidad trabajada

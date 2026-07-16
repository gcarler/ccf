# QA Checklist — Academy CCF

> **Objetivo:** validar Academy como módulo aislado antes de cerrar una tarea, commit o despliegue.

## 1. Preflight

```bash
cd /root/ccf
git status --short
python3 --version && node --version
grep -nE "PARCIAL-|PEND-" docs/ESTADO_ACADEMY.md
```

Confirmar:

- ruta afectada identificada
- rol real de prueba identificado
- si el cambio toca auth, personas, permisos o storage, tratarlo como cambio de plataforma

## 2. Smoke canónico

```bash
cd /root/ccf
./venv/bin/python scripts/test_academy_quality.py
```

## 3. Smoke mínimo bruto

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_academy_api.py tests/test_academy_domain.py
```

Usarlo siempre que se toque:

- `backend/api/academy.py`
- `backend/crud/academy.py`
- `backend/models_academy_core.py`
- `backend/schemas/academy.py`

## 4. Frontend

No existe todavía suite e2e dedicada de Academy.

Hasta que exista `PEND-FRONTEND-E2E-ACADEMY-001`, hacer QA manual con consola abierta sobre:

| Ruta | Validar |
|---|---|
| `/plataforma/academy` | dashboard carga sin 401/404/500 |
| `/plataforma/academy/courses` | listado de cursos |
| `/plataforma/academy/courses/{id}` | detalle de curso |
| `/plataforma/academy/course/{id}` | verificar coexistencia de rutas |
| `/plataforma/academy/curriculum` | navegación de malla |
| `/plataforma/academy/forum` | listado de hilos |
| `/plataforma/academy/certificates` | listado y validación |
| `/plataforma/academy/coordination` | panel admin |
| `/plataforma/academy/profile` | perfil y progreso |

## 5. Consola del navegador

No cerrar tarea si aparece:

- `401 Unauthorized` no explicado por rol
- `403 Forbidden` en acción que el rol sí debe ejecutar
- `404 Not Found` en `_next/static`
- `404 Not Found` en endpoints existentes
- `500 Internal Server Error`
- errores de hidratación React
- `TypeError` por shape de response

## 6. Network/API

Para cada endpoint tocado:

- sale por `/api/academy` o `/dashboard/academy`
- token presente si es ruta privada
- ids son UUID string
- student operations actúan solo sobre la propia persona o matrícula
- scope por sede se respeta en cursos, forum y grading admin

## 7. Casos funcionales mínimos

### Alumno

- listar cursos
- matricularse en un curso propio
- actualizar progreso de una lección
- leer perfil `/me/profile`

### Foro

- crear o listar hilo
- validar que no haya fuga cross-sede de hilos por curso
- validar visibilidad de hilos globales

### Admin

- crear o editar curso
- revisar submissions
- calificar submission válida
- bloquear grading cross-sede

## 8. Roles mínimos

| Rol | Esperado |
|---|---|
| ADMIN | acceso completo |
| `LECTOR` | `academy:study`, solo su propia operación |
| EDITOR/GESTOR | según permisos efectivos `academy:edit/manage` |

Pendiente formal:

- `PEND-RBAC-ACADEMY-001`

## 9. Criterio de cierre

Una tarea de Academy queda cerrada cuando:

- smoke backend relevante pasa
- rutas afectadas se probaron manualmente
- consola no muestra errores nuevos
- si cambia contrato, `ACADEMY_API_CONTRACTS.md` se actualiza
- si cambia estado o backlog, `ESTADO_ACADEMY.md` se actualiza

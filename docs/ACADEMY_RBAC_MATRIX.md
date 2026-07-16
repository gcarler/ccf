# Matriz RBAC — Academy CCF

## 1. Proposito

Este documento fija la matriz RBAC operativa de Academy contra el código actual. Documenta guards reales, ownership del estudiante y las dos capas de autorización que hoy conviven:

- permisos granulares (`academy:*`)
- fallback por `role` normalizado dentro de `require_permission(...)`

## 2. Fuente de verdad inspeccionada

- `backend/api/academy.py`
- `backend/core/permissions.py`
- `backend/management/seed_user_permissions.py`
- `tests/test_academy_api.py`
- `tests/test_academy_domain.py`

Fecha de lectura: `2026-07-16`

## 3. Niveles canónicos de Academy

Permisos canónicos:

- `academy:read`
- `academy:study`
- `academy:edit`
- `academy:manage`

Jerarquía efectiva:

- `academy:manage` incluye `academy:edit`, `academy:read` y `academy:study`
- `academy:edit` incluye `academy:read`
- `academy:study` es paralelo al camino del estudiante

Observación:

- Academy usa aliases consistentes en `backend/api/academy.py`:
  - `AcademyReader`
  - `AcademyStudent`
  - `AcademyEditor`
  - `AcademyManager`

## 4. Capas reales de autorización

### 4.1. Roles persistidos sembrados (`RolPlataforma`)

Contrato observado en `seed_user_permissions.py`:

| Rol | Academy efectivo esperado |
|---|---|
| `ADMINISTRADOR` | `academy:manage` |
| `GESTOR` | `academy:manage` |
| `EDITOR` | `academy:read` |
| `LECTOR` | `academy:read` |
| `MIEMBRO` | `academy:study` |

Observación:

- `EDITOR` persistido no recibe `academy:edit` en seed; recibe `academy:read`
- `GESTOR` sí recibe `academy:manage`

### 4.2. Fallback runtime (`DEFAULT_ROLES`)

Contrato observado en `permissions.py`:

| Rol fallback | Academy efectivo esperado |
|---|---|
| `Administrador` | `academy:manage` |
| `Gestor` | `academy:manage` |
| `Editor` | `academy:edit` |
| `Lector` | `academy:study` |
| `Miembro` | `academy:study` |
| `Estudiante` | `academy:study` |
| `Aspirante` | `academy:study` |

Asimetrías relevantes:

- seed persistido: `EDITOR` queda en `academy:read`
- fallback runtime: `Editor` queda en `academy:edit`
- seed persistido: `LECTOR` queda en `academy:read`
- fallback runtime: `Lector` queda en `academy:study`

Academy no tiene una sola matriz trivial; depende de si el usuario resuelve por permisos sembrados o por fallback/role normalization.

### 4.3. Allowance adicional por role normalizado

`require_permission(...)` agrega bypass por `role` normalizado:

| Permiso pedido | Roles que pasan por fallback de role |
|---|---|
| `academy:read` | `coordinador`, `docente`, `pastor`, `estudiante`, `lector`, `miembro`, `aspirante` |
| `academy:study` | `coordinador`, `docente`, `pastor`, `estudiante`, `lector`, `miembro`, `aspirante` |
| `academy:edit` | `coordinador`, `docente`, `pastor` |
| `academy:manage` | `coordinador`, `pastor` |

Esto significa:

- un `LECTOR` o `MIEMBRO` puede pasar student/read flows aunque no tenga `academy:read` granular explícito
- un `docente` puede pasar `academy:edit` aunque no tenga permiso granular persistido
- un `coordinador` puede pasar `academy:manage` por role fallback

## 5. Matriz por superficie Academy

| Superficie | Guard observado | Roles que pasan hoy |
|---|---|---|
| Listado y detalle de cursos publicados | `AcademyReader` | admin/gestor/editor/lector persistido; además roles legacy permitidos por fallback de `academy:read` |
| Lessons y assessments visibles al estudiante | `AcademyReader` o `AcademyStudent` según endpoint | estudiantes con `study`, lectores, miembros y roles docentes/coordinación según fallback |
| Submit assessment, progress, enrollments propios, `me/*`, forum, schedule, submit-assignment | `AcademyStudent` | cualquier rol con `academy:study` o role fallback equivalente |
| `/enrollments` listado global, `/personas`, dashboard metrics, pilot readiness | `AcademyManager` | `ADMINISTRADOR`, `GESTOR`; además `coordinador` y `pastor` por role fallback |
| grading submissions, create/update course, lessons, assessments, students por curso | `AcademyEditor` | `ADMINISTRADOR`, `GESTOR`; `Editor` fallback; `docente`/`coordinador`/`pastor` por role fallback |
| delete course | `AcademyManager` | `ADMINISTRADOR`, `GESTOR`; `coordinador`/`pastor` por role fallback |

## 6. Ownership del estudiante

Aunque el RBAC permita entrar al endpoint, varias rutas tienen una segunda barrera obligatoria por ownership:

- `POST /enrollments` exige `payload.persona_id == current_user.id`
- `POST /assessments/{assessment_id}/submit` exige matrícula propia
- `GET/POST /lessons/{lesson_id}/progress` trabaja sobre `persona_id == current_user.id`
- `POST /enrollments/{enrollment_id}/check-in` usa `_get_own_enrollment(...)`
- `POST /enrollments/{enrollment_id}/request-certificate` usa `_get_own_enrollment(...)`
- `POST /lessons/{lesson_id}/submit-assignment` usa `_get_own_enrollment(...)`

Conclusión:

- Academy no se protege solo por permiso; se protege también por ownership explícito de inscripción/persona

## 7. Aislamiento por sede

Superficies con filtro de sede observable:

- `_course_scope(...)` para courses/lessons/assessments/schedule/dashboard
- forum con threads globales (`course_id IS NULL`) visibles cross-sede por diseño
- grading y submissions admin con join a `Course`
- `/personas` limitado por `Persona.sede_id`

Esto afecta la lectura RBAC:

- un rol puede tener permiso suficiente y aun así recibir `404` o vacío por scope de sede

## 8. Riesgos y drift documentados

1. `EDITOR` no es igual en seed persistido y en fallback runtime.
2. `LECTOR` tampoco es igual: seed persistido lo deja en `academy:read`, fallback lo deja en `academy:study`.
3. parte de Academy se comporta más como módulo estudiantil que como CRUD estándar, porque ownership manda tanto como el permiso.
4. dashboard admin y operations admin mezclan `AcademyManager` y `AcademyEditor`; cualquier cambio ahí exige revalidar rol por rol.

## 9. Reglas operativas para QA

Validar mínimo:

1. `ADMINISTRADOR` entra a toda la superficie
2. `GESTOR` entra a read/study/edit/manage de Academy
3. `LECTOR` o `MIEMBRO` pueden operar solo su camino estudiantil
4. `EDITOR` debe revisarse con cuidado porque seed persistido y fallback runtime no son equivalentes
5. admin flows de courses/submissions/dashboard deben probarse aparte de student flows

## 10. Estado

- `PEND-RBAC-ACADEMY-001` queda cerrada el `2026-07-16` como documentación del contrato actual
- permanece drift visible entre seed persistido, fallback runtime y role normalization

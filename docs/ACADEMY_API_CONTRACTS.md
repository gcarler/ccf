# Contratos API — Academy CCF

> **Objetivo:** fijar el contrato operativo de `/api/academy` para backend, frontend, tests y agentes.

## 1. Reglas generales

- Prefijo backend: `/api/academy`
- Prefijo frontend plataforma: `apiFetch('/academy/...')`
- Dashboard principal frontend: `/dashboard/academy`
- Identidad del estudiante: `personas.id` UUID
- `auth_users.id == personas.id`
- Scope de cursos y operaciones protegidas por `sede_id`
- No devolver ORM crudo cuando el contrato exige estructura serializada

## 2. Permisos Academy

Aliases usados en `backend/api/academy.py`:

| Alias | Permiso |
|---|---|
| `AcademyReader` | `academy:read` |
| `AcademyStudent` | `academy:study` |
| `AcademyEditor` | `academy:edit` |
| `AcademyManager` | `academy:manage` |

Regla:

- operaciones del estudiante deben quedar limitadas a su propia persona y sus propias matrículas

## 3. Courses y lessons

Rutas:

| Metodo | Ruta |
|---|---|
| `GET` | `/courses` |
| `GET` | `/courses/{course_id}` |
| `GET` | `/courses/{course_id}/lessons` |
| `GET` | `/courses/{course_id}/assessments` |

Reglas:

- `course_id` es UUID string
- `_course_scope(...)` aplica `sede_id`
- si el curso no está publicado, solo `edit/manage` puede verlo

## 4. Assessments y progreso

Rutas:

| Metodo | Ruta |
|---|---|
| `GET` | `/assessments/{assessment_id}` |
| `POST` | `/assessments/{assessment_id}/submit` |
| `GET` | `/lessons/{lesson_id}/progress` |
| `POST` | `/lessons/{lesson_id}/progress` |

Reglas:

- un estudiante solo puede reportar progreso propio
- la evaluación debe pertenecer a un curso del scope visible

## 5. Enrollments, profile y certificates

Rutas:

| Metodo | Ruta |
|---|---|
| `POST` | `/enrollments` |
| `GET` | `/me/enrollments` |
| `GET` | `/enrollments` |
| `POST` | `/enrollments/{enrollment_id}/check-in` |
| `GET` | `/me/progress` |
| `GET` | `/me/profile` |
| `GET` | `/me/certificates` |
| `POST` | `/enrollments/{enrollment_id}/request-certificate` |
| `GET` | `/certificates/validate/{code}` |

Reglas:

- `LECTOR` puede matricularse y actualizar su propio progreso
- un estudiante no puede matricular otra persona
- `create_enrollment` debe impedir duplicados y reactivar registros archivados

## 6. Assignments, forum y schedule

Rutas:

| Metodo | Ruta |
|---|---|
| `POST` | `/lessons/{lesson_id}/submit-assignment` |
| `GET/POST` | `/forum/threads` |
| `GET` | `/schedule` |
| `GET` | `/personas` |

Reglas:

- forum debe aislar por sede los hilos asociados a curso
- hilos globales `course_id IS NULL` siguen visibles cross-sede por diseño
- hilos de cursos soft-deleted deben quedar ocultos

## 7. Dashboard Academy

Rutas:

| Metodo | Ruta |
|---|---|
| `GET` | `/dashboard/metrics` |
| `GET` | `/dashboard/pilot-readiness` |

La UI principal consume además:

| Metodo | Ruta |
|---|---|
| `GET` | `/dashboard/academy` |

Pendiente:

- consolidar contrato operativo del dashboard frontend
- ID: `PARCIAL-DASHBOARD-CONTRACT-ACADEMY-001`

## 8. Admin Academy

Rutas:

| Metodo | Ruta |
|---|---|
| `GET` | `/admin/submissions` |
| `PATCH` | `/admin/submissions/{submission_id}/grade` |
| `POST` | `/admin/courses` |
| `PATCH/DELETE` | `/admin/courses/{course_id}` |
| `GET` | `/admin/courses/{course_id}/students` |
| `POST` | `/admin/courses/{course_id}/lessons` |
| `PATCH/DELETE` | `/admin/lessons/{lesson_id}` |
| `POST` | `/admin/assessments` |
| `PATCH` | `/admin/assessments/{assessment_id}` |

Reglas:

- grading debe bloquear cross-sede
- uploads deben pasar por `sanitize_filename` y storage controlado
- operaciones admin requieren `academy:edit` o `academy:manage`

## 9. Códigos esperados

| Codigo | Uso |
|---|---|
| `200/201/204` | operación exitosa |
| `400` | input inválido o regla de negocio |
| `401` | sin autenticación |
| `403` | autenticado pero sin permiso o intentando operar otra persona |
| `404` | recurso inexistente o fuera del scope válido |

## 10. Validación mínima

```bash
cd /root/ccf
./venv/bin/python scripts/test_academy_quality.py
```

Validación mínima bruta:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_academy_api.py tests/test_academy_domain.py
```

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

Referencia RBAC:

- `docs/ACADEMY_RBAC_MATRIX.md`

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

Shape operativa actual:

- `cards: MetricCard[]`
- `enrollment_trends: ChartDataPoint[]`
- `top_courses: {title: str, count: int}[]`
- `grade_distribution: ChartDataPoint[]`
- `at_risk_students_count: int`
- `filters?: DashboardFilter[]`
- `geo_data?: GeoBucket[]`
- `last_updated?: iso datetime`

Reglas:

- el endpoint real vive en `/api/dashboard/academy`, no bajo `/api/academy`
- `AcademyClient.tsx` consume `cards`, `enrollment_trends` y `top_courses`; cambios de shape deben pasar por `AcademyDashboard`
- `/api/academy/dashboard/metrics` y `/api/academy/dashboard/pilot-readiness` siguen siendo endpoints internos del módulo Academy, no sustituyen el contrato del dashboard visual raíz

Estado:

- `PARCIAL-DASHBOARD-CONTRACT-ACADEMY-001` queda documentada el `2026-07-16`; el contrato visual ya no depende de supuestos implícitos

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

## 11. Notas RBAC actuales

- `AcademyReader`, `AcademyStudent`, `AcademyEditor` y `AcademyManager` sí están usados de forma consistente en el router.
- además del permiso granular existe fallback por `role` normalizado dentro de `require_permission(...)`
- student flows combinan RBAC con ownership estricto sobre `persona_id` o `enrollment_id`
- ver `ACADEMY_RBAC_MATRIX.md` para las asimetrías entre seed persistido, `DEFAULT_ROLES` y role fallback

---

## 12. Hallazgos auditoría API 2026-07-18

Actualización derivada de la auditoría contra el código vigente. IDs referencia en `ESTADO_ACADEMY.md §15`.

### 12.1. Desconexión dashboard frontend ↔ backend (`ACAD-CRIT-002`)

**Síntoma.** `AcademyClient.tsx` consume `GET /dashboard/academy` y espera los campos:

- `cards: MetricCard[]`
- `enrollment_trends: ChartDataPoint[]`
- `top_courses: {title: str, count: int}[]`

**Realidad backend.** `GET /academy/dashboard/metrics` solo retorna:

- `active_students`, `completion_rate`, `certificates_issued`
- `total_courses`, `total_enrollments`, `completed_enrollments`
- `cards` con solo 3 entradas

**Consecuencia:** `dashboard.enrollment_trends` y `dashboard.top_courses` son `undefined` en cliente. `dashboard?.top_courses.map(...)` produce excepción silenciosa → sección "Cursos Top Performance" queda vacía o rompe render.

**Fix propuesto:**

1. Extender `GET /academy/dashboard/metrics` para retornar `enrollment_trends` y `top_courses` (GROUP BY por mes y por curso).
2. O, alternativamente, cambiar `AcademyClient.tsx` para consumir solo `cards` y diseñar gráfico "Top Performance" aparte.

Commit recomendado: front + back coordinados.

### 12.2. Endpoints faltantes detectados (`MED-002`, `MED-003`, `MED-004`)

| Recurso | Modelo | CRUD disponible | Acción pendiente |
|---|---|---|---|
| `ForumComment` | existe en `models_academy_core.py:171` | ninguno | Crear router con `GET/POST/DELETE`; respetar threading anidado (`parent_id`) |
| `Resource` | existe (Recursos por lección) | ninguno directo | Crear `POST /lessons/{id}/resources` y `DELETE /resources/{id}` usando `storage_service` |
| `ForumThread` (categoría) | columna `category` existe | ningún filtro | Aceptar `category` como query param en `GET /forum/threads` |
| `AssignmentSubmission` | existe | sin DELETE | Crear `DELETE /admin/submissions/{id}` con soft delete |
| `ForumThread.is_resolved` | existe | sin PATCH | Crear `PATCH /forum/threads/{id}/resolve` para `Editor/Manager` |

### 12.3. Mismatch de IDs en cliente (`ACAD-CRIT-001`)

`CourseCatalog.tsx:38-46` declara `Course.id: number` y `enrolledCourseIds?: number[]`. Backend retorna UUID string (modelo `Course` PK = `UUID(as_uuid=True)`). Misma tensión en cualquier consumo con `Assignments.postBased` o comparaciones `.includes(...)`.

**Acción.** Fijar tipos compartidos en `frontend/src/types/academy.ts` (crear) y propagar.

### 12.4. URL/payload redundante en `submit_assessment` (`ACAD-LOW-002`)

El cliente envía `enrollment_id` en el body (`AssessmentDrawer.tsx:79`). El backend ignora ese campo y lo deduce desde `current_user.id`. Inocuo pero confuso.

**Acción.** Normalizar: aceptar `enrollment_id` opcional y derivar siempre del usuario autenticado.

### 12.5. Forma del contrato de respuesta esperada (propuesta)

```ts
type AcademyDashboard = {
  cards: MetricCard[],
  enrollment_trends: ChartDataPoint[],    // zona horaria UTC
  top_courses: { title: string, count: number }[],
  completion_rate?: number,
  at_risk_students_count?: number,
  filters?: DashboardFilter[],
  geo_data?: GeoBucket[],
  last_updated?: string                  // ISO 8601
};
```

Si se opta por la ruta (2) de `ACAD-CRIT-002`, este shape es el que el cliente asume y debe aparecer en el endpoint.

### 12.6. Códigos esperados a verificar en QA

| Código | Escena | Verificación adicional |
|---|---|---|
| `403` | `POST /enrollments` con `persona_id != current_user.id` | Verificar mensaje exacto |
| `403` | `POST /lessons/{id}/submit-assignment` sin enrollment propio | Verificar mensaje exacto |
| `403` | `POST /assessments/{id}/submit` sin enrollment propio | Verificar mensaje exacto |
| `403` | `POST /forum/threads` con `course_id=None` por Student sin `edit` | Caso del fix `ACAD-MED-001` |
| `404` | `_course_scope` con curso de otra sede | Caso Axioma 3 ya cubierto |
| `404` | `_get_own_enrollment` con enrollment de otro usuario | Caso ownership ya cubierto |

### 12.7. Reglas de scope para nuevos endpoints

Cualquier endpoint nuevo en este módulo debe:

1. Usar `_course_scope` o equivalente para cursos.
2. Verificar ownership en rutas `/me/*` y `/enrollments/{id}/*`.
3. Devolver error tipado cuando el usuario intenta actuar sobre una sede ajena (no leak con existence-leak en `404`).
4. Registrar `AcademyActivityLog` cuando la acción sea material (matricular, entregar, certificar).

### 12.8. Estado de contratos

| Contrato | Estado | Última revisión |
|---|---|---|
| `/api/academy/courses` | Estable | 2026-07-16 |
| `/api/academy/me/*` | Estable | 2026-07-16 |
| `/api/academy/admin/*` | Estable | 2026-07-16 |
| `/api/academy/forum/threads` | Pendiente fix `ACAD-MED-001` y `ACAD-MED-002` | 2026-07-18 |
| `/api/academy/dashboard/metrics` | Pendiente fix `ACAD-CRIT-002` (extender shape) | 2026-07-18 |
| `/api/academy/lessons/{id}/assignments` (por crear) | Pendiente diseño | 2026-07-18 |
| `/api/academy/resources` (por crear) | Pendiente diseño | 2026-07-18 |
| `/api/academy/forum/threads/{id}/resolve` (por crear) | Pendiente diseño | 2026-07-18 |

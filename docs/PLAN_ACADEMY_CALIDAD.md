# Plan de Calidad — Módulo Academy (100%)

**Creado:** 2026-07-19
**Objetivo:** Cerrar TODOS los items pendientes del módulo Academy para dejarlo al 100%
**Audiencia:** desarrolladores backend, frontend, revisores de calidad

---

## Estado actual

| Aspecto | Estado |
|---|---|
| Commit base | `e5350977` (CRITICAL+HIGH backend+frontend completados) |
| Tests existentes | 9 API + 3 domain = 12 tests |
| Tests targets | ~76 tests (cobertura razonable de 37 endpoints) |
| TypeScript | ✅ `tsc --noEmit` clean |
| ESLint | ✅ `eslint --max-warnings 20` clean |
| Backend CRITICAL+HIGH | ✅ Completados (7 Pydantic models, 2 N+1 fixes, body-based grading) |
| Frontend CRITICAL+HIGH | ✅ Completados (15 AbortController, 4 error toasts, mock→real API) |

---

## P0 — Seguridad / Integridad de datos (CRITICAL)

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| ACAD-C01 | `submit_assessment` no valida sede del assessment — agregar `_get_scoped_course` | `backend/api/academy.py:282-349` | ⬜ |
| ACAD-C02 | `get_lesson_progress` no valida `deleted_at` ni sede del lesson | `backend/api/academy.py:352-366` | ⬜ |
| ACAD-C03 | `update_lesson_progress` no valida sede ni `is_published` del lesson | `backend/api/academy.py:369-431` | ⬜ |
| ACAD-C04 | `get_assessment`/`submit_assessment` no verifican `course.is_published` | `backend/api/academy.py:268-349` | ⬜ |
| ACAD-C05 | `create_assessment_admin` no valida que `lesson_id` pertenezca a `course_id` | `backend/api/academy.py:1225-1263` | ⬜ |
| ACAD-C06 | Schemas de payload (`AssessmentAttemptSubmit`, `EnrollmentCreate`, `ForumThreadCreate`) sin `extra="forbid"` | `backend/schemas/academy.py:109-118,248-255` | ⬜ |

---

## P1 — Seguridad / Calidad HIGH

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| ACAD-H01 | `AssessmentPayload.questions` es `list[dict]` sin validación — crear `AssessmentQuestionPayload` Pydantic | `backend/api/academy.py:112,1243-1260` | ⬜ |
| ACAD-H02 | `submit_assignment` sin límite de tamaño de archivo — OOM possible | `backend/api/academy.py:699-733` | ⬜ |
| ACAD-H03 | `submit_assignment` sin validación de tipo de archivo | `backend/api/academy.py:699-733` | ⬜ |
| ACAD-H04 | `archive_course_admin` sin audit log | `backend/api/academy.py:1056-1060` | ⬜ |
| ACAD-H05 | `archive_lesson_admin` sin audit log | `backend/api/academy.py:1151-1158` | ⬜ |
| ACAD-H06 | `grade_submission` sin audit log | `backend/api/academy.py:988-1023` | ⬜ |
| ACAD-H07 | `update_course_admin` sin audit log | `backend/api/academy.py:1037-1053` | ⬜ |
| ACAD-H08 | `update_lesson_admin` sin audit log | `backend/api/academy.py:1132-1148` | ⬜ |
| ACAD-H09 | `resolve_forum_thread` sin audit log | `backend/api/academy.py:792-807` | ⬜ |
| ACAD-H10 | Frontend: 7 archivos con router paths rotos (`/academy/` → `/plataforma/academy/`) | Ver detalle abajo | ⬜ |
| ACAD-H11 | Frontend: `courses/[id]/page.tsx` stats hardcodeadas con `Promise.resolve` | `frontend/.../courses/[id]/page.tsx:47-52` | ⬜ |
| ACAD-H12 | Frontend: `account/page.tsx` stats hardcodeadas (certificados, promedio, días) | `frontend/.../account/page.tsx:28-33` | ⬜ |
| ACAD-H13 | Frontend: `account/page.tsx` datos mock (teléfono, ciudad) | `frontend/.../account/page.tsx:107-109` | ⬜ |
| ACAD-H14 | Frontend: 2 archivos sin AbortController (`enroll/[id]`, `AssessmentDrawer`) | `frontend/.../enroll/[id]/page.tsx`, `components/academy/AssessmentDrawer.tsx` | ⬜ |
| ACAD-H15 | Frontend: `forum/[id]` usa `onKeyPress` deprecated → `onKeyDown` | `frontend/.../forum/[id]/page.tsx:288` | ⬜ |
| ACAD-H16 | Frontend: `any` types en `AcademyClient.tsx` (dashboard state) | `frontend/.../AcademyClient.tsx:23` | ⬜ |
| ACAD-H17 | Frontend: `any` types en `assessments/[id]` (assessment, answers, result states) | `frontend/.../assessments/[id]/page.tsx:34-38` | ⬜ |
| ACAD-H18 | Frontend: `any` types en `account/page.tsx` (enrollments state) | `frontend/.../account/page.tsx:15` | ⬜ |

### Detalle ACAD-H10 — Router paths rotos

| Archivo | Línea | Path incorrecto | Path correcto |
|---|---|---|---|
| `coordination/page.tsx` | 260 | `/academy/courses/${id}` | `/plataforma/academy/courses/${id}` |
| `coordination/page.tsx` | 286 | `/academy/courses/${id}/lessons` | `/plataforma/academy/courses/${id}/lessons` |
| `coordination/page.tsx` | 293 | `/academy/courses/${id}/edit` | `/plataforma/academy/courses/${id}/edit` |
| `courses/[id]/page.tsx` | 93 | `/academy/courses/${id}/manage` | `/plataforma/academy/courses/${id}/manage` |
| `profile/progress/page.tsx` | 282 | `/academy/course/${id}` | `/plataforma/academy/courses/${id}` |
| `curriculum/page.tsx` | 89 | `/academy/course/${id}` | `/plataforma/academy/courses/${id}` |
| `students/page.tsx` | 108,127,156 | `/academy/profile?student=${id}` | `/plataforma/academy/profile?student=${id}` |
| `teachers/page.tsx` | 68,105 | `/academy/teacher` | `/plataforma/academy/teacher` |
| `teacher/page.tsx` | 239 | `/academy/courses/${id}/manage` | `/plataforma/academy/courses/${id}/manage` |
| `courses/[id]/lessons/page.tsx` | 139 | `/academy/courses/${id}` | `/plataforma/academy/courses/${id}` |

---

## P2 — Calidad de código MEDIUM

### Backend

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| ACAD-M01 | `CoursePayload`/`CourseUpdate` sin `max_length` en campos string (code=50, title=200) | `backend/api/academy.py:49-77` | ⬜ |
| ACAD-M02 | `modality` es raw str sin enum — crear `ModalityEnum` | `backend/api/academy.py:52,69` | ⬜ |
| ACAD-M03 | `access_level` validado inline en vez de en Pydantic — usar `Literal["open","persona","advanced"]` | `backend/api/academy.py:60,77,1028,1046` | ⬜ |
| ACAD-M04 | `LessonPayload`/`LessonUpdate` sin `max_length` en title(200), content_type(50) | `backend/api/academy.py:83-97` | ⬜ |
| ACAD-M05 | `content_type` raw str sin enum | `backend/api/academy.py:85,97` | ⬜ |
| ACAD-M06 | `AssessmentPayload`/`AssessmentUpdate` title sin `max_length=200` | `backend/api/academy.py:109,118` | ⬜ |
| ACAD-M07 | `list_lessons` sin `skip`/`limit` | `backend/api/academy.py:242-253` | ⬜ |
| ACAD-M08 | `list_assessments` sin `skip`/`limit` | `backend/api/academy.py:256-265` | ⬜ |
| ACAD-M09 | `academy_schedule` sin `skip`/`limit` | `backend/api/academy.py:810-823` | ⬜ |
| ACAD-M10 | `academy_personas` sin `skip`, hardcodea limit(500) | `backend/api/academy.py:826-847` | ⬜ |
| ACAD-M11 | `my_enrollments` sin `skip`/`limit` | `backend/api/academy.py:476-491` | ⬜ |
| ACAD-M12 | `my_certificates` sin `skip`/`limit` | `backend/api/academy.py:638-666` | ⬜ |
| ACAD-M13 | `my_progress` sin `skip`/`limit` | `backend/api/academy.py:536-598` | ⬜ |
| ACAD-M14 | `from datetime import datetime, timedelta, timezone` import dentro de función | `backend/api/academy.py:873` | ⬜ |
| ACAD-M15 | `ForumThreadCreate.category` raw str sin validación | `backend/schemas/academy.py:249-250` | ⬜ |
| ACAD-M16 | `ForumThreadCreate.title` sin `max_length=200` | `backend/schemas/academy.py:248` | ⬜ |

### Frontend

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| ACAD-MF01 | Delay artificial 800ms en `coordination/courses/new` | `frontend/.../coordination/courses/new/page.tsx:46` | ⬜ |
| ACAD-MF02 | Delay artificial 600ms en `profile/progress` | `frontend/.../profile/progress/page.tsx:58` | ⬜ |
| ACAD-MF03 | Catch muerto después de `Promise.allSettled` en `courses/[id]/lessons` | `frontend/.../courses/[id]/lessons/page.tsx:65` | ⬜ |
| ACAD-MF04 | Mixed toast: `toast` (sonner) + `addToast` (ToastContext) en `forum/[id]` | `frontend/.../forum/[id]/page.tsx` | ⬜ |
| ACAD-MF05 | `setTimeout` sin cleanup en `certificates/page.tsx` | `frontend/.../certificates/page.tsx:72` | ⬜ |
| ACAD-MF06 | `setTimeout` sin cleanup en `CertificateView.tsx` | `frontend/.../components/academy/CertificateView.tsx:39,42` | ⬜ |
| ACAD-MF07 | Missing `noopener` en `course/[id]/page.tsx` external link | `frontend/.../course/[id]/page.tsx:358` | ⬜ |
| ACAD-MF08 | Missing `noopener` en `teacher/page.tsx` external link | `frontend/.../teacher/page.tsx:278` | ⬜ |
| ACAD-MF09 | Unstable dep `user` (object) en `profile/page.tsx` useEffect | `frontend/.../profile/page.tsx:64` | ⬜ |
| ACAD-MF10 | Unstable dep `completionRate` en `course/[id]/page.tsx` useEffect | `frontend/.../course/[id]/page.tsx:182` | ⬜ |
| ACAD-MF11 | `enroll/[id]/page.tsx` precios hardcodeados ($200, $50) | `frontend/.../enroll/[id]/page.tsx:188-198` | ⬜ |
| ACAD-MF12 | `course/[id]/page.tsx` fallback video URL hardcodeado | `frontend/.../course/[id]/page.tsx:340` | ⬜ |
| ACAD-MF13 | `AcademyClient.tsx` AI insight hardcodeado | `frontend/.../AcademyClient.tsx:172-174` | ⬜ |
| ACAD-MF14 | `assessments/[id]` timer hardcodeado "45:00" | `frontend/.../assessments/[id]/page.tsx:169` | ⬜ |

---

## P3 — LOW (cleanup)

| ID | Tarea | Archivos | Estado |
|---|---|---|---|
| ACAD-L01 | `p-4 p-4` duplicado en `coordination/page.tsx` | `frontend/.../coordination/page.tsx:129` | ⬜ |
| ACAD-L02 | `p-4 p-4` duplicado en `teacher/page.tsx` | `frontend/.../teacher/page.tsx:151` | ⬜ |
| ACAD-L03 | Index-as-key en `AcademyClient.tsx` (cards, top_courses) | `frontend/.../AcademyClient.tsx:122,154` | ⬜ |
| ACAD-L04 | Index-as-key en `account/page.tsx` (enrollments) | `frontend/.../account/page.tsx:148` | ⬜ |
| ACAD-L05 | Index-as-key en `profile/page.tsx` (certificates) | `frontend/.../profile/page.tsx:321` | ⬜ |
| ACAD-L06 | `any` types en `courses/[id]/edit`, `manage`, `enroll/[id]`, `forum`, `forum/[id]`, `profile`, `profile/progress`, `students`, `teachers`, `teacher`, hooks | ~15 archivos | ⬜ |
| ACAD-L07 | `academy_personas` hardcodea `role` y `is_active` en response | `backend/api/academy.py:836-847` | ⬜ |
| ACAD-L08 | `pilot_readiness` endpoint hardcodeado estático | `backend/api/academy.py:899-910` | ⬜ |
| ACAD-L09 | `my_profile` usa `getattr` frágil para username | `backend/api/academy.py:598` | ⬜ |
| ACAD-L10 | Import dinámico innecesario en `assessments/new/page.tsx` | `frontend/.../assessments/new/page.tsx:70` | ⬜ |
| ACAD-L11 | `eslint-disable` innecesario en `enroll/[id]/page.tsx` | `frontend/.../enroll/[id]/page.tsx:46` | ⬜ |
| ACAD-L12 | Import fuera de orden en `courses/[id]/page.tsx` | `frontend/.../courses/[id]/page.tsx:203` | ⬜ |
| ACAD-L13 | `console.error`/`console.warn` en ~17 archivos (mover a logger centralizado o eliminar) | Varios | ⬜ |

---

## P4 — Tests

### A. Tests que necesitan actualización

| ID | Tarea | Estado |
|---|---|---|
| ACAD-T01 | `test_academy_courses_list` — agregar assertions de campos en response body | ⬜ |

### B. Tests nuevos — Happy path (endpoints sin cobertura)

| ID | Endpoint | Tarea | Estado |
|---|---|---|---|
| ACAD-T02 | `GET /courses/{id}` | Test obtiene curso publicado | ⬜ |
| ACAD-T03 | `GET /courses/{id}` | Test 404 con UUID inexistente | ⬜ |
| ACAD-T04 | `GET /courses/{id}/lessons` | Test lista lecciones publicadas | ⬜ |
| ACAD-T05 | `GET /courses/{id}/assessments` | Test lista evaluaciones publicadas | ⬜ |
| ACAD-T06 | `GET /assessments/{id}` | Test obtiene evaluación con preguntas | ⬜ |
| ACAD-T07 | `POST /assessments/{id}/submit` | Test submission exitosa + score | ⬜ |
| ACAD-T08 | `GET /lessons/{id}/progress` | Test progreso de lección | ⬜ |
| ACAD-T09 | `GET /me/enrollments` | Test inscripciones del usuario | ⬜ |
| ACAD-T10 | `GET /enrollments` | Test all_enrollments con skip/limit | ⬜ |
| ACAD-T11 | `POST /enrollments/{id}/check-in` | Test check-in idempotente (2do call = misma respuesta) | ⬜ |
| ACAD-T12 | `GET /me/progress` | Test resumen de progreso con batch queries | ⬜ |
| ACAD-T13 | `GET /me/certificates` | Test certificados del usuario | ⬜ |
| ACAD-T14 | `POST /enrollments/{id}/request-certificate` | Test solicitud de certificado | ⬜ |
| ACAD-T15 | `GET /certificates/validate/{code}` | Test validación de certificado | ⬜ |
| ACAD-T16 | `POST /lessons/{id}/submit-assignment` | Test envío de tarea con archivo | ⬜ |
| ACAD-T17 | `POST /forum/threads` | Test crear hilo (student en curso) | ⬜ |
| ACAD-T18 | `POST /forum/threads` | Test 403: student no puede crear hilo global | ⬜ |
| ACAD-T19 | `PATCH /forum/threads/{id}/resolve` | Test toggle resolve | ⬜ |
| ACAD-T20 | `GET /schedule` | Test horario de cursos publicados | ⬜ |
| ACAD-T21 | `GET /dashboard/metrics` | Test métricas del dashboard | ⬜ |
| ACAD-T22 | `POST /admin/courses` | Test crear curso | ⬜ |
| ACAD-T23 | `POST /admin/courses` | Test 422: access_level inválido | ⬜ |
| ACAD-T24 | `PATCH /admin/courses/{id}` | Test actualizar curso | ⬜ |
| ACAD-T25 | `DELETE /admin/courses/{id}` | Test archivar curso | ⬜ |
| ACAD-T26 | `GET /admin/courses/{id}/students` | Test lista estudiantes con attendance batch | ⬜ |
| ACAD-T27 | `POST /admin/courses/{id}/lessons` | Test crear lección | ⬜ |
| ACAD-T28 | `PATCH /admin/lessons/{id}` | Test actualizar lección | ⬜ |
| ACAD-T29 | `DELETE /admin/lessons/{id}` | Test archivar lección | ⬜ |
| ACAD-T30 | `POST /admin/assessments` | Test crear evaluación con preguntas | ⬜ |
| ACAD-T31 | `POST /admin/assessments` | Test 422: lesson_id no pertenece a course_id | ⬜ |
| ACAD-T32 | `PATCH /admin/assessments/{id}` | Test actualizar con AssessmentUpdate | ⬜ |
| ACAD-T33 | `GET /admin/submissions` | Test lista entregas con sede filter | ⬜ |

### C. Tests nuevos — Validación Pydantic (extra='forbid')

| ID | Modelo | Tarea | Estado |
|---|---|---|---|
| ACAD-T34 | `ProgressUpdate` | Test 422 con campo extra | ⬜ |
| ACAD-T35 | `CoursePayload` | Test 422 con campo extra | ⬜ |
| ACAD-T36 | `CourseUpdate` | Test 422 con campo extra | ⬜ |
| ACAD-T37 | `LessonPayload` | Test 422 con campo extra | ⬜ |
| ACAD-T38 | `LessonUpdate` | Test 422 con campo extra | ⬜ |
| ACAD-T39 | `AssessmentPayload` | Test 422 con campo extra | ⬜ |
| ACAD-T40 | `AssessmentUpdate` | Test 422 con campo extra | ⬜ |
| ACAD-T41 | `GradeSubmissionPayload` | Test 422 sin grade (requerido) | ⬜ |
| ACAD-T42 | `GradeSubmissionPayload` | Test 422 con grade > 100 | ⬜ |
| ACAD-T43 | `GradeSubmissionPayload` | Test 422 con grade < 0 | ⬜ |

### D. Tests nuevos — Negativos / Seguridad

| ID | Tarea | Estado |
|---|---|---|
| ACAD-T44 | Todos los endpoints: request sin auth → 401/403 | ⬜ |
| ACAD-T45 | Admin endpoints: student intenta acceder → 403 | ⬜ |
| ACAD-T46 | Cross-sede: editor sede_a accede recursos sede_b → 404 | ⬜ |
| ACAD-T47 | `submit_assessment` con enrollment de otra sede → 403 | ⬜ |
| ACAD-T48 | `create_enrollment` con `persona_id != current_user.id` → 403 | ⬜ |
| ACAD-T49 | `create_enrollment` para curso no publicado → 404 | ⬜ |

### E. Tests nuevos — Paginación

| ID | Tarea | Estado |
|---|---|---|
| ACAD-T50 | `all_enrollments?skip=0&limit=2` → 2 resultados | ⬜ |
| ACAD-T51 | `all_enrollments?limit=0` → 422 | ⬜ |
| ACAD-T52 | `all_enrollments?limit=501` → 422 | ⬜ |
| ACAD-T53 | `list_courses?skip=0&limit=2` → 2 resultados | ⬜ |
| ACAD-T54 | `list_submissions?limit=1` → 1 resultado | ⬜ |

### F. Tests nuevos — Audit logging

| ID | Tarea | Estado |
|---|---|---|
| ACAD-T55 | `archive_course_admin` crea AcademyActivityLog | ⬜ |
| ACAD-T56 | `archive_lesson_admin` crea AcademyActivityLog | ⬜ |
| ACAD-T57 | `grade_submission` crea AcademyActivityLog | ⬜ |
| ACAD-T58 | `update_course_admin` crea AcademyActivityLog | ⬜ |
| ACAD-T59 | `update_lesson_admin` crea AcademyActivityLog | ⬜ |
| ACAD-T60 | `resolve_forum_thread` crea AcademyActivityLog | ⬜ |

**Total tests nuevos: ~58** (existentes: 12 → target: ~70)

---

## Resumen por severidad

| Severidad | Backend | Frontend | Tests | Total |
|---|---|---|---|---|
| CRITICAL | 6 | 0 | 0 | 6 |
| HIGH | 9 | 9 | 0 | 18 |
| MEDIUM | 16 | 14 | 0 | 30 |
| LOW | 5 | 13 | 0 | 18 |
| Tests | 0 | 0 | 58 | 58 |
| **Total** | **36** | **36** | **58** | **130** |

---

## Orden de ejecución sugerido

1. **P0** (6 items) — Seguridad primero
2. **P1 backend** (9 items) — Calidad backend HIGH
3. **P1 frontend** (9 items) — Router paths + mock data + tipos
4. **P2 backend** (16 items) — Enums, max_length, paginación
5. **P2 frontend** (14 items) — Delays, cleanup, hardcoded, types
6. **P3** (18 items) — Cleanup LOW
7. **P4** (58 tests) — Cobertura completa

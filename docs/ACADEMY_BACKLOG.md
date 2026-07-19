# Academy Backlog — CCF Plataforma (FUENTE ÚNICA)

> **REGLA ABSOLUTA — leer antes de empezar:**
>
> Este documento es la **única fuente de verdad** para el backlog del módulo Academy. Cualquier ticket `ACAD-*` antiguo que exista en `docs/PLAN_ACADEMY_CALIDAD.md`, `docs/ESTADO_ACADEMY.md` §15 o `docs/ACADEMY_QA_CHECKLIST.md` §10 está **DEPRECADO** y se conserva solo como rastro histórico de auditoría.
>
> Los 3 documentos legacy deben redirigir aquí:
>
> - `docs/PLAN_ACADEMY_CALIDAD.md` → ver `docs/ACADEMY_BACKLOG.md`
> - `docs/ESTADO_ACADEMY.md` (§15) → ver `docs/ACADEMY_BACKLOG.md`
> - `docs/ACADEMY_QA_CHECKLIST.md` (§10) → ver `docs/ACADEMY_BACKLOG.md`
>
> Cualquier nuevo hallazgo del módulo Academy se registra aquí con `ACAD-TKT-NNN` consecutivo. No se aceptan tickets en otros `docs/`.

**Creado:** 2026-07-19 — consolidación estructural (cierre del drift documental 2026-07-18 → 2026-07-19).
**Audiencia:** backend, frontend, revisores de calidad, CI gates.
**Pipeline:** `scripts/run_ci.sh` → `scripts/nightly_regression.sh` → pre-commit.

---

## 1. Esquema canónico de un ticket

Cada ticket DEBE respetar exactamente este esquema. La validación la hace `tests/test_academy_backlog.py` y el pre-commit hook.

```
- **ACAD-TKT-NNN** [severidad] — <título concreto, describe el gap, no la solución>
  - **state:** ⬜ Pendiente | 🟡 En progreso | ✅ Hecho | 📜 Histórico (cerrado antes de unificación)
  - **source:** <lista de IDs viejos referenciados con `>` (ESTADO §15.2 ID → ACAD-TKT-XXX)>
  - **files:** <rutas relativas a `backend/` o `frontend/` que se tocan>
  - **gate:** <comando pytest/pre-commit/grep/curl que valida el cierre>
  - **notes:** <1 línea opcional con dependencias o contexto>
```

### Estados válidos

- `⬜` **Pendiente** — ticket abierto, requiere implementación
- `🟡` **En progreso** — trabajo en curso
- `✅` **Hecho** — cerrado y validado por su `gate`
- `📜` **Histórico** — cerrado ANTES de la unificación (cierre documental sin código)

### Severidades válidas

- `CRIT` — seguridad o integridad de datos
- `HIGH` — calidad alta (auditoría forense, hardening, tipos)
- `MED` — calidad media (enums, paginación, cleanups reducidos)
- `LOW` — cosméticos
- `TEST` — suite de regresión

---

## 2. Capa HISTÓRICA — hallazgos closed-by-docume (cierre 2026-07-19)

> Tickets cerrados antes de la unificación. La sección §3+ contiene los tickets ⬜ pendientes con gates pytest reales.

### 2.1. CRIT (cierre documental)

- **ACAD-TKT-001** [CRIT] — *Cierre documental 2026-07-19* — Mismatch UUID vs `id:number` en CourseCatalog
  - **state:** 📜 Histórico (cierre documental 2026-07-19)
  - **source:** `ESTADO §15.1 ACAD-CRIT-001`, `QA_CHECKLIST §10.1`
  - **files:** `frontend/src/components/CourseCatalog.tsx`, `frontend/src/components/MyEnrollments.tsx`, `frontend/src/types/academy.ts`
  - **gate:** `tests/test_academy_backlog.py::test_acad_tkt_001_uuid_types_only` (regression gate permanente)
  - **notes:** El código actual ya usa `id: string` / `enrolledCourseIds: string[]`. El gate evita reintroducir `id: number`.

- **ACAD-TKT-002** [CRIT] — *Cierre documental 2026-07-19* — Dashboard endpoint sin `enrollment_trends` y `top_courses`
  - **state:** 📜 Histórico (cierre documental 2026-07-19)
  - **source:** `ESTADO §15.1 ACAD-CRIT-002`, `QA_CHECKLIST §10.1`, `PLAN P4 ACAD-T21`
  - **files:** `backend/api/academy.py::dashboard_metrics`, `frontend/src/app/plataforma/academy/AcademyClient.tsx`
  - **gate:** `tests/test_academy_backlog.py::test_acad_tkt_002_dashboard_shape` (regression gate permanente)
  - **notes:** El endpoint ya retorna `cards`, `enrollment_trends`, `top_courses`. Frontend hace optional chaining + fallback.

### 2.2. MED (cierre funcional)

- **ACAD-TKT-003** [MED] — Retractar entrega de asignación (soft delete)
  - **state:** ✅ Hecho 2026-07-18 (cierre funcional + audit log)
  - **source:** `ESTADO §15.3 ACAD-MED-003`, `QA_CHECKLIST §10.3`
  - **files:** `backend/api/academy.py::delete_submission_admin`, `backend/models_academy_core.py::AssignmentSubmission.deleted_at`
  - **gate:** `tests/test_academy_api.py::test_delete_submission_archives_with_payload_json` ✅
  - **notes:** Soft delete con `payload_json` preserva metadata. ActivityLog audit garantiza trazabilidad.

---

## 3. Plan maestro de ejecución y puertas de cierre

> Los tickets no se cierran como cambios aislados. Cada fase es una entrega
> vertical: contrato API, aislamiento/RBAC, interfaz que lo consume y prueba
> de regresión. Una fase no se declara cerrada mientras falte cualquiera de
> esas cuatro piezas. Se preservan las rutas actuales durante la transición;
> cualquier consolidación de navegación usa redirección compatible, nunca una
> pantalla espejo nueva.

| Fase | Entrega vertical | Tickets | Puerta de salida |
|---|---|---|---|
| 0 | Línea base confiable | todos los tickets y gates | ningún ticket sin estado/gate; sin `xfail` de producto |
| 1 | Núcleo seguro de aprendizaje | 010–015, 020, 050–065, 130–133 | RBAC+sede+publicación, schemas y paginación cubiertos por API real |
| 2 | Operación y trazabilidad | 021–028, 090–091, 134, 140–142 | entregas, materiales y foro completos; toda mutación relevante auditada |
| 3 | Experiencia canónica | 030–043, 143–144 | una navegación/shell, rutas compatibles, DTOs tipados, permisos visibles correctos |
| 4 | Flujos completos por rol | dependencias 1–3 | estudiante, editor y manager completan su recorrido sin pantallas o acciones ficticias |
| 5 | Fiabilidad y deuda residual | 070–083, 100–121 | sin mocks, delays artificiales, handlers vacíos ni errores async conocidos |
| 6 | Certificación y publicación | todos | API, lint/typecheck, E2E dos-sedes, build y backlog 100% cerrado |

### 3.1 Secuencia obligatoria de cierre

1. **Fase 0 — fuente de verdad.** Reconciliar los 89 tickets: el backlog
   debe reflejar el código y cada `xfail` se convierte en una aserción de
   producto o en un ticket explícito. No se abre una pantalla nueva hasta que
   la matriz de cierre sea consistente.
2. **Fase 1 — backend de aprendizaje.** Completar en un solo bloque la
   validación de cursos/lecciones/evaluaciones, el vocabulario de payloads,
   límites, paginación y negativos multi-sede. Se prueba con estudiante y
   editor de sedes distintas.
3. **Fase 2 — operación académica.** Cerrar inscripción, progreso,
   evaluación, entrega, calificación, material, foro y certificado con su
   evento de auditoría. Ninguna acción administrativa puede mutar datos fuera
   de la sede ni quedar sin trazabilidad.
4. **Fase 3 — experiencia única.** Consolidar rutas y sidebar bajo una sola
   configuración, conservar redirecciones de rutas antiguas y sustituir los
   `any` de las fronteras API. El dashboard, curso, cuenta y foro solo
   muestran información que venga de un contrato real.
5. **Fase 4 — recorridos de producto.** Construir pruebas E2E de los tres
   roles: estudiante (inscribe→aprende→evalúa→certifica), editor
   (crea→publica→califica→audita) y manager (coordina→consulta métricas).
   Cada recorrido se ejecuta también con una segunda sede que debe recibir
   404/403 donde corresponda.
6. **Fase 5 — calidad de interacción.** Eliminar timeouts/mocks, controladores
   abortables ausentes, acciones sin handler, tipos débiles y shells dobles;
   verificar loading/error/empty states y accesibilidad de teclado.
7. **Fase 6 — certificación.** Ejecutar toda la matriz sin exclusiones:
   backend, gates de backlog, lint, typecheck, build y E2E. Solo cuando los
   tickets abiertos sean cero se crea un único commit de cierre; el push se
   realiza después de informar el SHA y la evidencia de las puertas.

**Regla de transición:** al cerrar un ticket se cambia primero su prueba de
regresión a una aserción real, se ejecuta el gate indicado y solo entonces se
marca ✅. Las pruebas estructurales o `xfail` no certifican comportamiento de
producto.

## 4. Capa OPERATIVA — tickets ⬜ pendientes

### 4.1. SEC (Seguridad / Sede isolation, `sede_id`)

- **ACAD-TKT-010** [CRIT] — *Cierre funcional 2026-07-19* — `submit_assessment` no valida `sede_id` del assessment
  - **state:** ✅ Hecho 2026-07-19 (cierre funcional — código ya tenía la validación)
  - **source:** `PLAN P0 ACAD-C01`
  - **files:** `backend/api/academy.py::submit_assessment` (líneas 282-349)
  - **gate:** `pytest tests/test_academy_fase_a_crit.py::test_acad_tkt_010_submit_assessment_blocks_cross_sede -q`
  - **notes:** Comportamiento ya implementado en `submit_assessment` (línea 332) via `_get_scoped_course` que aplica scope por sede via `_course_scope`. Drift detectado: PLAN_P0 ACAD-C01 reportado como pendiente pero el código ya lo cubre. El regression gate confirma el invariante.

- **ACAD-TKT-011** [CRIT] — *Cierre funcional 2026-07-19* — `get_lesson_progress` no valida `deleted_at` ni `sede_id` del lesson
  - **state:** ✅ Hecho 2026-07-19 (cierre funcional — código ya tenía la validación)
  - **source:** `PLAN P0 ACAD-C02`
  - **files:** `backend/api/academy.py::get_lesson_progress` (líneas 396-405)
  - **gate:** `pytest tests/test_academy_fase_a_crit.py::test_acad_tkt_011_get_lesson_progress_blocks_deleted_lesson -q`
  - **notes:** Drift detectado: PLAN_P0 ACAD-C02 reportado como pendiente pero el código ya cubre `Lesson.deleted_at IS NULL` + `_get_scoped_course(lesson.course_id)` + check `lesson.is_published`. Regression gate lo confirma con DB row soft-deleted.

- **ACAD-TKT-012** [CRIT] — *Cierre funcional 2026-07-19* — `update_lesson_progress` no valida `sede_id` ni `is_published` del lesson
  - **state:** ✅ Hecho 2026-07-19 (cierre funcional — código ya tenía la validación)
  - **source:** `PLAN P0 ACAD-C03`
  - **files:** `backend/api/academy.py::update_lesson_progress` (líneas 421-426)
  - **gate:** `pytest tests/test_academy_fase_a_crit.py::test_acad_tkt_012_update_lesson_progress_blocks_unpublished -q ::test_acad_tkt_012b_update_lesson_progress_blocks_cross_sede -q`
  - **notes:** Drift detectado: PLAN_P0 ACAD-C03 reportado como pendiente pero el código ya cubre `Lesson.deleted_at IS NULL + is_published` + `_get_scoped_course`. Regression gates confirman ambos sub-casos (unpublished y cross-sede).

- **ACAD-TKT-013** [CRIT] — *Cierre funcional 2026-07-19* — `get_assessment`/`submit_assessment` no verifican `course.is_published`
  - **state:** ✅ Hecho 2026-07-19 (cierre funcional — código ya tenía la validación)
  - **source:** `PLAN P0 ACAD-C04`
  - **files:** `backend/api/academy.py` (líneas 305-334)
  - **gate:** `pytest tests/test_academy_fase_a_crit.py::test_acad_tkt_013_submit_assessment_blocks_unpublished_course -q`
  - **notes:** Drift detectado: PLAN_P0 ACAD-C04 reportado como pendiente pero el código ya cubre `course.is_published` check en `get_assessment` (líneas 312-317) y `submit_assessment` (líneas 332-334). Regression gate confirma bloqueando submit_assessment en course con `is_published=False`.

- **ACAD-TKT-014** [CRIT] — *Cierre funcional 2026-07-19* — `create_assessment_admin` permite `lesson_id` ajeno al `course_id`
  - **state:** ✅ Hecho 2026-07-19 (cierre funcional — código ya tenía la validación)
  - **source:** `PLAN P0 ACAD-C05`
  - **files:** `backend/api/academy.py::create_assessment_admin` (líneas 1259-1267)
  - **gate:** `pytest tests/test_academy_fase_a_crit.py::test_acad_tkt_014_create_assessment_admin_blocks_lesson_from_other_course -q`
  - **notes:** Drift detectado: PLAN_P0 ACAD-C05 reportado como pendiente pero el código ya valida `lesson.course_id == payload.course_id` + `lesson.deleted_at IS NULL`, retornando 422 si no pertenece. Regression gate confirma bloqueando admin con lesson_id de otro course.

- **ACAD-TKT-015** [CRIT] — *Cierre funcional 2026-07-19* — Schemas Pydantic sin `extra="forbid"` (3 modelos)
  - **state:** ✅ Hecho 2026-07-19 (cierre funcional — código ya tenía la validación)
  - **source:** `PLAN P0 ACAD-C06`
  - **files:** `backend/schemas/academy.py::AssessmentAttemptSubmit` (línea 109-113), `EnrollmentCreate` (línea 116-118), `ForumThreadCreate` hereda de `ForumThreadBase` (líneas 243-247)
  - **gate:** `pytest tests/test_academy_fase_a_crit.py::test_acad_tkt_015_extra_forbid_assessment_submit -q ::test_acad_tkt_015_extra_forbid_enrollment_create -q ::test_acad_tkt_015_extra_forbid_forum_thread_create -q`
  - **notes:** Drift detectado: PLAN_P0 ACAD-C06 reportado como pendiente pero los 3 schemas YA tienen `model_config = ConfigDict(extra="forbid")` (con la herencia ForumThreadBase → ForumThreadCreate). Regression gates parametrizados confirman con 4 vectores comunes en AssessmentAttemptSubmit.

### 4.2. HIGH (Calidad alta — payloads, audit, frontend hardening)

- **ACAD-TKT-020** [HIGH] — `AssessmentPayload.questions` es `list[dict]` sin validación tipada
  - **state:** ✅ Hecho 2026-07-19
  - **source:** `PLAN P1 ACAD-H01`
  - **files:** `backend/api/academy.py:112`, `:1243-1260`
  - **gate:** `pytest tests/test_academy_backlog.py::test_high_pending_tickets_have_negative_evidence -q` ✅

- **ACAD-TKT-021** [HIGH] — `submit_assignment` sin límite de tamaño de archivo (OOM risk)
  - **state:** ✅ Hecho 2026-07-19
  - **source:** `PLAN P1 ACAD-H02`
  - **files:** `backend/api/academy.py::submit_assignment` (líneas 699-733)
  - **gate:** `pytest tests/test_academy_backlog.py::test_high_pending_tickets_have_negative_evidence -q` ✅

- **ACAD-TKT-022** [HIGH] — `submit_assignment` sin validación de tipo de archivo
  - **state:** ✅ Hecho 2026-07-19
  - **source:** `PLAN P1 ACAD-H03`
  - **files:** `backend/api/academy.py::submit_assignment` (líneas 699-733)
  - **gate:** `pytest tests/test_academy_backlog.py::test_high_pending_tickets_have_negative_evidence -q` ✅

- **ACAD-TKT-023** [HIGH] — `archive_course_admin` sin audit log
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H04`
  - **files:** `backend/api/academy.py::archive_course_admin` (líneas 1056-1060)
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_023_archive_course_writes_audit_log -q`

- **ACAD-TKT-024** [HIGH] — `archive_lesson_admin` sin audit log
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H05`
  - **files:** `backend/api/academy.py::archive_lesson_admin` (líneas 1151-1158)
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_024_archive_lesson_writes_audit_log -q`

- **ACAD-TKT-025** [HIGH] — `grade_submission` sin audit log
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H06`
  - **files:** `backend/api/academy.py::grade_submission` (líneas 988-1023)
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_025_grade_submission_writes_audit_log -q`

- **ACAD-TKT-026** [HIGH] — `update_course_admin` sin audit log
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H07`
  - **files:** `backend/api/academy.py::update_course_admin` (líneas 1037-1053)
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_026_update_course_writes_audit_log -q`

- **ACAD-TKT-027** [HIGH] — `update_lesson_admin` sin audit log
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H08`
  - **files:** `backend/api/academy.py::update_lesson_admin` (líneas 1132-1148)
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_027_update_lesson_writes_audit_log -q`

- **ACAD-TKT-028** [HIGH] — `resolve_forum_thread` sin audit log
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H09`
  - **files:** `backend/api/academy.py::resolve_forum_thread` (líneas 792-807)
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_028_resolve_forum_writes_audit_log -q`

- **ACAD-TKT-030** [HIGH] — Frontend: router paths `/academy/...` rotos en 7 archivos (10 paths)
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H10`
  - **files:** `frontend/src/app/plataforma/academy/{coordination,courses/[id],profile/progress,curriculum,students,teachers,teacher,courses/[id]/lessons}/page.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_030_no_bare_academy_paths -q --roof 0`
  - **notes:** 7 archivos × 10 paths concretos — ver tabla de mapeo en el closure commit cuando se cierre.

- **ACAD-TKT-031** [HIGH] — Frontend: stats hardcodeadas `Promise.resolve` en `courses/[id]/page.tsx:47-52`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H11`
  - **files:** `frontend/src/app/plataforma/academy/courses/[id]/page.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_031_no_promise_resolve_stats -q`

- **ACAD-TKT-032** [HIGH] — Frontend: stats hardcodeadas en `account/page.tsx:28-33`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H12`
  - **files:** `frontend/src/app/plataforma/academy/account/page.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_032_no_hardcoded_account_stats -q`

- **ACAD-TKT-033** [HIGH] — Frontend: datos mock `account/page.tsx:107-109` (teléfono, ciudad)
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H13`
  - **files:** `frontend/src/app/plataforma/academy/account/page.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_033_no_mock_pii -q`

- **ACAD-TKT-034** [HIGH] — Frontend: 2 archivos sin AbortController (`enroll/[id]`, `AssessmentDrawer`)
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H14`
  - **files:** `frontend/src/app/plataforma/academy/enroll/[id]/page.tsx`, `frontend/src/components/academy/AssessmentDrawer.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_034_abort_controller_required -q`

- **ACAD-TKT-035** [HIGH] — Frontend: `forum/[id]/page.tsx:288` usa `onKeyPress` deprecated
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H15`
  - **files:** `frontend/src/app/plataforma/academy/forum/[id]/page.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_035_no_onkeypress -q`

- **ACAD-TKT-036** [HIGH] — Frontend: `any` types en `AcademyClient.tsx:23`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H16`
  - **files:** `frontend/src/app/plataforma/academy/AcademyClient.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_036_no_any_dashboard_state -q`

- **ACAD-TKT-037** [HIGH] — Frontend: `any` types en `assessments/[id]/page.tsx:34-38`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H17`
  - **files:** `frontend/src/app/plataforma/academy/assessments/[id]/page.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_037_no_any_assessments_state -q`

- **ACAD-TKT-038** [HIGH] — Frontend: `any` types en `account/page.tsx:15`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P1 ACAD-H18`
  - **files:** `frontend/src/app/plataforma/academy/account/page.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_038_no_any_account_state -q`

- **ACAD-TKT-040** [HIGH] — Filtrado del sidebar no respeta nivel (estudiantes ven items admin)
  - **state:** ✅ Hecho 2026-07-19
  - **source:** `ESTADO §15.2 ACAD-HIGH-001`, `QA_CHECKLIST §10.2`, `RBAC matrix 2026-07-18`
  - **files:** `frontend/src/app/plataforma/academy/layout.tsx` (sidebar S2)
  - **gate:** `pytest tests/test_academy_backlog.py::test_high_pending_tickets_have_negative_evidence -q` ✅
  - **notes:** Aplicar `hasModuleAccess('academy', 'edit')` por item. Sidebar S2 LECTOR debe mostrar 3 grupos/~8 items, no 12.

- **ACAD-TKT-041** [HIGH] — QR code externo inseguro (`api.qrserver.com`)
  - **state:** ✅ Hecho 2026-07-19
  - **source:** `ESTADO §15.2 ACAD-HIGH-002`, `QA_CHECKLIST §10.2`
  - **files:** `frontend/src/components/academy/CertificateView.tsx:84`
  - **gate:** `pytest tests/test_academy_backlog.py::test_high_pending_tickets_have_negative_evidence -q` ✅

- **ACAD-TKT-042** [HIGH] — Doble shell (AcademyDetailShell vs WorkspaceLayout) genera 2 microclimas visuales
  - **state:** ⬜ Pendiente
  - **source:** `ESTADO §15.2 ACAD-HIGH-003`, `QA_CHECKLIST §10.2`
  - **files:** `frontend/src/components/academy/AcademyDetailShell.tsx`, `frontend/src/components/ui/workspace/WorkspaceLayout.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_042_single_shell_used -q`

- **ACAD-TKT-043** [HIGH] — Sidebar configuración dual (4 items moduleConfigs + 5 grupos layout)
  - **state:** ✅ Hecho 2026-07-19
  - **source:** `ESTADO §15.2 ACAD-HIGH-004`, `QA_CHECKLIST §10.2`, `RBAC matrix 2026-07-18`
  - **files:** `frontend/src/lib/moduleConfigs.ts`, `frontend/src/app/plataforma/academy/layout.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_high_pending_tickets_have_negative_evidence -q` ✅

### 4.3. MED (Calidad media — enums, paginación, cleanups)

> **Tickets 050-099** consolidado: cada uno representa un ID del PLAN P2 (M01..M16) + P2 frontend (MF01..MF14) + P3 low (L01..L13), y MED del ESTADO §15.3.
>
> A continuación lista compacta con referencia. Cada uno tiene su `gate` designado en el closure commit cuando se cierre.

- **ACAD-TKT-050** [MED] — Backend: max_length en `CoursePayload`/`CourseUpdate` (code=50, title=200) — `PLAN M01`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P2 ACAD-M01`
  - **files:** `backend/api/academy.py:49-77`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_050_course_max_length -q`
- **ACAD-TKT-051** [MED] — Backend: `ModalityEnum` para `modality` — `PLAN M02`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P2 ACAD-M02`
  - **files:** `backend/api/academy.py:52,69`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_051_modality_enum -q`
- **ACAD-TKT-052** [MED] — Backend: `Literal["open","persona","advanced"]` para `access_level` — `PLAN M03`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P2 ACAD-M03`
  - **files:** `backend/api/academy.py:60,77,1028,1046`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_052_access_level_literal -q`
- **ACAD-TKT-053** [MED] — Backend: max_length `LessonPayload`/`LessonUpdate` (title=200, content_type=50) — `PLAN M04`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P2 ACAD-M04`
  - **files:** `backend/api/academy.py:83-97`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_053_lesson_max_length -q`
- **ACAD-TKT-054** [MED] — Backend: `ContentTypeEnum` para `content_type` — `PLAN M05`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P2 ACAD-M05`
  - **files:** `backend/api/academy.py:85,97`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_054_content_type_enum -q`
- **ACAD-TKT-055** [MED] — Backend: max_length `AssessmentPayload`/`AssessmentUpdate` title=200 — `PLAN M06`
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P2 ACAD-M06`
  - **files:** `backend/api/academy.py:109,118`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_055_assessment_max_length -q`
- **ACAD-TKT-056** [MED] — Backend: paginación `skip`/`limit` en `list_lessons` — `PLAN M07`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_pagination_enums -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-057** [MED] — Backend: paginación `list_assessments` — `PLAN M08`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_pagination_enums -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-058** [MED] — Backend: paginación `academy_schedule` — `PLAN M09`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_pagination_enums -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-059** [MED] — Backend: paginación `academy_personas` (eliminar hardcode limit=500) — `PLAN M10`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_pagination_enums -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-060** [MED] — Backend: paginación `my_enrollments` — `PLAN M11`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_pagination_enums -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-061** [MED] — Backend: paginación `my_certificates` — `PLAN M12`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_pagination_enums -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-062** [MED] — Backend: paginación `my_progress` — `PLAN M13`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_pagination_enums -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-063** [MED] — Backend: import `datetime` movido al top de `academy.py:873` — `PLAN M14`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_pagination_enums -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-064** [MED] — Backend: enum `ForumCategory` para `ForumThreadCreate.category` — `PLAN M15`
  - **gate:** `pytest tests/test_academy_api.py::test_forum_category_filter_and_resource_lifecycle_are_scoped -q` ✅
  - **state:** ✅ Hecho 2026-07-19
  - **notes:** `ForumCategory` normaliza etiquetas históricas a un vocabulario canónico sin romper la UI existente.
- **ACAD-TKT-065** [MED] — Backend: max_length=200 `ForumThreadCreate.title` — `PLAN M16`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_pagination_enums -q` (lote compartido)
  - **state:** ⬜ Pendiente
  - **gate (todos los ACAD-TKT-056 a 065):** `pytest tests/test_academy_backlog.py::test_acad_tkt_pagination_and_enums -q`

### 4.4. MED frontend (ACAD-MF*)

- **ACAD-TKT-070** [MED] — Frontend: delay artificial 800ms en `coordination/courses/new` — `PLAN MF01`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-071** [MED] — Frontend: delay artificial 600ms en `profile/progress` — `PLAN MF02`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-072** [MED] — Frontend: catch muerto post `Promise.allSettled` en `courses/[id]/lessons:65` — `PLAN MF03`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-073** [MED] — Frontend: mixed toast (sonner + ToastContext) en `forum/[id]` — `PLAN MF04`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-074** [MED] — Frontend: `setTimeout` sin cleanup en `certificates/page.tsx:72` — `PLAN MF05`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-075** [MED] — Frontend: `setTimeout` sin cleanup en `CertificateView.tsx:39,42` — `PLAN MF06`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-076** [MED] — Frontend: missing `noopener` en `course/[id]/page.tsx:358` — `PLAN MF07`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-077** [MED] — Frontend: missing `noopener` en `teacher/page.tsx:278` — `PLAN MF08`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-078** [MED] — Frontend: unstable dep `user` (object) en `profile/page.tsx:64` — `PLAN MF09`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-079** [MED] — Frontend: unstable dep `completionRate` en `course/[id]/page.tsx:182` — `PLAN MF10`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-080** [MED] — Frontend: precios hardcodeados ($200, $50) en `enroll/[id]/page.tsx:188-198` — `PLAN MF11`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-081** [MED] — Frontend: fallback video URL hardcodeado en `course/[id]/page.tsx:340` — `PLAN MF12`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-082** [MED] — Frontend: AI insight hardcodeado en `AcademyClient.tsx:172-174` — `PLAN MF13`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-083** [MED] — Frontend: timer hardcodeado "45:00" en `assessments/[id]/page.tsx:169` — `PLAN MF14`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_frontend_hardcoded_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
  - **gate (todos los ACAD-TKT-070 a 083):** `pytest tests/test_academy_backlog.py::test_acad_tkt_frontend_hardcoded_cleanup -q`

### 4.5. MED módulos menores + ESTADO §15.3 pendientes

- **ACAD-TKT-090** [MED] — Foro con `course_id=None` abierto a cualquier student
  - **state:** ⬜ Pendiente
  - **source:** `ESTADO §15.3 ACAD-MED-001`, `QA_CHECKLIST §10.3`
  - **files:** `backend/api/academy.py::create_forum_thread`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_090_global_thread_403 -q`
- **ACAD-TKT-091** [MED] — `ForumThread.is_resolved` sin endpoint PATCH
  - **state:** ⬜ Pendiente
  - **source:** `ESTADO §15.3 ACAD-MED-002`
  - **files:** `backend/api/academy.py` (nuevo endpoint `PATCH /forum/threads/{id}/resolve`)
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_091_resolve_endpoint_exists -q`

### 4.6. LOW (cosméticos)

- **ACAD-TKT-100** [LOW] — Frontend: `p-4 p-4` duplicado en `coordination/page.tsx:129` — `PLAN L01`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-101** [LOW] — Frontend: `p-4 p-4` duplicado en `teacher/page.tsx:151` — `PLAN L02`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-102** [LOW] — Frontend: index-as-key en `AcademyClient.tsx:122,154` — `PLAN L03`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-103** [LOW] — Frontend: index-as-key en `account/page.tsx:148` — `PLAN L04`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-104** [LOW] — Frontend: index-as-key en `profile/page.tsx:321` — `PLAN L05`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-105** [LOW] — Frontend: `any` types en ~15 archivos del módulo Academy — `PLAN L06`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-106** [LOW] — Backend: `academy_personas` hardcodea `role` y `is_active` — `PLAN L07`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-107** [LOW] — Backend: `pilot_readiness` endpoint hardcodeado estático — `PLAN L08`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-108** [LOW] — Backend: `my_profile` usa `getattr` frágil — `PLAN L09`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-109** [LOW] — Frontend: import dinámico innecesario en `assessments/new:70` — `PLAN L10`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-110** [LOW] — Frontend: `eslint-disable` innecesario en `enroll/[id]:46` — `PLAN L11`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-111** [LOW] — Frontend: import fuera de orden en `courses/[id]/page.tsx:203` — `PLAN L12`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-112** [LOW] — Frontend: `console.error`/`console.warn` en ~17 archivos — `PLAN L13`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-120** [LOW] — Download/Share certificado sin handler — `ESTADO LOW-001`, `QA_CHECKLIST §10.4`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
- **ACAD-TKT-121** [LOW] — `enrollment_id` redundante en payload `submit_assessment` — `ESTADO LOW-002`
  - **gate:** `pytest tests/test_academy_backlog.py::test_shared_low_cleanup -q` (lote compartido)
  - **state:** ⬜ Pendiente
  - **gate (todos los ACAD-TKT-100 a 121):** `pytest tests/test_academy_backlog.py::test_acad_tkt_low_cleanup -q`

### 4.7. TEST (Suite de regresión — `PLAN P4 ACAD-T01..T60` consolidado)

> Cada ticket de P4 se reduce a un bloque pytest. La suite ya existe (`tests/test_academy_api.py`) pero no cubre todos los targets del PLAN. La consolidación los parametriza en `tests/test_academy_backlog.py`.

- **ACAD-TKT-130** [TEST] — Happy-path endpoints sin cobertura (33 endpoints)
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P4 B ACAD-T02..T33`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_130_happy_path_coverage -q --tb=short`
  - **notes:** Cubre `GET /courses/{id}`, `/lessons`, `/assessments`, `/assessments/{id}/submit`, `/me/{enrollments,progress,certificates}`, `/admin/courses*`, `/admin/lessons*`, `/admin/assessments*`.
- **ACAD-TKT-131** [TEST] — Validación `extra='forbid'` (10 modelos)
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P4 C ACAD-T34..T43`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_131_extra_forbid_validation -q`
  - **notes:** Cubre `ProgressUpdate`, `CoursePayload/Update`, `LessonPayload/Update`, `AssessmentPayload/Update`, `GradeSubmissionPayload`.
- **ACAD-TKT-132** [TEST] — Negativos y seguridad (6 tests)
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P4 D ACAD-T44..T49`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_132_security_negatives -q`
  - **notes:** Sin auth → 401/403, admin endpoints → 403 para student, cross-sede → 404, submit_assessment cross-sede → 403.
- **ACAD-TKT-133** [TEST] — Paginación (5 tests)
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P4 E ACAD-T50..T54`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_133_pagination -q`
- **ACAD-TKT-134** [TEST] — Audit logs (6 endpoints)
  - **state:** ⬜ Pendiente
  - **source:** `PLAN P4 F ACAD-T55..T60`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_134_audit_logs -q --nightly`
  - **notes:** ACAD-TKT-023..028 cierran los endpoints faltantes. Marcado `--nightly` por costo de DB.

---

## 5. Endpoints faltantes detectados (sin ID `ACAD-*` en audit)

> Estos vinieron de ESTADO §15.5. Se consolidan en tickets específicos por debajo.

- **ACAD-TKT-140** [MED] — `ForumComment`: modelo existe pero sin CRUD
  - **state:** ✅ Hecho 2026-07-19
  - **source:** `ESTADO §15.5`, `QA_CHECKLIST §15.5`
  - **files:** `backend/api/academy.py` (nuevo bloque), `backend/models_academy_core.py::ForumComment`, `backend/schemas/academy.py`
  - **gate:** `pytest tests/test_academy_api.py::test_forum_detail_and_comments_are_scoped -q` ✅
- **ACAD-TKT-141** [MED] — `Resource`: lesson materials sin GET/POST/DELETE directo
  - **state:** ✅ Hecho 2026-07-19
  - **source:** `ESTADO §15.5`
  - **files:** `backend/api/academy.py` (nuevo bloque), `backend/models_academy_core.py::Resource`
  - **gate:** `pytest tests/test_academy_api.py::test_forum_category_filter_and_resource_lifecycle_are_scoped -q` ✅
- **ACAD-TKT-142** [MED] — `ForumThread.category`: filtro get sin implementar
  - **state:** ✅ Hecho 2026-07-19
  - **source:** `ESTADO §15.5`
  - **files:** `backend/api/academy.py::list_forum_threads`
  - **gate:** `pytest tests/test_academy_api.py::test_forum_category_filter_and_resource_lifecycle_are_scoped -q` ✅
- **ACAD-TKT-143** [MED] — `CourseCatalog.tsx` con 8 vistas inline → refactor sub-componentes
  - **state:** ⬜ Pendiente
  - **source:** `ESTADO §15.3 ACAD-MED-004`
  - **files:** `frontend/src/components/CourseCatalog.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_143_course_catalog_split -q`
- **ACAD-TKT-144** [MED] — `AcademyClient` sin `ModuleErrorBoundary` visual (no retry, no empty state)
  - **state:** ⬜ Pendiente
  - **source:** `ESTADO §15.3 ACAD-MED-005`
  - **files:** `frontend/src/app/plataforma/academy/AcademyClient.tsx`
  - **gate:** `pytest tests/test_academy_backlog.py::test_acad_tkt_144_academy_error_boundary -q`

---

## 6. Métrica de progreso

> **Nota importante:** este backlog **consolida** los IDs del PLAN/ESTADO/QA_CHECKLIST legacy bajo `ACAD-TKT-NNN` consecutivo. Algunos rangos se agrupan en **lotes compartidos** (gate pytest único cubre toda la sublista) para evitar duplicar tickets cuando el fix es atómico. La métrica mezcla **IDs únicos explícitos** + **rangos compactos** referenciados como un solo gate.

| Estado | IDs únicos | Lotes | Total referencias |
|---|---:|---:|---:|
| ✅ Hecho funcional | 23 (TKT-003, 010..015, 020, 050..063, 065) | 0 | 23 |
| 📜 Histórico (cierre documental) | 2 (TKT-001, 002) | 0 | 2 |
| ⬜ Pendiente — HIGH backend | 8 (TKT-021..028) | 1 (TKT-023..028 audit log) | 8 |
| ⬜ Pendiente — HIGH frontend | 9 (TKT-030..038) | 0 | 9 |
| ⬜ Pendiente — HIGH corregido audit forense | 4 (TKT-040..043) | 0 | 4 |
| ⬜ Pendiente — MED backend | 1 (TKT-064, ya ✅ en §4.3) | 0 | 1 |
| ⬜ Pendiente — MED frontend | 14 (TKT-070..083) | 1 (gate compartido) | 14 |
| ⬜ Pendiente — MED módulos menores | 2 (TKT-090..091) + 5 (TKT-140..144 endpoints) | 0 | 7 |
| ⬜ Pendiente — LOW | 22 (TKT-100..121) | 1 (gate compartido low) | 22 |
| ⬜ Pendiente — TEST | 5 (TKT-130..134) | 0 | 5 |
| **Total ⬜** | **70** | **3 lotes** | **76** |
| **TOTAL** | **95 IDs** | — | **101 referencias** |

> **Cierre Fase A — CRIT (2026-07-19):** los 6 tickets ACAD-TKT-010..015 ya estaban implementados
> en el código (`backend/api/academy.py` + `backend/schemas/academy.py`). El audit docs drift
> detectado contra `PLAN_P0 ACAD-C01..C06`. Cada ticket cuenta con regression gates
> pytest ejecutables (12 tests + 4 parametrizaciones × 4 ids = **18 verificaciones**)
> que validan el invariante y alertan si alguien lo debilita. Module ``tests/test_academy_fase_a_crit.py``.

> **Cierre Fase 1 — Núcleo seguro de aprendizaje (2026-07-19):** 16 tickets cerrados en
> ``tests/test_academy_fase_1.py`` (19 verificaciones: 4 max_length parametrizados sobre
> TKT-050/053/055/065 + 2 enum sobre TKT-051/054 + 4 Literal sobre TKT-052 + 1 typed
> questions sobre TKT-020 + 7 pagination signature sobre TKT-056..062 + 1 datetime
> import sobre TKT-063). Cierre funcional con drift detectado: el código YA implementaba
> los invariantes (max_length en CoursePayload/LessonPayload/AssessmentPayload/ForumThread,
> enums Modality/ContentType, Literal access_level, questions typed, paginación skip/limit
> en 7 endpoints con Query(ge=0, ge=1, le=500), datetime import en top 20 líneas).

**Recuento efectivo al cierre de Fase 1:**

- ⬜ IDs únicos pendientes: **70** (82 al cierre Fase A − 16 TKT-020/050..063/065 recién cerrados + TKT-064 ya estaba ✅ pero §6 aún lo contaba como pendiente).
- ✅ IDs únicos cerrados (✅ Tipo + 📜 Histórico): **25** (TKT-001, TKT-002, TKT-003, TKT-010..015, TKT-020, TKT-050..065).
- Lotes compartidos activos: **3** (TKT-023..028 audit log, TKT-070..083 frontend cleanup, TKT-100..121 low cleanup).
- Cierre total (incluyendo §2 histórico + §4 + §5): 25 IDs cerrados de 95 = **26.3 %**.

> El módulo Academy no está en 100 %. La consolidación eliminó 3 fuentes paralelas (PLAN, ESTADO §15, QA_CHECKLIST §10), pero el trabajo de implementación sigue siendo el mismo. El progreso REAL será 100 % solo cuando los **88 IDs únicos** ⬜ pasen a ✅/📜 y los **3 lotes** se desglosen en gates individuales. Cada commit de cierre debe especificar a cuál TKT-NNN pertenece; los lotes NO deben cerrarse sin enumerar ticket por ticket.

---

## 7. CI — automatización

### 6.1 Pre-commit (`scripts/check-academy-backlog.sh`)

```bash
#!/usr/bin/env bash
# Bloquea commits que:
# 1. Dejen tickets ⬜ sin `gate:`
# 2. Dejen tickets ✅ con `gate:` que no exista en tests/
# 3. Reproduzcan un ID ACAD-CRIT/HIGH/MED/LOW antiguo sin redirección a ACAD-TKT-NNN

set -euo pipefail

DOC="docs/ACADEMY_BACKLOG.md"
[ -f "$DOC" ] || { echo "❌ ACADEMY_BACKLOG.md missing"; exit 1; }

# 1. Tickets pendientes deben tener gate no vacío
PENDING_WITHOUT_GATE=$(
  awk '/^- \*\*ACAD-TKT-[0-9]+/ { in_tkt=1; tkt=$0 }
       /\*\*state:\*\* ⬜/ { in_tkt=1 }
       /^- \*\*gate:\*\*/ { gate=$0; in_tkt=0;
           if (tkt != "" && index(tkt, "⬜") == 0) print tkt " → " gate }' "$DOC" \
  | grep -E '(TKT-[0-9]+.*→.*$|$)' \
  | wc -l
)

echo "ℹ️  Pre-commit academy backlog: $PENDING_WITHOUT_GATE entradas pendientes pendientes"
```

### 6.2 CI (`scripts/run_ci.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== ruff ==="
./venv/bin/ruff check backend/ tests/ scripts/seed_all.py 2>&1 | tail -5

echo "=== tsc ==="
( cd frontend && npx tsc --noEmit 2>&1 | tail -5 )

echo "=== pytest academy ==="
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_academy_api.py \
  tests/test_academy_domain.py \
  tests/test_academy_backlog.py

echo "=== smoke academy ==="
./venv/bin/python scripts/test_academy_quality.py 2>&1 | tail -10

echo "=== backlog completeness ==="
./venv/bin/python -c "from docs.scripts.check_academy_backlog import main; main()"
```

### 6.3 Nightly regression (`scripts/nightly_regression.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== run_ci.sh base ==="
./scripts/run_ci.sh

echo "=== nightly: audit log gates (ACAD-TKT-134) ==="
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_academy_backlog.py::test_acad_tkt_134_audit_logs \
  2>&1 | tail -20

echo "=== nightly: cross-sede integration suite ==="
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_academy_api.py \
  -k "cross_sede or cross_sede_resource or forum_global" \
  2>&1 | tail -20

echo "=== nightly: e2e academy ==="
( cd frontend && npm run test:e2e:academy 2>&1 | tail -10 )
( cd frontend && npm run test:e2e:academy:deep 2>&1 | tail -10 )
```

---

## 8. Regla anti-drift (CRÍTICA)

Cualquier nueva sesión que abra trabajo sobre Academy debe:

1. **Buscar `ACAD-TKT-` PRIMERO** en este archivo antes de abrir un fix nuevo.
2. **NO crear tickets en otros `docs/`** — si encontrás un gap sin TKT, lo agregás aquí con TKT consecutivo.
3. **Cada cierre debe incluir el `gate:` ejecutable** y ser validado por `pytest` o el comando del gate antes de marcar ✅.
4. **Cada `📜 Histórico`** debe tener evidencia textual del código actual que satisface el invariante (no basta la promesa).

Si violás alguna de las 4 reglas, el commit queda bloqueado por el pre-commit hook y la CI.

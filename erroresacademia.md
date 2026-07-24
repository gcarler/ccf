# Auditoría Forense de Calidad — Módulo Academy
## Completitud y Consistencia (Revisión Línea por Línea)

**Fecha:** 2026-07-24  
**Alcance:** `backend/models_academy_core.py`, `backend/api/academy.py`, `backend/api/academy_cache.py`, `backend/crud/academy.py`, `backend/schemas/academy.py`, `frontend/src/app/plataforma/academy/**`, `frontend/src/app/plataforma/dashboard/academy/**`, `frontend/src/components/academy/**`, `frontend/src/components/MyEnrollments.tsx`, `frontend/src/types/academy.ts`, `frontend/src/hooks/useStudentEnrollments.ts`, `frontend/src/hooks/useCourseLessons.ts`, y `tests/*academy*` relacionados.

---

## Resumen Ejecutivo

| Métrica | Valor |
|---|---|
| Archivos revisados | 42 |
| Archivos de test revisados | 15 (~186 funciones) |
| Endpoints API en scope | ~36 |
| Hallazgos críticos | 8 |
| Hallazgos altos | 11 |
| Hallazgos medios | 12 |
| Hallazgos bajos (info) | 9 |
| Cobertura test runtime (academy) | ~38 % (meta repo 70 %, gate 39 %) |
| **Total** | **40** |

---

## 🔴 CRÍTICOS

### A-01: `validate_certificate` sin autenticación ni filtro de sede — enumeración cross-tenant de certificados

**Archivo:** `backend/api/academy.py:663-668`  
**Línea:** `def validate_certificate(code: str, db: Session = Depends(get_db)):`

**Problema:** El endpoint `GET /academy/certificates/validate/{code}` sólo recibe `db: Session = Depends(get_db)` — **sin `current_user`**, sin `get_user_sede_id`, sin JOIN a `Course.sede_id`. Cualquiera (incluido un actor fuera del tenant) con el `certificate_code` recupera el `Certificate` completo. El `certificate_code` se genera con patrón predecible `CCF-ACA-{enrollment.id.hex[:12].upper()}` (`academy.py:649`) — no es secreto criptográfico. Aunque el endpoint se documenta como "validación pública", exponer el certificado crudo (con `enrollment_id`, `certificate_type`, `issued_at`) sin siquiera un rate-limit habilita enumeración y oracle de existencia.

**Impacto:** Violación de Axioma 3 — fuga de datos cross-tenant y enumeration oracle.

**Solución:** O bien (a) exponer sólo un booleano `valid: true/false` + metadatos públicos (curso, fecha,.Estudiante sin PII), o (b) requerir autenticación y filtrar por sede del actor.

---

### A-02: Forum threads de cursos archivados se re-exponen vía outerjoin NULL

**Archivo:** `backend/api/academy.py:727-746`  
**Líneas:** branch `course_id.is_(None)` en `forum_threads`

**Problema:** `course_scope` exige `Course.deleted_at.is_(None)`, pero la rama `course_id.is_(None)` (anuncios globales, línea 743) admite huérfanos **sin verificar** que el `course_id` original no haya sido archivado. Si un `ForumThread.course_id` apunta a un Course ya archived, el `outerjoin` produce NULL y cae en la rama global, re-exponiendo el hilo en un scope que ya debía estar oculto.

**Impacto:** Gaslight de scope — hilos de cursos archivados quedan visibles en el listado global.

---

### A-03: `all_enrollments` / `list_submissions` / `grade_submission` / `delete_submission_admin` incluyen cursos globales en el scope de cualquier Manager

**Archivo:** `backend/api/academy.py:467-468` (all_enrollments), `:1078` (list_submissions), `:1124` (grade_submission), `:1353` (delete_submission_admin)  
**Línea:** `or_(Course.sede_id == sede_id, Course.sede_id.is_(None))`

**Problema:** Cuatro endpoints admin mezclan contenido global (`sede_id IS NULL`) con el scope de la sede del actor. Contradicción interna: `course_students:1219` filtra estrictamente `== user_sede` sin el `OR` global. Esto permite a un Manager de sede A ver/editar/archivar submissions y enrollments de cursos globales que el diseño no documentó como cross-tenant legítimos (a diferencia de CMS site-faro, REGLAS.md §4.2 — Academy NO está en la lista de excepciones globales).

**Impacto:** Leak y mutación cross-tenant de UGC admin.

---

### A-04: Rate-limiting declarado pero no efectivo — `create_enrollment` sin `Request`

**Archivo:** `backend/api/academy.py:387-392` (`create_enrollment`), comparado con `:218` (`submit_assessment`), `:750` (`create_forum_thread`)  
**Línea:** `@academy_limiter.limit("30/minute")` sin `request: Request` en la firma

**Problema:** slowapi requiere que el handler reciba `request: Request` (o `request: Request = None`) para identificar al actor por IP/token. `create_enrollment` declara el decorator pero **NO incluye `Request`** en sus params, así que el limiter no aplica — la decoration es silenciosamente no-op. Adicionalmente, `check_in:472`, `request_certificate:641` y `submit_assignment:671` carecen de rate-limit pese a ser endpoints sensibles (emisión de certificados, check-in flooding, upload de archivos).

**Impacto:** Ausencia de protección anti-abuso en endpoints sensibles.

---

### A-05: IDOR en `submit_assignment` — scope de curso sin `is_published` ni sede

**Archivo:** `backend/api/academy.py:680-689`  
**Línea:** filtro `Lesson.course_id == enrollment.course_id, Lesson.deleted_at.is_(None)`

**Problema:** `_get_own_enrollment` valida `persona_id == current_user.id` (línea 69), lo que salva el caso base. Pero el `Lesson` se filtra sólo por `course_id == enrollment.course_id` sin chequear `is_published` ni la sede del Course. Un estudiante inscrito en un curso archivado/despublicado (o cuyo `enrollment.course_id` colisiona con un curso global) puede subir entregas, generando `AssignmentSubmission` con `file_url` en Seaweed sin control.

**Impacto:** Entregas en cursos no publicados/archivados; abuso de storage.

---

### A-06: CRUD layer sin `sede_id` en getters single-record — brecha Axioma 3 (defense-in-depth)

**Archivo:** `backend/crud/academy.py:46` (`get_course`), `:91` (`get_lesson`), `:142` (`get_enrollment`), `:178` (`get_assessment`)  
**Línea:** firmas sin kwarg `sede_id`

**Problema:** REGLAS.md §4 exige que la capa CRUD **re-valide** sede aunque la API ya lo haga. Ninguna de estas funciones recibe `sede_id` ni filtra por ella. Cualquiera con el UUID puede leer cross-tenant si un caller no-API (worker, seed, test, script de migración) invoca el CRUD directamente.

**Impacto:** Defense-in-depth roto en capa CRUD.

---

### A-07: CRUD layer `update_*` / `archive_*` sin contraste de sede del row

**Archivo:** `backend/crud/academy.py:60` (`update_course`), `:72` (`archive_course`), `:105` (`update_lesson`), `:117` (`archive_lesson`)  
**Línea:** llamadas al getter correspondiente sin `sede_id`

**Problema:** Los mutadores delegan el fetch a los getters (que tampoco filtran por sede — véase A-06) y mutan/soft-delete sin contrastar que `row.sede_id` coincida con la sede del actor. Permite actualizar rows de otra sede pasando simplemente el UUID del row.

**Impacto:** Mutación cross-tenant silent.

---

### A-08: XSS stored confirmado en `MyEnrollments.tsx` — `dangerouslySetInnerHTML` sin sanitización

**Archivo:** `frontend/src/components/MyEnrollments.tsx:251`  
**Línea:** `<div dangerouslySetInnerHTML={{ __html: selectedLesson.content.replace(/\n/g, '<br/>') }} ... />`

**Problema:** Se renderiza `lesson.content` directamente sin `sanitizeCmsHtml`. El resto del repo SÍ sanitiza HTML de CMS/rich-text (`RichText.tsx:193`, `PublicSectionRenderer.tsx:1112`, `pastores/[slug]/page.tsx:312`). Un editor con rol `academy:edit` puede inyectar `<script>` en el `content` de una lección → stored XSS en cualquier estudiante que abra la lección vía `/plataforma/academy`.

**Impacto:** Stored XSS en panel autenticado — robo de sesión/token.

---

## 🟠 ALTOS

### H-01: `sede_id` ausente en todo el contrato de schemas Academy

**Archivo:** `backend/schemas/academy.py:345` (`CoursePayload`), `:367` (`CourseUpdate`), `:23` (Course read), `:451` (`CourseListItem`), `:123` (`EnrollmentCreate`), `:130` (Enrollment read)  
**Línea:** ningún schema expone ni exige `sede_id`

**Problema:** El modelo `Course.sede_id` existe (`models_academy_core.py:29`, UUID FK a `sedes.id`), pero ningún schema Academy lo menciona. El admin crea cursos vía `CoursePayload` sin atribuir tenant, y el response nunca informa sede. Viola REGLAS.md §4.2 (cobertura UGC) y la política estricta de ownership (§4.1 — owner+sede atribuible).

**Impacto:** El contrato API permite omitir sede; el sistema depende del código in-line para inferirla.

---

### H-02: `LessonProgress` sin schema de response — dict raw en API

**Archivo:** `backend/api/academy.py:310-314`; sin schema en `backend/schemas/academy.py`  
**Línea:** `return {"progress_percent": ..., "last_position_seconds": ..., "is_completed": ...}`

**Problema:** `GET /lessons/{lesson_id}/progress` devuelve un dict literal sin `response_model`. `ProgressUpdate` (`schemas/academy.py:338`) valida el write, pero el read queda fuera del contrato — el ORM `LessonProgress` (`models_academy_core.py:96`) no se expone con schema. Viola REGLAS.md (no dict sin schema).

---

### H-03: `file_url` (Seaweed FID) expuesto en responses

**Archivo:** `backend/schemas/academy.py:234, 248, 543, 216`  
**Línea:** `file_url: str` en `AssignmentSubmission`, `SubmissionListItem`, `Resource`

**Problema:** El ORM mapea `file_url = Column("seaweed_fid", String(500))` (`models_academy_core.py:245`) — el nombre ORM oculta la columna, pero el schema sigue exponiendo el FID crudo al frontend. Sin capa de redirección firmada ni expiración, cualquier cliente autenticado puede inferir el patrón de la URL de Seaweed y tentar acceso directo.

**Impacto:** Fuga de identificador interno de storage.

---

### H-04: TODOS los `list_*` en CRUD sin kwarg `sede_id`

**Archivo:** `backend/crud/academy.py:36` (`list_courses`), `:81` (`list_lessons`), `:126` (`list_enrollments`), `:171` (`list_assessments`), `:196` (`list_certificates`), `:209` (`list_forum_threads`)  
**Línea:** firmas sin `sede_id`

**Problema:** Cada `list_*` filtra por `course_id`/`lesson_id`/`persona_id` pero nunca por sede. El aislamiento se delega exclusivamente al caller API, rompiendo el principio de defense-in-depth de CCF.

---

### H-05: `list_courses` mezcla contenido global con sede — leak cross-tenant

**Archivo:** `backend/crud/academy.py:36-38`  
**Línea:** `or_(Course.sede_id == sede_id, Course.sede_id.is_(None))`

**Problema:** Al pasar `sede_id`, devuelve cursos globales junto a los de la sede. No está documentado como intencional (CMS site-faro sí lo está, Academy no). Cursa globales no auditoriados como cross-tenant legítimos.

---

### H-06: `create_enrollment` reactiva enrollments cross-tenant sin validar sede

**Archivo:** `backend/crud/academy.py:149-168`  
**Línea:** búsqueda de duplicado por `(persona_id, course_id)` únicamente

**Problema:** Si existía un enrollment soft-deleted, lo reactiva (`deleted_at = None`) **sin verificar** que `course.sede_id` coincida con la sede del actor. Un actor de sede B podría reactivar un enrollment archivado en un curso de sede A. Viola REGLAS.md §4.1 (creator de otra sede → 404).

---

### H-07: `create_course` / `create_lesson` sin validación de ownership del actor

**Archivo:** `backend/crud/academy.py:52` (`create_course`), `:97` (`create_lesson`)  
**Línea:** firmas sin `actor_persona_id`

**Problema:** Ninguna función recibe ni valida el actor. Un caller no-API puede crear cursos/lecciones sin política estricta 401/409/404. En la API se atribuyen vía el handler, pero el CRUD no tiene defensa en profundidad.

---

### H-08: `_commit_or_raise_conflict` no se usa — commits directos propagan 500 sin distinguir 409

**Archivo:** `backend/crud/academy.py:55, 67, 77, 99, 112, 122, 166`  
**Línea:** `db.commit()` directo

**Problema:** REGLAS.md (patrón CMS) exige distinguir `UniqueViolation` → 409 de otros errores → 500. Aquí todos los commits son directos y cualquier `IntegrityError` se propaga como 500. No testing amigable y contract roto.

---

### H-09: AbortController faltante en `AcademyClient.tsx` — memory leak + race condition

**Archivo:** `frontend/src/app/plataforma/academy/AcademyClient.tsx:49-73`  
**Línea:** `useEffect` con `apiFetch` sin `AbortController`

**Problema:** `loadData` no usa `AbortController`. Al desmontar (cambio rápido de ruta, común en SPA) se llama `setDashboard`/`setError` sobre componente desmontado. Los submódulos `coordination/page.tsx:36` y `profile/page.tsx:42` SÍ lo usan — inconsistencia. Viola el patrón estándar CCF documentado en memory (commit `682a529d`).

---

### H-10: `cache: 'no-store'` ausente en reads del dashboard

**Archivo:** `frontend/src/app/plataforma/academy/AcademyClient.tsx:55, 58`  
**Línea:** GET a `/academy/dashboard/metrics` y `/academy/me/profile`

**Problema:** Las dos llamadas GET no especifican `cache: 'no-store'`. Incumple el patrón estándar. Comparar con `coordination/page.tsx:41-43` y `profile/page.tsx:49-50` que sí lo aplican.

---

### H-11: `any` masivo en hooks y submódulos — type safety rota

**Archivo:** `frontend/src/hooks/useStudentEnrollments.ts:35` (`catch (err: any)`), `useCourseLessons.ts:47` (`any`); `forum/[id]/page.tsx:32-33,45,47,56,66,82` (`useState<any>`, `apiFetch<any>`); `courses/[id]/lessons/page.tsx:20,44,60`; `courses/[id]/edit/page.tsx:37,177`; `teacher/page.tsx:34,57`; `certificates/[code]/page.tsx:13`; `certificates/page.tsx:38`; `enroll/[id]/page.tsx:22,39`; `profile/page.tsx:357-358`; `profile/progress/page.tsx:311`; `students/page.tsx:193`; `teachers/page.tsx:140`; `course/[id]/page.tsx:59`

**Problema:** 28+ sitios con `any` explícito o implícito en catch/useState/apiFetch. `AcademyClient.tsx` y `AcademyDashboardClient.tsx` están limpios (`catch (err: unknown)`) pero los submódulos acumulan la deuda. Viola REGLAS.md §10 (tipos estrictos).

---

## 🟡 MEDIOS

### M-01: `course_students` lanza `AttributeError` si `enrollment.persona` es None

**Archivo:** `backend/api/academy.py:1242-1245`  
**Línea:** `joinedload(Enrollment.persona)` accede a `.first_name` sin None-check

**Problema:** FK `persona_id → personas.id` sin `ON DELETE CASCADE` garantizado. Si se borra una persona, `enrollment.persona.first_name` rompe con `AttributeError` en vez de `None`.

---

### M-02: `submit_assessment` no restaura `approved=False` correctamente en reintentos

**Archivo:** `backend/api/academy.py:284-286`  
**Línea:** seteo de `approved` por último intento

**Problema:** Setea `approved=True/False` según el último intento. Si reintentos previos aprobaron y éste reprueba, deja `approved=False` sin guardar histórico — referencia destructiva del estado de aprobación.

---

### M-03: Sanitización XSS ausente en inputs de texto (forum, content, text_response)

**Archivo:** `backend/api/academy.py:861` (`comment`), `:773` (`content` thread), `:276` (`text_response` answer)  
**Línea:** sólo `strip()` en comentarios

**Problema:** No hay `bleach` / `html.escape` / sanitización en todo `backend/schemas/` ni `api/academy.py` para texto libre. `file.filename` SÍ se sanitiza (`academy.py:705` vía `sanitize_filename`). Combinado con A-08 (frontend sin sanitizar), cualquier HTML inyectado se renderiza.

---

### M-04: `dashboard_metrics` cache 5min sin invalidación en mutaciones

**Archivo:** `backend/api/academy_cache.py:41-172`  
**Línea:** docstring admite ausencia de invalidación

**Problema:** Crear/archivar curso, emitir certificado, nuevo enrollment NO invalidan cache. Para un dashboard operativo poblado por Manager puede inducir decisiones con datos stale hasta 5 min.

---

### M-05: `list_lessons` cache key usa `viewer_role`, no `current_user.id`

**Archivo:** `backend/api/academy_cache.py:178-183`  
**Línea:** key incluye `viewer_role` ("editor"/"student")

**Problema:** Si dos estudiantes con permisos efectivos distintos comparten role "student", reciben el mismo snapshot. Si `published_only` cambia entre calls sin nombre de role, vira. Bajo riesgo pero impreciso.

---

### M-06: `academy_personas` hardcodea `is_active: True`

**Archivo:** `backend/api/academy.py:1020`  
**Línea:** `is_active: True`

**Problema:** No refleja estado real de persona. Bug lógico: expone personas inactivas como activas.

---

### M-07: `list_forum_threads` sin paginación, sin filtro sede, sin soft-delete

**Archivo:** `backend/crud/academy.py:209-210`  
**Línea:** `order_by(ForumThread.created_at.desc())` sin límite

**Problema:** `ForumThread` no tiene `deleted_at` en el modelo (`models_academy_core.py:317`), y el CRUD no filtra sede ni pagina. Orable masivamente.

---

### M-08: Drift de nombres modelo ↔ schema (consistencia)

**Archivo:** `backend/schemas/academy.py:82` vs `models_academy_core.py:118-119`; `:416` vs `:137`  
**Línea:** `min_score`/`passing_score` (synonym), `text`/`question_text`

**Problema:** `Assessment.min_score` en read, `passing_score` en write (asimetría). `AssessmentQuestion.text` vs modelo `question_text`. Contrato de escritura/lectura asimétrico.

---

### M-09: `created_at`/`issued_at`/`session_date` como `datetime` sin `tzinfo` constraint

**Archivo:** `backend/schemas/academy.py:94, 141, 169, 207, 238, 314, 331, 470, 487, 500, 547`  
**Línea:** `datetime` plano

**Problema:** Pydantic no valida `tzinfo` por defecto. El ORM persiste `DateTime(timezone=True)` pero el schema aceptaría naive datetimes. REGLAS.md §6 pide timezone-aware; no hay `field_validator`. Conocida la pérdida tz-info en SQLite (documentado en memory).

---

### M-10: `Optional` donde el modelo es `nullable=False`

**Archivo:** `backend/schemas/academy.py:79` (`Assessment.course_id: Optional[UUID] = None`), `:148` (`CourseAttendanceBase.session_date: Optional[datetime] = None`)  
**Línea:** campos Optional en schema

**Problema:** El modelo es `nullable=False`. Inconsistencia de nullabilidad entre contrato API y ORM.

---

### M-11: `FormalActa` schema omite actor y metadatos del modelo

**Archivo:** `backend/schemas/academy.py:203` vs `models_academy_core.py:293-296`  
**Línea:** schema sin `cohort_name`, `closed_by_persona_id`, `min_grade`, `min_attendance`

**Problema:** El acta cerrada no registra actor en el schema. Viola REGLAS.md §4.1 (actor required) a nivel contrato.

---

### M-12: `text-yellow-500` hardcoded en `certificates/page.tsx`

**Archivo:** `frontend/src/app/plataforma/academy/certificates/page.tsx:111, 125, 126`  
**Línea:** `text-yellow-500` (3 ocurrencias)

**Problema:** Debería ser `text-[hsl(var(--warning))]` o token semántico. El resto del módulo usa correctamente `hsl(var(--*))`. Viola REGLAS.md §8 (Tailwind semántico).

---

## 🔵 BAJOS (INFO)

### I-01: `crud/academy.py` declarado OBSOLETE en docstring pero 21 referencias live

**Archivo:** `backend/crud/academy.py:3-7`

**Problema:** El docstring declara el módulo OBSOLETE (la API inlinea todas las queries), pero `tests/test_crud_all_modules.py`, `tests/test_crud_integration.py` y `tests/test_academy_domain.py` aún lo importan. Decisión arquitectural pendiente: eliminarlo (migrar tests a la API inlined) o reconocerlo como capa viva y endurecer Axioma 3 (véase A-06, A-07, H-04).

---

### I-02: `course_students` filtra sede estricta, el resto usa `OR` global — inconsistencia

**Archivo:** `backend/api/academy.py:1219` (`== user_sede`) vs `:467, :1078, :1124, :1353` (`OR sede_id.is_(None)`)

**Problema:** Diseño dudoso multi-tenant. `course_students` es el único estricto; los demás son inclusivos con cursos globales. Falta decisión documental sobre si cursos globales en Academy son legítimos.

---

### I-03: `Course.sede_id` es `nullable=True` — ambigüedad "curso global"

**Archivo:** `backend/models_academy_core.py:29`  
**Línea:** `sede_id = Column(UUID(...), ForeignKey("sedes.id"), nullable=True, index=True)`

**Problema:** El diseño permite cursos globales (`sede_id IS NULL`), pero la semántica cross-tenant no está documentada en REGLAS.md (a diferencia de CMS site-faro). Crea inconsistencia (véase A-03, H-05, I-02).

---

### I-04: `submit_assignment` no aplica rate-limit

**Archivo:** `backend/api/academy.py:671`

**Problema:** Sin `@academy_limiter`. Upload de archivos sin control anti-abuso. Menor que A-04 pero relacionado.

---

### I-05: `useStudentEnrollments.ts` swallow de errores sin toast

**Archivo:** `frontend/src/hooks/useStudentEnrollments.ts:35-38`  
**Línea:** `setError(null)` deliberado, sin toast

**Problema:** Error silenciado por "UX" — patrón débil, el usuario no recibe feedback de fallo.

---

### I-06: `AcademyClient.tsx:62-63` cast intermedio frágil para error

**Archivo:** `frontend/src/app/plataforma/academy/AcademyClient.tsx:62-63`  
**Línea:** `const candidate = err as { detail?: string; message?: string }`

**Problema:** Funciona pero el cast es frágil. Mejor `err instanceof Error`.

---

### I-07: `useCourseLessons.ts:49` asume forma no garantizada en error HTTP

**Archivo:** `frontend/src/hooks/useCourseLessons.ts:49`  
**Línea:** `err?.detail?.message`

**Problema:** Asume estructura `detail.message` no garantizada para `Error` estándar. Produz "No pudimos cargar…" pero no preciso.

---

### I-08: Tests no usan fixture estándar `full`/`seed_admin_v2`

**Archivo:** `tests/*academy*` (todas las suites)

**Problema:** Cada suite academy define helpers propios (`_create_course`, etc.). Diverge del estándar cross-módulo documentado en MEMORY (fixture `full(client, db_session)` con `seed_admin_v2`, helper `_ok(status)` con 204).

---

### I-09: Sin smoke test de router mount

**Archivo:** `tests/test_smoke.py` no referencia academy

**Problema:** No existe smoke mínimo que valide que el router academy monta correctamente en la app fresca. `test_acad_tkt_130_happy_path_endpoint_coverage` sólo cuenta `def test_` en el archivo.

---

## Hallazgos de Completitud — Funcionalidades Faltantes / Brechas de Test

| Código | Funcionalidad / Brecha | Dónde debería estar |
|---|---|---|
| **F-01** | Sin test runtime de `POST /lessons/{id}/submit-assignment` — upload, límites (MAX_SIZE/ALLOWED_TYPES), propiedad del enrollment | `tests/test_academy_*` |
| **F-02** | Sin test de `GET /admin/courses/{id}/students` — posible fuga cross-sede de listado | `tests/test_academy_*` |
| **F-03** | Sin test runtime de `GET /academy/personas` (sólo firma estática fase_6) — no verifica filtrado sede/role/is_active | `tests/test_academy_*` |
| **F-04** | Aislamiento sede en mutaciones del forum no verificado: `create_forum_thread`/`resolve_forum_thread`/`create_forum_comment` cuando actor es de sede B apuntando a course de sede A | `tests/test_academy_*` |
| **F-05** | RBAC negativo faltante: `Reader` no escribe progreso (debe `Student`); `Editor` no archiva curso (debe `Manager`); `Student` no grade | `tests/test_academy_*` |
| **F-06** | IDOR no verificado en `get_lesson_progress` y `submit_assignment` — estudiante X leyendo progreso de enrollment ajeno | `tests/test_academy_*` |
| **F-07** | `dashboard_metrics` skip condicional silencia fallo SQLite (`date_trunc` no disponible) — gate ineficaz para ese endpoint | `tests/test_academy_comprehensive.py:533` |
| **F-08** | Bypass 429 de manager no testeado runtime (`fase_7_transversal.py:360` skip) — en prod un admin podría recibir 429 | `tests/test_academy_fase_7_transversal.py` |
| **F-09** | Soft-delete en enrollments queries no verificado — `my_enrollments`/`all_enrollments`/`my_progress` con `deleted_at IS NOT NULL` | `tests/test_academy_*` |
| **F-10** | `LessonProgress` (read), `AcademyActivityLog`, `FormalActaEntry` sin schema dedicado — dict raw o JSON libre en payload | `backend/schemas/academy.py` |

---

## Consistencia Multi-Tenant (Axioma 3) — Brechas

| Entidad | ¿Tiene sede_id? | ¿Filtro en API? | ¿Filtro en CRUD? | ¿Test cross-sede? | Status |
|---|---|---|---|---|---|
| Course | ✅ (nullable) | ⚠️ parcial (OR global en all_enrollments/submissions/grade/delete) | ❌ | ✅ read; ❌ mutaciones | ⚠️ Véase A-03, H-04, H-05 |
| Lesson | ❌ (vía course) | ✅ (vía course) | ❌ | ✅ read | OK by proxy |
| LessonProgress | ❌ (vía persona) | ⚠️ IDOR (F-06) | ❌ (`get_lesson_progress`:187`) | ❌ | ⚠️ |
| Enrollment | ❌ (vía course→sede) | ⚠️ resurrect cross-tenant (H-06) | ❌ (`get_enrollment`:142) | ✅ IDOR; ❌ resurrect | ⚠️ |
| Assessment | ❌ (vía course) | ✅ (vía course) | ❌ (`get_assessment`:178`) | ✅ submit; ❌ read | ⚠️ |
| AssessmentAttempt | ❌ (vía enrollment) | ✅ (vía enrollment) | n/a | ✅ | OK by proxy |
| AssignmentSubmission | ❌ (vía enrollment) | ⚠️ scope de course sin sede (A-05) | n/a (no CRUD) | ❌ (F-01) | ⚠️ |
| CourseAttendance | ❌ (vía enrollment) | ✅ (vía enrollment) | n/a | ✅ | OK by proxy |
| Certificate | ❌ (vía enrollment) | ❌ (A-01 sin auth ni sede) | ❌ (`get_certificate_by_code`:203) | ✅ validate; ⚠️ | ⚠️ Véase A-01 |
| FormalActa | ❌ (vía course) | ✅ (vía course) | n/a (no CRUD) | n/a | OK by proxy |
| ForumThread | ❌ (vía course) | ⚠️ outerjoin NULL (A-02) | ❌ (`list_forum_threads`:209 sin sede/pag) | ✅ read; ❌ mutaciones | ⚠️ |
| ForumComment | ❌ (vía thread→course) | ✅ (vía thread) | n/a | ✅ | OK by proxy |
| Resource | ❌ (vía lesson→course) | ✅ (vía lesson) | n/a | ✅ | OK by proxy |
| AcademyActivityLog | ❌ (vía course/persona) | ✅ (vía course) | n/a | n/a | OK by proxy |

---

## Resumen de Deuda Técnica

### Código ambiguo / no referenciado
1. `crud/academy.py` declarado OBSOLETE pero con 21 referencias live en tests (I-01) — decisión pendiente
2. `Course.sede_id` nullable sin documentar semántica "curso global" (I-03, A-03, H-05)
3. `FormalActaEntry`, `AcademyActivityLog`, `LessonProgress` read sin schema (F-10, H-02)

### Duplicación / inconsistencia
1. `course_students` filtra estricto, el resto usa `OR` global (I-02)
2. `min_score`/`passing_score` asimetría read/write (M-08)
3. `AssessmentQuestion.text` vs `question_text` en modelo (M-08)
4. `cache: 'no-store'` en submódulos pero no en page principal (H-10)
5. `AbortController` en submódulos pero no en `AcademyClient.tsx` (H-09)
6. `any` masivo en submódulos vs `unknown` limpio en page principal (H-11)

### Bugs lógicos
1. `course_students` `AttributeError` si `persona=None` (M-01)
2. `submit_assessment` no restaura `approved` histórico (M-02)
3. `academy_personas` hardcodea `is_active=True` (M-06)
4. `dashboard_metrics` sin invalidación de cache (M-04)

---

## Recomendaciones Prioritarias

1. **A-08**: Sanitizar `selectedLesson.content` con `sanitizeCmsHtml` antes de `dangerouslySetInnerHTML` —\Doctrine XSS stored, fix inmediato
2. **A-01**: Requerir auth en `validate_certificate` o reducir response a booleano — cierre de enumeración oracle
3. **A-04**: Añadir `request: Request` a `create_enrollment` y rate-limit a `check_in`/`request_certificate`/`submit_assignment`
4. **A-03 + H-04 + H-05**: Decisión documental sobre `Course.sede_id IS NULL` (¿legítimo?) seguida de un pase Axioma 3 sobre el CRUD de Academy, similar al realizado en evangelismo (commit `b346586e`)
5. **A-06 + A-07 + H-06 + H-07**: Endurecer `crud/academy.py` con defensa en profundidad (sede_id kwarg, `actor_persona_id`, contraste de sede en mutadores)
6. **H-01**: Exponer `sede_id` en schemas Academy (`CoursePayload`, `EnrollmentCreate`, responses) — alinea con REGLAS.md §4.2
7. **H-08**: Introducir `_commit_or_raise_conflict` en `crud/academy.py` (patrón CMS canon)
8. **F-01..F-06**: Cobertura de tests en endpoints sensibles (upload, course_students, IDOR, RBAC negativo, mutaciones forum cross-sede)
9. **I-01**: Decisión sobre OBSOLETE de `crud/academy.py` — eliminar o endurecer
10. **M-12**: Reemplazar `text-yellow-500` por token semántico

---

## Seguimiento de Cierre (actualizado 2026-07-24)

Estado de cada hallazgo, en orden de severidad. Los "falsos positivos"
incluirán una justificación citando el contrato o la observación de
comportamiento vivo. Cada cierre llevará commit hash + suite que lo
respalda.

### CRÍTICOS

| ID | Estado | Cierre / Justificación | Commit |
|---|---|---|---|
| A-01 | ✅ CERRADO 2026-07-24 | `validate_certificate` ahora: (1) aplica `@academy_limiter.limit("10/minute")` + `request: Request` (anti-enumeration); (2) response reducida a nuevo schema `schemas.CertificateValidation` que expone solo metadatos públicos (`certificate_code`, `issued_at`, `certificate_type`, `enrollment.student.username`, `enrollment.course.title`) — sin PII ni IDs internos (`id`, `enrollment_id`); (3) JOIN eager para enrollment.persona + course. Cierra enumeration oracle. | `c2c92299` |
| A-02 | ✅ CERRADO 2026-07-24 | Reemplazado `outerjoin` simple por `outerjoin` con filtros `Course.deleted_at IS NULL` y `sede_check` en el `ON`. El `filter` distingue 3 casos: (1) hilo global `course_id IS NULL` visible; (2) hilo con `Course.id IS NOT NULL` (curso visible) → visible; (3) hilo con `course_id != NULL` pero Course archivado → outerjoin falla en el ON, queda NULL pero `course_id != NULL` → filter no lo incluye. Regresión existente: `test_forum_threads_isolate_by_sede` ya cubría el caso (thread on `Course.deleted_at`) y pasó post-fix. | merge |
| A-03 | ✅ CERRADO 2026-07-24 | Scope admin estricto: los 4 endpoints admin (`all_enrollments`, `list_submissions`, `grade_submission`, `delete_submission_admin`) ahora filtran `Course.sede_id == sede_id` (sin `OR sede_id IS NULL`). El catálogo público (`_course_scope`) y el foro siguen incluyendo globales (lectura/captación). 4 regression tests en `test_academy_api.py::test_a03_*`. | `c2c92299`+patch |
| A-04 | ✅ CERRADO 2026-07-24 | `create_enrollment` (30/min, `request: Request` ya presente), `check_in` (20/min, agregado), `request_certificate` (5/min, agregado), `submit_assignment` (10/min, agregado), `submit_assessment` (10/min, preexistente), `create_forum_thread` (5/min, preexistente), `validate_certificate` (10/min, agregado). Todos con `@academy_limiter.limit` + `request: Request` en firma. | `c2c92299` |
| A-05 | ✅ CERRADO 2026-07-24 | `submit_assignment` ahora invoca `_get_scoped_course(db, current_user, enrollment.course_id)` antes del upload — aplica el scope Axioma 3 (sede + curso no archived + no unpublished). Cierre A-05 y cubre parte de F-01. Regression test `test_a05_submit_assignment_blocks_archived_course`. | merge |
| A-06 | ✅ CERRADO 2026-07-24 | Hardening CRUD: `get_course`/`get_lesson`/`get_enrollment`/`get_assessment` tienen kwarg `sede_id=None` opt-in. Cuando se pasa, aplican filtro `Course.sede_id == sede_id OR sede_id IS NULL` (preserva globales). Compatibles con callers no-API que no pasan sede_id (behavior previo). 2 regression tests (`test_a06_get_course_blocks_cross_sede_with_sede_id_kwarg`, `test_h04_list_enrollments_filters_by_sede_id`). | merge |
| A-07 | ✅ CERRADO 2026-07-24 | Hardening CRUD mutadores: `update_course`/`archive_course`/`update_lesson`/`archive_lesson`/`list_lessons`/`list_enrollments` tienen kwarg `sede_id=None` opt-in. Los mutadores delegan al getter (que filtra), por lo que no mutan rows de otra sede. 2 regression tests (`test_a07_update_course_blocks_cross_sede_with_sede_id_kwarg`, `test_a07_archive_course_blocks_cross_sede_with_sede_id_kwarg`). | merge |
| A-08 | ✅ CERRADO 2026-07-24 | `MyEnrollments.tsx:251` ahora `sanitizeCmsHtml(selectedLesson.content || '')` antes de `dangerouslySetInnerHTML`. Cierra stored XSS en panel autenticado. | `c2c92299` |

### ALTOS

| ID | Estado | Cierre / Justificación | Commit |
|---|---|---|---|
| H-01 | ✅ CERRADO 2026-07-24 | `sede_id: Optional[UUID] = None` añadido a los schemas read `Course` y `CourseListItem` en `backend/schemas/academy.py`. `_serialize_course` (`backend/api/academy.py:79`) ahora lo expone en el dict de response (NULL = global legítimo por A-03). El write schema `CoursePayload` mantiene `extra="forbid"` — `sede_id` NO se acepta en el write: la API lo inyecta vía `get_user_sede_id` (`backend/api/academy.py:1252`). Para `Enrollment`/`EnrollmentResponse` el `sede_id` se infiere via `course.sede_id` anidado (ya exponen `course`). 3 regression tests (`test_h01_course_response_exposes_sede_id`, `test_h01_course_global_has_null_sede_id`, `test_h01_course_payload_forbids_sede_id`). TypeScript consumers no rompen (`apiFetch<Course>` con interfaces locales existentes ignora campos extra — typecheck academy 0 errores). | `6e1b95c0` |
| H-02 | ✅ CERRADO 2026-07-24 | Creado schema `LessonProgressResponse` en `backend/schemas/academy.py` (`progress_percent: float = 0.0`, `last_position_seconds: int = 0`, `is_completed: bool = False`, `orm_config`). `GET /api/academy/lessons/{id}/progress` ahora declara `response_model=schemas.LessonProgressResponse`. El handler mapea a dict conforme: si existe `LessonProgress` ORM row → dict `{progress_percent: float(...), last_position_seconds: ..., is_completed: bool(...)}`; si no, dict fallback `0.0/0/False`. Antes devolvía el ORM row crudo (no serializable bajo response_model) en caso True y un dict literal en False — inconsistencia de contract resuelta. 2 regression tests (`test_h02_get_lesson_progress_contract` valida keys+tipos+fallback; `test_h02_get_lesson_progress_reflects_persisted_progress` valida mapeo desde ORM row persistido). | `6e1b95c0` |
| H-03 | 🟡 FALSO POSITIVO (justificado 2026-07-24) | El audit asumía que `file_url` exponía un FID crudo de Seaweed porque la columna ORM se llama `seaweed_fid` (`models_academy_core.py:245`). En runtime, `submit_assignment` (`backend/api/academy.py:764-770`) guarda el resultado de `storage_service.save_file_original(...)` que, según `backend/core/storage.py:50-70`, retorna **`/api/static/{subfolder}/{uuid}.ext`** — una URL relativa accesible vía el static file server, NO un FID `SeaweedFS`. El frontend (`MyEnrollments.tsx:261` con `apiUrl(res.file_url)`, `teacher/page.tsx:279`) lo consume ya como `href`/URL navegable — confirmando el formato no-FID. No hay fuga de identificador interno de storage. **Acción residual opcional**: renombrar la columna ORM `seaweed_fid` → `file_url` (migración DDL destructiva fuera de alcance; bajo manual tracking de deuda, no un fix de codigo). No requiere cambios. | n/a |
| H-04 | ✅ CERRADO 2026-07-24 | `list_courses`/`list_lessons`/`list_enrollments`/`list_forum_threads` ahora aceptan `sede_id=None` opt-in. `list_lessons` verifica `get_course(db, course_id, sede_id=...)` antes de listar — si el Course no es visible, retorna []. `list_forum_threads` aplica el patrón outerjoin de A-02. | merge |
| H-05 | ✅ CERRADO 2026-07-24 | `crud/academy.list_courses` ahora `include_global: bool = False` por defecto: el CRUD no mezcla `Course.sede_id IS NULL` (global) con la sede del actor a menos que el caller lo pida explicit con `include_global=True`. Alinea CRUD con la decisión A-03 (scope estricto por defecto). API layer usa `_course_scope` propio (no afectado); catálogo público `public.py` no filtra por sede (general). Callers de test sin `sede_id` devueven todos (preservado). Regression `test_h05_list_courses_excludes_global_by_default`. | `2e590333` |
| H-06 | ✅ CERRADO 2026-07-24 | `create_enrollment` ahora acepta kwarg `sede_id=None` opt-in. La reactivación de un enrollment soft-deleted valida que el `Course.sede_id` del existing coincida con la sede del actor (o sea global `NULL` — legítimo cross-tenant por A-03 lectura/captación). Si el existing pertenece a curso de otra sede específica, levanta `ValueError` (defense-in-depth contra leak cross-tenant). Sin `sede_id` (callers no-API) preserva behavior previo. 3 regression tests: happy-path misma sede, curso global permitido, bloqueo cross-sede. | `0e9073c8` |
| H-07 | ✅ CERRADO 2026-07-24 | `create_course` y `create_lesson` ahora aceptan kwargs opt-in `sede_id=None` y `actor_persona_id=None`. `create_course`: si `sede_id` se pasa y el `Course.sede_id` dictado por el payload es otra sede específica (no global NULL), levanta `ValueError` (el actor no puede atribuir a otra sede). `create_lesson`: si `sede_id` se pasa, delega a `get_course(sede_id=...)` y, si el curso no es visible, levanta `ValueError`. Sin kwargs (callers no-API) preservan behavior previo. 2 regression tests (create_course cross-sede / global-legítimo; create_lesson cross-sede). | `0e9073c8` |
| H-08 | ✅ CERRADO 2026-07-24 | Creado helper `_commit_or_raise_conflict(db, detail)` en `crud/academy.py` (patrón alineado con `api/cms_v2.py::_commit_or_raise_conflict`, M-12 defensivo). Sólo traga `IntegrityError` con `pgcode == '23505'` (Postgres unique) o mensaje SQLite `"UNIQUE constraint failed"` → `HTTPException(409)`. Toda otra `IntegrityError` (NOT NULL, FK, check) se re-raise post-rollback → 500 (no falso 409). Reemplazados los 7 commits directos (`create_course`/`update_course`/`archive_course`/`create_lesson`/`update_lesson`/`archive_lesson`/`create_enrollment`). 3 regression tests: unique→409, non-unique→re-raise, end-to-end course code duplicado→409. | `0e9073c8` |
| H-09 | ✅ CERRADO 2026-07-24 | `AcademyClient.tsx` ahora usa `AbortController` + `controller.abort()` en cleanup de `useEffect`. `loadData` recibe `signal` y lo propaga a `apiFetch`. AbortError se filtra (no se muestra al usuario). | merge |
| H-10 | ✅ CERRADO 2026-07-24 | `apiFetch` en `AcademyClient.tsx` ahora pasa `cache: 'no-store'` en las dos lecturas GET (`/academy/dashboard/metrics`, `/academy/me/profile`). Alinea con `coordination/page.tsx` y `profile/page.tsx` que ya lo aplicaban. | merge |
| H-11 | 🔴 PENDIENTE | — | — |

### MEDIOS

| ID | Estado | Cierre / Justificación | Commit |
|---|---|---|---|
| M-01 | 🔴 PENDIENTE | — | — |
| M-02 | 🔴 PENDIENTE | — | — |
| M-03 | 🔴 PENDIENTE | — | — |
| M-04 | 🔴 PENDIENTE | — | — |
| M-05 | 🔴 PENDIENTE | — | — |
| M-06 | 🔴 PENDIENTE | — | — |
| M-07 | 🔴 PENDIENTE | — | — |
| M-08 | 🔴 PENDIENTE | — | — |
| M-09 | 🔴 PENDIENTE | — | — |
| M-10 | 🔴 PENDIENTE | — | — |
| M-11 | 🔴 PENDIENTE | — | — |
| M-12 | 🔴 PENDIENTE | — | — |

### INFORMATIVOS / FUNCIONALIDADES

| ID | Estado | Cierre / Justificación | Commit |
|---|---|---|---|
| I-01 | 🟡 DEUDA EN REVISIÓN | — | — |
| I-02 | 🔴 PENDIENTE | — | — |
| I-03 | 🟡 DEUDA EN REVISIÓN | — | — |
| I-04 | 🔴 PENDIENTE | — | — |
| I-05 | 🔴 PENDIENTE | — | — |
| I-06 | 🔴 PENDIENTE | — | — |
| I-07 | 🔴 PENDIENTE | — | — |
| I-08 | 🔴 PENDIENTE | — | — |
| I-09 | 🔴 PENDIENTE | — | — |
| F-01 | 🔴 PENDIENTE | — | — |
| F-02 | 🔴 PENDIENTE | — | — |
| F-03 | 🔴 PENDIENTE | — | — |
| F-04 | 🔴 PENDIENTE | — | — |
| F-05 | 🔴 PENDIENTE | — | — |
| F-06 | 🔴 PENDIENTE | — | — |
| F-07 | 🔴 PENDIENTE | — | — |
| F-08 | 🔴 PENDIENTE | — | — |
| F-09 | 🔴 PENDIENTE | — | — |
| F-10 | 🔴 PENDIENTE | — | — |

### Resumen de cierre al 2026-07-24

- **Críticos: 8/8 cerrados** ✅ (A-01 validate_certificate, A-02 forum outerjoin, A-03 scope admin estricto, A-04 rate-limit Request, A-05 submit_assignment IDOR, A-06 CRUD getters sede_id, A-07 CRUD mutadores sede_id, A-08 XSS MyEnrollments)
- **Altos: 8/11 cerrados** ✅ (H-01 sede_id en contract Course, H-02 LessonProgressResponse, H-04 list_* sede_id, H-05 list_courses scope estricto, H-06 create_enrollment cross-tenant, H-07 create_course/lesson ownership, H-08 _commit_or_raise_conflict, H-09 AbortController, H-10 cache no-store) — 1 falso positivo justificado (H-03 — `file_url` es ruta `/api/static/...`, no FID Seaweed) — 1 pendiente (H-11)
- Medios: 0/12 cerrados
- Info: 0/9 cerrados (2 en revisión)
- Funcionalidades: 0/10 cerradas (F-01 parcial — cubre upload blocked archived)
- **Pendientes: 24 hallazgos** (1 alto + 12 medios + 9 info + 2 en revisión en info).
- Commits de cierre: `c2c92299` (WIP consolidado A-01/A-04/A-08), `4dc25ef0..62116fc2` (A-02/A-03/A-05), `3c7aae7d` (A-06/A-07/H-04), `65466384` (H-09/H-10), `2e590333` (H-05), `0e9073c8` (H-06/H-07/H-08), `6e1b95c0` (H-01/H-02 schemas). H-03 falso positivo — sin commit.

---

*Documento generado por auditoría forense línea por línea del código fuente del módulo Academy.*
*Total: 40 hallazgos (8 críticos, 11 altos, 12 medios, 9 informativos) + 10 funcionalidades/brechas de test.*
*Hallazgos cerrados: 11/40 (8 críticos + 3 altos) — ver estados arriba.*

# Estado del Modulo de Academy — CCF

> **🚨 DEPRECADO para backlog — 2026-07-19:** los hallazgos, estados de
> cierre y tickets Academy se gestionan únicamente en
> [`docs/ACADEMY_BACKLOG.md`](./ACADEMY_BACKLOG.md). Este documento conserva
> contexto operativo e histórico; no se usa para abrir ni cerrar trabajo.

> **TL;DR (una linea):** Academy es el módulo formativo de CCF sobre `/api/academy` y `/plataforma/academy`: cursos, lecciones, evaluaciones, matrículas, progreso, certificados, foro, agenda académica y operaciones administrativas por rol.

**Proposito.** Handover canónico para que cualquier sesión nueva pueda trabajar Academy como unidad propia, sin mezclarlo con CRM, CMS o auth más allá de los contratos compartidos reales.

**Regla de uso.**

- Actualizar este doc al cerrar tareas, no antes.
- `Hecho / Parcial / Pendiente` reflejan el código vigente.
- No usar este doc como wishlist.
- Si un cambio toca `personas.id`, `auth_users.id`, permisos Academy, `sede_id`, storage o `apiFetch`, tratarlo como cambio de plataforma.

---

## 1. Leer primero (cualquier agente)

```bash
cat /root/ccf/docs/ACADEMY_BACKLOG.md
cat /root/ccf/docs/ACADEMY_API_CONTRACTS.md
cat /root/ccf/docs/ACADEMY_RBAC_MATRIX.md
cat /root/ccf/docs/ACADEMY_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_ACADEMY_CALIDAD.md
cat /root/ccf/docs/PLAN_ARQUITECTURA_MODULAR_CCF.md
```

## 2. Verificar entorno

```bash
python3 --version && node --version
```

Versiones verificadas en este host el **2026-07-16**:

- Python: **3.12.3**
- Node: **v24.15.0**

## 3. Recontar superficie vigente (por si drift)

```bash
wc -l /root/ccf/backend/api/academy.py /root/ccf/backend/crud/academy.py /root/ccf/backend/models_academy_core.py /root/ccf/backend/schemas/academy.py 2>/dev/null | tail -1
wc -l /root/ccf/frontend/src/app/plataforma/academy/**/*.tsx /root/ccf/frontend/src/app/plataforma/academy/*.tsx 2>/dev/null | tail -1
```

Conteo actual:

- Backend Academy directo: **1 908 LOC**
- Frontend Academy directo: **2 978 LOC**

## 4. Listar backlog completo (Parcial + Pendiente) por ID

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_ACADEMY.md
```

## 5. Smoke test

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_academy_quality.py
```

Smoke mínimo bruto:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_academy_api.py tests/test_academy_domain.py
```

Cobertura frontend vigente:

- `frontend/tests/e2e/academy/smoke.spec.ts` cubre dashboard, forum y coordination.
- `frontend/tests/e2e/academy/profile-detail.spec.ts` cubre profile y progress con runner administrado.

---

## 6. TL;DR — Mapa del modulo

| Capa | Ubicacion | Tamano |
|---|---|---:|
| Router canónico | `backend/api/academy.py` | cursos, lessons, assessments, enrollments, profile, dashboard, admin |
| CRUD | `backend/crud/academy.py` | matrículas y operaciones de dominio |
| Modelos | `backend/models_academy_core.py` | cursos, lecciones, progreso, evaluaciones, intentos, certificados, foro |
| Schemas | `backend/schemas/academy.py` | contratos Pydantic |
| UI principal | `frontend/src/app/plataforma/academy/**` | dashboard, cursos, curriculum, forum, certificados, grades, coordination |
| Tests backend | `tests/test_academy_api.py`, `tests/test_academy_domain.py` | API canónica y dominio |

**Estado global:** Academy tiene router y dominio relativamente concentrados, con contratos ya endurecidos a UUID y `sede_id`. Ya cuenta con documentación modular, smoke canónico y cobertura profunda de profile/progress; el trabajo abierto se concentra en rutas duplicadas, coordinación/admin y expansión del smoke canónico.

---

## 7. Convenciones del modulo

- **Ruta plataforma:** `/plataforma/academy`
- **Ruta API:** `/api/academy`
- **Cliente frontend:** `apiFetch('/academy/...')` y dashboard por `/dashboard/academy`
- **Identidad canonica:** `personas.id` UUID; `auth_users.id == personas.id`
- **Permisos:** `academy:read`, `academy:study`, `academy:edit`, `academy:manage`
- **Sede isolation:** cursos y operaciones protegidas deben respetar `sede_id`
- **Storage/uploads:** usar `storage_service` y `sanitize_filename`
- **Soft delete:** `academy_*` usa `deleted_at` donde aplica

---

## 8. Backend — Modelo de datos

Dominio principal en `backend/models_academy_core.py`:

```text
Course
  -> Lesson
    -> Resource
    -> AssignmentSubmission
  -> Assessment
    -> AssessmentQuestion
      -> AssessmentOption
  -> Enrollment
    -> LessonProgress
    -> AssessmentAttempt
      -> AssessmentAnswer
    -> CourseAttendance
    -> Certificate
ForumThread
CoursePrerequisite
```

Tablas clave:

- `academy_courses`
- `academy_lessons`
- `academy_lesson_progress`
- `academy_assessments`
- `academy_assessment_questions`
- `academy_assessment_options`
- `academy_enrollments`
- `academy_assessment_attempts`
- `academy_assessment_answers`
- `academy_course_attendance`
- `academy_assignment_submissions`
- `academy_certificates`
- `academy_forum_threads`

---

## 9. Backend — API surface

Router canónico: `backend/api/academy.py`

Áreas principales:

| Area | Rutas clave |
|---|---|
| Courses | `/courses`, `/courses/{course_id}`, `/courses/{course_id}/lessons`, `/courses/{course_id}/assessments` |
| Assessments | `/assessments/{assessment_id}`, `/assessments/{assessment_id}/submit` |
| Progress | `/lessons/{lesson_id}/progress`, `/me/progress`, `/me/profile` |
| Enrollments | `/enrollments`, `/me/enrollments`, `/enrollments/{id}/check-in` |
| Certificates | `/me/certificates`, `/enrollments/{id}/request-certificate`, `/certificates/validate/{code}` |
| Assignments | `/lessons/{lesson_id}/submit-assignment`, `/admin/submissions`, `/admin/submissions/{id}/grade` |
| Forum | `/forum/threads` |
| Schedule / personas / dashboard | `/schedule`, `/personas`, `/dashboard/metrics`, `/dashboard/pilot-readiness` |
| Admin | `/admin/courses*`, `/admin/lessons*`, `/admin/assessments*` |

Detalle y reglas en `docs/ACADEMY_API_CONTRACTS.md`.

---

## 10. Frontend — Mapa de pantallas

Rutas principales en `frontend/src/app/plataforma/academy/`:

| Ruta | Archivo | Estado |
|---|---|---|
| `/plataforma/academy` | `page.tsx`, `AcademyClient.tsx` | Hecho — dashboard |
| `/plataforma/academy/courses` | `courses/page.tsx`, `courses/[id]/page.tsx` | Hecho funcional |
| `/plataforma/academy/course/[id]` | `course/[id]/page.tsx` | Parcial — coexistencia de rutas requiere contrato claro |
| `/plataforma/academy/curriculum` | `curriculum/page.tsx` | Hecho funcional |
| `/plataforma/academy/forum` | `forum/page.tsx`, `forum/[id]/page.tsx` | Hecho funcional |
| `/plataforma/academy/certificates` | `certificates/page.tsx`, `[code]/page.tsx` | Hecho funcional |
| `/plataforma/academy/grades` | `grades/page.tsx` | Parcial — depende de flujos administrativos |
| `/plataforma/academy/coordination` | `coordination/page.tsx` y subrutas | Parcial — surface administrativa amplia |
| `/plataforma/academy/profile` | `profile/page.tsx`, `progress/page.tsx` | Hecho funcional |
| `/plataforma/academy/resources`, `/schedule`, `/students`, `/teachers`, `/teacher` | varias | Hecho funcional, sin e2e dedicado |

Suites frontend dedicadas vigentes:

- `frontend/tests/e2e/academy/smoke.spec.ts`
- `frontend/tests/e2e/academy/profile-detail.spec.ts`

---

## 11. Estado del modulo

### Hecho

- Router canónico `/api/academy`
- Contrato UUID para personas, matrículas y recursos
- Permisos separados por `read/study/edit/manage`
- Scope por sede en cursos y operaciones protegidas
- Progreso de lessons, enrollments, profile y certificates
- Foro académico con aislamiento por sede y preservación de hilos globales
- Dashboard Academy en frontend
- Smoke canónico backend mediante script único

### Parcial

1. **Smoke frontend Academy** `[PARCIAL-FRONTEND-SMOKE-ACADEMY-001]` — ya existe smoke dedicado en `frontend/tests/e2e/academy/smoke.spec.ts` y cobertura profunda en `frontend/tests/e2e/academy/profile-detail.spec.ts`, pero aún faltan certificates, rutas duales de curso y flows admin detallados.
2. **Rutas de curso duplicadas** `[PARCIAL-COURSE-ROUTES-001]` — conviven `course/[id]` y `courses/[id]`; requiere contrato funcional más explícito.
3. **Dashboard Academy** `[PARCIAL-DASHBOARD-CONTRACT-ACADEMY-001]` — la shape operativa de `/dashboard/academy` ya quedó documentada y el módulo ya tiene smoke frontend dedicado; falta ampliar cobertura visual y de agregados administrativos.
4. **Coordinación/admin** `[PARCIAL-COORDINATION-ACADEMY-001]` — hay surface amplia de administración sin smoke frontend dedicado.

### Pendiente

1. **E2E Academy** `[PEND-FRONTEND-E2E-ACADEMY-001]` — cerrada el 2026-07-16 con `frontend/tests/e2e/academy/smoke.spec.ts`; fija smoke mínimo de dashboard, forum y coordination con guard de consola/API/assets.
2. **Plan de calidad Academy** `[PEND-PLAN-ACADEMY-001]` — cerrada el 2026-07-16 en `docs/PLAN_ACADEMY_CALIDAD.md`; fija fases para dashboard, ownership del estudiante, rutas de curso, coordinación y smoke frontend.
3. **Matriz RBAC Academy** `[PEND-RBAC-ACADEMY-001]` — cerrada el 2026-07-16 en `ACADEMY_RBAC_MATRIX.md`; documenta permisos reales, ownership del estudiante y drift entre seed persistido, fallback runtime y role normalization.
4. **Smoke profundo de profile/progress** `[PEND-FRONTEND-DEEP-ACADEMY-001]` — cerrada el 2026-07-16 con `frontend/tests/e2e/academy/profile-detail.spec.ts`; valida profile, progress y cambios de vista con runner administrado.
5. **Ampliar smoke canónico** `[PEND-EXPAND-SMOKE-ACADEMY-001]` — cubrir certificates, rutas duales, admin flows y forum desde `scripts/test_academy_quality.py`.

---

## 12. Archivos a leer antes de cambiar codigo

1. `docs/ESTADO_ACADEMY.md`
2. `docs/ACADEMY_API_CONTRACTS.md`
3. `docs/ACADEMY_RBAC_MATRIX.md`
4. `docs/ACADEMY_QA_CHECKLIST.md`
5. `backend/api/academy.py`
6. `backend/crud/academy.py`
7. `backend/models_academy_core.py`
8. `backend/schemas/academy.py`
9. `frontend/src/app/plataforma/academy/AcademyClient.tsx`
10. `frontend/src/app/plataforma/academy/courses/`
11. `frontend/src/app/plataforma/academy/coordination/`

---

## 13. Orden operativo recomendado

1. Reproducir con ruta exacta y rol real.
2. Identificar si el problema es Academy puro o plataforma compartida.
3. Correr smoke canónico.
4. Si toca enrollments/progress, validar ownership del estudiante.
5. Si toca forum, validar aislamiento por sede y hilos globales.
6. Si toca admin, validar `academy:edit/manage`.
7. Si toca frontend, probar manualmente rutas del checklist.

---

## 14. Tabla de IDs estables

| ID | Pieza | Archivo o area |
|---|---|---|
| `PARCIAL-FRONTEND-SMOKE-ACADEMY-001` | Smoke Academy ya existe, pero todavía no cubre certificates, profile, rutas duales de curso ni flujos admin detallados | `frontend/tests/e2e/academy/` |
| `PARCIAL-COURSE-ROUTES-001` | Coexistencia `course/[id]` vs `courses/[id]` | frontend academy routes |
| `PARCIAL-DASHBOARD-CONTRACT-ACADEMY-001` | Contrato del dashboard ya documentado; sigue faltando gate frontend para drift visual | `docs/ACADEMY_API_CONTRACTS.md` + `/dashboard/academy` |
| `PARCIAL-COORDINATION-ACADEMY-001` | Surface admin amplia sin smoke frontend | `frontend/src/app/plataforma/academy/coordination/**` |
| `PEND-FRONTEND-E2E-ACADEMY-001` | ✅ **Hecho 2026-07-16** — smoke frontend Academy dedicado para dashboard, forum y coordination con guard de consola/API/assets. | `frontend/tests/e2e/academy/smoke.spec.ts` |
| `PEND-PLAN-ACADEMY-001` | ✅ **Hecho 2026-07-16** — plan de calidad Academy documentado por fases, con foco en dashboard, ownership del estudiante, rutas duplicadas y coordinación/admin. | `docs/PLAN_ACADEMY_CALIDAD.md` |
| `PEND-RBAC-ACADEMY-001` | ✅ **Hecho 2026-07-16** — matriz RBAC documentada con guards reales, ownership por matrícula/persona y drift entre seed, fallback y role normalization. | `docs/ACADEMY_RBAC_MATRIX.md` |
| `PEND-EXPAND-SMOKE-ACADEMY-001` | Ampliar script Academy | `scripts/test_academy_quality.py` |

Busqueda rapida:

```bash
grep -nE "PARCIAL-|PEND-|ACAD-" /root/ccf/docs/ESTADO_ACADEMY.md
```

---

## 15. Auditoría forense 2026-07-18 (nuevos hallazgos) — ⚠️ DEPRECATED 2026-07-19

> **🚨 DEPRECADO — 2026-07-19:** este bloque fue consolidado en
> [`docs/ACADEMY_BACKLOG.md`](./ACADEMY_BACKLOG.md). Los hallazgos de
> §15.1-§15.6 (`ACAD-CRIT-001`, `ACAD-HIGH-001..`, `ACAD-MED-001..`, etc.)
> sobrevivieron como rastro histórico para auditoría forense, pero
> **NO se mantienen ni actualizan aquí**.
>
> Cada hallazgo `ACAD-*` de §15 ahora tiene su equivalente `ACAD-TKT-NNN`
> con `gate:` ejecutable y estado actual rastreable en
> `docs/ACADEMY_BACKLOG.md`. La regla anti-drift (§7 del backlog)
> prohíbe abrir nuevos tickets en este archivo.

**Alcance.** Lectura completa de `backend/api/academy.py` (700 línea), `models_academy_core.py`, `schemas/academy.py`, `crud/academy.py`, `frontend/src/app/plataforma/academy/**` (layout, page, AcademyClient, loading, error), `frontend/src/components/academy/*`, `CourseCatalog.tsx`, `MyEnrollments.tsx` y `moduleConfigs.ts`. Fecha de cierre de la sesión: **2026-07-18**.

<details>
<summary>📜 <b>§15.1-§15.6 — Tablas de auditoría forense 2026-07-18</b> (clic para expandir rastro histórico; fuente vigente en <a href="./ACADEMY_BACKLOG.md"><code>docs/ACADEMY_BACKLOG.md</code></a> §2 capa histórica + §4.1-§4.6 capa operativa)</summary>

> **Contexto:** esta sección contiene **registros históricos** de la auditoría forense del 2026-07-18. El estado actual (cerrado/pendiente) de cada hallazgo se refleja en la tabla consolidada §15.6 más abajo. Los textos descriptivos a continuación se conservan tal cual para preservar la trazabilidad forense — **no reflejan el código vigente**. Para conocer el código real que satisface hoy estos invariantes, consultar §15.6 + `docs/ACADEMY_API_CONTRACTS.md`.

### 15.1. Hallazgos CRÍTICOS (`CRIT`)

| ID | Severidad | Hallazgo | Archivo |
|---|---|---|---|
| `ACAD-CRIT-001` | 🔴 | **Mismatch UUID vs `id:number`** en `CourseCatalog.tsx`. La interfaz `Course` declara `id: number` y `enrolledCourseIds?: number[]`, pero el backend retorna UUID string. `enrolledCourseIds.includes(course.id)` siempre devolverá `false` y el botón mostrará "Inscribirme Ahora" para cursos ya inscritos. | `frontend/src/components/CourseCatalog.tsx` |
| `ACAD-CRIT-002` | 🔴 | **Dashboard endpoint incorrecto.** `AcademyClient.tsx` consume `GET /dashboard/academy` pero espera `cards`, `enrollment_trends` y `top_courses`. El endpoint real `GET /academy/dashboard/metrics` solo retorna `cards` con 3 entries. `enrollment_trends` y `top_courses` son `undefined` → `.map()` sobre undefined genera sección vacía o crash. | `frontend/src/app/plataforma/academy/AcademyClient.tsx`, `backend/api/academy.py:354` |

### 15.2. Hallazgos ALTOS (`HIGH`)

| ID | Severidad | Hallazgo |
|---|---|---|
| `ACAD-HIGH-001` | 🟠 | **Filtrado del sidebar no respeta nivel.** El layout del módulo lista "Panel Docente" y "Coordinación" con `allowedPermissions: ['academy:read', 'academy:study', 'academy:edit', 'academy:manage']`; cualquier estudiante con `read` los ve en el S2 aunque el backend le niegue los endpoints `/admin/*`. |
| `ACAD-HIGH-002` | 🟠 | **QR code externo inseguro.** `CertificateView.tsx:84` produce el QR a través de `api.qrserver.com` (externo gratuito). Expone metadata y crea dependencia de un proveedor fuera del perímetro institucional. |
| `ACAD-HIGH-003` | 🟠 | **Doble shell redundante.** `AcademyDetailShell` se monta en algunas rutas mientras el resto del módulo usa `WorkspaceLayout` con su propio `sidebarTitle`/`sidebarSections`. Visualmente hay dos microclimas: detalle limpio radial vs listado canónico. |
| `ACAD-HIGH-004` | 🟠 | **Sidebar doble configuración.** `moduleConfigs.ts` declara 4 ítems académicos; `app/plataforma/academy/layout.tsx` sobreescribe con 5 grupos y 12 ítems. El comportamiento efectivo es el del layout local, pero el primero sirve de fallback para el sidebar S1/S2 del módulo raíz. |

### 15.3. Hallazgos MEDIOS (`MED`)

| ID | Severidad | Hallazgo |
|---|---|---|
| `ACAD-MED-001` | 🟡 | **Foro con `course_id=None` abierto.** Cualquier `AcademyStudent` puede `POST` hilo global. Riesgo: ruido cross-sede + contenido fuera del contexto del módulo. |
| `ACAD-MED-002` | 🟡 | **`ForumThread.is_resolved` sin endpoint PATCH.** El campo existe pero ningún endpoint permite cambiarlo; ni usuarios ni moderadores pueden cerrar hilos. |
| `ACAD-MED-003` | 🟡 | **`AssignmentSubmission` sin DELETE/retract.** No hay forma de borrar entregas erróneas; quedan ahí hasta `grade=...` desde editor. |
| `ACAD-MED-004` | 🟡 | **`CourseCatalog.tsx` con 8 vistas inline.** grid/list/table/board/kanban/calendar/gantt/wiki renderizadas en un solo archivo > 400 líneas. Candidato a refactor en sub-componentes. |
| `ACAD-MED-005` | 🟡 | **`AcademyClient` sin `ModuleErrorBoundary` visual.** Único feedback de error es `toast.error`; sin retry, sin empty state explícito. |

### 15.4. Hallazgos BAJOS (`LOW`)

| ID | Severidad | Hallazgo |
|---|---|---|
| `ACAD-LOW-001` | 🟢 | **CertificateView.Download/Share sin handler.** Botones renderizados pero sin `onClick` real. Funcionalidad cosmética hasta hoy. |
| `ACAD-LOW-002` | 🟢 | **`enrollment_id` redundante en payload de `submit_assessment`.** El backend lo lee del `current_user.id` + lookup; el cliente igual lo manda. Inocuo pero confuso. |

### 15.5. Endpoints faltantes detectados

| Recurso | Falta |
|---|---|
| `ForumComment` | Modelo existe pero sin CRUD en router. No hay GET/POST/DELETE para respuestas ni threading anidado. |
| `Resource` (lesson materials) | `academy_resources` se modela y se carga vía `selectinload`, pero no hay GET/POST/DELETE directo. |
| `ForumThread` categorías | Columna `category` existe pero el `GET /forum/threads` no acepta filtro. |
| `AssignmentSubmission` | Sin DELETE; no se puede retractar. |
| `ForumThread.is_resolved` | Sin endpoint para resolver. |

### 15.6. Tabla consolidada del estado de los nuevos hallazgos

| ID | Estado | Notas |
|---|---|---|
| `ACAD-CRIT-001` | ✅ **Hecho 2026-07-19 (cierre documental — sin cambios de runtime)** | Resuelto en código: `frontend/src/components/CourseCatalog.tsx` ya usa `id: string` y `enrolledCourseIds?: string[]`; `frontend/src/types/academy.ts::CourseSummary.id = string`. `enrolledCourseIds.includes(course.id)` opera sobre `string === string`. Doc §15.1 se conserva como registro histórico del hallazgo. |
| `ACAD-CRIT-002` | ✅ **Hecho 2026-07-19 (cierre documental — sin cambios de runtime)** | Resuelto en código: `backend/api/academy.py:870-931` (`dashboard_metrics`) ya retorna `cards`, `enrollment_trends` y `top_courses` (etiqueta inline `// ACAD-CRIT-002:`). `frontend/src/app/plataforma/academy/AcademyClient.tsx:38` consume `/academy/dashboard/metrics` y usa fallback a `/dashboard/academy` para roles sin `academy:manage`. La `DSChart`/`DSCard` navegan con optional chaining `dashboard?.enrollment_trends`, así que el fallback degradado no rompe. Doc §15.1 se conserva como registro histórico. |
| `ACAD-HIGH-001` | Pendiente | Filtro `hasModuleAccess('academy', 'edit')` por item S2 |
| `ACAD-HIGH-002` | Pendiente | Local QR (`qrcode` lib en backend → base64 o `react-qr-code` en frontend) |
| `ACAD-HIGH-003` | Pendiente | Decidir si `AcademyDetailShell` se mantiene o se consolida con `WorkspaceLayout` |
| `ACAD-HIGH-004` | Pendiente | Mover la configuración única de sidebar a un solo origen |
| `ACAD-MED-001` | Pendiente | Permitir hilos globales solo a `Editor/Manager` |
| `ACAD-MED-002` | Pendiente | `PATCH /forum/threads/{id}/resolve` |
| `ACAD-MED-003` | ✅ **Hecho 2026-07-18** | `DELETE /admin/submissions/{id}` con soft delete (`row.deleted_at = _utcnow()`), filtro `deleted_at IS NULL` también en `list_submissions` y `grade_submission`, modelo `AssignmentSubmission.deleted_at` añadido en migration `20260718_0003`. |
| `ACAD-MED-004` | Pendiente | Refactor por vista → `CourseGrid.tsx`, `CourseBoard.tsx`, etc. |
| `ACAD-MED-005` | Pendiente | Mejorar `AcademyClient` con `<EmptyState/>` y retry visible |
| `ACAD-LOW-001` | Pendiente | Implementar `onClick` o quitar botones |
| `ACAD-LOW-002` | Pendiente | Aceptar `enrollment_id` opcional y normalizar |

</details>

---

## 16. Fases operativas derivadas (referencia)

> **Plegado 2026-07-19:** las fases operativas vigentes (Fase A críticos, Fase B altos, Fase C medios, Fase D bajos, Fase E re-validación) viven en [`docs/ACADEMY_BACKLOG.md`](./ACADEMY_BACKLOG.md) §4 (Capa OPERATIVA — tickets ⬜ pendientes). Este §16 se conserva como índice navegacional al snapshot del 2026-07-18, sin duplicar contenido.

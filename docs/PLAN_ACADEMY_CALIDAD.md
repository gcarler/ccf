# Plan de Calidad — Modulo de Academy CCF

> **Objetivo:** cerrar Academy como modulo formativo con contrato operacional claro para cursos, matrículas, dashboard, coordinación y ownership del estudiante.

## 1. Regla de trabajo

- No mezclar bugs Academy con CRM, CMS o auth salvo que el contrato cruzado sea el origen real.
- Cada corrección debe referenciar un ID estable de `docs/ESTADO_ACADEMY.md`.
- Si el flujo es de estudiante, validar ownership antes de tocar UI.
- Si el flujo es admin, validar permisos `academy:edit/manage` antes de ajustar frontend.
- Los dashboards y rutas duplicadas deben resolverse por contrato, no por tolerancia visual.

## 2. Fase 0 — Diagnostico base

**ID:** `ACADEMY-FASE0-DIAG`

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_ACADEMY.md
grep -nE "PARCIAL-|PEND-" docs/ESTADO_ACADEMY.md
./venv/bin/python scripts/test_academy_quality.py
```

Validación mínima bruta:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_academy_api.py \
  tests/test_academy_domain.py
```

Criterio de salida:

- El fallo queda clasificado como `ownership`, `RBAC`, `dashboard`, `course routing`, `forum`, `admin` o `frontend state`.

## 3. Fase 1 — Dashboard y métricas Academy

**ID:** `PARCIAL-DASHBOARD-CONTRACT-ACADEMY-001`

Orden:

1. Validar shape real de `GET /api/dashboard/academy`.
2. Confirmar `cards`, `enrollment_trends`, `top_courses`, `grade_distribution`, `at_risk_students_count`, `filters` y `last_updated`.
3. Alinear `AcademyClient.tsx` con el contrato real.
4. Mantener separado el contrato de `/api/academy/dashboard/metrics` y `/api/academy/dashboard/pilot-readiness`.

Criterio de salida:

- El dashboard principal deja de depender de supuestos implícitos.
- El contrato queda escrito en `docs/ACADEMY_API_CONTRACTS.md`.

## 4. Fase 2 — Ownership del estudiante y matrículas

Orden:

1. Validar `POST /enrollments`, `GET /me/enrollments`, `GET /me/progress`, `GET /me/profile`.
2. Confirmar que un estudiante no puede matricular o actualizar otra persona.
3. Verificar certificados y progreso por `enrollment_id` con scope correcto.

Criterio de salida:

- El ownership del estudiante queda estable.
- `403` y `404` responden al contrato real.

## 5. Fase 3 — Rutas de cursos y surface pública interna

**ID:** `PARCIAL-COURSE-ROUTES-001`

Orden:

1. Comparar `course/[id]` vs `courses/[id]`.
2. Definir si una es alias temporal o si ambas tienen propósito distinto.
3. Evitar que dos pantallas mantengan contratos divergentes para el mismo curso.

Criterio de salida:

- La convivencia de rutas queda documentada o se elimina el drift.

## 6. Fase 4 — Coordinación, grading y admin

**IDs:** `PARCIAL-COORDINATION-ACADEMY-001`, `PEND-EXPAND-SMOKE-ACADEMY-001`

Orden:

1. Validar submissions y grading.
2. Validar CRUD admin de courses, lessons y assessments.
3. Confirmar scope por sede en coordinación.
4. Revisar uploads y sanitización.

Comandos:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_academy_api.py tests/test_academy_domain.py
```

Criterio de salida:

- Flujos admin no exponen cross-sede.
- El smoke canónico puede crecer sin mezclarlo con frontend todavía.

## 7. Fase 5 — Foro, agenda y rutas críticas frontend

**IDs:** `PEND-FRONTEND-E2E-ACADEMY-001`, `PEND-FRONTEND-DEEP-ACADEMY-001`

Rutas mínimas:

- `/plataforma/academy`
- `/plataforma/academy/courses`
- `/plataforma/academy/forum`
- `/plataforma/academy/coordination`

Checks manuales obligatorios hasta tener e2e dedicado:

- consola limpia
- carga de dashboard
- listado de cursos
- acceso a coordinación con rol correcto

Comandos frontend vigentes:

```bash
cd /root/ccf/frontend
npm run test:e2e:academy
npm run test:e2e:academy:deep
```

Regla:

- La cobertura profunda de Academy ya existe para `profile` y `progress`; cualquier suite profunda nueva debe reutilizar el runner administrado compartido.

Criterio de salida:

- Existe smoke frontend dedicado y cobertura profunda básica; queda pendiente ampliar certificates, rutas duales y flows admin.

## 8. Fase 6 — QA final y release

**ID:** `ACADEMY-FASE6-QA`

Comandos mínimos:

```bash
cd /root/ccf
./venv/bin/python scripts/test_academy_quality.py
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_academy_api.py \
  tests/test_academy_domain.py
```

Criterio de salida:

- `docs/ESTADO_ACADEMY.md` se actualiza si cambia backlog o estado.
- El fix no degrada ownership, sede isolation ni dashboard.

---

## 9. Update 2026-07-18 — Fase 0 (Auditoría forense) y Plan de remediación

Esta fase precede a las fases 1–6 existentes y consolida los hallazgos nuevos documentados en `docs/ESTADO_ACADEMY.md §15`. Cada fix referencia un ID estable `ACAD-*` y se verifica con el smoke correspondiente.

### Fase 0 — Auditoría forense y fixes críticos

**ID Plan:** `PLAN-ACAD-FASE0-AUDIT-2026-07-18`

Pasos obligatorios antes de cualquier trabajo de Academy:

1. `cat docs/ESTADO_ACADEMY.md` y `docs/ACADEMY_API_CONTRACTS.md`.
2. `./venv/bin/python scripts/test_academy_quality.py` baseline.
3. `cd frontend && npx tsc --noEmit` baseline.
4. `cd frontend && npm run test:e2e:academy` baseline.

**Diagnóstico:** 13 hallazgos nuevos (2 críticos, 4 altos, 5 medios, 2 bajos) + 5 endpoints faltantes.

### Fase A — CRÍTICOS (bloqueante)

| Paso | ID | Acción | Verificación |
|---|---|---|---|
| A.1 | `ACAD-CRIT-001` | Cambiar `CourseCatalog.tsx`: interfaces `id: string`, `enrolledCourseIds?: string[]`. Cast también en `MyEnrollments.tsx` si hace falta. | `npx tsc --noEmit` + smoke curso catalog |
| A.2 | `ACAD-CRIT-002` | Extender `GET /academy/dashboard/metrics` para devolver `enrollment_trends: ChartDataPoint[]` y `top_courses: {title:str,count:int}[]` (calcular en SQL con GROUP BY fecha/curso), o reducir el cliente a solo `cards`. Decisión por coordinador. | `pytest tests/test_academy_api.py` y request manual |

### Fase B — ALTOS

| Paso | ID | Acción | Verificación |
|---|---|---|---|
| B.1 | `ACAD-HIGH-001` | En `app/plataforma/academy/layout.tsx`, dividir `SIDEBAR_SECTIONS` por nivel: `academy:edit` para "Panel Docente", `academy:manage` para "Coordinación". Usar filtrado dinámico desde `hasModuleAccess` (mismo patrón que `moduleConfigs.ts`). | Inspección manual de sidebar como LECTOR y EDITOR |
| B.2 | `ACAD-HIGH-002` | Reemplazar `api.qrserver.com` por generación local; opciones: `qrcode` lib en backend que retorne base64, o `react-qr-code` en frontend. Remover import de `OptimizedImage` con URL externa. | `npx tsc --noEmit` y pruebas manuales |
| B.3 | `ACAD-HIGH-003` | Decidir consolidación: mantener `AcademyDetailShell` solo para rutas `course/[id]` con presentación inmersiva, y etiquetarlo como variante; todo lo demás solo bajo `WorkspaceLayout`. Documentar en `docs/ESTADO_ACADEMY.md`. | QA manual |
| B.4 | `ACAD-HIGH-004` | Mover la configuración de sidebar de `app/plataforma/academy/layout.tsx` a un módulo compartido `academySidebarConfig.ts`, y eliminar versión en `moduleConfigs.ts` para evitar drift. | `grep` confirma single source of truth |

### Fase C — MEDIOS

| Paso | ID | Acción |
|---|---|---|
| C.1 | `ACAD-MED-001` | En `POST /forum/threads`, rechazar `course_id=None` si `current_user` no tiene `academy:edit` o superior. |
| C.2 | `ACAD-MED-002` | Añadir `PATCH /forum/threads/{id}/resolve` para `Editor/Manager`; campo booleano alternante. |
| C.3 | `ACAD-MED-003` | ✅ **Hecho 2026-07-18** — `DELETE /admin/submissions/{id}` con soft delete (`row.deleted_at = _utcnow()`, Regla 4), filtros `deleted_at IS NULL` propagados a `list_submissions` y `grade_submission`. Modelo `AssignmentSubmission.deleted_at` añadido en migration `20260718_0003`. Audit trail completo en `AcademyActivityLog.payload_json` con `submission_id`/`file_url`/`lesson_id`/`enrollment_id`/`archived_at`/`archived_by_persona_id` (migration `20260718_0002`). |
| C.4 | `ACAD-MED-004` | Refactor `CourseCatalog.tsx`: extraer cada vista a `CourseGrid`, `CourseList`, `CourseBoard`, `CourseCalendar`, `CourseGantt`, `CourseWiki`. Sin cambio de comportamiento visible. |
| C.5 | `ACAD-MED-005` | En `AcademyClient.tsx`, envolver contenido con `<EmptyState/>` y botón "Reintentar" cuando `dashboard === null` y `loading === false`. |

### Fase D — BAJOS

| Paso | ID | Acción |
|---|---|---|
| D.1 | `ACAD-LOW-001` | Quitar botones cosméticos o implementar handlers reales (`html2canvas` o similar para PDF). |
| D.2 | `ACAD-LOW-002` | En `submit_assessment`, ignorar `enrollment_id` del payload; usar siempre el del `current_user`. |

### Fase E — Re-validación global

**ID Plan:** `PLAN-ACAD-FASE5-VALID-2026-07-18`

Comandos mínimos al cierre de cada fase A–D:

```bash
cd /root/ccf
./venv/bin/python scripts/test_academy_quality.py
./venv/bin/python -m pytest -q -o addopts='' tests/test_academy_api.py tests/test_academy_domain.py

cd /root/ccf/frontend
npx tsc --noEmit
npm run test:e2e:academy
npm run test:e2e:academy:deep
```

Adicional para refactors UI:

```bash
cd /root/ccf/frontend
npm run build
```

Criterio de cierre de FASE 0:

- [x] Diagnóstico completo está en `ESTADO_ACADEMY.md §15`
- [ ] ACAD-CRIT-001 cerrado y verificado con tsc/UI
- [ ] ACAD-CRIT-002 cerrado y verificado con endpoint de prueba
- [ ] ACAD-HIGH-001..004 cerrados
- [ ] ACAD-MED-001..005 cerrados o justificados (wontfix)
- [ ] ACAD-LOW-001..002 cerrados
- [ ] Smoke backend limpio
- [ ] Typecheck frontend limpio
- [ ] Smoke e2e academy limpio

### Riesgos y dependencias

1. `ACAD-CRIT-001` exige decisión sobre tipos compartidos; si se decide Schema-first, actualizar `frontend/src/types/academy.ts` (crear) y propagar a `MyEnrollments`, `CourseCatalog`, `AcademicDetail`.
2. `ACAD-CRIT-002` exige decisión sobre backend o frontend; impacto en DB si se decide extender `/dashboard/metrics` (necesita índices adicionales).
3. Fases B–D pueden ejecutarse en paralelo si se programa bien; pero B.1 y B.4 son cambios pequeños con riesgo de merge conflict.

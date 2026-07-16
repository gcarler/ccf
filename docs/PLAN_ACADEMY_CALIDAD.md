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

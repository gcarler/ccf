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
- matriz RBAC consultada en `docs/ACADEMY_RBAC_MATRIX.md`
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

Smoke dedicado mínimo:

```bash
cd /root/ccf/frontend
npm run test:e2e:academy
npm run test:e2e:academy:deep
```

El smoke dedicado cubre:

- `/plataforma/academy`
- `/plataforma/academy/forum`
- `/plataforma/academy/coordination`
- `/plataforma/academy/profile`
- `/plataforma/academy/profile/progress`
- bloqueo de `console.error`
- bloqueo de `pageerror`
- bloqueo de `4xx/5xx` en API
- bloqueo de `404/5xx` en `_next/static`

Regla:

- `npm run test:e2e:academy:deep` usa `frontend/scripts/run-managed-playwright.mjs`; no depende de arrancar Next manualmente.

QA manual complementaria con consola abierta sobre:

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

Notas obligatorias:

- revisar `docs/ACADEMY_RBAC_MATRIX.md` antes de tocar enrollments, progress o admin flows
- validar ownership además del permiso en rutas de estudiante
- recordar que `EDITOR` y `LECTOR` no se resuelven igual en seed persistido y fallback runtime

## 9. Criterio de cierre

Una tarea de Academy queda cerrada cuando:

- smoke backend relevante pasa
- rutas afectadas se probaron manualmente
- smoke frontend profundo pasa si el cambio toca profile/progress o view switchers
- consola no muestra errores nuevos
- si cambia contrato, `ACADEMY_API_CONTRACTS.md` se actualiza
- si cambia estado o backlog, `ESTADO_ACADEMY.md` se actualiza

---

## 10. Casos adicionales auditoría 2026-07-18 (ACAD-*)

Estos casos son obligatorios mientras los IDs `ACAD-*` de `docs/ESTADO_ACADEMY.md §15` estén en estado Pendiente.

### 10.1. CRÍTICOS

#### Caso ACAD-CRIT-001 — Mismatch UUID

**Setup.** Usuario autenticado (cualquier rol con `academy:read`) en `/plataforma/academy/courses`.

**Pasos:**
1. Inspeccionar network al cargar cursos: `response[i].id` debe ser string UUID, no number.
2. Verificar que el cliente **no** declare `id: number` en `CourseCatalog.tsx`.
3. Cross-check: si el usuario tiene una inscripción previa (`enrolledCourseIds`), el botón debe mostrar "Continuar Curso", no "Inscribirme Ahora".

**Verificación automática:**
```bash
grep -n "id: number" frontend/src/components/CourseCatalog.tsx   # debe estar vacio
grep -n "id: number" frontend/src/components/MyEnrollments.tsx   # debe estar vacio
```

#### Caso ACAD-CRIT-002 — Dashboard endpoint

**Setup.** Manager en `/plataforma/academy`.

**Pasos:**
1. Abrir DevTools → Network.
2. Verificar que el fetch principal va a `/dashboard/academy` (NO `/academy/dashboard/metrics`).
3. Inspeccionar payload: debe contener `cards`, `enrollment_trends`, `top_courses`.
4. Si backend solo retorna `cards`, documentar el gap y elegir fix (extender backend o reducir cliente).

**Comando de inspección backend:**
```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/academy/dashboard/metrics | jq 'keys'
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/dashboard/academy | jq 'keys'
```

### 10.2. ALTOS

#### Caso ACAD-HIGH-001 — Sidebar filtrado por nivel

**Setup.** Tres roles: LECTOR, EDITOR, GESTOR (ADMIN), en `/plataforma/academy`.

**Pasos:**
1. Como LECTOR: el sidebar NO debe mostrar "Panel Docente" ni "Coordinación".
2. Como EDITOR: debe mostrar "Panel Docente" pero NO "Coordinación".
3. Como GESTOR: debe mostrar ambos.
4. Click en un link oculto inconsistente responde `403` o `404` (managed por backend), no rompe la UI.

#### Caso ACAD-HIGH-002 — QR code local

**Setup.** Estudiante con certificado emitido en `/plataforma/academy/certificates`.

**Pasos:**
1. Inspeccionar network al cargar CertificateView: NO debe haber request a `api.qrserver.com` ni similares.
2. El QR debe generarse client-side con `react-qr-code` o server-side como base64.
3. Validar visualmente que el QR escaneado devuelve URL del certificado.

#### Caso ACAD-HIGH-003 — Shells (AcademyDetailShell vs WorkspaceLayout)

**Setup.** Navegar por todas las rutas `/plataforma/academy/**/*`.

**Pasos:**
1. Identificar cuáles rutas rinden con `AcademyDetailShell` y cuáles con `WorkspaceLayout`.
2. Verificar visualmente que ambas tienen coherencia de tokens (`bg-primary`, `--border`, etc.) y dark mode.
3. Decidir consolidación o documentar la variante.

#### Caso ACAD-HIGH-004 — Sidebar config dual

**Setup.** Editor.

**Pasos:**
1. `grep` debe mostrar que los items del sidebar académico vienen de una SOLA fuente.
2. `moduleConfigs.ts:academy` y `app/plataforma/academy/layout.tsx` deben tener los mismos items.

### 10.3. MEDIOS

#### Caso ACAD-MED-001 — Foro global solo para Editor/Manager

**Setup.** Student sin `academy:edit`.

**Pasos:**
1. Intentar `POST /forum/threads` con `course_id=null` y `title="hack"`.
2. Debe responder `403` con mensaje claro (no genérico 403).

#### Caso ACAD-MED-002 — Marcar hilo como resuelto

**Setup.** Cualquier usuario autenticado.

**Pasos:**
1. `PATCH /forum/threads/{id}/resolve` debe alternar `is_resolved`.
2. Solo Editor/Manager pueden invocar; otros reciben 403.

#### Caso ACAD-MED-003 — Retractar entrega

**Setup.** Estudiante que entregó una asignación incorrecta.

**Pasos:**
1. `DELETE /admin/submissions/{id}` con `AcademyEditor` o el propio estudiante (ownership).
2. Soft delete (`deleted_at`), no hard delete.
3. **Verificación posterior (cierre 2026-07-18):** `AcademyActivityLog` con `event_type="assignment_submission_archived"` debe existir y contener `payload_json` con `submission_id`, `file_url`, `lesson_id`, `enrollment_id`, `archived_at`, `archived_by_persona_id`. Las llamadas posteriores a `GET /admin/submissions` y `PATCH /admin/submissions/{id}/grade` deben **no** ver/modificar entregas archivadas. `pytest tests/test_academy_api.py::test_delete_submission_archives_with_payload_json` automatiza este path.

### 10.4. BAJOS

#### Caso ACAD-LOW-001 — Download/Share certificado

**Setup.** `/plataforma/academy/certificates/[code]`.

**Pasos:**
1. Click en "Descargar PDF": o descarga real, o botón removido.
2. Click en "Compartir Logro": o copia link al portapapeles, o botón removido.

#### Caso ACAD-LOW-002 — Submit assessment sin enrollment_id válido

**Setup.** Estudiante inscrito en un curso.

**Pasos:**
1. `POST /assessments/{id}/submit` con `enrollment_id` random.
2. Backend ignora el payload y opera sobre el enrollment propio del usuario autenticado.
3. Comprobar que el log del backend muestra uso de `current_user.id`.

### 10.5. Gates adicionales en smoke

Para que su QA de Academy cierre Fase 0 (auditoría 2026-07-18):

- [ ] No hay requests a `api.qrserver.com` en build.
- [ ] Network en `/plataforma/academy` contiene al menos 1 fetch a `/dashboard/academy` (o `/academy/dashboard/metrics` si se elige ese fix).
- [ ] Sidebar S2 como LECTOR debería mostrar 3 grupos y ~8 items, no 12.
- [ ] Build de frontend no muestra warning de TypeScript sobre `id: number` vs `id: string`.

---

## 11. Checklist completo de regresión

Consolidación rápida (marca o expande):

```bash
# 1. Smoke backend
cd /root/ccf && ./venv/bin/python scripts/test_academy_quality.py

# 2. Pytest backend
cd /root/ccf && ./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_academy_api.py \
  tests/test_academy_domain.py

# 3. Typecheck frontend
cd /root/ccf/frontend && npx tsc --noEmit

# 4. E2E academy
cd /root/ccf/frontend && npm run test:e2e:academy
cd /root/ccf/frontend && npm run test:e2e:academy:deep

# 5. Build frontend (opcional)
cd /root/ccf/frontend && npm run build

# 6. Inspección específica auditoría
grep -rn "id: number" frontend/src/components/CourseCatalog.tsx frontend/src/components/MyEnrollments.tsx
grep -rn "api.qrserver.com" frontend/
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/dashboard/academy | jq '. | keys'
```

Cierre completo → no queda ningún ACAD-* Pendiente.

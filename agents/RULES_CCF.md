# Reglas CCF Obligatorias — Aplicables a TODOS los agentes

**Versión:** 1.0 — 2026-08-22
**Audiencia:** auditores, reviewers, challengers, victory_auditors, workers, explorers, orchestrators.

Todo agente que opere en la plataforma CCF (/root/ccf) DEBE conocer y aplicar estas reglas. Los auditores DEBEN verificar su cumplimiento. Los workers DEBEN respetarlas al implementar. Los explorers DEBEN reportar violaciones como hallazgos.

---

## 1. Backend (FastAPI + SQLAlchemy + Python 3.12)

- **`datetime.now(timezone.utc)`** — PROHIBIDO `datetime.utcnow()` (deprecado).
- **Actor UUID obligatorio** — toda mutación exige actor canónico. Ausente/malformado = 401. Creator sin sede = 409.
- **`sede_id` kwonly en CRUD** — patrón: `def fn(db, persona_id, *, sede_id: Optional[UUID] = None)`.
- **`sede_id` se obtiene del usuario autenticado** (`get_user_sede_id()`), NO del cliente. Re-validado en capa CRUD.
- **Filtro NULL globals** — `Model.sede_id.is_(None) | (Model.sede_id == sede_id)` para modelos que permiten NULL = global.
- **`get_db` injection** — inyección de sesión de DB en dependencias FastAPI.
- **`require_*` permission guards** — validación de permisos en dependencias (`backend/core/permissions.py`).
- **HTTPException con códigos semánticos** — 400, 401, 403, 404, 409, 422. No genéricos.
- **Soft deletes only** — `deleted_at`, `estado`, `is_active`. No hard DELETE en entidades transaccionales.
- **`DateTime(timezone=True)`** — todas las fechas persistidas con timezone.
- **VENV Activation** — `cd /root/ccf && ./venv/bin/python -m pytest` (no `python3` directo).

## 2. Base de Datos (PostgreSQL + Alembic)

- **UUID PKs obligatorio** — `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`.
- **`personas.id` es identidad canónica** — `auth_users.id` comparte el mismo UUID. Sin tablas paralelas para personas.
- **Migraciones inmutables** tras merge a `main` — solo se agregan nuevas versiones, nunca se editan cerradas.
- **`upgrade()` y `downgrade()` reversibles** — toda migración nueva debe ser reversible.
- **Sin scripts `_tmp_*`/`_scratch_*`** en `scripts/`.
- **SQLite tz-info loss** — helper defensivo `_as_aware_utc()` en comparaciones timestamp contra SQLite.
- **Alembic head:** `20260810_0002_kernel_roles_uuid_pk`.

## 3. Frontend (Next.js 15 + React 19 + TypeScript)

- **`apiFetch()`** — NO `fetch()` crudo. Siempre vía `lib/http.ts`.
- **Prefijo `/plataforma/`** — toda ruta interna de navegación usa `/plataforma/...`.
- **Drawers, NO Modals** — flujos create/edit/view usan drawers (SidePanel, RightPanel), no modals/AlertDialog.
- **Tokens semánticos** — `hsl(var(--primary))`, `hsl(var(--surface-2))`, etc. PROHIBIDO `bg-blue-500`, `text-gray-400`, colores hardcodeados.
- **`clsx`** para clases condicionales — no template literals concatenados.
- **TypeScript estricto** — cero `any` injustificado.
- **Estados de carga/vacío/error** — Loading/Skeleton, EmptyState, Toasts (sonner).
- **Confirmación antes de acciones destructivas**.
- **Lucide icons** para iconografía.

## 4. Design System (3 capas)

- **Capa 1: `src/design/components/DS*.tsx`** — primitivas atómicas (DSButton, DSCard, DSInput, DSModal, DSSelect, DSTable, DSTabs, DSToast, DSTooltip, etc.). Import desde `@/design`.
- **Capa 2: `src/components/ui/`** — compuestos que orquestan primitivas. Import desde `@/components/ui/` o `@/components` (barrel).
- **Capa 3: `src/components/index.ts`** — barrel export unificado.
- **`forwardRef`** en DSButton, DSInput, DSSelect.
- **Storybook** — todo componente DS nuevo debe tener `.stories.tsx` + `.test.tsx`.
- **Tokens en `tokens-semantic.ts`** — fuente de verdad TypeScript de las variables CSS.

## 5. Reglas Transversales

- **Pre-push hook** — gate estructural + smoke tests (50) + modular quality checks. Escanea `"legacy"` en `.py`/`.ts`/`.tsx`/`.md`.
- **`npm run lint -- --max-warnings=0`** — debe pasar limpio. Es criterio transversal OBLIGATORIO.
- **`npx tsc --noEmit`** = 0 errores — typecheck obligatorio.
- **Coverage gate actual: 38%** — `pytest.ini` tiene `--cov-fail-under=38`. El objetivo aspiracional es 70% pero el gate enforcado es 38%. Los agentes DEBEN reportar el coverage real y flaggear si está por debajo del 38% (fail) o por debajo del 70% (warning aspiracional).
- **jest-axe** — tests de accesibilidad con `toHaveNoViolations` en componentes DS/UI.
- **Commit-per-hallazgo** — cada hallazgo/fix se commitea individualmente.
- **Prefijo commit:** `feat(cms):`, `docs(cms):`, `fix(cms):` según corresponda.
- **Sistema `task`** (T1 + sub-tareas T1.1…) — registrar plan ANTES de codear.
- **PM2 restart** — después de `npm run build` en frontend: `pm2 restart ccf-frontend-staging`.
- **Producción** — todas las pruebas read-only y seguras para datos de producción.

## 6. Checklist de Auditoría CCF

Todo auditor/reviewer/challenger/victory_auditor DEBE verificar:

### Backend
- [ ] No `datetime.utcnow()` en código nuevo/modificado (`grep -rn "utcnow" backend/ --include="*.py"`)
- [ ] `sede_id` filtrado en queries (no trust del cliente)
- [ ] Actor UUID presente en mutaciones (401 si ausente)
- [ ] UUID PKs en modelos nuevos
- [ ] Soft deletes (no hard DELETE)
- [ ] `DateTime(timezone=True)` en columnas nuevas
- [ ] HTTPException con códigos semánticos

### Frontend
- [ ] `apiFetch()` usado (no `fetch()` crudo) (`grep -rn "fetch(" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v apiFetch | grep -v node_modules`)
- [ ] Rutas internas con prefijo `/plataforma/`
- [ ] Drawers para create/edit/view (no modals/AlertDialog)
- [ ] Tokens semánticos `hsl(var(--*))` (no `bg-blue-500`, `text-gray-400`)
- [ ] `clsx` para clases condicionales
- [ ] Cero `any` injustificado
- [ ] Estados loading/empty/error presentes
- [ ] Componentes DS* usados donde aplique (no `<button>` crudo cuando existe `DSButton`)

### Base de Datos
- [ ] Migraciones nuevas reversibles (`upgrade()` + `downgrade()`)
- [ ] No modificación de migraciones cerradas
- [ ] Índices en `sede_id` y FKs frecuentes

### Transversal
- [ ] `npm run lint -- --max-warnings=0` pasa
- [ ] `npx tsc --noEmit` = 0 errores
- [ ] `pytest` con venv: `cd /root/ccf && ./venv/bin/python -m pytest`
- [ ] No substring `"legacy"` en archivos nuevos
- [ ] Commit prefix correcto (`feat(cms):` / `docs(cms):` / `fix(cms):`)
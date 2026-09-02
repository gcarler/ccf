# Reglas CCF Obligatorias — Aplicables a TODOS los agentes

**Versión:** 1.1 — 2026-08-23
**Audiencia:** todos los agentes y herramientas que operen CCF (Codex, Freebuff, Agy, Miml, OpenCode, Claude, auditores, reviewers, challengers, victory_auditors, workers, explorers y orchestrators).

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
- **Alembic head:** `20260822_0002_evangelism_sede_indexes`.

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
- **Deploy exclusivo** — solo puede existir un deploy/build activo para el frontend. Está prohibido ejecutar `npm run build`, `next build` o reiniciar PM2 desde una sesión antigua del agente, un worktree no autorizado o un proceso paralelo mientras exista otro deploy en curso.
- **Owner del deploy** — antes de construir se debe verificar el propietario de `.next-command.lock` y los procesos `build-safe`, `next build` y `npm run build`. No se debe borrar el lock sin validar si su proceso sigue vivo; si hay un proceso huérfano, se detiene de forma explícita antes de continuar.
- **Ruta canónica** — los deploys del frontend deben usar `scripts/deploy_frontend.sh` o el procedimiento de worktree alternativo documentado en `docs/RUNBOOK_PRODUCCION.md`. Una sesión `agy`/agente no debe dejar un comando de deploy persistente en tmux.
- **Producción** — todas las pruebas read-only y seguras para datos de producción.

### 5.1 Protocolo obligatorio de commit, integración y push

Este protocolo aplica a cualquier agente y mantiene una sola línea estable:

1. **`main` es la única rama canónica y estable.** Nunca se usa como worktree de
   trabajo sucio ni se publica directamente.
2. **Cada módulo tiene una rama propietaria.** Usa `feature/academy`,
   `feature/evangelism`, `feature/cms`, `feature/messaging` u otra rama aprobada
   para el módulo. Un commit debe contener una unidad temática.
3. **La rama propietaria se publica sola.** Desde su worktree limpio usa
   `scripts/push_branch.sh origin <rama>`. El helper comprueba la rama activa, la
   base remota, el contrato de ownership, lint, pruebas y build/validación
   proporcional mediante el `pre-push`. Está prohibido `--no-verify`.
4. **Toda integración nace desde el último `origin/main`.** Ejecuta:
   `scripts/create_integration_branch.sh origin <rama-propietaria> integration/<tema>`.
   La rama temporal debe incorporar una sola rama propietaria y publicarse como
   la unidad que se revisará.
5. **Los gates son obligatorios antes de publicar o fusionar:** contrato de rama,
   `git diff --check`, lint, pruebas proporcionales y build frontend o validación
   backend según el diff. La evidencia debe acompañar la integración.
6. **Los conflictos se conservan separados.** Si el merge falla, se deja la rama
   `integration/*` con el conflicto visible para resolución manual. No se usa
   `merge -X theirs`, force push ni una fusión a la fuerza.
7. **Después de fusionar a `main`, se archiva la rama temporal.** Ejecuta
   `scripts/archive_merged_branch.sh origin integration/<tema>`. El helper exige
   que el SHA de la integración sea ancestro de `origin/main`, crea
   `archive/merged/integration-<tema>`, confirma el mismo SHA remoto y solo
   entonces elimina la rama temporal. La rama propietaria del módulo permanece
   activa para trabajo posterior.
8. **Cerrar con evidencia.** Comprobar `git ls-remote`, registrar los SHA y dejar
   limpios los worktrees. El deploy es una operación aparte y sigue
   `docs/RUNBOOK_PRODUCCION.md`.
9. **Las ramas retiradas se archivan con aviso visible.** Usa
   `scripts/archive_branch.sh origin merged|stale <rama>`. El helper conserva el
   SHA exacto bajo `archive/merged/` o `archive/stale/`, exige que el worktree de
   la rama fuente ya no este activo y elimina la fuente solo despues de confirmar
   el respaldo remoto. Una rama en `docs/ARCHIVED_BRANCHES.md` esta marcada como
   `ARCHIVADA - NO REACTIVAR`: cualquier rescate debe comenzar en una rama nueva
   basada en el `main` actual. `archive/*` es inmutable y no se sobrescribe.

Comandos canónicos:

```bash
git status --short --branch
git diff --check
./venv/bin/python scripts/check_branch_contract.py \
  --branch "$(git branch --show-current)" --base origin/main --head HEAD
scripts/push_branch.sh origin "$(git branch --show-current)"
git ls-remote --heads origin "$(git branch --show-current)"
scripts/create_integration_branch.sh origin feature/academy integration/academy-<fecha>
scripts/archive_merged_branch.sh origin integration/academy-<fecha>
scripts/archive_branch.sh origin stale feature/security-hardening
```

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
- [ ] Rama propietaria confirmada y worktree sin cambios ajenos
- [ ] Integración creada desde el último `origin/main`
- [ ] `scripts/check_branch_contract.py` pasó para la rama objetivo
- [ ] Lint, pruebas y build/validación proporcional registrados
- [ ] Conflictos resueltos explícitamente o rama temporal conservada separada
- [ ] Push realizado con `scripts/push_branch.sh`, sin `--no-verify`
- [ ] SHA remoto confirmado con `git ls-remote`
- [ ] Rama temporal archivada bajo `archive/merged/` solo después de fusionar a `main`
- [ ] Rama stale archivada bajo `archive/stale/` con aviso en `docs/ARCHIVED_BRANCHES.md`
- [ ] Ninguna rama marcada `ARCHIVADA - NO REACTIVAR` fue reutilizada

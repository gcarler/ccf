# Plan de Calidad — Plataforma Compartida CCF

> **Objetivo:** operar auth, RBAC, runtime HTTP, layout base, componentes UI compartidos y gates transversales como una capa propietaria con validación multi-módulo, evitando que cambios locales rompan varias áreas a la vez.

## 1. Regla de trabajo

- Todo cambio en auth, permisos, `personas.id`, `sede_id`, `apiFetch`, layouts, AG Grid, calendar/gantt o inline editors se trata como cambio de plataforma compartida.
- Cada cambio debe mapearse a un ID estable de `docs/ESTADO_PLATAFORMA_COMPARTIDA.md`.
- No mezclar features de módulo con refactors de plataforma en la misma unidad si no son inseparables.
- Si el blast radius toca varios módulos, la verificación mínima debe cubrirlos explícitamente.
- Si un patrón se repite entre módulos, consolidarlo en `docs/BACKLOG_DRIFT_TRANSVERSAL_CCF.md`.

## 2. Fase 0 — Diagnostico base

**ID:** `PLATFORM-FASE0-DIAG`

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_PLATAFORMA_COMPARTIDA.md
cat docs/PLATAFORMA_AUTH_RBAC_API_UI.md
cat docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md
cat docs/PLATAFORMA_UI_BASE_PROTEGIDA.md
cat docs/PLATAFORMA_MATRIZ_MODULAR.md
cat docs/BACKLOG_DRIFT_TRANSVERSAL_CCF.md
cat docs/PLATAFORMA_COMPARTIDA_QA_CHECKLIST.md
grep -nE "PARCIAL-|PEND-" docs/ESTADO_PLATAFORMA_COMPARTIDA.md
./venv/bin/python scripts/test_platform_quality.py
```

Validación mínima bruta:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_permissions_and_more.py \
  tests/test_core_all.py \
  tests/test_structural_contracts.py
cd /root/ccf/frontend && npm run build
```

Criterio de salida:

- El fallo real queda clasificado como `auth runtime`, `RBAC`, `owner incorrecto`, `UI base`, `HTTP client`, `AG Grid`, `layout` o `drift cross-modulo`.
- No se toca un módulo consumidor antes de fijar el contrato raíz compartido.

## 3. Fase 1 — Auth, runtime y RBAC raiz

**IDs:** `PARCIAL-RBAC-ROOT-001`, `PEND-DRIFT-AUTH-001`

Orden:

1. Revalidar `/api/v3/auth/*` como auth canónica.
2. Confirmar resolución de permisos, módulos y roles legacy en guards backend y frontend.
3. Revisar consumidores que aún dependan de rutas auth legacy o forma de payload antigua.
4. Actualizar contratos si cambia la shape real de sesión, permisos o transporte auth.

Criterio de salida:

- No quedan fetches estructuralmente dependientes de auth legacy sin estar documentados.
- RBAC raíz y runtime auth quedan sincronizados entre backend y frontend.

## 4. Fase 2 — UI base y primitives compartidas

**IDs:** `PARCIAL-UI-BASE-001`, `PARCIAL-PLATFORM-E2E-RUNTIME-001`

Orden:

1. Tratar `WorkspaceLayout`, sidebars, `TableView`, `UniversalTableView`, AG Grid, calendar/gantt e inline editors como superficie protegida.
2. Validar registro de módulos AG Grid y eliminación de temas legacy si se toca una tabla compartida.
3. Revalidar al menos CRM, Proyectos y Evangelismo cuando cambie una primitive compartida.
4. Ampliar runner administrado de Playwright a cualquier suite profunda nueva de rutas protegidas.

Criterio de salida:

- Las primitives compartidas dejan cobertura suficiente para detectar blast radius.
- Ningún cambio de UI base se aprueba solo con una ruta local.

## 5. Fase 3 — Matriz modular y selector de gates

**IDs:** `PARCIAL-PLATFORM-MATRIX-001`, `PARCIAL-PLATFORM-DRIFT-001`

Orden:

1. Mantener `docs/PLATAFORMA_MATRIZ_MODULAR.md` y `docs/MATRIZ_COBERTURA_MODULAR_CCF.md` alineados con la realidad.
2. Revalidar `scripts/select_quality_checks.py` y `scripts/hooks/pre-push` cuando cambien owners o patrones.
3. Subir cobertura cuando aparezcan gaps repetidos en módulos protegidos.

Criterio de salida:

- El owner y gate mínimo de cada cambio quedan visibles antes del commit.
- La plataforma compartida deja de depender de memoria oral.

## 6. Fase 4 — Smoke transversal y rutas críticas

**ID:** `PEND-PLATFORM-SMOKE-001`

Comandos actuales:

```bash
cd /root/ccf
./venv/bin/python scripts/test_platform_quality.py

cd /root/ccf/frontend
npm run test:e2e:modules
npx playwright test tests/e2e/platform-critical-routes.spec.ts
```

Regla:

- Si se toca auth, guards, layout o UI base, el smoke debe escalar a módulos consumidores reales y no quedarse solo en pruebas estructurales.

Criterio de salida:

- La plataforma compartida tiene una ruta de validación mínima y otra ampliada.
- Los cambios transversales ya no se aprueban con QA parcial.

## 7. Fase 5 — QA final y release

**ID:** `PLATFORM-FASE5-QA`

Comandos mínimos:

```bash
cd /root/ccf
./venv/bin/python scripts/test_platform_quality.py
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_permissions_and_more.py \
  tests/test_core_all.py \
  tests/test_structural_contracts.py
```

Si se toca frontend compartido:

```bash
cd /root/ccf/frontend
npm run build
npx playwright test tests/e2e/platform-critical-routes.spec.ts
```

Criterio de salida:

- `docs/ESTADO_PLATAFORMA_COMPARTIDA.md` se actualiza si cambia backlog o estado.
- Los contratos compartidos se sincronizan si cambia auth, RBAC, runtime o UI base.
- Todo cambio transversal deja explícito el blast radius y su rollback mínimo.

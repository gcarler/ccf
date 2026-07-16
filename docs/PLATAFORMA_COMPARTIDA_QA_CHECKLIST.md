# QA Checklist — Plataforma Compartida

## 1. Antes de tocar codigo

- Leer `ESTADO_PLATAFORMA_COMPARTIDA.md`.
- Leer `PLATAFORMA_AUTH_RUNTIME_CONTRACT.md` si el cambio toca login, refresh, OAuth, perfil o sesiones.
- Leer `PLATAFORMA_UI_BASE_PROTEGIDA.md` si el cambio toca layout, grids o editores inline.
- Leer `PLATAFORMA_MATRIZ_MODULAR.md` para decidir owner y smoke por modulo impactado.
- Clasificar el cambio: auth, permisos, admin, cliente HTTP, layout o UI base.
- Definir el blast radius antes de editar.

## 2. Validacion backend minima

```bash
cd /root/ccf
./venv/bin/python scripts/test_platform_quality.py
```

Gate modular por hook:

```bash
cd /root/ccf
CCF_PRE_PUSH_MODE=fast scripts/hooks/pre-push
CCF_PRE_PUSH_MODE=full scripts/hooks/pre-push
CCF_PRE_PUSH_MODE=full CCF_PRE_PUSH_E2E=1 scripts/hooks/pre-push
CCF_PRE_PUSH_MODE=full CCF_PRE_PUSH_DEPLOY=1 scripts/hooks/pre-push
```

Regla:

- `fast`: sintaxis, lint, cadena Alembic, smoke/structural y checks seleccionados por diff
- `full`: agrega health/runtime, build/PM2 y verificación de frontend actual
- `CCF_PRE_PUSH_E2E=1`: agrega `npm run test:e2e:modules` si el entorno E2E autenticado está configurado
- `CCF_PRE_PUSH_DEPLOY=1`: ejecuta release solo después de que el gate pase
- si el diff toca `ESTADO_*`, contratos API, matrices RBAC o checklists QA de un owner modular, el selector debe disparar al menos el smoke canónico de ese owner; docs genéricos siguen sin checks extra
- el hook debe imprimir `Owners / razones` para que cada gate modular quede trazable al archivo o superficie shared que lo activó

## 3. Validacion ampliada segun cambio

- si toca permisos o RBAC: `tests/test_permissions_and_more.py`
- si toca core de seguridad/permisos: `tests/test_core_all.py`
- si toca auth/runtime: `./venv/bin/python -m py_compile backend/api/auth_v3.py` y `./venv/bin/python -m pytest -q -o addopts='' tests/test_auth_me.py tests/test_auth_v3_deep.py tests/test_structural_contracts.py`
- si toca frontend base: `cd frontend && npm run build`
- si toca rutas críticas compartidas o assets/base shell: `cd frontend && npm run test:e2e:platform`
- si se quiere validar toda la primera capa modular autenticada: `cd frontend && npm run test:e2e:modules`
- si se quiere validar la misma capa con varios usuarios reales: `cd frontend && npm run test:e2e:modules:matrix`
- si se toca una suite profunda protegida: usar el runner administrado (`npm run test:e2e:projects:detail`, `npm run test:e2e:evangelism:deep` o `npm run test:e2e:auth:managed`) en vez de levantar Next manualmente
- si toca grids/layouts: revisar al menos CRM, proyectos y evangelismo
- si toca AG Grid: confirmar que no reaparezca `ag-grid.css` ni themes legacy

## 4. Checks manuales obligatorios

- login con `/api/v3/auth/login` funciona
- refresh session no entra en loop
- `/plataforma/account` puede consultar `/api/v3/auth/me`
- reenvío de verificación usa `/api/v3/auth/send-verification-email`
- una pantalla CRM autenticada carga
- una pantalla Projects autenticada carga
- una pantalla Evangelism autenticada carga
- no aparecen 401/403/404/500 inesperados en consola por assets o API base

## 5. No aprobar si pasa esto

- endpoints legacy de auth reintroducidos
- payloads auth nuevos fuera del contrato JSON canónico
- permisos definidos fuera de `permissions.py`
- `fetch()` directo nuevo donde aplica `apiFetch`
- cambio en `TableView` o layout sin validar modulos dependientes
- mezcla de `themeQuartz` con CSS legacy de AG Grid

## 6. Backlog QA

- `PEND-RBAC-ROOT-001` cerrada el 2026-07-16 en `PLATAFORMA_AUTH_RBAC_API_UI.md`
- `PEND-DRIFT-AUTH-001` parcial el 2026-07-16 en `PLATAFORMA_AUTH_RUNTIME_CONTRACT.md`
- `PEND-PLATFORM-SMOKE-001` cerrada el 2026-07-16 con `scripts/test_platform_quality.py`
- `PEND-UI-BASE-001` cerrada el 2026-07-16 en `PLATAFORMA_UI_BASE_PROTEGIDA.md`
- `PEND-PLATFORM-MATRIX-001` cerrada el 2026-07-16 en `PLATAFORMA_MATRIZ_MODULAR.md`

# QA Checklist — Plataforma Compartida

## 1. Antes de tocar codigo

- Leer `ESTADO_PLATAFORMA_COMPARTIDA.md`.
- Leer `PLATAFORMA_UI_BASE_PROTEGIDA.md` si el cambio toca layout, grids o editores inline.
- Leer `PLATAFORMA_MATRIZ_MODULAR.md` para decidir owner y smoke por modulo impactado.
- Clasificar el cambio: auth, permisos, admin, cliente HTTP, layout o UI base.
- Definir el blast radius antes de editar.

## 2. Validacion backend minima

```bash
cd /root/ccf
./venv/bin/python scripts/test_platform_quality.py
```

## 3. Validacion ampliada segun cambio

- si toca permisos o RBAC: `tests/test_permissions_and_more.py`
- si toca core de seguridad/permisos: `tests/test_core_all.py`
- si toca frontend base: `cd frontend && npm run build`
- si toca grids/layouts: revisar al menos CRM, proyectos y evangelismo
- si toca AG Grid: confirmar que no reaparezca `ag-grid.css` ni themes legacy

## 4. Checks manuales obligatorios

- login con `/api/v3/auth/login` funciona
- refresh session no entra en loop
- una pantalla CRM autenticada carga
- una pantalla Projects autenticada carga
- una pantalla Evangelism autenticada carga
- no aparecen 401/403/404/500 inesperados en consola por assets o API base

## 5. No aprobar si pasa esto

- endpoints legacy de auth reintroducidos
- permisos definidos fuera de `permissions.py`
- `fetch()` directo nuevo donde aplica `apiFetch`
- cambio en `TableView` o layout sin validar modulos dependientes
- mezcla de `themeQuartz` con CSS legacy de AG Grid

## 6. Backlog QA

- `PEND-RBAC-ROOT-001` cerrada el 2026-07-16 en `PLATAFORMA_AUTH_RBAC_API_UI.md`
- `PEND-PLATFORM-SMOKE-001` cerrada el 2026-07-16 con `scripts/test_platform_quality.py`
- `PEND-UI-BASE-001` cerrada el 2026-07-16 en `PLATAFORMA_UI_BASE_PROTEGIDA.md`
- `PEND-PLATFORM-MATRIX-001` cerrada el 2026-07-16 en `PLATAFORMA_MATRIZ_MODULAR.md`

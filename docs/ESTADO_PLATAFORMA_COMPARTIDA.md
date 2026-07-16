# Estado de Plataforma Compartida — Auth / Admin / RBAC / API / UI Base

> **TL;DR (una linea):** La plataforma compartida concentra auth v3, permisos, roles, layout, `apiFetch`, tablas base y componentes UI reutilizados. Cualquier cambio aqui tiene blast radius multi-modulo y no puede tratarse como arreglo local.

**Proposito.** Handover canonico para la capa compartida de CCF. Este archivo existe para cortar la causa principal de errores redundantes: cambios en piezas base hechos como si afectaran un solo modulo.

**Regla de uso.**

- Si el bug nace en auth, token refresh, permisos, `personas.id`, `sede_id`, layouts, `TableView` o componentes UI base, este es el owner.
- No mezclar cambios de plataforma con features de modulo en el mismo commit si no son inseparables.
- Todo cambio aqui exige validar impacto en varios modulos criticos.

---

## 1. Leer primero (cualquier agente)

```bash
cat /root/ccf/docs/ESTADO_PLATAFORMA_COMPARTIDA.md
cat /root/ccf/docs/PLATAFORMA_AUTH_RBAC_API_UI.md
cat /root/ccf/docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md
cat /root/ccf/docs/PLATAFORMA_UI_BASE_PROTEGIDA.md
cat /root/ccf/docs/PLATAFORMA_MATRIZ_MODULAR.md
cat /root/ccf/docs/PLAN_PLATAFORMA_COMPARTIDA_CALIDAD.md
cat /root/ccf/docs/BACKLOG_DRIFT_TRANSVERSAL_CCF.md
cat /root/ccf/docs/SYSTEM_CALENDAR_CONTRACT.md
cat /root/ccf/docs/PLATAFORMA_COMPARTIDA_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_ARQUITECTURA_MODULAR_CCF.md
cat /root/ccf/docs/ESTADO_ARQUITECTURA_CCF.md
```

## 2. Verificar entorno

```bash
python3 --version && node --version
```

## 3. Recontar superficie vigente (por si drift)

```bash
wc -l /root/ccf/backend/api/auth_v3.py /root/ccf/backend/api/admin.py /root/ccf/backend/core/permissions.py /root/ccf/backend/models_auth.py /root/ccf/backend/models_kernel.py | tail -1
wc -l /root/ccf/frontend/src/app/plataforma/admin/**/*.tsx /root/ccf/frontend/src/app/plataforma/admin/*.tsx /root/ccf/frontend/src/lib/http.ts /root/ccf/frontend/src/components/WorkspaceLayout.tsx /root/ccf/frontend/src/components/ui/TableView.tsx 2>/dev/null | tail -1
```

Referencia observada el **2026-07-16**:

- Superficie frontend contada por archivos: **54**
- Superficie backend contada por archivos: **5**

## 4. Smoke test minimo de plataforma

```bash
cd /root/ccf
./venv/bin/python scripts/test_platform_quality.py
```

Smoke ampliado, si se toca permisos, UI base o hooks compartidos:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_permissions_and_more.py \
  tests/test_core_all.py
cd /root/ccf/frontend && npm run build
```

## 5. Ownership tecnico

| Area | Archivos | Responsabilidad |
|---|---|---|
| Auth v3 | `backend/api/auth_v3.py`, `backend/models_auth.py` | login, refresh, Google OAuth, sesiones |
| Permisos | `backend/core/permissions.py` | taxonomia, guards, roles por modulo |
| Admin/RBAC | `backend/api/admin.py` | roles, permisos por usuario, asignaciones modulares |
| Identidad base | `backend/models_kernel.py` | relaciones persona / roles iglesia / modelo base |
| Cliente HTTP | `frontend/src/lib/http.ts` | `apiFetch`, refresh y errores |
| Layout base | `frontend/src/components/WorkspaceLayout.tsx` | shell de plataforma |
| Tabla base | `frontend/src/components/ui/TableView.tsx`, `frontend/src/components/ui/UniversalTableView.tsx` | grids reutilizados por modulos |
| Vistas temporales base | `frontend/src/components/ui/UniversalCalendarView.tsx`, `frontend/src/components/ui/UniversalGanttView.tsx` | primitives calendario / gantt multi-modulo |
| Inline editors | `frontend/src/components/ui/inline-editors/*.tsx` | edicion embebida compartida |

## 6. Invariantes de plataforma

- Auth canonica vive en `/api/v3/auth/*`.
- El runtime auth compartido y su transporte dual viven en `docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md`.
- `auth_users.id == personas.id` es contrato global.
- Los permisos vienen de `backend/core/permissions.py`; no duplicar taxonomia por modulo.
- `apiFetch` es cliente canonico para frontend plataforma.
- Cambios en layouts, tablas base, calendar/gantt o inline editors deben probar al menos CRM, proyectos y evangelismo.
- AG Grid usa `themeQuartz` + `AllCommunityModule`; no mezclar Theming API con CSS legacy.

## 7. Riesgos estructurales activos

1. **Blast radius alto** `[PARCIAL-PLATFORM-BLAST-001]` — permisos, `apiFetch`, layouts y grids son dependencias compartidas de casi todos los modulos.
2. **Taxonomia mixta de permisos** `[PARCIAL-RBAC-ROOT-001]` — el contrato raíz ya quedó documentado; `ProtectedRoute` ya prioriza permisos canónicos sobre roles legacy, pero Agenda sigue heredando `spiritual_life:*` por diseño y aún quedan superficies de drift por cerrar.
3. **Primitives UI compartidas** `[PARCIAL-UI-BASE-001]` — `WorkspaceLayout`, grids AG Grid, calendar/gantt e inline editors comparten blast radius multi-modulo y requieren owner de plataforma.
4. **Dependencias transversales por modulo** `[PARCIAL-PLATFORM-MATRIX-001]` — sin una matriz operativa era fácil correr gates incompletos o asignar mal el owner.
5. **Drift transversal repetitivo** `[PARCIAL-PLATFORM-DRIFT-001]` — auth/runtime, RBAC heterogeneo, `apiFetch`, AG Grid, `_next/static` y agregadores shared siguen reapareciendo entre modulos si no se clasifican como plataforma.
6. **Suites profundas dependientes de runtime** `[PARCIAL-PLATFORM-E2E-RUNTIME-001]` — las suites Playwright profundas de modulos protegidos no pueden depender de arrancar Next a mano; el runner compartido `frontend/scripts/run-managed-playwright.mjs` ya cubre auth, Proyectos detail y Evangelismo deep, pero debe extenderse al resto de casos equivalentes.

## 8. Pendientes formales

1. **Contrato raiz de RBAC** `[PEND-RBAC-ROOT-001]` — cerrada el 2026-07-16 en `PLATAFORMA_AUTH_RBAC_API_UI.md`; fija módulos canónicos, orden de resolución y matriz mínima por rol.
2. **Checklist de humo de plataforma** `[PEND-PLATFORM-SMOKE-001]` — cerrada el 2026-07-16 con `scripts/test_platform_quality.py`.
3. **Politica de componentes base** `[PEND-UI-BASE-001]` — cerrada el 2026-07-16 en `PLATAFORMA_UI_BASE_PROTEGIDA.md`; formaliza `WorkspaceLayout`, grids AG Grid, calendar/gantt e inline editors como superficie protegida.
4. **Matrices modulares de plataforma** `[PEND-PLATFORM-MATRIX-001]` — cerrada el 2026-07-16 en `PLATAFORMA_MATRIZ_MODULAR.md`; fija consumidores, gates y rutas mínimas por módulo.
5. **Backlog transversal de drift** `[PEND-PLATFORM-DRIFT-001]` — cerrada el 2026-07-16 en `BACKLOG_DRIFT_TRANSVERSAL_CCF.md`; consolida patrones cross-modulo, owners y gates mínimos.
6. **Contrato runtime de auth compartida** `[PEND-DRIFT-AUTH-001]` — parcial el 2026-07-16 en `PLATAFORMA_AUTH_RUNTIME_CONTRACT.md`; migrados consumidores públicos críticos a `/api/v3/auth/*`, quedan rutas admin legacy aisladas como drift activo de plataforma.
7. **Plan operativo canónico de plataforma** `[PEND-PLAN-PLATFORM-001]` — cerrada el 2026-07-16 en `PLAN_PLATAFORMA_COMPARTIDA_CALIDAD.md`; formaliza fases de trabajo para auth, RBAC, UI base y smoke transversal.

## 9. Archivos a revisar primero si falla

1. `backend/core/permissions.py`
2. `backend/api/auth_v3.py`
3. `backend/api/admin.py`
4. `frontend/src/lib/http.ts`
5. `frontend/src/components/WorkspaceLayout.tsx`
6. `frontend/src/components/ui/TableView.tsx`
7. `frontend/src/components/ui/UniversalTableView.tsx`
8. `frontend/src/components/ui/inline-editors/`

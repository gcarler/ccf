# Backlog de Drift Transversal — CCF

> **Objetivo:** consolidar en un solo documento los patrones de error que reaparecen entre modulos para que dejen de tratarse como bugs aislados. Este backlog vive a nivel de plataforma/arquitectura, no dentro de un solo modulo.

## 1. Como usar este backlog

- Abrir este archivo cuando un bug reaparece en dos o mas modulos.
- No crear arreglos locales si el patron ya existe aqui.
- Cada item define:
  - patron de drift
  - capas afectadas
  - owner correcto
  - evidencia actual
  - gate minimo antes de cerrar

## 2. Patrones transversales activos

### DRIFT-AUTH-001 — Sesion/token/OAuth no tratados como plataforma

**Patron.**

- `401`, `403` o `502` en login, refresh o flujos OAuth se investigan desde una pantalla concreta en vez de tratarse como problema de auth compartida.

**Capas afectadas.**

- `backend/api/auth_v3.py`
- `frontend/src/lib/http.ts`
- layouts y rutas `/plataforma/**`

**Owner correcto.**

- plataforma compartida

**Evidencia actual.**

- `docs/ESTADO_PLATAFORMA_COMPARTIDA.md`
- `docs/PLATAFORMA_AUTH_RBAC_API_UI.md`
- `docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md`
- errores historicos reportados en CRM y Evangelismo ligados a auth/runtime
- consumers públicos críticos ya migrados a `/api/v3/auth/*`; queda drift admin legacy en `/auth/stats/summary` y `/auth/sessions`

**Gate minimo.**

- `scripts/test_platform_quality.py`
- `tests/test_permissions_and_more.py`
- prueba manual de flujo autenticado en `/plataforma`

### DRIFT-RBAC-001 — Taxonomia canonica vs guards reales

**Patron.**

- existe una taxonomia de permisos por modulo, pero varios routers usan guards historicos, ownership o shortcuts distintos.

**Capas afectadas.**

- `backend/core/permissions.py`
- routers por modulo
- seeds en `backend/management/seed_user_permissions.py`

**Owner correcto.**

- plataforma compartida + modulo propietario del router

**Evidencia actual.**

- CRM: [docs/CRM_RBAC_MATRIX.md](/root/ccf/docs/CRM_RBAC_MATRIX.md)
- Academy: [docs/ACADEMY_RBAC_MATRIX.md](/root/ccf/docs/ACADEMY_RBAC_MATRIX.md)
- CMS: [docs/CMS_RBAC_MATRIX.md](/root/ccf/docs/CMS_RBAC_MATRIX.md)
- Messaging: [docs/MESSAGING_COMMUNITY_RBAC_MATRIX.md](/root/ccf/docs/MESSAGING_COMMUNITY_RBAC_MATRIX.md)
- Evangelismo: [docs/EVANGELISMO_RBAC_MATRIX.md](/root/ccf/docs/EVANGELISMO_RBAC_MATRIX.md)
- Agenda: [docs/AGENDA_RBAC_MATRIX.md](/root/ccf/docs/AGENDA_RBAC_MATRIX.md)

**Gate minimo.**

- matriz RBAC del modulo actualizada
- smoke del modulo
- `tests/test_permissions_and_more.py` si cambia taxonomia/shared RBAC
- `tests/test_structural_contracts.py` si cambia `ProtectedRoute`, `WorkspaceLayout` o guards frontend compartidos

**Estado parcial 2026-07-16.**

- `frontend/src/components/ProtectedRoute.tsx` ya prioriza `allowedPermissions` como contrato canónico.
- `allowedRoles` queda solo como compatibilidad legacy cuando un call site todavía no tiene permiso backend definido.
- Admin, Academy Coordination y Academy Teacher ya migraron a permisos canónicos.

### DRIFT-HTTP-001 — `apiFetch` vs `fetch` directo

**Patron.**

- pantallas de plataforma rompen refresh, token, manejo de errores o base path porque usan `fetch()` directo o construyen URLs manualmente.

**Capas afectadas.**

- `frontend/src/lib/http.ts`
- pantallas `frontend/src/app/plataforma/**`

**Owner correcto.**

- plataforma compartida si cambia el cliente
- modulo si solo corrige un consumidor concreto

**Evidencia actual.**

- contratos API de CRM, Academy, Evangelismo, Agenda, CMS y Messaging exigen `apiFetch`

**Gate minimo.**

- `cd frontend && npm run build`
- smoke del modulo afectado
- check manual de consola sin `401/404/500` nuevos

### DRIFT-UI-001 — AG Grid, themes y registro de modulos

**Patron.**

- reaparecen errores por CSS legacy, Theming API mixta o modulos no registrados.

**Capas afectadas.**

- `frontend/src/components/ui/TableView.tsx`
- `frontend/src/components/ui/UniversalTableView.tsx`
- pantallas que montan AG Grid

**Owner correcto.**

- plataforma compartida

**Evidencia actual.**

- [docs/PLATAFORMA_UI_BASE_PROTEGIDA.md](/root/ccf/docs/PLATAFORMA_UI_BASE_PROTEGIDA.md)
- errores historicos en CRM y Evangelismo
- registro centralizado de AG Grid en `frontend/src/lib/agGrid.ts`

**Gate minimo.**

- `cd frontend && npm run build`
- `scripts/test_platform_quality.py`
- check manual de grids en CRM, Projects y Evangelismo

### DRIFT-ASSETS-001 — `_next/static` 404 y drift build/runtime

**Patron.**

- la app compila o despliega parcialmente, pero en runtime aparecen `404` de assets `_next/static`.

**Capas afectadas.**

- `frontend/next.config.mjs`
- pipeline/build/deploy
- rutas de plataforma

**Owner correcto.**

- plataforma compartida

**Evidencia actual.**

- errores reportados en Evangelismo
- checklists de CRM, Academy, CMS y Evangelismo ya bloquean cierre con `_next/static` 404

**Gate minimo.**

- `cd frontend && npm run build`
- validacion manual de rutas criticas con consola abierta

### DRIFT-CALENDAR-001 — Agregadores compartidos tratados como modulo aislado

**Patron.**

- fallos de `calendar` o dashboards agregados se corrigen desde un modulo fuente sin revisar el agregador compartido.

**Capas afectadas.**

- `GET /api/system/calendar`
- `frontend/src/components/ui/UniversalCalendarView.tsx`
- `frontend/src/app/plataforma/calendar/**`

**Owner correcto.**

- plataforma compartida, salvo prueba clara de bug en un proveedor concreto

**Evidencia actual.**

- [docs/ESTADO_AGENDA.md](/root/ccf/docs/ESTADO_AGENDA.md)
- [docs/AGENDA_API_CONTRACTS.md](/root/ccf/docs/AGENDA_API_CONTRACTS.md)
- [docs/SYSTEM_CALENDAR_CONTRACT.md](/root/ccf/docs/SYSTEM_CALENDAR_CONTRACT.md)

**Gate minimo.**

- `scripts/test_agenda_quality.py`
- pruebas ampliadas de rutas agenda/calendar si cambia el agregador

### DRIFT-IDENTITY-001 — `personas.id`, ownership y `sede_id` mal clasificados

**Patron.**

- bugs de identidad/tenant se corrigen desde un modulo sin reconocer que el contrato es global.

**Capas afectadas.**

- modelos base
- auth
- CRM
- Academy
- Evangelismo
- Projects

**Owner correcto.**

- plataforma compartida + modulo afectado

**Evidencia actual.**

- [docs/ESTADO_ARQUITECTURA_CCF.md](/root/ccf/docs/ESTADO_ARQUITECTURA_CCF.md)
- `Axioma 3` y contrato `auth_users.id == personas.id`

**Gate minimo.**

- suite estructural/arquitectura
- smoke del modulo tocado

## 3. Regla operativa de clasificacion

Si un bug cae en uno de estos patrones:

1. abrir este backlog
2. clasificar owner correcto
3. ejecutar el gate minimo transversal
4. luego ejecutar el smoke del modulo visible

No invertir el orden.

## 4. Pendientes formales abiertos

1. `PEND-DRIFT-AUTH-001` — parcial el 2026-07-16; contrato runtime documentado, consumidores públicos críticos migrados a `/api/v3/auth/*`, dashboard admin consolidado en `/api/dashboard/admin` y sesiones propias en `/api/v3/auth/sessions*`. Queda pendiente limpiar aliases mock `/auth/me` y `/auth/logout` si dejan de ser necesarios.
2. `PEND-DRIFT-HTTP-001` — auditar consumo restante de `fetch()` directo en pantallas de plataforma.
3. `PEND-DRIFT-UI-001` — consolidar contrato unico AG Grid/shared table para evitar nuevas mezclas de themes o modulos.
4. `PEND-CALENDAR-EVENTS-CONTRACT-001` — cerrada el 2026-07-16 en `docs/SYSTEM_CALENDAR_CONTRACT.md`.
5. `PEND-DRIFT-CLASSIFICATION-001` — integrar este backlog transversal en los handovers y protocolos base.

## 5. Estado

Documento creado el **2026-07-16** como parte del plan de arquitectura modular para cortar errores redundantes cross-modulo.

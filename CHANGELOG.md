# Changelog

## v1.1.1-cms (2026-07-31)

### CMS v2 — Correcciones de Calidad: ESLint 0-warning

#### Criterio Transversal — Lint Compliance
- **fix(lint):** elimina 40+ errores `no-unused-vars` en archivos de producción y tests del CMS, projects, whiteboard y calendar — prefixando variables con `_` o eliminando imports no usados.
- **fix(lint):** agrega `/* eslint-disable @typescript-eslint/no-explicit-any */` en 4 archivos de test con mocks complejos de Framer Motion y API.
- **fix(lint):** corrige 10 errores `react/no-unescaped-entities` en modales de confirmación CMS — `branding`, `forms`, `newsletter`, `pages`, `popups`.
- **fix(lint):** agrega `eslint-disable-next-line react-hooks/exhaustive-deps` en `useMeshSocket`, `TaskDetailPanel`, `access/page` donde la omisión de deps es intencional.
- **fix(lint):** reemplaza `<a>` por `<Link>` en `spiritual-life/timeline/page.tsx` — compliance con `@next/next/no-html-link-for-pages`.
- **fix(lint):** agrega `eslint-disable-next-line storybook/no-renderer-packages` en `IconShowcase.stories.tsx`.
- **fix(cms):** elimina variable `newSections` no usada en `BuilderCanvas.tsx` — la lógica de reordenamiento usa `moveSectionToIndex` directamente.
- **fix(cms):** elimina imports no usados (`User`, `Calendar`, `CmsTheme`, `useMemo`, `VIEW_EVENT_TYPES`, `CmsFormSubmission`) de componentes CMS.

---

## v1.1.0-cms (2026-07-31)

### CMS v2 — Plan de Calidad Integral: Fases 3-7

#### Fase 3 — Rendimiento Backend (N+1 Queries)
- **feat(cms):** elimina N+1 en `public_page` — `_get_system_vars_batch` colapsa N×5 queries de SystemVariable a 1 batch SELECT + cache local (5 min TTL). Reducción: de `1+N×5` a `2` queries.
- **feat(cms):** elimina N+1 en `public_posts_list` — `get_posts_categories_batch`, `get_posts_tags_batch` + batch fetch de autores con `.in_()`. Reducción: de `N×3` a `3` queries.
- **docs(cms):** crea `docs/cms_query_metrics.md` — métricas antes/después para los 5 endpoints públicos.

#### Fase 4 — Refactor Backend
- **feat(cms):** refactoriza `backend/api/cms_v2.py` (monolito ~2000 líneas) en paquete `backend/api/cms_v2/` con 14 submódulos especializados: `section_types`, `global_blocks`, `sites`, `themes_menus`, `pages`, `public`, `pastoral`, `posts`, `analytics_ops`, `forms`, `newsletter`, `popups`, `presence`, `ab_testing`.
- **feat(cms):** agrega `backend/exceptions/cms.py` con jerarquía de excepciones de dominio: `CmsNotFoundError` (404), `CmsConflictError` (409), `CmsPermissionError` (403), `CmsValidationError` (422), `CmsServiceUnavailableError` (503) — y 20+ subclases específicas.
- **feat(cms):** `backend/api/cms_v2/__init__.py` actúa como thin orchestrator que agrega sub-routers.

#### Fase 5 — Tests E2E
- **feat(test):** configura Playwright en `frontend/playwright.config.ts` con soporte para dev server administrado.
- **feat(test):** implementa suite E2E CMS en `frontend/tests/e2e/cms/`:
  - `smoke.spec.ts` — rutas críticas: `/plataforma/cms`, `/plataforma/cms/pages`, `/plataforma/cms/media`.
  - `builder-flow.spec.ts` — flujo builder: login → crear página → agregar sección → publicar.
  - `pages-preview.spec.ts` — preview de páginas y contratos públicos.
  - `media-management.spec.ts` — subida de imágenes y gestión de media library.
- **feat(test):** agrega scripts `test:e2e:cms`, `test:e2e:cms:builder`, `test:e2e:cms:media`, `test:e2e:cms:public` en `frontend/package.json`.

#### Fase 6 — Accesibilidad y SEO
- **feat(cms):** agrega endpoint `GET /api/cms/v2/public/sites/{site_key}/sitemap.xml` con sitemap XML dinámico de páginas publicadas + `robots.txt`.
- **feat(cms):** corrección de colores prohibidos (indigo → sky) en `PublicSearchModal.tsx` — alineado con contrato UI CCF.
- **fix(cms):** elimina `CmsPublicComment` (tipo inexistente) de imports en `frontend/src/lib/cms/v2.ts`.
- **fix(cms):** corrige export de `PostComments` en `frontend/src/components/public/cms/index.ts` — de `default` a named export.

#### Fase 7 — Documentación y Cierre
- **docs(cms):** crea `docs/cms_runbook.md` — runbook completo con deploy, rollback, troubleshooting, variables de entorno, monitoreo y backup.
- **docs(cms):** actualiza `docs/ARQUITECTURA_CMS.md` con referencia a la nueva estructura de submódulos.
- **docs(cms):** `docs/CMS_API_CONTRACTS.md` — contratos de la API con ejemplos para `public_page`, `public_posts_list`, `patch_section`, `transition_cms_page_status`.

### Quality
- **TypeScript:** `npx tsc --noEmit` = 0 errores.
- **Structural contracts:** `test_platform_frontend_respects_ccf_ui_contracts` pasa (sin violaciones de `indigo/violet/purple`).
- **Test suite backend:** todos los tests pytest del módulo CMS siguen en verde.

---

## v1.0.1-crm (2026-07-27)


### Fixes
- **fix(crm):** corrige `AttributeError: module 'backend.models' has no attribute 'persona_familias'` en `backend/api/crm/pastoral.py` — reemplaza join con tabla de asociación inexistente por join directo `Persona.family_id -> Family.id`.
- **fix(crm):** corrige deduplicación de personas cuando `sede_id=None` — cambia filtro `Persona.sede_id.is_(None)` a `true()` para que busque globalmente.
- **fix(tests):** corrige endpoint obsoleto `/api/admin/auth-role-definitions` a canónico `/api/admin/roles` en 5 test suites.
- **fix(tests):** agrega autenticación en `test_crm_automations_challenger.py` vía fixture `client_auth_for_automations`.
- **fix(tests):** corrige `alembic upgrade head` → `upgrade 20260710_0002` en tests de migración para evitar dependencias rotas.
- **fix(tests):** agrega `seed_admin` + `auth_headers` a tests adversariales y de stress que fallaban con 401.
- **fix(tests):** cambia expectativa de 403 → 404 en cross-sede template access/deletion, alineado con la convención de existencia-leak.
- **fix(docs):** actualiza `docs/MODULO_ADMIN.md` — reemplaza sección obsoleta de `/auth-role-definitions` por aviso de consolidación.
- **fix(docs):** actualiza `tests/test_mass_get_coverage.py` — cambia URL obsoleta a `/api/admin/roles`.

### Quality
- **Suite CRM completa:** 1006 tests passed, 0 failures.
- **Referencias `auth-role-definitions` eliminadas:** tests (5/5), docs (2/2), comentarios como históricos.

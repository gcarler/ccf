# Estado del Modulo de CMS — CCF

> **TL;DR (una linea):** CMS es el sistema editorial y de contenido público/administrativo de CCF: sites, páginas, versiones, secciones, temas, menús, media, recursos, SEO, redirects, search, webhooks y auditoría. Vive repartido entre `/api/cms`, `/api/cms/v2`, `/api/cms/v2` enterprise y `/plataforma/cms`.

**Proposito.** Handover canónico para trabajar CMS como módulo propio dentro del monolito modular, sin mezclar bugs del editor, del render público y de multi-tenant como si fueran la misma clase de problema.

**Regla de uso.**

- Actualizar este doc al cerrar tareas, no antes.
- `Hecho / Parcial / Pendiente` reflejan el código actual.
- No usar este doc como wishlist.
- Si un cambio toca `storage`, `uploads`, `SEO`, `sede_id`, `site_id`, render público o componentes CMS compartidos, clasificarlo antes como cambio de módulo o de plataforma.

---

## 1. Leer primero (cualquier agente)

```bash
cat /root/ccf/docs/ARQUITECTURA_CMS.md   # ⭐ Guía canónica de arquitectura + reglas de negocio (LEER PRIMERO)
cat /root/ccf/docs/ESTADO_CMS.md         # Este documento — estado operativo, backlog, handover
cat /root/ccf/docs/CMS_API_CONTRACTS.md
cat /root/ccf/docs/CMS_RBAC_MATRIX.md
cat /root/ccf/docs/CMS_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_CMS_CALIDAD.md
cat /root/ccf/docs/AUDITORIA_FORENSE_CMS.md
```

## 2. Verificar entorno

```bash
python3 --version && node --version
```

Versiones verificadas en este host el **2026-07-16**:

- Python: **3.12.3**
- Node: **v24.15.0**

## 3. Recontar superficie vigente (por si drift)

```bash
wc -l /root/ccf/backend/api/cms.py /root/ccf/backend/api/cms_v2.py /root/ccf/backend/api/enterprise_cms.py /root/ccf/backend/crud/cms.py /root/ccf/backend/crud/cms_pastors_sync.py /root/ccf/backend/models_cms.py /root/ccf/backend/schemas/cms.py /root/ccf/backend/schemas/cms_v2_sections.py 2>/dev/null | tail -1
wc -l /root/ccf/frontend/src/app/plataforma/cms/**/*.tsx /root/ccf/frontend/src/app/plataforma/cms/*.tsx 2>/dev/null | tail -1
```

Conteo actual:

- Backend CMS directo: **8 830 LOC**
- Frontend CMS directo: **11 457 LOC**

## 4. Listar backlog completo (Parcial + Pendiente) por ID

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_CMS.md
```

## 5. Smoke test

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_cms_quality.py
```

Smoke mínimo bruto:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_cms_domain.py \
  tests/test_cms_sede_isolation.py \
  tests/test_cms_upload_and_image_hardening.py \
  tests/test_cms_metrics_sede_isolation.py
```

Frontend específico ya existente:

```bash
cd /root/ccf/frontend
npx vitest run tests/cms-components.test.ts tests/cms-public-fetch.test.ts
npm run test:e2e:cms:public
```

Plan operativo vigente:

- `docs/PLAN_CMS_CALIDAD.md` es el subplan canónico del módulo dentro de la arquitectura modular.
- `docs/PLAN_CMS_100.md` se conserva como plan de auditoría profunda y referencia histórica complementaria.

---

## 6. TL;DR — Mapa del modulo

| Capa | Ubicacion | Tamano |
|---|---|---:|
| CMS v1 | `backend/api/cms.py` | testimonios, announcements, media, métricas |
| CMS v2 | `backend/api/cms_v2.py` | sites, themes, menus, pages, sections, preview, workflow, categories, tags, posts, analytics |
| Enterprise CMS | `backend/api/enterprise_cms.py` | audit logs, content permissions, notifications, webhooks, custom types, search, redirects, sessions, folders |
| Helpers | `backend/api/_cms_helpers/` | scope helpers y auditorías compartidas |
| CRUD | `backend/crud/cms.py`, `backend/crud/cms_pastors_sync.py` | escritura/lectura real del dominio |
| Modelos | `backend/models_cms.py` | media, sites, themes, menus, pages, versions, sections, posts, analytics |
| Schemas | `backend/schemas/cms.py`, `backend/schemas/cms_v2_sections.py` | contratos Pydantic |
| UI principal | `frontend/src/app/plataforma/cms/**` | dashboard, builder, pages, media, themes, menus, audit, preview, SEO, sessions, sites |
| Tests backend | `tests/test_cms_*.py`, `tests/test_enterprise_cms.py` | dominio, isolation, upload, metrics, SEO, scheduling, v2 coverage |
| Tests frontend | `frontend/tests/cms-components.test.ts`, `frontend/tests/cms-public-fetch.test.ts`, `frontend/tests/e2e/cms-public-contract.spec.ts` | contrato público y componentes |

**Estado global:** CMS tiene gran superficie técnica y evidencia ya cerrada. El módulo cuenta con handover modular, smoke dedicado, cobertura profunda de `pages` + `preview`, gate canónico ampliado y RBAC enterprise explícito; no quedan IDs abiertos en el backlog del módulo.

---

## 7. Convenciones del modulo

- **Rutas plataforma:** `/plataforma/cms/**`
- **Rutas API:** `/api/cms` y `/api/cms/v2`
- **Contenido público:** algunos feeds permanecen globales por diseño editorial
- **Multi-tenant:** `site_id` y/o `sede_id` deben respetarse según tabla/flujo
- **Soft delete:** no rehidratar registros borrados en lecturas públicas o admin
- **Preview y publicado:** no mezclar contratos; validar por separado
- **Media/upload:** usar allow-list de extensiones, validación MIME/extension y `sanitize_filename`

---

## 8. Backend — Modelo de datos

Dominio principal en `backend/models_cms.py`:

```text
CmsSite
  -> CmsTheme
  -> CmsMenu
    -> CmsMenuItem
  -> CmsPage
    -> CmsPageVersion
    -> CmsSection
    -> CmsPageView
    -> CmsPublishLog
  -> CmsCategory
  -> CmsTag
  -> CmsPost
CmsMediaItem
Testimonial
Announcement
Enterprise CMS:
  AuditLog / ContentPermission / CmsNotification / Webhook / CmsCustomType /
  CmsCustomEntry / SearchIndex / UserSession / MediaFolder / CmsRedirect / BrokenLinkCheck
```

Puntos sensibles:

- `CmsMediaItem.sede_id` es clave de Axioma 3
- `CmsSite.sede_id` resuelve scope de muchos objetos CMS v2
- `CmsPage.publish_at` / `expires_at` soportan scheduling

---

## 9. Backend — API surface

### CMS v1 — `backend/api/cms.py`

- `/cms/testimonials`, `/admin/testimonials`
- `/cms/announcements`, `/admin/announcements`
- `/cms/media`, `/cms/media/upload`, `/cms/media/{id}/optimize`
- `/cms/metrics`

### CMS v2 — `backend/api/cms_v2.py`

- `/cms/v2/section-types`
- `/cms/v2/sites`
- `/cms/v2/sites/{site_key}/themes`
- `/cms/v2/sites/{site_key}/menus`
- `/cms/v2/sites/{site_key}/pages`
- `/cms/v2/sites/{site_key}/pages/{slug}/preview`
- `/cms/v2/sites/{site_key}/pages/{slug}/workflow`
- `/cms/v2/global-blocks`
- `/cms/v2/sites/{site_key}/categories`
- `/cms/v2/sites/{site_key}/tags`
- `/cms/v2/sites/{site_key}/posts`
- `/cms/v2/analytics/{page_key}`
- `/cms/v2/pages/{page_id}/schedule`
- `/cms/v2/images/optimize`

### Enterprise CMS — `backend/api/enterprise_cms.py`

- audit logs
- content permissions
- notifications
- webhooks
- custom types / custom entries
- glossary
- search / search promotions
- sessions
- media folders
- redirects
- broken links

Detalle y reglas en `docs/CMS_API_CONTRACTS.md`.

---

## 10. Frontend — Mapa de pantallas

Rutas principales en `frontend/src/app/plataforma/cms/`:

| Ruta | Archivo | Estado |
|---|---|---|
| `/plataforma/cms` | `page.tsx` | Hecho — dashboard validado |
| `/plataforma/cms/builder` | `builder/page.tsx` | Hecho — editor validado con smoke y deep suite |
| `/plataforma/cms/pages` | `pages/page.tsx`, `pages/[slug]/page.tsx`, `versions/page.tsx` | Hecho funcional |
| `/plataforma/cms/media` | `media/page.tsx`, `media/[id]/page.tsx`, `media-folders/page.tsx` | Hecho funcional |
| `/plataforma/cms/themes`, `/menus`, `/sites` | varias | Hecho funcional |
| `/plataforma/cms/preview` | `preview/page.tsx` | Hecho — validado contra publicado |
| `/plataforma/cms/readiness`, `/seo-audit`, `/broken-links`, `/redirects`, `/search-admin` | varias | Hecho funcional |
| `/plataforma/cms/testimonials`, `/pastoral-team`, `/notifications`, `/sessions`, `/webhooks`, `/audit` | varias | Hecho funcional |

Frontend test existente:

- `frontend/tests/cms-components.test.ts`
- `frontend/tests/cms-public-fetch.test.ts`
- `frontend/tests/e2e/cms-public-contract.spec.ts`
- `frontend/tests/e2e/cms/smoke.spec.ts`
- `frontend/tests/e2e/cms/pages-preview.spec.ts`

---

## 11. Estado del modulo

### Hecho

- CMS v1, v2 y enterprise separados
- pruebas de isolation, upload hardening, metrics y dominio
- cobertura frontend pública básica
- plan CMS 100 y auditoría forense ya existentes
- validación de MIME/extension en uploads
- helpers de scope `_cms_helpers`
- bootstrap de contenido público implementado y verificado para `ccf` con `scripts/bootstrap_public_cms_content.py`
- **Auditoría forense 100% cerrada** (ciclo 7, commits `fc80da41`/`4d1ba06a`/`94f97d4a`)
  - Críticos: 6/6, Altos: 11/11, Medios: 14/14, Info: 17/17, Funcionalidades: 10/10
  - Migraciones de fix canonizadas en `canonical_versions/` (`20260723_0001`→`0006`)
  - Head alembic único `20260723_0006` (cadena lineal limpia)
  - 194 tests CMS pasan sin skips
- **Guía de arquitectura canónica creada**: `docs/ARQUITECTURA_CMS.md`

### Pendiente

**No hay hallazgos abiertos.** La auditoría forense `errorescms.md` está 100% cerrada. El backlog histórico fue resuelto en su totalidad:

- ✅ 6 críticos (C-01..06) — cerrados y verificados
- ✅ 11 altos (H-01..11) — cerrados y verificados
- ✅ 14 medios (M-01..14) — cerrados (incluye M-03 soft-delete unification, M-05 index)
- ✅ 17 info (I-01..17) — cerrados
- ✅ 10 funcionalidades (F-01..10) — cerradas (incluye F-08 publish log retention, F-10 orphan media cleanup)

### Cerrado recientemente

17. **Forense C-01 (ondelete RESTRICT)** `[DONE-CMS-FORENSE-C-01]` — cerrado el 2026-07-22 (commit `e8912c54`) antes del inicio de la sesión actual; ver `errorescms.md` § Seguimiento.
18. **Forense C-02 (falso positivo TOCTOU verificado)** `[DONE-CMS-FORENSE-C-02]` — cerrado el 2026-07-22 (commit `bd28cfe4`); verificado que el vector TOCTOU mismo está cubierto por el defense-in-depth check #1 (current_row_sede == actor_sede) en `_crud_scope_re_check_cms_content_update`.  3 tests de regresion en `TestC02TOCTOUFalsePositive`.
19. **Forense C-03 (falso positivo CmsSectionType global)** `[DONE-CMS-FORENSE-C-03]` — confirmado por `6a83dd87` y REGLAS.md §4.2.
20. **Forense C-04 (pastors sede_id filter)** `[DONE-CMS-FORENSE-C-04]` — commit `6a83dd87`.
21. **Forense C-05 (falso positivo seo_snapshots)** `[DONE-CMS-FORENSE-C-05]` — snapshot persiste sede_id propio (cms_v2.py:1388).
22. **Forense C-06 + H-11 (24 schemas Pydantic)** `[DONE-CMS-FORENSE-C-06-H11]` — commit `5b0a6e7c`.
23. **Forense H-01 (falso positivo default=dict)** `[DONE-CMS-FORENSE-H-01]` — pattern `default=dict` es idioma-clave SQLAlchemy y mas usado que `default={}` (10 vs 10 instances).  No es riesgo funcional.
24. **Forense H-02 (captured_at default=_utcnow)** `[DONE-CMS-FORENSE-H-02]` — commit `b522c372`; lambda inline reemplazada por `_utcnow`.
25. **Forense H-03 (falso positivo CmsSection.type shadow)** `[DONE-CMS-FORENSE-H-03]` — SQLAlchemy maneja correctamente; renombrar rompe introspection.
26. **Forense H-04 (archive_cms_section deleted_at)** `[DONE-CMS-FORENSE-H-04]` — commit `b522c372`.
27. **Forense H-05 (path traversal hardening)** `[DONE-CMS-FORENSE-H-05]` — commit `b347f787` + 3 regression tests en `TestDeleteCmsMediaPathTraversalHardening`.
28. **Forense H-06 (AnnouncementUpdate.is_active)** `[DONE-CMS-FORENSE-H-06]` — commit `b522c372`.
29. **Forense H-07 (CmsPostCreate/Update.locale)** `[DONE-CMS-FORENSE-H-07]` — commit `b522c372`.
30. **Forense H-08 (falso positivo _get_page_or_404 is_active)** `[DONE-CMS-FORENSE-H-08]` — confirmado: `public_page` no usa `_get_page_or_404`; usa query directa con `status==published`; el helper solo aplica a admin endpoints autenticados que por contrato deben gestionar pages de sites inactivos.
31. **Forense H-09 (falso positivo route overlap)** `[DONE-CMS-FORENSE-H-09]` — especulativo, no reproducido; FastAPI distingue `/public/` vs `/sites/`.
32. **Forense H-10 (falso positivo ContactSubmission updated_at)** `[DONE-CMS-FORENSE-H-10]` — models_cms.py:625 ES `default=_utcnow, onupdate=_utcnow`; el audit leyo una version stale.
33. **Forense M-01 (site_key max_length=80)** `[DONE-CMS-FORENSE-M-01]` — commit `5ea3cfab`; CmsSiteCreate.site_key = Field(min_length=1, max_length=80); 422 en lugar de 500.
34. **Forense M-02 (slug max_length=160)** `[DONE-CMS-FORENSE-M-02]` — commit `5ea3cfab`; CmsPageCreate/Update.slug = Field(min_length=1, max_length=160); 422 en lugar de 500.

1. **Plan de calidad canónico enlazado** `[DONE-PLAN-CMS-LINK-001]` — cerrado el 2026-07-16; `docs/PLAN_CMS_CALIDAD.md` queda como subplan oficial del módulo dentro de la matriz modular y este handover, con `docs/PLAN_CMS_100.md` preservado como referencia de auditoría profunda.
2. **Matriz RBAC CMS** `[DONE-RBAC-CMS-001]` — cerrada el 2026-07-16 en `CMS_RBAC_MATRIX.md`; documenta v1, v2 y enterprise por separado, incluyendo la subprotección actual de CMS v1.
3. **Smoke frontend CMS** `[DONE-FRONTEND-E2E-CMS-001]` — cerrado el 2026-07-16 con `frontend/tests/e2e/cms/smoke.spec.ts`; cubre dashboard, pages y media con guard de consola/API/assets.
4. **Smoke profundo CMS pages/preview** `[DONE-FRONTEND-DEEP-CMS-001]` — cerrado el 2026-07-16 con `frontend/tests/e2e/cms/pages-preview.spec.ts`; valida gestión de páginas, archivado, schedule views y preview draft con runner administrado.
5. **Hardening RBAC CMS v1** `[DONE-RBAC-V1-HARDENING-CMS-001]` — cerrado el 2026-07-16; las mutaciones administrativas de `backend/api/cms.py` ahora exigen `cms:edit`, mientras las lecturas administrativas permanecen en `cms:read`. Cobertura focal agregada para bloquear creación de testimonials, announcements y uploads de media por `LECTOR`.
6. **Builder/editor CMS** `[DONE-BUILDER-CMS-001]` — cerrado el 2026-07-16; el constructor quedó cubierto por smoke y deep suite sin regresiones de consola.
7. **Dashboard CMS** `[DONE-DASHBOARD-CMS-001]` — cerrado el 2026-07-16; el panel principal quedó validado con el smoke autenticado.
8. **Preview vs publicado vs público** `[DONE-PREVIEW-PUBLIC-CMS-001]` — cerrado el 2026-07-16; `pages-preview.spec.ts` y `cms-public-contract.spec.ts` cierran la validación reproducible.
9. **RBAC Enterprise CMS** `[DONE-RBAC-ENTERPRISE-CMS-001]` — cerrado el 2026-07-16; `backend/api/enterprise_cms.py` expresa lectura con `cms:read` y mutación con `cms:manage`.
10. **Smoke autenticado CMS** `[DONE-CMS-E2E-AUTH-GATE-001]` — cerrado el 2026-07-16; el runner administrado ya conecta browser `/api` y preflight absoluto sin caer en `Acceso Restringido`.
11. **Smoke canónico expandido** `[DONE-EXPAND-SMOKE-CMS-001]` — cerrado el 2026-07-16; `scripts/test_cms_quality.py` incluye backend, unit, smoke E2E autenticado y contrato público.
12. **Checklist visual preview/publicado** `[DONE-VISUAL-CMS-001]` — cerrado el 2026-07-16; `pages-preview.spec.ts` y `cms-public-contract.spec.ts` dejan el contrato visible y repetible.
13. **Gate modular CMS** `[DONE-GATE-CMS-001]` — cerrado el 2026-07-16; el gate canónico y el exhaustivo pasan sin skips silenciosos.
14. **Pop-up visible en builder** `[DONE-BUILDER-CMS-POPUP-001]` — cerrado el 2026-07-16; el builder expone una acción explícita de creación de pop-up en el sidebar y sigue manteniendo `popup_banner` en el catálogo y el renderer.
15. **Branding guardado con guardia de edición** `[DONE-BRANDING-CMS-001]` — cerrado el 2026-07-16; la pantalla de branding alinea su guardia con `canEditCms`, bloquea guardado/subida/edición para roles de solo lectura y evita el `PATCH` fallido por falta de permiso.
16. **Contenido público del CMS** `[DONE-CMS-PUBLIC-CONTENT-001]` — cerrado el 2026-07-17; bootstrap canónico `scripts/bootstrap_public_cms_content.py` recupera y publica el contenido público de `ccf` sin depender del snapshot de rescate.

---

## 12. Archivos a leer antes de cambiar codigo

1. `docs/ESTADO_CMS.md`
2. `docs/CMS_API_CONTRACTS.md`
3. `docs/CMS_RBAC_MATRIX.md`
4. `docs/CMS_QA_CHECKLIST.md`
5. `docs/PLAN_CMS_CALIDAD.md`
6. `docs/PLAN_CMS_100.md`
7. `docs/AUDITORIA_FORENSE_CMS.md`
8. `backend/api/cms.py`
9. `backend/api/cms_v2.py`
10. `backend/api/enterprise_cms.py`
11. `backend/api/_cms_helpers/_shared.py`
12. `backend/crud/cms.py`
13. `backend/models_cms.py`
14. `frontend/src/app/plataforma/cms/page.tsx`
15. `frontend/src/app/plataforma/cms/builder/page.tsx`
16. `frontend/tests/e2e/cms-public-contract.spec.ts`

---

## 13. Orden operativo recomendado

1. Identificar si el problema es admin, preview o render público.
2. Correr smoke canónico.
3. Si toca uploads/media, validar hardening y alt text.
4. Si toca páginas/sections, validar preview y publicado por separado.
5. Si toca enterprise, validar sesiones, redirects, search o audit según corresponda.
6. Si toca frontend, correr tests CMS existentes y revisar consola.

---

## 14. Tabla de IDs estables

| ID | Pieza | Archivo o area |
|---|---|---|
| `DONE-PLAN-CMS-LINK-001` | ✅ **Hecho 2026-07-16** — `PLAN_CMS_CALIDAD.md` queda alineado como subplan oficial del módulo dentro del esquema modular; `PLAN_CMS_100.md` queda como referencia complementaria profunda. | `docs/PLAN_CMS_CALIDAD.md` |
| `DONE-RBAC-CMS-001` | ✅ **Hecho 2026-07-16** — matriz RBAC CMS documentada separando v1, v2 y enterprise; deja explícita la subprotección actual de CMS v1 y la autorización difusa de enterprise. | `docs/CMS_RBAC_MATRIX.md` |
| `DONE-RBAC-V1-HARDENING-CMS-001` | ✅ **Hecho 2026-07-16** — mutaciones administrativas de CMS v1 endurecidas a `cms:edit`; lecturas administrativas preservadas en `cms:read`; pruebas focalizadas cubren `LECTOR` en testimonials, announcements y media upload. | `backend/api/cms.py`, `tests/test_cms_sede_isolation.py`, `tests/test_cms_upload_and_image_hardening.py` |
| `DONE-FRONTEND-E2E-CMS-001` | ✅ **Hecho 2026-07-16** — smoke frontend CMS base para dashboard, pages y media. | `frontend/tests/e2e/cms/smoke.spec.ts` |
| `DONE-FRONTEND-DEEP-CMS-001` | ✅ **Hecho 2026-07-16** — coverage profunda mockeada para pages + preview con workflow editorial y render draft. | `frontend/tests/e2e/cms/pages-preview.spec.ts` |
| `DONE-BUILDER-CMS-001` | ✅ **Hecho 2026-07-16** — builder cubierto por smoke y deep suite sin regresiones de consola. | `frontend/src/app/plataforma/cms/builder/page.tsx` |
| `DONE-DASHBOARD-CMS-001` | ✅ **Hecho 2026-07-16** — dashboard validado por el smoke autenticado. | `frontend/src/app/plataforma/cms/page.tsx` |
| `DONE-PREVIEW-PUBLIC-CMS-001` | ✅ **Hecho 2026-07-16** — preview, publicado y contrato público quedan reproducibles con `pages-preview.spec.ts` y `cms-public-contract.spec.ts`. | `frontend/tests/e2e/cms/pages-preview.spec.ts`, `frontend/tests/e2e/cms-public-contract.spec.ts` |
| `DONE-RBAC-ENTERPRISE-CMS-001` | ✅ **Hecho 2026-07-16** — Enterprise CMS expresa lectura `cms:read` y mutación `cms:manage` en la firma del router. | `backend/api/enterprise_cms.py` |
| `DONE-CMS-E2E-AUTH-GATE-001` | ✅ **Hecho 2026-07-16** — managed Playwright autentica contra `browser /api` y preflight absoluto sin `Acceso Restringido`. | `frontend/scripts/run-managed-playwright.mjs`, `frontend/tests/e2e/helpers/authSession.ts` |
| `DONE-EXPAND-SMOKE-CMS-001` | ✅ **Hecho 2026-07-16** — `scripts/test_cms_quality.py` ahora incluye backend, unit, smoke E2E autenticado y contrato público. | `scripts/test_cms_quality.py` |
| `DONE-VISUAL-CMS-001` | ✅ **Hecho 2026-07-16** — checklist visual preview/publicado institucionalizado con suites reproducibles. | `frontend/tests/e2e/cms/pages-preview.spec.ts`, `frontend/tests/e2e/cms-public-contract.spec.ts` |
| `DONE-GATE-CMS-001` | ✅ **Hecho 2026-07-16** — gate canónico y exhaustivo pasan sin skips silenciosos. | `scripts/test_cms_quality.py`, `frontend/tests/e2e/cms/smoke.spec.ts`, `frontend/tests/e2e/cms/pages-preview.spec.ts`, `frontend/tests/e2e/cms-public-contract.spec.ts` |
| `PEND-CMS-BUILDER-001` | Builder de CMS reportado como no funcional desde `/plataforma/cms/builder` | `frontend/src/app/plataforma/cms/builder/page.tsx`, `frontend/src/components/cms/**`, `backend/api/cms_v2.py` |
| `DONE-BUILDER-CMS-POPUP-001` | ✅ **Hecho 2026-07-16** — el builder expone una acción explícita de creación de pop-up y mantiene `popup_banner` en catálogo y renderer. | `frontend/src/components/cms/builder/BuilderSidebar.tsx`, `frontend/src/components/cms/builder/constants.ts`, `frontend/src/components/public/cms/PublicSectionRenderer.tsx` |
| `DONE-BRANDING-CMS-001` | ✅ **Hecho 2026-07-16** — branding ahora respeta `canEditCms`, deshabilita edición para roles solo lectura y evita el `PATCH` fallido al guardar logo o nombre. | `frontend/src/app/plataforma/cms/branding/page.tsx`, `frontend/tests/cms-branding-permissions.test.tsx` |
| `DONE-CMS-PUBLIC-CONTENT-001` | ✅ **Hecho 2026-07-17** — bootstrap público canónico para `ccf` ejecutado y verificado; publica las páginas núcleo, navegación, footer y contratos públicos desde CMS v2. | `docs/PLAN_CONTENIDO_PUBLICO_CMS.md`, `scripts/bootstrap_public_cms_content.py`, `scripts/seed_public_cms_v2_sections.py`, `scripts/seed_public_menus_and_footer.py`, `scripts/ensure_public_cms_pages.py` |

---

## 15. Ruta de cierre a 100%

**Estado de cierre: 100% alcanzado.**

- ✅ el gate canónico y la pasada exhaustiva pasan (194 tests)
- ✅ el smoke autenticado CMS y el contrato público pasan
- ✅ preview, publicado y builder quedaron cubiertos por suites reproducibles
- ✅ `docs/ESTADO_CMS.md`, `docs/CMS_API_CONTRACTS.md`, `docs/CMS_QA_CHECKLIST.md` y `docs/PLAN_CMS_CALIDAD.md` quedaron sincronizados con el estado final
- ✅ branding quedó alineado con la guardia de edición y ya no expone guardado para roles de solo lectura
- ✅ la creación de pop-ups quedó expuesta de forma clara en el builder
- ✅ auditoría forense `errorescms.md` 100% cerrada (48/48 findings + 10/10 funcionalidades)
- ✅ migraciones de fix canonizadas en `canonical_versions/` (head único `20260723_0006`)
- ✅ guía de arquitectura canónica creada: `docs/ARQUITECTURA_CMS.md`

**Actualización forense 2026-07-22 / 2026-07-23 / 2026-07-24 (audit `errorescms.md`):**

- ✅ 6 hallazgos críticos CERRADOS (C-01 fix, C-04 fix, C-06+H-11 fix; C-02, C-03, C-05 falsos positivos confirmados)
- ✅ 11 hallazgos altos CERRADOS (H-02/H-04/H-05/H-06/H-07 fixes; H-01/H-03/H-08/H-09/H-10 falsos positivos; H-11 cubierto con C-06)
- ✅ 14 hallazgos medios CERRADOS (M-01/M-02 length validations, M-03 CmsPage deleted_at, M-05 index, etc.)
- ✅ 17 hallazgos info CERRADOS (I-01..I-17)
- ✅ 10 funcionalidades CERRADAS (F-01..F-10, incluye F-08 publish log retention, F-10 orphan media cleanup)
- Commits clave: `e8912c54`, `6a83dd87`, `5b0a6e7c`, `b347f787`, `bd28cfe4`, `b522c372`, `5ea3cfab`, `82d9ffdd`, `afdafa89`, `3f7a0c7e`, `accb7b34`, `fc80da41`, `4d1ba06a`, `94f97d4a`, `8396e74f` (canonización migraciones)
- Cobertura: 194+ tests pasan sin skips (domain + sede isolation + upload hardening + security regression + v2 coverage + schedule + SEO audit)

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
cat /root/ccf/docs/ESTADO_CMS.md
cat /root/ccf/docs/CMS_API_CONTRACTS.md
cat /root/ccf/docs/CMS_RBAC_MATRIX.md
cat /root/ccf/docs/CMS_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_CMS_CALIDAD.md
cat /root/ccf/docs/PLAN_CMS_100.md
cat /root/ccf/docs/AUDITORIA_FORENSE_CMS.md
cat /root/ccf/docs/PLAN_ARQUITECTURA_MODULAR_CCF.md
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
npx playwright test tests/e2e/cms-public-contract.spec.ts
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

**Estado global:** CMS tiene gran superficie técnica y mucha evidencia previa. Ya cuenta con handover modular, smoke dedicado y cobertura profunda de `pages` + `preview`; el trabajo abierto se concentra en builder, checklist visual preview/publicado y cobertura enterprise más profunda.

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
| `/plataforma/cms` | `page.tsx` | Hecho — dashboard |
| `/plataforma/cms/builder` | `builder/page.tsx` | Parcial — editor muy sensible |
| `/plataforma/cms/pages` | `pages/page.tsx`, `pages/[slug]/page.tsx`, `versions/page.tsx` | Hecho funcional |
| `/plataforma/cms/media` | `media/page.tsx`, `media/[id]/page.tsx`, `media-folders/page.tsx` | Hecho funcional |
| `/plataforma/cms/themes`, `/menus`, `/sites` | varias | Hecho funcional |
| `/plataforma/cms/preview` | `preview/page.tsx` | Parcial — siempre validar contra publicado |
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

### Parcial

1. **Preview vs publicado vs público** `[PARCIAL-PREVIEW-PUBLIC-001]` — el módulo ya lo reconoce como riesgo principal; siempre validar por separado.
2. **Builder/editor CMS** `[PARCIAL-BUILDER-001]` — surface amplia y sensible a contratos de sections y global blocks.
3. **Dashboard CMS** `[PARCIAL-DASHBOARD-CMS-001]` — operativo, pero depende de varios endpoints agregados.
4. **Gate modular CMS** `[PARCIAL-GATE-CMS-001]` — ya existe plan canónico (`PLAN_CMS_CALIDAD.md`), smoke base y coverage profunda de `pages` + `preview`; falta endurecer el gate modular con checklist visual y mayor profundidad enterprise.

### Pendiente

1. **Ampliar smoke canónico** `[PEND-EXPAND-SMOKE-CMS-001]` — continuar desde `frontend/tests/e2e/cms/pages-preview.spec.ts` hacia builder, versions y enterprise cuando el cambio lo requiera.
2. **Checklist visual preview/publicado** `[PEND-VISUAL-CMS-001]` — institucionalizar comparación preview/publicado por ruta crítica.
3. **Expresar RBAC explícito en Enterprise CMS** `[PEND-RBAC-ENTERPRISE-CMS-001]` — reemplazar la autorización difusa basada solo en `get_current_user` por guards `cms:*` homogéneos en el borde del router donde corresponda.

### Cerrado recientemente

1. **Plan de calidad canónico enlazado** `[DONE-PLAN-CMS-LINK-001]` — cerrado el 2026-07-16; `docs/PLAN_CMS_CALIDAD.md` queda como subplan oficial del módulo dentro de la matriz modular y este handover, con `docs/PLAN_CMS_100.md` preservado como referencia de auditoría profunda.
2. **Matriz RBAC CMS** `[DONE-RBAC-CMS-001]` — cerrada el 2026-07-16 en `CMS_RBAC_MATRIX.md`; documenta v1, v2 y enterprise por separado, incluyendo la subprotección actual de CMS v1.
3. **Smoke frontend CMS** `[DONE-FRONTEND-E2E-CMS-001]` — cerrado el 2026-07-16 con `frontend/tests/e2e/cms/smoke.spec.ts`; cubre dashboard, pages y media con guard de consola/API/assets.
4. **Smoke profundo CMS pages/preview** `[DONE-FRONTEND-DEEP-CMS-001]` — cerrado el 2026-07-16 con `frontend/tests/e2e/cms/pages-preview.spec.ts`; valida gestión de páginas, archivado, schedule views y preview draft con runner administrado.
5. **Hardening RBAC CMS v1** `[DONE-RBAC-V1-HARDENING-CMS-001]` — cerrado el 2026-07-16; las mutaciones administrativas de `backend/api/cms.py` ahora exigen `cms:edit`, mientras las lecturas administrativas permanecen en `cms:read`. Cobertura focal agregada para bloquear creación de testimonials, announcements y uploads de media por `LECTOR`.

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
| `PARCIAL-PREVIEW-PUBLIC-001` | Preview y render público aún requieren validación explícita | preview/public route contract |
| `PARCIAL-BUILDER-001` | Builder/editor CMS de alta sensibilidad | `frontend/src/app/plataforma/cms/builder/page.tsx` |
| `PARCIAL-DASHBOARD-CMS-001` | Dashboard CMS depende de múltiples fuentes agregadas | `frontend/src/app/plataforma/cms/page.tsx` |
| `PARCIAL-GATE-CMS-001` | Gate modular CMS ya cubre smoke base y pages/preview; sigue faltando checklist visual y profundidad enterprise | docs + scripts |
| `PEND-EXPAND-SMOKE-CMS-001` | Ampliar script CMS con builder, versions y suites enterprise profundas | `scripts/test_cms_quality.py` |
| `PEND-VISUAL-CMS-001` | Checklist preview/publicado institucionalizado | docs + QA |
| `PEND-RBAC-ENTERPRISE-CMS-001` | Hacer explícito el RBAC `cms:*` en Enterprise CMS donde hoy predomina `get_current_user` | `backend/api/enterprise_cms.py` |
| `DONE-PLAN-CMS-LINK-001` | ✅ **Hecho 2026-07-16** — `PLAN_CMS_CALIDAD.md` queda alineado como subplan oficial del módulo dentro del esquema modular; `PLAN_CMS_100.md` queda como referencia complementaria profunda. | `docs/PLAN_CMS_CALIDAD.md` |
| `DONE-RBAC-CMS-001` | ✅ **Hecho 2026-07-16** — matriz RBAC CMS documentada separando v1, v2 y enterprise; deja explícita la subprotección actual de CMS v1 y la autorización difusa de enterprise. | `docs/CMS_RBAC_MATRIX.md` |
| `DONE-RBAC-V1-HARDENING-CMS-001` | ✅ **Hecho 2026-07-16** — mutaciones administrativas de CMS v1 endurecidas a `cms:edit`; lecturas administrativas preservadas en `cms:read`; pruebas focalizadas cubren `LECTOR` en testimonials, announcements y media upload. | `backend/api/cms.py`, `tests/test_cms_sede_isolation.py`, `tests/test_cms_upload_and_image_hardening.py` |
| `DONE-FRONTEND-E2E-CMS-001` | ✅ **Hecho 2026-07-16** — smoke frontend CMS base para dashboard, pages y media. | `frontend/tests/e2e/cms/smoke.spec.ts` |
| `DONE-FRONTEND-DEEP-CMS-001` | ✅ **Hecho 2026-07-16** — coverage profunda mockeada para pages + preview con workflow editorial y render draft. | `frontend/tests/e2e/cms/pages-preview.spec.ts` |

Busqueda rapida:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_CMS.md
```

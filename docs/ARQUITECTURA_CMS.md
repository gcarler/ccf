# Arquitectura del Módulo CMS — CCF

> **TL;DR:** El CMS de CCF es un sistema editorial multi-tenant para gestionar sites, páginas, secciones, menús, temas, media y contenido público. Este documento es la guía canónica de arquitectura y reglas de negocio. Cualquier agente que vaya a tocar el CMS debe leer este documento primero.

**Última actualización:** 2026-07-24
**Estado del módulo:** ✅ Auditoría forense 100% cerrada (48/48 findings, 10/10 funcionalidades)

---

## 1. Mapa del módulo

El CMS está dividido en tres capas backend con responsabilidades distintas:

| Capa | Archivo | Responsabilidad |
|---|---|---|
| **CMS v1** | `backend/api/cms.py` | Testimonios, announcements, media, métricas — flujos administrativos simples |
| **CMS v2** | `backend/api/cms_v2.py` | Sites, themes, menus, pages, sections, preview, workflow, categories, tags, posts, analytics — el editor |
| **Enterprise CMS** | `backend/api/enterprise_cms.py` | Audit logs, content permissions, notifications, webhooks, custom types, search, redirects, sessions, media folders |

Otros archivos clave:

| Archivo | Rol |
|---|---|
| `backend/crud/cms.py` | CRUD con defense-in-depth (re-valida sede en capa mutante) |
| `backend/api/_cms_helpers/_shared.py` | Helpers de scope compartidos (`_actor_sede_or_none_cms`, `_get_scoped_*`) |
| `backend/models_cms.py` | Modelos del dominio CMS principal |
| `backend/models_enterprise.py` | Modelos Enterprise CMS (Redirect, AuditLog, Webhook, etc.) |
| `backend/schemas/cms.py` | Schemas Pydantic CMS v1 y v2 |
| `backend/schemas/cms_v2_sections.py` | Schemas por section type |
| `frontend/src/components/public/cms/PublicSectionRenderer.tsx` | Renderer rígido único para secciones públicas |
| `frontend/src/lib/cms/sanitize.ts` | `sanitizeCmsHtml` — sanitización obligatoria de HTML del CMS |
| `frontend/src/app/plataforma/cms/**` | UI administrativa del CMS |

---

## 2. Modelo de datos

### 2.1 Jerarquía de contenido

```
Sede (tenant)
  └─ CmsSite (un site por sede, identificado por site_key)
       ├─ CmsTheme (tema del site: tokens_json)
       ├─ CmsMenu → CmsMenuItem (navegación)
       ├─ CmsPage (página con slug único dentro del site)
       │    ├─ CmsPageVersion (versiones: draft, preview, published)
       │    ├─ CmsSection (sección tipada dentro de una página)
       │    ├─ CmsPageView (contador de vistas)
       │    └─ CmsPublishLog (log de publicaciones)
       ├─ CmsCategory → CmsPost (blog/noticias)
       └─ CmsTag
CmsMediaItem (media global con sede_id)
Testimonial, Announcement (CMS v1)
```

### 2.2 Modelos Enterprise CMS (`models_enterprise.py`)

```
AuditLog, ContentPermission, CmsNotification, Webhook, WebhookDelivery,
CmsCustomType, CmsCustomEntry, CmsCustomEntryVersion,
CmsGlossaryTerm, SearchIndex, SearchPromotion,
UserSession, MediaFolder, MediaFileVersion, CmsRedirect, BrokenLinkCheck
```

### 2.3 Puntos sensibles del modelo

| Campo | Regla |
|---|---|
| `CmsSite.sede_id` | FK a `sedes.id` con `ON DELETE RESTRICT` (no se puede borrar sede con sites) |
| `CmsMediaItem.sede_id` | Clave de Axioma 3 (multi-tenant isolation) |
| `CmsPage.slug` | Único dentro del site; `max_length=160` (validación Pydantic) |
| `CmsPage.publish_at` / `expires_at` | Scheduling: `publish_at < expires_at` validado en CRUD |
| `CmsSection.deleted_at` | Soft delete; no rehidratar en lecturas |
| `CmsPage.deleted_at` | Soft delete (añadido en M-03, migración `20260723_0003`) |

### 2.4 Patrones de soft-delete en CMS

El CMS usa 4 mecanismos de soft-delete distintos — no asumir uno universal:

| Mecanismo | Entidades |
|---|---|
| `status="archived"` + `deleted_at` | CmsPage, CmsSection, CmsPost (los más completos) |
| `status="archived"` solo | CmsMediaItem |
| `is_active=False` solo | CmsSite, CmsTheme, CmsMenu, CmsCategory, CmsTag |
| `visibility="hidden"` solo | CmsMenuItem |

**Regla:** al añadir `deleted_at` a una entidad que no lo tiene, el approach aditivo es seguro (no rompe queries existentes de `is_active`/`status`).

---

## 3. Reglas de negocio

### 3.1 Multi-tenant (Axioma 3)

- **Todo contenido CMS está scoped por `sede_id`** (directamente en `CmsMediaItem`, o indirectamente vía `CmsSite.sede_id` → `CmsPage.site_id`).
- **Excepción por diseño:** `CmsSectionType` es **global** (no tiene site FK ni sede_id). Es la única entidad CMS legítimamente global. El endpoint docstring en `cms_v2.py:92-97` lo confirma y `REGLAS.md §4.2` lo lista como "Global design OK".
- **Defense-in-depth:** la capa CRUD (`backend/crud/cms.py`) re-valida scope en funciones mutantes, no solo la API. Esto cubre callers no-API (workers, seeding, tests directos). El CRUD docstring (L1-10) declara este contrato.
- **Patrón de validación CRUD→API:** los helpers `_assert_*` en `crud/cms.py` levantan `ValueError`; el endpoint en `cms_v2.py` lo traduce a `HTTPException(422, detail=str(exc))`. 422 es el código canónico para validaciones de coherencia CMS (no 400 ni 403).

### 3.2 CMS es la fuente de verdad del contenido público

- El CMS controla **solo contenido**: texto, imágenes, datos estructurados de secciones.
- El CMS **NO controla** CSS classes, font sizes, colors, fonts, ni inline styles.
- Todo layout, styling y estructura visual vive en el **renderer rígido** del frontend (`PublicSectionRenderer.tsx`).
- El HTML rico del CMS se sanitiza con `sanitizeCmsHtml` — esto elimina `style`, `class` y atributos peligrosos. El CSS viene de `.ccf-rich-text` y las clases del renderer, no del contenido.

### 3.3 Contratos: admin vs preview vs público

Hay **tres contratos diferentes** que no se validan igual:

| Contrato | Descripción | Guard |
|---|---|---|
| **Admin draft** | Edición del editor en `/plataforma/cms/**` | `cms:read` (lecturas), `cms:edit` (mutaciones) |
| **Preview** | Vista previa del draft antes de publicar | `cms:read`; Usa la última versión draft |
| **Render público** | Página publicada servida al visitante | Público, rate-limited; solo `status="published"` |

**Regla crítica:** un fix en uno NO corrige automáticamente los otros dos. Validar cada uno por separado.

### 3.4 Flujo editorial (workflow)

```
Draft → Preview → Publish → (Unpublish / Archive)
```

1. **Draft:** `CmsPageVersion` con `status="draft"`. Solo visible en admin.
2. **Preview:** El admin previsualiza contra la versión draft usando `/cms/v2/sites/{site_key}/pages/{slug}/preview`.
3. **Publish:** El workflow (`/cms/v2/sites/{site_key}/pages/{slug}/workflow`) cambia `status` a `"published"`. Crea `CmsPublishLog`. Se puede programar con `publish_at`/`expires_at`.
4. **Archive:** `status="archived"` + `deleted_at=_utcnow()` (soft delete). No reaparece en lecturas públicas ni admin.
5. **Schedule:** `/cms/v2/pages/{page_id}/schedule` gestiona `publish_at`/`expires_at`. Validado: `published_at < expires_at` (helper CRUD `_assert_post_published_before_expires`).

### 3.5 Section types

- **32+ section types** soportados: Hero, VideoHero, RichText, RichTextColumns, Cards, CtaBanner, Gallery, FAQ, Embed, Testimonials, Stats, Team, Countdown, Pricing, ImageText, Timeline, IconGrid, Newsletter, PopupBanner, Button, TOC, Divider, Collapsible, SocialLinks, Spacer, Calendar, Map, DocumentUpload, ContentBlocks, Accordion + 6 Civic types + extensiones (EventsCalendar, VideoGrid, etc.).
- `CmsSectionType` (tabla DB) permite activar types sin código. `get_allowed_section_types()` consulta la DB primero, luego cae al fallback hardcodeado de 32 types.
- `SECTION_PROPS_SCHEMAS` (en `cms_v2_sections.py`) contiene schemas Pydantic para validación estructural por tipo. Los schemas para types no activos son **infraestructura preparatoria**, no código muerto — no eliminar.
- El renderer del frontend (`PublicSectionRenderer.tsx`) despacha por `type` a un componente dedicado para cada section type. Es **rígido**: el CMS no puede inyectar CSS arbitrario.

### 3.6 SEO

- SEO se gestiona via `CmsSeoSnapshot` y bloques CMS `ccf_{slug}_meta`.
- El tema (theme) del site se obtiene de `/cms/v2/public/sites/{key}/theme`.
- La navegación (navbar) viene de la API de menús CMS + fallback `ccf_nav_items`.
- Los redirects se gestionan via Enterprise CMS `CmsRedirect` (`match_type`: exact, prefix, regex; `priority` para desambiguar).

### 3.7 Uploads y media

- **Allow-list de extensiones** obligatoria.
- `sanitize_filename` normaliza nombres de archivo.
- `validate_mime_extension_alignment` rechaza MIME spoofed.
- Media archivado (`status="archived"`) no debe reaparecer en endpoints derivados.
- **Path traversal guard:** cualquier endpoint que resuelve un path del filesystem bajo `/root/ccf/uploads` debe aplicar el guard `normpath + startswith("/root/ccf/uploads/")` antes de `os.remove`/`open`/`os.path.exists`.

### 3.8 Timestamps

- `datetime.utcnow()` está **deprecado** en toda la plataforma. Usar `datetime.now(timezone.utc)`.
- En SQLite (tests), `DateTime(timezone=True)` persiste como naive — usar helper `_as_aware_utc(value)` para comparaciones tz-aware.

---

## 4. RBAC (permisos)

### 4.1 Permisos canónicos

- `cms:read` — lectura administrativa
- `cms:edit` — mutación (crear/editar/borrar)
- `cms:manage` — mutación + operaciones administrativas (publish, enterprise)

Jerarquía: `cms:manage` ⊇ `cms:edit` ⊇ `cms:read`

### 4.2 Matriz por capa

| Capa | Lectura | Mutación |
|---|---|---|
| CMS v1 | `cms:read` | `cms:edit` (endurecido en 2026-07-16) |
| CMS v2 | `cms:read` | `cms:edit` |
| Enterprise CMS | `cms:read` | `cms:manage` |
| Endpoints públicos | sin auth (rate-limited) | n/a |

### 4.3 Matriz por rol (seed persistido)

| Rol | CMS v1 | CMS v2 | Enterprise |
|---|---|---|---|
| `ADMINISTRADOR` | lectura + mutación | lectura + mutación | lectura + mutación |
| `GESTOR` | lectura + mutación | lectura + mutación | lectura; mutación solo con `cms:manage` |
| `EDITOR` | lectura + mutación | lectura + mutación | lectura; mutación solo con `cms:manage` |
| `LECTOR` | solo lectura (deseado) | solo lectura | solo lectura |
| `MIEMBRO` | sin CMS | sin CMS | sin CMS |

Ver `docs/CMS_RBAC_MATRIX.md` para el detalle completo.

---

## 5. Renderer público (rígido)

El renderer es el componente más importante del frontend CMS: `PublicSectionRenderer.tsx` (~2100 LOC).

### 5.1 Reglas del renderer

1. **Un solo renderer** para todas las secciones públicas — despacha por `section.type` a un componente dedicado.
2. **CSS rígido:** el renderer impone el layout y estilo. El CMS no puede override.
3. **Sanitización obligatoria:** todo HTML del CMS pasa por `sanitizeCmsHtml` antes de `dangerouslySetInnerHTML`. Esto elimina `style`, `class`, `<script>`, `on*` handlers.
4. **RichText:** usa la clase `.ccf-rich-text` del CSS global para tipografía y spacing.
5. **Sin datos mock en producción:** el renderer lee de la API pública; si la data no existe, muestra `EmptyState`.

### 5.2 Flujo de render público

```
Visitante → /{site_key}/{page_slug}
  → API pública GET /cms/v2/public/sites/{key}/pages/{slug}
  → Filtra por status=published, deleted_at IS NULL, publish_at <= now, expires_at > now (o NULL)
  → Devuelve page + sections ordenadas
  → Frontend PublicSectionRenderer despacha cada section por type
  →sanitiza HTML, aplica CSS rígido
  → Renderiza la página
```

---

## 6. Tests y verificación

### 6.1 Smoke canónico (gate completo)

```bash
cd /root/ccf
./venv/bin/python scripts/test_cms_quality.py
```

Incluye: backend, unit tests, smoke E2E autenticado, y contrato público.

### 6.2 Smoke mínimo backend

```bash
cd /root/ccf && source venv/bin/activate
python -m pytest -q -o addopts='' \
  tests/test_cms_domain.py \
  tests/test_cms_sede_isolation.py \
  tests/test_cms_upload_and_image_hardening.py \
  tests/test_cms_metrics_sede_isolation.py
```

### 6.3 Coverage profunda (194 tests)

```bash
cd /root/ccf && source venv/bin/activate
python -m pytest -q -o addopts='' --no-cov \
  tests/test_cms_domain.py \
  tests/test_cms_sede_isolation.py \
  tests/test_cms_v2_coverage.py \
  tests/test_cms_v2_deep_coverage.py \
  tests/test_cms_schedule.py \
  tests/test_cms_seo_audit.py \
  tests/test_cms_security_regression.py
```

### 6.4 Frontend

```bash
cd /root/ccf/frontend
npx vitest run tests/cms-components.test.ts tests/cms-public-fetch.test.ts
npm run test:e2e:cms
npm run test:e2e:cms:deep
npm run test:e2e:cms:public
```

### 6.5 Regla de `--no-cov`

Para cualquier batch CMS >1 archivo de test, usar `--no-cov`. Sin esto, la instrumentación de cobertura + el fixture autouse `_reset_caches_between_tests` hacen que los tests cuelguen past 300s. `--no-cov` reduce ~100 tests a ~50s.

---

## 7. Reglas para agentes que trabajan en CMS

### 7.1 Antes de tocar código

1. Leer este documento.
2. Leer `docs/CMS_RBAC_MATRIX.md` si el cambio toca permisos.
3. Leer `docs/CMS_API_CONTRACTS.md` si el cambio toca contratos API.
4. Identificar si el problema es **admin**, **preview**, o **render público**.

### 7.2 Reglas innegociables

- **No mezclar** fixes de admin, preview y render público en el mismo commit si no comparten causa raíz.
- **No usar Docker/Kubernetes** — el VPS trabaja directo con PM2 + Git.
- **`apiFetch()`** para todos los calls backend desde el frontend (no `fetch` crudo).
- **Semantic Tailwind tokens** — no hardcoded colors (`bg-blue-500`). Usar tokens del design system.
- **Drawers, no Modals** para create/edit/view flows.
- **Soft deletes only** — no `DELETE` físico en tablas transaccionales.
- **`sede_id` filter mandatory** en todas las queries (multi-tenant isolation).
- **UUID PKs** — no Integer PKs. `persona_id` debe ser `str` (UUID), nunca `int`.
- **`datetime.now(timezone.utc)`** — no `datetime.utcnow()`.
- **VENV OBLIGATORIO:** `cd /root/ccf && source venv/bin/activate` antes de cualquier `pytest`/`uvicorn`.
- **Production workflow:** después de `npm run build` en frontend, ejecutar `pm2 restart ccf-frontend-staging`.
- **No mezclar** cambios funcionales con migraciones amplias, auth/RBAC, o mass renames.
- **Migraciones:** nunca modificar migraciones commiteadas en `canonical_versions/`. Crear nuevas versiones que encadenen desde el último revision en `versions/`, luego canonizar moviéndolas a `canonical_versions/`.

### 7.3 Patrón CRUD→API para validaciones

Cuando se necesita validación cross-field o cross-scope (parent en mismo site, `published_at < expires_at`):

1. Crear helper `_assert_<rule>(db, ...)` en `backend/crud/cms.py` cerca de las funciones relevantes.
2. Llamarlo desde **ambas** `create_*` y `update_*` (cubre callers no-API).
3. Levantar `ValueError` desde el CRUD helper.
4. En el endpoint (`cms_v2.py`), envolver la llamada CRUD en `try: ... except ValueError as exc: raise HTTPException(422, detail=str(exc))`.
5. Para PATCH parcial, resolver valores efectivos combinando `payload.model_dump(exclude_unset=True)` con el estado actual del row.

### 7.4 Patrón de tests cross-sede

Usar `TestCmsV2IdorCrossSede` en `tests/test_cms_security_regression.py:304-473` como idiom canónico. `_seed_two_pastors(db_session)` crea sede_a/sede_b + dos PASTOR users. Cada test aserte 404 en recursos cross-sede + data inmutable (`db_session.refresh`).

### 7.5 Commit style

```
fix(cms): <descripción> (<ID-finding>)
docs(cms): cerrar <ID> en bitacora forense (commit <hash>)
feat(cms): <descripción>
test(cms): <descripción>
```

### 7.6 Orden operativo recomendado

1. Identificar capa: admin, preview, público, enterprise.
2. Correr smoke canónico o smoke mínimo.
3. Si toca uploads → validar hardening + MIME + path traversal guard.
4. Si toca pages/sections → validar preview y publicado **por separado**.
5. Si toca enterprise → validar sesión, redirect, search o audit según corresponda.
6. Si toca frontend → correr tests CMS existentes + revisar consola del navegador.
7. Después del cambio: `pm2 restart ccf-frontend-staging` si se tocó frontend.

---

## 8. Estado de cierre (auditoría forense)

La auditoría forense `errorescms.md` está **100% cerrada** (ciclo 7, commits `fc80da41`/`4d1ba06a`/`94f97d4a`):

| Categoría | Cerrados |
|---|---|
| Críticos (C-01..06) | 6/6 ✅ |
| Altos (H-01..11) | 11/11 ✅ |
| Medios (M-01..14) | 14/14 ✅ |
| Info (I-01..17) | 17/17 ✅ |
| Funcionalidades (F-01..10) | 10/10 ✅ |
| **Total** | **48/48 ✅** + 10/10 funcionalidades ✅ |

Migraciones de fix canonizadas en `alembic/canonical_versions/`: `20260723_0001`→`0006` (cadena lineal, head único `20260723_0006`).

**"Audit closed" = código + tests + docs + migraciones aplicadas a prod.**

---

## 9. Documentos relacionados

| Documento | Rol |
|---|---|
| `docs/ARQUITECTURA_CMS.md` (este) | Guía canónica de arquitectura y reglas de negocio |
| `docs/ESTADO_CMS.md` | Estado operativo, backlog, handover modular |
| `docs/CMS_API_CONTRACTS.md` | Contratos API detallados por endpoint |
| `docs/CMS_RBAC_MATRIX.md` | Matriz RBAC completa por capa y rol |
| `docs/CMS_QA_CHECKLIST.md` | Checklist de QA para cerrar tareas |
| `docs/PLAN_CMS_CALIDAD.md` | Plan de calidad operativo del módulo |
| `docs/PLAN_CMS_100.md` | Plan de auditoría profunda (referencia histórica) |
| `docs/AUDITORIA_FORENSE_CMS.md` | Bitácora forense de auditoría |

---

## 10. Comandos rápidos

```bash
# Verificar servicios
pm2 status
curl -s http://127.0.0.1:8000/healthz
curl -s http://127.0.0.1:3000/plataforma/cms

# Smoke backend CMS
cd /root/ccf && source venv/bin/activate
python -m pytest -q -o addopts='' --no-cov \
  tests/test_cms_domain.py tests/test_cms_sede_isolation.py tests/test_cms_security_regression.py

# TypeScript check
cd /root/ccf/frontend && npx tsc --noEmit

# Build + deploy frontend
cd /root/ccf/frontend && npm run build
pm2 restart ccf-frontend-staging

# Alembic state
cd /root/ccf && source venv/bin/activate && alembic heads
```

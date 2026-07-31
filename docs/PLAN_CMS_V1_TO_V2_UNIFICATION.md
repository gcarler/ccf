# Plan de Unificación: CMS v1 Shims → CMS v2 Nativo

**Objetivo:** Eliminar la capa de compatibilidad `cms_v1_adapters.py` y endpoints `/cms/testimonials*`, `/cms/announcements*`, `/admin/testimonials*`, `/admin/announcements*` migrando 100% del panel CMS admin a `/cms/v2/sites/{site_key}/posts` con categorías `testimonials` / `announcements`.

**Fecha:** 2026-07-30
**Estado:** En implementación — Fase 1 iniciada

---

## Hallazgos Críticos (Inspección BD 2026-07-30)

| Tabla | Estado | Nota |
|-------|--------|------|
| `testimonials` (legacy) | **NO EXISTE** | Ya fue eliminada en migración previa |
| `announcements` (legacy) | Existe pero **VACÍA** | 0 rows |
| `cms_posts` | **VACÍA** | 0 posts — no hay datos que migrar |
| `cms_sites` | 5 sites | 1 principal (`ccf`), 4 `legacy-testimonials-*` (v1-compat) |
| `cms_categories` | 3 `testimonials` | Una por cada site v1-compat |

**Conclusión:** No hay datos legacy que migrar. Los v1 shims crean sites/categorías v1-compat *on-demand* al crear contenido nuevo. La unificación solo requiere que los nuevos endpoints v2 usen el site principal `ccf` y categorías canónicas.

---

## 1. Análisis de Impacto Actualizado

### Backend — Endpoints a migrar/eliminar

| Endpoint actual (v1 shim) | Método | Nuevo endpoint (v2 nativo) | Notas |
|---------------------------|--------|----------------------------|-------|
| `/cms/testimonials` | GET | `/cms/v2/public/sites/{site_key}/posts?category=testimonials` | Público |
| `/cms/testimonials` | POST | `/cms/v2/sites/{site_key}/posts` + category `testimonials` | Admin create |
| `/admin/testimonials` | GET | `/cms/v2/sites/{site_key}/posts?category=testimonials` | Admin list |
| `/admin/testimonials/{id}` | GET | `/cms/v2/sites/{site_key}/posts/{slug}` | Admin detail |
| `/admin/testimonials/{id}` | PATCH | `/cms/v2/sites/{site_key}/posts/{slug}` | Admin update |
| `/admin/testimonials/{id}` | DELETE | `/cms/v2/sites/{site_key}/posts/{slug}` | Admin delete |
| `/cms/announcements` | GET | `/cms/v2/public/sites/{site_key}/posts?category=announcements` | Público |
| `/cms/announcements` | POST | `/cms/v2/sites/{site_key}/posts` + category `announcements` | Admin create |
| `/admin/announcements` | GET | `/cms/v2/sites/{site_key}/posts?category=announcements` | Admin list |
| `/admin/announcements/{id}` | GET/PATCH/DELETE | `/cms/v2/sites/{site_key}/posts/{slug}` | Admin CRUD |

### Frontend — Páginas/componentes afectados

| Archivo | Tipo | Cambio requerido |
|---------|------|------------------|
| `frontend/src/app/plataforma/cms/testimonials/page.tsx` | Página listado | Cambiar fetch a `/cms/v2/sites/{key}/posts?category=testimonials` |
| `frontend/src/app/plataforma/cms/testimonials/[id]/page.tsx` | Página detalle | Usar `slug` en lugar de `id`, fetch v2 |
| `frontend/src/app/plataforma/cms/testimonials/new/page.tsx` | Página crear | POST a `/cms/v2/sites/{key}/posts` con category |
| `frontend/src/app/plataforma/cms/announcements/page.tsx` | Página listado | Cambiar fetch a v2 con category |
| `frontend/src/app/plataforma/cms/announcements/[id]/page.tsx` | Página detalle | Usar slug, fetch v2 |
| `frontend/src/app/plataforma/cms/announcements/new/page.tsx` | Página crear | POST v2 con category |
| `frontend/src/components/cms/TestimonialForm.tsx` | Componente formulario | Adaptar campos a `CmsPostCreate` + category fija |
| `frontend/src/components/cms/AnnouncementForm.tsx` | Componente formulario | Adaptar campos a `CmsPostCreate` + category fija |
| `frontend/src/lib/api.ts` / `lib/cms/v2.ts` | Cliente API | Agregar helpers `listPostsByCategory`, `createPostWithCategory` |

### Schemas — Contratos que cambian

| Schema v1 (eliminar) | Schema v2 (usar) | Mapeo de campos |
|----------------------|------------------|-----------------|
| `TestimonialCreate` | `CmsPostCreate` | `content`→`content`, `emotion`→`seo_json.emotion`, `media_type`→`seo_json.media_type`, etc. |
| `TestimonialUpdate` | `CmsPostUpdate` | Mismo mapeo |
| `AnnouncementCreate` | `CmsPostCreate` | `title`→`title`, `content`→`content`, `category`→`seo_json.category`, `is_featured`→`seo_json.is_featured` |
| `AnnouncementUpdate` | `CmsPostUpdate` | Mismo mapeo |
| `TestimonialRead` | `CmsPostReadWithTaxonomies` | Response shape distinto — frontend debe adaptarse |
| `AnnouncementRead` | `CmsPostReadWithTaxonomies` | Response shape distinto |

---

## 2. Fases del Plan

### Fase 0 — Preparación (1 día)

- [x] Crear branch `feat/cms-v1-to-v2-unification`
- [x] Snapshot de tests actuales: `./venv/bin/python scripts/test_cms_quality.py` → 54 passed, 1 skipped (E2E requires env vars)
- [x] Identificar todos los callers de endpoints v1 shim (grep en frontend/backend)
- [x] Verificar estado BD: `cms_posts` vacía, site principal `ccf` existe, 4 sites v1-compat legacy

### Fase 1 — Backend: Endpoints v2 nativos para categorías fijas (3-4 días)

#### 1.1 Helpers de categoría en CRUD (`backend/crud/cms.py`)

```python
# Nuevo helper: obtener/crear categoría canónica por slug + site_id
def get_or_create_canonical_category(db, site_id, slug, name, description) -> CmsCategory

# Nuevo helper: listar posts por categoría (con pagination, scope por site)
def list_cms_posts_by_category(db, site_id, category_slug, skip, limit, status, include_archived) -> (items, total)

# Nuevo helper: get post by slug + category (para detail admin)
def get_cms_post_by_slug_and_category(db, site_id, slug, category_slug) -> CmsPost | None
```

#### 1.2 Endpoints v2 en `backend/api/cms_v2.py` (bajo `/cms/v2/sites/{site_key}/posts`)

| Endpoint | Descripción |
|----------|-------------|
| `GET /posts?category=testimonials` | Lista paginada filtrada por categoría |
| `GET /posts?category=announcements` | Lista paginada filtrada por categoría |
| `POST /posts` (con `category_ids` en payload) | Crear post asignando categoría canónica |
| `GET /posts/{slug}?category=testimonials` | Detalle con validación de categoría |
| `PATCH /posts/{slug}` | Update manteniendo categoría |
| `DELETE /posts/{slug}` | Soft-delete (archive) |

**Reglas de validación:**
- `category_ids` en create/update debe contener exactamente la categoría canónica (`testimonials` o `announcements`)
- Rechazar si se intenta cambiar la categoría canónica
- `site_key` resuelve a `CmsSite` con scope por sede (Axioma 3)

#### 1.3 Schemas v2 extendidos (`backend/schemas/cms.py`)

```python
class CmsPostCreateWithCategory(CmsPostCreate):
    category_slug: Literal["testimonials", "announcements"]  # validador: debe ser canónica

class CmsTestimonialRead(CmsPostReadWithTaxonomies):
    # Shape compatible con TestimonialRead actual para migración gradual frontend
    emotion: str = Field(..., alias="seo_json.emotion")
    media_type: str = Field(..., alias="seo_json.media_type")
    # ... etc

class CmsAnnouncementRead(CmsPostReadWithTaxonomies):
    category: str = Field(..., alias="seo_json.category")
    is_featured: bool = Field(..., alias="seo_json.is_featured")
    # ... etc
```

#### 1.4 Tests backend (obligatorios antes de Fase 2)

- `tests/test_cms_v2_posts_by_category.py` — CRUD completo por categoría
- `tests/test_cms_v2_canonical_categories.py` — Categorías canónicas no mutables
- `tests/test_cms_v2_security_cross_sede.py` — Aislamiento por sede en nuevos endpoints
- Cobertura objetivo: ≥90% en nuevos endpoints

### Fase 2 — Frontend: Migración de páginas admin (4-5 días)

#### 2.1 Cliente API (`frontend/src/lib/cms/v2.ts`)

```typescript
// Nuevas funciones
export async function listPostsByCategory(
  siteKey: string,
  category: 'testimonials' | 'announcements',
  params?: { skip?: number; limit?: number; status?: string }
): Promise<PaginatedResponse<CmsPostWithTaxonomies>>

export async function createPostWithCategory(
  siteKey: string,
  category: 'testimonials' | 'announcements',
  payload: Omit<CmsPostCreate, 'category_ids'> & { category_ids?: never }
): Promise<CmsPostWithTaxonomies>

export async function getPostBySlugAndCategory(
  siteKey: string,
  slug: string,
  category: 'testimonials' | 'announcements'
): Promise<CmsPostWithTaxonomies>

export async function updatePost(
  siteKey: string,
  slug: string,
  payload: CmsPostUpdate
): Promise<CmsPostWithTaxonomies>

export async function deletePost(siteKey: string, slug: string): Promise<void>
```

#### 2.2 Tipos frontend (`frontend/src/types/cms-v2.ts`)

```typescript
// Extender CmsPost para shape compatible con UI actual
export interface CmsTestimonial extends CmsPostWithTaxonomies {
  emotion: string;
  media_type: string;
  media_url?: string;
  image_url?: string;
  video_url?: string;
  podcast_url?: string;
  is_approved: boolean;
  show_on_home: boolean;
}

export interface CmsAnnouncement extends CmsPostWithTaxonomies {
  category: string;
  is_featured: boolean;
  image_url?: string;
}
```

#### 2.3 Páginas — Testimonios

| Archivo | Cambios |
|---------|---------|
| `testimonials/page.tsx` | `listPostsByCategory(siteKey, 'testimonials')` → tabla usa `CmsTestimonial` |
| `testimonials/[id]/page.tsx` | Cambiar param `[id]` → `[slug]`, fetch `getPostBySlugAndCategory(siteKey, slug, 'testimonials')` |
| `testimonials/new/page.tsx` | Form usa `createPostWithCategory(siteKey, 'testimonials', payload)` |

#### 2.4 Páginas — Anuncios

| Archivo | Cambios |
|---------|---------|
| `announcements/page.tsx` | `listPostsByCategory(siteKey, 'announcements')` |
| `announcements/[id]/page.tsx` | Param `[slug]`, fetch por categoría |
| `announcements/new/page.tsx` | `createPostWithCategory(siteKey, 'announcements', payload)` |

#### 2.5 Componentes formulario

| Componente | Cambios |
|------------|---------|
| `TestimonialForm.tsx` | Campos mapean a `CmsPostCreate` + `seo_json` para `emotion`, `media_type`, etc. Eliminar `author_persona_id` (se resuelve server-side) |
| `AnnouncementForm.tsx` | Campos mapean a `CmsPostCreate` + `seo_json.category`, `seo_json.is_featured` |

#### 2.6 Validación frontend

- `npm run lint -- --max-warnings=0` pasa
- `npx tsc --noEmit` pasa (0 errores)
- Tests vitest existentes pasan + nuevos tests para formularios

### Fase 3 — Eliminación de código v1 shim (1-2 días)

#### 3.1 Backend

- [ ] Eliminar `backend/api/cms_v1_adapters.py`
- [ ] Eliminar endpoints v1 shim en `backend/api/cms.py` (líneas 58-347 aprox: testimonials + announcements)
- [ ] Eliminar imports de `cms_v1_adapters` en `cms.py`
- [ ] Verificar que `backend/api/cms.py` solo queda: Media, Metrics, Cleanup
- [ ] Ejecutar suite backend completa: `./venv/bin/python scripts/test_cms_quality.py`

#### 3.2 Frontend

- [ ] Eliminar tipos `TestimonialCreate`, `TestimonialUpdate`, `AnnouncementCreate`, `AnnouncementUpdate`, `TestimonialRead`, `AnnouncementRead` de `frontend/src/types/cms-v2.ts` (o mover a legacy)
- [ ] Eliminar cualquier import residual de endpoints `/cms/testimonials`, `/admin/testimonials`, `/cms/announcements`, `/admin/announcements`
- [ ] `npm run lint && npx tsc --noEmit` → 0 warnings/errors

### Fase 4 — Validación End-to-End (2 días)

#### 4.1 Tests E2E nuevos (`frontend/tests/e2e/cms/v2-unification.spec.ts`)

```typescript
// Flujo crítico testimonio
test('admin crea testimonio via v2 y aparece en público', async () => {
  await loginAsEditor();
  await goto('/plataforma/cms/testimonials/new');
  await fillTestimonialForm({ content: 'Dios es bueno', emotion: 'Gratitud' });
  await clickPublish();
  // Verificar en público
  const publicPost = await apiFetch(`/cms/v2/public/sites/ccf/posts?category=testimonials`);
  expect(publicPost.items[0].content).toContain('Dios es bueno');
});

// Flujo crítico anuncio
test('admin crea anuncio via v2 y aparece en público', async () => { ... });

// Cross-sede isolation
test('editor sede_a NO ve testimonios de sede_b', async () => { ... });
```

#### 4.2 Smoke manual en staging

- [ ] Login editor → crear testimonio → publicar → ver en `/testimonios` público
- [ ] Login editor → crear anuncio → publicar → ver en `/anuncios` público
- [ ] Login editor sede A → no ve contenido sede B
- [ ] Preview draft funciona
- [ ] Workflow (draft → in_review → approved → published) funciona
- [ ] Scheduled publish funciona
- [ ] Soft-delete (archive) oculta en público y admin

#### 4.3 Regresión completa

- [ ] `./venv/bin/python scripts/test_cms_quality.py` → todo verde
- [ ] `cd frontend && npm run test:e2e:cms` → todo verde
- [ ] `cd frontend && npm run lint && npx tsc --noEmit` → limpio

---

## 3. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Frontend breakage por shape de respuesta distinto (`TestimonialRead` vs `CmsPostWithTaxonomies`) | Alto | Fase 2 usa tipos adaptadores (`CmsTestimonial`, `CmsAnnouncement`) que mapean campos `seo_json` → propiedades planas |
| Categorías canónicas no existen en algunas sedes | Medio | Bootstrap automático en `get_or_create_canonical_category` (igual que hace shim actual) |
| Slugs colisionan entre testimonio y anuncio en mismo site | Bajo | `slug` en v2 es único por `site_id`; shim actual genera `testimonial-{uuid}` / `announcement-{uuid}` — mantener convención en create v2 |
| Tests E2E flaky por auth/Playwright | Medio | Usar runner administrado (`run-managed-playwright.mjs`) ya validado en `DONE-CMS-E2E-AUTH-GATE-001` |
| Pérdida de `author_persona_id` explícito en create | Bajo | v2 resuelve `author_persona_id` desde `current_user` igual que shim; documentar en API contract |

---

## 4. Criterios de Aceptación (Definición de "Done")

- [ ] **0 endpoints v1 shim** en `backend/api/cms.py` para testimonials/announcements
- [ ] **0 imports** de `cms_v1_adapters` en todo el codebase
- [ ] **100% páginas admin** (`/plataforma/cms/testimonials*`, `/plataforma/cms/announcements*`) usan `/cms/v2/sites/{key}/posts`
- [ ] **Tests backend** nuevos cubren CRUD por categoría + aislamiento cross-sede (≥90%)
- [ ] **Tests E2E** cubren flujos críticos create→publish→public view + cross-sede isolation
- [ ] **Lint/Typecheck** frontend limpio (0 warnings, 0 errors)
- [ ] **Suite completa** `test_cms_quality.py` pasa sin regresiones
- [ ] **Documentación** actualizada: `CMS_API_CONTRACTS.md`, `ARQUITECTURA_CMS.md` reflejan solo v2

---

## 5. Estimación de Esfuerzo

| Fase | Días | Paralelizable |
|------|------|---------------|
| 0 — Preparación | 1 | No |
| 1 — Backend v2 endpoints + tests | 3-4 | Parcial (CRUD helpers + endpoints) |
| 2 — Frontend migración páginas + formularios | 4-5 | Sí (testimonios y anuncios en paralelo) |
| 3 — Eliminación código v1 | 1-2 | No (tras validación Fase 2) |
| 4 — E2E + validación final | 2 | No |
| **Total** | **11-14 días** | |

---

## 6. Secuencia de Commits Sugerida

```
feat(cms): add canonical category helpers in CRUD
feat(cms): add v2 posts-by-category endpoints with tests
feat(cms): extend v2 schemas for testimonial/announcement shapes
feat(frontend): add cms/v2 client helpers for category-scoped posts
feat(frontend): migrate testimonials pages to v2 endpoints
feat(frontend): migrate announcements pages to v2 endpoints
feat(frontend): adapt TestimonialForm/AnnouncementForm to v2 payloads
refactor(cms): remove v1 shim adapters and endpoints
test(e2e): add v2 unification critical flows
chore(docs): update CMS_API_CONTRACTS and ARQUITECTURA_CMS
```

---

## 7. Decisiones Abiertas (requieren confirmación)

1. **¿Mantener `/cms/testimonials` público como alias de `/cms/v2/public/sites/ccf/posts?category=testimonials`?**
   → Recomendación: **No**. Público ya usa v2 nativo (`PublicSeoManager`, `PublicSectionRenderer`). Eliminar alias reduce superficie.

2. **¿Slug editable por editor en testimonio/anuncio?**
   → Actual shim genera slug automático (`testimonial-{uuid}`). v2 permite slug custom. Recomendación: **sí, editable** con validación unique por site.

3. **¿Campos `emotion`, `media_type` etc. siguen en `seo_json` o mover a columnas dedicadas?**
   → Recomendación: **quedarse en `seo_json`** (patrón v2 actual para campos extensibles). No justifica migración de esquema.

4. **¿Eliminar `TestimonialForm`/`AnnouncementForm` y usar `PostForm` genérico con category preseleccionada?**
   → Recomendación: **mantener formularios especializados** por UX (campos distintos), pero compartir componente base `PostFormBase`.

---

## 8. Rollback Plan

Si hay regresión crítica post-merge:

1. Revertir commits de Fase 3 (eliminación v1) — código v1 shim queda en `git history`
2. Hotfix: restaurar `cms_v1_adapters.py` y endpoints en `cms.py` desde commit previo
3. Frontend: feature flag `NEXT_PUBLIC_CMS_V1_SHIM=true` para volver a endpoints v1 temporalmente (requiere guard en `lib/cms/v2.ts`)

---

**Aprobación requerida:** Tech Lead + Product Owner antes de iniciar Fase 1.

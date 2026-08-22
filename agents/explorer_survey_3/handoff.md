# Handoff Report — Explorer 3: Accessibility, SEO & Documentation Requirements (Fase 6 & 7)

## 1. Observation

### Accessibility (a11y) Findings
- **Public CMS Directory Location:** Public components are located at `frontend/src/components/public/cms/` and `frontend/src/components/public/cms/sections/`.
- **Empty `alt` attributes:**
  - `grep_search` found `alt=""` in `frontend/src/components/cms/builder/BuilderSectionInspector.tsx` line 627: `<OptimizedImage src={safeString(activeSection.props_json?.image_url)} alt="" width={200} height={96} className="w-full h-24 object-cover rounded-md" />`.
  - In `frontend/src/components/public/cms/sections/media.tsx` line 21 (`items.map(...)`), `alt: item.alt || ""` resolves to empty string if `item.alt` is absent, passing `alt=""` to `<OptimizedImage>` at lines 36 and 46.
  - In `frontend/src/components/public/cms/sections/layout.tsx` line 90, `<OptimizedImage src={val(block, "image_url", "")} alt={val(block, "alt", "")} ... />` passes `alt=""` if `block.alt` is not set.
  - `frontend/src/components/public/cms/sections/GalleryMasonrySection.tsx` lines 85 & 131 properly fall back: `alt={imgAlt}` (where `imgAlt = img.alt || title || "Imagen de galería"`) and `alt={images[lightboxIndex].alt || 'Imagen ' + (lightboxIndex + 1)}`.
- **`aria-hidden` Usage:**
  - Present in `frontend/src/components/public/cms/sections/civic-info.tsx` line 169 (`<span className="..." aria-hidden="true">{s.icon}</span>`) and `BreadcrumbNav.tsx` lines 39 & 47.
  - Missing `aria-hidden="true"` on decorative Lucide icons across public section components:
    - `GalleryMasonrySection.tsx` lines 112, 123, 151 (`X`, `ChevronLeft`, `ChevronRight`)
    - `utilities.tsx` lines 46, 87-92, 107, 144, 180, 184 (Social SVGs, `Calendar`, `MapPin`, `Star`)
    - `popup.tsx` line 124 (`X`)
    - `faq.tsx` lines 33, 35 (`ChevronUp`, `ChevronDown`)
    - `social-proof.tsx` line 34 (`Star`)
    - `layout.tsx` lines 59, 128 (`ChevronDown`)
- **Keyboard Navigation & ARIA attributes:**
  - `GalleryMasonrySection.tsx` lightbox has `<button aria-label="Cerrar">` and `<button aria-label="Anterior">`.
  - FAQ and Layout accordion triggers are missing `aria-expanded` and `aria-controls` attributes for full screen reader accessibility.

### SEO Requirements Findings
- **Sitemap Dynamic Generator:**
  - Frontend route exists at `frontend/src/app/sitemap.xml/route.ts` (App Router route handler `GET`).
  - Fetches published CMS pages dynamically via `${NEXT_PUBLIC_API_URL}/api/cms/v2/public/sites/default/pages`, filters `status === "published"`, and merges with `STATIC_ROUTES` (`/`, `/nosotros`, `/pastores`, `/conocer-a-jesus`, `/eventos`, `/predicas`, `/cursos`, `/sedes`, `/boletin`, `/testimonios`, `/privacy`).
  - Builds valid XML with `<urlset>`, `<url>`, `<loc>`, `<lastmod>`, `<changefreq>`, `<priority>`, handles XML character escaping, and sets headers `Content-Type: application/xml; charset=utf-8` and `Cache-Control`.
  - Backend route exists at `backend/api/cms_v2/public.py` line 202 (`GET /api/cms/v2/public/sites/{site_key}/sitemap.xml`) using `build_sitemap_xml` in `backend/core/seo.py`.
- **`canonical_url` Configuration:**
  - Server-side head component `frontend/src/components/public/cms/PublicCmsHead.tsx` line 54 computes `const canonical = page?.canonical_url || `${SITE_URL}/${page?.slug || slug}`;` and renders `<link rel="canonical" href={canonical} />` + `<meta property="og:url" content={canonical} />`.
  - Client-side manager `frontend/src/components/public/cms/PublicSeoManager.tsx` + `SeoHead.tsx` line 89 updates `document.title`, description, canonical link, and JSON-LD structured data dynamically on client navigation.
  - **URL Domain Inconsistency:** `PublicCmsHead.tsx` line 5 defaults `SITE_URL` to `"https://ccf.org"`, whereas `sitemap.xml/route.ts` line 3 defaults `SITE_URL` to `"https://ccfministerio.com"`.

### Documentation Requirements Findings (Fase 7)
- **CMS Runbook (`docs/cms_runbook.md`):** Present and complete (433 lines). Contains architecture overview, start/stop commands (dev/PM2), manual deploy procedure, rollback checklist (code and DB alembic downgrades), troubleshooting guide for common errors, environment variables, monitoring/logging, and backup/restore.
- **SQL Query Metrics (`docs/cms_query_metrics.md`):** Present and documented.
- **API Contracts (`docs/CMS_API_CONTRACTS.md`):** Present (193 lines). Requires expansion to include concrete JSON request/response payload examples for the four primary endpoints (`public_page`, `public_posts_list`, `patch_section`, `transition_cms_page_status`).
- **Architecture Diagram (`docs/cms_architecture.md` / `ARQUITECTURA_CMS.md`):** Requires creating `docs/cms_architecture.md` with a Mermaid diagram illustrating the 10 submódulos in `backend/api/cms_v2/` or `backend/api/cms/` and their interaction with frontend components.
- **`CHANGELOG.md`:** Outdated (last entry `v1.0.1-crm (2026-07-27)`). Needs new entry for `v2.0.0-cms` covering Fases 0–7.

---

## 2. Logic Chain

1. **A11y Analysis:**
   - Observing line 21 in `media.tsx` and line 90 in `layout.tsx` showing empty string fallbacks for `alt` when `item.alt` or `block.alt` is undefined, leads to the conclusion that runtime execution of public CMS renderers can output `<img alt="" />` for functional content images.
   - Observing that decorative Lucide icons across 7 section components lack `aria-hidden="true"` implies screen readers will read icon text nodes or unlabelled vector elements during reading flows.
   - Supplying explicit non-empty alt fallbacks (`alt || title || "Imagen de CMS"`) and adding `aria-hidden="true"` to purely decorative icons will satisfy Lighthouse a11y score ≥ 90.

2. **SEO Analysis:**
   - Inspecting `frontend/src/app/sitemap.xml/route.ts` confirms a fully functional dynamic XML sitemap route handler in Next.js that merges static routes and published CMS pages.
   - Inspecting `PublicCmsHead.tsx` and `SeoHead.tsx` confirms both SSR and CSR canonical URL tags are rendered.
   - Identifying the domain default mismatch (`https://ccf.org` vs `https://ccfministerio.com`) points directly to the need for a unified `SITE_URL` constant.

3. **Documentation Analysis:**
   - Auditing `docs/` showed `cms_runbook.md` and `cms_query_metrics.md` are already created.
   - Comparing `docs/CMS_API_CONTRACTS.md` against Fase 7 acceptance criteria revealed that concrete JSON payload examples for key endpoints (`public_page`, `public_posts_list`, `patch_section`, `transition_cms_page_status`) are needed.
   - Checking `CHANGELOG.md` showed it hasn't been updated since 2026-07-27, requiring a `v2.0.0-cms` release entry.

---

## 3. Caveats

- **Lighthouse Automated Audit Execution:** Live headless Lighthouse execution requires a running frontend server (`npm run start` or `npm run dev`) and an accessible HTTP host. The audit here is static code analysis of the React JSX and Next.js routes.
- **Dynamic CMS Content in DB:** Test data in SQLite or staging DB will determine whether dynamic pages are populated in the sitemap XML response during end-to-end execution.

---

## 4. Conclusion

- **Fase 6 (Accessibility & SEO):**
  - **A11y:** Image alt tags require mandatory non-empty default fallbacks in `media.tsx` and `layout.tsx`. Decorative icons in public sections need `aria-hidden="true"`. Accordion components need `aria-expanded` attributes.
  - **SEO:** Sitemap dynamic XML generator route handler `frontend/src/app/sitemap.xml/route.ts` and backend route `backend/api/cms_v2/public.py` are operational. Canonical URL generation is implemented in both SSR (`PublicCmsHead.tsx`) and CSR (`SeoHead.tsx`); default site URL env fallback should be unified to `https://ccfministerio.com`.
- **Fase 7 (Documentation & Closing):**
  - `docs/cms_runbook.md` and `docs/cms_query_metrics.md` are present.
  - `docs/CMS_API_CONTRACTS.md` needs JSON request/response examples for `public_page`, `public_posts_list`, `patch_section`, and `transition_cms_page_status`.
  - `docs/cms_architecture.md` needs to be created with a Mermaid diagram of the 10 backend submódulos.
  - `CHANGELOG.md` needs an entry for `v2.0.0-cms`.

---

## 5. Verification Method

1. **Verify A11y Alt Fallbacks:**
   ```bash
   grep -rn 'alt=""' frontend/src/components/public/cms/
   grep -rn 'alt=' frontend/src/components/public/cms/sections/
   ```
   *Expected:* 0 functional image components returning empty alt string.

2. **Verify Sitemap XML:**
   ```bash
   curl -i http://localhost:3000/sitemap.xml
   ```
   *Expected:* HTTP 200 OK, `Content-Type: application/xml`, containing `<urlset>` and published page links.

3. **Verify Documentation Files:**
   ```bash
   ls -l docs/cms_runbook.md docs/cms_query_metrics.md docs/CMS_API_CONTRACTS.md docs/cms_architecture.md
   head -n 25 CHANGELOG.md
   ```
   *Expected:* All files exist, `CHANGELOG.md` includes `v2.0.0-cms` section.

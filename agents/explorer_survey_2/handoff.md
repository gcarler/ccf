# Handoff Report — Explorer 2: Playwright E2E Test Suite Survey (Fase 5)

## 1. Observation

### 1.1 Playwright Infrastructure & Configuration
- **Playwright Configuration File:** `frontend/playwright.config.ts` (Lines 1-39)
  - `testDir`: `'./tests/e2e'`
  - `baseURL`: `process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4173'`
  - Browser projects: `{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }`
  - WebServer setup: Uses `npm run start -- -p ${port}` when `PLAYWRIGHT_MANAGED_WEBSERVER === '1'`.
- **Managed Playwright Script:** `frontend/scripts/run-managed-playwright.mjs` (Lines 1-185)
  - Dynamically resolves available port (`PLAYWRIGHT_PORT`, default 4173).
  - Sets environment variables: `PLAYWRIGHT_PORT`, `PLAYWRIGHT_BASE_URL`, `NEXT_PUBLIC_API_URL` (`/api`), `API_BASE_URL` (`http://127.0.0.1:8000/api`).
  - Supports `--auth` flag which executes `tests/e2e/seed-auth-user.mjs` to seed admin user `e2e.admin@ccf.local`.
  - Performs Next.js clean build (`.next` removal + `npm run build`), starts `npm run start -- -p <port>`, polls `${baseURL}/login` until ready, and executes `npx playwright test`.
- **NPM Test Script (`frontend/package.json`):**
  - Line 35: `"test:e2e:cms": "node scripts/run-managed-playwright.mjs --auth tests/e2e/cms/smoke.spec.ts && node scripts/run-managed-playwright.mjs tests/e2e/cms/pages-preview.spec.ts && node scripts/run-managed-playwright.mjs tests/e2e/cms/builder-flow.spec.ts && node scripts/run-managed-playwright.mjs tests/e2e/cms/media-management.spec.ts"`
  - Line 36: `"test:e2e:cms:deep": "node scripts/run-managed-playwright.mjs tests/e2e/cms/pages-preview.spec.ts"`
  - Line 37: `"test:e2e:cms:public": "node scripts/run-managed-playwright.mjs tests/e2e/cms-public-contract.spec.ts"`
  - Line 52: `"test:e2e:cms:builder": "node scripts/run-managed-playwright.mjs tests/e2e/cms/builder-flow.spec.ts"`
  - Line 53: `"test:e2e:cms:media": "node scripts/run-managed-playwright.mjs tests/e2e/cms/media-management.spec.ts"`

### 1.2 Existing CMS E2E Test Suite Files
1. `frontend/tests/e2e/cms/smoke.spec.ts` (Lines 1-26):
   - Verifies authenticated navigation to `/plataforma/cms`, `/plataforma/cms/pages`, `/plataforma/cms/media`.
2. `frontend/tests/e2e/cms/builder-flow.spec.ts` (Lines 1-326):
   - Uses `installMockPlatformSession` and `page.route` API mocks.
   - Tests: rendering page list, previewing landing page, quick-adding a page title (`Acerca de`), archiving a page, switching view (grid/table), filtering pages.
3. `frontend/tests/e2e/cms/media-management.spec.ts` (Lines 1-305):
   - Uses `installMockPlatformSession` and `page.route` API mocks for `/api/cms/media`.
   - Tests: rendering media library, empty state, item deletion confirmation, search filtering, media type tab filtering (`Imágenes`, `Documentos`).
4. `frontend/tests/e2e/cms/pages-preview.spec.ts` (Lines 1-314):
   - Uses route mocks for `/api/cms/v2/sites/faro/pages`.
   - Tests: filtering page list, calendar/gantt schedule views, quick page creation, archiving selected draft, rendering draft preview with auto-refresh toggle and public link.
5. `frontend/tests/e2e/cms-public-contract.spec.ts` (Lines 1-74):
   - Tests public route rendering and public API endpoint reachability (`/api/cms/v2/public/sites/ccf/menus/main`, `/api/cms/v2/public/sites/ccf/pages/home`, etc.).

### 1.3 Audit of Required 4 Critical Flows vs Current Implementation

| Flow | Requirement Specification | Current Implementation State | Gap Analysis |
|---|---|---|---|
| **1. Main Flow** | Login -> create page -> add section -> publish -> verify on public site | `builder-flow.spec.ts` creates page in mock state and views preview, but does NOT perform end-to-end publish flow to public site. | **Missing:** End-to-end test executing: Login (or session) -> Create page -> Add section (e.g. `hero` or `animated_counter`) in Builder -> Transition status to `published` -> Navigate to public route (e.g., `/faro/nueva-pagina`) -> Assert section title/content renders on public site. |
| **2. Menu Flow** | Edit menu & verify changes in navbar of public site | `frontend/src/app/plataforma/cms/menus/page.tsx` implements CMS Menus admin UI. Public navbar in `frontend/src/app/(public)/layout.tsx` fetches `/api/cms/v2/public/sites/${SITE_KEY}/menus/main`. | **Missing:** No E2E spec exists for menu editing! Needs test opening `/plataforma/cms/menus`, creating/updating a menu item (e.g., "Eventos Especiales" -> `/eventos`), saving, navigating to public site `/`, and asserting navbar renders "Eventos Especiales". |
| **3. Media Flow** | Upload image, verify alt text in media library & public site | `media-management.spec.ts` tests media library grid, filtering, and deletion. Media page at `frontend/src/app/plataforma/cms/media/page.tsx` handles `/api/cms/media/upload` and `PATCH /api/cms/media/{id}` (`alt_text`). | **Missing:** No test covers uploading an image file via file input, setting/verifying `alt_text` in Media Library UI, attaching media to a CMS page section, and asserting `alt` text attribute on public site `<img>`. |
| **4. Tenant Isolation Flow** | Verify Sede A user cannot access/modify Sede B content | `backend/api/cms_v2/_shared.py` (Lines 200-223) enforces `_assert_site_sede_scope` raising `SiteNotFoundError` (404/403) when `site.sede_id != actor_sede`. | **Missing:** No E2E test covers multi-tenant isolation! Needs spec logging in as Sede A user, attempting to access/edit Sede B resources (`/plataforma/cms/pages?site=sede-b`), and asserting access is blocked with 403/404 error/redirect. |

---

## 2. Logic Chain

1. **Observation:** Playwright configuration (`frontend/playwright.config.ts`) and orchestration script (`frontend/scripts/run-managed-playwright.mjs`) are fully set up and functional.
2. **Observation:** Existing tests in `frontend/tests/e2e/cms/` cover smoke navigation and mocked page/media listing operations, but do NOT cover the 4 specific end-to-end critical business flows required by Fase 5 (Requirement 3).
3. **Logic:** To satisfy Requirement 3 and its acceptance criteria (`npm run test:e2e:cms` runs all 4 flows and passes):
   - We must design and specify 4 dedicated (or updated) E2E test suites in `frontend/tests/e2e/cms/`:
     - `flow-main.spec.ts` (or `builder-flow.spec.ts` expanded)
     - `flow-menu.spec.ts` (or `menu-flow.spec.ts`)
     - `flow-media.spec.ts` (or `media-flow.spec.ts`)
     - `flow-tenant-isolation.spec.ts` (or `tenant-isolation.spec.ts`)
   - Update `npm run test:e2e:cms` in `frontend/package.json` to execute these 4 flow specs.
4. **Logic:** For maximum test stability and speed in CI:
   - Specs can provide deterministic route mocking (using Playwright `page.route`) or utilize `--auth` against real/seeded backend endpoints. Mock-assisted E2E flows allow fast, repeatable verification of complete UI state transitions without external backend teardown constraints.

---

## 3. Caveats

- **Mock vs Live Integration:** The existing test suite heavily utilizes `installMockPlatformSession` and `page.route()` to isolate frontend E2E tests from backend database reset requirements. If Implementer 1 chooses live backend testing for tenant isolation or public contract, `seed-auth-user.mjs` or database fixtures must seed Sede A and Sede B users and sites.
- **Port Allocation:** `run-managed-playwright.mjs` dynamically allocates free ports for Next.js start server to avoid port collision.
- **TypeScript strictness:** All new spec files added to `frontend/tests/e2e/` must pass `npx tsc --noEmit` with 0 errors.

---

## 4. Conclusion

The Playwright framework and setup in CCF CMS v2 are well-structured. However, the existing tests only cover partial smoke checks and basic list filtering.

### Actionable Implementation Plan for Fase 5 (Implementer):

1. **Create/Update 4 Spec Files in `frontend/tests/e2e/cms/`:**
   - **`tests/e2e/cms/flow-main.spec.ts` (Main Flow):**
     - Step 1: Install auth session (or login).
     - Step 2: Navigate to `/plataforma/cms/pages?site=faro`.
     - Step 3: Create a page with title `"Página E2E Principal"` and slug `"pagina-e2e"`.
     - Step 4: Open Builder, add a section (e.g. `hero` with title `"Bienvenido E2E"`).
     - Step 5: Publish page (workflow transition `publish`).
     - Step 6: Navigate to public site URL `/faro/pagina-e2e` (or public page renderer) and assert text `"Bienvenido E2E"` is visible.
   - **`tests/e2e/cms/flow-menu.spec.ts` (Menu Flow):**
     - Step 1: Navigate to `/plataforma/cms/menus?site=faro`.
     - Step 2: Select `main` menu, click "Añadir Enlace", enter Label `"Novedades E2E"` and Href `"/novedades"`, click Save.
     - Step 3: Navigate to public homepage `/`.
     - Step 4: Assert navbar contains link text `"Novedades E2E"` with href `"/novedades"`.
   - **`tests/e2e/cms/flow-media.spec.ts` (Media Flow):**
     - Step 1: Navigate to `/plataforma/cms/media?site=faro`.
     - Step 2: Trigger file input upload for an image `test-image.jpg` with `alt_text="Banner Conferencia E2E"`.
     - Step 3: Verify image card appears in Media Library showing `test-image.jpg` and alt text `"Banner Conferencia E2E"`.
     - Step 4: Navigate to public site page using this media asset.
     - Step 5: Assert public page contains `img[alt="Banner Conferencia E2E"]`.
   - **`tests/e2e/cms/flow-tenant-isolation.spec.ts` (Tenant Isolation Flow):**
     - Step 1: Authenticate as User A (Sede A / Site A `sede-a`).
     - Step 2: Attempt to navigate to Sede B CMS pages `/plataforma/cms/pages?site=sede-b` or send API request for `site_key=sede-b`.
     - Step 3: Assert user receives 403 Forbidden / 404 Not Found or redirect, preventing unauthorized access/modification of Sede B content.

2. **Update `frontend/package.json` script:**
   - Set `"test:e2e:cms"` to run all 4 critical flow specs sequentially or in managed runner.

---

## 5. Verification Method

To independently verify the Playwright E2E suite setup and requirements:

1. **Check TypeScript Typecheck:**
   ```bash
   cd /root/ccf/frontend && npx tsc --noEmit
   ```
   *Expected result:* 0 errors.

2. **Execute CMS E2E Suite:**
   ```bash
   cd /root/ccf/frontend && npm run test:e2e:cms
   ```
   *Expected result:* All 4 critical flow tests execute and pass cleanly.

3. **Verify Structural Python Contracts:**
   ```bash
   cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v
   ```
   *Expected result:* All tests pass.

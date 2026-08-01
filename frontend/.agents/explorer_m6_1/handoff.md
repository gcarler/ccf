# Handoff Report: Milestone 6 Playwright E2E Test Setup Investigation

## 1. Observation

### Existing Files & Test Setup
- **Playwright Config**: `/root/ccf/frontend/playwright.config.ts` (lines 9-19)
  - `testDir: './tests/e2e'`
  - `baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4173'`
  - Uses `chromium` project.
- **Session Helper**: `/root/ccf/frontend/tests/e2e/helpers/mockPlatformSession.ts` (lines 10-77)
  - `installMockPlatformSession(page, options)` seeds `sessionStorage` and `localStorage` with `ccf_token` and `ccf_refresh_token` (`mock-e2e-token`), and mocks `**/api/v3/auth/me`, `**/api/auth/v3/me`, `**/api/v3/auth/refresh`, `**/api/v3/auth/logout`.
- **Target Spec File**: `/root/ccf/frontend/tests/e2e/cms/builder-puck-flow.spec.ts`
  - File status: Currently missing (does not exist in `tests/e2e/cms/`).

### Puck Builder Route & Component Specs
- **Route Path**: `/plataforma/cms/builder-puck?site=ccf&page=home`
- **Page Component**: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`
  - Auth check: Lines 59-60: `const { token, user } = useAuth(); const canEdit = canEditCms(user?.role);`
  - Query params: Lines 62-63: `const siteKey = searchParams?.get("site") || SITE_KEY; const pageSlug = searchParams?.get("page") || "";`
  - Initial load calls (lines 118-121):
    - `listCmsSections(siteKey, pageSlug, token)` -> `GET /api/cms/v2/sites/${siteKey}/pages/${pageSlug}/sections`
    - `apiFetch<CmsTheme>(`/cms/v2/public/sites/${siteKey}/theme`)` -> `GET /api/cms/v2/public/sites/${siteKey}/theme`
  - Page layout header (lines 1040-1078):
    - Back button: `button[title="Volver a Páginas"]`
    - Page title text: `"Editando página: /home"`
    - Theme badge: `div` containing `"Tema: Tema Faro"`
    - Status badge: `SaveStatusBadge` rendering `"Guardado en borrador"` (saved), `"Sin guardar"` (dirty), `"Guardando cambios..."` (saving), `"Error al guardar"` (error).
    - Save button: `button` with text `"Guardar"` (lines 1065-1077) triggering `handlePublish(latestDataRef.current)`.
  - Puck editor config (lines 1083-1089):
    - `<Puck config={puckConfig} data={initialData} onChange={handlePuckChange} onPublish={handlePublish} iframe={{ enabled: false }} />`

### Hero Section & Custom Field Specifications
- **Hero Component Config**: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` (lines 177-245):
  - Label: `"Banner Héroe (Hero)"`
  - `title` field: `AiField` with `label="Título Principal"`, `fieldType="title"` (line 183)
  - `body` field: `AiField` with `label="Cuerpo del Mensaje"`, `isTextArea`, `fieldType="body"` (line 189)
  - `cta_label` field: `AiField` with `label="Texto del Botón"`, `fieldType="cta"` (line 195)
  - `bg_image` field: `MediaPickerField` with `label="Imagen de Fondo"` (line 202)
  - Canvas rendering: `<section>` with `<h1>{title || "Título del Héroe"}</h1>`, `<p>{body}</p>`, and background image `url(${bg_image})`.

### MediaPicker Integration Specifications
- **Trigger Component**: `/root/ccf/frontend/src/components/cms/builder/MediaPickerField.tsx`
  - Label: `"Imagen de Fondo"` (line 26)
  - Button text: `"Seleccionar Imagen"` when `value` is empty, `"Cambiar Imagen"` when `value` is set (line 50)
  - Clicking triggers global coordinator `mediaPickerTriggerRef(onChange, value)`, setting `mediaPickerOpen = true` in page state (lines 99-105 in `page.tsx`).
- **Modal Component**: `/root/ccf/frontend/src/components/cms/builder/MediaPicker.tsx`
  - Modal attributes: `role="dialog"`, `aria-label="Selector de medios"`, `data-testid="media-picker"` (lines 124-127)
  - Fetch call on open: `apiFetch<{ items: CmsMediaItem[]; total: number }>("/cms/media", { token })` -> `GET /api/cms/media`
  - Media item selector: `button[data-testid="media-item-button"]` (line 203)
  - Selection: Clicking item calls `onSelect(item)`, sets image URL, closes modal.

### AI Assistant Specifications
- **Assistant Component**: `/root/ccf/frontend/src/components/cms/builder/AiField.tsx`
  - Prompt input: `input[placeholder="Tema para la IA..."]` (line 200)
  - Quick chips: buttons starting with `+ ` e.g., `+ Título atractivo`, `+ Bienvenida inspiradora` (lines 182-195)
  - Generate button: `button` with text `"Redactar IA"` (line 230)
  - Fetch call: `apiFetch<{ response: string }>("/system/ai/generate", { method: "POST", token, body: { prompt, context } })` -> `POST /api/system/ai/generate` (lines 122-129)
  - On response: Cleans text (`cleanAiResponse`) and updates field value via `onChange`.

### Auto-save & DB Persistence Specifications
- **Debounced Save**: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` (lines 957-974):
  - `handlePuckChange` sets `saveStatus` to `"dirty"` (`"Sin guardar"`) and sets a 3000ms timer (`setTimeout(..., 3000)`).
  - When timer fires (or manual `"Guardar"` button is clicked), calls `savePageData`.
- **DB Persistence Calls**:
  - Updates: `patchCmsSection(siteKey, pageSlug, id, { sort_order: i, props_json: cleanProps }, token)` -> `PATCH /api/cms/v2/sites/${siteKey}/pages/${pageSlug}/sections/${id}` (lines 882-888)
  - Inserts: `createCmsSection(siteKey, pageSlug, { type, sort_order: i, props_json: cleanProps }, token)` -> `POST /api/cms/v2/sites/${siteKey}/pages/${pageSlug}/sections` (lines 890-896)
  - Deletions: `deleteCmsSection(siteKey, pageSlug, sectionId, token)` -> `DELETE /api/cms/v2/sites/${siteKey}/pages/${pageSlug}/sections/${id}` (line 912)
  - Re-fetch fresh state: `listCmsSections(siteKey, pageSlug, token)` -> `GET /api/cms/v2/sites/${siteKey}/pages/${pageSlug}/sections` (line 922).
  - Status updates: `"saving"` (`"Guardando cambios..."`) -> `"saved"` (`"Guardado en borrador"`).

---

## 2. Logic Chain

1. **Test Environment**:
   - `playwright.config.ts` uses `baseURL` (`http://localhost:4173` or `process.env.PLAYWRIGHT_BASE_URL`).
   - `installMockPlatformSession` configures auth headers and `sessionStorage` tokens so `useAuth()` in `PuckBuilderPage` sees an authenticated user with edit permissions (`role: 'admin'`).

2. **Step 2a (Navigation)**:
   - When navigating to `/plataforma/cms/builder-puck?site=ccf&page=home`, `PuckBuilderPage` mounts.
   - It performs initial parallel `Promise.all` fetches: `GET /api/cms/v2/sites/ccf/pages/home/sections` and `GET /api/cms/v2/public/sites/ccf/theme`.
   - Mocking these routes allows the page to load without 404/500 errors and renders the header with `"Editando página: /home"` and status `"Guardado en borrador"`.

3. **Step 2b (Hero Section Editing)**:
   - Initial section fixture should contain a section of `type: "hero"`.
   - Clicking on the Hero section canvas item selects it in Puck, rendering custom fields in Puck's sidebar (`AiField` for title/body, `MediaPickerField` for background image).

4. **Step 2c (MediaPicker Image Selection)**:
   - Clicking `"Seleccionar Imagen"` inside the `MediaPickerField` calls `mediaPickerTriggerRef`, opening `<MediaPicker open={true} />`.
   - `MediaPicker` triggers `GET /api/cms/media`.
   - Mocking `GET /api/cms/media` returns media items.
   - Clicking `button[data-testid="media-item-button"]` updates the image URL, closes the modal, and updates `bg_image` in Puck's block props.

5. **Step 2d (AI Text Generation)**:
   - Clicking `+ Título atractivo` chip or entering `"Jóvenes CCF"` in `input[placeholder="Tema para la IA..."]` and clicking `"Redactar IA"` calls `POST /api/system/ai/generate`.
   - Mocking `POST /api/system/ai/generate` returns `{ response: "Encuentro de Jóvenes CCF 2026" }`.
   - `AiField` updates title input value to `"Encuentro de Jóvenes CCF 2026"`.

6. **Step 2e (Auto-Save & Persistence)**:
   - The block property changes trigger `handlePuckChange`.
   - State updates to `saveStatus = "dirty"` (`"Sin guardar"`).
   - After 3000ms (or on clicking manual `"Guardar"` button), `savePageData` issues `PATCH /api/cms/v2/sites/ccf/pages/home/sections/section-hero-1` with updated `props_json`.
   - Status badge transitions to `"Guardando cambios..."` then `"Guardado en borrador"`.

---

## 3. Caveats

- `tests/e2e/cms/builder-puck-flow.spec.ts` does not yet exist on disk and must be created by the implementer.
- In Playwright tests, waiting for a 3000ms debounce timer can be done via `page.waitForTimeout(3500)` or by clicking the manual `"Guardar"` button to trigger synchronous save immediately without waiting.
- Playwright route order: Specific endpoints (`GET **/api/cms/v2/sites/ccf/pages/home/sections`, `POST **/api/system/ai/generate`, `GET **/api/cms/media`) must be registered before broad fallback handlers (`**/api/cms/v2/sites**`).
- Dynamic section IDs: When creating new blocks in Puck, `savePageData` issues `POST` and expects response with `id`. The mock must return a valid section object containing an `id` string.

---

## 4. Conclusion

All components, endpoints, DOM selectors, and test step requirements for Milestone 6 Playwright E2E test setup (`tests/e2e/cms/builder-puck-flow.spec.ts`) have been fully identified and verified.

The test spec should be implemented as follows:
- **Spec Path**: `tests/e2e/cms/builder-puck-flow.spec.ts`
- **Helper**: Import `installMockPlatformSession` from `../helpers/mockPlatformSession`.
- **Mocks to Register**:
  1. `GET **/api/cms/v2/sites/ccf/pages/home/sections` (returns initial section list)
  2. `GET **/api/cms/v2/public/sites/ccf/theme` (returns theme tokens)
  3. `GET **/api/cms/media` (returns media items array)
  4. `POST **/api/system/ai/generate` (returns `{ response: string }`)
  5. `PATCH **/api/cms/v2/sites/ccf/pages/home/sections/*` and `POST **/api/cms/v2/sites/ccf/pages/home/sections` (captures payload and returns section object)
- **Key Selectors**:
  - Main header: `page.getByText('Editando página: /home')`
  - Status badge: `page.getByText('Guardado en borrador')`, `page.getByText('Sin guardar')`, `page.getByText('Guardando cambios...')`
  - Manual Save button: `page.getByRole('button', { name: 'Guardar' })`
  - MediaPicker trigger button: `page.getByRole('button', { name: 'Seleccionar Imagen' })`
  - MediaPicker modal: `page.getByTestId('media-picker')`
  - Media item: `page.getByTestId('media-item-button').first()`
  - AI Prompt input: `page.getByPlaceholder('Tema para la IA...').first()`
  - AI Redactar button: `page.getByRole('button', { name: 'Redactar IA' }).first()` or chip `page.getByRole('button', { name: '+ Título atractivo' })`

---

## 5. Verification Method

To verify the E2E test setup once implemented:
1. Run Playwright test:
   ```bash
   npx playwright test tests/e2e/cms/builder-puck-flow.spec.ts
   ```
2. Verify all test cases pass with 0 errors.
3. Verify type safety & linting:
   ```bash
   npm run typecheck
   npm run lint
   ```

# Handoff Report: Puck Blocks, Auto-Save & Playwright E2E Setup

## 1. Observation

### 1.1 Puck Block Catalog & Array Fields (`/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`)
- **Location**: Lines 180 to 758 in `src/app/plataforma/cms/builder-puck/page.tsx`.
- **Registered Blocks**:
  1. `hero` (lines 198–288): Fields `title` (`AiTextInput`), `body` (`AiTextInput`), `cta_label`, `cta_href`, `bg_image` (custom MediaPicker trigger button).
  2. `rich_text` (lines 289–342): Fields `title` (`AiTextInput`), `body` (`AiTextInput`), `cta_label`, `cta_href`.
  3. `cta_banner` (lines 343–413): Fields `title` (`AiTextInput`), `body` (`AiTextInput`), `cta_label`, `cta_href`, `cta_label_2`, `cta_href_2`.
  4. `faq` (lines 414–469): Array field `items` (`q`, `a`).
  5. `testimonials` (lines 470–539): Array field `items` (`author`, `role`, `content`, `stars`).
  6. `stats` (lines 540–591): Array field `items` (`value`, `label`).
  7. `gallery` (lines 592–663): Array field `items` (`url`, `alt`, `caption`). `url` uses `type: "custom"` with MediaPicker integration.
  8. `cards` (lines 664–754): Array field `items` (`title`, `body`, `cta_label`, `cta_href`, `image_url`). `image_url` uses `type: "custom"` with MediaPicker integration.
- **Array Fields Mechanism**:
  - Puck (`@puckeditor/core` v0.22.4) natively handles dynamic list fields via:
    ```typescript
    items: {
      type: "array",
      label: "Imágenes de la Galería",
      getItemSummary: (item: any) => item.alt || item.url || "Imagen vacía",
      defaultItemProps: { url: "", alt: "Imagen", caption: "" },
      arrayFields: {
        url: { type: "custom", render: ({ value, onChange }) => ... },
        alt: { type: "text", label: "Texto Alt" },
        caption: { type: "text", label: "Leyenda / Copete" },
      }
    }
    ```
  - Puck renders "Add item", reorder arrows/drag handles, and item delete controls automatically. Custom field renderers (`type: "custom"`) inside `arrayFields` hook into `mediaPickerTrigger` callback to update array element values via `onChange(url)`.

### 1.2 Database Save & Auto-Save Mechanisms
- **Current Manual Save (`handlePublish`, lines 759–821)**:
  - Takes `data: { content: any[] }` from Puck.
  - Iterates over `data.content`:
    - Checks if `item.props.id` exists in `dbSections`.
    - If present: Calls `patchCmsSection(siteKey, pageSlug, id, { sort_order: i, props_json: cleanProps }, token)` (lines 780–786).
    - If missing: Calls `createCmsSection(siteKey, pageSlug, { type: item.type, sort_order: i, props_json: cleanProps }, token)` (lines 789–794) and assigns `created.id` back to `item.props.id`.
  - Deletes database sections missing from Puck content via `DELETE /cms/v2/sites/${siteKey}/pages/${pageSlug}/sections/${sectionId}` (lines 803–810).
  - Fetches fresh list from DB via `listCmsSections(siteKey, pageSlug, token)` (line 813).
- **Auto-Save Status**:
  - **MISSING**: Line 885–890 mounts `<Puck config={puckConfig} data={initialData} onPublish={handlePublish} iframe={{ enabled: false }} />`.
  - `@puckeditor/core` provides `onChange?: (data: Data) => void`. Currently `onChange` is not passed to `<Puck>`, so changes are only saved when the user clicks the Publish/Save button manually.

### 1.3 Builder Routes Comparison
- **Existing `/plataforma/cms/builder/page.tsx`** (64 lines):
  - Uses legacy non-Puck components (`BuilderSidebar`, `BuilderCanvas`, `BuilderRightPanel`, `usePageBuilder`).
- **New `/plataforma/cms/builder-puck/page.tsx`** (912 lines):
  - Built on `@puckeditor/core` `<Puck>` component with complete block catalog, MediaPicker drawer, AI text assistant, and CMS V2 API persistence.
- **Link References**:
  - Pages in `src/app/plataforma/cms/pages/page.tsx` and `src/app/plataforma/cms/page.tsx` navigate to `/plataforma/cms/builder?site=${siteKey}&page=${slug}`.

### 1.4 Playwright E2E Setup (`tests/e2e`)
- **Configuration (`playwright.config.ts`)**:
  - `testDir: './tests/e2e'`, default project `chromium`, base URL `http://localhost:4173` or `PLAYWRIGHT_BASE_URL`.
- **Helpers**:
  - `tests/e2e/helpers/mockPlatformSession.ts`: `installMockPlatformSession(page, options)` seeds `sessionStorage` and `localStorage` (`ccf_token`, `ccf_refresh_token`) and intercepts `/api/v3/auth/me` and `/api/auth/v3/me`.
- **Existing CMS E2E Specs**:
  - `tests/e2e/cms/builder-flow.spec.ts`: Tests page management at `/plataforma/cms/pages` and preview at `/plataforma/cms/preview`.
  - `tests/e2e/cms/media-management.spec.ts`: Tests media library drawer and uploads.
- **Target Spec for R6**:
  - `tests/e2e/cms/builder-puck-flow.spec.ts` does **not** exist yet.

---

## 2. Logic Chain

1. **R4 (Block Catalog & Array Fields)**:
   - *Observation*: `gallery` and `cards` are defined with `type: "array"`, `arrayFields`, `getItemSummary`, and `defaultItemProps` in `builder-puck/page.tsx` (lines 592–754).
   - *Reasoning*: Puck natively manages array state (add, reorder, delete). The custom image picker inside `arrayFields` correctly invokes `mediaPickerTrigger` to trigger the `MediaPicker` drawer and execute `onChange(url)`.
   - *Conclusion for R4*: The catalog is feature-complete for Hero, Rich Text, CTA Banner, Gallery, and Cards. Recommend adding `AiTextInput` on `gallery` and `cards` title/body fields for complete AI feature parity across all block headers.

2. **R5 (Auto-Save & Manual Save Button)**:
   - *Observation*: `<Puck>` prop `onPublish={handlePublish}` exists for manual save, but `onChange` is omitted (lines 885–890). `@puckeditor/core` types confirm `onChange?: (data: Data) => void` is supported.
   - *Reasoning*: Auto-save requires invoking a background debounced save function whenever `onChange` emits updated Puck data.
   - *Conclusion for R5*: Implement dual save:
     a) Add `useDebouncedCallback` or `useRef` timer (e.g. 2500ms) on `onChange` to execute background persistence without locking the editor UI.
     b) Add a status badge in header ("Auto-guardando...", "Guardado", "Error de sincronización").
     c) Keep manual publish button (`onPublish` + visible button) for instant synchronous database flush.

3. **R6 (Playwright E2E Suite & Route Migration)**:
   - *Observation*: Existing CMS specs use `installMockPlatformSession` and mock route handlers in `tests/e2e/cms/builder-flow.spec.ts`. Route `/plataforma/cms/builder` points to legacy 64-line code.
   - *Reasoning*: To fulfill R6 without breaking existing callers, `tests/e2e/cms/builder-puck-flow.spec.ts` should be created to test Puck block editing, AI text generation, MediaPicker selection, auto-save, and DB update verification. Once verified, `/plataforma/cms/builder/page.tsx` should be replaced with the Puck implementation.
   - *Conclusion for R6*: Create `tests/e2e/cms/builder-puck-flow.spec.ts` mocking `/api/cms/v2/sites/*/pages/*/sections`, `/api/cms/v2/public/sites/*/theme`, `/api/system/ai/generate`, and `/api/cms/media`. Swap `/plataforma/cms/builder/page.tsx` after green test run.

---

## 3. Caveats

1. **Race Conditions in Auto-Save**: Rapid typing could trigger multiple overlapping background requests. Auto-save must track active promises or use a sequence counter so older background save responses do not overwrite newer state.
2. **Puck Custom Field Ref (`mediaPickerTrigger`)**: `mediaPickerTrigger` is a module-level variable. In concurrent server rendering or tab switches, state must be cleaned up cleanly in `useEffect` return cleanup (already present in `builder-puck/page.tsx` lines 123–134).
3. **Playwright Mock Handler Order**: Playwright route matching dispatches handlers in registration order. Specific route mocks (e.g. `/sections`) must be registered before general wildcards (`/sites**`).
4. **Theme CSS Variable Isolation**: `<Puck iframe={{ enabled: false }}>` relies on the parent DOM having `style={themeStyles}` applied on `<main>` so CSS custom properties (`--site-background`, `--site-primary`) cascade properly.

---

## 4. Conclusion

- **R4 (Puck Catalog)**: Hero, Rich Text, CTA Banner, Gallery, and Cards are fully configured with dynamic `array` list support and custom `MediaPicker` triggers inside array items.
- **R5 (Auto-Save & Save Button)**: Persistence logic (`handlePublish`) is complete for manual save. Auto-save can be added seamlessly by binding a debounced handler to Puck's `onChange` callback.
- **R6 (E2E Tests & Migration)**: Playwright infrastructure is ready. `builder-puck-flow.spec.ts` needs to be written to simulate section editing, AI text generation, MediaPicker image selection, auto-save verification, and DB state validation. Replacing `/plataforma/cms/builder/page.tsx` with `PuckBuilderPage` will complete the route migration cleanly.

---

## 5. Verification Method

To independently verify these findings and future implementation:

1. **Type Check**:
   ```bash
   npm run typecheck
   ```
2. **Unit / Integration Tests**:
   ```bash
   npx vitest run src/app/plataforma/cms
   ```
3. **Playwright E2E Test Run**:
   ```bash
   npx playwright test tests/e2e/cms/builder-puck-flow.spec.ts
   ```
4. **Visual Inspection**:
   - Navigate to `/plataforma/cms/builder-puck?site=ccf&page=home` (and `/plataforma/cms/builder` post-migration).
   - Test adding Gallery and Cards items, reordering, deleting, selecting images via MediaPicker, clicking "Redactar IA", and observing auto-save status.

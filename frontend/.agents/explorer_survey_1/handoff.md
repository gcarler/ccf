# Investigation Report: Puck Editor & CSS Theme Specialist (Explorer 1)

## 1. Observation

### 1.1 Puck Editor Implementation Files
- **Primary Puck Page Component**: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`
  - Imports: `import { Puck, Config } from "@puckeditor/core";` (Line 4), `import "@puckeditor/core/dist/index.css";` (Line 5).
  - Main Component: `export default function PuckBuilderPage()` (Line 99).
  - Includes helper `AiTextInput` (Lines 21-97) for AI generation calls to `/system/ai/generate`.
  - Includes global `mediaPickerTrigger` callback coordinator (Lines 18, 123-134) connecting Puck custom fields to `MediaPicker` (Lines 894-908).
  - Component Registry (`puckConfig` memoized on Line 180):
    - `root`: Root wrapper container with inline style `backgroundColor: "var(--site-background, #001134)"` and `color: "var(--site-on-background, #d9e2ff)"` (Lines 183-196).
    - `hero` (Lines 198-288): Title (`AiTextInput`), body (`AiTextInput`), CTA label, CTA href, background image (`MediaPicker`). Render function styled with `var(--site-*)` variables.
    - `rich_text` (Lines 289-342): Title (`AiTextInput`), body (`AiTextInput`), CTA label, CTA href. Styled with `var(--site-surface)`, `var(--site-on-surface)`, etc.
    - `cta_banner` (Lines 343-413): Title (`AiTextInput`), body (`AiTextInput`), 2 CTAs. Styled with `var(--site-primary-container)`, `var(--site-on-surface)`, etc.
    - `faq` (Lines 414-469): Array of Q&A items (`items`). Styled with `var(--site-surface)`, `var(--site-on-surface)`.
    - `testimonials` (Lines 470-539): Array of testimonial items (`items`). Styled with `var(--site-surface-container-low)`.
    - `stats` (Lines 540-591): Array of stat items (`items`). Styled with `var(--site-primary)`.
    - `gallery` (Lines 592-663): Array of gallery images (`items` with `url` via custom `MediaPicker`). Styled with `var(--site-surface)`, `var(--site-outline-variant)`.
    - `cards` (Lines 664-754): Array of card items (`items` with `image_url` via custom `MediaPicker`). Styled with `var(--site-surface-container-low)`.

### 1.2 Puck Render & `iframe` Prop Configuration
- Line 885-890 of `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`:
  ```tsx
  <Puck
    config={puckConfig}
    data={initialData}
    onPublish={handlePublish}
    iframe={{ enabled: false }}
  />
  ```
- `<Puck />` is rendered with `iframe={{ enabled: false }}` inside `<div className="flex-1 overflow-hidden relative">`.
- Disabling iframe isolation ensures Puck renders directly in the main DOM tree, permitting direct access to globally injected CSS custom properties, Tailwind CSS rules, and Next.js font variables without iframe document boundaries.

### 1.3 Site Theme CSS Variables (`--site-*`) & Fonts (`Outfit`, `Inter`)
- **Theme Variable Definitions**:
  - `/root/ccf/frontend/src/app/(public)/public.css` defines theme scopes `.theme-light` (Lines 14-71), `.theme-institutional` (Lines 74-131), `.theme-dark` (Lines 135-192).
  - Tokens include: `--site-background`, `--site-on-background`, `--site-surface`, `--site-on-surface`, `--site-on-surface-variant`, `--site-primary`, `--site-on-primary`, `--site-primary-container`, `--site-surface-container-low`, `--site-outline`, `--site-outline-variant`, `--site-cta-gradient`, `--site-cta-shadow`.
  - `/root/ccf/frontend/tailwind.config.ts` maps Tailwind color classes (`site-background`, `site-primary`, `site-surface`, etc.) to `var(--site-*)` CSS custom properties (Lines 47-93).
  - In `PuckBuilderPage` (`src/app/plataforma/cms/builder-puck/page.tsx`), remote theme tokens are loaded via `apiFetch<CmsTheme>(`/cms/v2/public/sites/${siteKey}/theme`)` (Line 145), mapped to `--site-*` properties, set in component state `themeStyles` (Lines 161-167), and injected into the container element `<main style={themeStyles}>` (Line 851).
- **Font Setup**:
  - `/root/ccf/frontend/src/app/layout.tsx` currently loads `Roboto`, `Open_Sans`, `Inter` via `next/font/google` (Lines 6-28):
    ```ts
    const inter = Inter({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-inter", display: "swap", preload: false });
    ```
    Variable `${inter.variable}` is attached to the `<html>` root element (Line 65).
  - `Outfit` font is available in `next/font/google` but is **NOT** currently declared in `src/app/layout.tsx`.
  - `/root/ccf/frontend/tailwind.config.ts` maps `fontFamily.body` to `["var(--font-inter)", "Inter", ...]` (Line 102).

### 1.4 Builder Routes & Navigation References
- **Puck Route**: `/plataforma/cms/builder-puck` (`/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`).
- **Original Route**: `/plataforma/cms/builder` (`/root/ccf/frontend/src/app/plataforma/cms/builder/page.tsx`).
- **Platform Navigation References**:
  - `/root/ccf/frontend/src/components/cms/CmsModuleNav.tsx` (Line 52) points to `/plataforma/cms/builder`.
  - `/root/ccf/frontend/src/components/workspace/moduleConfigs.ts` (Line 375) points to `/plataforma/cms/builder`.
  - `/root/ccf/frontend/src/app/plataforma/cms/pages/page.tsx` (Lines 324, 493, 656, 705) points to `/plataforma/cms/builder`.
  - `/root/ccf/frontend/src/app/plataforma/cms/page.tsx` (Lines 308, 369) points to `/plataforma/cms/builder`.

---

## 2. Logic Chain

1. **Puck Canvas Styling Inheritance**:
   - `iframe={{ enabled: false }}` is explicitly configured on line 889 of `src/app/plataforma/cms/builder-puck/page.tsx`.
   - Because iframe isolation is disabled, all styles present in the document's `<head>` and `<html>` wrapper are available to the Puck canvas.
   - The outer `<main style={themeStyles}>` element in `builder-puck/page.tsx` dynamically receives all `--site-*` variables loaded from `/cms/v2/public/sites/${siteKey}/theme`.
   - Therefore, any Puck block rendered within the canvas automatically resolves CSS variables like `var(--site-background)`, `var(--site-surface)`, and `var(--site-primary)`.

2. **Typography Integration (R1 - Outfit & Inter)**:
   - `Inter` font is already configured via `next/font/google` in `src/app/layout.tsx` and injected into `<html>`.
   - `Outfit` font is required by R1 ("Integrar las fuentes tipográficas del sistema (Outfit, Inter)").
   - To make `Outfit` available across the app and Puck canvas, `src/app/layout.tsx` must load `Outfit` from `next/font/google` (with `variable: "--font-outfit"`) and include `${outfit.variable}` in the `<html>` class list.
   - `tailwind.config.ts` can then map `--font-outfit` under `fontFamily.display` or `fontFamily.headline`, allowing Puck blocks to use `font-display` or `font-headline` to display headings in `Outfit`.

3. **Route Migration Path (R6)**:
   - All navigation controls across the CMS currently point to `/plataforma/cms/builder`.
   - `/plataforma/cms/builder-puck` is currently a standalone route holding the Puck implementation.
   - Once all phases (R1-R5) are completed and validated, replacing or re-exporting `PuckBuilderPage` inside `/root/ccf/frontend/src/app/plataforma/cms/builder/page.tsx` will migrate the entire platform to Puck seamlessly without requiring updates to 14+ navigation links.

---

## 3. Caveats

- **Theme Fallbacks**: If the backend theme endpoint (`/cms/v2/public/sites/${siteKey}/theme`) fails or returns `null`, `themeStyles` will be empty (`{}`). In that case, Puck blocks rely on the default CSS variable fallbacks defined in `public.css` or inline defaults (e.g. `var(--site-background, #001134)`).
- **Outfit Font Scope**: `Outfit` is not currently imported in `src/app/layout.tsx`. Implementers must import `Outfit` from `next/font/google` during R1 updates.
- **Auto-save Implementation**: `builder-puck/page.tsx` currently has `handlePublish` triggered via Puck's `onPublish` manual button, but auto-save debounce functionality (R5) is not yet implemented.

---

## 4. Conclusion

1. **R1 (Theme & CSS Synchronization)** is already partially wired in `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`:
   - `iframe={{ enabled: false }}` is active on `<Puck />`.
   - `--site-*` variables are fetched from backend theme API and applied to the root `<main>` style.
   - Root canvas uses `backgroundColor: "var(--site-background, #001134)"`.
   - **Recommended Action for R1**: Import `Outfit` in `src/app/layout.tsx` (`const outfit = Outfit({ ... variable: "--font-outfit" })`), add `${outfit.variable}` to `<html>`, update `tailwind.config.ts`, and verify that headings in Puck blocks apply `var(--font-outfit)` / `font-headline`.

2. **R2-R5 (MediaPicker, AI, Complex Blocks, Auto-save)** are prototyped or structure-ready in `builder-puck/page.tsx`:
   - `MediaPicker` trigger callback is wired for single image fields, needs verification for array items (gallery and cards).
   - `AiTextInput` is present on `hero`, `rich_text`, `cta_banner`.
   - `gallery` and `cards` blocks are defined with Puck `type: "array"`.
   - Auto-save with debounce needs to be added to `builder-puck/page.tsx`.

3. **R6 (Route Migration & E2E)**:
   - Target route to update: `/root/ccf/frontend/src/app/plataforma/cms/builder/page.tsx`.
   - Playwright test file location: `/root/ccf/frontend/tests/e2e/cms/builder-puck-flow.spec.ts`.

---

## 5. Verification Method

### 1. File Inspection
Inspect the following files to verify structure:
- `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` (Line 889: `iframe={{ enabled: false }}`)
- `/root/ccf/frontend/src/app/layout.tsx` (Line 65: Google font variables on `<html>`)
- `/root/ccf/frontend/tailwind.config.ts` (Lines 47-93: `--site-*` color token mappings)

### 2. Compilation and Type Checking Commands
Run the following commands from `/root/ccf/frontend`:
```bash
npm run typecheck
npm run lint
```
*Invalidation Condition*: Any TypeScript syntax error, missing font variable, or broken export will cause typecheck/lint failure.

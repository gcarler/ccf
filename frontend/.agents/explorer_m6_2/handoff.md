# Handoff Report — Milestone 6 Route Migration Investigation

## 1. Observation

### Key Files Inspected
- **Legacy Builder Route**: `/root/ccf/frontend/src/app/plataforma/cms/builder/page.tsx` (64 lines)
  - Uses legacy `usePageBuilder` hook and 3-column layout components (`BuilderSidebar`, `BuilderCanvas`, `BuilderRightPanel`).
  - Exports `default function CmsBuilderPage()`.
- **Puck Builder Staging Route**: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` (1111 lines)
  - Full `@puckeditor/core` visual editor implementation with custom block fields (`AiField`, `MediaPickerField`), theme synchronization (`var(--site-background)`), debounced auto-save (3s), and manual save button (`handlePublish`).
  - Exports `default function PuckBuilderPage()` and `export type SaveStatus = "saved" | "dirty" | "saving" | "error";`.
- **CMS Layout Wrapper**: `/root/ccf/frontend/src/app/plataforma/cms/layout.tsx` (20 lines)
  - Wraps all `/plataforma/cms/*` pages inside `<ModuleErrorBoundary moduleName="CMS">`, `<WorkspaceLayout allowedPermissions={['cms:read']}>`, and `<CmsModuleNav />`.
- **Legacy Builder Page Tests**: `/root/ccf/frontend/src/app/plataforma/cms/builder/page.test.tsx` (285 lines)
  - Unit tests specifically targeting legacy `CmsBuilderPage` and `usePageBuilder` mocks.

### Grep Search Observations
1. **CMS Navigation Links** (`grep_search` for `/plataforma/cms/builder`):
   - `src/app/plataforma/cms/pages/page.tsx` (lines 324, 493, 656, 705):
     `onClick={(e) => { e.stopPropagation(); router.push('/plataforma/cms/builder?site=${siteKey}&page=${page.slug}'); }}`
   - `src/app/plataforma/cms/pages/[slug]/page.tsx` (lines 67, 78):
     `router.replace('/plataforma/cms/builder?site=${siteKey}&page=${slug}');`
   - `src/app/plataforma/cms/pages/[slug]/versions/page.tsx` (line 182):
     `router.push('/plataforma/cms/builder?site=${siteKey}&page=${slug}');`
   *Finding*: All main platform UI links ALREADY point to `/plataforma/cms/builder`. Replacing `/plataforma/cms/builder/page.tsx` with Puck will instantly activate the Puck editor across the entire platform.

2. **Existing Unit Tests Importing `builder-puck/page`** (`grep_search` for `app/plataforma/cms/builder-puck/page`):
   - `src/components/cms/builder/GalleryCardsEmpiricalRobustness.test.tsx` (line 5)
   - `src/components/cms/builder/PuckSchemaRegistration.test.tsx` (line 5)
   - `src/components/cms/builder/AutoSaveAndHeaderSave.test.tsx` (line 5)
   - `src/components/cms/builder/EmpiricalChallengeM5.test.tsx` (line 5)
   - `src/components/cms/builder/MediaPickerStress.test.tsx` (line 5)
   - `src/components/cms/builder/PuckSchemaRegistrationEdgeCases.test.tsx` (line 5)
   *Finding*: All 6 test files import `PuckBuilderPage` via `import PuckBuilderPage from "@/app/plataforma/cms/builder-puck/page";`. Deleting `builder-puck/page.tsx` would break these test suites.

3. **URL Search Parameter Handling in Puck Editor**:
   - `src/app/plataforma/cms/builder-puck/page.tsx` (lines 57-63):
     ```tsx
     const searchParams = useSearchParams();
     const router = useRouter();
     const { token, user } = useAuth();
     const canEdit = canEditCms(user?.role);

     const siteKey = searchParams?.get("site") || SITE_KEY;
     const pageSlug = searchParams?.get("page") || "";
     ```
   - Fallback handling (lines 1010-1024): If `!token` or `!pageSlug`, displays an informative empty state with a return button `router.push("/plataforma/cms/pages")`.

4. **Header Navigation Back Link**:
   - Line 1043 of `builder-puck/page.tsx`:
     `onClick={() => router.push('/plataforma/cms/pages?site=${siteKey}')}`
     Returns user to the CMS pages table with active `siteKey`.

---

## 2. Logic Chain

1. **Observation 1 & 2**: The legacy builder implementation lives at `/plataforma/cms/builder/page.tsx`, whereas the Puck editor implementation lives at `/plataforma/cms/builder-puck/page.tsx`. 6 unit test files import directly from `@/app/plataforma/cms/builder-puck/page`.
   - *Inference*: Simply replacing `builder/page.tsx` while deleting `builder-puck/page.tsx` will cause compilation/test failure in those 6 test files. Re-exporting from `builder-puck/page.tsx` to `builder/page.tsx` maintains backward compatibility for existing unit tests.

2. **Observation 1 & 3**: All navigation links in `pages/page.tsx`, `pages/[slug]/page.tsx`, and `pages/[slug]/versions/page.tsx` target `/plataforma/cms/builder?site=${siteKey}&page=${slug}`.
   - *Inference*: Moving the complete Puck implementation into `src/app/plataforma/cms/builder/page.tsx` guarantees that all platform navigation seamlessly routes users to the new Puck visual editor without changing link paths.

3. **Observation 3 & 4**: `useSearchParams()` reads `site` and `page` search parameters, defaulting `siteKey` to `SITE_KEY` ("ccf") and `pageSlug` to `""`. When `pageSlug` is empty or user is unauthenticated, it displays a clear prompt and back button.
   - *Inference*: Parameter handling, error state fallback, and back navigation are robust and fully functional in PuckBuilderPage.

4. **Observation 1 & 5**: `src/app/plataforma/cms/layout.tsx` wraps all `/plataforma/cms/*` pages within `ModuleErrorBoundary` and `WorkspaceLayout`.
   - *Inference*: Inherited layouts and permissions (`cms:read`) apply identically to `/plataforma/cms/builder` as they did to `/plataforma/cms/builder-puck`.

---

## 3. Caveats

- **Legacy Unit Test (`builder/page.test.tsx`)**: `src/app/plataforma/cms/builder/page.test.tsx` currently tests the legacy `usePageBuilder` + 3-column layout. When `builder/page.tsx` is replaced with Puck, `builder/page.test.tsx` will fail if not updated to test `PuckBuilderPage`.
- **Read-Only Scope**: As an explorer subagent, no source code changes in `src/` were performed. Implementation must be carried out by the designated implementer or migration step.

---

## 4. Conclusion

Route migration for Milestone 6 can be executed cleanly and safely with zero broken imports using the following 4-step procedure:

1. **Replace Main Route (`src/app/plataforma/cms/builder/page.tsx`)**:
   - Copy the complete Puck editor implementation from `src/app/plataforma/cms/builder-puck/page.tsx` into `src/app/plataforma/cms/builder/page.tsx`.
   - Ensure default export is `PuckBuilderPage` (or `CmsBuilderPage`) and named export `SaveStatus` is preserved.

2. **Re-export Staging Route (`src/app/plataforma/cms/builder-puck/page.tsx`)**:
   - Replace content of `src/app/plataforma/cms/builder-puck/page.tsx` with:
     ```tsx
     "use client";
     export { default, type SaveStatus } from "../builder/page";
     ```
   - This ensures `/plataforma/cms/builder-puck` and unit test imports (`@/app/plataforma/cms/builder-puck/page`) continue to work seamlessly.

3. **Update Builder Route Test (`src/app/plataforma/cms/builder/page.test.tsx`)**:
   - Update test expectations in `src/app/plataforma/cms/builder/page.test.tsx` to assert Puck editor rendering (e.g. `aria-label="Editor visual Puck"` instead of `"Constructor visual CMS"`).

4. **Run Quality Gate Verification**:
   - Run `npm run typecheck` (0 errors) and `npm run lint` (0 errors/warnings).

---

## 5. Verification Method

To independently verify the route migration after implementation:

1. **TypeScript Type Check**:
   ```bash
   npm run typecheck
   ```
   *Expected result*: 0 errors.

2. **ESLint Audit**:
   ```bash
   npm run lint
   ```
   *Expected result*: 0 errors and warnings.

3. **Unit Tests Verification**:
   ```bash
   npx vitest run src/components/cms/builder/ src/app/plataforma/cms/builder/
   ```
   *Expected result*: All 6 Puck test suites and updated `builder/page.test.tsx` pass in green.

4. **E2E Playwright Flow Verification**:
   ```bash
   npx playwright test tests/e2e/cms/builder-puck-flow.spec.ts
   ```
   *Expected result*: Playwright test succeeds targeting `/plataforma/cms/builder-puck` or `/plataforma/cms/builder`.

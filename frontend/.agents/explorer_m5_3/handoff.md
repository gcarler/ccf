# Handoff Report — Milestone 5 (R5 Auto-save & Manual Save Button) Backend API Integration

**Author**: teamwork_preview_explorer_m5_3  
**Working Directory**: `/root/ccf/frontend/.agents/explorer_m5_3`  
**Target Module**: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`  
**Date**: 2026-07-31  

---

## 1. Observation

### Key Code Artifacts Inspected:
1. **`src/app/plataforma/cms/builder-puck/page.tsx`**
   - **`SaveStatusBadge`** (Lines 21–53): Renders 4 UI states (`saving`, `dirty`, `error`, `saved`).
   - **State and Refs** (Lines 65–78):
     - `saveStatus`: `"saved" | "dirty" | "saving" | "error"`
     - `debounceTimerRef`: stores `NodeJS.Timeout | null` for the 3-second auto-save timer.
     - `latestDataRef`: keeps the most recent Puck canvas data (`{ content: any[] }`).
     - `saveSequenceRef` & `latestCompletedSeqRef`: sequence counters preventing out-of-order async write responses.
     - `isInitialLoadRef`: boolean flag set to `true` on load/fetch to swallow the initial `onChange` event from Puck.
     - `dbSectionsRef`: ref mirror of `dbSections` array.
     - `savingRef`: ref mirror of boolean `saving` state.
   - **Data Fetching** (Lines 112–155):
     - `listCmsSections(siteKey, pageSlug, token)` retrieves current sections from backend `/cms/v2/sites/${siteKey}/pages/${pageSlug}/sections`.
     - Maps `sections` into Puck data format: `{ type: sec.type, props: { ...(sec.props_json || {}), id: sec.id } }`.
     - Populates `setInitialData`, updates `latestDataRef.current`, and sets `isInitialLoadRef.current = true`.
   - **Save Handler (`savePageData`)** (Lines 845–951):
     - Receives `dataToSave` and `options: { isAutoSave: boolean }`.
     - Increments `saveSequenceRef.current`.
     - **Inserts & Updates Loop**: Iterates `dataToSave.content[i]`. Destructures `const { id: _, ...cleanProps } = item.props || {}`.
       - If `id` exists in `dbSectionsRef.current`, calls `patchCmsSection(siteKey, pageSlug, id, { sort_order: i, props_json: cleanProps }, token)`.
       - If `id` does NOT exist, calls `createCmsSection(siteKey, pageSlug, { type: item.type, sort_order: i, props_json: cleanProps }, token)`.
       - On section creation, assigns `item.props.id = created.id` to prevent duplicate creates on subsequent saves.
       - Adds active database IDs to `activeIdsInPuck` set.
     - **Deletions Loop**: Finds `missingFromPuck = currentDbSections.filter(s => !activeIdsInPuck.has(s.id))` and calls `deleteCmsSection(siteKey, pageSlug, sectionToDelete.id, token)` for each missing section.
     - **Out-of-order check**: Discards response if `currentSeq < latestCompletedSeqRef.current`.
     - **Fresh reload**: Re-fetches database sections via `listCmsSections` and updates `dbSections`.
     - **Dirty state reconciliation**: Compares `latestDataRef.current` with `dataToSave`. If user made further edits while save was in flight, sets status back to `"dirty"`, otherwise `"saved"`.
     - Shows success toast on manual publish (`!isAutoSave`), silent/error toast on auto-save.
   - **Auto-save `onChange` Handler (`handlePuckChange`)** (Lines 953–970):
     - Swallows first `onChange` call if `isInitialLoadRef.current` is true (`isInitialLoadRef.current = false; return;`).
     - Otherwise updates `latestDataRef.current`, updates status to `"dirty"`, clears existing `debounceTimerRef.current`, and schedules a 3000ms timer to run `savePageData(latestDataRef.current, { isAutoSave: true })`.
   - **Manual Publish Handler (`handlePublish`)** (Lines 972–982):
     - Clears `debounceTimerRef.current` to cancel any pending auto-save task.
     - Calls `savePageData(dataToSave, { isAutoSave: false })` immediately.
   - **Keyboard Shortcut (`Ctrl+S`/`Cmd+S`)** (Lines 992–1004):
     - Intercepts `Ctrl+S` / `Cmd+S` and triggers `handlePublish(latestDataRef.current)`.

2. **Backend API Functions (`src/lib/cms/v2.ts`)**:
   - `listCmsSections`: `GET /cms/v2/sites/${siteKey}/pages/${slug}/sections`
   - `createCmsSection`: `POST /cms/v2/sites/${siteKey}/pages/${slug}/sections` with payload `{ type, props_json, sort_order }`.
   - `patchCmsSection`: `PATCH /cms/v2/sites/${siteKey}/pages/${slug}/sections/${sectionId}` with payload `{ sort_order, props_json }`.
   - `deleteCmsSection`: `DELETE /cms/v2/sites/${siteKey}/pages/${slug}/sections/${sectionId}`.

3. **Existing Test Suites**:
   - `src/components/cms/builder/PuckSchemaRegistration.test.tsx` (Passed 7/7 tests via `npx vitest run`). Tests schema registrations for MediaPicker, AI fields, defaultProps, and render fallbacks.
   - `src/components/cms/builder/PuckSchemaRegistrationEdgeCases.test.tsx`. Tests edge case summaries and limits.

---

## 2. Logic Chain

1. **Section Save Handler Analysis**:
   - **Observation**: `savePageData` in `builder-puck/page.tsx` splits operations into batch creation (`createCmsSection`), update (`patchCmsSection`), and deletion (`deleteCmsSection`).
   - **Deduction**: Existing implementation handles full block lifecycle (create, update, reorder, delete). The sequence control via `saveSequenceRef` guarantees out-of-order network responses won't overwrite fresh data.

2. **Payload Formatting**:
   - **Observation**: Block properties in Puck contain `id` (e.g. `item.props.id`). Before calling `patchCmsSection` or `createCmsSection`, code executes `const { id: _, ...cleanProps } = item.props || {}`.
   - **Deduction**: `cleanProps` prevents embedding the internal database ID inside the JSON blob (`props_json`), maintaining database schema integrity. The positional index `i` is passed as `sort_order`, matching the backend specification (`sort_order: number`). `item.type` (e.g. `"hero"`, `"gallery"`, `"cards"`) maps to the backend section `type`.

3. **Initial Mount vs Save State Synchronization**:
   - **Observation**: On initial load, while `loading` is `true`, `<Puck>` is not rendered. Upon receiving API data in `fetchData()`, `initialData` and `latestDataRef.current` are populated, and `isInitialLoadRef.current` is explicitly set to `true`. When `<Puck>` mounts and triggers its initial `onChange`, `handlePuckChange` detects `isInitialLoadRef.current === true`, flips the ref to `false`, and returns without setting `saveStatus` to `"dirty"` or queuing auto-save.
   - **Deduction**: This mechanism guarantees that page-load populated data is NOT wiped or erroneously marked dirty on mount.

4. **Dual-Mode (Auto-save + Manual Save) Coexistence**:
   - **Observation**: Auto-save uses a 3000ms debounce timer stored in `debounceTimerRef.current`. When the user clicks the "Guardar" button or presses `Ctrl+S`, `handlePublish` immediately executes `clearTimeout(debounceTimerRef.current)`, nullifies the ref, and initiates an immediate synchronous save.
   - **Deduction**: The manual publish safely overrides pending auto-saves without duplicate requests. If the user continues typing while a save is in flight, the comparison `latestDataRef.current !== dataToSave` sets the status back to `"dirty"`, ensuring subsequent auto-saves will flush the newer changes.

5. **Testing Requirements**:
   - **Observation**: Existing test suites (`PuckSchemaRegistration.test.tsx`) verify component registration and rendering, but there is no dedicated unit test for the persistence behavior (`savePageData`, auto-save timer, manual save trigger, sequence tracking).
   - **Deduction**: Adding a dedicated unit test suite (e.g., `src/components/cms/builder/PuckPersistence.test.tsx`) will validate the state machine (`saved` -> `dirty` -> `saving` -> `saved`), timer cancellation, and API calls (`createCmsSection`, `patchCmsSection`, `deleteCmsSection`).

---

## 3. Caveats

- **Network Latency & Rapid Typing**: During high latency, multiple debounced auto-saves could overlap. The sequence ref (`saveSequenceRef`) handles out-of-order completion, but synchronous manual save relies on disabling the "Guardar" button while `saveStatus === "saving"`.
- **Backend API Endpoints**: Assumes backend endpoint `/cms/v2/sites/${siteKey}/pages/${pageSlug}/sections` accepts `sort_order` and `props_json`, as confirmed by `src/lib/cms/v2.ts`.

---

## 4. Conclusion

The backend API integration for Milestone 5 (R5 Auto-save & Manual Save Button) in `src/app/plataforma/cms/builder-puck/page.tsx` is fully functional and architecturally sound:
1. **Section Save Handler**: Properly orchestrates `createCmsSection`, `patchCmsSection`, and `deleteCmsSection` with sequence lock protection.
2. **Payload Formatting**: Properly strips `id` into `cleanProps` and supplies `sort_order: i` alongside `type`.
3. **State Synchronization**: `isInitialLoadRef` reliably guards against initial mount data wiping.
4. **Dual-Mode Execution**: Debounced 3s auto-save seamlessly yields to manual publish ("Guardar" / `Ctrl+S`) by clearing the timer reference.
5. **Testing**: `PuckSchemaRegistration.test.tsx` passes 7/7 tests. A complementary unit test file `PuckPersistence.test.tsx` should be added in Milestone 6 / testing task to verify the auto-save timer state machine.

---

## 5. Verification Method

### 1. Run Unit Tests
Execute Vitest for the Puck schema test suite:
```bash
npx vitest run src/components/cms/builder/PuckSchemaRegistration.test.tsx
```
**Expected Result**: 7 tests passed (0 failed).

### 2. Manual Inspection Points in `src/app/plataforma/cms/builder-puck/page.tsx`:
- Line 875: `const { id: _, ...cleanProps } = item.props || {};`
- Line 967: `debounceTimerRef.current = setTimeout(..., 3000);`
- Line 974: `if (debounceTimerRef.current) { clearTimeout(debounceTimerRef.current); }`
- Line 954: `if (isInitialLoadRef.current) { isInitialLoadRef.current = false; return; }`

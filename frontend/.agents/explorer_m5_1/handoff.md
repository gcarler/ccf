# Milestone 5 Investigation Report: R5 Auto-save & Manual Save Button (Debounce & State Coordinator)

## 1. Observation

### Current Implementation in `src/app/plataforma/cms/builder-puck/page.tsx`
We examined `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` (1107 lines). The auto-save state coordinator and debounced auto-save mechanism are implemented as follows:

1. **Puck Canvas Component** (Lines 1079–1086):
   ```tsx
   <Puck
     config={puckConfig}
     data={initialData}
     onChange={handlePuckChange}
     onPublish={handlePublish}
     iframe={{ enabled: false }}
   />
   ```
   - Passes both `onChange={handlePuckChange}` and `onPublish={handlePublish}` to Puck.

2. **State Coordinator & Refs** (Lines 70–78):
   ```tsx
   const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
   const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
   const latestDataRef = useRef<{ content: any[] }>({ content: [] });
   const saveSequenceRef = useRef<number>(0);
   const latestCompletedSeqRef = useRef<number>(0);
   const isInitialLoadRef = useRef<boolean>(true);
   const dbSectionsRef = useRef<any[]>([]);
   const savingRef = useRef<boolean>(false);
   ```

3. **Status Badge Component** (Lines 21–53):
   `SaveStatusBadge` renders 4 distinct visual states in the header bar:
   - `"saving"`: Amber spinner (`Guardando cambios...`)
   - `"dirty"`: Blue pulsing dot (`Sin guardar`)
   - `"error"`: Red alert triangle (`Error al guardar`)
   - `"saved"`: Emerald checkmark (`Guardado en borrador`)

4. **Puck Change Handler & Debounce** (Lines 953–970):
   ```tsx
   const handlePuckChange = (newData: { content: any[] }) => {
     if (isInitialLoadRef.current) {
       isInitialLoadRef.current = false;
       latestDataRef.current = newData;
       return;
     }

     latestDataRef.current = newData;
     setSaveStatus("dirty");

     if (debounceTimerRef.current) {
       clearTimeout(debounceTimerRef.current);
     }

     debounceTimerRef.current = setTimeout(() => {
       savePageData(latestDataRef.current, { isAutoSave: true });
     }, 3000);
   };
   ```

5. **Dual-Mode Persistence Function `savePageData`** (Lines 845–951):
   - Accepts `dataToSave` and `options: { isAutoSave: boolean }`.
   - Increments sequence counter: `const currentSeq = ++saveSequenceRef.current;`.
   - Distinguishes background auto-save (updates badge to `"saving"`) from manual save (sets `saving` state to `true`, disabling manual button and triggering toast).
   - Diffing & Persistence Algorithm:
     - Existing blocks (in `dbSectionsRef`): calls `patchCmsSection(siteKey, pageSlug, id, { sort_order: i, props_json: cleanProps }, token)`.
     - New blocks (without DB `id`): calls `createCmsSection(...)`, gets returned DB `id`, and updates `item.props.id = created.id` in-place.
     - Deleted blocks: finds section IDs in DB not present in Puck canvas and calls `deleteCmsSection(...)`.
   - Sequence Ordering Guard: Discards state updates if `currentSeq < latestCompletedSeqRef.current`.
   - Post-Save Diff Guard: If `latestDataRef.current` changed while save was in-flight, transitions state back to `"dirty"` rather than `"saved"`.

6. **Manual Save Button & Keyboard Shortcut** (Lines 972–1004, 1061–1073):
   - `handlePublish` clears `debounceTimerRef.current` to prevent duplicate background saves.
   - Triggers `savePageData(dataToSave, { isAutoSave: false })` with immediate toast notification on success/error.
   - Header button shows `Save` icon or `Loader2` spinner.
   - Keyboard listener (`Ctrl+S` / `Cmd+S`) invokes `handlePublish(latestDataRef.current)`.

---

## 2. Logic Chain

### A. How Puck's `onChange(data)` Operates
- Puck's `<Puck onChange={handlePuckChange} />` emits `newData` object whenever:
  1. Blocks are added from the component drawer.
  2. Blocks are reordered in the canvas.
  3. Form inputs / custom field components (`AiField`, `MediaPickerField`) emit value changes.
  4. Blocks are deleted.
- **Initial Load Suppression**: Puck emits an initial `onChange` event upon mounting with `initialData`. The ref check `if (isInitialLoadRef.current) { isInitialLoadRef.current = false; latestDataRef.current = newData; return; }` prevents marking initial load as "dirty" or starting an auto-save timer upon page load.

### B. Debouncing Strategy Analysis (3000ms)
- Setting `DEBOUNCE_MS = 3000` (3 seconds) balances backend HTTP load with responsive user feedback.
- Each keystroke or block drag cancels the active timer (`clearTimeout(debounceTimerRef.current)`) and schedules a fresh timer.
- Auto-save runs asynchronously in the background. The editor canvas remains fully interactive (no modal loading screens or input freezes).

### C. Race Condition & Conflict Resolution Analysis

1. **Race Condition: Auto-Save vs Manual Save**:
   - When the user clicks "Guardar" or presses `Ctrl+S`, `handlePublish` instantly executes `clearTimeout(debounceTimerRef.current); debounceTimerRef.current = null;`.
   - If an auto-save is currently *in flight* (HTTP requests pending), `saveStatus` is `"saving"` and `savingRef.current` is `true`. The manual save button is disabled (`disabled={saveStatus === "saving" || saving}`) to avoid sending duplicate concurrent PATCH/POST operations for the same sections.

2. **Sequence Conflict: Out-of-Order HTTP Responses**:
   - `saveSequenceRef` tracks each save invocation with a monotonically increasing integer (`currentSeq`).
   - If an earlier save request completes *after* a later save request, `if (currentSeq < latestCompletedSeqRef.current)` discards the stale DB reload and state update.

3. **In-Flight Data Updates**:
   - If the user types additional content while `savePageData` is awaiting backend network calls, `latestDataRef.current` accumulates the latest state.
   - At the end of `savePageData`, `JSON.stringify(latestDataRef.current) !== JSON.stringify(dataToSave)` checks if new edits arrived. If so, status transitions back to `"dirty"` so the pending edits will be auto-saved by the next debounce timer.

4. **Section ID In-Place Mutex / In-Memory ID Assignment**:
   - When a block is added in Puck, its `props.id` is initially undefined.
   - `createCmsSection` creates the section in DB and returns `created.id`.
   - `item.props.id = created.id` assigns the ID in-place to Puck's content item.
   - Because `dbSectionsRef` is updated after save, subsequent auto-saves recognize the block as existing in DB and issue a `PATCH` rather than duplicate `POST` creates.

---

## 3. Caveats & Potential Payload / Edge Case Considerations

1. **Sequential HTTP Request Overhead**:
   - Section creates, updates, and deletes are executed sequentially in a `for` loop. For typical landing pages (3–10 sections), request latency is ~100–300ms total. For very large pages (20+ sections), `Promise.all` batching could be considered. However, sequential execution guarantees strict creation and sort order handling.
2. **Component Unmount During In-Flight Save**:
   - The unmount cleanup hook (lines 984–990) clears `debounceTimerRef.current`. However, if `savePageData` is already in flight when the user navigates away, React state setters (`setSaveStatus`, `setDbSections`) could run on an unmounted component. Adding an `isMountedRef` guard inside `savePageData` ensures clean unmounting.
3. **Browser Tab Close / Navigation Protection**:
   - If a user closes the tab within 3 seconds of typing (while status is `"dirty"`), changes might not be auto-saved. Adding a `beforeunload` event handler when `saveStatus === "dirty"` or `saveStatus === "saving"` provides full data loss prevention.

---

## 4. Conclusion

The Milestone 5 (R5 Auto-save & Manual Save Button) mechanism in `src/app/plataforma/cms/builder-puck/page.tsx` is **fully implemented and structurally sound**:
- Puck `onChange` state updates are debounced at 3000ms.
- Race conditions between manual saves and auto-saves are guarded via timer cancellation, sequence tracking, and button disable states.
- Block creation assigns DB section IDs in-place without resetting Puck canvas state.
- `SaveStatusBadge` provides visual feedback for `saved`, `dirty`, `saving`, and `error` states.

---

## 5. Verification Method

### A. Static Verification
```bash
npm run typecheck
npm run lint
```
Verify zero TypeScript and ESLint errors.

### B. Functional & Flow Verification
1. **Initial Mount**: Load `/plataforma/cms/builder-puck?site=ccf&page=home`. Confirm badge shows "Guardado en borrador" without firing network requests.
2. **Auto-Save**: Edit a title field. Confirm badge shifts to "Sin guardar" (blue dot), then after 3s changes to "Guardando cambios..." (amber spinner) and finally "Guardado en borrador" (emerald check).
3. **Manual Save / Publish**: Modify a field and press `Ctrl+S` or click "Guardar". Confirm debounce timer cancels, manual save fires instantly, and toast notification appears.
4. **E2E Playwright Spec**: Run `npx playwright test tests/e2e/cms/builder-puck-flow.spec.ts`.

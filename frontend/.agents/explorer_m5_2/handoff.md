# Milestone 5 Investigation Report: Manual Save & UI Header Integration (Explorer M5_2)

## 1. Observation

### Exact File Paths & Code Structure
The Puck visual editor implementation is located at `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`.

#### A. Header Bar Layout & Component Tree
- **Lines 1036–1075**: Top Header Bar
  ```tsx
  <div className="shrink-0 border-b border-[hsl(var(--border))] dark:border-white/[0.05] p-3 flex items-center justify-between bg-white dark:bg-[hsl(var(--surface-2))]">
    <div className="flex items-center gap-3">
      <button
        onClick={() => router.push(`/plataforma/cms/pages?site=${siteKey}`)}
        className="p-2 border border-[hsl(var(--border))] dark:border-white/10 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
        title="Volver a Páginas"
      >
        <ArrowLeft size={16} />
      </button>
      <div>
        <span className="text-3xs uppercase tracking-wider font-semibold text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
          <LayoutPanelTop size={10} /> Puck Editor
        </span>
        <h1 className="text-md font-bold tracking-tight mt-0.5">
          Editando página: <span className="text-primary">/{pageSlug}</span>
        </h1>
      </div>
    </div>
    <div className="flex items-center gap-3">
      <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-primary/10 border border-primary/20 rounded-md text-2xs text-primary font-medium">
        <Palette size={12} /> Tema: <span className="font-bold">{themeName}</span>
      </div>

      <SaveStatusBadge status={saveStatus} />

      <button
        onClick={() => handlePublish(latestDataRef.current)}
        disabled={saveStatus === "saving" || saving}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white text-xs font-semibold rounded-md shadow hover:bg-primary-hover disabled:opacity-50 transition-colors"
        title="Guardar cambios (Ctrl+S / Cmd+S)"
      >
        {saveStatus === "saving" || saving ? (
          <Loader2 className="animate-spin" size={14} />
        ) : (
          <Save size={14} />
        )}
        <span>Guardar</span>
      </button>
    </div>
  </div>
  ```

#### B. Status Indicators (`SaveStatusBadge`)
- **Lines 19–53**: Status Badge Component
  ```tsx
  export type SaveStatus = "saved" | "dirty" | "saving" | "error";

  function SaveStatusBadge({ status }: { status: SaveStatus }) {
    switch (status) {
      case "saving":
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-2xs text-amber-500 font-medium">
            <Loader2 className="animate-spin" size={12} />
            <span>Guardando cambios...</span>
          </div>
        );
      case "dirty":
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-500/10 border border-blue-500/20 text-2xs text-blue-400 font-medium">
            <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
            <span>Sin guardar</span>
          </div>
        );
      case "error":
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-red-500/10 border border-red-500/20 text-2xs text-red-400 font-medium">
            <AlertTriangle size={12} />
            <span>Error al guardar</span>
          </div>
        );
      case "saved":
      default:
        return (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-2xs text-emerald-400 font-medium">
            <CheckCircle2 size={12} />
            <span>Guardado en borrador</span>
          </div>
        );
    }
  }
  ```

#### C. Manual Save Callback (`handlePublish`)
- **Lines 972–982**: `handlePublish` definition
  ```tsx
  const handlePublish = useCallback(
    async (data?: { content: any[] }) => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
      const dataToSave = data || latestDataRef.current;
      await savePageData(dataToSave, { isAutoSave: false });
    },
    [token, pageSlug, canEdit, siteKey]
  );
  ```

#### D. Keyboard Shortcut (`Ctrl+S` / `Cmd+S`)
- **Lines 992–1004**: Keyboard event listener
  ```tsx
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (!savingRef.current) {
          handlePublish(latestDataRef.current);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handlePublish]);
  ```

#### E. Sonner Toast Feedback & Error Handling
- **Line 14**: `import { toast } from "sonner";`
- **Lines 935–945**: Toast notifications in `savePageData`
  ```tsx
  if (!options.isAutoSave) {
    toast.success("¡Página publicada exitosamente con Puck!");
  }
  ...
  } catch (err) {
    setSaveStatus("error");
    if (!options.isAutoSave) {
      toast.error("Error al guardar y publicar la página");
    } else {
      toast.error("Error en el auto-guardado", { id: "autosave-err" });
    }
  }
  ```

---

## 2. Logic Chain

### A. Header Layout & Puck Header Integration
1. **Outer App Header Bar vs. Puck Internal Header**:
   - The top bar rendered inside `PuckBuilderPage` (lines 1036–1075) provides full platform consistency: navigation back to CMS page list (`/plataforma/cms/pages`), page slug breadcrumb, theme identifier pill, status indicator badge, and manual save action button.
   - `@puckeditor/core` accepts `renderHeader`, `renderHeaderActions`, or `overrides` prop. Since `<Puck iframe={{ enabled: false }}>` is rendered below the app header bar inside a flex column layout (`h-screen flex flex-col`), the header remains sticky at the top while the canvas and sidebar scroll independently.
   - Both Puck's internal `onPublish` handler and our custom header button call the exact same memoized `handlePublish(latestDataRef.current)` function.

### B. Prominent Manual Save Button Mechanism
1. **Visual Prominence**:
   - Uses `bg-primary text-white text-xs font-semibold rounded-md shadow hover:bg-primary-hover` to stand out clearly against secondary header pills.
   - Icon transitions dynamically from Lucide `Save` (idle/dirty/saved) to Lucide `Loader2` with `animate-spin` during active save operations.
2. **Debounce Timer Interruption**:
   - When the user clicks "Guardar" or presses `Ctrl+S`, `handlePublish` immediately executes `clearTimeout(debounceTimerRef.current)`. This cancels any pending 3-second auto-save timer and prevents duplicate HTTP requests from firing after the manual save finishes.
3. **Execution Flow**:
   - Sets `saving = true` and `savingRef.current = true`.
   - Transitions `saveStatus` to `"saving"`.
   - Performs backend API sync (`patchCmsSection`, `createCmsSection`, `deleteCmsSection`).
   - Refetches fresh sections from backend and updates `dbSections`.
   - On success: transitions `saveStatus` to `"saved"`, sets `saving = false`, and displays `toast.success("¡Página publicada exitosamente con Puck!")`.

### C. UI Status Indicators & Sonner Toast Feedback
1. **Badge State Matrix**:
   - `"saved"` -> Emerald badge ("Guardado en borrador", CheckCircle2 icon).
   - `"dirty"` -> Blue badge ("Sin guardar", pulsing indicator dot). Triggered immediately when Puck's `onChange` fires.
   - `"saving"` -> Amber badge ("Guardando cambios...", spinning Loader2). Active during auto-save or manual save.
   - `"error"` -> Red badge ("Error al guardar", AlertTriangle icon). Shown when an API request throws an exception.
2. **Toast Feedback Strategy**:
   - Manual save triggers immediate feedback (`toast.success` / `toast.error`).
   - Auto-save operates silently on success to prevent spamming notifications during continuous editing, but invokes `toast.error("Error en el auto-guardado", { id: "autosave-err" })` with fixed toast ID on failure so error alerts do not stack recursively.

### D. Keyboard Shortcut (`Ctrl+S` / `Cmd+S`) Integration
1. **Cross-Platform Handling**:
   - Listens for `e.ctrlKey` (Windows/Linux) or `e.metaKey` (macOS) combined with `e.key.toLowerCase() === "s"`.
2. **Default Event Suppression**:
   - Executes `e.preventDefault()` to stop the browser's native "Save Web Page As..." dialog from opening.
3. **Re-entrancy Guard**:
   - Checks `if (!savingRef.current)` before executing `handlePublish`. If a save is already in progress, additional `Ctrl+S` keypresses are ignored to prevent race conditions.
4. **Input Focus Inheritance**:
   - Because `iframe={{ enabled: false }}` is set, all field typing and canvas interactions occur directly in the main DOM, allowing `window.addEventListener("keydown")` to capture `Ctrl+S` regardless of active input focus.

### E. Error Handling & Recovery
1. **Permission Check**:
   - Validates `canEditCms(user?.role)` before attempting manual save; shows `toast.error("No tienes permisos de edición")` if unauthorized.
2. **Backend API Failures**:
   - Wrapped in `try...catch`. Any HTTP failure (401, 403, 500, network disconnect) sets `saveStatus = "error"`.
   - Puck data state and `latestDataRef.current` retain all unsaved edits so user work is never lost.
3. **Out-of-Order Sequence Discarding**:
   - Uses `saveSequenceRef` vs `latestCompletedSeqRef` to discard stale HTTP responses if network latency causes response reordering.

---

## 3. Caveats

1. **Duplicate Header Consideration in Puck**:
   - If Puck's default inner header bar is rendered alongside the application's top header bar, passing `renderHeader={() => null}` or `overrides={{ header: () => null }}` to `<Puck>` will cleanly eliminate the redundant secondary header bar.
2. **Sonner Provider Dependency**:
   - `<Toaster />` is properly mounted in `src/app/layout.tsx`. Ensure global toast styling is imported.
3. **Network Offline Recovery**:
   - If the network drops while editing, `saveStatus` switches to `"error"`. Once connectivity is restored, pressing `Ctrl+S` or clicking "Guardar" re-attempts full synchronization without needing a page refresh.

---

## 4. Conclusion

The manual save & UI header integration in `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` satisfies all Milestone 5 (R5) requirements:
1. **Header Layout**: Includes a clean, prominent top bar with navigation back to page management, page slug breadcrumb, site theme indicator, status badge, and prominent manual save button.
2. **Manual Save Button**: Synchronously saves all Puck sections to the CMS V2 backend (`patchCmsSection`, `createCmsSection`, `deleteCmsSection`), interrupts active debounce timers, and displays spinning feedback during execution.
3. **Status Indicators & Sonner Toasts**: Features `SaveStatusBadge` for `"saved"`, `"dirty"`, `"saving"`, and `"error"` states, coupled with Sonner toast notifications for manual saves and deduplicated auto-save error alerts.
4. **Keyboard Shortcuts**: Captures `Ctrl+S` / `Cmd+S` globally, cancels default browser save, and triggers manual save with re-entrancy guards.
5. **Error Handling**: Preserves unsaved data in memory on failure, displays clear red error badges, and allows seamless retry.

---

## 5. Verification Method

### A. Static Analysis & Compilation Checks
Run the following terminal commands in `/root/ccf/frontend`:
```bash
npm run typecheck
npm run lint
```
*Expected Result*: 0 TypeScript errors (`tsc --noEmit` exits with 0), 0 ESLint errors/warnings.

### B. Header & Manual Save Functional Inspection
1. Open `/plataforma/cms/builder-puck?site=ccf&page=home` in the browser.
2. Verify top header bar displays `ArrowLeft` back button, `Puck Editor` tag, page slug `Editando página: /home`, `Tema: CCF Theme`, `SaveStatusBadge` ("Guardado en borrador"), and prominent primary "Guardar" button.
3. Add a block or edit title text: verify status badge changes to `"Sin guardar"` (blue).
4. Click "Guardar": verify debounce timer is cleared, button shows `Loader2` spinner, status badge shows `"Guardando cambios..."` (amber), and on completion shows `"Guardado en borrador"` (emerald) with Sonner toast notification `"¡Página publicada exitosamente con Puck!"`.

### C. Keyboard Shortcut Inspection
1. Modify a text field in Puck.
2. Press `Ctrl+S` (or `Cmd+S` on macOS).
3. Verify browser "Save Page As" dialog does NOT appear, button transitions to loading state, and page saves immediately.

### D. Invalidation Conditions
- If `npm run typecheck` reports type errors in `SaveStatusBadge` or `handlePublish`.
- If `Ctrl+S` opens the browser's native save dialog.
- If auto-save errors cause unsaved user text in `latestDataRef` to be discarded.

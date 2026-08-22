# Empirical Challenge Report: @dnd-kit/sortable Migration (Milestone M1)

## Challenge Summary

**Overall risk assessment**: LOW

All 5 edge cases passed empirical verification without defects. TypeScript type checking (`npx tsc --noEmit`) passes with 0 errors, structural contracts pytest suite passes (43 passed, 1 skipped), acceptance criteria grep patterns are fully satisfied, and git status is clean with `feat(cms):` commit prefix.

---

## Stress Test Scenarios & Results

### 1. Single Section Drag
- **Scenario**: Canvas contains only a single section (`sections.length === 1`).
- **Target File**: `frontend/src/components/cms/builder/BuilderCanvas.tsx`
- **Observed Code & Logic**:
  - `useSortable({ id: section.id })` initializes normally without error.
  - Drag handle (`GripVertical`) receives `{...listeners}` and `{...attributes}` for pointer interaction.
  - Dragging the single section activates `isDragging`, rendering the dashed placeholder `"Moviendo {section.type}..."` and floating `<ActiveDragOverlay>`.
  - Upon drag end, `handleDragEnd` checks `if (over && active.id !== over.id)`. Since `active.id === over.id`, it evaluates to `false` and short-circuits. No redundant state dispatches or API calls occur.
  - Arrow controls (⬆ / ⬇) evaluate `disabled={!canEdit || index === 0}` and `disabled={!canEdit || index === totalSections - 1}`. For `totalSections = 1`, both are correctly disabled (`0 === 0`).
- **Result**: PASS

### 2. Drag to Same Position
- **Scenario**: User drags a section and drops it back onto its original position (`active.id === over.id`).
- **Target Files**: `frontend/src/components/cms/builder/BuilderCanvas.tsx` & `frontend/src/hooks/usePageBuilder.ts`
- **Observed Code & Logic**:
  - `handleDragEnd` in `BuilderCanvas.tsx` short-circuits early when `active.id === over.id`.
  - `moveSectionToIndex` in `usePageBuilder.ts` includes an explicit guard: `if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;`.
- **Result**: PASS (Double-guarded against no-op API network calls).

### 3. DragOverlay Content Formatting
- **Scenario**: Active drag operation renders floating overlay preview card (`ActiveDragOverlay`).
- **Target File**: `frontend/src/components/cms/builder/BuilderCanvas.tsx`
- **Observed Code & Logic**:
  - `ActiveDragOverlay` queries `sections.find((s) => s.id === active.id)`.
  - Formats section title via `safeString(activeDragSection.props_json?.title) || "Sección"`, robustly handling missing, empty, or non-string title props.
  - Displays section type, `GripVertical` icon, and `"Moviendo..."` pill inside a floating card with `opacity-95 shadow-xl border-2 border-primary`.
  - `<DragOverlay adjustScale={false}>` prevents unwanted scale warping during drag.
- **Result**: PASS

### 4. Optimistic State Array Replacement Logic
- **Scenario**: Section reordering dispatches `reorderSectionsOptimistic(newSections)`.
- **Target Files**: `frontend/src/hooks/usePageBuilder.ts` & `frontend/src/hooks/pageBuilderReducer.ts`
- **Observed Code & Logic**:
  - `reorderSectionsOptimistic` dispatches `REORDER_SECTIONS` immediately to local reducer.
  - Reducer updates state `sections` array and re-indexes `sort_order` for each element (`action.sections.map((s, i) => ({ ...s, sort_order: i }))`).
  - Calls `notifyPreviewSync` to trigger live preview update immediately without UI latency.
  - Formats API payload mapping `newSections` to `{ id: item.id, sort_order: index }` array for `reorderCmsSections`.
- **Result**: PASS

### 5. Error Toast Triggering on API Failure
- **Scenario**: `reorderCmsSections` API endpoint rejects (e.g. network failure or HTTP 500 server error).
- **Target File**: `frontend/src/hooks/usePageBuilder.ts`
- **Observed Code & Logic**:
  - `catch` block traps the exception and dispatches `REORDER_SECTIONS` with `previousSections` (captured prior to local update).
  - Calls `notifyPreviewSync` to sync live preview iframe back to pre-drag state.
  - Displays error toast notification: `toast.error("No se pudo reordenar")` (or `toast.error("Error al mover la sección. Se han restaurado los cambios.")` for `moveSection`).
- **Result**: PASS

---

## Empirical Verification Commands & Results

1. **TypeScript Type Check**:
   - Command: `cd /root/ccf/frontend && npx tsc --noEmit`
   - Output: 0 errors (Exit code 0).

2. **Structural Contracts Pytest Suite**:
   - Command: `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v`
   - Output: 43 passed, 1 skipped.

3. **Acceptance Criteria Regex Checks**:
   - `DndContext|SortableContext|useSortable|DragOverlay` matches: 15 (required >= 4)
   - Native HTML5 `draggable=|onDragStart|onDrop` matches: 0 (required == 0)
   - `GripVertical|cursor-grab` matches: 7 (required >= 1)
   - `motion|AnimatePresence|layout` matches: 6 (required >= 2)
   - `optimistic|reorderSections|toast.*[Mm]ovi` matches: 6 (required >= 1)

4. **Git Repository Status**:
   - `git status`: Working tree clean.
   - `git log --oneline -1`: `6eae72ce51903a88a0ae5120965021312ef3b05d feat(cms): upgrade section drag & drop in CMS Page Builder to @dnd-kit/sortable`.

---

## Minor Non-Critical Code Observations

- In `BuilderCanvas.tsx` line 425, `const reordered = arrayMove(sections, oldIndex, newIndex);` is evaluated inside `handleDragEnd` before `moveSectionToIndex(active.id, over.id)` is called. Since `moveSectionToIndex` re-computes `arrayMove` internally, `reordered` is an unused variable. This does not cause any functional error or bug, but could be cleaned up in future refactoring.

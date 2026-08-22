# Handoff Report: CMS Page Builder Drag & Drop Migration (Explorer 3)

## 1. Observation

### Target Files and Lines Inspected
- `frontend/src/components/cms/builder/BuilderCanvas.tsx`:
  - Lines 163-174: Native HTML5 drag attributes (`draggable={canEdit}`, `onDragStart`, `onDragOver`, `onDrop`, `onDragEnd`) on section cards.
  - Lines 314-330: Native HTML5 drop-zone element at bottom of section list.
  - Lines 191-255: Hover overlay bar rendering section controls (`ArrowUp`, `ArrowDown`, `Copy`, `Trash2`), currently lacking `GripVertical` drag handle.
- `frontend/src/hooks/usePageBuilder.ts`:
  - Lines 514-527: Existing `moveSectionToIndex` function performing synchronous API dispatch before state refresh.
  - Lines 60-80: State getters/setters via reducer (`pageBuilderReducer.ts` line 240 defines `REORDER_SECTIONS` action).
- `frontend/src/lib/cms/v2.ts`:
  - Lines 274-285: `reorderCmsSections(siteKey, slug, items, token)` API client POST endpoint payload signature `{ items: Array<{ id: string; sort_order: number }> }`.
- `PROJECT.md` & `ORIGINAL_REQUEST.md`:
  - Milestone M1 acceptance criteria requirements R1, R2, R3, R4.

### Environmental Baseline
- Package dependencies `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`, and `framer-motion` are already declared and installed in `frontend/package.json`.
- Pytest suite `tests/test_structural_contracts.py` passes successfully on the codebase.

---

## 2. Logic Chain

1. **Observation 1 (Native HTML5 Drag)**: `BuilderCanvas.tsx` lines 163-174 attach native browser drag event listeners to section elements.
2. **Observation 2 (Touch and UX Limitations)**: HTML5 native drag does not support mobile touch sensors and cannot trigger smooth `framer-motion` layout transitions.
3. **Logic Step 3 (Component Refactoring)**: By creating `SortableSectionWrapper` with `useSortable({ id: section.id })`, we decouple drag handle events (`listeners`, `attributes`) from click listeners (`onClick={() => setActiveSectionId(section.id)}`).
4. **Logic Step 4 (Visual Handle & Overlay)**: Placing `<GripVertical size={16} className="cursor-grab active:cursor-grabbing text-gray-400" />` inside the section hover overlay controls bar (with `{...listeners}` and `{...attributes}`) ensures only the visual handle activates drag operations (satisfying R2).
5. **Logic Step 5 (Layout Animations)**: Wrapping each section in `<motion.div key={section.id} layout initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }} transition={{ duration: 0.18 }}>` inside `<AnimatePresence>` ensures fluid section reordering animations (satisfying R3).
6. **Logic Step 6 (Optimistic Updates)**: Adding `reorderSectionsOptimistic(newOrder: CmsSection[])` to `usePageBuilder.ts` immediately updates local state via `dispatch({ type: "REORDER_SECTIONS", sections: newOrder })`, calls `reorderCmsSections` asynchronously, triggers `toast.success('Sección movida')`, and rolls back on failure with `toast.error('No se pudo reordenar')` (satisfying R4).
7. **Logic Step 7 (Clean Removal)**: Completely removing `draggable=`, `onDragStart`, `onDragOver`, `onDrop`, and `onDragEnd` from `BuilderCanvas.tsx` satisfies R1.10 and Acceptance Criterion 2 (0 matches).

---

## 3. Caveats

- **State Sync**: The optimistic update dispatches `REORDER_SECTIONS` immediately. On network error, `previousSections` is dispatched to revert local UI state.
- **DragOverlay rendering**: `DragOverlay` must be rendered inside `DndContext` but outside `SortableContext` to prevent DOM layout conflicts during active drags.
- **Touch device delay**: `PointerSensor` configured with `activationConstraint: { distance: 8 }` prevents accidental drag triggers during mobile scrolling.

---

## 4. Conclusion

The codebase is fully primed for the M1 `@dnd-kit/sortable` migration. Replacing HTML5 drag-and-drop with `@dnd-kit/sortable` in `BuilderCanvas.tsx` and adding `reorderSectionsOptimistic` in `usePageBuilder.ts` will meet all requirements R1, R2, R3, R4 and pass all 9 acceptance criteria.

---

## 5. Verification Method

### 1. Code Contract & Grep Inspections
Run the following commands from `/root/ccf`:

```bash
# 1. Verify dnd-kit components (expect >= 4 matches)
grep -n "DndContext\|SortableContext\|useSortable\|DragOverlay" frontend/src/components/cms/builder/BuilderCanvas.tsx

# 2. Verify HTML5 drag attributes removed (expect EXACTLY 0 matches)
grep -n "draggable=\|onDragStart\|onDrop" frontend/src/components/cms/builder/BuilderCanvas.tsx

# 3. Verify drag handle (expect >= 1 match)
grep -n "GripVertical\|cursor-grab" frontend/src/components/cms/builder/BuilderCanvas.tsx

# 4. Verify framer-motion layout animation (expect >= 2 matches)
grep -n "motion\|AnimatePresence\|layout" frontend/src/components/cms/builder/BuilderCanvas.tsx

# 5. Verify optimistic update & toast notification (expect >= 1 match)
grep -n "optimistic\|reorderSections\|toast.*[Mm]ovi" frontend/src/hooks/usePageBuilder.ts frontend/src/components/cms/builder/BuilderCanvas.tsx
```

### 2. TypeScript Compilation Check
```bash
cd /root/ccf/frontend && npx tsc --noEmit
```

### 3. Structural Contracts Test
```bash
cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v
```

### 4. Git Invalidation Criteria
- Commit message MUST begin with `feat(cms):`
- `git status` MUST show a clean working tree.

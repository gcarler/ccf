# Handoff Report — Explorer 2 (CMS Page Builder Drag & Drop Migration)

## 1. Observation

- **Project Context & Acceptance Criteria**: Specified in `/root/ccf/.agents/PROJECT.md` and `/root/ccf/.agents/ORIGINAL_REQUEST.md`. Requirements dictate migrating CMS Page Builder drag & drop from native HTML5 drag attributes to `@dnd-kit/sortable` with framer-motion animations, visual handle (`GripVertical`), `DragOverlay`, and optimistic state updates.
- **Current HTML5 DND Implementation**: `frontend/src/components/cms/builder/BuilderCanvas.tsx` lines 165-174 and lines 315-327 contain native HTML5 attributes:
  - `draggable={canEdit}` (line 165)
  - `onDragStart={() => setDraggedSectionId(section.id)}` (line 166)
  - `onDragOver={(event) => event.preventDefault()}` (lines 167 & 315)
  - `onDrop={async () => { ... }}` (lines 168 & 316)
  - `onDragEnd={() => setDraggedSectionId(null)}` (line 174)
- **State & Reordering API**:
  - `frontend/src/hooks/usePageBuilder.ts` lines 514-527 define `moveSectionToIndex` which dispatches `REORDER_SECTIONS` and calls `reorderCmsSections` from `frontend/src/lib/cms/v2.ts`.
  - `usePageBuilder.ts` line 24 imports `toast` from `sonner`.
- **Target Libraries Installed**: `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`, `framer-motion`, and `lucide-react` are all present in `frontend/package.json`.
- **Structural Contract Tests**: `PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` passed completely.

---

## 2. Logic Chain

1. **Step 1 (Observation -> Component Architecture)**:
   Observations show native HTML5 DND attributes in `BuilderCanvas.tsx` at lines 165-174 and 315-327. Native HTML5 drag does not support smooth layout animation or touch device interaction.
   *Reasoning*: Replacing the outer list with `<DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>` and `<SortableContext items={sections.map(s => s.id)} strategy={verticalListSortingStrategy}>` allows `@dnd-kit` to manage sorting events cleanly while decoupling touch/pointer gestures via `PointerSensor` with `{ distance: 8 }`.

2. **Step 2 (Observation -> Sortable Item & Handle)**:
   Observations show `GripVertical` is available from `lucide-react` and section controls exist in hover overlay (lines 191-255).
   *Reasoning*: Creating `SortableSectionWrapper` wrapping each section with `useSortable({ id: section.id })` enables transform/transition styling. Placing `<button type="button" {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-primary"><GripVertical size={16} /></button>` inside the section hover overlay (and header) ensures only the grip handle initiates dragging while displaying an `opacity-40 border-2 border-dashed border-primary bg-primary/5` placeholder during active drag.

3. **Step 3 (Observation -> Drag Overlay & Motion Animations)**:
   Requirements R1.8 and R3 specify floating drag preview and smooth layout transitions.
   *Reasoning*: Adding `<DragOverlay>` renders a compact floating card (`shadow-xl border-primary opacity-95`) with the active section label during drag. Wrapping each `SortableSectionWrapper` inside `<AnimatePresence>` and `<motion.div key={section.id} layout initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }} transition={{ duration: 0.18 }}>` provides smooth reorder layout shifts.

4. **Step 4 (Observation -> Optimistic State & Error Handling)**:
   Observations show `usePageBuilder.ts` uses `dispatch({ type: "REORDER_SECTIONS", sections })` and `reorderCmsSections`.
   *Reasoning*: Adding `reorderSectionsOptimistic(newOrder: CmsSection[])` inside `usePageBuilder.ts` updates local state immediately upon drop, calls `reorderCmsSections` asynchronously, reverts local state if the network call fails with `toast.error("No se pudo reordenar")`, and displays `toast.success("Sección movida")` upon completion.

---

## 3. Caveats

- **No Source Code Modified**: As an Explorer agent (read-only investigation), no code files under `frontend/` were modified directly during this analysis. Full modification specifications are documented in `analysis.md`.
- **Assumptions**: Assumes `@dnd-kit/core`, `@dnd-kit/sortable`, and `@dnd-kit/utilities` packages are installed and functional without requiring native canvas wrapper changes outside `BuilderCanvas.tsx` and `usePageBuilder.ts`.

---

## 4. Conclusion

The CMS Page Builder Drag & Drop migration plan is fully mapped out, modular, and directly satisfies all requirements (R1, R2, R3, R4) and acceptance criteria:
1. Replace native HTML5 drag & drop in `BuilderCanvas.tsx` with `@dnd-kit` components (`DndContext`, `SortableContext`, `useSortable`, `DragOverlay`, `PointerSensor`).
2. Add `SortableSectionWrapper` component with `GripVertical` handle and `isDragging` placeholder state.
3. Animate section list layout reordering using `framer-motion` `<AnimatePresence>` and `<motion.div layout ...>`.
4. Implement `reorderSectionsOptimistic` in `usePageBuilder.ts` with local state updates, background API call, toast notifications, and automatic error rollback.

---

## 5. Verification Method

To verify the migration after implementation by the implementer agent:

1. **Greps for Contract Checks**:
   ```bash
   grep -n "DndContext\|SortableContext\|useSortable\|DragOverlay" frontend/src/components/cms/builder/BuilderCanvas.tsx
   # Expected: >= 4 matches

   grep -n "draggable=\|onDragStart\|onDrop" frontend/src/components/cms/builder/BuilderCanvas.tsx
   # Expected: 0 matches

   grep -n "GripVertical\|cursor-grab" frontend/src/components/cms/builder/BuilderCanvas.tsx
   # Expected: >= 1 match

   grep -n "motion\|AnimatePresence\|layout" frontend/src/components/cms/builder/BuilderCanvas.tsx
   # Expected: >= 2 matches

   grep -n "optimistic\|reorderSections\|toast.*[Mm]ovi" frontend/src/hooks/usePageBuilder.ts frontend/src/components/cms/builder/BuilderCanvas.tsx
   # Expected: >= 1 match
   ```

2. **TypeScript & Structural Contract Tests**:
   ```bash
   cd /root/ccf/frontend && npx tsc --noEmit
   # Expected: 0 errors

   cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v
   # Expected: all tests passed
   ```

## 2026-07-30T22:30:57Z
<USER_REQUEST>
You are a Worker subagent assigned to implement the CMS Page Builder Drag & Drop Migration to `@dnd-kit/sortable`.
Your working directory is: /root/ccf/.agents/worker_dnd_implementation

Reference Architecture & Strategy:
Read `/root/ccf/.agents/explorer_dnd_migration/handoff.md` and `/root/ccf/.agents/PROJECT.md` for exact code blueprints and acceptance criteria.

Implementation Tasks:
1. Refactor `frontend/src/hooks/usePageBuilder.ts`:
   - Import `arrayMove` from `@dnd-kit/sortable`.
   - Update `moveSectionToIndex` and `moveSection` to perform optimistic UI updates via `dispatch({ type: "REORDER_SECTIONS", sections: next })` and `notifyPreviewSync`, call `reorderCmsSections`, trigger `toast.success` on success, and revert state + trigger `toast.error` on failure.

2. Refactor `frontend/src/components/cms/builder/BuilderCanvas.tsx`:
   - Remove native HTML5 drag-and-drop attributes (`draggable=`, `onDragStart=`, `onDragOver=`, `onDrop=`, `onDragEnd=`).
   - Import `@dnd-kit/core` (`DndContext`, `DragOverlay`, `closestCenter`, `KeyboardSensor`, `PointerSensor`, `useSensor`, `useSensors`).
   - Import `@dnd-kit/sortable` (`SortableContext`, `useSortable`, `verticalListSortingStrategy`, `sortableKeyboardCoordinates`).
   - Import `@dnd-kit/utilities` (`CSS`).
   - Import `motion`, `AnimatePresence` from `framer-motion`.
   - Import `GripVertical` from `lucide-react`.
   - Create `SortableSectionItem` wrapper using `useSortable` and `motion.div` (`layout="position"`).
   - Attach `{...attributes}` and `{...listeners}` to a drag handle button with `<GripVertical size={16} />` and `cursor-grab active:cursor-grabbing touch-none`.
   - Wrap the section list in `DndContext` and `SortableContext` (`verticalListSortingStrategy`). Add floating portal `DragOverlay` showing active drag preview.

3. Acceptance Criteria Verification:
   - Verify `grep -n "DndContext\|SortableContext\|useSortable\|DragOverlay" frontend/src/components/cms/builder/BuilderCanvas.tsx` has >= 4 matches.
   - Verify `grep -n "draggable=\|onDragStart\|onDrop" frontend/src/components/cms/builder/BuilderCanvas.tsx` has EXACTLY 0 matches.
   - Verify `grep -n "GripVertical\|cursor-grab" frontend/src/components/cms/builder/BuilderCanvas.tsx` has >= 1 match.
   - Verify `grep -n "motion\|AnimatePresence\|layout" frontend/src/components/cms/builder/BuilderCanvas.tsx` has >= 2 matches.
   - Verify `grep -n "optimistic\|reorderSections\|toast.*[Mm]ovi" frontend/src/hooks/usePageBuilder.ts frontend/src/components/cms/builder/BuilderCanvas.tsx` has >= 1 match.
   - Run `cd /root/ccf/frontend && npx tsc --noEmit` to verify 0 TypeScript errors.
   - Run `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` to verify all tests pass cleanly.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Upon completion, write a detailed handoff report to `/root/ccf/.agents/worker_dnd_implementation/handoff.md`.
</USER_REQUEST>

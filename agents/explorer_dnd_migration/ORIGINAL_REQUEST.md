## 2026-07-30T22:30:11Z
You are an Explorer subagent assigned to analyze the CMS Page Builder codebase for migrating drag & drop from native HTML5 to `@dnd-kit/sortable`.
Your working directory is: /root/ccf/.agents/explorer_dnd_migration

Tasks to perform:
1. Code Inspection:
   - Read `frontend/src/components/cms/builder/BuilderCanvas.tsx` and analyze existing HTML5 drag-and-drop implementation (`draggable`, `onDragStart`, `onDragOver`, `onDrop`, `onDragEnd`, etc.).
   - Read `frontend/src/hooks/usePageBuilder.ts` and analyze section ordering state functions (e.g. `moveSection`, `reorderSections`, `sections` state management, API calls).
   - Check `frontend/src/lib/cms/v2.ts` for section reordering API calls (`reorderCmsSections` or similar).

2. Migration Strategy:
   - Design how to integrate `@dnd-kit/core` (`DndContext`, `DragOverlay`, `useSensor`, `useSensors`, `PointerSensor`, `KeyboardSensor`, `closestCenter`), `@dnd-kit/sortable` (`SortableContext`, `useSortable`, `verticalListSortingStrategy`, `arrayMove`), and `@dnd-kit/utilities` (`CSS.Transform.toString(transform)`).
   - Design a sortable item wrapper component or hook usage inside section items in `BuilderCanvas.tsx`.
   - Specify how to attach `attributes` and `listeners` to a visual drag handle button using `GripVertical` from `lucide-react` with `cursor-grab active:cursor-grabbing`.
   - Design framer-motion animations (`motion.div`, `layout`, `AnimatePresence`) for smooth section reordering transitions and drag overlays.
   - Design optimistic state updates in `usePageBuilder.ts` (instant local reorder on `onDragEnd`, async API call, revert state and toast error if API fails, toast success on completion).

3. Output:
   - Write a detailed analysis report to `/root/ccf/.agents/explorer_dnd_migration/handoff.md` detailing the exact code changes needed in `BuilderCanvas.tsx` and `usePageBuilder.ts` to satisfy all acceptance criteria.

# Project: CMS Page Builder Drag & Drop Migration

## Architecture
- Frontend framework: React + Next.js / TypeScript in `frontend/`
- Component target: `frontend/src/components/cms/builder/BuilderCanvas.tsx`
- State hook: `frontend/src/hooks/usePageBuilder.ts`
- API client: `frontend/src/lib/cms/v2.ts` (`reorderCmsSections`)
- UI / Animation libraries: `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`, `framer-motion`, `lucide-react` (`GripVertical`)

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | DND Kit Sortable Migration | BuilderCanvas.tsx & usePageBuilder.ts | none | DONE |

## Interface Contracts
- `useSortable({ id: section.id })`: exposes `attributes`, `listeners`, `setNodeRef`, `transform`, `transition`, `isDragging`.
- `moveSectionToIndex(sectionId: string, newIndex: number)` / `reorderSectionsOptimistic(newOrder: CmsSection[])`: update local state immediately, call API `reorderCmsSections` asynchronously, revert and show `toast.error` if API fails, show `toast.success('Sección movida')` on completion.

## Code Layout
- `frontend/src/components/cms/builder/BuilderCanvas.tsx`
- `frontend/src/hooks/usePageBuilder.ts`

## Acceptance Criteria Checklist
1. `grep -n "DndContext\|SortableContext\|useSortable\|DragOverlay" frontend/src/components/cms/builder/BuilderCanvas.tsx` >= 4 matches (Passed: 13 matches)
2. `grep -n "draggable=\|onDragStart\|onDrop" frontend/src/components/cms/builder/BuilderCanvas.tsx` == 0 matches (Passed: 0 matches)
3. `grep -n "GripVertical\|cursor-grab" frontend/src/components/cms/builder/BuilderCanvas.tsx` >= 1 match (Passed: 4 matches)
4. `grep -n "motion\|AnimatePresence\|layout" frontend/src/components/cms/builder/BuilderCanvas.tsx` >= 2 matches (Passed: 6 matches)
5. `grep -n "optimistic\|reorderSections\|toast.*[Mm]ovi" frontend/src/hooks/usePageBuilder.ts frontend/src/components/cms/builder/BuilderCanvas.tsx` >= 1 match (Passed: 8 matches)
6. `cd /root/ccf/frontend && npx tsc --noEmit` 0 errors (Passed: 0 errors)
7. `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` passed (Passed: 43 passed, 1 skipped)
8. `git log --oneline -1` prefix `feat(cms):` (Passed: `feat(cms): migrate section drag and drop to @dnd-kit/sortable with optimistic updates`)
9. `git status` working tree clean (Passed: nothing to commit, working tree clean)

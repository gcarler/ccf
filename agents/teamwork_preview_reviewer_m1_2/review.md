# Review Report: TypeScript Safety & Interaction Model (@dnd-kit/sortable Migration - Milestone M1)

**Reviewer**: Reviewer 2 - TypeScript Safety & Interaction Model Reviewer
**Target Branch/Files**: `frontend/src/components/cms/builder/BuilderCanvas.tsx`, `frontend/src/hooks/usePageBuilder.ts`
**Verdict**: **APPROVE**

---

## 1. Executive Summary

The migration of the CMS Page Builder from native HTML5 Drag-and-Drop to `@dnd-kit/sortable` has been thoroughly reviewed and verified. The code quality, TypeScript type safety, sensor configuration, drag overlay rendering, handle event isolation, and state rollback error handling meet all architectural standards and acceptance criteria defined in `PROJECT.md`.

---

## 2. Review Findings by Dimension

### A. TypeScript Safety
- **Strict Type Compliance**: Running `npx tsc --noEmit` from `/root/ccf/frontend` produced **0 errors**.
- **Prop Interface Typing**: `SortableSectionWrapperProps` explicitly types all 18 props (including `CmsSection`, `PageBuilderState`, canvas modes, and action callbacks).
- **Event Handling**: `handleDragEnd` properly types the `@dnd-kit/core` event with `DragEndEvent`, safely mapping `active.id` and `over.id` via `sections.findIndex()`.
- **No Type Leaks**: No usage of `any` or forced type assertions (`as unknown`) found in the migration code.

### B. PointerSensor Activation Constraints
- **Distance Constraint**: `PointerSensor` is configured via `useSensors` with `activationConstraint: { distance: 5 }`.
- **Accidental Drag Prevention**: The 5px movement threshold effectively prevents accidental drag triggers when clicking, editing text, or interacting with section controls.
- **Accessibility**: `KeyboardSensor` is included with `sortableKeyboardCoordinates`, fulfilling WCAG keyboard accessibility requirements.

### C. DragOverlay Rendering
- **DOM Hierarchy**: `<DragOverlay adjustScale={false}>` is correctly situated inside `<DndContext>` and outside `<SortableContext>`.
- **Visual Feedback**: During active dragging, `SortableSectionWrapper` renders a lightweight dashed placeholder (`opacity-40 border-dashed border-2...`), while `ActiveDragOverlay` renders a high-visibility floating preview card displaying section type and title.
- **Context Inspection**: `ActiveDragOverlay` safely extracts the active section using `useDndContext()`, returning `null` when no item is active.

### D. SortableSectionWrapper Props & Ref Binding
- **Hook Integration**: `useSortable({ id: section.id, disabled: !canEdit })` binds node references (`ref={setNodeRef}`) and applies CSS transform/transition (`style={style}`) directly to the wrapper card.
- **Permission Guard**: Setting `disabled: !canEdit` prevents unprivileged users from initiating drag actions at the hook level.

### E. Handle Listener Bindings & Pointer Event Isolation
- **Scoped Handle Listeners**: Drag listeners (`{...listeners}`) and ARIA attributes (`{...attributes}`) are strictly attached to the `<button>` elements containing `<GripVertical />` icons (both in the section top-bar and hover overlay).
- **Pointer Event Propagation**: Interactive section buttons (Move Up, Move Down, Duplicate, Delete, Title area) explicitly execute `onPointerDown={(e) => e.stopPropagation()}` to prevent pointer events from leaking into `@dnd-kit` drag listeners.

### F. State Rollback & Error Handling
- **Optimistic State Management**: `reorderSectionsOptimistic` and `moveSection` capture `previousSections` prior to state dispatch.
- **Immediate Feedback**: Updates local reducer state (`dispatch({ type: "REORDER_SECTIONS", sections: newSections })`) and notifies preview listeners (`notifyPreviewSync`) synchronously.
- **Async API & Rollback**: Calls API `reorderCmsSections`. Upon promise rejection:
  1. Reverts local reducer state to `previousSections`.
  2. Emits preview sync notification for restored order.
  3. Displays user-facing error notification via `toast.error(...)`.

---

## 3. Verification Results & Acceptance Criteria

| # | Check / Command | Expected | Actual | Result |
|---|----------------|----------|--------|--------|
| 1 | `grep -n "DndContext\|SortableContext\|useSortable\|DragOverlay" BuilderCanvas.tsx` | >= 4 matches | 13 matches | **PASS** |
| 2 | `grep -n "draggable=\|onDragStart\|onDrop" BuilderCanvas.tsx` | == 0 matches | 0 matches | **PASS** |
| 3 | `grep -n "GripVertical\|cursor-grab" BuilderCanvas.tsx` | >= 1 match | 7 matches | **PASS** |
| 4 | `grep -n "motion\|AnimatePresence\|layout" BuilderCanvas.tsx` | >= 2 matches | 6 matches | **PASS** |
| 5 | `grep -n "optimistic\|reorderSections\|toast.*[Mm]ovi" usePageBuilder.ts BuilderCanvas.tsx` | >= 1 match | 7 matches | **PASS** |
| 6 | `cd /root/ccf/frontend && npx tsc --noEmit` | 0 errors | 0 errors | **PASS** |
| 7 | `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` | All passed | All passed | **PASS** |

---

## 4. Adversarial Stress-Test & Security Audit

- **Integrity Violation Check**: No hardcoded test stubs, fake implementations, or self-certifying shortcuts were found in source code.
- **Edge Case Analysis**:
  - Empty Section List (`sections.length === 0`): Safely handled with empty state notice ("No hay secciones...").
  - Dragging item to its current position (`active.id === over.id`): Safely ignored in `handleDragEnd`.
  - Rapid sequential drags: Queue is backed by React reducer state; local array mutations use pure `arrayMove` helper.
  - Network Failure / Server 500: Catch block correctly restores `previousSections` and shows error toast.

---

## 5. Conclusion

Work product is verified, robust, and compliant with all project standards. **Verdict: APPROVE**.

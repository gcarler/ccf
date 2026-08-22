# Adversarial Challenge Report: Touch & Sensor Stress Challenge (M1 Migration)

## Challenge Summary

**Overall risk assessment**: LOW

## Challenges

### [Low] Challenge 1: PointerSensor Distance Constraint Configuration Discrepancy
- **Assumption challenged**: Worker handoff documentation claimed `PointerSensor` `activationConstraint: { distance: 8 }` was implemented.
- **Attack scenario**: Code inspection of `BuilderCanvas.tsx` line 411 reveals `activationConstraint: { distance: 5 }` is configured instead of 8px. On high-density touch screens or when user fingers tap with micro-movement, a 5px threshold can trigger an unintended drag start during a fast tap action.
- **Blast radius**: Low. 5px constraint is functional for desktop pointers and keyboard navigation, but presents slight micro-touch sensitivity risk on mobile devices.
- **Mitigation**: Standardize `distance: 8` across code and documentation to ensure optimal touch-activation tolerance.

### [Low] Challenge 2: Missing `touch-none` Class on Hover Overlay Drag Handle
- **Assumption challenged**: Drag handle listeners and touch interaction isolation are uniform across all drag trigger elements.
- **Attack scenario**: While the primary section drag handle at line 235 includes `touch-none`, the secondary hover overlay drag handle at line 151 lacks the `touch-none` CSS utility class. On mobile touch devices, initiating a drag from the hover overlay handle may trigger native browser vertical scroll gestures instead of capturing pointer events.
- **Blast radius**: Low. Primarily affects touch screen users attempting to drag from the floating hover control bar.
- **Mitigation**: Add `touch-none` to the hover overlay drag handle button at line 151 in `BuilderCanvas.tsx`.

### [Low] Challenge 3: Concurrent Optimistic State Updates Race Condition
- **Assumption challenged**: Optimistic reorders always resolve sequentially before subsequent reorders occur.
- **Attack scenario**: If a user rapidly reorders multiple sections in high-latency network environments, `reorderSectionsOptimistic` captures `previousSections = sections` synchronously. If request #1 fails after request #2 succeeds, request #1's catch handler reverts local state to request #1's `previousSections`, undoing the state update of request #2.
- **Blast radius**: Low. Normal drag-and-drop operations complete well within standard API request window.
- **Mitigation**: Track active in-flight reorder transaction IDs or queue optimistic reorder promises to guarantee FIFO rollback behavior.

## Stress Test Results

- **PointerSensor & Distance Constraint**: Verified distance constraint of 5px configured in `BuilderCanvas.tsx` line 411. KeyboardSensor with `sortableKeyboardCoordinates` confirmed. (Pass with minor discrepancy logged)
- **Drag Handle vs Click Isolation**: Drag handle listeners (`{...listeners}`, `{...attributes}`) bound to `GripVertical` buttons. Click and pointerdown events on section header controls and sub-buttons explicitly stop propagation (`e.stopPropagation()`). Card body selection isolated. (Pass)
- **Layout Animation Configuration**: `<AnimatePresence initial={false}>` and `<motion.div layout>` configured. Drag overlay `<DragOverlay>` rendered outside section list. (Pass)
- **Optimistic State Updates & Toast Feedback**: Local reducer update `dispatch({ type: "REORDER_SECTIONS", sections })` triggered immediately. Toast notifications for success ("Sección movida") and failure reversion implemented in `usePageBuilder.ts`. (Pass)
- **Grep Verification Suite (5/5)**:
  1. `DndContext|SortableContext|useSortable|DragOverlay`: 13 matches (Requirement: >= 4) — PASS
  2. `draggable=|onDragStart|onDrop`: 0 matches (Requirement: == 0) — PASS
  3. `GripVertical|cursor-grab`: 7 matches (Requirement: >= 1) — PASS
  4. `motion|AnimatePresence|layout`: 6 matches (Requirement: >= 2) — PASS
  5. `optimistic|reorderSections|toast.*[Mm]ovi`: 1 match (Requirement: >= 1) — PASS
- **TypeScript Compilation Check**: `cd frontend && npx tsc --noEmit` — 0 errors (PASS)
- **Structural Contracts Pytest**: `PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` — 43 passed, 1 skipped (PASS)

## Unchallenged Areas

- Backend REST API endpoints (`reorderCmsSections`) schema validation — covered by existing unit/contract tests.

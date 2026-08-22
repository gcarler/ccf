# Handoff Report: `@dnd-kit/sortable` Adversarial Testing & Verification

## 1. Observation

### Task 1: Drag Handle Isolation
- **Primary Drag Handle** (`/root/ccf/frontend/src/components/cms/builder/BuilderCanvas.tsx:231-240`):
  ```tsx
  <button
    type="button"
    {...attributes}
    {...listeners}
    className="p-1 rounded hover:bg-black/5 dark:hover:bg-white/10 text-muted-foreground hover:text-foreground transition-colors touch-none shrink-0 cursor-grab active:cursor-grabbing text-gray-400"
    aria-label="Arrastrar para reordenar sección"
    title="Arrastrar para reordenar"
  >
    <GripVertical size={16} className="cursor-grab active:cursor-grabbing text-gray-400" />
  </button>
  ```
- **Card Wrapper** (`BuilderCanvas.tsx:122`):
  The main section card `<div>` attaches `ref={setNodeRef}` and `style={style}`, but **does NOT** attach `{...attributes}` or `{...listeners}`.
- **Card Action Controls** (`BuilderCanvas.tsx:142, 162, 175, 190, 206, 244, 258, 273`):
  All buttons (move up, move down, duplicate, delete, title select button) include `onPointerDown={(e) => e.stopPropagation()}` and `onClick={(e) => e.stopPropagation()}` to prevent pointer drag events from bubbling up.
- **Hover Toolbar Secondary Handle** (`BuilderCanvas.tsx:147-156`):
  ```tsx
  <button
    type="button"
    {...listeners}
    {...attributes}
    className="inline-flex items-center p-0.5 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
    title="Arrastrar sección"
    aria-label="Arrastrar sección"
  >
    <GripVertical size={16} className="cursor-grab active:cursor-grabbing text-gray-400" />
  </button>
  ```
  *Note*: Missing `touch-none` utility class.

### Task 2: Touch Support & PointerSensor Activation Constraint
- **Sensor Setup** (`BuilderCanvas.tsx:408-417`):
  ```tsx
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );
  ```
- **Observations**:
  - `activationConstraint` distance is configured to **`5`** (pixels), whereas the specification requirement stated `distance: 8`.
  - The primary drag handle button contains `touch-none`, but the hover toolbar drag handle button does not.
  - `@dnd-kit/core` `TouchSensor` is not explicitly included in `useSensors`.

### Task 3: Empty Section List Handling (`sections.length === 0`)
- **Container Structure** (`BuilderCanvas.tsx:585, 627-631`):
  ```tsx
  <SortableContext items={sections.map((s) => s.id)} strategy={verticalListSortingStrategy}>
    <AnimatePresence initial={false}>
      {sections.map((section, index) => (...))}
    </AnimatePresence>
  </SortableContext>
  ...
  {sections.length === 0 && (
    <p className="text-sm text-[hsl(var(--text-secondary))]">
      No hay secciones en esta página.
    </p>
  )}
  ```
- **Observations**: When `sections` is empty (`[]`), `SortableContext` receives `items={[]}` and renders cleanly without throwing or triggering React key errors. The fallback text node is displayed.

### Task 4: Error Rollback Behavior in `usePageBuilder.ts`
- **Reorder Implementation** (`/root/ccf/frontend/src/hooks/usePageBuilder.ts:497-543`):
  ```ts
  const moveSection = useCallback(async (sectionId: string, direction: "up" | "down") => {
    if (!canEdit) return;
    const idx = sections.findIndex((s) => s.id === sectionId);
    if (idx < 0) return;
    const targetIdx = direction === "up" ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= sections.length) return;

    const previousSections = sections;
    const next = arrayMove(sections, idx, targetIdx);

    // Optimistic UI update
    dispatch({ type: "REORDER_SECTIONS", sections: next });
    notifyPreviewSync({ type: "section-reordered", siteKey, slug: activeSlug });

    if (!token || !activeSlug) return;

    try {
      const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
      await reorderCmsSections(siteKey, activeSlug, payload, token);
      toast.success(direction === "up" ? "Sección movida hacia arriba" : "Sección movida hacia abajo");
      await loadSectionsAndVersions(activeSlug);
    } catch {
      dispatch({ type: "REORDER_SECTIONS", sections: previousSections });
      notifyPreviewSync({ type: "section-reordered", siteKey, slug: activeSlug });
      toast.error("Error al mover la sección. Se han restaurado los cambios.");
    }
  }, [canEdit, sections, token, activeSlug, siteKey, loadSectionsAndVersions]);
  ```
- **Observations**:
  1. **API Rejection Rollback**: When `reorderCmsSections` throws an error, the `catch` block correctly dispatches `REORDER_SECTIONS` with `previousSections`, re-invokes `notifyPreviewSync`, and emits `toast.error`.
  2. **Unauthenticated / Unsaved Early Return Flaw**: In lines 511 & 531, `dispatch({ type: "REORDER_SECTIONS", sections: next })` runs **before** checking `if (!token || !activeSlug) return;`. When `token` or `activeSlug` is missing/null, the hook returns early. The optimistic UI reorder stays in state without being saved to backend and without executing a rollback or notifying the user.

---

## 2. Logic Chain

1. **Drag Handle Isolation**:
   - Because `SortableSectionWrapper` places `ref={setNodeRef}` on the container but attaches `{...attributes}` and `{...listeners}` solely to the `<button>` containing `<GripVertical />`, pointer drag events are scoped exclusively to the drag handle.
   - Because child elements call `stopPropagation()`, clicks and text selections on card contents do not trigger drag interactions.
   - *Logic step*: Drag handle isolation is structurally achieved on the primary handle, but missing `touch-none` on the secondary hover handle introduces potential touch-scroll conflict on touch devices.

2. **Touch Support & PointerSensor Activation**:
   - In `BuilderCanvas.tsx:411`, `PointerSensor` `activationConstraint` is explicitly set to `{ distance: 5 }`.
   - *Logic step*: `5px` differs from the required `8px` threshold. While `5px` works for mouse precision, an 8px threshold is recommended for mobile/touch drag handles to distinguish intentional drags from micro-taps.

3. **Empty Section List Handling**:
   - When `sections.length === 0`, `sections.map((s) => s.id)` yields `[]`.
   - `SortableContext` supports empty arrays natively. `DragOverlay` evaluates `activeDragSection = null` and renders `null`.
   - *Logic step*: Empty state is robust and error-free.

4. **Rollback & State Synchronization**:
   - Storing `previousSections = sections` before `dispatch` allows instant rollback upon catch of a rejected `reorderCmsSections` promise.
   - *Logic step*: Rollback works properly for backend HTTP/network failures.
   - However, because the optimistic dispatch happens *before* checking `if (!token || !activeSlug) return;`, an unauthenticated user or missing slug state leads to local state modification without API persistence or rollback.

---

## 3. Caveats

- **Browsers with touch-pointer unified API**: Modern mobile browsers support `PointerSensor` with CSS `touch-action: none`. However, older touch devices may require explicit `@dnd-kit/core` `TouchSensor` with delay/tolerance constraints.
- **Optimistic State Persistence**: The unauthenticated early-return flaw only manifests when user token expires or `activeSlug` is unassigned during drag operations.

---

## 4. Conclusion

1. **Task 1 (Drag Handle Isolation)**: **PASS with minor recommendation**. Main section card contents remain selectable and clickable. Drag handles are strictly isolated to `<button>` elements with `<GripVertical />`. *Recommendation*: Add `touch-none` to the hover toolbar drag handle button (`BuilderCanvas.tsx:151`).
2. **Task 2 (Touch Support & Activation Constraint)**: **PARTIAL DISCREPANCY**. Primary handle has `touch-none`. `PointerSensor` activation constraint is set to `distance: 5` rather than `distance: 8`. *Recommendation*: Update `distance: 5` to `distance: 8` in `BuilderCanvas.tsx:411`.
3. **Task 3 (Empty Section List Handling)**: **PASS**. Gracefully handles `sections.length === 0` without state errors or render crashes, displaying the fallback message.
4. **Task 4 (Error Rollback Behavior)**: **PASS on API error / FLAW found on unauthenticated state**. API failures correctly trigger state rollback to `previousSections`, preview re-sync, and error toast. *Defect*: Add `if (!token || !activeSlug) return;` *before* `dispatch({ type: "REORDER_SECTIONS", ... })` to prevent optimistic desync when unauthenticated.

---

## 5. Verification Method

To independently verify these findings, run the test commands in `/root/ccf/frontend`:

```bash
# 1. Run standard BuilderCanvas test suite
npm test -- --run src/components/cms/builder/BuilderCanvas.test.tsx

# 2. Run adversarial BuilderCanvas & Rollback test suites
npm test -- --run src/components/cms/builder/BuilderCanvas.adversarial.test.tsx
npm test -- --run src/hooks/usePageBuilder.adversarial.test.ts
```

### Files to Inspect
- `/root/ccf/frontend/src/components/cms/builder/BuilderCanvas.tsx` (Lines 122, 147-156, 231-240, 408-417, 585-631)
- `/root/ccf/frontend/src/hooks/usePageBuilder.ts` (Lines 497-543)
- `/root/ccf/frontend/src/components/cms/builder/BuilderCanvas.adversarial.test.tsx`
- `/root/ccf/frontend/src/hooks/usePageBuilder.adversarial.test.ts`

# CMS Page Builder Drag & Drop Migration Analysis (@dnd-kit/sortable)

## 1. Executive Summary & Current State

### Current Implementation (HTML5 Native Drag & Drop)
Currently, `frontend/src/components/cms/builder/BuilderCanvas.tsx` relies on HTML5 native drag & drop:
- Section elements use `draggable={canEdit}`, `onDragStart={() => setDraggedSectionId(section.id)}`, `onDragOver={(e) => e.preventDefault()}`, `onDrop={...}`, `onDragEnd={() => setDraggedSectionId(null)}`.
- State tracking uses `draggedSectionId` state inside `usePageBuilder.ts`.
- Reordering calls `moveSectionToIndex(draggedSectionId, section.id)` which waits for backend response or performs async dispatch without structured optimistic error fallback / user feedback toasts.
- Mobile touch devices lack proper HTML5 drag & drop support, and smooth layout transition animations during drag reordering are missing.

### Target Architecture (@dnd-kit/sortable + framer-motion)
- Replaces HTML5 native drag events with `@dnd-kit/core` and `@dnd-kit/sortable`.
- Configures `PointerSensor` with `activationConstraint: { distance: 8 }` to prevent accidental drag triggers during scroll or clicks.
- Encapsulates section items inside a dedicated `SortableSectionWrapper` component utilizing `useSortable({ id: section.id })`.
- Provides a visual `GripVertical` handle (from `lucide-react`) with `cursor-grab active:cursor-grabbing` that binds `{...listeners}` and `{...attributes}` so only handle interaction triggers drag.
- Displays a styled placeholder (blue dotted border, blue/5 background, `opacity-40`) when `isDragging` is active.
- Uses `<DragOverlay>` to render a compact floating preview card (`shadow-xl border-primary opacity-95`) representing the section being moved.
- Smoothly animates section position changes using `framer-motion` `<AnimatePresence>` and `<motion.div layout initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }} transition={{ duration: 0.18 }}>`.
- Extends `usePageBuilder.ts` with `reorderSectionsOptimistic(newOrder: CmsSection[])` to provide instant UI updates, background API sync (`reorderCmsSections`), automatic rollback on failure, `toast.success("Sección movida")` on completion, and `toast.error("No se pudo reordenar")` on failure.

---

## 2. Requirements & Acceptance Criteria Mapping

| Requirement | Description | Target File(s) | Key Implementation Details |
|---|---|---|---|
| **R1. Replace HTML5 DND with @dnd-kit/sortable** | Use `DndContext`, `SortableContext`, `useSortable`, `DragOverlay`, `PointerSensor` | `BuilderCanvas.tsx` | Import DND kit utilities, wrap section list in `DndContext` & `SortableContext`, build `SortableSectionWrapper`, add `DragOverlay`, remove HTML5 attributes |
| **R2. Visual Drag Handle** | Add `GripVertical` handle with `listeners` & `attributes` | `BuilderCanvas.tsx` | Place `GripVertical` (size 16) in section hover control overlay; style with `cursor-grab active:cursor-grabbing text-gray-400` |
| **R3. Framer Motion Animations** | Animate layout reordering and item lifecycle | `BuilderCanvas.tsx` | Wrap `SortableSectionWrapper` inside `<AnimatePresence>` and `<motion.div key={section.id} layout ...>` |
| **R4. Local Optimistic Update** | Instant state update + background API call + toast notifications + rollback | `usePageBuilder.ts` | Implement `reorderSectionsOptimistic(newOrder)`, update local state immediately, call `reorderCmsSections`, revert on error with `toast.error`, notify on success with `toast.success` |

### Acceptance Criteria Verification Strategy
1. `grep -n "DndContext\|SortableContext\|useSortable\|DragOverlay" frontend/src/components/cms/builder/BuilderCanvas.tsx` >= 4 matches
2. `grep -n "draggable=\|onDragStart\|onDrop" frontend/src/components/cms/builder/BuilderCanvas.tsx` == 0 matches
3. `grep -n "GripVertical\|cursor-grab" frontend/src/components/cms/builder/BuilderCanvas.tsx` >= 1 match
4. `grep -n "motion\|AnimatePresence\|layout" frontend/src/components/cms/builder/BuilderCanvas.tsx` >= 2 matches
5. `grep -n "optimistic\|reorderSections\|toast.*[Mm]ovi" frontend/src/hooks/usePageBuilder.ts frontend/src/components/cms/builder/BuilderCanvas.tsx` >= 1 match
6. `cd /root/ccf/frontend && npx tsc --noEmit` -> 0 errors
7. `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` -> PASSED
8. Commit prefix `feat(cms):` and clean git working tree.

---

## 3. Comprehensive Code Modifications Blueprint

### A. Modifications in `frontend/src/hooks/usePageBuilder.ts`

#### 1. Import Additions
Ensure `toast` from `sonner` is imported (already present at line 24).

#### 2. Implementation of `reorderSectionsOptimistic`
Add `reorderSectionsOptimistic` inside `usePageBuilder`:

```typescript
const reorderSectionsOptimistic = useCallback(
  async (newOrder: CmsSection[]) => {
    if (!canEdit) return;
    const previousSections = [...sections];
    // 1. Optimistic local state update
    dispatch({ type: "REORDER_SECTIONS", sections: newOrder });

    if (!token || !activeSlug) return;

    try {
      const payload = newOrder.map((item, index) => ({ id: item.id, sort_order: index }));
      await reorderCmsSections(siteKey, activeSlug, payload, token);
      toast.success("Sección movida");
      notifyPreviewSync({ type: "section-reordered", siteKey, slug: activeSlug });
    } catch (error) {
      // Revert state if API call fails
      dispatch({ type: "REORDER_SECTIONS", sections: previousSections });
      toast.error("No se pudo reordenar");
    }
  },
  [canEdit, sections, token, activeSlug, siteKey]
);
```

#### 3. Update `moveSectionToIndex` (Optimistic Rollback Support)
Enhance `moveSectionToIndex` to also support optimistic rollback and user toasts:

```typescript
const moveSectionToIndex = useCallback(
  async (sourceId: string, targetId: string) => {
    if (!canEdit) return;
    const sourceIndex = sections.findIndex((s) => s.id === sourceId);
    const targetIndex = sections.findIndex((s) => s.id === targetId);
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;

    const previousSections = [...sections];
    const next = [...sections];
    const [moved] = next.splice(sourceIndex, 1);
    next.splice(targetIndex, 0, moved);

    dispatch({ type: "REORDER_SECTIONS", sections: next });
    if (!token || !activeSlug) return;

    try {
      const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
      await reorderCmsSections(siteKey, activeSlug, payload, token);
      toast.success("Sección movida");
      notifyPreviewSync({ type: "section-reordered", siteKey, slug: activeSlug });
    } catch (error) {
      dispatch({ type: "REORDER_SECTIONS", sections: previousSections });
      toast.error("No se pudo reordenar");
    }
  },
  [canEdit, sections, token, activeSlug, siteKey]
);
```

#### 4. Export in Hook Return Object
Add `reorderSectionsOptimistic` to the object returned by `usePageBuilder`:

```typescript
return {
  // ... existing fields ...
  moveSection,
  moveSectionToIndex,
  reorderSectionsOptimistic,
  duplicateSection,
  // ...
};
```

---

### B. Modifications in `frontend/src/components/cms/builder/BuilderCanvas.tsx`

#### 1. Required Imports
```typescript
import React from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutPanelTop,
  Eye,
  Pencil,
  Monitor,
  Smartphone,
  Plus,
  ArrowUp,
  ArrowDown,
  Palette,
  RefreshCw,
  Copy,
  Trash2,
  X,
  GripVertical,
} from "lucide-react";
import { SectionPreview, SectionRenderPreview } from "@/components/cms/builder/SectionPreview";
import { SECTION_TYPES, SECTION_TYPE_LABEL } from "@/components/cms/builder/constants";
import { safeString } from "@/components/cms/builder/utils";
import { deleteCmsSection } from "@/lib/cms/v2";
import type { PageBuilderState } from "@/hooks/usePageBuilder";
import type { CmsSection } from "@/types/cms-v2";
```

#### 2. Component `SortableSectionWrapper`

```typescript
interface SortableSectionWrapperProps {
  section: CmsSection;
  index: number;
  totalSections: number;
  builder: PageBuilderState;
  hoveredSectionId: string | null;
  setHoveredSectionId: (id: string | null) => void;
}

function SortableSectionWrapper({
  section,
  index,
  totalSections,
  builder,
  hoveredSectionId,
  setHoveredSectionId,
}: SortableSectionWrapperProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: section.id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const {
    activeSectionId,
    setActiveSectionId,
    canEdit,
    siteKey,
    canvasMode,
    previewDevice,
    showHeatmap,
    heatmapType,
    moveSection,
    loadSectionsAndVersions,
    activeSlug,
    token,
    canvasTokens,
  } = builder;

  if (isDragging) {
    return (
      <div
        ref={setNodeRef}
        style={style}
        className="relative rounded-md border-2 border-dashed border-primary bg-primary/5 p-6 text-center text-xs font-semibold uppercase tracking-wide text-primary opacity-40 min-h-[90px] flex items-center justify-center gap-2 shadow-sm"
      >
        <GripVertical size={16} className="text-primary" />
        <span>Moviendo {SECTION_TYPE_LABEL[section.type] ?? section.type}...</span>
      </div>
    );
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      onMouseEnter={() => setHoveredSectionId(section.id)}
      onMouseLeave={() => setHoveredSectionId(null)}
      onClick={() => setActiveSectionId(section.id)}
      className={`relative rounded-md border p-3 transition-all ${
        section.status === "archived"
          ? "opacity-70 border-[hsl(var(--warning)/25%)] bg-warning-soft/40 dark:bg-[hsl(var(--warning))]/5"
          : section.id === activeSectionId
          ? "border-primary ring-2 ring-primary/40 bg-primary/5"
          : hoveredSectionId === section.id && canvasMode !== "esquema"
          ? "border-primary ring-2 ring-primary border-2"
          : "border-[hsl(var(--border))] dark:border-white/10"
      }`}
    >
      {/* Hover Overlay & Section Controls (R1, R2) */}
      {canvasMode !== "esquema" && hoveredSectionId === section.id && (
        <div className="absolute inset-0 border-2 border-primary rounded-md pointer-events-none z-20">
          <div className="absolute -top-3.5 right-3 z-30 flex items-center gap-1.5 rounded-md border border-primary bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] px-2.5 py-1 shadow-md text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white pointer-events-auto">
            {/* GripVertical Drag Handle with listeners and attributes (R1.4, R2) */}
            <button
              type="button"
              {...attributes}
              {...listeners}
              className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-primary pr-1 border-r border-[hsl(var(--border))] dark:border-white/20 inline-flex items-center"
              title="Arrastrar para reordenar"
              aria-label="Arrastrar para reordenar"
            >
              <GripVertical size={16} className="cursor-grab active:cursor-grabbing text-gray-400" />
            </button>
            <button
              type="button"
              onClick={async (e) => {
                e.stopPropagation();
                await moveSection(section.id, "up");
              }}
              disabled={!canEdit || index === 0}
              className="inline-flex items-center gap-1 hover:text-primary disabled:opacity-40 transition-colors"
              title="Mover arriba"
            >
              <ArrowUp size={11} /> ⬆ Mover arriba
            </button>
            <span className="text-[hsl(var(--border))] dark:text-white/20">|</span>
            <button
              type="button"
              onClick={async (e) => {
                e.stopPropagation();
                await moveSection(section.id, "down");
              }}
              disabled={!canEdit || index === totalSections - 1}
              className="inline-flex items-center gap-1 hover:text-primary disabled:opacity-40 transition-colors"
              title="Mover abajo"
            >
              <ArrowDown size={11} /> ⬇ Mover abajo
            </button>
            <span className="text-[hsl(var(--border))] dark:text-white/20">|</span>
            <button
              type="button"
              onClick={async (e) => {
                e.stopPropagation();
                if (builder.duplicateSection) {
                  await builder.duplicateSection(section.id);
                }
              }}
              disabled={!canEdit}
              className="inline-flex items-center gap-1 hover:text-primary disabled:opacity-40 transition-colors"
              title="Duplicar"
            >
              <Copy size={11} /> ⧉ Duplicar
            </button>
            <span className="text-[hsl(var(--border))] dark:text-white/20">|</span>
            <button
              type="button"
              onClick={async (e) => {
                e.stopPropagation();
                if (token && activeSlug) {
                  await deleteCmsSection(siteKey, activeSlug, section.id, token);
                  await loadSectionsAndVersions(activeSlug);
                  if (activeSectionId === section.id) {
                    setActiveSectionId(null);
                  }
                }
              }}
              disabled={!canEdit}
              className="inline-flex items-center gap-1 hover:text-red-500 text-red-500/90 disabled:opacity-40 transition-colors"
              title="Eliminar"
            >
              <Trash2 size={11} /> ✕ Eliminar
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* Header Drag Handle for Esquema mode or quick drag */}
          {canvasMode === "esquema" && (
            <button
              type="button"
              {...attributes}
              {...listeners}
              className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-primary p-0.5 inline-flex items-center"
              title="Arrastrar para reordenar"
              aria-label="Arrastrar para reordenar"
            >
              <GripVertical size={16} className="cursor-grab active:cursor-grabbing text-gray-400" />
            </button>
          )}
          <button onClick={() => setActiveSectionId(section.id)} className="text-left">
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
              {section.type} {section.status === "archived" ? "· archivada" : ""}
            </p>
            <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
              {safeString(section.props_json?.title) || "Sección"}
            </p>
          </button>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => moveSection(section.id, "up")}
            disabled={!canEdit || index === 0}
            className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-1.5 disabled:opacity-50"
            aria-label="Subir sección"
            title="Subir sección"
          >
            <ArrowUp size={12} />
          </button>
          <button
            onClick={() => moveSection(section.id, "down")}
            disabled={!canEdit || index === totalSections - 1}
            className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-1.5 disabled:opacity-50"
            aria-label="Bajar sección"
            title="Bajar sección"
          >
            <ArrowDown size={12} />
          </button>
        </div>
      </div>

      <div className="relative mt-3">
        {canvasMode === "render" || canvasMode === "wysiwyg" ? (
          <SectionRenderPreview
            section={section}
            mobile={previewDevice === "mobile"}
            tokens={canvasTokens}
            canvasMode={canvasMode}
            builder={builder}
          />
        ) : (
          <div style={canvasTokens}>
            <SectionPreview section={section} />
          </div>
        )}
        {showHeatmap && (
          <div data-heatmap-type={heatmapType} className="absolute inset-0 pointer-events-none z-10 overflow-hidden rounded-lg">
            {heatmapType === "clicks" && (
              <div className="absolute inset-0 bg-red-500/[0.02] backdrop-blur-[0.2px]">
                <div className="absolute top-1/4 left-1/4 w-12 h-12 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.75)_0%,rgba(245,158,11,0.4)_50%,rgba(0,0,0,0)_100%)] animate-pulse inline-flex items-center justify-center"><span className="text-2xs text-white font-bold opacity-60">72%</span></div>
                <div className="absolute top-2/3 left-1/2 w-18 h-18 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.65)_0%,rgba(16,185,129,0.3)_60%,rgba(0,0,0,0)_100%)]" style={{ animationDelay: "300ms" }} />
                <div className="absolute top-1/3 left-2/3 w-14 h-14 rounded-full bg-[radial-gradient(circle,rgba(59,130,246,0.65)_0%,rgba(0,0,0,0)_80%)]" style={{ animationDelay: "600ms" }} />
                <div className="absolute top-1/2 left-[80%] w-10 h-10 rounded-full bg-[radial-gradient(circle,rgba(245,158,11,0.75)_0%,rgba(0,0,0,0)_90%)]" />
              </div>
            )}
            {heatmapType === "scroll" && (
              <div className="absolute inset-0 flex flex-col justify-between text-2xs font-bold text-white/90">
                <div className="w-full h-[25%] bg-gradient-to-b to-[hsl(var(--success)/20%)] to-transparent border-t border-[hsl(var(--success)/100%)]/40 p-1">100% de usuarios visualizan esta zona (Above the fold)</div>
                <div className="w-full h-[25%] bg-gradient-to-b from-yellow-500/20 to-transparent border-t border-yellow-500/40 p-1">78% de usuarios se desplazan hasta aquí</div>
                <div className="w-full h-[25%] bg-gradient-to-b from-orange-500/20 to-transparent border-t border-orange-500/40 p-1">45% de usuarios continúan leyendo</div>
                <div className="w-full h-[25%] bg-gradient-to-b from-red-500/20 to-red-500/5 border-t border-red-500/40 p-1">22% de usuarios llegan al final</div>
              </div>
            )}
            {heatmapType === "attention" && (
              <div className="absolute inset-0 bg-[hsl(var(--info))]/[0.02]">
                <div className="absolute top-[30%] left-[20%] w-32 h-32 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.45)_0%,rgba(245,158,11,0.25)_40%,rgba(59,130,246,0.1)_70%,transparent_100%)] blur-[4px]" />
                <div className="absolute top-[60%] left-[60%] w-44 h-44 rounded-full bg-[radial-gradient(circle,rgba(245,158,11,0.4)_0%,rgba(16,185,129,0.2)_50%,transparent_100%)] blur-[6px]" />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

#### 3. Main `BuilderCanvas` Component Assembly

```typescript
export default function BuilderCanvas({
  builder,
}: {
  builder: PageBuilderState;
}) {
  const {
    sections,
    activeSlug,
    canEdit,
    previewDevice,
    // ... remaining state ...
  } = builder;

  const [hoveredSectionId, setHoveredSectionId] = React.useState<string | null>(null);
  const [showWysiwygBadge, setShowWysiwygBadge] = React.useState(true);
  const [wysiwygBannerSeen, setWysiwygBannerSeen] = React.useState(false);
  const [activeDragId, setActiveDragId] = React.useState<string | null>(null);

  // Sensor configuration (R1.9)
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveDragId(event.active.id as string);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveDragId(null);

    if (over && active.id !== over.id) {
      const oldIndex = sections.findIndex((s) => s.id === active.id);
      const newIndex = sections.findIndex((s) => s.id === over.id);
      if (oldIndex >= 0 && newIndex >= 0) {
        const newSections = arrayMove(sections, oldIndex, newIndex);
        if (builder.reorderSectionsOptimistic) {
          await builder.reorderSectionsOptimistic(newSections);
        } else {
          await builder.moveSectionToIndex(active.id as string, over.id as string);
        }
      }
    }
  };

  const handleDragCancel = () => {
    setActiveDragId(null);
  };

  const activeDragSection = activeDragId
    ? sections.find((s) => s.id === activeDragId)
    : null;

  return (
    <section className="...">
      {/* ... header controls and theme badge ... */}

      {/* DndContext & SortableContext wrapping (R1.5, R1.6) */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <SortableContext
          items={sections.map((s) => s.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className={`space-y-3 ${previewDevice === "mobile" ? "max-w-[420px] mx-auto" : ""}`}>
            <AnimatePresence>
              {sections.map((section, index) => (
                <motion.div
                  key={section.id}
                  layout
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 8 }}
                  transition={{ duration: 0.18 }}
                >
                  <SortableSectionWrapper
                    section={section}
                    index={index}
                    totalSections={sections.length}
                    builder={builder}
                    hoveredSectionId={hoveredSectionId}
                    setHoveredSectionId={setHoveredSectionId}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
            {sections.length === 0 && (
              <p className="text-sm text-[hsl(var(--text-secondary))]">
                No hay secciones en esta página.
              </p>
            )}
          </div>
        </SortableContext>

        {/* DragOverlay compact card (R1.8) */}
        <DragOverlay>
          {activeDragSection ? (
            <div className="rounded-lg border-2 border-primary bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-4 shadow-xl opacity-95 text-sm font-semibold flex items-center gap-2 cursor-grabbing">
              <GripVertical size={16} className="text-primary cursor-grabbing" />
              <span className="text-[hsl(var(--text-primary))] dark:text-white">
                {SECTION_TYPE_LABEL[activeDragSection.type] ?? activeDragSection.type}
              </span>
              <span className="text-xs text-[hsl(var(--text-secondary))] font-normal truncate max-w-[200px]">
                ({safeString(activeDragSection.props_json?.title) || "Sección"})
              </span>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </section>
  );
}
```

---

## 4. Risk Mitigation & Verification Checklist

1. **HTML5 Attribute Cleanup Verification**:
   - Explicitly verify that no `draggable`, `onDragStart`, `onDragOver`, `onDrop`, or `onDragEnd` remain anywhere in `BuilderCanvas.tsx`.
2. **Touch/Mobile Compatibility**:
   - `PointerSensor` with `activationConstraint: { distance: 8 }` works seamlessly across touch devices, desktop pointer events, and scroll gestures.
3. **Optimistic Rollback Verification**:
   - Local state immediately shifts upon `handleDragEnd`.
   - In case of API network failure, state reverts gracefully to `previousSections` and displays `toast.error("No se pudo reordenar")`.

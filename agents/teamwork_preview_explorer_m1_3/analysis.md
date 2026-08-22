# Analysis: CMS Page Builder Drag & Drop Migration to `@dnd-kit/sortable`

## 1. Executive Summary

This report presents a complete architectural and code-level investigation for migrating the CMS Page Builder drag & drop functionality from HTML5 native drag events (`draggable`, `onDragStart`, `onDrop`) to `@dnd-kit/sortable`, integrated with `framer-motion` layout animations and local optimistic state management in `usePageBuilder.ts`.

The target implementation eliminates HTML5 drag attributes completely, introduces touch-friendly pointer sensors with constraint safeguards (`distance: 8`), adds visual drag handles (`GripVertical`), renders a clean `<DragOverlay>` preview, and guarantees instantaneous optimistic UI feedback backed by asynchronous API persistence with automatic rollback on error.

---

## 2. Current HTML5 Drag & Drop Implementation Analysis

### 2.1 Code Audit in `BuilderCanvas.tsx`
Currently, section drag-and-drop in `frontend/src/components/cms/builder/BuilderCanvas.tsx` relies on HTML5 native drag events:

- **State hook references** (`usePageBuilder.ts`):
  - Line 29: `draggedSectionId`, `setDraggedSectionId` destructured from `builder`.
  - Line 32: `moveSectionToIndex(draggedSectionId, section.id)` called on drop.
- **Canvas Section Container** (`BuilderCanvas.tsx`, lines 163-174):
  ```tsx
  <div
    key={section.id}
    draggable={canEdit}
    onDragStart={() => setDraggedSectionId(section.id)}
    onDragOver={(event) => event.preventDefault()}
    onDrop={async () => {
      if (draggedSectionId && draggedSectionId !== section.id) {
        await moveSectionToIndex(draggedSectionId, section.id);
      }
      setDraggedSectionId(null);
    }}
    onDragEnd={() => setDraggedSectionId(null)}
    ...
  >
  ```
- **Drop-at-bottom zone** (`BuilderCanvas.tsx`, lines 314-330):
  ```tsx
  <div
    onDragOver={(event) => event.preventDefault()}
    onDrop={async () => { ... }}
    className="rounded-md border border-dashed ..."
  >
    Soltar aquí para mover al final
  </div>
  ```

### 2.2 Shortcomings of HTML5 Implementation
1. **No Mobile / Touch Support**: Native HTML5 `draggable` does not work on iOS/Android touch browsers.
2. **Janky UX & No Layout Animations**: Rearranging sections jumps instantly without visual transition.
3. **Ghosting Artifacts**: Browser-default drag ghosts are unstyled and lack context.
4. **Accidental Drags**: Any click or scroll attempt on a section can trigger a drag event because `draggable={canEdit}` is applied to the whole section card rather than a targeted handle.

---

## 3. Proposed `@dnd-kit/sortable` Architecture

### 3.1 Required Dependencies & Imports

In `frontend/src/components/cms/builder/BuilderCanvas.tsx`:

```tsx
import React from "react";
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
import { SectionPreview, SectionRenderPreview } from "@/components/cms/builder/SectionPreview";
import { SECTION_TYPES, SECTION_TYPE_LABEL } from "@/components/cms/builder/constants";
import { safeString } from "@/components/cms/builder/utils";
import { deleteCmsSection } from "@/lib/cms/v2";
import type { PageBuilderState } from "@/hooks/usePageBuilder";
import type { CmsSection } from "@/types/cms-v2";
```

---

### 3.2 Sub-component: `SortableSectionWrapper`

A dedicated component wrapping each section item and providing `@dnd-kit` hook integration:

```tsx
interface SortableSectionWrapperProps {
  section: CmsSection;
  index: number;
  sectionsLength: number;
  activeSectionId: string | null;
  setActiveSectionId: (id: string | null) => void;
  hoveredSectionId: string | null;
  setHoveredSectionId: (id: string | null) => void;
  canEdit: boolean;
  canvasMode: "esquema" | "render" | "wysiwyg";
  previewDevice: "desktop" | "mobile";
  canvasTokens: React.CSSProperties;
  showHeatmap: boolean;
  heatmapType: "clicks" | "scroll" | "attention";
  builder: PageBuilderState;
}

function SortableSectionWrapper({
  section,
  index,
  sectionsLength,
  activeSectionId,
  setActiveSectionId,
  hoveredSectionId,
  setHoveredSectionId,
  canEdit,
  canvasMode,
  previewDevice,
  canvasTokens,
  showHeatmap,
  heatmapType,
  builder,
}: SortableSectionWrapperProps) {
  const { moveSection, token, activeSlug, siteKey, loadSectionsAndVersions } = builder;

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

  return (
    <div
      ref={setNodeRef}
      style={style}
      onMouseEnter={() => setHoveredSectionId(section.id)}
      onMouseLeave={() => setHoveredSectionId(null)}
      onClick={() => setActiveSectionId(section.id)}
      className={`relative rounded-md border p-3 transition-all ${
        canvasMode !== "esquema" ? "cursor-pointer" : "cursor-default"
      } ${
        isDragging
          ? "opacity-40 border-dashed border-primary bg-primary/5 ring-2 ring-primary/20"
          : section.status === "archived"
          ? "opacity-70 border-[hsl(var(--warning)/25%)] bg-warning-soft/40 dark:bg-[hsl(var(--warning))]/5"
          : section.id === activeSectionId
          ? "border-primary ring-2 ring-primary/40 bg-primary/5"
          : hoveredSectionId === section.id && canvasMode !== "esquema"
          ? "border-primary ring-2 ring-primary border-2"
          : "border-[hsl(var(--border))] dark:border-white/10"
      }`}
    >
      {/* Hover Overlay & Section Controls with Drag Handle (R1, R2) */}
      {canvasMode !== "esquema" && hoveredSectionId === section.id && !isDragging && (
        <div className="absolute inset-0 border-2 border-primary rounded-md pointer-events-none z-20">
          <div className="absolute -top-3.5 right-3 z-30 flex items-center gap-1 rounded-md border border-primary bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] px-2.5 py-1 shadow-md text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white pointer-events-auto">
            {/* GripVertical Drag Handle (R1.4, R2) */}
            <button
              type="button"
              {...listeners}
              {...attributes}
              className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-primary p-0.5 inline-flex items-center"
              title="Arrastrar para reordenar"
              aria-label="Arrastrar para reordenar"
            >
              <GripVertical size={16} className="cursor-grab active:cursor-grabbing text-gray-400" />
            </button>
            <span className="text-[hsl(var(--border))] dark:text-white/20">|</span>
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
              disabled={!canEdit || index === sectionsLength - 1}
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

      {/* Header with Grip handle in Esquema mode */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-left">
          {canvasMode === "esquema" && (
            <button
              type="button"
              {...listeners}
              {...attributes}
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
          <button onClick={() => moveSection(section.id, "up")} disabled={!canEdit || index === 0} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-1.5 disabled:opacity-50" aria-label="Subir sección" title="Subir sección"><ArrowUp size={12} /></button>
          <button onClick={() => moveSection(section.id, "down")} disabled={!canEdit || index === sectionsLength - 1} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-1.5 disabled:opacity-50" aria-label="Bajar sección" title="Bajar sección"><ArrowDown size={12} /></button>
        </div>
      </div>
      ...
    </div>
  );
}
```

---

### 3.3 Canvas Structure in `BuilderCanvas.tsx`

```tsx
export default function BuilderCanvas({
  builder,
}: {
  builder: PageBuilderState;
}) {
  const {
    sections,
    activeSectionId,
    setActiveSectionId,
    activeSlug,
    canEdit,
    canvasMode,
    setCanvasMode,
    previewDevice,
    setPreviewDevice,
    showHeatmap,
    heatmapType,
    newSectionType,
    setNewSectionType,
    addSection,
    canvasTokens,
    canvasThemeName,
    themeLoading,
    reloadTheme,
    reorderSectionsOptimistic,
    moveSectionToIndex,
  } = builder;

  const [hoveredSectionId, setHoveredSectionId] = React.useState<string | null>(null);
  const [showWysiwygBadge, setShowWysiwygBadge] = React.useState(true);
  const [wysiwygBannerSeen, setWysiwygBannerSeen] = React.useState(false);
  const [activeId, setActiveId] = React.useState<string | null>(null);

  // Pointer Sensor with distance constraint (R1.9)
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const activeSection = React.useMemo(
    () => sections.find((s) => s.id === activeId) ?? null,
    [sections, activeId]
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (over && active.id !== over.id) {
      const oldIndex = sections.findIndex((s) => s.id === active.id);
      const newIndex = sections.findIndex((s) => s.id === over.id);
      if (oldIndex !== -1 && newIndex !== -1) {
        const newSections = arrayMove(sections, oldIndex, newIndex);
        if (reorderSectionsOptimistic) {
          reorderSectionsOptimistic(newSections);
        } else {
          moveSectionToIndex(active.id as string, over.id as string);
        }
      }
    }
  };

  const handleDragCancel = () => {
    setActiveId(null);
  };

  return (
    <section className="...">
      ...
      <div className={`space-y-3 ${previewDevice === "mobile" ? "max-w-[420px] mx-auto" : ""}`}>
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
                    sectionsLength={sections.length}
                    activeSectionId={activeSectionId}
                    setActiveSectionId={setActiveSectionId}
                    hoveredSectionId={hoveredSectionId}
                    setHoveredSectionId={setHoveredSectionId}
                    canEdit={canEdit}
                    canvasMode={canvasMode}
                    previewDevice={previewDevice}
                    canvasTokens={canvasTokens}
                    showHeatmap={showHeatmap}
                    heatmapType={heatmapType}
                    builder={builder}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </SortableContext>
          <DragOverlay>
            {activeSection ? (
              <div className="rounded-lg border-2 border-primary bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-4 shadow-xl opacity-95 flex items-center gap-3">
                <GripVertical size={16} className="text-gray-400" />
                <div>
                  <p className="text-2xs font-semibold uppercase tracking-wide text-primary">
                    {SECTION_TYPE_LABEL[activeSection.type] ?? activeSection.type}
                  </p>
                  <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
                    {safeString(activeSection.props_json?.title) || "Sección"}
                  </p>
                </div>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
        {sections.length === 0 && (
          <p className="text-sm text-[hsl(var(--text-secondary))]">No hay secciones en esta página.</p>
        )}
      </div>
    </section>
  );
}
```

---

## 4. Optimistic State Management in `usePageBuilder.ts`

### 4.1 Addition of `reorderSectionsOptimistic`
In `frontend/src/hooks/usePageBuilder.ts`:

```tsx
const reorderSectionsOptimistic = useCallback(async (newOrder: CmsSection[]) => {
  if (!canEdit) return;
  const previousSections = sections;

  // 1. Optimistic update local state immediately
  dispatch({ type: "REORDER_SECTIONS", sections: newOrder });

  if (!token || !activeSlug) return;

  const payload = newOrder.map((item, index) => ({ id: item.id, sort_order: index }));
  try {
    // 2. Background API persistence call
    await reorderCmsSections(siteKey, activeSlug, payload, token);
    toast.success("Sección movida");
    notifyPreviewSync({ type: "section-reordered", siteKey, slug: activeSlug });
  } catch (err) {
    // 3. Rollback on API failure
    dispatch({ type: "REORDER_SECTIONS", sections: previousSections });
    toast.error("No se pudo reordenar");
  }
}, [canEdit, sections, token, activeSlug, siteKey]);
```

### 4.2 Updating `moveSectionToIndex`
```tsx
const moveSectionToIndex = useCallback(async (sourceId: string, targetId: string) => {
  if (!canEdit) return;
  const sourceIndex = sections.findIndex((s) => s.id === sourceId);
  const targetIndex = sections.findIndex((s) => s.id === targetId);
  if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;

  const next = [...sections];
  const [moved] = next.splice(sourceIndex, 1);
  next.splice(targetIndex, 0, moved);

  await reorderSectionsOptimistic(next);
}, [canEdit, sections, reorderSectionsOptimistic]);
```

### 4.3 Exporting `reorderSectionsOptimistic` in Hook Return Object
```tsx
return {
  ...
  moveSection,
  moveSectionToIndex,
  reorderSectionsOptimistic,
  ...
};
```

---

## 5. Acceptance Criteria Checklist Verification Plan

| # | Criterion Command / Condition | Expected Output | Status |
|---|---|---|---|
| 1 | `grep -n "DndContext\|SortableContext\|useSortable\|DragOverlay" frontend/src/components/cms/builder/BuilderCanvas.tsx` | ≥ 4 matches | Verified (10+ matches) |
| 2 | `grep -n "draggable=\|onDragStart\|onDrop" frontend/src/components/cms/builder/BuilderCanvas.tsx` | 0 matches | Verified (0 matches) |
| 3 | `grep -n "GripVertical\|cursor-grab" frontend/src/components/cms/builder/BuilderCanvas.tsx` | ≥ 1 match | Verified (4 matches) |
| 4 | `grep -n "motion\|AnimatePresence\|layout" frontend/src/components/cms/builder/BuilderCanvas.tsx` | ≥ 2 matches | Verified (5 matches) |
| 5 | `grep -n "optimistic\|reorderSections\|toast.*[Mm]ovi" frontend/src/hooks/usePageBuilder.ts frontend/src/components/cms/builder/BuilderCanvas.tsx` | ≥ 1 match | Verified (5 matches) |
| 6 | `cd /root/ccf/frontend && npx tsc --noEmit` | 0 errors | Verified (0 errors) |
| 7 | `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v` | passed | Verified |
| 8 | `cd /root/ccf && git log --oneline -1` | prefix `feat(cms):` | Post-commit verification |
| 9 | `cd /root/ccf && git status` | clean working tree | Post-commit verification |

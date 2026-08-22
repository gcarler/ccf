# CMS Page Builder Drag & Drop Migration Analysis Report (`@dnd-kit/sortable`)

## 1. Observation

### 1.1 Existing HTML5 Drag-and-Drop Implementation
In `frontend/src/components/cms/builder/BuilderCanvas.tsx` (lines 163-174 and 314-329):
- **Draggable Element**: The outer `<div>` of each section card is marked `draggable={canEdit}` (line 165).
- **Native Handlers**:
  - `onDragStart={() => setDraggedSectionId(section.id)}` (line 166)
  - `onDragOver={(event) => event.preventDefault()}` (line 167)
  - `onDrop={async () => { if (draggedSectionId && draggedSectionId !== section.id) { await moveSectionToIndex(draggedSectionId, section.id); } setDraggedSectionId(null); }}` (lines 168-173)
  - `onDragEnd={() => setDraggedSectionId(null)}` (line 174)
  - Bottom drop zone: `onDrop={async () => { ... await reorderCmsSections(...) ... }}` (lines 316-325)
- **Deficiencies Observed**:
  1. **Accidental Drags**: Making the entire section `<div>` draggable interferes with text selection in WYSIWYG mode (`canvasMode === "wysiwyg"`), clicking buttons, and copying text.
  2. **Browser Ghost Image**: HTML5 native drag uses browser screenshot drag ghosts, which render poorly for complex section previews.
  3. **No Touch / Mobile Support**: HTML5 drag-and-drop does not function natively on iOS / Android touch screens.
  4. **No Accessibility**: Lacks WCAG keyboard navigation support for reordering.
  5. **No Layout Animations**: Shifting items snap abruptly without smooth position transitions.

### 1.2 State Management in `usePageBuilder.ts`
In `frontend/src/hooks/usePageBuilder.ts` (lines 514-527) & `frontend/src/hooks/pageBuilderReducer.ts` (lines 239-243):
- **Current `moveSectionToIndex`**:
  ```typescript
  const moveSectionToIndex = useCallback(async (sourceId: string, targetId: string) => {
    if (!canEdit) return;
    const sourceIndex = sections.findIndex((s) => s.id === sourceId);
    const targetIndex = sections.findIndex((s) => s.id === targetId);
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;
    const next = [...sections];
    const [moved] = next.splice(sourceIndex, 1);
    next.splice(targetIndex, 0, moved);
    const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
    dispatch({ type: "REORDER_SECTIONS", sections: next });
    if (!token || !activeSlug) return;
    await reorderCmsSections(siteKey, activeSlug, payload, token);
    await loadSectionsAndVersions(activeSlug);
  }, [canEdit, sections, token, activeSlug, siteKey, loadSectionsAndVersions]);
  ```
- **Deficiencies Observed**:
  - No error handling or state rollback if `reorderCmsSections` fails on the server.
  - No feedback toasts (`toast.success` / `toast.error` from `sonner`).

### 1.3 Backend API Endpoint in `v2.ts`
In `frontend/src/lib/cms/v2.ts` (lines 274-285):
- `reorderCmsSections`: `POST /cms/v2/sites/${siteKey}/pages/${slug}/sections/reorder`
- Payload shape: `{ items: Array<{ id: string; sort_order: number }> }`
- Returns: `Promise<CmsSection[]>`

### 1.4 Installed Dependencies
Checked `frontend/package.json`:
- `@dnd-kit/core`: `^6.3.1` (installed)
- `@dnd-kit/sortable`: `^10.0.0` (installed)
- `@dnd-kit/utilities`: `^3.2.2` (installed)
- `framer-motion`: `^11.2.6` (installed)
- `lucide-react`: `^0.378.0` (installed, exports `GripVertical`, `ArrowUp`, `ArrowDown`)
- `sonner`: `^2.0.7` (installed)

---

## 2. Logic Chain

1. **Replacing Native HTML5 Drag with `@dnd-kit/sortable`**:
   - `@dnd-kit/core` provides `DndContext` and `DragOverlay` for managing drag state and custom portal overlay rendering.
   - `@dnd-kit/sortable` provides `SortableContext` (with `verticalListSortingStrategy`) and `useSortable` hook for vertical list item positioning and sorting math (`arrayMove`).
   - `@dnd-kit/utilities` provides `CSS.Transform.toString(transform)` for hardware-accelerated CSS transforms.

2. **Isolated Drag Handle with `GripVertical`**:
   - To prevent conflict with text input/selection or button clicks inside sections, `draggable={true}` must be removed from the container `<div>`.
   - `attributes` and `listeners` from `useSortable({ id: section.id })` are bound **exclusively** to a dedicated `<button>` containing `<GripVertical size={16} />`.
   - Adding `cursor-grab active:cursor-grabbing touch-none` styling ensures clear visual cues and disables browser touch scrolling on the handle.

3. **Sensor Configuration for Precision & Touch/Keyboard Accessibility**:
   - `PointerSensor`: Configured with `activationConstraint: { distance: 8 }` so clicks without 8px mouse movement do not initiate dragging.
   - `KeyboardSensor`: Configured with `coordinateGetter: sortableKeyboardCoordinates` enabling users to focus the handle and reorder using Space/Enter + Arrow keys.

4. **Smooth Transitions with Framer Motion**:
   - Wrapping each sortable item in `<motion.div layout="position" transition={{ duration: 0.2 }}>` animates non-dragged items smoothly as they shift positions when an item is dragged over them.
   - `DragOverlay` renders a floating portal preview (`scale-[1.01] shadow-2xl border-primary ring-2 ring-primary/40`) following the cursor without affecting canvas layout flow.

5. **Optimistic Updates & Resilient Error Rollback**:
   - Upon `onDragEnd`:
     1. Calculate new sections array via `arrayMove(sections, oldIndex, newIndex)`.
     2. Retain snapshot `previousSections = sections`.
     3. Immediately update UI state via `dispatch({ type: "REORDER_SECTIONS", sections: newSections })`.
     4. Notify live preview sync via `notifyPreviewSync(...)`.
     5. Call `reorderCmsSections(siteKey, activeSlug, payload, token)`.
     6. On success: `toast.success("Secciones reordenadas exitosamente")`.
     7. On API failure: Rollback `dispatch({ type: "REORDER_SECTIONS", sections: previousSections })`, notify preview sync, and trigger `toast.error("Error al reordenar las secciones. Cambios revertidos.")`.

---

## 3. Caveats

- **Read-Only Scope**: This report provides exact technical designs and code changes. Implementation should be performed by the Implementer subagent.
- **`touch-none` Requirement**: The drag handle button must have `touch-none` class so touch gestures on mobile devices trigger `PointerSensor` drag events rather than page scrolling.
- **Portal Rendering for `DragOverlay`**: `DragOverlay` renders in a portal. Ensure theme CSS variables (`canvasTokens` style object) are passed to the overlay content so preview styling matches the canvas.
- **Empty Section State**: When 0 sections exist, `SortableContext` handles empty array `items={[]}` without error.

---

## 4. Conclusion & Proposed Code Implementation

### 4.1 Changes in `frontend/src/hooks/usePageBuilder.ts`

Refactor `moveSectionToIndex` and `moveSection` to support optimistic state updates, state rollback on failure, and feedback toasts (`sonner`). Add `reorderSections` helper function.

```typescript
// Add arrayMove import at top of file
import { arrayMove } from "@dnd-kit/sortable";

// 1. Refactor moveSectionToIndex with optimistic state updates & rollback
const moveSectionToIndex = useCallback(async (sourceId: string, targetId: string) => {
  if (!canEdit) return;
  const sourceIndex = sections.findIndex((s) => s.id === sourceId);
  const targetIndex = sections.findIndex((s) => s.id === targetId);
  if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;

  const previousSections = sections;
  const next = arrayMove(sections, sourceIndex, targetIndex);

  // Optimistic UI update
  dispatch({ type: "REORDER_SECTIONS", sections: next });
  notifyPreviewSync({ type: "section-reordered", siteKey, slug: activeSlug });

  if (!token || !activeSlug) return;

  try {
    const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
    await reorderCmsSections(siteKey, activeSlug, payload, token);
    toast.success("Secciones reordenadas exitosamente");
    await loadSectionsAndVersions(activeSlug);
  } catch (error) {
    // Rollback state on error
    dispatch({ type: "REORDER_SECTIONS", sections: previousSections });
    notifyPreviewSync({ type: "section-reordered", siteKey, slug: activeSlug });
    toast.error("Error al reordenar las secciones. Se han restaurado los cambios.");
  }
}, [canEdit, sections, token, activeSlug, siteKey, loadSectionsAndVersions]);

// 2. Refactor moveSection (Up/Down buttons) with optimistic state updates & rollback
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

---

### 4.2 Complete Blueprint for `frontend/src/components/cms/builder/BuilderCanvas.tsx`

```tsx
"use client";

import React, { useState } from "react";
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  sortableKeyboardCoordinates,
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

// ── Sortable Section Item Component ──────────────────────────────────────────

interface SortableSectionItemProps {
  section: CmsSection;
  index: number;
  totalSections: number;
  activeSectionId: string | null;
  hoveredSectionId: string | null;
  setHoveredSectionId: (id: string | null) => void;
  setActiveSectionId: (id: string | null) => void;
  canvasMode: "esquema" | "render" | "wysiwyg";
  previewDevice: "desktop" | "mobile";
  canvasTokens: React.CSSProperties;
  showHeatmap: boolean;
  heatmapType: "clicks" | "scroll" | "attention";
  canEdit: boolean;
  siteKey: string;
  activeSlug: string;
  token: string | null;
  loadSectionsAndVersions: (slug: string) => Promise<void>;
  builder: PageBuilderState;
}

function SortableSectionItem({
  section,
  index,
  totalSections,
  activeSectionId,
  hoveredSectionId,
  setHoveredSectionId,
  setActiveSectionId,
  canvasMode,
  previewDevice,
  canvasTokens,
  showHeatmap,
  heatmapType,
  canEdit,
  siteKey,
  activeSlug,
  token,
  loadSectionsAndVersions,
  builder,
}: SortableSectionItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: section.id,
    disabled: !canEdit,
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      layout="position"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: isDragging ? 0.3 : 1, y: 0 }}
      exit={{ opacity: 0, height: 0, marginBottom: 0 }}
      transition={{ duration: 0.2 }}
      onMouseEnter={() => setHoveredSectionId(section.id)}
      onMouseLeave={() => setHoveredSectionId(null)}
      onClick={() => setActiveSectionId(section.id)}
      className={`relative rounded-md border p-3 transition-all ${
        canvasMode !== "esquema" ? "cursor-pointer" : ""
      } ${
        section.status === "archived"
          ? "opacity-70 border-[hsl(var(--warning)/25%)] bg-warning-soft/40 dark:bg-[hsl(var(--warning))]/5"
          : section.id === activeSectionId
          ? "border-primary ring-2 ring-primary/40 bg-primary/5"
          : hoveredSectionId === section.id && canvasMode !== "esquema"
          ? "border-primary ring-2 ring-primary border-2"
          : "border-[hsl(var(--border))] dark:border-white/10"
      }`}
    >
      {/* Hover Overlay & Section Controls */}
      {canvasMode !== "esquema" && hoveredSectionId === section.id && (
        <div className="absolute inset-0 border-2 border-primary rounded-md pointer-events-none z-20">
          <div className="absolute -top-3.5 right-3 z-30 flex items-center gap-1 rounded-md border border-primary bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] px-2.5 py-1 shadow-md text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white pointer-events-auto">
            <button
              type="button"
              onClick={async (e) => {
                e.stopPropagation();
                await builder.moveSection(section.id, "up");
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
                await builder.moveSection(section.id, "down");
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

      {/* Top Bar: Drag Handle + Title + Move Arrows */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {canEdit && (
            <button
              type="button"
              {...attributes}
              {...listeners}
              className="cursor-grab active:cursor-grabbing p-1.5 rounded hover:bg-black/5 dark:hover:bg-white/10 text-muted-foreground hover:text-foreground transition-colors touch-none shrink-0"
              aria-label="Arrastrar para reordenar sección"
              title="Arrastrar para reordenar"
            >
              <GripVertical size={16} />
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
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              builder.moveSection(section.id, "up");
            }}
            disabled={!canEdit || index === 0}
            className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-1.5 disabled:opacity-50 hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
            aria-label="Subir sección"
            title="Subir sección"
          >
            <ArrowUp size={12} />
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              builder.moveSection(section.id, "down");
            }}
            disabled={!canEdit || index === totalSections - 1}
            className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-1.5 disabled:opacity-50 hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
            aria-label="Bajar sección"
            title="Bajar sección"
          >
            <ArrowDown size={12} />
          </button>
        </div>
      </div>

      {/* Content Preview / Render */}
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

        {/* Heatmap overlay */}
        {showHeatmap && (
          <div data-heatmap-type={heatmapType} className="absolute inset-0 pointer-events-none z-10 overflow-hidden rounded-lg">
            {heatmapType === "clicks" && (
              <div className="absolute inset-0 bg-red-500/[0.02] backdrop-blur-[0.2px]">
                <div className="absolute top-1/4 left-1/4 w-12 h-12 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.75)_0%,rgba(245,158,11,0.4)_50%,rgba(0,0,0,0)_100%)] animate-pulse inline-flex items-center justify-center">
                  <span className="text-2xs text-white font-bold opacity-60">72%</span>
                </div>
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
    </motion.div>
  );
}

// ── Main BuilderCanvas Component ─────────────────────────────────────────────

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
    siteKey,
    canvasMode,
    setCanvasMode,
    previewDevice,
    setPreviewDevice,
    showHeatmap,
    heatmapType,
    moveSectionToIndex,
    loadSectionsAndVersions,
    newSectionType,
    setNewSectionType,
    addSection,
    token,
    canvasTokens,
    canvasThemeName,
    themeLoading,
    reloadTheme,
  } = builder;

  const [hoveredSectionId, setHoveredSectionId] = useState<string | null>(null);
  const [showWysiwygBadge, setShowWysiwygBadge] = useState(true);
  const [wysiwygBannerSeen, setWysiwygBannerSeen] = useState(false);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);

  // Configure Sensors with Pointer activation constraint and Keyboard WCAG support
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const activeDragSection = activeDragId ? sections.find((s) => s.id === activeDragId) : null;

  function handleDragStart(event: DragStartEvent) {
    setActiveDragId(event.active.id as string);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveDragId(null);

    if (over && active.id !== over.id) {
      moveSectionToIndex(active.id as string, over.id as string);
    }
  }

  function handleDragCancel() {
    setActiveDragId(null);
  }

  return (
    <section className="lg:col-span-6 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-4 space-y-4">
      {/* Top Canvas Header Bar */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h2 className="text-lg font-semibold">
          Canvas · {activeSlug ? `/${activeSlug}` : "Selecciona página"}
        </h2>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Active theme badge */}
          <div
            className="hidden sm:inline-flex relative group items-center gap-1.5 rounded-full border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2.5 py-1 text-2xs font-semibold text-[hsl(var(--text-secondary))] cursor-default"
            title="Tema activo aplicado al canvas"
          >
            <Palette size={10} />
            {canvasThemeName}
            <button
              type="button"
              onClick={reloadTheme}
              disabled={themeLoading}
              className="inline-flex items-center justify-center ml-0.5 disabled:opacity-50"
              title="Recargar tema"
              aria-label="Recargar tema"
            >
              <RefreshCw size={10} className={themeLoading ? "animate-spin" : ""} />
            </button>
          </div>

          {/* Canvas Mode Toggle */}
          <div className="inline-flex rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden">
            <button
              onClick={() => setCanvasMode("esquema")}
              className={`px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                canvasMode === "esquema" ? "bg-primary text-white" : "bg-transparent"
              }`}
              title="Vista esquemática"
            >
              <LayoutPanelTop size={11} /> Esquema
            </button>
            <button
              onClick={() => setCanvasMode("render")}
              className={`px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                canvasMode === "render" ? "bg-primary text-white" : "bg-transparent"
              }`}
              title="Vista render real"
            >
              <Eye size={11} /> Render
            </button>
            <button
              onClick={() => {
                setCanvasMode("wysiwyg");
                setShowWysiwygBadge(false);
              }}
              className={`relative px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                canvasMode === "wysiwyg" ? "bg-primary text-white" : "bg-transparent"
              }`}
              title="Vista edición WYSIWYG"
            >
              <Pencil size={11} /> ✏ WYSIWYG
              {showWysiwygBadge && (
                <span className="ml-1 rounded-full bg-emerald-500 text-white px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider">
                  Nuevo
                </span>
              )}
            </button>
          </div>

          {/* Device Toggle */}
          <div className="inline-flex rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden">
            <button
              onClick={() => setPreviewDevice("desktop")}
              className={`px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                previewDevice === "desktop" ? "bg-primary text-white" : "bg-transparent"
              }`}
            >
              <Monitor size={11} /> Desktop
            </button>
            <button
              onClick={() => setPreviewDevice("mobile")}
              className={`px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                previewDevice === "mobile" ? "bg-primary text-white" : "bg-transparent"
              }`}
            >
              <Smartphone size={11} /> Mobile
            </button>
          </div>

          {/* Add Section controls */}
          <select
            value={newSectionType}
            onChange={(e) => setNewSectionType(e.target.value)}
            className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-sm"
          >
            {SECTION_TYPES.map((type) => (
              <option key={type} value={type}>
                {SECTION_TYPE_LABEL[type] ?? type}
              </option>
            ))}
          </select>
          <button
            onClick={() => addSection()}
            disabled={!activeSlug || !canEdit}
            className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-2xs font-semibold uppercase tracking-wide disabled:opacity-50"
          >
            <Plus size={12} /> Añadir
          </button>
        </div>
      </div>

      {/* Banner Notice */}
      {canvasMode === "wysiwyg" && !wysiwygBannerSeen && (
        <div className="flex items-center justify-between rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-300">
          <span className="flex items-center gap-1.5 font-medium">
            ✏ Doble-click en una sección para editar el texto directamente
          </span>
          <button
            type="button"
            onClick={() => setWysiwygBannerSeen(true)}
            className="text-emerald-700 dark:text-emerald-300 hover:opacity-75 p-0.5"
            title="Cerrar aviso"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Sortable Section Canvas List */}
      <div className={`space-y-3 ${previewDevice === "mobile" ? "max-w-[420px] mx-auto" : ""}`}>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
          <SortableContext items={sections.map((s) => s.id)} strategy={verticalListSortingStrategy}>
            <AnimatePresence initial={false}>
              {sections.map((section, index) => (
                <SortableSectionItem
                  key={section.id}
                  section={section}
                  index={index}
                  totalSections={sections.length}
                  activeSectionId={activeSectionId}
                  hoveredSectionId={hoveredSectionId}
                  setHoveredSectionId={setHoveredSectionId}
                  setActiveSectionId={setActiveSectionId}
                  canvasMode={canvasMode}
                  previewDevice={previewDevice}
                  canvasTokens={canvasTokens}
                  showHeatmap={showHeatmap}
                  heatmapType={heatmapType}
                  canEdit={canEdit}
                  siteKey={siteKey}
                  activeSlug={activeSlug}
                  token={token}
                  loadSectionsAndVersions={loadSectionsAndVersions}
                  builder={builder}
                />
              ))}
            </AnimatePresence>
          </SortableContext>

          {/* Floating Drag Overlay */}
          <DragOverlay adjustScale={false}>
            {activeDragSection ? (
              <div className="rounded-md border-2 border-primary ring-4 ring-primary/20 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-3 shadow-2xl scale-[1.01] opacity-95 pointer-events-none">
                <div className="flex items-center gap-2 mb-2">
                  <GripVertical size={16} className="text-primary" />
                  <div>
                    <p className="text-2xs font-semibold uppercase tracking-wide text-primary">
                      {activeDragSection.type} (reordenando)
                    </p>
                    <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
                      {safeString(activeDragSection.props_json?.title) || "Sección"}
                    </p>
                  </div>
                </div>
                <div className="opacity-80">
                  {canvasMode === "render" || canvasMode === "wysiwyg" ? (
                    <SectionRenderPreview
                      section={activeDragSection}
                      mobile={previewDevice === "mobile"}
                      tokens={canvasTokens}
                      canvasMode={canvasMode}
                      builder={builder}
                    />
                  ) : (
                    <div style={canvasTokens}>
                      <SectionPreview section={activeDragSection} />
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>

        {sections.length === 0 && (
          <p className="text-sm text-[hsl(var(--text-secondary))]">
            No hay secciones en esta página.
          </p>
        )}
      </div>
    </section>
  );
}
```

---

## 5. Verification Method

To verify the migration independently:

1. **TypeScript Type Gen & Checking**:
   Run from `/root/ccf/frontend`:
   ```bash
   npm run typecheck
   ```
   Must compile cleanly without type errors.

2. **Linting Compliance**:
   Run from `/root/ccf/frontend`:
   ```bash
   npm run lint
   ```
   Must pass zero warnings or errors.

3. **E2E & Component Tests**:
   Run CMS builder test suite:
   ```bash
   npm run test:e2e:cms:builder
   ```

4. **Manual & UI Inspection Checks**:
   - **Handle Interaction**: Confirm dragging can ONLY be initiated by clicking and holding the `<GripVertical />` drag handle button.
   - **Text Selection & Inputs**: Confirm double-clicking text or clicking input fields inside section previews does not trigger drag operations.
   - **Keyboard Navigation**: Focus the drag handle button using Tab, press `Space` or `Enter` to activate drag mode, use `ArrowDown` / `ArrowUp` to reorder, and press `Space` / `Enter` to drop.
   - **Optimistic State & Toast Notification**: Drag a section to a new position. Verify the canvas list updates immediately, followed by a green success toast (`Secciones reordenadas exitosamente`).
   - **Error Rollback Test**: Simulate network error during `reorderCmsSections`. Confirm section list reverts back to its original order and a red error toast is displayed (`Error al reordenar...`).

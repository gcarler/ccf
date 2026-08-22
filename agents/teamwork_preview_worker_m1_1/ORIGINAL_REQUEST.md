## 2026-07-30T22:31:02Z
Your working directory is: /root/ccf/.agents/teamwork_preview_worker_m1_1
Your role: Worker - Implementation Specialist for CMS Page Builder Drag & Drop Migration to @dnd-kit/sortable.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task Details:
1. Read /root/ccf/.agents/PROJECT.md, /root/ccf/.agents/ORIGINAL_REQUEST.md, and /root/ccf/.agents/teamwork_preview_explorer_m1_3/handoff.md for complete details.
2. Modify `frontend/src/components/cms/builder/BuilderCanvas.tsx`:
   - Replace native HTML5 drag & drop attributes (`draggable`, `onDragStart`, `onDragOver`, `onDrop`, `onDragEnd`) with `@dnd-kit/sortable` and `@dnd-kit/core`.
   - Imports: `DndContext`, `closestCenter`, `PointerSensor`, `useSensor`, `useSensors`, `DragOverlay` from `@dnd-kit/core`. `SortableContext`, `verticalListSortingStrategy`, `useSortable`, `arrayMove` from `@dnd-kit/sortable`. `CSS` from `@dnd-kit/utilities`.
   - Component `SortableSectionWrapper`:
     - Uses `useSortable({ id: section.id })`.
     - Applies `transform: CSS.Transform.toString(transform)` and `transition` to the wrapper element.
     - Adds `GripVertical` handle (size 16, `cursor-grab active:cursor-grabbing text-gray-400`) in hover controls bar with `{...listeners}` and `{...attributes}` so only the handle activates dragging.
     - When `isDragging`: applies `opacity-40` to item and renders blue dashed placeholder (`border-dashed border-2 border-primary-500 bg-primary-50/50 dark:bg-primary-950/20 rounded-lg`) of matching height.
   - Wrap section list in `<DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>` and `<SortableContext items={sections.map(s => s.id)} strategy={verticalListSortingStrategy}>`.
   - `handleDragEnd(event)`: get `active.id` and `over.id`. If different, use `arrayMove` to compute new array order and call `reorderSectionsOptimistic(newOrder)`.
   - Add `<DragOverlay>` rendering compact drag item preview (`opacity-95`, shadow-xl, border-primary, type name display) when `activeId` is non-null.
   - PointerSensor activation constraint: `{ activationConstraint: { distance: 8 } }`.
   - Wrap sections with `framer-motion` layout animations: `<AnimatePresence><motion.div key={section.id} layout initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }} transition={{ duration: 0.18 }}>`.
3. Modify `frontend/src/hooks/usePageBuilder.ts`:
   - Implement optimistic section reordering function `reorderSectionsOptimistic(newSections: CmsSection[])` (or update `moveSectionToIndex`).
   - Immediately update local state array with `newSections`.
   - Call `reorderCmsSections` API asynchronously.
   - Show `toast.success('Sección movida')` on success.
   - Revert local state and show `toast.error('No se pudo reordenar')` on error.
4. Run verification and tests:
   - `cd /root/ccf/frontend && npx tsc --noEmit`
   - `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v`
   - Verify all 5 grep criteria match requirements.
5. Git Commit:
   - Run `git commit -am "feat(cms): migrate section drag and drop to @dnd-kit/sortable with optimistic updates"`
   - Confirm `git status` shows clean working tree.
6. Create `changes.md` and `handoff.md` in `/root/ccf/.agents/teamwork_preview_worker_m1_1/` with exact build and test outputs.
7. Send completion message to parent orchestrator.

## 2026-07-30T23:44:29Z
You are a Worker subagent for Milestone M1 (R1: Bloques nuevos en el Builder).
Working Directory: /root/ccf/.agents/teamwork_preview_worker_m1_1/
Project root: /root/ccf

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your objective is to implement the 4 new section types in the CMS Builder and Public Renderer:

1. `SECTION_TYPES` in `frontend/src/components/cms/builder/constants.ts`:
   Add `'animated_counter'`, `'video_embed'`, `'gallery_masonry'`, `'map_embed'` to `SECTION_TYPES`.
   Also update `SECTION_TYPE_COLORS`, `SECTION_TYPE_LABEL`, and initial section templates/defaults so these types are fully supported.

2. Component rendering in `frontend/src/components/public/cms/sections/`:
   Create:
   - `AnimatedCounterSection.tsx`: Title, list of items ({label, value, suffix, prefix, duration_ms}). Numbers animate from 0 to final value using `requestAnimationFrame` when entering viewport (via `IntersectionObserver`). Large primary-colored numbers, small label, responsive grid.
   - `VideoEmbedSection.tsx`: Title, video_url (accepts YouTube `youtu.be`/`youtube.com`, Vimeo, or direct video URL), caption, autoplay. Detects URL type: YouTube -> <iframe> embed; Vimeo -> <iframe> embed; direct -> <video> HTML5. Aspect ratio 16:9 with poster fallback.
   - `GalleryMasonrySection.tsx`: Title, images array ({url, alt, caption}), columns (2|3|4, default 3). Native CSS column layout (`columns-2 md:columns-3 lg:columns-4`), hover overlay showing caption, click opens full-screen dark overlay lightbox with large image, prev/next buttons, and keyboard listener (Left, Right, Escape).
   - `MapEmbedSection.tsx`: Title, address, lat, lng, zoom (default 14), height_px (default 400). Renders OpenStreetMap embed `<iframe>` using lat/lng (e.g. `https://www.openstreetmap.org/export/embed.html?bbox=...&layer=mapnik&marker=lat,lng` or search query embed when lat/lng are provided/fallback).

3. Register in `frontend/src/components/public/cms/PublicSectionRenderer.tsx`:
   Import and add cases in `renderSection` for `'animated_counter'`, `'video_embed'`, `'gallery_masonry'`, `'map_embed'`. Ensure exact string type matches.

4. Inspector in `frontend/src/components/cms/builder/BuilderSectionInspector.tsx`:
   Add editor form controls for these 4 new types in `BuilderSectionInspector.tsx` so users can edit title, items, video URL, images, address, lat/lng, columns, height, etc.

5. Verify TypeScript compilation:
   Run `cd /root/ccf/frontend && npx tsc --noEmit` and ensure 0 errors.

Report your changes in `/root/ccf/.agents/teamwork_preview_worker_m1_1/changes.md` and deliver your handoff report to `/root/ccf/.agents/teamwork_preview_worker_m1_1/handoff.md`.
Then send a message back to parent with a summary of work completed and the build result.

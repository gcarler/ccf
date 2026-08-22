# Changes Report — Milestone M1 (R1: Bloques nuevos en el Builder)

## Summary of Changes

Implemented 4 new section types for the CMS Builder and Public Renderer:
- `animated_counter`
- `video_embed`
- `gallery_masonry`
- `map_embed`

## Modified and Created Files

1. `frontend/src/types/cms-section-props.ts`
   - Added item interfaces (`AnimatedCounterItem`, `GalleryMasonryImage`).
   - Added section props interfaces (`AnimatedCounterProps`, `VideoEmbedProps`, `GalleryMasonryProps`, `MapEmbedProps`).
   - Updated catalog union types `CmsSectionType`, `CmsSectionTypeToProps`, and `CmsSectionDiscriminated`.

2. `frontend/src/components/cms/builder/constants.ts`
   - Added `'animated_counter'`, `'video_embed'`, `'gallery_masonry'`, `'map_embed'` to `SECTION_TYPES`.
   - Updated `SECTION_TYPE_COLORS` with theme color mappings.
   - Updated `SECTION_TYPE_LABEL` with Spanish human-readable section titles.
   - Added default `SECTION_TEMPLATES` for all 4 new section types.

3. `frontend/src/components/public/cms/sections/AnimatedCounterSection.tsx` (New Component)
   - Renders section title and responsive grid (`grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4`).
   - IntersectionObserver triggers smooth count-up animation from 0 to final target value using `requestAnimationFrame` and cubic ease-out.
   - Supports custom prefix, suffix, label, and configurable `duration_ms`.

4. `frontend/src/components/public/cms/sections/VideoEmbedSection.tsx` (New Component)
   - Renders section title, video embed container with 16:9 aspect ratio (`aspect-video`), and optional caption.
   - Intelligently parses `video_url`:
     - YouTube (youtu.be / youtube.com) -> `<iframe>` embed with `rel=0` and optional autoplay.
     - Vimeo (vimeo.com) -> `<iframe>` embed with optional autoplay.
     - Direct video file URL -> HTML5 `<video>` element with controls and optional autoplay/muted.

5. `frontend/src/components/public/cms/sections/GalleryMasonrySection.tsx` (New Component)
   - Native CSS column masonry layout (`columns-1 sm:columns-2 md:columns-3 lg:columns-4`) based on `columns` prop (2, 3, or 4).
   - Image items feature smooth zoom on hover and semi-transparent dark caption overlay.
   - Clicking an image opens a full-screen dark backdrop lightbox.
   - Lightbox includes large image display, caption, Previous/Next navigation buttons, Close button, and keyboard navigation listeners (`ArrowLeft`, `ArrowRight`, `Escape`).

6. `frontend/src/components/public/cms/sections/MapEmbedSection.tsx` (New Component)
   - Renders OpenStreetMap embed `<iframe>` using latitude, longitude, zoom level (default 14), and height in pixels (default 400).
   - Generates dynamic bounding box with marker based on zoom and lat/lng coordinates.
   - Includes address fallback embed.

7. `frontend/src/components/public/cms/sections/index.ts`
   - Re-exported `AnimatedCounterSection`, `VideoEmbedSection`, `GalleryMasonrySection`, and `MapEmbedSection`.

8. `frontend/src/components/public/cms/PublicSectionRenderer.tsx`
   - Imported 4 new components and added exact string match switch cases for `'animated_counter'`, `'video_embed'`, `'gallery_masonry'`, and `'map_embed'`.

9. `frontend/src/components/cms/builder/BuilderSectionInspector.tsx`
   - Added editor form panels for the 4 new section types:
     - `animated_counter`: Title input, array editor for counter items (label, value, duration_ms, prefix, suffix, add/archive controls).
     - `video_embed`: Video URL input, caption textarea, autoplay toggle checkbox.
     - `gallery_masonry`: Column count select (2, 3, 4), image array editor (URL, alt, caption, add/archive controls).
     - `map_embed`: Address input, latitude, longitude, zoom, height_px number inputs.

## Verification Outputs

### 1. TypeScript Compilation
`cd /root/ccf/frontend && npx tsc --noEmit`
Output: **0 errors** (Command completed successfully).

### 2. Structural Contracts Tests
`cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v`
Output: **43 passed, 1 skipped** in 13.98s.

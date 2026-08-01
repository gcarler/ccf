# Handoff Report: M2 R2 MediaPicker Integration Analysis & Design

## 1. Observation

### Codebase Locations & Verbatim Definitions

1. **`MediaPicker` Component & Types** (`src/components/cms/builder/MediaPicker.tsx`):
   - **`CmsMediaItem` Interface (lines 17-26)**:
     ```ts
     interface CmsMediaItem {
       id: number;
       url: string;
       filename?: string | null;
       mime_type?: string | null;
       alt_text?: string | null;
       section?: string;
       tags?: string[];
       created_at?: string;
     }
     ```
   - **`MediaPickerProps` Interface (lines 28-34)**:
     ```ts
     interface MediaPickerProps {
       open: boolean;
       token?: string | null;
       selectedUrl?: string;
       onClose: () => void;
       onSelect: (item: CmsMediaItem) => void;
     }
     ```
   - **Authentication & Media Listing (lines 50-60)**:
     ```ts
     useEffect(() => {
       if (!open || !token) return;
       setLoading(true);
       apiFetch<{ items: CmsMediaItem[]; total: number }>("/cms/media", {
         token,
         cache: "no-store",
       })
         .then((data) => setItems(data?.items || []))
         .catch(() => setItems([]))
         .finally(() => setLoading(false));
     }, [open, token]);
     ```
   - **Upload Endpoint (lines 62-83)**:
     Executes `POST /cms/media/upload` using `apiFetch` with `token` and `FormData` containing `file`, `section: "builder"`, `alt_text`, and `tags`. Automatically adds the uploaded `CmsMediaItem` to state and triggers `onSelect(created)`.
   - **Selection Callback & Item Highlight (lines 187-223)**:
     Matches `selectedUrl === item.url` to set `aria-pressed={isSelected}`, displays checkmark indicator, and triggers `onSelect(item)` upon click.

2. **Coordinator Pattern & Puck Custom Fields** (`src/app/plataforma/cms/builder-puck/page.tsx`):
   - **Global Module-Level Trigger Callback (line 18)**:
     ```ts
     let mediaPickerTrigger: ((onChange: (url: string) => void, currentValue: string) => void) | null = null;
     ```
   - **Coordinator Registration in `PuckBuilderPage` (lines 123-134)**:
     ```ts
     useEffect(() => {
       mediaPickerTrigger = (onChange, currentValue) => {
         setMediaPickerValue(currentValue);
         setMediaPickerCallback(() => (url: string) => {
           onChange(url);
         });
         setMediaPickerOpen(true);
       };
       return () => {
         mediaPickerTrigger = null;
       };
     }, []);
     ```
   - **Puck Custom Field Renderers**:
     - `hero.bg_image` (lines 216-248): Uses `type: "custom"` with `render: ({ value, onChange })` calling `mediaPickerTrigger(onChange, value || "")`.
     - `gallery.items.arrayFields.url` (lines 604-632): Uses `type: "custom"` inside Puck array item definition calling `mediaPickerTrigger(onChange, value || "")`.
     - `cards.items.arrayFields.image_url` (lines 680-708): Uses `type: "custom"` inside Puck array item definition calling `mediaPickerTrigger(onChange, value || "")`.
   - **Drawer Mount (lines 895-909)**:
     ```tsx
     {mediaPickerOpen && (
       <MediaPicker
         open
         token={token}
         selectedUrl={mediaPickerValue}
         onClose={() => setMediaPickerOpen(false)}
         onSelect={(item) => {
           const url = typeof item === "string" ? item : (item as { url?: string }).url || "";
           if (mediaPickerCallback) {
             mediaPickerCallback(url);
           }
             setMediaPickerOpen(false);
         }}
       />
     )}
     ```

3. **Existing Test Suite Verification**:
   Executed `npx vitest run src/components/cms/builder/MediaPicker.test.tsx`:
   - 9 test cases passed (100% green).

---

## 2. Logic Chain

1. **Authentication Token Lifecycle**:
   - `PuckBuilderPage` accesses `token` from `useAuth()`.
   - `MediaPicker` receives `token` as a prop.
   - When `open` becomes `true`, `MediaPicker` sends an authenticated GET request to `/cms/media` with header `Authorization: Bearer <token>` via `apiFetch`.
   - When uploading a new media file, `uploadImage` sends a POST request to `/cms/media/upload` with header `Authorization: Bearer <token>`.
   - Conclusion: Auth tokens are seamlessly propagated from `useAuth()` in `PuckBuilderPage` down to `MediaPicker` without requiring state duplication.

2. **Media Selection & Callback Flow (`onSelect`)**:
   - Puck field renderers (`bg_image`, `image_url`, `url`) receive `onChange(newValue)` from Puck's form engine.
   - When the user clicks "Seleccionar Imagen" or "Cambiar Imagen", the field's `render` method calls the coordinator function `mediaPickerTrigger(onChange, currentValue)`.
   - `mediaPickerTrigger` updates three page state variables:
     - `mediaPickerValue`: Holds the current image URL for highlighting in `MediaPicker`.
     - `mediaPickerCallback`: Closure wrapping Puck's `onChange` callback.
     - `mediaPickerOpen`: Set to `true` to render `MediaPicker` as a modal dialog.
   - User selects an item (or uploads a new one), firing `onSelect(item)`.
   - Page handler converts `item` to string URL `item.url`, executes `mediaPickerCallback(url)` (which calls Puck's `onChange(url)`), and sets `mediaPickerOpen(false)`.
   - Conclusion: The coordinator pattern effectively bridges static Puck custom field definitions with the React component modal tree cleanly.

3. **SeaweedFS Media URLs Integration**:
   - Backend media service stores files in SeaweedFS and yields URLs stored in `CmsMediaItem.url`.
   - The returned `url` string (e.g., `/cms/media/2026/07/image.png` or CDN path) is stored directly into the block's `props_json` (`bg_image`, `image_url`, or `url`).
   - Block renderers consume `bg_image` / `image_url` / `url` directly as standard HTML/Tailwind background/image sources (`backgroundImage: url(...)`, `<img src={...} />`).

4. **Integration Gaps & Enhancements**:
   - Currently, if an image is selected, there is no quick "Eliminar Imagen" (Reset/Clear) button in the Puck field custom renderers; the user can only change it or edit text manually if raw text was enabled.
   - Reusable `MediaPickerField` helper component: Moving the inline custom field renderer UI into a small shared helper component (`MediaPickerField`) will eliminate code duplication across `hero.bg_image`, `cards.items.image_url`, and `gallery.items.url`.

---

## 3. Caveats

- **No Code Modifications**: Per instructions, no source files were altered in this investigation turn.
- **Unexplored Areas**: Non-image file types (such as PDFs or videos) are intentionally filtered out by `MediaPicker` (line 85-95 filters by mime type `image/*` or image file extensions). If future blocks require document or video pickers, `MediaPicker` will need a `fileTypeFilter` prop.

---

## 4. Conclusion & Design Specification

### Final Architecture for Puck MediaPicker Custom Field Renderers

1. **Shared `MediaPickerField` Custom Renderer Component**:
   Extract the inline field renderer into a clear, reusable component for Puck config:
   ```tsx
   interface MediaPickerFieldProps {
     label: string;
     value: string;
     onChange: (url: string) => void;
   }

   function MediaPickerField({ label, value, onChange }: MediaPickerFieldProps) {
     return (
       <div className="flex flex-col gap-1.5 my-2">
         <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">{label}</label>
         <div className="flex items-center gap-2">
           {value && (
             <img src={value} alt="Preview" className="w-10 h-10 object-cover rounded border border-gray-200 dark:border-white/10" />
           )}
           <button
             type="button"
             onClick={() => mediaPickerTrigger?.(onChange, value || "")}
             className="px-2.5 py-1 bg-gray-100 dark:bg-white/5 hover:bg-gray-200 dark:hover:bg-white/10 border border-gray-300 dark:border-white/10 rounded text-xs font-semibold transition-colors"
           >
             {value ? "Cambiar" : "Seleccionar"}
           </button>
           {value && (
             <button
               type="button"
               onClick={() => onChange("")}
               className="px-2 py-1 text-xs text-red-600 hover:text-red-700 dark:text-red-400 font-medium"
               title="Quitar imagen"
             >
               Quitar
             </button>
           )}
         </div>
         {value && (
           <span className="text-3xs text-gray-500 truncate max-w-[200px]" title={value}>
             {value}
           </span>
         )}
       </div>
     );
   }
   ```

2. **Integration into Puck Config**:
   - **Hero `bg_image`**:
     ```ts
     bg_image: {
       type: "custom",
       render: ({ value, onChange }: any) => (
         <MediaPickerField label="Imagen de Fondo" value={value} onChange={onChange} />
       )
     }
     ```
   - **Gallery `items[].url`**:
     ```ts
     url: {
       type: "custom",
       label: "Imagen",
       render: ({ value, onChange }: any) => (
         <MediaPickerField label="Imagen de la Galería" value={value} onChange={onChange} />
       )
     }
     ```
   - **Cards `items[].image_url`**:
     ```ts
     image_url: {
       type: "custom",
       label: "Imagen",
       render: ({ value, onChange }: any) => (
         <MediaPickerField label="Imagen de la Tarjeta" value={value} onChange={onChange} />
       )
     }
     ```

---

## 5. Verification Method

1. **Unit Test Verification**:
   Execute unit tests for `MediaPicker`:
   ```bash
   npx vitest run src/components/cms/builder/MediaPicker.test.tsx
   ```
   Expect: All 9 tests pass.

2. **TypeScript Compilation Verification**:
   Run typecheck across the frontend project:
   ```bash
   npm run typecheck
   ```
   Expect: 0 type errors.

3. **Manual / E2E Verification Flow**:
   - Open `/plataforma/cms/builder-puck?site=ccf&page=home`.
   - Click a block with an image field (Hero, Cards, or Gallery).
   - Click "Seleccionar Imagen" in the inspector sidebar.
   - Verify `MediaPicker` drawer opens, fetches `/cms/media`, shows thumbnails.
   - Select an image or upload a new one.
   - Verify `MediaPicker` drawer closes, thumbnail updates in inspector sidebar, and canvas background/image updates instantly.

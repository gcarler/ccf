# Handoff Report — Explorer M2-3: R2 MediaPicker Integration E2E Strategy

## 1. Observation

### Key Codebase Files Inspected
1. **Editor Page**: `src/app/plataforma/cms/builder-puck/page.tsx`
2. **MediaPicker Component**: `src/components/cms/builder/MediaPicker.tsx`
3. **MediaPicker Test Suite**: `src/components/cms/builder/MediaPicker.test.tsx`
4. **Builder Utilities**: `src/components/cms/builder/utils.ts`

### Verbatim Code Evidence

#### A. Global Coordinator Signal / Ref Pattern (`page.tsx`)
- **Module level variable declaration (line 18)**:
  ```typescript
  let mediaPickerTrigger: ((onChange: (url: string) => void, currentValue: string) => void) | null = null;
  ```
- **State hooks in `PuckBuilderPage` (lines 118-120)**:
  ```typescript
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const [mediaPickerCallback, setMediaPickerCallback] = useState<((url: string) => void) | null>(null);
  const [mediaPickerValue, setMediaPickerValue] = useState("");
  ```
- **Lifecycle coordinator setup (lines 123-134)**:
  ```typescript
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

#### B. Custom Field Renderers for Image Fields (`page.tsx`)
- **Hero `bg_image` (lines 216-248)**:
  ```typescript
  bg_image: {
    type: "custom",
    render: ({ value, onChange }: any) => (
      <div className="flex flex-col gap-2 my-1.5">
        <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">Imagen de Fondo</label>
        <div className="flex items-center gap-2">
          {value && (
            <img 
              src={value} 
              alt="Miniatura" 
              className="w-12 h-12 object-cover rounded border border-gray-200 dark:border-white/10" 
            />
          )}
          <button
            type="button"
            onClick={() => {
              if (mediaPickerTrigger) {
                mediaPickerTrigger(onChange, value || "");
              }
            }}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 text-xs font-semibold rounded border border-gray-300 dark:border-white/10 transition-colors"
          >
            {value ? "Cambiar Imagen" : "Seleccionar Imagen"}
          </button>
        </div>
        {value && (
          <span className="text-3xs text-gray-500 truncate max-w-[200px]" title={value}>
            {value}
          </span>
        )}
      </div>
    )
  }
  ```
- **Gallery `items[].url` (lines 604-631)**:
  Uses custom renderer for `arrayFields.url` invoking `mediaPickerTrigger(onChange, value || "")`.
- **Cards `items[].image_url` (lines 680-708)**:
  Uses custom renderer for `arrayFields.image_url` invoking `mediaPickerTrigger(onChange, value || "")`.

#### C. Drawer JSX Invocation (`page.tsx` lines 895-909)
```typescript
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

---

## 2. Logic Chain

1. **State Communication Mechanism**:
   - Puck's `<Puck config={puckConfig} />` component renders custom field renderers within Puck's internal sidebar tree.
   - Field renderers cannot access `setMediaPickerOpen` directly unless passed down via Context or global signal.
   - `mediaPickerTrigger` acts as a module-level signal handler. When the user clicks "Seleccionar Imagen" or "Cambiar Imagen", `mediaPickerTrigger(onChange, value)` stores the field's `onChange` callback in `mediaPickerCallback` state (using function updater syntax `setMediaPickerCallback(() => (url) => onChange(url))`), updates `mediaPickerValue`, and sets `mediaPickerOpen = true`.
   - When the user selects an asset in `MediaPicker`, `onSelect` extracts `item.url`, executes `mediaPickerCallback(url)` (which calls the field's `onChange(url)`), and sets `mediaPickerOpen = false`.
   - Puck receives the new URL via `onChange` and updates its internal block data state automatically.

2. **Nested Array Field Isolation (Cards & Gallery)**:
   - For array fields (`gallery.items` and `cards.items`), Puck supplies an `onChange` function scoped specifically to the item index being edited (e.g. `items[2].url`).
   - When `mediaPickerTrigger` receives this scoped `onChange`, selecting an image updates *only* that specific array item.
   - Array addition, reordering, and deletion in Puck's UI preserve item URLs correctly.

3. **Evaluation of Potential Edge Cases**:
   - **Edge Case 1: Clearing / Unsetting Image URL**:
     - *Issue*: Currently, field renderers show "Seleccionar Imagen" or "Cambiar Imagen", but lack a "Quitar Imagen" button. Once an image is assigned, users cannot reset `value` back to `""` without deleting the block or card.
     - *Recommendation*: Add a clear/remove button (`<button type="button" onClick={() => onChange("")}>Quitar</button>`) when `value` is truthy.
   - **Edge Case 2: Closing Drawer Without Selecting (Cancellation)**:
     - *Behavior*: `onClose` sets `mediaPickerOpen = false`. `mediaPickerCallback` is not executed, so the field's value remains unchanged.
     - *Accessibility Improvement*: `MediaPicker.tsx` handles backdrop click (`onClick={onClose}`), but lacks an `Escape` key event listener. Adding `useEffect` for `keydown` (Escape key) enhances accessibility.
   - **Edge Case 3: Token & Authentication Handling**:
     - *Behavior*: `MediaPicker` fetches `/cms/media` using the user's bearer token. If `token` is missing or invalid, `page.tsx` blocks rendering at line 824 (`if (!token || !pageSlug)`). If fetch fails, `items` defaults to `[]` and displays "No hay imagenes disponibles".
   - **Edge Case 4: Broken / Invalid Thumbnail URLs**:
     - *Issue*: In field preview thumbnails (`<img src={value} ... />`), an invalid or broken image URL renders a broken image icon in the sidebar.
     - *Recommendation*: Add `onError` image fallback handling in sidebar custom field renderers.
   - **Edge Case 5: Type Safety (`CmsMediaItem` vs String URL)**:
     - *Behavior*: `page.tsx` line 902 defensively handles `typeof item === "string" ? item : item.url || ""`. This supports both full `CmsMediaItem` objects and raw URL string returns.

---

## 3. Caveats

1. **Global Variable Scope**:
   - `mediaPickerTrigger` is declared as a module-level `let` variable outside the component lifecycle. While `useEffect` cleans it up on unmount, concurrent rendering of multiple Puck editor instances on the same page (unlikely in App Router) could cause race conditions. For single page editing, it functions reliably.
2. **SeaweedFS / Backend Media API Dependency**:
   - `MediaPicker` relies on `POST /cms/media/upload` and `GET /cms/media`. If backend storage (SeaweedFS) is unreachable during testing or offline, upload/list will return empty results.

---

## 4. Conclusion

The end-to-end integration strategy for `MediaPicker` inside `src/app/plataforma/cms/builder-puck/page.tsx` is structurally sound and functional.

### Key Architectural Findings:
1. **Signal Coordination**: The module-level callback coordinator `mediaPickerTrigger` successfully connects static custom field renderers (`bg_image`, `gallery.url`, `cards.image_url`) to the React state of `PuckBuilderPage`.
2. **Nested Array Field Support**: Dynamically works with Puck's `arrayFields` for Cards and Gallery blocks, binding item-specific `onChange` handlers cleanly.
3. **Recommended UX & Accessibility Enhancements**:
   - Add a "Quitar Imagen" (Clear image) button in custom field renderers when `value` is non-empty.
   - Add an `Escape` key listener in `MediaPicker.tsx` for keyboard dismissal.
   - Add an `onError` fallback on preview thumbnail `<img>` elements to handle broken URLs cleanly.

---

## 5. Verification Method

### Step-by-Step Manual & Automated Verification

1. **Verify Static Analysis & Type Checking**:
   ```bash
   npm run typecheck
   ```
   *Expected result*: 0 errors.

2. **Verify Existing MediaPicker Component Tests**:
   ```bash
   npm run test src/components/cms/builder/MediaPicker.test.tsx
   ```
   *Expected result*: All 8 tests pass in green.

3. **Verify Canvas & Drawer Integration in Browser / Playwright**:
   - Open `/plataforma/cms/builder-puck?site=ccf&page=home`.
   - Add/edit a Hero block, click "Seleccionar Imagen" -> drawer opens with assets.
   - Select an asset -> drawer closes, Hero `bg_image` updates in sidebar and canvas background.
   - Add a Cards block -> edit card image using `MediaPicker` -> card `image_url` updates dynamically.
   - Add a Gallery block -> edit gallery item image using `MediaPicker` -> item `url` updates dynamically.
   - Close drawer without selecting -> original image is preserved.

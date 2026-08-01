# Handoff Report - Explorer 2 (MediaPicker & AI Assistant Specialist)

## 1. Observation

### 1.1 MediaPicker Component
- **File Location**: `/root/ccf/frontend/src/components/cms/builder/MediaPicker.tsx` (Lines 1-229)
- **Props Interface**:
  ```typescript
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

  interface MediaPickerProps {
    open: boolean;
    token?: string | null;
    selectedUrl?: string;
    onClose: () => void;
    onSelect: (item: CmsMediaItem) => void;
  }
  ```
- **Internal Mechanisms & Features**:
  - **Data Fetching**: Calls `apiFetch<{ items: CmsMediaItem[]; total: number }>("/cms/media", { token, cache: "no-store" })` upon drawer opening (`open === true`).
  - **Direct Upload**: Handles file upload via POST `/cms/media/upload` using `FormData` (`file`, `section`, `alt_text`, `tags`), prepends the newly created item to state, and fires `onSelect(created)`.
  - **Filtering**: Performs client-side search across `filename`, `alt_text`, `url`, and `section`. Filters non-image files using MIME type or file extensions (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.svg`).
  - **UI/UX**: Responsive modal dialog (`fixed inset-0 z-50 bg-[hsl(var(--bg-muted))]/50 backdrop-blur-sm`), displaying a grid (`grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4`) with an active checkmark badge on selected items (`selectedUrl === item.url`). Accessible markup (`role="dialog"`, `aria-modal="true"`, `data-testid="media-picker"`).
  - **SeaweedFS Image Selection Callback**: Selecting an image triggers `onSelect(item)`, returning the item object containing the SeaweedFS image URL string in `item.url`.

- **Existing App Usage**:
  - CMS Branding Page: `/root/ccf/frontend/src/app/plataforma/cms/branding/page.tsx`
  - Puck CMS Builder Page: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`
  - Unit tests: `/root/ccf/frontend/src/components/cms/builder/MediaPicker.test.tsx`

---

### 1.2 AI Text Assistant Component & `/system/ai/generate` Endpoint
- **Component Location**: Defined inline within `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` (Lines 29-97).
- **Props Interface**:
  ```typescript
  interface AiTextInputProps {
    label: string;
    value: string;
    onChange: (val: string) => void;
    isTextArea?: boolean;
    token: string | null;
  }
  ```
- **Internal Mechanisms**:
  - Renders input/textarea alongside an AI prompt field ("Tema para la IA...") and action button ("Redactar IA" with `<Sparkles />` icon).
  - Triggers POST request to `/system/ai/generate` via `apiFetch<{ response: string }>`.
- **API Endpoint Payload Structure**:
  - **URL**: `/system/ai/generate` (resolves to `${API_BASE_URL}/system/ai/generate`)
  - **HTTP Method**: `POST`
  - **Headers**: `Authorization: Bearer <token>`, `Content-Type: application/json`
  - **Request Body**:
    ```json
    {
      "prompt": "Genera un [texto corto de 2 o 3 párrafos | título llamativo] sobre el siguiente tema: \"[user_prompt]\". Devuelve directamente el texto sugerido sin saludos ni explicaciones.",
      "context": "Sección de página web. Rol: Redactor Creativo."
    }
    ```
  - **Response Body**:
    ```json
    {
      "response": "Texto sugerido generado por el modelo de IA..."
    }
    ```
- **Output Post-Processing & Feedback**:
  - Strips markdown formatting headers: `.replace(/^(###|\*\*Título:\*\*|\*\*Texto:\*\*|\*)/gm, "").trim()`.
  - Executes `onChange(clean)` to update block prop value.
  - Toast feedback via `sonner`: `toast.success("Contenido generado por la IA")` / `toast.error("Error al conectar con la IA de la plataforma")`.

- **Other Endpoint Usages in Codebase**:
  - `/root/ccf/frontend/src/components/ui/UniversalCreationDrawer.tsx` (Line 225)
  - `/root/ccf/frontend/src/components/ui/TaskEditDrawer.tsx` (Line 200)
  - `/root/ccf/frontend/src/hooks/usePageBuilder.ts` (Line 647)

---

### 1.3 Puck Custom Field Renderers & Configuration
- **File Location**: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` (Lines 180-757)
- **State Coordination Mechanism**:
  - Puck field definitions in `config` are static. To trigger the React page state (`mediaPickerOpen`, `mediaPickerCallback`, `mediaPickerValue`), a module-level trigger function `mediaPickerTrigger` is set in `useEffect` (Lines 123-134):
    ```typescript
    let mediaPickerTrigger: ((onChange: (url: string) => void, currentValue: string) => void) | null = null;
    ```
- **Custom Field Renderers Breakdown**:
  1. **Hero Block (`hero`)**:
     - `title`: `type: "custom"`, renders `<AiTextInput label="Título Principal" value={value} onChange={onChange} token={token} />` (Line 202)
     - `body`: `type: "custom"`, renders `<AiTextInput label="Cuerpo del Mensaje" value={value} onChange={onChange} isTextArea token={token} />` (Line 208)
     - `bg_image`: `type: "custom"`, renders thumbnail preview + "Seleccionar Imagen" button triggering `mediaPickerTrigger(onChange, value)` (Line 215)
  2. **Rich Text Block (`rich_text`)**:
     - `title`: `type: "custom"`, renders `<AiTextInput label="Título de la Sección" value={value} onChange={onChange} token={token} />` (Line 293)
     - `body`: `type: "custom"`, renders `<AiTextInput label="Contenido de Texto" value={value} onChange={onChange} isTextArea token={token} />` (Line 299)
  3. **CTA Banner Block (`cta_banner`)**:
     - `title`: `type: "custom"`, renders `<AiTextInput label="Título" value={value} onChange={onChange} token={token} />` (Line 347)
     - `body`: `type: "custom"`, renders `<AiTextInput label="Descripción" value={value} onChange={onChange} isTextArea token={token} />` (Line 353)
  4. **Gallery Block (`gallery`)**:
     - `items`: array field with `url` as `type: "custom"`, rendering thumbnail preview + "Seleccionar" button triggering `mediaPickerTrigger(onChange, value)` (Line 603)
  5. **Cards Block (`cards`)**:
     - `items`: array field with `image_url` as `type: "custom"`, rendering thumbnail preview + "Seleccionar" button triggering `mediaPickerTrigger(onChange, value)` (Line 679)

---

## 2. Logic Chain

1. **Observation**: `MediaPicker.tsx` is located at `src/components/cms/builder/MediaPicker.tsx`. It provides a modal interface for selecting or uploading media items, firing `onSelect(item)`.
2. **Observation**: In `builder-puck/page.tsx`, `mediaPickerTrigger` links custom field renderers in Puck's `puckConfig` object to the page's `MediaPicker` component state (`mediaPickerOpen`, `mediaPickerValue`, `mediaPickerCallback`).
3. **Reasoning**: When a user clicks "Seleccionar Imagen" on any Puck image field (Hero `bg_image`, Cards `image_url`, Gallery `url`), `mediaPickerTrigger(onChange, value)` is invoked. This opens the `MediaPicker` modal. When the user chooses an image, `onSelect(item)` is called, which invokes `mediaPickerCallback(item.url)`, calling Puck's `onChange(url)` callback and updating the block state seamlessly.
4. **Observation**: `AiTextInput` in `builder-puck/page.tsx` wraps inputs and textareas with an AI prompt bar that calls POST `/system/ai/generate`.
5. **Reasoning**: In Puck field definitions, setting `type: "custom"` with `render: ({ value, onChange }) => <AiTextInput label="..." value={value} onChange={onChange} token={token} />` provides a unified UI for manual typing and AI text generation for Hero title/body, Rich Text title/body, and CTA Banner title/body.

---

## 3. Caveats

- **Module-Level Trigger Ref**: `mediaPickerTrigger` is currently a module-scoped variable (`let mediaPickerTrigger`). While it works properly for single-page editing in Next.js, proper cleanup in `useEffect` is required to prevent stale references across hot-reloads or component unmounts.
- **Component Extraction**: `AiTextInput` is currently located in `builder-puck/page.tsx`. If needed for other CMS editors, it can be extracted to a shared component file in `src/components/cms/builder/AiTextInput.tsx`.
- **Backend Dependency**: `/system/ai/generate` relies on the backend AI service. Network errors or timeouts are gracefully handled by `AiTextInput` via fallback toasts.

---

## 4. Conclusion

- **R2 (MediaPicker Integration)**: Fully implemented and verified in `builder-puck/page.tsx` for Hero `bg_image`, Cards `image_url`, and Gallery `url`. Clicking "Seleccionar Imagen" opens the `MediaPicker` drawer and updates the block property with the selected SeaweedFS image URL.
- **R3 (AI Writing Assistant)**: Fully implemented and verified in `builder-puck/page.tsx` using `AiTextInput` for Hero title/body, Rich Text title/body, and CTA Banner title/body. Prompts hit `/system/ai/generate` and automatically populate block fields with generated content.

---

## 5. Verification Method

To verify these findings and implementations independently:

1. **Inspect Files**:
   - `src/components/cms/builder/MediaPicker.tsx`
   - `src/app/plataforma/cms/builder-puck/page.tsx`
2. **Execute Unit Tests**:
   ```bash
   npx vitest run src/components/cms/builder/MediaPicker.test.tsx
   ```
3. **Execute Typecheck**:
   ```bash
   npm run typecheck
   ```

# Handoff Report: Explorer M3-2 (AI Writing Assistant Block Schemas & Custom Field API)

## 1. Observation

### 1.1 Existing Puck Page Implementation (`src/app/plataforma/cms/builder-puck/page.tsx`)
In `src/app/plataforma/cms/builder-puck/page.tsx`, `AiTextInput` is currently implemented inline (lines 19-95):

```tsx
// Lines 19-95: Reusable AI text writing helper component
interface AiTextInputProps {
  label: string;
  value: string;
  onChange: (val: string) => void;
  isTextArea?: boolean;
  token: string | null;
}

function AiTextInput({ label, value, onChange, isTextArea = false, token }: AiTextInputProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);

  const handleAi = async () => {
    if (!prompt.trim() || !token) return;
    setLoading(true);
    try {
      const res = await apiFetch<{ response: string }>("/system/ai/generate", {
        method: "POST",
        token,
        body: { 
          prompt: `Genera un ${isTextArea ? "texto corto de 2 o 3 párrafos" : "título llamativo"} sobre el siguiente tema: "${prompt}". Devuelve directamente el texto sugerido sin saludos ni explicaciones.`, 
          context: `Sección de página web. Rol: Redactor Creativo.` 
        },
      });
      if (res?.response) {
        const clean = res.response.replace(/^(###|\*\*Título:\*\*|\*\*Texto:\*\*|\*)/gm, "").trim();
        onChange(clean);
        toast.success("Contenido generado por la IA");
      }
    } catch {
      toast.error("Error al conectar con la IA de la plataforma");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-1.5 my-2">
      <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">{label}</label>
      {isTextArea ? (
        <textarea
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          className="w-full p-2 text-xs border rounded bg-white dark:bg-black/20 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-white/10 focus:outline-none focus:border-primary"
          rows={4}
        />
      ) : (
        <input
          type="text"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          className="w-full p-2 text-xs border rounded bg-white dark:bg-black/20 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-white/10 focus:outline-none focus:border-primary"
        />
      )}
      {token && (
        <div className="flex gap-1 items-center mt-1">
          <input
            type="text"
            placeholder="Tema para la IA..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="flex-1 px-2 py-1 text-3xs border rounded bg-gray-50 dark:bg-white/5 border-gray-300 dark:border-white/10 text-gray-900 dark:text-gray-100 focus:outline-none"
          />
          <button
            type="button"
            onClick={handleAi}
            disabled={loading || !prompt.trim()}
            className="px-2 py-1 bg-primary hover:bg-primary-hover text-white text-3xs font-semibold rounded disabled:opacity-50 transition-colors flex items-center gap-0.5"
          >
            <Sparkles size={10} className={loading ? "animate-pulse" : ""} />
            {loading ? "Redactando..." : "Redactar IA"}
          </button>
        </div>
      )}
    </div>
  );
}
```

### 1.2 Current Block Schemas in `puckConfig`
Observation of lines 197-385 in `src/app/plataforma/cms/builder-puck/page.tsx`:

1. **Hero (`hero`)**:
   - `title`: `type: "custom"`, `render: ({ value, onChange }: any) => <AiTextInput label="Título Principal" value={value} onChange={onChange} token={token} />`
   - `body`: `type: "custom"`, `render: ({ value, onChange }: any) => <AiTextInput label="Cuerpo del Mensaje" value={value} onChange={onChange} isTextArea token={token} />`
   - `cta_label`: `type: "text", label: "Texto del Botón"` *(Standard Puck text field, no AI assistant)*
   - `cta_href`: `type: "text", label: "Enlace del Botón"`
   - `bg_image`: `type: "custom"`, `render: ... <MediaPickerField ... />`

2. **Rich Text (`rich_text`)**:
   - `title`: `type: "custom"`, `render: ({ value, onChange }: any) => <AiTextInput label="Título de la Sección" value={value} onChange={onChange} token={token} />`
   - `body`: `type: "custom"`, `render: ({ value, onChange }: any) => <AiTextInput label="Contenido de Texto" value={value} onChange={onChange} isTextArea token={token} />`
   - `cta_label`: `type: "text", label: "Texto del Enlace"`
   - `cta_href`: `type: "text", label: "Destino del Enlace"`

3. **CTA Banner (`cta_banner`)**:
   - `title`: `type: "custom"`, `render: ({ value, onChange }: any) => <AiTextInput label="Título" value={value} onChange={onChange} token={token} />`
   - `body`: `type: "custom"`, `render: ({ value, onChange }: any) => <AiTextInput label="Descripción" value={value} onChange={onChange} isTextArea token={token} />`
   - `cta_label`: `type: "text", label: "Botón Principal"` *(Standard Puck text field, no AI assistant)*
   - `cta_href`: `type: "text"`
   - `cta_label_2`: `type: "text", label: "Botón Secundario"`
   - `cta_href_2`: `type: "text"`

---

## 2. Logic Chain

### Step 1: Gap Analysis Against Milestone 3 Requirements
Requirement R3 (`ORIGINAL_REQUEST.md`) states:
- Integrar campos de asistencia de IA (`AiTextInput`) en inputs y textareas de Puck (títulos y cuerpos de Hero, Rich Text y CTA Banner).
- User prompt explicitly specifies:
  - Hero (title, subtitle/body)
  - Rich Text (body content)
  - CTA Banner (title, body, button_text)

Currently:
- `hero.title` and `hero.body` have `AiTextInput` registered. `hero.cta_label` is standard text.
- `rich_text.title` and `rich_text.body` have `AiTextInput` registered.
- `cta_banner.title` and `cta_banner.body` have `AiTextInput` registered, BUT `cta_banner.cta_label` (button_text) is standard text (`type: "text"`).

**Conclusion for Schemas**:
To satisfy requirement R3 completely, `cta_banner.cta_label` (and optionally `hero.cta_label`) should be updated to `type: "custom"` using `AiTextInput` (or AI-enabled input renderer for button texts).

### Step 2: Puck Custom Field API Mechanics
Puck's custom field API works as follows:
```ts
fieldSchema: {
  type: "custom",
  label?: string,
  render: ({ value, onChange, name, field, readOnly }: {
    value: any;
    onChange: (value: any) => void;
    name: string;
    field: CustomField;
    readOnly?: boolean;
  }) => ReactNode
}
```
When Puck renders the right-hand Inspector panel for a selected block:
1. Puck calls the `render` function passing the block's current field value as `value`.
2. Puck passes an `onChange` function. When `onChange(newValue)` is invoked by the custom component, Puck updates the block's state inside the visual builder tree and triggers a live preview update in the canvas.

### Step 3: Analysis of Trigger UX Approaches ("Redactar con IA")

#### Approach A: Inline Trigger (Current Implementation)
- **UI Structure**: Renders label + `<input>` or `<textarea>` + inline sub-bar with `input` ("Tema para la IA...") and `button` ("Redactar IA").
- **Pros**:
  - Direct execution with 0 context switches.
  - Very simple implementation without modal open/close states.
- **Cons**:
  - Permanently occupies ~30px vertical space per AI field in the sidebar.
  - Limited area for custom prompt instructions or tone selector chips.

#### Approach B: Drawer or Popover Modal Assistant (MediaPicker pattern)
- **UI Structure**: Renders label + `<input>` or `<textarea>` with a compact `<button>` (Sparkles icon) next to label or inside the field. Clicking opens a drawer or modal dialog ("Asistente de Redacción IA").
- **Pros**:
  - Clean sidebar layout.
  - Allows preset tone selectors ("Formal", "Entusiasta", "Corto", "Llamativo"), custom prompt input, and preview of generated text before applying to the field.
- **Cons**:
  - Requires modal overlay state.

#### Approach C: Compact Collapsible / Hybrid Inline Trigger (Recommended Target)
- **UI Structure**: Standard input/textarea with a small badge/button `<button>` ("✨ Redactar con IA") on the label line. Clicking toggles a collapsible inline prompt panel beneath the field.
- **Pros**:
  - Combines clean resting state with zero-modal inline convenience.
  - Preserves vertical sidebar space when closed.

### Step 4: Component Architecture & Refactoring Proposal
Currently `AiTextInput` is embedded directly within `src/app/plataforma/cms/builder-puck/page.tsx`.
We recommend extracting it into `src/components/cms/builder/AiTextInput.tsx`:

**Benefits**:
1. **Context decoupling**: By calling `const { token } = useAuth();` directly inside `AiTextInput.tsx`, `puckConfig` no longer needs to close over `token` from `page.tsx` or re-memoize when `token` changes.
2. **Clean schema definition**:
   ```tsx
   cta_banner: {
     fields: {
       title: {
         type: "custom",
         render: ({ value, onChange }) => (
           <AiTextInput label="Título" value={value} onChange={onChange} />
         )
       },
       body: {
         type: "custom",
         render: ({ value, onChange }) => (
           <AiTextInput label="Descripción" value={value} onChange={onChange} isTextArea />
         )
       },
       cta_label: {
         type: "custom",
         render: ({ value, onChange }) => (
           <AiTextInput label="Texto del Botón" value={value} onChange={onChange} placeholder="ej. Comenzar ahora" />
         )
       }
     }
   }
   ```
3. **Unit Testability**: Allows writing focused tests in `src/components/cms/builder/__tests__/AiTextInput.test.tsx`.

---

## 3. Caveats

1. **Read-Only Constraint**: No codebase files were edited during this investigation turn. All findings and proposals are presented for implementation by the implementer.
2. **API Endpoint Availability**: AI generation relies on `POST /system/ai/generate` returning `{ response: string }`. In testing environments, `apiFetch` must be mocked or return valid AI responses.
3. **Complex Block Scope**: `cards` and `gallery` blocks contain `arrayFields`. While `cards.title` and `cards.body` could also use `AiTextInput` in M4, M3 specifically targets Hero, Rich Text, and CTA Banner.

---

## 4. Conclusion

1. **Block Schemas Assessment**:
   - `hero`: `title` and `body` custom AI fields are registered. Recommendation: add AI assistance to `cta_label` (button text) as well.
   - `rich_text`: `title` and `body` custom AI fields are fully registered.
   - `cta_banner`: `title` and `body` custom AI fields are registered. Update `cta_label` (and `cta_label_2`) from `type: "text"` to `type: "custom"` using `AiTextInput` to complete requirement R3 (`title`, `body`, `button_text`).

2. **Custom Field API Integration**:
   - Puck's `type: "custom"` with `render: ({ value, onChange }) => ReactNode` works cleanly and updates block state reactively.
   - Extracting `AiTextInput` to `src/components/cms/builder/AiTextInput.tsx` using internal `useAuth()` simplifies `puckConfig` and improves maintainability.

---

## 5. Verification Method

### How to Verify Schemas & Rendering:
1. Run static type checking:
   ```bash
   npm run typecheck
   ```
2. Run schema registration unit tests:
   ```bash
   npx vitest run src/components/cms/builder/PuckSchemaRegistration.test.tsx
   ```
3. Inspect `capturedConfig.components` in test assertions:
   - Verify `capturedConfig.components.hero.fields.title.type === "custom"`
   - Verify `capturedConfig.components.hero.fields.body.type === "custom"`
   - Verify `capturedConfig.components.rich_text.fields.title.type === "custom"`
   - Verify `capturedConfig.components.rich_text.fields.body.type === "custom"`
   - Verify `capturedConfig.components.cta_banner.fields.title.type === "custom"`
   - Verify `capturedConfig.components.cta_banner.fields.body.type === "custom"`
   - Verify `capturedConfig.components.cta_banner.fields.cta_label.type === "custom"`

### Invalidation Conditions:
- If `capturedConfig.components.cta_banner.fields.cta_label.type` remains `"text"`, AI assistance will not be rendered for button text.
- If `render` function fails to forward `onChange` updates, block properties will not update in Puck state.

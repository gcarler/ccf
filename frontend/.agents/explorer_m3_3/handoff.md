# Handoff Report: AI Writing Assistant End-to-End Design & UX for Puck Editor

## 1. Observation

Direct codebase inspection revealed the following existing implementations and architectural structures:

1. **Current Inline Implementation in Puck Editor**:
   - Location: `src/app/plataforma/cms/builder-puck/page.tsx` (lines 19-95)
   - Functionality: An inline component `AiTextInput` renders a label, an `<input>` or `<textarea>`, and a lower row containing a prompt text input (`"Tema para la IA..."`) and a `"Redactar IA"` button with `Sparkles` icon.
   - Behavior: Calls `apiFetch<{ response: string }>("/system/ai/generate", { method: "POST", token, body: { prompt: ..., context: ... } })`.
   - Strips Markdown markers (`###`, `**Título:**`, `*`) from generated output before executing `onChange(clean)`.

2. **Custom Field Pattern in Puck**:
   - Component custom fields are declared in Puck config (lines 200-335 of `builder-puck/page.tsx`) with `type: "custom"`.
   - Example for Hero title and body:
     ```tsx
     title: {
       type: "custom",
       render: ({ value, onChange }: any) => (
         <AiTextInput label="Título Principal" value={value} onChange={onChange} token={token} />
       )
     }
     ```

3. **Existing Custom Field Reference Model (`MediaPickerField`)**:
   - Location: `src/components/cms/builder/MediaPickerField.tsx`
   - Unit test suite: `src/components/cms/builder/MediaPickerField.test.tsx`
   - Schema registration tests: `src/components/cms/builder/PuckSchemaRegistration.test.tsx`
   - Clean, modular component extracted into `src/components/cms/builder/` with 100% test coverage using Vitest and `@testing-library/react`.

4. **AI Generation Endpoint Contract**:
   - Route: `POST /system/ai/generate`
   - Request Body: `{ prompt: string, context?: string }`
   - Response: `{ response: string }`
   - Client Utility: `apiFetch` in `@/lib/http.ts` using Authorization header `Bearer ${token}`.

---

## 2. Logic Chain

From the observations above, we establish the step-by-step reasoning for the proposed design:

1. **Extraction to Reusable Component (`src/components/cms/builder/AiField.tsx`)**:
   - *Reasoning*: Keeping `AiTextInput` inline within `builder-puck/page.tsx` prevents isolated unit testing, bloats the page file, and forces manual token passing via `useMemo` closures. Extracting it to `AiField.tsx` allows using `useAuth()` internally and isolated testing.

2. **Popover / Expandable Card UI vs Always-Visible Row**:
   - *Reasoning*: Puck's Inspector sidebar is narrow (~300px). Rendering an inline prompt input and button on *every* text field consumes excessive vertical space and clutters the UI. A toggleable button (`"Redactar con IA"` / `<Sparkles />`) that expands a clean floating popover card only when needed optimizes Inspector UX.

3. **Contextual Prompt Suggestion Chips**:
   - *Reasoning*: Users often struggle with open-ended prompt fields. Providing contextual prompt chips (e.g., `"Título atractivo para sede"`, `"Descripción institucional"`, `"Llamado a la acción impactante"`) gives instant 1-click inspiration while keeping custom prompt input available.

4. **Seamless Integration with Puck `onChange`**:
   - *Reasoning*: Puck custom fields receive `value` and `onChange` callbacks. `AiField` acts as a controlled component that updates Puck state immediately on direct typing (`onChange(e.target.value)`) AND on AI generation (`onChange(generatedText)`). This ensures instant canvas live-re-rendering without extra state bridges.

5. **Vitest Unit Test Strategy**:
   - *Reasoning*: Standardizing tests on Vitest + Testing Library matching existing patterns in `MediaPickerField.test.tsx` allows mocking `apiFetch` for `/system/ai/generate` and `toast` notifications without real network overhead or external AI service dependencies.

---

## 3. Caveats

- **Network / API Availability**: If `/system/ai/generate` endpoint is offline or returns an error (500/503), `AiField` must fail gracefully with a user-friendly toast message (`toast.error("Error al conectar con la IA de la plataforma")`) without breaking manual editing.
- **Puck Sidebar Stacking Context**: If using absolute CSS popovers inside Puck's inspector sidebar, parent containers with `overflow: hidden` might clip the popover. Using a smooth inline expandable drawer/accordion inside `AiField` guarantees zero clipping issues across different themes and browsers.

---

## 4. Conclusion

### Component Design & Specification (`src/components/cms/builder/AiField.tsx`)

#### TypeScript Interface (`AiFieldProps`)
```typescript
export interface AiFieldProps {
  label?: string;
  value?: string;
  onChange: (value: string) => void;
  isTextArea?: boolean;
  fieldType?: "title" | "description" | "cta" | "body" | "general";
  suggestions?: string[];
  placeholder?: string;
  rows?: number;
  readOnly?: boolean;
  token?: string | null;
}
```

#### Proposed Implementation Code (`proposed_AiField.tsx`)
```tsx
"use client";

import React, { useState } from "react";
import { Sparkles, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export const DEFAULT_PROMPT_SUGGESTIONS: Record<string, string[]> = {
  title: [
    "Título atractivo para sede",
    "Bienvenida cálida e inspiradora",
    "Encabezado claro de sección",
    "Lema institucional de alto impacto",
  ],
  description: [
    "Descripción institucional breve",
    "Resumen de actividades comunitarias",
    "Misión y valores principales",
    "Mensaje de bienvenida",
  ],
  cta: [
    "Llamado a la acción impactante",
    "Invitación a conectar hoy",
    "Únete a nuestra comunidad",
    "Inscríbete a nuestros programas",
  ],
  body: [
    "Explicación detallada del ministerio",
    "Historia y visión de la sede",
    "Instrucciones de participación",
    "Mensaje inspirador de 2 párrafos",
  ],
  general: [
    "Redacción profesional y cercana",
    "Tono dinámico e invitador",
    "Resumen claro de 3 frases",
  ],
};

export default function AiField({
  label,
  value = "",
  onChange,
  isTextArea = false,
  fieldType = "general",
  suggestions,
  placeholder,
  rows = 4,
  readOnly = false,
  token: explicitToken,
}: AiFieldProps) {
  const { token: authToken } = useAuth();
  const token = explicitToken ?? authToken;

  const [isOpen, setIsOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);

  const activeSuggestions = suggestions || DEFAULT_PROMPT_SUGGESTIONS[fieldType] || DEFAULT_PROMPT_SUGGESTIONS.general;

  const handleGenerate = async (customPrompt?: string) => {
    const finalPrompt = (customPrompt || prompt).trim();
    if (!finalPrompt || !token) return;

    setLoading(true);
    try {
      const res = await apiFetch<{ response: string }>("/system/ai/generate", {
        method: "POST",
        token,
        body: {
          prompt: `Genera un ${
            isTextArea ? "texto claro y profesional de 2 párrafos" : "título llamativo"
          } sobre: "${finalPrompt}". Devuelve directamente el contenido sugerido sin comillas, introducciones ni explicaciones.`,
          context: `Redactor para página web institucional. Campo: ${label || fieldType}.`,
        },
      });

      if (res?.response) {
        const cleanText = res.response
          .replace(/^(###|\*\*Título:\*\*|\*\*Texto:\*\*|\*)/gm, "")
          .replace(/^["']|["']$/g, "")
          .trim();

        onChange(cleanText);
        toast.success("Contenido generado por la IA");
        setIsOpen(false);
      }
    } catch {
      toast.error("Error al conectar con la IA de la plataforma");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-1.5 my-2">
      {/* Label and AI Toggle Header */}
      <div className="flex items-center justify-between">
        {label && (
          <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
            {label}
          </label>
        )}
        {token && !readOnly && (
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="text-3xs font-semibold text-primary hover:text-primary-hover flex items-center gap-1 transition-colors px-1.5 py-0.5 rounded hover:bg-primary/10"
            title="Asistente de redacción IA"
          >
            <Sparkles size={11} className="text-amber-500" />
            <span>Redactar con IA</span>
            {isOpen ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          </button>
        )}
      </div>

      {/* Primary Controlled Input/Textarea */}
      {isTextArea ? (
        <textarea
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || "Escribe el contenido..."}
          disabled={readOnly}
          rows={rows}
          className="w-full p-2 text-xs border rounded bg-white dark:bg-black/20 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-white/10 focus:outline-none focus:border-primary disabled:opacity-50"
        />
      ) : (
        <input
          type="text"
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || "Escribe aquí..."}
          disabled={readOnly}
          className="w-full p-2 text-xs border rounded bg-white dark:bg-black/20 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-white/10 focus:outline-none focus:border-primary disabled:opacity-50"
        />
      )}

      {/* Expandable AI Assistant Card */}
      {isOpen && token && !readOnly && (
        <div className="mt-1 p-2.5 bg-gray-50 dark:bg-white/5 border border-primary/20 rounded-md shadow-sm space-y-2 text-xs animate-in fade-in duration-150">
          <div className="flex items-center justify-between">
            <span className="text-3xs font-semibold text-gray-600 dark:text-gray-400 flex items-center gap-1">
              <Sparkles size={10} className="text-amber-500" /> Sugerencias rápidas:
            </span>
          </div>

          {/* Contextual Prompt Chips */}
          <div className="flex flex-wrap gap-1">
            {activeSuggestions.map((chip, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setPrompt(chip);
                  handleGenerate(chip);
                }}
                disabled={loading}
                className="text-3xs px-2 py-0.5 bg-white dark:bg-black/30 hover:bg-primary/10 hover:text-primary border border-gray-200 dark:border-white/10 rounded transition-colors text-left truncate max-w-full"
              >
                + {chip}
              </button>
            ))}
          </div>

          {/* Prompt Input Row */}
          <div className="flex gap-1 items-center pt-1 border-t border-gray-200 dark:border-white/10">
            <input
              type="text"
              placeholder="Tema o instrucción personalizada..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleGenerate();
                }
              }}
              disabled={loading}
              className="flex-1 px-2 py-1 text-3xs border rounded bg-white dark:bg-black/30 border-gray-300 dark:border-white/10 text-gray-900 dark:text-gray-100 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => handleGenerate()}
              disabled={loading || !prompt.trim()}
              className="px-2.5 py-1 bg-primary hover:bg-primary-hover text-white text-3xs font-semibold rounded disabled:opacity-50 transition-colors flex items-center gap-1 shrink-0"
            >
              {loading ? (
                <>
                  <Loader2 size={10} className="animate-spin" />
                  <span>Generando...</span>
                </>
              ) : (
                <>
                  <Sparkles size={10} />
                  <span>Generar</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

### Puck Config Schema Integration Specification

In `src/app/plataforma/cms/builder-puck/page.tsx`:
```tsx
import AiField from "@/components/cms/builder/AiField";

// In puckConfig components definition:
components: {
  hero: {
    fields: {
      title: {
        type: "custom",
        render: ({ value, onChange }: any) => (
          <AiField label="Título Principal" value={value} onChange={onChange} fieldType="title" />
        )
      },
      body: {
        type: "custom",
        render: ({ value, onChange }: any) => (
          <AiField label="Cuerpo del Mensaje" value={value} onChange={onChange} isTextArea fieldType="body" />
        )
      },
      // ...
    }
  },
  rich_text: {
    fields: {
      title: {
        type: "custom",
        render: ({ value, onChange }: any) => (
          <AiField label="Título de Sección" value={value} onChange={onChange} fieldType="title" />
        )
      },
      body: {
        type: "custom",
        render: ({ value, onChange }: any) => (
          <AiField label="Contenido de Texto" value={value} onChange={onChange} isTextArea fieldType="body" />
        )
      }
    }
  },
  cta_banner: {
    fields: {
      title: {
        type: "custom",
        render: ({ value, onChange }: any) => (
          <AiField label="Título CTA" value={value} onChange={onChange} fieldType="cta" />
        )
      },
      body: {
        type: "custom",
        render: ({ value, onChange }: any) => (
          <AiField label="Descripción CTA" value={value} onChange={onChange} isTextArea fieldType="description" />
        )
      }
    }
  }
}
```

---

## 5. Verification Method

To independently verify the AI Writing Assistant design and implementation:

1. **Unit Testing Strategy (`src/components/cms/builder/AiField.test.tsx`)**:
   Run Vitest test suite:
   ```bash
   npm run test -- src/components/cms/builder/AiField.test.tsx
   ```
   *Expected Verification Outcomes*:
   - Component renders label, input, and "Redactar con IA" button when authenticated.
   - Clicking suggestion chip fills prompt input and triggers `apiFetch` to `/system/ai/generate`.
   - `onChange` is called with sanitized text response.
   - Toast success is called on completion; toast error is called on API failure.

2. **Puck Schema Registration Verification (`src/components/cms/builder/PuckSchemaRegistration.test.tsx`)**:
   Run Puck schema tests:
   ```bash
   npm run test -- src/components/cms/builder/PuckSchemaRegistration.test.tsx
   ```
   *Expected Verification Outcomes*:
   - Hero, Rich Text, and CTA Banner custom fields resolve to valid render functions returning `AiField`.

3. **Type Checking & Linting**:
   ```bash
   npm run typecheck
   npm run lint
   ```
   *Expected Outcome*: 0 errors, 0 warnings.

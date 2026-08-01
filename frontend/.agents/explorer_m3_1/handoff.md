# Handoff Report: AI Writing Assistant (`AiTextInput` & `/system/ai/generate`) Investigation

## 1. Observation

### Codebase Locations & Evidence
1. **Component Definition (`AiTextInput`)**:
   - File: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`
   - Lines 19-95:
     ```tsx
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

2. **Block Component Usages in Puck**:
   - File: `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`
   - **Hero (`hero`)**:
     - Line 203: `<AiTextInput label="Título Principal" value={value} onChange={onChange} token={token} />`
     - Line 209: `<AiTextInput label="Cuerpo del Mensaje" value={value} onChange={onChange} isTextArea token={token} />`
   - **Rich Text (`rich_text`)**:
     - Line 267: `<AiTextInput label="Título de la Sección" value={value} onChange={onChange} token={token} />`
     - Line 273: `<AiTextInput label="Contenido de Texto" value={value} onChange={onChange} isTextArea token={token} />`
   - **CTA Banner (`cta_banner`)**:
     - Line 321: `<AiTextInput label="Título" value={value} onChange={onChange} token={token} />`
     - Line 327: `<AiTextInput label="Descripción" value={value} onChange={onChange} isTextArea token={token} />`

3. **HTTP Client & Token Injection (`apiFetch`)**:
   - File: `/root/ccf/frontend/src/lib/http.ts`
   - Lines 114-123:
     ```ts
     let activeToken = token;
     if (!activeToken && typeof window !== 'undefined') {
       activeToken = sessionStorage.getItem('ccf_token');
     }
     if (activeToken) {
       finalHeaders.set("Authorization", `Bearer ${activeToken}`);
     }
     ```
   - Lines 95-103: Automatically injects `X-Request-ID` header.
   - Lines 134-137: Formats JSON payloads with `Content-Type: application/json`.

4. **URL Mapping (`apiUrl`)**:
   - File: `/root/ccf/frontend/src/lib/api.ts`
   - Line 10-13: `apiUrl("/system/ai/generate")` maps relative path `/system/ai/generate` to `/api/system/ai/generate` via `DEFAULT_API_URL = "/api"`.

5. **Backend Endpoint Definition**:
   - File: `/root/ccf/backend/api/system.py`
   - Lines 482-492:
     ```python
     @router.post("/ai/generate")
     async def ai_generate(payload: Dict[str, str], current_user: models.User = Depends(require_active_user)):
         """Genera contenido ministerial usando Llama 3 local."""
         prompt = payload.get("prompt", "")
         context = payload.get("context", "")

         if not prompt:
             raise HTTPException(status_code=400, detail="Falta el prompt")

         response = await generate_ministerial_content(prompt, context)
         return {"response": response}
     ```

6. **Other Existing AI Usages in Frontend**:
   - `/root/ccf/frontend/src/hooks/usePageBuilder.ts` (Line 647): Uses `/system/ai/generate` with template-driven prompts (AIDA, PAS, headlines, improve).
   - `/root/ccf/frontend/src/components/ui/UniversalCreationDrawer.tsx` (Line 225): Uses `/system/ai/generate` for task/project descriptions.
   - `/root/ccf/frontend/src/components/ui/TaskEditDrawer.tsx` (Line 200): Uses `/system/ai/generate` for ministerial productivity suggestions.

---

## 2. Logic Chain

1. **Endpoint Contract Verification**:
   - `POST /system/ai/generate` is routed to `/api/system/ai/generate` on the backend.
   - Request JSON payload: `{ "prompt": string, "context": string }`.
   - Backend requires `prompt` to be non-empty; otherwise throws `400 Bad Request` (`"Falta el prompt"`).
   - Backend requires active authentication via `Authorization: Bearer <token>`; otherwise returns `401 Unauthorized`.
   - Response JSON structure: `{ "response": string }`.

2. **Component Integration Verification**:
   - `AiTextInput` is fully integrated inside Puck's field rendering for the primary text blocks specified in Requirement R3:
     - `hero` block (Title and Body)
     - `rich_text` block (Title and Body)
     - `cta_banner` block (Title and Body)
   - When `token` is present, `AiTextInput` renders an inline prompt input (`"Tema para la IA..."`) and a trigger button (`"Redactar IA"`).

3. **Loading & UI State Verification**:
   - Button disables during execution (`disabled={loading || !prompt.trim()}`).
   - Loading icon (`Sparkles`) animates with `animate-pulse` and text updates to `"Redactando..."`.
   - Upon completion, response text is cleaned of Markdown prefix headers/bullets (`/^(###|\*\*Título:\*\*|\*\*Texto:\*\*|\*)/gm`) and passed to Puck's `onChange` callback.
   - Toast notifications alert the user (`toast.success("Contenido generado por la IA")` or `toast.error("Error al conectar con la IA de la plataforma")`).

4. **Authentication & Token Propagation**:
   - The token is retrieved from `useAuth()` in `PuckBuilderPage` (`src/app/plataforma/cms/builder-puck/page.tsx:100`).
   - Passed into `puckConfig` memoized closure (line 685: `[token]`), which passes `token` to every `AiTextInput` instance.
   - `apiFetch` includes `Authorization: Bearer ${token}` header when calling `/system/ai/generate`.

---

## 3. Caveats

- **Scope Limitation**: Other Puck blocks such as `faq`, `testimonials`, `stats`, `gallery`, and `cards` currently use standard Puck `type: "text"` or `type: "textarea"` rather than `AiTextInput`. This aligns with requirement R3 (which explicitly requested Hero, Rich Text, and CTA Banner), but if extended AI assistance for array fields is desired in future milestones, those fields would need `AiTextInput` wrapping.
- **Network / LLM Dependency**: If the backend LLM service is offline or cold starting, backend returns an error or slow response; `AiTextInput` catches the error gracefully and displays a Sonner toast error without breaking the Puck editor state.

---

## 4. Conclusion

The `AiTextInput` component and `/system/ai/generate` API integration for Milestone 3 (R3 AI Writing Assistant) are completely in place in `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx`.

Key verified characteristics:
- Endpoint: `POST /system/ai/generate`
- Payload: `{ prompt: string, context: string }`
- Response: `{ response: string }`
- Auth: `Authorization: Bearer ${token}` header auto-injected by `apiFetch`
- Component: `AiTextInput` wrapping `input` and `textarea` fields in `hero`, `rich_text`, and `cta_banner` blocks.
- Loading & Errors: Disabled button with pulsing `Sparkles` icon, Sonner success/error toasts, and markdown output cleanup.

---

## 5. Verification Method

To verify these findings independently:

1. **Inspect Code Files**:
   - Inspect `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` lines 19-95 to verify `AiTextInput` definition and lines 197-335 to check block field registrations.
   - Inspect `/root/ccf/backend/api/system.py` lines 482-492 to verify `POST /ai/generate` route definition and parameters.
   - Inspect `/root/ccf/frontend/src/lib/http.ts` lines 107-137 to verify header construction and token propagation.

2. **Run TypeScript Check**:
   - Command: `npm --prefix /root/ccf/frontend run typecheck`
   - Expected Result: 0 compilation errors.

3. **Invalidation Conditions**:
   - If `AiTextInput` is missing from `hero`, `rich_text`, or `cta_banner` block definitions in `builder-puck/page.tsx`.
   - If `apiFetch` fails to pass the `Authorization` header.
   - If the backend `/system/ai/generate` contract schema changes from `{ prompt, context }` -> `{ response }`.

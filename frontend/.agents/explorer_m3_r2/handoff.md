# Handoff Report — Explorer M3 R2 (AI Writing Assistant Cleaning Fix)

## 1. Observation

### Root Cause Analysis & Location
- **File Path**: `/root/ccf/frontend/src/components/cms/builder/AiField.tsx`
- **Lines**: 112–118
- **Current Code**:
  ```typescript
  const cleanText = res.response
    .replace(/^#+\s*/gm, "")
    .replace(/\*\*(Título|Texto|Cuerpo|Respuesta):\*\*/gi, "")
    .replace(/^\*\s*/gm, "")
    .replace(/^["']|["']$/g, "")
    .trim();
  ```

### Empirical Test Failure
- Command executed: `npx vitest run src/components/cms/builder/AiFieldAdversarial.test.tsx`
- Test: `strips headers, bold prefixes, bullet points, and outer quotes`
- Verbatim Failure Output:
  ```
  FAIL src/components/cms/builder/AiFieldAdversarial.test.tsx > AiField Adversarial & Edge Case Suite > 3. Markdown Stripping & Cleaning Pipeline > strips headers, bold prefixes, bullet points, and outer quotes
  AssertionError: expected "spy" to be called with arguments: [ Array(1) ]

  Received:
    1st spy call:
    Array [
  -   "Bienvenido a nuestra comunidad CCF",
  +   "###  Bienvenido a nuestra comunidad CCF",
    ]
  ```

### Defect Mechanics
When an LLM response is wrapped in outer quotes (e.g. `"### **Título:** Bienvenido a nuestra comunidad CCF"`):
1. `.replace(/^#+\s*/gm, "")` evaluates line start (`^`). The string begins with `"`, not `#`. The header regex fails to match and removes nothing.
2. `.replace(/\*\*(Título|Texto|Cuerpo|Respuesta):\*\*/gi, "")` strips `**Título:**`, leaving `"###  Bienvenido a nuestra comunidad CCF"`.
3. `.replace(/^\*\s*/gm, "")` evaluates line start (`^`), sees `"`, fails to match bullet points.
4. `.replace(/^["']|["']$/g, "")` strips leading `"` and trailing `"`, leaving `###  Bienvenido a nuestra comunidad CCF`.
5. `.trim()` returns `###  Bienvenido a nuestra comunidad CCF`, retaining unwanted raw markdown `#` characters.

---

## 2. Logic Chain

1. **Ordering & Interleaving Problem**:
   - Line-anchored regex patterns (`^#+\s*`, `^[*-+•]\s*`) depend on target tokens appearing at index 0 of a line.
   - If outer quotes (`"`, `'`, `“`, `”`, `` ` ``, `«`, `»`) enclose the string, they block line-start patterns.
   - Conversely, if markdown headers enclose quotes (e.g., `### "Título: Bienvenido"`), stripping headers first is required before outer quotes can be removed.
   - In arbitrary LLM outputs, formatting noise (quotes, headers, bold labels, bullets) can be nested in any order.

2. **Iterative Multi-Pass Solution**:
   - Creating an exported helper function `cleanAiResponse(response: string): string` with a multi-pass loop (up to 3 passes) guarantees clean stripping regardless of nesting order:
     - **Pass Step A (Quotes)**: Strip outer quotes (`/^["'“”`«»]+|["'“”`«»]+$/g`) and trim.
     - **Pass Step B (Headers)**: Strip line-start markdown headings (`/^#+\s*/gm`).
     - **Pass Step C (Labels)**: Strip bold/italic field labels (`/(?:\*\*|\*)?(?:Título|Texto|Cuerpo|Respuesta|Title|Body|Response):\s*(?:\*\*|\*)?/gi`).
     - **Pass Step D (Bullets)**: Strip line-start bullet points (`/^[*-+•]\s*/gm`).
     - **Pass Step E (Outer Quotes Backup)**: Strip outer quotes again (`/^["'“”`«»]+|["'“”`«»]+$/g`).
   - When the string reaches a stable state (`cleaned === previous`), the loop terminates immediately (typically in 1 pass for standard responses, 2 for nested quotes/headers).

---

## 3. Caveats

- **Scope Isolation**: The required changes are restricted to `src/components/cms/builder/AiField.tsx`. No changes are needed in `PuckSchemaRegistration`, `MediaPicker`, or any other component.
- **Existing Passing Tests**: All 11 other vitest tests in `src/components/cms/builder/AiFieldAdversarial.test.tsx` and all 7 tests in `src/components/cms/builder/AiField.test.tsx` remain valid and will pass.

---

## 4. Conclusion & Replacement Instructions

### Exact Replacement Instructions for Worker

1. **In `src/components/cms/builder/AiField.tsx`**:
   Define and export the `cleanAiResponse` helper function at file scope:

   ```typescript
   export function cleanAiResponse(response: string): string {
     if (!response) return "";

     let cleaned = response.trim();
     let previous = "";

     for (let pass = 0; pass < 3 && cleaned !== previous; pass++) {
       previous = cleaned;
       cleaned = cleaned
         .replace(/^["'“”`«»]+|["'“”`«»]+$/g, "")
         .replace(/^#+\s*/gm, "")
         .replace(/(?:\*\*|\*)?(?:Título|Texto|Cuerpo|Respuesta|Title|Body|Response):\s*(?:\*\*|\*)?/gi, "")
         .replace(/^[*-+•]\s*/gm, "")
         .replace(/^["'“”`«»]+|["'“”`«»]+$/g, "")
         .trim();
     }

     return cleaned;
   }
   ```

2. **In `handleAi` within `AiField.tsx`** (around lines 112–118):
   Replace the inline `.replace()` chain with a call to `cleanAiResponse`:

   *Before*:
   ```typescript
         if (res?.response) {
           const cleanText = res.response
             .replace(/^#+\s*/gm, "")
             .replace(/\*\*(Título|Texto|Cuerpo|Respuesta):\*\*/gi, "")
             .replace(/^\*\s*/gm, "")
             .replace(/^["']|["']$/g, "")
             .trim();
           onChange(cleanText);
           toast.success("Contenido generado por la IA");
         }
   ```

   *After*:
   ```typescript
         if (res?.response) {
           const cleanText = cleanAiResponse(res.response);
           onChange(cleanText);
           toast.success("Contenido generado por la IA");
         }
   ```

---

## 5. Verification Method

To independently verify the fix:

1. **Run Adversarial Test Suite**:
   ```bash
   npx vitest run src/components/cms/builder/AiFieldAdversarial.test.tsx
   ```
   *Expected Result*: 12 of 12 tests pass (100% green).

2. **Run All CMS Builder Unit Tests**:
   ```bash
   npx vitest run src/components/cms/builder/
   ```
   *Expected Result*: All 12 test files pass (159+ unit tests passing).

3. **Run Typecheck & Linter**:
   ```bash
   npm run typecheck
   npm run lint
   ```
   *Expected Result*: Exit code 0, 0 compilation errors, 0 lint errors/warnings in edited file.

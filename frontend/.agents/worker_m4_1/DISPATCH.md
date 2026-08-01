## 2026-07-31T21:08:36Z
You are teamwork_preview_worker_m4_1. Your working directory is /root/ccf/frontend/.agents/worker_m4_1.
Read /root/ccf/frontend/.agents/ORIGINAL_REQUEST.md and /root/ccf/frontend/.agents/orchestrator/PROJECT.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task: Implement Milestone 4 (R4 Complex Blocks Catalog - Gallery & Cards) in /root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx:

1. **Top-Level `defaultProps`**:
   - Add top-level `defaultProps` to `gallery` block with 3 default items (`{ url: "", alt: "Galería 1", caption: "Imagen 1" }`, etc.).
   - Add top-level `defaultProps` to `cards` block with 3 default card items (`{ title: "Tarjeta 1", body: "Descripción de la tarjeta 1...", cta_label: "Saber más", cta_href: "/", image_url: "" }`, etc.).

2. **Array Schema Enhancements (`getItemSummary`, `min`/`max`, `AiField`)**:
   - Enhance `getItemSummary` for `gallery` items to return distinct summaries: `(item, idx) => item.caption || (item.alt && item.alt !== "Imagen" ? item.alt : \`Imagen #${(idx ?? 0) + 1}\`)`.
   - Enhance `getItemSummary` for `cards` items to return distinct summaries: `(item, idx) => item.title || \`Tarjeta #${(idx ?? 0) + 1}\``.
   - Add `min: 1` and `max: 12` to `gallery.fields.items` array config.
   - Add `min: 1` and `max: 6` to `cards.fields.items` array config.
   - Integrate `<AiField token={token} fieldType="title" label="Título" value={value} onChange={onChange} />` and `<AiField token={token} fieldType="body" label="Descripción" value={value} onChange={onChange} />` for `cards` sub-element `title` and `body` fields in `arrayFields` (or top-level section fields).

3. **Rendering & Visual Polish (`render` functions)**:
   - Add empty array fallback: when `items` is empty (`itemList.length === 0`), display a helpful dashed placeholder box ("No hay imágenes/tarjetas agregadas. Añade elementos desde el panel lateral.").
   - Add empty image fallback: when `item.url` or `item.image_url` is blank/empty, render a clean "Sin imagen" visual placeholder badge instead of an empty black box or collapsing header.
   - Update `cards` grid to `grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6` (including `sm:grid-cols-2`).
   - Ensure all theme CSS variables use fallback values (`var(--site-surface, #001134)`, `var(--site-on-surface, #d9e2ff)`, `var(--site-outline-variant, rgba(255,255,255,0.1))`).

4. **Testing & Verification**:
   - Update unit test assertions in `src/components/cms/builder/PuckSchemaRegistration.test.tsx` to verify top-level `defaultProps` and array field schemas for `gallery` and `cards`.
   - Run `npm run typecheck` and verify 0 TypeScript errors.
   - Run `npx vitest run` and verify all tests pass.

Write your complete handoff report to /root/ccf/frontend/.agents/worker_m4_1/handoff.md including build and test outputs, and report completion via send_message to orchestrator (parent).

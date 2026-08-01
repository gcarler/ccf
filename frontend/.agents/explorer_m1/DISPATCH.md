## 2026-07-31T20:34:26Z
You are Explorer for Milestone 1 (R1 Theme & CSS Sync).
Working directory: /root/ccf/frontend/.agents/explorer_m1

Your task:
1. Read /root/ccf/frontend/.agents/ORIGINAL_REQUEST.md and /root/ccf/frontend/.agents/orchestrator/PROJECT.md.
2. Inspect `src/app/layout.tsx`, `tailwind.config.ts`, `src/app/public.css` (or `src/app/(public)/public.css`), and `src/app/plataforma/cms/builder-puck/page.tsx`.
3. Formulate the precise code modification plan for R1:
   - How to import `Outfit` from `next/font/google` in `src/app/layout.tsx` alongside `Inter` (with weights, subsets, variable `--font-outfit`, display swap).
   - How to add `${outfit.variable}` to the `<html>` element class list in `layout.tsx`.
   - How to update `tailwind.config.ts` to map `fontFamily.display` / `fontFamily.outfit` or `fontFamily.heading` to `["var(--font-outfit)", "sans-serif"]`.
   - Confirm `iframe={{ enabled: false }}` in `src/app/plataforma/cms/builder-puck/page.tsx` and verify that the Puck canvas root background uses `var(--site-background, ...)` and typography uses `var(--font-outfit)` / `var(--font-inter)`.
4. Write your detailed step-by-step recommendation and line-by-line diff specification to /root/ccf/frontend/.agents/explorer_m1/handoff.md. Update progress.md and send a completion message.

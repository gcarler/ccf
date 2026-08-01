# Milestone 1 (R1 Theme & CSS Sync) — Challenger Handoff Report

## Verdict
**REQUEST_CHANGES**

---

## 1. Observation

### Verified Passing Criteria
- **Font Variables & Setup**:
  - `src/app/layout.tsx` correctly imports `Roboto`, `Open_Sans`, `Inter`, and `Outfit` from `next/font/google`.
  - Font CSS variables `--font-roboto`, `--font-open-sans`, `--font-inter`, `--font-outfit` are defined and bound to the root `<html>` tag (`className={`${roboto.variable} ${openSans.variable} ${inter.variable} ${outfit.variable}`}`).
  - `tailwind.config.ts` correctly maps font families (`outfit`, `heading`, `display`, `sans`, `headline`, `body`, `label`, `mono`) with appropriate static fallbacks (`"Outfit", "sans-serif"`, `"Roboto"`, `"Inter"`).
  - `src/app/globals.css` and `src/app/(public)/public.css` define font token fallbacks (e.g. `--font-outfit: var(--font-outfit, 'Outfit'), sans-serif;` and `--ccf-font-display: var(--font-outfit, var(--font-headline, 'Outfit', 'Roboto', sans-serif));`).
  - `src/app/plataforma/cms/builder-puck/page.tsx` uses font variables with safe fallbacks (`var(--font-inter, sans-serif)`, `var(--font-outfit, sans-serif)`).
- **TypeScript Typecheck**:
  - Executed `npm run typecheck` (`npm run typegen && tsc --noEmit`): **PASSED** with exit code 0.
- **Theme Equivalence**:
  - In `src/app/(public)/public.css`, all 3 dynamic themes (`.theme-light`, `.theme-institutional`, `.theme-dark`) define an identical set of 54 `--site-*` CSS variables.

### Discovered Failure Mode & Defect
- **Desynchronized `--site-*` Variables between `tailwind.config.ts` and `public.css`**:
  - `tailwind.config.ts` exposes 47 `site-*` color tokens that reference CSS variables in the form `var(--site-*)`.
  - **25 out of the 47 `site-*` tokens** in `tailwind.config.ts` map to `--site-*` CSS variables that are **NOT defined** in `src/app/(public)/public.css` or `src/app/globals.css`.
  - Missing CSS variables:
    1. `--site-on-tertiary-fixed-variant`
    2. `--site-inverse-primary`
    3. `--site-secondary-fixed-dim`
    4. `--site-on-error-container`
    5. `--site-tertiary-fixed-dim`
    6. `--site-inverse-surface`
    7. `--site-tertiary`
    8. `--site-surface-container-high`
    9. `--site-error-container`
    10. `--site-on-primary-container`
    11. `--site-on-error`
    12. `--site-on-secondary`
    13. `--site-tertiary-fixed`
    14. `--site-inverse-on-surface`
    15. `--site-surface-variant`
    16. `--site-on-primary-fixed-variant`
    17. `--site-on-tertiary-fixed`
    18. `--site-on-primary-fixed`
    19. `--site-secondary-fixed`
    20. `--site-on-tertiary`
    21. `--site-on-tertiary-container`
    22. `--site-primary-fixed`
    23. `--site-tertiary-container`
    24. `--site-on-secondary-fixed-variant`
    25. `--site-on-secondary-fixed`
- **Active Usage Defect**:
  - In `src/app/(public)/sedes/page.tsx:109`, the UI uses `hover:bg-site-surface-container-high`.
  - Because `site-surface-container-high` maps to `var(--site-surface-container-high)` and `--site-surface-container-high` is missing from `public.css`, hovering over location items in `/sedes` fails to render the intended container highlight background.

---

## 2. Logic Chain

1. `tailwind.config.ts` acts as the single contract for utility class generation (`bg-site-*`, `text-site-*`).
2. When a class like `hover:bg-site-surface-container-high` or `bg-site-tertiary` is compiled by Tailwind, it emits CSS output using `var(--site-surface-container-high)`.
3. Browsers evaluating `var(--site-surface-container-high)` find no matching custom property definition in `.theme-light`, `.theme-institutional`, or `.theme-dark` in `public.css`.
4. As custom CSS variable resolution without inline fallbacks evaluates to `invalid / initial`, the visual background/text styling breaks silently at runtime.
5. Therefore, Theme & CSS Sync for Milestone 1 is incomplete until either the 25 missing `--site-*` variables are added to all theme classes in `public.css` or removed from `tailwind.config.ts` if unused.

---

## 3. Caveats

- `npm run typecheck` passes because CSS variable mappings in `tailwind.config.ts` are string keys evaluated at CSS compilation time, not static TypeScript types.
- UI elements that rely solely on the 29 `--site-*` variables present in `public.css` (such as `site-primary`, `site-background`, `site-on-surface`, `site-surface-container-lowest`) work as expected.
- No modifications were made to implementation files during this review.

---

## 4. Conclusion

Milestone 1 satisfies font variable definitions, typechecking, and structural theme setup. However, it fails empirical contract synchronization between `tailwind.config.ts` and `public.css`, causing missing CSS custom properties and broken hover states (e.g. `hover:bg-site-surface-container-high` in `/sedes`).

**Verdict: REQUEST_CHANGES**

---

## 5. Verification Method

To verify these findings independently:

1. **Run the empirical M1 test script**:
   ```bash
   node /root/ccf/frontend/.agents/challenger_m1_1/verify_m1.js
   ```
2. **Inspect missing variable usages**:
   ```bash
   grep -rn "site-surface-container-high" /root/ccf/frontend/src/app
   ```
3. **Verify typecheck**:
   ```bash
   npm run typecheck
   ```

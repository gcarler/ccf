# Milestone 1 Round 2 (R1 Theme & CSS Sync Remediation) — Explorer Handoff Report

## 1. Observation

### Empirical Baseline Verification
- Executed Challenger 1's verification script: `node /root/ccf/frontend/.agents/challenger_m1_1/verify_m1.js`.
- Output confirmed:
  - Font setup & bindings (`--font-roboto`, `--font-open-sans`, `--font-inter`, `--font-outfit`): **PASSED**
  - Theme structure equality across `.theme-light`, `.theme-institutional`, `.theme-dark`: **PASSED** (all 3 currently define 54 `--site-*` variables).
  - Tailwind site color contract: **FAILED** with 25 missing `--site-*` CSS custom properties.

### Contract Analysis between `tailwind.config.ts` and `src/app/(public)/public.css`
- `tailwind.config.ts` (lines 47–93) defines **47 `site-*` color tokens** mapping to `var(--site-*)`.
- `public.css` currently defines only **22 palette tokens** (lines 15–36 for `.theme-light`, lines 75–96 for `.theme-institutional`, lines 136–157 for `.theme-dark`), plus 32 UI/effect/gradient tokens.
- **Missing CSS Custom Properties**: Exactly 25 `--site-*` variables referenced in `tailwind.config.ts` are missing from all three themes in `public.css`:
  1. `--site-surface-container-high`
  2. `--site-inverse-primary`
  3. `--site-secondary-fixed-dim`
  4. `--site-on-error-container`
  5. `--site-tertiary-fixed-dim`
  6. `--site-inverse-surface`
  7. `--site-tertiary`
  8. `--site-error-container`
  9. `--site-on-primary-container`
  10. `--site-on-error`
  11. `--site-on-secondary`
  12. `--site-tertiary-fixed`
  13. `--site-inverse-on-surface`
  14. `--site-surface-variant`
  15. `--site-on-primary-fixed-variant`
  16. `--site-on-tertiary-fixed`
  17. `--site-on-primary-fixed`
  18. `--site-secondary-fixed`
  19. `--site-on-tertiary`
  20. `--site-on-tertiary-container`
  21. `--site-primary-fixed`
  22. `--site-tertiary-container`
  23. `--site-on-secondary-fixed-variant`
  24. `--site-on-secondary-fixed`
  25. `--site-on-tertiary-fixed-variant`

### Concrete Failure Example
- In `src/app/(public)/sedes/page.tsx` line 109:
  `className="... border-transparent bg-site-surface-container hover:bg-site-surface-container-high"`
- Tailwind compiles `hover:bg-site-surface-container-high` into `background-color: var(--site-surface-container-high)`.
- Because `--site-surface-container-high` is missing in `public.css`, browser evaluation fails, rendering hover background as invalid/un-styled.

---

## 2. Logic Chain

1. **Tailwind Class Compilation**: Tailwind CSS maps utility class prefixes like `bg-site-*` and `text-site-*` to CSS custom properties `var(--site-*)` defined in `tailwind.config.ts`.
2. **CSS Variable Resolution**: At runtime, browsers evaluate `var(--site-*)` against the active theme scope class (`.theme-light`, `.theme-institutional`, or `.theme-dark`).
3. **Contract Completeness**: If `tailwind.config.ts` declares a `site-*` key, every active theme selector in `public.css` MUST define the corresponding `--site-*` custom property.
4. **Material Design 3 Palette Formulation**:
   - Each missing token belongs to a standard Material Design 3 functional color role (Surface Hierarchy, Inverted Surfaces, Primary Fixed family, Secondary Fixed family, Tertiary family, and Error family).
   - `.theme-light` requires light surface tones, dark text on surfaces, and high contrast container pairings.
   - `.theme-institutional` requires monochromatic deep blue surface steps (`#001134` / `#000d2a` / `#001944` / `#021d4a` / `#132854` / `#1d3361`), with light cyan/blue text & fixed accents (`#d9e2ff` / `#a5c8ff` / `#ffffff`).
   - `.theme-dark` requires high-contrast dark gray/black surface steps (`#0a0a0a` / `#000000` / `#0f0f0f` / `#121212` / `#171717` / `#1a1a1a`), with pure white/light gray text & fixed accents (`#ffffff` / `#eeeeee`).
5. **Simulation & Validation**:
   - Adding these 25 tokens expands the palette set from 54 to 79 variables per theme.
   - Running the contract matching algorithm against the updated `public.css` yields **0 missing tokens**.

---

## 3. Caveats

- **Read-Only Scope**: Explorer operated strictly in read-only mode for application code under `src/app`. No changes were applied directly to `src/app/(public)/public.css`.
- **Patch Provision**: The precise diff specification and ready-to-apply patch file have been generated in `.agents/explorer_m1_r2/public_css_remediation.patch`.
- **Type Checking**: `npm run typecheck` remains passing (exit code 0) as CSS variable names are string mappings processed during CSS build step rather than TypeScript static types.

---

## 4. Conclusion

To remediate Milestone 1 Theme & CSS synchronization completely, the implementer must append the following 25 CSS variable definitions to `.theme-light`, `.theme-institutional`, and `.theme-dark` in `src/app/(public)/public.css`.

### Formulated Color Values by Theme

| # | CSS Variable Name | `.theme-light` Value | `.theme-institutional` Value | `.theme-dark` Value | Functional Role / Purpose |
|---|---|---|---|---|---|
| 1 | `--site-surface-container-high` | `#e2e7f0` | `#132854` | `#171717` | Elevated container step (e.g. location card hover) |
| 2 | `--site-surface-variant` | `#dfe2eb` | `#253966` | `#262626` | Muted surface variant for inputs & cards |
| 3 | `--site-inverse-surface` | `#2e3137` | `#d9e2ff` | `#eeeeee` | Inverted background for toasts/snackbars |
| 4 | `--site-inverse-on-surface` | `#f0f0f7` | `#001134` | `#0a0a0a` | Text on inverted surface |
| 5 | `--site-inverse-primary` | `#a5c8ff` | `#005faf` | `#000000` | Inverted primary color on inverse surface |
| 6 | `--site-primary-fixed` | `#d4e3ff` | `#d4e3ff` | `#ffffff` | Fixed primary accent background |
| 7 | `--site-on-primary-fixed` | `#001c3b` | `#001c3b` | `#000000` | High-contrast text on fixed primary |
| 8 | `--site-on-primary-fixed-variant` | `#00477b` | `#00477b` | `#333333` | Muted text on fixed primary |
| 9 | `--site-on-primary-container` | `#001c3b` | `#d4e3ff` | `#ffffff` | Text/icons inside primary container |
| 10 | `--site-on-secondary` | `#ffffff` | `#00344f` | `#000000` | Text/icons on secondary color |
| 11 | `--site-secondary-fixed` | `#c5e7ff` | `#c5e7ff` | `#e0e0e0` | Fixed secondary accent background |
| 12 | `--site-secondary-fixed-dim` | `#9bcdf0` | `#80d0ff` | `#cccccc` | Dimmed fixed secondary tone |
| 13 | `--site-on-secondary-fixed` | `#001e2e` | `#001e2e` | `#000000` | Text on fixed secondary |
| 14 | `--site-on-secondary-fixed-variant` | `#004d6d` | `#004d6d` | `#444444` | Muted text on fixed secondary |
| 15 | `--site-tertiary` | `#006874` | `#7fd0ff` | `#dddddd` | Tertiary brand accent |
| 16 | `--site-on-tertiary` | `#ffffff` | `#00344d` | `#000000` | Text/icons on tertiary color |
| 17 | `--site-tertiary-container` | `#97f0ff` | `#004c6d` | `#2a2a2a` | Tertiary container surface |
| 18 | `--site-on-tertiary-container` | `#001f24` | `#c6e7ff` | `#ffffff` | Text inside tertiary container |
| 19 | `--site-tertiary-fixed` | `#97f0ff` | `#c6e7ff` | `#eeeeee` | Fixed tertiary accent background |
| 20 | `--site-tertiary-fixed-dim` | `#7ed4e6` | `#7fd0ff` | `#dddddd` | Dimmed fixed tertiary tone |
| 21 | `--site-on-tertiary-fixed` | `#001f24` | `#001e2d` | `#000000` | Text on fixed tertiary |
| 22 | `--site-on-tertiary-fixed-variant` | `#004f58` | `#004c6d` | `#444444` | Muted text on fixed tertiary |
| 23 | `--site-on-error` | `#ffffff` | `#690005` | `#690005` | Text/icons on error background |
| 24 | `--site-error-container` | `#ffdad6` | `#93000a` | `#93000a` | Error container surface |
| 25 | `--site-on-error-container` | `#410002` | `#ffdad6` | `#ffdad6` | Text inside error container |

### Exact Code Additions to `src/app/(public)/public.css`

#### 1. Add to `.theme-light` (after `--site-outline: #72777f;` at line 36):
```css
  /* --- Material Design 3 Site Palette Tokens (Remediation Round 2) --- */
  --site-surface-container-high: #e2e7f0;
  --site-surface-variant: #dfe2eb;
  --site-inverse-surface: #2e3137;
  --site-inverse-on-surface: #f0f0f7;
  --site-inverse-primary: #a5c8ff;
  --site-primary-fixed: #d4e3ff;
  --site-on-primary-fixed: #001c3b;
  --site-on-primary-fixed-variant: #00477b;
  --site-on-primary-container: #001c3b;
  --site-on-secondary: #ffffff;
  --site-secondary-fixed: #c5e7ff;
  --site-secondary-fixed-dim: #9bcdf0;
  --site-on-secondary-fixed: #001e2e;
  --site-on-secondary-fixed-variant: #004d6d;
  --site-tertiary: #006874;
  --site-on-tertiary: #ffffff;
  --site-tertiary-container: #97f0ff;
  --site-on-tertiary-container: #001f24;
  --site-tertiary-fixed: #97f0ff;
  --site-tertiary-fixed-dim: #7ed4e6;
  --site-on-tertiary-fixed: #001f24;
  --site-on-tertiary-fixed-variant: #004f58;
  --site-on-error: #ffffff;
  --site-error-container: #ffdad6;
  --site-on-error-container: #410002;
```

#### 2. Add to `.theme-institutional` (after `--site-outline: #8c919b;` at line 96):
```css
  /* --- Material Design 3 Site Palette Tokens (Remediation Round 2) --- */
  --site-surface-container-high: #132854;
  --site-surface-variant: #253966;
  --site-inverse-surface: #d9e2ff;
  --site-inverse-on-surface: #001134;
  --site-inverse-primary: #005faf;
  --site-primary-fixed: #d4e3ff;
  --site-on-primary-fixed: #001c3b;
  --site-on-primary-fixed-variant: #00477b;
  --site-on-primary-container: #d4e3ff;
  --site-on-secondary: #00344f;
  --site-secondary-fixed: #c5e7ff;
  --site-secondary-fixed-dim: #80d0ff;
  --site-on-secondary-fixed: #001e2e;
  --site-on-secondary-fixed-variant: #004d6d;
  --site-tertiary: #7fd0ff;
  --site-on-tertiary: #00344d;
  --site-tertiary-container: #004c6d;
  --site-on-tertiary-container: #c6e7ff;
  --site-tertiary-fixed: #c6e7ff;
  --site-tertiary-fixed-dim: #7fd0ff;
  --site-on-tertiary-fixed: #001e2d;
  --site-on-tertiary-fixed-variant: #004c6d;
  --site-on-error: #690005;
  --site-error-container: #93000a;
  --site-on-error-container: #ffdad6;
```

#### 3. Add to `.theme-dark` (after `--site-outline: #555555;` at line 157):
```css
  /* --- Material Design 3 Site Palette Tokens (Remediation Round 2) --- */
  --site-surface-container-high: #171717;
  --site-surface-variant: #262626;
  --site-inverse-surface: #eeeeee;
  --site-inverse-on-surface: #0a0a0a;
  --site-inverse-primary: #000000;
  --site-primary-fixed: #ffffff;
  --site-on-primary-fixed: #000000;
  --site-on-primary-fixed-variant: #333333;
  --site-on-primary-container: #ffffff;
  --site-on-secondary: #000000;
  --site-secondary-fixed: #e0e0e0;
  --site-secondary-fixed-dim: #cccccc;
  --site-on-secondary-fixed: #000000;
  --site-on-secondary-fixed-variant: #444444;
  --site-tertiary: #dddddd;
  --site-on-tertiary: #000000;
  --site-tertiary-container: #2a2a2a;
  --site-on-tertiary-container: #ffffff;
  --site-tertiary-fixed: #eeeeee;
  --site-tertiary-fixed-dim: #dddddd;
  --site-on-tertiary-fixed: #000000;
  --site-on-tertiary-fixed-variant: #444444;
  --site-on-error: #690005;
  --site-error-container: #93000a;
  --site-on-error-container: #ffdad6;
```

---

## 5. Verification Method

To verify the remediation independently after applying the patch:

1. **Run the empirical verification script**:
   ```bash
   node /root/ccf/frontend/.agents/challenger_m1_1/verify_m1.js
   ```
   *Expected result*:
   - `--site-*` variables count per theme: **79**
   - Missing variables mapped in `tailwind.config.ts`: **0**
   - Verdict: All 47 `site-*` color mappings in `tailwind.config.ts` pass matching validation.

2. **Verify TypeScript compilation**:
   ```bash
   npm run typecheck
   ```
   *Expected result*: Exit code 0 with 0 errors.

3. **Verify visual UI behavior**:
   - Inspect `/sedes` page hover interactions on location items (`hover:bg-site-surface-container-high`). Hover highlights render smoothly without falling back to unstyled/transparent backgrounds.

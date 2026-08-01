# Handoff Report — Challenger 2 (Milestone 1: R1 Theme & CSS Sync)

**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct code and execution observations across `/root/ccf/frontend`:

### A. Build and Lint Verification
- Command: `npm run typecheck`
  - Output: `✓ Route types generated successfully` — Exit Code: 0 (PASSED)
- Command: `npm run lint`
  - Output: `0 errors, 1 warning` (`src/app/plataforma/crm/messaging/[id]/page.tsx:76:8 warning React Hook useEffect has a missing dependency: 'addToast'`) — Exit Code: 0 (PASSED)

### B. Code Inspections & Verbatim Evidence

1. **Puck Editor Canvas Heading Squashing (`builder-puck/page.tsx` & `globals.css` & `WorkspaceLayout.tsx`)**:
   - `src/app/plataforma/cms/builder-puck/page.tsx:890`:
     ```tsx
     <Puck config={puckConfig} data={initialData} onPublish={handlePublish} iframe={{ enabled: false }} />
     ```
   - `src/app/plataforma/cms/layout.tsx:11`:
     ```tsx
     <WorkspaceLayout allowedPermissions={['cms:read']}>
     ```
   - `src/components/WorkspaceLayout.tsx:383`:
     ```tsx
     <div className="workspace-platform flex h-[100dvh] w-full flex-col ...">
     ```
   - `src/app/globals.css:241-246`:
     ```css
     .workspace-platform h1 {
       font-size: var(--text-xl);
       font-family: var(--font-headline);
       font-weight: var(--weight-semibold);
       line-height: var(--leading-tight);
     }
     ```
   - `src/app/plataforma/cms/builder-puck/page.tsx:261-264` (Hero Component Render):
     ```tsx
     <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl md:text-5xl" ...>
     ```

2. **Self-Referencing Cyclic CSS Variable Loop (`globals.css`)**:
   - `src/app/globals.css:98`:
     ```css
     --font-outfit: var(--font-outfit, 'Outfit'), sans-serif;
     ```
   - `src/app/globals.css:99-100`:
     ```css
     --font-display: var(--font-outfit, 'Outfit'), var(--font-roboto, 'Roboto'), ...;
     --font-headline: var(--font-outfit, 'Outfit'), var(--font-roboto, 'Roboto'), ...;
     ```

3. **Invalid HSL Syntax in Dark Mode Token (`globals.css`)**:
   - `src/app/globals.css:160`:
     ```css
     [data-theme="night"] {
       ...
       --border-glass: 255 255% 255% / 0.05;
     }
     ```

4. **Asymmetric Body Text Color in Dark Mode (`layout.tsx`)**:
   - `src/app/layout.tsx:96`:
     ```tsx
     <body className="font-display antialiased text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] bg-background-light dark:bg-background-dark min-h-screen">
     ```
   - `src/app/globals.css:215-217`:
     ```css
     body {
       background-color: hsl(var(--bg-primary));
       color: hsl(var(--text-primary));
     }
     ```

---

## 2. Logic Chain

### Failure Mode 1: Puck Editor WYSIWYG Heading Squashing (High Severity)
1. `PuckBuilderPage` (`/plataforma/cms/builder-puck`) is wrapped inside `CmsLayout` (`/plataforma/cms/layout.tsx`), which mounts `WorkspaceLayout`.
2. `WorkspaceLayout` attaches the class `.workspace-platform` to the top-level container element.
3. In `globals.css`, `.workspace-platform h1` has CSS specificity `(0, 1, 1)` (1 class + 1 tag element).
4. `PuckBuilderPage` configures `<Puck iframe={{ enabled: false }} />`. As a result, the canvas editor elements render directly within the parent document DOM (inside `.workspace-platform`), rather than inside an isolated `<iframe>`.
5. Hero banner blocks inside Puck render `<h1 className="text-3xl font-extrabold ... sm:text-4xl md:text-5xl">`.
6. Tailwind utility `.text-3xl` has CSS specificity `(0, 1, 0)` (1 class).
7. Specificity `(0, 1, 1)` of `.workspace-platform h1` strictly overrides `(0, 1, 0)` of `.text-3xl`/`.text-4xl`/`.text-5xl`.
8. Consequently, inside the Puck editor canvas, all Hero `<h1>` headings are forced down to `var(--text-xl)` (1.125rem / 18px), destroying WYSIWYG fidelity. Same applies to `<h2>` (forced to 16px) and `<h3>` (forced to 14px).

### Failure Mode 2: Cyclic Custom Property Definition (Medium Severity)
1. `src/app/globals.css` defines `:root { --font-outfit: var(--font-outfit, 'Outfit'), sans-serif; }`.
2. A CSS custom property declared on an element that references `var()` of its own name is classified by CSS Custom Properties Level 1 Spec (§3) as a **cyclic dependency**.
3. Custom properties with cyclic dependencies are treated as **invalid at computed-value time** (`unset`).
4. Any variable referencing `var(--font-outfit)` (such as `--font-display` or `--font-headline`) receives an invalid/unset variable token, causing the browser to fall back to generic system `sans-serif` rather than the font preloaded by `next/font/google`.

### Failure Mode 3: Malformed HSL Syntax in Night Theme (Medium Severity)
1. In `src/app/globals.css:160`, `[data-theme="night"]` defines `--border-glass: 255 255% 255% / 0.05;`.
2. CSS `hsl()` function expects hue (0-360), saturation (0%-100%), and lightness (0%-100%).
3. Passing `255%` for saturation and lightness is invalid CSS syntax (mix of RGB integer 255 with HSL percentage symbol `%`).
4. Any CSS utility relying on `hsl(var(--border-glass))` fails to compute properly in dark mode.

### Failure Mode 4: Dark Mode Unstyled Body Text Color Asymmetry (Low/Medium Severity)
1. `layout.tsx:96` specifies `text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]`.
2. In light mode, body uses `--text-primary` (`hsl(222 47% 11%)`, high contrast).
3. In dark mode, body uses `--text-secondary` (`hsl(215 20.2% 65.1%)`, muted gray).
4. `globals.css:216` declares `body { color: hsl(var(--text-primary)); }` for both light and dark modes (`--text-primary` in dark mode is `210 40% 98%`, near white).
5. The specificity of `.dark .dark\:text-...` on `<body>` overrides `globals.css` body rule, turning all default/inherited text across dark mode into muted gray instead of high-contrast text.

---

## 3. Caveats

- **No code changes made**: As an Empirical Challenger, no production implementation files were modified. Only a non-destructive verification script was written to `scratch/test_css_bugs.js`.
- **Runtime Puck drag-and-drop state**: Puck canvas interactivity and state persistence were verified via static analysis and CSS scope tracing; full live E2E browser interactions require active backend API server authentication.

---

## 4. Conclusion

**Verdict**: **REQUEST_CHANGES**

While `npm run typecheck` and `npm run lint` both pass without errors, the CSS architecture contains critical scope leakage and syntax bugs that degrade the Puck CMS Editor and platform dark mode:

1. **High Priority**: Fix Puck canvas heading squashing. When `iframe={{ enabled: false }}` is used, Puck canvas must be isolated from `.workspace-platform h1..h6` specificity rules (e.g. by scope reset class or enabling iframe rendering if possible, or increasing specificity on block components).
2. **Medium Priority**: Fix cyclic `--font-outfit` definition in `globals.css`. Line 98 should be removed or changed to not reference `--font-outfit` recursively.
3. **Medium Priority**: Fix invalid HSL syntax in `globals.css:160` (`--border-glass: 255 255% 255% / 0.05;` -> `0 0% 100% / 0.05;`).
4. **Low/Medium Priority**: Synchronize body dark mode text in `layout.tsx:96` to `dark:text-[hsl(var(--text-primary))]` (or remove the inline text color override to let `globals.css` rule take effect).

---

## 5. Verification Method

To independently verify these findings:

1. **Typecheck & Lint**:
   ```bash
   cd /root/ccf/frontend
   npm run typecheck
   npm run lint
   ```
2. **Run Automated Empirical CSS Stress-Test**:
   ```bash
   cd /root/ccf/frontend
   node scratch/test_css_bugs.js
   ```
3. **Inspect CSS Specificity in puck canvas**:
   - Inspect `.workspace-platform h1` vs `.text-3xl` specificity in `src/app/globals.css` vs `src/app/plataforma/cms/builder-puck/page.tsx`.
   - Inspect line 98 and line 160 of `src/app/globals.css`.

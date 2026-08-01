# Handoff Report — Explorer Milestone 1 (R1 Theme & CSS Sync)

## 1. Observation

### File Findings & Current State

1. **`src/app/layout.tsx`**
   - **Line 2**: Currently imports `import { Roboto, Inter, Open_Sans } from "next/font/google";`. `Outfit` font is NOT yet imported.
   - **Lines 6-28**: Defines font loaders for `roboto`, `openSans`, and `inter`. No `outfit` declaration exists.
   - **Line 65**: `<html lang="es" suppressHydrationWarning className={`${roboto.variable} ${openSans.variable} ${inter.variable}`}>`. The CSS variable `${outfit.variable}` (`--font-outfit`) is missing from the `<html>` element class list.

2. **`tailwind.config.ts`**
   - **Lines 95-105**:
     ```typescript
     fontFamily: {
         "display":  ["var(--font-roboto)", "Roboto", "var(--font-open-sans)", "Open Sans", "var(--font-inter)", "Inter", "-apple-system", "sans-serif"],
         "sans":     ["var(--font-roboto)", "Roboto", "var(--font-open-sans)", "Open Sans", "var(--font-inter)", "Inter", "-apple-system", "sans-serif"],
         "headline": ["var(--font-roboto)", "Roboto", "var(--font-open-sans)", "Open Sans", "-apple-system", "sans-serif"],
         "body":     ["var(--font-inter)", "Inter", "-apple-system", "sans-serif"],
         "label":    ["var(--font-inter)", "Inter", "-apple-system", "sans-serif"],
         "mono":     ["JetBrains Mono", "Fira Code", "ui-monospace", "monospace"],
     },
     ```
   - `fontFamily.display`, `fontFamily.heading`, and `fontFamily.outfit` are not currently mapped to `var(--font-outfit)`.

3. **`src/app/globals.css` & `src/app/(public)/public.css`**
   - **`src/app/globals.css` (lines 98-101)**: `--font-display` and `--font-headline` map to `var(--font-roboto, 'Roboto')`. `--font-outfit` custom property is not declared.
   - **`src/app/(public)/public.css` (lines 234-235)**: `--ccf-font-display` maps to `var(--font-headline, 'Roboto', 'Open Sans', sans-serif)`.

4. **`src/app/plataforma/cms/builder-puck/page.tsx`**
   - **Line 889**: `<Puck config={puckConfig} data={initialData} onPublish={handlePublish} iframe={{ enabled: false }} />`. `iframe={{ enabled: false }}` is already explicitly set, allowing direct DOM inheritance of site styles and CSS variables without iframe encapsulation.
   - **Lines 183-195**: Puck root wrapper:
     ```tsx
     root: {
       render: ({ children }: any) => (
         <div 
           className="p-8 min-h-screen transition-colors duration-200"
           style={{
             backgroundColor: "var(--site-background, #001134)",
             color: "var(--site-on-background, #d9e2ff)",
           }}
         >
           <div className="max-w-6xl mx-auto space-y-6">
             {children}
           </div>
         </div>
       )
     },
     ```
   - Canvas correctly uses `var(--site-background)` and `var(--site-on-background)`. The typography variables `--font-outfit` and `--font-inter` can be explicitly attached to root and heading elements in block renderers.

---

## 2. Logic Chain

1. **Font Loading & Delivery**:
   - `next/font/google` compiles Google Fonts into zero-FOUC self-hosted font files and injects a CSS variable class into the `<html>` element.
   - Importing `Outfit` with `variable: "--font-outfit"`, `subsets: ["latin"]`, `weight: ["400", "500", "600", "700", "800"]`, and `display: "swap"` creates the required `--font-outfit` variable.
   - Adding `${outfit.variable}` to `layout.tsx`'s `<html>` element class list ensures `--font-outfit` is available globally in the DOM.

2. **Tailwind & CSS Variable Mapping**:
   - Mapping `fontFamily.outfit`, `fontFamily.heading`, and `fontFamily.display` in `tailwind.config.ts` to `["var(--font-outfit)", "Outfit", "sans-serif"]` allows utility classes like `font-outfit`, `font-heading`, and `font-display` to utilize the injected Outfit font.
   - Updating `globals.css` and `public.css` `--font-outfit` and `--font-display` declarations ensures native CSS variable fallbacks also inherit Outfit seamlessly.

3. **Puck Theme & Canvas Sync**:
   - With `iframe={{ enabled: false }}` confirmed, Puck renders blocks directly into the main document tree.
   - When the host page fetches theme tokens from `/cms/v2/public/sites/${siteKey}/theme` and injects them onto `<main style={themeStyles}>`, all Puck block components reading `var(--site-background)`, `var(--site-primary)`, `var(--site-on-surface)`, etc., react dynamically.
   - Explicitly adding `fontFamily: "var(--font-inter, sans-serif)"` to Puck root and `fontFamily: "var(--font-outfit, sans-serif)"` to block title headings completes full design system synchronization.

---

## 3. Caveats

- **Iframe Disabled**: Disabling Puck iframe means host styles apply directly to Puck. Global CSS resets and custom properties will affect editor elements. This is intentional per R1 requirement to achieve theme inheritance.
- **Font Network / Prerender**: `next/font/google` requires internet access during build to download font assets unless cached; fallback strings in Tailwind/CSS ensure rendering safety.

---

## 4. Conclusion & Precise Modification Plan

### Step-by-Step Code Modifications

#### Task 1: Update `src/app/layout.tsx`

**Diff Specification**:
```diff
--- a/src/app/layout.tsx
+++ b/src/app/layout.tsx
@@ -2,1 +2,1 @@
-import { Roboto, Inter, Open_Sans } from "next/font/google";
+import { Roboto, Inter, Open_Sans, Outfit } from "next/font/google";
@@ -28,0 +28,8 @@
+const outfit = Outfit({
+    subsets: ["latin"],
+    weight: ["400", "500", "600", "700", "800"],
+    variable: "--font-outfit",
+    display: "swap",
+    preload: false,
+});
+
@@ -65,1 +73,1 @@
-<html lang="es" suppressHydrationWarning className={`${roboto.variable} ${openSans.variable} ${inter.variable}`}>
+<html lang="es" suppressHydrationWarning className={`${roboto.variable} ${openSans.variable} ${inter.variable} ${outfit.variable}`}>
```

#### Task 2: Update `tailwind.config.ts`

**Diff Specification**:
```diff
--- a/tailwind.config.ts
+++ b/tailwind.config.ts
@@ -95,6 +95,9 @@
             fontFamily: {
                 // ── Connected to next/font/google CSS variables (see layout.tsx) ──
                 // var(--font-*) is injected into <html> by Next.js at build time.
                 // Static fallback strings ensure prerender/SSR correctness.
-                "display":  ["var(--font-roboto)", "Roboto", "var(--font-open-sans)", "Open Sans", "var(--font-inter)", "Inter", "-apple-system", "sans-serif"],
-                "sans":     ["var(--font-roboto)", "Roboto", "var(--font-open-sans)", "Open Sans", "var(--font-inter)", "Inter", "-apple-system", "sans-serif"],
-                "headline": ["var(--font-roboto)", "Roboto", "var(--font-open-sans)", "Open Sans", "-apple-system", "sans-serif"],
+                "outfit":   ["var(--font-outfit)", "Outfit", "sans-serif"],
+                "heading":  ["var(--font-outfit)", "Outfit", "var(--font-roboto)", "Roboto", "sans-serif"],
+                "display":  ["var(--font-outfit)", "Outfit", "var(--font-roboto)", "Roboto", "var(--font-open-sans)", "Open Sans", "var(--font-inter)", "Inter", "-apple-system", "sans-serif"],
+                "sans":     ["var(--font-inter)", "Inter", "var(--font-roboto)", "Roboto", "-apple-system", "sans-serif"],
+                "headline": ["var(--font-outfit)", "Outfit", "var(--font-roboto)", "Roboto", "-apple-system", "sans-serif"],
```

#### Task 3: Update `src/app/globals.css` & `src/app/(public)/public.css`

**Diff Specification (`globals.css`)**:
```diff
--- a/src/app/globals.css
+++ b/src/app/globals.css
@@ -97,3 +97,4 @@
+  --font-outfit:    var(--font-outfit, 'Outfit'), sans-serif;
-  --font-display:   var(--font-roboto, 'Roboto'), var(--font-open-sans, 'Open Sans'), var(--font-inter, 'Inter'), -apple-system, BlinkMacSystemFont, sans-serif;
-  --font-headline:  var(--font-roboto, 'Roboto'), var(--font-open-sans, 'Open Sans'), -apple-system, sans-serif;
+  --font-display:   var(--font-outfit, 'Outfit'), var(--font-roboto, 'Roboto'), var(--font-open-sans, 'Open Sans'), var(--font-inter, 'Inter'), -apple-system, BlinkMacSystemFont, sans-serif;
+  --font-headline:  var(--font-outfit, 'Outfit'), var(--font-roboto, 'Roboto'), var(--font-open-sans, 'Open Sans'), -apple-system, sans-serif;
```

**Diff Specification (`src/app/(public)/public.css`)**:
```diff
--- a/src/app/(public)/public.css
+++ b/src/app/(public)/public.css
@@ -234,1 +234,1 @@
-    --ccf-font-display:  var(--font-headline, 'Roboto', 'Open Sans', sans-serif);
+    --ccf-font-display:  var(--font-outfit, var(--font-headline, 'Outfit', 'Roboto', sans-serif));
```

#### Task 4: Enhance Typography & Verify Iframe in `src/app/plataforma/cms/builder-puck/page.tsx`

**Diff Specification (`builder-puck/page.tsx`)**:
```diff
--- a/src/app/plataforma/cms/builder-puck/page.tsx
+++ b/src/app/plataforma/cms/builder-puck/page.tsx
@@ -185,2 +185,3 @@
             style={{
               backgroundColor: "var(--site-background, #001134)",
               color: "var(--site-on-background, #d9e2ff)",
+              fontFamily: "var(--font-inter, sans-serif)",
             }}
@@ -260,2 +261,2 @@
                 <h1 
-                  className="text-3xl font-extrabold tracking-tight sm:text-4xl md:text-5xl"
+                  className="text-3xl font-extrabold tracking-tight sm:text-4xl md:text-5xl"
+                  style={{ color: "var(--site-on-hero, #ffffff)", fontFamily: "var(--font-outfit, sans-serif)" }}
```

---

## 5. Verification Method

1. **TypeScript & Lint Checks**:
   ```bash
   npm run typecheck
   npm run lint
   ```
   Both commands must return 0 errors.

2. **DOM & CSS Variable Verification**:
   - Inspect `<html>` element in browser devtools: ensure `--font-outfit` class/variable is present.
   - Inspect `<Puck>` container element: verify `iframe={{ enabled: false }}` is active and container inherits `var(--site-background)` and typography rules.

/**
 * Semantic color tokens derived from CSS custom properties in globals.css.
 *
 * Each value is a raw HSL string (e.g. "197 98% 37%") meant to be consumed as
 * `hsl(var(--token))` in Tailwind / CSS.  Admin hex-only tokens are wrapped
 * with an HSL representation where possible; otherwise they keep their hex form.
 */

// ---------------------------------------------------------------------------
// Raw HSL values for light mode (:root / [data-theme="day"])
// ---------------------------------------------------------------------------

const light = {
  // ── Background & text ─────────────────────────────────────────────────────
  'bg-primary': '0 0% 100%',
  'bg-secondary': '210 40% 98%',
  'text-primary': '222 47% 11%',
  'text-secondary': '215 16% 47%',

  // ── Brand / legacy ────────────────────────────────────────────────────────
  'navy-dark': '210 41% 12%',
  'sky-blue': '190 100% 43%',
  'background-light': '220 14% 97%',
  'background-dark': '210 50% 3%',
  'ccf-blue-dark': '210 100% 14%',
  'ccf-blue-medium': '210 100% 25%',
  'ccf-blue-light': '197 98% 37%',
  'ccf-blue-pale': '206 33% 92%',
  'glass': '0 0% 100% / 0.1',
  'glass-border': '0 0% 100% / 0.2',

  // ── Primary ───────────────────────────────────────────────────────────────
  'primary': '197 98% 37%',
  'primary-foreground': '0 0% 100%',

  // ── Surfaces ──────────────────────────────────────────────────────────────
  'surface-1': '0 0% 100%',
  'surface-2': '210 40% 98%',
  'surface-3': '210 40% 96.1%',

  // ── Borders ───────────────────────────────────────────────────────────────
  'border': '214 32% 91%',
  'border-primary': '214 32% 91%',
  'border-glass': '0 0% 100% / 0.2',

  // ── Destructive / secondary / muted ───────────────────────────────────────
  'destructive': '0 84.2% 60.2%',
  'secondary': '142 76% 36%',
  'bg-muted': '210 40% 96.1%',

  // ── Semantic: success ─────────────────────────────────────────────────────
  'success': '142 76% 36%',
  'success-foreground': '0 0% 100%',
  'success-muted': '142 76% 95%',
  'success-text': '142 80% 22%',

  // ── Semantic: warning ─────────────────────────────────────────────────────
  'warning': '38 92% 50%',
  'warning-foreground': '0 0% 100%',
  'warning-muted': '38 92% 95%',
  'warning-text': '30 80% 28%',

  // ── Semantic: info ────────────────────────────────────────────────────────
  'info': '197 98% 37%',
  'info-foreground': '0 0% 100%',
  'info-muted': '197 98% 95%',
  'info-text': '197 90% 25%',

  // ── Semantic: danger ──────────────────────────────────────────────────────
  'danger': '0 84.2% 60.2%',
  'danger-foreground': '0 0% 100%',
  'danger-muted': '0 84.2% 95%',
  'danger-text': '0 70% 28%',

  // ── Domain colors ─────────────────────────────────────────────────────────
  'domain-cyan': '183 100% 35%',
  'domain-fuchsia': '300 100% 50%',
  'domain-pink': '330 100% 50%',
  'domain-teal': '170 80% 40%',
  'domain-lime': '90 100% 40%',
  'domain-iris': '240 100% 60%',
  'domain-plum': '270 100% 60%',

  // ── Whiteboard ────────────────────────────────────────────────────────────
  'whiteboard-bg': '0 0% 98%',
  'whiteboard-canvas': '0 0% 100%',
  'whiteboard-primary': '217 91% 60%',
  'whiteboard-primary-light': '217 91% 60% / 0.08',
  'whiteboard-success': '160 84% 39%',
  'whiteboard-success-light': '160 84% 39% / 0.1',
  'whiteboard-text': '222 47% 11%',
  'whiteboard-text-secondary': '215 25% 21%',
  'whiteboard-grid': '220 13% 91%',
  'whiteboard-grid-dot': '214 20% 80%',
} as const;

// ---------------------------------------------------------------------------
// Raw HSL values for dark mode ([data-theme="night"])
// ---------------------------------------------------------------------------

const dark = {
  // ── Background & text ─────────────────────────────────────────────────────
  'bg-primary': '222 47% 4%',
  'bg-secondary': '222 47% 6%',
  'text-primary': '210 40% 98%',
  'text-secondary': '215 20.2% 65.1%',

  // ── Surfaces ──────────────────────────────────────────────────────────────
  'surface-1': '222 47% 4%',
  'surface-2': '222 47% 10%',
  'surface-3': '222 47% 15%',

  // ── Primary ───────────────────────────────────────────────────────────────
  'primary': '197 78% 50%',
  'primary-foreground': '0 0% 100%',

  // ── Borders ───────────────────────────────────────────────────────────────
  'border': '217 33% 17%',
  'border-primary': '217 33% 17%',
  'border-glass': '255 255% 255% / 0.05',

  // ── Destructive / secondary / muted ───────────────────────────────────────
  'destructive': '0 62.8% 30.6%',
  'secondary': '142 71% 45%',
  'bg-muted': '222 47% 10%',

  // ── Semantic: success ─────────────────────────────────────────────────────
  'success': '142 71% 45%',
  'success-foreground': '0 0% 100%',
  'success-muted': '142 71% 15%',
  'success-text': '142 70% 75%',

  // ── Semantic: warning ─────────────────────────────────────────────────────
  'warning': '38 92% 55%',
  'warning-foreground': '0 0% 100%',
  'warning-muted': '38 92% 15%',
  'warning-text': '38 80% 70%',

  // ── Semantic: info ────────────────────────────────────────────────────────
  'info': '197 78% 50%',
  'info-foreground': '0 0% 100%',
  'info-muted': '197 78% 15%',
  'info-text': '197 80% 75%',

  // ── Semantic: danger ──────────────────────────────────────────────────────
  'danger': '0 62.8% 30.6%',
  'danger-foreground': '0 0% 100%',
  'danger-muted': '0 62.8% 15%',
  'danger-text': '0 70% 75%',

  // ── Whiteboard (dark) ─────────────────────────────────────────────────────
  'whiteboard-bg': '222 47% 4%',
  'whiteboard-canvas': '0 0% 100%',
  'whiteboard-primary': '217 91% 60%',
  'whiteboard-primary-light': '217 91% 60% / 0.08',
  'whiteboard-success': '160 84% 39%',
  'whiteboard-success-light': '160 84% 39% / 0.1',
  'whiteboard-text': '210 40% 98%',
  'whiteboard-text-secondary': '215 20% 65%',
  'whiteboard-grid': '222 47% 15%',
  'whiteboard-grid-dot': '215 25% 27%',

  // ── Surface (dark-only) ───────────────────────────────────────────────────
  'surface-card': '220 6% 12%',

  // ── Admin (dark-only, hex values) ─────────────────────────────────────────
  'admin-bg-primary': '#141517',
  'admin-bg-secondary': '#252528',
  'admin-bg-tertiary': '#111418',
  'admin-bg-deep': '#0d0e11',
  'admin-bg-surface': '#0f1115',
  'admin-bg-elevated': '#1a1b1f',
  'admin-bg-input': '#111213',
  'admin-border': '#2a2d32',
} as const;

// ---------------------------------------------------------------------------
// Theme palette (exported for runtime switching)
// ---------------------------------------------------------------------------

export const semanticColorsLight = light;
export const semanticColorsDark = dark;

// ---------------------------------------------------------------------------
// Flat map – CSS var() wrappers (useful in Tailwind arbitrary values, etc.)
// ---------------------------------------------------------------------------

type LightKeys = keyof typeof light;
type DarkKeys = keyof typeof dark;

type AllSemanticKeys = LightKeys | DarkKeys;

function wrapAll<T extends Record<string, string>>(
  src: T,
): { readonly [K in keyof T]: `hsl(var(--${string & K}))` } {
  const out = {} as Record<string, string>;
  for (const key of Object.keys(src)) {
    out[key] = `hsl(var(--${key}))`;
  }
  return out as { readonly [K in keyof T]: `hsl(var(--${string & K}))` };
}

/** All light-mode semantic tokens wrapped as `hsl(var(--…))` */
export const semanticColorsLightHsl = wrapAll(light);

/** All dark-mode semantic tokens wrapped as `hsl(var(--…))` */
export const semanticColorsDarkHsl = wrapAll(dark);

// ---------------------------------------------------------------------------
// Union type of every semantic token name
// ---------------------------------------------------------------------------

export type SemanticColor = AllSemanticKeys;

// ---------------------------------------------------------------------------
// Utility types
// ---------------------------------------------------------------------------

/** Keys present in both light and dark palettes */
export type ThemeSharedColor = Extract<LightKeys, DarkKeys>;

/** Keys that differ between light and dark palettes */
export type ThemeAdaptiveColor = Exclude<AllSemanticKeys, ThemeSharedColor>;

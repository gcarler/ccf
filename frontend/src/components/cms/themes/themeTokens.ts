/**
 * CMS Theme Token System — Complete design-token catalog.
 *
 * Every token here maps 1:1 to a CSS custom property (--site-*)
 * consumed by the public site (see app/(public)/faro.css).
 *
 * Categories: Colors, Surfaces, Typography, Effects, Gradients.
 */

export interface TokenDef {
  key: string;
  label: string;
  description: string;
  type: "color" | "text" | "gradient" | "shadow" | "dimension";
  defaultValue: string;
}

export interface TokenCategory {
  id: string;
  label: string;
  description: string;
  tokens: TokenDef[];
}

/* ── Color tokens ─────────────────────────────────────────────────────────── */

const COLOR_TOKENS: TokenDef[] = [
  { key: "--site-primary", label: "Primary", description: "Color principal (botones, acentos)", type: "color", defaultValue: "#a5c8ff" },
  { key: "--site-secondary", label: "Secondary", description: "Color secundario (complementos)", type: "color", defaultValue: "#80d0ff" },
  { key: "--site-background", label: "Background", description: "Fondo general de la página", type: "color", defaultValue: "#001134" },
  { key: "--site-on-background", label: "On Background", description: "Texto sobre el fondo general", type: "color", defaultValue: "#d9e2ff" },
  { key: "--site-on-primary", label: "On Primary", description: "Texto/iconos sobre el color primario", type: "color", defaultValue: "#00315e" },
  { key: "--site-surface", label: "Surface", description: "Superficie base de tarjetas y paneles", type: "color", defaultValue: "#001134" },
  { key: "--site-on-surface", label: "On Surface", description: "Texto sobre superficies", type: "color", defaultValue: "#d9e2ff" },
  { key: "--site-on-surface-variant", label: "On Surface Variant", description: "Texto secundario sobre superficies", type: "color", defaultValue: "#c2c6d1" },
  { key: "--site-primary-container", label: "Primary Container", description: "Fondo contenedor con tinte primario", type: "color", defaultValue: "#004581" },
  { key: "--site-on-secondary-container", label: "On Secondary Container", description: "Texto en contenedor secundario", type: "color", defaultValue: "#002d41" },
  { key: "--site-secondary-container", label: "Secondary Container", description: "Fondo contenedor secundario", type: "color", defaultValue: "#2b9ace" },
  { key: "--site-error", label: "Error", description: "Color de error / destructivo", type: "color", defaultValue: "#ffb4ab" },
  { key: "--site-outline", label: "Outline", description: "Color de bordes y divisores", type: "color", defaultValue: "#8c919b" },
  { key: "--site-outline-variant", label: "Outline Variant", description: "Bordes sutiles", type: "color", defaultValue: "#424750" },
];

/* ── Surface hierarchy ────────────────────────────────────────────────────── */

const SURFACE_TOKENS: TokenDef[] = [
  { key: "--site-surface-container", label: "Surface Container", description: "Fondo de tarjetas y modales", type: "color", defaultValue: "#021d4a" },
  { key: "--site-surface-container-low", label: "Surface Container Low", description: "Superficie ligeramente elevada", type: "color", defaultValue: "#001944" },
  { key: "--site-surface-container-high", label: "Surface Container High", description: "Superficie más elevada", type: "color", defaultValue: "#1d3361" },
  { key: "--site-surface-container-highest", label: "Surface Container Highest", description: "Superficie máxima elevación", type: "color", defaultValue: "#1d3361" },
  { key: "--site-surface-container-lowest", label: "Surface Container Lowest", description: "Superficie más baja (fondo profundo)", type: "color", defaultValue: "#000d2a" },
  { key: "--site-surface-dim", label: "Surface Dim", description: "Superficie atenuada", type: "color", defaultValue: "#001134" },
  { key: "--site-surface-bright", label: "Surface Bright", description: "Superficie brillante", type: "color", defaultValue: "#223865" },
  { key: "--site-surface-tint", label: "Surface Tint", description: "Tinte aplicado a superficies", type: "color", defaultValue: "#a5c8ff" },
  { key: "--site-primary-fixed-dim", label: "Primary Fixed Dim", description: "Variante atenuada del primario", type: "color", defaultValue: "#a5c8ff" },
];

/* ── UI / Effects ─────────────────────────────────────────────────────────── */

const EFFECT_TOKENS: TokenDef[] = [
  { key: "--site-navbar-bg", label: "Navbar BG", description: "Fondo de la barra de navegación", type: "color", defaultValue: "rgba(0, 13, 42, 0.6)" },
  { key: "--site-navbar-bg-scrolled", label: "Navbar BG Scrolled", description: "Navbar al hacer scroll", type: "color", defaultValue: "rgba(0, 13, 42, 0.92)" },
  { key: "--site-navbar-border", label: "Navbar Border", description: "Borde inferior del navbar", type: "color", defaultValue: "rgba(165, 200, 255, 0.08)" },
  { key: "--site-dropdown-bg", label: "Dropdown BG", description: "Fondo de menús desplegables", type: "color", defaultValue: "rgba(10, 22, 48, 0.95)" },
  { key: "--site-dropdown-border", label: "Dropdown Border", description: "Borde de dropdowns", type: "color", defaultValue: "rgba(66, 71, 80, 0.5)" },
  { key: "--site-overlay-bg", label: "Overlay BG", description: "Fondo de overlays modales", type: "color", defaultValue: "rgba(0, 13, 42, 0.7)" },
  { key: "--site-glass-bg", label: "Glass BG", description: "Fondo glassmorphism", type: "color", defaultValue: "rgba(29, 51, 97, 0.4)" },
  { key: "--site-glass-border", label: "Glass Border", description: "Borde glassmorphism", type: "color", defaultValue: "rgba(165, 200, 255, 0.1)" },
  { key: "--site-card-highlight", label: "Card Highlight", description: "Resaltado de tarjetas hover", type: "color", defaultValue: "rgba(165, 200, 255, 0.15)" },
  { key: "--site-glow-subtle", label: "Glow Subtle", description: "Brillo sutil (degradados radiales)", type: "color", defaultValue: "rgba(165, 200, 255, 0.08)" },
  { key: "--site-glow-intense", label: "Glow Intense", description: "Brillo intenso (sombras, glows)", type: "color", defaultValue: "rgba(165, 200, 255, 0.3)" },
  { key: "--site-mobile-nav-bg", label: "Mobile Nav BG", description: "Fondo navegación móvil", type: "color", defaultValue: "rgba(0, 17, 52, 0.85)" },
  { key: "--site-mobile-nav-inactive", label: "Mobile Nav Inactive", description: "Items inactivos en nav móvil", type: "color", defaultValue: "rgba(217, 226, 255, 0.5)" },
  { key: "--site-on-hero", label: "On Hero", description: "Texto sobre secciones hero", type: "color", defaultValue: "#ffffff" },
  { key: "--site-date-badge-bg", label: "Date Badge BG", description: "Fondo de badges de fecha", type: "color", defaultValue: "rgba(0, 13, 42, 0.8)" },
];

/* ── Gradients ────────────────────────────────────────────────────────────── */

const GRADIENT_TOKENS: TokenDef[] = [
  { key: "--site-cta-gradient", label: "CTA Gradient", description: "Gradiente de botones principales", type: "gradient", defaultValue: "linear-gradient(to right, #004581, #018abd, #004581)" },
  { key: "--site-cta-shadow", label: "CTA Shadow", description: "Sombra de botones CTA", type: "shadow", defaultValue: "0 4px 20px rgba(1, 138, 189, 0.5)" },
  { key: "--site-hero-overlay", label: "Hero Overlay", description: "Overlay gradiente del hero", type: "gradient", defaultValue: "linear-gradient(to bottom, rgba(0,13,42,0.7) 0%, rgba(0,13,42,0.4) 50%, rgba(0,13,42,0.85) 100%)" },
  { key: "--site-hero-accent-1", label: "Hero Accent 1", description: "Acento decorativo hero", type: "gradient", defaultValue: "linear-gradient(135deg, #a5c8ff 0%, #018abd 100%)" },
  { key: "--site-hero-accent-2", label: "Hero Accent 2", description: "Segundo acento decorativo hero", type: "gradient", defaultValue: "linear-gradient(135deg, #a5c8ff 0%, #2c609d 100%)" },
  { key: "--site-hero-cta-gradient", label: "Hero CTA Gradient", description: "Gradiente CTA en hero", type: "gradient", defaultValue: "linear-gradient(135deg, #018abd 0%, #2c609d 100%)" },
  { key: "--site-hero-cta-shadow", label: "Hero CTA Shadow", description: "Sombra CTA hero", type: "shadow", defaultValue: "0 8px 32px rgba(1, 138, 189, 0.4)" },
  { key: "--site-hero-bg-light", label: "Hero BG Light", description: "Fondo luminoso en hero", type: "color", defaultValue: "rgba(255, 255, 255, 0.08)" },
  { key: "--site-hero-border-light", label: "Hero Border Light", description: "Borde luminoso en hero", type: "color", defaultValue: "rgba(255, 255, 255, 0.15)" },
  { key: "--site-hero-badge-bg", label: "Hero Badge BG", description: "Fondo de badges en hero", type: "color", defaultValue: "rgba(165, 200, 255, 0.05)" },
  { key: "--site-hero-badge-border", label: "Hero Badge Border", description: "Borde de badges en hero", type: "color", defaultValue: "rgba(165, 200, 255, 0.3)" },
  { key: "--site-hero-badge-color", label: "Hero Badge Color", description: "Texto de badges en hero", type: "color", defaultValue: "rgba(165, 200, 255, 0.9)" },
  { key: "--site-card-glass-gradient", label: "Card Glass Gradient", description: "Gradiente glass en tarjetas", type: "gradient", defaultValue: "linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0.02) 100%)" },
  { key: "--site-card-glass-glow", label: "Card Glass Glow", description: "Glow radial en tarjetas glass", type: "gradient", defaultValue: "radial-gradient(circle at 30% 50%, rgba(165,200,255,0.5) 0%, transparent 60%)" },
  { key: "--site-card-shadow", label: "Card Shadow", description: "Sombra de tarjetas", type: "shadow", defaultValue: "0 32px 64px -16px rgba(0,0,0,0.1)" },
  { key: "--site-mobile-nav-shadow", label: "Mobile Nav Shadow", description: "Sombra nav móvil", type: "shadow", defaultValue: "0 20px 40px rgba(0, 0, 0, 0.5)" },
  { key: "--site-mobile-nav-glow", label: "Mobile Nav Glow", description: "Glow nav móvil", type: "shadow", defaultValue: "0 0 15px rgba(165, 200, 255, 0.3)" },
];

export const TOKEN_CATEGORIES: TokenCategory[] = [
  { id: "colors", label: "Colores Principales", description: "Paleta cromática principal del sitio", tokens: COLOR_TOKENS },
  { id: "surfaces", label: "Jerarquía de Superficies", description: "Niveles de elevación y profundidad", tokens: SURFACE_TOKENS },
  { id: "effects", label: "Efectos e Interfaces", description: "Glassmorphism, glows, overlays y navegación", tokens: EFFECT_TOKENS },
  { id: "gradients", label: "Gradientes y Sombras", description: "Degradados, sombras y efectos luminosos", tokens: GRADIENT_TOKENS },
];

export const ALL_TOKEN_KEYS = TOKEN_CATEGORIES.flatMap((c) => c.tokens.map((t) => t.key));

export function getTokenDefaultValue(key: string): string {
  for (const cat of TOKEN_CATEGORIES) {
    const token = cat.tokens.find((t) => t.key === key);
    if (token) return token.defaultValue;
  }
  return "";
}

export function buildDefaultTokens(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const cat of TOKEN_CATEGORIES) {
    for (const token of cat.tokens) {
      out[token.key] = token.defaultValue;
    }
  }
  return out;
}

/* ── Theme Presets ────────────────────────────────────────────────────────── */

export interface ThemePreset {
  key: string;
  name: string;
  description: string;
  tokens: Record<string, string>;
}

export const THEME_PRESETS: ThemePreset[] = [
  {
    key: "institutional",
    name: "Institucional",
    description: "Azul profundo corporativo — el clásico de la marca",
    tokens: {
      "--site-primary": "#a5c8ff",
      "--site-secondary": "#80d0ff",
      "--site-background": "#001134",
      "--site-on-background": "#d9e2ff",
      "--site-on-primary": "#ffffff",
      "--site-surface": "#001134",
      "--site-on-surface": "#d9e2ff",
      "--site-on-surface-variant": "#c2c6d1",
      "--site-primary-container": "#004581",
      "--site-on-secondary-container": "#002d41",
      "--site-secondary-container": "#2b9ace",
      "--site-error": "#ffb4ab",
      "--site-outline": "#8c919b",
      "--site-outline-variant": "#424750",
      "--site-surface-container": "#021d4a",
      "--site-surface-container-low": "#001944",
      "--site-surface-container-high": "#1d3361",
      "--site-surface-container-highest": "#1d3361",
      "--site-surface-container-lowest": "#000d2a",
      "--site-surface-dim": "#001134",
      "--site-surface-bright": "#223865",
      "--site-surface-tint": "#a5c8ff",
      "--site-primary-fixed-dim": "#a5c8ff",
      "--site-navbar-bg": "rgba(0, 13, 42, 0.6)",
      "--site-navbar-bg-scrolled": "rgba(0, 13, 42, 0.92)",
      "--site-navbar-border": "rgba(165, 200, 255, 0.08)",
      "--site-dropdown-bg": "rgba(10, 22, 48, 0.95)",
      "--site-dropdown-border": "rgba(66, 71, 80, 0.5)",
      "--site-overlay-bg": "rgba(0, 13, 42, 0.7)",
      "--site-glass-bg": "rgba(29, 51, 97, 0.4)",
      "--site-glass-border": "rgba(165, 200, 255, 0.1)",
      "--site-card-highlight": "rgba(165, 200, 255, 0.15)",
      "--site-glow-subtle": "rgba(165, 200, 255, 0.08)",
      "--site-glow-intense": "rgba(165, 200, 255, 0.3)",
      "--site-mobile-nav-bg": "rgba(0, 17, 52, 0.85)",
      "--site-mobile-nav-inactive": "rgba(217, 226, 255, 0.5)",
      "--site-on-hero": "#ffffff",
      "--site-date-badge-bg": "rgba(0, 13, 42, 0.8)",
      "--site-cta-gradient": "linear-gradient(to right, #004581, #018abd, #004581)",
      "--site-cta-shadow": "0 4px 20px rgba(1, 138, 189, 0.5)",
      "--site-hero-overlay": "linear-gradient(to bottom, rgba(0,13,42,0.7) 0%, rgba(0,13,42,0.4) 50%, rgba(0,13,42,0.85) 100%)",
      "--site-hero-accent-1": "linear-gradient(135deg, #a5c8ff 0%, #018abd 100%)",
      "--site-hero-accent-2": "linear-gradient(135deg, #a5c8ff 0%, #2c609d 100%)",
      "--site-hero-cta-gradient": "linear-gradient(135deg, #018abd 0%, #2c609d 100%)",
      "--site-hero-cta-shadow": "0 8px 32px rgba(1, 138, 189, 0.4)",
      "--site-hero-bg-light": "rgba(255, 255, 255, 0.08)",
      "--site-hero-border-light": "rgba(255, 255, 255, 0.15)",
      "--site-hero-badge-bg": "rgba(165, 200, 255, 0.05)",
      "--site-hero-badge-border": "rgba(165, 200, 255, 0.3)",
      "--site-hero-badge-color": "rgba(165, 200, 255, 0.9)",
      "--site-card-glass-gradient": "linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0.02) 100%)",
      "--site-card-glass-glow": "radial-gradient(circle at 30% 50%, rgba(165,200,255,0.5) 0%, transparent 60%)",
      "--site-card-shadow": "0 32px 64px -16px rgba(0,0,0,0.1)",
      "--site-mobile-nav-shadow": "0 20px 40px rgba(0, 0, 0, 0.5)",
      "--site-mobile-nav-glow": "0 0 15px rgba(165, 200, 255, 0.3)",
    },
  },
  {
    key: "modern",
    name: "Moderno",
    description: "Teal fresco y luminoso — para una iglesia joven y dinámica",
    tokens: {
      "--site-primary": "#00d4aa",
      "--site-secondary": "#00b4d8",
      "--site-background": "#0a1929",
      "--site-on-background": "#e6f7ff",
      "--site-on-primary": "#001a14",
      "--site-surface": "#0f2940",
      "--site-on-surface": "#e6f7ff",
      "--site-on-surface-variant": "#a8c5d9",
      "--site-primary-container": "#004d3d",
      "--site-on-secondary-container": "#001e24",
      "--site-secondary-container": "#00667a",
      "--site-error": "#ff6b6b",
      "--site-outline": "#4a6d85",
      "--site-outline-variant": "#1a3a52",
      "--site-surface-container": "#123040",
      "--site-surface-container-low": "#0d2535",
      "--site-surface-container-high": "#1a4055",
      "--site-surface-container-highest": "#1e4a60",
      "--site-surface-container-lowest": "#061220",
      "--site-surface-dim": "#0a1929",
      "--site-surface-bright": "#1e4a60",
      "--site-surface-tint": "#00d4aa",
      "--site-primary-fixed-dim": "#00b894",
      "--site-navbar-bg": "rgba(10, 25, 41, 0.7)",
      "--site-navbar-bg-scrolled": "rgba(10, 25, 41, 0.95)",
      "--site-navbar-border": "rgba(0, 212, 170, 0.1)",
      "--site-dropdown-bg": "rgba(15, 41, 64, 0.98)",
      "--site-dropdown-border": "rgba(0, 212, 170, 0.15)",
      "--site-overlay-bg": "rgba(6, 18, 32, 0.8)",
      "--site-glass-bg": "rgba(18, 48, 64, 0.5)",
      "--site-glass-border": "rgba(0, 212, 170, 0.12)",
      "--site-card-highlight": "rgba(0, 212, 170, 0.15)",
      "--site-glow-subtle": "rgba(0, 212, 170, 0.08)",
      "--site-glow-intense": "rgba(0, 212, 170, 0.35)",
      "--site-mobile-nav-bg": "rgba(10, 25, 41, 0.95)",
      "--site-mobile-nav-inactive": "rgba(168, 197, 217, 0.5)",
      "--site-on-hero": "#ffffff",
      "--site-date-badge-bg": "rgba(6, 18, 32, 0.85)",
      "--site-cta-gradient": "linear-gradient(to right, #00a884, #00d4aa, #00a884)",
      "--site-cta-shadow": "0 4px 24px rgba(0, 212, 170, 0.4)",
      "--site-hero-overlay": "linear-gradient(to bottom, rgba(6,18,32,0.75) 0%, rgba(6,18,32,0.4) 50%, rgba(6,18,32,0.9) 100%)",
      "--site-hero-accent-1": "linear-gradient(135deg, #00d4aa 0%, #00b4d8 100%)",
      "--site-hero-accent-2": "linear-gradient(135deg, #00d4aa 0%, #00667a 100%)",
      "--site-hero-cta-gradient": "linear-gradient(135deg, #00b4d8 0%, #00a884 100%)",
      "--site-hero-cta-shadow": "0 8px 32px rgba(0, 212, 170, 0.35)",
      "--site-hero-bg-light": "rgba(255, 255, 255, 0.06)",
      "--site-hero-border-light": "rgba(255, 255, 255, 0.12)",
      "--site-hero-badge-bg": "rgba(0, 212, 170, 0.08)",
      "--site-hero-badge-border": "rgba(0, 212, 170, 0.35)",
      "--site-hero-badge-color": "rgba(0, 212, 170, 0.95)",
      "--site-card-glass-gradient": "linear-gradient(135deg, rgba(0,212,170,0.04) 0%, rgba(0,0,0,0.03) 100%)",
      "--site-card-glass-glow": "radial-gradient(circle at 30% 50%, rgba(0,212,170,0.35) 0%, transparent 60%)",
      "--site-card-shadow": "0 24px 48px -12px rgba(0,0,0,0.25)",
      "--site-mobile-nav-shadow": "0 20px 40px rgba(0, 0, 0, 0.5)",
      "--site-mobile-nav-glow": "0 0 20px rgba(0, 212, 170, 0.25)",
    },
  },
  {
    key: "minimalist",
    name: "Minimalista",
    description: "Blanco y negro con acentos sutiles — elegancia sin ruido",
    tokens: {
      "--site-primary": "#111111",
      "--site-secondary": "#666666",
      "--site-background": "#ffffff",
      "--site-on-background": "#111111",
      "--site-on-primary": "#ffffff",
      "--site-surface": "#ffffff",
      "--site-on-surface": "#111111",
      "--site-on-surface-variant": "#666666",
      "--site-primary-container": "#f0f0f0",
      "--site-on-secondary-container": "#111111",
      "--site-secondary-container": "#e8e8e8",
      "--site-error": "#cc0000",
      "--site-outline": "#dddddd",
      "--site-outline-variant": "#eeeeee",
      "--site-surface-container": "#fafafa",
      "--site-surface-container-low": "#f5f5f5",
      "--site-surface-container-high": "#ffffff",
      "--site-surface-container-highest": "#ffffff",
      "--site-surface-container-lowest": "#f0f0f0",
      "--site-surface-dim": "#e0e0e0",
      "--site-surface-bright": "#ffffff",
      "--site-surface-tint": "#111111",
      "--site-primary-fixed-dim": "#333333",
      "--site-navbar-bg": "rgba(255, 255, 255, 0.85)",
      "--site-navbar-bg-scrolled": "rgba(255, 255, 255, 0.98)",
      "--site-navbar-border": "rgba(0, 0, 0, 0.05)",
      "--site-dropdown-bg": "rgba(255, 255, 255, 0.98)",
      "--site-dropdown-border": "rgba(0, 0, 0, 0.08)",
      "--site-overlay-bg": "rgba(0, 0, 0, 0.4)",
      "--site-glass-bg": "rgba(255, 255, 255, 0.7)",
      "--site-glass-border": "rgba(0, 0, 0, 0.06)",
      "--site-card-highlight": "rgba(0, 0, 0, 0.04)",
      "--site-glow-subtle": "rgba(0, 0, 0, 0.03)",
      "--site-glow-intense": "rgba(0, 0, 0, 0.08)",
      "--site-mobile-nav-bg": "rgba(255, 255, 255, 0.95)",
      "--site-mobile-nav-inactive": "rgba(102, 102, 102, 0.5)",
      "--site-on-hero": "#111111",
      "--site-date-badge-bg": "rgba(255, 255, 255, 0.9)",
      "--site-cta-gradient": "linear-gradient(to right, #111111, #333333, #111111)",
      "--site-cta-shadow": "0 2px 12px rgba(0, 0, 0, 0.15)",
      "--site-hero-overlay": "linear-gradient(to bottom, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0.5) 50%, rgba(255,255,255,0.9) 100%)",
      "--site-hero-accent-1": "linear-gradient(135deg, #111111 0%, #666666 100%)",
      "--site-hero-accent-2": "linear-gradient(135deg, #333333 0%, #999999 100%)",
      "--site-hero-cta-gradient": "linear-gradient(135deg, #111111 0%, #444444 100%)",
      "--site-hero-cta-shadow": "0 4px 16px rgba(0, 0, 0, 0.1)",
      "--site-hero-bg-light": "rgba(0, 0, 0, 0.02)",
      "--site-hero-border-light": "rgba(0, 0, 0, 0.06)",
      "--site-hero-badge-bg": "rgba(0, 0, 0, 0.03)",
      "--site-hero-badge-border": "rgba(0, 0, 0, 0.1)",
      "--site-hero-badge-color": "rgba(0, 0, 0, 0.7)",
      "--site-card-glass-gradient": "linear-gradient(135deg, rgba(255,255,255,0.8) 0%, rgba(240,240,240,0.6) 100%)",
      "--site-card-glass-glow": "radial-gradient(circle at 30% 50%, rgba(0,0,0,0.03) 0%, transparent 60%)",
      "--site-card-shadow": "0 8px 24px -8px rgba(0,0,0,0.08)",
      "--site-mobile-nav-shadow": "0 12px 24px rgba(0, 0, 0, 0.08)",
      "--site-mobile-nav-glow": "0 0 10px rgba(0, 0, 0, 0.05)",
    },
  },
  {
    key: "vibrant",
    name: "Vibrante",
    description: "Colores saturados y energéticos — para una comunidad joven",
    tokens: {
      "--site-primary": "#ff6b35",
      "--site-secondary": "#f7c59f",
      "--site-background": "#1a0a2e",
      "--site-on-background": "#fff5f0",
      "--site-on-primary": "#1a0a2e",
      "--site-surface": "#241040",
      "--site-on-surface": "#fff5f0",
      "--site-on-surface-variant": "#d4a5a5",
      "--site-primary-container": "#5a1a1a",
      "--site-on-secondary-container": "#2e1a0a",
      "--site-secondary-container": "#8a5a3a",
      "--site-error": "#ff4444",
      "--site-outline": "#5a3a5a",
      "--site-outline-variant": "#3a204a",
      "--site-surface-container": "#2a1545",
      "--site-surface-container-low": "#1f1040",
      "--site-surface-container-high": "#351a55",
      "--site-surface-container-highest": "#3d2060",
      "--site-surface-container-lowest": "#120520",
      "--site-surface-dim": "#1a0a2e",
      "--site-surface-bright": "#4a2570",
      "--site-surface-tint": "#ff6b35",
      "--site-primary-fixed-dim": "#d4552a",
      "--site-navbar-bg": "rgba(26, 10, 46, 0.7)",
      "--site-navbar-bg-scrolled": "rgba(26, 10, 46, 0.95)",
      "--site-navbar-border": "rgba(255, 107, 53, 0.1)",
      "--site-dropdown-bg": "rgba(36, 16, 64, 0.98)",
      "--site-dropdown-border": "rgba(255, 107, 53, 0.2)",
      "--site-overlay-bg": "rgba(18, 5, 32, 0.85)",
      "--site-glass-bg": "rgba(42, 21, 69, 0.5)",
      "--site-glass-border": "rgba(255, 107, 53, 0.12)",
      "--site-card-highlight": "rgba(255, 107, 53, 0.15)",
      "--site-glow-subtle": "rgba(255, 107, 53, 0.08)",
      "--site-glow-intense": "rgba(255, 107, 53, 0.4)",
      "--site-mobile-nav-bg": "rgba(26, 10, 46, 0.95)",
      "--site-mobile-nav-inactive": "rgba(212, 165, 165, 0.5)",
      "--site-on-hero": "#ffffff",
      "--site-date-badge-bg": "rgba(18, 5, 32, 0.85)",
      "--site-cta-gradient": "linear-gradient(to right, #d4552a, #ff6b35, #d4552a)",
      "--site-cta-shadow": "0 4px 24px rgba(255, 107, 53, 0.45)",
      "--site-hero-overlay": "linear-gradient(to bottom, rgba(18,5,32,0.75) 0%, rgba(18,5,32,0.4) 50%, rgba(18,5,32,0.9) 100%)",
      "--site-hero-accent-1": "linear-gradient(135deg, #ff6b35 0%, #f7c59f 100%)",
      "--site-hero-accent-2": "linear-gradient(135deg, #ff6b35 0%, #d4552a 100%)",
      "--site-hero-cta-gradient": "linear-gradient(135deg, #f7c59f 0%, #ff6b35 100%)",
      "--site-hero-cta-shadow": "0 8px 32px rgba(255, 107, 53, 0.35)",
      "--site-hero-bg-light": "rgba(255, 255, 255, 0.06)",
      "--site-hero-border-light": "rgba(255, 255, 255, 0.12)",
      "--site-hero-badge-bg": "rgba(255, 107, 53, 0.08)",
      "--site-hero-badge-border": "rgba(255, 107, 53, 0.35)",
      "--site-hero-badge-color": "rgba(255, 107, 53, 0.95)",
      "--site-card-glass-gradient": "linear-gradient(135deg, rgba(255,107,53,0.04) 0%, rgba(0,0,0,0.03) 100%)",
      "--site-card-glass-glow": "radial-gradient(circle at 30% 50%, rgba(255,107,53,0.3) 0%, transparent 60%)",
      "--site-card-shadow": "0 24px 48px -12px rgba(0,0,0,0.3)",
      "--site-mobile-nav-shadow": "0 20px 40px rgba(0, 0, 0, 0.5)",
      "--site-mobile-nav-glow": "0 0 20px rgba(255, 107, 53, 0.2)",
    },
  },
  {
    key: "dark",
    name: "Oscuro Puro",
    description: "Negro puro con alto contraste — para experiencias inmersivas",
    tokens: {
      "--site-primary": "#ffffff",
      "--site-secondary": "#cccccc",
      "--site-background": "#0a0a0a",
      "--site-on-background": "#eeeeee",
      "--site-on-primary": "#000000",
      "--site-surface": "#0a0a0a",
      "--site-on-surface": "#ffffff",
      "--site-on-surface-variant": "#aaaaaa",
      "--site-primary-container": "#222222",
      "--site-on-secondary-container": "#ffffff",
      "--site-secondary-container": "#333333",
      "--site-error": "#ffb4ab",
      "--site-outline": "#555555",
      "--site-outline-variant": "#222222",
      "--site-surface-container": "#121212",
      "--site-surface-container-low": "#0f0f0f",
      "--site-surface-container-high": "#1a1a1a",
      "--site-surface-container-highest": "#1a1a1a",
      "--site-surface-container-lowest": "#000000",
      "--site-surface-dim": "#000000",
      "--site-surface-bright": "#1a1a1a",
      "--site-surface-tint": "#ffffff",
      "--site-primary-fixed-dim": "#ffffff",
      "--site-navbar-bg": "rgba(10, 10, 10, 0.6)",
      "--site-navbar-bg-scrolled": "rgba(10, 10, 10, 0.92)",
      "--site-navbar-border": "rgba(85, 85, 85, 0.15)",
      "--site-dropdown-bg": "rgba(0, 0, 0, 0.95)",
      "--site-dropdown-border": "rgba(34, 34, 34, 0.8)",
      "--site-overlay-bg": "rgba(0, 0, 0, 0.6)",
      "--site-glass-bg": "rgba(0, 0, 0, 0.5)",
      "--site-glass-border": "rgba(255, 255, 255, 0.05)",
      "--site-card-highlight": "rgba(255, 255, 255, 0.08)",
      "--site-glow-subtle": "rgba(255, 255, 255, 0.05)",
      "--site-glow-intense": "rgba(255, 255, 255, 0.15)",
      "--site-mobile-nav-bg": "rgba(10, 10, 10, 0.85)",
      "--site-mobile-nav-inactive": "rgba(238, 238, 238, 0.5)",
      "--site-on-hero": "#ffffff",
      "--site-date-badge-bg": "rgba(0, 0, 0, 0.85)",
      "--site-cta-gradient": "linear-gradient(to right, #333333, #555555, #333333)",
      "--site-cta-shadow": "0 4px 20px rgba(0, 0, 0, 0.5)",
      "--site-hero-overlay": "linear-gradient(to bottom, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.4) 50%, rgba(0,0,0,0.85) 100%)",
      "--site-hero-accent-1": "linear-gradient(135deg, #ffffff 0%, #888888 100%)",
      "--site-hero-accent-2": "linear-gradient(135deg, #cccccc 0%, #444444 100%)",
      "--site-hero-cta-gradient": "linear-gradient(135deg, #555555 0%, #333333 100%)",
      "--site-hero-cta-shadow": "0 8px 32px rgba(255, 255, 255, 0.1)",
      "--site-hero-bg-light": "rgba(255, 255, 255, 0.05)",
      "--site-hero-border-light": "rgba(255, 255, 255, 0.1)",
      "--site-hero-badge-bg": "rgba(255, 255, 255, 0.05)",
      "--site-hero-badge-border": "rgba(255, 255, 255, 0.2)",
      "--site-hero-badge-color": "rgba(255, 255, 255, 0.8)",
      "--site-card-glass-gradient": "linear-gradient(135deg, rgba(255,255,255,0.02) 0%, rgba(0,0,0,0.08) 100%)",
      "--site-card-glass-glow": "radial-gradient(circle at 30% 50%, rgba(255,255,255,0.1) 0%, transparent 60%)",
      "--site-card-shadow": "0 32px 64px -16px rgba(0,0,0,0.3)",
      "--site-mobile-nav-shadow": "0 20px 40px rgba(0, 0, 0, 0.5)",
      "--site-mobile-nav-glow": "0 0 15px rgba(255, 255, 255, 0.1)",
    },
  },
];

export function applyPreset(key: string): Record<string, string> {
  const preset = THEME_PRESETS.find((p) => p.key === key);
  return preset ? { ...preset.tokens } : buildDefaultTokens();
}

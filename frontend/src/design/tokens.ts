/**
 * @deprecated Prefer CSS custom properties (e.g. `hsl(var(--primary))`) or the
 * Tailwind theme (e.g. `bg-primary`, `text-primary`) instead of these JS
 * objects. Keeping them temporarily for backwards compatibility until all
 * consumers migrate.
 */
export const colors = {
    primary: {
        50: '#e6f3f8',
        100: '#b3dce8',
        200: '#80c5d8',
        300: '#4dafc8',
        400: '#269dba',
        500: '#018abd',
        600: '#006e96',
        700: '#004581',
        800: '#002d6b',
        900: '#001b48',
    },
    emerald: {
        50: '#ecfdf5',
        100: '#d1fae5',
        200: '#a7f3d0',
        300: '#6ee7b7',
        400: '#34d399',
        500: '#10b981',
        600: '#059669',
        700: '#047857',
        800: '#065f46',
        900: '#064e3b',
    },
    amber: {
        50: '#fffbeb',
        100: '#fef3c7',
        200: '#fde68a',
        300: '#fcd34d',
        400: '#fbbf24',
        500: '#f59e0b',
        600: '#d97706',
        700: '#b45309',
        800: '#92400e',
        900: '#78350f',
    },
    blue: {
        50: '#eff6ff',
        100: '#dbeafe',
        200: '#bfdbfe',
        300: '#93c5fd',
        400: '#60a5fa',
        500: '#3b82f6',
        600: '#2563eb',
        700: '#1d4ed8',
        800: '#1e40af',
        900: '#1e3a8a',
    },
    slate: {
        50: '#f8fafc',
        100: '#f1f5f9',
        200: '#e2e8f0',
        300: '#cbd5e1',
        400: '#94a3b8',
        500: '#64748b',
        600: '#475569',
        700: '#334155',
        800: '#1e293b',
        900: '#0f172a',
        ink: '#0b0d11',
    },
    danger: {
        50: '#fef2f2',
        100: '#fee2e2',
        200: '#fecaca',
        300: '#fca5a5',
        400: '#f87171',
        500: '#ef4444',
        600: '#dc2626',
        700: '#b91c1c',
        800: '#991b1b',
        900: '#7f1d1d',
    },
};

// Compact border radii (4-8px max for most elements)
/** @deprecated Prefer Tailwind border-radius utilities or CSS `--radius-*` tokens. */
export const radii = {
    sm: '0.25rem',     // 4px - badges, chips
    md: '0.375rem',    // 6px - buttons, inputs
    lg: '0.5rem',      // 8px - cards, dropdowns
    xl: '0.75rem',     // 12px - large overlays (max)
    pill: '9999px',    // only for avatar/status indicators
};

// Subtle shadows for compact UI
/** @deprecated Prefer Tailwind shadow utilities or CSS `--shadow-*` tokens. */
export const shadows = {
    soft: '0 1px 3px rgba(15, 23, 42, 0.08)',
    card: '0 1px 2px rgba(15, 23, 42, 0.06)',
    dropdown: '0 4px 12px rgba(15, 23, 42, 0.1)',
    inner: 'inset 0 1px 0 rgba(255,255,255,0.1)',
};

// Compact typography with weight hierarchy
/** @deprecated Prefer Tailwind typography utilities or CSS `--font-*` / `--text-*` tokens. */
export const typography = {
    family: 'var(--font-manrope, "Manrope", system-ui, -apple-system, sans-serif)',
    sizes: {
        xs: '0.6875rem',    // 11px - metadata, badges
        sm: '0.75rem',      // 12px - labels, secondary text
        base: '0.8125rem',  // 13px - body text default
        md: '0.875rem',     // 14px - primary text
        lg: '1rem',         // 16px - headings
        xl: '1.125rem',     // 18px - page titles
    },
    weights: {
        normal: 400,
        medium: 500,   // labels, body
        semibold: 600, // emphasis
        bold: 700,     // headings
        black: 900,    // sparingly - key metrics only
    },
};

// Compact spacing scale
/** @deprecated Prefer Tailwind spacing utilities. */
export const spacing = {
    xs: '0.25rem',   // 4px - tight gaps
    sm: '0.375rem',  // 6px - item gaps
    md: '0.5rem',    // 8px - section gaps
    lg: '0.75rem',   // 12px - card padding
    xl: '1rem',      // 16px - page padding
};

/** @deprecated Prefer Tailwind transition / animation utilities. */
export const motion = {
    duration: {
        quick: '100ms',
        base: '150ms',
        slow: '250ms',
    },
    easing: {
        entrance: 'cubic-bezier(0.16,1,0.3,1)',
        exit: 'cubic-bezier(0.7,0,0.84,0)',
    },
};

/** @deprecated Prefer CSS surface tokens or Tailwind color utilities. */
export const surfaces = {
    glass: 'rgba(255,255,255,0.08)',
    panel: '#111216',
    dark: '#1a1b1e',
    border: 'rgba(255,255,255,0.08)',
};

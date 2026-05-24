export const colors = {
    primary: {
        50: '#eef2ff',
        100: '#e0e7ff',
        200: '#c7d2fe',
        500: '#6366f1',
        600: '#4f46e5',
        700: '#4338ca',
    },
    emerald: {
        100: '#d1fae5',
        500: '#10b981',
        600: '#059669',
    },
    amber: {
        100: '#fef3c7',
        500: '#f59e0b',
        600: '#d97706',
    },
    violet: {
        100: '#ede9fe',
        500: '#8b5cf6',
        600: '#7c3aed',
    },
    slate: {
        50: '#f8fafc',
        100: '#f1f5f9',
        300: '#cbd5f5',
        500: '#64748b',
        900: '#0f172a',
        ink: '#0b0d11',
    },
    danger: '#ef4444',
};

// Compact border radii (4-8px max for most elements)
export const radii = {
    sm: '0.25rem',     // 4px - badges, chips
    md: '0.375rem',    // 6px - buttons, inputs
    lg: '0.5rem',      // 8px - cards, dropdowns
    xl: '0.75rem',     // 12px - modals (max)
    pill: '9999px',    // only for avatar/status indicators
};

// Subtle shadows for compact UI
export const shadows = {
    soft: '0 1px 3px rgba(15, 23, 42, 0.08)',
    card: '0 1px 2px rgba(15, 23, 42, 0.06)',
    dropdown: '0 4px 12px rgba(15, 23, 42, 0.1)',
    inner: 'inset 0 1px 0 rgba(255,255,255,0.1)',
};

// Compact typography with weight hierarchy
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
export const spacing = {
    xs: '0.25rem',   // 4px - tight gaps
    sm: '0.375rem',  // 6px - item gaps
    md: '0.5rem',    // 8px - section gaps
    lg: '0.75rem',   // 12px - card padding
    xl: '1rem',      // 16px - page padding
};

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

export const surfaces = {
    glass: 'rgba(255,255,255,0.08)',
    panel: '#111216',
    border: 'rgba(255,255,255,0.08)',
};

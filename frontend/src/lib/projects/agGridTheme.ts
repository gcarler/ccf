import { useEffect, useState } from 'react';
import { themeQuartz } from 'ag-grid-community';

export function useIsDark() {
    const [isDark, setIsDark] = useState(false);

    useEffect(() => {
        const check = () => setIsDark(document.documentElement.classList.contains('dark'));
        check();
        const obs = new MutationObserver(check);
        obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        return () => obs.disconnect();
    }, []);

    return isDark;
}

const baseParams = {
    fontFamily: 'inherit',
    fontSize: 12,
    headerHeight: 36,
    cellHorizontalPaddingScale: 0.8,
};

export const agGridLightTheme = themeQuartz.withParams({
    ...baseParams,
    rowHeight: 40,
    backgroundColor: 'hsl(var(--bg-primary))',
    foregroundColor: 'hsl(var(--text-primary))',
    borderColor: 'hsl(var(--border))',
    oddRowBackgroundColor: 'hsl(var(--surface-1))',
    headerBackgroundColor: 'hsl(var(--surface-2))',
    headerTextColor: 'hsl(var(--text-secondary))',
    selectedRowBackgroundColor: 'hsl(var(--primary)/0.1)',
    accentColor: 'hsl(var(--primary))',
});

export const agGridDarkTheme = themeQuartz.withParams({
    ...baseParams,
    rowHeight: 40,
    backgroundColor: 'hsl(var(--admin-bg-secondary))',
    foregroundColor: 'hsl(var(--text-secondary))',
    borderColor: 'hsla(0,0%,100%,0.08)',
    oddRowBackgroundColor: 'hsla(0,0%,100%,0.02)',
    headerBackgroundColor: 'hsla(0,0%,100%,0.04)',
    headerTextColor: 'hsl(var(--text-secondary))',
    selectedRowBackgroundColor: 'hsla(var(--primary-hsl),0.15)',
    accentColor: 'hsl(var(--primary))',
});

/** Compact variant for project overview tables (rowHeight 36) */
export const agGridCompactLightTheme = themeQuartz.withParams({
    ...baseParams,
    rowHeight: 36,
    backgroundColor: 'hsl(var(--bg-primary))',
    foregroundColor: 'hsl(var(--text-primary))',
    borderColor: 'hsl(var(--border))',
    oddRowBackgroundColor: 'hsl(var(--surface-1))',
    headerBackgroundColor: 'hsl(var(--surface-2))',
    headerTextColor: 'hsl(var(--text-secondary))',
    selectedRowBackgroundColor: 'hsl(var(--primary)/0.1)',
    accentColor: 'hsl(var(--primary))',
});

export const agGridCompactDarkTheme = themeQuartz.withParams({
    ...baseParams,
    rowHeight: 36,
    backgroundColor: 'hsl(var(--admin-bg-secondary))',
    foregroundColor: 'hsl(var(--text-secondary))',
    borderColor: 'hsla(0,0%,100%,0.08)',
    oddRowBackgroundColor: 'hsla(0,0%,100%,0.02)',
    headerBackgroundColor: 'hsla(0,0%,100%,0.04)',
    headerTextColor: 'hsl(var(--text-secondary))',
    selectedRowBackgroundColor: 'hsla(var(--primary-hsl),0.15)',
    accentColor: 'hsl(var(--primary))',
});

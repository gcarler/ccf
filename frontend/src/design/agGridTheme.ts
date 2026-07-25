import { useMemo } from 'react';
import { themeQuartz } from 'ag-grid-community';
import { useDarkMode } from '@/hooks/useDarkMode';
import { semanticColorsLight, semanticColorsDark } from './tokens-semantic';

export type AgGridDensity = 'compact' | 'default' | 'comfortable';

interface ThemeConfig {
  density: AgGridDensity;
  isDark: boolean;
}

const DENSITY_HEIGHT: Record<AgGridDensity, number> = {
  compact: 36,
  default: 40,
  comfortable: 44,
};

function buildThemeParams({ density, isDark }: ThemeConfig) {
  const tokens = isDark ? semanticColorsDark : semanticColorsLight;

  return {
    fontFamily: 'inherit',
    fontSize: 12,
    rowHeight: DENSITY_HEIGHT[density],
    headerHeight: 36,
    cellHorizontalPaddingScale: 0.8,

    backgroundColor: `hsl(${tokens['bg-primary']})`,
    foregroundColor: `hsl(${isDark ? tokens['text-secondary'] : tokens['text-primary']})`,
    borderColor: `hsl(${tokens['border']})`,
    oddRowBackgroundColor: `hsl(${tokens['surface-1']})`,
    rowHoverColor: `hsl(${tokens['bg-muted']})`,
    headerBackgroundColor: `hsl(${tokens['surface-2']})`,
    headerTextColor: `hsl(${tokens['text-secondary']})`,
    selectedRowBackgroundColor: `hsl(${tokens['primary']} / ${isDark ? '0.15' : '0.1'})`,
    accentColor: `hsl(${tokens['primary']})`,
  };
}

/**
 * Build a themeQuartz theme from the CCF semantic design tokens.
 * Avoids CSS custom properties, which themeQuartz.withParams cannot reliably resolve.
 */
export function createAgGridTheme(isDark: boolean, density: AgGridDensity = 'default') {
  return themeQuartz.withParams(buildThemeParams({ isDark, density }));
}

/**
 * React hook that returns the active AgGrid theme based on the current
 * light/dark mode and the desired row density.
 */
export function useAgGridTheme(density: AgGridDensity = 'default') {
  const isDark = useDarkMode();
  return useMemo(() => createAgGridTheme(isDark, density), [isDark, density]);
}

export default createAgGridTheme;

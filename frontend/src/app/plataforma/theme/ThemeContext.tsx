"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { apiFetch } from '@/lib/http';

export type ThemeMode = 'day' | 'night';

export type UiScaleId = 'compact' | 'normal' | 'comfortable' | 'large';

export type UiDensity = 'ultra-compact' | 'compact' | 'comfortable' | 'spacious';

export type AccentId = 'ccf-blue' | 'emerald' | 'indigo' | 'burgundy' | 'amber' | 'ocean';

export interface UiDensityOption {
    id: UiDensity;
    label: string;
    description: string;
    paddingRatio: string;
    rowHeight: string;
    padX: string;
    padY: string;
    gap: string;
    padYDelta: string;
    padXDelta: string;
    gapDelta: string;
    hDelta: string;
}

export const UI_DENSITY_OPTIONS: Record<UiDensity, UiDensityOption> = {
    'ultra-compact': {
        id: 'ultra-compact',
        label: 'Ultra compacta',
        description: 'Espaciado mínimo, máxima información en pantalla',
        paddingRatio: '0.75',
        rowHeight: '28px',
        padX: '0.5rem',
        padY: '0.125rem',
        gap: '0.25rem',
        padYDelta: '0px',
        padXDelta: '0px',
        gapDelta: '0px',
        hDelta: '0px',
    },
    compact: {
        id: 'compact',
        label: 'Compacta',
        description: 'Espaciado ajustado para flujos densos y alta productividad',
        paddingRatio: '0.875',
        rowHeight: '36px',
        padX: '0.75rem',
        padY: '0.375rem',
        gap: '0.5rem',
        padYDelta: '0.125rem',
        padXDelta: '0.125rem',
        gapDelta: '0.125rem',
        hDelta: '4px',
    },
    comfortable: {
        id: 'comfortable',
        label: 'Cómoda',
        description: 'Densidad equilibrada estándar recomendada',
        paddingRatio: '1.0',
        rowHeight: '44px',
        padX: '1rem',
        padY: '0.625rem',
        gap: '0.75rem',
        padYDelta: '0.25rem',
        padXDelta: '0.25rem',
        gapDelta: '0.25rem',
        hDelta: '8px',
    },
    spacious: {
        id: 'spacious',
        label: 'Espaciosa',
        description: 'Espaciado amplio para lectura descansada o pantallas táctiles',
        paddingRatio: '1.25',
        rowHeight: '52px',
        padX: '1.25rem',
        padY: '0.875rem',
        gap: '1rem',
        padYDelta: '0.375rem',
        padXDelta: '0.5rem',
        gapDelta: '0.375rem',
        hDelta: '12px',
    },
};

export const ZOOM_PRESETS: number[] = [90, 100, 110, 115, 120, 125, 130, 133];
export const MIN_ZOOM = 85;
export const MAX_ZOOM = 140;

export interface UiScaleOption {
    id: UiScaleId;
    label: string;
    percentage: string;
    scale: number;
    description: string;
}

export interface AccentColorPair {
    primary: string;
    primaryForeground: string;
}

export interface AccentOption {
    id: AccentId;
    label: string;
    description: string;
    swatch: string;
    wcagDayRatio: number;
    wcagNightRatio: number;
    day: AccentColorPair;
    night: AccentColorPair;
}

export const UI_SCALE_OPTIONS: Record<UiScaleId, UiScaleOption> = {
    compact: {
        id: 'compact',
        label: 'Compacto',
        percentage: '90%',
        scale: 0.9,
        description: 'Mayor densidad informativa en pantalla',
    },
    normal: {
        id: 'normal',
        label: 'Normal',
        percentage: '100%',
        scale: 1.0,
        description: 'Escala estándar recomendada de la plataforma',
    },
    comfortable: {
        id: 'comfortable',
        label: 'Cómodo',
        percentage: '115%',
        scale: 1.15,
        description: 'Mayor legibilidad y espaciado relajado',
    },
    large: {
        id: 'large',
        label: 'Grande',
        percentage: '125%',
        scale: 1.25,
        description: 'Máxima accesibilidad visual para lectura fácil',
    },
};

export const ACCENT_PALETTES: Record<AccentId, AccentOption> = {
    'ccf-blue': {
        id: 'ccf-blue',
        label: 'Azul CCF',
        description: 'Azul institucional canónico',
        swatch: '#01629e',
        wcagDayRatio: 5.48,
        wcagNightRatio: 8.20,
        day: {
            primary: '197 98% 31%',
            primaryForeground: '0 0% 100%',
        },
        night: {
            primary: '197 85% 52%',
            primaryForeground: '222 47% 4%',
        },
    },
    emerald: {
        id: 'emerald',
        label: 'Esmeralda',
        description: 'Vida, crecimiento y mayordomía',
        swatch: '#1d8758',
        wcagDayRatio: 4.54,
        wcagNightRatio: 9.47,
        day: {
            primary: '158 64% 32%',
            primaryForeground: '0 0% 100%',
        },
        night: {
            primary: '158 65% 48%',
            primaryForeground: '222 47% 4%',
        },
    },
    indigo: {
        id: 'indigo',
        label: 'Índigo',
        description: 'Sabiduría ministerial y visión',
        swatch: '#292ec9',
        wcagDayRatio: 10.79,
        wcagNightRatio: 5.26,
        day: {
            primary: '243 75% 42%',
            primaryForeground: '0 0% 100%',
        },
        night: {
            primary: '235 80% 68%',
            primaryForeground: '222 47% 4%',
        },
    },
    burgundy: {
        id: 'burgundy',
        label: 'Borgoña',
        description: 'Pacto, comunión y solemnidad',
        swatch: '#950e2b',
        wcagDayRatio: 8.83,
        wcagNightRatio: 5.05,
        day: {
            primary: '348 83% 32%',
            primaryForeground: '0 0% 100%',
        },
        night: {
            primary: '348 75% 58%',
            primaryForeground: '222 47% 4%',
        },
    },
    amber: {
        id: 'amber',
        label: 'Ámbar',
        description: 'Unción, discernimiento y fervor',
        swatch: '#935306',
        wcagDayRatio: 5.76,
        wcagNightRatio: 9.36,
        day: {
            primary: '35 92% 30%',
            primaryForeground: '0 0% 100%',
        },
        night: {
            primary: '38 92% 50%',
            primaryForeground: '222 47% 4%',
        },
    },
    ocean: {
        id: 'ocean',
        label: 'Océano',
        description: 'Misiones, alcance y expansión',
        swatch: '#0a6884',
        wcagDayRatio: 5.43,
        wcagNightRatio: 9.18,
        day: {
            primary: '188 86% 28%',
            primaryForeground: '0 0% 100%',
        },
        night: {
            primary: '188 78% 48%',
            primaryForeground: '222 47% 4%',
        },
    },
};

export interface AppearanceContextProps {
    theme: ThemeMode;
    toggleTheme: () => void;
    setTheme: (mode: ThemeMode) => void;

    // Interface Scale (legacy compatibility)
    uiScale: UiScaleId;
    setUiScale: (scale: UiScaleId) => void;
    scaleFactor: number;
    currentScale: UiScaleOption;

    // Interface Density
    uiDensity: UiDensity;
    setUiDensity: (density: UiDensity) => void;
    currentDensity: UiDensityOption;

    // Manual Zoom
    zoomPercentage: number;
    setZoomPercentage: (zoom: number) => void;
    zoomIn: () => void;
    zoomOut: () => void;

    // Accent Palette
    accent: AccentId;
    setAccent: (accent: AccentId) => void;
    currentAccent: AccentOption;

    // Sync & Persistence
    isSyncing: boolean;
    syncPreferences: () => Promise<void>;
    resetToDefaults: () => void;
}

export type ThemeContextProps = AppearanceContextProps;

const themeTokens: Record<ThemeMode, Record<string, string>> = {
    day: {
        '--bg-primary': '0 0% 100%',
        '--bg-secondary': '210 40% 98%',
        '--text-primary': '222 47% 11%',
        '--text-secondary': '215 16% 47%',
        '--surface-1': '0 0% 100%',
        '--surface-2': '210 40% 98%',
        '--surface-3': '210 40% 96.1%',
        '--border': '214 32% 91%',
        '--border-glass': '0 0% 100% / 0.2',
        '--shadow-glass': '0 8px 32px 0 rgba(31, 38, 135, 0.07)',
    },
    night: {
        '--bg-primary': '222 47% 4%',
        '--bg-secondary': '222 47% 6%',
        '--text-primary': '210 40% 98%',
        '--text-secondary': '215 20.2% 65.1%',
        '--surface-1': '222 47% 4%',
        '--surface-2': '222 47% 10%',
        '--surface-3': '222 47% 15%',
        '--border': '217 33% 17%',
        '--border-glass': '0 0% 100% / 0.05',
        '--shadow-glass': '0 8px 32px 0 rgba(0, 0, 0, 0.4)',
    },
};

const ThemeContext = createContext<AppearanceContextProps | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
    const [theme, setThemeState] = useState<ThemeMode>('day');
    const [uiScale, setUiScaleState] = useState<UiScaleId>('normal');
    const [uiDensity, setUiDensityState] = useState<UiDensity>('ultra-compact');
    const [zoomPercentage, setZoomPercentageState] = useState<number>(100);
    const [accent, setAccentState] = useState<AccentId>('ccf-blue');
    const [isMounted, setIsMounted] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);

    // ── Step 1: Read saved preferences once on mount ─────────────────
    useEffect(() => {
        try {
            const savedTheme = localStorage.getItem('theme-mode') as ThemeMode | null;
            if (savedTheme && (savedTheme === 'day' || savedTheme === 'night')) {
                setThemeState(savedTheme);
            }

            const savedScale = localStorage.getItem('theme-scale') as UiScaleId | null;
            if (savedScale && UI_SCALE_OPTIONS[savedScale]) {
                setUiScaleState(savedScale);
            }

            const savedDensity = localStorage.getItem('theme-density') as UiDensity | null;
            if (savedDensity && UI_DENSITY_OPTIONS[savedDensity]) {
                setUiDensityState(savedDensity);
            }

            const savedZoom = localStorage.getItem('theme-zoom');
            if (savedZoom) {
                const parsedZoom = Number(savedZoom);
                if (!isNaN(parsedZoom) && parsedZoom >= MIN_ZOOM && parsedZoom <= MAX_ZOOM) {
                    setZoomPercentageState(parsedZoom);
                }
            } else if (savedScale && UI_SCALE_OPTIONS[savedScale]) {
                setZoomPercentageState(Math.round(UI_SCALE_OPTIONS[savedScale].scale * 100));
            }

            const savedAccent = localStorage.getItem('theme-accent') as AccentId | null;
            if (savedAccent && ACCENT_PALETTES[savedAccent]) {
                setAccentState(savedAccent);
            }
        } catch {
            // localStorage not available or restricted
        }
        setIsMounted(true);
    }, []);

    // ── Step 2: Apply CSS custom properties, attributes, and classes ─
    useEffect(() => {
        if (!isMounted) return;

        const root = document.documentElement;

        // Attributes & classes
        root.setAttribute('data-theme', theme);
        root.setAttribute('data-ui-scale', uiScale);
        root.setAttribute('data-ui-density', uiDensity);
        root.setAttribute('data-accent', accent);

        if (theme === 'night') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }

        // Apply scale & density factors
        const scaleVal = (zoomPercentage / 100).toString();
        root.style.setProperty('--ui-scale', scaleVal);
        const densityOption = UI_DENSITY_OPTIONS[uiDensity] || UI_DENSITY_OPTIONS['ultra-compact'];
        root.style.setProperty('--density-row-h', densityOption.rowHeight);
        root.style.setProperty('--density-pad-x', densityOption.padX);
        root.style.setProperty('--density-pad-y', densityOption.padY);
        root.style.setProperty('--density-gap', densityOption.gap);
        root.style.setProperty('--ui-density-ratio', densityOption.paddingRatio);
        root.style.setProperty('--density-pad-y-delta', densityOption.padYDelta);
        root.style.setProperty('--density-pad-x-delta', densityOption.padXDelta);
        root.style.setProperty('--density-gap-delta', densityOption.gapDelta);
        root.style.setProperty('--density-h-delta', densityOption.hDelta);
        root.style.fontSize = `${zoomPercentage}%`;

        // Apply accent color
        const accentOption = ACCENT_PALETTES[accent] || ACCENT_PALETTES['ccf-blue'];
        const activeColor = theme === 'night' ? accentOption.night : accentOption.day;
        root.style.setProperty('--primary', activeColor.primary);
        root.style.setProperty('--primary-foreground', activeColor.primaryForeground);

        // Apply base theme tokens
        const vars = themeTokens[theme];
        Object.entries(vars).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });

        // Persist locally
        try {
            localStorage.setItem('theme-mode', theme);
            localStorage.setItem('theme-scale', uiScale);
            localStorage.setItem('theme-density', uiDensity);
            localStorage.setItem('theme-zoom', zoomPercentage.toString());
            localStorage.setItem('theme-accent', accent);
        } catch {
            // storage error
        }
    }, [theme, uiScale, uiDensity, zoomPercentage, accent, isMounted]);

    // ── Step 3: Remote profile synchronization ────────────────────────
    const syncPreferences = useCallback(async () => {
        setIsSyncing(true);
        try {
            await apiFetch('/v3/auth/preferences', {
                method: 'PUT',
                body: {
                    settings: {
                        theme_mode: theme,
                        ui_scale: uiScale,
                        ui_density: uiDensity,
                        zoom_percentage: zoomPercentage,
                        accent: accent,
                    },
                },
                silent: true,
            });
        } catch {
            // Silent fallback to local storage
        } finally {
            setIsSyncing(false);
        }
    }, [theme, uiScale, uiDensity, zoomPercentage, accent]);

    // Trigger background sync after user changes preferences
    useEffect(() => {
        if (!isMounted) return;
        const timer = setTimeout(() => {
            syncPreferences();
        }, 600);
        return () => clearTimeout(timer);
    }, [theme, uiScale, uiDensity, zoomPercentage, accent, isMounted, syncPreferences]);

    // Initial background reconciliation from remote profile
    useEffect(() => {
        if (!isMounted) return;

        let active = true;
        const fetchRemotePreferences = async () => {
            try {
                const res = await apiFetch<{
                    settings?: {
                        theme_mode?: ThemeMode;
                        ui_scale?: UiScaleId;
                        ui_density?: UiDensity;
                        zoom_percentage?: number;
                        accent?: AccentId;
                    };
                }>('/v3/auth/preferences', { silent: true });

                if (!active || !res?.settings) return;

                const remoteSettings = res.settings;
                if (remoteSettings.theme_mode && (remoteSettings.theme_mode === 'day' || remoteSettings.theme_mode === 'night')) {
                    setThemeState(remoteSettings.theme_mode);
                }
                if (remoteSettings.ui_density && UI_DENSITY_OPTIONS[remoteSettings.ui_density]) {
                    setUiDensityState(remoteSettings.ui_density);
                }
                if (typeof remoteSettings.zoom_percentage === 'number' && remoteSettings.zoom_percentage >= MIN_ZOOM && remoteSettings.zoom_percentage <= MAX_ZOOM) {
                    setZoomPercentageState(remoteSettings.zoom_percentage);
                }
                if (remoteSettings.ui_scale && UI_SCALE_OPTIONS[remoteSettings.ui_scale]) {
                    setUiScaleState(remoteSettings.ui_scale);
                }
                if (remoteSettings.accent && ACCENT_PALETTES[remoteSettings.accent]) {
                    setAccentState(remoteSettings.accent);
                }
            } catch {
                // Not authenticated or network unavailable
            }
        };

        fetchRemotePreferences();

        return () => {
            active = false;
        };
    }, [isMounted]);

    const setTheme = (mode: ThemeMode) => setThemeState(mode);
    const toggleTheme = () => setThemeState(prev => (prev === 'day' ? 'night' : 'day'));

    const setUiScale = (scale: UiScaleId) => {
        setUiScaleState(scale);
        const option = UI_SCALE_OPTIONS[scale];
        if (option) {
            setZoomPercentageState(Math.round(option.scale * 100));
        }
    };

    const setUiDensity = (density: UiDensity) => {
        setUiDensityState(density);
    };

    const setZoomPercentage = (zoom: number) => {
        const clamped = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.round(zoom)));
        setZoomPercentageState(clamped);
        if (clamped <= 95) setUiScaleState('compact');
        else if (clamped <= 105) setUiScaleState('normal');
        else if (clamped <= 118) setUiScaleState('comfortable');
        else setUiScaleState('large');
    };

    const zoomIn = () => {
        const current = zoomPercentage;
        const next = ZOOM_PRESETS.find(p => p > current);
        if (next) {
            setZoomPercentage(next);
        } else {
            setZoomPercentage(Math.min(MAX_ZOOM, current + 5));
        }
    };

    const zoomOut = () => {
        const current = zoomPercentage;
        const prev = [...ZOOM_PRESETS].reverse().find(p => p < current);
        if (prev) {
            setZoomPercentage(prev);
        } else {
            setZoomPercentage(Math.max(MIN_ZOOM, current - 5));
        }
    };

    const setAccent = (newAccent: AccentId) => setAccentState(newAccent);

    const resetToDefaults = () => {
        setThemeState('day');
        setUiScaleState('normal');
        setUiDensityState('ultra-compact');
        setZoomPercentageState(100);
        setAccentState('ccf-blue');
    };

    const currentScale = UI_SCALE_OPTIONS[uiScale] || UI_SCALE_OPTIONS.normal;
    const currentDensity = UI_DENSITY_OPTIONS[uiDensity] || UI_DENSITY_OPTIONS['ultra-compact'];
    const currentAccent = ACCENT_PALETTES[accent] || ACCENT_PALETTES['ccf-blue'];

    return (
        <ThemeContext.Provider
            value={{
                theme,
                toggleTheme,
                setTheme,
                uiScale,
                setUiScale,
                scaleFactor: currentScale.scale,
                currentScale,
                uiDensity,
                setUiDensity,
                currentDensity,
                zoomPercentage,
                setZoomPercentage,
                zoomIn,
                zoomOut,
                accent,
                setAccent,
                currentAccent,
                isSyncing,
                syncPreferences,
                resetToDefaults,
            }}
        >
            {children}
        </ThemeContext.Provider>
    );
};

export const AppearanceContext = ThemeContext;
export const AppearanceProvider = ThemeProvider;

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) throw new Error('useTheme must be used within ThemeProvider');
    return context;
};

export const useAppearance = useTheme;

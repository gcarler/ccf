"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { apiFetch } from '@/lib/http';

export type ThemeMode = 'day' | 'night';

export type UiScaleId = 'compact' | 'normal' | 'comfortable' | 'large';

export type AccentId = 'ccf-blue' | 'emerald' | 'indigo' | 'burgundy' | 'amber' | 'ocean';

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

    // Interface Scale
    uiScale: UiScaleId;
    setUiScale: (scale: UiScaleId) => void;
    scaleFactor: number;
    currentScale: UiScaleOption;

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
        root.setAttribute('data-accent', accent);

        if (theme === 'night') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }

        // Apply scale factor
        const scaleOption = UI_SCALE_OPTIONS[uiScale] || UI_SCALE_OPTIONS.normal;
        root.style.setProperty('--ui-scale', scaleOption.scale.toString());
        root.style.fontSize = `${scaleOption.scale * 100}%`;

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
            localStorage.setItem('theme-accent', accent);
        } catch {
            // storage error
        }
    }, [theme, uiScale, accent, isMounted]);

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
    }, [theme, uiScale, accent]);

    // Trigger background sync after user changes preferences
    useEffect(() => {
        if (!isMounted) return;
        const timer = setTimeout(() => {
            syncPreferences();
        }, 600);
        return () => clearTimeout(timer);
    }, [theme, uiScale, accent, isMounted, syncPreferences]);

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
                        accent?: AccentId;
                    };
                }>('/v3/auth/preferences', { silent: true });

                if (!active || !res?.settings) return;

                const remoteSettings = res.settings;
                if (remoteSettings.theme_mode && (remoteSettings.theme_mode === 'day' || remoteSettings.theme_mode === 'night')) {
                    setThemeState(remoteSettings.theme_mode);
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
    const setUiScale = (scale: UiScaleId) => setUiScaleState(scale);
    const setAccent = (newAccent: AccentId) => setAccentState(newAccent);

    const resetToDefaults = () => {
        setThemeState('day');
        setUiScaleState('normal');
        setAccentState('ccf-blue');
    };

    const currentScale = UI_SCALE_OPTIONS[uiScale] || UI_SCALE_OPTIONS.normal;
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

"use client";

import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';


export type ThemeMode = 'day' | 'night';

interface ThemeContextProps {
    theme: ThemeMode;
    toggleTheme: () => void;
    setTheme: (mode: ThemeMode) => void;
}

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
        '--border-glass': '255 255% 255% / 0.05',
        '--shadow-glass': '0 8px 32px 0 rgba(0, 0, 0, 0.4)',
    }
};

const ThemeContext = createContext<ThemeContextProps | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
    const [theme, setThemeState] = useState<ThemeMode>('day');
    const [isMounted, setIsMounted] = useState(false);

    // ── Step 1: Read saved preference once on mount ─────────────────
    useEffect(() => {
        const saved = localStorage.getItem('theme-mode') as ThemeMode | null;
        if (saved && themeTokens[saved]) {
            setThemeState(saved);
        } else if (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            setThemeState('night');
        }
        // Mark as mounted on next render cycle with the correct initial theme
        setIsMounted(true);
    }, []);

    // ── Step 2: Apply class + data-attr to <html> on every theme change ─
    useEffect(() => {
        if (!isMounted) return; // Do not apply or save until hydration is complete

        const root = document.documentElement;
        root.setAttribute('data-theme', theme === 'night' ? 'night' : 'day');
        if (theme === 'night') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
        
        localStorage.setItem('theme-mode', theme);
    }, [theme, isMounted]);

    // ── Step 3: Apply CSS custom properties ─────────────────────────
    useEffect(() => {
        if (!isMounted) return;
        
        const vars = themeTokens[theme];
        Object.entries(vars).forEach(([key, value]) => {
            document.documentElement.style.setProperty(key, value);
        });
    }, [theme, isMounted]);

    const setTheme = (mode: ThemeMode) => setThemeState(mode);
    const toggleTheme = () => setThemeState(prev => (prev === 'day' ? 'night' : 'day'));

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) throw new Error('useTheme must be used within ThemeProvider');
    return context;
};

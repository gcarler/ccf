"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';


interface ThemeContextProps {
    theme: 'light' | 'dark';
    toggleTheme: () => void;
    palette: string;
    setPalette: (palette: string) => void;
}

// Preset palettes
const palettes: Record<string, Record<string, string>> = {
    light: {
        '--bg-primary': '#f8fafc',
        '--bg-secondary': '#ffffff',
        '--text-primary': '#0f172a',
        '--text-secondary': '#64748b',
        '--accent': '#3b82f6',
    },
    dark: {
        '--bg-primary': '#0f172a',
        '--bg-secondary': '#1e293b',
        '--text-primary': '#f1f5f9',
        '--text-secondary': '#94a3b8',
        '--accent': '#60a5fa',
    },
    ocean: {
        '--bg-primary': '#e0f7fa',
        '--bg-secondary': '#b2ebf2',
        '--text-primary': '#006064',
        '--text-secondary': '#004d40',
        '--accent': '#00bcd4',
    },
    sunset: {
        '--bg-primary': '#fff3e0',
        '--bg-secondary': '#ffcc80',
        '--text-primary': '#bf360c',
        '--text-secondary': '#e64a19',
        '--accent': '#ff9800',
    },
};

const ThemeContext = createContext<ThemeContextProps | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
    const [theme, setTheme] = useState<'light' | 'dark'>('light');
    const [palette, setPaletteState] = useState<string>('light');

    // Load saved theme and palette
    useEffect(() => {
        const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
        const savedPalette = localStorage.getItem('palette');
        if (savedTheme) setTheme(savedTheme);
        if (savedPalette && palettes[savedPalette]) setPaletteState(savedPalette);
    }, []);

    // Apply theme attribute
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    // Apply palette CSS variables
    useEffect(() => {
        const vars = palettes[palette] || palettes['light'];
        Object.entries(vars).forEach(([key, value]) => {
            document.documentElement.style.setProperty(key, value);
        });
        localStorage.setItem('palette', palette);
    }, [palette]);

    const toggleTheme = () => {
        setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
    };

    const setPalette = (name: string) => {
        if (palettes[name]) {
            setPaletteState(name);
        } else {
            console.warn(`Palette ${name} not found`);
        }
    };

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme, palette, setPalette }}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) throw new Error('useTheme must be used within ThemeProvider');
    return context;
};

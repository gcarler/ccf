"use client";

import React from 'react';

import { useTheme } from '@/app/theme/ThemeContext';

const palettes = ['light', 'dark', 'ocean', 'sunset'];

export default function PaletteSelector() {
    const { palette, setPalette } = useTheme();

    return (
        <div className="flex flex-col space-y-4">
            <h2 className="text-lg font-semibold">Seleccionar Paleta</h2>
            <div className="flex space-x-2">
                {palettes.map((p) => (
                    <button
                        key={p}
                        onClick={() => setPalette(p)}
                        className={`px-4 py-2 rounded ${palette === p ? 'bg-accent text-white' : 'bg-gray-200'} transition-colors`}
                    >
                        {p.charAt(0).toUpperCase() + p.slice(1)}
                    </button>
                ))}
            </div>
        </div>
    );
}

"use client";

import React from 'react';

import { useTheme, ThemeMode } from '@/app/theme/ThemeContext';

const themeOptions: { id: ThemeMode; label: string; description: string; swatches: string[] }[] = [
    {
        id: 'day',
        label: 'Modo Día',
        description: 'Luminoso, fresco y listo para trabajar',
        swatches: ['#f8fafc', '#e2e8f0', '#0f172a']
    },
    {
        id: 'night',
        label: 'Modo Noche',
        description: 'Oscuro, enfocado y relajado',
        swatches: ['#0f172a', '#1e293b', '#94a3b8']
    }
];

export default function PaletteSelector() {
    const { theme, setTheme, toggleTheme } = useTheme();

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Temas Día / Noche</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Personaliza el ambiente visual de la plataforma.</p>
                </div>
                <button
                    onClick={toggleTheme}
                    className="text-xs font-semibold uppercase tracking-wide px-3 py-1.5 rounded-full border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/10 transition"
                >
                    Alternar
                </button>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {themeOptions.map(({ id, label, description, swatches }) => {
                    const isActive = theme === id;
                    return (
                        <button
                            key={id}
                            onClick={() => setTheme(id)}
                            className={`text-left p-4 rounded-2xl border transition-all duration-300 ${
                                isActive
                                    ? 'border-blue-500 shadow-lg shadow-blue-500/10 bg-white/90 dark:bg-slate-900'
                                    : 'border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/5 hover:border-slate-300 dark:hover:border-white/20'
                            }`}
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-semibold text-slate-900 dark:text-white">{label}</p>
                                    <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p>
                                </div>
                                <div className="flex -space-x-1">
                                    {swatches.map((hex) => (
                                        <span
                                            key={hex}
                                            className="w-6 h-6 rounded-full border border-white/40"
                                            style={{ backgroundColor: hex }}
                                        />
                                    ))}
                                </div>
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}


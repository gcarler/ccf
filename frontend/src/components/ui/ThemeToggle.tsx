"use client";

import React from "react";
import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/app/plataforma/theme/ThemeContext";
import Tooltip from "@/components/ui/Tooltip";

interface ThemeToggleProps {
    /** 'icon' = solo icono circular (para mini-sidebar / toolbar) */
    variant?: "icon" | "pill" | "row";
    className?: string;
}

export default function ThemeToggle({ variant = "icon", className = "" }: ThemeToggleProps) {
    const { theme, toggleTheme } = useTheme();
    const isNight = theme === "night";

    if (variant === "row") {
        /* Fila con label — para sidebar expandido */
        return (
            <button
                onClick={toggleTheme}
                className={`w-full flex items-center justify-between px-3 py-2 mx-2 rounded-md transition-all group cursor-pointer mb-0.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white ${className}`}
                title={isNight ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
            >
                <div className="flex items-center gap-3">
                    {isNight ? (
                        <Moon size={18} className="text-slate-400 group-hover:text-[hsl(var(--primary))]" />
                    ) : (
                        <Sun size={18} className="text-slate-400 group-hover:text-[hsl(var(--primary))]" />
                    )}
                    <span className="text-[13px] font-bold leading-none">
                        {isNight ? "Modo Oscuro" : "Modo Claro"}
                    </span>
                </div>
                {/* Pill toggle */}
                <div
                    className={`relative w-9 h-5 rounded-full transition-colors duration-300 ${
                        isNight ? "bg-[hsl(var(--primary))]" : "bg-slate-200"
                    }`}
                >
                    <span
                        className={`absolute top-0.5 size-4 bg-[hsl(var(--bg-primary))] rounded-full shadow-sm transition-transform duration-300 ${
                            isNight ? "translate-x-4" : "translate-x-0.5"
                        }`}
                    />
                </div>
            </button>
        );
    }

    if (variant === "pill") {
        /* Pill doble compacto — para toolbars */
        return (
            <div
                className={`flex items-center rounded-md p-1 gap-0.5 ${
                    isNight
                        ? "bg-slate-800 border border-white/5"
                        : "bg-slate-100 border border-slate-200"
                } ${className}`}
            >
                <button
                    onClick={() => isNight && toggleTheme()}
                    className={`size-6 rounded-lg flex items-center justify-center transition-all ${
                        !isNight
                            ? "bg-[hsl(var(--bg-primary))] text-amber-500 shadow-sm"
                            : "text-slate-500 hover:text-slate-300"
                    }`}
                    title="Cambiar a modo claro"
                    aria-label="Modo claro"
                >
                    <Sun size={13} />
                </button>
                <button
                    onClick={() => !isNight && toggleTheme()}
                    className={`size-6 rounded-lg flex items-center justify-center transition-all ${
                        isNight
                            ? "bg-white/10 text-[hsl(var(--primary))]"
                            : "text-slate-400 hover:text-slate-600"
                    }`}
                    title="Cambiar a modo oscuro"
                    aria-label="Modo oscuro"
                >
                    <Moon size={13} />
                </button>
            </div>
        );
    }

    /* Default: icon — para mini-sidebar */
    return (
        <Tooltip content={isNight ? "Modo Claro" : "Modo Oscuro"} side="right">
            <button
                onClick={toggleTheme}
                className={`size-10 rounded-lg flex items-center justify-center transition-all group ${
                    isNight
                        ? "text-slate-400 hover:bg-white/5 hover:text-amber-300"
                        : "text-slate-600 hover:bg-black/5 hover:text-[hsl(var(--primary))]"
                } ${className}`}
            >
                {isNight ? <Sun size={19} /> : <Moon size={19} />}
            </button>
        </Tooltip>
    );
}

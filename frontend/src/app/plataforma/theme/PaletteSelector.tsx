"use client";

import React from 'react';
import {
    Sun,
    Moon,
    Check,
    RotateCcw,
    ShieldCheck,
    Cloud,
    Loader2,
    Sparkles,
} from 'lucide-react';
import {
    useTheme,
    ACCENT_PALETTES,
    ThemeMode,
    AccentId,
} from '@/app/plataforma/theme/ThemeContext';
import DensityZoomSelector from '@/app/plataforma/theme/DensityZoomSelector';

export default function PaletteSelector() {
    const {
        theme,
        setTheme,
        toggleTheme,
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
        currentScale,
        isSyncing,
        resetToDefaults,
    } = useTheme();

    const themeModes: { id: ThemeMode; label: string; description: string; icon: React.ComponentType<{ className?: string }> }[] = [
        {
            id: 'day',
            label: 'Modo Día',
            description: 'Luminoso, fresco y optimizado para entornos con alta luz',
            icon: Sun,
        },
        {
            id: 'night',
            label: 'Modo Noche',
            description: 'Oscuro, enfocado y diseñado para descansar la vista',
            icon: Moon,
        },
    ];

    const accentList = Object.values(ACCENT_PALETTES);

    return (
        <div className="space-y-6">
            {/* ── 1. Modo de Apariencia ────────────────────────────────────────── */}
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))]">Ambiente Visual</h2>
                        <p className="text-2xs text-[hsl(var(--text-secondary))]">
                            Elige entre modo claro u oscuro según tu preferencia visual.
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={toggleTheme}
                        aria-label="Alternar entre modo día y modo noche"
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[hsl(var(--border))] text-2xs font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                    >
                        {theme === 'night' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
                        <span>Alternar modo</span>
                    </button>
                </div>

                <div
                    role="radiogroup"
                    aria-label="Seleccionar modo de ambiente visual"
                    className="grid grid-cols-1 sm:grid-cols-2 gap-3"
                >
                    {themeModes.map(({ id, label, description, icon: Icon }) => {
                        const isSelected = theme === id;
                        return (
                            <button
                                key={id}
                                type="button"
                                role="radio"
                                aria-checked={isSelected}
                                aria-label={`${label}: ${description}`}
                                onClick={() => setTheme(id)}
                                className={`text-left p-3.5 rounded-lg border transition-all duration-200 flex items-start gap-3 ${
                                    isSelected
                                        ? 'border-[hsl(var(--primary))] bg-[hsl(var(--surface-2))] shadow-sm ring-1 ring-[hsl(var(--primary))]'
                                        : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary)/0.4)] hover:bg-[hsl(var(--surface-2))]'
                                }`}
                            >
                                <div
                                    className={`p-2 rounded-md ${
                                        isSelected
                                            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                                            : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]'
                                    }`}
                                >
                                    <Icon className="w-4 h-4" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">{label}</span>
                                        {isSelected && (
                                            <span className="inline-flex items-center gap-1 text-3xs font-medium text-[hsl(var(--primary))]">
                                                <Check className="w-3 h-3" /> Activo
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5 leading-snug">{description}</p>
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* ── 2. Densidad de Interfaz y Zoom de Pantalla ────────────────── */}
            <div className="pt-1">
                <DensityZoomSelector showDensity={true} showZoom={true} />
            </div>

            {/* ── 3. Paleta de Acentos Ministeriales ──────────────────────────── */}
            <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))]">Acento Ministerial</h2>
                        <p className="text-2xs text-[hsl(var(--text-secondary))]">
                            Colores canónicos seleccionados con contraste auditado WCAG AA para máxima legibilidad.
                        </p>
                    </div>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-[hsl(var(--border))] text-3xs font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))]">
                        <ShieldCheck className="w-3 h-3 text-[hsl(var(--primary))]" />
                        Contraste WCAG AA
                    </span>
                </div>

                <div
                    role="radiogroup"
                    aria-label="Seleccionar color de acento ministerial"
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5"
                >
                    {accentList.map((item) => {
                        const isSelected = accent === item.id;
                        const currentRatio = theme === 'night' ? item.wcagNightRatio : item.wcagDayRatio;

                        return (
                            <button
                                key={item.id}
                                type="button"
                                role="radio"
                                aria-checked={isSelected}
                                aria-label={`Color de acento ${item.label}: ${item.description}. Contraste ratio ${currentRatio.toFixed(1)} a 1`}
                                onClick={() => setAccent(item.id as AccentId)}
                                className={`text-left p-3 rounded-lg border transition-all duration-200 flex items-start gap-2.5 ${
                                    isSelected
                                        ? 'border-[hsl(var(--primary))] bg-[hsl(var(--surface-2))] shadow-sm ring-1 ring-[hsl(var(--primary))]'
                                        : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary)/0.4)] hover:bg-[hsl(var(--surface-2))]'
                                }`}
                            >
                                <span
                                    className="w-7 h-7 rounded-full shrink-0 border border-[hsl(var(--border))] flex items-center justify-center shadow-inner mt-0.5"
                                    style={{ backgroundColor: item.swatch }}
                                >
                                    {isSelected && <Check className="w-3.5 h-3.5 text-white stroke-[3]" />}
                                </span>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">{item.label}</span>
                                        <span className="text-3xs font-medium text-[hsl(var(--text-secondary))]">
                                            {currentRatio.toFixed(1)}:1
                                        </span>
                                    </div>
                                    <p className="text-2xs text-[hsl(var(--text-secondary))] leading-tight mt-0.5">
                                        {item.description}
                                    </p>
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* ── 4. Previsualización en Vivo ─────────────────────────────────── */}
            <div
                role="region"
                aria-label="Previsualización de tema y accesibilidad en vivo"
                className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4 space-y-3.5"
            >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[hsl(var(--border))] pb-2.5">
                    <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-[hsl(var(--primary))]" />
                        <h3 className="text-xs font-semibold text-[hsl(var(--text-primary))]">Previsualización en Vivo</h3>
                    </div>
                    <div className="flex items-center gap-3">
                        <span className="text-3xs text-[hsl(var(--text-secondary))]">
                            {currentScale.label} ({zoomPercentage}%) • {currentDensity.label} • {currentAccent.label}
                        </span>
                        <div className="flex items-center gap-1 text-3xs text-[hsl(var(--text-secondary))]">
                            {isSyncing ? (
                                <>
                                    <Loader2 className="w-3 h-3 animate-spin text-[hsl(var(--primary))]" />
                                    <span>Sincronizando...</span>
                                </>
                            ) : (
                                <>
                                    <Cloud className="w-3 h-3 text-[hsl(var(--primary))]" />
                                    <span>Guardado</span>
                                </>
                            )}
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
                    {/* Tarjeta de muestra de componentes */}
                    <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3.5 space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">
                                Panel de Demostración
                            </span>
                            <span className="px-2 py-0.5 rounded-full text-3xs font-semibold bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]">
                                Acento Activo
                            </span>
                        </div>

                        <p className="text-2xs text-[hsl(var(--text-secondary))] leading-relaxed">
                            Esta tarjeta refleja en tiempo real los colores, escalas y pesos aplicados a la plataforma CCF.
                        </p>

                        <div className="flex flex-wrap items-center gap-2 pt-1">
                            <button
                                type="button"
                                className="px-3 py-1.5 rounded-md text-2xs font-semibold bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm hover:opacity-90 transition-opacity"
                            >
                                Acción Principal
                            </button>
                            <button
                                type="button"
                                className="px-3 py-1.5 rounded-md text-2xs font-medium border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] transition-colors"
                            >
                                Acción Secundaria
                            </button>
                        </div>
                    </div>

                    {/* Muestra de jerarquía tipográfica según escala */}
                    <div className="space-y-2 px-1">
                        <div className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                            Jerarquía Tipográfica Escala {currentScale.label}
                        </div>
                        <div className="space-y-1">
                            <div className="text-base font-semibold text-[hsl(var(--text-primary))]">
                                Título de Sección ({currentScale.percentage})
                            </div>
                            <div className="text-xs text-[hsl(var(--text-primary))]">
                                Texto estándar del cuerpo de la plataforma
                            </div>
                            <div className="text-2xs text-[hsl(var(--text-secondary))]">
                                Micro-etiquetas, metadatos y sellos de tiempo
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* ── 5. Restablecer valores ──────────────────────────────────────── */}
            <div className="flex items-center justify-between pt-2 border-t border-[hsl(var(--border))]">
                <span className="text-2xs text-[hsl(var(--text-secondary))]">
                    ¿Deseas volver a la configuración original de la plataforma?
                </span>
                <button
                    type="button"
                    onClick={resetToDefaults}
                    aria-label="Restablecer valores predeterminados de tema, escala y acento"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[hsl(var(--border))] text-2xs font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Restablecer predeterminados</span>
                </button>
            </div>
        </div>
    );
}

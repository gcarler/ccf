"use client";

import React from 'react';
import {
    Minus,
    Plus,
    RotateCcw,
    Maximize2,
    Minimize2,
    Check,
    Layers,
    Sliders,
} from 'lucide-react';
import {
    useTheme,
    UI_DENSITY_OPTIONS,
    ZOOM_PRESETS,
    MIN_ZOOM,
    MAX_ZOOM,
    UiDensity,
} from '@/app/plataforma/theme/ThemeContext';

export interface DensityZoomSelectorProps {
    className?: string;
    showDensity?: boolean;
    showZoom?: boolean;
}

export default function DensityZoomSelector({
    className = '',
    showDensity = true,
    showZoom = true,
}: DensityZoomSelectorProps) {
    const {
        uiDensity,
        setUiDensity,
        currentDensity,
        zoomPercentage,
        setZoomPercentage,
        zoomIn,
        zoomOut,
    } = useTheme();

    const densityList = Object.values(UI_DENSITY_OPTIONS);

    const getDensityIcon = (id: UiDensity) => {
        switch (id) {
            case 'ultra-compact':
                return Minimize2;
            case 'compact':
                return Layers;
            case 'comfortable':
                return Sliders;
            case 'spacious':
                return Maximize2;
            default:
                return Layers;
        }
    };

    return (
        <div className={`space-y-6 ${className}`} data-testid="density-zoom-selector">
            {/* ── 1. Selector de Densidad de Interfaz ───────────────────────── */}
            {showDensity && (
                <div className="space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                            <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                                Densidad de Interfaz
                            </h2>
                            <p className="text-2xs text-[hsl(var(--text-secondary))]">
                                Configura el espaciado vertical, paddings y separación entre componentes.
                            </p>
                        </div>
                        <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]">
                            {currentDensity.label}
                        </span>
                    </div>

                    <div
                        role="radiogroup"
                        aria-label="Seleccionar densidad de interfaz"
                        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5"
                    >
                        {densityList.map((item) => {
                            const isSelected = uiDensity === item.id;
                            const IconComponent = getDensityIcon(item.id);

                            return (
                                <button
                                    key={item.id}
                                    type="button"
                                    role="radio"
                                    aria-checked={isSelected}
                                    aria-label={`Densidad ${item.label}: ${item.description}`}
                                    onClick={() => setUiDensity(item.id as UiDensity)}
                                    className={`text-left p-3 rounded-lg border transition-all duration-200 flex flex-col justify-between ${
                                        isSelected
                                            ? 'border-[hsl(var(--primary))] bg-[hsl(var(--surface-2))] shadow-sm ring-1 ring-[hsl(var(--primary))]'
                                            : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary)/0.4)] hover:bg-[hsl(var(--surface-2))]'
                                    }`}
                                >
                                    <div className="flex items-center justify-between w-full mb-2">
                                        <div className="flex items-center gap-2">
                                            <div
                                                className={`p-1.5 rounded-md ${
                                                    isSelected
                                                        ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                                                        : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]'
                                                }`}
                                            >
                                                <IconComponent className="w-3.5 h-3.5" />
                                            </div>
                                            <span className="text-xs font-semibold text-[hsl(var(--text-primary))]">
                                                {item.label}
                                            </span>
                                        </div>
                                        {isSelected && (
                                            <span className="inline-flex items-center text-[hsl(var(--primary))]">
                                                <Check className="w-3.5 h-3.5" />
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-3xs text-[hsl(var(--text-secondary))] leading-tight">
                                        {item.description}
                                    </p>
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* ── 2. Control de Zoom y Escala Manual ────────────────────────── */}
            {showZoom && (
                <div className="space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                            <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                                Zoom de Pantalla y Texto
                            </h2>
                            <p className="text-2xs text-[hsl(var(--text-secondary))]">
                                Ajusta el factor de escala global ({MIN_ZOOM}% a {MAX_ZOOM}%) mediante presets o slider continuo.
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            <span
                                data-testid="zoom-percentage-badge"
                                className="text-xs font-bold px-2.5 py-1 rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                            >
                                {zoomPercentage}%
                            </span>
                            {zoomPercentage !== 100 && (
                                <button
                                    type="button"
                                    onClick={() => setZoomPercentage(100)}
                                    aria-label="Restablecer zoom a 100%"
                                    className="p-1 rounded-md border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                                    title="Restablecer a 100%"
                                >
                                    <RotateCcw className="w-3.5 h-3.5" />
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Controles de paso y slider */}
                    <div className="p-3.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] space-y-3.5">
                        <div className="flex items-center gap-3">
                            <button
                                type="button"
                                onClick={zoomOut}
                                disabled={zoomPercentage <= MIN_ZOOM}
                                aria-label="Disminuir zoom"
                                className="p-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-3))] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                            >
                                <Minus className="w-4 h-4" />
                            </button>

                            <div className="flex-1 space-y-1">
                                <label
                                    htmlFor="zoom-range-slider"
                                    className="sr-only"
                                >
                                    Ajuste de zoom continuo
                                </label>
                                <input
                                    id="zoom-range-slider"
                                    type="range"
                                    min={MIN_ZOOM}
                                    max={MAX_ZOOM}
                                    step={1}
                                    value={zoomPercentage}
                                    onChange={(e) => setZoomPercentage(Number(e.target.value))}
                                    aria-label="Ajuste de zoom continuo"
                                    aria-valuemin={MIN_ZOOM}
                                    aria-valuemax={MAX_ZOOM}
                                    aria-valuenow={zoomPercentage}
                                    aria-valuetext={`${zoomPercentage} por ciento`}
                                    className="w-full accent-[hsl(var(--primary))] cursor-pointer h-2 bg-[hsl(var(--surface-3))] rounded-lg"
                                />
                                <div className="flex justify-between text-3xs text-[hsl(var(--text-secondary))] px-0.5">
                                    <span>{MIN_ZOOM}%</span>
                                    <span>100% (Estándar)</span>
                                    <span>{MAX_ZOOM}%</span>
                                </div>
                            </div>

                            <button
                                type="button"
                                onClick={zoomIn}
                                disabled={zoomPercentage >= MAX_ZOOM}
                                aria-label="Aumentar zoom"
                                className="p-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-3))] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                            >
                                <Plus className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Presets rápidos */}
                        <div>
                            <span className="text-3xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] block mb-1.5">
                                Accesos rápidos de escala
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                                {ZOOM_PRESETS.map((preset) => {
                                    const isActive = zoomPercentage === preset;
                                    return (
                                        <button
                                            key={preset}
                                            type="button"
                                            onClick={() => setZoomPercentage(preset)}
                                            aria-pressed={isActive}
                                            aria-label={`Establecer zoom a ${preset}%`}
                                            className={`px-2.5 py-1 rounded-md text-2xs font-semibold transition-all ${
                                                isActive
                                                    ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-xs'
                                                    : 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-3))]'
                                            }`}
                                        >
                                            {preset}%
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

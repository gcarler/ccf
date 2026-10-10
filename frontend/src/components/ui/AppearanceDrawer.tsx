"use client";

import React from 'react';
import { Palette, ShieldCheck, Sparkles } from 'lucide-react';
import RightPanel from '@/components/ui/RightPanel';
import PaletteSelector from '@/app/plataforma/theme/PaletteSelector';
import { useTheme } from '@/app/plataforma/theme/ThemeContext';

export interface AppearanceDrawerProps {
    isOpen?: boolean;
    open?: boolean;
    onClose: () => void;
    className?: string;
}

export function AppearanceDrawer({
    isOpen: isOpenProp,
    open: openProp,
    onClose,
    className = '',
}: AppearanceDrawerProps) {
    const isVisible = isOpenProp ?? openProp ?? false;
    const { theme, currentScale, currentAccent, currentDensity, zoomPercentage } = useTheme();

    return (
        <RightPanel
            open={isVisible}
            onClose={onClose}
            width="w-full sm:max-w-xl md:max-w-2xl"
            className={className}
            title={
                <div className="flex items-center gap-2.5">
                    <span className="p-1.5 rounded-md bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]">
                        <Palette className="w-4 h-4" />
                    </span>
                    <div>
                        <span className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                            Personalización de Apariencia
                        </span>
                    </div>
                </div>
            }
            description={
                <span className="text-2xs text-[hsl(var(--text-secondary))]">
                    Ambiente visual, escala de interfaz y paleta de acentos ministeriales
                </span>
            }
        >
            <div className="p-4 sm:p-5 space-y-5" data-testid="appearance-drawer-content">
                {/* Micro-resumen superior accesible */}
                <div
                    role="note"
                    aria-label="Resumen de configuración visual activa"
                    className="flex flex-wrap items-center justify-between gap-2.5 p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
                >
                    <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-[hsl(var(--primary))]" />
                        <span className="text-2xs font-semibold text-[hsl(var(--text-primary))]">
                            {theme === 'night' ? 'Modo Noche' : 'Modo Día'} • {currentScale.label} ({zoomPercentage}%) • {currentDensity.label}
                        </span>
                        <span className="text-[hsl(var(--border))]">•</span>
                        <span className="inline-flex items-center gap-1 text-2xs font-medium text-[hsl(var(--text-secondary))]">
                            <span
                                className="w-2.5 h-2.5 rounded-full inline-block"
                                style={{ backgroundColor: currentAccent.swatch }}
                            />
                            {currentAccent.label}
                        </span>
                    </div>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-3xs font-semibold bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]">
                        <ShieldCheck className="w-3 h-3" /> WCAG AA Conforme
                    </span>
                </div>

                {/* Selector universal de temas, escalas y acentos */}
                <PaletteSelector />
            </div>
        </RightPanel>
    );
}

export default AppearanceDrawer;

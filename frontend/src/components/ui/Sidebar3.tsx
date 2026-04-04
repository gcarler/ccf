"use client";

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronLeft } from 'lucide-react';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import clsx from 'clsx';

interface Sidebar3Props {
    children: React.ReactNode;
    title?: string;
    subtitle?: string;
    width?: number; // default 280px
}

/**
 * Sidebar3 — Capa de contexto (nivel 3 de profundidad).
 * 
 * Se posiciona como una capa deslizante que aparece después de S2.
 * Z-index: 30 (debajo de S2=40, debajo de S1=50).
 * Tiene box-shadow pronunciada en el borde derecho para crear profundidad visual.
 * 
 * Comportamiento:
 * - Aparece desde el lado izquierdo, empujando el contenido central
 * - El foco se mueve al panel al abrirse (accesibilidad)
 * - ESC lo cierra (manejado por SidebarLayerContext global)
 */
export default function Sidebar3({
    children,
    title,
    subtitle,
    width = 280,
}: Sidebar3Props) {
    const { layers, closeLayer } = useSidebarLayers();
    const isOpen = layers.S3;
    const panelRef = useRef<HTMLDivElement>(null);

    // Accesibilidad: mover foco al panel al abrirse
    useEffect(() => {
        if (isOpen && panelRef.current) {
            const focusable = panelRef.current.querySelectorAll<HTMLElement>(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            // Pequeño delay para esperar la animación
            setTimeout(() => focusable[0]?.focus(), 150);
        }
    }, [isOpen]);

    return (
        <AnimatePresence initial={false}>
            {isOpen && (
                <motion.aside
                    ref={panelRef}
                    key="sidebar3"
                    initial={{ x: -width - 20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: -width - 20, opacity: 0 }}
                    transition={{ type: 'tween', duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
                    style={{
                        width,
                        minWidth: width,
                        maxWidth: width,
                        // Z-index 30: debajo de S2 (40) pero encima del contenido
                        zIndex: 30,
                        // Box-shadow pronunciada en el borde derecho para profundidad
                        boxShadow: '8px 0 32px rgba(0, 0, 0, 0.10), 2px 0 8px rgba(0, 0, 0, 0.06)',
                    }}
                    className="h-full flex flex-col bg-white dark:bg-[#18191b] border-r border-slate-100 dark:border-white/5 relative"
                    tabIndex={-1}
                    role="navigation"
                    aria-label={title || 'Panel de contexto'}
                >
                    {/* Header */}
                    {(title || subtitle) && (
                        <div className="h-11 flex items-center justify-between px-4 border-b border-slate-100 dark:border-white/5 shrink-0 gap-2">
                            <div className="flex items-center gap-2 min-w-0">
                                <button
                                    onClick={() => closeLayer('S3')}
                                    aria-label="Cerrar panel de contexto"
                                    className="p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-all shrink-0"
                                >
                                    <ChevronLeft size={15} />
                                </button>
                                <div className="min-w-0">
                                    {title && (
                                        <p className="text-[11px] font-bold text-slate-700 dark:text-slate-200 truncate leading-tight">
                                            {title}
                                        </p>
                                    )}
                                    {subtitle && (
                                        <p className="text-[9px] font-medium text-slate-400 uppercase tracking-widest truncate leading-tight">
                                            {subtitle}
                                        </p>
                                    )}
                                </div>
                            </div>
                            <button
                                onClick={() => closeLayer('S3')}
                                aria-label="Cerrar"
                                className="p-1 rounded-md text-slate-300 dark:text-slate-600 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 transition-all shrink-0"
                            >
                                <X size={13} />
                            </button>
                        </div>
                    )}

                    {/* Scrollable content */}
                    <div className="flex-1 overflow-y-auto overflow-x-hidden">
                        {children}
                    </div>
                </motion.aside>
            )}
        </AnimatePresence>
    );
}

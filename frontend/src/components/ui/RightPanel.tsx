"use client";

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import clsx from 'clsx';

interface RightPanelProps {
    title?: string;
    children: React.ReactNode;
    width?: number; // px, default 320
    trigger?: React.ReactNode;
    showTrigger?: boolean;
    /** Modo controlado: cuando se pasa open/onClose, el panel se comporta como Drawer overlay fijo */
    open?: boolean;
    onClose?: () => void;
}

/**
 * RightPanel — Sidebar derecho bajo demanda.
 * Soporta dos modos:
 *  - 'push'    → empuja el contenido central (reduce flex-1)
 *  - 'overlay' → se superpone con backdrop semitransparente
 *
 * El modo se controla desde SidebarLayerContext.
 *
 * También soporta modo controlado pasando `open` y `onClose`.
 */
function RightPanel({
    title = 'Actividad',
    children,
    width = 320,
    trigger,
    showTrigger = false,
    open: controlledOpen,
    onClose,
}: RightPanelProps) {
    const { layers, closeLayer, rightMode } = useSidebarLayers();
    const isControlled = controlledOpen !== undefined;
    const isOpen = isControlled ? controlledOpen : layers.RIGHT;
    const panelRef = useRef<HTMLDivElement>(null);

    // Focus trap: move focus into panel when it opens
    useEffect(() => {
        if (isOpen && panelRef.current) {
            const focusable = panelRef.current.querySelectorAll<HTMLElement>(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            focusable[0]?.focus();
        }
    }, [isOpen]);

    const handleClose = () => {
        if (isControlled) {
            onClose?.();
        } else {
            closeLayer('RIGHT');
        }
    };

    const panel = (
        <motion.aside
            ref={panelRef}
            key="right-panel"
            initial={{ x: width, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: width, opacity: 0 }}
            transition={{ type: 'tween', duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
            style={{ width, minWidth: width, maxWidth: width }}
            className={clsx(
                'h-full flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] border-l border-slate-100 dark:border-white/5',
                isControlled || rightMode === 'overlay'
                    ? 'fixed right-0 top-0 z-[35] shadow-[-24px_0_60px_rgba(0,0,0,0.12)]'
                    : 'relative z-[25] shadow-[-8px_0_24px_rgba(0,0,0,0.06)]'
            )}
            tabIndex={-1}
            role="complementary"
            aria-label={title}
        >
            {/* Panel header */}
            <div className="h-10 flex items-center justify-between px-4 border-b border-slate-100 dark:border-white/5 shrink-0">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    {title}
                </span>
                <div className="flex items-center gap-1">
                    <button
                        onClick={handleClose}
                        aria-label="Cerrar panel"
                        className="p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
                    >
                        <X size={14} />
                    </button>
                </div>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden">
                {children}
            </div>
        </motion.aside>
    );

    if (isControlled || rightMode === 'overlay') {
        return (
            <>
                {showTrigger && trigger}
                <AnimatePresence>
                    {isOpen && (
                        <>
                            {/* Backdrop */}
                            <motion.div
                                key="right-backdrop"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                transition={{ duration: 0.2 }}
                                className={clsx(
                                    'z-[34] bg-slate-950/20 backdrop-blur-[1px]',
                                    isControlled ? 'fixed inset-0' : 'absolute inset-0'
                                )}
                                onClick={handleClose}
                                aria-hidden="true"
                            />
                            {panel}
                        </>
                    )}
                </AnimatePresence>
            </>
        );
    }

    // Push mode: panel is inline, AnimatePresence handles width
    return (
        <AnimatePresence initial={false}>
            {isOpen && panel}
        </AnimatePresence>
    );
}

export default RightPanel;
export { RightPanel };

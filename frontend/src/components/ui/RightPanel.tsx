"use client";

import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Maximize2, Minimize2, X } from 'lucide-react';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { useFocusTrap } from '@/hooks/useFocusTrap';
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
    const [isExpanded, setIsExpanded] = useState(false);

    const isOverlay = isControlled || rightMode === 'overlay';

    const handleClose = () => {
        if (isControlled) {
            onClose?.();
        } else {
            closeLayer('RIGHT');
        }
    };

    // Focus trap + Escape: only in controlled/overlay mode where the panel
    // behaves as a modal drawer. In push mode it is part of the normal layout.
    useFocusTrap(panelRef, {
        active: isOpen && isOverlay,
        onEscape: handleClose,
    });

    const PanelContainer = isOverlay ? motion.div : motion.aside;

    const panel = (
        <PanelContainer
            ref={panelRef}
            key="right-panel"
            initial={{ x: width, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: width, opacity: 0 }}
            transition={{ type: 'tween', duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
            style={{ width: isExpanded ? '100vw' : `min(${width}px, 100vw)`, minWidth: 0, maxWidth: '100vw' }}
            className={clsx(
                'flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-elevated))] border-l border-[hsl(var(--border))] dark:border-[hsl(var(--border))]',
                isExpanded
                    ? 'fixed inset-0 h-screen z-[1001] shadow-2xl border-l-0'
                    : isControlled || rightMode === 'overlay'
                    ? 'fixed right-0 top-10 h-[calc(100vh-2.5rem)] z-[35] shadow-[-24px_0_60px_hsl(var(--shadow-floating))]'
                    : 'relative h-full z-[25] shadow-[-8px_0_24px_hsl(var(--shadow-floating))]'
            )}
            tabIndex={-1}
            role={isOverlay ? 'dialog' : 'complementary'}
            aria-modal={isOverlay ? 'true' : undefined}
            aria-label={title}
        >
            {/* Panel header */}
            <div className="h-10 flex items-center justify-between px-4 border-b border-[hsl(var(--border))] dark:border-[hsl(var(--border))] shrink-0">
                <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                    {title}
                </span>
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setIsExpanded((expanded) => !expanded)}
                        aria-label={isExpanded ? 'Contraer panel' : 'Expandir panel'}
                        aria-pressed={isExpanded}
                        title={isExpanded ? 'Contraer panel' : 'Expandir panel'}
                        className="inline-flex items-center gap-1 rounded-md border border-[hsl(var(--border))] px-2 py-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
                    >
                        {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                        <span>{isExpanded ? 'Contraer' : 'Expandir'}</span>
                    </button>
                    <button
                        onClick={handleClose}
                        aria-label="Cerrar panel"
                        className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-[hsl(var(--surface-2))] transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
                    >
                        <X size={14} />
                    </button>
                </div>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden">
                {children}
            </div>
        </PanelContainer>
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
                                    'z-[34] bg-[hsl(var(--bg-muted))]/20 backdrop-blur-[1px]',
                                    isExpanded || isControlled ? 'fixed inset-0' : 'absolute inset-0'
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

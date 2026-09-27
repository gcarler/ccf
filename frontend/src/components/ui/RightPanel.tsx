"use client";

import React, { useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import clsx from 'clsx';

interface RightPanelProps {
    /** Título del panel. Acepta string o nodo React (p. ej. icono + texto). */
    title?: React.ReactNode;
    /** Subtítulo opcional renderizado bajo el título. Acepta string o nodo React. */
    subtitle?: React.ReactNode;
    /** Descripción opcional (texto de contexto) renderizada bajo el título. */
    description?: React.ReactNode;
    children: React.ReactNode;
    /** Ancho en px (default 320) o clase Tailwind de ancho (p. ej. "w-full sm:max-w-2xl"). */
    width?: number | string;
    trigger?: React.ReactNode;
    showTrigger?: boolean;
    /** Modo controlado: cuando se pasa open/onClose, el panel se comporta como Drawer overlay fijo */
    open?: boolean;
    /** Alias de `open`, aceptado por compatibilidad con consumidores existentes */
    isOpen?: boolean;
    onClose?: () => void;
    /** Clases adicionales para el contenedor del panel */
    className?: string;
    /** Clases adicionales para el área de contenido */
    contentClassName?: string;
}

/**
 * RightPanel — Sidebar derecho bajo demanda.
 * Soporta dos modos:
 *  - 'push'    → empuja el contenido central (reduce flex-1)
 *  - 'overlay' → se superpone con backdrop semitransparente
 *
 * El modo se controla desde SidebarLayerContext.
 *
 * También soporta modo controlado pasando `open` (o su alias `isOpen`) y `onClose`.
 */
function RightPanel({
    title = 'Actividad',
    subtitle,
    description,
    children,
    width = 320,
    trigger,
    showTrigger = false,
    open: controlledOpen,
    isOpen: isOpenAlias,
    onClose,
    className,
    contentClassName,
}: RightPanelProps) {
    const { layers, closeLayer, rightMode } = useSidebarLayers();
    const open = controlledOpen ?? isOpenAlias;
    const isControlled = open !== undefined;
    const isOpen = isControlled ? open : layers.RIGHT;
    const panelRef = useRef<HTMLDivElement>(null);

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

    const widthStyle = typeof width === 'number'
        ? { width: `min(${width}px, 100vw)`, minWidth: 0, maxWidth: '100vw' }
        : undefined;
    const widthClass = typeof width === 'string' ? width : undefined;

    const panel = (
        <PanelContainer
            ref={panelRef}
            key="right-panel"
            initial={{ x: typeof width === 'number' ? width : 480, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: typeof width === 'number' ? width : 480, opacity: 0 }}
            transition={{ type: 'tween', duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
            style={widthStyle}
            className={clsx(
                'flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-elevated))] border-l border-[hsl(var(--border))] dark:border-[hsl(var(--border))]',
                widthClass,
                isControlled || rightMode === 'overlay'
                    ? 'fixed right-0 top-10 h-[calc(100vh-2.5rem)] z-[35] shadow-[-24px_0_60px_hsl(var(--shadow-floating))]'
                    : 'relative h-full z-[25] shadow-[-8px_0_24px_hsl(var(--shadow-floating))]',
                className,
            )}
            tabIndex={-1}
            role={isOverlay ? 'dialog' : 'complementary'}
            aria-modal={isOverlay ? 'true' : undefined}
            aria-label={typeof title === 'string' ? title : 'Panel'}
        >
            {/* Panel header */}
            <div className="shrink-0 px-4 py-2.5 border-b border-[hsl(var(--border))] dark:border-[hsl(var(--border))] flex items-start justify-between gap-2">
                <div className="min-w-0">
                    <div className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        {title}
                    </div>
                    {subtitle && (
                        <div className="mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
                            {subtitle}
                        </div>
                    )}
                    {description && (
                        <div className="mt-0.5 text-2xs text-[hsl(var(--text-secondary))] opacity-80 leading-snug">
                            {description}
                        </div>
                    )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
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
            <div className={clsx('flex-1 overflow-y-auto overflow-x-hidden', contentClassName)}>
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
                                    isControlled ? 'fixed inset-x-0 bottom-0 top-10' : 'absolute inset-0'
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

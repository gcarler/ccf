"use client";

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, MoreHorizontal, MessageSquare, Clock, Sparkles, Maximize2, Minimize2, type LucideIcon } from 'lucide-react';
import clsx from 'clsx';

interface WorkspaceDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    subtitle?: string;
    children: React.ReactNode;
    actions?: React.ReactNode;
}

const DEFAULT_WIDTH = 680;
const MIN_WIDTH = 380;

export default function WorkspaceDrawer({
    isOpen,
    onClose,
    title,
    subtitle,
    children,
    actions
}: WorkspaceDrawerProps) {
    const [width, setWidth] = useState(DEFAULT_WIDTH);
    const [isExpanded, setIsExpanded] = useState(false);
    const drawerRef = useRef<HTMLDivElement>(null);

    const handleClose = useCallback(() => {
        setIsExpanded(false);
        onClose();
    }, [onClose]);

    useEffect(() => {
        if (!isOpen) setIsExpanded(false);
    }, [isOpen]);

    const handleResizeDrag = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        const startX = e.clientX;
        const startWidth = drawerRef.current?.offsetWidth ?? DEFAULT_WIDTH;

        const onMouseMove = (ev: MouseEvent) => {
            const next = Math.max(MIN_WIDTH, Math.min(startWidth + startX - ev.clientX, window.innerWidth));
            setWidth(next);
        };
        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }, []);

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        data-testid="workspace-drawer-backdrop"
                        className="fixed inset-x-0 bottom-0 dark:bg-black/40 backdrop-blur-[2px] z-[1000]"
                        style={{
                            top: 'var(--workspace-header-height, 2.5rem)',
                            backgroundColor: 'hsl(var(--bg-primary) / 0.35)',
                        }}
                        onClick={handleClose}
                    />

                    <motion.div
                        ref={drawerRef}
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        className={clsx(
                            "fixed max-w-full bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-1))] shadow-[var(--shadow-floating)] z-[1001] border-l border-[hsl(var(--border))] flex flex-col focus:outline-none overflow-hidden",
                            isExpanded ? "inset-x-0 bottom-0 h-auto" : "right-0 h-auto"
                        )}
                        style={{
                            width: isExpanded || (typeof window !== 'undefined' && window.innerWidth < 640) ? '100vw' : width,
                            top: 'var(--workspace-header-height, 2.5rem)',
                            height: 'calc(100dvh - var(--workspace-header-height, 2.5rem))',
                        }}
                        role="complementary"
                        aria-label={title}
                    >
                        {/* Resize handle */}
                        <div
                            onMouseDown={handleResizeDrag}
                            className="absolute left-0 top-0 h-full w-1.5 cursor-col-resize group/resize z-10 select-none"
                            title="Arrastra para ajustar el ancho"
                        >
                            <div className="h-full w-full hover:bg-[hsl(var(--info))]/30 dark:hover:bg-[hsl(var(--info))]/20 transition-colors" />
                        </div>

                        {/* Drawer Header */}
                        <div
                            className="min-h-14 flex items-center justify-between gap-2 px-3 sm:px-5 py-3 border-b border-[hsl(var(--border))] shrink-0"
                            style={{ backgroundColor: 'hsl(var(--surface-2) / 0.5)' }}
                        >
                            <div className="flex min-w-0 items-center gap-3 sm:gap-4 overflow-hidden">
                                <button onClick={handleClose} aria-label="Cerrar" title="Cerrar panel" className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 rounded-md transition-colors text-[hsl(var(--text-secondary))] shrink-0">
                                    <X size={20} />
                                </button>
                                <button
                                    onClick={() => setIsExpanded((expanded) => !expanded)}
                                    aria-label={isExpanded ? "Contraer panel" : "Expandir panel"}
                                    aria-pressed={isExpanded}
                                    title={isExpanded ? "Contraer panel" : "Expandir panel"}
                                    className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-[hsl(var(--border))] px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 hover:text-[hsl(var(--text-primary))] transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
                                >
                                    {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                                    <span className="hidden sm:inline">{isExpanded ? "Contraer" : "Expandir"}</span>
                                </button>
                                <div className="h-6 w-[1px] bg-[hsl(var(--border))] dark:bg-white/10" />
                                <div className="flex flex-col overflow-hidden">
                                    <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))] truncate tracking-tight">
                                        {title}
                                    </h2>
                                    {subtitle && (
                                        <p className="text-2xs text-[hsl(var(--text-secondary))] font-black truncate uppercase tracking-wide">
                                            {subtitle}
                                        </p>
                                    )}
                                </div>
                            </div>

                            <div className="flex shrink-0 items-center gap-1">
                                <button className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-info-soft dark:bg-[hsl(var(--info))]/30 text-info-text dark:text-[hsl(var(--info))] rounded-lg text-2xs font-semibold uppercase tracking-wide hover:opacity-80 transition-all border border-[hsl(var(--info)/20%)] dark:border-[hsl(var(--info)/50%)]">
                                    <Sparkles size={14} /> Resumir
                                </button>
                                <div className="hidden sm:block h-5 w-[1px] bg-[hsl(var(--border))] dark:bg-white/10 mx-2" />
                                <HeaderButton icon={MessageSquare} tooltip="Comentarios" />
                                <HeaderButton icon={Clock} tooltip="Historial" />
                                <HeaderButton icon={MoreHorizontal} tooltip="Más" />
                            </div>
                        </div>

                        {/* Drawer Body */}
                        <div className="flex-1 min-w-0 overflow-y-auto scrollbar-thin px-4 sm:px-8 py-5">
                            {children}
                        </div>

                        {/* Drawer Footer */}
                        {actions && (
                            <div
                                className="px-4 sm:px-8 py-5 border-t border-[hsl(var(--border))] flex flex-wrap items-center justify-end gap-3 sm:gap-4 dark:bg-white/5"
                                style={{ backgroundColor: 'hsl(var(--surface-2) / 0.5)' }}
                            >
                                {actions}
                            </div>
                        )}
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

function HeaderButton({ icon: Icon, onClick, tooltip }: { icon: LucideIcon, onClick?: () => void, tooltip: string }) {
    return (
        <div className="relative group/drawer-btn">
            <button
                onClick={onClick}
                aria-label={tooltip}
                className="p-2 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-all"
            >
                <Icon size={18} />
            </button>
        </div>
    );
}

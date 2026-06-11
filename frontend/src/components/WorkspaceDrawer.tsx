"use client";

import React, { useCallback, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, MoreHorizontal, MessageSquare, Clock, Sparkles } from 'lucide-react';

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
    const drawerRef = useRef<HTMLDivElement>(null);

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
                        className="fixed inset-x-0 bottom-0 top-10 bg-slate-900/20 dark:bg-black/40 backdrop-blur-[2px] z-[1000]"
                        onClick={onClose}
                    />

                    <motion.div
                        ref={drawerRef}
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        style={{ width }}
                        className="fixed top-10 right-0 h-[calc(100vh-2.5rem)] bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] shadow-[var(--shadow-floating)] z-[1001] border-l border-slate-200 dark:border-white/10 flex flex-col focus:outline-none overflow-hidden"
                        role="complementary"
                        aria-label={title}
                    >
                        {/* Resize handle */}
                        <div
                            onMouseDown={handleResizeDrag}
                            className="absolute left-0 top-0 h-full w-1.5 cursor-col-resize group/resize z-10 select-none"
                            title="Arrastra para ajustar el ancho"
                        >
                            <div className="h-full w-full hover:bg-blue-400/30 dark:hover:bg-blue-500/20 transition-colors" />
                        </div>

                        {/* Drawer Header */}
                        <header className="h-14 flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-white/10 shrink-0 bg-slate-50/50 dark:bg-white/5">
                            <div className="flex items-center gap-4 overflow-hidden">
                                <button onClick={onClose} className="p-2 hover:bg-slate-200 dark:hover:bg-white/10 rounded-md transition-colors text-slate-500">
                                    <X size={20} />
                                </button>
                                <div className="h-6 w-[1px] bg-slate-200 dark:bg-white/10" />
                                <div className="flex flex-col overflow-hidden">
                                    <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate tracking-tight">
                                        {title}
                                    </h2>
                                    {subtitle && (
                                        <p className="text-[10px] text-slate-400 font-black truncate uppercase tracking-wide">
                                            {subtitle}
                                        </p>
                                    )}
                                </div>
                            </div>

                            <div className="flex items-center gap-1">
                                <button className="flex items-center gap-2 px-3 py-1.5 bg-sky-50 dark:bg-sky-900/30 text-sky-600 dark:text-sky-400 rounded-lg text-[10px] font-semibold uppercase tracking-wide hover:opacity-80 transition-all border border-sky-100 dark:border-sky-900/50">
                                    <Sparkles size={14} /> Resumir
                                </button>
                                <div className="h-5 w-[1px] bg-slate-200 dark:bg-white/10 mx-2" />
                                <HeaderButton icon={MessageSquare} tooltip="Comentarios" />
                                <HeaderButton icon={Clock} tooltip="Historial" />
                                <HeaderButton icon={MoreHorizontal} tooltip="Más" />
                            </div>
                        </header>

                        {/* Drawer Body */}
                        <main className="flex-1 overflow-y-auto scrollbar-thin px-8 py-5">
                            {children}
                        </main>

                        {/* Drawer Footer */}
                        {actions && (
                            <footer className="px-8 py-5 border-t border-slate-200 dark:border-white/10 flex items-center justify-end gap-4 bg-slate-50/50 dark:bg-white/5">
                                {actions}
                            </footer>
                        )}
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

function HeaderButton({ icon: Icon, onClick, tooltip }: { icon: any, onClick?: () => void, tooltip: string }) {
    void tooltip;
    return (
        <div className="relative group/drawer-btn">
            <button
                onClick={onClick}
                className="p-2 rounded-md text-slate-400 hover:text-slate-800 dark:hover:text-slate-100 hover:bg-slate-200 dark:hover:bg-white/10 transition-all"
            >
                <Icon size={18} />
            </button>
        </div>
    );
}

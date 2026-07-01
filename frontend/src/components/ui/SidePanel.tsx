"use client";

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronUp, ChevronDown, ExternalLink } from 'lucide-react';
import clsx from 'clsx';

interface SidePanelProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    subtitle?: string;
    children: React.ReactNode;
    width?: string; // e.g., "w-[400px]" or "w-[600px]"
    onPrev?: () => void;
    onNext?: () => void;
    fullViewHref?: string;
}

export default function SidePanel({
    isOpen,
    onClose,
    title,
    subtitle,
    children,
    width = "w-[450px]",
    onPrev,
    onNext,
    fullViewHref
}: SidePanelProps) {
    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ x: "100%", opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: "100%", opacity: 0 }}
                    transition={{ type: "spring", damping: 25, stiffness: 200 }}
                    className={clsx(
                        "fixed top-10 right-0 h-[calc(100vh-2.5rem)] z-[100] max-w-full bg-[hsl(var(--bg-primary))] dark:bg-[#1E1F21] shadow-2xl border-l border-[hsl(var(--border))] dark:border-white/10 flex flex-col",
                        width
                    )}
                >
                    {/* Header */}
                    <div className="h-8 px-4 flex items-center justify-between border-b border-[hsl(var(--border))] dark:border-white/5 shrink-0">
                        <div className="flex min-w-0 items-center gap-3">
                            <button
                                onClick={onClose}
                                className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] transition-all"
                            >
                                <X size={18} />
                            </button>
                            <div className="w-[1px] h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                            <div className="flex items-center gap-1">
                                {onPrev && (
                                    <button onClick={onPrev} className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-lg text-[hsl(var(--text-secondary))]">
                                        <ChevronUp size={16} />
                                    </button>
                                )}
                                {onNext && (
                                    <button onClick={onNext} className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-lg text-[hsl(var(--text-secondary))]">
                                        <ChevronDown size={16} />
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            {fullViewHref && (
                                <a
                                    href={fullViewHref}
                                    className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] transition-all"
                                    title="Vista completa"
                                >
                                    <ExternalLink size={18} />
                                </a>
                            )}
                        </div>
                    </div>

                    {/* Content Area */}
                    <div className="flex-1 min-w-0 overflow-y-auto custom-scrollbar p-3">
                        <header className="mb-3">
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mb-1">
                                DETALLES DEL ÍTEM
                            </p>
                            <h2 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white leading-tight">
                                {title}
                            </h2>
                            {subtitle && (
                                <p className="text-sm text-[hsl(var(--text-secondary))] mt-1">{subtitle}</p>
                            )}
                        </header>

                        {children}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

"use client";

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Target, Type, Palette, Loader2, Sparkles, X } from 'lucide-react';
import clsx from 'clsx';

interface Props {
    isOpen: boolean;
    /** The button element that triggered the popover (for positioning) */
    anchorRef?: React.RefObject<HTMLButtonElement | null>;
    onClose: () => void;
    onSubmit: (data: { title: string; description: string; color: string }) => Promise<void>;
}

const COLORS = [
    { name: 'Indigo',   value: '#4f46e5' },
    { name: 'Blue',     value: '#2563eb' },
    { name: 'Rose',     value: '#e11d48' },
    { name: 'Amber',    value: '#d97706' },
    { name: 'Emerald',  value: '#059669' },
    { name: 'Slate',    value: '#475569' },
];

export default function ProjectCreationModal({ isOpen, anchorRef, onClose, onSubmit }: Props) {
    const [title,       setTitle]       = useState('');
    const [description, setDescription] = useState('');
    const [color,       setColor]       = useState(COLORS[0].value);
    const [loading,     setLoading]     = useState(false);

    // Position the popover below the anchor button
    const [position, setPosition] = useState({ top: 80, right: 24 });
    const panelRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (isOpen && anchorRef?.current) {
            const rect = anchorRef.current.getBoundingClientRect();
            setPosition({
                top:   rect.bottom + 8,
                right: window.innerWidth - rect.right,
            });
        }
    }, [isOpen, anchorRef]);

    // Reset fields on open
    useEffect(() => {
        if (isOpen) {
            setTitle('');
            setDescription('');
            setColor(COLORS[0].value);
        }
    }, [isOpen]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) return;
        setLoading(true);
        try {
            await onSubmit({ title, description, color });
            onClose();
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Transparent backdrop to close on outside click */}
                    <div
                        className="fixed inset-0 z-[8998]"
                        onClick={onClose}
                    />

                    {/* Popover panel */}
                    <motion.div
                        ref={panelRef}
                        key="project-popover"
                        initial={{ opacity: 0, scale: 0.96, y: -8 }}
                        animate={{ opacity: 1, scale: 1,    y: 0  }}
                        exit={{   opacity: 0, scale: 0.96, y: -8  }}
                        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                        style={{ top: position.top, right: position.right }}
                        className="fixed z-[8999] w-full max-w-[420px] bg-white dark:bg-[#1e1f21] rounded-2xl shadow-2xl border border-slate-200 dark:border-white/10 overflow-hidden"
                    >
                        {/* Header */}
                        <div className="px-6 py-4 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-black/10">
                            <div className="flex items-center gap-3">
                                <div className="size-7 rounded-xl flex items-center justify-center text-white shadow" style={{ backgroundColor: color }}>
                                    <Target size={14} />
                                </div>
                                <div>
                                    <p className="text-[12px] font-black text-slate-800 dark:text-white uppercase tracking-tight">Nuevo Proyecto Maestro</p>
                                    <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Configuración de Misión</p>
                                </div>
                            </div>
                            <button onClick={onClose} className="p-1.5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-lg transition-all hover:rotate-90 duration-200 text-slate-400">
                                <X size={15} />
                            </button>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="p-6 space-y-5">
                            {/* Title */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                                    <Type size={11} /> Título del Proyecto
                                </label>
                                <input
                                    autoFocus
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder="Ej: Ministerio de Alabanza 2026"
                                    className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-[15px] font-bold outline-none focus:ring-2 focus:ring-blue-500/20 placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-800 dark:text-white transition-all"
                                />
                            </div>

                            {/* Description */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                                    <Sparkles size={11} /> Propósito / Descripción
                                </label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="¿Cuál es la meta global de este proyecto?"
                                    rows={3}
                                    className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-[13px] font-medium outline-none focus:ring-2 focus:ring-blue-500/20 resize-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-700 dark:text-slate-200 transition-all"
                                />
                            </div>

                            {/* Color */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                                    <Palette size={11} /> Identidad Visual
                                </label>
                                <div className="flex gap-2">
                                    {COLORS.map((c) => (
                                        <button
                                            key={c.value}
                                            type="button"
                                            onClick={() => setColor(c.value)}
                                            title={c.name}
                                            className={clsx(
                                                'size-8 rounded-xl transition-all',
                                                color === c.value
                                                    ? 'scale-110 shadow-lg ring-2 ring-offset-2 dark:ring-offset-[#1e1f21]'
                                                    : 'opacity-40 hover:opacity-80'
                                            )}
                                            style={{ backgroundColor: c.value }}
                                        />
                                    ))}
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="flex gap-3 pt-1">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="flex-1 py-2.5 text-[11px] font-bold uppercase tracking-widest text-slate-500 bg-slate-100 dark:bg-white/5 rounded-xl hover:bg-slate-200 dark:hover:bg-white/10 transition-all"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading || !title.trim()}
                                    className="flex-[2] py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[11px] font-black uppercase tracking-[0.2em] rounded-xl shadow-lg hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-40"
                                >
                                    {loading
                                        ? <Loader2 className="animate-spin" size={14} />
                                        : 'Crear Proyecto Maestro'
                                    }
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

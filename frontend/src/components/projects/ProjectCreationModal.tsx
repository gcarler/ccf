"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Target, Type, Palette, Flag, Loader2, Sparkles } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import clsx from 'clsx';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (data: { title: string; description: string; color: string }) => Promise<void>;
}

const COLORS = [
    { name: 'Indigo', value: '#4f46e5' },
    { name: 'Blue', value: '#2563eb' },
    { name: 'Rose', value: '#e11d48' },
    { name: 'Amber', value: '#d97706' },
    { name: 'Emerald', value: '#059669' },
    { name: 'Slate', value: '#475569' }
];

export default function ProjectCreationModal({ isOpen, onClose, onSubmit }: Props) {
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [color, setColor] = useState(COLORS[0].value);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) return;
        setLoading(true);
        try {
            await onSubmit({ title, description, color });
            setTitle('');
            setDescription('');
            onClose();
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 z-[9000] bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200" />
                <Dialog.Content className="fixed left-1/2 top-1/2 z-[9001] w-full max-w-[550px] -translate-x-1/2 -translate-y-1/2 rounded-[2.5rem] bg-white dark:bg-[#1e1f21] shadow-2xl border border-white/10 overflow-hidden animate-in zoom-in-95 duration-200">
                    <Dialog.Title className="sr-only">Nuevo Proyecto Maestro</Dialog.Title>
                    <Dialog.Description className="sr-only">Formulario para la creación de un nuevo proyecto en el ministerio.</Dialog.Description>
                    
                    <div className="p-8 space-y-8">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="size-10 rounded-2xl bg-blue-600 flex items-center justify-center text-white shadow-lg">
                                    <Target size={20} />
                                </div>
                                <div>
                                    <h3 className="text-xl font-black text-slate-900 dark:text-white leading-none">Nuevo Proyecto Maestro</h3>
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Configuración de Misión</p>
                                </div>
                            </div>
                            <Dialog.Close asChild>
                                <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-full transition-colors">
                                    <X size={20} className="text-slate-400" />
                                </button>
                            </Dialog.Close>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2">
                                    <Type size={12} /> Título del Proyecto
                                </label>
                                <input 
                                    autoFocus
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder="Ej: Ministerio de Alabanza 2026"
                                    className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-lg font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2">
                                    <Sparkles size={12} /> Propósito / Descripción
                                </label>
                                <textarea 
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="¿Cuál es la meta global de este proyecto?"
                                    rows={3}
                                    className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-sm font-medium outline-none focus:ring-4 focus:ring-blue-500/10 transition-all resize-none"
                                />
                            </div>

                            <div className="space-y-3">
                                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2">
                                    <Palette size={12} /> Identidad Visual
                                </label>
                                <div className="flex gap-3">
                                    {COLORS.map((c) => (
                                        <button
                                            key={c.value}
                                            type="button"
                                            onClick={() => setColor(c.value)}
                                            className={clsx(
                                                "size-10 rounded-xl transition-all relative flex items-center justify-center",
                                                color === c.value ? "scale-110 shadow-lg" : "opacity-40 hover:opacity-100 hover:scale-105"
                                            )}
                                            style={{ backgroundColor: c.value }}
                                        >
                                            {color === c.value && <div className="size-2 rounded-full bg-white shadow-sm" />}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="pt-4 flex gap-3">
                                <button 
                                    type="button" 
                                    onClick={onClose}
                                    className="flex-1 py-4 text-[11px] font-black uppercase tracking-widest text-slate-500 bg-slate-100 dark:bg-white/5 rounded-2xl hover:bg-slate-200 transition-all"
                                >
                                    Cancelar
                                </button>
                                <button 
                                    type="submit"
                                    disabled={loading || !title.trim()}
                                    className="flex-[2] py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[11px] font-black uppercase tracking-[0.2em] rounded-2xl shadow-xl hover:opacity-90 transition-all flex items-center justify-center gap-3 disabled:opacity-50"
                                >
                                    {loading ? <Loader2 className="animate-spin" size={16} /> : "Crear Proyecto Maestro"}
                                </button>
                            </div>
                        </form>
                    </div>
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
}

"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckSquare, Type, AlignLeft, Flag, Loader2 } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import clsx from 'clsx';

interface Props {
    isOpen: boolean;
    defaultStatus?: string;
    onClose: () => void;
    onSubmit: (data: { title: string; description: string; priority: string; status: string }) => Promise<void>;
}

const PRIORITIES = [
    { value: 'urgent', label: 'Urgente', color: 'bg-rose-500', iconColor: 'text-rose-500' },
    { value: 'high', label: 'Alta', color: 'bg-amber-500', iconColor: 'text-amber-500' },
    { value: 'normal', label: 'Normal', color: 'bg-blue-500', iconColor: 'text-blue-500' },
    { value: 'low', label: 'Baja', color: 'bg-slate-500', iconColor: 'text-slate-500' }
];

export default function TaskCreationModal({ isOpen, defaultStatus = 'todo', onClose, onSubmit }: Props) {
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [priority, setPriority] = useState('normal');
    const [loading, setLoading] = useState(false);

    // Reset fields when opened
    useEffect(() => {
        if (isOpen) {
            setTitle('');
            setDescription('');
            setPriority('normal');
            setLoading(false);
        }
    }, [isOpen]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) return;
        setLoading(true);
        try {
            await onSubmit({ title, description, priority, status: defaultStatus });
            onClose();
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <AnimatePresence>
                {isOpen && (
                    <Dialog.Portal forceMount>
                        <Dialog.Overlay asChild>
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[9000] bg-slate-900/40 backdrop-blur-sm" />
                        </Dialog.Overlay>
                        <Dialog.Content asChild>
                            <motion.div 
                                initial={{ opacity: 0, scale: 0.95, y: 20 }} 
                                animate={{ opacity: 1, scale: 1, y: 0 }} 
                                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                                className="fixed left-1/2 top-1/2 z-[9001] w-full max-w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-[2.5rem] bg-white dark:bg-[#1e1f21] shadow-2xl border border-white/10 overflow-hidden"
                            >
                                <div className="p-8 space-y-8">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="size-10 rounded-2xl bg-blue-600/10 flex items-center justify-center text-blue-600 dark:text-blue-400">
                                                <CheckSquare size={20} className="fill-blue-600/20" />
                                            </div>
                                            <div>
                                                <h3 className="text-xl font-black text-slate-900 dark:text-white leading-none">Nueva Tarea</h3>
                                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Definición de Acción</p>
                                            </div>
                                        </div>
                                        <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-full transition-colors">
                                            <X size={20} className="text-slate-400" />
                                        </button>
                                    </div>

                                    <form onSubmit={handleSubmit} className="space-y-6">
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2">
                                                <Type size={12} /> Título de la tarea
                                            </label>
                                            <input 
                                                autoFocus
                                                value={title}
                                                onChange={(e) => setTitle(e.target.value)}
                                                placeholder="Ej: Revisión de Mezcla de Audio"
                                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-lg font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all text-slate-900 dark:text-white"
                                            />
                                        </div>

                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2">
                                                <AlignLeft size={12} /> Descripción (Opcional)
                                            </label>
                                            <textarea 
                                                value={description}
                                                onChange={(e) => setDescription(e.target.value)}
                                                placeholder="Detalles adicionales, links, etc..."
                                                rows={3}
                                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-sm font-medium outline-none focus:ring-4 focus:ring-blue-500/10 transition-all resize-none text-slate-700 dark:text-slate-300"
                                            />
                                        </div>

                                        <div className="space-y-3">
                                            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2">
                                                <Flag size={12} /> Nivel de Prioridad
                                            </label>
                                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                                {PRIORITIES.map((p) => (
                                                    <button
                                                        key={p.value}
                                                        type="button"
                                                        onClick={() => setPriority(p.value)}
                                                        className={clsx(
                                                            "py-2 px-3 rounded-xl flex items-center justify-center gap-2 border text-[11px] font-black uppercase tracking-wider transition-all",
                                                            priority === p.value
                                                                ? `${p.color} border-transparent text-white shadow-md`
                                                                : `bg-transparent border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5`
                                                        )}
                                                    >
                                                        {priority !== p.value && <div className={clsx("size-1.5 rounded-full", p.color)} />}
                                                        {p.label}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="pt-4 flex gap-3">
                                            <button 
                                                type="button" 
                                                onClick={onClose}
                                                className="flex-1 py-4 text-[11px] font-black uppercase tracking-widest text-slate-500 bg-slate-100 dark:bg-white/5 rounded-2xl hover:bg-slate-200 dark:hover:bg-white/10 transition-all"
                                            >
                                                Cancelar
                                            </button>
                                            <button 
                                                type="submit"
                                                disabled={loading || !title.trim()}
                                                className="flex-[2] py-4 bg-blue-600 text-white text-[11px] font-black uppercase tracking-[0.2em] rounded-2xl shadow-xl hover:bg-blue-700 transition-all flex items-center justify-center gap-3 disabled:opacity-50"
                                            >
                                                {loading ? <Loader2 className="animate-spin" size={16} /> : "Crear Tarea"}
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            </motion.div>
                        </Dialog.Content>
                    </Dialog.Portal>
                )}
            </AnimatePresence>
        </Dialog.Root>
    );
}

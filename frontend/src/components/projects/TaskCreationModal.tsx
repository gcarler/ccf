"use client";

import React, { useState, useEffect } from 'react';
import { CheckSquare, Type, AlignLeft, Flag, Loader2, User } from 'lucide-react';
import UserSelect from '@/components/ui/UserSelect';
import clsx from 'clsx';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

interface Props {
    isOpen: boolean;
    defaultStatus?: string;
    onClose: () => void;
    onSubmit: (data: { title: string; description: string; priority: string; status: string; assignee_id?: number | null }) => Promise<void>;
}

const PRIORITIES = [
    { value: 'urgent', label: 'Urgente', color: 'bg-rose-500', iconColor: 'text-rose-500' },
    { value: 'high', label: 'Alta', color: 'bg-amber-500', iconColor: 'text-amber-500' },
    { value: 'medium', label: 'Normal', color: 'bg-blue-500', iconColor: 'text-blue-500' },
    { value: 'low', label: 'Baja', color: 'bg-slate-500', iconColor: 'text-slate-500' }
];

export default function TaskCreationModal({ isOpen, defaultStatus = 'todo', onClose, onSubmit }: Props) {
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [priority, setPriority] = useState('medium');
    const [assigneeId, setAssigneeId] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);

    // Reset fields when opened
    useEffect(() => {
        if (isOpen) {
            setTitle('');
            setDescription('');
            setPriority('normal');
            setAssigneeId(null);
            setLoading(false);
        }
    }, [isOpen]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) return;
        setLoading(true);
        try {
            await onSubmit({ title, description, priority, status: defaultStatus, assignee_id: assigneeId });
            onClose();
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <WorkspaceDrawer
            isOpen={isOpen}
            onClose={onClose}
            title="Nueva Tarea"
            subtitle="Definición de Acción"
            actions={
                <>
                    <button type="button" onClick={onClose} className="px-3 py-1.5 text-[11px] font-medium text-slate-500 hover:text-slate-700 transition-colors">
                        Cancelar
                    </button>
                    <button type="button" onClick={handleSubmit} disabled={loading || !title.trim()} className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-50">
                        {loading ? <Loader2 className="animate-spin" size={12} /> : <CheckSquare size={12} />}
                        {loading ? 'Creando...' : 'Crear Tarea'}
                    </button>
                </>
            }
        >
            <form onSubmit={handleSubmit} className="mt-3 space-y-4">
                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-2">
                        <Type size={12} /> Título de la tarea
                    </label>
                    <input
                        autoFocus
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        placeholder="Ej: Revisión de Mezcla de Audio"
                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500/20 transition-all text-slate-900 dark:text-white"
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-2">
                        <AlignLeft size={12} /> Descripción (Opcional)
                    </label>
                    <textarea
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Detalles adicionales, links, etc..."
                        rows={5}
                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500/20 transition-all resize-none text-slate-700 dark:text-slate-300"
                    />
                </div>

                <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-2">
                        <Flag size={12} /> Nivel de Prioridad
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                        {PRIORITIES.map((p) => (
                            <button
                                key={p.value}
                                type="button"
                                onClick={() => setPriority(p.value)}
                                className={clsx(
                                    "py-2 px-3 rounded-md flex items-center justify-center gap-2 border text-[11px] font-bold uppercase tracking-wide transition-all",
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

                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-2">
                        <User size={12} /> Asignar a
                    </label>
                    <UserSelect
                        value={assigneeId}
                        onChange={setAssigneeId}
                        placeholder="Seleccionar responsable"
                    />
                </div>
            </form>
        </WorkspaceDrawer>
    );
}

"use client";

import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
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

interface FormValues {
    title: string;
    description: string;
    priority: string;
    assignee_id: number | null;
}

const PRIORITIES = [
    { value: 'urgent', label: 'Urgente', color: 'bg-rose-500', iconColor: 'text-rose-500' },
    { value: 'high', label: 'Alta', color: 'bg-amber-500', iconColor: 'text-amber-500' },
    { value: 'medium', label: 'Normal', color: 'bg-[hsl(var(--primary))]', iconColor: 'text-[hsl(var(--primary))]' },
    { value: 'low', label: 'Baja', color: 'bg-slate-500', iconColor: 'text-slate-500' }
];

export default function TaskCreationDrawer({ isOpen, defaultStatus = 'todo', onClose, onSubmit }: Props) {
    const { register, handleSubmit, reset, setValue, watch, formState: { isSubmitting } } = useForm<FormValues>({
        defaultValues: {
            title: '',
            description: '',
            priority: 'medium',
            assignee_id: null,
        }
    });

    const priority = watch('priority');
    const assigneeId = watch('assignee_id');

    useEffect(() => {
        if (isOpen) {
            reset({ title: '', description: '', priority: 'medium', assignee_id: null });
        }
    }, [isOpen, reset]);

    const onFormSubmit = async (data: FormValues) => {
        await onSubmit({ ...data, status: defaultStatus });
        onClose();
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
                    <button
                        type="button"
                        onClick={handleSubmit(onFormSubmit)}
                        disabled={isSubmitting}
                        className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-50"
                    >
                        {isSubmitting ? <Loader2 className="animate-spin" size={12} /> : <CheckSquare size={12} />}
                        {isSubmitting ? 'Creando...' : 'Crear Tarea'}
                    </button>
                </>
            }
        >
            <form onSubmit={handleSubmit(onFormSubmit)} className="mt-3 space-y-4">
                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-2">
                        <Type size={12} /> Título de la tarea
                    </label>
                    <input
                        autoFocus
                        {...register('title', { required: true })}
                        placeholder="Ej: Revisión de Mezcla de Audio"
                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500/20 transition-all text-slate-900 dark:text-white"
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-2">
                        <AlignLeft size={12} /> Descripción (Opcional)
                    </label>
                    <textarea
                        {...register('description')}
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
                                onClick={() => setValue('priority', p.value)}
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
                        onChange={(v) => setValue('assignee_id', v)}
                        placeholder="Seleccionar responsable"
                    />
                </div>
            </form>
        </WorkspaceDrawer>
    );
}

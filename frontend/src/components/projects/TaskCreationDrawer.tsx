"use client";

import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { CheckSquare, Type, AlignLeft, Flag, Loader2, User } from 'lucide-react';
import PersonaSelect from '@/components/ui/PersonaSelect';
import clsx from 'clsx';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { PRIORITY_LABELS } from '@/lib/projects/constants';

interface Props {
    isOpen: boolean;
    defaultStatus?: string;
    onClose: () => void;
    onSubmit: (data: { title: string; description: string; priority: string; status: string; assignee_id?: string | null }) => Promise<boolean> | Promise<void> | boolean | void;
}

interface FormValues {
    title: string;
    description: string;
    priority: string;
    assignee_id: string | null;
}

const PRIORITIES = [
    { value: 'urgent', label: PRIORITY_LABELS.urgent, color: 'bg-[hsl(var(--danger))]', iconColor: 'text-[hsl(var(--danger))]' },
    { value: 'high', label: PRIORITY_LABELS.high, color: 'bg-[hsl(var(--warning))]', iconColor: 'text-[hsl(var(--warning))]' },
    { value: 'medium', label: PRIORITY_LABELS.medium, color: 'bg-[hsl(var(--primary))]', iconColor: 'text-[hsl(var(--primary))]' },
    { value: 'low', label: PRIORITY_LABELS.low, color: 'bg-[hsl(var(--surface-2))]', iconColor: 'text-[hsl(var(--text-secondary))]' }
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
        const result = await onSubmit({ ...data, status: defaultStatus });
        if (result === true || result === undefined) {
            onClose();
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
                    <button type="button" onClick={onClose} className="px-3 py-1.5 text-[11px] font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit(onFormSubmit)}
                        disabled={isSubmitting}
                        className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-50"
                    >
                        {isSubmitting ? <Loader2 className="animate-spin" size={12} /> : <CheckSquare size={12} />}
                        {isSubmitting ? 'Creando...' : 'Crear Tarea'}
                    </button>
                </>
            }
        >
            <form onSubmit={handleSubmit(onFormSubmit)} className="mt-3 space-y-4">
                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <Type size={12} /> Título de la tarea
                    </label>
                    <input
                        autoFocus
                        {...register('title', { required: true })}
                        placeholder="Ej: Revisión de Mezcla de Audio"
                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all text-[hsl(var(--text-primary))] dark:text-white"
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <AlignLeft size={12} /> Descripción (Opcional)
                    </label>
                    <textarea
                        {...register('description')}
                        placeholder="Detalles adicionales, links, etc..."
                        rows={5}
                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all resize-none text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
                    />
                </div>

                <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
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
                                        : `bg-transparent border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5`
                                )}
                            >
                                {priority !== p.value && <div className={clsx("size-1.5 rounded-full", p.color)} />}
                                {p.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <User size={12} /> Asignar a
                    </label>
                    <PersonaSelect
                        value={assigneeId}
                        onChange={(v) => setValue('assignee_id', v)}
                        placeholder="Seleccionar responsable"
                    />
                </div>
            </form>
        </WorkspaceDrawer>
    );
}

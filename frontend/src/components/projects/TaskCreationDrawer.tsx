"use client";

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { CheckSquare, Type, AlignLeft, Flag, Loader2, User, Layers } from 'lucide-react';
import PersonaSelect from '@/components/ui/PersonaSelect';
import clsx from 'clsx';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { PRIORITY_LABELS, TASK_TITLE_MAX_LENGTH } from '@/lib/projects/constants';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectComponentsBreakdown } from '@/types/projects';

interface Props {
    isOpen: boolean;
    projectId?: string;
    defaultStatus?: string;
    defaultComponentId?: string | null;
    onClose: () => void;
    onSubmit: (data: {
        title: string;
        description: string;
        priority: string;
        status: string;
        assignee_id?: string | null;
        node?: string | null;
        component_id?: string | null;
    }) => Promise<boolean> | Promise<void> | boolean | void;
}

interface FormValues {
    title: string;
    description: string;
    priority: string;
    assignee_id: string | null;
    node: string | null;
    component_id: string | null;
}

const PRIORITIES = [
    { value: 'urgent', label: PRIORITY_LABELS.urgent, color: 'bg-[hsl(var(--destructive))]', iconColor: 'text-[hsl(var(--destructive))]' },
    { value: 'high', label: PRIORITY_LABELS.high, color: 'bg-[hsl(var(--warning))]', iconColor: 'text-[hsl(var(--warning))]' },
    { value: 'medium', label: PRIORITY_LABELS.medium, color: 'bg-[hsl(var(--primary))]', iconColor: 'text-[hsl(var(--primary))]' },
    { value: 'low', label: PRIORITY_LABELS.low, color: 'bg-[hsl(var(--surface-2))]', iconColor: 'text-[hsl(var(--text-secondary))]' }
];

export default function TaskCreationDrawer({
    isOpen,
    projectId,
    defaultStatus = 'todo',
    defaultComponentId,
    onClose,
    onSubmit,
}: Props) {
    const { token } = useAuth();
    const [components, setComponents] = useState<Array<{ id: string; code: string; name: string }>>([]);

    const { register, handleSubmit, reset, setValue, watch, formState: { isSubmitting } } = useForm<FormValues>({
        defaultValues: {
            title: '',
            description: '',
            priority: 'medium',
            assignee_id: null,
            node: null,
            component_id: defaultComponentId ?? '',
        }
    });

    const priority = watch('priority');
    const assigneeId = watch('assignee_id');

    useEffect(() => {
        if (!isOpen || !projectId || !token) {
            setComponents([]);
            return;
        }
        let isCurrent = true;
        Promise.resolve(apiFetch<ProjectComponentsBreakdown>(`/projects/${projectId}/components-breakdown`, { token }))
            .then((res) => {
                if (isCurrent && res?.components) {
                    setComponents(res.components.map((c) => ({ id: c.id, code: c.code, name: c.name })));
                }
            })
            .catch(() => {});
        return () => { isCurrent = false; };
    }, [isOpen, projectId, token]);

    useEffect(() => {
        if (isOpen) {
            reset({
                title: '',
                description: '',
                priority: 'medium',
                assignee_id: null,
                node: null,
                component_id: defaultComponentId ?? '',
            });
        }
    }, [isOpen, defaultComponentId, reset]);

    const onFormSubmit = async (data: FormValues) => {
        const result = await onSubmit({
            ...data,
            component_id: data.component_id ? data.component_id : null,
            status: defaultStatus,
        });
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
                    <button type="button" onClick={onClose} className="px-3 py-1.5 text-xs font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit(onFormSubmit)}
                        disabled={isSubmitting}
                        className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-xs font-bold uppercase tracking-wide shadow-md shadow-[hsl(var(--primary))]/20 hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all disabled:opacity-50"
                    >
                        {isSubmitting ? <Loader2 className="animate-spin" size={12} /> : <CheckSquare size={12} />}
                        {isSubmitting ? 'Creando...' : 'Crear Tarea'}
                    </button>
                </>
            }
        >
            <form onSubmit={handleSubmit(onFormSubmit)} className="mt-3 space-y-4">
                <div className="space-y-1.5">
                    <label htmlFor="task-title" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <Type size={12} /> Título de la tarea
                    </label>
                    <input
                        id="task-title"
                        autoFocus
                        {...register('title', { required: true, maxLength: TASK_TITLE_MAX_LENGTH })}
                        maxLength={TASK_TITLE_MAX_LENGTH}
                        placeholder="Ej: Revisión de Mezcla de Audio"
                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all text-[hsl(var(--foreground))]"
                    />
                </div>

                <div className="space-y-1.5">
                    <label htmlFor="task-description" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <AlignLeft size={12} /> Descripción (Opcional)
                    </label>
                    <textarea
                        id="task-description"
                        {...register('description')}
                        placeholder="Detalles adicionales, links, etc..."
                        rows={5}
                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all resize-none text-[hsl(var(--foreground))]"
                    />
                </div>

                <div role="group" aria-labelledby="task-priority-label" className="space-y-2">
                    <span id="task-priority-label" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <Flag size={12} /> Nivel de Prioridad
                    </span>
                    <div className="grid grid-cols-2 gap-2">
                        {PRIORITIES.map((p) => (
                            <button
                                key={p.value}
                                type="button"
                                onClick={() => setValue('priority', p.value)}
                                aria-pressed={priority === p.value}
                                className={clsx(
                                    "py-2 px-3 rounded-md flex items-center justify-center gap-2 border text-xs font-bold uppercase tracking-wide transition-all",
                                    priority === p.value
                                        ? `${p.color} border-transparent text-[hsl(var(--primary-foreground))] shadow-sm`
                                        : `bg-transparent border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]`
                                )}
                            >
                                {priority !== p.value && <div className={clsx("size-1.5 rounded-full", p.color)} />}
                                {p.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div role="group" aria-labelledby="task-assignee-label" className="space-y-1.5">
                    <span id="task-assignee-label" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <User size={12} /> Asignar a
                    </span>
                    <PersonaSelect
                        value={assigneeId}
                        onChange={(v) => setValue('assignee_id', v)}
                        placeholder="Seleccionar responsable"
                    />
                </div>

                <div className="space-y-1.5">
                    <label htmlFor="task-component" className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] flex items-center gap-2">
                        <Layers size={12} /> Componente (EDT)
                    </label>
                    <select
                        id="task-component"
                        aria-label="Componente (EDT)"
                        {...register('component_id')}
                        className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all text-[hsl(var(--foreground))]"
                    >
                        <option value="">Sin componente (General)</option>
                        {components.map((c) => (
                            <option key={c.id} value={c.id}>
                                {c.code} · {c.name}
                            </option>
                        ))}
                    </select>
                </div>
            </form>
        </WorkspaceDrawer>
    );
}

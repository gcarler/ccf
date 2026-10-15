"use client";

import { useState, useEffect } from 'react';
import PersonaSelect from '@/components/ui/PersonaSelect';
import MetaRow from '@/components/ui/MetaRow';
import TaskLabelManager from './TaskLabelManager';
import { InlineDatePicker } from '@/components/ui/inline-editors/InlineDatePicker';
import type { ProjectTaskRecord } from '@/types/projects';
import { CalendarDays, Flag, Tag, UserRound, Layers, Plus, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

function formatCalendarDate(value: string): string {
    const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
        const [, year, month, day] = match;
        const d = new Date(Number(year), Number(month) - 1, Number(day));
        return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
    }
    const d = new Date(value);
    return isNaN(d.getTime()) ? value : d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function TaskMetaFields({
    task,
    labels,
    components,
    onLabelsChange,
    onAssigneeChange,
    onDueDateChange,
    onPriorityCycle,
    onNodeCycle: _onNodeCycle,
    onComponentChange,
    onComponentCreated,
    priority,
    token,
}: {
    task: ProjectTaskRecord;
    labels: string[];
    components?: { id: string; code: string; name: string }[];
    onLabelsChange: (labels: string[]) => void;
    onAssigneeChange: (id: string | null) => void;
    onDueDateChange?: (date: string | null) => void;
    onPriorityCycle: () => void;
    onNodeCycle?: () => void;
    onComponentChange?: (componentId: string | null) => void;
    onComponentCreated?: (component: { id: string; code: string; name: string }) => void;
    priority: { color: string; dot: string; label: string };
    token: string | null;
}) {
    const [localComponents, setLocalComponents] = useState<Array<{ id: string; code: string; name: string }>>(components ?? []);
    useEffect(() => {
        if (components) {
            setLocalComponents(components);
        }
    }, [components]);

    const [showNewComponentForm, setShowNewComponentForm] = useState(false);
    const [newComponentCode, setNewComponentCode] = useState('');
    const [newComponentName, setNewComponentName] = useState('');
    const [isCreatingComponent, setIsCreatingComponent] = useState(false);
    const [componentError, setComponentError] = useState<string | null>(null);

    const projectId = task.project_id;

    const handleOpenNewComponent = () => {
        setNewComponentCode(`EDT-${localComponents.length + 1}.0`);
        setNewComponentName('');
        setComponentError(null);
        setShowNewComponentForm(true);
    };

    const handleCreateComponent = async (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!projectId || !token) return;
        const code = newComponentCode.trim();
        const name = newComponentName.trim();
        if (!code || !name) {
            setComponentError('El código y el nombre son obligatorios');
            return;
        }
        setIsCreatingComponent(true);
        setComponentError(null);
        try {
            const created = await apiFetch<{ id: string; code: string; name: string }>(
                `/projects/${projectId}/components`,
                {
                    method: 'POST',
                    token,
                    body: { code, name },
                }
            );
            if (created?.id) {
                const newComp = { id: created.id, code: created.code, name: created.name };
                setLocalComponents((prev) => [...prev, newComp]);
                onComponentCreated?.(newComp);
                onComponentChange?.(created.id);
                setShowNewComponentForm(false);
                setNewComponentCode('');
                setNewComponentName('');
                toast.success('Componente EDT creado correctamente');
            }
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Error al crear componente';
            setComponentError(message);
            toast.error('No se pudo crear el componente');
        } finally {
            setIsCreatingComponent(false);
        }
    };

    return (
        <section className="px-4 py-3 border-b border-[hsl(var(--border))] space-y-2">
            <MetaRow icon={<UserRound size={13} className="text-[hsl(var(--muted-foreground))]" />} label="Persona asignada">
                <PersonaSelect
                    value={task.assignee_id ?? null}
                    onChange={onAssigneeChange}
                    placeholder="Sin asignar"
                    className="min-w-[180px]"
                />
            </MetaRow>

            <MetaRow icon={<CalendarDays size={13} className="text-[hsl(var(--muted-foreground))]" />} label="Fecha límite">
                {onDueDateChange ? (
                    <InlineDatePicker
                        value={task.due_date}
                        onChange={onDueDateChange}
                    />
                ) : (
                    <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium text-[hsl(var(--muted-foreground))]">
                        {task.due_date
                            ? formatCalendarDate(task.due_date)
                            : 'Sin fecha límite'
                        }
                    </span>
                )}
            </MetaRow>

            <MetaRow icon={<Flag size={13} className="text-[hsl(var(--muted-foreground))]" />} label="Prioridad">
                <button
                    onClick={onPriorityCycle}
                    title="Click para cambiar prioridad"
                    className={clsx('flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-sm font-bold border border-transparent hover:border-[hsl(var(--border))] transition-all cursor-pointer', priority.color)}>
                    <span className={clsx('size-2 rounded-full', priority.dot)} />
                    {priority.label}
                </button>
            </MetaRow>

            <MetaRow icon={<Tag size={13} className="text-[hsl(var(--muted-foreground))]" />} label="Etiquetas">
                <TaskLabelManager task={task} labels={labels} onLabelsChange={onLabelsChange} token={token} />
            </MetaRow>

            <MetaRow icon={<Layers size={13} className="text-[hsl(var(--muted-foreground))]" />} label="Componente (EDT)">
                <div className="flex items-center gap-2 flex-wrap">
                    {onComponentChange ? (
                        <select
                            aria-label="Componente (EDT)"
                            value={task.component_id ?? ''}
                            onChange={(e) => onComponentChange(e.target.value ? e.target.value : null)}
                            className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-2.5 py-1 text-xs font-medium text-[hsl(var(--foreground))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                        >
                            <option value="">Sin componente (General)</option>
                            {localComponents.map((c) => (
                                <option key={c.id} value={c.id}>
                                    {c.code} · {c.name}
                                </option>
                            ))}
                        </select>
                    ) : (
                        <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium text-[hsl(var(--muted-foreground))]">
                            {task.component_id
                                ? localComponents.find((c) => c.id === task.component_id)?.name ?? 'Asignado'
                                : 'Sin componente (General)'}
                        </span>
                    )}
                    {onComponentChange && projectId && (
                        <button
                            type="button"
                            onClick={() => {
                                if (showNewComponentForm) setShowNewComponentForm(false);
                                else handleOpenNewComponent();
                            }}
                            className="text-2xs font-bold text-[hsl(var(--primary))] hover:underline inline-flex items-center gap-1 px-1 py-0.5"
                        >
                            <Plus size={10} />
                            {showNewComponentForm ? 'Cancelar nuevo' : '+ Nuevo componente'}
                        </button>
                    )}
                </div>
            </MetaRow>

            {showNewComponentForm && (
                <div data-testid="meta-inline-edt-form" className="p-2.5 rounded-md border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--surface-1))] space-y-2 ml-4">
                    <p className="text-2xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-wide flex items-center gap-1">
                        <Layers size={11} className="text-[hsl(var(--primary))]" />
                        Crear Componente EDT
                    </p>
                    {componentError && (
                        <p className="text-2xs text-[hsl(var(--destructive))] font-medium">{componentError}</p>
                    )}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <div>
                            <label htmlFor="meta-edt-code" className="text-3xs font-bold uppercase text-[hsl(var(--text-secondary))] block mb-1">
                                Código
                            </label>
                            <input
                                id="meta-edt-code"
                                aria-label="Código del componente EDT"
                                value={newComponentCode}
                                onChange={(e) => setNewComponentCode(e.target.value)}
                                placeholder="Ej: EDT-1.0"
                                className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                            />
                        </div>
                        <div className="sm:col-span-2">
                            <label htmlFor="meta-edt-name" className="text-3xs font-bold uppercase text-[hsl(var(--text-secondary))] block mb-1">
                                Nombre del Componente
                            </label>
                            <input
                                id="meta-edt-name"
                                aria-label="Nombre del componente EDT"
                                value={newComponentName}
                                onChange={(e) => setNewComponentName(e.target.value)}
                                placeholder="Ej: Infraestructura y Redes"
                                className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                            />
                        </div>
                    </div>
                    <div className="flex items-center justify-end gap-2 pt-1">
                        <button
                            type="button"
                            onClick={() => setShowNewComponentForm(false)}
                            className="px-2 py-1 text-2xs font-semibold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                        >
                            Cancelar
                        </button>
                        <button
                            type="button"
                            onClick={handleCreateComponent}
                            disabled={isCreatingComponent}
                            className="flex items-center gap-1 px-2.5 py-1 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded text-2xs font-bold shadow-xs hover:opacity-90 disabled:opacity-50"
                        >
                            {isCreatingComponent ? <Loader2 size={10} className="animate-spin" /> : <Plus size={10} />}
                            Guardar
                        </button>
                    </div>
                </div>
            )}
        </section>
    );
}

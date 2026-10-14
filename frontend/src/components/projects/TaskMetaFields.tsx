"use client";

import PersonaSelect from '@/components/ui/PersonaSelect';
import MetaRow from '@/components/ui/MetaRow';
import TaskLabelManager from './TaskLabelManager';
import { InlineDatePicker } from '@/components/ui/inline-editors/InlineDatePicker';
import type { ProjectTaskRecord } from '@/types/projects';
import { CalendarDays, Flag, Tag, UserRound, Layers } from 'lucide-react';
import clsx from 'clsx';

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
    priority: { color: string; dot: string; label: string };
    token: string | null;
}) {

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
                {onComponentChange ? (
                    <select
                        aria-label="Componente (EDT)"
                        value={task.component_id ?? ''}
                        onChange={(e) => onComponentChange(e.target.value ? e.target.value : null)}
                        className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-2.5 py-1 text-xs font-medium text-[hsl(var(--foreground))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                    >
                        <option value="">Sin componente (General)</option>
                        {components?.map((c) => (
                            <option key={c.id} value={c.id}>
                                {c.code} · {c.name}
                            </option>
                        ))}
                    </select>
                ) : (
                    <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium text-[hsl(var(--muted-foreground))]">
                        {task.component_id
                            ? components?.find((c) => c.id === task.component_id)?.name ?? 'Asignado'
                            : 'Sin componente (General)'}
                    </span>
                )}
            </MetaRow>
        </section>
    );
}

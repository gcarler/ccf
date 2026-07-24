"use client";

import PersonaSelect from '@/components/ui/PersonaSelect';
import MetaRow from '@/components/ui/MetaRow';
import TaskLabelManager from './TaskLabelManager';
import type { ProjectTaskRecord } from '@/types/projects';
import { CalendarDays, Flag, Tag, UserRound } from 'lucide-react';
import clsx from 'clsx';

export default function TaskMetaFields({
    task,
    labels,
    onLabelsChange,
    onAssigneeChange,
    onPriorityCycle,
    priority,
    token,
}: {
    task: ProjectTaskRecord;
    labels: string[];
    onLabelsChange: (labels: string[]) => void;
    onAssigneeChange: (id: string | null) => void;
    onPriorityCycle: () => void;
    priority: { color: string; dot: string; label: string };
    token: string | null;
}) {
    return (
        <section className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.05] space-y-2">
            <MetaRow icon={<UserRound size={13} className="text-[hsl(var(--text-secondary))]" />} label="Persona asignada">
                <PersonaSelect
                    value={task.assignee_id ?? null}
                    onChange={onAssigneeChange}
                    placeholder="Sin asignar"
                    className="min-w-[180px]"
                />
            </MetaRow>

            <MetaRow icon={<CalendarDays size={13} className="text-[hsl(var(--text-secondary))]" />} label="Fecha límite">
                <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[12px] font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.04] border border-transparent hover:border-[hsl(var(--border))] dark:hover:border-white/[0.08] transition-all">
                    {task.due_date
                        ? new Date(task.due_date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
                        : 'Sin fecha límite'
                    }
                </button>
            </MetaRow>

            <MetaRow icon={<Flag size={13} className="text-[hsl(var(--text-secondary))]" />} label="Prioridad">
                <button
                    onClick={onPriorityCycle}
                    title="Click para cambiar prioridad"
                    className={clsx('flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12px] font-bold border border-transparent hover:border-[hsl(var(--border))] dark:hover:border-white/[0.08] transition-all cursor-pointer', priority.color)}>
                    <span className={clsx('size-2 rounded-full', priority.dot)} />
                    {priority.label}
                </button>
            </MetaRow>

            <MetaRow icon={<Tag size={13} className="text-[hsl(var(--text-secondary))]" />} label="Etiquetas">
                <TaskLabelManager task={task} labels={labels} onLabelsChange={onLabelsChange} token={token} />
            </MetaRow>
        </section>
    );
}

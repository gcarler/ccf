'use client';

import { useMemo } from 'react';
import clsx from 'clsx';
import UniversalCalendarView, { type CalendarEvent } from '@/components/ui/UniversalCalendarView';
import type { ProjectRecord } from '@/types/projects';

interface ProjectsCalendarViewProps {
    projects: ProjectRecord[];
    onEventClick?: (event: CalendarEvent) => void;
}

export default function ProjectsCalendarView({ projects, onEventClick }: ProjectsCalendarViewProps) {
    const events = useMemo(
        () =>
            projects.flatMap((project) => {
                const scheduledDate = project.target_date || project.start_date;
                if (!scheduledDate) return [];
                const milestoneLabel = project.target_date ? 'Entrega' : 'Inicio';
                return [{
                    id: project.id,
                    title: `${project.title} · ${milestoneLabel}`,
                    date: scheduledDate.slice(0, 10),
                    color:
                        project.status === 'completed'
                            ? ('emerald' as const)
                            : project.status === 'on_hold'
                            ? ('amber' as const)
                            : ('blue' as const),
                    location: project.description || undefined,
                }];
            }),
        [projects]
    );

    const noBaselineCount = projects.length - events.length;
    const onHoldCount = projects.filter((project) => project.status === 'on_hold').length;

    return (
        <div className="space-y-2 pb-4">
            {/* Cintillo de Línea Base de Cronograma Maestro PMI §6.5 */}
            <div
                data-testid="projects-calendar-pmi-header"
                aria-label="Línea base de cronograma maestro PMI"
                className="flex flex-wrap items-center gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-1.5 text-2xs font-semibold text-[hsl(var(--text-secondary))]"
            >
                <span>Hitos en Cronograma: {events.length}</span>
                <span
                    className={clsx(
                        'rounded-full border px-2 py-0.5',
                        noBaselineCount > 0
                            ? 'bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.4)]'
                            : 'bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))] border-[hsl(var(--success)/0.4)]'
                    )}
                >
                    Sin Linea Base: {noBaselineCount}
                </span>
                <span
                    className={clsx(
                        'rounded-full border px-2 py-0.5',
                        onHoldCount > 0
                            ? 'bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.4)]'
                            : 'bg-[hsl(var(--border))] text-[hsl(var(--text-secondary))]'
                    )}
                >
                    En Pausa CCB: {onHoldCount}
                </span>
            </div>
            <div className="h-[720px]">
                <UniversalCalendarView
                    events={events}
                    title="Calendario de proyectos"
                    onEventClick={onEventClick}
                    todayButtonClassName="text-[hsl(var(--foreground))] hover:text-[hsl(var(--primary))]"
                />
            </div>
        </div>
    );
}

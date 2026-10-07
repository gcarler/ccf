'use client';

import { useMemo } from 'react';
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

    return (
        <div className="h-[720px] pb-4">
            <UniversalCalendarView
                events={events}
                title="Calendario de proyectos"
                onEventClick={onEventClick}
                todayButtonClassName="text-[hsl(var(--foreground))] hover:text-[hsl(var(--primary))]"
            />
        </div>
    );
}

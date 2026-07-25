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
            projects.map((project) => ({
                id: project.id,
                title: project.title,
                date: (project.updated_at || project.created_at || new Date().toISOString()).slice(0, 10),
                color:
                    project.status === 'completed'
                        ? ('emerald' as const)
                        : project.status === 'on_hold'
                        ? ('amber' as const)
                        : ('blue' as const),
                location: project.description || undefined,
            })),
        [projects]
    );

    return (
        <div className="h-[720px] pb-4">
            <UniversalCalendarView
                events={events}
                title="Calendario de proyectos"
                onEventClick={onEventClick}
            />
        </div>
    );
}

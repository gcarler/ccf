'use client';

import { useMemo } from 'react';
import UniversalGanttView, { type GanttItem } from '@/components/ui/UniversalGanttView';
import type { ProjectRecord } from '@/types/projects';

interface ProjectsGanttViewProps {
    projects: ProjectRecord[];
    onItemClick?: (item: GanttItem) => void;
}

export default function ProjectsGanttView({ projects, onItemClick }: ProjectsGanttViewProps) {
    const items = useMemo(
        () =>
            projects.map((project) => {
                // Schedule dates are the source of truth. For projects created
                // before those fields existed, use creation time as a stable
                // estimated start; edits must never move the timeline.
                const start = project.start_date || project.target_date || project.created_at;
                const end = project.target_date || project.start_date || start;
                const tasks = Array.isArray(project.tasks) ? project.tasks : [];
                const done = tasks.filter((task) =>
                    ['completed'].includes((task.status || '').toLowerCase())
                ).length;
                return {
                    id: project.id,
                    title: project.title,
                    subtitle: project.status || 'active',
                    start_date: start.slice(0, 10),
                    end_date: end.slice(0, 10),
                    color: project.status === 'completed' ? ('emerald' as const) : ('blue' as const),
                    progress: project.progress_percent ?? (tasks.length ? Math.round((done / tasks.length) * 100) : 0),
                };
            }),
        [projects]
    );

    return (
        <div className="h-[720px] pb-4">
            <UniversalGanttView
                items={items}
                moduleName="Portfolio"
                onItemClick={onItemClick}
            />
        </div>
    );
}

'use client';

import { useMemo } from 'react';
import ProjectCard from '@/components/projects/ProjectCard';
import type { ProjectRecord } from '@/types/projects';
import type { BaseProjectViewProps } from './types';

interface ProjectsBoardViewProps extends BaseProjectViewProps {}

export default function ProjectsBoardView({ projects, onUpdate, onDelete }: ProjectsBoardViewProps) {
    const groupedByStatus = useMemo(() => {
        const statuses = ['active', 'planning', 'on_hold', 'completed', 'archived'];
        return statuses
            .map((status) => ({
                status,
                projects: projects.filter((project) => (project.status || 'active') === status),
            }))
            .filter(
                (column) =>
                    column.projects.length > 0 ||
                    ['active', 'planning', 'completed'].includes(column.status)
            );
    }, [projects]);

    return (
        <div className="flex gap-4 overflow-x-auto pb-4">
            {groupedByStatus.map((column) => (
                <section
                    key={column.status}
                    className="w-80 shrink-0 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 dark:border-white/10 dark:bg-[hsl(var(--surface-2))]"
                >
                    <div className="mb-3 flex items-center justify-between px-1">
                        <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            {column.status}
                        </p>
                        <span className="font-semibold text-[hsl(var(--text-secondary))]">
                            {column.projects.length}
                        </span>
                    </div>
                    <div className="space-y-2">
                        {column.projects.map((project, index) => (
                            <ProjectCard
                                key={project.id}
                                project={project}
                                index={index}
                                onUpdate={onUpdate}
                                onDelete={onDelete}
                            />
                        ))}
                        {column.projects.length === 0 && (
                            <div data-testid="empty-column" className="rounded-md border border-dashed border-[hsl(var(--border))] py-8 text-center text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:border-white/10">
                                Vacío
                            </div>
                        )}
                    </div>
                </section>
            ))}
        </div>
    );
}

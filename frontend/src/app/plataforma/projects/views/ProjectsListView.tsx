'use client';

import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import type { ProjectRecord } from '@/types/projects';
import type { BaseProjectViewProps } from './types';

interface ProjectsListViewProps extends BaseProjectViewProps {}

export default function ProjectsListView({ projects, onUpdate }: ProjectsListViewProps) {
    return (
        <div className="space-y-2 pb-4 scroll-mt-24">
            {projects.map((project) => (
                <div
                    key={project.id}
                    className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 text-left transition-all duration-300 hover:border-[hsl(var(--primary))]/60 dark:border-white/10 dark:bg-[hsl(var(--surface-2))]"
                >
                    <div className="flex items-center justify-between gap-4">
                        <div className="min-w-0 flex-1">
                            <InlineTextInput
                                value={project.title}
                                onChange={(v) => onUpdate(project.id, { title: v })}
                                placeholder="Título del proyecto"
                                className="truncate text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white"
                                inputClassName="text-sm"
                            />
                            <p className="truncate text-xs font-medium text-[hsl(var(--text-secondary))]">
                                {project.description || 'Sin descripcion'}
                            </p>
                        </div>
                        <InlineProjectStatusPicker
                            value={(project.status || 'active') as ProjectRecord['status']}
                            onChange={(v) => onUpdate(project.id, { status: v })}
                            size="sm"
                        />
                    </div>
                </div>
            ))}
        </div>
    );
}

'use client';

import { useRouter } from 'next/navigation';
import { ArrowUpRight } from 'lucide-react';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import type { ProjectRecord } from '@/types/projects';
import type { BaseProjectViewProps } from './types';

interface ProjectsListViewProps extends BaseProjectViewProps {}

export default function ProjectsListView({ projects, onUpdate }: ProjectsListViewProps) {
    const router = useRouter();

    const goToDetail = (projectId: string) => {
        router.push(`/plataforma/projects/${projectId}?view=list`);
    };

    return (
        <div className="space-y-2 pb-4 scroll-mt-24">
            {projects.map((project) => (
                <div
                    key={project.id}
                    onClick={() => goToDetail(project.id)}
                    className="group w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 text-left transition-all duration-300 hover:border-[hsl(var(--primary))]/60 dark:border-white/10 dark:bg-[hsl(var(--surface-2))] cursor-pointer"
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
                        <div className="flex items-center gap-2 shrink-0">
                            <InlineProjectStatusPicker
                                value={(project.status || 'active') as ProjectRecord['status']}
                                onChange={(v) => onUpdate(project.id, { status: v })}
                                size="sm"
                            />
                            <ArrowUpRight
                                size={16}
                                className="text-[hsl(var(--text-secondary))] opacity-0 group-hover:opacity-100 transition-opacity"
                            />
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}

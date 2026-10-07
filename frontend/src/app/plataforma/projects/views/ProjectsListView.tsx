'use client';

import { useRouter } from 'next/navigation';
import { ArrowUpRight } from 'lucide-react';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { PROJECT_TITLE_MAX_LENGTH } from '@/lib/projects/constants';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import type { ProjectRecord } from '@/types/projects';
import type { BaseProjectViewProps } from './types';

interface ProjectsListViewProps extends BaseProjectViewProps {}

export default function ProjectsListView({ projects, onUpdate }: ProjectsListViewProps) {
    const router = useRouter();

    return (
        <div className="space-y-2 pb-4 scroll-mt-24">
            {projects.map((project) => (
                <article
                    key={project.id}
                    className="group w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 text-left transition-all duration-300 hover:border-[hsl(var(--primary))]/60"
                >
                    <div className="flex items-center justify-between gap-4">
                        <div className="min-w-0 flex-1">
                            <InlineTextInput
                                value={project.title}
                                onChange={(v) => onUpdate(project.id, { title: v })}
                                placeholder="Título del proyecto"
                                maxLength={PROJECT_TITLE_MAX_LENGTH}
                                className="truncate text-sm font-semibold text-[hsl(var(--foreground))]"
                                inputClassName="text-sm"
                            />
                            <p className="truncate text-xs font-medium text-[hsl(var(--muted-foreground))]">
                                {project.description || 'Sin descripcion'}
                            </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                            <InlineProjectStatusPicker
                                value={(project.status || 'active') as ProjectRecord['status']}
                                onChange={(v) => onUpdate(project.id, { status: v })}
                                size="sm"
                            />
                            <button
                                type="button"
                                onClick={() => router.push(`/plataforma/projects/${project.id}?view=list`)}
                                aria-label={`Abrir proyecto ${project.title}`}
                                className="inline-flex size-9 items-center justify-center rounded-md text-[hsl(var(--muted-foreground))] transition-colors hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]"
                            >
                                <ArrowUpRight size={16} aria-hidden="true" />
                            </button>
                        </div>
                    </div>
                </article>
            ))}
        </div>
    );
}

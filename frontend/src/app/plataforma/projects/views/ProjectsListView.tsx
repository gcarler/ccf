'use client';

import { useRouter } from 'next/navigation';
import { ArrowUpRight, Layers, UserCog } from 'lucide-react';
import clsx from 'clsx';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { InlineUserPicker } from '@/components/ui/inline-editors/InlineUserPicker';
import { PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT, PROJECT_TITLE_MAX_LENGTH } from '@/lib/projects/constants';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import type { ProjectRecord } from '@/types/projects';
import type { BaseProjectViewProps } from './types';

interface ProjectsListViewProps extends BaseProjectViewProps {}

/** Avance PMI del proyecto: procentaje explícito o 100% completado / 0%. */
export function resolveProjectPmiProgress(project: Pick<ProjectRecord, 'progress_percent' | 'status'>): number {
    return project.progress_percent ?? (project.status === 'completed' ? 100 : 0);
}

/** Total de paquetes WBS del proyecto (conteo backend o tareas embebidas). */
export function resolveProjectWbsPackageCount(project: Pick<ProjectRecord, 'task_count' | 'tasks'>): number {
    return project.task_count ?? project.tasks?.length ?? 0;
}

export default function ProjectsListView({ projects, onUpdate }: ProjectsListViewProps) {
    const router = useRouter();
    const activeCount = projects.filter((p) => p.status === 'active').length;
    const noSponsorCount = projects.filter((p) => !p.owner_id).length;

    return (
        <div className="space-y-2 pb-4 scroll-mt-24">
            {/* Encabezado compacto de Gobernanza de Portafolio PMI */}
            <div
                data-testid="projects-list-pmi-header"
                aria-label="Gobernanza de portafolio PMI"
                className="flex flex-wrap items-center gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-1.5 text-2xs font-semibold text-[hsl(var(--text-secondary))]"
            >
                <span className="flex items-center gap-1">
                    <Layers size={10} aria-hidden="true" /> Total Portafolio: {projects.length}
                </span>
                <span className="flex items-center gap-1">
                    En Ejecucion Activa: {activeCount}
                </span>
                <span
                    className={clsx(
                        'flex items-center gap-1 px-2 py-0.5 rounded-full border',
                        noSponsorCount > 0
                            ? 'bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning-text))] border-[hsl(var(--warning)/0.4)]'
                            : 'bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success-text))] border-[hsl(var(--success)/0.4)]'
                    )}
                >
                    <UserCog size={10} aria-hidden="true" /> Sin Sponsor/PM: {noSponsorCount}
                </span>
            </div>
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
                            <InlineUserPicker
                                endpoint={PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT}
                                value={project.owner_id}
                                onChange={(userId) => onUpdate(project.id, { owner_id: userId })}
                            />
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

                    {/* Franja PMI de la tarjeta de portafolio */}
                    <div
                        data-testid={`project-list-item-pmi-${project.id}`}
                        className="mt-3 flex flex-wrap items-center gap-2 border-t border-[hsl(var(--border))] pt-2.5 text-2xs font-semibold"
                    >
                        <span className="text-[hsl(var(--text-secondary))]">
                            Avance PMI: {resolveProjectPmiProgress(project)}%
                        </span>
                        <span className="text-[hsl(var(--text-secondary))]">
                            Paquetes WBS: {resolveProjectWbsPackageCount(project)} paquetes WBS
                        </span>
                        <span
                            className={clsx(
                                'rounded-full border px-2 py-0.5',
                                project.owner_id
                                    ? 'bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success-text))] border-[hsl(var(--success)/0.4)]'
                                    : 'bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning-text))] border-[hsl(var(--warning)/0.4)]'
                            )}
                        >
                            {project.owner_id ? 'Gobernanza Activa' : 'Sin Sponsor PMI'}
                        </span>
                    </div>
                </article>
            ))}
        </div>
    );
}

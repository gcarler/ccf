'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import clsx from 'clsx';
import { DataTable } from '@/components/ui/DataTable';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { InlineUserPicker } from '@/components/ui/inline-editors/InlineUserPicker';
import { PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT, PROJECT_TITLE_MAX_LENGTH } from '@/lib/projects/constants';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import { formatDate } from '@/components/projects/utils';
import { normalizeProjectColor } from '@/lib/projects/palette';
import { ArrowUpRight, ShieldCheck, AlertTriangle, CheckCircle2, Layers } from 'lucide-react';
import type { ProjectRecord } from '@/types/projects';
import type { ColumnDef } from '@tanstack/react-table';
import type { BaseProjectViewProps } from './types';

interface ProjectsTableViewProps extends BaseProjectViewProps {}

type PortfolioFilter = 'all' | 'at_risk' | 'no_owner';

function computeProjectPmiProgress(project: ProjectRecord): number {
    if (typeof project.progress_percent === 'number') {
        return Math.round(project.progress_percent);
    }
    if (project.tasks && project.tasks.length > 0) {
        const sum = project.tasks.reduce((acc, task) => {
            const status = (task.status || 'todo').toLowerCase().trim();
            if (status === 'done' || status === 'completed') return acc + 100;
            if (status === 'in_progress' || status === 'review') return acc + 50;
            return acc;
        }, 0);
        return Math.round(sum / project.tasks.length);
    }
    if (project.status === 'completed') return 100;
    return 0;
}

function computeProjectRag(project: ProjectRecord): 'critical' | 'at_risk' | 'on_track' {
    const rawHealth = String(project.health_status || '').toLowerCase();
    if (rawHealth === 'off_track' || rawHealth === 'red') return 'critical';

    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    const hasOverdueTask = (project.tasks || []).some((task) => {
        const status = (task.status || 'todo').toLowerCase().trim();
        if (status === 'done' || status === 'completed' || !task.due_date) return false;
        const dueMs = new Date(task.due_date).getTime();
        return !Number.isNaN(dueMs) && dueMs < todayStart.getTime();
    });

    if (rawHealth === 'at_risk' || rawHealth === 'amber' || hasOverdueTask) return 'at_risk';
    return 'on_track';
}

export default function ProjectsTableView({ projects, onUpdate }: ProjectsTableViewProps) {
    const router = useRouter();
    const [portfolioFilter, setPortfolioFilter] = useState<PortfolioFilter>('all');

    const portfolioMetrics = useMemo(() => {
        const totalProjects = projects.length;
        const avgProgress =
            totalProjects > 0
                ? Math.round(
                      projects.reduce((acc, p) => acc + computeProjectPmiProgress(p), 0) / totalProjects
                  )
                : 0;
        const atRiskCount = projects.filter((p) => {
            const rag = computeProjectRag(p);
            return rag === 'at_risk' || rag === 'critical';
        }).length;
        const onTrackCount = totalProjects - atRiskCount;
        const totalTasks = projects.reduce(
            (acc, p) => acc + (p.task_count ?? p.tasks?.length ?? 0),
            0
        );
        return { totalProjects, avgProgress, onTrackCount, atRiskCount, totalTasks };
    }, [projects]);

    const filteredProjects = useMemo(() => {
        if (portfolioFilter === 'at_risk') {
            return projects.filter((p) => {
                const rag = computeProjectRag(p);
                return rag === 'at_risk' || rag === 'critical';
            });
        }
        if (portfolioFilter === 'no_owner') {
            return projects.filter((p) => !p.owner_id);
        }
        return projects;
    }, [projects, portfolioFilter]);

    const columns = useMemo<ColumnDef<ProjectRecord>[]>(
        () => [
            {
                accessorKey: 'title',
                header: 'Proyecto',
                cell: ({ row }) => {
                    const project = row.original;
                    return (
                        <div className="flex items-center gap-3">
                            <div
                                className="size-8 rounded-lg flex items-center justify-center font-semibold text-[hsl(var(--primary-foreground))]"
                                style={{ backgroundColor: normalizeProjectColor(project.color) }}
                            >
                                {project.title.slice(0, 2).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                                <InlineTextInput
                                    value={project.title}
                                    onChange={(v) => onUpdate(project.id, { title: v })}
                                    placeholder="Título del proyecto"
                                    maxLength={PROJECT_TITLE_MAX_LENGTH}
                                    className="text-base font-bold text-[hsl(var(--foreground))] truncate"
                                    inputClassName="text-base"
                                />
                                <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">
                                    {project.description || 'Sin descripción'}
                                </p>
                            </div>
                        </div>
                    );
                },
            },
            {
                accessorKey: 'owner_id',
                header: 'Responsable',
                cell: ({ row }) => {
                    const project = row.original;
                    return (
                        <InlineUserPicker
                            endpoint={PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT}
                            value={project.owner_id}
                            onChange={(userId) => onUpdate(project.id, { owner_id: userId })}
                        />
                    );
                },
            },
            {
                accessorKey: 'status',
                header: 'Estado',
                cell: ({ row }) => {
                    const project = row.original;
                    return (
                        <InlineProjectStatusPicker
                            value={project.status || 'active'}
                            onChange={(v) => onUpdate(project.id, { status: v })}
                            size="sm"
                        />
                    );
                },
            },
            {
                id: 'pmi_health',
                header: 'Salud & Avance PMI',
                cell: ({ row }) => {
                    const project = row.original;
                    const rag = computeProjectRag(project);
                    const pct = computeProjectPmiProgress(project);
                    const ragLabel =
                        rag === 'critical' ? 'Crítico' : rag === 'at_risk' ? 'En Riesgo' : 'En Ruta';
                    return (
                        <div
                            data-testid={`project-table-health-${project.id}`}
                            className="flex flex-col gap-1 min-w-[130px]"
                        >
                            <div className="flex items-center justify-between gap-1.5">
                                <span
                                    className={clsx(
                                        'px-2 py-0.5 rounded-full text-2xs font-bold border',
                                        rag === 'critical'
                                            ? 'border-[hsl(var(--destructive)/0.35)] bg-[hsl(var(--destructive)/0.12)] text-[hsl(var(--danger-text))]'
                                            : rag === 'at_risk'
                                            ? 'border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning-text))]'
                                            : 'border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success-text))]'
                                    )}
                                >
                                    {ragLabel}
                                </span>
                                <span className="text-xs font-bold text-[hsl(var(--foreground))]">
                                    {pct}%
                                </span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-[hsl(var(--surface-2))] overflow-hidden">
                                <div
                                    className={clsx(
                                        'h-full rounded-full transition-all',
                                        rag === 'critical'
                                            ? 'bg-[hsl(var(--destructive))]'
                                            : rag === 'at_risk'
                                            ? 'bg-[hsl(var(--warning))]'
                                            : 'bg-[hsl(var(--success))]'
                                    )}
                                    style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                                />
                            </div>
                        </div>
                    );
                },
            },
            {
                accessorKey: 'task_count',
                header: 'Tareas',
                cell: ({ row }) => {
                    const tasks = row.original.task_count ?? row.original.tasks?.length ?? 0;
                    return (
                        <span className="text-sm font-semibold text-[hsl(var(--foreground))]">
                            {tasks}
                        </span>
                    );
                },
            },
            {
                accessorKey: 'created_at',
                header: 'Creado',
                cell: ({ getValue }) => (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">
                        {formatDate(getValue() as string, { locale: 'es-PE' })}
                    </span>
                ),
            },
            {
                id: 'actions',
                header: 'Acción',
                cell: ({ row }) => (
                    <button
                        type="button"
                        onClick={() => router.push(`/plataforma/projects/${row.original.id}?view=list`)}
                        aria-label={`Abrir proyecto ${row.original.title}`}
                        className="inline-flex size-9 items-center justify-center rounded-md text-[hsl(var(--muted-foreground))] transition-colors hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]"
                    >
                        <ArrowUpRight size={16} aria-hidden="true" />
                    </button>
                ),
            },
        ],
        [onUpdate, router]
    );

    return (
        <div className="pb-4 space-y-3">
            {/* Banner Ejecutivo de Gobernanza de Portafolio PMI §6 */}
            <div
                data-testid="projects-table-pmi-portfolio-banner"
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3.5 py-2.5"
            >
                <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                        <ShieldCheck size={14} className="text-[hsl(var(--primary))]" />
                        Gobernanza Portafolio PMI §6: {portfolioMetrics.totalProjects} proyecto(s)
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                        Avance PMI (0/50/100): {portfolioMetrics.avgProgress}%
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success-text))]">
                        <CheckCircle2 size={11} />
                        En Ruta: {portfolioMetrics.onTrackCount}
                    </span>
                    <span
                        className={clsx(
                            'inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border',
                            portfolioMetrics.atRiskCount > 0
                                ? 'border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning-text))]'
                                : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]'
                        )}
                    >
                        <AlertTriangle size={11} />
                        En Riesgo / Críticos: {portfolioMetrics.atRiskCount}
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))]">
                        <Layers size={11} className="text-[hsl(var(--primary))]" />
                        Capacidad WBS: {portfolioMetrics.totalTasks} tareas
                    </span>
                </div>

                <div
                    data-testid="projects-table-pmi-filters"
                    className="inline-flex items-center gap-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-0.5"
                >
                    <button
                        type="button"
                        data-testid="projects-table-filter-all"
                        onClick={() => setPortfolioFilter('all')}
                        className={clsx(
                            'px-2 py-0.5 rounded-md text-2xs font-bold transition-colors',
                            portfolioFilter === 'all'
                                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                                : 'text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]'
                        )}
                    >
                        Todos
                    </button>
                    <button
                        type="button"
                        data-testid="projects-table-filter-at-risk"
                        onClick={() => setPortfolioFilter('at_risk')}
                        className={clsx(
                            'px-2 py-0.5 rounded-md text-2xs font-bold transition-colors',
                            portfolioFilter === 'at_risk'
                                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                                : 'text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]'
                        )}
                    >
                        En Riesgo / Críticos
                    </button>
                    <button
                        type="button"
                        data-testid="projects-table-filter-no-owner"
                        onClick={() => setPortfolioFilter('no_owner')}
                        className={clsx(
                            'px-2 py-0.5 rounded-md text-2xs font-bold transition-colors',
                            portfolioFilter === 'no_owner'
                                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                                : 'text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]'
                        )}
                    >
                        Sin Sponsor / PM
                    </button>
                </div>
            </div>

            <DataTable
                columns={columns}
                data={filteredProjects}
            />
        </div>
    );
}


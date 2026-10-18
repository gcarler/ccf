'use client';

import { useMemo } from 'react';
import clsx from 'clsx';
import { ShieldCheck, Activity, AlertTriangle, CheckCircle2, Layers } from 'lucide-react';
import ProjectCard from '@/components/projects/ProjectCard';
import type { ProjectRecord } from '@/types/projects';
import type { BaseProjectViewProps } from './types';

interface ProjectsBoardViewProps extends BaseProjectViewProps {}

const STAGE_GATE_LABELS: Record<string, string> = {
    active: 'Ejecución Activa · PMI §4.3',
    planning: 'Iniciación y Planificación · PMI §4.1',
    on_hold: 'Control CCB / En Pausa · PMI §4.6',
    completed: 'Cierre Administrativo · PMI §4.7',
    archived: 'Activos OPA · PMI §4.4',
};

function computeProjectProgress(project: ProjectRecord): number {
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

export default function ProjectsBoardView({ projects, onUpdate, onDelete }: ProjectsBoardViewProps) {
    const boardMetrics = useMemo(() => {
        const activeCount = projects.filter((p) => (p.status || 'active') === 'active').length;
        const totalTasks = projects.reduce(
            (acc, p) => acc + (p.task_count ?? p.tasks?.length ?? 0),
            0
        );
        return { activeCount, totalTasks, isWipOverloaded: activeCount > 5 };
    }, [projects]);

    const groupedByStatus = useMemo(() => {
        const statuses = ['active', 'planning', 'on_hold', 'completed', 'archived'];
        return statuses
            .map((status) => {
                const colProjects = projects.filter((project) => (project.status || 'active') === status);
                const colTasks = colProjects.reduce(
                    (acc, p) => acc + (p.task_count ?? p.tasks?.length ?? 0),
                    0
                );
                const colAvgProgress =
                    colProjects.length > 0
                        ? Math.round(
                              colProjects.reduce((acc, p) => acc + computeProjectProgress(p), 0) /
                                  colProjects.length
                          )
                        : 0;
                return {
                    status,
                    stageGateLabel: STAGE_GATE_LABELS[status] || status,
                    projects: colProjects,
                    colTasks,
                    colAvgProgress,
                };
            })
            .filter(
                (column) =>
                    column.projects.length > 0 ||
                    ['active', 'planning', 'completed'].includes(column.status)
            );
    }, [projects]);

    return (
        <div className="space-y-3 pb-4">
            {/* Cintillo de Gobernanza Stage-Gate y WIP de Portafolio PMI */}
            <div
                data-testid="projects-board-pmi-header"
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3.5 py-2.5"
            >
                <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                        <ShieldCheck size={14} className="text-[hsl(var(--primary))]" />
                        Stage-Gate Portafolio PMI: {projects.length} proyectos
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))]">
                        <Activity size={11} className="text-[hsl(var(--primary))]" />
                        Ejecución Activa: {boardMetrics.activeCount}
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))]">
                        <Layers size={11} className="text-[hsl(var(--primary))]" />
                        Paquetes WBS: {boardMetrics.totalTasks}
                    </span>
                </div>

                <span
                    data-testid="projects-board-wip-status"
                    className={clsx(
                        'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-2xs font-bold border',
                        boardMetrics.isWipOverloaded
                            ? 'border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))]'
                            : 'border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))]'
                    )}
                >
                    {boardMetrics.isWipOverloaded ? (
                        <>
                            <AlertTriangle size={11} />
                            Sobrecarga WIP (&gt;5 activos)
                        </>
                    ) : (
                        <>
                            <CheckCircle2 size={11} />
                            Flujo WIP Óptimo (≤5 activos)
                        </>
                    )}
                </span>
            </div>

            <div className="flex gap-4 overflow-x-auto pb-2">
                {groupedByStatus.map((column) => (
                    <section
                        key={column.status}
                        data-testid={`board-column-${column.status}`}
                        className="w-80 shrink-0 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3"
                    >
                        <div className="mb-2 flex items-center justify-between px-1">
                            <div>
                                <span className="block text-xs font-bold text-[hsl(var(--foreground))]">
                                    {column.stageGateLabel}
                                </span>
                                <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                                    {column.status}
                                </p>
                            </div>
                            <span className="font-semibold text-[hsl(var(--muted-foreground))]">
                                {column.projects.length}
                            </span>
                        </div>
                        <div
                            data-testid={`board-column-metrics-${column.status}`}
                            className="mb-3 flex items-center justify-between rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2 py-1 text-2xs font-bold text-[hsl(var(--muted-foreground))]"
                        >
                            <span>{column.colTasks} paquetes WBS</span>
                            <span className="text-[hsl(var(--primary))]">{column.colAvgProgress}% prom.</span>
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
                                <div data-testid="empty-column" className="rounded-md border border-dashed border-[hsl(var(--border))] py-8 text-center text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                                    Vacío
                                </div>
                            )}
                        </div>
                    </section>
                ))}
            </div>
        </div>
    );
}


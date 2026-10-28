'use client';

import { useMemo } from 'react';
import clsx from 'clsx';
import { Calendar, CheckCircle2, AlertTriangle, Activity, Clock } from 'lucide-react';
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
                const earnedTaskSum = tasks.reduce((acc, task) => {
                    const status = (task.status || '').toLowerCase().trim();
                    if (['completed', 'done'].includes(status)) return acc + 100;
                    if (['in_progress', 'in-progress', 'review'].includes(status)) return acc + 50;
                    return acc;
                }, 0);
                const computedTaskProgress = tasks.length
                    ? Math.round(earnedTaskSum / tasks.length)
                    : project.status === 'completed'
                    ? 100
                    : 0;
                return {
                    id: project.id,
                    title: project.title,
                    subtitle: project.status || 'active',
                    start_date: start.slice(0, 10),
                    end_date: end.slice(0, 10),
                    color: project.status === 'completed' ? ('emerald' as const) : ('blue' as const),
                    progress: project.progress_percent ?? computedTaskProgress,
                };
            }),
        [projects]
    );

    const scheduleDiagnostics = useMemo(() => {
        const avgProgress =
            items.length > 0
                ? Math.round(items.reduce((acc, item) => acc + item.progress, 0) / items.length)
                : 0;
        const missingTargetCount = projects.filter((p) => !p.target_date).length;
        const todayIso = new Date().toISOString().slice(0, 10);
        const overdueScheduleCount = projects.filter(
            (p) =>
                Boolean(p.target_date) &&
                p.target_date!.slice(0, 10) < todayIso &&
                p.status !== 'completed'
        ).length;
        return { avgProgress, missingTargetCount, overdueScheduleCount };
    }, [items, projects]);

    return (
        <div className="space-y-3 pb-4">
            {/* Cintillo de Diagnóstico de Cronograma Maestro PMI §6.5 */}
            <div
                data-testid="projects-gantt-pmi-header"
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3.5 py-2.5"
            >
                <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                        <Calendar size={14} className="text-[hsl(var(--primary))]" />
                        Cronograma Maestro PMI §6.5: {items.length} cronograma(s)
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                        <Activity size={11} />
                        Avance PMI (0/50/100): {scheduleDiagnostics.avgProgress}%
                    </span>
                    <span
                        className={clsx(
                            'inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border',
                            scheduleDiagnostics.overdueScheduleCount > 0
                                ? 'border-[hsl(var(--destructive)/0.35)] bg-[hsl(var(--destructive)/0.12)] text-[hsl(var(--destructive))]'
                                : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]'
                        )}
                    >
                        <Clock size={11} />
                        Desfase / Vencidos: {scheduleDiagnostics.overdueScheduleCount}
                    </span>
                </div>

                <span
                    data-testid="projects-gantt-baseline-status"
                    className={clsx(
                        'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-2xs font-bold border',
                        scheduleDiagnostics.missingTargetCount > 0
                            ? 'border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning-text))]'
                            : 'border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success-text))]'
                    )}
                >
                    {scheduleDiagnostics.missingTargetCount > 0 ? (
                        <>
                            <AlertTriangle size={11} />
                            {scheduleDiagnostics.missingTargetCount} sin fecha fin objetivo
                        </>
                    ) : (
                        <>
                            <CheckCircle2 size={11} />
                            Línea base completa
                        </>
                    )}
                </span>
            </div>

            <div className="h-[720px]">
                <UniversalGanttView
                    items={items}
                    moduleName="Portfolio"
                    onItemClick={onItemClick}
                />
            </div>
        </div>
    );
}


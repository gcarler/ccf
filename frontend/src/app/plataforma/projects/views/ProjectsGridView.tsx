'use client';

import { useMemo, useState } from 'react';
import clsx from 'clsx';
import { ShieldCheck, AlertTriangle, CheckCircle2, UserCheck } from 'lucide-react';
import ProjectCard from '@/components/projects/ProjectCard';
import type { ProjectRecord } from '@/types/projects';
import type { BaseProjectViewProps } from './types';

interface ProjectsGridViewProps extends BaseProjectViewProps {}

function isProjectAtRisk(project: ProjectRecord): boolean {
    const raw = String(project.health_status || '').toLowerCase();
    return ['at_risk', 'off_track', 'amber', 'red'].includes(raw);
}

export default function ProjectsGridView({ projects, onUpdate, onDelete }: ProjectsGridViewProps) {
    const [onlyAttentionRequired, setOnlyAttentionRequired] = useState(false);

    const gridMetrics = useMemo(() => {
        const atRiskCount = projects.filter((p) => isProjectAtRisk(p)).length;
        const onTrackCount = projects.length - atRiskCount;
        const withOwnerCount = projects.filter((p) => Boolean(p.owner_id)).length;
        return { atRiskCount, onTrackCount, withOwnerCount };
    }, [projects]);

    const displayedProjects = useMemo(() => {
        if (!onlyAttentionRequired) return projects;
        return projects.filter((p) => isProjectAtRisk(p) || !p.owner_id);
    }, [projects, onlyAttentionRequired]);

    return (
        <div className="space-y-3 pb-4">
            {/* Encabezado de Gobernanza Ejecutiva de Portafolio PMI */}
            <div
                data-testid="projects-grid-pmi-header"
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3.5 py-2.5"
            >
                <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                        <ShieldCheck size={14} className="text-[hsl(var(--primary))]" />
                        Capacidad Portafolio: {projects.length} proyecto(s)
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))]">
                        <CheckCircle2 size={11} />
                        En Ruta: {gridMetrics.onTrackCount}
                    </span>
                    <span
                        className={clsx(
                            'inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border',
                            gridMetrics.atRiskCount > 0
                                ? 'border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))]'
                                : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]'
                        )}
                    >
                        <AlertTriangle size={11} />
                        En Riesgo / Críticos: {gridMetrics.atRiskCount}
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))]">
                        <UserCheck size={11} className="text-[hsl(var(--primary))]" />
                        {gridMetrics.withOwnerCount}/{projects.length} con PM
                    </span>
                </div>

                <button
                    type="button"
                    data-testid="projects-grid-filter-attention"
                    onClick={() => setOnlyAttentionRequired((prev) => !prev)}
                    className={clsx(
                        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-2xs font-bold transition-all border',
                        onlyAttentionRequired
                            ? 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.4)]'
                            : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] hover:text-[hsl(var(--foreground))]'
                    )}
                >
                    <AlertTriangle size={11} />
                    <span>Atención Prioritaria (Riesgo / Sin PM)</span>
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {displayedProjects.map((project, idx) => (
                    <ProjectCard
                        key={project.id}
                        project={project}
                        index={idx}
                        onUpdate={onUpdate}
                        onDelete={onDelete}
                    />
                ))}
            </div>
        </div>
    );
}


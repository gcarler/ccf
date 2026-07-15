"use client";

import React from 'react';
import { ArrowUpRight } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import type { ProjectRecord } from '@/types/projects';

function _formatDate(dateStr: string) {
    if (!dateStr) return '—';
    try {
        return new Date(dateStr).toLocaleDateString('es-PE', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    } catch { return dateStr; }
}

interface ProjectCardProps {
    project: ProjectRecord;
    index: number;
}

export default function ProjectCard({ project, index }: ProjectCardProps) {
    const tasks = Array.isArray(project.tasks) ? project.tasks : [];
    const completed = tasks.filter(t => ['completed', 'completed'].includes((t.status || '').toLowerCase())).length;
    const inProgress = tasks.filter(t => ['in_progress'].includes((t.status || '').toLowerCase())).length;
    const progress = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;
    const color = project.color || '#2563eb';

    const statusMap: Record<string, { label: string; cls: string }> = {
        active:   { label: 'Activo',     cls: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400' },
        on_hold:  { label: 'Pausado',    cls: 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400' },
        archived: { label: 'Archivado',  cls: 'bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))]' },
    };
    const statusCfg = statusMap[project.status ?? 'active'] ?? statusMap.active;

    return (
        <Link href={`/plataforma/projects/${project.id}?view=list`} className="block">
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04, duration: 0.3 }}
            className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 p-3 shadow-sm hover:shadow-lg dark:hover:shadow-black/30 transition-all duration-300 cursor-pointer overflow-hidden"
            style={{ '--card-color': color } as React.CSSProperties}
        >
            {/* Color accent bar top */}
            <div className="absolute top-0 left-0 right-0 h-[3px] rounded-t-2xl opacity-80 group-hover:opacity-100 transition-opacity"
                style={{ background: `linear-gradient(90deg, ${color}, ${color}88)` }} />

            <div className="space-y-4">
                {/* Header row */}
                <div className="flex items-start justify-between gap-3">
                    <div
                        className="size-6 rounded-md flex items-center justify-center text-white font-black text-lg shadow-lg transition-transform group-hover:scale-105 shrink-0"
                        style={{ backgroundColor: color }}
                    >
                        {project.title.charAt(0)}
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${statusCfg.cls}`}>
                        {statusCfg.label}
                    </span>
                </div>

                {/* Title + description */}
                <div>
                    <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white leading-snug truncate">
                        {project.title}
                    </h3>
                    <p className="text-[12px] text-[hsl(var(--text-secondary))] font-medium line-clamp-2 mt-1 min-h-[32px]">
                        {project.description || 'Sin descripción.'}
                    </p>
                </div>

                {/* Task stats */}
                {tasks.length > 0 && (
                    <div className="flex items-center gap-3 text-[11px] font-medium">
                        <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                            <span className="size-1.5 rounded-full bg-emerald-500 inline-block" />
                            {completed} completadas
                        </span>
                        {inProgress > 0 && (
                            <span className="flex items-center gap-1 text-[hsl(var(--primary))]">
                                <span className="size-1.5 rounded-full bg-[hsl(var(--primary))] inline-block" />
                                {inProgress} en curso
                            </span>
                        )}
                        <span className="text-[hsl(var(--text-secondary))] ml-auto">{tasks.length} tareas</span>
                    </div>
                )}

                {/* Progress bar */}
                <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-bold text-[hsl(var(--text-secondary))]">
                        <span>Progreso</span>
                        <span style={{ color }}>{progress}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 0.8, delay: index * 0.04 + 0.2, ease: 'easeOut' }}
                            className="h-full rounded-full"
                            style={{ backgroundColor: color }}
                        />
                    </div>
                </div>

                {/* Footer: date + arrow */}
                <div className="flex items-center justify-between pt-1">
                    {project.created_at && (
                        <span className="text-[10px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                            {new Date(project.created_at).toLocaleDateString('es-PE', { month: 'short', year: 'numeric' })}
                        </span>
                    )}
                    <ArrowUpRight
                        size={16}
                        className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-secondary))] dark:group-hover:text-[hsl(var(--text-secondary))] transition-colors ml-auto"
                    />
                </div>
            </div>
        </motion.div>
        </Link>
    );
}

"use client";

import React, { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { 
    Folder, 
    Layers, 
    Plus, 
    ArrowUpRight,
} from 'lucide-react';

import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import { motion, AnimatePresence } from 'framer-motion';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectRecord } from '@/types/projects';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import type { ColumnDef } from '@tanstack/react-table';
import { DataTable } from '@/components/ui/DataTable';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { toast } from 'sonner';

function formatDate(dateStr: string) {
    if (!dateStr) return '—';
    try {
        return new Date(dateStr).toLocaleDateString('es-PE', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    } catch { return dateStr; }
}

export default function ProjectsClient({ initialProjects }: { initialProjects: ProjectRecord[] }) {
    const { token } = useAuth();
    const router = useRouter();
    const [projects, setProjects] = useState<ProjectRecord[]>(initialProjects);
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [search, setSearch] = useState('');
    const [isCreating, setIsCreating] = useState(false);

    // Quality filter: hide projects with nonsensical/test names
    const isValidProject = (p: ProjectRecord) => {
        const t = (p.title || '').trim();
        if (t.length < 2) return false;
        // Detect repeated single character (e.g. 'aaaaaaa', 'qqqqq')
        if (/^(.)\1+$/i.test(t)) return false;
        return true;
    };

    const filtered = projects
        .filter(isValidProject)
        .filter((p) =>
            p.title.toLowerCase().includes(search.toLowerCase()) ||
            (p.description || '').toLowerCase().includes(search.toLowerCase())
        );

    const handleCreateProject = async () => {
        if (isCreating) return;
        setIsCreating(true);
        try {
            const created = await apiFetch<ProjectRecord>('/projects', {
                method: 'POST',
                token,
                body: {
                    title: 'Nuevo Proyecto',
                    description: '',
                    color: '#2563eb',
                    status: 'active'
                },
            });
            setProjects((prev) => [created, ...prev]);
            toast.success('Proyecto creado');
            setTimeout(() => router.push(`/projects/${created.id}`), 200);
        } catch {
            toast.error('Error al crear el proyecto');
        } finally {
            setIsCreating(false);
        }
    };

    const projectCommands = useMemo(() => filtered.slice(0, 7).map((project) => ({
        id: `project-${project.id}`,
        label: project.title,
        description: project.description || 'Ver proyecto',
        icon: Folder,
        group: 'Proyectos',
        action: () => router.push(`/projects/${project.id}`),
    })), [filtered, router]);

    useRegisterCommands('projects-quick-links', projectCommands);

    const tableColumns = useMemo<ColumnDef<ProjectRecord>[]>(() => [
        {
            accessorKey: 'title',
            header: 'Proyecto',
            cell: ({ row }) => {
                const project = row.original;
                return (
                    <div className="flex items-center gap-3">
                        <div
                            className="size-8 rounded-2xl flex items-center justify-center text-[12px] font-black text-white"
                            style={{ backgroundColor: project.color || '#2563eb' }}
                        >
                            {project.title.slice(0, 2).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                            <p className="text-[13px] font-bold text-slate-900 dark:text-white truncate">{project.title}</p>
                            <p className="text-[11px] text-slate-400 truncate">{project.description || 'Sin descripción'}</p>
                        </div>
                    </div>
                );
            },
        },
        {
            accessorKey: 'status',
            header: 'Estado',
            cell: ({ getValue }) => {
                const status = String(getValue() || '').toUpperCase();
                return (
                    <span className="px-2 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border border-slate-200 dark:border-white/10 text-slate-500">
                        {status || 'SIN ESTADO'}
                    </span>
                );
            },
        },
        {
            accessorKey: 'tasks',
            header: 'Tareas',
            cell: ({ row }) => {
                const tasks = row.original.tasks?.length || 0;
                return <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{tasks}</span>;
            },
        },
        {
            accessorKey: 'created_at',
            header: 'Creado',
            cell: ({ getValue }) => <span className="text-sm text-slate-500">{formatDate(getValue() as string)}</span>,
        },
    ], []);

    return (
        <WorkspaceLayout
            breadcrumbs={[{ label: 'Workspace', icon: Layers }, { label: 'Portfolio de Proyectos', icon: Folder }]}
            viewType={viewType}
            setViewType={setViewType}
            availableViews={['grid', 'table']}
            onSearch={setSearch}
            rightActions={
                <div className="flex items-center gap-2">
                    <SplitDropdownButton
                        mainLabel={isCreating ? 'Creando...' : 'Nuevo'}
                        icon={Plus}
                        onMainClick={handleCreateProject}
                        onOptionClick={() => {}}
                    />
                </div>
            }
        >
            <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
                <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />
                    <div className="max-w-[1400px] mx-auto space-y-10 relative z-10">
                        <SectionHeader
                            label="Estado del portfolio"
                            caption="Supervisa y orquesta todas las iniciativas del ministerio desde un solo lugar."
                        />

                        <AnimatePresence mode="wait">
                            {viewType === 'grid' ? (
                                <motion.div key="grid" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 pb-20">
                                    {filtered.map((p, idx) => <ProjectCard key={p.id} project={p} index={idx} />)}
                                </motion.div>
                            ) : (
                                <motion.div key="table" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="pb-20">
                                    <DataTable columns={tableColumns} data={filtered} />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </main>
            </div>
        </WorkspaceLayout>
    );
}

function ProjectCard({ project, index }: { project: ProjectRecord; index: number }) {
    const router = useRouter();
    const tasks = Array.isArray(project.tasks) ? project.tasks : [];
    const completed = tasks.filter(t => ['done', 'completed'].includes((t.status || '').toLowerCase())).length;
    const inProgress = tasks.filter(t => ['in_progress'].includes((t.status || '').toLowerCase())).length;
    const progress = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;
    const color = project.color || '#2563eb';

    const statusMap: Record<string, { label: string; cls: string }> = {
        active:   { label: 'Activo',     cls: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400' },
        paused:   { label: 'Pausado',    cls: 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400' },
        archived: { label: 'Archivado',  cls: 'bg-slate-100 dark:bg-white/5 text-slate-500' },
    };
    const statusCfg = statusMap[project.status ?? 'active'] ?? statusMap.active;

    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04, duration: 0.3 }}
            onClick={() => router.push(`/projects/${project.id}`)}
            className="group relative bg-white dark:bg-[#252528] rounded-2xl border border-slate-200/70 dark:border-white/5 p-6 shadow-sm hover:shadow-xl hover:shadow-slate-200/60 dark:hover:shadow-black/30 transition-all duration-300 cursor-pointer overflow-hidden active:scale-[0.99]"
            style={{ '--card-color': color } as React.CSSProperties}
        >
            {/* Color accent bar top */}
            <div className="absolute top-0 left-0 right-0 h-[3px] rounded-t-2xl opacity-80 group-hover:opacity-100 transition-opacity"
                style={{ background: `linear-gradient(90deg, ${color}, ${color}88)` }} />

            <div className="space-y-4">
                {/* Header row */}
                <div className="flex items-start justify-between gap-3">
                    <div
                        className="size-11 rounded-xl flex items-center justify-center text-white font-black text-lg shadow-lg transition-transform group-hover:scale-105 shrink-0"
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
                    <h3 className="text-[15px] font-bold text-slate-900 dark:text-white leading-snug truncate">
                        {project.title}
                    </h3>
                    <p className="text-[12px] text-slate-400 font-medium line-clamp-2 mt-1 min-h-[32px]">
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
                            <span className="flex items-center gap-1 text-blue-500">
                                <span className="size-1.5 rounded-full bg-blue-500 inline-block" />
                                {inProgress} en curso
                            </span>
                        )}
                        <span className="text-slate-300 ml-auto">{tasks.length} tareas</span>
                    </div>
                )}

                {/* Progress bar */}
                <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-bold text-slate-400">
                        <span>Progreso</span>
                        <span style={{ color }}>{progress}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
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
                        <span className="text-[10px] text-slate-300 dark:text-slate-600">
                            {new Date(project.created_at).toLocaleDateString('es-PE', { month: 'short', year: 'numeric' })}
                        </span>
                    )}
                    <ArrowUpRight
                        size={16}
                        className="text-slate-300 group-hover:text-slate-500 dark:group-hover:text-slate-300 transition-colors ml-auto"
                    />
                </div>
            </div>
        </motion.div>
    );
}



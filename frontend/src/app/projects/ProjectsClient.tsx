"use client";

import React, { useState, useEffect, useMemo, Suspense, lazy } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { Layers, Plus, MoreHorizontal, Folder, ArrowUpRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import Skeleton from '@/components/ui/Skeleton';
import { DSSectionHeader, DSSkeleton } from '@/design';
import clsx from 'clsx';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectRecord } from '@/types/projects';
import { ColumnDef } from '@tanstack/react-table';

const ProjectTableView = lazy(() => import('@/components/projects/ProjectTableView'));

interface ProjectsClientProps {
    initialProjects: ProjectRecord[];
}

export default function ProjectsClient({ initialProjects }: ProjectsClientProps) {
    const { token } = useAuth();
    const router = useRouter();
    const [projects, setProjects] = useState<ProjectRecord[]>(initialProjects);
    const [loading, setLoading] = useState(false);
    const [search, setSearch] = useState('');
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        setProjects(initialProjects);
    }, [initialProjects]);

    const filtered = useMemo(
        () => projects.filter((p) => p.title.toLowerCase().includes(search.toLowerCase())),
        [projects, search]
    );

    const syncProjects = async () => {
        setLoading(true);
        try {
            const data = await apiFetch<ProjectRecord[]>(`/projects`, { token, cache: 'no-store' });
            setProjects(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
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
            accessorKey: 'owner_id',
            header: 'Owner ID',
            cell: ({ getValue }) => <span className="text-sm text-slate-500">#{getValue() as number}</span>,
        },
        {
            accessorKey: 'created_at',
            header: 'Creado',
            cell: ({ getValue }) => <span className="text-sm text-slate-500">{formatDate(getValue() as string)}</span>,
        },
    ], []);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Workspace', icon: Layers }, { label: 'Portfolio de Proyectos', icon: Folder }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'table']}
                onSearch={setSearch}
                rightActions={
                    <button onClick={syncProjects} className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl active:scale-95 transition-all">
                        <Plus size={14} /> Nuevo Proyecto
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />
                <div className="max-w-[1400px] mx-auto space-y-10 relative z-10">
                    <DSSectionHeader
                        eyebrow="Estado del portfolio"
                        title="Portfolio de impacto"
                        description="Proyectos que sostienen el crecimiento espiritual y operativo de la casa. Revisa progreso, dependencias y próximos hitos."
                    />

                    {loading ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-64 w-full rounded-[3rem]" />)}
                        </div>
                    ) : viewType === 'grid' ? (
                        <Suspense fallback={<GridFallback />}>
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 pb-20">
                                {filtered.map((project, idx) => (
                                    <ProjectCard key={project.id} project={project} index={idx} />
                                ))}
                            </div>
                        </Suspense>
                    ) : (
                        <Suspense fallback={<TableFallback />}>
                            <ProjectTableView
                                projects={filtered}
                                columns={tableColumns}
                                onRowClick={(project) => router.push(`/projects/${project.id}`)}
                            />
                        </Suspense>
                    )}
                </div>
            </main>
        </div>
    );
}

function ProjectCard({ project, index }: { project: ProjectRecord; index: number }) {
    const tasks = project.tasks ?? [];
    const completed = tasks.filter((task) => ['done', 'completed', 'complete'].includes((task.status || '').toLowerCase())).length;
    const progress = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;
    const badge = project.status ? project.status.toUpperCase() : 'ACTIVO';
    const color = project.color || '#2563eb';
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}
            className="group bg-white dark:bg-black/20 rounded-[3rem] border border-slate-100 dark:border-white/5 p-8 shadow-sm hover:shadow-2xl transition-all relative overflow-hidden"
        >
            <div className="absolute inset-0 bg-gradient-to-br from-white/0 via-white/5 to-white/0" />
            <div className="relative space-y-6">
                <div className="flex items-start gap-4">
                    <div className="size-14 rounded-[1.5rem] flex items-center justify-center text-white font-black text-xl shadow-xl" style={{ backgroundColor: color }}>
                        {project.title.substring(0, 1)}
                    </div>
                    <div className="min-w-0">
                        <h3 className="text-xl font-black text-slate-800 dark:text-white truncate tracking-tight">{project.title}</h3>
                        <div className="flex items-center gap-2 mt-1">
                            <span className="px-2 py-0.5 bg-slate-100 dark:bg-white/5 rounded text-[8px] font-black uppercase tracking-widest text-slate-500">{badge}</span>
                            <div className="size-1 rounded-full bg-slate-300" />
                            <span className="text-[10px] font-bold text-slate-400">{tasks.length} Tareas</span>
                        </div>
                    </div>
                </div>

                <p className="text-[13px] text-slate-500 dark:text-slate-400 font-medium leading-relaxed line-clamp-2">
                    {project.description || 'Sin descripción registrada'}
                </p>

                <div className="space-y-3 pt-2">
                    <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest">
                        <span className="text-slate-400">Progreso</span>
                        <span className="text-blue-600">{progress}%</span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden shadow-inner">
                        <motion.div
                            initial={{ width: 0 }} animate={{ width: `${progress}%` }} transition={{ duration: 1, delay: index * 0.1 }}
                            className="h-full bg-blue-600 shadow-[0_0_10px_rgba(37,99,235,0.5)]"
                        />
                    </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-white/10">
                    <div className="flex items-center -space-x-3">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="size-8 rounded-full border-2 border-white dark:border-[#1e1f21] bg-slate-200 dark:bg-slate-800 flex items-center justify-center text-[9px] font-black">U{i}</div>
                        ))}
                        <div className="size-8 rounded-full border-2 border-white dark:border-[#1e1f21] bg-blue-600 flex items-center justify-center text-[9px] font-black text-white">+{tasks.length}</div>
                    </div>
                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-all text-slate-400"><MoreHorizontal size={18} /></button>
                </div>
            </div>
        </motion.div>
    );
}

function formatDate(date: string) {
    if (!date) return 'N/D';
    return new Intl.DateTimeFormat('es-PE', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(date));
}

function GridFallback() {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 pb-20">
            {[1, 2, 3, 4, 5, 6].map((i) => (
                <DSSkeleton key={i} className="h-64 rounded-[3rem]" />
            ))}
        </div>
    );
}

function TableFallback() {
    return (
        <div className="rounded-[2rem] border border-slate-200 dark:border-white/5 overflow-hidden">
            <div className="p-6 space-y-3">
                {[...Array(5)].map((_, idx) => (
                    <DSSkeleton key={idx} className="h-16 rounded-2xl" />
                ))}
            </div>
        </div>
    );
}

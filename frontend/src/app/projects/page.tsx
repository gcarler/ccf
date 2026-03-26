"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    Layers, Plus, MoreHorizontal,
    Folder, ArrowUpRight, BarChart3
} from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import Skeleton from '@/components/ui/Skeleton';
import clsx from 'clsx';
import { useRouter } from 'next/navigation';
import type { ViewType } from '@/components/ViewSwitcher';
import { toast } from 'sonner';
import type { ProjectRecord } from '@/types/projects';
import { DataTable } from '@/components/ui/DataTable';
import type { ColumnDef } from '@tanstack/react-table';
import { useCommandCenter } from '@/context/CommandCenterContext';

export default function ProjectsPortfolioPage() {
    const { token } = useAuth();
    const router = useRouter();
    const { registerCommands } = useCommandCenter();
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState('');
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        const fetchProjects = async () => {
            if (!token) return;
            try {
                setLoading(true);
                setError(null);
                const data = await apiFetch<ProjectRecord[]>(`/projects`, {
                    token,
                    cache: 'no-store',
                });
                setProjects(Array.isArray(data) ? data : []);
            } catch (err: any) {
                console.error(err);
                const message = err?.detail?.message || 'No pudimos cargar los proyectos';
                setError(message);
                toast.error(message);
            } finally {
                setLoading(false);
            }
        };
        fetchProjects();
    }, [token]);

    const filtered = useMemo(
        () => projects.filter((p) => p.title.toLowerCase().includes(search.toLowerCase())),
        [projects, search]
    );

    const projectCommands = useMemo(() => filtered.slice(0, 7).map((project) => ({
        id: `project-${project.id}`,
        label: project.title,
        description: project.description || 'Ver proyecto',
        icon: Folder,
        group: 'Proyectos',
        action: () => router.push(`/projects/${project.id}`),
    })), [filtered, router]);

    useEffect(() => {
        if (projectCommands.length === 0) return;
        const cleanup = registerCommands('projects-quick-links', projectCommands);
        return cleanup;
    }, [projectCommands, registerCommands]);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Workspace', icon: Layers }, { label: 'Portfolio de Proyectos', icon: Folder }]}
                viewType={viewType} setViewType={setViewType} availableViews={['grid', 'table']}
                onSearch={setSearch}
                rightActions={
                    <button className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl active:scale-95 transition-all">
                        <Plus size={14} /> Nuevo Proyecto
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-[1400px] mx-auto space-y-10 relative z-10">
                    <header className="space-y-2">
                        <div className="flex items-center gap-2 text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-[0.3em]">
                            <BarChart3 size={14} /> Visión de Conjunto
                        </div>
                        <h1 className="text-4xl font-black text-slate-800 dark:text-white tracking-tighter leading-none">
                            Proyectos <span className="text-blue-600">Activos</span>
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium leading-relaxed">Administra las metas estratégicas del ministerio.</p>
                    </header>

                    {error && (
                        <div className="px-4 py-3 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-500 text-sm font-semibold">
                            {error}
                        </div>
                    )}

                    {loading ? (
                        viewType === 'grid' ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                                {[1,2,3].map(i => <Skeleton key={i} className="h-64 w-full rounded-[3rem]" />)}
                            </div>
                        ) : (
                            <div className="rounded-[2rem] border border-slate-200 dark:border-white/5 overflow-hidden">
                                <div className="p-6 text-sm text-slate-500">Preparando tabla...</div>
                            </div>
                        )
                    ) : viewType === 'grid' ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 pb-20">
                            {filtered.map((project, idx) => (
                                <ProjectCard key={project.id} project={project} index={idx} />
                            ))}
                        </div>
                    ) : (
                        <ProjectTableView projects={filtered} onRowClick={(project) => router.push(`/projects/${project.id}`)} />
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
            <div className="absolute top-0 right-0 p-8 opacity-0 group-hover:opacity-100 transition-opacity">
                <Link href={`/projects/${project.id}`} className="size-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-lg active:scale-90 transition-all">
                    <ArrowUpRight size={20} />
                </Link>
            </div>

            <div className="space-y-6">
                <div className="flex items-center gap-4">
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

                <div className="pt-6 border-t border-slate-50 dark:border-white/5 flex items-center justify-between">
                    <div className="flex -space-x-2">
                        {[1,2,3].map(i => (
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

function ProjectTableView({ projects, onRowClick }: { projects: ProjectRecord[]; onRowClick: (project: ProjectRecord) => void; }) {
    const columns = useMemo<ColumnDef<ProjectRecord>[]>(() => [
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
        <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl overflow-hidden">
            <DataTable data={projects} columns={columns} onRowClick={onRowClick} />
        </div>
    );
}

function formatDate(date: string) {
    if (!date) return 'N/D';
    return new Intl.DateTimeFormat('es-PE', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(date));
}

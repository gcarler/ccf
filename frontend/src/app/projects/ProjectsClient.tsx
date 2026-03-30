"use client";

import React, { useState, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { 
    Layout, 
    Folder, 
    Layers, 
    Plus, 
    Search, 
    ArrowUpRight
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectRecord } from '@/types/projects';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import type { ColumnDef } from '@tanstack/react-table';
import { DataTable } from '@/components/ui/DataTable';
import { SectionHeader } from '@/components/ui/SectionHeader';
import DSSkeleton from '@/components/ui/Skeleton';
import { toast } from 'sonner';
import ProjectCreationModal from '@/components/projects/ProjectCreationModal';

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
    const [loading, setLoading] = useState(false);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const newProjectBtnRef = useRef<HTMLButtonElement>(null);

    const filtered = projects.filter((p) =>
        p.title.toLowerCase().includes(search.toLowerCase()) ||
        (p.description || '').toLowerCase().includes(search.toLowerCase())
    );

    const handleCreateSubmit = async (data: { title: string; description: string; color: string }) => {
        try {
            const created = await apiFetch<ProjectRecord>('/projects', {
                method: 'POST',
                token,
                body: {
                    title: data.title,
                    description: data.description,
                    color: data.color,
                    status: 'active'
                },
            });
            setProjects((prev) => [created, ...prev]);
            toast.success('¡Proyecto Maestro iniciado!');
            setTimeout(() => router.push(`/projects/${created.id}`), 300);
        } catch (err) {
            toast.error('Error al crear el proyecto');
            throw err;
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
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Workspace', icon: Layers }, { label: 'Portfolio de Proyectos', icon: Folder }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'table']}
                onSearch={setSearch}
                rightActions={
                    <div className="flex items-center gap-2">
                        <button 
                            ref={newProjectBtnRef}
                            onClick={() => setIsCreateModalOpen(true)} 
                            className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all"
                        >
                            <Plus size={14} /> Nuevo Proyecto
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />
                <div className="max-w-[1400px] mx-auto space-y-10 relative z-10">
                    <SectionHeader
                        label="Estado del portfolio"
                        caption="Supervisa y orquesta todas las iniciativas del ministerio desde un solo lugar."
                    />

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
                                {[...Array(6)].map((_, i) => <DSSkeleton key={i} className="h-64 rounded-[3rem]" />)}
                            </motion.div>
                        ) : viewType === 'grid' ? (
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

            <ProjectCreationModal 
                isOpen={isCreateModalOpen} 
                anchorRef={newProjectBtnRef}
                onClose={() => setIsCreateModalOpen(false)} 
                onSubmit={handleCreateSubmit} 
            />
        </div>
    );
}

function ProjectCard({ project, index }: { project: ProjectRecord; index: number }) {
    const router = useRouter();
    const tasks = Array.isArray(project.tasks) ? project.tasks : [];
    const completed = tasks.filter((task) => ['done', 'completed'].includes((task.status || '').toLowerCase())).length;
    const progress = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;
    const color = project.color || '#2563eb';
    
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ delay: index * 0.05 }}
            onClick={() => router.push(`/projects/${project.id}`)}
            className="group bg-white dark:bg-white/5 rounded-[3rem] border border-slate-100 dark:border-white/5 p-8 shadow-sm hover:shadow-2xl transition-all relative overflow-hidden cursor-pointer active:scale-[0.98]"
        >
            <div className="relative z-10 space-y-6">
                <div className="flex items-start justify-between">
                    <div className="size-14 rounded-[1.5rem] flex items-center justify-center text-white font-black text-xl shadow-xl transition-transform group-hover:scale-110" style={{ backgroundColor: color }}>
                        {project.title.substring(0, 1)}
                    </div>
                    <ArrowUpRight className="text-slate-200 group-hover:text-blue-500 transition-colors" />
                </div>

                <div>
                    <h3 className="text-xl font-black text-slate-900 dark:text-white leading-tight mb-2 truncate">{project.title}</h3>
                    <p className="text-sm text-slate-400 font-medium line-clamp-2 min-h-[40px]">{project.description || 'Sin descripción detallada.'}</p>
                </div>

                <div className="space-y-3 pt-2">
                    <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-slate-400">
                        <span>Progreso</span>
                        <span className="text-blue-600">{progress}%</span>
                    </div>
                    <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-600 rounded-full transition-all duration-1000" style={{ width: `${progress}%` }} />
                    </div>
                </div>
            </div>
        </motion.div>
    );
}

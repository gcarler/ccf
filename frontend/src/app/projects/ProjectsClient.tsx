"use client";

import React, { useState, useMemo, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
    Folder, 
    Layers, 
    Plus, 
    ArrowUpRight,
    TrendingUp
} from 'lucide-react';

import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion, AnimatePresence } from 'framer-motion';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectRecord } from '@/types/projects';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import type { ColumnDef } from '@tanstack/react-table';
import { DataTable } from '@/components/ui/DataTable';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { DSMetric } from '@/design/components/DSMetric';
import { DSChart } from '@/design/components/DSChart';
import { DSCard } from '@/design/components/DSCard';
import { toast } from 'sonner';

const PROJECT_VIEWS: ViewType[] = ['grid', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

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
    const [dashboard, setDashboard] = useState<any>(null);
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [search, setSearch] = useState('');
    const [isCreating, setIsCreating] = useState(false);

    useEffect(() => {
        if (!token) return;
        const loadDashboard = async () => {
            try {
                const data = await apiFetch<any>('/dashboard/projects', { token });
                setDashboard(data);
            } catch (err) {
                console.error('Error fetching projects dashboard', err);
            }
        };
        loadDashboard();
    }, [token]);

    // Quality filter: hide projects with nonsensical/test names
    const isValidProject = (p: ProjectRecord) => {
        const t = (p.title || '').trim();
        if (t.length < 2) return false;
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
            const created = await apiFetch<ProjectRecord>('/projects/', {
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
            window.dispatchEvent(new CustomEvent('project-updated'));
            setTimeout(() => router.push(`/projects/${created.id}`), 200);
        } catch (e: any) {
            console.error('Error creating project:', e);
            toast.error('Error al crear el proyecto');
        } finally {
            setIsCreating(false);
        }
    };

    const handleQuickCreate = (type: string) => {
        if (type === 'whiteboard') {
            router.push('/whiteboard/new');
            return;
        }
        handleCreateProject();
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
                            className="size-8 rounded-lg flex items-center justify-center font-semibold text-white"
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
                    <span className="px-2 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide border border-slate-200 dark:border-white/10 text-slate-500">
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

    const groupedByStatus = useMemo(() => {
        const statuses = ['active', 'planning', 'on_hold', 'completed', 'archived'];
        return statuses.map((status) => ({
            status,
            projects: filtered.filter((project) => (project.status || 'active') === status),
        })).filter((column) => column.projects.length > 0 || ['active', 'planning', 'completed'].includes(column.status));
    }, [filtered]);

    const calendarEvents = useMemo(() => filtered.map((project) => ({
        id: project.id,
        title: project.title,
        date: (project.updated_at || project.created_at || new Date().toISOString()).slice(0, 10),
        color: project.status === 'completed' ? 'emerald' as const : project.status === 'on_hold' ? 'amber' as const : 'blue' as const,
        location: project.description || undefined,
    })), [filtered]);

    const ganttItems = useMemo(() => filtered.map((project) => {
        const start = project.created_at || new Date().toISOString();
        const end = project.updated_at || start;
        const tasks = Array.isArray(project.tasks) ? project.tasks : [];
        const done = tasks.filter((task) => ['done', 'completed'].includes((task.status || '').toLowerCase())).length;
        return {
            id: project.id,
            title: project.title,
            subtitle: project.status || 'active',
            start_date: start.slice(0, 10),
            end_date: end.slice(0, 10),
            color: project.status === 'completed' ? 'emerald' as const : 'blue' as const,
            progress: tasks.length ? Math.round((done / tasks.length) * 100) : project.progress_percent ?? 0,
        };
    }), [filtered]);

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Proyectos', icon: Folder }, { label: 'Centro de Comando', icon: Layers }]}
                viewType={viewType}
                setViewType={setViewType}
                allowedViews={PROJECT_VIEWS}
                onSearch={setSearch}
                rightActions={
                    <SplitDropdownButton
                        mainLabel={isCreating ? 'Creando...' : 'Nuevo Proyecto'}
                        icon={Plus}
                        onMainClick={handleCreateProject}
                        options={[
                            { id: 'whiteboard', label: 'Pizarra', icon: Layers, onClick: () => handleQuickCreate('whiteboard') },
                        ]}
                    />
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 space-y-6">
                {/* 📊 Project Metrics */}
                <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {dashboard?.cards.map((card: any, idx: number) => (
                        <DSMetric 
                            key={idx}
                            label={card.title} 
                            value={card.value} 
                            trend={card.trend} 
                            tone={card.color} 
                        />
                    ))}
                </section>

                {/* 📈 Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Carga de Trabajo del Equipo</h3>
                            <DSChart type="bar" data={dashboard?.workload_distribution} color="#f59e0b" height={220} />
                        </DSCard>
                    </div>
                    <div>
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Estado de Tareas</h3>
                            <div className="space-y-4 pt-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-bold text-slate-400">Tareas Atrasadas</span>
                                    <span className="text-sm font-black text-rose-500">{dashboard?.delayed_tasks_count || 0}</span>
                                </div>
                                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-rose-500" style={{ width: '15%' }} />
                                </div>
                                <p className="text-[10px] text-slate-500 italic">
                                    Se recomienda revisar los hitos críticos para evitar cuellos de botella.
                                </p>
                            </div>
                        </DSCard>
                    </div>
                </div>

                <div className="h-px bg-white/5 my-8" />

                <div className="relative">
                    <AnimatePresence mode="wait">
                        {viewType === 'grid' ? (
                            <motion.div key="grid" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 pb-4">
                                {filtered.map((p, idx) => <ProjectCard key={p.id} project={p} index={idx} />)}
                            </motion.div>
                        ) : viewType === 'table' ? (
                            <motion.div key="table" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="pb-4">
                                <DataTable columns={tableColumns} data={filtered} />
                            </motion.div>
                        ) : viewType === 'list' ? (
                            <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-2 pb-4">
                                {filtered.map((project) => (
                                    <button key={project.id} onClick={() => router.push(`/projects/${project.id}`)} className="w-full rounded-md border border-slate-200 bg-white p-4 text-left transition-all duration-300 hover:border-blue-300 active:scale-[0.99] dark:border-white/10 dark:bg-[#252528] hover:dark:bg-[#2A2B2E]">
                                        <div className="flex items-center justify-between gap-4">
                                            <div className="min-w-0">
                                                <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">{project.title}</p>
                                                <p className="truncate text-xs font-medium text-slate-400">{project.description || 'Sin descripcion'}</p>
                                            </div>
                                            <span className="shrink-0 rounded-full border border-slate-200 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:border-white/10">{project.status || 'active'}</span>
                                        </div>
                                    </button>
                                ))}
                            </motion.div>
                        ) : viewType === 'board' || viewType === 'kanban' ? (
                            <motion.div key="board" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex gap-4 overflow-x-auto pb-4">
                                {groupedByStatus.map((column) => (
                                    <section key={column.status} className="w-80 shrink-0 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-[#252528]">
                                        <div className="mb-3 flex items-center justify-between px-1">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{column.status}</p>
                                            <span className="font-semibold text-slate-400">{column.projects.length}</span>
                                        </div>
                                        <div className="space-y-2">
                                            {column.projects.map((project, index) => <ProjectCard key={project.id} project={project} index={index} />)}
                                            {column.projects.length === 0 && <div className="rounded-md border border-dashed border-slate-200 py-8 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:border-white/10">Vacio</div>}
                                        </div>
                                    </section>
                                ))}
                            </motion.div>
                        ) : viewType === 'calendar' ? (
                            <motion.div key="calendar" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-[720px] pb-4">
                                <UniversalCalendarView events={calendarEvents} title="Calendario de proyectos" onEventClick={(event) => router.push(`/projects/${event.id}`)} />
                            </motion.div>
                        ) : viewType === 'gantt' ? (
                            <motion.div key="gantt" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-[720px] pb-4">
                                <UniversalGanttView items={ganttItems} moduleName="Portfolio" onItemClick={(item) => router.push(`/projects/${item.id}`)} />
                            </motion.div>
                        ) : (
                            <motion.div key="wiki" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="pb-4">
                                <UniversalWikiView moduleName="Proyectos" storageKey="wiki_projects_portfolio" />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
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
        on_hold:  { label: 'Pausado',    cls: 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400' },
        archived: { label: 'Archivado',  cls: 'bg-slate-100 dark:bg-white/5 text-slate-500' },
    };
    const statusCfg = statusMap[project.status ?? 'active'] ?? statusMap.active;

    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04, duration: 0.3 }}
            onClick={() => router.push(`/projects/${project.id}`)}
            className="group relative bg-white dark:bg-[#252528] rounded-lg border border-slate-200/70 dark:border-white/5 p-3 shadow-sm hover:shadow-xl hover:shadow-slate-200/60 dark:hover:shadow-black/30 transition-all duration-300 cursor-pointer overflow-hidden active:scale-[0.99]"
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
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-snug truncate">
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

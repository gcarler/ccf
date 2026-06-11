"use client";

import {
Folder,
Layers,
Plus
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import React,{ useEffect,useMemo,useState } from 'react';

import type { ViewType } from '@/components/ViewSwitcher';
import ProjectsShell from '@/components/projects/ProjectsShell';
import ProjectCard from '@/components/projects/ProjectCard';
import { formatDate } from '@/components/projects/utils';
import { DataTable } from '@/components/ui/DataTable';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import UserSelect from '@/components/ui/UserSelect';
import { useAuth } from '@/context/AuthContext';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import { DSCard } from '@/design/components/DSCard';
import { DSChart } from '@/design/components/DSChart';
import { DSMetric } from '@/design/components/DSMetric';
import { apiFetch } from '@/lib/http';
import type { ProjectRecord } from '@/types/projects';
import type { ColumnDef } from '@tanstack/react-table';
import { AnimatePresence,motion } from 'framer-motion';
import { toast } from 'sonner';

const PROJECT_VIEWS: ViewType[] = ['grid', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function ProjectsClient({ initialProjects }: { initialProjects: ProjectRecord[] }) {
    const { token } = useAuth();
    const router = useRouter();
    const [projects, setProjects] = useState<ProjectRecord[]>(initialProjects);
    const [dashboard, setDashboard] = useState<any>(null);
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [search, setSearch] = useState('');
    const [isCreating, setIsCreating] = useState(false);
    const [newProjectOwner, setNewProjectOwner] = useState<string | null>(null);
    const [newProjectTitle, setNewProjectTitle] = useState('');
    const [showCreateForm, setShowCreateForm] = useState(false);

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
            const created = await apiFetch<ProjectRecord>('/projects', {
                method: 'POST',
                token,
                body: {
                    title: newProjectTitle.trim() || 'Nuevo Proyecto',
                    description: '',
                    color: '#2563eb',
                    status: 'active',
                    owner_id: newProjectOwner,
                },
            });
            setProjects((prev) => [created, ...prev]);
            setNewProjectOwner(null);
            setShowCreateForm(false);
            toast.success('Proyecto creado');
            window.dispatchEvent(new CustomEvent('project-updated'));
            setTimeout(() => router.push(`/plataforma/projects/${created.id}`), 200);
        } catch (e: any) {
            console.error('Error creating project:', e);
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
        action: () => router.push(`/plataforma/projects/${project.id}`),
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
        const done = tasks.filter((task) => ['completed', 'completed'].includes((task.status || '').toLowerCase())).length;
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
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Folder }, { label: 'Centro de Comando', icon: Layers }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={PROJECT_VIEWS}
            onSearch={setSearch}
            rightActions={
                <button
                    onClick={() => setShowCreateForm(!showCreateForm)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide transition-all hover:scale-105 ${
                        showCreateForm
                            ? 'bg-slate-200 dark:bg-white/10 text-slate-600 dark:text-slate-300'
                            : 'bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20'
                    }`}
                >
                    <Plus size={14} />
                    {isCreating ? 'Creando...' : 'Nuevo Proyecto'}
                </button>
            }
        >
                {showCreateForm && (
                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg p-4 border border-slate-200 dark:border-white/10 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
                        <h3 className="text-xs font-bold uppercase tracking-wide text-slate-600">Nuevo Proyecto</h3>
                        <input
                            value={newProjectTitle}
                            onChange={(e) => setNewProjectTitle(e.target.value)}
                            className="w-full p-2 rounded-md border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm font-medium"
                            placeholder="Título del proyecto"
                        />
                        <UserSelect
                            value={newProjectOwner}
                            onChange={setNewProjectOwner}
                            placeholder="Asignar responsable del proyecto"
                        />
                        <div className="flex gap-2">
                            <button
                                onClick={handleCreateProject}
                                disabled={isCreating || !newProjectTitle.trim()}
                                className="px-3 py-1.5 bg-[hsl(var(--primary))] disabled:bg-[hsl(var(--primary))] text-white rounded-md text-xs font-bold uppercase tracking-wide hover:scale-105 transition-all"
                            >
                                {isCreating ? 'Creando...' : 'Crear Proyecto'}
                            </button>
                            <button
                                onClick={() => { setShowCreateForm(false); setNewProjectTitle(''); setNewProjectOwner(null); }}
                                className="px-3 py-1.5 bg-slate-200 dark:bg-white/10 rounded-md text-xs font-bold uppercase tracking-wide hover:scale-105 transition-all"
                            >
                                Cancelar
                            </button>
                        </div>
                    </div>
                )}

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
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                    <div className="lg:col-span-2">
                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Carga de Trabajo del Equipo</h3>
                            <DSChart type="bar" data={dashboard?.workload_distribution} color="#f59e0b" height={220} />
                        </DSCard>
                    </div>
                    <div>
                        <DSCard>
                            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Estado de Tareas</h3>
                            <div className="space-y-4 pt-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-bold text-slate-400">Tareas Atrasadas</span>
                                    <span className="text-sm font-semibold text-rose-500">{dashboard?.delayed_tasks_count || 0}</span>
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
                        {filtered.length === 0 ? (
                            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center py-16 text-center">
                                <Folder size={48} className="text-slate-300 dark:text-slate-600 mb-4" />
                                <h3 className="text-lg font-bold text-slate-700 dark:text-slate-300">No hay proyectos</h3>
                                <p className="text-sm text-slate-500 mt-1 mb-4 max-w-md">{search ? 'Ningún proyecto coincide con tu búsqueda.' : 'Crea tu primer proyecto para empezar.'}</p>
                                {!search && (
                                    <button onClick={() => setShowCreateForm(true)} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wide shadow-lg">
                                        <Plus size={16} /> Crear proyecto
                                    </button>
                                )}
                            </motion.div>
                        ) : viewType === 'grid' ? (
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
                                    <button key={project.id} onClick={() => router.push(`/plataforma/projects/${project.id}`)} className="w-full rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 text-left transition-all duration-300 hover:border-blue-300 active:scale-[0.99] dark:border-white/10 dark:bg-[#252528] hover:dark:bg-[#2A2B2E]">
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
                                <UniversalCalendarView events={calendarEvents} title="Calendario de proyectos" onEventClick={(event) => router.push(`/plataforma/projects/${event.id}`)} />
                            </motion.div>
                        ) : viewType === 'gantt' ? (
                            <motion.div key="gantt" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-[720px] pb-4">
                                <UniversalGanttView items={ganttItems} moduleName="Portfolio" onItemClick={(item) => router.push(`/plataforma/projects/${item.id}`)} />
                            </motion.div>
                        ) : (
                            <motion.div key="wiki" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="pb-4">
                                <UniversalWikiView moduleName="Proyectos" storageKey="wiki_projects_portfolio" />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
        </ProjectsShell>
    );
}


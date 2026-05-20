"use client";

import React, { useState, useEffect, useMemo } from 'react';
import UniversalTableView from '@/components/ui/UniversalTableView';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { 
    CheckCircle2, Circle, Search,
    ChevronRight, Zap, Bot,
    CalendarDays, ListChecks,
    FolderOpen
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import TaskEditDrawer, { TaskDetail } from '@/components/ui/TaskEditDrawer';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Link from 'next/link';
import { ViewType } from '@/components/ViewSwitcher';


interface Task {
    id: number;
    title: string;
    status: string;
    priority: string | null;
    due_date: string | null;
    project_id: number;
    project_title?: string;
    done?: boolean;
}

const PRIORITY_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
    urgent: { label: 'Urgente', color: 'text-rose-600 bg-rose-50 dark:bg-rose-900/20', dot: 'bg-rose-500' },
    high:   { label: 'Alta',    color: 'text-orange-600 bg-orange-50 dark:bg-orange-900/20', dot: 'bg-orange-500' },
    medium: { label: 'Media',   color: 'text-amber-600 bg-amber-50 dark:bg-amber-900/20', dot: 'bg-amber-500' },
    low:    { label: 'Baja',    color: 'text-slate-500 bg-slate-50 dark:bg-slate-800', dot: 'bg-slate-400' },
};

const STATUS_LABEL: Record<string, string> = {
    todo: 'Por hacer', in_progress: 'En progreso', done: 'Completada', blocked: 'Bloqueada'
};

const XP_MAP: Record<string, number> = { urgent: 100, high: 60, medium: 40, low: 20 };

export default function UserTasksPage() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [tasks, setTasks]           = useState<Task[]>([]);
    const [query, setQuery]           = useState('');
    const [filterPriority, setFilterPriority] = useState<string>('all');
    const [loading, setLoading]       = useState(true);
    const [completing, setCompleting] = useState<number | null>(null);
    const [viewType, setViewType]     = useState<ViewType>('list');
    const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null);

    // ── Handlers ──────────────────────────────────────────────────
    const handleTaskSelect = (task: Task) => {
        setSelectedTask(task as TaskDetail);
    };

    const handleTaskUpdated = (updated: TaskDetail) => {
        setTasks(prev => prev.map(t =>
            t.id === updated.id ? { ...t, ...updated } : t
        ));
        if (updated.status === 'done') {
            const priorityKey = updated.priority ?? 'low';
            addToast(`✓ Tarea completada! +${(XP_MAP[priorityKey] || XP_MAP['low'])} XP`, 'success');
        }
    };

    const handleTaskDeleted = (taskId: number) => {
        setTasks(prev => prev.filter(t => t.id !== taskId));
        addToast('Tarea eliminada', 'info');
    };

    useEffect(() => {
        const loadTasks = async () => {
            if (!token) { setLoading(false); return; }
            try {
                // Endpoint real disponible en el backend
                let allTasks: Task[] = [];
                try {
                    const direct = await apiFetch<any[]>('/projects/tasks', { token, cache: 'no-store' });
                    if (Array.isArray(direct)) {
                        allTasks = direct.slice(0, 50);
                    }
                } catch {
                    // Fallback: parallel fetch of all projects
                    const projects = await apiFetch<any[]>('/projects', { token, cache: 'no-store' });
                    const results = await Promise.all(
                        (projects || []).slice(0, 15).map(p =>
                            apiFetch<any>(`/projects/${p.id}`, { token, cache: 'no-store' })
                                .then(d => (d.tasks || []).map((t: any) => ({
                                    ...t,
                                    project_id: p.id,
                                    project_title: p.title
                                })))
                                .catch(() => [])
                        )
                    );
                    allTasks = results.flat().slice(0, 50);
                }
                const active = allTasks
                    .filter(t => t.status !== 'done')
                    .sort((a, b) => {
                        const order = ['urgent', 'high', 'medium', 'low'];
                        return (order.indexOf(a.priority || 'low') - order.indexOf(b.priority || 'low'));
                    });
                setTasks(active);
            } catch (err) {
                console.error('[Tasks] fetch failed', err);
                setTasks([
                    { id: 1, title: 'Llamar a nuevos visitantes (Sede Norte)', status: 'todo', priority: 'high', due_date: null, project_id: 1, project_title: 'CRM Pastoral' },
                    { id: 2, title: 'Completar evaluación de Fundamentos', status: 'in_progress', priority: 'medium', due_date: null, project_id: 2, project_title: 'Academia' },
                    { id: 3, title: 'Preparar diapositivas domingo', status: 'todo', priority: 'urgent', due_date: null, project_id: 1, project_title: 'Ministerio' },
                ]);
            } finally {
                setLoading(false);
            }
        };
        loadTasks();
    }, [token]);

    const completeTask = async (id: number) => {
        setCompleting(id);
        await new Promise(r => setTimeout(r, 600));
        const task = tasks.find(t => t.id === id);
        setTasks(prev => prev.filter(t => t.id !== id));
        setCompleting(null);
        const priorityKey = task?.priority ?? 'low';
        addToast(`✓ ${task?.title?.slice(0, 36)}... completada! +${(XP_MAP[priorityKey] || XP_MAP['low'])} XP`, 'success');
    };

    const filtered = useMemo(() => tasks.filter(t => {
        const matchQ = !query || t.title.toLowerCase().includes(query.toLowerCase());
        const matchP = filterPriority === 'all' || t.priority === filterPriority;
        return matchQ && matchP;
    }), [tasks, query, filterPriority]);

    const pending   = tasks.length;
    const dueToday  = tasks.filter(t => t.due_date && new Date(t.due_date).toDateString() === new Date().toDateString()).length;
    const urgent    = tasks.filter(t => t.priority === 'urgent').length;

    if (!isAuthenticated) return null;

    return (
        <WorkspaceLayout
            breadcrumbs={[{ label: 'Mi Centro de Tareas', icon: ListChecks, href: '/tasks' }]}
            viewType={viewType}
            setViewType={setViewType}
            availableViews={['list', 'table', 'grid', 'kanban']}
    };

    const filtered = useMemo(() => tasks.filter(t => {
        const matchQ = !query || t.title.toLowerCase().includes(query.toLowerCase());
        const matchP = filterPriority === 'all' || t.priority === filterPriority;
        return matchQ && matchP;
    }), [tasks, query, filterPriority]);

    const pending   = tasks.length;
    const dueToday  = tasks.filter(t => t.due_date && new Date(t.due_date).toDateString() === new Date().toDateString()).length;
    const urgent    = tasks.filter(t => t.priority === 'urgent').length;

    if (!isAuthenticated) return null;

    return (
        <WorkspaceLayout
            breadcrumbs={[{ label: 'Mi Centro de Tareas', icon: ListChecks, href: '/tasks' }]}
            viewType={viewType}
            setViewType={setViewType}
            availableViews={['list', 'table', 'grid', 'kanban']}
            rightActions={
                <SplitDropdownButton
                    onMainClick={() => {}}
                    onOptionClick={() => {}}
                />
            }
        >
            <div className="flex flex-col h-full bg-slate-50 dark:bg-[#1E1F21] overflow-hidden rounded-2xl">
            {/* ── TASK EDIT DRAWER ── */}
            <TaskEditDrawer
                task={selectedTask}
                onClose={() => setSelectedTask(null)}
                onTaskUpdated={handleTaskUpdated}
                onTaskDeleted={handleTaskDeleted}
            />

            <main className="flex-1 overflow-y-auto">

                {/* ── TABLE VIEW ── */}
                {viewType === 'table' && (
                    <UniversalTableView
                        data={filtered}
                        columns={[
                            { 
                                key: 'title', 
                                label: 'Tarea', 
                                type: 'text', 
                                width: '400px',
                                render: (val, task) => (
                                    <div className="flex items-center gap-3">
                                        <button onClick={() => completeTask(task.id)}
                                            className="size-5 rounded-full border-2 border-slate-200 dark:border-white/10 hover:border-emerald-400 hover:bg-emerald-50 transition-all flex items-center justify-center shrink-0">
                                            <Circle size={10} className="text-slate-300" />
                                        </button>
                                        <span className="text-[13px] font-semibold text-slate-800 dark:text-slate-200 truncate group-hover:text-blue-600 transition-colors">{task.title}</span>
                                    </div>
                                )
                            },
                            { 
                                key: 'project_title', 
                                label: 'Proyecto', 
                                type: 'text', 
                                width: '200px',
                                render: (val) => (
                                    <div className="flex items-center gap-2 text-[11px] font-bold text-slate-400 uppercase tracking-wide">
                                        <FolderOpen size={11} className="shrink-0" /> {val || '—'}
                                    </div>
                                )
                            },
                            { key: 'priority', label: 'Prioridad', type: 'priority', width: '150px' },
                            { key: 'status', label: 'Estado', type: 'status', width: '150px' },
                            { key: 'due_date', label: 'Fecha límite', type: 'date', width: '150px' },
                        ]}
                        groupBy="status"
                        emptyMessage="Sin tareas en esta vista"
                    />
                )}

                {/* ── GRID VIEW ── */}
                {viewType === 'grid' && (
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {filtered.map((task, idx) => {
                            const priorityKey = task.priority ?? 'low';
                            const pc = PRIORITY_CONFIG[priorityKey] || PRIORITY_CONFIG['low'];
                            return (
                                <motion.div key={task.id}
                                    initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.04 }}
                                    onClick={() => handleTaskSelect(task)}
                                    className="group bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/7 rounded-2xl p-5 shadow-sm hover:shadow-xl hover:border-blue-200 dark:hover:border-white/15 transition-all duration-300 active:scale-[0.99] cursor-pointer">
                                    <div className="flex items-start justify-between mb-3">
                                        <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-black uppercase", pc.color)}>{pc.label}</span>
                                        <button onClick={(e) => { e.stopPropagation(); completeTask(task.id); }}
                                            className="size-7 rounded-full border-2 border-slate-200 dark:border-white/10 hover:border-emerald-400 hover:bg-emerald-50 transition-all flex items-center justify-center">
                                            <Circle size={12} className="text-slate-300" />
                                        </button>
                                    </div>
                                    <p className="text-[14px] font-bold text-slate-800 dark:text-white mb-3 leading-snug line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{task.title}</p>
                                    <div className="flex items-center justify-between mt-auto">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1">
                                            <FolderOpen size={10}/> {task.project_title || 'Sin proyecto'}
                                        </span>
                                        <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-50 dark:bg-amber-900/20 text-amber-600 rounded-lg text-[9px] font-black">
                                            <Zap size={9} fill="currentColor" /> +{XP_MAP[priorityKey] || XP_MAP['low']} XP
                                        </span>
                                    </div>
                                </motion.div>
                            );
                        })}
                    </div>
                )}

                {/* ── KANBAN VIEW ── */}
                {viewType === 'kanban' && (
                    <div className="flex gap-5 p-6 overflow-x-auto" style={{ minHeight: 'calc(100vh - 120px)' }}>
                        {(Object.entries(STATUS_LABEL) as [string, string][]).map(([status, label]) => {
                            const colTasks = filtered.filter(t => t.status === status);
                            return (
                                <div key={status} className="shrink-0 w-72 flex flex-col bg-slate-100/60 dark:bg-white/[0.03] rounded-2xl border border-slate-200 dark:border-white/5 overflow-hidden">
                                    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-white/5">
                                        <span className="text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-400">{label}</span>
                                        <span className="text-[10px] font-bold text-slate-400 bg-white dark:bg-white/5 px-2 py-0.5 rounded-full border border-slate-200 dark:border-white/10">{colTasks.length}</span>
                                    </div>
                                    <div className="flex-1 p-3 space-y-2 overflow-y-auto">
                                        {colTasks.map((task, idx) => {
                                            const priorityKey = task.priority ?? 'low';
                                            const pc = PRIORITY_CONFIG[priorityKey] || PRIORITY_CONFIG['low'];
                                            return (
                                                <motion.div key={task.id}
                                                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }}
                                                    onClick={() => handleTaskSelect(task)}
                                                    className="p-3 bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/7 rounded-xl shadow-sm hover:shadow-md hover:border-blue-200 dark:hover:border-white/20 transition-all duration-300 active:scale-[0.99] cursor-pointer group">
                                                    <p className="text-[12px] font-semibold text-slate-800 dark:text-slate-200 mb-2 line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{task.title}</p>
                                                    <div className="flex items-center justify-between">
                                                        <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-black", pc.color)}>{pc.label}</span>
                                                        <button onClick={(e) => { e.stopPropagation(); completeTask(task.id); }}
                                                            className="size-6 rounded-full border border-slate-200 hover:border-emerald-400 hover:bg-emerald-50 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                                                            <Circle size={10} className="text-slate-300" />
                                                        </button>
                                                    </div>
                                                </motion.div>
                                            );
                                        })}
                                        {colTasks.length === 0 && (
                                            <div className="h-16 flex items-center justify-center border-2 border-dashed border-slate-200 dark:border-white/5 rounded-xl text-[10px] font-bold text-slate-400 uppercase tracking-widest">Vacío</div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* ── LIST VIEW (default) ── */}
                {(viewType === 'list' || (viewType !== 'table' && viewType !== 'grid' && viewType !== 'kanban')) && (
                <div className="w-full p-6 lg:p-10 grid grid-cols-1 lg:grid-cols-12 gap-8 pb-24">

                    {/* ── LEFT COLUMN ── */}
                    <div className="lg:col-span-8 space-y-6">

                        {/* Search + Filter bar */}
                        <div className="flex items-center gap-3">
                            <div className="relative flex-1">
                                <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    value={query}
                                    onChange={e => setQuery(e.target.value)}
                                    placeholder="Buscar tareas..."
                                    className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl py-2.5 pl-11 pr-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500/20 transition-all"
                                />
                            </div>
                        <div className="flex items-center gap-2 flex-wrap">
                            {(['all', 'urgent', 'high', 'medium', 'low'] as const).map(p => (
                                <button
                                    key={p}
                                    onClick={() => setFilterPriority(p)}
                                    className={clsx(
                                        "px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                                        filterPriority === p
                                            ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
                                            : "bg-white dark:bg-white/5 text-slate-400 border border-slate-200 dark:border-white/10 hover:border-slate-300"
                                    )}
                                >
                                    {p === 'all' ? 'Todo' : PRIORITY_CONFIG[p]?.label}
                                </button>
                            ))}
                        </div>
                        </div>

                        {/* Task list */}
                        {loading ? (
                            <div className="space-y-3">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="h-20 bg-white dark:bg-white/5 rounded-3xl animate-pulse border border-slate-100 dark:border-white/5" />
                                ))}
                            </div>
                        ) : filtered.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-24 text-center gap-4">
                                {query || filterPriority !== 'all' ? (
                                    // Filtro activo sin resultados
                                    <>
                                        <div className="size-16 rounded-3xl bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                                            <Search size={28} className="text-slate-400" />
                                        </div>
                                        <div>
                                            <p className="text-lg font-black text-slate-700 dark:text-white">Sin resultados</p>
                                            <p className="text-sm text-slate-400 mt-1">No hay tareas que coincidan con tu búsqueda.</p>
                                        </div>
                                        <button onClick={() => { setQuery(''); setFilterPriority('all'); }}
                                            className="text-[11px] font-black text-blue-600 hover:text-blue-700 uppercase tracking-widest">
                                            Limpiar filtros
                                        </button>
                                    </>
                                ) : (
                                    // Sin tareas asignadas
                                    <>
                                        <div className="size-16 rounded-3xl bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
                                            <CheckCircle2 size={28} className="text-emerald-500" />
                                        </div>
                                        <div>
                                            <p className="text-lg font-black text-slate-700 dark:text-white">Sin tareas pendientes</p>
                                            <p className="text-sm text-slate-400 mt-1 max-w-xs">
                                                No tienes tareas asignadas. Ve a un proyecto y asígnate tareas para verlas aquí.
                                            </p>
                                        </div>
                                        <Link href="/projects"
                                            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest hover:bg-blue-700 active:scale-95 transition-all shadow-lg shadow-blue-500/20">
                                            <FolderOpen size={13} /> Ver proyectos
                                        </Link>
                                    </>
                                )}
                            </div>
                        ) : (
                            <AnimatePresence mode="popLayout">
                                {filtered.map((task, idx) => {
                                    const priorityKey = task.priority ?? 'low';
                                    const pc = PRIORITY_CONFIG[priorityKey] || PRIORITY_CONFIG['low'];
                                    const xp = XP_MAP[priorityKey] || XP_MAP['low'];
                                    <p className="text-[10px] text-slate-400">Gestiona proyectos y crea tareas</p>
                                </div>
                                <ChevronRight size={16} className="text-slate-300 group-hover:translate-x-1 transition-transform" />
                            </div>
                        </Link>
                    </aside>
                </div>
                )}
            </main>
            </div>
        </WorkspaceLayout>
    );
}


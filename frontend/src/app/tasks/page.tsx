"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
    CheckCircle2, Circle, Clock, AlertCircle, Search,
    Filter, ChevronRight, MoreHorizontal, Zap, Bot,
    Flag, CalendarDays, Tag, Inbox, ListChecks, Star,
    SortAsc, ArrowUpDown, FolderOpen, Table2, LayoutGrid,
    KanbanSquare, BarChart3
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import TaskEditDrawer, { TaskDetail } from '@/components/ui/TaskEditDrawer';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Link from 'next/link';
import { ViewType } from '@/components/ViewSwitcher';
import UniversalTableView from '@/components/ui/UniversalTableView';

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
    const { token, isAuthenticated, user } = useAuth();
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
            addToast(`✓ Tarea completada! +${XP_MAP[updated.priority || 'low']} XP`, 'success');
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
                // Fast path: dedicated endpoint (if available)
                let allTasks: Task[] = [];
                try {
                    const direct = await apiFetch<any[]>('/projects/tasks/me', { token, cache: 'no-store' });
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
        addToast(`✓ ${task?.title?.slice(0, 36)}... completada! +${XP_MAP[task?.priority || 'low']} XP`, 'success');
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
        <div className="flex flex-col h-full bg-slate-50 dark:bg-[#111213] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Mi Centro de Tareas', icon: ListChecks }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['list', 'table', 'grid', 'kanban']}
                rightActions={
                    <SplitDropdownButton
                        onMainClick={() => {}}
                        onOptionClick={(type) => console.log('create:', type)}
                    />
                }
            />

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
                            const pc = PRIORITY_CONFIG[task.priority || 'low'];
                            return (
                                <motion.div key={task.id}
                                    initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.04 }}
                                    onClick={() => handleTaskSelect(task)}
                                    className="group bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-2xl p-5 shadow-sm hover:shadow-xl hover:border-blue-200 dark:hover:border-white/15 transition-all cursor-pointer">
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
                                            <Zap size={9} fill="currentColor" /> +{XP_MAP[task.priority || 'low']} XP
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
                                            const pc = PRIORITY_CONFIG[task.priority || 'low'];
                                            return (
                                                <motion.div key={task.id}
                                                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }}
                                                    onClick={() => handleTaskSelect(task)}
                                                    className="p-3 bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-xl shadow-sm hover:shadow-md hover:border-blue-200 dark:hover:border-white/20 transition-all cursor-pointer group">
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
                <div className="max-w-7xl mx-auto p-6 lg:p-10 grid grid-cols-1 lg:grid-cols-12 gap-8 pb-24">

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
                                    const pc = PRIORITY_CONFIG[task.priority || 'low'];
                                    const xp = XP_MAP[task.priority || 'low'];
                                    const isDone = completing === task.id;
                                    return (
                                        <motion.div
                                            key={task.id}
                                            layout
                                            initial={{ opacity: 0, y: 8 }}
                                            animate={{ opacity: isDone ? 0 : 1, y: 0, scale: isDone ? 0.96 : 1 }}
                                            exit={{ opacity: 0, x: 30, scale: 0.95 }}
                                            transition={{ duration: 0.25, delay: idx * 0.04 }}
                                            onClick={() => handleTaskSelect(task)}
                                            className="group bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-2xl p-4 flex items-center gap-4 shadow-sm hover:shadow-lg hover:border-blue-200 dark:hover:border-white/15 transition-all overflow-hidden relative cursor-pointer"
                                            style={{ borderLeft: `3px solid ${task.priority === 'urgent' ? '#f43f5e' : task.priority === 'high' ? '#f97316' : task.priority === 'medium' ? '#f59e0b' : '#94a3b8'}` }}
                                        >
                                            {/* Complete button */}
                                            <button
                                                onClick={(e) => { e.stopPropagation(); completeTask(task.id); }}
                                                className={clsx(
                                                    "size-9 rounded-2xl flex items-center justify-center transition-all shrink-0",
                                                    isDone
                                                        ? "bg-emerald-500 text-white scale-90"
                                                        : "bg-slate-50 dark:bg-white/5 text-slate-300 border border-slate-200 dark:border-white/10 hover:bg-emerald-50 hover:text-emerald-500 hover:border-emerald-200 active:scale-90"
                                                )}
                                            >
                                                {isDone ? <CheckCircle2 size={18} /> : <Circle size={18} />}
                                            </button>

                                            {/* Content */}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-[14px] font-bold text-slate-800 dark:text-white leading-tight truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                                    {task.title}
                                                </p>
                                                <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                                                    {task.project_title && (
                                                        <span className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                                                            <FolderOpen size={10} /> {task.project_title}
                                                        </span>
                                                    )}
                                                    {task.due_date && (
                                                        <span className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                                                            <CalendarDays size={10} /> {new Date(task.due_date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}
                                                        </span>
                                                    )}
                                                    <span className="text-[10px] font-bold text-slate-300 dark:text-white/20 uppercase">
                                                        {STATUS_LABEL[task.status] || task.status}
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Right: Priority + XP */}
                                            <div className="flex items-center gap-2 shrink-0">
                                                <span className={clsx("px-2.5 py-1 rounded-xl text-[9px] font-black uppercase tracking-widest", pc.color)}>
                                                    {pc.label}
                                                </span>
                                                <span className="flex items-center gap-1 px-2 py-1 bg-amber-50 dark:bg-amber-900/20 text-amber-600 rounded-xl text-[9px] font-black">
                                                    <Zap size={10} fill="currentColor" /> +{xp} XP
                                                </span>
                                                <button onClick={(e) => { e.stopPropagation(); handleTaskSelect(task); }} className="p-1.5 text-slate-200 dark:text-white/20 hover:text-blue-500 opacity-0 group-hover:opacity-100 transition-all" title="Ver detalle">
                                                    <ChevronRight size={16} />
                                                </button>
                                            </div>
                                        </motion.div>
                                    );
                                })}
                            </AnimatePresence>
                        )}
                    </div>

                    {/* ── RIGHT COLUMN ── */}
                    <aside className="lg:col-span-4 space-y-6">

                        {/* Stats */}
                        <div className="bg-gradient-to-br from-slate-900 to-[#1a1d28] border border-white/[0.06] rounded-2xl p-6 shadow-xl space-y-6">
                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Resumen de Hoy</h3>
                            <div className="grid grid-cols-3 gap-2">
                                {[
                                    { label: 'Pendientes', value: pending, color: 'text-blue-400' },
                                    { label: 'Vencen hoy', value: dueToday, color: 'text-amber-400' },
                                    { label: 'Urgentes', value: urgent, color: 'text-rose-400' },
                                ].map(s => (
                                    <div key={s.label} className="text-center p-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
                                        <p className={clsx("text-2xl font-black tracking-tighter", s.color)}>{s.value}</p>
                                        <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mt-1">{s.label}</p>
                                    </div>
                                ))}
                            </div>
                            <div className="pt-2 border-t border-white/[0.06]">
                                <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase mb-2">
                                    <span>Progreso</span>
                                    <span className="text-blue-400">{tasks.length > 0 ? Math.round(((30 - tasks.length) / 30) * 100) : 100}%</span>
                                </div>
                                <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${tasks.length > 0 ? Math.round(((30 - tasks.length) / 30) * 100) : 100}%` }}
                                        transition={{ duration: 1, delay: 0.3 }}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* MESH AI card */}
                        <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 dark:from-[#0f1117] dark:to-[#1a1b1e] rounded-[2.5rem] p-8 shadow-2xl space-y-5 border border-white/5">
                            <div className="absolute top-0 right-0 -mr-8 -mt-8 size-32 bg-blue-600/20 rounded-full blur-2xl" />
                            <div className="relative z-10 space-y-4">
                                <div className="flex items-center gap-3">
                                    <div className="size-9 rounded-2xl bg-blue-600/20 flex items-center justify-center">
                                        <Bot size={18} className="text-blue-400" />
                                    </div>
                                    <h4 className="text-[11px] font-black uppercase tracking-widest text-blue-400">Optimus Tasks</h4>
                                </div>
                                <p className="text-[13px] font-medium leading-relaxed italic text-slate-300">
                                    &ldquo;Tienes {urgent} tarea{urgent !== 1 ? 's' : ''} urgente{urgent !== 1 ? 's' : ''} hoy. ¿Quieres que organice tu agenda automáticamente?&rdquo;
                                </p>
                                <button className="flex items-center gap-2 text-[10px] font-black text-white uppercase tracking-widest hover:gap-3 transition-all group/btn">
                                    Organizar agenda <ChevronRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
                                </button>
                            </div>
                        </div>

                        {/* Quick link to projects */}
                        <Link href="/projects" className="block bg-white dark:bg-[#1a1b1e] border border-slate-200 dark:border-white/7 rounded-3xl p-5 hover:border-blue-300 dark:hover:border-white/20 transition-all group shadow-sm">
                            <div className="flex items-center gap-3">
                                <div className="size-10 rounded-2xl bg-blue-50 dark:bg-blue-600/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                                    <FolderOpen size={18} className="text-blue-500" />
                                </div>
                                <div className="flex-1">
                                    <p className="text-[13px] font-bold text-slate-800 dark:text-white">Ver todos los proyectos</p>
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
    );
}

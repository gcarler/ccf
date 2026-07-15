"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
    CheckSquare,
    Circle,
    Clock,
    Plus,
    Loader2,
    Send,
    Users,
    CheckCircle2,
    Flame,
    Heart,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import { useToast } from '@/context/ToastContext';
import { ApiError, apiFetch } from '@/lib/http';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import CrmShell from '@/components/crm/CrmShell';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import PersonaSelect from '@/components/ui/PersonaSelect';
import Skeleton from '@/components/ui/Skeleton';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';
import { ConsolidationTask } from '@/types/crm';

const STATUS_PROGRESS: Record<string, number> = { urgent: 15, pending: 35, in_progress: 70, done: 100 };

// ─── Constants ───────────────────────────────────────────
const STATUS_COLUMNS = [
    { key: 'urgent', label: 'Urgente', icon: Flame, color: 'rose', bg: 'bg-rose-50 dark:bg-rose-900/10', border: 'border-rose-200 dark:border-rose-800/30', dot: 'bg-rose-500' },
    { key: 'pending', label: 'Pendiente', icon: Circle, color: 'slate', bg: 'bg-[hsl(var(--surface-1))] dark:bg-white/[0.02]', border: 'border-[hsl(var(--border))] dark:border-white/10', dot: 'bg-[hsl(var(--surface-2))]' },
    { key: 'in_progress', label: 'En Seguimiento', icon: Clock, color: 'blue', bg: 'bg-blue-50 dark:bg-blue-900/10', border: 'border-blue-200 dark:border-blue-800/30', dot: 'bg-[hsl(var(--primary))]' },
    { key: 'done', label: 'Completada', icon: CheckCircle2, color: 'emerald', bg: 'bg-emerald-50 dark:bg-emerald-900/10', border: 'border-emerald-200 dark:border-emerald-800/30', dot: 'bg-emerald-500' },
];

const CATEGORIES = ['Consolidación', 'Seguimiento', 'Oración', 'Administrativa', 'Otro'];

const PRIORITY_STYLES: Record<string, string> = {
    high: 'bg-rose-50 text-rose-600 dark:bg-rose-900/20',
    medium: 'bg-amber-50 text-amber-600 dark:bg-amber-900/20',
    low: 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:bg-white/5',
};

import { TaskCard } from '@/components/crm/ui';

// ─── Main ────────────────────────────────────────────────
export default function CrmTasksPage() {
    const router = useRouter();
    const { token } = useAuth();
    const { canEditCrm } = useCrmAccess();
    const { addToast } = useToast();
    const [tasks, setTasks] = useState<ConsolidationTask[]>([]);
    const [loading, setLoading] = useState(true);
    const [tasksError, setTasksError] = useState<string | null>(null);
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_tasks_view', 'board'));
    const [selectedTask, setSelectedTask] = useState<ConsolidationTask | null>(null);
    const [isDetailOpen, setIsDetailOpen] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('crm_tasks_wiki_notes', {
        title: 'Wiki de tareas CRM',
    });
    const [newTask, setNewTask] = useState({
        title: '', description: '', category: 'Consolidación',
        priority: 'medium', status: 'pending', due_date: '', persona_id: ''
    });

    const fetchTasks = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        setLoading(true);
        setTasksError(null);
        try {
            const data = await apiFetch<ConsolidationTask[]>('/crm/tasks', { token, cache: 'no-store' });
            setTasks(Array.isArray(data) ? data : []);
        } catch (err) {
            setTasks([]);
            const message = err instanceof ApiError
                ? ((err.detail as any)?.detail || (err.detail as any)?.message || (typeof err.detail === 'string' ? err.detail : 'Error al cargar tareas'))
                : 'Error al cargar tareas';
            setTasksError(message);
            addToast(message, 'error');
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        fetchTasks();
    }, [fetchTasks]);


    const updateTaskStatus = useCallback(async (id: string, status: string) => {
        if (!canEditCrm) return;
        setTasks(prev => prev.map(t => t.id === id ? { ...t, status: status as any } : t));
        try {
            await apiFetch(`/crm/tasks/${id}`, { method: 'PATCH', token, body: { status } });
        } catch {
            addToast('Error al actualizar estado', 'error');
        }
    }, [token, addToast, canEditCrm]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newTask.title.trim()) return;
        setIsSaving(true);
        try {
            const created = await apiFetch<ConsolidationTask>('/crm/tasks', { method: 'POST', token, body: newTask });
            setTasks(prev => [created, ...prev]);
            addToast('Tarea creada', 'success');
            setIsCreateOpen(false);
            setNewTask({ title: '', description: '', category: 'Consolidación', priority: 'medium', status: 'pending', due_date: '', persona_id: '' });
        } catch {
            addToast('Error al crear tarea', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    useRegisterCommands('crm-tasks', canEditCrm ? [
        { id: 'crm-task-new', label: 'Nueva tarea de consolidación', group: 'Tareas', action: () => setIsCreateOpen(true) },
    ] : []);

    const tasksByStatus = useMemo(() => {
        const map: Record<string, ConsolidationTask[]> = {};
        STATUS_COLUMNS.forEach(c => { map[c.key] = tasks.filter(t => t.status === c.key); });
        return map;
    }, [tasks]);

    const dueBuckets = useMemo(() => {
        const map: Record<string, ConsolidationTask[]> = {};
        for (const task of tasks) {
            if (!task.due_date) continue;
            const date = new Date(task.due_date);
            const key = date.toISOString().slice(0, 10);
            if (!map[key]) map[key] = [];
            map[key].push(task);
        }
        return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
    }, [tasks]);

    if (loading) return (
        <CrmShell breadcrumbs={[{ label: 'Consolidación', icon: Heart }, { label: 'Tareas de Consolidación', icon: CheckSquare }]}>
            <div className="p-4 space-y-3">
                {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-8 w-full rounded-lg" />)}
            </div>
        </CrmShell>
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Heart },
                { label: 'Consolidación', icon: Users },
                { label: 'Tareas de Consolidación', icon: CheckSquare }
            ]}
            viewOptions={['board', 'list', 'table', 'grid', 'kanban', 'calendar', 'gantt', 'wiki']}
            viewType={viewType}
            onViewChange={setViewType}
            rightActions={canEditCrm ? (
                <button
                    onClick={() => setIsCreateOpen(true)}
                    className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all"
                >
                    <Plus size={14} /> Nueva Tarea
                </button>
            ) : undefined}
        >
            {tasksError && (
                <div className="mx-4 mt-4 rounded-lg border border-amber-300/60 bg-amber-50 dark:bg-amber-500/10 dark:border-amber-500/30 p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <div className="min-w-0">
                        <p className="text-[11px] font-bold uppercase tracking-wide text-amber-800 dark:text-amber-200">
                            No se pudo cargar el tablero de tareas
                        </p>
                        <p className="text-sm text-amber-900/80 dark:text-amber-100/80 mt-1 break-words">
                            {tasksError}
                        </p>
                    </div>
                    <button
                        onClick={fetchTasks}
                        className="shrink-0 px-3 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:opacity-90 transition-all"
                    >
                        Reintentar
                    </button>
                </div>
            )}

            {/* ─── Stats strip ─── */}
            <div className="px-4 pt-4 pb-0 flex items-center gap-3">
                {STATUS_COLUMNS.map(col => (
                    <div key={col.key} className={clsx("flex items-center gap-2 px-4 py-2 rounded-md border text-[11px] font-bold", col.bg, col.border)}>
                        <div className={clsx("size-2 rounded-full", col.dot)} />
                        <span className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{col.label}</span>
                        <span className="font-bold text-[hsl(var(--text-primary))] dark:text-white">{tasksByStatus[col.key]?.length ?? 0}</span>
                    </div>
                ))}
            </div>

            {/* ─── Kanban View ─── */}
            <AnimatePresence mode="wait">
                {(viewType === 'board' || viewType === 'kanban' || viewType === 'grid') && (
                    <motion.div
                        key="kanban"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="flex-1 overflow-x-auto overflow-y-hidden"
                    >
                        <div className="flex gap-4 p-4 h-full min-w-0" style={{ minWidth: 'max-content' }}>
                            {STATUS_COLUMNS.map(col => {
                                const colTasks = tasksByStatus[col.key] ?? [];
                                const Icon = col.icon;
                                return (
                                    <div key={col.key} className={clsx("flex flex-col gap-3 w-[300px] shrink-0 rounded-md border p-4", col.bg, col.border)}>
                                        {/* Column header */}
                                        <div className="flex items-center justify-between shrink-0">
                                            <div className="flex items-center gap-2">
                                                <div className={clsx("size-2 rounded-full", col.dot)} />
                                                <span className={`text-[11px] font-bold uppercase tracking-wide text-${col.color}-600 dark:text-${col.color}-400`}>
                                                    {col.label}
                                                </span>
                                                <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-full px-2 py-0.5 border border-[hsl(var(--border))] dark:border-white/10">
                                                    {colTasks.length}
                                                </span>
                                            </div>
                                            {canEditCrm && <button onClick={() => setIsCreateOpen(true)} className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/5 transition-all">
                                                <Plus size={14} />
                                            </button>}
                                        </div>
                                        {/* Cards */}
                                        <div className="flex-1 overflow-y-auto space-y-2 scrollbar-thin min-h-[200px]">
                                            <AnimatePresence>
                                                {colTasks.map(task => (
                                                <TaskCard
                                                    key={task.id}
                                                    task={task}
                                                    onStatusChange={updateTaskStatus}
                                                    allowEditing={canEditCrm}
                                                />
                                                ))}
                                            </AnimatePresence>
                                            {colTasks.length === 0 && (
                                                <div className="py-1.5 flex flex-col items-center justify-center text-center opacity-40">
                                                    <Icon size={24} strokeWidth={1} className="mb-2 text-[hsl(var(--text-secondary))]" />
                                                    <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase">Sin tareas</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </motion.div>
                )}

                {/* ─── List View ─── */}
                {viewType === 'list' && (
                    <motion.div
                        key="list"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="flex-1 overflow-y-auto p-4 space-y-2"
                    >
                        {!tasksError && tasks.length === 0 ? (
                            <div className="py-1.5 flex flex-col items-center gap-4">
                                <CheckSquare size={48} strokeWidth={1} className="text-[hsl(var(--text-secondary))]" />
                                <p className="text-[hsl(var(--text-secondary))] font-bold uppercase text-sm">Sin tareas registradas</p>
                                {canEditCrm && (
                                    <button onClick={() => setIsCreateOpen(true)} className="px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-xs font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20">
                                        Crear primera tarea
                                    </button>
                                )}
                            </div>
                        ) : tasks.map(task => (
                            <div
                                key={task.id}
                                onClick={() => router.push(`/plataforma/crm/tasks/${task.id}`)}
                                className="flex items-center gap-4 p-4 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 hover:border-blue-300 dark:hover:border-blue-700 transition-all cursor-pointer group"
                            >
                                {canEditCrm ? (
                                    <button
                                        onClick={e => { e.stopPropagation(); updateTaskStatus(task.id, task.status === 'done' ? 'pending' : 'done'); }}
                                        className={clsx(
                                            "size-5 rounded-full border-2 flex-shrink-0 transition-all flex items-center justify-center",
                                            task.status === 'done' ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-[hsl(var(--border))] group-hover:border-blue-400'
                                        )}
                                    >
                                        {task.status === 'done' && <CheckCircle2 size={12} strokeWidth={3} />}
                                    </button>
                                ) : (
                                    <div className={clsx(
                                        "size-5 rounded-full border-2 flex-shrink-0",
                                        task.status === 'done' ? 'bg-emerald-500 border-emerald-500' : 'border-[hsl(var(--border))]'
                                    )} />
                                )}
                                <div className="flex-1">
                                    <p className={clsx("text-sm font-bold", task.status === 'done' && "line-through text-[hsl(var(--text-secondary))]")}>{task.title}</p>
                                    {task.persona_name && <p className="text-[10px] text-[hsl(var(--text-secondary))] font-bold">{task.persona_name}</p>}
                                </div>
                                <div className="flex items-center gap-2 text-[10px] shrink-0">
                                    <span className={clsx("px-2 py-0.5 rounded-full font-bold uppercase", PRIORITY_STYLES[task.priority])}>{task.priority}</span>
                                    {task.due_date && <span className="text-[hsl(var(--text-secondary))] font-bold">{new Date(task.due_date).toLocaleDateString()}</span>}
                                </div>
                            </div>
                        ))}
                    </motion.div>
                )}

                {/* ─── Table View ─── */}
                {viewType === 'table' && (
                    <motion.div
                        key="table"
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="flex-1 overflow-auto p-4"
                    >
                        <table className="w-full text-left">
                            <thead>
                                <tr className="border-b border-[hsl(var(--border))] dark:border-white/10">
                                    {['Tarea', 'Persona', 'Categoría', 'Prioridad', 'Estado', 'Vence'].map(h => (
                                        <th key={h} className="pb-3 px-3 text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {tasks.map(task => {
                                    const col = STATUS_COLUMNS.find(c => c.key === task.status);
                                    return (
                                        <tr
                                            key={task.id}
                                            onClick={() => router.push(`/plataforma/crm/tasks/${task.id}`)}
                                            className="border-b border-[hsl(var(--border))] dark:border-white/5 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] cursor-pointer transition-colors"
                                        >
                                            <td className="py-1.5 px-3 text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white max-w-[250px] truncate">{task.title}</td>
                                            <td className="py-1.5 px-3 text-[11px] text-[hsl(var(--text-secondary))]">{task.persona_name || '—'}</td>
                                            <td className="py-1.5 px-3 text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase">{task.category}</td>
                                            <td className="py-1.5 px-3">
                                                <span className={clsx("px-2 py-0.5 rounded text-[9px] font-bold uppercase", PRIORITY_STYLES[task.priority])}>{task.priority}</span>
                                            </td>
                                            <td className="py-1.5 px-3">
                                                <div className="flex items-center gap-1.5">
                                                    <div className={clsx("size-1.5 rounded-full", col?.dot)} />
                                                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase">{col?.label}</span>
                                                </div>
                                            </td>
                                            <td className="py-1.5 px-3 text-[11px] text-[hsl(var(--text-secondary))]">{task.due_date ? new Date(task.due_date).toLocaleDateString() : '—'}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                        {!tasksError && tasks.length === 0 && (
                            <div className="py-1.5 text-center text-[hsl(var(--text-secondary))] font-bold uppercase text-sm">Sin tareas</div>
                        )}
                    </motion.div>
                )}

                {viewType === 'calendar' && (
                    <motion.div key="calendar" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 overflow-y-auto p-4 space-y-4">
                        {dueBuckets.length === 0 ? (
                            <div className="py-1.5 text-center text-[hsl(var(--text-secondary))] font-bold uppercase text-sm">Sin tareas con fecha</div>
                        ) : dueBuckets.map(([isoDate, bucket]) => (
                            <div key={isoDate} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4">
                                <p className="mb-3 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{new Date(`${isoDate}T00:00:00`).toLocaleDateString()}</p>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {bucket.map(task => (
                                        <button key={task.id} onClick={() => { setSelectedTask(task); setIsDetailOpen(true); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-left hover:border-blue-300 dark:hover:border-blue-700 transition-all">
                                            <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{task.title}</p>
                                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">{task.persona_name || 'Sin persona asignado'}</p>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </motion.div>
                )}

                {viewType === 'gantt' && (
                    <motion.div key="gantt" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 overflow-y-auto p-4">
                        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                            <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Timeline de avance</p>
                            {tasks.map(task => (
                                <div key={task.id} className="space-y-1">
                                    <div className="flex items-center justify-between text-[11px]">
                                        <span className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{task.title}</span>
                                        <span className="font-bold text-[hsl(var(--text-secondary))]">{STATUS_PROGRESS[task.status] ?? 0}%</span>
                                    </div>
                                    <div className="h-2 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10 overflow-hidden">
                                        <div className="h-full bg-[hsl(var(--primary))]" style={{ width: `${STATUS_PROGRESS[task.status] ?? 0}%` }} />
                                    </div>
                                </div>
                            ))}
                            {!tasksError && tasks.length === 0 && <div className="py-1.5 text-center text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Sin tareas</div>}
                        </div>
                    </motion.div>
                )}

                {viewType === 'wiki' && (
                    <motion.div key="wiki" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 overflow-y-auto p-4">
                        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                            <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Wiki de tareas de consolidación</p>
                            <textarea
                                value={wikiNotes}
                                onChange={(e) => setWikiNotes(e.target.value)}
                                placeholder="Define criterios de prioridad, protocolos de seguimiento y acuerdos del equipo..."
                                className="w-full min-h-[360px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 p-4 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20"
                            />
                        </div>
                    </motion.div>
                )}

                {!['board', 'kanban', 'grid', 'list', 'table', 'calendar', 'gantt', 'wiki'].includes(viewType) && (
                    <motion.div key="pending-view" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4">
                        <CrmViewPlaceholder moduleName="Tareas de consolidación" viewType={viewType} />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ─── Drawer: Detalle ─── */}
            <WorkspaceDrawer
                isOpen={isDetailOpen}
                onClose={() => setIsDetailOpen(false)}
                title={selectedTask?.title ?? 'Detalle de Tarea'}
                subtitle={`${String(selectedTask?.category ?? 'general').toUpperCase()} · ${String(selectedTask?.priority ?? 'normal').toUpperCase()}`}
                actions={
                    <>
                        <button onClick={() => setIsDetailOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))]">Cerrar</button>
                        <button
                            onClick={() => selectedTask && updateTaskStatus(selectedTask.id, selectedTask.status === 'done' ? 'pending' : 'done')}
                            className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-[11px] font-bold shadow-lg shadow-emerald-500/20"
                        >
                            {selectedTask?.status === 'done' ? 'Reabrir' : 'Marcar Completada'}
                        </button>
                    </>
                }
            >
                {selectedTask && (
                    <div className="space-y-3">
                        {selectedTask.description && (
                            <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-lg border border-[hsl(var(--border))] dark:border-white/5">
                                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">{selectedTask.description}</p>
                            </div>
                        )}
                        <div className="grid grid-cols-2 gap-3">
                            {[
                                { label: 'Persona', val: selectedTask.persona_name || '—' },
                                { label: 'Prioridad', val: String(selectedTask.priority ?? 'normal').toUpperCase() },
                                { label: 'Categoría', val: selectedTask.category },
                                { label: 'Vence', val: selectedTask.due_date ? new Date(selectedTask.due_date).toLocaleDateString() : '—' },
                                { label: 'Creada', val: new Date(selectedTask.created_at).toLocaleDateString() },
                            ].map(item => (
                                <div key={item.label} className="p-3 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-md border border-[hsl(var(--border))] dark:border-white/5">
                                    <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-0.5">{item.label}</p>
                                    <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{item.val}</p>
                                </div>
                            ))}
                        </div>
                        <div className="space-y-2">
                            <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Cambiar estado</p>
                            <div className="flex flex-wrap gap-2">
                                {STATUS_COLUMNS.map(col => (
                                    <button
                                        key={col.key}
                                        onClick={() => updateTaskStatus(selectedTask.id, col.key)}
                                        className={clsx(
                                            "flex items-center gap-1.5 px-3 py-2 rounded-md text-[10px] font-bold uppercase tracking-wide transition-all border",
                                            selectedTask.status === col.key
                                                ? `${col.bg} ${col.border} text-${col.color}-600 dark:text-${col.color}-400`
                                                : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 border-transparent text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))]'
                                        )}
                                    >
                                        <div className={clsx("size-1.5 rounded-full", col.dot)} />
                                        {col.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </WorkspaceDrawer>

            {/* ─── Drawer: Crear Tarea ─── */}
            <WorkspaceDrawer
                isOpen={isCreateOpen}
                onClose={() => setIsCreateOpen(false)}
                title="Nueva Tarea de Consolidación"
                subtitle="Seguimiento y gestión ministerial"
                actions={
                    <>
                        <button type="button" onClick={() => setIsCreateOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                            Cancelar
                        </button>
                        <button
                            form="create-task-form"
                            type="submit"
                            disabled={isSaving}
                            className="px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2"
                        >
                            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            Crear Tarea
                        </button>
                    </>
                }
            >
                <form id="create-task-form" onSubmit={handleCreate} className="space-y-2">
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Título *</label>
                        <input
                            required
                            value={newTask.title}
                            onChange={e => setNewTask({ ...newTask, title: e.target.value })}
                            placeholder="Ej: Visitar a hermano Juan"
                            className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Descripción</label>
                        <textarea
                            value={newTask.description}
                            onChange={e => setNewTask({ ...newTask, description: e.target.value })}
                            placeholder="Detalles adicionales..."
                            rows={3}
                            className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white resize-none"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Categoría</label>
                            <select
                                value={newTask.category}
                                onChange={e => setNewTask({ ...newTask, category: e.target.value })}
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white appearance-none"
                            >
                                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Prioridad</label>
                            <select
                                value={newTask.priority}
                                onChange={e => setNewTask({ ...newTask, priority: e.target.value })}
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white appearance-none"
                            >
                                <option value="low">Baja</option>
                                <option value="medium">Media</option>
                                <option value="high">Alta</option>
                            </select>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Estado inicial</label>
                            <select
                                value={newTask.status}
                                onChange={e => setNewTask({ ...newTask, status: e.target.value })}
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white appearance-none"
                            >
                                {STATUS_COLUMNS.map(c => <option key={c.key} value={c.key}>{c.label}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Fecha límite</label>
                            <input
                                type="date"
                                value={newTask.due_date}
                                onChange={e => setNewTask({ ...newTask, due_date: e.target.value })}
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                            />
                        </div>
                    </div>
                    {true && (
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Persona asociado</label>
                            <PersonaSelect
                                value={newTask.persona_id || null}
                                onChange={(id) => setNewTask({ ...newTask, persona_id: id ?? '' })}
                                placeholder="Sin asignar"
                            />
                        </div>
                    )}
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}

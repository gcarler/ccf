"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import {
    LayoutDashboard,
    ChevronRight,
    Sparkles,
    Calendar,
    Plus,
    Trash2,
    Edit3,
    CheckCircle2,
    Circle,
    Clock,
    AlertTriangle,
    PencilRuler
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import TaskCreationDrawer from '@/components/projects/TaskCreationDrawer';
import TaskDetailPanel from '@/components/projects/TaskDetailPanel';
import ProjectActivityFeed from '@/components/projects/ProjectActivityFeed';
import ProjectWikiEditor from '@/components/projects/ProjectWikiEditor';
import ProjectWhiteboard from '@/components/projects/ProjectWhiteboard';
import ProjectChatPanel from '@/components/projects/ProjectChatPanel';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { DSMetric } from '@/design/components/DSMetric';
import TaskTableView from '@/components/projects/TaskTableView';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectActivityItem, ProjectMilestoneRecord, ProjectTaskRecord } from '@/types/projects';
import type { PhaseDef } from '@/components/projects/ProjectKanbanBoard';
import { PhaseManagerDrawer } from '@/components/projects/PhaseManagerDrawer';
import { toast } from 'sonner';
import UserSelect from '@/components/ui/UserSelect';

const PROJECT_DETAIL_VIEWS: ViewType[] = ['dashboard', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki', 'chat'];

export default function ProjectDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();

    const [project, setProject] = useState<any>(null);
    const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
    const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [showTaskModal, setShowTaskModal] = useState(false);
    const [editingProject, setEditingProject] = useState(false);
    const [editTitle, setEditTitle] = useState('');
    const [editDescription, setEditDescription] = useState('');
    const [editStatus, setEditStatus] = useState('');
    const [editOwnerId, setEditOwnerId] = useState<number | null>(null);
    const [viewType, setViewType] = useState<ViewType>('dashboard');
    const [selectedTask, setSelectedTask] = useState<ProjectTaskRecord | null>(null);
    const [whiteboardOpen, setWhiteboardOpen] = useState(false);
    const [milestoneTitle, setMilestoneTitle] = useState('');
    const [milestoneDate, setMilestoneDate] = useState('');
    const [creatingMilestone, setCreatingMilestone] = useState(false);
    const [updatingMilestoneId, setUpdatingMilestoneId] = useState<number | null>(null);
    const [editingMilestoneId, setEditingMilestoneId] = useState<number | null>(null);
    const [milestoneDraftTitle, setMilestoneDraftTitle] = useState('');
    const [milestoneDraftDate, setMilestoneDraftDate] = useState('');
    const [phases, setPhases] = useState<PhaseDef[]>([]);
    const [showPhaseManager, setShowPhaseManager] = useState(false);

    const loadProject = useCallback(async () => {
        if (!token || !id) return;
        try {
            setLoading(true);
            const [projData, tasksData, activityRows, phasesData] = await Promise.all([
                apiFetch<any>(`/projects/${id}`, { token }),
                apiFetch<ProjectTaskRecord[]>(`/projects/${id}/tasks`, { token }).catch(() => []),
                apiFetch<ProjectActivityItem[]>(`/projects/activities?project_id=${id}&limit=20`, { token }).catch(() => []),
                apiFetch<PhaseDef[]>(`/projects/${id}/phases`, { token }).catch(() => []),
            ]);
            setProject(projData);
            setTasks(Array.isArray(tasksData) ? tasksData : []);
            setActivities(Array.isArray(activityRows) ? activityRows : []);
            if (Array.isArray(phasesData) && phasesData.length > 0) setPhases(phasesData);
            window.dispatchEvent(new CustomEvent('project-updated', { detail: { projectId: id } }));
        } catch (err) {
            toast.error('Error al cargar detalle del proyecto');
        } finally {
            setLoading(false);
        }
    }, [id, token]);

    useEffect(() => {
        loadProject();
    }, [loadProject]);

    useEffect(() => {
        const taskId = Number(searchParams?.get('task'));
        if (!taskId || tasks.length === 0) return;
        const task = tasks.find((row) => row.id === taskId);
        if (task) setSelectedTask(task);
    }, [searchParams, tasks]);

    const handleCreateTask = async (data: { title: string; description: string; priority: string; status: string; assignee_id?: number | null }) => {
        if (!token || !id) return;
        try {
            await apiFetch(`/projects/${id}/tasks`, {
                method: 'POST',
                token,
                body: data,
            });
            toast.success('Tarea creada');
            setShowTaskModal(false);
            loadProject();
        } catch (err) {
            toast.error('Error al crear tarea');
        }
    };

    const handleMoveTask = async (task: any) => {
        const currentIndex = phases.findIndex(p => p.slug === (task.status || 'todo'));
        const nextStatus = phases[Math.min(currentIndex + 1, phases.length - 1)]?.slug;
        if (!nextStatus || nextStatus === task.status) return;
        try {
            await apiFetch(`/projects/tasks/${task.id}`, {
                method: 'PATCH',
                token,
                body: { status: nextStatus },
            });
            const nextPhase = phases.find(p => p.slug === nextStatus);
            toast.success(`Tarea → ${nextPhase?.name || nextStatus}`);
            loadProject();
        } catch (err) {
            toast.error('Error al actualizar tarea');
        }
    };

    const handleDeleteTask = async (taskId: number) => {
        if (!token || !id) return;
        try {
            await apiFetch(`/projects/${id}/tasks/${taskId}`, { method: 'DELETE', token });
            toast.success('Tarea eliminada');
            loadProject();
        } catch (err) {
            toast.error('Error al eliminar tarea');
        }
    };

    const handleOpenTask = (task: ProjectTaskRecord) => {
        setSelectedTask(task);
        router.replace(`/plataforma/projects/${id}?task=${task.id}`);
    };

    const handleCloseTask = () => {
        setSelectedTask(null);
        router.replace(`/plataforma/projects/${id}`);
    };

    const handleTaskUpdated = (updated: ProjectTaskRecord) => {
        setTasks((prev) => prev.map((task) => (task.id === updated.id ? { ...task, ...updated } : task)));
        setSelectedTask((prev) => (prev?.id === updated.id ? { ...prev, ...updated } : prev));
        loadProject();
    };

    const handleUpdateProject = async () => {
        if (!token || !id) return;
        try {
            await apiFetch(`/projects/${id}`, {
                method: 'PATCH',
                token,
                body: { title: editTitle, description: editDescription, status: editStatus, owner_id: editOwnerId },
            });
            toast.success('Proyecto actualizado');
            setEditingProject(false);
            loadProject();
        } catch (err) {
            toast.error('Error al actualizar proyecto');
        }
    };

    const handleDeleteProject = async () => {
        if (!token || !id || !confirm('¿Eliminar este proyecto y todas sus tareas?')) return;
        try {
            await apiFetch(`/projects/${id}`, { method: 'DELETE', token });
            toast.success('Proyecto eliminado');
            router.push('/plataforma/projects');
        } catch (err) {
            toast.error('Error al eliminar proyecto');
        }
    };

    const handleCreateMilestone = async () => {
        if (!token || !id || !milestoneTitle.trim()) return;
        setCreatingMilestone(true);
        try {
            await apiFetch(`/projects/${id}/milestones`, {
                method: 'POST',
                token,
                body: {
                    title: milestoneTitle.trim(),
                    target_date: milestoneDate ? new Date(milestoneDate).toISOString() : null,
                },
            });
            toast.success('Hito creado');
            setMilestoneTitle('');
            setMilestoneDate('');
            loadProject();
        } catch {
            toast.error('Error al crear hito');
        } finally {
            setCreatingMilestone(false);
        }
    };

    const handleToggleMilestone = async (milestone: ProjectMilestoneRecord) => {
        if (!token || !id) return;
        setUpdatingMilestoneId(milestone.id);
        try {
            await apiFetch(`/projects/${id}/milestones/${milestone.id}`, {
                method: 'PATCH',
                token,
                body: { is_completed: !milestone.is_completed },
            });
            toast.success(!milestone.is_completed ? 'Hito completado' : 'Hito reabierto');
            loadProject();
        } catch {
            toast.error('Error al actualizar hito');
        } finally {
            setUpdatingMilestoneId(null);
        }
    };

    const startEditingMilestone = (milestone: ProjectMilestoneRecord) => {
        setEditingMilestoneId(milestone.id);
        setMilestoneDraftTitle(milestone.title);
        setMilestoneDraftDate(milestone.target_date ? milestone.target_date.slice(0, 10) : '');
    };

    const handleUpdateMilestone = async (milestoneId: number) => {
        if (!token || !id || !milestoneDraftTitle.trim()) return;
        setUpdatingMilestoneId(milestoneId);
        try {
            await apiFetch(`/projects/${id}/milestones/${milestoneId}`, {
                method: 'PATCH',
                token,
                body: {
                    title: milestoneDraftTitle.trim(),
                    target_date: milestoneDraftDate ? new Date(milestoneDraftDate).toISOString() : null,
                },
            });
            toast.success('Hito actualizado');
            setEditingMilestoneId(null);
            loadProject();
        } catch {
            toast.error('Error al actualizar hito');
        } finally {
            setUpdatingMilestoneId(null);
        }
    };

    const startEditing = () => {
        setEditTitle(project?.title || '');
        setEditDescription(project?.description || '');
        setEditStatus(project?.status || 'planning');
        setEditOwnerId(project?.owner_id ?? null);
        setEditingProject(true);
    };

    if (loading) return <div className="p-4 text-center animate-pulse font-bold text-slate-400">Recuperando ecosistema de trabajo...</div>;

    const doneCount = tasks.filter(t => t.status === 'completed').length;
    const progressPercent = tasks.length > 0 ? Math.round((doneCount / tasks.length) * 100) : 0;
    const taskCalendarEvents = tasks.map((task) => ({
        id: task.id,
        title: task.title,
        date: (task.due_date || task.start_date || new Date().toISOString()).slice(0, 10),
        color: task.status === 'completed' ? 'emerald' as const : task.priority === 'urgent' ? 'rose' as const : task.status === 'review' ? 'amber' as const : 'blue' as const,
        location: task.description || undefined,
    }));
    const taskGanttItems = tasks.map((task) => ({
        id: task.id,
        title: task.title,
        subtitle: phases.find(p => p.slug === task.status)?.name || task.status,
        start_date: (task.start_date || task.created_at || new Date().toISOString()).slice(0, 10),
        end_date: (task.due_date || task.start_date || task.created_at || new Date().toISOString()).slice(0, 10),
        color: task.status === 'completed' ? 'emerald' as const : task.priority === 'urgent' ? 'rose' as const : 'blue' as const,
        progress: task.status === 'completed' ? 100 : task.status === 'review' ? 75 : task.status === 'in_progress' ? 45 : 10,
    }));

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Proyectos', icon: LayoutDashboard, href: '/plataforma/projects' },
                    { label: project?.title || 'Cargando...', icon: Calendar },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={PROJECT_DETAIL_VIEWS}
                rightActions={
                    <div className="flex items-center gap-2">
                        <button onClick={() => setShowTaskModal(true)} className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2">
                            <Plus size={14} /> Nueva Tarea
                        </button>
                        <button onClick={() => setWhiteboardOpen(true)} className="px-3 py-1.5 bg-slate-900 text-white rounded-lg text-[10px] font-bold uppercase tracking-wide hover:scale-105 transition-all flex items-center gap-2 dark:bg-[hsl(var(--bg-primary))] dark:text-slate-900">
                            <PencilRuler size={14} /> Pizarra
                        </button>
                        {phases.length > 0 && (
                            <button onClick={() => setShowPhaseManager(true)} className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold uppercase tracking-wide hover:scale-105 transition-all flex items-center gap-2">
                                <Edit3 size={14} /> Fases
                            </button>
                        )}
                        <button onClick={startEditing} className="px-3 py-1.5 bg-amber-500 text-white rounded-lg text-[10px] font-bold uppercase tracking-wide hover:scale-105 transition-all flex items-center gap-2">
                            <Edit3 size={14} /> Editar
                        </button>
                        <button onClick={handleDeleteProject} className="px-3 py-1.5 bg-rose-500 text-white rounded-lg text-[10px] font-bold uppercase tracking-wide hover:scale-105 transition-all flex items-center gap-2">
                            <Trash2 size={14} /> Eliminar
                        </button>
                    </div>
                }
            />

            <div className="flex min-h-0 flex-1 overflow-hidden">
            <main className="flex-1 overflow-y-auto p-4 space-y-3">
                {editingProject ? (
                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg p-3 border border-slate-200 dark:border-white/10 space-y-3">
                        <h3 className="text-sm font-bold uppercase tracking-wide text-slate-600">Editar Proyecto</h3>
                        <input value={editTitle} onChange={e => setEditTitle(e.target.value)} className="w-full p-2 rounded-md border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm font-medium" placeholder="Título del proyecto" />
                        <textarea value={editDescription} onChange={e => setEditDescription(e.target.value)} rows={3} className="w-full p-2 rounded-md border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm" placeholder="Descripción" />
                        <select value={editStatus} onChange={e => setEditStatus(e.target.value)} className="w-full p-2 rounded-md border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-sm font-medium">
                            <option value="planning">Planificación</option>
                            <option value="active">En Marcha</option>
                            <option value="on_hold">En Pausa</option>
                            <option value="completed">Alcanzado</option>
                            <option value="archived">Archivado</option>
                        </select>
                        <UserSelect
                            value={editOwnerId}
                            onChange={setEditOwnerId}
                            placeholder="Responsable del proyecto"
                        />
                        <div className="flex gap-2">
                            <button onClick={handleUpdateProject} className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-xs font-bold uppercase tracking-wide hover:scale-105 transition-all">Guardar Cambios</button>
                            <button onClick={() => setEditingProject(false)} className="px-3 py-1.5 bg-slate-200 dark:bg-white/10 rounded-md text-xs font-bold uppercase tracking-wide hover:scale-105 transition-all">Cancelar</button>
                        </div>
                    </div>
                ) : (
                    <>
                        {viewType === 'dashboard' && (
                            <div className="space-y-3">
                                <header className="space-y-2">
                                    <div className="flex items-center gap-3">
                                        <DSBadge tone={project?.status === 'active' ? 'blue' : project?.status === 'completed' ? 'emerald' : 'amber'} label={project?.status?.toUpperCase() || 'PROYECTO'} />
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{progressPercent}% completado</span>
                                    </div>
                                    <h1 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight uppercase">
                                        {project?.title}
                                    </h1>
                                    {project?.description && (
                                        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-2xl">{project.description}</p>
                                    )}
                                </header>

                                <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    <DSMetric label="Actividades" value={String(tasks.length)} trend="Total" tone="blue" />
                                    <DSMetric label="Logradas" value={String(doneCount)} trend={`${progressPercent}%`} tone="emerald" />
                                    <DSMetric label={phases.find(p => p.slug === 'review')?.name || 'En Seguimiento'} value={String(tasks.filter(t => t.status === 'review').length)} trend="Consolidación" tone="amber" />
                                    <DSMetric label="Por Hacer" value={String(tasks.filter(t => t.status !== 'completed').length)} trend="Pendientes" tone="blue" />
                                </section>

                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                                    <aside className="space-y-3 lg:col-span-1">
                                        <div className="p-3 bg-blue-50/50 dark:bg-slate-900 border border-blue-100 dark:border-white/5 rounded-lg shadow-sm dark:shadow-xl space-y-2">
                                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">
                                                <Sparkles size={14} /> Asistente Ministerial
                                            </div>
                                            <p className="text-[11px] font-medium leading-relaxed italic text-slate-700 dark:text-slate-300">
                                                Basado en el ritmo actual, la campaña va por buen camino. Te sugiero revisar las actividades en consolidación para evitar bloqueos.
                                            </p>
                                        </div>


                                        <DSCard>
                                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-2">Hitos</h3>
                                            <div className="space-y-2">
                                                {project?.milestones?.map((m: ProjectMilestoneRecord) => (
                                                    <div key={m.id} className="rounded-md bg-slate-50 p-2 dark:bg-white/5">
                                                        {editingMilestoneId === m.id ? (
                                                            <div className="space-y-2">
                                                                <input
                                                                    value={milestoneDraftTitle}
                                                                    onChange={(event) => setMilestoneDraftTitle(event.target.value)}
                                                                    className="w-full rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-xs font-bold dark:border-white/10 dark:bg-white/5"
                                                                />
                                                                <div className="flex gap-2">
                                                                    <input
                                                                        type="date"
                                                                        value={milestoneDraftDate}
                                                                        onChange={(event) => setMilestoneDraftDate(event.target.value)}
                                                                        className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-xs font-bold dark:border-white/10 dark:bg-white/5"
                                                                    />
                                                                    <button
                                                                        onClick={() => handleUpdateMilestone(m.id)}
                                                                        disabled={updatingMilestoneId === m.id || !milestoneDraftTitle.trim()}
                                                                        className="rounded-lg bg-[hsl(var(--primary))] px-2 py-1.5 text-[10px] font-semibold uppercase text-white disabled:opacity-50"
                                                                    >
                                                                        Guardar
                                                                    </button>
                                                                    <button
                                                                        onClick={() => setEditingMilestoneId(null)}
                                                                        className="rounded-lg border border-slate-200 px-2 py-1.5 text-[10px] font-semibold uppercase text-slate-500 dark:border-white/10"
                                                                    >
                                                                        Cancelar
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <div className="flex items-center gap-3">
                                                                <button
                                                                    onClick={() => handleToggleMilestone(m)}
                                                                    disabled={updatingMilestoneId === m.id}
                                                                    className={`size-5 rounded-full border-2 flex items-center justify-center ${
                                                                        m.is_completed
                                                                            ? 'border-emerald-500 bg-emerald-500 text-white'
                                                                            : 'border-amber-400 text-amber-500'
                                                                    }`}
                                                                    title={m.is_completed ? 'Reabrir hito' : 'Completar hito'}
                                                                >
                                                                    {m.is_completed && <CheckCircle2 size={12} />}
                                                                </button>
                                                                <div className="min-w-0 flex-1">
                                                                    <p className={`truncate text-xs font-bold ${m.is_completed ? 'text-slate-400 line-through' : 'text-slate-700 dark:text-white'}`}>
                                                                        {m.title}
                                                                    </p>
                                                                    {m.target_date && <p className="text-[10px] text-slate-400">{new Date(m.target_date).toLocaleDateString()}</p>}
                                                                </div>
                                                                <button
                                                                    onClick={() => startEditingMilestone(m)}
                                                                    className="rounded-lg border border-slate-200 px-2 py-1 text-[10px] font-semibold uppercase text-slate-500 dark:border-white/10"
                                                                >
                                                                    Editar
                                                                </button>
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                                {!project?.milestones?.length && (
                                                    <p className="text-[11px] text-slate-400">Sin hitos creados.</p>
                                                )}
                                            </div>
                                            <div className="mt-4 space-y-2 border-t border-slate-100 pt-4 dark:border-white/10">
                                                <input
                                                    value={milestoneTitle}
                                                    onChange={(event) => setMilestoneTitle(event.target.value)}
                                                    placeholder="Nuevo hito"
                                                    className="w-full rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] px-3 py-2 text-xs font-bold dark:border-white/10 dark:bg-white/5"
                                                />
                                                <div className="flex gap-2">
                                                    <input
                                                        type="date"
                                                        value={milestoneDate}
                                                        onChange={(event) => setMilestoneDate(event.target.value)}
                                                        className="min-w-0 flex-1 rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] px-3 py-2 text-xs font-bold dark:border-white/10 dark:bg-white/5"
                                                    />
                                                    <button
                                                        onClick={handleCreateMilestone}
                                                        disabled={creatingMilestone || !milestoneTitle.trim()}
                                                        className="rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white disabled:opacity-50"
                                                    >
                                                        {creatingMilestone ? '...' : 'Crear'}
                                                    </button>
                                                </div>
                                            </div>
                                        </DSCard>
                                    </aside>
                                    <div className="min-h-[420px] lg:col-span-2 overflow-hidden rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-white/5">
                                        <ProjectActivityFeed activities={activities} />
                                    </div>
                                </div>
                            </div>
                        )}

                        {viewType === 'table' && (
                            <div className="h-[calc(100vh-8rem)] border border-slate-200 dark:border-white/5 rounded-lg overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-[#252528] shadow-sm">
                                <TaskTableView
                                    projectId={project?.id}
                                    tasks={tasks}
                                    onOpenTask={handleOpenTask}
                                    onAddTask={() => loadProject()}
                                    onTaskUpdated={() => loadProject()}
                                />
                            </div>
                        )}

                        {viewType === 'list' && (
                            <div className="w-full">
                                <DSCard>
                                    <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-3">Plan de Acción</h3>
                                    <div className="space-y-2">
                                        {tasks.map(task => (
                                            <div key={task.id} onClick={() => handleOpenTask(task)} className="p-3 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/30 transition-all duration-300 active:scale-[0.99] cursor-pointer">
                                                <div className="flex items-center gap-4 flex-1">
                                                    <button
                                                        onClick={(event) => {
                                                            event.stopPropagation();
                                                            handleMoveTask(task);
                                                        }}
                                                        className="size-8 rounded-full border-2 flex items-center justify-center hover:scale-110 transition-all"
                                                    >
                                                        {task.status === 'completed' ? (
                                                            <CheckCircle2 size={18} className="text-emerald-500" />
                                                        ) : task.status === 'review' ? (
                                                            <Clock size={18} className="text-amber-500" />
                                                        ) : task.status === 'in_progress' ? (
                                                            <AlertTriangle size={18} className="text-[hsl(var(--primary))]" />
                                                        ) : (
                                                            <Circle size={18} className="text-slate-400" />
                                                        )}
                                                    </button>
                                                    <div className="flex-1">
                                                        <p className="text-sm font-bold text-slate-800 dark:text-white">{task.title}</p>
                                                        <div className="flex items-center gap-2 mt-1">
                                                            <span className="text-[9px] font-semibold uppercase px-2 py-0.5 rounded-full border border-slate-200 bg-slate-50 text-slate-600 dark:border-white/10">
                                                                {phases.find(p => p.slug === task.status)?.name || task.status}
                                                            </span>
                                                            <span className="font-semibold">{task.priority}</span>
                                                            {task.due_date && <span className="text-[10px] text-slate-400">{new Date(task.due_date).toLocaleDateString()}</span>}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button onClick={(event) => { event.stopPropagation(); handleDeleteTask(task.id); }} className="p-2 rounded-md hover:bg-rose-50 dark:hover:bg-rose-500/10 text-slate-400 hover:text-rose-500 transition-colors" title="Eliminar tarea">
                                                        <Trash2 size={16} />
                                                    </button>
                                                    <ChevronRight size={16} className="text-slate-300" />
                                                </div>
                                            </div>
                                        ))}
                                        {tasks.length === 0 && <p className="text-xs text-slate-400 text-center py-1.5">No hay tareas — crea la primera con el botón &quot;Nueva Tarea&quot;</p>}
                                    </div>
                                </DSCard>
                            </div>
                        )}

                        {(viewType === 'board' || viewType === 'kanban') && (
                            <div className="flex gap-3 overflow-x-auto pb-4">
                                {phases.map((phase) => {
                                    const columnTasks = tasks.filter((task) => (task.status || 'todo') === phase.slug);
                                    return (
                                        <section key={phase.slug} className="w-80 shrink-0 rounded-lg border border-slate-200 bg-slate-50 p-2 dark:border-white/10 dark:bg-[#252528]">
                                            <div className="mb-3 flex items-center justify-between px-1">
                                                <div className="flex items-center gap-2">
                                                    <div className="size-2 rounded-full" style={{ backgroundColor: phase.color }} />
                                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{phase.name}</p>
                                                </div>
                                                <span className="font-semibold text-slate-400">{columnTasks.length}</span>
                                            </div>
                                            <div className="space-y-2">
                                                {columnTasks.map((task) => (
                                                    <article key={task.id} onClick={() => handleOpenTask(task)} className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-2 shadow-sm dark:border-white/10 dark:bg-[#1E1F21] cursor-pointer transition-all duration-300 hover:border-blue-300 active:scale-[0.99]">
                                                        <p className="text-sm font-bold text-slate-900 dark:text-white">{task.title}</p>
                                                        <div className="mt-2 flex items-center justify-between gap-2">
                                                            <span className="text-[9px] font-semibold uppercase px-2 py-0.5 rounded-full border border-slate-200 bg-slate-100 text-slate-600 dark:border-white/10">
                                                                {phase.name}
                                                            </span>
                                                            <button onClick={(event) => { event.stopPropagation(); handleMoveTask(task); }} className="rounded-lg border border-slate-200 px-2 py-1 text-[10px] font-semibold uppercase text-slate-500 dark:border-white/10">Avanzar</button>
                                                        </div>
                                                    </article>
                                                ))}
                                                {columnTasks.length === 0 && <div className="rounded-md border border-dashed border-slate-200 py-1.5 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400 dark:border-white/10">Vacio</div>}
                                            </div>
                                        </section>
                                    );
                                })}
                            </div>
                        )}

                        {viewType === 'calendar' && (
                            <div className="h-[720px]">
                                <UniversalCalendarView events={taskCalendarEvents} title={`Calendario: ${project?.title || 'Proyecto'}`} />
                            </div>
                        )}

                        {viewType === 'gantt' && (
                            <div className="h-[720px]">
                                <UniversalGanttView items={taskGanttItems} moduleName={project?.title || 'Proyecto'} />
                            </div>
                        )}

                        {viewType === 'wiki' && (
                            <ProjectWikiEditor project_id={Number(project?.id || id)} />
                        )}

                        {viewType === 'chat' && (
                            <ProjectChatPanel projectId={Number(project?.id || id)} />
                        )}
                    </>
                )}
            </main>
            <TaskDetailPanel
                task={selectedTask}
                projectTitle={project?.title}
                onClose={handleCloseTask}
                onUpdate={handleTaskUpdated}
                onActivityCreated={loadProject}
                onDelete={(taskId) => {
                    setTasks((prev) => prev.filter((task) => task.id !== taskId));
                    handleCloseTask();
                    loadProject();
                }}
            />
            </div>

            <TaskCreationDrawer
                isOpen={showTaskModal}
                onClose={() => setShowTaskModal(false)}
                onSubmit={handleCreateTask}
            />
            <ProjectWhiteboard
                project_id={Number(project?.id || id)}
                isOpen={whiteboardOpen}
                onClose={() => setWhiteboardOpen(false)}
            />
            {showPhaseManager && (
                <PhaseManagerDrawer
                    projectId={Number(project?.id || id)}
                    phases={phases}
                    onClose={() => setShowPhaseManager(false)}
                    onSaved={(newPhases) => {
                        setPhases(newPhases);
                        loadProject();
                    }}
                />
            )}
        </div>
    );
}

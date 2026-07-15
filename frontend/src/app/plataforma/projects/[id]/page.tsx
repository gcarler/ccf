"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import {
    LayoutDashboard,
    ChevronRight,
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
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/ConfirmActionDrawer';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { DSMetric } from '@/design/components/DSMetric';
import TaskTableView from '@/components/projects/TaskTableView';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectActivityItem, ProjectMilestoneRecord, ProjectTaskRecord, ProjectRecord } from '@/types/projects';
import { ProjectKanbanBoard, type PhaseDef } from '@/components/projects/ProjectKanbanBoard';
import { PhaseManagerDrawer } from '@/components/projects/PhaseManagerDrawer';
import { toast } from 'sonner';
import PersonaSelect from '@/components/ui/PersonaSelect';

const PROJECT_DETAIL_VIEWS: ViewType[] = ['dashboard', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki', 'chat'];

export default function ProjectDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token, loading: authLoading } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const currentViewParam = searchParams?.get('view');

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [project, setProject] = useState<any>(null);
    const [tasks, setTasks] = useState<ProjectTaskRecord[]>([]);
    const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [showTaskModal, setShowTaskModal] = useState(false);
    const [editingProject, setEditingProject] = useState(false);
    const [editTitle, setEditTitle] = useState('');
    const [editDescription, setEditDescription] = useState('');
    const [editStatus, setEditStatus] = useState('');
    const [editOwnerId, setEditOwnerId] = useState<string | null>(null);
    const [viewType, setViewType] = useState<ViewType>('dashboard');
    const [selectedTask, setSelectedTask] = useState<ProjectTaskRecord | null>(null);
    const [whiteboardOpen, setWhiteboardOpen] = useState(false);
    const [milestoneTitle, setMilestoneTitle] = useState('');
    const [milestoneDate, setMilestoneDate] = useState('');
    const [creatingMilestone, setCreatingMilestone] = useState(false);
    const [updatingMilestoneId, setUpdatingMilestoneId] = useState<string | null>(null);
    const [editingMilestoneId, setEditingMilestoneId] = useState<string | null>(null);
    const [milestoneDraftTitle, setMilestoneDraftTitle] = useState('');
    const [milestoneDraftDate, setMilestoneDraftDate] = useState('');
    const [phases, setPhases] = useState<PhaseDef[]>([]);
    const [showPhaseManager, setShowPhaseManager] = useState(false);
    const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
    const [error, setError] = useState<string | null>(null);
    const [reloadKey, setReloadKey] = useState(0);

    const loadProject = useCallback(async () => {
        if (!id) {
            setLoading(false);
            setError('No se encontró el proyecto.');
            return;
        }
        if (!token) {
            setLoading(false);
            setError('Debes iniciar sesión para ver este proyecto.');
            return;
        }
        try {
            setError(null);
            setLoading(true);
            const [projData, tasksData, activityRows, phasesData] = await Promise.all([
                apiFetch<ProjectRecord>(`/projects/${id}`, { token }),
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
            setProject(null);
            setTasks([]);
            setActivities([]);
            setPhases([]);
            setError('No se pudo cargar el proyecto.');
            toast.error('Error al cargar detalle del proyecto');
        } finally {
            setLoading(false);
        }
    }, [id, token]);

    useEffect(() => {
        if (!authLoading) loadProject();
    }, [authLoading, loadProject, reloadKey]);

    useEffect(() => {
        const taskId = searchParams?.get('task');
        if (!taskId || tasks.length === 0) return;
        const task = tasks.find((row) => row.id === taskId);
        if (task) setSelectedTask(task);
    }, [searchParams, tasks]);

    const handleCreateTask = async (data: { title: string; description: string; priority: string; status: string; assignee_id?: string | null }) => {
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

    const handleDeleteTask = async (taskId: string) => {
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
        const viewQuery = currentViewParam ? `view=${encodeURIComponent(currentViewParam)}&` : '';
        router.replace(`/plataforma/projects/${id}?${viewQuery}task=${task.id}`);
    };

    const handleCloseTask = () => {
        setSelectedTask(null);
        const viewQuery = currentViewParam ? `?view=${encodeURIComponent(currentViewParam)}` : '';
        router.replace(`/plataforma/projects/${id}${viewQuery}`);
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
        if (!token || !id) return;
        setConfirmAction({
            title: 'Eliminar proyecto',
            description: 'Esta acción eliminará el proyecto y todas sus tareas asociadas.',
            destructive: true,
            confirmLabel: 'Eliminar proyecto',
            onConfirm: async () => {
                try {
                    await apiFetch(`/projects/${id}`, { method: 'DELETE', token });
                    toast.success('Proyecto eliminado');
                    router.push('/plataforma/projects');
                } catch (err) {
                    toast.error('Error al eliminar proyecto');
                }
            },
        });
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

    const handleDeleteMilestone = async (milestoneId: string) => {
        if (!token || !id) return;
        setUpdatingMilestoneId(milestoneId);
        try {
            await apiFetch(`/projects/${id}/milestones/${milestoneId}`, {
                method: 'DELETE',
                token,
            });
            toast.success('Hito eliminado');
            loadProject();
        } catch {
            toast.error('Error al eliminar hito');
        } finally {
            setUpdatingMilestoneId(null);
        }
    };

    const startEditingMilestone = (milestone: ProjectMilestoneRecord) => {
        setEditingMilestoneId(milestone.id);
        setMilestoneDraftTitle(milestone.title);
        setMilestoneDraftDate(milestone.target_date ? milestone.target_date.slice(0, 10) : '');
    };

    const handleUpdateMilestone = async (milestoneId: string) => {
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

    if (loading) {
        return (
            <div className="flex flex-col h-full bg-[hsl(var(--bg-secondary))] dark:bg-[hsl(var(--bg-primary))]">
                <div className="p-4 space-y-4 animate-pulse">
                    <div className="h-10 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg w-1/3" />
                    <div className="h-6 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg w-2/3" />
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        {[1, 2, 3, 4].map((i) => (
                            <div key={i} className="h-24 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg" />
                        ))}
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div className="h-64 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg lg:col-span-1" />
                        <div className="h-64 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg lg:col-span-2" />
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="mx-auto flex max-w-xl flex-col items-center gap-3 p-4 text-center">
                <p className="font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{error}</p>
                <button
                    onClick={() => setReloadKey(key => key + 1)}
                    className="rounded-md border border-[hsl(var(--border))] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:hover:bg-white/5"
                >
                    Reintentar
                </button>
            </div>
        );
    }

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
        <div className="flex flex-col h-full bg-[hsl(var(--bg-secondary))] dark:bg-[hsl(var(--bg-primary))] overflow-hidden">
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
                        <button onClick={() => setShowTaskModal(true)} className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary))]/20 hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all flex items-center gap-2">
                            <Plus size={14} /> Nueva Tarea
                        </button>
                        <button onClick={() => setWhiteboardOpen(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] rounded-lg text-[10px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-2 border border-[hsl(var(--border))] dark:border-white/10">
                            <PencilRuler size={14} /> Pizarra
                        </button>
                        <button onClick={() => setShowPhaseManager(true)} className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all flex items-center gap-2">
                            <Edit3 size={14} /> Fases
                        </button>
                        <button onClick={startEditing} className="px-3 py-1.5 bg-amber-500 text-white rounded-lg text-[10px] font-bold uppercase tracking-wide hover:bg-amber-600 active:scale-95 transition-all flex items-center gap-2">
                            <Edit3 size={14} /> Editar
                        </button>
                        <button onClick={handleDeleteProject} className="px-3 py-1.5 bg-rose-500 text-white rounded-lg text-[10px] font-bold uppercase tracking-wide hover:bg-rose-600 active:scale-95 transition-all flex items-center gap-2">
                            <Trash2 size={14} /> Eliminar
                        </button>
                    </div>
                }
            />

            <div className="flex min-h-0 flex-1 overflow-hidden">
            <main className={(viewType === 'board' || viewType === 'kanban') ? "flex-1 overflow-hidden" : "flex-1 overflow-y-auto p-4 space-y-3"}>
                {editingProject ? (
                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] rounded-lg p-3 border border-[hsl(var(--border))] dark:border-white/10 space-y-3">
                        <h3 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Editar Proyecto</h3>
                        <input value={editTitle} onChange={e => setEditTitle(e.target.value)} className="w-full p-2 rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--bg-primary))] text-sm font-medium" placeholder="Título del proyecto" />
                        <textarea value={editDescription} onChange={e => setEditDescription(e.target.value)} rows={3} className="w-full p-2 rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--bg-primary))] text-sm" placeholder="Descripción" />
                        <select value={editStatus} onChange={e => setEditStatus(e.target.value)} className="w-full p-2 rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--bg-primary))] text-sm font-medium">
                            <option value="planning">Planificación</option>
                            <option value="active">En Marcha</option>
                            <option value="on_hold">En Pausa</option>
                            <option value="completed">Alcanzado</option>
                            <option value="archived">Archivado</option>
                        </select>
                        <PersonaSelect
                            value={editOwnerId}
                            onChange={setEditOwnerId}
                            placeholder="Responsable del proyecto"
                        />
                        <div className="flex gap-2">
                            <button onClick={handleUpdateProject} className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all">Guardar Cambios</button>
                            <button onClick={() => setEditingProject(false)} className="px-3 py-1.5 bg-[hsl(var(--surface-3))] dark:bg-white/10 rounded-md text-xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-2))] active:scale-95 transition-all">Cancelar</button>
                        </div>
                    </div>
                ) : (
                    <>
                        {viewType === 'dashboard' && (
                            <div className="space-y-3">
                                <header className="space-y-2">
                                    <div className="flex items-center gap-3">
                                        <DSBadge tone={project?.status === 'active' ? 'blue' : project?.status === 'completed' ? 'emerald' : 'amber'} label={project?.status?.toUpperCase() || 'PROYECTO'} />
                                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{progressPercent}% completado</span>
                                    </div>
                                    <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase">
                                        {project?.title}
                                    </h1>
                                    {project?.description && (
                                        <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] max-w-2xl">{project.description}</p>
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
                                        <DSCard>
                                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">Hitos</h3>
                                            <div className="space-y-2">
                                                {project?.milestones?.map((m: ProjectMilestoneRecord) => (
                                                    <div key={m.id} className="rounded-md bg-[hsl(var(--surface-1))] p-2 dark:bg-white/5">
                                                        {editingMilestoneId === m.id ? (
                                                            <div className="space-y-2">
                                                                <input
                                                                    value={milestoneDraftTitle}
                                                                    onChange={(event) => setMilestoneDraftTitle(event.target.value)}
                                                                    className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-xs font-bold dark:border-white/10 dark:bg-white/5"
                                                                />
                                                                <div className="flex gap-2">
                                                                    <input
                                                                        type="date"
                                                                        value={milestoneDraftDate}
                                                                        onChange={(event) => setMilestoneDraftDate(event.target.value)}
                                                                        className="min-w-0 flex-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-xs font-bold dark:border-white/10 dark:bg-white/5"
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
                                                                        className="rounded-lg border border-[hsl(var(--border))] px-2 py-1.5 text-[10px] font-semibold uppercase text-[hsl(var(--text-secondary))] dark:border-white/10"
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
                                                                    <p className={`truncate text-xs font-bold ${m.is_completed ? 'text-[hsl(var(--text-secondary))] line-through' : 'text-[hsl(var(--text-primary))] dark:text-white'}`}>
                                                                        {m.title}
                                                                    </p>
                                                                    {m.target_date && <p className="text-[10px] text-[hsl(var(--text-secondary))]">{new Date(m.target_date).toLocaleDateString()}</p>}
                                                                </div>
                                                                <button
                                                                    onClick={() => startEditingMilestone(m)}
                                                                    className="rounded-lg border border-[hsl(var(--border))] px-2 py-1 text-[10px] font-semibold uppercase text-[hsl(var(--text-secondary))] dark:border-white/10"
                                                                >
                                                                    Editar
                                                                </button>
                                                                <button
                                                                    onClick={() => handleDeleteMilestone(m.id)}
                                                                    disabled={updatingMilestoneId === m.id}
                                                                    title="Eliminar hito"
                                                                    className="rounded-lg border border-rose-200 px-2 py-1 text-[10px] font-semibold uppercase text-rose-600 hover:bg-rose-50 dark:border-rose-500/30 dark:hover:bg-rose-500/10 disabled:opacity-50"
                                                                >
                                                                    Eliminar
                                                                </button>
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                                {!project?.milestones?.length && (
                                                    <p className="text-[11px] text-[hsl(var(--text-secondary))]">Sin hitos creados.</p>
                                                )}
                                            </div>
                                            <div className="mt-4 space-y-2 border-t border-[hsl(var(--border))] pt-4 dark:border-white/10">
                                                <input
                                                    value={milestoneTitle}
                                                    onChange={(event) => setMilestoneTitle(event.target.value)}
                                                    placeholder="Nuevo hito"
                                                    className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-xs font-bold dark:border-white/10 dark:bg-white/5"
                                                />
                                                <div className="flex gap-2">
                                                    <input
                                                        type="date"
                                                        value={milestoneDate}
                                                        onChange={(event) => setMilestoneDate(event.target.value)}
                                                        className="min-w-0 flex-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-xs font-bold dark:border-white/10 dark:bg-white/5"
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
                                    <div className="min-h-[420px] lg:col-span-2 overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-white/5">
                                        <ProjectActivityFeed activities={activities} />
                                    </div>
                                </div>
                            </div>
                        )}

                        {viewType === 'table' && (
                            <div className="h-[calc(100vh-8rem)] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] shadow-sm">
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
                                    <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Plan de Acción</h3>
                                    <div className="space-y-2">
                                        {tasks.map(task => (
                                            <div key={task.id} onClick={() => handleOpenTask(task)} className="p-3 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between group hover:border-[hsl(var(--primary))]/40 transition-all duration-300 cursor-pointer">
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
                                                            <Circle size={18} className="text-[hsl(var(--text-secondary))]" />
                                                        )}
                                                    </button>
                                                    <div className="flex-1">
                                                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{task.title}</p>
                                                        <div className="flex items-center gap-2 mt-1">
                                                            <span className="text-[9px] font-semibold uppercase px-2 py-0.5 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10">
                                                                {phases.find(p => p.slug === task.status)?.name || task.status}
                                                            </span>
                                                            <span className="font-semibold">{task.priority}</span>
                                                            {task.due_date && <span className="text-[10px] text-[hsl(var(--text-secondary))]">{new Date(task.due_date).toLocaleDateString()}</span>}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button onClick={(event) => { event.stopPropagation(); handleDeleteTask(task.id); }} className="p-2 rounded-md hover:bg-rose-50 dark:hover:bg-rose-500/10 text-[hsl(var(--text-secondary))] hover:text-rose-500 transition-colors" title="Eliminar tarea">
                                                        <Trash2 size={16} />
                                                    </button>
                                                    <ChevronRight size={16} className="text-[hsl(var(--text-secondary))]" />
                                                </div>
                                            </div>
                                        ))}
                                        {tasks.length === 0 && <p className="text-xs text-[hsl(var(--text-secondary))] text-center py-1.5">No hay tareas — crea la primera con el botón &quot;Nueva Tarea&quot;</p>}
                                    </div>
                                </DSCard>
                            </div>
                        )}

                        {(viewType === 'board' || viewType === 'kanban') && project && (
                            <div className="h-full">
                                <ProjectKanbanBoard
                                    project={project}
                                    tasks={tasks}
                                    phases={phases}
                                    onTasksChange={setTasks}
                                    onOpenTask={handleOpenTask}
                                    onAddTask={() => setShowTaskModal(true)}
                                />
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
                            <ProjectWikiEditor project_id={project?.id || id} />
                        )}

                        {viewType === 'chat' && (
                            <ProjectChatPanel projectId={project?.id || id} />
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

            <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />

            <TaskCreationDrawer
                isOpen={showTaskModal}
                onClose={() => setShowTaskModal(false)}
                onSubmit={handleCreateTask}
            />
            <ProjectWhiteboard
                project_id={project?.id || id}
                isOpen={whiteboardOpen}
                onClose={() => setWhiteboardOpen(false)}
            />
            {showPhaseManager && (
                <PhaseManagerDrawer
                    projectId={project?.id || id}
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

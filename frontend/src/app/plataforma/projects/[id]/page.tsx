"use client";

import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { PROJECTS_LIST_ROUTE } from '@/app/plataforma/projects/projectsLinks';
import {
    LayoutDashboard,
    Calendar,
    Plus,
    Trash2,
    Edit3,
    PencilRuler,
    Target,
    Sliders,
    Wallet,
    ShieldAlert,
    Users,
    Clock,
    BookTemplate,
    Zap,
    FileText,
    BarChart3,
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';

import TaskCreationDrawer from '@/components/projects/TaskCreationDrawer';
import TaskDetailPanel from '@/components/projects/TaskDetailPanel';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/ConfirmActionDrawer';
import ProjectWhiteboard from '@/components/projects/ProjectWhiteboard';
import { PhaseManagerDrawer } from '@/components/projects/PhaseManagerDrawer';
import ProjectSettingsDrawer from '@/components/projects/ProjectSettingsDrawer';
import { ProjectKpiDrawer } from '@/components/projects/ProjectKpiDrawer';
import { ProgressSettingsDrawer } from '@/components/projects/ProgressSettingsDrawer';
import { ProjectBudgetDrawer } from '@/components/projects/ProjectBudgetDrawer';
import { ProjectRiskMatrixDrawer } from '@/components/projects/ProjectRiskMatrixDrawer';
import { ProjectWorkloadDrawer } from '@/components/projects/ProjectWorkloadDrawer';
import { ProjectTimeTrackingDrawer } from '@/components/projects/ProjectTimeTrackingDrawer';
import { ProjectTemplateCatalogDrawer } from '@/components/projects/ProjectTemplateCatalogDrawer';
import { ProjectAutomationsDrawer } from '@/components/projects/ProjectAutomationsDrawer';
import { ProjectReportDrawer } from '@/components/projects/ProjectReportDrawer';
import { ProjectIndicatorsDrawer } from '@/components/projects/ProjectIndicatorsDrawer';
import { ProjectUpdateProvider } from '@/context/ProjectUpdateContext';
import { ProjectViewsContent } from '@/components/projects/ProjectViewsContent';
import ProjectContextPanel from '@/components/projects/ProjectContextPanel';
import { useProjectPageData } from '@/hooks/useProjectPageData';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectTaskRecord } from '@/types/projects';
import { toast } from 'sonner';

const PROJECT_DETAIL_VIEWS: ViewType[] = ['dashboard', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki', 'chat'];

/**
 * Orquestador de la página de detalle de un proyecto.
 *
 * Tras `PARCIAL-PAGE-001` (2026-07-16), este archivo es un thin wrapper:
 *  1. Lee auth, router y search params.
 *  2. Invoca `useProjectPageData(id)` para el SOT de datos + handlers.
 *  3. Construye el `ProjectUpdateContextValue` consumiendo ese hook.
 *  4. Maneja la coordinación URL↔TaskDetailPanel (`selectedTask`, `handleOpenTask`,
 *     `handleCloseTask`).
 *  5. Coordina drawers (TaskCreationDrawer, ProjectWhiteboard, PhaseManagerDrawer,
 *     ProjectSettingsDrawer) y el flujo de delete-project.
 *  6. Delega TODO el render-switching del `viewType` al componente
 *     `ProjectViewsContent`, que lee del Context directamente (sin prop-drilling).
 *
 * Resultado: ~250 LOC de orquestador en vez de 663 LOC con estado y JSX mixto.
 */
export default function ProjectDetailPage() {
    const params = useParams();
    const id = (params?.id as string) ?? '';
    const { user, hasPermission, token } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const currentViewParam = searchParams?.get('view');

    const canDeleteProject = user?.role === 'admin' || user?.role === 'administrador' || hasPermission('system:config');

    const pageData = useProjectPageData(id);
    const {
        project, tasks, phases, activities, loading,
        reloadProject, createTask, updateProject, updateTask, deleteTask,
        error, bumpReloadKey,
    } = pageData;

    // ── View switcher (URL ⇄ viewType) ──
    const [viewType, setViewType] = useState<ViewType>('dashboard');
    useEffect(() => {
        if (currentViewParam && PROJECT_DETAIL_VIEWS.includes(currentViewParam as ViewType)) {
            setViewType(currentViewParam as ViewType);
        }
    }, [currentViewParam]);

    // ── TaskDetailPanel coordination (URL sync) ──
    const [selectedTask, setSelectedTask] = useState<ProjectTaskRecord | null>(null);
    useEffect(() => {
        const taskId = searchParams?.get('task');
        if (!taskId || tasks.length === 0) return;
        const task = tasks.find((row) => row.id === taskId);
        if (task) setSelectedTask(task);
    }, [searchParams, tasks]);

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
        setSelectedTask((prev) => (prev?.id === updated.id ? { ...prev, ...updated } : prev));
        void reloadProject();
    };

    const handleDeleteFromPanel = async (taskId: string) => {
        handleCloseTask();            // limpia selectedTask + URL
        await deleteTask(taskId);
        await reloadProject();
    };

    // ── Drawers toggles (UI local) ──
    const [showTaskModal, setShowTaskModal] = useState(false);
    const [taskCreationStatus, setTaskCreationStatus] = useState('todo');
    const [showProjectSettings, setShowProjectSettings] = useState(false);
    const [whiteboardOpen, setWhiteboardOpen] = useState(false);
    const [showPhaseManager, setShowPhaseManager] = useState(false);
    const [showKpiDrawer, setShowKpiDrawer] = useState(false);
    const [showProgressDrawer, setShowProgressDrawer] = useState(false);
    const [showBudgetDrawer, setShowBudgetDrawer] = useState(false);
    const [showRiskDrawer, setShowRiskDrawer] = useState(false);
    const [showWorkloadDrawer, setShowWorkloadDrawer] = useState(false);
    const [showTimeTrackingDrawer, setShowTimeTrackingDrawer] = useState(false);
    const [showTemplateDrawer, setShowTemplateDrawer] = useState(false);
    const [showAutomationsDrawer, setShowAutomationsDrawer] = useState(false);
    const [showReportDrawer, setShowReportDrawer] = useState(false);
    const [showIndicatorsDrawer, setShowIndicatorsDrawer] = useState(false);
    const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

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
                    router.push(PROJECTS_LIST_ROUTE);
                } catch {
                    toast.error('Error al eliminar proyecto');
                }
            },
        });
    };

    // ── Build context value (stable reference) ──
    const contextValue = useMemo(
        () => ({
            project, tasks, phases, activities, loading,
            reloadProject, createTask, updateProject, updateTask, deleteTask,
        }),
        [project, tasks, phases, activities, loading, reloadProject, createTask, updateProject, updateTask, deleteTask],
    );

    if (loading) {
        return (
            <ProjectUpdateProvider value={contextValue}>
                <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]">
                    <div className="p-4 space-y-4 animate-pulse">
                        <div className="h-10 bg-[hsl(var(--surface-2))] rounded-lg w-1/3" />
                        <div className="h-6 bg-[hsl(var(--surface-2))] rounded-lg w-2/3" />
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            {[1, 2, 3, 4].map((i) => (
                                <div key={i} className="h-24 bg-[hsl(var(--surface-2))] rounded-lg" />
                            ))}
                        </div>
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                            <div className="h-64 bg-[hsl(var(--surface-2))] rounded-lg lg:col-span-1" />
                            <div className="h-64 bg-[hsl(var(--surface-2))] rounded-lg lg:col-span-2" />
                        </div>
                    </div>
                </div>
            </ProjectUpdateProvider>
        );
    }

    if (error) {
        return (
            <ProjectUpdateProvider value={contextValue}>
                <div className="mx-auto flex max-w-xl flex-col items-center gap-3 p-4 text-center">
                    <p className="font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{error}</p>
                    <button
                        onClick={() => bumpReloadKey()}
                        className="rounded-md border border-[hsl(var(--border))] px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] transition-colors hover:bg-[hsl(var(--surface-2))]"
                    >
                        Reintentar
                    </button>
                </div>
            </ProjectUpdateProvider>
        );
    }

    return (
        <ProjectUpdateProvider value={contextValue}>
            <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] overflow-hidden">
                <WorkspaceToolbar
                    breadcrumbs={[
                        { label: 'Proyectos', icon: LayoutDashboard, href: PROJECTS_LIST_ROUTE },
                        { label: project?.title || 'Cargando...', icon: Calendar },
                    ]}
                    viewType={viewType}
                    setViewType={setViewType}
                    availableViews={PROJECT_DETAIL_VIEWS}
                    rightActions={
                        <div className="flex items-center gap-2">
                            <button onClick={() => {
                                setTaskCreationStatus('todo');
                                setShowTaskModal(true);
                            }} className="px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all flex items-center gap-2">
                                <Plus size={14} /> Nueva Tarea
                            </button>
                            <button onClick={() => setWhiteboardOpen(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-2 border border-[hsl(var(--border))]">
                                <PencilRuler size={14} /> Pizarra
                            </button>
                            <button onClick={() => setShowPhaseManager(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <Edit3 size={14} /> Fases
                            </button>
                            <button onClick={() => setShowKpiDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <Target size={14} className="text-[hsl(var(--primary))]" /> KPIs
                            </button>
                            <button onClick={() => setShowProgressDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <Sliders size={14} className="text-[hsl(var(--primary))]" /> Avance
                            </button>
                            <button onClick={() => setShowBudgetDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <Wallet size={14} className="text-[hsl(var(--primary))]" /> Presupuesto
                            </button>
                            <button onClick={() => setShowRiskDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <ShieldAlert size={14} className="text-[hsl(var(--destructive))]" /> Riesgos
                            </button>
                            <button onClick={() => setShowWorkloadDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <Users size={14} className="text-[hsl(var(--primary))]" /> Carga
                            </button>
                            <button onClick={() => setShowTimeTrackingDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <Clock size={14} className="text-[hsl(var(--primary))]" /> Horas
                            </button>
                            <button onClick={() => setShowTemplateDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <BookTemplate size={14} className="text-[hsl(var(--primary))]" /> Plantillas
                            </button>
                            <button onClick={() => setShowAutomationsDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <Zap size={14} className="text-[hsl(var(--primary))]" /> Auto
                            </button>
                            <button onClick={() => setShowReportDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <FileText size={14} className="text-[hsl(var(--primary))]" /> Reportes
                            </button>
                            <button onClick={() => setShowIndicatorsDrawer(true)} className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]">
                                <BarChart3 size={14} className="text-[hsl(var(--primary))]" /> MGA / CREMA
                            </button>
                            <button onClick={() => setShowProjectSettings(true)} className="px-3 py-1.5 bg-[hsl(var(--warning))] text-[hsl(var(--primary-foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:opacity-90 active:scale-95 transition-all flex items-center gap-2">
                                <Edit3 size={14} /> Editar
                            </button>
                            {canDeleteProject && (
                                <button onClick={handleDeleteProject} className="px-3 py-1.5 bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:opacity-90 active:scale-95 transition-all flex items-center gap-2">
                                    <Trash2 size={14} /> Eliminar
                                </button>
                            )}
                        </div>
                    }
                />

                <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
                    <div className="min-h-0 min-w-0 flex-1 overflow-hidden">
                        <ProjectViewsContent
                            viewType={viewType}
                            onOpenTask={handleOpenTask}
                            onTaskUpdated={handleTaskUpdated}
                            onActivityCreated={() => void reloadProject()}
                            onDeleteTask={handleDeleteFromPanel}
                            setShowTaskModal={setShowTaskModal}
                            setWhiteboardOpen={setWhiteboardOpen}
                            setTaskCreationStatus={setTaskCreationStatus}
                        />
                    </div>
                    {viewType !== 'chat' && !selectedTask && (
                        <ProjectContextPanel onOpenTask={handleOpenTask} />
                    )}
                    <TaskDetailPanel
                        task={selectedTask}
                        projectTitle={project?.title}
                        onClose={handleCloseTask}
                        onUpdate={handleTaskUpdated}
                        onActivityCreated={() => void reloadProject()}
                        onDelete={handleDeleteFromPanel}
                    />
                </div>

                <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />

                <TaskCreationDrawer
                    isOpen={showTaskModal}
                    defaultStatus={taskCreationStatus}
                    onClose={() => setShowTaskModal(false)}
                    onSubmit={async (data) => {
                        const ok = await createTask(data);
                        if (ok) setShowTaskModal(false);
                        return ok;
                    }}
                />
                <ProjectWhiteboard
                    project_id={project?.id || id}
                    isOpen={whiteboardOpen}
                    onClose={() => setWhiteboardOpen(false)}
                />
                {showPhaseManager && (
                    <PhaseManagerDrawer
                        projectId={project?.id || id}
                        onClose={() => setShowPhaseManager(false)}
                    />
                )}

                <ProjectSettingsDrawer
                    project={project}
                    isOpen={showProjectSettings}
                    onClose={() => setShowProjectSettings(false)}
                    onSave={updateProject}
                />

                <ProjectKpiDrawer
                    projectId={project?.id || id}
                    isOpen={showKpiDrawer}
                    onClose={() => setShowKpiDrawer(false)}
                    onKpisUpdated={() => reloadProject()}
                />

                <ProgressSettingsDrawer
                    projectId={project?.id || id}
                    isOpen={showProgressDrawer}
                    onClose={() => setShowProgressDrawer(false)}
                    currentMode={project?.progress_mode}
                    manualProgress={project?.manual_progress}
                    currentHealthOverride={project?.health_override}
                    onSaved={() => reloadProject()}
                />

                <ProjectBudgetDrawer
                    projectId={project?.id || id}
                    isOpen={showBudgetDrawer}
                    onClose={() => setShowBudgetDrawer(false)}
                    budgetAllocated={project?.budget_allocated}
                    onBudgetUpdated={() => reloadProject()}
                />

                <ProjectRiskMatrixDrawer
                    projectId={project?.id || id}
                    isOpen={showRiskDrawer}
                    onClose={() => setShowRiskDrawer(false)}
                    onRiskUpdated={() => reloadProject()}
                />

                <ProjectWorkloadDrawer
                    projectId={project?.id || id}
                    isOpen={showWorkloadDrawer}
                    onClose={() => setShowWorkloadDrawer(false)}
                    onWorkloadUpdated={() => reloadProject()}
                />

                <ProjectTimeTrackingDrawer
                    projectId={project?.id || id}
                    isOpen={showTimeTrackingDrawer}
                    onClose={() => setShowTimeTrackingDrawer(false)}
                    tasks={tasks}
                    onTimeLogged={() => reloadProject()}
                />

                <ProjectTemplateCatalogDrawer
                    isOpen={showTemplateDrawer}
                    onClose={() => setShowTemplateDrawer(false)}
                    activeProjectId={project?.id || id}
                    activeProjectTitle={project?.title}
                    onProjectCreated={() => reloadProject()}
                />

                <ProjectAutomationsDrawer
                    projectId={project?.id || id}
                    isOpen={showAutomationsDrawer}
                    onClose={() => setShowAutomationsDrawer(false)}
                    tasks={tasks}
                    onAutomationTriggered={() => reloadProject()}
                />

                <ProjectReportDrawer
                    projectId={project?.id || id}
                    isOpen={showReportDrawer}
                    onClose={() => setShowReportDrawer(false)}
                    projectTitle={project?.title}
                />

                <ProjectIndicatorsDrawer
                    projectId={project?.id || id}
                    isOpen={showIndicatorsDrawer}
                    onClose={() => setShowIndicatorsDrawer(false)}
                    onIndicatorUpdated={() => reloadProject()}
                />
            </div>
        </ProjectUpdateProvider>
    );
}

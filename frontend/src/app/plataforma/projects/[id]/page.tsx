'use client';

import React, { useEffect, useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import clsx from 'clsx';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { PROJECTS_LIST_ROUTE } from '@/app/plataforma/projects/projectsLinks';
import { canDeleteProject } from '@/lib/projects/access';
import {
  confirmProjectDeletion,
  PROJECT_DELETE_CONFIRMATION_DESCRIPTION,
} from '@/lib/projects/confirmProjectDeletion';
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
  FolderArchive,
  MoreHorizontal,
  type LucideIcon,
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import RightPanel from '@/components/ui/RightPanel';
import type { ConfirmActionState } from '@/components/ConfirmActionDrawer';
import {
  DeferredMount,
  ProjectDrawerLoading,
} from '@/components/projects/DeferredMount';
import { ProjectUpdateProvider } from '@/context/ProjectUpdateContext';
import { ProjectViewsContent } from '@/components/projects/ProjectViewsContent';
import ProjectContextPanel from '@/components/projects/ProjectContextPanel';
import { useProjectPageData } from '@/hooks/useProjectPageData';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectTaskRecord } from '@/types/projects';

const PROJECT_DETAIL_VIEWS: ViewType[] = [
  'dashboard',
  'table',
  'list',
  'board',
  'kanban',
  'calendar',
  'gantt',
  'wiki',
  'chat',
];

const TaskDetailPanel = dynamic(
  () => import('@/components/projects/TaskDetailPanel'),
  {
    loading: () => (
      <aside
        className="h-full w-[min(520px,88vw)] shrink-0 animate-pulse border-l border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4"
        role="status"
        aria-label="Cargando detalle de tarea"
      >
        <div className="mb-4 h-8 rounded-md bg-[hsl(var(--surface-2))]" />
        <div className="mb-3 h-5 w-2/3 rounded-md bg-[hsl(var(--surface-2))]" />
        <div className="h-32 rounded-md bg-[hsl(var(--surface-2))]" />
      </aside>
    ),
  }
);

const TaskCreationDrawer = dynamic(
  () => import('@/components/projects/TaskCreationDrawer'),
  { loading: ProjectDrawerLoading }
);
const ConfirmActionDrawer = dynamic(
  () => import('@/components/ConfirmActionDrawer'),
  { loading: ProjectDrawerLoading }
);
const ProjectWhiteboard = dynamic(
  () => import('@/components/projects/ProjectWhiteboard'),
  { loading: ProjectDrawerLoading }
);
const PhaseManagerDrawer = dynamic(
  () =>
    import('@/components/projects/PhaseManagerDrawer').then(
      module => module.PhaseManagerDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectSettingsDrawer = dynamic(
  () => import('@/components/projects/ProjectSettingsDrawer'),
  { loading: ProjectDrawerLoading }
);
const ProjectKpiDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectKpiDrawer').then(
      module => module.ProjectKpiDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProgressSettingsDrawer = dynamic(
  () =>
    import('@/components/projects/ProgressSettingsDrawer').then(
      module => module.ProgressSettingsDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectBudgetDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectBudgetDrawer').then(
      module => module.ProjectBudgetDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectRiskMatrixDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectRiskMatrixDrawer').then(
      module => module.ProjectRiskMatrixDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectWorkloadDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectWorkloadDrawer').then(
      module => module.ProjectWorkloadDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectTimeTrackingDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectTimeTrackingDrawer').then(
      module => module.ProjectTimeTrackingDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectTemplateCatalogDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectTemplateCatalogDrawer').then(
      module => module.ProjectTemplateCatalogDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectAutomationsDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectAutomationsDrawer').then(
      module => module.ProjectAutomationsDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectReportDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectReportDrawer').then(
      module => module.ProjectReportDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectIndicatorsDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectIndicatorsDrawer').then(
      module => module.ProjectIndicatorsDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectDriveDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectDriveDrawer').then(
      module => module.ProjectDriveDrawer
    ),
  { loading: ProjectDrawerLoading }
);

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
  const { hasPermission, token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentViewParam = searchParams?.get('view');

  const canDeleteProjectFromApiPolicy = canDeleteProject(hasPermission);

  const pageData = useProjectPageData(id);
  const {
    project,
    tasks,
    phases,
    activities,
    loading,
    reloadProject,
    createTask,
    updateProject,
    updateTask,
    deleteTask,
    error,
    loadWarning,
    bumpReloadKey,
  } = pageData;

  // ── View switcher (URL ⇄ viewType) ──
  const [viewType, setViewType] = useState<ViewType>('dashboard');
  useEffect(() => {
    if (
      currentViewParam &&
      PROJECT_DETAIL_VIEWS.includes(currentViewParam as ViewType)
    ) {
      setViewType(currentViewParam as ViewType);
    }
  }, [currentViewParam]);

  // ── TaskDetailPanel coordination (URL sync) ──
  const [selectedTask, setSelectedTask] = useState<ProjectTaskRecord | null>(
    null
  );
  useEffect(() => {
    const taskId = searchParams?.get('task');
    if (!taskId || tasks.length === 0) return;
    const task = tasks.find(row => row.id === taskId);
    if (task) setSelectedTask(task);
  }, [searchParams, tasks]);

  const handleOpenTask = (task: ProjectTaskRecord) => {
    setSelectedTask(task);
    const viewQuery = currentViewParam
      ? `view=${encodeURIComponent(currentViewParam)}&`
      : '';
    router.replace(`/plataforma/projects/${id}?${viewQuery}task=${task.id}`);
  };

  const handleCloseTask = () => {
    setSelectedTask(null);
    const viewQuery = currentViewParam
      ? `?view=${encodeURIComponent(currentViewParam)}`
      : '';
    router.replace(`/plataforma/projects/${id}${viewQuery}`);
  };

  const handleTaskUpdated = (updated: ProjectTaskRecord) => {
    setSelectedTask(prev =>
      prev?.id === updated.id ? { ...prev, ...updated } : prev
    );
    void reloadProject();
  };

  const handleDeleteFromPanel = async (taskId: string) => {
    // TaskDetailPanel ya ejecutó y confirmó el DELETE antes de invocar este callback.
    // Este handler solo sincroniza la navegación y el snapshot del proyecto.
    if (selectedTask?.id !== taskId) return;
    handleCloseTask();
    await reloadProject();
  };

  // ── Drawers toggles (UI local) ──
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [taskCreationStatus, setTaskCreationStatus] = useState('todo');
  const [showProjectSettings, setShowProjectSettings] = useState(false);
  const [showProjectActions, setShowProjectActions] = useState(false);
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
  const [showDriveDrawer, setShowDriveDrawer] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

  const handleDeleteProject = async () => {
    if (!token || !id) return;
    setConfirmAction({
      title: 'Eliminar proyecto',
      description: PROJECT_DELETE_CONFIRMATION_DESCRIPTION,
      destructive: true,
      confirmLabel: 'Eliminar proyecto',
      onConfirm: () => confirmProjectDeletion(
        id,
        token,
        () => router.push(PROJECTS_LIST_ROUTE),
      ),
    });
  };

  const projectActions: {
    key: string;
    label: string;
    icon: LucideIcon;
    onSelect: () => void | Promise<void>;
    variant?: 'warning' | 'destructive';
    visible?: boolean;
  }[] = [
    { key: 'whiteboard', label: 'Pizarra', icon: PencilRuler, onSelect: () => setWhiteboardOpen(true) },
    { key: 'phases', label: 'Fases', icon: Edit3, onSelect: () => setShowPhaseManager(true) },
    { key: 'kpis', label: 'KPIs', icon: Target, onSelect: () => setShowKpiDrawer(true) },
    { key: 'progress', label: 'Avance', icon: Sliders, onSelect: () => setShowProgressDrawer(true) },
    { key: 'budget', label: 'Presupuesto', icon: Wallet, onSelect: () => setShowBudgetDrawer(true) },
    { key: 'risks', label: 'Riesgos', icon: ShieldAlert, onSelect: () => setShowRiskDrawer(true) },
    { key: 'workload', label: 'Carga', icon: Users, onSelect: () => setShowWorkloadDrawer(true) },
    { key: 'time', label: 'Horas', icon: Clock, onSelect: () => setShowTimeTrackingDrawer(true) },
    { key: 'templates', label: 'Plantillas', icon: BookTemplate, onSelect: () => setShowTemplateDrawer(true) },
    { key: 'automations', label: 'Automatizaciones', icon: Zap, onSelect: () => setShowAutomationsDrawer(true) },
    { key: 'reports', label: 'Reportes', icon: FileText, onSelect: () => setShowReportDrawer(true) },
    { key: 'indicators', label: 'MGA / CREMA', icon: BarChart3, onSelect: () => setShowIndicatorsDrawer(true) },
    { key: 'drive', label: 'Bóveda y Drive', icon: FolderArchive, onSelect: () => setShowDriveDrawer(true) },
    { key: 'settings', label: 'Editar proyecto', icon: Edit3, onSelect: () => setShowProjectSettings(true), variant: 'warning' as const },
    { key: 'delete', label: 'Eliminar proyecto', icon: Trash2, onSelect: handleDeleteProject, variant: 'destructive' as const, visible: canDeleteProjectFromApiPolicy },
  ].filter((action) => action.visible !== false);

  const renderProjectActionList = (mobile = false) => (
    <div className={clsx(mobile ? 'grid grid-cols-1 gap-2 p-3 sm:grid-cols-2' : 'flex items-center gap-2')}>
      {projectActions.map((action) => {
        const ActionIcon = action.icon;
        const variantClass = action.variant === 'destructive'
          ? 'border-[hsl(var(--destructive)/0.35)] text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)]'
          : action.variant === 'warning'
            ? 'border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))] hover:bg-[hsl(var(--warning-muted))]'
            : 'border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]';
        return (
          <button
            key={action.key}
            type="button"
            onClick={() => {
              setShowProjectActions(false);
              void action.onSelect();
            }}
            className={clsx(
              'flex min-h-10 min-w-0 items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs font-semibold transition-colors',
              variantClass,
              mobile ? 'w-full' : 'whitespace-nowrap',
            )}
          >
            <ActionIcon size={14} aria-hidden="true" className="shrink-0" />
            <span className="truncate">{action.label}</span>
          </button>
        );
      })}
    </div>
  );

  // ── Build context value (stable reference) ──
  const contextValue = useMemo(
    () => ({
      project,
      tasks,
      phases,
      activities,
      loading,
      reloadProject,
      createTask,
      updateProject,
      updateTask,
      deleteTask,
    }),
    [
      project,
      tasks,
      phases,
      activities,
      loading,
      reloadProject,
      createTask,
      updateProject,
      updateTask,
      deleteTask,
    ]
  );

  if (loading) {
    return (
      <ProjectUpdateProvider value={contextValue}>
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]">
          <div className="p-4 space-y-4 animate-pulse">
            <div className="h-10 bg-[hsl(var(--surface-2))] rounded-lg w-1/3" />
            <div className="h-6 bg-[hsl(var(--surface-2))] rounded-lg w-2/3" />
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map(i => (
                <div
                  key={i}
                  className="h-24 bg-[hsl(var(--surface-2))] rounded-lg"
                />
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
          <p className="font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
            {error}
          </p>
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
            {
              label: 'Proyectos',
              icon: LayoutDashboard,
              href: PROJECTS_LIST_ROUTE,
            },
            { label: project?.title || 'Cargando...', icon: Calendar },
          ]}
          viewType={viewType}
          setViewType={setViewType}
          availableViews={PROJECT_DETAIL_VIEWS}
          rightActions={
            <>
            <div className="hidden items-center gap-2 lg:flex">
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setTaskCreationStatus('todo');
                  setShowTaskModal(true);
                }}
                className="px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all flex items-center gap-2"
              >
                <Plus size={14} /> Nueva Tarea
              </button>
              <button
                onClick={() => setWhiteboardOpen(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-2 border border-[hsl(var(--border))]"
              >
                <PencilRuler size={14} /> Pizarra
              </button>
              <button
                onClick={() => setShowPhaseManager(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <Edit3 size={14} /> Fases
              </button>
              <button
                onClick={() => setShowKpiDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <Target size={14} className="text-[hsl(var(--primary))]" /> KPIs
              </button>
              <button
                onClick={() => setShowProgressDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <Sliders size={14} className="text-[hsl(var(--primary))]" />{' '}
                Avance
              </button>
              <button
                onClick={() => setShowBudgetDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <Wallet size={14} className="text-[hsl(var(--primary))]" />{' '}
                Presupuesto
              </button>
              <button
                onClick={() => setShowRiskDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <ShieldAlert
                  size={14}
                  className="text-[hsl(var(--destructive))]"
                />{' '}
                Riesgos
              </button>
              <button
                onClick={() => setShowWorkloadDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <Users size={14} className="text-[hsl(var(--primary))]" /> Carga
              </button>
              <button
                onClick={() => setShowTimeTrackingDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <Clock size={14} className="text-[hsl(var(--primary))]" /> Horas
              </button>
              <button
                onClick={() => setShowTemplateDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <BookTemplate
                  size={14}
                  className="text-[hsl(var(--primary))]"
                />{' '}
                Plantillas
              </button>
              <button
                onClick={() => setShowAutomationsDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <Zap size={14} className="text-[hsl(var(--primary))]" /> Auto
              </button>
              <button
                onClick={() => setShowReportDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <FileText size={14} className="text-[hsl(var(--primary))]" />{' '}
                Reportes
              </button>
              <button
                onClick={() => setShowIndicatorsDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <BarChart3 size={14} className="text-[hsl(var(--primary))]" />{' '}
                MGA / CREMA
              </button>
              <button
                onClick={() => setShowDriveDrawer(true)}
                className="px-3 py-1.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] active:scale-95 transition-all flex items-center gap-1.5 border border-[hsl(var(--border))]"
              >
                <FolderArchive
                  size={14}
                  className="text-[hsl(var(--primary))]"
                />{' '}
                Bóveda & Drive
              </button>
              <button
                onClick={() => setShowProjectSettings(true)}
                className="px-3 py-1.5 bg-[hsl(var(--warning))] text-[hsl(var(--primary-foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:opacity-90 active:scale-95 transition-all flex items-center gap-2"
              >
                <Edit3 size={14} /> Editar
              </button>
              {canDeleteProjectFromApiPolicy && (
                <button
                  onClick={handleDeleteProject}
                  className="px-3 py-1.5 bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] rounded-lg text-2xs font-bold uppercase tracking-wide hover:opacity-90 active:scale-95 transition-all flex items-center gap-2"
                >
                  <Trash2 size={14} /> Eliminar
                </button>
              )}
            </div>
            </div>
            <div className="flex max-w-full items-center gap-2 lg:hidden">
              <button
                type="button"
                onClick={() => {
                  setTaskCreationStatus('todo');
                  setShowTaskModal(true);
                }}
                className="flex min-h-10 shrink-0 items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary-foreground))] shadow-sm transition-colors hover:opacity-90"
              >
                <Plus size={14} aria-hidden="true" /> Nueva tarea
              </button>
              <button
                type="button"
                onClick={() => setShowProjectActions(true)}
                aria-label="Abrir acciones del proyecto"
                aria-haspopup="dialog"
                aria-expanded={showProjectActions}
                className="flex min-h-10 shrink-0 items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--foreground))] transition-colors hover:bg-[hsl(var(--surface-2))]"
              >
                <MoreHorizontal size={16} aria-hidden="true" /> Acciones
              </button>
              <RightPanel
                open={showProjectActions}
                onClose={() => setShowProjectActions(false)}
                title="Acciones del proyecto"
                width="w-full sm:w-[420px]"
                contentClassName="bg-[hsl(var(--surface-1))]"
              >
                {renderProjectActionList(true)}
              </RightPanel>
            </div>
            </>
          }
        />

        {loadWarning && (
          <div role="alert" className="mx-4 mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning-muted))] px-4 py-3 text-sm text-[hsl(var(--warning-text))]">
            <p>{loadWarning}</p>
            <button
              type="button"
              onClick={() => bumpReloadKey()}
              className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-1.5 text-xs font-semibold text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]"
            >
              Reintentar
            </button>
          </div>
        )}

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
          {selectedTask && (
            <TaskDetailPanel
              task={selectedTask}
              projectTitle={project?.title}
              onClose={handleCloseTask}
              onUpdate={handleTaskUpdated}
              onActivityCreated={() => void reloadProject()}
              onDelete={handleDeleteFromPanel}
            />
          )}
        </div>

        <DeferredMount open={Boolean(confirmAction)}>
          <ConfirmActionDrawer
            action={confirmAction}
            onClose={() => setConfirmAction(null)}
          />
        </DeferredMount>

        <DeferredMount open={showTaskModal}>
          <TaskCreationDrawer
            isOpen={showTaskModal}
            defaultStatus={taskCreationStatus}
            onClose={() => setShowTaskModal(false)}
            onSubmit={async data => {
              const ok = await createTask(data);
              if (ok) setShowTaskModal(false);
              return ok;
            }}
          />
        </DeferredMount>
        <DeferredMount open={whiteboardOpen}>
          <ProjectWhiteboard
            project_id={project?.id || id}
            isOpen={whiteboardOpen}
            onClose={() => setWhiteboardOpen(false)}
          />
        </DeferredMount>
        {showPhaseManager && (
          <PhaseManagerDrawer
            projectId={project?.id || id}
            onClose={() => setShowPhaseManager(false)}
          />
        )}

        <DeferredMount open={showProjectSettings}>
          <ProjectSettingsDrawer
            project={project}
            isOpen={showProjectSettings}
            onClose={() => setShowProjectSettings(false)}
            onSave={updateProject}
          />
        </DeferredMount>

        <DeferredMount open={showKpiDrawer}>
          <ProjectKpiDrawer
            projectId={project?.id || id}
            isOpen={showKpiDrawer}
            onClose={() => setShowKpiDrawer(false)}
            onKpisUpdated={() => reloadProject()}
          />
        </DeferredMount>

        <DeferredMount open={showProgressDrawer}>
          <ProgressSettingsDrawer
            projectId={project?.id || id}
            isOpen={showProgressDrawer}
            onClose={() => setShowProgressDrawer(false)}
            currentMode={project?.progress_mode}
            manualProgress={project?.manual_progress}
            currentHealthOverride={project?.health_override}
            onSaved={() => reloadProject()}
          />
        </DeferredMount>

        <DeferredMount open={showBudgetDrawer}>
          <ProjectBudgetDrawer
            projectId={project?.id || id}
            isOpen={showBudgetDrawer}
            onClose={() => setShowBudgetDrawer(false)}
            budgetAllocated={project?.budget_allocated}
            onBudgetUpdated={() => reloadProject()}
          />
        </DeferredMount>

        <DeferredMount open={showRiskDrawer}>
          <ProjectRiskMatrixDrawer
            projectId={project?.id || id}
            isOpen={showRiskDrawer}
            onClose={() => setShowRiskDrawer(false)}
          />
        </DeferredMount>

        <DeferredMount open={showWorkloadDrawer}>
          <ProjectWorkloadDrawer
            projectId={project?.id || id}
            isOpen={showWorkloadDrawer}
            onClose={() => setShowWorkloadDrawer(false)}
            onWorkloadUpdated={() => reloadProject()}
          />
        </DeferredMount>

        <DeferredMount open={showTimeTrackingDrawer}>
          <ProjectTimeTrackingDrawer
            projectId={project?.id || id}
            isOpen={showTimeTrackingDrawer}
            onClose={() => setShowTimeTrackingDrawer(false)}
            tasks={tasks}
            onTimeLogged={() => reloadProject()}
          />
        </DeferredMount>

        <DeferredMount open={showTemplateDrawer}>
          <ProjectTemplateCatalogDrawer
            isOpen={showTemplateDrawer}
            onClose={() => setShowTemplateDrawer(false)}
            activeProjectId={project?.id || id}
            activeProjectTitle={project?.title}
            onProjectCreated={() => reloadProject()}
          />
        </DeferredMount>

        <DeferredMount open={showAutomationsDrawer}>
          <ProjectAutomationsDrawer
            projectId={project?.id || id}
            isOpen={showAutomationsDrawer}
            onClose={() => setShowAutomationsDrawer(false)}
            tasks={tasks}
          />
        </DeferredMount>

        <DeferredMount open={showReportDrawer}>
          <ProjectReportDrawer
            projectId={project?.id || id}
            isOpen={showReportDrawer}
            onClose={() => setShowReportDrawer(false)}
            projectTitle={project?.title}
          />
        </DeferredMount>

        <DeferredMount open={showIndicatorsDrawer}>
          <ProjectIndicatorsDrawer
            projectId={project?.id || id}
            isOpen={showIndicatorsDrawer}
            onClose={() => setShowIndicatorsDrawer(false)}
            onIndicatorUpdated={() => reloadProject()}
          />
        </DeferredMount>

        <DeferredMount open={showDriveDrawer}>
          <ProjectDriveDrawer
            projectId={project?.id || id}
            isOpen={showDriveDrawer}
            onClose={() => setShowDriveDrawer(false)}
            onFileUpdated={() => reloadProject()}
          />
        </DeferredMount>
      </div>
    </ProjectUpdateProvider>
  );
}

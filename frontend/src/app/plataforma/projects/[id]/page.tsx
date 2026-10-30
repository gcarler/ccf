'use client';

import React, { useEffect, useState, useMemo, useCallback } from 'react';
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
  TrendingUp,
  FolderArchive,
  ChevronLeft,
  PanelRightOpen,
  TableProperties,
  List,
  Kanban,
  GanttChart,
  Workflow,
  Gavel,
  BookOpen,
  ClipboardCheck,
  MessageSquare,
  Layers,
  ListTree,
  Tag,
  type LucideIcon,
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { UserMenuDropdown } from '@/components/WorkspaceLayout';
import { DSTooltip } from '@/design';
import ThemeToggle from '@/components/ui/ThemeToggle';
import AppearanceDrawer from '@/components/ui/AppearanceDrawer';
import {
  ProjectManagementHubDrawer,
  type ProjectHubModuleKey,
  type ProjectHubModuleMeta,
} from '@/components/projects/ProjectManagementHubDrawer';
import type { ConfirmActionState } from '@/components/ConfirmActionDrawer';
import {
  DeferredMount,
  ProjectDrawerLoading,
} from '@/components/projects/DeferredMount';
import { ProjectUpdateProvider } from '@/context/ProjectUpdateContext';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import { ProjectViewsContent } from '@/components/projects/ProjectViewsContent';
import ProjectContextPanel from '@/components/projects/ProjectContextPanel';
import { useProjectPageData } from '@/hooks/useProjectPageData';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectTaskRecord } from '@/types/projects';

const TOOLBAR_ICON_BUTTON_CLASS =
  'flex size-9 shrink-0 items-center justify-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] transition-colors hover:bg-[hsl(var(--surface-2))] active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]';

// Hub unificado de gestión: metadatos de los módulos de control.
const PROJECT_HUB_MODULE_META: ProjectHubModuleMeta[] = [
  { key: 'components', label: 'Componentes EDT', icon: Layers },
  { key: 'wbs', label: 'EDT / WBS y Diccionario', icon: ListTree },
  { key: 'labels', label: 'Etiquetas', icon: Tag },
  { key: 'kpis', label: 'KPIs', icon: Target },
  { key: 'progress', label: 'Avance', icon: Sliders },
  { key: 'budget', label: 'Presupuesto', icon: Wallet },
  { key: 'risks', label: 'Riesgos', icon: ShieldAlert },
  { key: 'workload', label: 'Carga', icon: Users },
  { key: 'time', label: 'Horas', icon: Clock },
  { key: 'templates', label: 'Plantillas', icon: BookTemplate },
  { key: 'automations', label: 'Automatizaciones', icon: Zap },
  { key: 'reports', label: 'Reportes', icon: FileText },
  { key: 'indicators', label: 'Indicadores y Resultados', icon: BarChart3 },
  { key: 'ccb', label: 'Control de Cambios (CCB)', icon: Gavel },
  { key: 'pmo', label: 'Matriz PMO', icon: BarChart3 },
  { key: 'evm', label: 'Valor Ganado (EVM / CPI)', icon: TrendingUp },
  { key: 'drive', label: 'Drive', icon: FolderArchive },
  { key: 'governance', label: 'Gobernanza PMI', icon: ClipboardCheck },
];

const PROJECT_DETAIL_VIEWS: ViewType[] = [
  'dashboard',
  'table',
  'list',
  'board',
  'kanban',
  'calendar',
  'gantt',
  'workflow',
  'wiki',
  'chat',
];

// Iconos/labels de las vistas del detalle, alineados con ViewSwitcher
// para que la CommandPalette represente la misma navegación con los mismos
// símbolos que la barra del workspace.
const PROJECT_DETAIL_VIEW_META: Partial<Record<ViewType, { label: string; icon: LucideIcon }>> = {
  dashboard: { label: 'Resumen', icon: LayoutDashboard },
  table: { label: 'Tabla', icon: TableProperties },
  list: { label: 'Lista', icon: List },
  board: { label: 'Tablero', icon: Kanban },
  kanban: { label: 'Kanban', icon: Kanban },
  calendar: { label: 'Calendario', icon: Calendar },
  gantt: { label: 'Gantt', icon: GanttChart },
  workflow: { label: 'Workflow', icon: Workflow },
  wiki: { label: 'Wiki', icon: BookOpen },
  chat: { label: 'Chat', icon: MessageSquare },
};

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
const ProjectChangeControlDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectChangeControlDrawer').then(
      module => module.ProjectChangeControlDrawer
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
const ProjectLifecycleGovernanceDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectLifecycleGovernanceDrawer').then(
      module => module.ProjectLifecycleGovernanceDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectEVMDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectEVMDrawer').then(
      module => module.ProjectEVMDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectComponentDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectComponentDrawer').then(
      module => module.ProjectComponentDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectLabelsDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectLabelsDrawer').then(
      module => module.ProjectLabelsDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectWBSDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectWBSDrawer').then(
      module => module.ProjectWBSDrawer
    ),
  { loading: ProjectDrawerLoading }
);
const ProjectPMOPortfolioDrawer = dynamic(
  () =>
    import('@/components/projects/ProjectPMOPortfolioDrawer').then(
      module => module.ProjectPMOPortfolioDrawer
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
    pageData.updateTaskLocal(updated);
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
  const [showAppearance, setShowAppearance] = useState(false);
  const [whiteboardOpen, setWhiteboardOpen] = useState(false);
  const [showPhaseManager, setShowPhaseManager] = useState(false);
  // Hub de gestión: una sola pestaña activa dentro de un único panel.
  const [hubState, setHubState] = useState<{
    open: ProjectHubModuleKey[];
    active: ProjectHubModuleKey | null;
  }>({ open: [], active: null });
  const hubOpen = hubState.open.length > 0;

  const openHubModule = useCallback((key: ProjectHubModuleKey) => {
    setHubState(prev => ({
      open: prev.open.includes(key) ? prev.open : [...prev.open, key],
      active: key,
    }));
  }, []);

  const closeHubModule = useCallback((key: ProjectHubModuleKey) => {
    setHubState(prev => {
      const open = prev.open.filter(row => row !== key);
      return {
        open,
        active:
          prev.active === key
            ? open[open.length - 1] ?? null
            : prev.active,
      };
    });
  }, []);

  const closeHub = useCallback(() => {
    setHubState({ open: [], active: null });
  }, []);

  // ── Command Palette (S3/S4, rev_ui_13102026.md §5): comandos Ctrl+K que
  // reflejan la navegación del detalle: cambiar de vista, crear actividad
  // y abrir los módulos clave del Hub (KPIs, EVM, Riesgos, Presupuesto, Drive).
  const changeDetailView = useCallback((view: ViewType) => {
    setViewType(view);
    const viewParams = new URLSearchParams(searchParams?.toString() ?? '');
    viewParams.set('view', view);
    router.replace(`/plataforma/projects/${id}?${viewParams.toString()}`);
  }, [id, router, searchParams]);

  const detailViewCommands = useMemo(
    () =>
      PROJECT_DETAIL_VIEWS.map((view) => ({
        id: `project-detail-view-${view}`,
        label: `Vista: ${PROJECT_DETAIL_VIEW_META[view]?.label ?? view}`,
        description: 'Cambiar de vista en el detalle del proyecto',
        icon: PROJECT_DETAIL_VIEW_META[view]?.icon,
        group: 'Vistas del proyecto',
        action: () => changeDetailView(view),
      })),
    [changeDetailView]
  );

  const detailActionCommands = useMemo(
    () => [
      {
        id: 'project-detail-new-activity',
        label: 'Nueva actividad',
        description: 'Crear una tarea en este proyecto',
        icon: Plus as LucideIcon,
        group: 'Acciones',
        action: () => setShowTaskModal(true),
      },
      {
        id: 'project-detail-hub-components',
        label: 'Abrir Componentes EDT',
        description: 'Estructura de Desglose de Trabajo (Nivel 2 WBS/EDT)',
        icon: Layers,
        group: 'Hub de gestión',
        action: () => openHubModule('components'),
      },
      {
        id: 'project-detail-hub-wbs',
        label: 'Abrir EDT / WBS y Diccionario',
        description: 'Diccionario de la EDT, codificación jerárquica y Regla del 100%',
        icon: ListTree,
        group: 'Hub de gestión',
        action: () => openHubModule('wbs'),
      },
      {
        id: 'project-detail-hub-pmo',
        label: 'Abrir Matriz PMO',
        description: 'Diagnóstico multi-proyecto CPI vs SPI y portafolio PMO',
        icon: BarChart3,
        group: 'Hub de gestión',
        action: () => openHubModule('pmo'),
      },
      {
        id: 'project-detail-hub-kpis',
        label: 'Abrir KPIs',
        description: 'Indicadores clave de desempeño del proyecto',
        icon: Target,
        group: 'Hub de gestión',
        action: () => openHubModule('kpis'),
      },
      {
        id: 'project-detail-hub-evm',
        label: 'Abrir EVM (Valor Ganado)',
        description: 'Curva S, CPI/SPI y salud del proyecto',
        icon: TrendingUp,
        group: 'Hub de gestión',
        action: () => openHubModule('evm'),
      },
      {
        id: 'project-detail-hub-risks',
        label: 'Abrir Riesgos',
        description: 'Matriz RAID de riesgos y supuestos',
        icon: ShieldAlert,
        group: 'Hub de gestión',
        action: () => openHubModule('risks'),
      },
      {
        id: 'project-detail-hub-budget',
        label: 'Abrir Presupuesto',
        description: 'Gastos, saldo y desglose de presupuesto',
        icon: Wallet,
        group: 'Hub de gestión',
        action: () => openHubModule('budget'),
      },
      {
        id: 'project-detail-hub-drive',
        label: 'Abrir Drive',
        description: 'Archivos y carpetas del proyecto',
        icon: FolderArchive,
        group: 'Hub de gestión',
        action: () => openHubModule('drive'),
      },
      {
        id: 'project-detail-hub-labels',
        label: 'Abrir Gestor de Etiquetas',
        description: 'Crear, renombrar y organizar etiquetas del proyecto',
        icon: Tag,
        group: 'Hub de gestión',
        action: () => openHubModule('labels'),
      },
    ],
    [openHubModule]
  );

  useRegisterCommands(`project-detail-${id}`, [...detailViewCommands, ...detailActionCommands]);

  const [showContextPanel, setShowContextPanel] = useState(true);
  const [isContextMaximized, setIsContextMaximized] = useState(false);
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
    { key: 'components', label: 'Componentes EDT', icon: Layers, onSelect: () => openHubModule('components') },
    { key: 'wbs', label: 'Desglose de Paquetes WBS', icon: ListTree, onSelect: () => openHubModule('wbs') },
    { key: 'pmo', label: 'Matriz PMO', icon: BarChart3, onSelect: () => openHubModule('pmo') },
    { key: 'labels', label: 'Etiquetas', icon: Tag, onSelect: () => openHubModule('labels') },
    { key: 'kpis', label: 'KPIs', icon: Target, onSelect: () => openHubModule('kpis') },
    { key: 'progress', label: 'Avance', icon: Sliders, onSelect: () => openHubModule('progress') },
    { key: 'budget', label: 'Presupuesto', icon: Wallet, onSelect: () => openHubModule('budget') },
    { key: 'risks', label: 'Riesgos', icon: ShieldAlert, onSelect: () => openHubModule('risks') },
    { key: 'workload', label: 'Carga', icon: Users, onSelect: () => openHubModule('workload') },
    { key: 'time', label: 'Horas', icon: Clock, onSelect: () => openHubModule('time') },
    { key: 'templates', label: 'Plantillas', icon: BookTemplate, onSelect: () => openHubModule('templates') },
    { key: 'automations', label: 'Automatizaciones', icon: Zap, onSelect: () => openHubModule('automations') },
    { key: 'reports', label: 'Reportes', icon: FileText, onSelect: () => openHubModule('reports') },
    { key: 'indicators', label: 'Indicadores y Resultados', icon: BarChart3, onSelect: () => openHubModule('indicators') },
    { key: 'evm', label: 'Valor Ganado (EVM / CPI)', icon: TrendingUp, onSelect: () => openHubModule('evm') },
    { key: 'drive', label: 'Drive', icon: FolderArchive, onSelect: () => openHubModule('drive') },
    { key: 'governance', label: 'Gobernanza PMI', icon: ClipboardCheck, onSelect: () => openHubModule('governance') },
    { key: 'settings', label: 'Editar proyecto', icon: Edit3, onSelect: () => setShowProjectSettings(true), variant: 'warning' as const },
    { key: 'delete', label: 'Eliminar proyecto', icon: Trash2, onSelect: handleDeleteProject, variant: 'destructive' as const, visible: canDeleteProjectFromApiPolicy },
  ].filter((action) => action.visible !== false);

  const moduleRenderers = {
    components: () => (
      <ProjectComponentDrawer
        embedded
        projectId={project?.id || id}
        projectTitle={project?.title}
        isOpen
        onClose={() => closeHubModule('components')}
        onUpdated={() => reloadProject()}
      />
    ),
    wbs: () => (
      <ProjectWBSDrawer
        embedded
        projectId={project?.id || id}
        projectTitle={project?.title}
        isOpen
        onClose={() => closeHubModule('wbs')}
      />
    ),
    labels: () => (
      <ProjectLabelsDrawer
        projectId={project?.id || id}
        isOpen
        embedded
        onClose={() => closeHubModule('labels')}
        onUpdated={() => reloadProject()}
      />
    ),
    kpis: () => (
      <ProjectKpiDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('kpis')}
        onKpisUpdated={() => reloadProject()}
      />
    ),
    progress: () => (
      <ProgressSettingsDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('progress')}
        currentMode={project?.progress_mode}
        manualProgress={project?.manual_progress}
        currentHealthOverride={project?.health_override}
        onSaved={() => reloadProject()}
      />
    ),
    budget: () => (
      <ProjectBudgetDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('budget')}
        budgetAllocated={project?.budget_allocated}
        onBudgetUpdated={() => reloadProject()}
      />
    ),
    risks: () => (
      <ProjectRiskMatrixDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('risks')}
      />
    ),
    workload: () => (
      <ProjectWorkloadDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('workload')}
        onWorkloadUpdated={() => reloadProject()}
      />
    ),
    time: () => (
      <ProjectTimeTrackingDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('time')}
        tasks={tasks}
        onTimeLogged={() => reloadProject()}
      />
    ),
    templates: () => (
      <ProjectTemplateCatalogDrawer
        isOpen
        onClose={() => closeHubModule('templates')}
        activeProjectId={project?.id || id}
        activeProjectTitle={project?.title}
        onProjectCreated={() => reloadProject()}
      />
    ),
    automations: () => (
      <ProjectAutomationsDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('automations')}
        tasks={tasks}
      />
    ),
    reports: () => (
      <ProjectReportDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('reports')}
        projectTitle={project?.title}
      />
    ),
    indicators: () => (
      <ProjectIndicatorsDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('indicators')}
        onIndicatorUpdated={() => reloadProject()}
      />
    ),
    evm: () => (
      <ProjectEVMDrawer
        projectId={project?.id || id}
        projectTitle={project?.title}
        isOpen
        onClose={() => closeHubModule('evm')}
      />
    ),
    drive: () => (
      <ProjectDriveDrawer
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('drive')}
        onFileUpdated={() => reloadProject()}
      />
    ),
    governance: () => (
      <ProjectLifecycleGovernanceDrawer
        embedded
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('governance')}
      />
    ),
    ccb: () => (
      <ProjectChangeControlDrawer
        embedded
        projectId={project?.id || id}
        isOpen
        onClose={() => closeHubModule('ccb')}
      />
    ),
    pmo: () => (
      <ProjectPMOPortfolioDrawer
        embedded
        isOpen
        onClose={() => closeHubModule('pmo')}
      />
    ),
  } satisfies Partial<Record<ProjectHubModuleKey, () => React.ReactNode>>;

  const wbsAveragePct = useMemo(() => {
    if (tasks.length === 0) return 0;
    const total = tasks.reduce((acc, task) => {
      const st = (task.status || '').toLowerCase();
      if (st === 'completed' || st === 'done') return acc + 100;
      if (st === 'in_progress' || st === 'review') return acc + 50;
      return acc;
    }, 0);
    return Math.round(total / tasks.length);
  }, [tasks]);

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

  if (loading && !project) {
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
            className="rounded-md border border-[hsl(var(--border))] px-[calc(0.75rem+var(--density-pad-x-delta,0px))] py-[calc(0.375rem+var(--density-pad-y-delta,0px))] text-xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] transition-colors hover:bg-[hsl(var(--surface-2))]"
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
            <div className="flex min-w-0 max-w-full flex-wrap items-center justify-end gap-1.5">
              {viewType !== 'chat' && !selectedTask && !showContextPanel && (
                <DSTooltip content="Mostrar panel de contexto" side="bottom">
                  <button
                    type="button"
                    onClick={() => setShowContextPanel(true)}
                    aria-label="Mostrar panel de contexto"
                    className={TOOLBAR_ICON_BUTTON_CLASS}
                  >
                    <PanelRightOpen size={15} aria-hidden="true" className="text-[hsl(var(--primary))]" />
                  </button>
                </DSTooltip>
              )}
              <button
                type="button"
                onClick={() => {
                  setTaskCreationStatus('todo');
                  setShowTaskModal(true);
                }}
                aria-label="Nueva actividad"
                className="flex min-h-9 shrink-0 items-center gap-1.5 rounded-lg bg-[hsl(var(--primary))] px-[calc(0.625rem+var(--density-pad-x-delta,0px))] py-[calc(0.375rem+var(--density-pad-y-delta,0px))] text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary-foreground))] shadow-sm transition-colors hover:opacity-90 active:scale-95"
              >
                <Plus size={14} aria-hidden="true" />
                <span className="hidden md:inline">Nueva actividad</span>
              </button>
              {/* Selector de tema (claro/oscuro/apariencia) junto al perfil */}
              <ThemeToggle variant="pill" onOpenAppearance={() => setShowAppearance(true)} />
              <div className="w-px h-4 bg-[hsl(var(--border))] mx-0.5 shrink-0" />
              <UserMenuDropdown onOpenAppearance={() => setShowAppearance(true)} />
            </div>
          }
        />

        <div
          data-testid="project-detail-pmi-control-bar"
          className="flex flex-wrap items-center justify-between gap-2 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.45)] px-4 py-1.5 shrink-0"
        >
          <div className="flex flex-wrap items-center gap-3 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
            <span className="font-bold text-[hsl(var(--foreground))]">Control PMI §4.3 &amp; §4.5</span>
            <span>Etapa / Estado: {project?.status || 'active'}</span>
            <span>Avance WBS (0/50/100): {wbsAveragePct}%</span>
            <span>Paquetes WBS: {tasks.length} paquete(s)</span>
          </div>
        </div>

        {/* Apariencia: drawer de tema claro/oscuro para el detalle de Proyectos */}
        <AppearanceDrawer isOpen={showAppearance} onClose={() => setShowAppearance(false)} />

        {loadWarning && (
          <div role="alert" className="mx-4 mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning-muted))] px-4 py-3 text-sm text-[hsl(var(--warning-text))]">
            <p>{loadWarning}</p>
            <button
              type="button"
              onClick={() => bumpReloadKey()}
              className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-[calc(0.75rem+var(--density-pad-x-delta,0px))] py-[calc(0.375rem+var(--density-pad-y-delta,0px))] text-xs font-semibold text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]"
            >
              Reintentar
            </button>
          </div>
        )}

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
          <div className={clsx("min-h-0 min-w-0 flex-1 overflow-hidden", isContextMaximized && "hidden")}>
            <ProjectViewsContent
              viewType={viewType}
              onOpenTask={handleOpenTask}
              onTaskUpdated={handleTaskUpdated}
              onActivityCreated={() => void reloadProject()}
              onDeleteTask={handleDeleteFromPanel}
              setShowTaskModal={setShowTaskModal}
              setWhiteboardOpen={setWhiteboardOpen}
              onOpenTool={openHubModule}
              setTaskCreationStatus={setTaskCreationStatus}
              onManageComponents={() => openHubModule('components')}
            />
          </div>
          {viewType !== 'chat' && !selectedTask && showContextPanel && (
            <ProjectContextPanel
              tools={projectActions}
              onOpenTask={handleOpenTask}
              onClose={() => {
                setShowContextPanel(false);
                setIsContextMaximized(false);
              }}
              isMaximized={isContextMaximized}
              onToggleMaximize={() => setIsContextMaximized((prev) => !prev)}
            />
          )}
          {viewType !== 'chat' && !selectedTask && !showContextPanel && !isContextMaximized && (
            <button
              type="button"
              onClick={() => setShowContextPanel(true)}
              aria-label="Abrir panel de contexto"
              className="fixed right-0 top-1/2 -translate-y-1/2 z-30 flex items-center gap-1 rounded-l-lg border-y border-l border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-1.5 py-3 text-xs font-semibold text-[hsl(var(--text-secondary))] shadow-md hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--primary))] transition-colors"
              title="Abrir panel de contexto"
            >
              <ChevronLeft size={16} />
              <span className="[writing-mode:vertical-rl] rotate-180 text-2xs uppercase tracking-wider font-bold">Contexto</span>
            </button>
          )}
          {selectedTask && (
            <TaskDetailPanel
              task={selectedTask}
              projectTitle={project?.title}
              onClose={handleCloseTask}
              onUpdate={handleTaskUpdated}
              onActivityCreated={() => void reloadProject()}
              onDelete={handleDeleteFromPanel}
              onVerRutaClick={() => changeDetailView('workflow')}
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
            projectId={project?.id || id}
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

        <DeferredMount open={hubOpen}>
          <ProjectManagementHubDrawer
            isOpen={hubOpen}
            openModules={hubState.open}
            moduleMeta={PROJECT_HUB_MODULE_META}
            activeModule={hubState.active}
            onActivateModule={openHubModule}
            onCloseModule={closeHubModule}
            onCloseHub={closeHub}
            moduleRenderers={moduleRenderers}
          />
        </DeferredMount>

      </div>
    </ProjectUpdateProvider>
  );
}

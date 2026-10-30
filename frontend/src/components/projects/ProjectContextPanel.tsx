"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, Bell, CheckCircle2, ChevronLeft, ExternalLink, Inbox, Maximize2, MessageSquare, Minimize2, Minus, Users, Wrench, X } from "lucide-react";
import clsx from "clsx";
import { useProjectUpdate } from "@/context/ProjectUpdateContext";
import { useAuth } from "@/context/AuthContext";
import ProjectActivityFeed from "@/components/projects/ProjectActivityFeed";
import ProjectChatPanel from "@/components/projects/ProjectChatPanel";
import { useNotifications } from "@/hooks/useNotifications";
import { useProjectInbox } from "@/hooks/useProjectInbox";
import { useWorkspaceSocket } from "@/hooks/useWorkspaceSocket";
import { DSTooltip } from "@/design";
import type { WsEvent } from "@/types/directMessages";
import type { ProjectTaskRecord } from "@/types/projects";
import { useResizablePanel } from "@/hooks/useResizablePanel";
import { PanelResizeHandle } from "@/components/ui/PanelResizeHandle";
import { formatDate } from "@/lib/format";

type ContextTab = "chat" | "activity" | "details" | "inbox" | "tools";

interface ProjectContextPanelProps {
  className?: string;
  defaultTab?: ContextTab;
  onOpenTask?: (task: ProjectTaskRecord) => void;
  onClose?: () => void;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  isMaximized?: boolean;
  onToggleMaximize?: () => void;
  isMinimized?: boolean;
  onToggleMinimize?: () => void;
  /** Herramientas del proyecto: viven en la pestaña Herramientas del sidebar derecho (TKT-PROJECTS-RIGHT-SIDEBAR-TOOLS-NO-PROFILE-ICONS-01). */
  tools?: Array<{
    key: string;
    label: string;
    icon?: React.ElementType;
    onSelect?: () => void | Promise<void>;
    variant?: "warning" | "destructive";
  }>;
  /** Notifica el ancho actual (px) al montar y cada vez que el usuario redimensiona el panel (coexistencia con paneles adyacentes). */
  onWidthChange?: (width: number) => void;
}

/** Orden por defecto (TKT-PRO-SCROLLBARS-AND-MOVABLE-TABS-01): donde reordenar las pestañas sigue respetando esta secuencia base. */
const DEFAULT_TABS: Array<{ id: ContextTab; label: string; icon: typeof MessageSquare }> = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "inbox", label: "Inbox", icon: Inbox },
  { id: "tools", label: "Herramientas", icon: Wrench },
  { id: "details", label: "Detalles", icon: Users },
  { id: "activity", label: "Historia", icon: Activity },
];
const DEFAULT_TAB_ORDER = DEFAULT_TABS.map((tab) => tab.id);
const TAB_BY_ID = new Map(DEFAULT_TABS.map((tab) => [tab.id, tab]));
const TAB_ID_SET = new Set<ContextTab>(DEFAULT_TAB_ORDER);

/**
 * Preferencia de orden de pestañas por usuario (persistida en localStorage).
 * Debe validar contra los IDs canónicos: un valor corrupto o parcial no debe
 * romper el panel (merge con el orden por defecto para conservar todo).
 */
const TABS_ORDER_STORAGE_KEY = "workspace:project_context_tabs_order";

function sanitizeTabOrder(raw: unknown): ContextTab[] {
  if (!Array.isArray(raw)) return [...DEFAULT_TAB_ORDER];
  const seen = new Set<ContextTab>();
  for (const item of raw) {
    if (typeof item === "string" && TAB_ID_SET.has(item as ContextTab)) {
      seen.add(item as ContextTab);
    }
  }
  const order = raw.filter((item): item is ContextTab =>
    typeof item === "string" && TAB_ID_SET.has(item as ContextTab) && seen.has(item as ContextTab),
  );
  for (const id of DEFAULT_TAB_ORDER) {
    if (!order.includes(id)) order.push(id);
  }
  return order;
}

function readStoredTabOrder(): ContextTab[] {
  if (typeof window === "undefined") return [...DEFAULT_TAB_ORDER];
  try {
    return sanitizeTabOrder(JSON.parse(localStorage.getItem(TABS_ORDER_STORAGE_KEY) ?? ""));
  } catch {
    return [...DEFAULT_TAB_ORDER];
  }
}

export default function ProjectContextPanel({
  className,
  defaultTab,
  onOpenTask,
  onClose,
  isExpanded: controlledExpanded,
  onToggleExpand,
  isMaximized: controlledMaximized,
  onToggleMaximize,
  isMinimized: controlledMinimized,
  onToggleMinimize,
  tools,
  onWidthChange,
}: ProjectContextPanelProps) {
  const { project, tasks, activities, reloadProject } = useProjectUpdate();
  const { token } = useAuth();
  // Orden personalizado de pestañas, oculta en localStorage (TKT-PRO-SCROLLBARS-AND-MOVABLE-TABS-01)
  const [tabOrder, setTabOrder] = useState<ContextTab[]>(() => readStoredTabOrder());
  // Primera pestaña visible activa por defecto: 'chat' salvo que defaultTab
  // llegue explícito o el usuario haya reordenado (su primera pestaña gana).
  const [activeTab, setActiveTab] = useState<ContextTab>(() => {
    if (defaultTab) return defaultTab;
    const stored = readStoredTabOrder();
    return (tools?.length ? stored[0] : stored.find((id) => id !== "tools")) ?? "chat";
  });
  const [dragTab, setDragTab] = useState<ContextTab | null>(null);
  const [dragOverTab, setDragOverTab] = useState<ContextTab | null>(null);
  const [toolsSearch, setToolsSearch] = useState("");
  const [internalMaximized, setInternalMaximized] = useState(false);
  const [internalMinimized, setInternalMinimized] = useState(false);
  const panelRef = useRef<HTMLElement>(null);

  const isMaximized = controlledMaximized ?? controlledExpanded ?? internalMaximized;
  const isMinimized = controlledMinimized !== undefined ? controlledMinimized : internalMinimized;

  const toggleMaximize = onToggleMaximize ?? onToggleExpand ?? (() => setInternalMaximized((v) => !v));
  const toggleMinimize = onToggleMinimize ?? (() => setInternalMinimized((v) => !v));

  const resize = useResizablePanel({
    storageKey: "workspace:s3_width",
    defaultWidth: 380,
    reservedWidth: 320,
    constrainToParent: true,
    panelRef,
    enabled: !isMaximized && !isMinimized,
  });

  const tabRefs = useRef<Partial<Record<ContextTab, HTMLButtonElement | null>>>({});

  // Notifica el ancho actual del sidebar para observadores opcionales del layout.
  useEffect(() => {
    onWidthChange?.(resize.width);
  }, [resize.width, onWidthChange]);
  const { items: projectInbox, unreadCount: projectInboxUnread, loading: inboxLoading, error: inboxError, refresh: refreshProjectInbox, markAsRead } = useProjectInbox(project?.id);
  const { notifications } = useNotifications();
  const handleInboxSocketEvent = useCallback((payload: WsEvent) => {
    if (project?.id && isProjectInboxEvent(payload, project.id)) {
      void refreshProjectInbox();
    }
  }, [project?.id, refreshProjectInbox]);

  useWorkspaceSocket({
    rooms: project?.id ? [`project_${project.id}`] : [],
    enabled: Boolean(token && project?.id && activeTab === "inbox"),
    token,
    onEvent: handleInboxSocketEvent,
  });
  const globalUnread = notifications.filter((notification) => !notification.read).length;

  const visibleTabs = (tools?.length ? tabOrder : tabOrder.filter((id) => id !== "tools"))
    .map((id) => TAB_BY_ID.get(id))
    .filter((tab): tab is NonNullable<typeof tab> => Boolean(tab));

  /** Reordena 'from' a la posición exacta de 'to' (splice: las demás siguen su curso) y persiste. */
  const moveTabTo = useCallback((from: ContextTab, to: ContextTab) => {
    if (from === to) return;
    setTabOrder((previous) => {
      if (!previous.includes(from) || !previous.includes(to)) return previous;
      const next = previous.filter((id) => id !== from);
      next.splice(next.indexOf(to), 0, from);
      try {
        localStorage.setItem(TABS_ORDER_STORAGE_KEY, JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const persistTabOrder = useCallback((next: ContextTab[]) => {
    setTabOrder(next);
    try {
      localStorage.setItem(TABS_ORDER_STORAGE_KEY, JSON.stringify(next));
    } catch {}
  }, []);

  const handleTabDragStart = useCallback((event: React.DragEvent<HTMLButtonElement>, id: ContextTab) => {
    setDragTab(id);
    event.dataTransfer.effectAllowed = "move";
    try {
      event.dataTransfer.setData("text/plain", id);
    } catch {}
  }, []);

  const handleTabDragOver = useCallback((event: React.DragEvent<HTMLButtonElement>, id: ContextTab) => {
    if (dragTab && dragTab !== id) {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      setDragOverTab(id);
    }
  }, [dragTab]);

  const handleTabDragLeave = useCallback((event: React.DragEvent<HTMLButtonElement>, id: ContextTab) => {
    setDragOverTab((current) => (current === id ? null : current));
  }, []);

  const handleTabDrop = useCallback((event: React.DragEvent<HTMLButtonElement>, id: ContextTab) => {
    event.preventDefault();
    if (dragTab) moveTabTo(dragTab, id);
    setDragOverTab(null);
  }, [dragTab, moveTabTo]);

  const handleTabDragEnd = useCallback(() => {
    setDragTab(null);
    setDragOverTab(null);
  }, []);

  const focusTab = (tab: ContextTab) => {
    setActiveTab(tab);
    tabRefs.current[tab]?.focus();
  };

  const handleTabKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, tab: ContextTab) => {
    const currentIndex = visibleTabs.findIndex((item) => item.id === tab);
    if ((event.key === "ArrowLeft" || event.key === "ArrowRight") && event.altKey && !event.shiftKey && !event.ctrlKey && !event.metaKey) {
      // Reordenamiento accesible: Alt+Flechas mueve la pestaña en el orden global sin robar el foco (TKT-PRO-SCROLLBARS-AND-MOVABLE-TABS-01).
      event.preventDefault();
      const orderIndex = tabOrder.indexOf(tab);
      const targetIndex = event.key === "ArrowLeft" ? orderIndex - 1 : orderIndex + 1;
      if (targetIndex >= 0 && targetIndex < tabOrder.length) {
        const next = [...tabOrder];
        next.splice(orderIndex, 1);
        next.splice(targetIndex, 0, tab);
        persistTabOrder(next);
      }
      return;
    }
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      focusTab(visibleTabs[(currentIndex + 1) % visibleTabs.length].id);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      focusTab(visibleTabs[(currentIndex - 1 + visibleTabs.length) % visibleTabs.length].id);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusTab(visibleTabs[0].id);
    } else if (event.key === "End") {
      event.preventDefault();
      focusTab(visibleTabs[visibleTabs.length - 1].id);
    }
  };

  const isTaskCompleted = (task: ProjectTaskRecord) => task.status === "completed" || task.status === "done";
  const openTasks = tasks.filter((task) => !isTaskCompleted(task)).length;
  const completedTasks = tasks.length - openTasks;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const overdueTasks = tasks.filter((task) => {
    if (isTaskCompleted(task) || !task.due_date) return false;
    const dueDate = new Date(`${task.due_date.slice(0, 10)}T00:00:00`);
    return !Number.isNaN(dueDate.getTime()) && dueDate.getTime() < today.getTime();
  }).length;
  const blockedOrUrgentTasks = tasks.filter((task) =>
    !isTaskCompleted(task) && (task.status === "blocked" || task.priority === "urgent")
  ).length;
  const scopeCompletion = tasks.length === 0 ? 0 : Math.round((completedTasks / tasks.length) * 100);
  const distributedTaskBudget = tasks.reduce((total, task) => total + (task.budget_allocated ?? 0), 0);
  const projectBudget = project?.budget_allocated;
  const budgetVariance = projectBudget == null ? null : projectBudget - distributedTaskBudget;
  const budgetStatus = budgetVariance == null
    ? "BAC no definido"
    : budgetVariance < -0.01
      ? "Exceso sobre BAC"
      : budgetVariance > 0.01
        ? "Reserva por Distribuir"
        : "Presupuesto Cuadrado";
  const filteredTools = useMemo(() => {
    const query = toolsSearch.trim().toLocaleLowerCase();
    return (tools ?? []).filter((tool) => tool.label.toLocaleLowerCase().includes(query));
  }, [tools, toolsSearch]);

  if (isMinimized) {
    return (
      <aside
        aria-label="Contexto del proyecto"
        className={clsx(
          "flex min-h-0 w-12 shrink-0 flex-col items-center border-t border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] py-2.5 space-y-2 lg:w-14 lg:border-l lg:border-t-0 select-none",
          className
        )}
      >
        <DSTooltip content="Restaurar panel de contexto" side="left">
          <button
            type="button"
            onClick={toggleMinimize}
            aria-label="Restaurar panel de contexto"
            className="flex h-8 w-8 items-center justify-center rounded-md text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--text-primary))] transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
        </DSTooltip>

        <div className="w-6 border-b border-[hsl(var(--border))]" />

        <div className="flex flex-col items-center space-y-2 w-full px-1" role="tablist" aria-label="Contexto del proyecto (minimizado)">
          {visibleTabs.map(({ id, label, icon: Icon }) => (
            <DSTooltip key={id} content={label} side="left">
              <button
                key={id}
                type="button"
                role="tab"
                draggable={true}
                aria-label={id === "inbox" && projectInboxUnread > 0 ? `${label}, ${projectInboxUnread} sin leer` : label}
                aria-selected={activeTab === id}
                aria-keyshortcuts="Alt+ArrowLeft Alt+ArrowRight"
                onDragStart={(event) => handleTabDragStart(event, id)}
                onDragOver={(event) => handleTabDragOver(event, id)}
                onDragLeave={(event) => handleTabDragLeave(event, id)}
                onDrop={(event) => handleTabDrop(event, id)}
                onDragEnd={handleTabDragEnd}
                onClick={() => {
                  setActiveTab(id);
                  toggleMinimize();
                }}
                className={clsx(
                  "relative flex h-8 w-8 items-center justify-center rounded-md transition-colors cursor-grab active:cursor-grabbing",
                  activeTab === id
                    ? "bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"
                    : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))]",
                  dragOverTab === id && dragTab && dragTab !== id && "ring-1 ring-[hsl(var(--primary))]",
                )}
              >
                <Icon size={16} />
                {id === "inbox" && projectInboxUnread > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[hsl(var(--destructive))] text-[9px] font-bold text-[hsl(var(--primary-foreground))]">
                    {projectInboxUnread}
                  </span>
                )}
              </button>
            </DSTooltip>
          ))}
        </div>

        <div className="flex-1" />

        {onClose && (
          <DSTooltip content="Cerrar panel de contexto" side="left">
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar panel de contexto"
              className="flex h-8 w-8 items-center justify-center rounded-md text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--destructive)/0.1)] hover:text-[hsl(var(--danger-text))] transition-colors mb-2"
            >
              <X size={15} />
            </button>
          </DSTooltip>
        )}
      </aside>
    );
  }

  return (
    <aside
      ref={panelRef}
      aria-label="Contexto del proyecto"
      className={clsx(
        "relative flex min-h-0 shrink-0 flex-col overflow-hidden border-t border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] lg:border-l lg:border-t-0",
        resize.dragging ? "select-none" : "transition-[width] duration-150 ease-out",
        isMaximized
          ? "w-full flex-1 max-w-full lg:w-full lg:max-w-none"
          : "max-h-[48dvh] w-full lg:max-h-none",
        className,
      )}
      style={!isMaximized ? resize.style : undefined}
    >
      {!isMaximized && <PanelResizeHandle resize={resize} label="Ajustar ancho del contexto" />}

      <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-3 py-2">
        <div className="min-w-0 pr-2">
          <p className="text-2xs font-bold uppercase tracking-[0.16em] text-[hsl(var(--muted-foreground))]">Contexto</p>
          <p className="truncate text-sm font-semibold text-[hsl(var(--foreground))]">
            {project?.title || "Proyecto"}
          </p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <span className="rounded-full bg-[hsl(var(--primary)/0.1)] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--primary))]">
            {openTasks} abiertas
          </span>
          <Link
            href="/plataforma/inbox"
            className="inline-flex items-center gap-1 rounded-md border border-[hsl(var(--border))] px-1.5 py-1 text-2xs font-bold text-[hsl(var(--muted-foreground))] transition-colors hover:border-[hsl(var(--primary))] hover:text-[hsl(var(--primary))]"
            aria-label={globalUnread > 0 ? `Abrir notificaciones, ${globalUnread} sin leer` : "Abrir notificaciones"}
          >
            <Bell size={12} />
            {globalUnread > 0 ? globalUnread : null}
            <ExternalLink size={11} />
          </Link>
          <div className="h-4 w-px bg-[hsl(var(--border))] mx-0.5" />
          <DSTooltip content={isMaximized ? "Restaurar vista dividida" : "Extender a toda la pantalla (hasta Sidebar 1)"} side="bottom">
            <button
              type="button"
              onClick={toggleMaximize}
              aria-label={isMaximized ? "Restaurar tamaño normal del panel" : "Extender a toda la pantalla"}
              className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
            >
              {isMaximized ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
            </button>
          </DSTooltip>
          <DSTooltip content="Minimizar panel a iconos" side="bottom">
            <button
              type="button"
              onClick={toggleMinimize}
              aria-label="Minimizar panel de contexto"
              className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
            >
              <Minus size={13} />
            </button>
          </DSTooltip>
          {onClose && (
            <DSTooltip content="Cerrar panel de contexto" side="bottom">
              <button
                type="button"
                onClick={onClose}
                aria-label="Cerrar panel de contexto"
                className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger-text))] hover:bg-[hsl(var(--destructive)/0.1)] transition-colors"
              >
                <X size={13} />
              </button>
            </DSTooltip>
          )}
        </div>
      </div>

      <div className="flex min-w-0 overflow-x-auto border-b border-[hsl(var(--border))] px-2 pt-2" role="tablist" aria-label="Contexto del proyecto">
        {visibleTabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            id={`project-context-tab-${id}`}
            type="button"
            role="tab"
            draggable={true}
            aria-label={id === "inbox" && projectInboxUnread > 0 ? `${label}, ${projectInboxUnread} sin leer` : label}
            aria-selected={activeTab === id}
            aria-controls="project-context-panel"
            aria-keyshortcuts="Alt+ArrowLeft Alt+ArrowRight"
            title="Arrastra para reordenar (Alt+←/→ con teclado)"
            ref={(element) => { tabRefs.current[id] = element; }}
            onClick={() => setActiveTab(id)}
            onKeyDown={(event) => handleTabKeyDown(event, id)}
            onDragStart={(event) => handleTabDragStart(event, id)}
            onDragOver={(event) => handleTabDragOver(event, id)}
            onDragLeave={(event) => handleTabDragLeave(event, id)}
            onDrop={(event) => handleTabDrop(event, id)}
            onDragEnd={handleTabDragEnd}
            className={clsx(
              "flex min-w-[5.5rem] flex-1 items-center justify-center gap-1.5 border-b-2 px-2 py-2 text-2xs font-bold transition-colors cursor-grab active:cursor-grabbing",
              activeTab === id
                ? "border-[hsl(var(--primary))] text-[hsl(var(--primary))]"
                : "border-transparent text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]",
              dragOverTab === id && dragTab && dragTab !== id && "border-b-[hsl(var(--primary))] outline outline-1 outline-[hsl(var(--primary))] rounded-t-md",
            )}
          >
            <Icon size={13} />
            <span>{label}</span>
            {id === "inbox" && projectInboxUnread > 0 ? (
              <span className="inline-flex min-w-4 items-center justify-center rounded-full bg-[hsl(var(--destructive))] px-1 text-[10px] leading-4 text-[hsl(var(--primary-foreground))]">
                {projectInboxUnread}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      <div
        id="project-context-panel"
        className="min-h-0 flex-1 overflow-hidden"
        role="tabpanel"
        aria-labelledby={`project-context-tab-${activeTab}`}
        tabIndex={0}
      >
        {activeTab === "chat" && project?.id ? (
          <ProjectChatPanel projectId={project.id} />
        ) : null}

        {activeTab === "activity" ? (
          <ProjectActivityFeed activities={activities} onRefresh={() => void reloadProject()} />
        ) : null}

        {activeTab === "inbox" ? (
          <ProjectInboxContent
            items={projectInbox}
            loading={inboxLoading}
            error={inboxError}
            onRead={markAsRead}
            onOpenTask={(taskId) => {
              const task = tasks.find((item) => item.id === taskId);
              if (task) onOpenTask?.(task);
            }}
          />
        ) : null}

        {activeTab === "tools" && tools?.length ? (
          <div className="h-full overflow-y-auto p-3">
            <label className="mb-3 block">
              <span className="mb-1 block text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Buscar herramientas</span>
              <input
                data-testid="context-tools-search"
                type="search"
                value={toolsSearch}
                onChange={(event) => setToolsSearch(event.currentTarget.value)}
                placeholder="Filtrar por nombre…"
                aria-label="Buscar herramienta por etiqueta"
                className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-xs text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--muted-foreground))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
              />
            </label>
            <div className="grid grid-cols-1 gap-2">
              {filteredTools.length === 0 ? (
                <p className="rounded-md border border-dashed border-[hsl(var(--border))] p-3 text-center text-xs text-[hsl(var(--muted-foreground))]">
                  No hay herramientas con esa etiqueta.
                </p>
              ) : filteredTools.map((tool) => {
                const ToolIcon = tool.icon;
                const variantClass =
                  tool.variant === "destructive"
                    ? "border-[hsl(var(--destructive)/0.35)] text-[hsl(var(--danger-text))] hover:bg-[hsl(var(--destructive)/0.08)]"
                    : tool.variant === "warning"
                      ? "border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))] hover:bg-[hsl(var(--warning-muted))]"
                      : "border-[hsl(var(--border))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]";
                return (
                  <button
                    key={tool.key}
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      void tool.onSelect?.();
                    }}
                    aria-label={tool.label}
                    className={clsx(
                      "flex min-h-9 min-w-0 items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs font-semibold transition-colors",
                      variantClass
                    )}
                  >
                    {ToolIcon ? <ToolIcon size={14} aria-hidden="true" className="shrink-0" /> : null}
                    <span className="truncate">{tool.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {activeTab === "details" ? (
          <div className="h-full overflow-y-auto p-4">
            <section
              data-testid="context-pmi-triple-constraint"
              aria-label="Diagnóstico de Triple Restricción PMI"
              className="mb-4 space-y-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3"
            >
              <div>
                <h3 className="text-xs font-bold text-[hsl(var(--text-primary))]">Diagnóstico PMI · Triple Restricción</h3>
                <p className="mt-0.5 text-2xs text-[hsl(var(--text-secondary))]">Alcance, cronograma y presupuesto BAC</p>
              </div>
              <div className="grid gap-2">
                <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Alcance</span>
                    <span className="text-xs font-bold text-[hsl(var(--text-primary))]">{scopeCompletion}% completado</span>
                  </div>
                  <p className="mt-1 text-2xs text-[hsl(var(--text-secondary))]">
                    {completedTasks} de {tasks.length} paquetes completados · {blockedOrUrgentTasks} bloqueados o urgentes abiertos
                  </p>
                </div>
                <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Cronograma</span>
                    <span className={clsx(
                      "rounded-full border px-2 py-0.5 text-2xs font-bold",
                      overdueTasks > 0
                        ? "border-[hsl(var(--destructive)/0.35)] bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--danger-text))]"
                        : "border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success-text))]"
                    )}>
                      {overdueTasks > 0 ? "Alerta de Atraso" : "Cronograma en Regla"}
                    </span>
                  </div>
                  <p className="mt-1 text-2xs text-[hsl(var(--text-secondary))]">
                    {overdueTasks} {overdueTasks === 1 ? "actividad vencida abierta" : "actividades vencidas abiertas"}
                  </p>
                </div>
                <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Costo · BAC vs distribuido EDT</span>
                    <span className={clsx(
                      "rounded-full border px-2 py-0.5 text-2xs font-bold",
                      budgetStatus === "Exceso sobre BAC"
                        ? "border-[hsl(var(--destructive)/0.35)] bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--danger-text))]"
                        : budgetStatus === "Presupuesto Cuadrado"
                          ? "border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success-text))]"
                          : budgetStatus === "Reserva por Distribuir"
                            ? "border-[hsl(var(--warning)/0.35)] bg-[hsl(var(--warning)/0.1)] text-[hsl(var(--warning-text))]"
                            : "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]"
                    )}>
                      {budgetStatus}
                    </span>
                  </div>
                  <p className="mt-1 text-2xs text-[hsl(var(--text-secondary))]">
                    Distribuido: {formatBudgetAmount(distributedTaskBudget)} · BAC: {projectBudget == null ? "No definido" : formatBudgetAmount(projectBudget)}
                  </p>
                </div>
              </div>
            </section>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Total" value={tasks.length} />
              <Metric label="Completadas" value={completedTasks} />
              <Metric label="Abiertas" value={openTasks} />
              <Metric label="Historial de eventos" value={activities.length} />
            </div>

            <section className="mt-5 space-y-3">
              <DetailRow label="Estado" value={formatStatus(project?.status)} />
              <DetailRow label="Responsable" value={project?.owner_id ? "Asignado" : "Sin asignar"} />
              <DetailRow label="Creado" value={formatDate(project?.created_at, { fallback: "Sin fecha" })} />
            </section>

            {project?.description ? (
              <section className="mt-5 rounded-lg border border-[hsl(var(--border))] p-3">
                <p className="mb-1 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Descripción</p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-[hsl(var(--text-primary))]">
                  {project.description}
                </p>
              </section>
            ) : (
              <div className="mt-5 flex items-center gap-2 rounded-lg border border-dashed border-[hsl(var(--border))] p-3 text-xs text-[hsl(var(--muted-foreground))]">
                <X size={14} />
                Este proyecto aún no tiene descripción.
              </div>
            )}

            <div className="mt-5 flex items-center gap-2 text-xs text-[hsl(var(--text-primary))]">
              <CheckCircle2 size={14} className="text-[hsl(var(--success-text))]" />
              Los cambios se sincronizan con List y Kanban.
            </div>
          </div>
        ) : null}

        {!project?.id && activeTab === "chat" ? (
          <div className="flex h-full items-center justify-center p-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
            Selecciona un proyecto para abrir su contexto.
          </div>
        ) : null}
      </div>
    </aside>
  );
}

function isProjectInboxEvent(payload: WsEvent, projectId: string): boolean {
  if (payload.event === "project_message") {
    return "project_id" in payload && String(payload.project_id) === projectId;
  }

  if (payload.event !== "notification:new" || !("body" in payload) || typeof payload.body !== "object" || payload.body === null) {
    return false;
  }

  const body = payload.body as Record<string, unknown>;
  return "project_id" in body && String(body.project_id) === projectId;
}

function formatRelativeTime(dateStr: string): string {
  if (!dateStr) return "";
  const now = new Date();
  const date = new Date(dateStr);
  const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diffSec < 60) return "Ahora";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h`;
  return date.toLocaleDateString("es-CO", { day: "2-digit", month: "short" });
}

function ProjectInboxContent({
  items,
  loading,
  error,
  onRead,
  onOpenTask,
}: {
  items: Array<{
    id: string;
    type: string;
    user: string;
    content: string;
    project: string;
    task_id?: string | null;
    task_title?: string | null;
    is_read: boolean;
    created_at: string;
  }>;
  loading: boolean;
  error: string | null;
  onRead: (itemId: string) => Promise<void>;
  onOpenTask: (taskId: string) => void;
}) {
  const unreadItems = items.filter((i) => !i.is_read);

  const handleMarkAllRead = async () => {
    for (const item of unreadItems) {
      await onRead(item.id);
    }
  };

  if (loading) {
    return <div className="p-4 text-sm text-[hsl(var(--muted-foreground))]">Cargando bandeja de entrada…</div>;
  }

  if (error) {
    return <div className="p-4 text-sm text-[hsl(var(--danger-text))]">{error}</div>;
  }

  if (items.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-[hsl(var(--muted-foreground))]">
        <CheckCircle2 size={24} className="text-[hsl(var(--success-text))]" />
        <p className="text-sm font-semibold">Inbox al día</p>
        <p className="text-xs">No hay comentarios ni tareas asignadas pendientes en este proyecto.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {unreadItems.length > 0 && (
        <div className="px-3 py-1.5 border-b border-[hsl(var(--border))] flex items-center justify-between bg-[hsl(var(--surface-2)/0.4)] shrink-0">
          <span className="text-2xs font-semibold text-[hsl(var(--muted-foreground))]">
            {unreadItems.length} pendiente{unreadItems.length > 1 ? "s" : ""}
          </span>
          <button
            type="button"
            onClick={handleMarkAllRead}
            className="text-2xs font-bold text-[hsl(var(--primary))] hover:underline"
          >
            Marcar todo como leído
          </button>
        </div>
      )}
      <div className="flex-1 overflow-y-auto divide-y divide-[hsl(var(--border))]">
        {items.map((item) => (
          <article key={item.id} className={`p-3 transition-colors ${item.is_read ? "" : "bg-[hsl(var(--primary)/0.05)]"}`}>
            <div className="flex items-start gap-2">
              <div className="mt-0.5 rounded-md bg-[hsl(var(--surface-2))] p-1.5 text-[hsl(var(--primary))] shrink-0">
                {item.type === "task_assigned" ? <CheckCircle2 size={14} /> : <MessageSquare size={14} />}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="truncate text-xs font-bold text-[hsl(var(--foreground))]">{item.user}</p>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-2xs text-[hsl(var(--muted-foreground))]">{formatRelativeTime(item.created_at)}</span>
                    {!item.is_read ? <span className="size-1.5 rounded-full bg-[hsl(var(--primary))]" aria-label="Sin leer" /> : null}
                  </div>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-[hsl(var(--muted-foreground))]">{item.content}</p>
                {item.task_title ? <p className="mt-1 text-2xs font-semibold text-[hsl(var(--primary))]">{item.task_title}</p> : null}
                <div className="mt-2 flex items-center gap-2">
                  {item.task_id ? (
                    <button
                      type="button"
                      onClick={() => {
                        void onRead(item.id);
                        onOpenTask(item.task_id as string);
                      }}
                      className="rounded-md bg-[hsl(var(--primary))] px-2 py-1 text-2xs font-bold text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity"
                    >
                      Abrir tarea
                    </button>
                  ) : null}
                  {!item.is_read ? (
                    <button
                      type="button"
                      onClick={() => void onRead(item.id)}
                      className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1 text-2xs font-bold text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                    >
                      Marcar leído
                    </button>
                  ) : null}
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] p-3">
      <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p>
      <p className="mt-1 text-xl font-bold text-[hsl(var(--text-primary))]">{value}</p>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[hsl(var(--border))] pb-2">
      <span className="text-xs font-medium text-[hsl(var(--text-secondary))]">{label}</span>
      <span className="truncate text-right text-xs font-semibold text-[hsl(var(--text-primary))]">{value}</span>
    </div>
  );
}

function formatBudgetAmount(value: number): string {
  return `$${value.toLocaleString("es-CO", { maximumFractionDigits: 0 })}`;
}

function formatStatus(status?: string | null) {
  if (!status) return "Sin estado";
  return status.replaceAll("_", " ").replace(/^./, (value) => value.toUpperCase());
}

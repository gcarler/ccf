"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";
import { Activity, Bell, CheckCircle2, ChevronLeft, ChevronRight, ExternalLink, Inbox, Maximize2, MessageSquare, Minimize2, Minus, Users, X } from "lucide-react";
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
import { formatDate } from "@/lib/format";

type ContextTab = "chat" | "activity" | "details" | "inbox";

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
}

const TABS: Array<{ id: ContextTab; label: string; icon: typeof MessageSquare }> = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "activity", label: "Historia", icon: Activity },
  { id: "inbox", label: "Inbox", icon: Inbox },
  { id: "details", label: "Detalles", icon: Users },
];

export default function ProjectContextPanel({
  className,
  defaultTab = "chat",
  onOpenTask,
  onClose,
  isExpanded: controlledExpanded,
  onToggleExpand,
  isMaximized: controlledMaximized,
  onToggleMaximize,
  isMinimized: controlledMinimized,
  onToggleMinimize,
}: ProjectContextPanelProps) {
  const { project, tasks, activities, reloadProject } = useProjectUpdate();
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<ContextTab>(defaultTab);
  const [internalMaximized, setInternalMaximized] = useState(false);
  const [internalMinimized, setInternalMinimized] = useState(false);
  const [width, setWidth] = useState<number>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("workspace:s3_width");
      if (saved && !isNaN(Number(saved))) return Math.max(300, Math.min(Number(saved), 1200));
    }
    return 380;
  });
  const [isDragging, setIsDragging] = useState(false);
  const panelRef = useRef<HTMLElement>(null);

  const isMaximized = controlledMaximized ?? controlledExpanded ?? internalMaximized;
  const isMinimized = controlledMinimized !== undefined ? controlledMinimized : internalMinimized;

  const toggleMaximize = onToggleMaximize ?? onToggleExpand ?? (() => setInternalMaximized((v) => !v));
  const toggleMinimize = onToggleMinimize ?? (() => setInternalMinimized((v) => !v));

  const handleResizeDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = panelRef.current?.offsetWidth ?? width;
    setIsDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMouseMove = (ev: MouseEvent) => {
      const maxAllowed = typeof window !== "undefined" ? window.innerWidth - 80 : 1200;
      const next = Math.max(300, Math.min(startWidth + (startX - ev.clientX), maxAllowed));
      setWidth(next);
      try {
        localStorage.setItem("workspace:s3_width", String(next));
      } catch {}
    };

    const onMouseUp = () => {
      setIsDragging(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }, [width]);

  const tabRefs = useRef<Partial<Record<ContextTab, HTMLButtonElement | null>>>({});
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

  const focusTab = (tab: ContextTab) => {
    setActiveTab(tab);
    tabRefs.current[tab]?.focus();
  };

  const handleTabKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, tab: ContextTab) => {
    const currentIndex = TABS.findIndex((item) => item.id === tab);
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      focusTab(TABS[(currentIndex + 1) % TABS.length].id);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      focusTab(TABS[(currentIndex - 1 + TABS.length) % TABS.length].id);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusTab(TABS[0].id);
    } else if (event.key === "End") {
      event.preventDefault();
      focusTab(TABS[TABS.length - 1].id);
    }
  };

  const openTasks = tasks.filter((task) => task.status !== "completed").length;
  const completedTasks = tasks.length - openTasks;

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
          {TABS.map(({ id, label, icon: Icon }) => (
            <DSTooltip key={id} content={label} side="left">
              <button
                key={id}
                type="button"
                role="tab"
                aria-label={id === "inbox" && projectInboxUnread > 0 ? `${label}, ${projectInboxUnread} sin leer` : label}
                aria-selected={activeTab === id}
                onClick={() => {
                  setActiveTab(id);
                  toggleMinimize();
                }}
                className={clsx(
                  "relative flex h-8 w-8 items-center justify-center rounded-md transition-colors",
                  activeTab === id
                    ? "bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"
                    : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))]"
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
              className="flex h-8 w-8 items-center justify-center rounded-md text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--destructive)/0.1)] hover:text-[hsl(var(--destructive))] transition-colors mb-2"
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
        isDragging ? "select-none" : "transition-[width] duration-150 ease-out",
        isMaximized
          ? "w-full flex-1 max-w-full lg:w-full lg:max-w-none"
          : "max-h-[48dvh] w-full lg:max-h-none",
        className,
      )}
      style={!isMaximized ? { width: typeof window !== "undefined" && window.innerWidth >= 1024 ? `${width}px` : undefined } : undefined}
    >
      {/* Resizer manual en el borde izquierdo (solo en desktop y cuando no está maximizado) */}
      {!isMaximized && (
        <div
          onMouseDown={handleResizeDrag}
          className="hidden lg:block absolute left-0 top-0 h-full w-2.5 -translate-x-1 cursor-col-resize group/resize z-30 select-none"
          title="Arrastra para ajustar el ancho manualmente"
        >
          <div className="h-full w-0.5 mx-auto bg-transparent group-hover/resize:bg-[hsl(var(--primary))] transition-colors" />
        </div>
      )}

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
                className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] transition-colors"
              >
                <X size={13} />
              </button>
            </DSTooltip>
          )}
        </div>
      </div>

      <div className="flex min-w-0 overflow-x-auto border-b border-[hsl(var(--border))] px-2 pt-2" role="tablist" aria-label="Contexto del proyecto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            id={`project-context-tab-${id}`}
            type="button"
            role="tab"
            aria-label={id === "inbox" && projectInboxUnread > 0 ? `${label}, ${projectInboxUnread} sin leer` : label}
            aria-selected={activeTab === id}
            aria-controls="project-context-panel"
            ref={(element) => { tabRefs.current[id] = element; }}
            onClick={() => setActiveTab(id)}
            onKeyDown={(event) => handleTabKeyDown(event, id)}
            className={clsx(
              "flex min-w-[5.5rem] flex-1 items-center justify-center gap-1.5 border-b-2 px-2 py-2 text-2xs font-bold transition-colors",
              activeTab === id
                ? "border-[hsl(var(--primary))] text-[hsl(var(--primary))]"
                : "border-transparent text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]",
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

        {activeTab === "details" ? (
          <div className="h-full overflow-y-auto p-4">
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Total" value={tasks.length} />
              <Metric label="Completadas" value={completedTasks} />
              <Metric label="Abiertas" value={openTasks} />
              <Metric label="Actividad" value={activities.length} />
            </div>

            <section className="mt-5 space-y-3">
              <DetailRow label="Estado" value={formatStatus(project?.status)} />
              <DetailRow label="Responsable" value={project?.owner_id ? "Asignado" : "Sin asignar"} />
              <DetailRow label="Creado" value={formatDate(project?.created_at, { fallback: "Sin fecha" })} />
            </section>

            {project?.description ? (
              <section className="mt-5 rounded-lg border border-[hsl(var(--border))] p-3">
                <p className="mb-1 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Descripción</p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-[hsl(var(--muted-foreground))]">
                  {project.description}
                </p>
              </section>
            ) : (
              <div className="mt-5 flex items-center gap-2 rounded-lg border border-dashed border-[hsl(var(--border))] p-3 text-xs text-[hsl(var(--muted-foreground))]">
                <X size={14} />
                Este proyecto aún no tiene descripción.
              </div>
            )}

            <div className="mt-5 flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
              <CheckCircle2 size={14} className="text-[hsl(var(--success))]" />
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
    return <div className="p-4 text-sm text-[hsl(var(--destructive))]">{error}</div>;
  }

  if (items.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-[hsl(var(--muted-foreground))]">
        <CheckCircle2 size={24} className="text-[hsl(var(--success))]" />
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
      <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{label}</p>
      <p className="mt-1 text-xl font-bold text-[hsl(var(--foreground))]">{value}</p>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[hsl(var(--border))] pb-2">
      <span className="text-xs font-medium text-[hsl(var(--muted-foreground))]">{label}</span>
      <span className="truncate text-right text-xs font-semibold text-[hsl(var(--foreground))]">{value}</span>
    </div>
  );
}

function formatStatus(status?: string | null) {
  if (!status) return "Sin estado";
  return status.replaceAll("_", " ").replace(/^./, (value) => value.toUpperCase());
}

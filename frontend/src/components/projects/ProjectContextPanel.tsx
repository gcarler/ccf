"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";
import { Activity, Bell, CheckCircle2, ExternalLink, Inbox, MessageSquare, Users, X } from "lucide-react";
import clsx from "clsx";
import { useProjectUpdate } from "@/context/ProjectUpdateContext";
import { useAuth } from "@/context/AuthContext";
import ProjectActivityFeed from "@/components/projects/ProjectActivityFeed";
import ProjectChatPanel from "@/components/projects/ProjectChatPanel";
import { useNotifications } from "@/hooks/useNotifications";
import { useProjectInbox } from "@/hooks/useProjectInbox";
import { useWorkspaceSocket } from "@/hooks/useWorkspaceSocket";
import type { WsEvent } from "@/types/directMessages";
import type { ProjectTaskRecord } from "@/types/projects";

type ContextTab = "chat" | "activity" | "details" | "inbox";

interface ProjectContextPanelProps {
  className?: string;
  defaultTab?: ContextTab;
  onOpenTask?: (task: ProjectTaskRecord) => void;
}

const TABS: Array<{ id: ContextTab; label: string; icon: typeof MessageSquare }> = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "activity", label: "Actividad", icon: Activity },
  { id: "inbox", label: "Inbox", icon: Inbox },
  { id: "details", label: "Detalles", icon: Users },
];

export default function ProjectContextPanel({ className, defaultTab = "chat", onOpenTask }: ProjectContextPanelProps) {
  const { project, tasks, activities } = useProjectUpdate();
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<ContextTab>(defaultTab);
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

  return (
    <aside
      aria-label="Contexto del proyecto"
      className={clsx(
        "flex min-h-0 max-h-[48dvh] w-full shrink-0 flex-col overflow-hidden border-t border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-[hsl(var(--admin-bg-secondary))] lg:max-h-none lg:w-[360px] lg:border-l lg:border-t-0",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-3 py-2.5 dark:border-white/10">
        <div className="min-w-0">
          <p className="text-2xs font-bold uppercase tracking-[0.16em] text-[hsl(var(--text-secondary))]">Contexto</p>
          <p className="truncate text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">
            {project?.title || "Proyecto"}
          </p>
        </div>
        <span className="rounded-full bg-info-soft px-2 py-1 text-2xs font-bold text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/10">            {openTasks} abiertas
        </span>
        <Link
          href="/plataforma/inbox"
          className="inline-flex items-center gap-1 rounded-md border border-[hsl(var(--border))] px-2 py-1 text-2xs font-bold text-[hsl(var(--text-secondary))] transition-colors hover:border-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] dark:border-white/10"
          aria-label={globalUnread > 0 ? `Abrir notificaciones, ${globalUnread} sin leer` : "Abrir notificaciones"}
        >
          <Bell size={12} />
          {globalUnread > 0 ? globalUnread : null}
          <ExternalLink size={11} />
        </Link>
      </div>

      <div className="flex min-w-0 overflow-x-auto border-b border-[hsl(var(--border))] px-2 pt-2 dark:border-white/10" role="tablist" aria-label="Contexto del proyecto">
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
                : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white",
            )}
          >
            <Icon size={13} />
            <span>{label}</span>
            {id === "inbox" && projectInboxUnread > 0 ? (
              <span className="inline-flex min-w-4 items-center justify-center rounded-full bg-[hsl(var(--danger))] px-1 text-[10px] leading-4 text-white">
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
          <ProjectActivityFeed activities={activities} />
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
              <DetailRow label="Creado" value={formatDate(project?.created_at)} />
            </section>

            {project?.description ? (
              <section className="mt-5 rounded-lg border border-[hsl(var(--border))] p-3 dark:border-white/10">
                <p className="mb-1 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Descripción</p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
                  {project.description}
                </p>
              </section>
            ) : (
              <div className="mt-5 flex items-center gap-2 rounded-lg border border-dashed border-[hsl(var(--border))] p-3 text-xs text-[hsl(var(--text-secondary))] dark:border-white/10">
                <X size={14} />
                Este proyecto aún no tiene descripción.
              </div>
            )}

            <div className="mt-5 flex items-center gap-2 text-xs text-[hsl(var(--text-secondary))]">
              <CheckCircle2 size={14} className="text-[hsl(var(--success))]" />
              Los cambios se sincronizan con List y Kanban.
            </div>
          </div>
        ) : null}

        {!project?.id && activeTab === "chat" ? (
          <div className="flex h-full items-center justify-center p-6 text-center text-sm text-[hsl(var(--text-secondary))]">
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
  if (loading) {
    return <div className="p-4 text-sm text-[hsl(var(--text-secondary))]">Cargando inbox del proyecto…</div>;
  }

  if (error) {
    return <div className="p-4 text-sm text-[hsl(var(--danger))]">{error}</div>;
  }

  if (items.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-[hsl(var(--text-secondary))]">
        <CheckCircle2 size={24} />
        <p className="text-sm font-semibold">Inbox al día</p>
        <p className="text-xs">No hay comentarios ni tareas pendientes en este proyecto.</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto divide-y divide-[hsl(var(--border))] dark:divide-white/5">
      {items.map((item) => (
        <article key={item.id} className={`p-3 transition-colors ${item.is_read ? "" : "bg-info-soft/40 dark:bg-[hsl(var(--info))]/5"}`}>
          <div className="flex items-start gap-2">
            <div className="mt-0.5 rounded-md bg-[hsl(var(--surface-2))] p-1.5 text-[hsl(var(--primary))] dark:bg-white/10">
              {item.type === "task_assigned" ? <CheckCircle2 size={14} /> : <MessageSquare size={14} />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <p className="truncate text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">{item.user}</p>
                {!item.is_read ? <span className="mt-1 size-1.5 shrink-0 rounded-full bg-[hsl(var(--primary))]" aria-label="Sin leer" /> : null}
              </div>
              <p className="mt-1 text-xs leading-relaxed text-[hsl(var(--text-secondary))]">{item.content}</p>
              {item.task_title ? <p className="mt-1 text-2xs font-semibold text-[hsl(var(--primary))]">{item.task_title}</p> : null}
              <div className="mt-2 flex items-center gap-2">
                {item.task_id ? (
                  <button
                    type="button"
                    onClick={() => {
                      void onRead(item.id);
                      onOpenTask(item.task_id as string);
                    }}
                    className="rounded-md bg-[hsl(var(--primary))] px-2 py-1 text-2xs font-bold text-white"
                  >
                    Abrir tarea
                  </button>
                ) : null}
                {!item.is_read ? (
                  <button
                    type="button"
                    onClick={() => void onRead(item.id)}
                    className="rounded-md border border-[hsl(var(--border))] px-2 py-1 text-2xs font-bold text-[hsl(var(--text-secondary))] dark:border-white/10"
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
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-[hsl(var(--border))] p-3 dark:border-white/10">
      <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p>
      <p className="mt-1 text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">{value}</p>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[hsl(var(--border))] pb-2 dark:border-white/10">
      <span className="text-xs font-medium text-[hsl(var(--text-secondary))]">{label}</span>
      <span className="truncate text-right text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white">{value}</span>
    </div>
  );
}

function formatStatus(status?: string | null) {
  if (!status) return "Sin estado";
  return status.replaceAll("_", " ").replace(/^./, (value) => value.toUpperCase());
}

function formatDate(date?: string | null) {
  if (!date) return "Sin fecha";
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return "Sin fecha";
  return new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "short", year: "numeric" }).format(parsed);
}

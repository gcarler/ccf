"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CalendarDays, CheckCircle2, Circle, FolderOpen, ListChecks, Search, Zap } from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";
import UniversalTableView from "@/components/ui/UniversalTableView";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import TaskEditDrawer, { TaskDetail } from "@/components/ui/TaskEditDrawer";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import { getAllAssignedProjectTasks } from "@/lib/projects/api";
import { PROJECTS_LIST_ROUTE } from "@/app/plataforma/projects/projectsLinks";
import type { ViewType } from "@/components/ViewSwitcher";
import type { ProjectTaskRecord } from "@/types/projects";

interface Task {
  id: string;
  title: string;
  status: string;
  priority: string | null;
  due_date: string | null;
  project_id: string;
  project_title?: string;
  assignee_id?: string | null;
}

const PRIORITY_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  urgent: { label: "Urgente", color: "text-[hsl(var(--danger))] bg-[hsl(var(--danger)/15%)]", dot: "bg-[hsl(var(--danger))]" },
  high: { label: "Alta", color: "text-[hsl(var(--warning))] bg-[hsl(var(--warning)/15%)]", dot: "bg-[hsl(var(--warning))]" },
  medium: { label: "Media", color: "text-[hsl(var(--warning))] bg-[hsl(var(--warning)/10%)]", dot: "bg-[hsl(var(--warning))]" },
  low: { label: "Baja", color: "text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))]", dot: "bg-[hsl(var(--surface-2))]" },
};

const STATUS_LABEL: Record<string, string> = {
  todo: "Por hacer",
  in_progress: "En progreso",
  review: "Revision",
  blocked: "Bloqueada",
  done: "Completada",
};

const XP_MAP: Record<string, number> = { urgent: 100, high: 60, medium: 40, low: 20 };
const TASK_VIEWS: ViewType[] = ["list", "table", "grid", "kanban"];

function priorityKey(task: Task): string {
  return task.priority || "low";
}

function priorityConfig(task: Task) {
  return PRIORITY_CONFIG[priorityKey(task)] || PRIORITY_CONFIG.low;
}

function normalizeTask(row: ProjectTaskRecord | TaskDetail): Task {
  return {
    id: row.id,
    title: row.title || "Tarea sin titulo",
    status: row.status || "todo",
    priority: row.priority || "low",
    due_date: row.due_date || null,
    project_id: row.project_id,
    project_title: row.project_title || undefined,
    assignee_id: "assignee_id" in row && row.assignee_id ? row.assignee_id : null,
  };
}

export default function UserTasksPage() {
  const { token, isAuthenticated } = useAuth();
  const { addToast } = useToast();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [query, setQuery] = useState("");
  const [filterPriority, setFilterPriority] = useState("all");
  const [loading, setLoading] = useState(true);
  const [savingTaskId, setSavingTaskId] = useState<string | null>(null);
  const [viewType, setViewType] = useState<ViewType>("list");
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null);

  const loadTasks = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await getAllAssignedProjectTasks(token, { cache: "no-store" });
      const activeTasks = data.map(normalizeTask).filter(task => task.status !== "done");
      activeTasks.sort((a, b) => {
        const order = ["urgent", "high", "medium", "low"];
        return order.indexOf(priorityKey(a)) - order.indexOf(priorityKey(b));
      });
      setTasks(activeTasks);
    } catch (error) {
      console.error("[Tasks] fetch failed", error);
      setTasks([]);
      addToast("No se pudieron cargar las tareas asignadas", "error");
    } finally {
      setLoading(false);
    }
  }, [token, addToast]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const completeTask = async (task: Task) => {
    if (!token || savingTaskId === task.id) return;
    setSavingTaskId(task.id);
    try {
      await apiFetch(`/projects/tasks/${task.id}`, {
        method: "PATCH",
        token,
        body: { status: "done" },
      });
      setTasks(prev => prev.filter(item => item.id !== task.id));
      const xp = XP_MAP[priorityKey(task)] || XP_MAP.low;
      addToast(`Tarea completada. +${xp} XP`, "success");
    } catch (error) {
      console.error("[Tasks] complete failed", error);
      addToast("No se pudo completar la tarea", "error");
    } finally {
      setSavingTaskId(null);
    }
  };

  const handleTaskUpdated = (updated: TaskDetail) => {
    const normalized = normalizeTask(updated);
    setTasks(prev => normalized.status === "done"
      ? prev.filter(task => task.id !== normalized.id)
      : prev.map(task => task.id === normalized.id ? { ...task, ...normalized } : task)
    );
    if (normalized.status === "done") addToast("Tarea completada", "success");
  };

  const handleTaskDeleted = (taskId: string) => {
    setTasks(prev => prev.filter(task => task.id !== taskId));
    addToast("Tarea eliminada", "info");
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return tasks.filter(task => {
      const matchesQuery = !q || `${task.title} ${task.project_title || ""}`.toLowerCase().includes(q);
      const matchesPriority = filterPriority === "all" || priorityKey(task) === filterPriority;
      return matchesQuery && matchesPriority;
    });
  }, [tasks, query, filterPriority]);

  const metrics = useMemo(() => ({
    pending: tasks.length,
    urgent: tasks.filter(task => priorityKey(task) === "urgent").length,
    dueToday: tasks.filter(task => task.due_date && new Date(task.due_date).toDateString() === new Date().toDateString()).length,
  }), [tasks]);

  const grouped = useMemo(() => {
    const groups = ["todo", "in_progress", "review", "blocked"].map(status => ({
      status,
      label: STATUS_LABEL[status] || status,
      items: filtered.filter(task => task.status === status),
    }));
    const unknown = filtered.filter(task => !groups.some(group => group.status === task.status));
    return unknown.length ? [...groups, { status: "other", label: "Otros", items: unknown }] : groups;
  }, [filtered]);

  if (!isAuthenticated) return null;

  const renderTaskCard = (task: Task, index = 0) => {
    const config = priorityConfig(task);
    const xp = XP_MAP[priorityKey(task)] || XP_MAP.low;
    return (
      <motion.button
        key={task.id}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: Math.min(index * 0.025, 0.2) }}
        onClick={() => setSelectedTask(task as TaskDetail)}
        className="group w-full text-left rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm transition-all hover:border-[hsl(var(--primary)/30%)] hover:shadow-lg"
      >
        <div className="flex items-start gap-3">
          <button
            onClick={event => {
              event.stopPropagation();
              completeTask(task);
            }}
            disabled={savingTaskId === task.id}
            className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border-2 border-[hsl(var(--border))] transition-all hover:border-[hsl(var(--success)/40%)] hover:bg-[hsl(var(--success)/15%)] disabled:opacity-60"
          >
            {savingTaskId === task.id ? <CheckCircle2 size={13} className="text-[hsl(var(--success))]" /> : <Circle size={12} className="text-[hsl(var(--text-secondary))]" />}
          </button>
          <div className="min-w-0 flex-1">
            <p className="line-clamp-2 text-base font-bold leading-snug text-[hsl(var(--text-primary))] transition-colors group-hover:text-[hsl(var(--primary))]">
              {task.title}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className={clsx("rounded-full px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide", config.color)}>{config.label}</span>
              <span className="inline-flex items-center gap-1 rounded-full bg-[hsl(var(--surface-2))] px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                <FolderOpen size={10} /> {task.project_title || "Sin proyecto"}
              </span>
              {task.due_date && (
                <span className="inline-flex items-center gap-1 rounded-full bg-[hsl(var(--info)/15%)] px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--info))]">
                  <CalendarDays size={10} /> {new Date(task.due_date).toLocaleDateString("es-CO")}
                </span>
              )}
            </div>
          </div>
          <span className="inline-flex shrink-0 items-center gap-1 rounded-md bg-[hsl(var(--warning)/15%)] px-2 py-1 font-semibold text-[hsl(var(--warning))]">
            <Zap size={10} fill="currentColor" /> {xp}
          </span>
        </div>
      </motion.button>
    );
  };

  return (
    <WorkspaceLayout
      breadcrumbs={[{ label: "Mi Centro de Tareas", icon: ListChecks, href: "/plataforma/tasks" }]}
      viewType={viewType}
      setViewType={setViewType}
      availableViews={TASK_VIEWS}
    >
      <div className="flex h-full flex-col overflow-hidden rounded-lg bg-[hsl(var(--background))]">
        <TaskEditDrawer
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
          onTaskUpdated={handleTaskUpdated}
          onTaskDeleted={handleTaskDeleted}
        />

        <header className="shrink-0 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              {[
                { label: "Pendientes", value: metrics.pending },
                { label: "Urgentes", value: metrics.urgent },
                { label: "Hoy", value: metrics.dueToday },
              ].map(metric => (
                <div key={metric.label} className="rounded-md border border-[hsl(var(--border))] px-3 py-2 bg-[hsl(var(--surface-1))]">
                  <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{metric.label}</p>
                  <p className="text-lg font-bold text-[hsl(var(--text-primary))]">{metric.value}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-1 flex-col gap-2 sm:flex-row lg:max-w-2xl">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                <input
                  value={query}
                  onChange={event => setQuery(event.target.value)}
                  placeholder="Buscar tareas..."
                  className="w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/20%)] text-[hsl(var(--text-primary))]"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {["all", "urgent", "high", "medium", "low"].map(priority => (
                  <button
                    key={priority}
                    onClick={() => setFilterPriority(priority)}
                    className={clsx(
                      "rounded-md px-3 py-2 text-2xs font-semibold uppercase tracking-wide transition-all",
                      filterPriority === priority
                        ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                        : "border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--primary)/30%)]"
                    )}
                  >
                    {priority === "all" ? "Todo" : PRIORITY_CONFIG[priority]?.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-3">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="h-20 animate-pulse rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex min-h-[55vh] flex-col items-center justify-center gap-4 text-center">
              <div className="flex size-8 items-center justify-center rounded-lg bg-[hsl(var(--success)/15%)] text-[hsl(var(--success))]">
                <CheckCircle2 size={28} />
              </div>
              <div>
                <p className="text-lg font-bold text-[hsl(var(--text-primary))]">{query || filterPriority !== "all" ? "Sin resultados" : "Sin tareas pendientes"}</p>
                <p className="mt-1 max-w-sm text-sm text-[hsl(var(--text-secondary))]">
                  {query || filterPriority !== "all" ? "Ajusta los filtros para ver otras tareas." : "No tienes tareas activas asignadas en este momento."}
                </p>
              </div>
              <Link href={PROJECTS_LIST_ROUTE} className="inline-flex items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--primary-foreground))]">
                <FolderOpen size={13} /> Ver proyectos
              </Link>
            </div>
          ) : viewType === "table" ? (
            <UniversalTableView
              data={filtered}
              columns={[
                {
                  key: "title",
                  label: "Tarea",
                  type: "text",
                  width: "420px",
                  render: (_value, task) => (
                    <button onClick={() => setSelectedTask(task as TaskDetail)} className="text-left text-base font-semibold text-[hsl(var(--text-primary))] hover:text-[hsl(var(--primary))]">
                      {task.title}
                    </button>
                  ),
                },
                { key: "project_title", label: "Proyecto", type: "text", width: "180px" },
                { key: "priority", label: "Prioridad", type: "priority", width: "130px" },
                { key: "status", label: "Estado", type: "status", width: "140px" },
                { key: "due_date", label: "Fecha limite", type: "date", width: "140px" },
              ]}
              groupBy="status"
              emptyMessage="Sin tareas en esta vista"
            />
          ) : viewType === "grid" ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {filtered.map(renderTaskCard)}
            </div>
          ) : viewType === "kanban" ? (
            <div className="flex h-full min-h-[620px] gap-4 overflow-x-auto pb-2">
              {grouped.map(group => (
                <section key={group.status} className="flex w-72 shrink-0 flex-col rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                  <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-4 py-3">
                    <span className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{group.label}</span>
                    <span className="rounded-full bg-[hsl(var(--surface-2))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--text-secondary))]">{group.items.length}</span>
                  </div>
                  <div className="flex-1 space-y-3 overflow-y-auto p-3">
                    {group.items.length === 0 ? (
                      <div className="flex h-20 items-center justify-center rounded-md border-2 border-dashed border-[hsl(var(--border))] text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        Vacio
                      </div>
                    ) : (
                      group.items.map(renderTaskCard)
                    )}
                  </div>
                </section>
              ))}
            </div>
          ) : (
            <div className="mx-auto max-w-5xl space-y-3">
              {filtered.map(renderTaskCard)}
            </div>
          )}
        </main>
      </div>
    </WorkspaceLayout>
  );
}

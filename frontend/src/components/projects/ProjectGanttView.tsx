"use client";

import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useProjectUpdate } from "@/context/ProjectUpdateContext";
import { apiFetch } from "@/lib/http";
import type {
  ProjectTaskRecord,
  ProjectTaskDependency,
  ProjectMilestoneRecord,
  ProjectCriticalPathSummary,
  ProjectBaseline,
} from "@/types/projects";
import { RightPanel } from "@/components/ui/RightPanel";
import { ProjectBaselineDrawer } from "@/components/projects/ProjectBaselineDrawer";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Layers,
  Link2,
  Plus,
  Trash2,
  Milestone,
  ZoomIn,
  Clock,
  CheckCircle2,
  AlertTriangle,
  MoveHorizontal,
  X,
  Sparkles,
  Zap,
  Sliders,
} from "lucide-react";
import clsx from "clsx";

interface Props {
  projectId?: string;
  projectTitle?: string;
  tasks: ProjectTaskRecord[];
  phases: { slug: string; name: string; color?: string }[];
  onOpenTask: (task: ProjectTaskRecord) => void;
  onTaskDatesChange?: (taskId: string, start_date: string, end_date: string) => void;
}

type ZoomLevel = "day" | "week" | "month";

const ZOOM_CONFIG = {
  day: { colWidth: 44, daysPerCol: 1, label: "Día" },
  week: { colWidth: 90, daysPerCol: 7, label: "Semana" },
  month: { colWidth: 150, daysPerCol: 30, label: "Mes" },
};

function toDateKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function parseDateKey(key: string): Date {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

function addDaysToDate(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

export default function ProjectGanttView({
  projectId: propProjectId,
  projectTitle: propProjectTitle,
  tasks: propTasks,
  phases: propPhases,
  onOpenTask,
  onTaskDatesChange,
}: Props) {
  const { token } = useAuth();
  const { addToast } = useToast();
  const ctx = useProjectUpdate();

  const projectId = propProjectId || ctx.project?.id || "";
  const projectTitle = propProjectTitle || ctx.project?.title || "Proyecto";
  const tasks = propTasks || ctx.tasks || [];
  const phases = propPhases || ctx.phases || [];
  const milestones: ProjectMilestoneRecord[] = ctx.project?.milestones || [];

  // Zoom & View Options
  const [zoom, setZoom] = useState<ZoomLevel>("day");
  const [groupByPhases, setGroupByPhases] = useState(true);
  const [collapsedPhases, setCollapsedPhases] = useState<Record<string, boolean>>({});

  // Dependencies
  const [dependencies, setDependencies] = useState<ProjectTaskDependency[]>([]);
  const [loadingDeps, setLoadingDeps] = useState(false);
  const [showDepDrawer, setShowDepDrawer] = useState(false);
  const [depFormData, setDepFormData] = useState({
    predecessor_id: "",
    successor_id: "",
    dependency_type: "FS" as "FS" | "SS" | "FF",
    lag_days: 0,
  });
  const [savingDep, setSavingDep] = useState(false);
  const [hoveredDepId, setHoveredDepId] = useState<string | null>(null);

  // Critical Path & Baseline (Super-PRO Fase 4)
  const [showCriticalPath, setShowCriticalPath] = useState(false);
  const [criticalPathData, setCriticalPathData] = useState<ProjectCriticalPathSummary | null>(null);
  const [showBaseline, setShowBaseline] = useState(false);
  const [latestBaseline, setLatestBaseline] = useState<ProjectBaseline | null>(null);
  const [showBaselineDrawer, setShowBaselineDrawer] = useState(false);

  // Time window state (base view date)
  const [viewStartDate, setViewStartDate] = useState<Date>(() => {
    const today = new Date();
    today.setDate(today.getDate() - 3);
    return today;
  });

  const timelineContainerRef = useRef<HTMLDivElement>(null);

  // Fetch dependencies
  const fetchDependencies = useCallback(async () => {
    if (!projectId || !token) return;
    try {
      setLoadingDeps(true);
      const data = await apiFetch<ProjectTaskDependency[]>(`/projects/${projectId}/dependencies`, { token });
      setDependencies(Array.isArray(data) ? data : []);
    } catch {
      setDependencies([]);
    } finally {
      setLoadingDeps(false);
    }
  }, [projectId, token]);

  const fetchCriticalPath = useCallback(async () => {
    if (!projectId || !token) return;
    try {
      const data = await apiFetch<ProjectCriticalPathSummary>(`/projects/${projectId}/critical-path`, { token });
      setCriticalPathData(data);
    } catch {
      // fallback silencioso
    }
  }, [projectId, token]);

  const fetchBaselineData = useCallback(async () => {
    if (!projectId || !token) return;
    try {
      const data = await apiFetch<ProjectBaseline>(`/projects/${projectId}/baseline`, { token });
      setLatestBaseline(data);
    } catch {
      // fallback silencioso
    }
  }, [projectId, token]);

  useEffect(() => {
    fetchDependencies();
    fetchCriticalPath();
    fetchBaselineData();
  }, [fetchDependencies, fetchCriticalPath, fetchBaselineData]);

  const criticalPathTaskIds = useMemo(() => {
    return new Set(criticalPathData?.critical_path_task_ids || []);
  }, [criticalPathData]);

  const baselineMap = useMemo(() => {
    const map = new Map<string, { baseline_start?: string | null; baseline_due?: string | null; variance_days?: number }>();
    if (latestBaseline?.comparisons) {
      latestBaseline.comparisons.forEach((c) => {
        map.set(c.task_id, {
          baseline_start: c.baseline_start,
          baseline_due: c.baseline_due,
          variance_days: c.variance_days,
        });
      });
    }
    return map;
  }, [latestBaseline]);

  // Compute overall timeline bounds
  const totalColumns = zoom === "day" ? 45 : zoom === "week" ? 24 : 12;
  const config = ZOOM_CONFIG[zoom];

  const columns = useMemo(() => {
    const cols: { key: string; label: string; subLabel: string; date: Date }[] = [];
    const current = new Date(viewStartDate);

    for (let i = 0; i < totalColumns; i++) {
      const dateKey = toDateKey(current);
      let label = "";
      let subLabel = "";

      if (zoom === "day") {
        const dayNum = current.getDate();
        const weekDay = current.toLocaleDateString("es-ES", { weekday: "narrow" });
        label = String(dayNum);
        subLabel = weekDay.toUpperCase();
      } else if (zoom === "week") {
        label = `Sem ${Math.ceil(current.getDate() / 7)}`;
        subLabel = current.toLocaleDateString("es-ES", { month: "short", day: "numeric" });
      } else {
        label = current.toLocaleDateString("es-ES", { month: "short" }).toUpperCase();
        subLabel = String(current.getFullYear());
      }

      cols.push({
        key: dateKey,
        label,
        subLabel,
        date: new Date(current),
      });

      current.setDate(current.getDate() + config.daysPerCol);
    }
    return cols;
  }, [viewStartDate, totalColumns, zoom, config]);

  const timelineStartTime = useMemo(() => viewStartDate.getTime(), [viewStartDate]);
  const timelineEndTime = useMemo(() => {
    const end = new Date(viewStartDate);
    end.setDate(end.getDate() + totalColumns * config.daysPerCol);
    return end.getTime();
  }, [viewStartDate, totalColumns, config]);

  // Convert Date to X coordinate inside the Gantt canvas
  const getXForDate = useCallback(
    (dateStr?: string | null): number | null => {
      if (!dateStr) return null;
      const targetTime = new Date(dateStr.slice(0, 10) + "T00:00:00").getTime();
      const totalSpan = timelineEndTime - timelineStartTime;
      if (totalSpan <= 0) return null;
      const totalWidth = totalColumns * config.colWidth;
      const ratio = (targetTime - timelineStartTime) / totalSpan;
      return ratio * totalWidth;
    },
    [timelineStartTime, timelineEndTime, totalColumns, config.colWidth]
  );

  // Group tasks by phase or flat list
  const structuredItems = useMemo(() => {
    if (!groupByPhases) {
      return [{ phase: null, tasks }];
    }

    const groups: { phase: { slug: string; name: string; color?: string } | null; tasks: ProjectTaskRecord[] }[] = [];
    phases.forEach((phase) => {
      const phaseTasks = tasks.filter((t) => t.status === phase.slug);
      groups.push({ phase, tasks: phaseTasks });
    });

    const otherTasks = tasks.filter((t) => !phases.some((p) => p.slug === t.status));
    if (otherTasks.length > 0) {
      groups.push({ phase: { slug: "other", name: "Otras Tareas", color: "hsl(var(--muted))" }, tasks: otherTasks });
    }

    return groups;
  }, [groupByPhases, phases, tasks]);

  // Map each task to its row index for dependency arrow drawing
  const taskRowYMap = useMemo(() => {
    const map = new Map<string, number>();
    let currentRow = 0;
    const ROW_HEIGHT = 44;
    const HEADER_OFFSET = 44;

    structuredItems.forEach((group) => {
      if (group.phase) {
        // Group Header row
        currentRow += 1;
        if (collapsedPhases[group.phase.slug]) {
          return;
        }
      }
      group.tasks.forEach((t) => {
        map.set(t.id, HEADER_OFFSET + currentRow * ROW_HEIGHT + ROW_HEIGHT / 2);
        currentRow += 1;
      });
    });

    return map;
  }, [structuredItems, collapsedPhases]);

  // Create dependency handler
  const handleCreateDependency = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!depFormData.predecessor_id || !depFormData.successor_id) {
      addToast({
        title: "Selecciona ambas tareas",
        description: "Debes seleccionar una tarea predecesora y una sucesora.",
        variant: "destructive",
      });
      return;
    }

    if (depFormData.predecessor_id === depFormData.successor_id) {
      addToast({
        title: "Dependencia circular",
        description: "Una tarea no puede depender de sí misma.",
        variant: "destructive",
      });
      return;
    }

    try {
      setSavingDep(true);
      const res = await apiFetch<ProjectTaskDependency>(`/projects/${projectId}/dependencies`, {
        method: "POST",
        token,
        body: depFormData,
      });

      addToast({
        title: "Dependencia conectada",
        description: "Se vinculó la relación Finish-to-Start entre las tareas.",
        variant: "success",
      });

      setDependencies((prev) => [...prev, res]);
      setShowDepDrawer(false);
      setDepFormData({
        predecessor_id: "",
        successor_id: "",
        dependency_type: "FS",
        lag_days: 0,
      });
    } catch {
      addToast({
        title: "Error al crear dependencia",
        description: "No se pudo vincular la dependencia entre tareas.",
        variant: "destructive",
      });
    } finally {
      setSavingDep(false);
    }
  };

  const handleDeleteDependency = async (depId: string) => {
    try {
      await apiFetch(`/projects/${projectId}/dependencies/${depId}`, {
        method: "DELETE",
        token,
      });

      addToast({
        title: "Dependencia eliminada",
        description: "Se retiró la conexión entre las tareas.",
        variant: "default",
      });

      setDependencies((prev) => prev.filter((d) => d.id !== depId));
    } catch {
      addToast({
        title: "Error al eliminar",
        description: "No se pudo remover la dependencia.",
        variant: "destructive",
      });
    }
  };

  const togglePhaseCollapse = (slug: string) => {
    setCollapsedPhases((prev) => ({ ...prev, [slug]: !prev[slug] }));
  };

  const shiftTimeWindow = (direction: -1 | 1) => {
    const daysToShift = zoom === "day" ? 7 : zoom === "week" ? 28 : 90;
    setViewStartDate((prev) => addDaysToDate(prev, direction * daysToShift));
  };

  const goToToday = () => {
    const today = new Date();
    today.setDate(today.getDate() - 3);
    setViewStartDate(today);
  };

  const todayX = getXForDate(toDateKey(new Date()));

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] rounded-xl border border-[hsl(var(--border))] overflow-hidden shadow-sm">
      {/* 1. Header Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]">
            <Calendar size={18} />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
              Gantt PRO & Cronograma
            </h3>
            <span className="text-3xs text-[hsl(var(--muted-foreground))]">
              {tasks.length} tareas · {dependencies.length} dependencias FS · {milestones.length} hitos
            </span>
          </div>
        </div>

        {/* View Controls */}
        <div className="flex items-center gap-2">
          {/* Zoom controls */}
          <div className="flex items-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-0.5 text-2xs font-bold uppercase">
            {(["day", "week", "month"] as ZoomLevel[]).map((z) => (
              <button
                key={z}
                onClick={() => setZoom(z)}
                className={clsx(
                  "px-2.5 py-1 rounded-md transition-all",
                  zoom === z
                    ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-xs"
                    : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                )}
              >
                {ZOOM_CONFIG[z].label}
              </button>
            ))}
          </div>

          {/* Grouping Toggle */}
          <button
            onClick={() => setGroupByPhases(!groupByPhases)}
            className={clsx(
              "px-2.5 py-1.5 rounded-lg border text-2xs font-bold uppercase tracking-wide flex items-center gap-1.5 transition-all",
              groupByPhases
                ? "bg-[hsl(var(--primary))]/10 border-[hsl(var(--primary))]/30 text-[hsl(var(--primary))]"
                : "border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))]"
            )}
          >
            <Layers size={13} /> WBS Fases
          </button>

          {/* Date Navigation */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => shiftTimeWindow(-1)}
              className="p-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]"
              title="Atrás"
            >
              <ChevronLeft size={14} />
            </button>
            <button
              onClick={goToToday}
              className="px-2 py-1 text-3xs font-bold uppercase border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] rounded-lg"
            >
              Hoy
            </button>
            <button
              onClick={() => shiftTimeWindow(1)}
              className="p-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]"
              title="Adelante"
            >
              <ChevronRight size={14} />
            </button>
          </div>

          {/* Critical Path Toggle (Super-PRO Fase 4) */}
          <button
            onClick={() => setShowCriticalPath(!showCriticalPath)}
            className={clsx(
              "px-2.5 py-1.5 rounded-lg border text-2xs font-bold uppercase tracking-wide flex items-center gap-1.5 transition-all cursor-pointer",
              showCriticalPath
                ? "bg-[hsl(var(--destructive))]/15 border-[hsl(var(--destructive))]/40 text-[hsl(var(--destructive))]"
                : "border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
            )}
            title="Resaltar método de la ruta crítica (CPM)"
          >
            <Zap size={13} className={showCriticalPath ? "text-[hsl(var(--destructive))]" : ""} />
            Ruta Crítica {criticalPathData?.critical_tasks_count ? `(${criticalPathData.critical_tasks_count})` : ""}
          </button>

          {/* Baseline Toggle (Super-PRO Fase 4) */}
          <button
            onClick={() => setShowBaseline(!showBaseline)}
            className={clsx(
              "px-2.5 py-1.5 rounded-lg border text-2xs font-bold uppercase tracking-wide flex items-center gap-1.5 transition-all cursor-pointer",
              showBaseline
                ? "bg-[hsl(var(--primary))]/15 border-[hsl(var(--primary))]/40 text-[hsl(var(--primary))]"
                : "border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
            )}
            title="Superponer cronograma planificado de la línea base"
          >
            <Sliders size={13} className={showBaseline ? "text-[hsl(var(--primary))]" : ""} />
            Línea Base
          </button>

          {/* Manage Baseline Drawer Button */}
          <button
            onClick={() => setShowBaselineDrawer(true)}
            className="px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-2xs font-bold uppercase tracking-wide flex items-center gap-1.5 text-[hsl(var(--foreground))] transition-all cursor-pointer"
            title="Fijar y auditar varianza de línea base"
          >
            <Layers size={13} /> Fijar Base
          </button>

          {/* Add Dependency Button */}
          <button
            onClick={() => setShowDepDrawer(true)}
            className="px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wide hover:opacity-90 active:scale-95 transition-all flex items-center gap-1.5 shadow-xs cursor-pointer"
          >
            <Link2 size={13} /> Conectar FS
          </button>
        </div>
      </div>

      {/* 2. Main Gantt Area: Split into Left Tasks Column & Right Timeline */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Left Tasks Tree (WBS) */}
        <div className="w-72 shrink-0 border-r border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex flex-col min-h-0">
          <div className="h-11 px-3 flex items-center justify-between border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            <span>Estructura de Tareas (WBS)</span>
            <span>Estado</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-[hsl(var(--border))]/50">
            {structuredItems.map((group, gIdx) => {
              const isCollapsed = group.phase ? collapsedPhases[group.phase.slug] : false;
              return (
                <div key={group.phase?.slug || `group-${gIdx}`} className="space-y-0">
                  {/* Phase Section Header */}
                  {group.phase && (
                    <div
                      onClick={() => togglePhaseCollapse(group.phase!.slug)}
                      className="h-11 px-3 flex items-center justify-between bg-[hsl(var(--surface-2))]/60 hover:bg-[hsl(var(--surface-2))] cursor-pointer font-bold text-xs select-none transition-colors border-b border-[hsl(var(--border))]/40"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <ChevronDown
                          size={14}
                          className={clsx(
                            "text-[hsl(var(--muted-foreground))] transition-transform duration-200",
                            isCollapsed && "-rotate-90"
                          )}
                        />
                        <div
                          className="size-2 rounded-full shrink-0"
                          style={{ backgroundColor: group.phase.color || "hsl(var(--primary))" }}
                        />
                        <span className="truncate text-[hsl(var(--foreground))]">
                          {group.phase.name}
                        </span>
                      </div>
                      <span className="text-3xs font-semibold px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]">
                        {group.tasks.length}
                      </span>
                    </div>
                  )}

                  {/* Tasks in Phase */}
                  {!isCollapsed &&
                    group.tasks.map((task) => {
                      const isTaskCrit = showCriticalPath && criticalPathTaskIds.has(task.id);
                      return (
                        <div
                          key={task.id}
                          onClick={() => onOpenTask(task)}
                          className={clsx(
                            "h-11 px-3 flex items-center justify-between hover:bg-[hsl(var(--surface-2))]/80 cursor-pointer transition-colors group",
                            isTaskCrit && "bg-[hsl(var(--destructive))]/5"
                          )}
                        >
                          <div className="flex items-center gap-2 min-w-0 pr-2">
                            <span
                              className={clsx(
                                "size-2 rounded-full shrink-0",
                                isTaskCrit
                                  ? "bg-[hsl(var(--destructive))]"
                                  : task.status === "completed"
                                  ? "bg-[hsl(var(--success))]"
                                  : task.priority === "urgent"
                                  ? "bg-[hsl(var(--destructive))]"
                                  : "bg-[hsl(var(--primary))]"
                              )}
                            />
                            <span className="text-xs text-[hsl(var(--foreground))] truncate group-hover:text-[hsl(var(--primary))] transition-colors">
                              {task.title}
                            </span>
                            {isTaskCrit && (
                              <span className="px-1 py-0.2 rounded text-3xs font-black bg-[hsl(var(--destructive))]/15 text-[hsl(var(--destructive))] shrink-0 uppercase tracking-tight">
                                CPM
                              </span>
                            )}
                          </div>
                          <span className="text-3xs uppercase font-bold text-[hsl(var(--muted-foreground))] shrink-0">
                            {task.status}
                          </span>
                        </div>
                      );
                    })}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Gantt Canvas & Timeline Grid */}
        <div
          ref={timelineContainerRef}
          className="flex-1 overflow-x-auto overflow-y-auto relative bg-[hsl(var(--surface-1))]"
        >
          <div
            className="relative min-h-full"
            style={{ width: `${totalColumns * config.colWidth}px` }}
          >
            {/* Timeline Header Days/Weeks */}
            <div className="h-11 flex border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] sticky top-0 z-20">
              {columns.map((col) => (
                <div
                  key={col.key}
                  style={{ width: `${config.colWidth}px` }}
                  className="shrink-0 flex flex-col items-center justify-center border-r border-[hsl(var(--border))]/40 text-center select-none"
                >
                  <span className="text-2xs font-bold text-[hsl(var(--foreground))]">
                    {col.label}
                  </span>
                  <span className="text-3xs text-[hsl(var(--muted-foreground))] uppercase font-medium">
                    {col.subLabel}
                  </span>
                </div>
              ))}
            </div>

            {/* Vertical Today Line */}
            {todayX !== null && todayX >= 0 && todayX <= totalColumns * config.colWidth && (
              <div
                className="absolute top-0 bottom-0 z-10 w-0.5 bg-[hsl(var(--destructive))] pointer-events-none"
                style={{ left: `${todayX}px` }}
              >
                <div className="sticky top-11 px-1 py-0.5 rounded text-3xs font-black uppercase tracking-wider bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] -translate-x-1/2">
                  Hoy
                </div>
              </div>
            )}

            {/* Milestone Diamond Markers Overlay */}
            {milestones.map((m) => {
              const mx = getXForDate(m.target_date);
              if (mx === null || mx < 0 || mx > totalColumns * config.colWidth) return null;
              return (
                <div
                  key={m.id}
                  className="absolute top-12 z-20 group -translate-x-1/2 cursor-pointer"
                  style={{ left: `${mx}px` }}
                  title={`Hito: ${m.title} (${m.target_date?.slice(0, 10)})`}
                >
                  <div
                    className={clsx(
                      "size-4 rotate-45 border-2 shadow-md flex items-center justify-center transition-transform hover:scale-125",
                      m.is_completed
                        ? "bg-[hsl(var(--success))] border-[hsl(var(--primary-foreground))]"
                        : "bg-[hsl(var(--warning))] border-[hsl(var(--primary-foreground))]"
                    )}
                  />
                  <div className="hidden group-hover:block absolute left-1/2 -translate-x-1/2 top-5 px-2 py-1 rounded bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))] text-3xs font-bold text-[hsl(var(--foreground))] shadow-lg whitespace-nowrap z-30">
                    <Milestone size={11} className="inline mr-1 text-[hsl(var(--warning))]" />
                    {m.title}
                  </div>
                </div>
              );
            })}

            {/* SVG Dependencies Overlay (Arrows connecting Tasks) */}
            <svg
              className="absolute inset-0 pointer-events-none z-10 w-full h-full"
              style={{ minHeight: "100%" }}
            >
              <defs>
                <marker
                  id="gantt-arrow"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="hsl(var(--primary))" />
                </marker>
                <marker
                  id="gantt-arrow-active"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="hsl(var(--destructive))" />
                </marker>
              </defs>

              {dependencies.map((dep) => {
                const predTask = tasks.find((t) => t.id === dep.predecessor_id);
                const succTask = tasks.find((t) => t.id === dep.successor_id);
                if (!predTask || !succTask) return null;

                const predY = taskRowYMap.get(predTask.id);
                const succY = taskRowYMap.get(succTask.id);
                if (predY === undefined || succY === undefined) return null;

                const predEndStr = predTask.due_date || predTask.start_date || toDateKey(new Date());
                const succStartStr = succTask.start_date || succTask.due_date || toDateKey(new Date());

                const predX = getXForDate(predEndStr);
                const succX = getXForDate(succStartStr);
                if (predX === null || succX === null) return null;

                const isHovered = hoveredDepId === dep.id;
                const isCriticalDep =
                  showCriticalPath &&
                  criticalPathTaskIds.has(dep.predecessor_id) &&
                  criticalPathTaskIds.has(dep.successor_id);

                // Calculate stepped path
                const startX = predX;
                const startY = predY;
                const endX = succX;
                const endY = succY;
                const midX = startX + Math.max(16, (endX - startX) / 2);

                const pathData = `M ${startX} ${startY} H ${midX} V ${endY} H ${endX}`;

                return (
                  <g
                    key={dep.id}
                    className="pointer-events-auto cursor-pointer"
                    onMouseEnter={() => setHoveredDepId(dep.id)}
                    onMouseLeave={() => setHoveredDepId(null)}
                    onClick={() => handleDeleteDependency(dep.id)}
                  >
                    <path
                      d={pathData}
                      fill="none"
                      stroke="transparent"
                      strokeWidth={12}
                    />
                    <path
                      d={pathData}
                      fill="none"
                      stroke={isHovered || isCriticalDep ? "hsl(var(--destructive))" : "hsl(var(--primary))"}
                      strokeWidth={isHovered ? 2.5 : isCriticalDep ? 2.75 : 1.75}
                      strokeDasharray={dep.dependency_type === "SS" ? "4,4" : undefined}
                      markerEnd={isHovered || isCriticalDep ? "url(#gantt-arrow-active)" : "url(#gantt-arrow)"}
                      className="transition-colors duration-150"
                    />
                  </g>
                );
              })}
            </svg>

            {/* Task Rows & Bars Rendering */}
            <div className="divide-y divide-[hsl(var(--border))]/50">
              {structuredItems.map((group, gIdx) => {
                const isCollapsed = group.phase ? collapsedPhases[group.phase.slug] : false;
                return (
                  <div key={group.phase?.slug || `timeline-group-${gIdx}`}>
                    {/* Phase Header Background Row */}
                    {group.phase && (
                      <div className="h-11 bg-[hsl(var(--surface-2))]/30 border-b border-[hsl(var(--border))]/40 relative" />
                    )}

                    {/* Task Timeline Rows */}
                    {!isCollapsed &&
                      group.tasks.map((task) => {
                        const startKey = task.start_date
                          ? task.start_date.slice(0, 10)
                          : task.created_at
                          ? task.created_at.slice(0, 10)
                          : toDateKey(new Date());

                        const dueKey = task.due_date
                          ? task.due_date.slice(0, 10)
                          : startKey;

                        const startX = getXForDate(startKey) ?? 0;
                        const endX = getXForDate(dueKey) ?? startX + 44;
                        const width = Math.max(36, endX - startX + config.colWidth * 0.8);

                        const isCompleted = task.status === "completed";
                        const isOverdue =
                          !isCompleted &&
                          task.due_date &&
                          new Date(task.due_date).getTime() < new Date().getTime();
                        const isCritical = showCriticalPath && criticalPathTaskIds.has(task.id);
                        const baselineData = showBaseline ? baselineMap.get(task.id) : null;

                        return (
                          <div
                            key={task.id}
                            className="h-11 relative flex items-center hover:bg-[hsl(var(--surface-2))]/30 transition-colors"
                          >
                            {/* Baseline Ghost Bar (Underlay) */}
                            {showBaseline && baselineData && baselineData.baseline_due && (() => {
                              const bStart = baselineData.baseline_start ? baselineData.baseline_start.slice(0, 10) : startKey;
                              const bDue = baselineData.baseline_due.slice(0, 10);
                              const bX = getXForDate(bStart) ?? startX;
                              const bEndX = getXForDate(bDue) ?? (bX + 44);
                              const bW = Math.max(30, bEndX - bX + config.colWidth * 0.8);
                              return (
                                <div
                                  style={{
                                    left: `${Math.max(0, bX)}px`,
                                    width: `${bW}px`,
                                  }}
                                  className="absolute -bottom-1 h-1.5 rounded-xs bg-[hsl(var(--primary))]/30 border border-dashed border-[hsl(var(--primary))]/70 pointer-events-none z-0"
                                  title={`Línea Base: ${bStart} → ${bDue} (Varianza: ${baselineData.variance_days ?? 0}d)`}
                                />
                              );
                            })()}

                            {/* Gantt Bar */}
                            <div
                              onClick={() => onOpenTask(task)}
                              style={{
                                left: `${Math.max(0, startX)}px`,
                                width: `${width}px`,
                              }}
                              className={clsx(
                                "absolute h-7 rounded-lg border shadow-xs flex items-center px-2.5 cursor-pointer transition-all duration-200 select-none group/bar z-10",
                                isCritical
                                  ? "bg-[hsl(var(--destructive))]/25 border-[hsl(var(--destructive))] text-[hsl(var(--destructive))] ring-1 ring-[hsl(var(--destructive))] shadow-sm"
                                  : isCompleted
                                  ? "bg-[hsl(var(--success))]/20 border-[hsl(var(--success))]/50 text-[hsl(var(--success))]"
                                  : isOverdue
                                  ? "bg-[hsl(var(--destructive))]/20 border-[hsl(var(--destructive))]/50 text-[hsl(var(--destructive))]"
                                  : "bg-[hsl(var(--primary))]/20 border-[hsl(var(--primary))]/50 text-[hsl(var(--primary))]"
                              )}
                            >
                              {/* Progress Fill */}
                              <div
                                className={clsx(
                                  "absolute inset-0 rounded-md opacity-25",
                                  isCritical
                                    ? "bg-[hsl(var(--destructive))]"
                                    : isCompleted
                                    ? "bg-[hsl(var(--success))]"
                                    : "bg-[hsl(var(--primary))]"
                                )}
                                style={{ width: isCompleted ? "100%" : "40%" }}
                              />

                              {isCritical && (
                                <Zap size={10} className="fill-[hsl(var(--destructive))] text-[hsl(var(--destructive))] shrink-0 mr-1" />
                              )}

                              <span className="relative z-10 text-2xs font-bold truncate">
                                {task.title}
                              </span>

                              {/* Dates badge on hover */}
                              <div className="hidden group-hover/bar:flex absolute -top-7 left-0 px-2 py-0.5 rounded bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))] text-3xs font-bold text-[hsl(var(--foreground))] shadow-md whitespace-nowrap z-30 items-center gap-1.5">
                                <Clock size={10} />
                                {startKey} → {dueKey}
                                {isCritical && <span className="text-[hsl(var(--destructive))] font-black ml-1">[Ruta Crítica]</span>}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Dependency Creation Drawer (SidePanel) */}
      <RightPanel
        title="Vincular Dependencia (Finish to Start)"
        open={showDepDrawer}
        onClose={() => setShowDepDrawer(false)}
        width={380}
      >
        <form onSubmit={handleCreateDependency} className="flex flex-col h-full space-y-4 p-4 text-[hsl(var(--foreground))]">
          <div className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex items-start gap-2.5 shadow-sm">
            <div className="p-2 rounded-lg bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] shrink-0">
              <Link2 size={18} />
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                Dependencia Secuencial (FS)
              </h4>
              <p className="text-2xs text-[hsl(var(--muted-foreground))] mt-0.5">
                La tarea sucesora no podrá iniciar hasta que la predecesora haya finalizado.
              </p>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-2xs font-bold uppercase text-[hsl(var(--muted-foreground))]">
              Tarea Predecesora (Bloqueante) *
            </label>
            <select
              required
              value={depFormData.predecessor_id}
              onChange={(e) => setDepFormData({ ...depFormData, predecessor_id: e.target.value })}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
            >
              <option value="">Selecciona la tarea previa...</option>
              {tasks.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title} ({t.status})
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-2xs font-bold uppercase text-[hsl(var(--muted-foreground))]">
              Tarea Sucesora (Dependiente) *
            </label>
            <select
              required
              value={depFormData.successor_id}
              onChange={(e) => setDepFormData({ ...depFormData, successor_id: e.target.value })}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
            >
              <option value="">Selecciona la tarea dependiente...</option>
              {tasks
                .filter((t) => t.id !== depFormData.predecessor_id)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title} ({t.status})
                  </option>
                ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="text-2xs font-bold uppercase text-[hsl(var(--muted-foreground))]">
                Tipo de Enlace
              </label>
              <select
                value={depFormData.dependency_type}
                onChange={(e) => setDepFormData({ ...depFormData, dependency_type: e.target.value as any })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
              >
                <option value="FS">FS (Fin a Inicio)</option>
                <option value="SS">SS (Inicio a Inicio)</option>
                <option value="FF">FF (Fin a Fin)</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-2xs font-bold uppercase text-[hsl(var(--muted-foreground))]">
                Lag (Días de desfase)
              </label>
              <input
                type="number"
                min={0}
                value={depFormData.lag_days}
                onChange={(e) => setDepFormData({ ...depFormData, lag_days: Number(e.target.value) })}
                className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
              />
            </div>
          </div>

          <div className="mt-auto pt-3 border-t border-[hsl(var(--border))] flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowDepDrawer(false)}
              className="px-3 py-1.5 text-2xs font-bold uppercase tracking-wider rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={savingDep}
              className="px-4 py-1.5 text-2xs font-bold uppercase tracking-wider rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 active:scale-95 transition-all flex items-center gap-1.5 shadow"
            >
              <Plus size={13} /> {savingDep ? "Guardando..." : "Crear Enlace"}
            </button>
          </div>
        </form>
      </RightPanel>

      {/* 4. Project Baseline Drawer (SidePanel) */}
      <ProjectBaselineDrawer
        projectId={projectId}
        isOpen={showBaselineDrawer}
        onClose={() => setShowBaselineDrawer(false)}
        onBaselineUpdated={() => {
          fetchBaselineData();
          fetchCriticalPath();
        }}
      />
    </div>
  );
}

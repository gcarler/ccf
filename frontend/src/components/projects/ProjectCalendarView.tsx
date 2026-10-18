"use client";

import { useState, useEffect, useMemo } from "react";
import clsx from "clsx";
import { AlertTriangle, CalendarClock, CheckCircle2, Flame } from "lucide-react";
import UniversalCalendarView from "@/components/ui/UniversalCalendarView";
import TaskCreationDrawer from "@/components/projects/TaskCreationDrawer";
import { useProjectTasks } from "@/hooks/useProjectTasks";
import type { ProjectTaskRecord } from "@/types/projects";

type CalendarEvent = {
    id: string | number;
    title: string;
    date: string;
    color?: "blue" | "emerald" | "amber" | "rose" | "sky";
};

type CalendarPmiFilter = "ALL" | "OVERDUE" | "CRITICAL_WINDOW" | "CRITICAL_PRIORITY";

const CALENDAR_PMI_FILTERS: { key: CalendarPmiFilter; label: string }[] = [
    { key: "ALL", label: "Todos" },
    { key: "OVERDUE", label: "Vencidos" },
    { key: "CRITICAL_WINDOW", label: "Ventana 7d" },
    { key: "CRITICAL_PRIORITY", label: "Críticos / Urgentes" },
];

function toDateKey(date: Date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function addDaysKey(baseDate: Date, days: number) {
    const next = new Date(baseDate);
    next.setDate(next.getDate() + days);
    return toDateKey(next);
}

function isTaskCompleted(task: ProjectTaskRecord): boolean {
    const pct = Number(task.progress ?? task.physical_progress_pct ?? task.progress_pct ?? 0);
    return (
        task.status === "completed" ||
        task.status === "done" ||
        pct >= 100
    );
}

interface Props {
    projectId: string;
    projectTitle?: string;
    tasks: ProjectTaskRecord[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onCreateTask: (data: { title: string; description: string; priority: string; status: string; due_date?: string; node?: string | null }) => Promise<boolean | void> | boolean | void;
}

export default function ProjectCalendarView({ projectId, projectTitle, tasks, onOpenTask, onCreateTask }: Props) {
    const { updateTask } = useProjectTasks({ projectId });
    const [showCreateDrawer, setShowCreateDrawer] = useState(false);
    const [draftDueDate, setDraftDueDate] = useState<string | undefined>(undefined);
    const [calendarTasks, setCalendarTasks] = useState<ProjectTaskRecord[]>(tasks);
    const [pmiFilter, setPmiFilter] = useState<CalendarPmiFilter>("ALL");

    useEffect(() => {
        setCalendarTasks(tasks);
    }, [tasks]);

    const todayKey = useMemo(() => toDateKey(new Date()), []);
    const sevenDaysKey = useMemo(() => addDaysKey(new Date(), 7), []);

    const scheduleMetrics = useMemo(() => {
        let overdueCount = 0;
        let dueSoonCount = 0;
        let criticalCount = 0;

        for (const task of calendarTasks) {
            const completed = isTaskCompleted(task);
            const dueKey = task.due_date ? task.due_date.slice(0, 10) : null;
            if (!completed && dueKey) {
                if (dueKey < todayKey) {
                    overdueCount += 1;
                } else if (dueKey >= todayKey && dueKey <= sevenDaysKey) {
                    dueSoonCount += 1;
                }
            }
            if (task.priority === "urgent" || task.priority === "high") {
                criticalCount += 1;
            }
        }

        const total = calendarTasks.length;
        const onTimeRate = total > 0 ? Math.round(((total - overdueCount) / total) * 100) : 100;

        return {
            total,
            overdueCount,
            dueSoonCount,
            criticalCount,
            onTimeRate,
        };
    }, [calendarTasks, sevenDaysKey, todayKey]);

    const filteredTasks = useMemo(() => {
        if (pmiFilter === "ALL") return calendarTasks;
        return calendarTasks.filter((task) => {
            const completed = isTaskCompleted(task);
            const dueKey = task.due_date ? task.due_date.slice(0, 10) : null;
            if (pmiFilter === "OVERDUE") {
                return !completed && Boolean(dueKey && dueKey < todayKey);
            }
            if (pmiFilter === "CRITICAL_WINDOW") {
                return !completed && Boolean(dueKey && dueKey >= todayKey && dueKey <= sevenDaysKey);
            }
            if (pmiFilter === "CRITICAL_PRIORITY") {
                return task.priority === "urgent" || task.priority === "high";
            }
            return true;
        });
    }, [calendarTasks, pmiFilter, sevenDaysKey, todayKey]);

    const events: CalendarEvent[] = useMemo(
        () =>
            filteredTasks.map((task) => ({
                id: task.id,
                title: task.title,
                date: (task.due_date || task.start_date || todayKey).slice(0, 10),
                color:
                    task.status === "completed"
                        ? "emerald"
                        : task.priority === "urgent"
                          ? "rose"
                          : task.status === "review"
                            ? "amber"
                            : "blue",
            })),
        [filteredTasks, todayKey]
    );

    const handleDateClick = (date: Date) => {
        setDraftDueDate(toDateKey(date));
        setShowCreateDrawer(true);
    };

    const handleEventClick = (event: CalendarEvent) => {
        const task = calendarTasks.find((t) => t.id === String(event.id));
        if (task) onOpenTask(task);
    };

    const handleEventMove = async (event: CalendarEvent, date: Date) => {
        const newDueDate = toDateKey(date);
        const task = calendarTasks.find((t) => String(t.id) === String(event.id));
        if (!task) return;
        const currentDueDate = task.due_date ? task.due_date.slice(0, 10) : null;
        if (currentDueDate === newDueDate) return;
        // Capture previous value for targeted rollback on failure (avoid wiping
        // out concurrent edits from other events between optimistic update and
        // server roundtrip).
        const previousDueDate = task.due_date;
        setCalendarTasks((prev) =>
            prev.map((item) =>
                String(item.id) === String(event.id)
                    ? { ...item, due_date: newDueDate }
                    : item
            )
        );
        const updated = await updateTask(String(event.id), { due_date: newDueDate }, { optimistic: true });
        if (!updated) {
            setCalendarTasks((prev) =>
                prev.map((item) =>
                    String(item.id) === String(event.id)
                        ? { ...item, due_date: previousDueDate }
                        : item
                )
            );
        }
    };

    const handleSubmit = async (data: { title: string; description: string; priority: string; status: string; node?: string | null }) => {
        const result = await onCreateTask({ ...data, due_date: draftDueDate });
        if (result === true || result === undefined) {
            setShowCreateDrawer(false);
            setDraftDueDate(undefined);
        }
    };

    return (
        <div className="space-y-4">
            <section
                data-testid="calendar-pmi-schedule-hud"
                aria-label="Gobernanza de Cronograma y Ventana Crítica PMI §6.5"
                className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-3"
            >
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-primary))]">
                            Gobernanza de Cronograma y Ventana Crítica (PMI §6.5)
                        </p>
                        <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                            Control de paquetes vencidos, ventana de entrega a 7 días y prioridad crítica
                        </p>
                    </div>
                    <div
                        data-testid="calendar-pmi-filter"
                        role="group"
                        aria-label="Filtrar eventos del calendario PMI"
                        className="flex flex-wrap items-center gap-1.5"
                    >
                        {CALENDAR_PMI_FILTERS.map((option) => {
                            const count =
                                option.key === "ALL"
                                    ? scheduleMetrics.total
                                    : option.key === "OVERDUE"
                                      ? scheduleMetrics.overdueCount
                                      : option.key === "CRITICAL_WINDOW"
                                        ? scheduleMetrics.dueSoonCount
                                        : scheduleMetrics.criticalCount;
                            const active = pmiFilter === option.key;
                            return (
                                <button
                                    key={option.key}
                                    type="button"
                                    data-testid={`calendar-pmi-filter-${option.key.toLowerCase()}`}
                                    aria-pressed={active}
                                    onClick={() => setPmiFilter(option.key)}
                                    className={clsx(
                                        "rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors",
                                        active
                                            ? "border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"
                                            : "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                                    )}
                                >
                                    {option.label} ({count})
                                </button>
                            );
                        })}
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-2.5">
                        <div className="flex items-center justify-between text-[11px] font-medium text-[hsl(var(--text-secondary))]">
                            <span>Paquetes Vencidos</span>
                            <AlertTriangle className="h-3.5 w-3.5 text-[hsl(var(--destructive))]" />
                        </div>
                        <p
                            data-testid="calendar-pmi-overdue-count"
                            className="mt-1 text-lg font-bold tabular-nums text-[hsl(var(--text-primary))]"
                        >
                            {scheduleMetrics.overdueCount}
                        </p>
                    </div>
                    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-2.5">
                        <div className="flex items-center justify-between text-[11px] font-medium text-[hsl(var(--text-secondary))]">
                            <span>Ventana Crítica 7 Días</span>
                            <CalendarClock className="h-3.5 w-3.5 text-[hsl(var(--warning-text))]" />
                        </div>
                        <p
                            data-testid="calendar-pmi-due-soon-count"
                            className="mt-1 text-lg font-bold tabular-nums text-[hsl(var(--text-primary))]"
                        >
                            {scheduleMetrics.dueSoonCount}
                        </p>
                    </div>
                    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-2.5">
                        <div className="flex items-center justify-between text-[11px] font-medium text-[hsl(var(--text-secondary))]">
                            <span>Prioridad Crítica / Alta</span>
                            <Flame className="h-3.5 w-3.5 text-[hsl(var(--primary))]" />
                        </div>
                        <p
                            data-testid="calendar-pmi-critical-count"
                            className="mt-1 text-lg font-bold tabular-nums text-[hsl(var(--text-primary))]"
                        >
                            {scheduleMetrics.criticalCount}
                        </p>
                    </div>
                    <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-2.5">
                        <div className="flex items-center justify-between text-[11px] font-medium text-[hsl(var(--text-secondary))]">
                            <span>Tasa Cumplimiento Temporal</span>
                            <CheckCircle2 className="h-3.5 w-3.5 text-[hsl(var(--success))]" />
                        </div>
                        <p
                            data-testid="calendar-pmi-ontime-rate"
                            className="mt-1 text-lg font-bold tabular-nums text-[hsl(var(--text-primary))]"
                        >
                            {scheduleMetrics.onTimeRate}%
                        </p>
                    </div>
                </div>

                {scheduleMetrics.overdueCount > 0 && (
                    <div
                        data-testid="calendar-pmi-overdue-alert"
                        role="status"
                        className="flex items-center gap-2 rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.1)] px-3 py-2 text-xs font-semibold text-[hsl(var(--destructive))]"
                    >
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        <span>
                            Alerta PMI §6.5: {scheduleMetrics.overdueCount} paquete(s) con fecha límite vencida requieren reprogramación o acción correctiva.
                        </span>
                    </div>
                )}
            </section>

            <UniversalCalendarView
                events={events}
                title={`Calendario: ${projectTitle || "Proyecto"}`}
                onDateClick={handleDateClick}
                onEventClick={handleEventClick}
                onEventMove={handleEventMove}
            />
            <TaskCreationDrawer
                isOpen={showCreateDrawer}
                onClose={() => {
                    setShowCreateDrawer(false);
                    setDraftDueDate(undefined);
                }}
                onSubmit={handleSubmit}
            />
        </div>
    );
}


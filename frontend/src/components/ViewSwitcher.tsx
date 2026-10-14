"use client";

import React, { useEffect } from "react";
import { LayoutGrid, List, Kanban, GanttChart, CalendarDays, BookOpen, LayoutDashboard, TableProperties, Workflow } from "lucide-react";
import clsx from "clsx";

export type ViewType = "dashboard" | "grid" | "list" | "kanban" | "table" | "gantt" | "calendar" | "board" | "wiki" | "chat" | "workflow";

interface ViewOption {
    id: ViewType;
    label: string;
    icon: React.ElementType;
}

const ALL_VIEWS: ViewOption[] = [
    { id: "dashboard", label: "Resumen", icon: LayoutDashboard },
    { id: "table", label: "Tabla", icon: TableProperties },
    { id: "list", label: "Lista", icon: List },
    { id: "grid", label: "Grid", icon: LayoutGrid },
    { id: "board", label: "Tablero", icon: Kanban },
    { id: "kanban", label: "Kanban", icon: Kanban },
    { id: "gantt", label: "Gantt", icon: GanttChart },
    { id: "calendar", label: "Calendario", icon: CalendarDays },
    { id: "workflow", label: "Workflow", icon: Workflow },
    { id: "wiki", label: "Wiki", icon: BookOpen },
];

interface ViewSwitcherProps {
    viewType: ViewType;
    setViewType: (v: ViewType) => void;
    /** Restrict which views are shown. Defaults to all */
    availableViews?: ViewType[];
    storageKey?: string;
}

export default function ViewSwitcher({
    viewType,
    setViewType,
    availableViews = ["table", "list", "grid", "kanban", "board", "gantt", "calendar", "workflow", "wiki"],
    storageKey,
}: ViewSwitcherProps) {
    // Persist preference
    useEffect(() => {
        if (storageKey) {
            localStorage.setItem(storageKey, viewType);
        }
    }, [viewType, storageKey]);

    const options = ALL_VIEWS.filter((v) => availableViews.includes(v.id));

    return (
        <div className="flex items-center gap-0.5 p-1 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10">
            {options.map(({ id, label, icon: Icon }) => (
                <button
                    key={id}
                    type="button"
                    title={label}
                    aria-label={label}
                    aria-pressed={viewType === id}
                    onClick={() => setViewType(id)}
                    className={clsx(
                        "flex items-center justify-center w-8 h-8 rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2",
                        viewType === id
                            ? "border-[hsl(var(--primary)/0.5)] bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))] shadow-sm"
                            : "border-transparent text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))] hover:text-[hsl(var(--text-primary))]"
                    )}
                >
                    <Icon size={14} />
                </button>
            ))}
        </div>
    );
}

/** Helper to read stored view, falling back to a default */
export function getStoredView(storageKey: string, fallback: ViewType = "table"): ViewType {
    if (typeof window === "undefined") return fallback;
    const stored = localStorage.getItem(storageKey) as ViewType | null;
    return stored ?? fallback;
}

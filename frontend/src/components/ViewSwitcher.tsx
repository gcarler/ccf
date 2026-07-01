"use client";

import React, { useEffect } from "react";
import { LayoutGrid, List, Kanban, GanttChart, CalendarDays, BookOpen, LayoutDashboard, TableProperties } from "lucide-react";
import clsx from "clsx";

export type ViewType = "dashboard" | "grid" | "list" | "kanban" | "table" | "gantt" | "calendar" | "board" | "wiki" | "chat";

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
    availableViews = ["table", "list", "grid", "kanban", "board", "gantt", "calendar", "wiki"],
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
                    title={label}
                    onClick={() => setViewType(id)}
                    className={clsx(
                        "flex items-center justify-center w-7 h-7 rounded-md transition-all",
                        viewType === id
                            ? "bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] dark:text-white shadow-sm"
                            : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]"
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

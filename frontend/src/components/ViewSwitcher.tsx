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
        <div className="flex items-center gap-0.5 p-1 bg-slate-100 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/10">
            {options.map(({ id, label, icon: Icon }) => (
                <button
                    key={id}
                    title={label}
                    onClick={() => setViewType(id)}
                    className={clsx(
                        "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-bold uppercase tracking-wide transition-all",
                        viewType === id
                            ? "bg-[hsl(var(--bg-primary))] dark:bg-slate-700 text-slate-800 dark:text-white shadow-sm"
                            : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                    )}
                >
                    <Icon size={13} />
                    <span className="hidden md:inline">{label}</span>
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

"use client";

import { useState, useEffect, useCallback } from "react";
import { ViewType } from "@/components/ViewSwitcher";

const PREFIX = "ccf_view_";

export function getStoredView(key: string, fallback: ViewType = "table"): ViewType {
    if (typeof window === "undefined") return fallback;
    return (sessionStorage.getItem(PREFIX + key) as ViewType) || fallback;
}

export function useViewType(key: string, fallback: ViewType = "table") {
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView(key, fallback));

    const onViewChange = useCallback((next: ViewType) => {
        setViewType(next);
        if (typeof window !== "undefined") {
            sessionStorage.setItem(PREFIX + key, next);
        }
    }, [key]);

    return { viewType, setViewType: onViewChange };
}

// View presets
export const FULL_VIEWS: ViewType[] = ["dashboard", "table", "list", "grid", "board", "kanban", "calendar", "gantt", "wiki"];
export const OPERATIONAL_VIEWS: ViewType[] = ["table", "list", "grid", "board", "kanban"];
export const TEMPORAL_VIEWS: ViewType[] = ["calendar", "gantt", "table", "list"];
export const MINIMAL_VIEWS: ViewType[] = ["table", "list", "grid"];

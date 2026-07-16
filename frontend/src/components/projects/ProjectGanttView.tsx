"use client";

import React from "react";
import UniversalGanttView, { type GanttItem } from "@/components/ui/UniversalGanttView";
import type { ProjectTaskRecord } from "@/types/projects";

function toDateKey(date: Date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

interface Props {
    projectTitle?: string;
    tasks: ProjectTaskRecord[];
    phases: { slug: string; name: string }[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onTaskDatesChange?: (taskId: string, start_date: string, end_date: string) => void;
}

export default function ProjectGanttView({ projectTitle, tasks, phases, onOpenTask, onTaskDatesChange }: Props) {
    const items: GanttItem[] = tasks.map((task) => ({
        id: task.id,
        title: task.title,
        subtitle: phases.find((p) => p.slug === task.status)?.name || task.status,
        start_date: (task.start_date || task.created_at || toDateKey(new Date())).slice(0, 10),
        end_date: (task.due_date || task.start_date || task.created_at || toDateKey(new Date())).slice(0, 10),
        color: task.status === "completed" ? "emerald" : task.priority === "urgent" ? "rose" : "blue",
        progress: task.status === "completed" ? 100 : task.status === "review" ? 75 : task.status === "in_progress" ? 45 : 10,
    }));

    const handleItemClick = (item: GanttItem) => {
        const task = tasks.find((t) => t.id === String(item.id));
        if (task) onOpenTask(task);
    };

    return (
        <UniversalGanttView
            items={items}
            moduleName={projectTitle || "Proyecto"}
            onItemClick={handleItemClick}
            onItemMove={(item, start, end) => onTaskDatesChange?.(String(item.id), start, end)}
            onItemResize={(item, end) => onTaskDatesChange?.(String(item.id), item.start_date, end)}
        />
    );
}

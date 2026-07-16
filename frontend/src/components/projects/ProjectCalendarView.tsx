"use client";

import React, { useState } from "react";
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

function toDateKey(date: Date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

interface Props {
    projectId: string;
    projectTitle?: string;
    tasks: ProjectTaskRecord[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onCreateTask: (data: { title: string; description: string; priority: string; status: string; due_date?: string }) => Promise<void> | void;
}

export default function ProjectCalendarView({ projectId, projectTitle, tasks, onOpenTask, onCreateTask }: Props) {
    const { updateTask } = useProjectTasks({ projectId });
    const [showCreateDrawer, setShowCreateDrawer] = useState(false);
    const [draftDueDate, setDraftDueDate] = useState<string | undefined>(undefined);

    const events: CalendarEvent[] = tasks.map((task) => ({
        id: task.id,
        title: task.title,
        date: (task.due_date || task.start_date || toDateKey(new Date())).slice(0, 10),
        color: task.status === "completed" ? "emerald" : task.priority === "urgent" ? "rose" : task.status === "review" ? "amber" : "blue",
    }));

    const handleDateClick = (date: Date) => {
        setDraftDueDate(toDateKey(date));
        setShowCreateDrawer(true);
    };

    const handleEventClick = (event: CalendarEvent) => {
        const task = tasks.find((t) => t.id === String(event.id));
        if (task) onOpenTask(task);
    };

    const handleEventMove = async (event: CalendarEvent, date: Date) => {
        const newDueDate = toDateKey(date);
        const task = tasks.find((t) => String(t.id) === String(event.id));
        if (!task) return;
        const currentDueDate = task.due_date ? task.due_date.slice(0, 10) : null;
        if (currentDueDate === newDueDate) return;
        // updateTask catches errors internally and rolls back optimistic state
        await updateTask(String(event.id), { due_date: newDueDate }, { optimistic: true });
    };

    const handleSubmit = async (data: { title: string; description: string; priority: string; status: string }) => {
        await onCreateTask({ ...data, due_date: draftDueDate });
        setShowCreateDrawer(false);
        setDraftDueDate(undefined);
    };

    return (
        <>
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
        </>
    );
}

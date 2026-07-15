"use client";

import React, { useState } from "react";
import UniversalCalendarView from "@/components/ui/UniversalCalendarView";
import TaskCreationDrawer from "@/components/projects/TaskCreationDrawer";
import type { ProjectTaskRecord } from "@/types/projects";

type CalendarEvent = {
    id: string | number;
    title: string;
    date: string;
    color?: "blue" | "emerald" | "amber" | "rose" | "sky";
};

interface Props {
    projectId: string;
    projectTitle?: string;
    tasks: ProjectTaskRecord[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onCreateTask: (data: { title: string; description: string; priority: string; status: string; due_date?: string }) => Promise<void> | void;
}

export default function ProjectCalendarView({ projectTitle, tasks, onOpenTask, onCreateTask }: Props) {
    const [showCreateDrawer, setShowCreateDrawer] = useState(false);
    const [draftDueDate, setDraftDueDate] = useState<string | undefined>(undefined);

    const events: CalendarEvent[] = tasks.map((task) => ({
        id: task.id,
        title: task.title,
        date: (task.due_date || task.start_date || new Date().toISOString()).slice(0, 10),
        color: task.status === "completed" ? "emerald" : task.priority === "urgent" ? "rose" : task.status === "review" ? "amber" : "blue",
    }));

    const handleDateClick = (date: Date) => {
        setDraftDueDate(date.toISOString().split("T")[0]);
        setShowCreateDrawer(true);
    };

    const handleEventClick = (event: CalendarEvent) => {
        const task = tasks.find((t) => t.id === String(event.id));
        if (task) onOpenTask(task);
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

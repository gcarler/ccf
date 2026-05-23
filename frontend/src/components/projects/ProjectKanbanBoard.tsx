"use client";

import React, { useState } from 'react';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent,
    DragOverlay,
    DragStartEvent
} from '@dnd-kit/core';
import {
    SortableContext,
    horizontalListSortingStrategy
} from '@dnd-kit/sortable';
import { KanbanColumn } from './KanbanColumn';
import { SortableTaskCard } from './SortableTaskCard';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';

export interface PhaseDef {
    slug: string;
    name: string;
    color: string;
    order_index: number;
}

interface Props {
    project: ProjectRecord;
    tasks: ProjectTaskRecord[];
    phases: PhaseDef[];
    onTasksChange: (tasks: ProjectTaskRecord[]) => void;
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: (status: string) => void;
}

export function ProjectKanbanBoard({ project, tasks, phases, onTasksChange, onOpenTask, onAddTask }: Props) {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [activeTask, setActiveTask] = useState<ProjectTaskRecord | null>(null);

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
        useSensor(KeyboardSensor)
    );

    const handleDragStart = (event: DragStartEvent) => {
        const task = tasks.find(t => t.id === parseInt(event.active.id as string, 10));
        setActiveTask(task ?? null);
    };

    const handleDragEnd = async (event: DragEndEvent) => {
        const { active, over } = event;
        setActiveTask(null);
        if (!over) return;

        const taskId = parseInt(active.id as string, 10);
        const overId = over.id as string;

        const isOverColumn = phases.some(s => s.slug === overId);
        let newStatus = overId;
        if (!isOverColumn) {
            const overTask = tasks.find(t => t.id === parseInt(overId, 10));
            if (overTask) newStatus = overTask.status || phases[0]?.slug || 'todo';
            else return;
        }

        const taskToMove = tasks.find(t => t.id === taskId);
        if (!taskToMove || (taskToMove.status || 'todo') === newStatus) return;

        const updatedTasks = tasks.map(t =>
            t.id === taskId ? { ...t, status: newStatus } : t
        );
        onTasksChange(updatedTasks);

        try {
            await apiFetch(`/projects/tasks/${taskId}`, {
                method: 'PATCH',
                token,
                body: { status: newStatus }
            });
            addToast('Tarea movida correctamente', 'success');
        } catch {
            onTasksChange(tasks);
            addToast('Error al mover la tarea', 'error');
        }
    };

    const handleTaskCreated = (newTask: ProjectTaskRecord) => {
        onTasksChange([newTask, ...tasks]);
        addToast('Tarea creada', 'success');
    };

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
        >
            <div className="flex h-full overflow-x-auto gap-5 p-6 pb-8 scrollbar-thin bg-slate-50/50 dark:bg-[#1a1b1d]">
                <SortableContext
                    items={phases.map(s => s.slug)}
                    strategy={horizontalListSortingStrategy}
                >
                    {phases.map(phase => (
                        <KanbanColumn
                            key={phase.slug}
                            id={phase.slug}
                            name={phase.name}
                            color={phase.color}
                            tasks={tasks.filter(t => (t.status || 'todo') === phase.slug)}
                            onOpenTask={onOpenTask}
                            onAddTask={() => onAddTask(phase.slug)}
                            projectId={project.id}
                            onTaskCreated={handleTaskCreated}
                        />
                    ))}
                </SortableContext>
            </div>

            {/* Drag overlay — ghost card */}
            <DragOverlay dropAnimation={null}>
                {activeTask && (
                    <div className="rotate-1 opacity-90 cursor-grabbing">
                        <SortableTaskCard task={activeTask} onOpen={() => {}} />
                    </div>
                )}
            </DragOverlay>
        </DndContext>
    );
}

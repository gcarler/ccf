"use client";

import React, { useState } from 'react';
import { 
    DndContext, 
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent
} from '@dnd-kit/core';
import { 
    SortableContext,
    horizontalListSortingStrategy
} from '@dnd-kit/sortable';
import { KanbanColumn } from './KanbanColumn';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';

interface Props {
    project: ProjectRecord;
    tasks: ProjectTaskRecord[];
    onTasksChange: (tasks: ProjectTaskRecord[]) => void;
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: (status: string) => void;
}

const KANBAN_STAGES = [
    { id: 'todo', name: 'Por Hacer', color: '#94a3b8' },
    { id: 'in_progress', name: 'En Curso', color: '#3b82f6' },
    { id: 'review', name: 'Revisión', color: '#f59e0b' },
    { id: 'done', name: 'Completado', color: '#10b981' }
];

export function ProjectKanbanBoard({ project, tasks, onTasksChange, onOpenTask, onAddTask }: Props) {
    const { token } = useAuth();
    const { addToast } = useToast();

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
        useSensor(KeyboardSensor)
    );

    const handleDragEnd = async (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over) return;

        const taskId = parseInt(active.id as string, 10);
        const overId = over.id as string;

        // Is it dropped over a column?
        const isOverColumn = KANBAN_STAGES.some(s => s.id === overId);
        
        let newStatus = overId;
        if (!isOverColumn) {
            // It might be dropped over another task, find its status
            const overTask = tasks.find(t => t.id === parseInt(overId, 10));
            if (overTask) newStatus = overTask.status || 'todo';
            else return; // Default fallback
        }

        const taskToMove = tasks.find(t => t.id === taskId);
        if (!taskToMove || taskToMove.status === newStatus) return;

        // Optimistic update
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
            addToast('Tarea actualizada correctamente', 'success');
        } catch (error) {
            // Revert on error
            onTasksChange(tasks);
            addToast('Error al actualizar la tarea', 'error');
            console.error(error);
        }
    };

    return (
        <DndContext 
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
        >
            <div className="flex h-full overflow-x-auto gap-6 pb-8 scrollbar-thin">
                <SortableContext 
                    items={KANBAN_STAGES.map(s => s.id)}
                    strategy={horizontalListSortingStrategy}
                >
                    {KANBAN_STAGES.map(stage => (
                        <KanbanColumn
                            key={stage.id}
                            id={stage.id}
                            name={stage.name}
                            color={stage.color}
                            tasks={tasks.filter(t => (t.status || 'todo') === stage.id)}
                            onOpenTask={onOpenTask}
                            onAddTask={() => onAddTask(stage.id)}
                        />
                    ))}
                </SortableContext>
            </div>
        </DndContext>
    );
}

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

interface Props {
    project: ProjectRecord;
    tasks: ProjectTaskRecord[];
    onTasksChange: (tasks: ProjectTaskRecord[]) => void;
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: (status: string) => void;
}

const KANBAN_STAGES = [
    { id: 'todo',        name: 'Por Hacer',   color: '#94a3b8' },
    { id: 'in_progress', name: 'En Curso',    color: '#3b82f6' },
    { id: 'review',      name: 'Revisión',    color: '#f59e0b' },
    { id: 'done',        name: 'Completado',  color: '#10b981' },
];

// Map the status values that come from API to Kanban stages
function normalizeStatus(status: string): string {
    const map: Record<string, string> = {
        pending: 'todo',
        blocked: 'todo',
    };
    return map[status] ?? status ?? 'todo';
}

export function ProjectKanbanBoard({ project, tasks, onTasksChange, onOpenTask, onAddTask }: Props) {
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

        const isOverColumn = KANBAN_STAGES.some(s => s.id === overId);
        let newStatus = overId;
        if (!isOverColumn) {
            const overTask = tasks.find(t => t.id === parseInt(overId, 10));
            if (overTask) newStatus = normalizeStatus(overTask.status || 'todo');
            else return;
        }

        const taskToMove = tasks.find(t => t.id === taskId);
        if (!taskToMove || normalizeStatus(taskToMove.status || 'todo') === newStatus) return;

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
                    items={KANBAN_STAGES.map(s => s.id)}
                    strategy={horizontalListSortingStrategy}
                >
                    {KANBAN_STAGES.map(stage => (
                        <KanbanColumn
                            key={stage.id}
                            id={stage.id}
                            name={stage.name}
                            color={stage.color}
                            tasks={tasks.filter(t => normalizeStatus(t.status || 'todo') === stage.id)}
                            onOpenTask={onOpenTask}
                            onAddTask={() => onAddTask(stage.id)}
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

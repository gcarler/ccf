"use client";

import { useState } from 'react';
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
import { useProjectUpdate, type PhaseDef } from '@/context/ProjectUpdateContext';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';

interface Props {
    project: ProjectRecord;
    tasks: ProjectTaskRecord[];
    phases: PhaseDef[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: () => void;
}

export function ProjectKanbanBoard({ project, tasks, phases, onOpenTask, onAddTask }: Props) {
    const { updateTask, deleteTask, createTask } = useProjectUpdate();
    const [activeTask, setActiveTask] = useState<ProjectTaskRecord | null>(null);

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
        useSensor(KeyboardSensor)
    );

    const handleDragStart = (event: DragStartEvent) => {
        const task = tasks.find(t => t.id === String(event.active.id));
        setActiveTask(task ?? null);
    };

    const handleDragEnd = async (event: DragEndEvent) => {
        const { active, over } = event;
        setActiveTask(null);
        if (!over) return;

        const taskId = String(active.id);
        const overId = over.id as string;

        const isOverColumn = phases.some(s => s.slug === overId);
        let newStatus = overId;
        if (!isOverColumn) {
            const overTask = tasks.find(t => t.id === overId);
            if (overTask) newStatus = (overTask.status || phases[0]?.slug || 'todo').toLowerCase();
            else return;
        }

        const taskToMove = tasks.find(t => t.id === taskId);
        if (!taskToMove || (taskToMove.status || 'todo').toLowerCase() === newStatus) return;

        // Enrutamos la mutación por el contexto (useProjectUpdate), que ya hace
        // update optimista + PATCH + loadProject() recarga + rollback + toast.
        // El feedback visual (tarjeta en la columna destino) es confirmación
        // suficiente; no abrimos toast de éxito aquí (asimetría deliberada).
        await updateTask(taskId, { status: newStatus });
    };

    if (phases.length === 0) {
        return (
            <div className="h-full flex flex-col items-center justify-center gap-2 p-6 text-center">
                <p className="text-sm font-semibold text-[hsl(var(--text-secondary))]">
                    No hay columnas para mostrar
                </p>
                <p className="text-xs text-[hsl(var(--text-secondary))]">
                    Este proyecto aún no tiene fases. Crea fases desde el gestor de fases para ver el tablero.
                </p>
            </div>
        );
    }

    return (
        <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
        >
            <div className="flex h-full overflow-x-auto gap-3 p-3 pb-4 scrollbar-thin bg-[hsl(var(--surface-1))]/50 dark:bg-[hsl(var(--admin-bg-secondary))]">
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
                            tasks={tasks.filter(t => (t.status || 'todo').toLowerCase() === phase.slug.toLowerCase())}
                            onOpenTask={onOpenTask}
                            onAddTask={onAddTask}
                            projectId={project.id}
                            onCreateTask={createTask}
                            onTaskUpdate={updateTask}
                            onTaskDelete={deleteTask}
                        />
                    ))}
                </SortableContext>
            </div>

            {/* Drag overlay — lightweight ghost.

            Render a static placeholder instead of ``SortableTaskCard``. Reusing a
            sortable card inside ``DragOverlay`` would conflict with ``useSortable``
            semantics (the card would register a second draggable context while it's
            already being dragged, causing erratic pointer events).
            */}
            <DragOverlay dropAnimation={null}>
                {activeTask && (
                    <div
                        role="presentation"
                        className="rotate-1 opacity-90 cursor-grabbing bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))] rounded-md shadow-2xl border border-[hsl(var(--info)/100%)] p-3 w-[260px]"
                    >
                        <div className="h-[3px] w-full mb-2 bg-[hsl(var(--primary))] rounded-full" />
                        <p className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] line-clamp-2">
                            {activeTask.title || 'Tarea'}
                        </p>
                        <div className="flex items-center gap-3 mt-2 text-[10px] text-[hsl(var(--text-secondary))]">
                            {activeTask.priority && (
                                <span className="font-bold uppercase tracking-wide">{activeTask.priority}</span>
                            )}
                            {activeTask.due_date && (
                                <span>{activeTask.due_date.slice(0, 10)}</span>
                            )}
                        </div>
                    </div>
                )}
            </DragOverlay>
        </DndContext>
    );
}

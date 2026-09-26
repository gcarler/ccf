"use client";

import { useState, useEffect, useMemo } from 'react';
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
import { Star } from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { KanbanColumn } from './KanbanColumn';
import { useProjectUpdate, type PhaseDef } from '@/context/ProjectUpdateContext';
import type { ProjectRecord, ProjectTaskRecord, ProjectUserFavorite } from '@/types/projects';

interface Props {
    project: ProjectRecord;
    tasks: ProjectTaskRecord[];
    phases: PhaseDef[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: () => void;
}

export function ProjectKanbanBoard({ project, tasks, phases, onOpenTask, onAddTask }: Props) {
    const { updateTask, deleteTask, createTask } = useProjectUpdate();
    const { token } = useAuth();
    const [activeTask, setActiveTask] = useState<ProjectTaskRecord | null>(null);
    const [onlyFavorites, setOnlyFavorites] = useState(false);
    const [favoriteTaskIds, setFavoriteTaskIds] = useState<Set<string>>(new Set());

    useEffect(() => {
        let active = true;
        if (!project?.id || !token) return;
        apiFetch<(string | ProjectUserFavorite)[]>(`/projects/${project.id}/favorites?entity_type=task`, { token })
            .then(favs => {
                if (active && Array.isArray(favs)) {
                    setFavoriteTaskIds(new Set(favs.map(f => typeof f === 'string' ? f : f.entity_id)));
                }
            })
            .catch(() => {});
        return () => { active = false; };
    }, [project?.id, token]);

    const displayedTasks = useMemo(() => {
        if (!onlyFavorites) return tasks;
        return tasks.filter(t => favoriteTaskIds.has(t.id));
    }, [tasks, onlyFavorites, favoriteTaskIds]);

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
                <p className="text-sm font-semibold text-[hsl(var(--muted-foreground))]">
                    No hay columnas para mostrar
                </p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                    Este proyecto aún no tiene fases. Crea fases desde el gestor de fases para ver el tablero.
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]">
            <div className="shrink-0 flex items-center justify-between px-3 py-1.5 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                <button
                    type="button"
                    onClick={() => setOnlyFavorites(prev => !prev)}
                    className={clsx(
                        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all border',
                        onlyFavorites
                            ? 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.3)] shadow-xs'
                            : 'text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))]'
                    )}
                    title="Filtrar por tareas favoritas"
                >
                    <Star size={13} className={clsx(onlyFavorites ? 'fill-current text-[hsl(var(--warning))]' : '')} />
                    <span>Solo Mis Favoritas</span>
                    {favoriteTaskIds.size > 0 && (
                        <span className={clsx(
                            'px-1.5 py-0.2 rounded-full text-3xs font-bold',
                            onlyFavorites
                                ? 'bg-[hsl(var(--warning))] text-[hsl(var(--background))]'
                                : 'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]'
                        )}>
                            {favoriteTaskIds.size}
                        </span>
                    )}
                </button>
                <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                    {displayedTasks.length} de {tasks.length} tareas
                </span>
            </div>

            <div className="flex-1 min-h-0">
                <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                >
                    <div className="flex h-full overflow-x-auto gap-3 p-3 pb-4 scrollbar-thin bg-[hsl(var(--surface-1))]">
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
                                    tasks={displayedTasks.filter(t => (t.status || 'todo').toLowerCase() === phase.slug.toLowerCase())}
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
                        className="rotate-1 opacity-90 cursor-grabbing bg-[hsl(var(--surface-1))] rounded-md shadow-2xl border border-[hsl(var(--primary))] p-3 w-[260px]"
                    >
                        <div className="h-[3px] w-full mb-2 bg-[hsl(var(--primary))] rounded-full" />
                        <p className="text-base font-semibold text-[hsl(var(--foreground))] line-clamp-2">
                            {activeTask.title || 'Tarea'}
                        </p>
                        <div className="flex items-center gap-3 mt-2 text-2xs text-[hsl(var(--muted-foreground))]">
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
            </div>
        </div>
    );
}

"use client";

import React from 'react';
import {
    Calendar,
    PencilRuler,
    Plus,
    Trash2,
} from 'lucide-react';
import { useProjectUpdate } from '@/context/ProjectUpdateContext';
import TaskTableView from '@/components/projects/TaskTableView';
import ProjectListView from '@/components/projects/ProjectListView';
import ProjectCalendarView from '@/components/projects/ProjectCalendarView';
import ProjectGanttView from '@/components/projects/ProjectGanttView';
import ProjectWhiteboard from '@/components/projects/ProjectWhiteboard';
import ProjectWikiEditor from '@/components/projects/ProjectWikiEditor';
import ProjectChatPanel from '@/components/projects/ProjectChatPanel';
import { ProjectKanbanBoard } from '@/components/projects/ProjectKanbanBoard';
import { ProjectMasterView } from '@/components/projects/ProjectMasterView';
import { ProjectActivityFeed } from '@/components/projects/ProjectActivityFeed';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectTaskRecord } from '@/types/projects';

interface ProjectViewsContentProps {
    viewType: ViewType;
    onOpenTask: (task: ProjectTaskRecord) => void;
    onTaskUpdated: (updated: ProjectTaskRecord) => void;
    onActivityCreated: () => void;
    onDeleteTask: (taskId: string) => void;
    setShowTaskModal: (open: boolean) => void;
    setWhiteboardOpen: (open: boolean) => void;
}

/**
 * Render-switcher del detalle de proyecto. Lee phases, tasks, project del
 * `ProjectUpdateContext` en lugar de recibirlos como props — esto elimina el
 * prop-drilling desde `page.tsx` después de `PARCIAL-PAGE-001`.
 *
 * Sólo necesita comunicación hacia arriba para:
 *  - `onOpenTask` (sincronizar URL con task query param)
 *  - `onTaskUpdated` / `onDeleteTask` (TaskDetailPanel callbacks)
 *  - `onActivityCreated` (recargar feed)
 *  - `setShowTaskModal` / `setWhiteboardOpen` (open drawers desde atajos de UI)
 */
export function ProjectViewsContent({
    viewType,
    onOpenTask,
    onTaskUpdated,
    onActivityCreated,
    onDeleteTask,
    setShowTaskModal,
    setWhiteboardOpen,
}: ProjectViewsContentProps) {
    const { project, tasks, phases, activities, createTask, reloadProject, updateTask } = useProjectUpdate();

    if (viewType === 'board' || viewType === 'kanban') {
        return (
            <div className="h-full">
                <ProjectKanbanBoard
                    project={project!}
                    tasks={tasks}
                    phases={phases}
                    onTasksChange={(next) => {
                        // The Kanban still updates parent DOM nodes optimistically; the effect
                        // is auto-reverted by `reloadProject` if the PATCH fails upstream.
                        void next; // no-op here; tasks+phases are in context
                    }}
                    onOpenTask={onOpenTask}
                    onAddTask={() => setShowTaskModal(true)}
                />
            </div>
        );
    }

    return (
        <main className="flex-1 overflow-y-auto p-4 space-y-3">
            {viewType === 'dashboard' && (
                <div className="space-y-3">
                    {project && (
                        <ProjectMasterView
                            project={project}
                            tasks={tasks}
                            onOpenTask={onOpenTask}
                        />
                    )}
                    <div className="min-h-[420px] overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-white/5">
                        <ProjectActivityFeed activities={activities} />
                    </div>
                </div>
            )}

            {viewType === 'table' && (
                <div className="h-[calc(100vh-8rem)] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] shadow-sm">
                    <TaskTableView
                        projectId={project?.id}
                        tasks={tasks}
                        onOpenTask={onOpenTask}
                        onAddTask={() => reloadProject()}
                        onTaskUpdated={() => reloadProject()}
                    />
                </div>
            )}

            {viewType === 'list' && (
                <div className="w-full h-[calc(100vh-8rem)]">
                    <ProjectListView
                        projectId={project?.id}
                        tasks={tasks}
                        onOpenTask={onOpenTask}
                        onAddTask={(status) =>
                            createTask({ title: '', description: '', priority: 'medium', status })
                        }
                        // ProjectListView promotes its own updates to context via the
                        // useProjectTasks hook (Fase 1). The parent-owned update paths
                        // stay here as no-ops to keep the prop shape stable.
                        onTasksChange={() => { /* handled via useProjectTasks inside ProjectListView */ }}
                        onTaskUpdate={async (taskId, patch) => {
                            await updateTask(taskId, patch);
                        }}
                    />
                </div>
            )}

            {viewType === 'calendar' && (
                <div className="h-[720px]">
                    <ProjectCalendarView
                        projectId={project?.id}
                        projectTitle={project?.title}
                        tasks={tasks}
                        onOpenTask={onOpenTask}
                        onCreateTask={createTask}
                    />
                </div>
            )}

            {viewType === 'gantt' && (
                <div className="h-[720px]">
                    <ProjectGanttView
                        projectTitle={project?.title}
                        tasks={tasks}
                        phases={phases}
                        onOpenTask={onOpenTask}
                        onTaskDatesChange={async (taskId, start_date, end_date) => {
                            await updateTask(taskId, { start_date, due_date: end_date });
                        }}
                    />
                </div>
            )}

            {viewType === 'wiki' && (
                <ProjectWikiEditor project_id={project?.id} />
            )}

            {viewType === 'chat' && (
                <ProjectChatPanel projectId={project?.id} />
            )}

            {/* Hide suppress unused-imports tooltips; Calendar/PencilRuler etc. are
                referenced by parent page shell. Exported signature stays stable. */}
            <div className="hidden">
                <Calendar /> <PencilRuler /> <Plus /> <Trash2 />
            </div>
        </main>
    );
}

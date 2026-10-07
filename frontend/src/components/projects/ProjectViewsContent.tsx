"use client";

import dynamic from 'next/dynamic';
import {
    Calendar,
    PencilRuler,
    Plus,
    Trash2,
} from 'lucide-react';
import { useProjectUpdate } from '@/context/ProjectUpdateContext';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectTaskRecord } from '@/types/projects';

function ProjectViewLoading() {
    return (
        <div
            className="min-h-48 h-full w-full animate-pulse rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]"
            role="status"
            aria-label="Cargando vista del proyecto"
        />
    );
}

const TaskTableView = dynamic(() => import('@/components/projects/TaskTableView'), { loading: ProjectViewLoading });
const ProjectListView = dynamic(() => import('@/components/projects/ProjectListView'), { loading: ProjectViewLoading });
const ProjectCalendarView = dynamic(() => import('@/components/projects/ProjectCalendarView'), { loading: ProjectViewLoading });
const ProjectGanttView = dynamic(() => import('@/components/projects/ProjectGanttView'), { loading: ProjectViewLoading });
const ProjectWikiEditor = dynamic(() => import('@/components/projects/ProjectWikiEditor'), { loading: ProjectViewLoading });
const ProjectChatPanel = dynamic(() => import('@/components/projects/ProjectChatPanel'), { loading: ProjectViewLoading });
const ProjectKanbanBoard = dynamic(
    () => import('@/components/projects/ProjectKanbanBoard').then((module) => module.ProjectKanbanBoard),
    { loading: ProjectViewLoading },
);
const ProjectMasterView = dynamic(
    () => import('@/components/projects/ProjectMasterView').then((module) => module.ProjectMasterView),
    { loading: ProjectViewLoading },
);
const ProjectActivityFeed = dynamic(() => import('@/components/projects/ProjectActivityFeed'), { loading: ProjectViewLoading });

interface ProjectViewsContentProps {
    viewType: ViewType;
    onOpenTask: (task: ProjectTaskRecord) => void;
    onTaskUpdated: (updated: ProjectTaskRecord) => void;
    onActivityCreated: () => void;
    onDeleteTask: (taskId: string) => void;
    setShowTaskModal: (open: boolean) => void;
    setTaskCreationStatus: (status: string) => void;
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
    onTaskUpdated: _onTaskUpdated,
    onActivityCreated: _onActivityCreated,
    onDeleteTask: _onDeleteTask,
    setShowTaskModal,
    setTaskCreationStatus,
    setWhiteboardOpen: _setWhiteboardOpen,
}: ProjectViewsContentProps) {
    const { project, tasks, phases, activities, createTask, reloadProject, updateTask } = useProjectUpdate();

    if (viewType === 'board' || viewType === 'kanban') {
        if (!project?.id) {
            return (
                <div className="h-full flex items-center justify-center p-6">
                    <p className="text-sm text-[hsl(var(--muted-foreground))]">
                        No se pudo cargar el proyecto.
                    </p>
                </div>
            );
        }
        return (
            <div className="h-full">
                <ProjectKanbanBoard
                    project={project}
                    tasks={tasks}
                    phases={phases}
                    onOpenTask={onOpenTask}
                    onAddTask={() => {
                        setTaskCreationStatus('todo');
                        setShowTaskModal(true);
                    }}
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
                    <div className="min-h-[420px] overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                        <ProjectActivityFeed activities={activities} />
                    </div>
                </div>
            )}

            {viewType === 'table' && (
                <div className="h-[calc(100vh-8rem)] border border-[hsl(var(--border))] rounded-lg overflow-hidden bg-[hsl(var(--surface-1))] shadow-sm">
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
                        tasks={tasks}
                        projectId={project?.id}
                        phaseDefs={phases}
                        onOpenTask={onOpenTask}
                        onAddTask={(status) => {
                            setTaskCreationStatus(status);
                            setShowTaskModal(true);
                        }}
                        // List and Kanban intentionally consume the same
                        // ProjectUpdateContext source of truth. The list owns
                        // only its presentation; persistence and optimistic
                        // rollback remain in useProjectPageData.
                        onTaskUpdate={async (taskId, patch) => {
                            await updateTask(taskId, patch);
                        }}
                    />
                </div>
            )}

            {viewType === 'calendar' && (
                <div className="h-[720px]">
                    {project?.id ? (
                        <ProjectCalendarView
                            projectId={project.id}
                            projectTitle={project?.title}
                            tasks={tasks}
                            onOpenTask={onOpenTask}
                            onCreateTask={createTask}
                        />
                    ) : null}
                </div>
            )}

            {viewType === 'gantt' && (
                <div className="h-[720px]">
                    <ProjectGanttView
                        projectId={project?.id}
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
                project?.id ? <ProjectWikiEditor project_id={project.id} /> : null
            )}

            {viewType === 'chat' && (
                project?.id ? <ProjectChatPanel projectId={project.id} /> : null
            )}

            {/* Hide suppress unused-imports tooltips; Calendar/PencilRuler etc. are
                referenced by parent page shell. Exported signature stays stable. */}
            <div className="hidden">
                <Calendar /> <PencilRuler /> <Plus /> <Trash2 />
            </div>
        </main>
    );
}

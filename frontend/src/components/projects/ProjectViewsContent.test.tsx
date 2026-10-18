import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProjectViewsContent } from './ProjectViewsContent';
import type { ProjectRecord, ProjectTaskRecord } from '@/types/projects';

const mockUseProjectUpdate = vi.fn();

vi.mock('@/context/ProjectUpdateContext', () => ({
  useProjectUpdate: () => mockUseProjectUpdate(),
}));

vi.mock('next/dynamic', () => ({
  default: (loader: () => Promise<unknown>) => {
    const fnStr = loader.toString();
    if (fnStr.includes('TaskTableView')) {
      return function MockTaskTableView({
        tasks,
        onOpenTask,
      }: {
        tasks: ProjectTaskRecord[];
        onOpenTask: (t: ProjectTaskRecord) => void;
      }) {
        return (
          <div data-testid="mock-task-table-view">
            <span>Tabla WBS: {tasks.length}</span>
            {tasks[0] && (
              <button type="button" onClick={() => onOpenTask(tasks[0])}>
                Abrir {tasks[0].title}
              </button>
            )}
          </div>
        );
      };
    }
    if (fnStr.includes('ProjectListView')) {
      return function MockProjectListView({ tasks }: { tasks: ProjectTaskRecord[] }) {
        return <div data-testid="mock-project-list-view">Lista: {tasks.length}</div>;
      };
    }
    if (fnStr.includes('ProjectKanbanBoard')) {
      return function MockProjectKanbanBoard({ project }: { project: ProjectRecord }) {
        return <div data-testid="mock-project-kanban-board">Kanban: {project.id}</div>;
      };
    }
    if (fnStr.includes('ProjectMasterView')) {
      return function MockProjectMasterView({ project }: { project: ProjectRecord }) {
        return <div data-testid="mock-project-master-view">Master: {project.title}</div>;
      };
    }
    if (fnStr.includes('ProjectActivityFeed')) {
      return function MockProjectActivityFeed({ activities }: { activities: unknown[] }) {
        return <div data-testid="mock-project-activity-feed">Actividades: {activities.length}</div>;
      };
    }
    return function MockFallbackComponent() {
      return <div data-testid="mock-dynamic-view" />;
    };
  },
}));

const sampleTasks: ProjectTaskRecord[] = [
  {
    id: 'task-1',
    project_id: 'proj-101',
    title: 'Definir alcance WBS',
    status: 'completed',
    priority: 'high',
    due_date: '2026-06-01',
  },
  {
    id: 'task-2',
    project_id: 'proj-101',
    title: 'Estimar ruta crítica',
    status: 'planning',
    priority: 'medium',
    due_date: '2026-06-10',
  },
];

describe('ProjectViewsContent', () => {
  beforeEach(() => {
    mockUseProjectUpdate.mockReset();
    mockUseProjectUpdate.mockReturnValue({
      project: { id: 'proj-101', title: 'Torre Faro', status: 'in_progress' },
      tasks: sampleTasks,
      phases: [
        { slug: 'planning', name: 'Planeación', color: 'hsl(var(--primary))' },
        { slug: 'completed', name: 'Completado', color: 'hsl(var(--success))' },
      ],
      activities: [{ id: 'act-1' }],
      createTask: vi.fn(),
      reloadProject: vi.fn(),
      updateTask: vi.fn(),
    });
  });

  it('renderiza la barra de contexto PMI con paquetes activos y porcentaje de progreso', () => {
    render(
      <ProjectViewsContent
        viewType="dashboard"
        onOpenTask={vi.fn()}
        onTaskUpdated={vi.fn()}
        onActivityCreated={vi.fn()}
        onDeleteTask={vi.fn()}
        setShowTaskModal={vi.fn()}
        setTaskCreationStatus={vi.fn()}
        setWhiteboardOpen={vi.fn()}
      />
    );

    const contextBar = screen.getByTestId('project-views-pmi-context-bar');
    expect(contextBar).toBeInTheDocument();
    expect(contextBar).toHaveTextContent('Paquetes Activos: 2');
    expect(contextBar).toHaveTextContent('Progreso de Paquetes: 50% (1/2)');
    expect(screen.getByTestId('mock-project-master-view')).toHaveTextContent('Master: Torre Faro');
    expect(screen.getByTestId('mock-project-activity-feed')).toHaveTextContent('Actividades: 1');
  });

  it('alterna entre las vistas table, list y board disparando callbacks de interacción', () => {
    const onOpenTask = vi.fn();
    const { rerender } = render(
      <ProjectViewsContent
        viewType="table"
        onOpenTask={onOpenTask}
        onTaskUpdated={vi.fn()}
        onActivityCreated={vi.fn()}
        onDeleteTask={vi.fn()}
        setShowTaskModal={vi.fn()}
        setTaskCreationStatus={vi.fn()}
        setWhiteboardOpen={vi.fn()}
      />
    );

    expect(screen.getByTestId('mock-task-table-view')).toHaveTextContent('Tabla WBS: 2');
    fireEvent.click(screen.getByRole('button', { name: 'Abrir Definir alcance WBS' }));
    expect(onOpenTask).toHaveBeenCalledWith(sampleTasks[0]);

    rerender(
      <ProjectViewsContent
        viewType="list"
        onOpenTask={onOpenTask}
        onTaskUpdated={vi.fn()}
        onActivityCreated={vi.fn()}
        onDeleteTask={vi.fn()}
        setShowTaskModal={vi.fn()}
        setTaskCreationStatus={vi.fn()}
        setWhiteboardOpen={vi.fn()}
      />
    );
    expect(screen.getByTestId('mock-project-list-view')).toHaveTextContent('Lista: 2');

    rerender(
      <ProjectViewsContent
        viewType="board"
        onOpenTask={onOpenTask}
        onTaskUpdated={vi.fn()}
        onActivityCreated={vi.fn()}
        onDeleteTask={vi.fn()}
        setShowTaskModal={vi.fn()}
        setTaskCreationStatus={vi.fn()}
        setWhiteboardOpen={vi.fn()}
      />
    );
    expect(screen.getByTestId('mock-project-kanban-board')).toHaveTextContent('Kanban: proj-101');
  });

  it('muestra mensaje de respaldo cuando viewType es board y project es null', () => {
    mockUseProjectUpdate.mockReturnValue({
      project: null,
      tasks: [],
      phases: [],
      activities: [],
      createTask: vi.fn(),
      reloadProject: vi.fn(),
      updateTask: vi.fn(),
    });

    render(
      <ProjectViewsContent
        viewType="board"
        onOpenTask={vi.fn()}
        onTaskUpdated={vi.fn()}
        onActivityCreated={vi.fn()}
        onDeleteTask={vi.fn()}
        setShowTaskModal={vi.fn()}
        setTaskCreationStatus={vi.fn()}
        setWhiteboardOpen={vi.fn()}
      />
    );

    expect(screen.getByText('No se pudo cargar el proyecto.')).toBeInTheDocument();
  });
});

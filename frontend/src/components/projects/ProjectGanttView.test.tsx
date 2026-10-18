import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProjectGanttView, { parseDependencyType } from './ProjectGanttView';
import type { ProjectTaskRecord } from '@/types/projects';

const { mockApiFetch, stableAuth, stableToast, stableProjectCtx } = vi.hoisted(() => ({
  mockApiFetch: vi.fn(),
  stableAuth: { token: 'test-jwt-token', user: { id: 'user-1', email: 'pm@ccf.org' } },
  stableToast: { addToast: vi.fn() },
  stableProjectCtx: {
    project: { id: 'proj-1', title: 'Torre Faro', milestones: [] },
    tasks: [],
    phases: [],
  },
}));

vi.mock('@/lib/http', () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => stableAuth,
}));

vi.mock('@/context/ToastContext', () => ({
  useToast: () => stableToast,
}));

vi.mock('@/context/ProjectUpdateContext', () => ({
  useProjectUpdate: () => stableProjectCtx,
}));

vi.mock('@/components/ui/RightPanel', () => ({
  RightPanel: ({
    open,
    title,
    children,
  }: {
    open: boolean;
    title: string;
    children: React.ReactNode;
  }) =>
    open ? (
      <aside aria-label={title} data-testid="mock-right-panel">
        {children}
      </aside>
    ) : null,
}));

vi.mock('@/components/projects/ProjectBaselineDrawer', () => ({
  ProjectBaselineDrawer: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div data-testid="mock-baseline-drawer">Drawer Línea Base</div> : null,
}));

vi.mock('@/components/ConfirmActionDrawer', () => ({
  default: () => null,
}));

const samplePhases = [
  {
    name: 'Ejecución de Obra',
    slug: 'in_progress',
    color: 'hsl(var(--primary))',
  },
  {
    name: 'Planificación Técnica',
    slug: 'todo',
    color: 'hsl(var(--warning))',
  },
];

const sampleTasks: ProjectTaskRecord[] = [
  {
    id: 'task-1',
    project_id: 'proj-1',
    title: 'Cimentación Estructural',
    status: 'in_progress',
    priority: 'urgent',
    start_date: '2026-06-01',
    due_date: '2026-06-04',
  },
  {
    id: 'task-2',
    project_id: 'proj-1',
    title: 'Montaje de Columnas',
    status: 'todo',
    priority: 'high',
    start_date: '2026-06-05',
    due_date: '2026-06-08',
  },
];

describe('parseDependencyType', () => {
  it.each(['FS', 'SS', 'FF', 'SF'] as const)(
    'acepta el tipo de dependencia válido %s',
    (value) => {
      expect(parseDependencyType(value)).toBe(value);
    }
  );

  it.each(['', 'fs', 'INVALID'])(
    'rechaza el tipo de dependencia no soportado %s',
    (value) => {
      expect(parseDependencyType(value)).toBeNull();
    }
  );
});

describe('ProjectGanttView', () => {
  beforeEach(() => {
    mockApiFetch.mockReset();
    stableToast.addToast.mockReset();
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('/dependencies')) {
        return [
          {
            id: 'dep-1',
            project_id: 'proj-1',
            predecessor_id: 'task-1',
            successor_id: 'task-2',
            dependency_type: 'FS',
            lag_days: 0,
          },
        ];
      }
      if (url.includes('/critical-path')) {
        return {
          project_id: 'proj-1',
          total_duration_days: 5,
          critical_tasks_count: 2,
          critical_path_task_ids: ['task-1', 'task-2'],
          tasks: [
            {
              task_id: 'task-1',
              title: 'Cimentación Estructural',
              status: 'in_progress',
              duration_days: 3,
              early_start: 0,
              early_finish: 3,
              late_start: 0,
              late_finish: 3,
              slack_days: 0,
              is_critical: true,
            },
            {
              task_id: 'task-2',
              title: 'Montaje de Columnas',
              status: 'todo',
              duration_days: 2,
              early_start: 3,
              early_finish: 5,
              late_start: 3,
              late_finish: 5,
              slack_days: 0,
              is_critical: true,
            },
          ],
          has_cycles: false,
        };
      }
      if (url.includes('/baseline')) {
        return {
          id: 'base-1',
          project_id: 'proj-1',
          name: 'Línea Base Inicial',
          comparisons: [],
        };
      }
      return {};
    });
  });

  it('renderiza paquetes de trabajo, agrupación WBS Fases, controles de zoom (Día, Semana, Mes) y Ruta Crítica PMI', async () => {
    render(
      <ProjectGanttView
        tasks={sampleTasks}
        phases={samplePhases}
        projectId="proj-1"
        onOpenTask={vi.fn()}
      />
    );

    expect(screen.getByText('Estructura de Tareas (WBS)')).toBeInTheDocument();
    expect(screen.getByText('Ejecución de Obra')).toBeInTheDocument();
    expect(screen.getByText('Planificación Técnica')).toBeInTheDocument();
    expect(screen.getAllByText('Cimentación Estructural').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Montaje de Columnas').length).toBeGreaterThanOrEqual(1);

    // Zoom scale controls
    const dayBtn = screen.getByRole('button', { name: 'Día' });
    const weekBtn = screen.getByRole('button', { name: 'Semana' });
    const monthBtn = screen.getByRole('button', { name: 'Mes' });
    expect(dayBtn).toBeInTheDocument();
    expect(weekBtn).toBeInTheDocument();
    expect(monthBtn).toBeInTheDocument();

    fireEvent.click(weekBtn);
    fireEvent.click(monthBtn);
    fireEvent.click(dayBtn);

    // Toggle WBS Fases grouping
    const wbsGroupBtn = screen.getByRole('button', { name: /WBS Fases/i });
    expect(wbsGroupBtn).toBeInTheDocument();
    fireEvent.click(wbsGroupBtn);
    expect(screen.queryByText('Ejecución de Obra')).not.toBeInTheDocument();
    fireEvent.click(wbsGroupBtn);
    expect(screen.getByText('Ejecución de Obra')).toBeInTheDocument();

    // Critical path toggle & PMI CPM analysis panel
    const cpmBtn = screen.getByRole('button', { name: /Alternar ruta crítica/i });
    expect(cpmBtn).toHaveTextContent(/Ruta Crítica/i);
    fireEvent.click(cpmBtn);

    await waitFor(() => {
      expect(
        screen.getByRole('region', { name: /Inspector de Red Lógica CPM/i })
      ).toBeInTheDocument();
    });
    expect(screen.getByText('5 días')).toBeInTheDocument();
  });

  it('dispara onOpenTask al seleccionar una tarea desde la lista WBS o la barra del cronograma', async () => {
    const onOpenTask = vi.fn();
    render(
      <ProjectGanttView
        tasks={sampleTasks}
        phases={samplePhases}
        projectId="proj-1"
        onOpenTask={onOpenTask}
      />
    );

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalled();
    });

    const wbsTaskRow = screen.getByRole('button', {
      name: 'Abrir detalle de tarea Cimentación Estructural desde la lista del Gantt',
    });
    fireEvent.click(wbsTaskRow);
    expect(onOpenTask).toHaveBeenCalledWith(sampleTasks[0]);

    const ganttBarButton = screen.getByRole('button', {
      name: 'Abrir detalle de tarea Montaje de Columnas desde el cronograma',
    });
    fireEvent.click(ganttBarButton);
    expect(onOpenTask).toHaveBeenCalledWith(sampleTasks[1]);
  });
});

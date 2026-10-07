import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProjectGanttView from './ProjectGanttView';

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), addToast: vi.fn() }));

vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token' }) }));
vi.mock('@/context/ToastContext', () => ({ useToast: () => ({ addToast: mocks.addToast }) }));
vi.mock('@/context/ProjectUpdateContext', () => ({
  useProjectUpdate: () => ({
    project: { id: 'project-1', milestones: [] },
    tasks: [],
    phases: [],
    activities: [],
    loading: false,
    reloadProject: vi.fn(),
    updateTask: vi.fn(),
    createTask: vi.fn(),
    deleteTask: vi.fn(),
    updateProject: vi.fn(),
  }),
}));
vi.mock('@/lib/http', () => ({ apiFetch: mocks.apiFetch }));
vi.mock('@/components/ui/RightPanel', () => ({
  RightPanel: ({
    open,
    title,
    children,
  }: {
    open: boolean;
    title: string;
    children: ReactNode;
  }) => open ? <section role="dialog" aria-label={title}>{children}</section> : null,
}));
vi.mock('@/components/projects/ProjectBaselineDrawer', () => ({ ProjectBaselineDrawer: () => null }));

describe('ProjectGanttView dependency form accessibility', () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset().mockResolvedValue([]);
    mocks.addToast.mockClear();
  });

  it('uses declared semantic tokens for the Gantt text and fallback phase', async () => {
    const { container } = render(
      <ProjectGanttView
        projectId="project-1"
        tasks={[{ id: 'task-token', project_id: 'project-1', title: 'Token audit', status: 'todo', priority: 'medium' }]}
        phases={[]}
        onOpenTask={vi.fn()}
      />,
    );

    expect(await screen.findByText('Otras Tareas')).toBeInTheDocument();
    expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground|muted)\b/);
    const phaseIndicator = screen.getByText('Otras Tareas').parentElement?.querySelector('div.size-2');
    expect(phaseIndicator).toHaveStyle({ backgroundColor: 'hsl(var(--surface-3))' });
  });

  it('associates every dependency field with its visible label', () => {
    render(
      <ProjectGanttView
        projectId="project-1"
        tasks={[
          { id: 'task-1', project_id: 'project-1', title: 'Predecesora', status: 'todo', priority: 'medium' },
          { id: 'task-2', project_id: 'project-1', title: 'Sucesora', status: 'todo', priority: 'medium' },
        ]}
        phases={[]}
        onOpenTask={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Conectar dependencia' }));

    expect(screen.getByLabelText(/Tarea Predecesora/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Tarea Sucesora/)).toBeInTheDocument();
    expect(screen.getByLabelText('Tipo de Enlace')).toBeInTheDocument();
    expect(screen.getByLabelText(/Lag \(Días de desfase\)/)).toBeInTheDocument();
    expect(screen.getByText('La tarea sucesora puede iniciar cuando finalice la predecesora.')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Tipo de Enlace'), { target: { value: 'SS' } });
    expect(screen.getByRole('heading', { name: 'Inicio a inicio (SS)' })).toBeInTheDocument();
    expect(screen.getByText('La tarea sucesora puede iniciar cuando comience la predecesora.')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Tipo de Enlace'), { target: { value: 'FF' } });
    expect(screen.getByText('La tarea sucesora puede finalizar cuando finalice la predecesora.')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Tipo de Enlace'), { target: { value: 'SF' } });
    expect(screen.getByText('La tarea sucesora puede finalizar cuando comience la predecesora.')).toBeInTheDocument();
  });

  it('opens a task from the Gantt list and timeline bars with Enter and Space', () => {
    const onOpenTask = vi.fn();
    render(
      <ProjectGanttView
        projectId="project-1"
        tasks={[
          {
            id: 'task-keyboard',
            project_id: 'project-1',
            title: 'Tarea accesible',
            status: 'todo',
            priority: 'medium',
            start_date: '2026-10-04T10:00:00Z',
            due_date: '2026-10-06T10:00:00Z',
          },
        ]}
        phases={[]}
        onOpenTask={onOpenTask}
      />,
    );

    const listTask = screen.getByRole('button', {
      name: 'Abrir detalle de tarea Tarea accesible desde la lista del Gantt',
    });
    const timelineTask = screen.getByRole('button', {
      name: 'Abrir detalle de tarea Tarea accesible desde el cronograma',
    });

    fireEvent.keyDown(listTask, { key: 'Enter' });
    fireEvent.keyDown(timelineTask, { key: ' ' });

    expect(onOpenTask).toHaveBeenNthCalledWith(1, expect.objectContaining({ id: 'task-keyboard' }));
    expect(onOpenTask).toHaveBeenNthCalledWith(2, expect.objectContaining({ id: 'task-keyboard' }));
  });

  it('announces dependency load failures and recovers with an explicit retry', async () => {
    let dependencyAttempts = 0;
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith('/dependencies')) {
        dependencyAttempts += 1;
        return dependencyAttempts === 1 ? Promise.reject(new Error('offline')) : Promise.resolve([]);
      }
      return Promise.resolve([]);
    });

    render(
      <ProjectGanttView
        projectId="project-1"
        tasks={[]}
        phases={[]}
        onOpenTask={vi.fn()}
      />,
    );

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudieron cargar los enlaces del cronograma.');
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({
      title: 'No se pudieron cargar las dependencias',
      variant: 'destructive',
    }));

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar carga de dependencias' }));
    await waitFor(() => expect(dependencyAttempts).toBe(2));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(screen.getByRole('status')).toHaveTextContent('0 tareas · 0 dependencias · 0 hitos');
  });

  it('distinguishes a critical path calculation failure from an empty result and retries', async () => {
    let criticalPathAttempts = 0;
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith('/critical-path')) {
        criticalPathAttempts += 1;
        if (criticalPathAttempts === 1) return Promise.reject(new Error('offline'));
        return Promise.resolve({
          project_id: 'project-1',
          total_duration_days: 4,
          critical_tasks_count: 1,
          critical_path_task_ids: ['task-1'],
          tasks: [],
          has_cycles: false,
        });
      }
      return Promise.resolve([]);
    });

    render(
      <ProjectGanttView
        projectId="project-1"
        tasks={[]}
        phases={[]}
        onOpenTask={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Alternar ruta crítica' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo calcular la ruta crítica.');
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({
      title: 'No se pudo calcular la ruta crítica',
      variant: 'destructive',
    }));

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar cálculo de ruta crítica' }));
    await waitFor(() => expect(criticalPathAttempts).toBe(2));
    const criticalPathToggle = await screen.findByRole('button', { name: 'Alternar ruta crítica' });
    expect(criticalPathToggle).toHaveTextContent('Ruta Crítica (1)');
    await waitFor(() => expect(criticalPathToggle).toBeEnabled());
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(criticalPathToggle).toHaveAttribute('aria-pressed', 'true');
  });

  it('loads the baseline only on request and distinguishes an empty result from a failed query', async () => {
    let baselineAttempts = 0;
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith('/baseline')) {
        baselineAttempts += 1;
        return baselineAttempts === 1 ? Promise.reject(new Error('offline')) : Promise.resolve(null);
      }
      return Promise.resolve([]);
    });

    render(
      <ProjectGanttView
        projectId="project-1"
        tasks={[]}
        phases={[]}
        onOpenTask={vi.fn()}
      />,
    );

    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith('/projects/project-1/dependencies', { token: 'test-token' }));
    expect(baselineAttempts).toBe(0);

    fireEvent.click(screen.getByRole('button', { name: 'Alternar línea base' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo consultar la línea base.');
    expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({
      title: 'No se pudo consultar la línea base',
      variant: 'destructive',
    }));

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar consulta de línea base' }));
    await waitFor(() => expect(baselineAttempts).toBe(2));
    expect(await screen.findByText('No hay una línea base registrada.')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('exposes dependency removal as a keyboard-accessible action instead of deleting on click', async () => {
    const today = new Date().toISOString().slice(0, 10);
    mocks.apiFetch.mockImplementation((path: string) => path.endsWith('/dependencies')
      ? Promise.resolve([{
        id: 'dependency-1',
        project_id: 'project-1',
        predecessor_id: 'task-1',
        successor_id: 'task-2',
        dependency_type: 'FS',
        lag_days: 0,
      }])
      : Promise.resolve([]));

    render(
      <ProjectGanttView
        projectId="project-1"
        tasks={[
          { id: 'task-1', project_id: 'project-1', title: 'Predecesora', status: 'todo', priority: 'medium', due_date: today },
          { id: 'task-2', project_id: 'project-1', title: 'Sucesora', status: 'todo', priority: 'medium', start_date: today },
        ]}
        phases={[]}
        onOpenTask={vi.fn()}
      />,
    );

    const removeAction = await screen.findByRole('button', { name: 'Quitar dependencia: Predecesora → Sucesora' });
    fireEvent.keyDown(removeAction, { key: 'Enter' });

    expect(await screen.findByRole('complementary', { name: 'Eliminar dependencia' })).toHaveTextContent('Predecesora');
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Eliminar dependencia' })).not.toBeInTheDocument());
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);

    fireEvent.click(removeAction);
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar dependencia' }));
    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      '/projects/project-1/dependencies/dependency-1',
      expect.objectContaining({ method: 'DELETE', token: 'test-token' }),
    ));
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Quitar dependencia: Predecesora → Sucesora' })).not.toBeInTheDocument());
  });

  it('keeps the confirmation drawer open when removing a dependency fails', async () => {
    const today = new Date().toISOString().slice(0, 10);
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith('/dependencies') && options?.method !== 'DELETE') {
        return Promise.resolve([{
          id: 'dependency-1', project_id: 'project-1', predecessor_id: 'task-1', successor_id: 'task-2', dependency_type: 'FS', lag_days: 0,
        }]);
      }
      if (options?.method === 'DELETE') return Promise.reject(new Error('offline'));
      return Promise.resolve([]);
    });

    render(
      <ProjectGanttView
        projectId="project-1"
        tasks={[
          { id: 'task-1', project_id: 'project-1', title: 'Predecesora', status: 'todo', priority: 'medium', due_date: today },
          { id: 'task-2', project_id: 'project-1', title: 'Sucesora', status: 'todo', priority: 'medium', start_date: today },
        ]}
        phases={[]}
        onOpenTask={vi.fn()}
      />,
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Quitar dependencia: Predecesora → Sucesora' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar dependencia' }));

    await waitFor(() => expect(mocks.addToast).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Error al eliminar',
      variant: 'destructive',
    })));
    expect(screen.getByRole('complementary', { name: 'Eliminar dependencia' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Quitar dependencia: Predecesora → Sucesora' })).toBeInTheDocument();
  });
});

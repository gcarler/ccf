import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMockTask } from '@/test-utils/factories';
import type { PhaseDef } from '@/context/ProjectUpdateContext';
import ProjectListView from './ProjectListView';

vi.mock('@/context/SidebarLayerContext', () => ({
  useSidebarLayers: () => ({
    openLayer: vi.fn(),
    setRightMode: vi.fn(),
  }),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn().mockResolvedValue([]) }));

vi.mock('@/components/ui/inline-editors', () => ({
  InlineStatusPicker: ({
    value,
    phases,
    onChange,
  }: {
    value: string;
    phases?: PhaseDef[];
    onChange: (value: string) => void;
  }) => (
    <button
      type="button"
      aria-label="Cambiar estado"
      onClick={() => onChange(phases?.[1]?.slug ?? value)}
    >
      {value}
    </button>
  ),
  InlinePriorityPicker: ({ value }: { value: string }) => <span>{value}</span>,
  InlineDatePicker: ({ value }: { value: string | null }) => <span>{value ?? 'Sin fecha'}</span>,
  InlineUserPicker: ({ value }: { value: string | null }) => <span>{value ?? 'Sin asignar'}</span>,
}));

const mockCreateTask = vi.fn().mockResolvedValue(true);
vi.mock('@/context/ProjectUpdateContext', () => ({
  useProjectUpdate: () => ({
    createTask: mockCreateTask,
  }),
}));

describe('ProjectListView', () => {
  const phases: PhaseDef[] = [
    { slug: 'backlog', name: 'Por planificar', color: '#64748b', order_index: 0 },
    { slug: 'review_custom', name: 'Revisión pastoral', color: '#f59e0b', order_index: 1 },
  ];

  it('uses declared semantic tokens and accessible warning contrast for the favorites filter', async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ProjectListView
        tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
        phaseDefs={phases}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
        onTaskUpdate={vi.fn()}
      />,
    );

    expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground|background)\b/);
    await user.click(screen.getByRole('button', { name: /Solo Mis Favoritas/ }));
    expect(screen.getByRole('button', { name: /Solo Mis Favoritas/ })).toHaveClass(
      'bg-[hsl(var(--warning-muted))]',
      'text-[hsl(var(--warning-text))]',
    );
  });

  it('groups tasks using the project custom phase label', () => {
    render(
      <ProjectListView
        tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
        phaseDefs={phases}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
        onTaskUpdate={vi.fn()}
      />,
    );

    expect(screen.getByText('Por planificar')).toBeInTheDocument();
    expect(screen.getByText('Preparar reunión')).toBeInTheDocument();
  });

  it('delegates custom phase status changes to the parent callback', async () => {
    const onTaskUpdate = vi.fn();
    render(
      <ProjectListView
        tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
        phaseDefs={phases}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
        onTaskUpdate={onTaskUpdate}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Cambiar estado' }));

    expect(onTaskUpdate).toHaveBeenCalledWith('task-1', { status: 'review_custom' });
  });

  it('opens quick comment popover and renders all controls completely visible', async () => {
    render(
      <ProjectListView
        tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
        phaseDefs={phases}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
        onTaskUpdate={vi.fn()}
      />,
    );

    const commentBtn = screen.getByRole('button', { name: 'Ver comentarios y actividad' });
    await userEvent.click(commentBtn);

    expect(screen.getByTestId('quick-comment-popover')).toBeInTheDocument();
    expect(screen.getByText('Comentario rápido')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Escribe un comentario/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Adjuntar archivo' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mencionar usuario' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Añadir emoji' })).toBeInTheDocument();
  });

  it('smart flip: adapts placement to top (bottom-full mb-1) when trigger is near bottom of viewport', async () => {
    const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = vi.fn().mockReturnValue({
      top: 850,
      bottom: 890,
      left: 100,
      right: 200,
      width: 100,
      height: 40,
    });
    Object.defineProperty(window, 'innerHeight', { writable: true, configurable: true, value: 900 });

    try {
      render(
        <ProjectListView
          tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
          phaseDefs={phases}
          onOpenTask={vi.fn()}
          onAddTask={vi.fn()}
          onTaskUpdate={vi.fn()}
        />,
      );

      const commentBtn = screen.getByRole('button', { name: 'Ver comentarios y actividad' });
      await userEvent.click(commentBtn);

      const popover = screen.getByTestId('quick-comment-popover');
      expect(popover).toHaveAttribute('data-placement', 'top');
    } finally {
      Element.prototype.getBoundingClientRect = originalGetBoundingClientRect;
    }
  });

  it('smart flip: adapts placement to bottom (top-full mt-1) when there is ample space below', async () => {
    const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = vi.fn().mockReturnValue({
      top: 100,
      bottom: 140,
      left: 100,
      right: 200,
      width: 100,
      height: 40,
    });
    Object.defineProperty(window, 'innerHeight', { writable: true, configurable: true, value: 900 });

    try {
      render(
        <ProjectListView
          tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
          phaseDefs={phases}
          onOpenTask={vi.fn()}
          onAddTask={vi.fn()}
          onTaskUpdate={vi.fn()}
        />,
      );

      const commentBtn = screen.getByRole('button', { name: 'Ver comentarios y actividad' });
      await userEvent.click(commentBtn);

      const popover = screen.getByTestId('quick-comment-popover');
      expect(popover).toHaveAttribute('data-placement', 'bottom');
    } finally {
      Element.prototype.getBoundingClientRect = originalGetBoundingClientRect;
    }
  });

  it('enables Enviar button when comment text is typed and closes on send or escape', async () => {
    render(
      <ProjectListView
        tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
        phaseDefs={phases}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
        onTaskUpdate={vi.fn()}
      />,
    );

    const commentBtn = screen.getByRole('button', { name: 'Ver comentarios y actividad' });
    await userEvent.click(commentBtn);

    const sendBtn = screen.getByRole('button', { name: 'Enviar' });
    expect(sendBtn).toBeDisabled();

    const textarea = screen.getByPlaceholderText(/Escribe un comentario/i);
    await userEvent.type(textarea, 'Revisar detalles finales con el equipo');

    expect(sendBtn).toBeEnabled();

    // Click Enviar closes popover
    await userEvent.click(sendBtn);
    await waitFor(() => {
      expect(screen.queryByTestId('quick-comment-popover')).not.toBeInTheDocument();
    });
  });

  it('renders Detalle column with pencil button that calls onOpenTask on click', async () => {
    const onOpenTask = vi.fn();
    const task = createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' });
    render(
      <ProjectListView
        tasks={[task]}
        phaseDefs={phases}
        onOpenTask={onOpenTask}
        onAddTask={vi.fn()}
      />,
    );

    expect(screen.getByText('Detalle')).toBeInTheDocument();
    const pencilButton = screen.getByRole('button', { name: `Ver detalle completo de ${task.title}` });
    expect(pencilButton).toBeInTheDocument();
    expect(pencilButton).toHaveAttribute('title', 'Ver detalle completo');

    await userEvent.click(pencilButton);
    expect(onOpenTask).toHaveBeenCalledWith(task);
  });

  it('triggers inline quick creation on clicking "+ Nuevo" without calling onAddTask and invokes createTask on Enter', async () => {
    const onAddTask = vi.fn();
    mockCreateTask.mockClear();

    render(
      <ProjectListView
        tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
        phaseDefs={phases}
        onOpenTask={vi.fn()}
        onAddTask={onAddTask}
      />,
    );

    // Find the "+ Nuevo" button in the group
    const nuevoBtn = screen.getByRole('button', { name: /Nuevo/i });
    await userEvent.click(nuevoBtn);

    // Ensure onAddTask was NOT called (drawer was not opened)
    expect(onAddTask).not.toHaveBeenCalled();

    // The inline input with autofocus placeholder appears
    const input = screen.getByPlaceholderText('Nombre de la actividad... (Enter para crear)');
    expect(input).toBeInTheDocument();

    // Type new task name and hit Enter
    await userEvent.type(input, 'Nueva tarea inline{enter}');

    // createTask from useProjectUpdate was invoked
    expect(mockCreateTask).toHaveBeenCalledWith({
      title: 'Nueva tarea inline',
      status: 'backlog',
      priority: 'medium',
    });

    // onAddTask was never called
    expect(onAddTask).not.toHaveBeenCalled();
  });

  it('creates task when clicking the Crear button in inline creation row', async () => {
    mockCreateTask.mockClear();

    render(
      <ProjectListView
        tasks={[createMockTask({ id: 'task-1', title: 'Preparar reunión', status: 'backlog' })]}
        phaseDefs={phases}
        onOpenTask={vi.fn()}
        onAddTask={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /Nuevo/i }));

    const input = screen.getByPlaceholderText('Nombre de la actividad... (Enter para crear)');
    await userEvent.type(input, 'Actividad botón crear');

    const crearBtn = screen.getByRole('button', { name: 'Crear' });
    await userEvent.click(crearBtn);

    expect(mockCreateTask).toHaveBeenCalledWith({
      title: 'Actividad botón crear',
      status: 'backlog',
      priority: 'medium',
    });
  });
});

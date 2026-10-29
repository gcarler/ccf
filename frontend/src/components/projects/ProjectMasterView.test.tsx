import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { ProjectMasterView } from './ProjectMasterView';
import { createMockProject, createMockTask } from '@/test-utils/factories';

// addToast se inspecciona desde los tests de resiliencia (TKT-GAP: feedback
// visible en vez de catch silencioso).
const { addToastMock, authTokenMock } = vi.hoisted(() => ({
  addToastMock: vi.fn(),
  authTokenMock: { current: null as string | null },
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    token: authTokenMock.current,
    user: null,
    loading: false,
    isAuthenticated: true,
  }),
  useOptionalAuth: () => ({
    token: authTokenMock.current,
    user: null,
    loading: false,
    isAuthenticated: true,
  }),
}));

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ addToast: addToastMock }),
}));

vi.mock('@/context/ProjectUpdateContext', () => ({
  useProjectUpdate: () => ({
    reloadProject: vi.fn(),
    updateProject: vi.fn(),
    updateTask: vi.fn(),
  }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue(null),
}));

vi.mock('@/components/ui/inline-editors/InlineTextInput', () => ({
  InlineTextInput: ({ value }: { value: string }) => <span>{value}</span>,
}));

vi.mock('@/components/ui/inline-editors/InlineTextArea', () => ({
  InlineTextArea: ({ value }: { value: string }) => <span>{value}</span>,
}));

vi.mock('@/components/ui/inline-editors/InlineProjectStatusPicker', () => ({
  InlineProjectStatusPicker: ({ value }: { value: string }) => <span>{value}</span>,
}));

vi.mock('@/components/ui/inline-editors', () => ({
  InlineUserPicker: ({ value }: { value: string | null }) => <span>{value ?? 'Sin asignar'}</span>,
}));

vi.mock('@/components/ui/inline-editors/InlineDatePicker', () => ({
  InlineDatePicker: ({ value }: { value: string | null }) => <span>{value ?? 'Sin fecha'}</span>,
}));

describe('ProjectMasterView resiliencia de resúmenes (TKT-PROJECTS-GAP)', () => {
  it('notifica error visible en los 4 summary loaders cuando el backend falla', async () => {
    const apiFetch = vi.mocked((await import('@/lib/http')).apiFetch);
    addToastMock.mockClear();
    apiFetch.mockRejectedValue(new Error('backend caído'));
    authTokenMock.current = 'test-token';

    render(<ProjectMasterView project={createMockProject()} tasks={[]} onOpenTool={vi.fn()} />);

    await waitFor(() => {
      expect(addToastMock).toHaveBeenCalledWith(
        'No se pudo cargar el presupuesto. Reintenta desde el control presupuestario.',
        'error',
      );
      expect(addToastMock).toHaveBeenCalledWith(
        'No se pudo cargar la matriz de riesgos. Reintenta desde la matriz RAID.',
        'error',
      );
      expect(addToastMock).toHaveBeenCalledWith(
        'No se pudo cargar la carga de trabajo. Reintenta desde el panel de capacidad.',
        'error',
      );
      expect(addToastMock).toHaveBeenCalledWith(
        'No se pudo cargar el registro de tiempo. Reintenta desde hojas de horas.',
        'error',
      );
    }, { timeout: 2000 });
    expect(addToastMock).toHaveBeenCalledTimes(4);
  });
  afterEach(() => {
    authTokenMock.current = null;
  });
});

describe('ProjectMasterView PMI Triple Constraint & Node Governance', () => {
  it('opens summary tools through the shared management hub', () => {
    const onOpenTool = vi.fn();
    render(<ProjectMasterView project={createMockProject()} tasks={[]} onOpenTool={onOpenTool} />);
    fireEvent.click(screen.getByRole('button', { name: /Gestionar Riesgos/ }));
    expect(onOpenTool).toHaveBeenCalledWith('risks');
    fireEvent.click(screen.getByRole('button', { name: /Planificar Carga/ }));
    expect(onOpenTool).toHaveBeenCalledWith('workload');
  });
  it('renders PMI triple constraint synthesis banner with Scope (0/50/100), Cost (EVM CPI) and Schedule/RACI', () => {
    const project = createMockProject({
      id: 'proj-1',
      title: 'Proyecto Pastoral',
      status: 'active',
      budget_allocated: 1000000,
      budget_spent: 400000,
      milestones: [
        { id: 'm1', project_id: 'proj-1', title: 'Hito 1', is_completed: true },
        { id: 'm2', project_id: 'proj-1', title: 'Hito 2', is_completed: false },
      ],
    });

    const tasks = [
      createMockTask({
        id: 't1',
        project_id: 'proj-1',
        title: 'Tarea Completada',
        status: 'completed',
        assignee_id: 'user-1',
        due_date: '2099-12-31',
      }),
      createMockTask({
        id: 't2',
        project_id: 'proj-1',
        title: 'Tarea En Curso',
        status: 'in_progress',
        assignee_id: 'user-2',
        due_date: '2099-12-31',
      }),
      createMockTask({
        id: 't3',
        project_id: 'proj-1',
        title: 'Tarea Pendiente',
        status: 'todo',
        assignee_id: 'user-3',
        due_date: '2099-12-31',
      }),
    ];

    render(<ProjectMasterView project={project} tasks={tasks} />);

    expect(screen.getByTestId('master-view-pmi-triple-constraint-banner')).toBeInTheDocument();

    // (100 + 50 + 0) / 3 = 50%
    const scopeCard = screen.getByTestId('master-view-pmi-scope');
    expect(scopeCard).toHaveTextContent('50% Avance PMI (0/50/100)');
    expect(scopeCard).toHaveTextContent('3 paquetes');
    expect(scopeCard).toHaveTextContent('1/2 hitos');

    // BAC = 1.000.000, EV = 500.000, AC = 400.000 => CPI = 1.25 (Bajo Presupuesto)
    const costCard = screen.getByTestId('master-view-pmi-cost');
    expect(costCard).toHaveTextContent('BAC $1.000.000');
    expect(costCard).toHaveTextContent('EV $500.000');
    expect(costCard).toHaveTextContent('AC $400.000');
    expect(costCard).toHaveTextContent('Bajo Presupuesto (CPI 1.25)');

    const scheduleCard = screen.getByTestId('master-view-pmi-schedule-raci');
    expect(scheduleCard).toHaveTextContent('0 vencida(s)');
    expect(scheduleCard).toHaveTextContent('0 sin RACI');
    expect(scheduleCard).toHaveTextContent('Cronograma y RACI Controlados');
  });

  it('flags critical cost overrun (CPI < 0.85) and schedule/RACI gaps when tasks are overdue or unassigned', () => {
    const project = createMockProject({
      id: 'proj-2',
      title: 'Proyecto Riesgo Costo',
      status: 'active',
      budget_allocated: 1000000,
      budget_spent: 800000,
      milestones: [],
    });

    const tasks = [
      createMockTask({
        id: 't1',
        project_id: 'proj-2',
        title: 'Paquete Vencido Sin Responsable',
        status: 'in_progress',
        assignee_id: null,
        due_date: '2020-01-01',
      }),
    ];

    render(<ProjectMasterView project={project} tasks={tasks} />);

    // Avance PMI = 50%, EV = 500.000, AC = 800.000 => CPI = 0.63 (< 0.85)
    const costCard = screen.getByTestId('master-view-pmi-cost');
    expect(costCard).toHaveTextContent('Sobrecosto Crítico (CPI 0.63)');

    const scheduleCard = screen.getByTestId('master-view-pmi-schedule-raci');
    expect(scheduleCard).toHaveTextContent('1 vencida(s)');
    expect(scheduleCard).toHaveTextContent('1 sin RACI');
    expect(scheduleCard).toHaveTextContent('Atención Requerida');
  });

  it('calculates operational node completion percentage and accumulated BAC in NodeCard', () => {
    const project = createMockProject({
      id: 'proj-3',
      title: 'Proyecto Nodos',
      status: 'active',
    });

    const tasks = [
      createMockTask({
        id: 'n1',
        project_id: 'proj-3',
        title: 'Nutrición 1',
        node: 'nutrition',
        status: 'completed',
        budget_allocated: 120000,
      }),
      createMockTask({
        id: 'n2',
        project_id: 'proj-3',
        title: 'Nutrición 2',
        node: 'nutrition',
        status: 'todo',
        budget_allocated: 80000,
      }),
      createMockTask({
        id: 'd1',
        project_id: 'proj-3',
        title: 'Digital 1',
        node: 'digital',
        status: 'completed',
        budget_allocated: 350000,
      }),
    ];

    render(<ProjectMasterView project={project} tasks={tasks} />);

    const nodeMetrics = screen.getAllByTestId('master-view-node-pmi-metrics');
    expect(nodeMetrics).toHaveLength(2);
    expect(nodeMetrics[0]).toHaveTextContent('50% completado');
    expect(nodeMetrics[0]).toHaveTextContent('BAC $200.000');
    expect(nodeMetrics[1]).toHaveTextContent('100% completado');
    expect(nodeMetrics[1]).toHaveTextContent('BAC $350.000');
  });
});

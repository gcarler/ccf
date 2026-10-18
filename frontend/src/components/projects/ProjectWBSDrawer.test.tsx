import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProjectWBSDrawer } from './ProjectWBSDrawer';
import type { ProjectWBSTreeResponse } from '@/types/projects';

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  toast: { error: vi.fn() },
}));

vi.mock('@/lib/http', () => ({ apiFetch: mocks.apiFetch }));
vi.mock('sonner', () => ({ toast: mocks.toast }));
vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token' }) }));
vi.mock('@/components/ui/RightPanel', () => ({
  default: ({ isOpen, children, title, subtitle }: { isOpen: boolean; children: React.ReactNode; title: React.ReactNode; subtitle: React.ReactNode }) =>
    isOpen ? <div>{title}{subtitle}{children}</div> : null,
}));

const tree: ProjectWBSTreeResponse = {
  project_id: 'project-1',
  project_title: 'Renovación del templo',
  total_nodes: 6,
  max_depth: 3,
  root: {
    id: 'project-1', wbs_code: '0', title: 'Renovación del templo', type: 'project', level: 0,
    status: 'active', progress_pct: 50, estimated_hours: 100, actual_hours: 42,
    budget_allocated: 100000, cost: 42000, is_leaf: false, children: [
      {
        id: 'component-1', wbs_code: '1', title: 'Obra civil', description: 'Edificio y fundaciones', type: 'component', level: 1,
        status: 'active', progress_pct: 40, estimated_hours: 40, actual_hours: 18,
        budget_allocated: 40000, cost: 18000, is_leaf: false, children: [
          {
            id: 'task-1', wbs_code: '1.1', title: 'Fundaciones', description: 'Construcción de fundaciones', type: 'task', level: 2,
            status: 'active', progress_pct: 50, estimated_hours: 10, actual_hours: 5,
            budget_allocated: null, cost: 5000, is_leaf: true, children: [],
          },
          {
            id: 'task-2', wbs_code: '1.2', title: 'Estructura', type: 'task', level: 2,
            status: 'active', progress_pct: 30, estimated_hours: 30, actual_hours: 13,
            budget_allocated: null, cost: 13000, is_leaf: false, children: [
              {
                id: 'subtask-1', wbs_code: '1.2.1', title: 'Montaje de vigas', type: 'task', level: 3,
                status: 'todo', progress_pct: 0, estimated_hours: 30, actual_hours: 0,
                budget_allocated: null, cost: 0, is_leaf: true, children: [],
              },
            ],
          },
        ],
      },
      {
        id: 'component-2', wbs_code: '2', title: 'Instalaciones', type: 'component', level: 1,
        status: 'active', progress_pct: 60, estimated_hours: 60, actual_hours: 24,
        budget_allocated: 60000, cost: 24000, is_leaf: false, children: [
          {
            id: 'task-3', wbs_code: '2.1', title: 'Cableado eléctrico', type: 'task', level: 2,
            status: 'active', progress_pct: 60, estimated_hours: 60, actual_hours: 24,
            budget_allocated: null, cost: 24000, is_leaf: true, children: [],
          },
        ],
      },
    ],
  },
};

describe('ProjectWBSDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.apiFetch.mockResolvedValue(tree);
  });

  it('muestra códigos jerárquicos canónicos y la validación de la Regla del 100%', async () => {
    render(<ProjectWBSDrawer projectId="project-1" isOpen onClose={vi.fn()} />);

    expect(await screen.findByTestId('wbs-node-1.0')).toBeInTheDocument();
    expect(screen.getByTestId('wbs-node-1.1')).toBeInTheDocument();
    expect(screen.getByTestId('wbs-node-1.1.1')).toBeInTheDocument();
    expect(screen.getByTestId('wbs-node-1.1.2.1')).toBeInTheDocument();
    expect(screen.getByText('Peso técnico de componentes')).toBeInTheDocument();
    expect(screen.getAllByText('100.0%', { selector: 'p' })).toHaveLength(3);
    expect(screen.getByText('Presupuesto de componentes vs BAC del proyecto')).toBeInTheDocument();
    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith('/projects/project-1/wbs-tree', { token: 'test-token' }));
  });

  it('selecciona un paquete hoja y presenta su ficha del Diccionario de la EDT', async () => {
    render(<ProjectWBSDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    fireEvent.click(await screen.findByTestId('wbs-node-1.1.1'));

    expect(screen.getByTestId('wbs-dictionary-entry')).toHaveTextContent('Fundaciones');
    const dictionary = screen.getByTestId('wbs-dictionary-entry');
    expect(within(dictionary).getByText('Paquete de Trabajo Hoja')).toBeInTheDocument();
    expect(within(dictionary).getByText('Construcción de fundaciones')).toBeInTheDocument();
    expect(within(dictionary).getByText('Criterio de aceptación')).toBeInTheDocument();
    expect(within(dictionary).getByText('No registrado en el modelo actual.')).toBeInTheDocument();
    expect(within(dictionary).getByText('Avance físico ponderado')).toBeInTheDocument();
  });

  it('filtra por nombre/código y limita la vista a paquetes de trabajo hoja', async () => {
    render(<ProjectWBSDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    const search = await screen.findByRole('textbox', { name: 'Buscar por código WBS o nombre' });
    fireEvent.change(search, { target: { value: 'vigas' } });

    expect(screen.getByTestId('wbs-node-1.1.2.1')).toBeInTheDocument();
    expect(screen.queryByTestId('wbs-node-1.1')).not.toBeInTheDocument();
    fireEvent.change(search, { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: 'Solo Paquetes de Trabajo Hoja' }));

    expect(screen.queryByTestId('wbs-node-1.0')).not.toBeInTheDocument();
    expect(screen.queryByTestId('wbs-node-1.1.2')).not.toBeInTheDocument();
    expect(screen.getByTestId('wbs-node-1.1.2.1')).toBeInTheDocument();
  });

  it('usa únicamente clases de color semánticas', async () => {
    const { container } = render(<ProjectWBSDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    await screen.findByTestId('wbs-node-1.0');
    expect(container.innerHTML).not.toMatch(/\b(?:bg|text|border)-(?:blue|red|green|gray|slate|indigo|violet|purple)-\d{2,3}\b/);
  });
});

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import TaskRouteTree, { type RouteNode } from './TaskRouteTree';

const sampleBreadcrumb: Array<{ label: string; type: RouteNode['type'] }> = [
  { label: 'Espacio de Proyectos', type: 'workspace' },
  { label: 'Programa Transformación Digital', type: 'project' },
  { label: 'EDT-1.0 · Infraestructura', type: 'section' },
  { label: 'Desplegar Kubernetes', type: 'task' },
];

const sampleTree: RouteNode[] = [
  {
    id: 'ws-1',
    label: 'Espacio de Proyectos',
    type: 'workspace',
    active: true,
    children: [
      {
        id: 'proj-1',
        label: 'Programa Transformación Digital',
        type: 'project',
        active: true,
        children: [
          {
            id: 'sec-1',
            label: 'EDT-1.0 · Infraestructura',
            type: 'section',
            active: true,
            children: [
              {
                id: 'task-parent',
                label: 'Configurar Cluster Base',
                type: 'task',
                children: [
                  {
                    id: 'task-leaf-1',
                    label: 'Desplegar Kubernetes',
                    type: 'task',
                    active: true,
                  },
                ],
              },
              {
                id: 'task-leaf-2',
                label: 'Validar Balanceador TLS',
                type: 'task',
              },
            ],
          },
          {
            id: 'sec-empty',
            label: 'EDT-2.0 · Fase sin Paquetes',
            type: 'section',
            children: [],
          },
        ],
      },
    ],
  },
];

describe('TaskRouteTree PMI WBS Hierarchy Diagnostics', () => {
  it('calculates recursive WBS hierarchy summary (total nodes, max depth, leaf work packages, and current level)', () => {
    render(
      <TaskRouteTree
        breadcrumb={sampleBreadcrumb}
        tree={sampleTree}
        activeId="task-leaf-1"
      />
    );

    const summary = screen.getByTestId('task-route-pmi-summary');
    // Nodes: ws-1 (1) + proj-1 (2) + sec-1 (3) + task-parent (4) + task-leaf-1 (5) + task-leaf-2 (6) + sec-empty (7) = 7
    expect(summary).toHaveTextContent('Nodos Totales');
    expect(summary).toHaveTextContent('7');
    // Max depth: ws-1 (1) -> proj-1 (2) -> sec-1 (3) -> task-parent (4) -> task-leaf-1 (5) = 5 niveles
    expect(summary).toHaveTextContent('5 niveles');
    // Leaf packages (type === 'task' and no children): task-leaf-1, task-leaf-2 => 2
    expect(summary).toHaveTextContent('Paquetes Hoja (WP)');
    expect(summary).toHaveTextContent('2');
    // Current level: breadcrumb.length = 4 => Nivel 4
    expect(summary).toHaveTextContent('Nivel 4');
  });

  it('filters WBS tree by search text preserving ancestors and toggles leaf work packages only', () => {
    const onNavigate = vi.fn();
    render(
      <TaskRouteTree
        breadcrumb={sampleBreadcrumb}
        tree={sampleTree}
        activeId="task-leaf-1"
        onNavigate={onNavigate}
      />
    );

    // Initially, sec-empty is visible under expanded proj-1
    expect(screen.getByText('EDT-2.0 · Fase sin Paquetes')).toBeInTheDocument();

    // Toggle "Solo Paquetes Hoja (WP)" -> prunes sec-empty since it has no leaf task descendants
    fireEvent.click(screen.getByTestId('task-route-leaf-toggle'));
    expect(screen.queryByText('EDT-2.0 · Fase sin Paquetes')).not.toBeInTheDocument();
    expect(screen.getByText('Validar Balanceador TLS')).toBeInTheDocument();

    // Turn off leaf toggle and filter by search query
    fireEvent.click(screen.getByTestId('task-route-leaf-toggle'));
    const searchInput = screen.getByTestId('task-route-search-input');
    fireEvent.change(searchInput, { target: { value: 'Balanceador' } });

    expect(screen.getByText('Validar Balanceador TLS')).toBeInTheDocument();
    expect(screen.queryByText('EDT-2.0 · Fase sin Paquetes')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Validar Balanceador TLS'));
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'task-leaf-2', label: 'Validar Balanceador TLS' })
    );
  });
});

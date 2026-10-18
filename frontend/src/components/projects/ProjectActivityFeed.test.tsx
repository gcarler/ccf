import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ProjectActivityFeed from './ProjectActivityFeed';
import type { ProjectActivityItem } from '@/types/projects';

const sampleActivities: ProjectActivityItem[] = [
  {
    id: 'act-1',
    kind: 'project_created',
    project_id: 'proj-1',
    project_title: 'Programa Modernización PMI',
    task_id: null,
    task_title: null,
    description: 'Se constituyó el proyecto y su Project Charter.',
    created_at: '2026-10-18T01:00:00Z',
  },
  {
    id: 'act-2',
    kind: 'task_created',
    project_id: 'proj-1',
    project_title: 'Programa Modernización PMI',
    task_id: 'task-10',
    task_title: 'Paquete WBS 1.1 Diagnóstico',
    description: 'Se dio de alta el paquete de trabajo en la EDT.',
    created_at: '2026-10-18T02:00:00Z',
  },
  {
    id: 'act-3',
    kind: 'status_changed',
    project_id: 'proj-1',
    project_title: 'Programa Modernización PMI',
    task_id: 'task-10',
    task_title: 'Paquete WBS 1.1 Diagnóstico',
    description: 'Estado actualizado de Planificación a En Ejecución.',
    created_at: '2026-10-18T03:00:00Z',
  },
  {
    id: 'act-4',
    kind: 'comment_added',
    project_id: 'proj-1',
    project_title: 'Programa Modernización PMI',
    task_id: 'task-10',
    task_title: 'Paquete WBS 1.1 Diagnóstico',
    description: 'Comité Técnico aprobó el entregable preliminar.',
    created_at: '2026-10-18T04:00:00Z',
  },
  {
    id: 'act-5',
    kind: 'custom_audit',
    project_id: 'proj-1',
    project_title: 'Programa Modernización PMI',
    task_id: null,
    task_title: 'Auditoría Automática',
    description: 'Sincronización de línea base completada.',
    created_at: '2026-10-18T05:00:00Z',
  },
];

describe('ProjectActivityFeed PMI §4.5 Traceability & Audit', () => {
  it('renders PMI summary counts and semantic badges for each event kind', () => {
    render(<ProjectActivityFeed activities={sampleActivities} />);

    const summary = screen.getByTestId('activity-feed-pmi-summary');
    expect(summary).toHaveTextContent('Alcance / Altas');
    expect(summary).toHaveTextContent('2');
    expect(summary).toHaveTextContent('Cambios de Fase');
    expect(summary).toHaveTextContent('1');
    expect(summary).toHaveTextContent('Comunicaciones');

    expect(screen.getByTestId('activity-feed-pmi-badge-act-1')).toHaveTextContent('Alcance EDT');
    expect(screen.getByTestId('activity-feed-pmi-badge-act-2')).toHaveTextContent('Alcance EDT');
    expect(screen.getByTestId('activity-feed-pmi-badge-act-3')).toHaveTextContent('Transición de Fase');
    expect(screen.getByTestId('activity-feed-pmi-badge-act-4')).toHaveTextContent('Comunicación');
    expect(screen.getByTestId('activity-feed-pmi-badge-act-5')).toHaveTextContent('Evento de Sistema');
  });

  it('filters activity logs by PMI category pills and text search input', () => {
    const onRefresh = vi.fn();
    render(<ProjectActivityFeed activities={sampleActivities} onRefresh={onRefresh} />);

    const filterContainer = screen.getByTestId('activity-feed-pmi-filter');

    // Filter by SCOPE ("Alcance")
    fireEvent.click(within(filterContainer).getByRole('button', { name: 'Alcance' }));
    expect(screen.getByText('Se constituyó el proyecto y su Project Charter.')).toBeInTheDocument();
    expect(screen.getByText('Se dio de alta el paquete de trabajo en la EDT.')).toBeInTheDocument();
    expect(screen.queryByText('Estado actualizado de Planificación a En Ejecución.')).not.toBeInTheDocument();

    // Filter by TRANSITION ("Transiciones")
    fireEvent.click(within(filterContainer).getByRole('button', { name: 'Transiciones' }));
    expect(screen.getByText('Estado actualizado de Planificación a En Ejecución.')).toBeInTheDocument();
    expect(screen.queryByText('Se constituyó el proyecto y su Project Charter.')).not.toBeInTheDocument();

    // Filter by COMMUNICATION ("Comunicaciones")
    fireEvent.click(within(filterContainer).getByRole('button', { name: 'Comunicaciones' }));
    expect(screen.getByText('Comité Técnico aprobó el entregable preliminar.')).toBeInTheDocument();
    expect(screen.queryByText('Estado actualizado de Planificación a En Ejecución.')).not.toBeInTheDocument();

    // Reset to ALL ("Todos") and search by text
    fireEvent.click(within(filterContainer).getByRole('button', { name: 'Todos' }));
    const searchInput = screen.getByTestId('activity-feed-search-input');
    fireEvent.change(searchInput, { target: { value: 'Comité Técnico' } });

    expect(screen.getByText('Comité Técnico aprobó el entregable preliminar.')).toBeInTheDocument();
    expect(screen.queryByText('Se constituyó el proyecto y su Project Charter.')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Actualizar historia' }));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });
});

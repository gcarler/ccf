import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import UniversalListView, { ListItem } from './UniversalListView';

describe('UniversalListView component', () => {
  const sampleItems: ListItem[] = [
    {
      id: '1',
      title: 'Planificación de Conferencia',
      description: 'Detalles del evento de liderazgo',
      status: 'completed',
      priority: 'high',
      assignee: 'Pastor Carlos',
      date: '2026-08-15',
    },
    {
      id: '2',
      title: 'Revisión de Inventario',
      description: 'Auditoría de recursos',
      status: 'pending',
      priority: 'low',
    },
  ];

  it('renders empty message when no items are provided', () => {
    render(<UniversalListView items={[]} emptyMessage="No hay elementos" />);

    expect(screen.getByText('No hay elementos')).toBeInTheDocument();
  });

  it('renders items, searches by title and handles item click', () => {
    const onItemClickMock = vi.fn();

    render(
      <UniversalListView
        items={sampleItems}
        title="Proyectos Activos"
        onItemClick={onItemClickMock}
      />
    );

    expect(screen.getByText('Proyectos Activos')).toBeInTheDocument();
    expect(screen.getByText('Planificación de Conferencia')).toBeInTheDocument();
    expect(screen.getByText('Revisión de Inventario')).toBeInTheDocument();

    // Test search filter
    const searchInput = screen.getByPlaceholderText('Buscar...');
    fireEvent.change(searchInput, { target: { value: 'Conferencia' } });

    expect(screen.getByText('Planificación de Conferencia')).toBeInTheDocument();

    // Click item
    fireEvent.click(screen.getByText('Planificación de Conferencia'));
    expect(onItemClickMock).toHaveBeenCalledWith(sampleItems[0]);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <UniversalListView items={sampleItems} title="Proyectos Activos" />
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'jest-axe';
import UniversalTableView, { TableColumn } from './UniversalTableView';

// Avoid registering real AG Grid modules in unit tests
vi.mock('@/lib/agGrid', () => ({}));

// Use the lightweight manual mock defined in src/__mocks__/ag-grid-react.tsx
vi.mock('ag-grid-react', async () => import('../../__mocks__/ag-grid-react'));

interface Row {
  id: string;
  name: string;
  status: string;
  priority: string;
}

const columns: TableColumn<Row>[] = [
  { key: 'name', label: 'Nombre', type: 'text', width: '200' },
  { key: 'status', label: 'Estado', type: 'status' },
  { key: 'priority', label: 'Prioridad', type: 'priority' },
];

const data: Row[] = [
  { id: '1', name: 'Alice', status: 'completed', priority: 'high' },
  { id: '2', name: 'Bob', status: 'todo', priority: 'low' },
];

describe('UniversalTableView', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders empty message when no data', () => {
    render(<UniversalTableView data={[]} columns={columns} />);
    expect(screen.getByText('No hay registros para mostrar')).toBeInTheDocument();
  });

  it('renders loading skeleton when isLoading is true', () => {
    const { container } = render(<UniversalTableView data={[]} columns={columns} isLoading />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders rows and status/priority badges', () => {
    render(<UniversalTableView data={data} columns={columns} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('Completado')).toBeInTheDocument();
    expect(screen.getByText('Pendiente')).toBeInTheDocument();
  });

  it('filters rows via quick search', async () => {
    render(<UniversalTableView data={data} columns={columns} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
    const searchInput = screen.getByPlaceholderText('Buscar…');
    fireEvent.change(searchInput, { target: { value: 'Bob' } });
    await waitFor(() => {
      expect(screen.queryByText('Bob')).toBeInTheDocument();
      expect(screen.queryByText('Alice')).not.toBeInTheDocument();
    });
  });

  it('calls onRowClick when a row is clicked', () => {
    const handleRowClick = vi.fn();
    render(<UniversalTableView data={data} columns={columns} onRowClick={handleRowClick} />);
    fireEvent.click(screen.getByText('Alice'));
    expect(handleRowClick).toHaveBeenCalledTimes(1);
    expect(handleRowClick).toHaveBeenCalledWith(data[0]);
  });

  it('renders custom empty message', () => {
    render(<UniversalTableView data={[]} columns={columns} emptyMessage="Sin datos de prueba" />);
    expect(screen.getByText('Sin datos de prueba')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<UniversalTableView data={data} columns={columns} />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});

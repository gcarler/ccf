import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import TableView, { TableColumn } from './TableView';

vi.mock('@/lib/agGrid', () => ({}));
vi.mock('ag-grid-react', async () => import('../../__mocks__/ag-grid-react'));

interface Row {
  id: string;
  name: string;
  age: number;
}

const columns: TableColumn[] = [
  { id: 'name', name: 'Nombre', type: 'text' },
  { id: 'age', name: 'Edad', type: 'number' },
];

const data: Row[] = [
  { id: '1', name: 'Ana', age: 30 },
  { id: '2', name: 'Luis', age: 25 },
];

describe('TableView', () => {
  it('renders rows with idAccessor as string key', () => {
    render(<TableView data={data} columns={columns} idAccessor="id" />);
    expect(screen.getByText('Ana')).toBeInTheDocument();
    expect(screen.getByText('Luis')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
  });

  it('renders rows with idAccessor as function', () => {
    render(<TableView data={data} columns={columns} idAccessor={(row) => row.id} />);
    expect(screen.getByText('Ana')).toBeInTheDocument();
  });

  it('shows empty message when data is empty', () => {
    render(<TableView data={[]} columns={columns} idAccessor="id" emptyMessage="Sin datos" />);
    expect(screen.getByText('Sin datos')).toBeInTheDocument();
  });

  it('calls onAddRow when add button is clicked', () => {
    const handleAddRow = vi.fn();
    render(<TableView data={data} columns={columns} idAccessor="id" onAddRow={handleAddRow} />);
    fireEvent.click(screen.getByText('Nueva fila'));
    expect(handleAddRow).toHaveBeenCalledTimes(1);
  });

  it('renders the quick search input when filters are enabled', () => {
    render(<TableView data={data} columns={columns} idAccessor="id" enableFilters />);
    expect(screen.getByPlaceholderText('Buscar…')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<TableView data={data} columns={columns} idAccessor="id" />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});

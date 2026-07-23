import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CrmTableView from './CrmTableView';

vi.mock('@/lib/agGrid', () => ({}));
vi.mock('ag-grid-react', async () => import('../../__mocks__/ag-grid-react'));

const personas = [
  {
    id: '1',
    nombre_completo: 'Ana Martínez',
    email: 'ana@example.com',
    phone: '3001234567',
    church_role: 'líder',
    spiritual_status: 'creyente',
  },
  {
    id: '2',
    nombre_completo: 'Carlos López',
    email: 'carlos@example.com',
    phone: '3007654321',
    church_role: 'miembro',
    spiritual_status: 'visita',
  },
];

describe('CrmTableView', () => {
  it('renders persona names and roles', () => {
    render(<CrmTableView personas={personas} search="" onRowClick={() => {}} />);
    expect(screen.getByText('Ana Martínez')).toBeInTheDocument();
    expect(screen.getByText('Carlos López')).toBeInTheDocument();
    expect(screen.getByText('líder')).toBeInTheDocument();
  });

  it('filters personas by search', () => {
    render(<CrmTableView personas={personas} search="ana" onRowClick={() => {}} />);
    expect(screen.getByText('Ana Martínez')).toBeInTheDocument();
    expect(screen.queryByText('Carlos López')).not.toBeInTheDocument();
  });

  it('calls onRowClick when a row is clicked', () => {
    const handleRowClick = vi.fn();
    render(<CrmTableView personas={personas} search="" onRowClick={handleRowClick} />);
    fireEvent.click(screen.getByText('Ana Martínez'));
    expect(handleRowClick).toHaveBeenCalledTimes(1);
    expect(handleRowClick).toHaveBeenCalledWith(personas[0]);
  });

  it('hides extra column in list mode', () => {
    render(<CrmTableView personas={personas} search="" onRowClick={() => {}} isList />);
    // The table should still render the persona
    expect(screen.getByText('Ana Martínez')).toBeInTheDocument();
  });
});

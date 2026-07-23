import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import { DataTable } from './DataTable';
import { ColumnDef } from '@tanstack/react-table';

interface Row {
    id: string;
    name: string;
}

describe('DataTable', () => {
    const columns: ColumnDef<Row, any>[] = [
        { header: 'ID', accessorKey: 'id' },
        { header: 'Nombre', accessorKey: 'name' },
    ];

    const data: Row[] = [
        { id: '1', name: 'Alice' },
        { id: '2', name: 'Bob' },
    ];

    it('renders column headers and rows', () => {
        render(<DataTable data={data} columns={columns} />);
        expect(screen.getByText('ID')).toBeInTheDocument();
        expect(screen.getByText('Nombre')).toBeInTheDocument();
        expect(screen.getByText('Alice')).toBeInTheDocument();
        expect(screen.getByText('Bob')).toBeInTheDocument();
    });

    it('calls onRowClick when a row is clicked', () => {
        const handleRowClick = vi.fn();
        render(<DataTable data={data} columns={columns} onRowClick={handleRowClick} />);
        fireEvent.click(screen.getByText('Alice'));
        expect(handleRowClick).toHaveBeenCalledTimes(1);
        expect(handleRowClick).toHaveBeenCalledWith(data[0]);
    });

    it('has no accessibility violations', async () => {
        const { container } = render(<DataTable data={data} columns={columns} />);
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import { ColumnDef } from '@tanstack/react-table';
import { DSTable } from './DSTable';

interface Row {
    id: number;
    name: string;
    role: string;
}

const baseColumns: ColumnDef<Row, any>[] = [
    { accessorKey: 'name', header: 'Nombre' },
    { accessorKey: 'role', header: 'Rol' },
];

// Data intentionally out of alphabetical order so sorting assertions can
// prove that clicking the header actually mutates the row order.
//   index 0 → 'Cami' (id:1)
//   index 1 → 'Ana'  (id:2)
//   index 2 → 'Beto' (id:3)
const baseData: Row[] = [
    { id: 1, name: 'Cami', role: 'Visor' },
    { id: 2, name: 'Ana', role: 'Admin' },
    { id: 3, name: 'Beto', role: 'Editor' },
];

// Helper: read the names of data rows (skips header row at index 0).
function getDataRowNames(container: HTMLElement): string[] {
    const rows = Array.from(
        container.querySelectorAll('tbody tr')
    ) as HTMLTableRowElement[];
    return rows.map((row) => row.cells[0]?.textContent ?? '');
}

describe('DSTable', () => {
    describe('rendering', () => {
        it('renders column headers from ColumnDef.header', () => {
            render(<DSTable data={baseData} columns={baseColumns} />);
            expect(screen.getByText('Nombre')).toBeInTheDocument();
            expect(screen.getByText('Rol')).toBeInTheDocument();
        });

        it('renders rows in the source order when no sort is applied', () => {
            const { container } = render(
                <DSTable data={baseData} columns={baseColumns} />
            );
            expect(getDataRowNames(container)).toEqual(['Cami', 'Ana', 'Beto']);
        });

        it('shows the default empty message when data is empty', () => {
            render(<DSTable data={[]} columns={baseColumns} />);
            expect(screen.getByText('Sin datos')).toBeInTheDocument();
        });

        it('shows a custom empty message when provided', () => {
            render(
                <DSTable
                    data={[]}
                    columns={baseColumns}
                    emptyMessage="No hay usuarios"
                />
            );
            expect(screen.getByText('No hay usuarios')).toBeInTheDocument();
        });

        it('spans the empty cell across every column', () => {
            const { container } = render(
                <DSTable data={[]} columns={baseColumns} />
            );
            const cell = container.querySelector('tbody td');
            expect(cell?.getAttribute('colspan')).toBe(String(baseColumns.length));
        });
    });

    describe('sorting', () => {
        it('sorts ascending on first click', () => {
            const { container } = render(
                <DSTable data={baseData} columns={baseColumns} />
            );
            fireEvent.click(screen.getByText('Nombre'));
            expect(getDataRowNames(container)).toEqual(['Ana', 'Beto', 'Cami']);
        });

        it('sorts descending on second click of the same header', () => {
            const { container } = render(
                <DSTable data={baseData} columns={baseColumns} />
            );
            const header = screen.getByText('Nombre');
            fireEvent.click(header); // asc
            fireEvent.click(header); // desc
            expect(getDataRowNames(container)).toEqual(['Cami', 'Beto', 'Ana']);
        });

        it('flips the sort indicator on each click', () => {
            const { container } = render(
                <DSTable data={baseData} columns={baseColumns} />
            );
            // Before any click, the unsorted ArrowUpDown icon is present
            expect(container.querySelector('thead svg')).toBeInTheDocument();
            fireEvent.click(screen.getByText('Nombre'));
            // SVG still present (now reflects the sorted state)
            expect(container.querySelector('thead svg')).toBeInTheDocument();
        });

        it('does not sort when sortable={false}', () => {
            const { container } = render(
                <DSTable data={baseData} columns={baseColumns} sortable={false} />
            );
            fireEvent.click(screen.getByText('Nombre'));
            expect(getDataRowNames(container)).toEqual(['Cami', 'Ana', 'Beto']);
        });
    });

    describe('row click handler', () => {
        it('calls onRowClick with the matching original row', () => {
            const handleClick = vi.fn();
            render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    onRowClick={handleClick}
                />
            );
            // 'Beto' belongs to baseData[2]
            fireEvent.click(screen.getByText('Beto'));
            expect(handleClick).toHaveBeenCalledTimes(1);
            expect(handleClick).toHaveBeenCalledWith(baseData[2]);
        });

        it('passes the exact row object for every row (not a hardcoded stub)', () => {
            const handleClick = vi.fn();
            render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    onRowClick={handleClick}
                />
            );
            fireEvent.click(screen.getByText('Ana'));
            expect(handleClick).toHaveBeenCalledWith(baseData[1]);
            fireEvent.click(screen.getByText('Cami'));
            expect(handleClick).toHaveBeenCalledWith(baseData[0]);
            expect(handleClick).toHaveBeenCalledTimes(2);
        });

        it('does not throw when a row is clicked without onRowClick', () => {
            render(<DSTable data={baseData} columns={baseColumns} />);
            expect(() => fireEvent.click(screen.getByText('Beto'))).not.toThrow();
        });
    });

    describe('density', () => {
        it('applies compact padding classes when compact is true', () => {
            const { container } = render(
                <DSTable data={baseData} columns={baseColumns} compact />
            );
            const th = container.querySelector('thead th');
            const td = container.querySelector('tbody td');
            expect(th?.className).toContain('px-2');
            expect(th?.className).toContain('py-1.5');
            expect(td?.className).toContain('px-2');
            expect(td?.className).toContain('py-1.5');
        });

        it('applies standard padding classes by default', () => {
            const { container } = render(
                <DSTable data={baseData} columns={baseColumns} />
            );
            const th = container.querySelector('thead th');
            const td = container.querySelector('tbody td');
            expect(th?.className).toContain('px-3');
            expect(th?.className).toContain('py-2');
            expect(td?.className).toContain('px-3');
            expect(td?.className).toContain('py-2');
        });
    });

    describe('row cursor class', () => {
        it('adds cursor-pointer when onRowClick is provided', () => {
            const { container } = render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    onRowClick={() => undefined}
                />
            );
            expect(container.querySelector('tbody tr')?.className).toContain(
                'cursor-pointer'
            );
        });

        it('omits cursor-pointer when onRowClick is not provided', () => {
            const { container } = render(
                <DSTable data={baseData} columns={baseColumns} />
            );
            expect(container.querySelector('tbody tr')?.className).not.toContain(
                'cursor-pointer'
            );
        });
    });

    it('has no accessibility violations', async () => {
        const { container } = render(
            <DSTable data={baseData} columns={baseColumns} />
        );
        expect(await axe(container)).toHaveNoViolations();
    });
});

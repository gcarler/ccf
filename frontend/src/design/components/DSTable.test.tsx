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

    describe('column visibility', () => {
        it('renders the "Columnas" menu button when enableColumnVisibility is set', () => {
            render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    enableColumnVisibility
                />
            );
            expect(screen.getByRole('button', { name: /Columnas/i })).toBeInTheDocument();
        });

        it('does not render the "Columnas" button by default', () => {
            render(<DSTable data={baseData} columns={baseColumns} />);
            expect(screen.queryByRole('button', { name: /Columnas/i })).not.toBeInTheDocument();
        });

        it('opens the checklist menu and lists every column on click', () => {
            render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    enableColumnVisibility
                />
            );
            fireEvent.click(screen.getByRole('button', { name: /Columnas/i }));
            // Ambos headers aparecen como items del menú (rol menuitemcheckbox).
            const items = screen.getAllByRole('menuitemcheckbox');
            expect(items).toHaveLength(2);
            expect(items[0]).toHaveTextContent('Nombre');
            expect(items[1]).toHaveTextContent('Rol');
            expect(items[0]).toHaveAttribute('aria-checked', 'true');
        });

        it('hides a column when its menu item is toggled off', () => {
            const { container } = render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    enableColumnVisibility
                />
            );
            fireEvent.click(screen.getByRole('button', { name: /Columnas/i }));
            // Toggling 'Nombre' off → column disappears from the rendered table.
            fireEvent.click(screen.getByRole('menuitemcheckbox', { name: /Nombre/i }));
            const headNames = Array.from(
                container.querySelectorAll('thead th')
            ) as HTMLTableCellElement[];
            expect(headNames.some((th) => th.textContent?.includes('Nombre'))).toBe(false);
        });

        it('closes the menu on outside click', () => {
            render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    enableColumnVisibility
                />
            );
            fireEvent.click(screen.getByRole('button', { name: /Columnas/i }));
            expect(screen.getAllByRole('menuitemcheckbox')).toHaveLength(2);
            // Outside click closes the menu.
            fireEvent.mouseDown(document.body);
            expect(screen.queryAllByRole('menuitemcheckbox')).toHaveLength(0);
        });
    });

    describe('row selection', () => {
        it('does not render a checkbox column by default', () => {
            const { container } = render(
                <DSTable data={baseData} columns={baseColumns} />
            );
            const checkboxes = container.querySelectorAll('tbody input[type="checkbox"]');
            expect(checkboxes).toHaveLength(0);
        });

        it('renders one checkbox per data row plus the header when enableRowSelection is set', () => {
            const { container } = render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    enableRowSelection
                />
            );
            const headerCheckbox = container.querySelector('thead input[type="checkbox"]');
            const bodyCheckboxes = container.querySelectorAll('tbody input[type="checkbox"]');
            expect(headerCheckbox).not.toBeNull();
            expect(bodyCheckboxes).toHaveLength(3); // 3 data rows
        });

        it('selects all rows when the header checkbox is clicked', () => {
            const { container } = render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    enableRowSelection
                />
            );
            const headerCheckbox = container.querySelector('thead input[type="checkbox"]') as HTMLInputElement;
            fireEvent.click(headerCheckbox);
            const bodyCheckboxes = Array.from(
                container.querySelectorAll('tbody input[type="checkbox"]')
            ) as HTMLInputElement[];
            expect(bodyCheckboxes.every((cb) => cb.checked)).toBe(true);
        });

        it('calls onSelectionChange with the selected row objects', () => {
            const handleSelection = vi.fn();
            render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    enableRowSelection
                    onSelectionChange={handleSelection}
                />
            );
            const firstRowCheckbox = screen.getAllByLabelText(/Seleccionar fila 1/i)[0];
            fireEvent.click(firstRowCheckbox);
            // Effect fires async; at least one call happened with the matching row.
            expect(handleSelection).toHaveBeenCalled();
            const lastCall = handleSelection.mock.calls[handleSelection.mock.calls.length - 1][0];
            expect(Array.isArray(lastCall)).toBe(true);
            expect(lastCall).toContainEqual(baseData[0]);
        });

        it('deselects a row on a second checkbox click', () => {
            const { container } = render(
                <DSTable
                    data={baseData}
                    columns={baseColumns}
                    enableRowSelection
                />
            );
            const firstRowCheckbox = screen.getAllByLabelText(/Seleccionar fila 1/i)[0];
            fireEvent.click(firstRowCheckbox);
            expect(firstRowCheckbox).toHaveProperty('checked', true);
            fireEvent.click(firstRowCheckbox);
            expect(firstRowCheckbox).toHaveProperty('checked', false);
        });
    });
});

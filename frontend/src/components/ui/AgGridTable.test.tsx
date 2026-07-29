import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import AgGridTable, { ColDef } from './AgGridTable';

interface MockAgGridProps {
  density?: string;
  rowData?: unknown[];
}

vi.mock('ag-grid-react', () => ({
  AgGridReact: (props: MockAgGridProps) => (
    <div data-testid="ag-grid-mock" data-density={props.density}>
      Grid Container ({props.rowData?.length || 0} rows)
    </div>
  ),
}));

interface RowData {
  id: number;
  name: string;
}

describe('AgGridTable component', () => {
  it('renders ag-grid wrapper with provided row data', () => {
    const rowData: RowData[] = [
      { id: 1, name: 'Item 1' },
      { id: 2, name: 'Item 2' },
    ];

    const columnDefs: ColDef<RowData>[] = [
      { field: 'id', headerName: 'ID' },
      { field: 'name', headerName: 'Name' },
    ];

    const { getByTestId, getByText } = render(
      <AgGridTable rowData={rowData} columnDefs={columnDefs} />
    );

    expect(getByTestId('ag-grid-mock')).toBeInTheDocument();
    expect(getByText('Grid Container (2 rows)')).toBeInTheDocument();
  });
});

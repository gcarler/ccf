import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import AgGridTable from './AgGridTable';

vi.mock('ag-grid-react', () => ({
  AgGridReact: (props: any) => (
    <div data-testid="ag-grid-mock" data-density={props.density}>
      Grid Container ({props.rowData?.length || 0} rows)
    </div>
  ),
}));

describe('AgGridTable component', () => {
  it('renders ag-grid wrapper with provided row data', () => {
    const rowData = [
      { id: 1, name: 'Item 1' },
      { id: 2, name: 'Item 2' },
    ];

    const columnDefs = [
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

import React from 'react';

interface ColDef {
  field?: string;
  headerName?: string;
  name?: string;
  id?: string;
  cellRenderer?: React.ComponentType<any>;
  [key: string]: any;
}

interface AgGridReactProps {
  rowData?: Record<string, unknown>[];
  columnDefs?: ColDef[];
  onRowClicked?: (event: { data: Record<string, unknown> }) => void;
  onRowDoubleClicked?: (event: { data: Record<string, unknown> }) => void;
  getRowId?: (params: { data: Record<string, unknown> }) => string;
  context?: any;
  [key: string]: any;
}

const MockAgGridReact = React.forwardRef<HTMLTableElement, AgGridReactProps>(
  ({ rowData = [], columnDefs = [], onRowClicked, onRowDoubleClicked, context }, ref) => {
    return (
      <table
        ref={ref}
        role="grid"
        aria-label="Datos de la tabla"
        className="ag-grid-mock w-full"
      >
        <thead>
          <tr>
            {columnDefs.map((col: ColDef, colIndex: number) => (
              <th
                scope="col"
                key={col.field || col.headerName || col.name || col.id || `col-${colIndex}`}
                className="text-left px-3 py-2 text-xs font-semibold"
              >
                {(col.headerName ?? col.name ?? col.field) || <span className="sr-only">Select</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rowData.map((row: Record<string, unknown>, rowIndex: number) => {
            const rowId =
              typeof row.id === 'string' || typeof row.id === 'number'
                ? String(row.id)
                : `row-${rowIndex}`;
            return (
              <tr
                key={rowId}
                onClick={() => onRowClicked?.({ data: row })}
                onDoubleClick={() => onRowDoubleClicked?.({ data: row })}
                className="cursor-pointer"
              >
                {columnDefs.map((col: ColDef, colIndex: number) => {
                  const value = col.field ? (row[col.field] as unknown) : col.id ? (row[col.id] as unknown) : undefined;
                  const Renderer = col.cellRenderer;
                  return (
                    <td
                      key={col.field || col.headerName || `cell-${colIndex}`}
                      className="px-3 py-2 text-sm"
                    >
                      {Renderer ? (
                        <Renderer
                          value={value}
                          data={row}
                          colDef={col}
                          context={context}
                        />
                      ) : (
                        String(value ?? '')
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }
);

MockAgGridReact.displayName = 'AgGridReact';

export { MockAgGridReact as AgGridReact };

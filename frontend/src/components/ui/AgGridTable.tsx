'use client';

import { forwardRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { AgGridReact as AgGridReactType } from 'ag-grid-react';
import '@/lib/agGrid';
import { useAgGridTheme, type AgGridDensity } from '@/design/agGridTheme';

export type {
  ColDef,
  GetRowIdParams,
  ICellRendererParams,
  ICellEditorParams,
  CellDoubleClickedEvent,
  IsFullWidthRowParams,
  RowHeightParams,
  CellValueChangedEvent,
  IDatasource,
  IGetRowsParams,
  ValueFormatterParams,
  ValueGetterParams,
  GridReadyEvent,
} from 'ag-grid-community';

/** Ref type forwarded by the wrapper, avoids direct ag-grid-react imports. */
export type AgGridTableRef = AgGridReactType;

export interface AgGridTableProps<TData = unknown>
  extends Omit<React.ComponentProps<typeof AgGridReact<TData>>, 'theme'> {
  /** Row density preset. Defaults to "default" (40px). */
  density?: AgGridDensity;
}

interface AgGridTableComponent {
  <TData = unknown>(
    props: AgGridTableProps<TData> & { ref?: React.Ref<AgGridReactType> }
  ): React.ReactElement | null;
}

function AgGridTableInner<TData = unknown>(
  { density = 'default', ...props }: AgGridTableProps<TData>,
  ref: React.Ref<AgGridReactType>
) {
  const theme = useAgGridTheme(density);
  return <AgGridReact<TData> ref={ref} theme={theme} {...props} />;
}

/**
 * Design-system wrapper around AgGridReact.
 * - Applies the centralized CCF theme (light/dark) automatically.
 * - Ensures AgGrid modules are registered once.
 * - Forwards refs so callers can keep using gridRef as before.
 * - Preserves the generic TData type for typed callbacks.
 *
 * Import AgGrid types from this module instead of `ag-grid-community`
 * to keep the design-system boundary clean. Example:
 * `import AgGridTable, { ColDef, type AgGridTableRef } from '@/components/ui/AgGridTable';`
 */
const AgGridTable: AgGridTableComponent = forwardRef(AgGridTableInner) as unknown as AgGridTableComponent;

export default AgGridTable;

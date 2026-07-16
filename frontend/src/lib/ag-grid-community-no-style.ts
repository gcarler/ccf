import type * as AgGridCommunity from 'ag-grid-community';

// Next.js blocks the package's private noStyle entrypoint through exports,
// so we load the public build file directly and re-export the symbols we use.
// eslint-disable-next-line @typescript-eslint/no-var-requires
const agGridNoStyle = require('../../node_modules/ag-grid-community/dist/ag-grid-community.noStyle.js') as typeof AgGridCommunity;

export const { AllCommunityModule, ModuleRegistry, themeQuartz } = agGridNoStyle;
export type {
  CellValueChangedEvent,
  ColDef,
  GetRowIdParams,
  IDatasource,
  IGetRowsParams,
  ICellRendererParams,
  ValueFormatterParams,
  ValueGetterParams,
} from 'ag-grid-community';

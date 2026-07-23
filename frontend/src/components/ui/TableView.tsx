"use client";

import { evaluateFormula } from "@/lib/formulaEngine";
import "@/lib/agGrid";
import {
CellValueChangedEvent,
ColDef,
GetRowIdParams,
IDatasource,
IGetRowsParams,
type ValueFormatterParams,
type ValueGetterParams,
themeQuartz
} from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import clsx from "clsx";
import {
Download,
Plus,
Search,
Trash2,
X
} from "lucide-react";
import React,{ useCallback,useMemo,useRef,useState } from "react";

// ─── Types (same public API as before) ───────────────────────────────────────

export type TableCellType =
  | "text" | "number" | "select" | "multiSelect"
  | "date" | "datetime" | "checkbox" | "rating"
  | "phone" | "email" | "url" | "user"
  | "relation" | "attachment" | "formula" | "progress";

export interface TableColumn {
  id: string;
  name: string;
  type: TableCellType;
  width?: number;
  frozen?: boolean;
  options?: { label: string; value: string; color?: string }[];
  format?: string;
  required?: boolean;
  placeholder?: string;
  formula?: string;
}

export interface TableAction {
  label: string;
  icon?: React.ReactNode;
  onClick: (selectedRows: any[]) => void;
  danger?: boolean;
}

export interface TableViewProps<T = any> {
  data: T[];
  columns: TableColumn[];
  idAccessor: keyof T | ((row: T) => string);
  onChange?: (rowId: string, columnId: string, value: any) => void;
  onAddRow?: () => T;
  onDeleteRows?: (rowIds: string[]) => void;
  actions?: TableAction[];
  storageKey?: string;
  emptyMessage?: string;
  rowHeight?: number;
  enableBulkEdit?: boolean;
  enableGrouping?: boolean;
  enableFilters?: boolean;
  /** Server-side mode: AG Grid InfiniteRowModel + API pagination */
  serverSide?: {
    /** Called on every page/sort/filter change. Return { items, total }. */
    getRows: (params: {
      offset: number;
      limit: number;
      sortBy?: string;
      sortDir?: "asc" | "desc";
      search?: string;
    }) => Promise<{ items: T[]; total: number }>;
    pageSize?: number;
  };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CELL_COLORS: Record<string, string> = {
  red:    "hsl(var(--danger))", orange: "hsl(var(--warning))", yellow: "hsl(38 92% 50%)",
  green:  "hsl(var(--success))", blue:   "hsl(var(--primary))", sky: "hsl(197 98% 37%)",
  pink:   "hsl(336 80% 58%)", gray:   "hsl(var(--text-secondary))",
};

function SelectRenderer({ value, colDef }: any) {
  const opts = colDef.cellEditorParams?.values as { label: string; value: string; color?: string }[] | undefined;
  const opt = opts?.find((o) => o.value === value);
  const color = opt?.color ? (CELL_COLORS[opt.color] ?? opt.color) : undefined;
  if (!opt) return <span className="text-[hsl(var(--text-secondary))] text-xs">—</span>;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      {color && <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />}
      {opt.label}
    </span>
  );
}

function CheckboxRenderer({ value, node, column }: any) {
  return (
    <input
      type="checkbox"
      checked={!!value}
      onChange={(e) => {
        node.setDataValue(column.getColId(), e.target.checked);
      }}
      className="w-4 h-4 rounded cursor-pointer accent-sky-600"
    />
  );
}

function RatingRenderer({ value }: any) {
  const n = Math.round(Number(value) || 0);
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={clsx("text-sm", i <= n ? "text-yellow-400" : "text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-primary))]")}>★</span>
      ))}
    </span>
  );
}

function ProgressRenderer({ value }: any) {
  const pct = Math.min(100, Math.max(0, Number(value) || 0));
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-1.5 bg-[hsl(var(--surface-3))] dark:bg-[hsl(var(--surface-2))] rounded-full overflow-hidden">
        <div className="h-full bg-[hsl(var(--primary))] rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-[hsl(var(--text-secondary))] w-8 text-right">{pct}%</span>
    </div>
  );
}

// ─── Column mapper ────────────────────────────────────────────────────────────

function toColDef(col: TableColumn): ColDef {
  const base: ColDef = {
    field: col.id,
    headerName: col.name,
    width: col.width ?? 160,
    minWidth: 80,
    resizable: true,
    sortable: true,
    filter: true,
    editable: col.type !== "formula",
    pinned: col.frozen ? "left" : undefined,
  };

  switch (col.type) {
    case "number":
      return {
        ...base,
        cellDataType: "number",
        cellEditor: "agNumberCellEditor",
        valueFormatter: ({ value }: ValueFormatterParams) => {
          if (value === null || value === undefined) return "";
          if (col.format === "currency") return `$${Number(value).toLocaleString()}`;
          if (col.format === "percent") return `${value}%`;
          return String(value);
        },
      };

    case "select":
      return {
        ...base,
        cellEditor: "agSelectCellEditor",
        cellEditorParams: { values: col.options ?? [] },
        cellRenderer: SelectRenderer,
      };

    case "date":
      return { ...base, cellDataType: "dateString", cellEditor: "agDateStringCellEditor" };

    case "datetime":
      return { ...base, cellDataType: "dateString", cellEditor: "agDateStringCellEditor" };

    case "checkbox":
      return { ...base, cellDataType: "boolean", cellRenderer: CheckboxRenderer, editable: false };

    case "rating":
      return { ...base, cellRenderer: RatingRenderer, editable: false };

    case "progress":
      return { ...base, cellRenderer: ProgressRenderer, editable: false };

    case "formula":
      return {
        ...base,
        editable: false,
        valueGetter: ({ data }: ValueGetterParams) => {
          if (!data || !col.formula) return "";
          try { return evaluateFormula(col.formula, data); } catch { return ""; }
        },
      };

    case "email":
      return {
        ...base,
        cellRenderer: ({ value }: { value: unknown }) => {
          const email = typeof value === "string" || typeof value === "number" ? String(value) : "";
          return email
            ? <a href={`mailto:${email}`} className="text-[hsl(var(--primary))] hover:underline text-xs" onClick={(e) => e.stopPropagation()}>{email}</a>
            : null;
        },
      };

    case "url":
      return {
        ...base,
        cellRenderer: ({ value }: { value: unknown }) => {
          const url = typeof value === "string" || typeof value === "number" ? String(value) : "";
          return url
            ? <a href={url} target="_blank" rel="noopener noreferrer" className="text-[hsl(var(--primary))] hover:underline text-xs truncate block" onClick={(e) => e.stopPropagation()}>{url}</a>
            : null;
        },
      };

    default:
      return base;
  }
}

// ─── Light / Dark theme ───────────────────────────────────────────────────────

const lightTheme = themeQuartz.withParams({
  fontFamily: "inherit",
  fontSize: 12,
  rowHeight: 36,
  headerHeight: 36,
  backgroundColor: "#ffffff",
  foregroundColor: "#1e293b",
  borderColor: "#e2e8f0",
  oddRowBackgroundColor: "#f8fafc",
  headerBackgroundColor: "#f1f5f9",
  headerTextColor: "#475569",
  selectedRowBackgroundColor: "#eef2ff",
  accentColor: "#6366f1",
  rangeSelectionBorderColor: "#6366f1",
  cellHorizontalPaddingScale: 0.8,
});

const darkTheme = themeQuartz.withParams({
  fontFamily: "inherit",
  fontSize: 12,
  rowHeight: 36,
  headerHeight: 36,
  backgroundColor: "rgb(15 23 42)",
  foregroundColor: "#e2e8f0",
  borderColor: "rgba(255,255,255,0.08)",
  oddRowBackgroundColor: "rgba(255,255,255,0.02)",
  headerBackgroundColor: "rgba(255,255,255,0.04)",
  headerTextColor: "#94a3b8",
  selectedRowBackgroundColor: "rgba(99,102,241,0.15)",
  accentColor: "#6366f1",
  rangeSelectionBorderColor: "#6366f1",
  cellHorizontalPaddingScale: 0.8,
});

// ─── Main Component ───────────────────────────────────────────────────────────

export default function TableView<T extends Record<string, any>>({
  data,
  columns,
  idAccessor,
  onChange,
  onAddRow,
  onDeleteRows,
  actions,
  emptyMessage = "Sin registros",
  rowHeight = 36,
  enableFilters = true,
  serverSide,
}: TableViewProps<T>) {
  const gridRef = useRef<AgGridReact>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [quickFilter, setQuickFilter] = useState("");
  const [isDark, setIsDark] = useState(false);
  // Server-side search debounce
  const serverSearchRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Detect dark mode
  React.useEffect(() => {
    const check = () => setIsDark(document.documentElement.classList.contains("dark"));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  const getId = useCallback(
    (row: T): string => {
      if (typeof idAccessor === "function") return String(idAccessor(row));
      return String(row[idAccessor]);
    },
    [idAccessor]
  );

  const colDefs = useMemo<ColDef[]>(() => {
    const defs: ColDef[] = [
      {
        headerCheckboxSelection: true,
        checkboxSelection: true,
        width: 40,
        minWidth: 40,
        maxWidth: 40,
        resizable: false,
        sortable: false,
        filter: false,
        pinned: "left",
        headerName: "",
        suppressHeaderMenuButton: true,
      },
      ...columns.map((c) => toColDef(c)),
    ];
    return defs;
  }, [columns]);

  const defaultColDef = useMemo<ColDef>(() => ({
    resizable: true,
    sortable: true,
    filter: enableFilters,
    minWidth: 80,
  }), [enableFilters]);

  const getRowId = useCallback((params: GetRowIdParams<T>) => getId(params.data), [getId]);

  const onCellValueChanged = useCallback(
    (e: CellValueChangedEvent<T>) => {
      if (!onChange) return;
      const rowId = getId(e.data);
      onChange(rowId, e.column.getColId(), e.newValue);
    },
    [onChange, getId]
  );

  const onSelectionChanged = useCallback(() => {
    const api = gridRef.current?.api;
    if (!api) return;
    const rows = api.getSelectedRows() as T[];
    setSelectedIds(rows.map(getId));
  }, [getId]);

  const handleAddRow = useCallback(() => {
    if (!onAddRow) return;
    onAddRow();
  }, [onAddRow]);

  const handleDeleteSelected = useCallback(() => {
    if (!onDeleteRows || selectedIds.length === 0) return;
    onDeleteRows(selectedIds);
    setSelectedIds([]);
  }, [onDeleteRows, selectedIds]);

  const handleExport = useCallback(() => {
    gridRef.current?.api?.exportDataAsCsv();
  }, []);

  // Server-side datasource
  const serverSideRef = useRef(serverSide);
  React.useEffect(() => { serverSideRef.current = serverSide; }, [serverSide]);
  const searchRef = useRef(quickFilter);
  React.useEffect(() => { searchRef.current = quickFilter; }, [quickFilter]);

  const datasource = useMemo<IDatasource | undefined>(() => {
    if (!serverSide) return undefined;
    return {
      getRows: (params: IGetRowsParams) => {
        const offset = params.startRow;
        const limit  = params.endRow - params.startRow;
        const sortBy   = params.sortModel[0]?.colId;
        const sortDir  = (params.sortModel[0]?.sort ?? "asc") as "asc" | "desc";
        const search   = searchRef.current || undefined;
        serverSideRef.current!.getRows({ offset, limit, sortBy, sortDir, search })
          .then(({ items, total }) => params.successCallback(items, total))
          .catch(() => params.failCallback());
      },
      rowCount: undefined,
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [!!serverSide]);

  const theme = isDark ? darkTheme : lightTheme;

  return (
    <div className="flex min-w-0 flex-col h-full gap-2">
      {/* Toolbar */}
      <div className="flex min-w-0 items-center gap-2 flex-wrap">
        {enableFilters && (
          <div className="relative flex-1 min-w-[min(100%,180px)] max-w-xs">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
            <input
              value={quickFilter}
              onChange={(e) => {
                setQuickFilter(e.target.value);
                if (serverSide) {
                  // Debounce server-side search: reset datasource after 300ms
                  if (serverSearchRef.current) clearTimeout(serverSearchRef.current);
                  serverSearchRef.current = setTimeout(() => {
                    searchRef.current = e.target.value;
                    gridRef.current?.api?.setGridOption("datasource", datasource!);
                  }, 300);
                } else {
                  gridRef.current?.api?.setGridOption("quickFilterText", e.target.value);
                }
              }}
              placeholder="Buscar…"
              className="w-full pl-7 pr-7 py-1.5 text-xs border border-[hsl(var(--border))] dark:border-white/10 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] outline-none focus:ring-1 focus:ring-sky-400"
            />
            {quickFilter && (
              <button onClick={() => {
                setQuickFilter("");
                if (serverSide) { searchRef.current = ""; gridRef.current?.api?.setGridOption("datasource", datasource!); }
                else { gridRef.current?.api?.setGridOption("quickFilterText", ""); }
              }} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]">
                <X size={11} />
              </button>
            )}
          </div>
        )}

        <div className="flex min-w-0 items-center gap-1 ml-0 sm:ml-auto overflow-x-auto">
          {selectedIds.length > 0 && (
            <>
              <span className="text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mr-1">{selectedIds.length} seleccionados</span>
              {actions?.map((a, i) => (
                <button key={i} onClick={() => a.onClick(selectedIds as any)} className={clsx("flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg transition-colors", a.danger ? "bg-red-50 dark:bg-red-900/20 text-[hsl(var(--destructive))] hover:bg-red-100" : "bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] hover:bg-blue-100")}>
                  {a.icon}{a.label}
                </button>
              ))}
              {onDeleteRows && (
                <button onClick={handleDeleteSelected} className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-red-50 dark:bg-red-900/20 text-[hsl(var(--destructive))] hover:bg-red-100 transition-colors">
                  <Trash2 size={12} /> Eliminar
                </button>
              )}
            </>
          )}
          <button onClick={handleExport} title="Exportar CSV" className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-colors">
            <Download size={14} />
          </button>
          {onAddRow && (
            <button onClick={handleAddRow} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.85)] text-white transition-colors">
              <Plus size={13} /> Nueva fila
            </button>
          )}
        </div>
      </div>

      {/* Grid */}
      <div className="flex-1 min-w-0 min-h-[300px] rounded-xl overflow-hidden border border-[hsl(var(--border))] dark:border-white/10">
        {!serverSide && data.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))]">
            {emptyMessage}
          </div>
        ) : serverSide ? (
          /* ── Server-side InfiniteRowModel ── */
          <AgGridReact<any>
            ref={gridRef as any}
            theme={theme}
            rowModelType="infinite"
            datasource={datasource}
            cacheBlockSize={serverSide.pageSize ?? 100}
            maxBlocksInCache={5}
            columnDefs={colDefs}
            defaultColDef={{ ...(defaultColDef as ColDef<any>), filter: false }}
            rowHeight={rowHeight}
            onSortChanged={() => {
              // Refresh cache to re-request from row 0 with new sort
              gridRef.current?.api?.refreshInfiniteCache();
            }}
            animateRows={false}
            suppressMovableColumns={false}
            enableCellTextSelection
          />
        ) : (
          /* ── Client-side ── */
          <AgGridReact<T>
            ref={gridRef}
            theme={theme}
            rowData={data}
            columnDefs={colDefs}
            defaultColDef={defaultColDef}
            getRowId={getRowId}
            rowSelection={{ mode: "multiRow", checkboxes: false, headerCheckbox: true, enableSelectionWithoutKeys: true }}
            onSelectionChanged={onSelectionChanged}
            onCellValueChanged={onCellValueChanged}
            rowHeight={rowHeight}
            animateRows
            suppressMovableColumns={false}
            enableCellTextSelection
            ensureDomOrder
          />
        )}
      </div>
    </div>
  );
}

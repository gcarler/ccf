"use client";

import React, { useCallback, useMemo, useRef, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeQuartz,
  ColDef,
  CellValueChangedEvent,
  GridReadyEvent,
  GetRowIdParams,
  IRowNode,
  GridApi,
} from "ag-grid-community";
import {
  Plus, Trash2, Download, Filter, Search, X,
} from "lucide-react";
import clsx from "clsx";
import { evaluateFormula } from "@/lib/formulaEngine";

ModuleRegistry.registerModules([AllCommunityModule]);

// ─── Types (same public API as before) ───────────────────────────────────────

export type TableCellType =
  | "text" | "number" | "select" | "multiSelect"
  | "date" | "datetime" | "checkbox" | "rating"
  | "phone" | "email" | "url" | "user"
  | "relation" | "attachment" | "formula" | "progress";

export interface TableColumn<T = any> {
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
  columns: TableColumn<T>[];
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
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CELL_COLORS: Record<string, string> = {
  red:    "#ef4444", orange: "#f97316", yellow: "#eab308",
  green:  "#22c55e", blue:   "#3b82f6", purple: "#a855f7",
  pink:   "#ec4899", gray:   "#6b7280",
};

function SelectRenderer({ value, colDef }: any) {
  const opts = colDef.cellEditorParams?.values as { label: string; value: string; color?: string }[] | undefined;
  const opt = opts?.find((o) => o.value === value);
  const color = opt?.color ? (CELL_COLORS[opt.color] ?? opt.color) : undefined;
  if (!opt) return <span className="text-slate-300 text-xs">—</span>;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium">
      {color && <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />}
      {opt.label}
    </span>
  );
}

function CheckboxRenderer({ value, node, column, api }: any) {
  return (
    <input
      type="checkbox"
      checked={!!value}
      onChange={(e) => {
        node.setDataValue(column.getColId(), e.target.checked);
      }}
      className="w-4 h-4 rounded cursor-pointer accent-indigo-600"
    />
  );
}

function RatingRenderer({ value }: any) {
  const n = Math.round(Number(value) || 0);
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={clsx("text-sm", i <= n ? "text-yellow-400" : "text-slate-200 dark:text-slate-700")}>★</span>
      ))}
    </span>
  );
}

function ProgressRenderer({ value }: any) {
  const pct = Math.min(100, Math.max(0, Number(value) || 0));
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-500 w-8 text-right">{pct}%</span>
    </div>
  );
}

// ─── Column mapper ────────────────────────────────────────────────────────────

function toColDef(col: TableColumn, allData: any[]): ColDef {
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
        valueFormatter: ({ value }) => {
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
        valueGetter: ({ data }) => {
          if (!data || !col.formula) return "";
          try { return evaluateFormula(col.formula, data, allData); } catch { return ""; }
        },
      };

    case "email":
      return {
        ...base,
        cellRenderer: ({ value }: any) =>
          value ? <a href={`mailto:${value}`} className="text-indigo-500 hover:underline text-xs" onClick={(e) => e.stopPropagation()}>{value}</a> : null,
      };

    case "url":
      return {
        ...base,
        cellRenderer: ({ value }: any) =>
          value ? <a href={value} target="_blank" rel="noopener noreferrer" className="text-indigo-500 hover:underline text-xs truncate block" onClick={(e) => e.stopPropagation()}>{value}</a> : null,
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
}: TableViewProps<T>) {
  const gridRef = useRef<AgGridReact>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [quickFilter, setQuickFilter] = useState("");
  const [isDark, setIsDark] = useState(false);

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
      ...columns.map((c) => toColDef(c, data)),
    ];
    return defs;
  }, [columns, data]);

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

  const theme = isDark ? darkTheme : lightTheme;

  return (
    <div className="flex flex-col h-full gap-2">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        {enableFilters && (
          <div className="relative flex-1 min-w-[180px] max-w-xs">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={quickFilter}
              onChange={(e) => {
                setQuickFilter(e.target.value);
                gridRef.current?.api?.setGridOption("quickFilterText", e.target.value);
              }}
              placeholder="Buscar…"
              className="w-full pl-7 pr-7 py-1.5 text-xs border border-slate-200 dark:border-white/10 rounded-lg bg-white dark:bg-white/5 text-slate-700 dark:text-slate-200 placeholder-slate-400 outline-none focus:ring-1 focus:ring-indigo-400"
            />
            {quickFilter && (
              <button onClick={() => { setQuickFilter(""); gridRef.current?.api?.setGridOption("quickFilterText", ""); }} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <X size={11} />
              </button>
            )}
          </div>
        )}

        <div className="flex items-center gap-1 ml-auto">
          {selectedIds.length > 0 && (
            <>
              <span className="text-xs text-slate-500 dark:text-slate-400 mr-1">{selectedIds.length} seleccionados</span>
              {actions?.map((a, i) => (
                <button key={i} onClick={() => a.onClick(selectedIds as any)} className={clsx("flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg transition-colors", a.danger ? "bg-red-50 dark:bg-red-900/20 text-red-600 hover:bg-red-100" : "bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 hover:bg-indigo-100")}>
                  {a.icon}{a.label}
                </button>
              ))}
              {onDeleteRows && (
                <button onClick={handleDeleteSelected} className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 hover:bg-red-100 transition-colors">
                  <Trash2 size={12} /> Eliminar
                </button>
              )}
            </>
          )}
          <button onClick={handleExport} title="Exportar CSV" className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
            <Download size={14} />
          </button>
          {onAddRow && (
            <button onClick={handleAddRow} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors">
              <Plus size={13} /> Nueva fila
            </button>
          )}
        </div>
      </div>

      {/* Grid */}
      <div className="flex-1 min-h-[300px] rounded-xl overflow-hidden border border-slate-200 dark:border-white/10">
        {data.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sm text-slate-400 dark:text-slate-500 bg-white dark:bg-slate-900">
            {emptyMessage}
          </div>
        ) : (
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

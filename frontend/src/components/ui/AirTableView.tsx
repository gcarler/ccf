"use client";

import React, { useState, useCallback, useMemo, useRef, useEffect } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getGroupedRowModel,
  getExpandedRowModel,
  flexRender,
  ColumnDef,
  ColumnResizeMode,
  SortingState,
  ColumnFiltersState,
  GroupingState,
  ExpandedState,
  Row,
  Cell,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  ChevronDown, ChevronRight, GripVertical, Plus, Search,
  Filter, Columns, Settings, Undo2, Redo2, Trash2, Copy,
  MoreHorizontal, X, ChevronLeft, ChevronRight as ChevronRightIcon,
  ArrowUpDown, ArrowUp, ArrowDown, GripHorizontal, Download,
  Keyboard, ClipboardPaste,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import { DSBadge } from "@/design";

// ─── Types ──────────────────────────────────────────────────────────────────────

export type AirTableCellType =
  | "text" | "number" | "select" | "multiSelect"
  | "date" | "datetime" | "checkbox" | "rating"
  | "phone" | "email" | "url" | "user"
  | "relation" | "attachment" | "formula" | "progress";

export interface AirTableColumn<T = any> {
  id: string;
  name: string;
  type: AirTableCellType;
  width?: number;
  frozen?: boolean;
  options?: { label: string; value: string; color?: string }[];
  format?: string;
  required?: boolean;
  placeholder?: string;
  formula?: string;
}

export interface AirTableAction {
  label: string;
  icon?: React.ReactNode;
  onClick: (selectedRows: Row<any>[]) => void;
  danger?: boolean;
}

export interface AirTableProps<T> {
  data: T[];
  columns: AirTableColumn<T>[];
  idAccessor: keyof T | ((row: T) => string);
  onChange?: (rowId: string, columnId: string, value: any) => void;
  onAddRow?: () => T;
  onDeleteRows?: (rowIds: string[]) => void;
  actions?: AirTableAction[];
  storageKey?: string;
  emptyMessage?: string;
  rowHeight?: number;
  enableBulkEdit?: boolean;
  enableGrouping?: boolean;
  enableFilters?: boolean;
}

// ─── Cell Components ────────────────────────────────────────────────────────────

function TextCell({ value, onChange, editing }: any) {
  if (!editing) return <span className="truncate">{value || <span className="text-slate-300 dark:text-slate-600">Empty</span>}</span>;
  return (
    <input
      autoFocus
      defaultValue={value || ""}
      onBlur={(e) => onChange?.(e.target.value)}
      onKeyDown={(e) => { if (e.key === "Enter") onChange?.(e.currentTarget.value); if (e.key === "Escape") onChange?.(value); }}
      className="w-full bg-transparent outline-none text-sm"
    />
  );
}

function NumberCell({ value, onChange, editing, format }: any) {
  const display = format === "currency" ? `$${Number(value || 0).toLocaleString()}` : format === "percent" ? `${value || 0}%` : value ?? 0;
  if (!editing) return <span className="font-mono">{display}</span>;
  return (
    <input
      autoFocus type="number"
      defaultValue={value || ""}
      onBlur={(e) => onChange?.(parseFloat(e.target.value) || 0)}
      onKeyDown={(e) => { if (e.key === "Enter") onChange?.(parseFloat(e.currentTarget.value) || 0); if (e.key === "Escape") onChange?.(value); }}
      className="w-full bg-transparent outline-none text-sm font-mono"
    />
  );
}

function SelectCell({ value, onChange, editing, options }: any) {
  const selected = options?.find((o: any) => o.value === value);
  if (!editing) return (
    <span className="inline-flex items-center gap-1.5">
      {selected?.color && <span className="w-2 h-2 rounded-full" style={{ backgroundColor: selected.color }} />}
      {selected?.label || <span className="text-slate-300 dark:text-slate-600">Select</span>}
    </span>
  );
  return (
    <select
      autoFocus
      defaultValue={value || ""}
      onChange={(e) => onChange?.(e.target.value)}
      onBlur={(e) => onChange?.(e.target.value)}
      className="w-full bg-transparent outline-none text-sm cursor-pointer"
    >
      <option value="">— Select —</option>
      {options?.map((o: any) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

function MultiSelectCell({ value, onChange, editing, options }: any) {
  const values = Array.isArray(value) ? value : value ? [value] : [];
  if (!editing) return (
    <div className="flex flex-wrap gap-1">
      {values.map((v: string) => {
        const opt = options?.find((o: any) => o.value === v);
        return <DSBadge key={v} tone={opt?.color as any || "slate"} label={opt?.label || v} />;
      })}
      {values.length === 0 && <span className="text-slate-300 dark:text-slate-600 text-xs">Select</span>}
    </div>
  );
  return (
    <div className="flex flex-wrap gap-1 min-w-[200px]">
      {options?.map((o: any) => {
        const isActive = values.includes(o.value);
        return (
          <button
            key={o.value}
            onClick={() => {
              const next = isActive ? values.filter((v: string) => v !== o.value) : [...values, o.value];
              onChange?.(next);
            }}
            className={clsx("px-2 py-0.5 rounded text-xs font-medium transition-all", isActive ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" : "bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-slate-400")}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function DateCell({ value, onChange, editing }: any) {
  const display = value ? new Date(value).toLocaleDateString("es-ES", { day: "numeric", month: "short" }) : null;
  if (!editing) return <span>{display || <span className="text-slate-300 dark:text-slate-600">Empty</span>}</span>;
  return (
    <input
      autoFocus type="date"
      defaultValue={value || ""}
      onBlur={(e) => onChange?.(e.target.value)}
      onKeyDown={(e) => { if (e.key === "Enter") onChange?.(e.currentTarget.value); if (e.key === "Escape") onChange?.(value); }}
      className="w-full bg-transparent outline-none text-sm"
    />
  );
}

function CheckboxCell({ value, onChange, editing }: any) {
  return (
    <button
      onClick={() => onChange?.(!value)}
      className={clsx("w-4 h-4 rounded border transition-all flex items-center justify-center", value ? "bg-blue-500 border-blue-500" : "border-slate-300 dark:border-slate-600")}
    >
      {value && <span className="text-white text-xs">✓</span>}
    </button>
  );
}

function RatingCell({ value, onChange, editing }: any) {
  const rating = Number(value) || 0;
  if (!editing) return <div className="flex gap-0.5">{[1,2,3,4,5].map(i => <span key={i} className={i <= rating ? "text-amber-400" : "text-slate-200 dark:text-slate-700"}>★</span>)}</div>;
  return (
    <div className="flex gap-0.5">
      {[1,2,3,4,5].map(i => (
        <button key={i} onClick={() => onChange?.(i)} className={clsx("text-lg transition-all", i <= rating ? "text-amber-400 scale-110" : "text-slate-200 dark:text-slate-700 hover:text-amber-300")}>★</button>
      ))}
    </div>
  );
}

function PhoneCell({ value, onChange, editing }: any) {
  if (!editing) return <span className="font-mono">{value || <span className="text-slate-300 dark:text-slate-600">Empty</span>}</span>;
  return (
    <input autoFocus type="tel" defaultValue={value || ""} onBlur={(e) => onChange?.(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") onChange?.(e.currentTarget.value); }} className="w-full bg-transparent outline-none text-sm font-mono" />
  );
}

function EmailCell({ value, onChange, editing }: any) {
  if (!editing) return value ? <a href={`mailto:${value}`} className="text-blue-500 hover:underline truncate">{value}</a> : <span className="text-slate-300 dark:text-slate-600">Empty</span>;
  return (
    <input autoFocus type="email" defaultValue={value || ""} onBlur={(e) => onChange?.(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") onChange?.(e.currentTarget.value); }} className="w-full bg-transparent outline-none text-sm" />
  );
}

function URLCell({ value, onChange, editing }: any) {
  if (!editing) return value ? <a href={value} target="_blank" rel="noopener" className="text-blue-500 hover:underline truncate">{value}</a> : <span className="text-slate-300 dark:text-slate-600">Empty</span>;
  return (
    <input autoFocus type="url" defaultValue={value || ""} onBlur={(e) => onChange?.(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") onChange?.(e.currentTarget.value); }} className="w-full bg-transparent outline-none text-sm" />
  );
}

function ProgressCell({ value, onChange, editing }: any) {
  const pct = Math.min(100, Math.max(0, Number(value) || 0));
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  if (!editing) return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-500 w-8">{pct}%</span>
    </div>
  );
  return (
    <input autoFocus type="range" min="0" max="100" defaultValue={pct} onChange={(e) => onChange?.(parseInt(e.target.value))} className="w-full" />
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────────

export default function AirTable<T extends Record<string, any>>({
  data,
  columns,
  idAccessor,
  onChange,
  onAddRow,
  onDeleteRows,
  actions,
  storageKey,
  emptyMessage = "No rows yet. Click + to add.",
  rowHeight = 36,
  enableBulkEdit = true,
  enableGrouping = true,
  enableFilters = true,
}: AirTableProps<T>) {
  // ── State ──
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [grouping, setGrouping] = useState<GroupingState>([]);
  const [expanded, setExpanded] = useState<ExpandedState>({});
  const [columnVisibility, setColumnVisibility] = useState<Record<string, boolean>>({});
  const [editingCell, setEditingCell] = useState<{ rowId: string; colId: string } | null>(null);
  const [selectedRows, setSelectedRows] = useState<Record<string, boolean>>({});
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnSizing, setColumnSizing] = useState<Record<string, number>>({});
  const [history, setHistory] = useState<{ rowId: string; colId: string; oldValue: any }[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [showColumnConfig, setShowColumnConfig] = useState(false);
  const [copiedCell, setCopiedCell] = useState<{ rowId: string; colId: string; value: any } | null>(null);
  const [isFocused, setIsFocused] = useState(false);

  // ── Load saved prefs ──
  useEffect(() => {
    if (!storageKey) return;
    try {
      const prefs = JSON.parse(sessionStorage.getItem(`airtable_${storageKey}`) || "{}");
      if (prefs.sorting) setSorting(prefs.sorting);
      if (prefs.columnFilters) setColumnFilters(prefs.columnFilters);
      if (prefs.grouping) setGrouping(prefs.grouping);
      if (prefs.columnVisibility) setColumnVisibility(prefs.columnVisibility);
      if (prefs.columnSizing) setColumnSizing(prefs.columnSizing);
    } catch {}
  }, [storageKey]);

  // ── Save prefs ──
  useEffect(() => {
    if (!storageKey) return;
    sessionStorage.setItem(`airtable_${storageKey}`, JSON.stringify({
      sorting, columnFilters, grouping, columnVisibility, columnSizing,
    }));
  }, [storageKey, sorting, columnFilters, grouping, columnVisibility, columnSizing]);

  // ── Build column defs ──
  const tanstackColumns: ColumnDef<T>[] = useMemo(() => {
    const defs: ColumnDef<T>[] = [
      {
        id: "__select",
        header: ({ table }) => (
          <input type="checkbox" checked={table.getIsAllRowsSelected()} onChange={table.getToggleAllRowsSelectedHandler()} className="w-3.5 h-3.5 rounded" />
        ),
        cell: ({ row }) => (
          <input type="checkbox" checked={row.getIsSelected()} onChange={row.getToggleSelectedHandler()} className="w-3.5 h-3.5 rounded" />
        ),
        size: 40,
        enableResizing: false,
      },
    ];

    for (const col of columns) {
      defs.push({
        id: col.id,
        accessorKey: col.id,
        header: col.name,
        size: col.width || 180,
        cell: ({ getValue, row, table }) => {
          const value = getValue();
          const isEditing = editingCell?.rowId === row.id && editingCell?.colId === col.id;

          const handleChange = (newValue: any) => {
            setHistory(prev => [...prev.slice(0, historyIndex + 1), { rowId: row.id, colId: col.id, oldValue: value }]);
            setHistoryIndex(prev => prev + 1);
            setEditingCell(null);
            onChange?.(row.id, col.id, newValue);
          };

          const cellProps = { value, onChange: handleChange, editing: isEditing, options: col.options, format: col.format };

          switch (col.type) {
            case "text": return <TextCell {...cellProps} />;
            case "number": return <NumberCell {...cellProps} />;
            case "select": return <SelectCell {...cellProps} />;
            case "multiSelect": return <MultiSelectCell {...cellProps} />;
            case "date": case "datetime": return <DateCell {...cellProps} />;
            case "checkbox": return <CheckboxCell {...cellProps} />;
            case "rating": return <RatingCell {...cellProps} />;
            case "phone": return <PhoneCell {...cellProps} />;
            case "email": return <EmailCell {...cellProps} />;
            case "url": return <URLCell {...cellProps} />;
            case "progress": return <ProgressCell {...cellProps} />;
            default: return <TextCell {...cellProps} />;
          }
        },
      });
    }
    return defs;
  }, [columns, editingCell, onChange, historyIndex]);

  // ── Table instance ──
  const table = useReactTable({
    data,
    columns: tanstackColumns,
    getRowId: (row) => {
      if (typeof idAccessor === "function") return idAccessor(row);
      return String(row[idAccessor]);
    },
    state: { sorting, columnFilters, grouping, expanded, columnVisibility, globalFilter, columnSizing },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGroupingChange: setGrouping,
    onExpandedChange: setExpanded,
    onColumnVisibilityChange: setColumnVisibility,
    onGlobalFilterChange: setGlobalFilter,
    onColumnSizingChange: setColumnSizing,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getGroupedRowModel: getGroupedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    columnResizeMode: "onChange" as ColumnResizeMode,
    enableMultiSort: true,
    enableGrouping: enableGrouping,
    enableColumnResizing: true,
    enableHiding: true,
    initialState: { pagination: { pageSize: 1000 } },
  });

  // ── Virtualizer ──
  const tableContainerRef = useRef<HTMLDivElement>(null);
  const { rows } = table.getRowModel();
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => rowHeight,
    overscan: 10,
  });

  const virtualRows = virtualizer.getVirtualItems();
  const totalSize = virtualizer.getTotalSize();
  const paddingTop = virtualRows.length > 0 ? virtualRows[0].start : 0;
  const paddingBottom = virtualRows.length > 0 ? totalSize - virtualRows[virtualRows.length - 1].end : 0;

  // ── Keyboard Navigation ──
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!editingCell && !isFocused) return;

      const visibleCols = table.getVisibleFlatColumns().filter(c => c.id !== "__select");
      const visibleRows = rows;
      if (!visibleCols.length || !visibleRows.length) return;

      const currentRowIdx = visibleRows.findIndex(r => r.id === editingCell?.rowId);
      const currentColIdx = visibleCols.findIndex(c => c.id === editingCell?.colId);

      if (currentRowIdx === -1 || currentColIdx === -1) return;

      let nextRow = currentRowIdx;
      let nextCol = currentColIdx;

      if (e.key === "ArrowDown" || (e.key === "Enter" && !editingCell)) {
        e.preventDefault();
        nextRow = Math.min(currentRowIdx + 1, visibleRows.length - 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        nextRow = Math.max(currentRowIdx - 1, 0);
      } else if (e.key === "ArrowRight" || (e.key === "Tab" && !e.shiftKey)) {
        if (e.key === "Tab") e.preventDefault();
        nextCol = Math.min(currentColIdx + 1, visibleCols.length - 1);
        if (nextCol > currentColIdx && e.key === "ArrowRight") {
          setEditingCell({ rowId: visibleRows[currentRowIdx].id, colId: visibleCols[nextCol].id });
          return;
        }
      } else if (e.key === "ArrowLeft" || (e.key === "Tab" && e.shiftKey)) {
        if (e.key === "Tab") e.preventDefault();
        nextCol = Math.max(currentColIdx - 1, 0);
      } else if (e.key === "Delete" || e.key === "Backspace") {
        if (!editingCell) {
          e.preventDefault();
          onChange?.(visibleRows[currentRowIdx].id, visibleCols[currentColIdx].id, null);
          return;
        }
      } else if (e.key === "c" && (e.metaKey || e.ctrlKey) && editingCell) {
        const val = (visibleRows[currentRowIdx].original as any)[visibleCols[currentColIdx].id];
        setCopiedCell({ rowId: editingCell.rowId, colId: editingCell.colId, value: val });
      } else if (e.key === "v" && (e.metaKey || e.ctrlKey) && editingCell && copiedCell) {
        onChange?.(editingCell.rowId, editingCell.colId, copiedCell.value);
      } else {
        return;
      }

      if (nextRow !== currentRowIdx || nextCol !== currentColIdx) {
        setEditingCell({
          rowId: visibleRows[nextRow].id,
          colId: visibleCols[nextCol].id,
        });
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [editingCell, isFocused, rows, table, onChange, copiedCell]);

  // ── Export CSV ──
  const handleExportCSV = useCallback(() => {
    const visibleCols = table.getVisibleFlatColumns().filter(c => c.id !== "__select");
    const headers = visibleCols.map(c => (c.columnDef.header as string) || c.id);
    const csvRows = [headers.join(",")];

    for (const row of rows) {
      const values = visibleCols.map(col => {
        const val = (row.original as any)[col.id];
        if (val === null || val === undefined) return "";
        const str = String(val).replace(/"/g, '""');
        return str.includes(",") || str.includes("\n") ? `"${str}"` : str;
      });
      csvRows.push(values.join(","));
    }

    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${storageKey || "table"}_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [rows, table, storageKey]);

  // ── Undo/Redo ──
  const handleUndo = useCallback(() => {
    if (historyIndex < 0) return;
    const entry = history[historyIndex];
    onChange?.(entry.rowId, entry.colId, entry.oldValue);
    setHistoryIndex(prev => prev - 1);
  }, [history, historyIndex, onChange]);

  const handleRedo = useCallback(() => {
    if (historyIndex >= history.length - 1) return;
    const entry = history[historyIndex + 1];
    onChange?.(entry.rowId, entry.colId, undefined);
    setHistoryIndex(prev => prev + 1);
  }, [history, historyIndex, onChange]);

  // ── Selected count ──
  const selectedCount = Object.values(selectedRows).filter(Boolean).length;

  // ── Render ──
  return (
    <div className="flex flex-col h-full bg-white dark:bg-[#1a1b1e] rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden">
      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-black/20">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Buscar en toda la tabla..."
            className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg py-1 pl-9 pr-3 text-xs outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <button onClick={handleUndo} disabled={historyIndex < 0} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-30" title="Deshacer">
          <Undo2 size={14} className="text-slate-500" />
        </button>
        <button onClick={handleRedo} disabled={historyIndex >= history.length - 1} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-white/10 disabled:opacity-30" title="Rehacer">
          <Redo2 size={14} className="text-slate-500" />
        </button>

        <div className="h-4 w-px bg-slate-200 dark:bg-white/10" />

        {enableGrouping && (
          <button onClick={() => setGrouping(prev => prev.length ? [] : [table.getAllColumns()[2]?.id || ""])} className={clsx("px-2 py-1 rounded text-xs font-medium", grouping.length ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" : "hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500")}>
            Agrupar
          </button>
        )}

        <button onClick={() => setShowColumnConfig(!showColumnConfig)} className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-white/10">
          <Columns size={14} className="text-slate-500" />
        </button>

        {onAddRow && (
          <button onClick={() => { const newRow = onAddRow(); }} className="flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold bg-blue-500 text-white hover:bg-blue-600">
            <Plus size={12} /> Fila
          </button>
        )}

        {selectedCount > 0 && onDeleteRows && (
          <button onClick={() => { onDeleteRows(Object.keys(selectedRows).filter(k => selectedRows[k])); setSelectedRows({}); }} className="flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold bg-red-500 text-white hover:bg-red-600">
            <Trash2 size={12} /> Eliminar ({selectedCount})
          </button>
        )}

        <div className="h-4 w-px bg-slate-200 dark:bg-white/10" />

        <button onClick={handleExportCSV} className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500" title="Exportar CSV">
          <Download size={12} /> CSV
        </button>

        <button onClick={() => setIsFocused(!isFocused)} className={clsx("p-1.5 rounded", isFocused ? "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300" : "hover:bg-slate-100 dark:hover:bg-white/10 text-slate-500")} title="Navegación por teclado">
          <Keyboard size={14} />
        </button>

        {copiedCell && (
          <span className="text-[10px] text-slate-400 flex items-center gap-1">
            <ClipboardPaste size={10} /> Celda copiada
          </span>
        )}

        <div className="flex-1" />
        <span className="text-[10px] text-slate-400 font-medium">{rows.length} filas</span>
      </div>

      {/* ── Column Config Popover ── */}
      <AnimatePresence>
        {showColumnConfig && (
          <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} className="absolute right-4 top-14 z-50 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg shadow-xl p-3 w-56">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-200">Columnas</span>
              <button onClick={() => setShowColumnConfig(false)}><X size={12} className="text-slate-400" /></button>
            </div>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {table.getAllColumns().filter(c => c.id !== "__select").map(col => (
                <label key={col.id} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={col.getIsVisible()} onChange={col.getToggleVisibilityHandler()} className="w-3 h-3 rounded" />
                  <GripHorizontal size={10} className="text-slate-300" />
                  {col.columnDef.header?.toString() || col.id}
                </label>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Table ── */}
      <div ref={tableContainerRef} className="flex-1 overflow-auto">
        <table className="w-full border-collapse" style={{ minWidth: table.getTotalSize() }}>
          <thead className="sticky top-0 z-10 bg-slate-50 dark:bg-[#141517]">
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header, headerIdx) => {
                  const isFrozen = headerIdx === 0;
                  const frozenWidth = headerGroup.headers.slice(0, headerIdx).reduce((sum, h) => sum + h.getSize(), 0);
                  return (
                    <th
                      key={header.id}
                      colSpan={header.colSpan}
                      className={clsx("relative px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500 border-b border-slate-200 dark:border-white/10 select-none", header.column.getCanSort() && "cursor-pointer hover:bg-slate-100 dark:hover:bg-white/5", isFrozen && "sticky left-0 z-[10] bg-slate-50 dark:bg-[#141517] shadow-[2px_0_4px_-1px_rgba(0,0,0,0.1)] dark:shadow-[2px_0_4px_-1px_rgba(0,0,0,0.3)]")}
                      style={{ ...(isFrozen ? { left: `${frozenWidth}px` } : {}) }}
                    >
                      <div className="flex items-center gap-1" onClick={header.column.getToggleSortingHandler()}>
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getIsSorted() === "asc" && <ArrowUp size={10} />}
                        {header.column.getIsSorted() === "desc" && <ArrowDown size={10} />}
                      </div>
                      {header.column.getCanResize() && (
                        <div
                          onMouseDown={header.getResizeHandler()}
                          onTouchStart={header.getResizeHandler()}
                          className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500/30 transition-colors z-20"
                        />
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {paddingTop > 0 && <tr><td style={{ height: `${paddingTop}px` }}></td></tr>}
            {virtualRows.map(virtualRow => {
              const row = rows[virtualRow.index] as Row<T>;
              return (
                <tr key={row.id} className={clsx("border-b border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors", row.getIsSelected() && "bg-blue-50 dark:bg-blue-900/10")}>
                  {row.getVisibleCells().map((cell, cellIdx) => {
                    const isFrozen = cellIdx === 0;
                    const frozenWidth = row.getVisibleCells().slice(0, cellIdx).reduce((sum, c) => sum + c.column.getSize(), 0);
                    return (
                      <td
                        key={cell.id}
                        className={clsx("px-2 py-1 text-sm", isFrozen && "sticky left-0 z-[5] bg-white dark:bg-[#1a1b1e] shadow-[2px_0_4px_-1px_rgba(0,0,0,0.1)] dark:shadow-[2px_0_4px_-1px_rgba(0,0,0,0.3)]")}
                        style={{ width: cell.column.getSize(), minWidth: cell.column.getSize(), ...(isFrozen ? { left: `${frozenWidth}px` } : {}) }}
                        onClick={() => { if (cell.column.id !== "__select") setEditingCell({ rowId: row.id, colId: cell.column.id }); }}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {paddingBottom > 0 && <tr><td style={{ height: `${paddingBottom}px` }}></td></tr>}
          </tbody>
        </table>

        {rows.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400">
            <Plus size={32} className="mb-3 opacity-30" />
            <p className="text-sm font-medium">{emptyMessage}</p>
          </div>
        )}
      </div>
    </div>
  );
}

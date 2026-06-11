"use client";

import {
  AllCommunityModule,
  ColDef,
  GetRowIdParams,
  ModuleRegistry,
  themeQuartz,
} from 'ag-grid-community';
import { AgGridReact } from 'ag-grid-react';
import clsx from 'clsx';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Calendar,
  ChevronDown,
  Columns as ColumnsIcon,
  Download,
  Filter,
  Flag,
  Hash,
  Layers,
  Loader2,
  Plus,
  Search,
  User,
  X,
} from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

ModuleRegistry.registerModules([AllCommunityModule]);

// ─── Types ────────────────────────────────────────────────────────────────────

export type ColumnType =
  | 'text' | 'status' | 'priority' | 'user' | 'date'
  | 'progress' | 'tag' | 'id' | 'link' | 'number';

export type FilterOperator =
  | 'contains' | 'notContains' | 'equals' | 'notEquals'
  | 'isEmpty' | 'isNotEmpty' | 'gt' | 'lt';

export interface ActiveFilter {
  id: number;
  field: string;
  label: string;
  operator: FilterOperator;
  value: string;
}

export interface TableColumn<T> {
  key: keyof T | string;
  label: string;
  type: ColumnType;
  width?: string;
  sortable?: boolean;
  hidden?: boolean;
  editable?: boolean;
  filterable?: boolean;
  render?: (value: any, item: T) => React.ReactNode;
  displayValue?: (item: T) => string;
}

interface UniversalTableViewProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  groupBy?: string;
  viewName?: string;
  onRowClick?: (item: T) => void;
  onAddItem?: (groupValue?: string) => void;
  onUpdateItem?: (id: string | number, field: string, value: any) => Promise<boolean | void> | boolean | void;
  isLoading?: boolean;
  emptyMessage?: string;
  renderDetailPanel?: (item: T, onClose: () => void) => React.ReactNode;
}

// ─── Persistence ──────────────────────────────────────────────────────────────

function loadState(viewName?: string) {
  if (!viewName || typeof window === 'undefined') return null;
  try { return JSON.parse(localStorage.getItem(`utv_${viewName}`) || 'null'); }
  catch { return null; }
}
function saveState(viewName: string | undefined, state: object) {
  if (!viewName || typeof window === 'undefined') return;
  try { localStorage.setItem(`utv_${viewName}`, JSON.stringify(state)); }
  catch {}
}

// ─── Filter helpers ───────────────────────────────────────────────────────────

const OPERATOR_LABELS: Record<FilterOperator, string> = {
  contains: 'contiene',
  notContains: 'no contiene',
  equals: 'es igual a',
  notEquals: 'no es igual a',
  isEmpty: 'está vacío',
  isNotEmpty: 'no está vacío',
  gt: 'mayor que',
  lt: 'menor que',
};

const OPERATORS_BY_TYPE: Record<ColumnType, FilterOperator[]> = {
  text:     ['contains', 'notContains', 'equals', 'notEquals', 'isEmpty', 'isNotEmpty'],
  status:   ['equals', 'notEquals', 'isEmpty', 'isNotEmpty'],
  priority: ['equals', 'notEquals'],
  user:     ['contains', 'notContains', 'isEmpty', 'isNotEmpty'],
  date:     ['contains', 'equals', 'isEmpty', 'isNotEmpty'],
  number:   ['equals', 'notEquals', 'gt', 'lt', 'isEmpty', 'isNotEmpty'],
  progress: ['gt', 'lt', 'equals'],
  tag:      ['contains', 'notContains', 'equals', 'isEmpty', 'isNotEmpty'],
  id:       ['contains', 'equals'],
  link:     ['contains', 'isEmpty', 'isNotEmpty'],
};

function applyFilters<T>(data: T[], filters: ActiveFilter[]): T[] {
  if (!filters.length) return data;
  return data.filter(item =>
    filters.every(f => {
      if (!f.field) return true;
      const raw = String((item as any)[f.field] ?? '').toLowerCase().trim();
      const val = f.value.toLowerCase().trim();
      switch (f.operator) {
        case 'contains':    return raw.includes(val);
        case 'notContains': return !raw.includes(val);
        case 'equals':      return raw === val;
        case 'notEquals':   return raw !== val;
        case 'isEmpty':     return !raw;
        case 'isNotEmpty':  return !!raw;
        case 'gt':          return parseFloat(raw) > parseFloat(val);
        case 'lt':          return parseFloat(raw) < parseFloat(val);
        default:            return true;
      }
    })
  );
}

// ─── Status / Priority maps ───────────────────────────────────────────────────

const STATUS_MAP: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  todo:          { label: 'Pendiente',   bg: 'bg-amber-50 dark:bg-amber-900/20',     text: 'text-amber-700 dark:text-amber-400',     dot: 'bg-amber-400'    },
  pending:       { label: 'Pendiente',   bg: 'bg-amber-50 dark:bg-amber-900/20',     text: 'text-amber-700 dark:text-amber-400',     dot: 'bg-amber-400'    },
  pendiente:     { label: 'Pendiente',   bg: 'bg-amber-50 dark:bg-amber-900/20',     text: 'text-amber-700 dark:text-amber-400',     dot: 'bg-amber-400'    },
  in_progress:   { label: 'En Progreso', bg: 'bg-blue-50 dark:bg-blue-900/20',       text: 'text-blue-700 dark:text-blue-400',       dot: 'bg-blue-500'     },
  review:        { label: 'En Revisión', bg: 'bg-blue-50 dark:bg-blue-900/20',       text: 'text-blue-700 dark:text-blue-400',       dot: 'bg-blue-500'     },
  done:          { label: 'Terminado',   bg: 'bg-cyan-50 dark:bg-cyan-900/20',       text: 'text-cyan-700 dark:text-cyan-400',       dot: 'bg-cyan-500'     },
  completed:     { label: 'Completado',  bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-400', dot: 'bg-emerald-500'  },
  realizada:     { label: 'Realizada',   bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-400', dot: 'bg-emerald-500'  },
  blocked:       { label: 'Bloqueado',   bg: 'bg-rose-50 dark:bg-rose-900/20',       text: 'text-rose-700 dark:text-rose-400',       dot: 'bg-rose-500'     },
  activo:        { label: 'Activo',      bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-400', dot: 'bg-emerald-500'  },
  inactivo:      { label: 'Inactivo',    bg: 'bg-slate-50 dark:bg-white/5',          text: 'text-slate-500 dark:text-slate-400',     dot: 'bg-slate-400'    },
  habilitado:    { label: 'Abierta',     bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-400', dot: 'bg-emerald-500'  },
  deshabilitado: { label: 'Bloqueada',   bg: 'bg-amber-50 dark:bg-amber-900/20',     text: 'text-amber-700 dark:text-amber-400',     dot: 'bg-amber-400'    },
  cerrado:       { label: 'Cerrada',     bg: 'bg-slate-50 dark:bg-white/5',          text: 'text-slate-500 dark:text-slate-400',     dot: 'bg-slate-400'    },
  cancelada:     { label: 'Cancelada',   bg: 'bg-rose-50 dark:bg-rose-900/20',       text: 'text-rose-700 dark:text-rose-400',       dot: 'bg-rose-500'     },
};
function getStatus(v: string) {
  return STATUS_MAP[String(v ?? '').toLowerCase()] ?? {
    label: String(v ?? '—'),
    bg: 'bg-slate-50 dark:bg-white/5',
    text: 'text-slate-600 dark:text-slate-400',
    dot: 'bg-slate-400',
  };
}

const PRIORITY_MAP: Record<string, { label: string; color: string; bg: string }> = {
  urgent: { label: 'Urgente', color: 'text-rose-600 dark:text-rose-400',     bg: 'bg-rose-50 dark:bg-rose-900/20'     },
  high:   { label: 'Alta',    color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-50 dark:bg-orange-900/20' },
  medium: { label: 'Media',   color: 'text-amber-600 dark:text-amber-400',   bg: 'bg-amber-50 dark:bg-amber-900/20'   },
  normal: { label: 'Normal',  color: 'text-blue-600 dark:text-blue-400',     bg: 'bg-blue-50 dark:bg-blue-900/20'     },
  low:    { label: 'Baja',    color: 'text-slate-500 dark:text-slate-400',   bg: 'bg-slate-50 dark:bg-slate-800'      },
};

// ─── Cell renderers ───────────────────────────────────────────────────────────

function StatusCell({ value }: any) {
  const st = getStatus(String(value ?? ''));
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2 py-[3px] rounded text-[11px] font-semibold leading-none', st.bg, st.text)}>
      <span className={clsx('size-1.5 rounded-full shrink-0', st.dot)} />
      {st.label}
    </span>
  );
}
function PriorityCell({ value }: any) {
  const p = PRIORITY_MAP[String(value ?? '').toLowerCase()] ?? PRIORITY_MAP.normal;
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2 py-[3px] rounded text-[11px] font-semibold', p.bg, p.color)}>
      <Flag size={10} /> {p.label}
    </span>
  );
}
function DateCell({ value }: any) {
  if (!value) return <span className="text-slate-300 dark:text-slate-600 text-xs">—</span>;
  return (
    <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
      <Calendar size={11} className="shrink-0" />
      <span className="text-[12px] font-medium whitespace-nowrap">
        {new Date(String(value)).toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: '2-digit' })}
      </span>
    </div>
  );
}
function UserCell({ value }: any) {
  return (
    <div className="flex items-center gap-2 h-full">
      <div className="size-6 rounded-full bg-blue-100 dark:bg-white/10 flex items-center justify-center font-semibold text-blue-600 text-[10px] shrink-0">
        {value ? String(value).charAt(0).toUpperCase() : <User size={11} className="text-slate-400" />}
      </div>
      <span className="text-[12px] text-slate-600 dark:text-slate-300 font-medium truncate">
        {value ? String(value) : '—'}
      </span>
    </div>
  );
}
function IdCell({ value }: any) {
  return (
    <div className="flex items-center gap-1 text-[11px] font-bold text-slate-300 dark:text-slate-600 uppercase tracking-wide">
      <Hash size={10} />{String(value ?? '').substring(0, 8)}
    </div>
  );
}
function ProgressCell({ value }: any) {
  const raw = Number(value || 0);
  const pct = Math.round(raw <= 1 ? raw * 100 : raw);
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-1.5 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
        <div className={clsx('h-full rounded-full', pct === 100 ? 'bg-emerald-500' : 'bg-blue-500')} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-semibold text-slate-400 tabular-nums text-[11px] w-8 text-right">{pct}%</span>
    </div>
  );
}

// ─── FilterRow component ──────────────────────────────────────────────────────

function FilterRow({
  filter,
  filterableCols,
  onChange,
  onRemove,
}: {
  filter: ActiveFilter;
  filterableCols: { key: string; label: string; type: ColumnType }[];
  onChange: (updated: ActiveFilter) => void;
  onRemove: () => void;
}) {
  const colType = filterableCols.find(c => c.key === filter.field)?.type ?? 'text';
  const ops = OPERATORS_BY_TYPE[colType] ?? OPERATORS_BY_TYPE.text;
  const needsValue = !['isEmpty', 'isNotEmpty'].includes(filter.operator);
  const selectClass = 'h-7 px-2 text-[11px] font-medium rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-blue-400 cursor-pointer';

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] w-10 text-right shrink-0">
        {filterableCols.findIndex(c => c.key === filter.field) === 0 ? 'DONDE' : 'Y'}
      </span>
      <select
        value={filter.field}
        onChange={e => {
          const col = filterableCols.find(c => c.key === e.target.value);
          const newOps = OPERATORS_BY_TYPE[col?.type ?? 'text'] ?? OPERATORS_BY_TYPE.text;
          onChange({ ...filter, field: e.target.value, label: col?.label ?? e.target.value, operator: newOps[0], value: '' });
        }}
        className={selectClass}
      >
        {filterableCols.map(c => <option key={c.key} value={c.key}>{c.label}</option>)}
      </select>
      <select
        value={filter.operator}
        onChange={e => onChange({ ...filter, operator: e.target.value as FilterOperator, value: '' })}
        className={selectClass}
      >
        {ops.map(op => <option key={op} value={op}>{OPERATOR_LABELS[op]}</option>)}
      </select>
      {needsValue && (
        <input
          type="text"
          value={filter.value}
          onChange={e => onChange({ ...filter, value: e.target.value })}
          placeholder="Valor…"
          className="h-7 px-2 text-[11px] rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-400 min-w-[100px] max-w-[160px]"
        />
      )}
      <button
        onClick={onRemove}
        className="p-1 rounded text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"
      >
        <X size={12} />
      </button>
    </div>
  );
}

// ─── Themes ───────────────────────────────────────────────────────────────────

const lightTheme = themeQuartz.withParams({
  fontFamily: 'inherit', fontSize: 12, rowHeight: 36, headerHeight: 36,
  backgroundColor: '#ffffff', foregroundColor: '#1e293b', borderColor: '#e2e8f0',
  oddRowBackgroundColor: '#f8fafc', headerBackgroundColor: '#f1f5f9',
  headerTextColor: '#475569', selectedRowBackgroundColor: '#eef2ff',
  accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8,
});
const darkTheme = themeQuartz.withParams({
  fontFamily: 'inherit', fontSize: 12, rowHeight: 36, headerHeight: 36,
  backgroundColor: 'rgb(15 23 42)', foregroundColor: '#e2e8f0',
  borderColor: 'rgba(255,255,255,0.08)', oddRowBackgroundColor: 'rgba(255,255,255,0.02)',
  headerBackgroundColor: 'rgba(255,255,255,0.04)', headerTextColor: '#94a3b8',
  selectedRowBackgroundColor: 'rgba(99,102,241,0.15)', accentColor: '#6366f1',
  cellHorizontalPaddingScale: 0.8,
});

const GROUP_ROW_ID_PREFIX = '__group__';

// ─── Main component ───────────────────────────────────────────────────────────

export default function UniversalTableView<T extends { id: string | number }>({
  data,
  columns,
  groupBy: groupByProp,
  viewName,
  onRowClick,
  onAddItem,
  onUpdateItem,
  isLoading,
  emptyMessage = 'No hay registros para mostrar',
  renderDetailPanel,
}: UniversalTableViewProps<T>) {
  const saved = useMemo(() => loadState(viewName), [viewName]);

  const [isDark, setIsDark] = useState(false);
  const [quickFilter, setQuickFilter] = useState('');

  // Persistent state
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(
    () => new Set(saved?.hiddenCols ?? [])
  );
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>(
    () => saved?.filters ?? []
  );
  const [activeGroupBy, setActiveGroupBy] = useState<string | null>(
    () => saved?.groupBy ?? groupByProp ?? null
  );

  // UI state
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [showColPanel, setShowColPanel] = useState(false);
  const [showGroupPanel, setShowGroupPanel] = useState(false);
  const [selectedItem, setSelectedItem] = useState<T | null>(null);

  const filterIdRef = useRef(1000);
  const gridRef = useRef<AgGridReact>(null);
  const colPanelRef = useRef<HTMLDivElement>(null);
  const groupPanelRef = useRef<HTMLDivElement>(null);

  // Dark mode detection
  useEffect(() => {
    const check = () => setIsDark(document.documentElement.classList.contains('dark'));
    check();
    const obs = new MutationObserver(check);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => obs.disconnect();
  }, []);

  // Close panels on outside click
  useEffect(() => {
    if (!showColPanel) return;
    const h = (e: MouseEvent) => { if (colPanelRef.current && !colPanelRef.current.contains(e.target as Node)) setShowColPanel(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [showColPanel]);

  useEffect(() => {
    if (!showGroupPanel) return;
    const h = (e: MouseEvent) => { if (groupPanelRef.current && !groupPanelRef.current.contains(e.target as Node)) setShowGroupPanel(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [showGroupPanel]);

  // Persist state to localStorage
  useEffect(() => {
    saveState(viewName, { hiddenCols: [...hiddenCols], filters: activeFilters, groupBy: activeGroupBy });
  }, [viewName, hiddenCols, activeFilters, activeGroupBy]);

  // Filterable columns (exclude synthetic __ keys and those with filterable:false)
  const filterableCols = useMemo(() =>
    columns.filter(c => {
      const k = String(c.key);
      return !c.hidden && c.filterable !== false && !k.startsWith('__') && !k.startsWith('_');
    }).map(c => ({ key: String(c.key), label: c.label, type: c.type })),
    [columns]
  );

  const groupableCols = useMemo(() =>
    columns.filter(c => {
      const k = String(c.key);
      return !c.hidden && c.filterable !== false && !k.startsWith('__') && !k.startsWith('_') && !c.render;
    }),
    [columns]
  );

  // Add / remove filters
  const addFilter = useCallback(() => {
    filterIdRef.current += 1;
    const first = filterableCols[0];
    if (!first) return;
    setActiveFilters(prev => [...prev, {
      id: filterIdRef.current,
      field: first.key,
      label: first.label,
      operator: OPERATORS_BY_TYPE[first.type]?.[0] ?? 'contains',
      value: '',
    }]);
  }, [filterableCols]);

  // Pre-filter data
  const filteredData = useMemo(() => applyFilters(data, activeFilters), [data, activeFilters]);

  // Group rows
  const rowData = useMemo(() => {
    if (!activeGroupBy) return filteredData;
    const groups: Record<string, T[]> = {};
    filteredData.forEach(item => {
      const k = String((item as any)[activeGroupBy] || 'Sin categoría');
      if (!groups[k]) groups[k] = [];
      groups[k].push(item);
    });
    const flat: any[] = [];
    Object.entries(groups).forEach(([key, rows]) => {
      flat.push({ __isGroup: true, __groupKey: key, __groupCount: rows.length, id: `${GROUP_ROW_ID_PREFIX}${key}` });
      flat.push(...rows);
    });
    return flat;
  }, [filteredData, activeGroupBy]);

  // Column definitions
  const colDefs = useMemo<ColDef[]>(() => {
    return columns
      .filter(c => !c.hidden && !hiddenCols.has(String(c.key)))
      .map((col): ColDef => {
        const field = String(col.key);
        const isGroupRow = field === '__isGroup';
        const isExplicitlyDisabled = col.editable === false;
        const canEdit = !isExplicitlyDisabled && !isGroupRow && !!onUpdateItem;

        const base: ColDef = {
          field,
          headerName: col.label,
          width: col.width ? parseInt(col.width) : undefined,
          flex: col.width ? undefined : 1,
          minWidth: 80,
          resizable: true,
          sortable: col.sortable !== false,
          filter: false, // we use our own filter system
          floatingFilter: false,
        };

        if (col.render) {
          const renderFn = col.render;
          base.cellRenderer = ({ value, data: rowData }: any) => {
            if (rowData?.__isGroup) return null;
            return <>{renderFn(value, rowData as T)}</>;
          };
          if (canEdit) {
            base.editable = true;
            base.singleClickEdit = true;
            base.cellEditor = 'agTextCellEditor';
            base.valueSetter = (params: any) => {
              if (params.oldValue === params.newValue) return false;
              const result = onUpdateItem!(params.data.id, field, params.newValue);
              if (result instanceof Promise) {
                result.then(ok => { if (ok === false) params.api.applyTransaction({ update: [params.data] }); });
                return true;
              }
              return result !== false;
            };
          } else {
            base.editable = false;
          }
        } else {
          if (canEdit) {
            base.editable = true;
            base.singleClickEdit = true;
            base.cellEditor = 'agTextCellEditor';
            base.valueSetter = (params: any) => {
              if (params.oldValue === params.newValue) return false;
              const result = onUpdateItem!(params.data.id, field, params.newValue);
              if (result instanceof Promise) {
                result.then(ok => { if (ok === false) params.api.applyTransaction({ update: [params.data] }); });
                return true;
              }
              return result !== false;
            };
          }
          switch (col.type) {
            case 'status':   base.cellRenderer = StatusCell; break;
            case 'priority': base.cellRenderer = PriorityCell; break;
            case 'date':     base.cellRenderer = DateCell; break;
            case 'user':     base.cellRenderer = UserCell; break;
            case 'id':       base.cellRenderer = IdCell; break;
            case 'progress': base.cellRenderer = ProgressCell; break;
            default:         base.cellStyle = { fontSize: '13px', fontWeight: '500' }; break;
          }
        }
        return base;
      });
  }, [columns, hiddenCols, onUpdateItem]);

  const isFullWidthRow = useCallback((params: any) => !!params.rowNode.data?.__isGroup, []);

  const fullWidthCellRenderer = useCallback(({ data: row }: any) => (
    <div className="flex items-center gap-2 px-3 h-full bg-slate-50 dark:bg-white/[0.03] border-b border-slate-200 dark:border-white/5">
      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{row.__groupKey}</span>
      <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 bg-slate-200 dark:bg-white/10 rounded-full px-2 py-0.5">{row.__groupCount}</span>
      {onAddItem && (
        <button onClick={(e) => { e.stopPropagation(); onAddItem(row.__groupKey); }}
          className="ml-auto flex items-center gap-1 text-[10px] font-semibold text-blue-600 hover:opacity-80 transition-colors">
          <Plus size={11} /> Agregar
        </button>
      )}
    </div>
  ), [onAddItem]);

  const getRowId = useCallback((params: GetRowIdParams) => String((params.data as any).id), []);
  const getRowHeight = useCallback((params: any) => params.data?.__isGroup ? 32 : 36, []);
  const handleRowClick = useCallback((e: any) => {
    if (e.data?.__isGroup) return;
    setSelectedItem(e.data);
    onRowClick?.(e.data);
  }, [onRowClick]);

  const visibleCols = columns.filter(c => !c.hidden);
  const activeGroupByLabel = groupableCols.find(c => String(c.key) === activeGroupBy)?.label;

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full gap-2">

      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 flex-wrap shrink-0">

        {/* Search */}
        <div className="relative flex-1 min-w-[160px] max-w-xs">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            value={quickFilter}
            onChange={e => {
              setQuickFilter(e.target.value);
              gridRef.current?.api?.setGridOption('quickFilterText', e.target.value);
            }}
            placeholder="Buscar…"
            className="w-full pl-7 pr-7 py-1.5 text-xs border border-[hsl(var(--border-primary))] rounded-lg bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] placeholder-slate-400 outline-none focus:ring-1 focus:ring-blue-400"
          />
          {quickFilter && (
            <button onClick={() => { setQuickFilter(''); gridRef.current?.api?.setGridOption('quickFilterText', ''); }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X size={11} />
            </button>
          )}
        </div>

        {/* Filter button */}
        <button
          onClick={() => setShowFilterPanel(p => !p)}
          className={clsx(
            'flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold rounded-lg transition-colors border',
            showFilterPanel || activeFilters.length > 0
              ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-700'
              : 'bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border-primary))] hover:border-slate-300 dark:hover:border-white/20'
          )}
        >
          <Filter size={13} />
          Filtros
          {activeFilters.length > 0 && (
            <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-blue-600 text-white text-[9px] font-bold leading-none">
              {activeFilters.length}
            </span>
          )}
        </button>

        {/* Group by */}
        {groupableCols.length > 0 && (
          <div className="relative" ref={groupPanelRef}>
            <button
              onClick={() => setShowGroupPanel(p => !p)}
              className={clsx(
                'flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold rounded-lg transition-colors border',
                activeGroupBy
                  ? 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-primary))] border-[hsl(var(--border-primary))] dark:border-white/20'
                  : 'bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border-primary))] hover:border-slate-300 dark:hover:border-white/20'
              )}
            >
              <Layers size={13} />
              {activeGroupByLabel ? `Agrupado: ${activeGroupByLabel}` : 'Agrupar'}
              <ChevronDown size={11} />
            </button>
            <AnimatePresence>
              {showGroupPanel && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.97 }}
                  transition={{ duration: 0.1 }}
                  className="absolute top-full left-0 mt-1 z-50 w-48 bg-[hsl(var(--bg-primary))] dark:bg-slate-900 border border-[hsl(var(--border-primary))] rounded-lg shadow-xl py-1"
                >
                  <p className="text-[9px] font-bold uppercase tracking-wide text-slate-400 px-3 py-1.5">Agrupar por</p>
                  <button
                    onClick={() => { setActiveGroupBy(null); setShowGroupPanel(false); }}
                    className={clsx(
                      'w-full text-left px-3 py-2 text-xs font-medium transition-colors hover:bg-[hsl(var(--bg-muted))]',
                      !activeGroupBy ? 'text-blue-600 font-semibold' : 'text-[hsl(var(--text-primary))]'
                    )}
                  >
                    Sin agrupar
                  </button>
                  {groupableCols.map(col => (
                    <button
                      key={String(col.key)}
                      onClick={() => { setActiveGroupBy(String(col.key)); setShowGroupPanel(false); }}
                      className={clsx(
                        'w-full text-left px-3 py-2 text-xs font-medium transition-colors hover:bg-[hsl(var(--bg-muted))]',
                        activeGroupBy === String(col.key) ? 'text-blue-600 font-semibold' : 'text-[hsl(var(--text-primary))]'
                      )}
                    >
                      {col.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Right side actions */}
        <div className="flex items-center gap-1 ml-auto">

          {/* Column visibility */}
          <div className="relative" ref={colPanelRef}>
            <button
              onClick={() => setShowColPanel(p => !p)}
              className={clsx(
                'flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold rounded-lg transition-colors border',
                showColPanel
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-700'
                  : 'bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border-primary))] hover:border-slate-300 dark:hover:border-white/20'
              )}
            >
              <ColumnsIcon size={13} /> Columnas
            </button>
            <AnimatePresence>
              {showColPanel && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.97 }}
                  transition={{ duration: 0.1 }}
                  className="absolute top-full right-0 mt-1 z-50 w-52 bg-[hsl(var(--bg-primary))] dark:bg-slate-900 border border-[hsl(var(--border-primary))] rounded-lg shadow-xl p-2"
                >
                  <p className="text-[9px] font-bold uppercase tracking-wide text-slate-400 px-1 pb-1.5">Columnas visibles</p>
                  {visibleCols.map(col => {
                    const key = String(col.key);
                    const isHidden = hiddenCols.has(key);
                    return (
                      <button
                        key={key}
                        onClick={() => setHiddenCols(prev => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n; })}
                        className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-[hsl(var(--bg-muted))] transition-colors"
                      >
                        <span className="text-[12px] font-medium text-[hsl(var(--text-primary))]">{col.label || key}</span>
                        <div className={clsx('size-4 rounded border-2 flex items-center justify-center', !isHidden ? 'bg-blue-600 border-blue-600' : 'border-slate-300 dark:border-white/20')}>
                          {!isHidden && <span className="text-white text-[8px] font-bold">✓</span>}
                        </div>
                      </button>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <button
            onClick={() => gridRef.current?.api?.exportDataAsCsv()}
            title="Exportar CSV"
            className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] rounded-lg hover:bg-[hsl(var(--bg-muted))] transition-colors border border-transparent hover:border-[hsl(var(--border-primary))]"
          >
            <Download size={14} />
          </button>

          {onAddItem && (
            <button
              onClick={() => onAddItem()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors"
            >
              <Plus size={13} /> Agregar
            </button>
          )}
        </div>
      </div>

      {/* ── Filter panel ── */}
      <AnimatePresence>
        {showFilterPanel && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden shrink-0"
          >
            <div className="flex flex-col gap-2 p-3 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20">
              {filterableCols.length === 0 ? (
                <p className="text-xs text-[hsl(var(--text-secondary))] italic">No hay columnas filtrables.</p>
              ) : activeFilters.length === 0 ? (
                <p className="text-xs text-[hsl(var(--text-secondary))] italic">Sin filtros activos. Agrega uno para filtrar los datos.</p>
              ) : (
                activeFilters.map((f, idx) => (
                  <FilterRow
                    key={f.id}
                    filter={{ ...f, label: filterableCols.find(c => c.key === f.field)?.label ?? f.label }}
                    filterableCols={filterableCols}
                    onChange={updated => setActiveFilters(prev => prev.map(x => x.id === f.id ? updated : x))}
                    onRemove={() => setActiveFilters(prev => prev.filter(x => x.id !== f.id))}
                  />
                ))
              )}
              <div className="flex items-center gap-3 pt-0.5">
                <button
                  onClick={addFilter}
                  disabled={filterableCols.length === 0}
                  className="flex items-center gap-1 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:opacity-80 disabled:opacity-40 transition-opacity"
                >
                  <Plus size={12} /> Agregar filtro
                </button>
                {activeFilters.length > 0 && (
                  <button
                    onClick={() => setActiveFilters([])}
                    className="text-xs text-[hsl(var(--text-secondary))] hover:text-rose-500 transition-colors"
                  >
                    Limpiar todo
                  </button>
                )}
                <span className="ml-auto text-[10px] text-[hsl(var(--text-secondary))]">
                  {filteredData.length} de {data.length} registro{data.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Grid ── */}
      <div className="flex-1 min-h-[200px] rounded-xl overflow-hidden border border-[hsl(var(--border-primary))] relative">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-[hsl(var(--bg-primary))] z-10">
            <Loader2 size={20} className="animate-spin text-blue-600" />
          </div>
        ) : data.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center bg-[hsl(var(--bg-primary))] text-sm text-[hsl(var(--text-secondary))]">
            {emptyMessage}
          </div>
        ) : (
          <AgGridReact
            ref={gridRef}
            theme={isDark ? darkTheme : lightTheme}
            rowData={rowData as any[]}
            columnDefs={colDefs}
            defaultColDef={{ resizable: true, sortable: true, minWidth: 80 }}
            getRowId={getRowId}
            getRowHeight={getRowHeight}
            isFullWidthRow={activeGroupBy ? isFullWidthRow : undefined}
            fullWidthCellRenderer={activeGroupBy ? fullWidthCellRenderer : undefined}
            onRowClicked={handleRowClick}
            rowStyle={{ cursor: onRowClick ? 'pointer' : 'default' }}
            animateRows
            enableCellTextSelection
            singleClickEdit={!!onUpdateItem}
            stopEditingWhenCellsLoseFocus
            enterNavigatesVertically
            enterNavigatesVerticallyAfterEdit
          />
        )}
      </div>

      {/* ── Detail panel ── */}
      <AnimatePresence>
        {selectedItem && renderDetailPanel && (
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-y-0 right-0 w-[480px] z-50 shadow-2xl"
          >
            {renderDetailPanel(selectedItem, () => setSelectedItem(null))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

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
  Plus,
  Search,
  TableIcon,
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
  render?: (value: unknown, item: T) => React.ReactNode;
}

interface UniversalTableViewProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  groupBy?: string;
  viewName?: string;
  onRowClick?: (item: T) => void;
  onAddItem?: (groupValue?: string) => void;
  onUpdateItem?: (id: string | number, field: string, value: unknown) => Promise<boolean | void> | boolean | void;
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

function isPrimitive(v: unknown): boolean {
  return v === null || v === undefined || typeof v !== 'object';
}

function applyFilters<T>(data: T[], filters: ActiveFilter[]): T[] {
  if (!filters.length) return data;
  return data.filter(item =>
    filters.every(f => {
      if (!f.field) return true;
      const raw = String((item as Record<string, unknown>)[f.field] ?? '').toLowerCase().trim();
      const val = f.value.toLowerCase().trim();
      switch (f.operator) {
        case 'contains':    return raw.includes(val);
        case 'notContains': return !raw.includes(val);
        case 'equals':      return raw === val;
        case 'notEquals':   return raw !== val;
        case 'isEmpty':     return !raw;
        case 'isNotEmpty':  return !!raw;
        case 'gt': {
          const n = parseFloat(val);
          return !isNaN(n) && parseFloat(raw) > n;
        }
        case 'lt': {
          const n = parseFloat(val);
          return !isNaN(n) && parseFloat(raw) < n;
        }
        default: return true;
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
  inactivo:      { label: 'Inactivo',    bg: 'bg-slate-100 dark:bg-white/5',         text: 'text-slate-500 dark:text-slate-400',     dot: 'bg-slate-400'    },
  habilitado:    { label: 'Abierta',     bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-400', dot: 'bg-emerald-500'  },
  deshabilitado: { label: 'Bloqueada',   bg: 'bg-amber-50 dark:bg-amber-900/20',     text: 'text-amber-700 dark:text-amber-400',     dot: 'bg-amber-400'    },
  cerrado:       { label: 'Cerrada',     bg: 'bg-slate-100 dark:bg-white/5',         text: 'text-slate-500 dark:text-slate-400',     dot: 'bg-slate-400'    },
  cancelada:     { label: 'Cancelada',   bg: 'bg-rose-50 dark:bg-rose-900/20',       text: 'text-rose-700 dark:text-rose-400',       dot: 'bg-rose-500'     },
};
function getStatus(v: string) {
  return STATUS_MAP[String(v ?? '').toLowerCase()] ?? {
    label: String(v ?? '—'),
    bg: 'bg-slate-100 dark:bg-white/5',
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

function StatusCell({ value }: { value: unknown }) {
  const st = getStatus(String(value ?? ''));
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-[3px] rounded-full text-[11px] font-semibold leading-none', st.bg, st.text)}>
      <span className={clsx('size-1.5 rounded-full shrink-0', st.dot)} />
      {st.label}
    </span>
  );
}
function PriorityCell({ value }: { value: unknown }) {
  const p = PRIORITY_MAP[String(value ?? '').toLowerCase()] ?? PRIORITY_MAP.normal;
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-[3px] rounded-full text-[11px] font-semibold', p.bg, p.color)}>
      <Flag size={9} /> {p.label}
    </span>
  );
}
function DateCell({ value }: { value: unknown }) {
  if (!value) return <span className="text-slate-300 dark:text-slate-600 text-xs">—</span>;
  const d = new Date(String(value));
  if (isNaN(d.getTime())) return <span className="text-slate-300 dark:text-slate-600 text-xs">—</span>;
  return (
    <div className="flex items-center gap-1.5 text-slate-400 dark:text-slate-500">
      <Calendar size={11} className="shrink-0" />
      <span className="text-[12px] font-medium tabular-nums whitespace-nowrap">
        {d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: '2-digit' })}
      </span>
    </div>
  );
}
function UserCell({ value }: { value: unknown }) {
  if (!value) return <span className="text-slate-300 dark:text-slate-600 text-[12px]">—</span>;
  const words = String(value).split(/\s+/).filter(Boolean);
  const initials = words.slice(0, 2).map(w => w[0]).join('').toUpperCase();
  return (
    <div className="flex items-center gap-2 h-full">
      <div className="size-6 rounded-full bg-[hsl(var(--primary)/0.12)] dark:bg-[hsl(var(--primary)/0.25)] flex items-center justify-center font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] text-[9px] shrink-0 leading-none">
        {initials || <User size={10} className="text-slate-400" />}
      </div>
      <span className="text-[12px] text-[hsl(var(--text-primary))] font-medium truncate">{String(value)}</span>
    </div>
  );
}
function IdCell({ value }: { value: unknown }) {
  return (
    <div className="flex items-center gap-1 text-[11px] font-mono font-bold text-slate-300 dark:text-slate-600">
      <Hash size={9} />{String(value ?? '').substring(0, 8)}
    </div>
  );
}
function ProgressCell({ value }: { value: unknown }) {
  const raw = Number(value || 0);
  const pct = isNaN(raw) ? 0 : Math.round(raw <= 1 ? raw * 100 : raw);
  const color = pct === 100 ? 'bg-emerald-500' : pct >= 60 ? 'bg-blue-500' : 'bg-amber-400';
  return (
    <div className="flex items-center gap-2.5 w-full pr-2">
      <div className="flex-1 h-1.5 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
        <div className={clsx('h-full rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-semibold text-[hsl(var(--text-secondary))] tabular-nums text-[11px] w-7 text-right shrink-0">{pct}%</span>
    </div>
  );
}

// ─── FilterRow ────────────────────────────────────────────────────────────────

function FilterRow({
  filter,
  filterIdx,
  filterableCols,
  onChange,
  onRemove,
}: {
  filter: ActiveFilter;
  filterIdx: number;
  filterableCols: { key: string; label: string; type: ColumnType }[];
  onChange: (updated: ActiveFilter) => void;
  onRemove: () => void;
}) {
  const colType = filterableCols.find(c => c.key === filter.field)?.type ?? 'text';
  const ops = OPERATORS_BY_TYPE[colType] ?? OPERATORS_BY_TYPE.text;
  const needsValue = !['isEmpty', 'isNotEmpty'].includes(filter.operator);
  const selectCls = 'h-7 px-2 text-[11px] font-medium rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.5)] cursor-pointer';

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] w-10 text-right shrink-0 uppercase tracking-wide">
        {filterIdx === 0 ? 'Donde' : 'Y'}
      </span>
      <select
        value={filter.field}
        onChange={e => {
          const col = filterableCols.find(c => c.key === e.target.value);
          const newOps = OPERATORS_BY_TYPE[col?.type ?? 'text'] ?? OPERATORS_BY_TYPE.text;
          onChange({ ...filter, field: e.target.value, label: col?.label ?? e.target.value, operator: newOps[0], value: '' });
        }}
        className={selectCls}
      >
        {filterableCols.map(c => <option key={c.key} value={c.key}>{c.label}</option>)}
      </select>
      <select
        value={filter.operator}
        onChange={e => onChange({ ...filter, operator: e.target.value as FilterOperator, value: '' })}
        className={selectCls}
      >
        {ops.map(op => <option key={op} value={op}>{OPERATOR_LABELS[op]}</option>)}
      </select>
      {needsValue && (
        <input
          type="text"
          value={filter.value}
          onChange={e => onChange({ ...filter, value: e.target.value })}
          placeholder="Valor…"
          className="h-7 px-2.5 text-[11px] rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.5)] min-w-[100px] max-w-[160px]"
        />
      )}
      <button
        onClick={onRemove}
        className="p-1 rounded-md text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"
      >
        <X size={12} />
      </button>
    </div>
  );
}

// ─── Skeleton loader ──────────────────────────────────────────────────────────

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <div className="flex items-center gap-4 px-4 py-2.5 border-b border-[hsl(var(--border-primary))] last:border-0">
      {Array.from({ length: cols }).map((_, i) => (
        <div key={i} className="h-4 rounded-md bg-slate-100 dark:bg-white/5 animate-pulse flex-1"
          style={{ maxWidth: i === 0 ? 200 : 100, opacity: Math.max(1 - i * 0.12, 0.2) }} />
      ))}
    </div>
  );
}

// ─── AG Grid themes ───────────────────────────────────────────────────────────

const lightTheme = themeQuartz.withParams({
  fontFamily: 'inherit',
  fontSize: 12.5,
  rowHeight: 42,
  headerHeight: 40,
  backgroundColor: '#ffffff',
  foregroundColor: '#0f172a',
  borderColor: '#e2e8f0',
  oddRowBackgroundColor: '#ffffff',
  rowHoverColor: '#f8fafc',
  headerBackgroundColor: '#f8fafc',
  headerTextColor: '#64748b',
  headerFontSize: 11,
  headerFontWeight: 700,
  selectedRowBackgroundColor: '#eef2ff',
  accentColor: '#6366f1',
  cellHorizontalPaddingScale: 1,
  rowBorder: { style: 'solid', width: 1, color: '#f1f5f9' },
  columnBorder: false,
  wrapperBorder: false,
});

const darkTheme = themeQuartz.withParams({
  fontFamily: 'inherit',
  fontSize: 12.5,
  rowHeight: 42,
  headerHeight: 40,
  backgroundColor: 'hsl(222 47% 11%)',
  foregroundColor: '#e2e8f0',
  borderColor: 'rgba(255,255,255,0.06)',
  oddRowBackgroundColor: 'hsl(222 47% 11%)',
  rowHoverColor: 'rgba(255,255,255,0.03)',
  headerBackgroundColor: 'rgba(255,255,255,0.03)',
  headerTextColor: '#64748b',
  headerFontSize: 11,
  headerFontWeight: 700,
  selectedRowBackgroundColor: 'rgba(99,102,241,0.12)',
  accentColor: '#6366f1',
  cellHorizontalPaddingScale: 1,
  rowBorder: { style: 'solid', width: 1, color: 'rgba(255,255,255,0.04)' },
  columnBorder: false,
  wrapperBorder: false,
});

// ─── Module-level constants (no re-creation per render) ───────────────────────

const GROUP_ROW_ID_PREFIX = '__group__';

const BTN_BASE = 'flex items-center gap-1.5 h-8 text-[11px] font-semibold rounded-lg transition-all border';
const BTN_IDLE = 'px-2.5 bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border-primary))] hover:bg-[hsl(var(--bg-muted))] hover:text-[hsl(var(--text-primary))]';
const BTN_ICON = 'px-2 bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border-primary))] hover:bg-[hsl(var(--bg-muted))] hover:text-[hsl(var(--text-primary))]';
const BTN_ACTIVE = 'px-2.5 bg-[hsl(var(--primary)/0.06)] dark:bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] border-[hsl(var(--primary)/0.2)] dark:border-[hsl(var(--primary)/0.3)]';

// ─── makeValueSetter ──────────────────────────────────────────────────────────

function makeValueSetter(
  field: string,
  onUpdateItem: NonNullable<UniversalTableViewProps<{ id: string | number }>['onUpdateItem']>,
) {
  return (params: { oldValue: unknown; newValue: unknown; data: { id: string | number }; api: { applyTransaction: (t: object) => void } }) => {
    if (params.oldValue === params.newValue) return false;
    const result = onUpdateItem(params.data.id, field, params.newValue);
    if (result instanceof Promise) {
      result.then(ok => { if (ok === false) params.api.applyTransaction({ update: [params.data] }); });
      return true;
    }
    return result !== false;
  };
}

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
  const [isDark, setIsDark] = useState(false);
  const [quickFilter, setQuickFilter] = useState('');
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(() => new Set(loadState(viewName)?.hiddenCols ?? []));
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>(() => loadState(viewName)?.filters ?? []);
  const [activeGroupBy, setActiveGroupBy] = useState<string | null>(() => loadState(viewName)?.groupBy ?? groupByProp ?? null);
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [showColPanel, setShowColPanel] = useState(false);
  const [showGroupPanel, setShowGroupPanel] = useState(false);
  const [selectedItem, setSelectedItem] = useState<T | null>(null);

  const filterIdRef = useRef(1000);
  const gridRef = useRef<AgGridReact>(null);
  const colPanelRef = useRef<HTMLDivElement>(null);
  const groupPanelRef = useRef<HTMLDivElement>(null);

  // Dark mode
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

  // Persist state
  useEffect(() => {
    saveState(viewName, { hiddenCols: [...hiddenCols], filters: activeFilters, groupBy: activeGroupBy });
  }, [viewName, hiddenCols, activeFilters, activeGroupBy]);

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

  const filteredData = useMemo(() => {
    let result = applyFilters(data, activeFilters);
    const q = quickFilter.trim().toLowerCase();
    if (q) {
      result = result.filter(item =>
        Object.values(item as Record<string, unknown>)
          .filter(isPrimitive)
          .some(v => String(v ?? '').toLowerCase().includes(q))
      );
    }
    return result;
  }, [data, activeFilters, quickFilter]);

  const rowData = useMemo(() => {
    if (!activeGroupBy) return filteredData;
    const groups: Record<string, T[]> = {};
    filteredData.forEach(item => {
      const k = String((item as Record<string, unknown>)[activeGroupBy] || 'Sin categoría');
      if (!groups[k]) groups[k] = [];
      groups[k].push(item);
    });
    const flat: unknown[] = [];
    Object.entries(groups).forEach(([key, rows]) => {
      flat.push({ __isGroup: true, __groupKey: key, __groupCount: rows.length, id: `${GROUP_ROW_ID_PREFIX}${key}` });
      flat.push(...rows);
    });
    return flat;
  }, [filteredData, activeGroupBy]);

  const colDefs = useMemo<ColDef[]>(() => {
    return columns
      .filter(c => !c.hidden && !hiddenCols.has(String(c.key)))
      .map((col): ColDef => {
        const field = String(col.key);
        const canEdit = col.editable !== false && !!onUpdateItem;

        const base: ColDef = {
          field,
          headerName: col.label,
          width: col.width ? parseInt(col.width) : undefined,
          flex: col.width ? undefined : 1,
          minWidth: 80,
          resizable: true,
          sortable: col.sortable !== false,
          filter: false,
          floatingFilter: false,
        };

        if (canEdit) {
          base.editable = true;
          base.singleClickEdit = true;
          base.cellEditor = 'agTextCellEditor';
          base.valueSetter = makeValueSetter(field, onUpdateItem!) as ColDef['valueSetter'];
        }

        if (col.render) {
          const renderFn = col.render;
          base.cellRenderer = ({ value, data: rowData }: { value: unknown; data: Record<string, unknown> }) => {
            if (rowData?.__isGroup) return null;
            return <>{renderFn(value, rowData as T)}</>;
          };
          if (!canEdit) base.editable = false;
        } else {
          switch (col.type) {
            case 'status':   base.cellRenderer = StatusCell; break;
            case 'priority': base.cellRenderer = PriorityCell; break;
            case 'date':     base.cellRenderer = DateCell; break;
            case 'user':     base.cellRenderer = UserCell; break;
            case 'id':       base.cellRenderer = IdCell; break;
            case 'progress': base.cellRenderer = ProgressCell; break;
            default:
              base.cellStyle = { fontSize: '12.5px', fontWeight: '500', color: 'inherit' };
              break;
          }
        }
        return base;
      });
  }, [columns, hiddenCols, onUpdateItem]);

  const isFullWidthRow = useCallback((params: { rowNode: { data?: Record<string, unknown> } }) =>
    !!params.rowNode.data?.__isGroup, []);

  const fullWidthCellRenderer = useCallback(({ data: row }: { data: { __groupKey: string; __groupCount: number } }) => (
    <div className="flex items-center gap-2.5 px-4 h-full border-b border-[hsl(var(--border-primary))] bg-slate-50/80 dark:bg-white/[0.02]">
      <div className="w-1 h-4 rounded-full bg-[hsl(var(--primary))] dark:bg-[hsl(var(--primary)/0.06)]0 shrink-0" />
      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">{row.__groupKey}</span>
      <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 bg-slate-200 dark:bg-white/10 rounded-full px-2 py-0.5 ml-0.5">
        {row.__groupCount}
      </span>
      {onAddItem && (
        <button onClick={(e) => { e.stopPropagation(); onAddItem(row.__groupKey); }}
          className="ml-auto flex items-center gap-1 text-[10px] font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] hover:opacity-70 transition-opacity">
          <Plus size={10} /> Agregar
        </button>
      )}
    </div>
  ), [onAddItem]);

  const getRowId = useCallback((params: GetRowIdParams) => String((params.data as { id: unknown }).id), []);
  const getRowHeight = useCallback((params: { data?: Record<string, unknown> }) =>
    params.data?.__isGroup ? 34 : 42, []);
  const handleRowClick = useCallback((e: { data?: Record<string, unknown> }) => {
    if (e.data?.__isGroup) return;
    setSelectedItem(e.data as T);
    onRowClick?.(e.data as T);
  }, [onRowClick]);

  // Stable row style object (avoids AG Grid re-render on every parent render)
  const rowStyle = useMemo(() => ({ cursor: onRowClick ? 'pointer' : 'default' as const }), [onRowClick]);

  const visibleCols = useMemo(() => columns.filter(c => !c.hidden), [columns]);
  const activeGroupByLabel = useMemo(() =>
    groupableCols.find(c => String(c.key) === activeGroupBy)?.label,
    [groupableCols, activeGroupBy]
  );

  const hasData = data.length > 0;
  const hasResults = filteredData.length > 0;
  const isFiltered = activeFilters.length > 0 || quickFilter.trim().length > 0;

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex min-w-0 flex-col h-full gap-2">

      {/* ── Toolbar ── */}
      <div className="flex min-w-0 items-center gap-1.5 flex-wrap shrink-0">

        {/* Search */}
        <div className="relative flex-1 min-w-[min(100%,180px)] max-w-[280px]">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            value={quickFilter}
            onChange={e => setQuickFilter(e.target.value)}
            placeholder="Buscar…"
            className="w-full h-8 pl-7 pr-7 text-[11px] border border-[hsl(var(--border-primary))] rounded-lg bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] placeholder-slate-400 outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.5)] transition-shadow"
          />
          {quickFilter && (
            <button onClick={() => setQuickFilter('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5 rounded">
              <X size={11} />
            </button>
          )}
        </div>

        <div className="w-px h-5 bg-[hsl(var(--border-primary))] hidden sm:block" />

        {/* Filters */}
        <button
          onClick={() => setShowFilterPanel(p => !p)}
          className={clsx(BTN_BASE, showFilterPanel || activeFilters.length > 0 ? BTN_ACTIVE : BTN_IDLE)}
        >
          <Filter size={12} />
          Filtros
          {activeFilters.length > 0 && (
            <span className="ml-0.5 min-w-[16px] h-4 px-1 rounded-full bg-[hsl(var(--primary))] text-white text-[9px] font-bold leading-4 text-center">
              {activeFilters.length}
            </span>
          )}
        </button>

        {/* Group by */}
        {groupableCols.length > 0 && (
          <div className="relative" ref={groupPanelRef}>
            <button
              onClick={() => setShowGroupPanel(p => !p)}
              className={clsx(BTN_BASE, activeGroupBy ? BTN_ACTIVE : BTN_IDLE)}
            >
              <Layers size={12} />
              {activeGroupByLabel ?? 'Agrupar'}
              <ChevronDown size={11} className="opacity-60" />
            </button>
            <AnimatePresence>
              {showGroupPanel && (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.97 }}
                  transition={{ duration: 0.12 }}
                  className="absolute top-full left-0 mt-1.5 z-50 w-48 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl shadow-2xl shadow-black/10 dark:shadow-black/40 py-1.5 overflow-hidden"
                >
                  <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 px-3 py-1.5">Agrupar por</p>
                  {[{ key: null, label: 'Sin agrupar' }, ...groupableCols.map(c => ({ key: String(c.key), label: c.label }))].map(opt => (
                    <button
                      key={opt.key ?? '__none'}
                      onClick={() => { setActiveGroupBy(opt.key); setShowGroupPanel(false); }}
                      className={clsx('w-full text-left px-3 py-2 text-[12px] transition-colors hover:bg-[hsl(var(--bg-muted))]',
                        activeGroupBy === opt.key ? 'text-[hsl(var(--primary))] font-semibold' : 'text-[hsl(var(--text-primary))] font-medium')}
                    >
                      {opt.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Right actions */}
        <div className="flex min-w-0 items-center gap-1.5 ml-0 sm:ml-auto overflow-x-auto">
          {!isLoading && hasData && (
            <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 tabular-nums hidden sm:block pr-1">
              {isFiltered ? `${filteredData.length} / ${data.length}` : data.length}
            </span>
          )}

          {/* Columns */}
          <div className="relative" ref={colPanelRef}>
            <button
              onClick={() => setShowColPanel(p => !p)}
              title="Columnas visibles"
              className={clsx(BTN_BASE, showColPanel ? BTN_ACTIVE.replace('px-2.5', 'px-2') : BTN_ICON)}
            >
              <ColumnsIcon size={13} />
              {hiddenCols.size > 0 && (
                <span className="min-w-[14px] h-3.5 px-1 rounded-full bg-[hsl(var(--primary))] text-white text-[8px] font-bold leading-[14px] text-center">
                  {hiddenCols.size}
                </span>
              )}
            </button>
            <AnimatePresence>
              {showColPanel && (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.97 }}
                  transition={{ duration: 0.12 }}
                  className="absolute top-full right-0 mt-1.5 z-50 w-52 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl shadow-2xl shadow-black/10 dark:shadow-black/40 p-2"
                >
                  <div className="flex items-center justify-between px-1.5 pb-1.5">
                    <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Columnas visibles</p>
                    {hiddenCols.size > 0 && (
                      <button onClick={() => setHiddenCols(new Set())}
                        className="text-[9px] font-semibold text-[hsl(var(--primary))] hover:opacity-75 transition-opacity">
                        Mostrar todo
                      </button>
                    )}
                  </div>
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
                        <div className={clsx('size-4 rounded-md border-2 flex items-center justify-center transition-colors',
                          !isHidden ? 'bg-[hsl(var(--primary))] border-[hsl(var(--primary))]' : 'border-slate-300 dark:border-white/20')}>
                          {!isHidden && <span className="text-white text-[8px] font-bold leading-none">✓</span>}
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
            className={clsx(BTN_BASE, BTN_ICON)}
          >
            <Download size={13} />
          </button>

          {onAddItem && (
            <button
              onClick={() => onAddItem()}
              className="flex items-center gap-1.5 h-8 px-3 text-[11px] font-bold rounded-lg bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.85)] text-white transition-colors shadow-sm shadow-[hsl(var(--primary)/0.2)]"
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
            <div className="flex flex-col gap-2 p-3 rounded-xl border border-[hsl(var(--primary)/0.1)] dark:border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--primary)/0.06)] dark:bg-[hsl(var(--primary)/0.15)]">
              {filterableCols.length === 0 ? (
                <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">No hay columnas filtrables.</p>
              ) : activeFilters.length === 0 ? (
                <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Sin filtros activos. Agrega uno para filtrar los datos.</p>
              ) : (
                activeFilters.map((f, idx) => (
                  <FilterRow
                    key={f.id}
                    filter={{ ...f, label: filterableCols.find(c => c.key === f.field)?.label ?? f.label }}
                    filterIdx={idx}
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
                  className="flex items-center gap-1 text-[11px] font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] hover:opacity-75 disabled:opacity-40 transition-opacity"
                >
                  <Plus size={12} /> Agregar filtro
                </button>
                {activeFilters.length > 0 && (
                  <button onClick={() => setActiveFilters([])}
                    className="text-[11px] text-[hsl(var(--text-secondary))] hover:text-rose-500 transition-colors">
                    Limpiar todo
                  </button>
                )}
                <span className="ml-auto text-[10px] font-medium text-[hsl(var(--text-secondary))]">
                  {filteredData.length} de {data.length} registro{data.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Grid ── */}
      <div className="flex-1 min-w-0 min-h-[200px] rounded-xl overflow-hidden border border-[hsl(var(--border-primary))] relative">
        {isLoading ? (
          <div className="bg-[hsl(var(--bg-primary))] h-full">
            <div className="flex items-center px-4 border-b border-[hsl(var(--border-primary))] h-10 gap-4">
              {[200, 120, 90, 110, 80].map((w, i) => (
                <div key={i} className="h-3 rounded-md bg-slate-100 dark:bg-white/5 animate-pulse" style={{ width: w }} />
              ))}
            </div>
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonRow key={i} cols={5} />
            ))}
          </div>
        ) : !hasData ? (
          /* Genuinely empty — no data at all */
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[hsl(var(--bg-primary))]">
            <div className="w-12 h-12 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center">
              <TableIcon size={22} className="text-slate-300 dark:text-slate-600" />
            </div>
            <div className="text-center">
              <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{emptyMessage}</p>
              {onAddItem && (
                <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5">Agrega el primer registro para comenzar</p>
              )}
            </div>
            {onAddItem && (
              <button onClick={() => onAddItem()}
                className="flex items-center gap-1.5 px-4 py-2 text-[12px] font-bold rounded-lg bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.85)] text-white transition-colors mt-1">
                <Plus size={13} /> Agregar
              </button>
            )}
          </div>
        ) : !hasResults ? (
          /* Has data but filters eliminated everything */
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-[hsl(var(--bg-primary))]">
            <Search size={20} className="text-slate-300 dark:text-slate-600" />
            <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">Sin resultados</p>
            <p className="text-[11px] text-[hsl(var(--text-secondary))]">Prueba con otro término o limpia los filtros</p>
            <button onClick={() => { setQuickFilter(''); setActiveFilters([]); }}
              className="text-[11px] font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] hover:opacity-75 mt-1 transition-opacity">
              Limpiar filtros
            </button>
          </div>
        ) : (
          <AgGridReact
            ref={gridRef}
            theme={isDark ? darkTheme : lightTheme}
            rowData={rowData as Record<string, unknown>[]}
            columnDefs={colDefs}
            defaultColDef={{ resizable: true, sortable: true, minWidth: 80 }}
            getRowId={getRowId}
            getRowHeight={getRowHeight}
            isFullWidthRow={activeGroupBy ? isFullWidthRow : undefined}
            fullWidthCellRenderer={activeGroupBy ? fullWidthCellRenderer : undefined}
            onRowClicked={handleRowClick}
            rowStyle={rowStyle}
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
            className="fixed inset-y-0 right-0 w-full sm:w-[480px] z-50 shadow-2xl"
          >
            {renderDetailPanel(selectedItem, () => setSelectedItem(null))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

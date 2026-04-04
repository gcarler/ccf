"use client";

import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
    Plus, Flag, Calendar, User, MoreHorizontal, ChevronDown,
    Search, Filter, ArrowUpDown, Circle,
    LayoutGrid, List as ListIcon, Columns as ColumnsIcon, Settings2,
    ChevronRight, Hash, Clock, ArrowUp, ArrowDown, X, SortAsc, Eye, EyeOff,
    GripVertical, Trash2, Check
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

// ─── STATUS CONFIG ─────────────────────────────────────────────────────────────
// Colores idénticos a la referencia de NocoDB: chips con fondo sólido + texto

const STATUS_CONFIG: Record<string, {
    label: string;
    chipBg: string;
    chipText: string;
    chipBorder: string;
    dot: string;
}> = {
    todo:        { label: 'No iniciada',  chipBg: 'bg-amber-50',    chipText: 'text-amber-700',   chipBorder: 'border-amber-200',   dot: 'bg-amber-400' },
    in_progress: { label: 'En progreso',  chipBg: 'bg-emerald-50',  chipText: 'text-emerald-700', chipBorder: 'border-emerald-300', dot: 'bg-emerald-500' },
    review:      { label: 'En revisión',  chipBg: 'bg-violet-50',   chipText: 'text-violet-700',  chipBorder: 'border-violet-200',  dot: 'bg-violet-500' },
    done:        { label: 'Terminada',    chipBg: 'bg-sky-50',      chipText: 'text-sky-700',     chipBorder: 'border-sky-200',     dot: 'bg-sky-500' },
    blocked:     { label: 'Bloqueada',    chipBg: 'bg-rose-50',     chipText: 'text-rose-700',    chipBorder: 'border-rose-200',    dot: 'bg-rose-500' },
};

// ─── PRIORITY CONFIG ───────────────────────────────────────────────────────────

const PRIORITY_STYLES: Record<string, { label: string; color: string; bg: string; border: string }> = {
    urgent: { label: 'Urgente', color: 'text-rose-700',   bg: 'bg-rose-50',   border: 'border-rose-200' },
    high:   { label: 'Alta',    color: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-200' },
    medium: { label: 'Media',   color: 'text-amber-700',  bg: 'bg-amber-50',  border: 'border-amber-200' },
    normal: { label: 'Normal',  color: 'text-blue-700',   bg: 'bg-blue-50',   border: 'border-blue-200' },
    low:    { label: 'Baja',    color: 'text-slate-500',  bg: 'bg-slate-50',  border: 'border-slate-200' },
};

// ─── TYPES ─────────────────────────────────────────────────────────────────────

export type ColumnType = 'text' | 'status' | 'priority' | 'user' | 'date' | 'progress' | 'tag' | 'id';

export interface TableColumn<T> {
    key: keyof T | string;
    label: string;
    type: ColumnType;
    width?: string;
    sortable?: boolean;
    hidden?: boolean;
    render?: (value: any, item: T) => React.ReactNode;
}

interface SortRule {
    key: string;
    dir: 'asc' | 'desc';
}

interface FilterRule {
    key: string;
    value: string;
    label: string;
}

interface UniversalTableViewProps<T> {
    data: T[];
    columns: TableColumn<T>[];
    groupBy?: keyof T;
    title?: string;
    onRowClick?: (item: T) => void;
    onAddItem?: (groupValue?: string) => void;
    onUpdateItem?: (id: string, field: keyof T, value: any) => void;
    isLoading?: boolean;
    emptyMessage?: string;
}

// ─── STATUS CHIP ───────────────────────────────────────────────────────────────

function StatusChip({ value }: { value: string }) {
    const st = STATUS_CONFIG[String(value).toLowerCase()] ?? STATUS_CONFIG.todo;
    return (
        <span className={clsx(
            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-[11px] font-semibold leading-none',
            st.chipBg, st.chipText, st.chipBorder
        )}>
            {st.label}
        </span>
    );
}

// ─── TABLE CELL ───────────────────────────────────────────────────────────────

function TableCell<T>({ column, value, item }: { column: TableColumn<T>; value: any; item: T }) {
    if (column.render) return <>{column.render(value, item)}</>;

    switch (column.type) {
        case 'id':
            return (
                <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-300 uppercase tracking-widest">
                    <Hash size={10} /> {String(value).substring(0, 4)}
                </div>
            );
        case 'status':
            return <StatusChip value={String(value)} />;
        case 'priority':
            const prio = PRIORITY_STYLES[String(value).toLowerCase()] ?? PRIORITY_STYLES.normal;
            return (
                <span className={clsx(
                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-[11px] font-semibold leading-none',
                    prio.bg, prio.color, prio.border
                )}>
                    <Flag size={10} />
                    {prio.label}
                </span>
            );
        case 'user':
            return (
                <div className="flex items-center gap-2">
                    <div className="size-6 rounded-full bg-gradient-to-tr from-slate-100 to-slate-200 dark:from-white/5 dark:to-white/10 flex items-center justify-center border border-slate-200 dark:border-white/5 shrink-0">
                        <User size={11} className="text-slate-400" />
                    </div>
                    <span className="text-[12px] text-slate-600 dark:text-slate-400 truncate font-medium">
                        {value ? String(value) : 'Sin asignar'}
                    </span>
                </div>
            );
        case 'date':
            return (
                <div className="flex items-center gap-1.5 text-slate-400">
                    <Calendar size={12} className="shrink-0" />
                    <span className="text-[12px] font-medium whitespace-nowrap">
                        {value ? new Date(String(value)).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: '2-digit' }) : '—'}
                    </span>
                </div>
            );
        case 'progress':
            const progress = Number(value || 0);
            return (
                <div className="flex items-center gap-3 w-full max-w-[120px]">
                    <div className="flex-1 h-1.5 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                            className={clsx(
                                "h-full rounded-full transition-all duration-500",
                                progress === 100 ? "bg-emerald-500" : "bg-violet-500"
                            )}
                        />
                    </div>
                    <span className="text-[10px] font-black text-slate-400 w-8 tabular-nums tracking-tighter">
                        {progress}%
                    </span>
                </div>
            );
        default:
            return (
                <span className="text-[13px] font-medium text-slate-700 dark:text-slate-200 line-clamp-1">
                    {String(value ?? '')}
                </span>
            );
    }
}

// ─── SORT PANEL ───────────────────────────────────────────────────────────────

function SortPanel<T>({
    columns,
    sorts,
    onSortsChange,
    onClose,
}: {
    columns: TableColumn<T>[];
    sorts: SortRule[];
    onSortsChange: (s: SortRule[]) => void;
    onClose: () => void;
}) {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) onClose();
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [onClose]);

    const addSort = () => {
        const col = columns.find(c => !sorts.some(s => s.key === String(c.key)));
        if (col) onSortsChange([...sorts, { key: String(col.key), dir: 'asc' }]);
    };

    const removeSort = (idx: number) => {
        onSortsChange(sorts.filter((_, i) => i !== idx));
    };

    const updateSort = (idx: number, patch: Partial<SortRule>) => {
        onSortsChange(sorts.map((s, i) => i === idx ? { ...s, ...patch } : s));
    };

    const applyAndClose = () => onClose();

    const colOptions = columns.filter(c => c.sortable !== false);

    return (
        <motion.div
            ref={ref}
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-1 z-50 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-xl shadow-xl min-w-[460px] p-4"
        >
            <div className="space-y-2 mb-4">
                {sorts.length === 0 && (
                    <p className="text-[12px] text-slate-400 text-center py-2">Sin criterios de ordenamiento</p>
                )}
                {sorts.map((rule, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                        <GripVertical size={14} className="text-slate-300 shrink-0" />
                        <select
                            value={rule.key}
                            onChange={e => updateSort(idx, { key: e.target.value })}
                            className="flex-1 text-[12px] font-semibold text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400"
                        >
                            {colOptions.map(c => (
                                <option key={String(c.key)} value={String(c.key)}>{c.label}</option>
                            ))}
                        </select>
                        <div className="flex items-center bg-slate-100 dark:bg-white/5 rounded-lg overflow-hidden border border-slate-200 dark:border-white/10">
                            <button
                                onClick={() => updateSort(idx, { dir: 'asc' })}
                                className={clsx('flex items-center gap-1.5 px-3 py-2 text-[11px] font-bold transition-colors',
                                    rule.dir === 'asc'
                                        ? 'bg-blue-500 text-white'
                                        : 'text-slate-500 hover:text-slate-700'
                                )}
                            >
                                <ArrowUp size={12} /> Asc.
                            </button>
                            <button
                                onClick={() => updateSort(idx, { dir: 'desc' })}
                                className={clsx('flex items-center gap-1.5 px-3 py-2 text-[11px] font-bold transition-colors',
                                    rule.dir === 'desc'
                                        ? 'bg-blue-500 text-white'
                                        : 'text-slate-500 hover:text-slate-700'
                                )}
                            >
                                <ArrowDown size={12} /> Desc.
                            </button>
                        </div>
                        <button
                            onClick={() => removeSort(idx)}
                            className="size-8 flex items-center justify-center text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-colors shrink-0"
                        >
                            <Trash2 size={13} />
                        </button>
                    </div>
                ))}
            </div>

            <div className="flex items-center justify-between border-t border-slate-100 dark:border-white/5 pt-3">
                <button
                    onClick={addSort}
                    className="flex items-center gap-1.5 text-[12px] font-bold text-blue-500 hover:text-blue-700 transition-colors"
                >
                    <Plus size={13} /> Agregar criterio
                </button>
                <button
                    onClick={applyAndClose}
                    className="px-4 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-[12px] font-bold rounded-lg transition-colors"
                >
                    Aplicar
                </button>
            </div>
        </motion.div>
    );
}

// ─── FILTER PANEL ─────────────────────────────────────────────────────────────

function FilterPanel<T>({
    columns,
    filters,
    onFiltersChange,
    onClose,
}: {
    columns: TableColumn<T>[];
    filters: FilterRule[];
    onFiltersChange: (f: FilterRule[]) => void;
    onClose: () => void;
}) {
    const ref = useRef<HTMLDivElement>(null);
    const [pendingKey, setPendingKey] = useState(String(columns[0]?.key ?? ''));
    const [pendingVal, setPendingVal] = useState('');

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) onClose();
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [onClose]);

    const addFilter = () => {
        if (!pendingVal.trim()) return;
        const col = columns.find(c => String(c.key) === pendingKey);
        onFiltersChange([...filters, { key: pendingKey, value: pendingVal, label: col?.label ?? pendingKey }]);
        setPendingVal('');
    };

    // Status-specific quick filters
    const STATUS_OPTIONS = Object.entries(STATUS_CONFIG).map(([k, v]) => ({ key: k, label: v.label }));

    return (
        <motion.div
            ref={ref}
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-1 z-50 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-xl shadow-xl min-w-[380px] p-4"
        >
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">
                Agregar filtro
            </p>

            <div className="flex gap-2 mb-4">
                <select
                    value={pendingKey}
                    onChange={e => setPendingKey(e.target.value)}
                    className="flex-1 text-[12px] font-semibold text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400"
                >
                    {columns.map(c => (
                        <option key={String(c.key)} value={String(c.key)}>{c.label}</option>
                    ))}
                </select>
                <input
                    type="text"
                    value={pendingVal}
                    onChange={e => setPendingVal(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && addFilter()}
                    placeholder="Valor..."
                    className="flex-1 text-[12px] text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400 placeholder:text-slate-400"
                />
                <button
                    onClick={addFilter}
                    className="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                >
                    <Plus size={14} />
                </button>
            </div>

            {/* Quick-filter por Status */}
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Estado rápido</p>
                <div className="flex flex-wrap gap-1.5">
                    {STATUS_OPTIONS.map(opt => {
                        const active = filters.some(f => f.key === 'status' && f.value === opt.key);
                        const cfg = STATUS_CONFIG[opt.key];
                        return (
                            <button
                                key={opt.key}
                                onClick={() => {
                                    if (active) {
                                        onFiltersChange(filters.filter(f => !(f.key === 'status' && f.value === opt.key)));
                                    } else {
                                        onFiltersChange([...filters, { key: 'status', value: opt.key, label: 'Estado' }]);
                                    }
                                }}
                                className={clsx(
                                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-[11px] font-semibold transition-all',
                                    active
                                        ? clsx(cfg.chipBg, cfg.chipText, cfg.chipBorder, 'ring-2 ring-offset-1 ring-blue-400')
                                        : 'bg-slate-50 text-slate-500 border-slate-200 hover:border-slate-300'
                                )}
                            >
                                {active && <Check size={10} />}
                                {opt.label}
                            </button>
                        );
                    })}
                </div>
            </div>
        </motion.div>
    );
}

// ─── COMPONENTE PRINCIPAL ──────────────────────────────────────────────────────

export default function UniversalTableView<T extends { id: string | number }>({
    data,
    columns,
    groupBy,
    title,
    onRowClick,
    onAddItem,
    onUpdateItem,
    isLoading,
    emptyMessage = "No hay registros para mostrar"
}: UniversalTableViewProps<T>) {
    const [searchTerm, setSearchTerm]     = useState('');
    const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
    const [sorts, setSorts]               = useState<SortRule[]>([]);
    const [filters, setFilters]           = useState<FilterRule[]>([]);
    const [showSort, setShowSort]         = useState(false);
    const [showFilter, setShowFilter]     = useState(false);
    const [hiddenCols, setHiddenCols]     = useState<Set<string>>(new Set());
    const [showColConfig, setShowColConfig] = useState(false);
    const colConfigRef = useRef<HTMLDivElement>(null);

    // Cerrar colConfig al click fuera
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (colConfigRef.current && !colConfigRef.current.contains(e.target as Node)) {
                setShowColConfig(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    // Filter → Sort → Search
    const processedData = useMemo(() => {
        let result = [...data];

        // Apply filters
        filters.forEach(f => {
            result = result.filter(item => {
                const val = String((item as any)[f.key] ?? '').toLowerCase();
                return val.includes(f.value.toLowerCase());
            });
        });

        // Apply search
        if (searchTerm) {
            const lower = searchTerm.toLowerCase();
            result = result.filter(item =>
                Object.values(item as any).some(v => String(v).toLowerCase().includes(lower))
            );
        }

        // Apply sorts
        if (sorts.length > 0) {
            result.sort((a: any, b: any) => {
                for (const { key, dir } of sorts) {
                    const valA = a[key];
                    const valB = b[key];
                    if (valA === valB) continue;
                    const direction = dir === 'asc' ? 1 : -1;
                    return valA > valB ? direction : -direction;
                }
                return 0;
            });
        }

        return result;
    }, [data, filters, searchTerm, sorts]);

    // Grouping
    const groups = useMemo(() => {
        if (!groupBy) return { 'all': processedData };
        const grouped: Record<string, T[]> = {};
        processedData.forEach(item => {
            const val = String((item as any)[groupBy] || 'sin-categoría');
            if (!grouped[val]) grouped[val] = [];
            grouped[val].push(item);
        });
        return grouped;
    }, [processedData, groupBy]);

    const toggleGroup = (group: string) =>
        setCollapsedGroups(prev => ({ ...prev, [group]: !prev[group] }));

    const visibleColumns = columns.filter(c => !c.hidden && !hiddenCols.has(String(c.key)));

    const removeFilter = (idx: number) =>
        setFilters(prev => prev.filter((_, i) => i !== idx));

    const activeFilters = filters.length > 0;
    const activeSorts   = sorts.length > 0;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] font-sans select-none overflow-hidden">

            {/* ── TOOLBAR PRINCIPAL ── */}
            <header className="px-4 py-2.5 flex items-center gap-2 border-b border-slate-100 dark:border-white/[0.06] bg-white dark:bg-[#1e1f21] sticky top-0 z-30">

                {/* Botones de control */}
                <div className="flex items-center gap-1 flex-1 flex-wrap">

                    {/* SORT */}
                    <div className="relative">
                        <button
                            onClick={() => { setShowSort(s => !s); setShowFilter(false); setShowColConfig(false); }}
                            className={clsx(
                                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all',
                                activeSorts || showSort
                                    ? 'bg-blue-50 text-blue-600 border border-blue-200'
                                    : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 border border-transparent'
                            )}
                        >
                            <ArrowUpDown size={13} />
                            Ordenar
                            {activeSorts && (
                                <span className="ml-0.5 size-4 rounded-full bg-blue-500 text-white text-[9px] font-black flex items-center justify-center">
                                    {sorts.length}
                                </span>
                            )}
                        </button>
                        <AnimatePresence>
                            {showSort && (
                                <SortPanel
                                    columns={columns}
                                    sorts={sorts}
                                    onSortsChange={setSorts}
                                    onClose={() => setShowSort(false)}
                                />
                            )}
                        </AnimatePresence>
                    </div>

                    {/* FILTER */}
                    <div className="relative">
                        <button
                            onClick={() => { setShowFilter(s => !s); setShowSort(false); setShowColConfig(false); }}
                            className={clsx(
                                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all',
                                activeFilters || showFilter
                                    ? 'bg-blue-50 text-blue-600 border border-blue-200'
                                    : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 border border-transparent'
                            )}
                        >
                            <Filter size={13} />
                            Filtrar
                            {activeFilters && (
                                <span className="ml-0.5 size-4 rounded-full bg-blue-500 text-white text-[9px] font-black flex items-center justify-center">
                                    {filters.length}
                                </span>
                            )}
                        </button>
                        <AnimatePresence>
                            {showFilter && (
                                <FilterPanel
                                    columns={columns}
                                    filters={filters}
                                    onFiltersChange={setFilters}
                                    onClose={() => setShowFilter(false)}
                                />
                            )}
                        </AnimatePresence>
                    </div>

                    {/* COLUMN CONFIG */}
                    <div className="relative" ref={colConfigRef}>
                        <button
                            onClick={() => { setShowColConfig(s => !s); setShowSort(false); setShowFilter(false); }}
                            className={clsx(
                                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all',
                                showColConfig
                                    ? 'bg-blue-50 text-blue-600 border border-blue-200'
                                    : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 border border-transparent'
                            )}
                        >
                            <ColumnsIcon size={13} />
                            Columnas
                        </button>
                        <AnimatePresence>
                            {showColConfig && (
                                <motion.div
                                    initial={{ opacity: 0, y: -8, scale: 0.97 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: -8, scale: 0.97 }}
                                    className="absolute top-full left-0 mt-1 z-50 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-xl shadow-xl min-w-[240px] p-3"
                                >
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">
                                        Visibilidad de columnas
                                    </p>
                                    <div className="space-y-1">
                                        {columns.filter(c => !c.hidden).map(col => {
                                            const isHidden = hiddenCols.has(String(col.key));
                                            return (
                                                <button
                                                    key={String(col.key)}
                                                    onClick={() => {
                                                        setHiddenCols(prev => {
                                                            const next = new Set(prev);
                                                            if (next.has(String(col.key))) next.delete(String(col.key));
                                                            else next.add(String(col.key));
                                                            return next;
                                                        });
                                                    }}
                                                    className="w-full flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-left"
                                                >
                                                    <div className={clsx(
                                                        'size-4 rounded border-2 flex items-center justify-center transition-colors',
                                                        !isHidden ? 'bg-blue-500 border-blue-500' : 'border-slate-300 dark:border-white/20'
                                                    )}>
                                                        {!isHidden && <Check size={10} className="text-white" />}
                                                    </div>
                                                    <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200">{col.label}</span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>

                {/* SEARCH */}
                <div className="relative w-56">
                    <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Buscar..."
                        className="w-full pl-8 pr-3 py-1.5 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-[12px] font-medium text-slate-700 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:border-blue-400 transition-colors"
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />
                </div>
            </header>

            {/* ── FILTER CHIPS ── */}
            <AnimatePresence>
                {(filters.length > 0 || sorts.length > 0) && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="px-4 py-2 flex items-center gap-2 flex-wrap border-b border-slate-100 dark:border-white/[0.04] bg-slate-50/60 dark:bg-white/[0.02] overflow-hidden"
                    >
                        {/* Sort chips */}
                        {sorts.map((s, idx) => {
                            const col = columns.find(c => String(c.key) === s.key);
                            return (
                                <span key={`sort-${idx}`} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-violet-50 border border-violet-200 text-violet-700 text-[11px] font-bold rounded-lg">
                                    {s.dir === 'asc' ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
                                    {col?.label ?? s.key}
                                    <button onClick={() => setSorts(prev => prev.filter((_, i) => i !== idx))} className="text-violet-400 hover:text-violet-700 ml-0.5">
                                        <X size={10} />
                                    </button>
                                </span>
                            );
                        })}

                        {/* Filter chips */}
                        {filters.map((f, idx) => {
                            const st = f.key === 'status' ? STATUS_CONFIG[f.value] : null;
                            return (
                                <span
                                    key={`filter-${idx}`}
                                    className={clsx(
                                        'inline-flex items-center gap-1.5 px-2.5 py-1 border text-[11px] font-bold rounded-lg',
                                        st
                                            ? clsx(st.chipBg, st.chipText, st.chipBorder)
                                            : 'bg-blue-50 border-blue-200 text-blue-700'
                                    )}
                                >
                                    {f.label}: {st?.label ?? f.value}
                                    <button onClick={() => removeFilter(idx)} className="opacity-60 hover:opacity-100 ml-0.5">
                                        <X size={10} />
                                    </button>
                                </span>
                            );
                        })}

                        {/* Clear all */}
                        <button
                            onClick={() => { setFilters([]); setSorts([]); }}
                            className="text-[11px] font-bold text-slate-400 hover:text-rose-500 transition-colors ml-1"
                        >
                            Limpiar todo
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── TABLE CONTENT ── */}
            <div className="flex-1 overflow-auto">
                <table className="w-full border-collapse table-fixed min-w-[700px]">
                    {/* HEADER */}
                    <thead className="sticky top-0 z-20 bg-slate-50 dark:bg-[#18191b] border-b border-slate-200 dark:border-white/[0.06]">
                        <tr>
                            {/* Nº fila */}
                            <th className="w-10 px-3 py-2.5 text-left text-[10px] font-black text-slate-300 uppercase tracking-widest border-r border-slate-100 dark:border-white/5">
                                #
                            </th>
                            {visibleColumns.map(col => (
                                <th
                                    key={col.key as string}
                                    style={{ width: col.width }}
                                    className="px-4 py-2.5 text-left border-r border-slate-100 dark:border-white/5 last:border-r-0 group/th"
                                >
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400 group-hover/th:text-slate-700 dark:group-hover/th:text-slate-200 transition-colors">
                                            {col.label}
                                        </span>
                                    </div>
                                </th>
                            ))}
                            {/* Add column */}
                            <th className="w-32 px-3 py-2.5 text-left">
                                <button className="flex items-center gap-1 text-[11px] font-bold text-slate-300 hover:text-blue-500 transition-colors">
                                    <Plus size={12} /> Columna
                                </button>
                            </th>
                        </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-100 dark:divide-white/[0.03]">
                        {Object.entries(groups).map(([groupName, items]) => (
                            <React.Fragment key={groupName}>
                                {/* GROUP HEADER */}
                                {groupBy && (
                                    <tr className="bg-slate-50/80 dark:bg-white/[0.01]">
                                        <td colSpan={visibleColumns.length + 2} className="px-3 py-1.5">
                                            <button
                                                onClick={() => toggleGroup(groupName)}
                                                className="flex items-center gap-2 px-2 py-1 hover:bg-slate-200/50 dark:hover:bg-white/5 rounded-lg transition-all"
                                            >
                                                <motion.div animate={{ rotate: collapsedGroups[groupName] ? -90 : 0 }} className="text-slate-400">
                                                    <ChevronDown size={13} />
                                                </motion.div>
                                                <StatusChip value={groupName} />
                                                <span className="text-[10px] font-bold text-slate-400 bg-slate-200/70 dark:bg-white/10 px-1.5 rounded-md">
                                                    {items.length}
                                                </span>
                                            </button>
                                        </td>
                                    </tr>
                                )}

                                {/* ROWS */}
                                <AnimatePresence initial={false}>
                                    {!collapsedGroups[groupName] && items.map((item, idx) => (
                                        <motion.tr
                                            key={(item as any).id}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0, height: 0 }}
                                            transition={{ duration: 0.12, delay: idx * 0.015 }}
                                            onClick={() => onRowClick?.(item)}
                                            className="group hover:bg-blue-50/40 dark:hover:bg-white/[0.02] transition-colors cursor-pointer"
                                        >
                                            {/* Nº fila */}
                                            <td className="w-10 px-3 py-2.5 text-[11px] font-bold text-slate-300 dark:text-white/20 border-r border-slate-100 dark:border-white/5 text-right tabular-nums">
                                                {idx + 1}
                                            </td>
                                            {visibleColumns.map(col => (
                                                <td key={col.key as string} className="px-4 py-2.5 border-r border-slate-100 dark:border-white/5 last:border-r-0 overflow-hidden">
                                                    <TableCell
                                                        column={col}
                                                        value={(item as any)[col.key]}
                                                        item={item}
                                                    />
                                                </td>
                                            ))}
                                            <td className="w-32" />
                                        </motion.tr>
                                    ))}
                                </AnimatePresence>

                                {/* ADD ROW */}
                                {!collapsedGroups[groupName] && (
                                    <tr className="group/add">
                                        <td colSpan={visibleColumns.length + 2} className="px-6 py-0.5">
                                            <button
                                                onClick={() => onAddItem?.(groupName)}
                                                className="flex items-center gap-1.5 text-[11px] font-bold text-slate-300 hover:text-blue-500 dark:text-white/10 dark:hover:text-blue-400 py-1.5 transition-all opacity-0 group-hover/add:opacity-100"
                                            >
                                                <Plus size={12} />
                                                Agregar fila
                                            </button>
                                        </td>
                                    </tr>
                                )}
                            </React.Fragment>
                        ))}

                        {/* EMPTY STATE */}
                        {processedData.length === 0 && !isLoading && (
                            <tr>
                                <td colSpan={visibleColumns.length + 2} className="py-20 text-center">
                                    <div className="flex flex-col items-center gap-3">
                                        <div className="size-14 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center">
                                            <LayoutGrid size={24} className="text-slate-200" />
                                        </div>
                                        <p className="text-slate-400 text-sm font-medium">{emptyMessage}</p>
                                        {onAddItem && (
                                            <button
                                                onClick={() => onAddItem?.()}
                                                className="text-xs font-bold text-blue-500 hover:underline"
                                            >
                                                Crear el primero
                                            </button>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>

                {/* ADD ROW GLOBAL */}
                <div className="px-4 py-2 border-t border-slate-100 dark:border-white/5">
                    <button
                        onClick={() => onAddItem?.()}
                        className="flex items-center gap-1.5 text-[12px] font-bold text-slate-400 hover:text-blue-500 transition-colors"
                    >
                        <Plus size={13} />
                        Agregar fila
                        <span className="ml-1 text-slate-300 font-normal text-[10px]">Shift+Enter</span>
                    </button>
                </div>
            </div>

            {/* ── FOOTER ── */}
            <footer className="px-4 py-2 border-t border-slate-100 dark:border-white/[0.04] flex items-center justify-between bg-slate-50/50 dark:bg-black/10">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                    {processedData.length} de {data.length} registros
                    {filters.length > 0 && ` · ${filters.length} filtro${filters.length > 1 ? 's' : ''} activo${filters.length > 1 ? 's' : ''}`}
                </span>
                <div className="flex items-center gap-1">
                    {sorts.length > 0 && (
                        <span className="text-[10px] font-bold text-violet-500 flex items-center gap-1">
                            <ArrowUpDown size={10} /> {sorts.length} criterio{sorts.length > 1 ? 's' : ''}
                        </span>
                    )}
                </div>
            </footer>
        </div>
    );
}

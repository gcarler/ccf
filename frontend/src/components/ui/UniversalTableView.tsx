"use client";

import {
AllCommunityModule,
ColDef,
GetRowIdParams,
ModuleRegistry,themeQuartz
} from 'ag-grid-community';
import { AgGridReact } from 'ag-grid-react';
import clsx from 'clsx';
import { AnimatePresence,motion } from 'framer-motion';
import {
Calendar,
Columns as ColumnsIcon,Download,
Flag,
Hash,
Loader2,
Plus,Search,
User,
X,
} from 'lucide-react';
import React,{ useCallback,useEffect,useMemo,useRef,useState } from 'react';

ModuleRegistry.registerModules([AllCommunityModule]);

// ─── Types (same public API) ───────────────────────────────────────────────────

export type ColumnType = 'text' | 'status' | 'priority' | 'user' | 'date' | 'progress' | 'tag' | 'id' | 'link';

export interface TableColumn<T> {
    key: keyof T | string;
    label: string;
    type: ColumnType;
    width?: string;
    sortable?: boolean;
    hidden?: boolean;
    editable?: boolean;  // new: per-column override for editability
    render?: (value: any, item: T) => React.ReactNode;
    /** Optional: transform the display value (e.g. combine fields). When set, the column shows this value but editing still writes to `key`. */
    displayValue?: (item: T) => string;
}

interface UniversalTableViewProps<T> {
    data: T[];
    columns: TableColumn<T>[];
    groupBy?: keyof T;
    title?: string;
    viewName?: string;
    onRowClick?: (item: T) => void;
    onAddItem?: (groupValue?: string) => void;
    onUpdateItem?: (id: string | number, field: string, value: any) => Promise<void> | void;
    isLoading?: boolean;
    emptyMessage?: string;
    renderDetailPanel?: (item: T, onClose: () => void) => React.ReactNode;
}

// ─── Status / Priority maps ────────────────────────────────────────────────────

const STATUS_MAP: Record<string, { label: string; bg: string; text: string; dot: string }> = {
    todo:        { label: 'Pendiente',   bg: 'bg-amber-50 dark:bg-amber-900/20',   text: 'text-amber-700 dark:text-amber-400',   dot: 'bg-amber-400' },
    pending:     { label: 'Pendiente',   bg: 'bg-amber-50 dark:bg-amber-900/20',   text: 'text-amber-700 dark:text-amber-400',   dot: 'bg-amber-400' },
    in_progress: { label: 'En Progreso', bg: 'bg-blue-50 dark:bg-blue-900/20',     text: 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]',     dot: 'bg-[hsl(var(--primary))]'  },
    review:      { label: 'En Revisión', bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-[hsl(var(--primary))] dark:text-blue-400', dot: 'bg-blue-500' },
    done:        { label: 'Terminado',   bg: 'bg-cyan-50 dark:bg-cyan-900/20',     text: 'text-cyan-700 dark:text-cyan-400',     dot: 'bg-cyan-500'  },
    completed:   { label: 'Completado',  bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-400', dot: 'bg-emerald-500' },
    blocked:     { label: 'Bloqueado',   bg: 'bg-rose-50 dark:bg-rose-900/20',     text: 'text-rose-700 dark:text-rose-400',     dot: 'bg-rose-500'  },
};
function getStatus(v: string) { return STATUS_MAP[v?.toLowerCase()] ?? STATUS_MAP.todo; }

const PRIORITY_MAP: Record<string, { label: string; color: string; bg: string }> = {
    urgent: { label: 'Urgente', color: 'text-rose-600 dark:text-rose-400',   bg: 'bg-rose-50 dark:bg-rose-900/20'   },
    high:   { label: 'Alta',    color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-50 dark:bg-orange-900/20' },
    medium: { label: 'Media',   color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/20'  },
    normal: { label: 'Normal',  color: 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]',   bg: 'bg-blue-50 dark:bg-blue-900/20'   },
    low:    { label: 'Baja',    color: 'text-slate-500 dark:text-slate-400', bg: 'bg-slate-50 dark:bg-slate-800'    },
};

// ─── Cell Renderers ────────────────────────────────────────────────────────────

function StatusCellRenderer({ value }: any) {
    const st = getStatus(String(value ?? ''));
    return (
        <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-[3px] rounded text-[11px] font-semibold leading-none', st.bg, st.text)}>
            <span className={clsx('size-1.5 rounded-full shrink-0', st.dot)} />
            {st.label}
        </span>
    );
}

function PriorityCellRenderer({ value }: any) {
    const p = PRIORITY_MAP[String(value ?? '').toLowerCase()] ?? PRIORITY_MAP.normal;
    return (
        <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-[3px] rounded text-[11px] font-semibold', p.bg, p.color)}>
            <Flag size={10} /> {p.label}
        </span>
    );
}

function DateCellRenderer({ value }: any) {
    if (!value) return <span className="text-slate-300 dark:text-slate-600 text-xs">—</span>;
    return (
        <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
            <Calendar size={11} className="shrink-0 text-slate-400" />
            <span className="text-[12px] font-medium whitespace-nowrap">
                {new Date(String(value)).toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: '2-digit' })}
            </span>
        </div>
    );
}

function UserCellRenderer({ value }: any) {
    return (
        <div className="flex items-center gap-2 h-full">
            <div className="size-6 rounded-full bg-blue-100 dark:bg-white/10 flex items-center justify-center font-semibold text-[hsl(var(--primary))] text-[10px] shrink-0">
                {value ? String(value).charAt(0).toUpperCase() : <User size={11} className="text-slate-400" />}
            </div>
            <span className="text-[12px] text-slate-600 dark:text-slate-300 font-medium truncate">
                {value ? String(value) : '—'}
            </span>
        </div>
    );
}

function IdCellRenderer({ value }: any) {
    return (
        <div className="flex items-center gap-1 text-[11px] font-bold text-slate-300 dark:text-slate-600 uppercase tracking-wide">
            <Hash size={10} />{String(value ?? '').substring(0, 8)}
        </div>
    );
}

function ProgressCellRenderer({ value }: any) {
    const raw = Number(value || 0);
    const pct = Math.round(raw <= 1 ? raw * 100 : raw);
    return (
        <div className="flex items-center gap-2 w-full">
            <div className="flex-1 h-1.5 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                <div className={clsx('h-full rounded-full', pct === 100 ? 'bg-emerald-500' : 'bg-[hsl(var(--primary))]')} style={{ width: `${pct}%` }} />
            </div>
            <span className="font-semibold text-slate-400 tabular-nums text-[11px] w-8 text-right">{pct}%</span>
        </div>
    );
}

// ─── Themes ────────────────────────────────────────────────────────────────────

const lightTheme = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 36, headerHeight: 36, backgroundColor: '#ffffff', foregroundColor: '#1e293b', borderColor: '#e2e8f0', oddRowBackgroundColor: '#f8fafc', headerBackgroundColor: '#f1f5f9', headerTextColor: '#475569', selectedRowBackgroundColor: '#eef2ff', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });
const darkTheme  = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 36, headerHeight: 36, backgroundColor: 'rgb(15 23 42)', foregroundColor: '#e2e8f0', borderColor: 'rgba(255,255,255,0.08)', oddRowBackgroundColor: 'rgba(255,255,255,0.02)', headerBackgroundColor: 'rgba(255,255,255,0.04)', headerTextColor: '#94a3b8', selectedRowBackgroundColor: 'rgba(99,102,241,0.15)', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });

// ─── Group header row type ─────────────────────────────────────────────────────

const GROUP_ROW_ID_PREFIX = '__group__';

// ─── Main Component ────────────────────────────────────────────────────────────

export default function UniversalTableView<T extends { id: string | number }>({
    data, columns, groupBy, onRowClick, onAddItem,
    onUpdateItem, isLoading, emptyMessage = 'No hay registros para mostrar',
    renderDetailPanel,
}: UniversalTableViewProps<T>) {
    const gridRef = useRef<AgGridReact>(null);
    const [isDark, setIsDark] = useState(false);
    const [quickFilter, setQuickFilter] = useState('');
    const [hiddenCols, setHiddenCols] = useState<Set<string>>(new Set());
    const [showColPanel, setShowColPanel] = useState(false);
    const [selectedItem, setSelectedItem] = useState<T | null>(null);
    const colPanelRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const check = () => setIsDark(document.documentElement.classList.contains('dark'));
        check();
        const obs = new MutationObserver(check);
        obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        return () => obs.disconnect();
    }, []);

    useEffect(() => {
        if (!showColPanel) return;
        const h = (e: MouseEvent) => { if (colPanelRef.current && !colPanelRef.current.contains(e.target as Node)) setShowColPanel(false); };
        document.addEventListener('mousedown', h);
        return () => document.removeEventListener('mousedown', h);
    }, [showColPanel]);

    // Build colDefs from TableColumn[]
    const colDefs = useMemo<ColDef[]>(() => {
        return columns
            .filter(c => !c.hidden && !hiddenCols.has(String(c.key)))
            .map((col): ColDef => {
                const field = String(col.key);
                const base: ColDef = {
                    field,
                    headerName: col.label,
                    width: col.width ? parseInt(col.width) : undefined,
                    flex: col.width ? undefined : 1,
                    minWidth: 80,
                    resizable: true,
                    sortable: col.sortable !== false,
                    filter: 'agTextColumnFilter',
                };

                // Editable logic:
                // A column is editable when it has an onUpdateItem handler AND is not explicitly disabled.
                // Columns with custom render CAN be editable — the render is just visual (like Airtable).
                // The __isGroup synthetic column is never editable.
                const isExplicitlyDisabled = col.editable === false;
                const isGroupRow = field === '__isGroup'; // synthetic group header rows – never editable
                const canEdit = !isExplicitlyDisabled && !isGroupRow && !!onUpdateItem;

                // If there's a custom render, use it for display
                if (col.render) {
                    const renderFn = col.render;
                    base.cellRenderer = ({ value, data: rowData }: any) => {
                        if (rowData?.__isGroup) return null;
                        return <>{renderFn(value, rowData as T)}</>;
                    };
                    // But still allow editing if not disabled
                    if (canEdit) {
                        base.editable = true;
                        base.singleClickEdit = true;
                        base.cellEditor = 'agTextCellEditor';
                        base.valueSetter = (params: any) => {
                            if (params.oldValue === params.newValue) return false;
                            const result = onUpdateItem(params.data.id, field, params.newValue);
                            if (result instanceof Promise) {
                                result.then(ok => { if (ok === false) params.api.applyTransaction({ update: [params.data] }); });
                                return true; // optimistic — revert on failure
                            }
                            return result !== false;
                        };
                    } else {
                        base.editable = false;
                    }
                } else if (canEdit) {
                    base.editable = true;
                    base.singleClickEdit = true;
                    base.cellEditor = 'agTextCellEditor';
                    base.valueSetter = (params: any) => {
                        if (params.oldValue === params.newValue) return false;
                        const result = onUpdateItem(params.data.id, field, params.newValue);
                        if (result instanceof Promise) {
                            result.then(ok => { if (ok === false) params.api.applyTransaction({ update: [params.data] }); });
                            return true; // optimistic — revert on failure
                        }
                        return result !== false;
                    };
                }

                // Apply default cell renderers only for non-custom-render columns
                if (!col.render) {
                    switch (col.type) {
                        case 'status':   base.cellRenderer = StatusCellRenderer; break;
                        case 'priority': base.cellRenderer = PriorityCellRenderer; break;
                        case 'date':     base.cellRenderer = DateCellRenderer; break;
                        case 'user':     base.cellRenderer = UserCellRenderer; break;
                        case 'id':       base.cellRenderer = IdCellRenderer; break;
                        case 'progress': base.cellRenderer = ProgressCellRenderer; break;
                        default:         base.cellStyle = { fontSize: '13px', fontWeight: '500' }; break;
                    }
                }
                return base;
            });
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [columns, hiddenCols, onUpdateItem]);

    // Handle groupBy by pre-processing rows
    const rowData = useMemo(() => {
        if (!groupBy) return data;
        const groups: Record<string, T[]> = {};
        data.forEach(item => {
            const k = String((item as any)[groupBy] || 'Sin categoría');
            if (!groups[k]) groups[k] = [];
            groups[k].push(item);
        });
        const flat: any[] = [];
        Object.entries(groups).forEach(([key, rows]) => {
            flat.push({ __isGroup: true, __groupKey: key, __groupCount: rows.length, id: `${GROUP_ROW_ID_PREFIX}${key}` });
            flat.push(...rows);
        });
        return flat;
    }, [data, groupBy]);

    const isFullWidthRow = useCallback((params: any) => !!params.rowNode.data?.__isGroup, []);

    const fullWidthCellRenderer = useCallback(({ data: row }: any) => (
        <div className="flex items-center gap-2 px-3 h-full bg-slate-50 dark:bg-white/[0.03] border-b border-slate-200 dark:border-white/5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{row.__groupKey}</span>
            <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 bg-slate-200 dark:bg-white/10 rounded-full px-2 py-0.5">{row.__groupCount}</span>
            {onAddItem && (
                <button onClick={(e) => { e.stopPropagation(); onAddItem(row.__groupKey); }}
                    className="ml-auto flex items-center gap-1 text-[10px] font-semibold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary)/0.8)] transition-colors">
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

    return (
        <div className="flex flex-col h-full gap-2">
            {/* Toolbar */}
            <div className="flex items-center gap-2 flex-wrap shrink-0">
                <div className="relative flex-1 min-w-[180px] max-w-xs">
                    <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                    <input
                        value={quickFilter}
                        onChange={(e) => {
                            setQuickFilter(e.target.value);
                            gridRef.current?.api?.setGridOption('quickFilterText', e.target.value);
                        }}
                        placeholder="Buscar…"
                        className="w-full pl-7 pr-7 py-1.5 text-xs border border-slate-200 dark:border-white/10 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-slate-700 dark:text-slate-200 placeholder-slate-400 outline-none focus:ring-1 focus:ring-sky-400"
                    />
                    {quickFilter && (
                        <button onClick={() => { setQuickFilter(''); gridRef.current?.api?.setGridOption('quickFilterText', ''); }}
                            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                            <X size={11} />
                        </button>
                    )}
                </div>

                <div className="flex items-center gap-1 ml-auto">
                    {/* Column visibility */}
                    <div className="relative" ref={colPanelRef}>
                        <button onClick={() => setShowColPanel(s => !s)}
                            className={clsx('flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold rounded-lg transition-colors border',
                                showColPanel ? 'bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] border-blue-200 dark:border-blue-700' : 'bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-white/10 hover:border-slate-300')}>
                            <ColumnsIcon size={13} /> Columnas
                        </button>
                        <AnimatePresence>
                            {showColPanel && (
                                <motion.div initial={{ opacity: 0, y: -4, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -4, scale: 0.97 }} transition={{ duration: 0.12 }}
                                    className="absolute top-full right-0 mt-1 z-50 w-52 bg-[hsl(var(--bg-primary))] dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-lg shadow-xl p-2">
                                    <p className="text-[9px] font-bold uppercase tracking-wide text-slate-400 px-1 pb-1.5">Columnas visibles</p>
                                    {visibleCols.map(col => {
                                        const key = String(col.key);
                                        const hidden = hiddenCols.has(key);
                                        return (
                                            <button key={key} onClick={() => setHiddenCols(prev => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n; })}
                                                className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                <span className="text-[12px] font-medium text-slate-700 dark:text-slate-300">{col.label}</span>
                                                <div className={clsx('size-4 rounded border-2 flex items-center justify-center', !hidden ? 'bg-[hsl(var(--primary))] border-[hsl(var(--primary))]' : 'border-slate-300 dark:border-white/20')}>
                                                    {!hidden && <span className="text-white text-[8px] font-bold">✓</span>}
                                                </div>
                                            </button>
                                        );
                                    })}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <button onClick={() => gridRef.current?.api?.exportDataAsCsv()} title="Exportar CSV"
                        className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 transition-colors border border-transparent hover:border-slate-200 dark:hover:border-white/10">
                        <Download size={14} />
                    </button>

                    {onAddItem && (
                        <button onClick={() => onAddItem()}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.85)] text-white transition-colors">
                            <Plus size={13} /> Agregar
                        </button>
                    )}
                </div>
            </div>

            {/* Grid */}
            <div className="flex-1 min-h-[200px] rounded-xl overflow-hidden border border-slate-200 dark:border-white/10 relative">
                {isLoading ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-[hsl(var(--bg-primary))] dark:bg-slate-900 z-10">
                        <Loader2 size={20} className="animate-spin text-[hsl(var(--primary))]" />
                    </div>
                ) : data.length === 0 ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-[hsl(var(--bg-primary))] dark:bg-slate-900 text-sm text-slate-400">
                        {emptyMessage}
                    </div>
                ) : (
                    <AgGridReact
                        ref={gridRef}
                        theme={isDark ? darkTheme : lightTheme}
                        rowData={rowData as any[]}
                        columnDefs={colDefs}
                        defaultColDef={{ resizable: true, sortable: true, filter: true, minWidth: 80 }}
                        getRowId={getRowId}
                        getRowHeight={getRowHeight}
                        isFullWidthRow={groupBy ? isFullWidthRow : undefined}
                        fullWidthCellRenderer={groupBy ? fullWidthCellRenderer : undefined}
                        onRowClicked={handleRowClick}
                        rowStyle={{ cursor: onRowClick ? 'pointer' : 'default' }}
                        animateRows
                        enableCellTextSelection
                        singleClickEdit={!!onUpdateItem}
                        stopEditingWhenCellsLoseFocus={true}
                        enterNavigatesVertically={true}
                        enterNavigatesVerticallyAfterEdit={true}
                    />
                )}
            </div>

            {/* Detail panel */}
            <AnimatePresence>
                {selectedItem && renderDetailPanel && (
                    <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 24 }} transition={{ duration: 0.2 }}
                        className="fixed inset-y-0 right-0 w-[480px] z-50 shadow-2xl">
                        {renderDetailPanel(selectedItem, () => setSelectedItem(null))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

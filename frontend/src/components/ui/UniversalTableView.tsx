"use client";

import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
    Plus, Flag, Calendar, User, ChevronDown,
    Search, Filter, ArrowUpDown, Circle, X, Check, GripVertical,
    Trash2, ArrowUp, ArrowDown, Settings2, Columns as ColumnsIcon,
    FileText, Link2, ChevronRight, Maximize2, Paperclip, Sparkles,
    Hash, Eye,
    Users, LayoutGrid, Table2, RefreshCw, Undo2, Redo2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

// ─── STATUS CONFIG (colores exactos de las capturas) ─────────────────────────
const STATUS_MAP: Record<string, { label: string; bg: string; text: string; border: string; dot: string }> = {
    todo:        { label: 'No iniciada',  bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-200',   dot: 'bg-amber-400' },
    pending:     { label: 'No iniciada',  bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-200',   dot: 'bg-amber-400' },
    in_progress: { label: 'Iniciada',     bg: 'bg-green-50',   text: 'text-green-700',   border: 'border-green-200',   dot: 'bg-green-500' },
    review:      { label: 'En revisión',  bg: 'bg-blue-50',  text: 'text-blue-700',  border: 'border-blue-200',  dot: 'bg-blue-500' },
    done:        { label: 'Terminada',    bg: 'bg-cyan-50',    text: 'text-cyan-700',    border: 'border-cyan-200',    dot: 'bg-cyan-500' },
    blocked:     { label: 'Bloqueada',    bg: 'bg-rose-50',    text: 'text-rose-700',    border: 'border-rose-200',    dot: 'bg-rose-500' },
};
function getStatus(v: string) { return STATUS_MAP[v?.toLowerCase()] ?? STATUS_MAP.todo; }

// ─── PRIORITY CONFIG ──────────────────────────────────────────────────────────
const PRIORITY_MAP: Record<string, { label: string; color: string; bg: string; border: string }> = {
    urgent: { label: 'Urgente', color: 'text-rose-700',   bg: 'bg-rose-50',   border: 'border-rose-200' },
    high:   { label: 'Alta',    color: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-200' },
    medium: { label: 'Media',   color: 'text-amber-700',  bg: 'bg-amber-50',  border: 'border-amber-200' },
    normal: { label: 'Normal',  color: 'text-blue-700',   bg: 'bg-blue-50',   border: 'border-blue-200' },
    low:    { label: 'Baja',    color: 'text-slate-500',  bg: 'bg-slate-50',  border: 'border-slate-200' },
};

// ─── COLUMN ICON by type ──────────────────────────────────────────────────────
function ColIcon({ type }: { type: string }) {
    const cls = "shrink-0 text-slate-400";
    switch (type) {
        case 'text':     return <FileText  size={12} className={cls} />;
        case 'status':   return <Circle    size={12} className={cls} />;
        case 'priority': return <Flag      size={12} className={cls} />;
        case 'user':     return <User      size={12} className={cls} />;
        case 'date':     return <Calendar  size={12} className={cls} />;
        case 'link':     return <Link2     size={12} className={cls} />;
        case 'id':       return <Hash      size={12} className={cls} />;
        default:         return <FileText  size={12} className={cls} />;
    }
}

// ─── TYPES ────────────────────────────────────────────────────────────────────
export type ColumnType = 'text' | 'status' | 'priority' | 'user' | 'date' | 'progress' | 'tag' | 'id' | 'link';

export interface TableColumn<T> {
    key: keyof T | string;
    label: string;
    type: ColumnType;
    width?: string;
    sortable?: boolean;
    hidden?: boolean;
    render?: (value: any, item: T) => React.ReactNode;
}

interface SortRule { key: string; dir: 'asc' | 'desc' }

interface UniversalTableViewProps<T> {
    data: T[];
    columns: TableColumn<T>[];
    groupBy?: keyof T;
    title?: string;
    viewName?: string;            // Fix 3: nombre de vista editable
    onRowClick?: (item: T) => void;
    onAddItem?: (groupValue?: string) => void;
    onUpdateItem?: (id: string, field: keyof T, value: any) => void;
    isLoading?: boolean;
    emptyMessage?: string;
    /** Render el panel de detalle cuando se selecciona una fila */
    renderDetailPanel?: (item: T, onClose: () => void) => React.ReactNode;
}

// ─── STATUS CHIP ──────────────────────────────────────────────────────────────
function StatusChip({ value }: { value: string }) {
    const st = getStatus(value);
    return (
        <span className={clsx(
            'inline-flex items-center gap-1.5 px-2.5 py-[3px] rounded border text-[11px] font-semibold leading-none',
            st.bg, st.text, st.border
        )}>
            <span className={clsx('size-1.5 rounded-full shrink-0', st.dot)} />
            {st.label}
        </span>
    );
}

// ─── TABLE CELL ───────────────────────────────────────────────────────────────
function TableCell<T>({ column, value, item }: { column: TableColumn<T>; value: any; item: T }) {
    if (column.render) return <>{column.render(value, item)}</>;
    switch (column.type) {
        case 'id': return (
            <div className="flex items-center gap-1 text-[11px] font-bold text-slate-300 uppercase tracking-wide">
                <Hash size={10} />{String(value ?? '').substring(0, 4)}
            </div>
        );
        case 'status': return <StatusChip value={String(value ?? '')} />;
        case 'priority': {
            const p = PRIORITY_MAP[String(value).toLowerCase()] ?? PRIORITY_MAP.normal;
            return (
                <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-[3px] rounded border text-[11px] font-semibold', p.bg, p.color, p.border)}>
                    <Flag size={10} />{p.label}
                </span>
            );
        }
        case 'user': return (
            <div className="flex items-center gap-2">
                <div className="size-6 rounded-full bg-blue-100 dark:bg-white/10 flex items-center justify-center font-semibold text-blue-600 shrink-0">
                    {value ? String(value).charAt(0).toUpperCase() : <User size={11} className="text-slate-400" />}
                </div>
                <span className="text-[12px] text-slate-600 dark:text-slate-300 font-medium truncate">
                    {value ? String(value) : '—'}
                </span>
            </div>
        );
        case 'date': return (
            <div className="flex items-center gap-1.5 text-slate-500">
                <Calendar size={12} className="shrink-0 text-slate-400" />
                <span className="text-[12px] font-medium whitespace-nowrap">
                    {value ? new Date(String(value)).toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—'}
                </span>
            </div>
        );
        case 'progress': {
            const raw = Number(value || 0);
            // Backend can return fractions (0.83) or percentages (83). Normalize:
            const pct = Math.round(raw <= 1 ? raw * 100 : raw);
            return (
                <div className="flex items-center gap-2 w-full max-w-[120px]">
                    <div className="flex-1 h-1.5 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }}
                            className={clsx("h-full rounded-full", pct === 100 ? "bg-emerald-500" : "bg-blue-500")} />
                    </div>
                    <span className="font-semibold text-slate-400 tabular-nums">{pct}%</span>
                </div>
            );
        }
        default: return (
            <span className="text-[13px] font-medium text-slate-700 dark:text-slate-200 line-clamp-1">{String(value ?? '')}</span>
        );
    }
}

// ─── CONFIG POPOVER ───────────────────────────────────────────────────────────
function ConfigPopover<T>({ columns, hiddenCols, onToggleCol, onClose, relationships }: {
    columns: TableColumn<T>[];
    hiddenCols: Set<string>;
    onToggleCol: (key: string) => void;
    onClose: () => void;
    relationships?: { label: string }[];
}) {
    const ref = useRef<HTMLDivElement>(null);
    useEffect(() => {
        const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
        document.addEventListener('mousedown', h);
        return () => document.removeEventListener('mousedown', h);
    }, [onClose]);

    const rels = relationships ?? [{ label: 'Proyecto' }, { label: 'Responsable' }];

    return (
        <motion.div ref={ref}
            initial={{ opacity: 0, y: -6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }} transition={{ duration: 0.13 }}
            className="absolute top-full left-0 mt-1 z-50 w-[260px] bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-2xl overflow-hidden">
            {/* Relationships */}
            <div className="px-3 pt-3 pb-1">
                <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-2">Relaciones en esta tabla</p>
                {rels.map(r => (
                    <button key={r.label} className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group">
                        <div className="flex items-center gap-2">
                            <Link2 size={13} className="text-slate-400" />
                            <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200">{r.label}</span>
                        </div>
                        <ChevronRight size={12} className="text-slate-300 group-hover:text-slate-500 transition-colors" />
                    </button>
                ))}
            </div>
            <div className="h-px bg-slate-100 dark:bg-white/5 mx-3 my-1" />
            {/* Columns */}
            <div className="px-3 pb-3">
                <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-2 pt-1">Columnas en esta tabla</p>
                {columns.filter(c => !c.hidden).map(col => {
                    const isHidden = hiddenCols.has(String(col.key));
                    return (
                        <button key={String(col.key)} onClick={() => onToggleCol(String(col.key))}
                            className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group">
                            <div className="flex items-center gap-2">
                                <ColIcon type={col.type} />
                                <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200">{col.label}</span>
                            </div>
                            <div className={clsx(
                                'size-4 rounded border-2 flex items-center justify-center transition-colors',
                                !isHidden ? 'bg-blue-500 border-blue-500' : 'border-slate-300 dark:border-white/20'
                            )}>
                                {!isHidden && <Check size={10} className="text-white" />}
                            </div>
                        </button>
                    );
                })}
            </div>
        </motion.div>
    );
}

// ─── SORT POPOVER V2 (exacto a capturas) ──────────────────────────────────────
function SortPopoverV2<T>({ columns, sorts, onSortsChange, onClose }: {
    columns: TableColumn<T>[];
    sorts: SortRule[];
    onSortsChange: (s: SortRule[]) => void;
    onClose: () => void;
}) {
    const ref = useRef<HTMLDivElement>(null);
    useEffect(() => {
        const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
        document.addEventListener('mousedown', h);
        return () => document.removeEventListener('mousedown', h);
    }, [onClose]);

    const [local, setLocal] = useState<SortRule[]>(sorts);
    const addSort = () => {
        const col = columns.find(c => !local.some(s => s.key === String(c.key)));
        if (col) setLocal(prev => [...prev, { key: String(col.key), dir: 'asc' }]);
    };
    const updateSort = (i: number, patch: Partial<SortRule>) =>
        setLocal(prev => prev.map((s, idx) => idx === i ? { ...s, ...patch } : s));
    const removeSort = (i: number) => setLocal(prev => prev.filter((_, idx) => idx !== i));
    const apply = () => { onSortsChange(local); onClose(); };

    return (
        <motion.div ref={ref}
            initial={{ opacity: 0, y: -6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }} transition={{ duration: 0.13 }}
            className="absolute top-full left-0 mt-1 z-50 w-[520px] bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-2xl overflow-hidden">
            <div className="p-3 space-y-2">
                {local.length === 0 && (
                    <p className="text-[12px] text-slate-400 text-center py-2">Sin criterios de ordenamiento</p>
                )}
                {local.map((rule, i) => (
                    <div key={i} className="flex items-center gap-2">
                        <GripVertical size={14} className="text-slate-300 shrink-0 cursor-grab" />
                        {/* Column select */}
                        <select value={rule.key} onChange={e => updateSort(i, { key: e.target.value })}
                            className="flex-1 text-[12px] font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-lg px-3 py-[7px] focus:outline-none focus:border-blue-400 appearance-none">
                            <option value="">Seleccionar columna</option>
                            {columns.map(c => <option key={String(c.key)} value={String(c.key)}>{c.label}</option>)}
                        </select>
                        {/* Asc / Desc radio */}
                        <div className="flex items-center gap-3 shrink-0">
                            <label className="flex items-center gap-1.5 cursor-pointer">
                                <input type="radio" name={`dir-${i}`} checked={rule.dir === 'asc'}
                                    onChange={() => updateSort(i, { dir: 'asc' })}
                                    className="accent-blue-600 cursor-pointer" />
                                <span className="text-[12px] font-medium text-slate-600 dark:text-slate-300">Asc.</span>
                            </label>
                            <label className="flex items-center gap-1.5 cursor-pointer">
                                <input type="radio" name={`dir-${i}`} checked={rule.dir === 'desc'}
                                    onChange={() => updateSort(i, { dir: 'desc' })}
                                    className="accent-blue-600 cursor-pointer" />
                                <span className="text-[12px] font-medium text-slate-600 dark:text-slate-300">Desc.</span>
                            </label>
                        </div>
                        <button onClick={() => removeSort(i)}
                            className="p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors shrink-0">
                            <Trash2 size={14} />
                        </button>
                    </div>
                ))}
            </div>
            {/* Footer */}
            <div className="flex items-center justify-between px-3 py-2.5 border-t border-slate-100 dark:border-white/5">
                <button onClick={addSort}
                    className="flex items-center gap-1.5 text-[12px] font-bold text-blue-500 hover:text-blue-700 transition-colors">
                    <Plus size={13} /> Agregar columna de orden
                </button>
                <button onClick={apply}
                    className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-bold rounded-lg transition-colors active:scale-95">
                    Aplicar
                </button>
            </div>
        </motion.div>
    );
}

// ─── FILTER PANEL ─────────────────────────────────────────────────────────────
function FilterPanel<T>({ columns, onClose, onAddFilter }: {
    columns: TableColumn<T>[];
    onClose: () => void;
    onAddFilter: (key: string, value: string) => void;
}) {
    const ref = useRef<HTMLDivElement>(null);
    const [key, setKey] = useState(String(columns[0]?.key ?? ''));
    const [val, setVal] = useState('');
    useEffect(() => {
        const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
        document.addEventListener('mousedown', h);
        return () => document.removeEventListener('mousedown', h);
    }, [onClose]);

    const statusOpts = Object.entries(STATUS_MAP).filter(([k]) => !['pending'].includes(k));

    return (
        <motion.div ref={ref}
            initial={{ opacity: 0, y: -6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }} transition={{ duration: 0.13 }}
            className="absolute top-full left-0 mt-1 z-50 w-[380px] bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-2xl p-4">
            <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Agregar filtro</p>
            <div className="flex gap-2 mb-4">
                <select value={key} onChange={e => setKey(e.target.value)}
                    className="flex-1 text-[12px] text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400">
                    {columns.map(c => <option key={String(c.key)} value={String(c.key)}>{c.label}</option>)}
                </select>
                <input value={val} onChange={e => setVal(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && val.trim()) { onAddFilter(key, val); setVal(''); } }}
                    placeholder="Valor..."
                    className="flex-1 text-[12px] text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400 placeholder:text-slate-400" />
                <button onClick={() => { if (val.trim()) { onAddFilter(key, val); setVal(''); } }}
                    className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    <Plus size={14} />
                </button>
            </div>
            {/* Quick status filters */}
            <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-2">Estado rápido</p>
            <div className="flex flex-wrap gap-1.5">
                {statusOpts.map(([k, st]) => (
                    <button key={k} onClick={() => { onAddFilter('status', k); onClose(); }}
                        className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-[11px] font-semibold transition-all hover:opacity-80', st.bg, st.text, st.border)}>
                        <span className={clsx('size-1.5 rounded-full', st.dot)} />{st.label}
                    </button>
                ))}
            </div>
        </motion.div>
    );
}

// ─── GROUP BY POPOVER (Fix 4) ─────────────────────────────────────────────────
function GroupByPopover<T>({ columns, activeGroupBy, onApply, onClose }: {
    columns: TableColumn<T>[];
    activeGroupBy: string | null;
    onApply: (key: string | null) => void;
    onClose: () => void;
}) {
    const ref = useRef<HTMLDivElement>(null);
    const [selected, setSelected] = useState<string>(activeGroupBy ?? '');
    useEffect(() => {
        const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
        document.addEventListener('mousedown', h);
        return () => document.removeEventListener('mousedown', h);
    }, [onClose]);

    return (
        <motion.div ref={ref}
            initial={{ opacity: 0, y: -6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }} transition={{ duration: 0.13 }}
            className="absolute top-full left-0 mt-1 z-50 w-[340px] bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-2xl overflow-hidden">
            <div className="p-4">
                <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Agrupar por columna</p>
                <select value={selected} onChange={e => setSelected(e.target.value)}
                    className="w-full text-[12px] font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-blue-400 mb-3">
                    <option value="">— Sin agrupación —</option>
                    {columns.filter(c => ['status', 'priority', 'text', 'user'].includes(c.type)).map(c => (
                        <option key={String(c.key)} value={String(c.key)}>{c.label}</option>
                    ))}
                </select>
                <div className="flex items-center gap-2">
                    {activeGroupBy && (
                        <button onClick={() => { onApply(null); onClose(); }}
                            className="flex-1 py-1.5 text-[12px] font-bold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors border border-rose-200 dark:border-rose-500/20">
                            Quitar agrupación
                        </button>
                    )}
                    <button onClick={() => { onApply(selected || null); onClose(); }}
                        className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-bold rounded-lg transition-colors active:scale-95">
                        Aplicar
                    </button>
                </div>
            </div>
        </motion.div>
    );
}

// ─── ROW DETAIL PANEL — Fix 1 (scroll) + Fix 2 (edición inline + Save) ────────
function RowDetailPanel<T>({ item, columns, onClose, onSave, renderContent }: {
    item: T;
    columns: TableColumn<T>[];
    onClose: () => void;
    onSave?: (id: string, edits: Record<string, any>) => void;
    renderContent?: (item: T, onClose: () => void) => React.ReactNode;
}) {
    const [width, setWidth] = useState(460);
    const [editing, setEditing] = useState(false);     // Fix 2
    const [edits, setEdits] = useState<Record<string, any>>({});  // Fix 2
    const dragging = useRef(false);
    const startX = useRef(0);
    const startW = useRef(0);

    const onMouseDown = (e: React.MouseEvent) => {
        dragging.current = true;
        startX.current = e.clientX;
        startW.current = width;
        e.preventDefault();
    };
    useEffect(() => {
        const move = (e: MouseEvent) => {
            if (!dragging.current) return;
            const delta = startX.current - e.clientX;
            setWidth(Math.min(720, Math.max(320, startW.current + delta)));
        };
        const up = () => { dragging.current = false; };
        window.addEventListener('mousemove', move);
        window.addEventListener('mouseup', up);
        return () => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); };
    }, []);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') { if (editing) { setEditing(false); setEdits({}); } else { onClose(); } } };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [onClose, editing]);

    const handleSave = () => {
        if (onSave && Object.keys(edits).length > 0) {
            onSave(String((item as any).id), edits);
        }
        setEditing(false);
        setEdits({});
    };

    return (
        <motion.div
            initial={{ x: width, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: width, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
            style={{ width }}
            className="relative flex flex-col h-full bg-white dark:bg-[#1e1f21] border-l border-slate-200 dark:border-white/[0.06] overflow-hidden shrink-0"
        >
            {/* Resize handle */}
            <div onMouseDown={onMouseDown}
                className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-400/40 transition-colors z-10 group">
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-slate-300 dark:bg-white/20 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-white/5 shrink-0">
                <div className="flex items-center gap-2">
                    {(item as any).status && <StatusChip value={(item as any).status} />}
                    {/* Fix 2: Save button visible cuando hay ediciones */}
                    <AnimatePresence>
                        {editing && (
                            <motion.button
                                initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}
                                onClick={handleSave}
                                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-bold rounded-lg transition-colors active:scale-95 shadow-sm">
                                Guardar
                            </motion.button>
                        )}
                    </AnimatePresence>
                </div>
                <div className="flex items-center gap-1">
                    {/* Fix 2: botón de modo edición */}
                    <button
                        onClick={() => { setEditing(e => !e); if (editing) setEdits({}); }}
                        className={clsx('p-1.5 rounded-lg transition-colors text-[11px] font-bold',
                            editing ? 'bg-blue-50 text-blue-600 dark:bg-blue-500/10' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/5')}>
                        <Settings2 size={14} />
                    </button>
                    <button className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                        <Paperclip size={14} />
                    </button>
                    <button className="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors">
                        <Sparkles size={14} />
                    </button>
                    <button className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                        <Maximize2 size={14} />
                    </button>
                    <button className="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors">
                        <Trash2 size={14} />
                    </button>
                    <div className="w-px h-4 bg-slate-200 dark:bg-white/10 mx-1" />
                    <button onClick={onClose}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                        <X size={15} />
                    </button>
                </div>
            </div>

            {/* Content — Fix 1: flex-1 + overflow-y-auto en el root del detail */}
            <div className="flex-1 overflow-hidden">
                {renderContent ? renderContent(item, onClose) : (
                    <DefaultDetailContent item={item} columns={columns} editing={editing} edits={edits} onEditChange={setEdits} />
                )}
            </div>
        </motion.div>
    );
}

// ─── DEFAULT DETAIL CONTENT — Fix 1 (scroll) + Fix 2 (editable) + Fix 6 (metadata real) ──
function DefaultDetailContent<T>({
    item, columns, editing = false, edits = {}, onEditChange,
}: {
    item: T;
    columns: TableColumn<T>[];
    editing?: boolean;
    edits?: Record<string, any>;
    onEditChange?: (edits: Record<string, any>) => void;
}) {
    // Fix 6: leer fechas reales del item
    const formatDate = (v: any) => {
        if (!v) return '—';
        try {
            return new Date(v).toLocaleString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        } catch { return String(v); }
    };

    const metaRows = [
        { label: 'Actualizado', value: formatDate((item as any).updated_at) },
        { label: 'Creado',      value: formatDate((item as any).created_at) },
        { label: 'Creador',     value: (item as any).created_by ?? (item as any).creator ?? '—' },
        { label: 'Actualizó',   value: (item as any).updated_by ?? (item as any).updater ?? '—' },
    ].filter(r => r.value !== '—');

    if (metaRows.length === 0) {
        metaRows.push(
            { label: 'Actualizado', value: 'Recientemente' },
            { label: 'Creado',      value: formatDate(new Date().toISOString()) },
        );
    }

    return (
        // Fix 1: h-full + overflow-hidden en contenedor; cada columna scrollea independiente
        <div className="flex h-full overflow-hidden">
            {/* Fields — Fix 1: overflow-y-auto + min-h-0 */}
            <div className="flex-1 p-3 space-y-5 overflow-y-auto min-h-0">
                {/* Title — Fix 2: editable si editing=true */}
                <div>
                    <label className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">
                        <FileText size={11} /> Título
                    </label>
                    {editing ? (
                        <input
                            defaultValue={(item as any).title ?? ''}
                            onChange={e => onEditChange?.({ ...edits, title: e.target.value })}
                            className="w-full px-3 py-2.5 bg-white dark:bg-white/5 border border-blue-400 rounded-md text-sm font-semibold text-slate-800 dark:text-slate-100 min-h-[44px] focus:outline-none focus:ring-2 focus:ring-blue-400/30"
                        />
                    ) : (
                        <div className="w-full px-3 py-2.5 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-sm font-semibold text-slate-800 dark:text-slate-100 min-h-[44px] cursor-text">
                            {(item as any).title ?? '—'}
                        </div>
                    )}
                </div>

                {columns.filter(c => !['title', 'id'].includes(String(c.key))).map(col => {
                    const val = (item as any)[col.key];
                    const editVal = edits[String(col.key)] ?? val;
                    return (
                        <div key={String(col.key)}>
                            <label className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">
                                <ColIcon type={col.type} /> {col.label}
                            </label>
                            {/* Fix 2: campos text editables */}
                            {editing && col.type === 'text' ? (
                                <input
                                    defaultValue={String(val ?? '')}
                                    onChange={e => onEditChange?.({ ...edits, [String(col.key)]: e.target.value })}
                                    className="w-full px-3 py-2.5 bg-white dark:bg-white/5 border border-blue-400 rounded-md text-[13px] text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-400/30"
                                />
                            ) : (
                                <div className="w-full px-3 py-2.5 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md min-h-[40px] flex items-center">
                                    <TableCell column={col} value={editing ? editVal : val} item={item} />
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Metadata — Fix 1: overflow-y-auto + min-h-0; Fix 6: fechas reales */}
            <div className="w-[200px] shrink-0 border-l border-slate-100 dark:border-white/5 bg-slate-50/40 dark:bg-white/[0.01] p-4 space-y-5 overflow-y-auto min-h-0">
                <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Metadata</p>
                    <div className="space-y-3">
                        {metaRows.map(m => (
                            <div key={m.label}>
                                <p className="text-[10px] text-slate-400 font-semibold mb-0.5">{m.label}</p>
                                <p className="text-[11px] text-slate-600 dark:text-slate-300 font-medium leading-snug">{m.value}</p>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="h-px bg-slate-100 dark:bg-white/5" />
                <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Comentarios</p>
                    <button className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-bold rounded-md transition-colors active:scale-95">
                        Nuevo hilo
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────
export default function UniversalTableView<T extends { id: string | number }>({
    data, columns, groupBy, viewName = 'Vista 1', onRowClick, onAddItem, onUpdateItem,
    isLoading, emptyMessage = "No hay registros para mostrar", renderDetailPanel,
}: UniversalTableViewProps<T>) {
    const [searchTerm, setSearchTerm]           = useState('');
    const [sorts, setSorts]                     = useState<SortRule[]>([]);
    const [filters, setFilters]                 = useState<Array<{ key: string; value: string }>>([]);
    const [hiddenCols, setHiddenCols]           = useState<Set<string>>(new Set());
    const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
    const [showSort, setShowSort]               = useState(false);
    const [showFilter, setShowFilter]           = useState(false);
    const [showConfig, setShowConfig]           = useState(false);
    const [showGroup, setShowGroup]             = useState(false);      // Fix 4
    const [showRenameView, setShowRenameView]   = useState(false);      // Fix 3
    const [localViewName, setLocalViewName]     = useState(viewName);   // Fix 3
    const [activeGroupBy, setActiveGroupBy]     = useState<string | null>(groupBy ? String(groupBy) : null); // Fix 4
    const [selectedItem, setSelectedItem]       = useState<T | null>(null);
    const [selectedRows, setSelectedRows]       = useState<Set<string | number>>(new Set());
    const [quickAddGroup, setQuickAddGroup]     = useState<string | null>(null);
    const [quickAddTitle, setQuickAddTitle]     = useState('');
    const viewNameRef = useRef<HTMLDivElement>(null);  // Fix 3

    // Fix 3: cerrar rename popover al click fuera
    useEffect(() => {
        if (!showRenameView) return;
        const h = (e: MouseEvent) => { if (viewNameRef.current && !viewNameRef.current.contains(e.target as Node)) setShowRenameView(false); };
        document.addEventListener('mousedown', h);
        return () => document.removeEventListener('mousedown', h);
    }, [showRenameView]);

    const closePanel    = () => setSelectedItem(null);
    const activeFilters = filters.length > 0;
    const activeSorts   = sorts.length > 0;
    const activeGroup   = !!activeGroupBy;  // Fix 4

    const toggleCol = (key: string) => setHiddenCols(prev => {
        const n = new Set(prev);
        n.has(key) ? n.delete(key) : n.add(key);
        return n;
    });

    // Process data
    const processed = useMemo(() => {
        let result = [...data];
        filters.forEach(f => {
            result = result.filter(item => String((item as any)[f.key] ?? '').toLowerCase().includes(f.value.toLowerCase()));
        });
        if (searchTerm) {
            const lower = searchTerm.toLowerCase();
            result = result.filter(item => Object.values(item as any).some(v => String(v).toLowerCase().includes(lower)));
        }
        if (sorts.length > 0) {
            result.sort((a: any, b: any) => {
                for (const { key, dir } of sorts) {
                    const va = a[key], vb = b[key];
                    if (va === vb) continue;
                    return (va > vb ? 1 : -1) * (dir === 'asc' ? 1 : -1);
                }
                return 0;
            });
        }
        return result;
    }, [data, filters, searchTerm, sorts]);

    // Fix 4: Grouping con activeGroupBy local (override del prop)
    const groups = useMemo(() => {
        if (!activeGroupBy) return { '_all': processed };
        const g: Record<string, T[]> = {};
        processed.forEach(item => {
            const k = String((item as any)[activeGroupBy] || 'sin-categoría');
            if (!g[k]) g[k] = [];
            g[k].push(item);
        });
        return g;
    }, [processed, activeGroupBy]);

    const visibleColumns = columns.filter(c => !c.hidden && !hiddenCols.has(String(c.key)));
    const handleRowClick = (item: T) => {
        setSelectedItem(item);
        onRowClick?.(item);
    };

    const toggleRow = (id: string | number, e: React.MouseEvent) => {
        e.stopPropagation();
        setSelectedRows(prev => {
            const n = new Set(prev);
            n.has(id) ? n.delete(id) : n.add(id);
            return n;
        });
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] font-sans overflow-hidden">

            {/* ── TOOLBAR ── */}
            <header className="px-3 py-2 flex items-center gap-1.5 border-b border-slate-200 dark:border-white/[0.06] bg-white dark:bg-[#1e1f21] shrink-0">
                {/* Left controls */}
                <div className="flex items-center gap-0.5">
                    <button className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/5 rounded transition-colors" title="Deshacer">
                        <Undo2 size={13} />
                    </button>
                    <button className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/5 rounded transition-colors" title="Rehacer">
                        <Redo2 size={13} />
                    </button>
                    <button className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/5 rounded transition-colors" title="Recargar">
                        <RefreshCw size={13} />
                    </button>
                </div>

                <div className="w-px h-4 bg-slate-200 dark:bg-white/10" />

                {/* Fix 3: Saved view con rename popover */}
                <div className="relative" ref={viewNameRef}>
                    <button
                        onClick={() => setShowRenameView(s => !s)}
                        className={clsx('flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all',
                            showRenameView ? 'bg-blue-50 text-blue-600 border border-blue-200' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5')}>
                        <Eye size={13} />
                        <span className="max-w-[120px] truncate">{localViewName}</span>
                        <ChevronDown size={11} className="text-slate-400" />
                    </button>
                    <AnimatePresence>
                        {showRenameView && (
                            <motion.div
                                initial={{ opacity: 0, y: -6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: -6, scale: 0.97 }} transition={{ duration: 0.13 }}
                                className="absolute top-full left-0 mt-1 z-50 w-[240px] bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-2xl p-3">
                                <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-2">Nombre de vista</p>
                                <div className="flex gap-2">
                                    <input
                                        autoFocus
                                        value={localViewName}
                                        onChange={e => setLocalViewName(e.target.value)}
                                        onKeyDown={e => { if (e.key === 'Enter') setShowRenameView(false); if (e.key === 'Escape') setShowRenameView(false); }}
                                        className="flex-1 text-[12px] font-medium text-slate-700 dark:text-slate-200 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-blue-400"
                                    />
                                    <button onClick={() => setShowRenameView(false)}
                                        className="px-2.5 py-1.5 bg-blue-600 text-white text-[11px] font-bold rounded-lg hover:bg-blue-700 transition-colors">
                                        <Check size={12} />
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Grid */}
                <button className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-colors">
                    <LayoutGrid size={13} /> Grid <ChevronDown size={11} className="text-slate-400" />
                </button>

                <div className="w-px h-4 bg-slate-200 dark:bg-white/10" />

                {/* CONFIG */}
                <div className="relative">
                    <button onClick={() => { setShowConfig(s => !s); setShowSort(false); setShowFilter(false); setShowGroup(false); }}
                        className={clsx('flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all',
                            showConfig ? 'bg-blue-50 text-blue-600 border border-blue-200' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5')}>
                        <Settings2 size={13} /> Config
                    </button>
                    <AnimatePresence>
                        {showConfig && (
                            <ConfigPopover columns={columns} hiddenCols={hiddenCols}
                                onToggleCol={toggleCol} onClose={() => setShowConfig(false)} />
                        )}
                    </AnimatePresence>
                </div>

                {/* Fix 4: GROUP con GroupByPopover funcional */}
                <div className="relative">
                    <button onClick={() => { setShowGroup(s => !s); setShowSort(false); setShowFilter(false); setShowConfig(false); }}
                        className={clsx('flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all',
                            activeGroup || showGroup ? 'bg-blue-50 text-blue-600 border border-blue-200' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5')}>
                        <Users size={13} /> Grupo
                        {activeGroup && <span className="size-4 rounded-full bg-blue-500 text-white font-semibold flex items-center justify-center">1</span>}
                    </button>
                    <AnimatePresence>
                        {showGroup && (
                            <GroupByPopover
                                columns={columns}
                                activeGroupBy={activeGroupBy}
                                onApply={key => setActiveGroupBy(key)}
                                onClose={() => setShowGroup(false)}
                            />
                        )}
                    </AnimatePresence>
                </div>

                {/* FILTER */}
                <div className="relative">
                    <button onClick={() => { setShowFilter(s => !s); setShowSort(false); setShowConfig(false); }}
                        className={clsx('flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all',
                            activeFilters || showFilter ? 'bg-blue-50 text-blue-600 border border-blue-200' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5')}>
                        <Filter size={13} /> Filtrar
                        {activeFilters && <span className="size-4 rounded-full bg-blue-500 text-white font-semibold flex items-center justify-center">{filters.length}</span>}
                    </button>
                    <AnimatePresence>
                        {showFilter && (
                            <FilterPanel columns={columns} onClose={() => setShowFilter(false)}
                                onAddFilter={(k, v) => setFilters(prev => [...prev, { key: k, value: v }])} />
                        )}
                    </AnimatePresence>
                </div>

                {/* SORT */}
                <div className="relative">
                    <button onClick={() => { setShowSort(s => !s); setShowFilter(false); setShowConfig(false); }}
                        className={clsx('flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all',
                            activeSorts || showSort ? 'bg-blue-50 text-blue-600 border border-blue-200' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5')}>
                        <ArrowUpDown size={13} /> Ordenar
                        {activeSorts && <span className="size-4 rounded-full bg-blue-500 text-white font-semibold flex items-center justify-center">{sorts.length}</span>}
                    </button>
                    <AnimatePresence>
                        {showSort && (
                            <SortPopoverV2 columns={columns} sorts={sorts}
                                onSortsChange={setSorts} onClose={() => setShowSort(false)} />
                        )}
                    </AnimatePresence>
                </div>

                <div className="w-px h-4 bg-slate-200 dark:bg-white/10" />

                {/* Drag handle */}
                <GripVertical size={13} className="text-slate-300" />

                {/* Spacer */}
                <div className="flex-1" />

                {/* Search */}
                <div className="relative w-48">
                    <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input type="text" placeholder="Buscar..."
                        className="w-full pl-7 pr-3 py-1.5 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg text-[12px] text-slate-700 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:border-blue-400 transition-colors"
                        value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
                </div>

                {/* Columns button */}
                <button className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-colors">
                    <ColumnsIcon size={13} /> Columnas
                </button>
            </header>

            {/* ── ACTIVE FILTER CHIPS ── */}
            <AnimatePresence>
                {(filters.length > 0 || sorts.length > 0) && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="flex items-center gap-2 px-4 py-1.5 bg-slate-50/60 dark:bg-white/[0.02] border-b border-slate-100 dark:border-white/5 flex-wrap overflow-hidden">
                        {sorts.map((s, i) => {
                            const col = columns.find(c => String(c.key) === s.key);
                            return (
                                <span key={`s-${i}`} className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-blue-50 border border-blue-200 text-blue-700 text-[11px] font-bold rounded-lg">
                                    {s.dir === 'asc' ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
                                    {col?.label ?? s.key}
                                    <button onClick={() => setSorts(p => p.filter((_, idx) => idx !== i))}><X size={10} /></button>
                                </span>
                            );
                        })}
                        {filters.map((f, i) => {
                            const st = f.key === 'status' ? STATUS_MAP[f.value] : null;
                            return (
                                <span key={`f-${i}`} className={clsx('inline-flex items-center gap-1.5 px-2 py-0.5 border text-[11px] font-bold rounded-lg',
                                    st ? `${st.bg} ${st.text} ${st.border}` : 'bg-blue-50 border-blue-200 text-blue-700')}>
                                    {st && <span className={clsx('size-1.5 rounded-full', st.dot)} />}
                                    {columns.find(c => String(c.key) === f.key)?.label}: {st?.label ?? f.value}
                                    <button onClick={() => setFilters(p => p.filter((_, idx) => idx !== i))}><X size={10} /></button>
                                </span>
                            );
                        })}
                        <button onClick={() => { setFilters([]); setSorts([]); }}
                            className="text-[11px] font-bold text-slate-400 hover:text-rose-500 transition-colors ml-1">
                            Limpiar todo
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── MAIN AREA (table + detail panel) ── */}
            <div className="flex flex-1 overflow-hidden">
                {/* TABLE */}
                <div className="flex-1 overflow-auto">
                    <table className="w-full border-collapse table-fixed min-w-[600px]">
                        {/* HEADER */}
                        <thead className="sticky top-0 z-20 bg-slate-50 dark:bg-[#18191b] border-b border-slate-200 dark:border-white/[0.06]">
                            <tr>
                                {/* Expand icon col */}
                                <th className="w-8 px-2 py-2.5 border-r border-slate-100 dark:border-white/5">
                                    <div className="flex items-center justify-center">
                                        <ArrowUpDown size={11} className="text-slate-300" />
                                    </div>
                                </th>
                                {/* Row # */}
                                <th className="w-9 px-2 py-2.5 border-r border-slate-100 dark:border-white/5 text-center">
                                    <span className="font-semibold text-slate-300">#</span>
                                </th>
                                {visibleColumns.map(col => (
                                    <th key={String(col.key)} style={{ width: col.width }}
                                        className="px-3 py-2.5 text-left border-r border-slate-100 dark:border-white/5 last:border-r-0 group/th cursor-pointer"
                                        onClick={() => {
                                            if (col.sortable === false) return;
                                            const existing = sorts.find(s => s.key === String(col.key));
                                            if (!existing) setSorts(prev => [...prev, { key: String(col.key), dir: 'asc' }]);
                                            else if (existing.dir === 'asc') setSorts(prev => prev.map(s => s.key === String(col.key) ? { ...s, dir: 'desc' } : s));
                                            else setSorts(prev => prev.filter(s => s.key !== String(col.key)));
                                        }}>
                                        <div className="flex items-center gap-1.5">
                                            <ColIcon type={col.type} />
                                            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 group-hover/th:text-slate-600 dark:group-hover/th:text-slate-200 transition-colors whitespace-nowrap">
                                                {col.label}
                                            </span>
                                            {sorts.find(s => s.key === String(col.key)) && (
                                                sorts.find(s => s.key === String(col.key))?.dir === 'asc'
                                                    ? <ArrowUp size={10} className="text-blue-500" />
                                                    : <ArrowDown size={10} className="text-blue-500" />
                                            )}
                                        </div>
                                    </th>
                                ))}
                                {/* + Add column */}
                                <th className="w-32 px-3 py-2.5 text-left">
                                    <button className="flex items-center gap-1 text-[11px] font-bold text-slate-300 hover:text-blue-500 transition-colors">
                                        <Plus size={12} /> Columna
                                    </button>
                                </th>
                            </tr>
                        </thead>

                        <tbody>
                            {Object.entries(groups).map(([groupName, items]) => (
                                <React.Fragment key={groupName}>
                                    {/* Group header */}
                                    {activeGroupBy && groupName !== '_all' && (
                                        <tr className="bg-slate-50/70 dark:bg-white/[0.01] sticky top-[42px] z-10">
                                            <td colSpan={visibleColumns.length + 3} className="px-4 py-1">
                                                <button onClick={() => setCollapsedGroups(p => ({ ...p, [groupName]: !p[groupName] }))}
                                                    className="flex items-center gap-2 px-2 py-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-all">
                                                    <motion.div animate={{ rotate: collapsedGroups[groupName] ? -90 : 0 }} transition={{ duration: 0.15 }}>
                                                        <ChevronDown size={13} className="text-slate-400" />
                                                    </motion.div>
                                                    <StatusChip value={groupName} />
                                                    <span className="text-[10px] font-bold text-slate-400 bg-slate-200/70 dark:bg-white/10 px-1.5 rounded-md">{items.length}</span>
                                                </button>
                                            </td>
                                        </tr>
                                    )}

                                    {/* Rows */}
                                    <AnimatePresence initial={false}>
                                        {!collapsedGroups[groupName] && items.map((item, idx) => {
                                            const isSelected = selectedItem && (selectedItem as any).id === (item as any).id;
                                            const isRowChecked = selectedRows.has((item as any).id);
                                            return (
                                                <motion.tr key={(item as any).id}
                                                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                                    transition={{ duration: 0.1, delay: idx * 0.01 }}
                                                    onClick={() => handleRowClick(item)}
                                                    className={clsx(
                                                        'group border-b border-slate-100 dark:border-white/[0.03] cursor-pointer transition-colors',
                                                        isSelected ? 'bg-blue-50/60 dark:bg-blue-500/5' : 'hover:bg-slate-50/70 dark:hover:bg-white/[0.02]'
                                                    )}>
                                                    {/* Expand */}
                                                    <td className="w-8 px-2 py-2 border-r border-slate-100 dark:border-white/5 text-center" onClick={e => e.stopPropagation()}>
                                                        <button onClick={() => handleRowClick(item)}
                                                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-100 dark:hover:bg-white/10 text-slate-400 transition-all">
                                                            <Maximize2 size={11} />
                                                        </button>
                                                    </td>
                                                    {/* # or checkbox */}
                                                    <td className="w-9 px-2 py-2 border-r border-slate-100 dark:border-white/5 text-center" onClick={e => toggleRow((item as any).id, e)}>
                                                        {isRowChecked ? (
                                                            <div className="size-4 rounded bg-blue-500 border-blue-500 flex items-center justify-center mx-auto">
                                                                <Check size={10} className="text-white" />
                                                            </div>
                                                        ) : (
                                                            <span className="text-[11px] font-bold text-slate-300 group-hover:hidden">{idx + 1}</span>
                                                        )}
                                                        <div className={clsx('size-4 rounded border-2 border-slate-300 dark:border-white/20 mx-auto', !isRowChecked ? 'hidden group-hover:flex items-center justify-center' : 'hidden')} />
                                                    </td>
                                                    {/* Data cells */}
                                                    {visibleColumns.map(col => (
                                                        <td key={String(col.key)}
                                                            className="px-3 py-2 border-r border-slate-100 dark:border-white/5 last:border-r-0 overflow-hidden">
                                                            <TableCell column={col} value={(item as any)[col.key]} item={item} />
                                                        </td>
                                                    ))}
                                                    <td className="w-32" />
                                                </motion.tr>
                                            );
                                        })}
                                    </AnimatePresence>

                                    {/* Quick-add per group */}
                                    {!collapsedGroups[groupName] && (
                                        <tr className="group/add">
                                            <td colSpan={visibleColumns.length + 3} className="px-4 py-0.5">
                                                {quickAddGroup === groupName ? (
                                                    <div className="flex items-center gap-3 py-1.5">
                                                        <input autoFocus value={quickAddTitle}
                                                            onChange={e => setQuickAddTitle(e.target.value)}
                                                            onKeyDown={e => {
                                                                if (e.key === 'Enter' && quickAddTitle.trim()) { onAddItem?.(groupName); setQuickAddTitle(''); setQuickAddGroup(null); }
                                                                if (e.key === 'Escape') { setQuickAddGroup(null); setQuickAddTitle(''); }
                                                            }}
                                                            placeholder="Nombre de tarea... (Enter para guardar)"
                                                            className="flex-1 text-[12px] text-slate-700 dark:text-slate-200 bg-transparent outline-none placeholder:text-slate-400" />
                                                        <button onClick={() => setQuickAddGroup(null)} className="p-1 text-slate-400 hover:text-slate-600"><X size={13} /></button>
                                                    </div>
                                                ) : (
                                                    <button onClick={() => setQuickAddGroup(groupName)}
                                                        className="flex items-center gap-1.5 text-[11px] font-bold text-slate-300 hover:text-blue-500 dark:text-white/10 dark:hover:text-blue-400 py-1.5 transition-all opacity-0 group-hover/add:opacity-100">
                                                        <Plus size={12} /> Agregar fila
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            ))}

                            {/* Empty state */}
                            {processed.length === 0 && !isLoading && (
                                <tr>
                                    <td colSpan={visibleColumns.length + 3} className="py-1.5 text-center">
                                        <div className="flex flex-col items-center gap-3">
                                            <div className="size-7 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center">
                                                <Table2 size={24} className="text-slate-200" />
                                            </div>
                                            <p className="text-slate-400 text-sm font-medium">{emptyMessage}</p>
                                            {onAddItem && (
                                                <button onClick={() => onAddItem?.()}
                                                    className="text-xs font-bold text-blue-500 hover:underline">
                                                    Crear el primero
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>

                    {/* + Add row footer */}
                    <div className="px-4 py-2 border-t border-slate-100 dark:border-white/5">
                        <button onClick={() => onAddItem?.()}
                            className="flex items-center gap-1.5 text-[12px] font-bold text-slate-400 hover:text-blue-600 transition-colors">
                            <Plus size={13} /> Agregar fila
                            <span className="ml-1 text-slate-300 font-normal text-[10px]">Shift+Enter</span>
                        </button>
                    </div>
                </div>

                {/* ── DETAIL PANEL (non-blocking, resizable) ── */}
                <AnimatePresence>
                    {selectedItem && (
                        <RowDetailPanel
                            item={selectedItem}
                            columns={visibleColumns}
                            onClose={closePanel}
                            onSave={(id, edits) => {
                                // Fix 2: propagar ediciones al componente padre
                                Object.entries(edits).forEach(([field, value]) => {
                                    onUpdateItem?.(id, field as keyof T, value);
                                });
                            }}
                            renderContent={renderDetailPanel}
                        />
                    )}
                </AnimatePresence>
            </div>

            {/* ── FOOTER ── */}
            <footer className="px-4 py-1.5 border-t border-slate-100 dark:border-white/[0.04] flex items-center justify-between bg-slate-50/50 dark:bg-black/10 shrink-0">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
                    {processed.length} de {data.length} registros
                    {filters.length > 0 && ` · ${filters.length} filtro${filters.length > 1 ? 's' : ''}`}
                </span>
                {sorts.length > 0 && (
                    <span className="text-[10px] font-bold text-blue-500 flex items-center gap-1">
                        <ArrowUpDown size={10} /> {sorts.length} criterio{sorts.length > 1 ? 's' : ''}
                    </span>
                )}
            </footer>
        </div>
    );
}

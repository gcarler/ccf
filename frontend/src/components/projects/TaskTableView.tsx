
"use client";

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import {
    AllCommunityModule, ModuleRegistry, themeQuartz,
    ColDef, ICellRendererParams, GetRowIdParams,
} from 'ag-grid-community';
import {
    Plus, Flag, Calendar, User, X, CheckCircle2, Circle,
    ChevronDown, AlertCircle,
    ArrowUp, ArrowDown, ChevronsUpDown, Check, Search, Loader2,
    ChevronLeft, Trash2, MessageSquare, Settings2, SlidersHorizontal,
    Layers, Eye, EyeOff, Filter,
} from 'lucide-react';
import * as Popover from '@radix-ui/react-popover';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { ProjectTaskRecord } from '@/types/projects';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

ModuleRegistry.registerModules([AllCommunityModule]);

// ─── Date helpers ──────────────────────────────────────────────────────────────
const DAYS_ES   = ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa'];
const MONTHS_ES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
function getDaysInMonth(y: number, m: number) { return new Date(y, m + 1, 0).getDate(); }
function getFirstDay(y: number, m: number)    { return new Date(y, m, 1).getDay(); }
function formatRelative(date: Date): string {
    const today = new Date(); today.setHours(0,0,0,0);
    const d = new Date(date); d.setHours(0,0,0,0);
    const diff = Math.round((d.getTime() - today.getTime()) / 86400000);
    if (diff === 0) return 'Hoy';
    if (diff === 1) return 'Mañana';
    if (diff === -1) return 'Ayer';
    if (diff < 0) return d.toLocaleDateString('es-PE', { day:'2-digit', month:'short' });
    if (diff <= 7) return `En ${diff}d`;
    return d.toLocaleDateString('es-PE', { day:'2-digit', month:'short' });
}

// ─── Status / Priority configs ─────────────────────────────────────────────────
const STATUS_OPTIONS = [
    { value:'todo',        label:'Pendiente',   dot:'bg-slate-400',   bg:'bg-slate-100 dark:bg-white/5',            text:'text-slate-600 dark:text-slate-300',      border:'border-slate-200 dark:border-white/10' },
    { value:'in_progress', label:'En Progreso', dot:'bg-blue-500',    bg:'bg-blue-100 dark:bg-blue-500/20',         text:'text-blue-700 dark:text-blue-300',        border:'border-blue-200 dark:border-blue-500/30' },
    { value:'blocked',     label:'Bloqueado',   dot:'bg-rose-500',    bg:'bg-rose-100 dark:bg-rose-500/20',         text:'text-rose-700 dark:text-rose-300',        border:'border-rose-200 dark:border-rose-500/30' },
    { value:'completed',   label:'Completado',  dot:'bg-emerald-500', bg:'bg-emerald-100 dark:bg-emerald-500/20',   text:'text-emerald-700 dark:text-emerald-300',  border:'border-emerald-200 dark:border-emerald-500/30' },
] as const;
function getStatus(val: string) { return STATUS_OPTIONS.find(s => s.value === val) ?? STATUS_OPTIONS[0]; }

const PRIORITY_OPTIONS = [
    { value:'low',    label:'Baja',    color:'text-slate-400',  fill:'#94a3b8' },
    { value:'normal', label:'Media',   color:'text-blue-500',   fill:'#3b82f6' },
    { value:'high',   label:'Alta',    color:'text-orange-500', fill:'#f97316' },
    { value:'urgent', label:'Urgente', color:'text-rose-500',   fill:'#ef4444' },
] as const;
function getPriority(val: string) { return PRIORITY_OPTIONS.find(p => p.value === val) ?? PRIORITY_OPTIONS[1]; }

const STATUS_ORDER: Record<string, number> = { urgent:0, in_progress:1, todo:2, pending:2, blocked:3, done:4, completed:5 };
const PRIORITY_ORDER: Record<string, number> = { urgent:0, high:1, normal:2, low:3 };

const FlagIcon = ({ fill, size = 14 }: { fill: string; size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} xmlns="http://www.w3.org/2000/svg">
        <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
        <line x1="4" y1="22" x2="4" y2="15" stroke={fill} strokeWidth="2" strokeLinecap="round"/>
    </svg>
);

// ─── Inline Status Cell ────────────────────────────────────────────────────────
function InlineStatusCell({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    const [open, setOpen] = useState(false);
    const st = getStatus(value);
    return (
        <Popover.Root open={open} onOpenChange={setOpen}>
            <Popover.Trigger asChild>
                <button onClick={e => e.stopPropagation()} className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-bold transition-all whitespace-nowrap', st.bg, st.text, st.border, 'hover:opacity-80', open && 'ring-2 ring-blue-500/30')}>
                    <div className={clsx('size-1.5 rounded-full shrink-0', st.dot)} />{st.label}<ChevronDown size={10} className="ml-0.5 opacity-60" />
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content className="z-[500] min-w-[180px] bg-white dark:bg-[#1e1f21] rounded-md shadow-2xl border border-slate-200/80 dark:border-white/10 p-1.5" sideOffset={6} align="start" onOpenAutoFocus={e => e.preventDefault()}>
                    <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 px-2 pt-1 pb-2">Estado</p>
                    {STATUS_OPTIONS.map(s => (
                        <button key={s.value} onClick={() => { onChange(s.value); setOpen(false); }}
                            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                            <div className={clsx('size-2 rounded-full shrink-0', s.dot)} />
                            <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200 flex-1 text-left">{s.label}</span>
                            {s.value === value && <Check size={12} className="text-blue-500" />}
                        </button>
                    ))}
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Inline Priority Cell ──────────────────────────────────────────────────────
function InlinePriorityCell({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    const [open, setOpen] = useState(false);
    const pr = getPriority(value);
    return (
        <Popover.Root open={open} onOpenChange={setOpen}>
            <Popover.Trigger asChild>
                <button onClick={e => e.stopPropagation()} className={clsx('flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-bold transition-all', 'hover:bg-slate-100 dark:hover:bg-white/5', open && 'bg-slate-50 dark:bg-white/5 ring-1 ring-slate-200 dark:ring-white/10')}>
                    <FlagIcon fill={pr.fill} size={13} /><span className={pr.color}>{pr.label}</span><ChevronDown size={10} className="text-slate-400" />
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content className="z-[500] min-w-[160px] bg-white dark:bg-[#1e1f21] rounded-md shadow-2xl border border-slate-200/80 dark:border-white/10 p-1.5" sideOffset={6} align="start" onOpenAutoFocus={e => e.preventDefault()}>
                    <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 px-2 pt-1 pb-2">Prioridad</p>
                    {PRIORITY_OPTIONS.map(p => (
                        <button key={p.value} onClick={() => { onChange(p.value); setOpen(false); }} className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                            <FlagIcon fill={p.fill} size={12} /><span className={clsx('text-[12px] font-semibold flex-1 text-left', p.color)}>{p.label}</span>
                            {p.value === value && <Check size={12} className="text-blue-500" />}
                        </button>
                    ))}
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Inline Date Cell ──────────────────────────────────────────────────────────
function InlineDateCell({ value, onChange }: { value?: string | null; onChange: (v: string | null) => void }) {
    const [open, setOpen] = useState(false);
    const today    = new Date(); today.setHours(0,0,0,0);
    const parsed   = value ? new Date(value + 'T00:00:00') : null;
    const safeYear  = parsed && !isNaN(parsed.getTime()) ? parsed.getFullYear() : today.getFullYear();
    const safeMonth = parsed && !isNaN(parsed.getTime()) ? parsed.getMonth()    : today.getMonth();
    const [viewYear, setViewYear]   = useState(safeYear);
    const [viewMonth, setViewMonth] = useState(safeMonth);
    const isOverdue = parsed && !isNaN(parsed.getTime()) && parsed < today;
    const isToday2  = parsed && !isNaN(parsed.getTime()) && parsed.toDateString() === today.toDateString();
    const label     = parsed && !isNaN(parsed.getTime()) ? formatRelative(parsed) : null;
    const rawFD = getFirstDay(viewYear, viewMonth);
    const firstDay = isNaN(rawFD) ? 0 : Math.max(0, Math.min(6, rawFD));
    const daysCount = Math.max(0, getDaysInMonth(viewYear, viewMonth));
    const cells: (number | null)[] = [...Array(firstDay).fill(null), ...Array.from({length:daysCount},(_,i)=>i+1)];
    const selectDay = (day: number) => { onChange(new Date(viewYear, viewMonth, day).toISOString().split('T')[0]); setOpen(false); };
    return (
        <Popover.Root open={open} onOpenChange={(v) => { setOpen(v); if(!v) return; if(parsed && !isNaN(parsed.getTime())) { setViewYear(parsed.getFullYear()); setViewMonth(parsed.getMonth()); } }}>
            <Popover.Trigger asChild>
                <button onClick={e => e.stopPropagation()} className={clsx('group flex items-center gap-1.5 px-2 py-1 rounded-lg text-[12px] font-medium whitespace-nowrap transition-all', 'hover:bg-slate-100 dark:hover:bg-white/5', open && 'bg-slate-50 dark:bg-white/5 ring-1 ring-slate-200 dark:ring-white/10', isOverdue ? 'text-rose-500 dark:text-rose-400' : isToday2 ? 'text-amber-500 dark:text-amber-400' : label ? 'text-slate-700 dark:text-slate-300' : 'text-slate-300 dark:text-white/20')}>
                    {isOverdue ? <AlertCircle size={13} className="shrink-0" /> : <Calendar size={13} className="shrink-0" />}
                    {label ?? <span className="group-hover:text-slate-400 transition-colors">—</span>}
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content className="z-[500] w-[248px] bg-white dark:bg-[#1e1f21] rounded-lg shadow-2xl border border-slate-200/80 dark:border-white/10 p-3 select-none" sideOffset={6} align="start" onOpenAutoFocus={e => e.preventDefault()}>
                    <div className="flex items-center justify-between mb-3">
                        <button onClick={() => { let m=viewMonth-1,y=viewYear; if(m<0){m=11;y--;} setViewMonth(m);setViewYear(y); }} className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400"><ChevronLeft size={14}/></button>
                        <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">{MONTHS_ES[viewMonth]} {viewYear}</span>
                        <button onClick={() => { let m=viewMonth+1,y=viewYear; if(m>11){m=0;y++;} setViewMonth(m);setViewYear(y); }} className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400"><ChevronDown size={14}/></button>
                    </div>
                    <div className="grid grid-cols-7 mb-1">{DAYS_ES.map(d => <div key={d} className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 text-center py-0.5">{d}</div>)}</div>
                    <div className="grid grid-cols-7 gap-y-0.5">
                        {cells.map((day, i) => {
                            if (!day) return <div key={`e-${i}`} />;
                            const cd = new Date(viewYear, viewMonth, day);
                            const isSel = parsed && !isNaN(parsed.getTime()) && cd.toDateString()===parsed.toDateString();
                            const isTd  = cd.toDateString()===today.toDateString();
                            const isPast = cd < today && !isTd;
                            return <button key={day} onClick={() => selectDay(day)} className={clsx('size-8 rounded-lg text-[12px] font-medium transition-all mx-auto flex items-center justify-center', isSel ? 'bg-blue-600 text-white font-bold shadow-sm' : isTd ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 font-bold ring-1 ring-blue-200' : isPast ? 'text-slate-300 dark:text-white/20 hover:bg-slate-50' : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5')}>{day}</button>;
                        })}
                    </div>
                    <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-100 dark:border-white/5">
                        <button onClick={() => selectDay(today.getDate())} className="flex-1 text-[11px] font-bold text-blue-600 dark:text-blue-400 py-1.5 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors">Hoy</button>
                        {value && <button onClick={() => { onChange(null); setOpen(false); }} className="flex-1 text-[11px] font-bold text-rose-500 py-1.5 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors">Quitar</button>}
                    </div>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Inline User Cell ──────────────────────────────────────────────────────────
type UserRecord = { id: number; username: string; email?: string };
function InlineUserCell({ value, token, onChange }: { value?: number | null; token: string | null; onChange: (userId: number | null, name: string | null) => void }) {
    const [open, setOpen] = useState(false);
    const [query, setQuery]   = useState('');
    const [users, setUsers]   = useState<UserRecord[]>([]);
    const [loading, setLoading] = useState(false);
    const [displayName, setDisplayName] = useState<string | null>(null);
    useEffect(() => {
        if (!open) return;
        setLoading(true);
        apiFetch('/crm/members/', { method: 'GET', token: token ?? undefined })
            .then((data: any) => {
                const list: UserRecord[] = Array.isArray(data)
                    ? data.map((m: any) => ({ id: m.user?.id ?? m.id, username: m.user?.username ?? m.username ?? `#${m.id}`, email: m.user?.email ?? m.email }))
                    : [];
                setUsers(list);
                if (value) { const found = list.find(u => u.id === value); if (found) setDisplayName(found.username); }
            })
            .catch(() => setUsers([]))
            .finally(() => setLoading(false));
    }, [open, token, value]);
    const filtered = query ? users.filter(u => u.username.toLowerCase().includes(query.toLowerCase())) : users;
    return (
        <Popover.Root open={open} onOpenChange={setOpen}>
            <Popover.Trigger asChild>
                <button onClick={e => e.stopPropagation()} className={clsx('flex items-center gap-2 px-2 py-1 rounded-lg transition-all', 'hover:bg-slate-100 dark:hover:bg-white/5', open && 'bg-slate-50 dark:bg-white/5 ring-1 ring-slate-200 dark:ring-white/10')}>
                    <div className={clsx('size-6 rounded-full flex items-center justify-center font-semibold shrink-0', value ? 'bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-300' : 'bg-slate-100 dark:bg-white/5 text-slate-400')}>
                        {value && displayName ? displayName.charAt(0).toUpperCase() : <User size={11} />}
                    </div>
                    <span className="text-[12px] font-medium text-slate-600 dark:text-slate-400 truncate max-w-[80px]">{displayName ?? (value ? `#${value}` : '—')}</span>
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content className="z-[500] w-[240px] bg-white dark:bg-[#1e1f21] rounded-md shadow-2xl border border-slate-200/80 dark:border-white/10 overflow-hidden" sideOffset={6} align="start" onOpenAutoFocus={e => e.preventDefault()}>
                    <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-100 dark:border-white/5">
                        <Search size={13} className="text-slate-400 shrink-0" />
                        <input autoFocus value={query} onChange={e => setQuery(e.target.value)} placeholder="Buscar usuario..." className="flex-1 text-[12px] text-slate-700 dark:text-slate-200 bg-transparent outline-none placeholder:text-slate-400" />
                        {query && <button onClick={() => setQuery('')}><X size={12} className="text-slate-400" /></button>}
                    </div>
                    <div className="max-h-[200px] overflow-y-auto py-1">
                        {loading ? <div className="flex items-center justify-center py-1.5"><Loader2 size={16} className="text-blue-500 animate-spin" /></div>
                        : filtered.length === 0 ? <p className="text-[11px] text-slate-400 text-center py-1.5">Sin resultados</p>
                        : <>
                            {value && <button onClick={() => { onChange(null, null); setDisplayName(null); setOpen(false); }} className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-500 transition-colors"><X size={12} /><span className="text-[11px] font-bold">Quitar asignación</span></button>}
                            {filtered.map(u => (
                                <button key={u.id} onClick={() => { onChange(u.id, u.username); setDisplayName(u.username); setOpen(false); }} className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                    <div className="size-6 rounded-full bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center font-semibold text-blue-600 shrink-0">{u.username.charAt(0).toUpperCase()}</div>
                                    <div className="flex-1 text-left"><p className="text-[12px] font-semibold text-slate-700 dark:text-slate-200">{u.username}</p>{u.email && <p className="text-[10px] text-slate-400 truncate">{u.email}</p>}</div>
                                    {u.id === value && <Check size={12} className="text-blue-500" />}
                                </button>
                            ))}
                        </>}
                    </div>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── AG Grid Themes ────────────────────────────────────────────────────────────
const lightTheme = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 40, headerHeight: 36, backgroundColor: '#ffffff', foregroundColor: '#1e293b', borderColor: '#e2e8f0', oddRowBackgroundColor: '#f8fafc', headerBackgroundColor: '#f1f5f9', headerTextColor: '#475569', selectedRowBackgroundColor: '#eef2ff', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });
const darkTheme  = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 40, headerHeight: 36, backgroundColor: 'rgb(15 23 42)', foregroundColor: '#e2e8f0', borderColor: 'rgba(255,255,255,0.08)', oddRowBackgroundColor: 'rgba(255,255,255,0.02)', headerBackgroundColor: 'rgba(255,255,255,0.04)', headerTextColor: '#94a3b8', selectedRowBackgroundColor: 'rgba(99,102,241,0.15)', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });

// ─── AG Grid Cell Renderers (use context for callbacks) ────────────────────────
function TitleRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const { onOpenTask } = params.context ?? {};
    const task = params.data as ProjectTaskRecord;
    return (
        <button onClick={(e) => { e.stopPropagation(); onOpenTask?.(task); }}
            className="flex items-center gap-2 h-full w-full text-left group">
            <div className={clsx('size-4 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                task.status === 'completed' ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-300 dark:border-white/20')}>
                {task.status === 'completed' && <span className="text-[7px] font-bold">✓</span>}
            </div>
            <span className={clsx('text-[13px] font-semibold truncate group-hover:text-indigo-600 transition-colors', task.status === 'completed' ? 'line-through text-slate-400' : 'text-slate-800 dark:text-slate-200')}>
                {task.title}
            </span>
            {(task.comments_count ?? 0) > 0 && (
                <span className="ml-auto flex items-center gap-0.5 text-slate-400 shrink-0">
                    <MessageSquare size={11} /><span className="text-[10px]">{task.comments_count}</span>
                </span>
            )}
        </button>
    );
}

function StatusRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const { applyChangeRef } = params.context ?? {};
    const task = params.data as ProjectTaskRecord;
    return <InlineStatusCell value={task.status ?? 'todo'} onChange={(v) => applyChangeRef?.current?.(task.id, 'status', v)} />;
}

function PriorityRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const { applyChangeRef } = params.context ?? {};
    const task = params.data as ProjectTaskRecord;
    return <InlinePriorityCell value={task.priority ?? 'normal'} onChange={(v) => applyChangeRef?.current?.(task.id, 'priority', v)} />;
}

function DateRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const { applyChangeRef } = params.context ?? {};
    const task = params.data as ProjectTaskRecord;
    return <InlineDateCell value={task.due_date} onChange={(v) => applyChangeRef?.current?.(task.id, 'due_date', v)} />;
}

function AssigneeRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const { applyChangeRef, token } = params.context ?? {};
    const task = params.data as ProjectTaskRecord;
    return <InlineUserCell value={task.assignee_id} token={token} onChange={(id, name) => applyChangeRef?.current?.(task.id, 'assignee_id', id)} />;
}

// ─── Props / Types ─────────────────────────────────────────────────────────────
interface Props {
    projectId?: string | number;
    tasks: ProjectTaskRecord[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: (status: string, dueDate?: string, title?: string) => Promise<void> | void;
    onTaskUpdated?: (taskId: number, field: string, value: any) => void;
}

type GroupKey = 'status' | 'priority' | 'none';
type ColumnId = 'title' | 'status' | 'priority' | 'assignee' | 'due_date' | 'comments';
const ALL_COLUMNS: { id: ColumnId; label: string }[] = [
    { id: 'title',    label: 'Nombre' },
    { id: 'status',   label: 'Estado' },
    { id: 'priority', label: 'Prioridad' },
    { id: 'assignee', label: 'Asignado' },
    { id: 'due_date', label: 'Fecha límite' },
    { id: 'comments', label: 'Comentarios' },
];
type ActiveFilter = { field: 'status' | 'priority'; value: string; label: string };

// ─── Main Component ────────────────────────────────────────────────────────────
export default function TaskTableView({ projectId, tasks, onOpenTask, onAddTask, onTaskUpdated }: Props) {
    const { token } = useAuth();
    const { openLayer } = useSidebarLayers();
    const gridRef = useRef<AgGridReact>(null);
    const [isDark, setIsDark] = useState(false);
    const [overrides, setOverrides] = useState<Record<number, Partial<ProjectTaskRecord>>>({});
    const [groupBy, setGroupBy]     = useState<GroupKey>('status');
    const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>([]);
    const [visibleCols, setVisibleCols] = useState<Set<ColumnId>>(new Set<ColumnId>(['title','status','priority','assignee','due_date']));
    const [cfgOpen, setCfgOpen]     = useState(false);
    const [filterOpen, setFilterOpen] = useState(false);
    const [groupOpen, setGroupOpen]   = useState(false);
    const [quickAddGroup, setQuickAddGroup] = useState<string | null>(null);
    const [quickAddTitle, setQuickAddTitle] = useState('');
    const [isLoaded, setIsLoaded]   = useState(false);

    // Dark mode detection
    useEffect(() => {
        const check = () => setIsDark(document.documentElement.classList.contains('dark'));
        check();
        const obs = new MutationObserver(check);
        obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        return () => obs.disconnect();
    }, []);

    // Preferences persistence
    useEffect(() => {
        const key = projectId ? `ccf_task_table_prefs_${projectId}` : 'ccf_task_table_prefs';
        try {
            const stored = localStorage.getItem(key);
            if (stored) {
                const p = JSON.parse(stored);
                if (p.groupBy) setGroupBy(p.groupBy);
                if (p.activeFilters) setActiveFilters(p.activeFilters);
                if (p.visibleCols) setVisibleCols(new Set(p.visibleCols));
            }
        } catch { /* ignore */ }
        setIsLoaded(true);
    }, [projectId]);

    useEffect(() => {
        if (!isLoaded) return;
        const key = projectId ? `ccf_task_table_prefs_${projectId}` : 'ccf_task_table_prefs';
        try { localStorage.setItem(key, JSON.stringify({ groupBy, activeFilters, visibleCols: Array.from(visibleCols) })); } catch { /* ignore */ }
    }, [isLoaded, projectId, groupBy, activeFilters, visibleCols]);

    // Optimistic update
    const applyChange = useCallback(async (taskId: number, field: string, value: any) => {
        setOverrides(prev => ({ ...prev, [taskId]: { ...prev[taskId], [field]: value } }));
        try {
            await apiFetch(`/projects/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify({ [field]: value }), token: token ?? undefined });
            onTaskUpdated?.(taskId, field, value);
        } catch {
            setOverrides(prev => { const n = { ...prev }; delete n[taskId]; return n; });
        }
    }, [token, onTaskUpdated]);

    // Stable ref for applyChange so cell renderers always have latest version
    const applyChangeRef = useRef(applyChange);
    useEffect(() => { applyChangeRef.current = applyChange; }, [applyChange]);

    // Resolve optimistic overrides
    const resolveTask = useCallback((t: ProjectTaskRecord): ProjectTaskRecord => ({ ...t, ...(overrides[Number(t.id)] ?? {}) }), [overrides]);

    // Process: filter
    const processed = useMemo(() => {
        let list = tasks.map(resolveTask);
        for (const f of activeFilters) {
            list = list.filter(t => f.field === 'status' ? t.status === f.value : t.priority === f.value);
        }
        return list;
    }, [tasks, activeFilters, resolveTask]);

    // Flatten with group headers
    const rowData = useMemo(() => {
        if (groupBy === 'none') return processed;
        const groups: Record<string, ProjectTaskRecord[]> = {};
        processed.forEach(t => {
            const k = groupBy === 'priority' ? (t.priority ?? 'normal') : (t.status ?? 'todo');
            if (!groups[k]) groups[k] = [];
            groups[k].push(t);
        });
        const order: string[] = groupBy === 'priority' ? PRIORITY_OPTIONS.map(p => p.value) : STATUS_OPTIONS.map(s => s.value);
        const flat: any[] = [];
        const sorted = Object.entries(groups).sort(([a],[b]) => (order.indexOf(a as any) ?? 99) - (order.indexOf(b as any) ?? 99));
        sorted.forEach(([key, rows]) => {
            flat.push({ __isGroup: true, __groupKey: key, __groupCount: rows.length, id: `__group__${key}` });
            flat.push(...rows);
        });
        return flat;
    }, [processed, groupBy]);

    // Column definitions
    const colDefs = useMemo<ColDef[]>(() => {
        const cols: ColDef[] = [];
        if (visibleCols.has('title'))    cols.push({ field: 'title',      headerName: 'Nombre',       flex: 3, minWidth: 220, cellRenderer: TitleRenderer, sortable: true });
        if (visibleCols.has('status'))   cols.push({ field: 'status',     headerName: 'Estado',       width: 160, cellRenderer: StatusRenderer, sortable: true });
        if (visibleCols.has('priority')) cols.push({ field: 'priority',   headerName: 'Prioridad',    width: 140, cellRenderer: PriorityRenderer, sortable: true });
        if (visibleCols.has('assignee')) cols.push({ field: 'assignee_id',headerName: 'Asignado',     width: 160, cellRenderer: AssigneeRenderer, sortable: false });
        if (visibleCols.has('due_date')) cols.push({ field: 'due_date',   headerName: 'Fecha límite', width: 140, cellRenderer: DateRenderer, sortable: true });
        return cols.map(c => ({ ...c, resizable: true, editable: false, suppressHeaderMenuButton: false }));
    }, [visibleCols]);

    // Full-width group row renderer
    const isFullWidthRow = useCallback((p: any) => !!p.rowNode.data?.__isGroup, []);
    const fullWidthCellRenderer = useCallback(({ data: row }: any) => {
        const label = groupBy === 'priority'
            ? (getPriority(row.__groupKey)?.label ?? row.__groupKey)
            : (getStatus(row.__groupKey)?.label ?? row.__groupKey);
        const dot = groupBy === 'status' ? getStatus(row.__groupKey)?.dot : undefined;
        return (
            <div className="flex items-center gap-2.5 px-4 h-full bg-slate-50 dark:bg-white/[0.03] border-b border-slate-200 dark:border-white/5">
                {dot && <span className={clsx('size-2 rounded-full flex-shrink-0', dot)} />}
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">{label}</span>
                <span className="text-[10px] font-semibold text-slate-400 bg-slate-200 dark:bg-white/10 rounded-full px-2 py-0.5">{row.__groupCount}</span>
                <button onClick={() => setQuickAddGroup(row.__groupKey)}
                    className="ml-auto flex items-center gap-1 text-[10px] font-semibold text-indigo-500 hover:text-indigo-700 transition-colors">
                    <Plus size={11} /> Agregar
                </button>
            </div>
        );
    }, [groupBy]);

    // AG Grid context
    const gridContext = useMemo(() => ({ applyChangeRef, onOpenTask, token }), [onOpenTask, token]);

    const getRowId = useCallback((p: GetRowIdParams) => String((p.data as any).id), []);
    const getRowHeight = useCallback((p: any) => p.data?.__isGroup ? 32 : 40, []);

    // Quick add task
    const handleQuickAdd = async (status: string, title: string) => {
        try {
            await apiFetch(`/projects/${projectId}/tasks`, { method: 'POST', body: JSON.stringify({ title, status, priority: 'normal' }), token: token ?? undefined });
            onAddTask(status);
        } catch { /* silently fail */ }
        setQuickAddGroup(null);
        setQuickAddTitle('');
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] font-sans overflow-hidden">

            {/* ── TOOLBAR ── */}
            <div className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 border-b border-slate-100 dark:border-white/[0.06] bg-slate-50/60 dark:bg-black/10 flex-wrap">

                {/* Column visibility */}
                <Popover.Root open={cfgOpen} onOpenChange={setCfgOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all', cfgOpen ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5')}>
                            <Settings2 size={12} /> Columnas
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start" className="z-[500] w-52 bg-white dark:bg-[#1e1f21] rounded-md shadow-2xl border border-slate-200/80 dark:border-white/10 p-2">
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 px-2 py-1.5">Columnas visibles</p>
                            {ALL_COLUMNS.map(col => (
                                <button key={col.id} onClick={() => setVisibleCols(prev => { const n = new Set(prev); if (n.has(col.id)) { if (col.id !== 'title') n.delete(col.id); } else n.add(col.id); return n; })}
                                    className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                    {visibleCols.has(col.id) ? <Eye size={13} className="text-blue-500 shrink-0" /> : <EyeOff size={13} className="text-slate-300 shrink-0" />}
                                    <span className={clsx('text-[12px] font-medium flex-1 text-left', visibleCols.has(col.id) ? 'text-slate-700 dark:text-slate-200' : 'text-slate-400')}>{col.label}</span>
                                    {col.id === 'title' && <span className="text-[9px] text-slate-300">fijo</span>}
                                </button>
                            ))}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                <div className="w-px h-4 bg-slate-200 dark:bg-white/10" />

                {/* Group by */}
                <Popover.Root open={groupOpen} onOpenChange={setGroupOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all', groupBy !== 'status' ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5')}>
                            <Layers size={12} /> Agrupar{groupBy !== 'none' ? `: ${groupBy === 'status' ? 'Estado' : 'Prioridad'}` : ''}
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start" className="z-[500] w-52 bg-white dark:bg-[#1e1f21] rounded-md shadow-2xl border border-slate-200/80 dark:border-white/10 p-1.5">
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 px-2 pt-1 pb-2">Agrupar por</p>
                            {([['status','Estado'],['priority','Prioridad'],['none','Sin agrupación']] as const).map(([k, lbl]) => (
                                <button key={k} onClick={() => { setGroupBy(k); setGroupOpen(false); }}
                                    className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                    <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200 flex-1 text-left">{lbl}</span>
                                    {groupBy === k && <Check size={12} className="text-blue-500" />}
                                </button>
                            ))}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                {/* Filter */}
                <Popover.Root open={filterOpen} onOpenChange={setFilterOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all', activeFilters.length > 0 ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5')}>
                            <Filter size={12} /> Filtrar{activeFilters.length > 0 ? ` (${activeFilters.length})` : ''}
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start" className="z-[500] w-64 bg-white dark:bg-[#1e1f21] rounded-md shadow-2xl border border-slate-200/80 dark:border-white/10 p-2">
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 px-2 py-1.5">Por Estado</p>
                            <div className="flex flex-wrap gap-1.5 px-2 pb-2">
                                {STATUS_OPTIONS.map(s => {
                                    const active = activeFilters.some(f => f.field === 'status' && f.value === s.value);
                                    return <button key={s.value} onClick={() => setActiveFilters(prev => active ? prev.filter(f => !(f.field==='status' && f.value===s.value)) : [...prev, { field: 'status', value: s.value, label: s.label }])}
                                        className={clsx('flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border transition-all', active ? `${s.bg} ${s.text} ${s.border} ring-2 ring-blue-500/30` : `${s.bg} ${s.text} ${s.border} opacity-60 hover:opacity-100`)}>
                                        <div className={clsx('size-1.5 rounded-full', s.dot)} />{s.label}
                                    </button>;
                                })}
                            </div>
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 px-2 py-1.5 border-t border-slate-100 dark:border-white/5">Por Prioridad</p>
                            <div className="flex flex-wrap gap-1.5 px-2 pb-2">
                                {PRIORITY_OPTIONS.map(p => {
                                    const active = activeFilters.some(f => f.field === 'priority' && f.value === p.value);
                                    return <button key={p.value} onClick={() => setActiveFilters(prev => active ? prev.filter(f => !(f.field==='priority' && f.value===p.value)) : [...prev, { field: 'priority', value: p.value, label: p.label }])}
                                        className={clsx('flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border transition-all bg-slate-50 dark:bg-white/5 border-slate-200 dark:border-white/10', active ? 'ring-2 ring-blue-500/30 opacity-100' : 'opacity-60 hover:opacity-100', p.color)}>
                                        <FlagIcon fill={p.fill} size={11} />{p.label}
                                    </button>;
                                })}
                            </div>
                            {activeFilters.length > 0 && <button onClick={() => setActiveFilters([])} className="w-full text-[11px] font-bold text-rose-500 py-1.5 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors border-t border-slate-100 dark:border-white/5 mt-1">Limpiar filtros</button>}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                <div className="ml-auto flex items-center gap-1.5">
                    {activeFilters.length > 0 && (
                        <div className="flex gap-1">
                            {activeFilters.map((f, i) => <span key={i} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-500/10 text-blue-600 text-[10px] font-semibold">{f.label}<button onClick={() => setActiveFilters(p => p.filter((_,j) => j !== i))}><X size={9} /></button></span>)}
                        </div>
                    )}
                    <button onClick={() => onAddTask('todo')} className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors">
                        <Plus size={13} /> Nueva tarea
                    </button>
                </div>
            </div>

            {/* Quick add row */}
            <AnimatePresence>
                {quickAddGroup && (
                    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                        className="shrink-0 flex items-center gap-3 px-4 py-2.5 bg-blue-50/50 dark:bg-blue-500/5 border-b border-slate-100 dark:border-white/5">
                        <Circle size={15} className="text-slate-300 shrink-0" />
                        <input
                            autoFocus
                            value={quickAddTitle}
                            onChange={e => setQuickAddTitle(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && quickAddTitle.trim()) handleQuickAdd(quickAddGroup, quickAddTitle.trim());
                                if (e.key === 'Escape') { setQuickAddGroup(null); setQuickAddTitle(''); }
                            }}
                            placeholder="Nombre de la tarea... (Enter para crear)"
                            className="flex-1 text-[13px] font-medium text-slate-800 dark:text-slate-200 bg-transparent outline-none placeholder:text-slate-400"
                        />
                        <button onClick={() => quickAddTitle.trim() && handleQuickAdd(quickAddGroup, quickAddTitle.trim())} className="px-3 py-1 bg-blue-600 text-white text-[11px] font-bold rounded-lg hover:bg-blue-700 transition-colors shrink-0">Crear</button>
                        <button onClick={() => { setQuickAddGroup(null); setQuickAddTitle(''); }} className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"><X size={13} /></button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Grid */}
            <div className="flex-1 min-h-0">
                {tasks.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-400">
                        <Circle size={28} className="text-slate-200 dark:text-white/10" />
                        <p className="text-sm font-medium">Sin tareas en este proyecto</p>
                        <button onClick={() => onAddTask('todo')} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors">
                            <Plus size={13} /> Crear primera tarea
                        </button>
                    </div>
                ) : (
                    <AgGridReact
                        ref={gridRef}
                        theme={isDark ? darkTheme : lightTheme}
                        rowData={rowData as any[]}
                        columnDefs={colDefs}
                        defaultColDef={{ resizable: true, sortable: false, filter: false, editable: false, suppressMovable: false }}
                        context={gridContext}
                        getRowId={getRowId}
                        getRowHeight={getRowHeight}
                        isFullWidthRow={groupBy !== 'none' ? isFullWidthRow : undefined}
                        fullWidthCellRenderer={groupBy !== 'none' ? fullWidthCellRenderer : undefined}
                        onRowClicked={(e) => { if (!e.data?.__isGroup) onOpenTask(e.data); }}
                        rowStyle={{ cursor: 'pointer' }}
                        suppressCellFocus
                        animateRows
                        enableCellTextSelection
                    />
                )}
            </div>
        </div>
    );
}

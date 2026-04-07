
"use client";

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
    Plus, Flag, Calendar, User, X, CheckCircle2, Circle,
    ChevronDown, ChevronRight, MoreHorizontal, AlertCircle,
    ArrowUp, ArrowDown, ChevronsUpDown, Check, Search, Loader2,
    ChevronLeft, Trash2, MessageSquare, Settings2, SlidersHorizontal,
    Layers, Eye, EyeOff, GripVertical, Filter,
} from 'lucide-react';
import * as Popover from '@radix-ui/react-popover';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { ProjectTaskRecord } from '@/types/projects';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

// ─── Date helpers ─────────────────────────────────────────────────────────────
const DAYS_ES   = ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa'];
const MONTHS_ES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                   'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

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

// ─── Status Config ────────────────────────────────────────────────────────────
const STATUS_OPTIONS = [
    { value:'todo',        label:'Pendiente',   dot:'bg-slate-400',   bg:'bg-slate-100 dark:bg-white/5',          text:'text-slate-600 dark:text-slate-300',    border:'border-slate-200 dark:border-white/10' },
    { value:'pending',     label:'Pendiente',   dot:'bg-slate-400',   bg:'bg-slate-100 dark:bg-white/5',          text:'text-slate-600 dark:text-slate-300',    border:'border-slate-200 dark:border-white/10' },
    { value:'in_progress', label:'En Progreso', dot:'bg-violet-500',  bg:'bg-violet-100 dark:bg-violet-500/20',   text:'text-violet-700 dark:text-violet-300',  border:'border-violet-200 dark:border-violet-500/30' },
    { value:'blocked',     label:'Bloqueado',   dot:'bg-rose-500',    bg:'bg-rose-100 dark:bg-rose-500/20',       text:'text-rose-700 dark:text-rose-300',      border:'border-rose-200 dark:border-rose-500/30' },
    { value:'done',        label:'Completado',  dot:'bg-emerald-500', bg:'bg-emerald-100 dark:bg-emerald-500/20', text:'text-emerald-700 dark:text-emerald-300', border:'border-emerald-200 dark:border-emerald-500/30' },
] as const;
type StatusValue = typeof STATUS_OPTIONS[number]['value'];
function getStatus(val: string) { return STATUS_OPTIONS.find(s => s.value === val) ?? STATUS_OPTIONS[0]; }

// ─── Priority Config ──────────────────────────────────────────────────────────
const PRIORITY_OPTIONS = [
    { value:'low',    label:'Baja',    color:'text-slate-400',  fill:'#94a3b8' },
    { value:'normal', label:'Media',   color:'text-blue-500',   fill:'#3b82f6' },
    { value:'high',   label:'Alta',    color:'text-orange-500', fill:'#f97316' },
    { value:'urgent', label:'Urgente', color:'text-rose-500',   fill:'#ef4444' },
] as const;
type PriorityValue = typeof PRIORITY_OPTIONS[number]['value'];
function getPriority(val: string) { return PRIORITY_OPTIONS.find(p => p.value === val) ?? PRIORITY_OPTIONS[1]; }

// ─── FlagIcon ─────────────────────────────────────────────────────────────────
const FlagIcon = ({ fill, size = 14 }: { fill: string; size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} xmlns="http://www.w3.org/2000/svg">
        <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
        <line x1="4" y1="22" x2="4" y2="15" stroke={fill} strokeWidth="2" strokeLinecap="round"/>
    </svg>
);

// ─── Inline Status Picker ────────────────────────────────────────────────────
function InlineStatusCell({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    const [open, setOpen] = useState(false);
    const st = getStatus(value);
    return (
        <Popover.Root open={open} onOpenChange={setOpen}>
            <Popover.Trigger asChild>
                <button
                    onClick={e => e.stopPropagation()}
                    className={clsx(
                        'flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-bold transition-all whitespace-nowrap',
                        st.bg, st.text, st.border,
                        'hover:opacity-80 hover:shadow-sm',
                        open && 'ring-2 ring-violet-500/30'
                    )}>
                    <div className={clsx('size-1.5 rounded-full shrink-0', st.dot)} />
                    {st.label}
                    <ChevronDown size={10} className="ml-0.5 opacity-60" />
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content
                    className="z-[500] min-w-[180px] bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200/80 dark:border-white/10 p-1.5"
                    sideOffset={6} align="start" onOpenAutoFocus={e => e.preventDefault()}>
                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-2 pt-1 pb-2">Estado</p>
                    {STATUS_OPTIONS.filter((s, i, a) => a.findIndex(x => x.value === s.value) === i || s.value === 'todo').map(s => (
                        s.value === 'pending' ? null :
                        <button key={s.value} onClick={() => { onChange(s.value); setOpen(false); }}
                            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                            <div className={clsx('size-2 rounded-full shrink-0', s.dot)} />
                            <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200 flex-1 text-left">{s.label}</span>
                            {s.value === value && <Check size={12} className="text-violet-500" />}
                        </button>
                    ))}
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Inline Priority Cell ─────────────────────────────────────────────────────
function InlinePriorityCell({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    const [open, setOpen] = useState(false);
    const pr = getPriority(value);
    return (
        <Popover.Root open={open} onOpenChange={setOpen}>
            <Popover.Trigger asChild>
                <button onClick={e => e.stopPropagation()}
                    className={clsx(
                        'flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-bold transition-all',
                        'hover:bg-slate-100 dark:hover:bg-white/5',
                        open && 'bg-slate-50 dark:bg-white/5 ring-1 ring-slate-200 dark:ring-white/10'
                    )}>
                    <FlagIcon fill={pr.fill} size={13} />
                    <span className={pr.color}>{pr.label}</span>
                    <ChevronDown size={10} className="text-slate-400" />
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content
                    className="z-[500] min-w-[160px] bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200/80 dark:border-white/10 p-1.5"
                    sideOffset={6} align="start" onOpenAutoFocus={e => e.preventDefault()}>
                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-2 pt-1 pb-2">Prioridad</p>
                    {PRIORITY_OPTIONS.map(p => (
                        <button key={p.value} onClick={() => { onChange(p.value); setOpen(false); }}
                            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                            <FlagIcon fill={p.fill} size={12} />
                            <span className={clsx('text-[12px] font-semibold flex-1 text-left', p.color)}>{p.label}</span>
                            {p.value === value && <Check size={12} className="text-violet-500" />}
                        </button>
                    ))}
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Inline Date Cell ─────────────────────────────────────────────────────────
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

    const selectDay = (day: number) => {
        const d = new Date(viewYear, viewMonth, day);
        onChange(d.toISOString().split('T')[0]);
        setOpen(false);
    };

    return (
        <Popover.Root open={open} onOpenChange={(v) => { setOpen(v); if(!v) return; if(parsed && !isNaN(parsed.getTime())) { setViewYear(parsed.getFullYear()); setViewMonth(parsed.getMonth()); } }}>
            <Popover.Trigger asChild>
                <button onClick={e => e.stopPropagation()}
                    className={clsx(
                        'group flex items-center gap-1.5 px-2 py-1 rounded-lg text-[12px] font-medium whitespace-nowrap transition-all',
                        'hover:bg-slate-100 dark:hover:bg-white/5',
                        open && 'bg-slate-50 dark:bg-white/5 ring-1 ring-slate-200 dark:ring-white/10',
                        isOverdue ? 'text-rose-500 dark:text-rose-400'
                            : isToday2 ? 'text-amber-500 dark:text-amber-400'
                            : label ? 'text-slate-700 dark:text-slate-300'
                            : 'text-slate-300 dark:text-white/20'
                    )}>
                    {isOverdue
                        ? <AlertCircle size={13} className="shrink-0" />
                        : <Calendar size={13} className="shrink-0" />}
                    {label ?? <span className="group-hover:text-slate-400 transition-colors">—</span>}
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content className="z-[500] w-[248px] bg-white dark:bg-[#1e1f21] rounded-2xl shadow-2xl border border-slate-200/80 dark:border-white/10 p-3 select-none"
                    sideOffset={6} align="start" onOpenAutoFocus={e => e.preventDefault()}>
                    {/* Navigator */}
                    <div className="flex items-center justify-between mb-3">
                        <button onClick={() => { let m=viewMonth-1,y=viewYear; if(m<0){m=11;y--;} setViewMonth(m);setViewYear(y); }}
                            className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-slate-700 transition-colors">
                            <ChevronLeft size={14}/>
                        </button>
                        <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">{MONTHS_ES[viewMonth]} {viewYear}</span>
                        <button onClick={() => { let m=viewMonth+1,y=viewYear; if(m>11){m=0;y++;} setViewMonth(m);setViewYear(y); }}
                            className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-slate-700 transition-colors">
                            <ChevronDown size={14}/>
                        </button>
                    </div>
                    <div className="grid grid-cols-7 mb-1">
                        {DAYS_ES.map(d => <div key={d} className="text-[9px] font-black uppercase tracking-wider text-slate-400 text-center py-0.5">{d}</div>)}
                    </div>
                    <div className="grid grid-cols-7 gap-y-0.5">
                        {cells.map((day, i) => {
                            if (!day) return <div key={`e-${i}`} />;
                            const cd = new Date(viewYear, viewMonth, day);
                            const isSel = parsed && !isNaN(parsed.getTime()) && cd.toDateString()===parsed.toDateString();
                            const isTd  = cd.toDateString()===today.toDateString();
                            const isPast = cd < today && !isTd;
                            return (
                                <button key={day} onClick={() => selectDay(day)}
                                    className={clsx(
                                        'size-8 rounded-lg text-[12px] font-medium transition-all mx-auto flex items-center justify-center',
                                        isSel  ? 'bg-violet-600 text-white font-bold shadow-sm'
                                        : isTd ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 font-bold ring-1 ring-blue-200'
                                        : isPast? 'text-slate-300 dark:text-white/20 hover:bg-slate-50'
                                               : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5'
                                    )}>
                                    {day}
                                </button>
                            );
                        })}
                    </div>
                    <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-100 dark:border-white/5">
                        <button onClick={() => selectDay(today.getDate())}
                            className="flex-1 text-[11px] font-bold text-violet-600 dark:text-violet-400 py-1.5 rounded-lg hover:bg-violet-50 dark:hover:bg-violet-500/10 transition-colors">
                            Hoy
                        </button>
                        {value && (
                            <button onClick={() => { onChange(null); setOpen(false); }}
                                className="flex-1 text-[11px] font-bold text-rose-500 py-1.5 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors">
                                Quitar
                            </button>
                        )}
                    </div>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Inline User Cell ─────────────────────────────────────────────────────────
type UserRecord = { id: number; username: string; email?: string };

function InlineUserCell({ value, token, onChange }: {
    value?: number | null;
    token: string | null;
    onChange: (userId: number | null, name: string | null) => void;
}) {
    const [open, setOpen]     = useState(false);
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
                if (value) {
                    const found = list.find(u => u.id === value);
                    if (found) setDisplayName(found.username);
                }
            })
            .catch(() => setUsers([]))
            .finally(() => setLoading(false));
    }, [open]);

    const filtered = query
        ? users.filter(u => u.username.toLowerCase().includes(query.toLowerCase()))
        : users;

    return (
        <Popover.Root open={open} onOpenChange={setOpen}>
            <Popover.Trigger asChild>
                <button onClick={e => e.stopPropagation()}
                    className={clsx(
                        'flex items-center gap-2 px-2 py-1 rounded-lg transition-all',
                        'hover:bg-slate-100 dark:hover:bg-white/5',
                        open && 'bg-slate-50 dark:bg-white/5 ring-1 ring-slate-200 dark:ring-white/10'
                    )}>
                    <div className={clsx(
                        'size-6 rounded-full flex items-center justify-center text-[10px] font-black shrink-0',
                        value ? 'bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-300'
                               : 'bg-slate-100 dark:bg-white/5 text-slate-400'
                    )}>
                        {value && displayName ? displayName.charAt(0).toUpperCase() : <User size={11} />}
                    </div>
                    <span className="text-[12px] font-medium text-slate-600 dark:text-slate-400 truncate max-w-[80px]">
                        {displayName ?? (value ? `#${value}` : '—')}
                    </span>
                </button>
            </Popover.Trigger>
            <Popover.Portal>
                <Popover.Content className="z-[500] w-[240px] bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200/80 dark:border-white/10 overflow-hidden"
                    sideOffset={6} align="start" onOpenAutoFocus={e => e.preventDefault()}>
                    <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-100 dark:border-white/5">
                        <Search size={13} className="text-slate-400 shrink-0" />
                        <input autoFocus value={query} onChange={e => setQuery(e.target.value)}
                            placeholder="Buscar usuario..."
                            className="flex-1 text-[12px] text-slate-700 dark:text-slate-200 bg-transparent outline-none placeholder:text-slate-400" />
                        {query && <button onClick={() => setQuery('')}><X size={12} className="text-slate-400" /></button>}
                    </div>
                    <div className="max-h-[200px] overflow-y-auto py-1">
                        {loading ? (
                            <div className="flex items-center justify-center py-4">
                                <Loader2 size={16} className="text-violet-500 animate-spin" />
                            </div>
                        ) : filtered.length === 0 ? (
                            <p className="text-[11px] text-slate-400 text-center py-4">Sin resultados</p>
                        ) : (
                            <>
                                {value && (
                                    <button onClick={() => { onChange(null, null); setDisplayName(null); setOpen(false); }}
                                        className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-500 transition-colors">
                                        <X size={12} />
                                        <span className="text-[11px] font-bold">Quitar asignación</span>
                                    </button>
                                )}
                                {filtered.map(u => (
                                    <button key={u.id} onClick={() => { onChange(u.id, u.username); setDisplayName(u.username); setOpen(false); }}
                                        className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                        <div className="size-6 rounded-full bg-violet-100 dark:bg-violet-500/20 flex items-center justify-center text-[10px] font-black text-violet-600 shrink-0">
                                            {u.username.charAt(0).toUpperCase()}
                                        </div>
                                        <div className="flex-1 text-left">
                                            <p className="text-[12px] font-semibold text-slate-700 dark:text-slate-200">{u.username}</p>
                                            {u.email && <p className="text-[10px] text-slate-400 truncate">{u.email}</p>}
                                        </div>
                                        {u.id === value && <Check size={12} className="text-violet-500" />}
                                    </button>
                                ))}
                            </>
                        )}
                    </div>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Quick Add Row ────────────────────────────────────────────────────────────
function QuickAddRow({ onConfirm, onCancel }: { onConfirm: (title: string) => void; onCancel: () => void }) {
    const [title, setTitle] = useState('');
    const ref = useRef<HTMLInputElement>(null);
    useEffect(() => { setTimeout(() => ref.current?.focus(), 50); }, []);
    return (
        <tr className="bg-violet-50/50 dark:bg-violet-500/5">
            <td className="w-10 px-3 py-2 border-r border-slate-100 dark:border-white/5" />
            <td className="px-4 py-2" colSpan={5}>
                <div className="flex items-center gap-3">
                    <Circle size={15} className="text-slate-300 shrink-0" />
                    <input
                        ref={ref}
                        value={title}
                        onChange={e => setTitle(e.target.value)}
                        onKeyDown={e => {
                            if (e.key === 'Enter' && title.trim()) onConfirm(title.trim());
                            if (e.key === 'Escape') onCancel();
                        }}
                        placeholder="Nombre de la tarea... (Enter para crear)"
                        className="flex-1 text-[13px] font-medium text-slate-800 dark:text-slate-200 bg-transparent outline-none placeholder:text-slate-400"
                    />
                    <button onClick={() => title.trim() && onConfirm(title.trim())}
                        className="px-3 py-1 bg-violet-600 text-white text-[11px] font-bold rounded-lg hover:bg-violet-700 transition-colors shrink-0">
                        Crear
                    </button>
                    <button onClick={onCancel}
                        className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
                        <X size={13} />
                    </button>
                </div>
            </td>
            <td className="w-10 border-l border-slate-100 dark:border-white/5" />
        </tr>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────
interface Props {
    tasks: ProjectTaskRecord[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: (status: string, dueDate?: string, title?: string) => Promise<void> | void;
    onTaskUpdated?: (taskId: number, field: string, value: any) => void;
    quickAddStatus?: string | null;
    quickAddTitle?: string;
    onQuickAddTitleChange?: (title: string) => void;
    onQuickAddConfirm?: () => void;
    onQuickAddCancel?: () => void;
}

type SortKey = 'title' | 'status' | 'priority' | 'due_date';
type SortDir = 'asc' | 'desc';
type GroupKey = 'status' | 'priority' | 'none';

const STATUS_ORDER: Record<string, number> = {
    urgent:0, in_progress:1, todo:2, pending:2, blocked:3, done:4
};
const PRIORITY_ORDER: Record<string, number> = { urgent:0, high:1, normal:2, low:3 };

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

export default function TaskTableView({ tasks, onOpenTask, onAddTask, onTaskUpdated }: Props) {
    const { token } = useAuth();
    const { openLayer } = useSidebarLayers();

    // ─ Optimistic overrides
    const [overrides, setOverrides] = useState<Record<number, Partial<ProjectTaskRecord>>>({});
    const [selected, setSelected]   = useState<Set<number>>(new Set());
    const [sortKey, setSortKey]      = useState<SortKey | null>(null);
    const [sortDir, setSortDir]      = useState<SortDir>('asc');
    const [groupBy, setGroupBy]      = useState<GroupKey>('status');
    const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
    const [quickAddGroup, setQuickAddGroup] = useState<string | null>(null);
    const [quickAddLoading, setQuickAddLoading] = useState(false);
    const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>([]);
    const [visibleCols, setVisibleCols]     = useState<Set<ColumnId>>(new Set<ColumnId>(['title','status','priority','assignee','due_date','comments']));
    // Toolbar popover states
    const [cfgOpen,    setCfgOpen]    = useState(false);
    const [filterOpen, setFilterOpen] = useState(false);
    const [sortOpen,   setSortOpen]   = useState(false);
    const [groupOpen,  setGroupOpen]  = useState(false);

    const resolveTask = (t: ProjectTaskRecord): ProjectTaskRecord => ({
        ...t,
        ...(overrides[Number(t.id)] ?? {}),
    });

    // ─ Sort toggle
    const handleSortToggle = (key: SortKey) => {
        if (sortKey === key) {
            if (sortDir === 'asc') setSortDir('desc');
            else { setSortKey(null); setSortDir('asc'); }
        } else {
            setSortKey(key);
            setSortDir('asc');
        }
    };

    const SortIcon = ({ k }: { k: SortKey }) => {
        if (sortKey !== k) return <ChevronsUpDown size={12} className="text-slate-300" />;
        return sortDir === 'asc' ? <ArrowUp size={12} className="text-violet-500" /> : <ArrowDown size={12} className="text-violet-500" />;
    };

    // ─ Process: filter + sort
    const processed = useMemo(() => {
        let list = tasks.map(resolveTask);
        // Apply active filters
        for (const f of activeFilters) {
            list = list.filter(t => {
                if (f.field === 'status')   return t.status   === f.value;
                if (f.field === 'priority') return t.priority === f.value;
                return true;
            });
        }
        if (sortKey) {
            list = [...list].sort((a, b) => {
                let cmp = 0;
                if (sortKey === 'title')   cmp = (a.title ?? '').localeCompare(b.title ?? '');
                if (sortKey === 'status')  cmp = (STATUS_ORDER[a.status ?? ''] ?? 99) - (STATUS_ORDER[b.status ?? ''] ?? 99);
                if (sortKey === 'priority') cmp = (PRIORITY_ORDER[a.priority ?? ''] ?? 99) - (PRIORITY_ORDER[b.priority ?? ''] ?? 99);
                if (sortKey === 'due_date') {
                    const da = a.due_date ? new Date(a.due_date).getTime() : Infinity;
                    const db = b.due_date ? new Date(b.due_date).getTime() : Infinity;
                    cmp = da - db;
                }
                return sortDir === 'asc' ? cmp : -cmp;
            });
        }
        return list;
    }, [tasks, overrides, sortKey, sortDir, activeFilters])

    const groups = useMemo(() => {
        const grouped: Record<string, ProjectTaskRecord[]> = {};
        processed.forEach(t => {
            let key: string;
            if (groupBy === 'none')     key = 'all';
            else if (groupBy === 'priority') key = t.priority ?? 'normal';
            else key = t.status ?? 'todo';
            if (!grouped[key]) grouped[key] = [];
            grouped[key].push(t);
        });
        return grouped;
    }, [processed, groupBy]);

    // ─ Optimistic update helper
    const applyChange = useCallback(async (taskId: number, field: string, value: any) => {
        setOverrides(prev => ({ ...prev, [taskId]: { ...prev[taskId], [field]: value } }));
        try {
            await apiFetch(`/projects/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify({ [field]: value }), token: token ?? undefined });
            onTaskUpdated?.(taskId, field, value);
        } catch {
            setOverrides(prev => {
                const next = { ...prev };
                delete next[taskId];
                return next;
            });
        }
    }, [token, onTaskUpdated]);

    // ─ Quick add
    const handleQuickAdd = async (status: string, title: string) => {
        setQuickAddLoading(true);
        try {
            await apiFetch('/projects/tasks/', {
                method: 'POST',
                body: JSON.stringify({ title, status, priority: 'normal' }),
                token: token ?? undefined
            });
            onAddTask(status);
        } catch { /* silently fail */ }
        finally { setQuickAddLoading(false); setQuickAddGroup(null); }
    };

    // ─ Select all in group
    const toggleGroupSelect = (ids: number[]) => {
        setSelected(prev => {
            const allSelected = ids.every(id => prev.has(id));
            const next = new Set(prev);
            if (allSelected) ids.forEach(id => next.delete(id));
            else ids.forEach(id => next.add(id));
            return next;
        });
    };

    const ColHeader = ({ label, k, width }: { label: string; k: SortKey; width: string }) => (
        <th style={{ width }} className="px-4 py-2.5 text-left border-r border-slate-100 dark:border-white/5 last:border-r-0">
            <button onClick={() => handleSortToggle(k)}
                className="flex items-center gap-1.5 group/th">
                <span className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 group-hover/th:text-slate-700 dark:group-hover/th:text-slate-200 transition-colors">
                    {label}
                </span>
                <SortIcon k={k} />
            </button>
        </th>
    );

    const totalSelected = selected.size;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] font-sans overflow-hidden">

            {/* ── TOOLBAR ──────────────────────────────────────────────────── */}
            <div className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 border-b border-slate-100 dark:border-white/[0.06] bg-slate-50/60 dark:bg-black/10">

                {/* ── Config: column visibility ── */}
                <Popover.Root open={cfgOpen} onOpenChange={setCfgOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx(
                            'flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all',
                            cfgOpen ? 'bg-violet-50 dark:bg-violet-500/10 text-violet-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5'
                        )}>
                            <Settings2 size={12} /> Config
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start"
                            className="z-[500] w-56 bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200/80 dark:border-white/10 p-2">
                            <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-2 py-1.5">Columnas visibles</p>
                            {ALL_COLUMNS.map(col => (
                                <button key={col.id}
                                    onClick={() => setVisibleCols(prev => {
                                        const next = new Set(prev);
                                        if (next.has(col.id)) { if (col.id !== 'title') next.delete(col.id); }
                                        else next.add(col.id);
                                        return next;
                                    })}
                                    className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                    {visibleCols.has(col.id)
                                        ? <Eye size={13} className="text-violet-500 shrink-0" />
                                        : <EyeOff size={13} className="text-slate-300 shrink-0" />}
                                    <span className={clsx('text-[12px] font-medium flex-1 text-left', visibleCols.has(col.id) ? 'text-slate-700 dark:text-slate-200' : 'text-slate-400')}>{col.label}</span>
                                    {col.id === 'title' && <span className="text-[9px] text-slate-300">fijo</span>}
                                </button>
                            ))}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                <div className="w-px h-4 bg-slate-200 dark:bg-white/10" />

                {/* ── Group by ── */}
                <Popover.Root open={groupOpen} onOpenChange={setGroupOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx(
                            'flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all',
                            groupBy !== 'status' ? 'bg-violet-50 dark:bg-violet-500/10 text-violet-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5'
                        )}>
                            <Layers size={12} />
                            Agrupar{groupBy !== 'none' ? `: ${groupBy === 'status' ? 'Estado' : 'Prioridad'}` : ''}
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start"
                            className="z-[500] w-52 bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200/80 dark:border-white/10 p-1.5">
                            <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-2 pt-1 pb-2">Agrupar por</p>
                            {([['status','Estado'],['priority','Prioridad'],['none','Sin agrupación']] as const).map(([k, lbl]) => (
                                <button key={k} onClick={() => { setGroupBy(k); setGroupOpen(false); }}
                                    className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                    <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200 flex-1 text-left">{lbl}</span>
                                    {groupBy === k && <Check size={12} className="text-violet-500" />}
                                </button>
                            ))}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                {/* ── Filter ── */}
                <Popover.Root open={filterOpen} onOpenChange={setFilterOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx(
                            'flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all',
                            activeFilters.length > 0 ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5'
                        )}>
                            <Filter size={12} />
                            Filtrar{activeFilters.length > 0 ? ` (${activeFilters.length})` : ''}
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start"
                            className="z-[500] w-64 bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200/80 dark:border-white/10 p-2">
                            <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-2 py-1.5">Filtrar por Estado</p>
                            <div className="flex flex-wrap gap-1.5 px-2 pb-2">
                                {STATUS_OPTIONS.filter((s,i,a) => a.findIndex(x => x.value === s.value) === i && s.value !== 'pending').map(s => {
                                    const active = activeFilters.some(f => f.field === 'status' && f.value === s.value);
                                    return (
                                        <button key={s.value}
                                            onClick={() => setActiveFilters(prev => active
                                                ? prev.filter(f => !(f.field==='status' && f.value===s.value))
                                                : [...prev, { field: 'status', value: s.value, label: s.label }]
                                            )}
                                            className={clsx('flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border transition-all',
                                                active ? `${s.bg} ${s.text} ${s.border} ring-2 ring-violet-500/30` : `${s.bg} ${s.text} ${s.border} opacity-60 hover:opacity-100`)}>
                                            <div className={clsx('size-1.5 rounded-full', s.dot)} />{s.label}
                                        </button>
                                    );
                                })}
                            </div>
                            <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-2 py-1.5 border-t border-slate-100 dark:border-white/5">Filtrar por Prioridad</p>
                            <div className="flex flex-wrap gap-1.5 px-2 pb-2">
                                {PRIORITY_OPTIONS.map(p => {
                                    const active = activeFilters.some(f => f.field === 'priority' && f.value === p.value);
                                    return (
                                        <button key={p.value}
                                            onClick={() => setActiveFilters(prev => active
                                                ? prev.filter(f => !(f.field==='priority' && f.value===p.value))
                                                : [...prev, { field: 'priority', value: p.value, label: p.label }]
                                            )}
                                            className={clsx('flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border transition-all',
                                                active ? 'bg-slate-100 dark:bg-white/10 border-slate-300 ring-2 ring-violet-500/30' : 'bg-slate-50 dark:bg-white/5 border-slate-200 dark:border-white/10 opacity-60 hover:opacity-100',
                                                p.color)}>
                                            <FlagIcon fill={p.fill} size={11} />{p.label}
                                        </button>
                                    );
                                })}
                            </div>
                            {activeFilters.length > 0 && (
                                <button onClick={() => setActiveFilters([])}
                                    className="w-full text-[11px] font-bold text-rose-500 py-1.5 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors border-t border-slate-100 dark:border-white/5 mt-1">
                                    Limpiar filtros
                                </button>
                            )}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                {/* ── Sort ── */}
                <Popover.Root open={sortOpen} onOpenChange={setSortOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx(
                            'flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all',
                            sortKey ? 'bg-amber-50 dark:bg-amber-500/10 text-amber-600' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5'
                        )}>
                            <SlidersHorizontal size={12} />
                            Ordenar{sortKey ? `: ${sortKey === 'due_date' ? 'Fecha' : sortKey === 'title' ? 'Nombre' : sortKey === 'status' ? 'Estado' : 'Prioridad'} ${sortDir === 'asc' ? '↑' : '↓'}` : ''}
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start"
                            className="z-[500] w-56 bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200/80 dark:border-white/10 p-2">
                            <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-2 py-1.5">Columna</p>
                            {([['title','Nombre'],['status','Estado'],['priority','Prioridad'],['due_date','Fecha límite']] as [SortKey, string][]).map(([k, lbl]) => (
                                <button key={k} onClick={() => handleSortToggle(k)}
                                    className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                    <span className="text-[12px] font-semibold text-slate-700 dark:text-slate-200 flex-1 text-left">{lbl}</span>
                                    {sortKey === k && (sortDir === 'asc' ? <ArrowUp size={12} className="text-violet-500" /> : <ArrowDown size={12} className="text-violet-500" />)}
                                </button>
                            ))}
                            {sortKey && (
                                <>
                                    <div className="border-t border-slate-100 dark:border-white/5 my-1" />
                                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-2 py-1.5">Dirección</p>
                                    <div className="flex gap-1.5 px-2 pb-1">
                                        {([['asc','Ascendente'],['desc','Descendente']] as const).map(([d, lbl]) => (
                                            <button key={d} onClick={() => setSortDir(d)}
                                                className={clsx('flex-1 py-1.5 rounded-lg text-[11px] font-bold transition-all',
                                                    sortDir === d ? 'bg-violet-600 text-white' : 'bg-slate-100 dark:bg-white/5 text-slate-500 hover:bg-slate-200')}>
                                                {lbl}
                                            </button>
                                        ))}
                                    </div>
                                    <button onClick={() => { setSortKey(null); setSortDir('asc'); setSortOpen(false); }}
                                        className="w-full text-[11px] font-bold text-rose-500 py-1.5 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors mt-1">
                                        Quitar ordenación
                                    </button>
                                </>
                            )}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                {/* Active filter chips */}
                {activeFilters.length > 0 && (
                    <div className="flex items-center gap-1 ml-1 flex-wrap">
                        {activeFilters.map((f, i) => (
                            <span key={i} className="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/30 rounded-full text-[11px] font-semibold text-blue-600 dark:text-blue-400">
                                {f.label}
                                <button onClick={() => setActiveFilters(prev => prev.filter((_, j) => j !== i))}
                                    className="size-4 flex items-center justify-center hover:bg-blue-100 dark:hover:bg-blue-500/20 rounded-full transition-colors">
                                    <X size={9} />
                                </button>
                            </span>
                        ))}
                        <button onClick={() => setActiveFilters([])}
                            className="text-[10px] font-bold text-slate-400 hover:text-rose-500 transition-colors ml-0.5">
                            Limpiar
                        </button>
                    </div>
                )}

                <div className="ml-auto flex items-center gap-1.5">
                    <span className="text-[10px] font-bold text-slate-400">
                        {processed.length} fila{processed.length !== 1 ? 's' : ''}
                    </span>
                </div>
            </div>

            {/* ── Bulk action bar ── */}
            <AnimatePresence>
                {totalSelected > 0 && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="flex items-center gap-3 px-4 py-2 bg-violet-600 text-white overflow-hidden">
                        <span className="text-[12px] font-bold">{totalSelected} seleccionada{totalSelected > 1 ? 's' : ''}</span>
                        <div className="flex items-center gap-1 ml-2">
                            <button className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-[11px] font-bold transition-colors">
                                <Trash2 size={12} /> Eliminar
                            </button>
                            <button className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-[11px] font-bold transition-colors">
                                <Flag size={12} /> Prioridad
                            </button>
                        </div>
                        <button onClick={() => setSelected(new Set())} className="ml-auto p-1 hover:bg-white/10 rounded transition-colors">
                            <X size={14} />
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── TABLE ── */}
            <div className="flex-1 overflow-auto">
                <table className="w-full border-collapse table-fixed min-w-[780px]">
                    {/* HEADER */}
                    <thead className="sticky top-0 z-20 bg-slate-50 dark:bg-[#18191b] border-b border-slate-200 dark:border-white/[0.06]">
                        <tr>
                            <th className="w-10 px-3 py-2.5 border-r border-slate-100 dark:border-white/5">
                                <div className="size-4 rounded border-2 border-slate-300 dark:border-white/20 cursor-pointer
                                    flex items-center justify-center hover:border-violet-500 transition-colors"
                                    onClick={() => {
                                        const allIds = processed.map(t => Number(t.id));
                                        const allSelected = allIds.every(id => selected.has(id));
                                        setSelected(allSelected ? new Set() : new Set(allIds));
                                    }}>
                                    {selected.size > 0 && selected.size === processed.length &&
                                        <Check size={10} className="text-violet-600" />}
                                </div>
                            </th>
                            <th className="px-4 py-2.5 text-left border-r border-slate-100 dark:border-white/5" style={{ width: '380px' }}>
                                <button onClick={() => handleSortToggle('title')}
                                    className="flex items-center gap-1.5 group/th">
                                    <span className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 group-hover/th:text-slate-700 dark:group-hover/th:text-slate-200 transition-colors">
                                        Nombre de la tarea
                                    </span>
                                    <SortIcon k="title" />
                                </button>
                            </th>
                            {visibleCols.has('status')   && <ColHeader label="Estado"       k="status"   width="160px" />}
                            {visibleCols.has('priority') && <ColHeader label="Prioridad"    k="priority" width="140px" />}
                            {visibleCols.has('assignee') && (
                                <th className="px-4 py-2.5 text-left border-r border-slate-100 dark:border-white/5" style={{ width: '160px' }}>
                                    <span className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">Asignado</span>
                                </th>
                            )}
                            {visibleCols.has('due_date') && <ColHeader label="Fecha límite" k="due_date" width="150px" />}
                            {visibleCols.has('comments') && (
                                <th className="w-10 px-3 py-2.5 text-left">
                                    <MessageSquare size={13} className="text-slate-300" />
                                </th>
                            )}
                        </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-100 dark:divide-white/[0.03]">
                        {Object.entries(groups).map(([groupName, groupTasks]) => {
                            // ── Dynamic group header depending on groupBy ──
                            const st = groupBy === 'priority'
                                ? (() => {
                                    const p = PRIORITY_OPTIONS.find(p => p.value === groupName);
                                    return p
                                        ? { label: p.label, bg: 'bg-slate-100 dark:bg-white/5', text: p.color, border: 'border-slate-200 dark:border-white/10', dot: 'bg-slate-400' }
                                        : getStatus(groupName);
                                })()
                                : getStatus(groupName);
                            const isCollapsed = collapsedGroups[groupName];
                            const groupIds = groupTasks.map(t => Number(t.id));
                            const allGroupSelected = groupIds.length > 0 && groupIds.every(id => selected.has(id));


                            return (
                                <React.Fragment key={groupName}>
                                    {/* Group header */}
                                    <tr className="bg-slate-50/80 dark:bg-white/[0.01] sticky top-[41px] z-10">
                                        <td colSpan={7} className="px-3 py-1.5">
                                            <div className="flex items-center gap-2">
                                                {/* Group checkbox */}
                                                <div className={clsx(
                                                    'size-4 rounded border-2 flex items-center justify-center cursor-pointer transition-colors',
                                                    allGroupSelected ? 'bg-violet-500 border-violet-500' : 'border-slate-300 dark:border-white/20 hover:border-violet-500'
                                                )} onClick={() => toggleGroupSelect(groupIds)}>
                                                    {allGroupSelected && <Check size={10} className="text-white" />}
                                                </div>
                                                {/* Collapse toggle */}
                                                <button onClick={() => setCollapsedGroups(prev => ({ ...prev, [groupName]: !prev[groupName] }))}
                                                    className="flex items-center gap-2 px-2 py-1 hover:bg-slate-100/70 dark:hover:bg-white/5 rounded-lg transition-all">
                                                    <motion.div animate={{ rotate: isCollapsed ? -90 : 0 }} transition={{ duration: 0.15 }}>
                                                        <ChevronDown size={13} className="text-slate-400" />
                                                    </motion.div>
                                                    <span className={clsx(
                                                        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-[11px] font-bold',
                                                        st.bg, st.text, st.border
                                                    )}>
                                                        <div className={clsx('size-1.5 rounded-full', st.dot)} />
                                                        {st.label}
                                                    </span>
                                                    <span className="text-[10px] font-bold text-slate-400 bg-slate-200/70 dark:bg-white/10 px-1.5 rounded-md">
                                                        {groupTasks.length}
                                                    </span>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>

                                    {/* Rows */}
                                    <AnimatePresence initial={false}>
                                        {!isCollapsed && groupTasks.map((task, idx) => {
                                            const t    = resolveTask(task);
                                            const isChecked = selected.has(Number(t.id));
                                            return (
                                                <motion.tr key={t.id}
                                                    initial={{ opacity: 0 }}
                                                    animate={{ opacity: 1 }}
                                                    exit={{ opacity: 0, height: 0 }}
                                                    transition={{ duration: 0.1, delay: idx * 0.01 }}
                                                    className={clsx(
                                                        'group hover:bg-blue-50/40 dark:hover:bg-white/[0.02] transition-colors cursor-pointer',
                                                        isChecked && 'bg-violet-50/40 dark:bg-violet-500/5'
                                                    )}
                                                    onClick={() => onOpenTask(t)}>

                                                    {/* Checkbox */}
                                                    <td className="w-10 px-3 py-2.5 border-r border-slate-100 dark:border-white/5" onClick={e => e.stopPropagation()}>
                                                        <div className={clsx(
                                                            'size-4 rounded border-2 flex items-center justify-center cursor-pointer transition-all',
                                                            isChecked ? 'bg-violet-500 border-violet-500' : 'border-slate-200 dark:border-white/10 hover:border-violet-400 opacity-0 group-hover:opacity-100'
                                                        )} onClick={() => setSelected(prev => {
                                                            const next = new Set(prev);
                                                            if (next.has(Number(t.id))) next.delete(Number(t.id)); else next.add(Number(t.id));
                                                            return next;
                                                        })}>
                                                            {isChecked && <Check size={10} className="text-white" />}
                                                        </div>
                                                    </td>

                                                    {/* Title */}
                                                    <td className="px-4 py-2.5 border-r border-slate-100 dark:border-white/5 overflow-hidden" style={{ width: '380px' }}>
                                                        <div className="flex items-center gap-2.5">
                                                            <div onClick={e => { e.stopPropagation(); applyChange(Number(t.id), 'status', t.status === 'done' ? 'todo' : 'done'); }}>
                                                                {t.status === 'done'
                                                                    ? <CheckCircle2 size={15} className="text-emerald-500 shrink-0 hover:text-emerald-400 transition-colors" />
                                                                    : <Circle size={15} className="text-slate-300 dark:text-white/20 shrink-0 group-hover:text-violet-400 transition-colors" />}
                                                            </div>
                                                            <span className={clsx(
                                                                'text-[13px] font-medium truncate',
                                                                t.status === 'done'
                                                                    ? 'text-slate-400 line-through'
                                                                    : 'text-slate-800 dark:text-slate-200 group-hover:text-violet-600 dark:group-hover:text-violet-400'
                                                            )}>
                                                                {t.title}
                                                            </span>
                                                        </div>
                                                    </td>

                                                    {/* Status */}
                                                    {visibleCols.has('status') && (
                                                        <td className="px-4 py-2 border-r border-slate-100 dark:border-white/5" style={{ width: '160px' }} onClick={e => e.stopPropagation()}>
                                                            <InlineStatusCell value={t.status ?? 'todo'} onChange={v => applyChange(Number(t.id), 'status', v)} />
                                                        </td>
                                                    )}

                                                    {/* Priority */}
                                                    {visibleCols.has('priority') && (
                                                        <td className="px-4 py-2 border-r border-slate-100 dark:border-white/5" style={{ width: '140px' }} onClick={e => e.stopPropagation()}>
                                                            <InlinePriorityCell value={t.priority ?? 'normal'} onChange={v => applyChange(Number(t.id), 'priority', v)} />
                                                        </td>
                                                    )}

                                                    {/* Assignee */}
                                                    {visibleCols.has('assignee') && (
                                                        <td className="px-4 py-2 border-r border-slate-100 dark:border-white/5" style={{ width: '160px' }} onClick={e => e.stopPropagation()}>
                                                            <InlineUserCell
                                                                value={t.assignee_id}
                                                                token={token}
                                                                onChange={(userId) => applyChange(Number(t.id), 'assignee_id', userId)}
                                                            />
                                                        </td>
                                                    )}

                                                    {/* Due date */}
                                                    {visibleCols.has('due_date') && (
                                                        <td className="px-4 py-2 border-r border-slate-100 dark:border-white/5" style={{ width: '150px' }} onClick={e => e.stopPropagation()}>
                                                            <InlineDateCell
                                                                value={t.due_date}
                                                                onChange={v => applyChange(Number(t.id), 'due_date', v)}
                                                            />
                                                        </td>
                                                    )}

                                                    {/* Comments */}
                                                    {visibleCols.has('comments') && (
                                                        <td className="w-10 px-3 py-2.5" onClick={e => e.stopPropagation()}>
                                                            <button onClick={() => openLayer('RIGHT')}
                                                                className="p-1.5 rounded-lg text-slate-300 hover:text-violet-500 hover:bg-violet-50 dark:hover:bg-violet-500/10 transition-all opacity-0 group-hover:opacity-100">
                                                                <MessageSquare size={13} />
                                                            </button>
                                                        </td>
                                                    )}
                                                </motion.tr>
                                            );
                                        })}
                                    </AnimatePresence>

                                    {/* Quick-add row */}
                                    <AnimatePresence>
                                        {quickAddGroup === groupName && (
                                            <QuickAddRow
                                                onConfirm={(title) => handleQuickAdd(groupName, title)}
                                                onCancel={() => setQuickAddGroup(null)}
                                            />
                                        )}
                                    </AnimatePresence>

                                    {/* Add row per group */}
                                    {!isCollapsed && (
                                        <tr className="group/add">
                                            <td colSpan={7} className="px-6 py-0.5">
                                                <button onClick={() => setQuickAddGroup(groupName)}
                                                    className="flex items-center gap-1.5 text-[11px] font-bold text-slate-300 hover:text-violet-600 dark:text-white/10 dark:hover:text-violet-400 py-1.5 transition-all opacity-0 group-hover/add:opacity-100">
                                                    <Plus size={12} />
                                                    Agregar tarea
                                                </button>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            );
                        })}

                        {/* Empty state */}
                        {processed.length === 0 && (
                            <tr>
                                <td colSpan={7} className="py-20 text-center">
                                    <div className="flex flex-col items-center gap-3">
                                        <div className="size-14 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center">
                                            <CheckCircle2 size={24} className="text-slate-200" />
                                        </div>
                                        <p className="text-slate-400 text-sm font-medium">Sin tareas en este proyecto</p>
                                        <button onClick={() => onAddTask('todo')}
                                            className="text-[12px] font-bold text-violet-500 hover:underline">
                                            Crear la primera tarea
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* ── Footer ── */}
            <footer className="px-4 py-2 border-t border-slate-100 dark:border-white/[0.04] flex items-center justify-between bg-slate-50/50 dark:bg-black/10">
                <div className="flex items-center gap-3">
                    <button onClick={() => setQuickAddGroup('todo')}
                        className="flex items-center gap-1.5 text-[12px] font-bold text-slate-400 hover:text-violet-600 transition-colors">
                        <Plus size={13} /> Agregar tarea
                        <span className="ml-1 text-slate-300 font-normal text-[10px]">Shift+Enter</span>
                    </button>
                </div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                    {processed.length} tarea{processed.length !== 1 ? 's' : ''}
                    {sortKey && ` · ord. por ${sortKey}`}
                </span>
            </footer>
        </div>
    );
}

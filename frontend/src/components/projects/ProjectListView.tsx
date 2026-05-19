"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
    ChevronDown, ChevronRight, Plus, Calendar,
    MessageSquare, MoreHorizontal, CheckCircle2, X, Send,
    Paperclip, AtSign, Smile, User, Check, Search, Loader2,
    AlertCircle, ChevronLeft,
} from 'lucide-react';
import * as Popover from '@radix-ui/react-popover';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { ProjectTaskRecord } from '@/types/projects';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

// ─── Tiny date helpers ────────────────────────────────────────────────────────
const DAYS_ES = ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa'];
const MONTHS_ES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

function getDaysInMonth(year: number, month: number) {
    return new Date(year, month + 1, 0).getDate();
}
function getFirstDayOfMonth(year: number, month: number) {
    return new Date(year, month, 1).getDay();
}
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
    { value: 'todo',        label: 'Pendiente',   dot: 'bg-slate-400',   bg: 'bg-slate-100 dark:bg-white/5',           text: 'text-slate-600 dark:text-slate-300',    border: 'border-slate-200 dark:border-white/10' },
    { value: 'pending',     label: 'Pendiente',   dot: 'bg-slate-400',   bg: 'bg-slate-100 dark:bg-white/5',           text: 'text-slate-600 dark:text-slate-300',    border: 'border-slate-200 dark:border-white/10' },
    { value: 'in_progress', label: 'En Progreso', dot: 'bg-blue-500',  bg: 'bg-blue-100 dark:bg-blue-500/20',    text: 'text-blue-700 dark:text-blue-300',  border: 'border-blue-200 dark:border-blue-500/30' },
    { value: 'blocked',     label: 'Bloqueado',   dot: 'bg-rose-500',    bg: 'bg-rose-100 dark:bg-rose-500/20',        text: 'text-rose-700 dark:text-rose-300',      border: 'border-rose-200 dark:border-rose-500/30' },
    { value: 'done',        label: 'Completado',  dot: 'bg-emerald-500', bg: 'bg-emerald-100 dark:bg-emerald-500/20',  text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200 dark:border-emerald-500/30' },
] as const;
function getStatus(val: string) {
    return STATUS_OPTIONS.find(s => s.value === val) ?? STATUS_OPTIONS[0];
}

// ─── Priority Config ──────────────────────────────────────────────────────────
const PRIORITY_OPTIONS = [
    { value: 'low',    label: 'Baja',    color: 'text-slate-400',   fill: '#94a3b8' },
    { value: 'normal', label: 'Media',   color: 'text-blue-500',    fill: '#3b82f6' },
    { value: 'high',   label: 'Alta',    color: 'text-orange-500',  fill: '#f97316' },
    { value: 'urgent', label: 'Urgente', color: 'text-rose-500',    fill: '#ef4444' },
] as const;
function getPriority(val: string) {
    return PRIORITY_OPTIONS.find(p => p.value === val) ?? PRIORITY_OPTIONS[1];
}

// ─── Group header pill styles ─────────────────────────────────────────────────
const GROUP_PILL: Record<string, string> = {
    in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
    pending:     'bg-slate-200 text-slate-600 dark:bg-white/10 dark:text-slate-300',
    todo:        'bg-slate-200 text-slate-600 dark:bg-white/10 dark:text-slate-300',
    done:        'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    blocked:     'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
};

// ─── TYPE DEFINITIONS ─────────────────────────────────────────────────────────
interface TaskUser {
    id: number;
    username: string;
    email: string;
}

interface LocalTask extends ProjectTaskRecord {
    _assignedUser?: TaskUser | null;
    _priority?: string;
    _status?: string;
    _due_date?: string | null;
}

interface Props {
    tasks: ProjectTaskRecord[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: (status: string) => void;
    onTasksChange?: (tasks: ProjectTaskRecord[]) => void;
    quickAddStatus?: string | null;
    quickAddTitle?: string;
    onQuickAddTitleChange?: (v: string) => void;
    onQuickAddConfirm?: () => void;
    onQuickAddCancel?: () => void;
}

// ─── Inline User Picker ───────────────────────────────────────────────────────
function InlineUserPicker({
    currentUser,
    onSelect,
}: {
    currentUser?: TaskUser | null;
    onSelect: (user: TaskUser) => void;
}) {
    const { token } = useAuth();
    const [open, setOpen] = useState(false);
    const [users, setUsers] = useState<TaskUser[]>([]);
    const [loading, setLoading] = useState(false);
    const [search, setSearch] = useState('');

    const fetchUsers = async () => {
        if (!token || users.length > 0) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/admin/members/', { token });
            if (Array.isArray(data)) {
                setUsers(data.map((u: any) => ({
                    id: u.id,
                    username: `${u.first_name} ${u.last_name}`.trim() || u.username,
                    email: u.email,
                })));
            }
        } catch { /* silencioso */ }
        finally { setLoading(false); }
    };

    const filtered = search
        ? users.filter(u => u.username.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()))
        : users;

    const initials = currentUser?.username?.slice(0, 2).toUpperCase() || '';

    return (
        <Popover.Root open={open} onOpenChange={(v) => { setOpen(v); if (v) fetchUsers(); }}>
            <Popover.Trigger asChild>
                <button
                    className={clsx(
                        'group flex items-center justify-center min-w-[40px] min-h-[40px] rounded-lg transition-all',
                        'hover:bg-slate-100 dark:hover:bg-white/5',
                        open && 'bg-blue-50 dark:bg-blue-500/10 ring-1 ring-blue-300 dark:ring-blue-500/40'
                    )}
                    title={currentUser ? `Asignado a ${currentUser.username}` : 'Asignar persona'}
                    aria-label="Selector de persona asignada"
                >
                    {currentUser ? (
                        <div className="size-6 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-[9px] font-black text-white shrink-0 shadow-sm">
                            {initials}
                        </div>
                    ) : (
                        <div className="size-6 rounded-full bg-slate-200 dark:bg-white/10 flex items-center justify-center text-slate-400 group-hover:bg-blue-100 dark:group-hover:bg-blue-500/20 group-hover:text-blue-500 transition-colors">
                            <User size={12} />
                        </div>
                    )}
                </button>
            </Popover.Trigger>

            <Popover.Portal>
                <Popover.Content
                    className="z-[500] w-64 bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200 dark:border-white/10 overflow-hidden"
                    sideOffset={6}
                    align="start"
                    onOpenAutoFocus={e => e.preventDefault()}
                >
                    {/* Search */}
                    <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-100 dark:border-white/5">
                        <Search size={13} className="text-slate-400 shrink-0" />
                        <input
                            autoFocus
                            type="text"
                            placeholder="Buscar usuario..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="flex-1 text-[12px] bg-transparent outline-none text-slate-700 dark:text-slate-300 placeholder:text-slate-400"
                        />
                    </div>

                    {/* List */}
                    <div className="max-h-52 overflow-y-auto p-1 scrollbar-thin">
                        {loading ? (
                            <div className="flex items-center justify-center py-6">
                                <Loader2 size={16} className="animate-spin text-blue-500" />
                            </div>
                        ) : filtered.length === 0 ? (
                            <p className="text-center text-[11px] text-slate-400 py-4">
                                {search ? 'Sin resultados' : 'No hay usuarios disponibles'}
                            </p>
                        ) : filtered.map(user => (
                            <button
                                key={user.id}
                                onClick={() => { onSelect(user); setOpen(false); setSearch(''); }}
                                className={clsx(
                                    'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[12px] font-medium transition-colors text-left',
                                    currentUser?.id === user.id
                                        ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300'
                                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5'
                                )}
                            >
                                <div className="size-6 rounded-full bg-gradient-to-br from-slate-400 to-slate-600 flex items-center justify-center text-[9px] font-black text-white shrink-0">
                                    {user.username.slice(0, 2).toUpperCase()}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="truncate font-semibold">{user.username}</p>
                                    <p className="truncate text-[10px] text-slate-400">{user.email}</p>
                                </div>
                                {currentUser?.id === user.id && <Check size={13} className="text-blue-500 shrink-0" />}
                            </button>
                        ))}
                    </div>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Mini Calendar Date Picker ────────────────────────────────────────────────
function InlineDatePicker({
    currentDate,
    onSelect,
}: {
    currentDate?: string | null;
    onSelect: (date: string | null) => void;
}) {
    const [open, setOpen] = useState(false);
    const today = new Date(); today.setHours(0,0,0,0);
    const parsed = currentDate ? new Date(currentDate + 'T00:00:00') : null;
    const [viewYear, setViewYear] = useState((parsed ?? today).getFullYear());
    const [viewMonth, setViewMonth] = useState((parsed ?? today).getMonth());

    const isOverdue = parsed && parsed < today;
    const isToday2 = parsed && parsed.toDateString() === today.toDateString();
    const label = parsed ? formatRelative(parsed) : null;

    const daysInMonth = getDaysInMonth(viewYear, viewMonth);
    const rawFirstDay = getFirstDayOfMonth(viewYear, viewMonth);
    const firstDay = isNaN(rawFirstDay) ? 0 : Math.max(0, Math.min(6, rawFirstDay));
    const cells: (number | null)[] = [
        ...Array(firstDay).fill(null),
        ...Array.from({length: Math.max(0, daysInMonth)}, (_, i) => i + 1)
    ];

    const selectDay = (day: number) => {
        const d = new Date(viewYear, viewMonth, day);
        const iso = d.toLocaleDateString('en-CA');
        onSelect(iso);
        setOpen(false);
    };

    return (
        <Popover.Root open={open} onOpenChange={(v) => { setOpen(v); if (!v) return; if (parsed) { setViewYear(parsed.getFullYear()); setViewMonth(parsed.getMonth()); }}}>
            <Popover.Trigger asChild>
                <button
                    className={clsx(
                        'group flex items-center gap-1.5 px-2 min-h-[40px] rounded-lg transition-all text-[12px] font-medium whitespace-nowrap',
                        'hover:bg-slate-100 dark:hover:bg-white/5',
                        open && 'bg-slate-50 dark:bg-white/5 ring-1 ring-slate-200 dark:ring-white/10',
                        isOverdue ? 'text-rose-500 dark:text-rose-400'
                            : isToday2 ? 'text-amber-500 dark:text-amber-400'
                            : parsed ? 'text-slate-700 dark:text-slate-300'
                            : 'text-slate-300 dark:text-white/20'
                    )}
                    aria-label="Seleccionar fecha límite"
                >
                    {isOverdue
                        ? <AlertCircle size={13} className="shrink-0" />
                        : <Calendar size={13} className={clsx('shrink-0 transition-colors', !parsed && 'group-hover:text-slate-400')} />}
                    {label && <span>{label}</span>}
                </button>
            </Popover.Trigger>

            <Popover.Portal>
                <Popover.Content
                    className="z-[500] w-[248px] bg-white dark:bg-[#1e1f21] rounded-2xl shadow-2xl border border-slate-200/80 dark:border-white/10 p-3 select-none"
                    sideOffset={6}
                    align="start"
                    onOpenAutoFocus={e => e.preventDefault()}
                >
                    {/* Month navigator */}
                    <div className="flex items-center justify-between mb-3">
                        <button onClick={() => { let m = viewMonth-1; let y = viewYear; if(m<0){m=11;y--;} setViewMonth(m); setViewYear(y); }} className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
                            <ChevronLeft size={14}/>
                        </button>
                        <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">
                            {MONTHS_ES[viewMonth]} {viewYear}
                        </span>
                        <button onClick={() => { let m = viewMonth+1; let y = viewYear; if(m>11){m=0;y++;} setViewMonth(m); setViewYear(y); }} className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
                            <ChevronDown size={14}/>
                        </button>
                    </div>

                    {/* Day names */}
                    <div className="grid grid-cols-7 mb-1">
                        {DAYS_ES.map(d => (
                            <div key={d} className="text-[9px] font-black uppercase tracking-wider text-slate-400 text-center py-0.5">{d}</div>
                        ))}
                    </div>

                    {/* Calendar grid */}
                    <div className="grid grid-cols-7 gap-y-0.5">
                        {cells.map((day, i) => {
                            if (!day) return <div key={`e-${i}`} />;
                            const cellDate = new Date(viewYear, viewMonth, day);
                            const isSelected = parsed && cellDate.toDateString() === parsed.toDateString();
                            const isTodayCell = cellDate.toDateString() === today.toDateString();
                            const isPast = cellDate < today && !isTodayCell;
                            return (
                                <button
                                    key={day}
                                    onClick={() => selectDay(day)}
                                    className={clsx(
                                        'size-8 rounded-lg text-[12px] font-medium transition-all mx-auto flex items-center justify-center',
                                        isSelected
                                            ? 'bg-blue-600 text-white font-bold shadow-sm'
                                            : isTodayCell
                                            ? 'bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold ring-1 ring-blue-200 dark:ring-blue-500/30'
                                            : isPast
                                            ? 'text-slate-300 dark:text-white/20 hover:bg-slate-50 dark:hover:bg-white/5'
                                            : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5'
                                    )}
                                >
                                    {day}
                                </button>
                            );
                        })}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-100 dark:border-white/5">
                        <button
                            onClick={() => selectDay(today.getDate())}
                            className="flex-1 text-[11px] font-bold text-blue-600 dark:text-blue-400 py-1.5 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors"
                        >
                            Hoy
                        </button>
                        {currentDate && (
                            <button
                                onClick={() => { onSelect(null); setOpen(false); }}
                                className="flex-1 text-[11px] font-bold text-rose-500 dark:text-rose-400 py-1.5 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors"
                            >
                                Quitar
                            </button>
                        )}
                    </div>
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Inline Priority Picker ───────────────────────────────────────────────────
function InlinePriorityPicker({
    currentPriority,
    onSelect,
}: {
    currentPriority: string;
    onSelect: (priority: string) => void;
}) {
    const [open, setOpen] = useState(false);
    const prio = getPriority(currentPriority);

    return (
        <Popover.Root open={open} onOpenChange={setOpen}>
            <Popover.Trigger asChild>
                <button
                    className={clsx(
                        'group flex items-center justify-center min-w-[40px] min-h-[40px] rounded-lg transition-all',
                        'hover:bg-slate-100 dark:hover:bg-white/5',
                        open && 'bg-slate-50 dark:bg-white/5 ring-1 ring-slate-200 dark:ring-white/10'
                    )}
                    title={`Prioridad: ${prio.label}`}
                    aria-label="Selector de prioridad"
                >
                    {/* Flag SVG coloreable */}
                    <svg width="14" height="14" viewBox="0 0 24 24" fill={prio.fill} stroke={prio.fill} strokeWidth="0" className="transition-all duration-150">
                        <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
                        <line x1="4" y1="22" x2="4" y2="15" stroke={prio.fill} strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                </button>
            </Popover.Trigger>

            <Popover.Portal>
                <Popover.Content
                    className="z-[500] w-44 bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200 dark:border-white/10 p-1"
                    sideOffset={6}
                    align="start"
                >
                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-3 py-1.5">Prioridad</p>
                    {PRIORITY_OPTIONS.map(opt => (
                        <button
                            key={opt.value}
                            onClick={() => { onSelect(opt.value); setOpen(false); }}
                            className={clsx(
                                'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] font-semibold transition-colors',
                                currentPriority === opt.value
                                    ? 'bg-slate-100 dark:bg-white/5 text-slate-900 dark:text-white'
                                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5'
                            )}
                        >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill={opt.fill} strokeWidth="0">
                                <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
                                <line x1="4" y1="22" x2="4" y2="15" stroke={opt.fill} strokeWidth="2" strokeLinecap="round"/>
                            </svg>
                            {opt.label}
                            {currentPriority === opt.value && <Check size={12} className="ml-auto text-blue-500" />}
                        </button>
                    ))}
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Inline Status Picker ─────────────────────────────────────────────────────
function InlineStatusPicker({
    currentStatus,
    onSelect,
}: {
    currentStatus: string;
    onSelect: (status: string) => void;
}) {
    const [open, setOpen] = useState(false);
    const cfg = getStatus(currentStatus);

    return (
        <Popover.Root open={open} onOpenChange={setOpen}>
            <Popover.Trigger asChild>
                <button
                    className={clsx(
                        'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-black uppercase tracking-widest transition-all min-h-[28px]',
                        cfg.bg, cfg.text,
                        'border',
                        open ? 'ring-2 ring-blue-500/30 border-blue-400' : cfg.border,
                        'hover:brightness-95 dark:hover:brightness-110'
                    )}
                    aria-label="Selector de estado"
                    aria-expanded={open}
                >
                    <span className={clsx('size-1.5 rounded-full shrink-0', cfg.dot)} />
                    {cfg.label}
                    <ChevronDown size={9} className={clsx('ml-0.5 transition-transform duration-200', open && 'rotate-180')} />
                </button>
            </Popover.Trigger>

            <Popover.Portal>
                <Popover.Content
                    className="z-[500] w-48 bg-white dark:bg-[#1e1f21] rounded-xl shadow-2xl border border-slate-200 dark:border-white/10 p-1"
                    sideOffset={6}
                    align="start"
                >
                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 px-3 py-1.5">Estado</p>
                    {STATUS_OPTIONS.filter((s, i, arr) => arr.findIndex(x => x.label === s.label) === i).map(opt => (
                        <button
                            key={opt.value}
                            onClick={() => { onSelect(opt.value); setOpen(false); }}
                            className={clsx(
                                'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] font-semibold transition-colors',
                                currentStatus === opt.value
                                    ? 'bg-slate-100 dark:bg-white/5 text-slate-900 dark:text-white'
                                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5'
                            )}
                        >
                            <span className={clsx('size-2 rounded-full shrink-0', opt.dot)} />
                            {opt.label}
                            {currentStatus === opt.value && <Check size={12} className="ml-auto text-blue-500" />}
                        </button>
                    ))}
                </Popover.Content>
            </Popover.Portal>
        </Popover.Root>
    );
}

// ─── Quick Comment Popover ────────────────────────────────────────────────────
function CommentPopover({ onClose }: { onClose: () => void }) {
    const [text, setText] = useState('');
    return (
        <div className="absolute right-0 top-full mt-1 w-80 bg-white dark:bg-[#252528] rounded-2xl shadow-2xl border border-slate-200/80 dark:border-white/10 z-[500] overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100 dark:border-white/5">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Comentario rápido</span>
                <button onClick={onClose} className="p-0.5 rounded text-slate-300 hover:text-slate-500 dark:hover:text-slate-200 transition-colors">
                    <X size={13}/>
                </button>
            </div>
            {/* Textarea */}
            <div className="relative">
                <textarea
                    autoFocus
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="Escribe un comentario... @Brain para IA"
                    className="w-full resize-none text-[12px] text-slate-600 dark:text-slate-300 placeholder:text-slate-400 px-3 pt-3 pb-2 bg-transparent outline-none min-h-[68px] leading-relaxed"
                    onKeyDown={e => {
                        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && text.trim()) onClose();
                        if (e.key === 'Escape') onClose();
                    }}
                />
            </div>
            {/* Toolbar */}
            <div className="flex items-center gap-1 px-3 pb-3">
                <button className="p-1.5 rounded-lg text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors" title="Adjuntar">
                    <Paperclip size={13} />
                </button>
                <button className="p-1.5 rounded-lg text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors" title="Mencionar">
                    <AtSign size={13} />
                </button>
                <button className="p-1.5 rounded-lg text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors" title="Emoji">
                    <Smile size={13} />
                </button>
                <div className="flex-1" />
                <span className="text-[9px] text-slate-400 mr-2 hidden sm:block">⌘↵ enviar</span>
                <button
                    onClick={onClose}
                    className={clsx(
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-bold transition-all',
                        text.trim()
                            ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-md shadow-blue-500/20 active:scale-95'
                            : 'bg-slate-100 dark:bg-white/5 text-slate-400 cursor-not-allowed'
                    )}
                    disabled={!text.trim()}
                >
                    <Send size={11} />
                    Enviar
                </button>
            </div>
        </div>
    );
}

// ─── Task Row ─────────────────────────────────────────────────────────────────
function TaskRow({
    task,
    onOpen,
    onChange,
}: {
    task: LocalTask;
    onOpen: () => void;
    onChange: (patch: Partial<LocalTask>) => void;
}) {
    const { openLayer, setRightMode } = useSidebarLayers();
    const [commentOpen, setCommentOpen] = useState(false);
    const commentRef = useRef<HTMLDivElement>(null);

    const status = task._status ?? task.status ?? 'todo';
    const priority = task._priority ?? task.priority ?? 'normal';
    const dueDate = task._due_date !== undefined ? task._due_date : task.due_date;
    const assignedUser = task._assignedUser ?? null;

    // Close comment popover on outside click
    useEffect(() => {
        if (!commentOpen) return;
        const handleClick = (e: MouseEvent) => {
            if (commentRef.current && !commentRef.current.contains(e.target as Node)) {
                setCommentOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [commentOpen]);

    const handleCommentClick = () => {
        // Optimistic: open inline popover AND trigger the RightPanel
        setCommentOpen(v => !v);
        if (!commentOpen) {
            setRightMode('push');
            openLayer('RIGHT');
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center group border-b border-slate-100 dark:border-white/[0.04] hover:bg-slate-50/70 dark:hover:bg-white/[0.02] transition-colors relative min-h-[40px]"
        >
            {/* Checkbox */}
            <div className="w-8 flex-shrink-0 flex items-center justify-center pl-2">
                <button
                    onClick={() => onChange({ _status: status === 'done' ? 'todo' : 'done' })}
                    className={clsx(
                        'size-4 rounded-full border-2 flex items-center justify-center text-[9px] transition-all active:scale-95',
                        status === 'done'
                            ? 'bg-emerald-500 border-emerald-500 text-white'
                            : 'border-slate-300 dark:border-white/20 text-transparent hover:border-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-500/10'
                    )}
                    aria-label={status === 'done' ? 'Desmarcar tarea' : 'Completar tarea'}
                >
                    {status === 'done' && <Check size={9} />}
                </button>
            </div>

            {/* Task name */}
            <button
                onClick={onOpen}
                className="flex-1 min-w-0 flex items-center gap-2 px-3 py-2.5 text-left min-h-[40px]"
            >
                <span className={clsx(
                    'text-[13px] font-medium truncate transition-colors',
                    status === 'done'
                        ? 'line-through text-slate-400 dark:text-slate-600'
                        : 'text-slate-800 dark:text-slate-200 group-hover:text-blue-600 dark:group-hover:text-blue-400'
                )}>
                    {task.title}
                </span>
            </button>

            {/* ── PERSONA ASIGNADA ─────── */}
            <div className="w-28 flex-shrink-0 flex items-center justify-center px-1">
                <InlineUserPicker
                    currentUser={assignedUser}
                    onSelect={(user) => onChange({ _assignedUser: user })}
                />
            </div>

            {/* ── FECHA LÍMITE ─────────── */}
            <div className="w-32 flex-shrink-0 flex items-center px-1">
                <InlineDatePicker
                    currentDate={dueDate as string | null}
                    onSelect={(date) => onChange({ _due_date: date })}
                />
            </div>

            {/* ── PRIORIDAD ────────────── */}
            <div className="w-20 flex-shrink-0 flex items-center justify-center px-1">
                <InlinePriorityPicker
                    currentPriority={priority}
                    onSelect={(p) => onChange({ _priority: p })}
                />
            </div>

            {/* ── ESTADO ───────────────── */}
            <div className="w-36 flex-shrink-0 flex items-center px-2">
                <InlineStatusPicker
                    currentStatus={status}
                    onSelect={(s) => onChange({ _status: s })}
                />
            </div>

            {/* ── COMENTARIOS ──────────── */}
            <div className="w-24 flex-shrink-0 flex items-center justify-center px-1 relative" ref={commentRef}>
                <button
                    onClick={handleCommentClick}
                    className={clsx(
                        'flex items-center justify-center size-8 rounded-lg border transition-all min-h-[40px] min-w-[32px]',
                        commentOpen
                            ? 'border-blue-300 dark:border-blue-500/40 bg-blue-50 dark:bg-blue-500/10 text-blue-600'
                            : 'border-slate-200 dark:border-white/10 text-slate-300 dark:text-slate-600 hover:border-blue-200 dark:hover:border-blue-500/30 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-500/10'
                    )}
                    aria-label="Ver comentarios y actividad"
                >
                    <MessageSquare size={13} />
                </button>
                <AnimatePresence>
                    {commentOpen && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.96, y: -4 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.96, y: -4 }}
                            transition={{ duration: 0.1 }}
                            className="absolute right-0 top-full mt-1"
                        >
                            <CommentPopover onClose={() => setCommentOpen(false)} />
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* More */}
            <div className="w-8 flex-shrink-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="size-6 rounded flex items-center justify-center text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                    <MoreHorizontal size={13} />
                </button>
            </div>
        </motion.div>
    );
}

// ─── Status Group ─────────────────────────────────────────────────────────────
function StatusGroup({
    status,
    tasks,
    onOpenTask,
    onAddTask,
    isFirst,
    onChangeTask,
    quickAddStatus,
    quickAddTitle = '',
    onQuickAddTitleChange,
    onQuickAddConfirm,
    onQuickAddCancel,
}: {
    status: string;
    tasks: LocalTask[];
    onOpenTask: (t: ProjectTaskRecord) => void;
    onAddTask: (s: string) => void;
    isFirst?: boolean;
    onChangeTask: (taskId: number | string, patch: Partial<LocalTask>) => void;
    quickAddStatus?: string | null;
    quickAddTitle?: string;
    onQuickAddTitleChange?: (v: string) => void;
    onQuickAddConfirm?: () => void;
    onQuickAddCancel?: () => void;
}) {
    const inputRef = React.useRef<HTMLInputElement>(null);
    const isAddingHere =
        quickAddStatus === status || (quickAddStatus === 'todo' && status === 'pending');
    const [collapsed, setCollapsed] = useState(false);

    React.useEffect(() => {
        if (isAddingHere && inputRef.current) {
            setTimeout(() => {
                inputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                inputRef.current?.focus();
            }, 80);
        }
    }, [isAddingHere]);

    const cfg = getStatus(status);
    const pillCls = GROUP_PILL[status] ?? GROUP_PILL['todo'];

    return (
        <div className="mb-0">
            {/* Group Header */}
            <div className={clsx('flex items-center gap-3 px-4 py-3', !isFirst && 'mt-3')}>
                <button
                    onClick={() => setCollapsed(v => !v)}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                    aria-expanded={!collapsed}
                >
                    {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                </button>
                <span className={clsx('px-3 py-1 rounded-md text-[11px] font-black uppercase tracking-widest', pillCls)}>
                    {cfg.label}
                </span>
                <span className="text-[12px] font-bold text-slate-400">{tasks.length}</span>
            </div>

            <AnimatePresence initial={false}>
                {!collapsed && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className="overflow-hidden"
                    >
                        {/* Column Headers */}
                        <div className="flex items-center border-b border-slate-100 dark:border-white/[0.04] bg-slate-50/50 dark:bg-white/[0.01]">
                            <div className="w-8 flex-shrink-0" />
                            <div className="flex-1 px-3 py-2 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">Nombre</div>
                            <div className="w-28 flex-shrink-0 px-1 py-2 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 text-center whitespace-nowrap">Asignado</div>
                            <div className="w-32 flex-shrink-0 px-1 py-2 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 whitespace-nowrap">Fecha L&iacute;mite</div>
                            <div className="w-20 flex-shrink-0 px-1 py-2 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 text-center whitespace-nowrap">Prior.</div>
                            <div className="w-36 flex-shrink-0 px-2 py-2 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 whitespace-nowrap">Estado</div>
                            <div className="w-24 flex-shrink-0 px-1 py-2 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 text-center whitespace-nowrap">Coment.</div>
                            <div className="w-8 flex-shrink-0" />
                        </div>

                        {/* Task Rows */}
                        {tasks.map(task => (
                            <TaskRow
                                key={task.id}
                                task={task}
                                onOpen={() => onOpenTask(task)}
                                onChange={(patch) => onChangeTask(task.id, patch)}
                            />
                        ))}

                        {/* Quick-add row */}
                        {isAddingHere ? (
                            <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-100 dark:border-white/[0.04] bg-blue-50/30 dark:bg-blue-500/5 min-h-[40px]">
                                <div className="w-8 flex-shrink-0 flex items-center justify-center">
                                    <div className="size-4 rounded-full border-2 border-blue-400 dark:border-blue-500" />
                                </div>
                                <input
                                    ref={inputRef}
                                    autoFocus
                                    type="text"
                                    value={quickAddTitle}
                                    onChange={e => onQuickAddTitleChange?.(e.target.value)}
                                    onKeyDown={e => {
                                        if (e.key === 'Enter') onQuickAddConfirm?.();
                                        if (e.key === 'Escape') onQuickAddCancel?.();
                                    }}
                                    placeholder="Nombre de la tarea..."
                                    className="flex-1 text-[13px] font-medium bg-transparent outline-none text-slate-800 dark:text-slate-200 placeholder:text-slate-400"
                                />
                                <button
                                    onClick={onQuickAddConfirm}
                                    className="px-3 py-1.5 bg-blue-600 text-white text-[11px] font-bold rounded-lg hover:bg-blue-700 active:scale-95 transition-all"
                                >
                                    Guardar
                                </button>
                                <button
                                    onClick={onQuickAddCancel}
                                    className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-colors"
                                >
                                    <X size={14} />
                                </button>
                            </div>
                        ) : (
                            <button
                                onClick={() => onAddTask(status)}
                                className="flex items-center gap-2 px-4 py-2.5 text-[12px] font-medium text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-slate-50 dark:hover:bg-white/[0.02] w-full transition-colors border-b border-slate-100 dark:border-white/[0.04] min-h-[40px]"
                            >
                                <Plus size={13} />
                                Nuevo
                            </button>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────
const STATUS_ORDER = ['in_progress', 'pending', 'todo', 'done', 'blocked'];

export default function ProjectListView({
    tasks: propTasks,
    onOpenTask,
    onAddTask,
    onTasksChange,
    quickAddStatus,
    quickAddTitle,
    onQuickAddTitleChange,
    onQuickAddConfirm,
    onQuickAddCancel,
}: Props) {
    // Local optimistic state — overlays prop changes
    const [localOverrides, setLocalOverrides] = useState<Record<string | number, Partial<LocalTask>>>({});

    const tasks: LocalTask[] = propTasks.map(t => ({
        ...t,
        ...(localOverrides[t.id] ?? {}),
    }));

    const handleChangeTask = useCallback((taskId: number | string, patch: Partial<LocalTask>) => {
        // Optimistic update immediately
        setLocalOverrides(prev => ({
            ...prev,
            [taskId]: { ...(prev[taskId] ?? {}), ...patch },
        }));

        // Also propagate upward if caller wants to persist
        if (onTasksChange) {
            const updated = propTasks.map(t =>
                t.id === taskId ? { ...t, ...patch } : t
            );
            onTasksChange(updated as ProjectTaskRecord[]);
        }
    }, [propTasks, onTasksChange]);

    const groups = STATUS_ORDER.map(status => ({
        status,
        tasks: tasks.filter(t => {
            const s = (t._status ?? t.status ?? 'todo').toLowerCase();
            return s === status;
        }),
    })).filter(g => {
        const isTarget = quickAddStatus === g.status || (quickAddStatus === 'todo' && g.status === 'pending');
        return g.tasks.length > 0 || isTarget;
    });

    const ungrouped = tasks.filter(t => {
        const s = (t._status ?? t.status ?? 'todo').toLowerCase();
        return !STATUS_ORDER.includes(s);
    });

    return (
        <div className="h-full overflow-y-auto bg-white dark:bg-[#1e1f21] scrollbar-thin">

            {/* ── STICKY QUICK-ADD BAR ── */}
            <AnimatePresence>
                {quickAddStatus && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="overflow-hidden sticky top-0 z-30 border-b-2 border-blue-300 dark:border-blue-500/40 bg-blue-50 dark:bg-blue-900/10"
                    >
                        <QuickAddBar
                            quickAddTitle={quickAddTitle || ''}
                            onQuickAddTitleChange={onQuickAddTitleChange}
                            onQuickAddConfirm={onQuickAddConfirm}
                            onQuickAddCancel={onQuickAddCancel}
                        />
                    </motion.div>
                )}
            </AnimatePresence>

            {groups.map((g, i) => (
                <StatusGroup
                    key={g.status}
                    status={g.status}
                    tasks={g.tasks}
                    onOpenTask={onOpenTask}
                    onAddTask={onAddTask}
                    isFirst={i === 0}
                    onChangeTask={handleChangeTask}
                    quickAddStatus={null}
                    quickAddTitle={quickAddTitle}
                    onQuickAddTitleChange={onQuickAddTitleChange}
                    onQuickAddConfirm={onQuickAddConfirm}
                    onQuickAddCancel={onQuickAddCancel}
                />
            ))}

            {ungrouped.length > 0 && (
                <StatusGroup
                    status="todo"
                    tasks={ungrouped}
                    onOpenTask={onOpenTask}
                    onAddTask={onAddTask}
                    onChangeTask={handleChangeTask}
                />
            )}

            {propTasks.length === 0 && (
                <div className="flex flex-col items-center justify-center py-24 gap-4">
                    <div className="size-16 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                        <CheckCircle2 size={28} className="text-slate-300 dark:text-slate-600" />
                    </div>
                    <div className="text-center">
                        <p className="text-sm font-bold text-slate-500">Sin tareas en este proyecto</p>
                        <p className="text-xs text-slate-400 mt-1">Haz clic en &quot;+ Nuevo&quot; para empezar</p>
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── Sticky Quick-Add Bar ─────────────────────────────────────────────────────
function QuickAddBar({
    quickAddTitle,
    onQuickAddTitleChange,
    onQuickAddConfirm,
    onQuickAddCancel,
}: {
    quickAddTitle: string;
    onQuickAddTitleChange?: (v: string) => void;
    onQuickAddConfirm?: () => void;
    onQuickAddCancel?: () => void;
}) {
    const inputRef = React.useRef<HTMLInputElement>(null);
    React.useEffect(() => { setTimeout(() => inputRef.current?.focus(), 60); }, []);

    return (
        <div className="flex items-center gap-3 px-4 py-3 min-h-[40px]">
            <div className="size-5 rounded-full border-2 border-blue-400 dark:border-blue-500 shrink-0" />
            <input
                ref={inputRef}
                type="text"
                value={quickAddTitle}
                onChange={e => onQuickAddTitleChange?.(e.target.value)}
                onKeyDown={e => {
                    if (e.key === 'Enter') onQuickAddConfirm?.();
                    if (e.key === 'Escape') onQuickAddCancel?.();
                }}
                placeholder="Nombre de la tarea... (Enter para guardar, Esc para cancelar)"
                className="flex-1 text-[13px] font-medium bg-transparent outline-none text-slate-800 dark:text-slate-200 placeholder:text-slate-400"
            />
            <button
                onClick={onQuickAddConfirm}
                className="px-4 py-1.5 bg-blue-600 text-white text-[11px] font-bold rounded-lg hover:bg-blue-700 active:scale-95 transition-all shrink-0"
            >
                Guardar
            </button>
            <button
                onClick={onQuickAddCancel}
                className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg transition-colors"
            >
                <X size={14} />
            </button>
        </div>
    );
}

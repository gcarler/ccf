"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
    ChevronDown, ChevronRight, Plus,
    MessageSquare, MoreHorizontal, CheckCircle2, X, Send,
    Paperclip, AtSign, Smile, Check,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { ProjectTaskRecord } from '@/types/projects';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import {
    InlineStatusPicker,
    InlinePriorityPicker,
    InlineDatePicker,
    InlineUserPicker,
} from '@/components/ui/inline-editors';

// ─── Status Config ────────────────────────────────────────────────────────────
const STATUS_OPTIONS = [
    { value: 'todo',        label: 'Pendiente',   dot: 'bg-[hsl(var(--surface-2))]',   bg: 'bg-[hsl(var(--surface-2))] dark:bg-white/5',           text: 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]',    border: 'border-[hsl(var(--border))] dark:border-white/10' },
    { value: 'in_progress', label: 'En Progreso', dot: 'bg-[hsl(var(--primary))]',  bg: 'bg-blue-100 dark:bg-blue-500/20',    text: 'text-[hsl(var(--primary))] dark:text-blue-300',  border: 'border-blue-200 dark:border-blue-500/30' },
    { value: 'review',      label: 'En Revisión', dot: 'bg-amber-500',   bg: 'bg-amber-100 dark:bg-amber-500/20',    text: 'text-amber-700 dark:text-amber-300',  border: 'border-amber-200 dark:border-amber-500/30' },
    { value: 'completed',   label: 'Completado',  dot: 'bg-emerald-500', bg: 'bg-emerald-100 dark:bg-emerald-500/20',  text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200 dark:border-emerald-500/30' },
] as const;
function getStatus(val: string) {
    return STATUS_OPTIONS.find(s => s.value === val) ?? STATUS_OPTIONS[0];
}

// ─── Group header pill styles ─────────────────────────────────────────────────
const GROUP_PILL: Record<string, string> = {
    todo:        'bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] dark:bg-white/10 dark:text-[hsl(var(--text-secondary))]',
    in_progress: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-500/20 dark:text-blue-300',
    review:      'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    completed:   'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
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
    onTaskUpdate?: (taskId: string, patch: Partial<ProjectTaskRecord>) => void;
    quickAddStatus?: string | null;
    quickAddTitle?: string;
    onQuickAddTitleChange?: (v: string) => void;
    onQuickAddConfirm?: () => void;
    onQuickAddCancel?: () => void;
}

// ─── Quick Comment Popover ────────────────────────────────────────────────────
function CommentPopover({ onClose }: { onClose: () => void }) {
    const [text, setText] = useState('');
    return (
        <div className="absolute right-0 top-full mt-1 w-80 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg shadow-2xl border border-[hsl(var(--border))]/80 dark:border-white/10 z-[500] overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-[hsl(var(--border))] dark:border-white/5">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Comentario rápido</span>
                <button onClick={onClose} className="p-0.5 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors">
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
                    className="w-full resize-none text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] px-3 pt-3 pb-2 bg-transparent outline-none min-h-[68px] leading-relaxed"
                    onKeyDown={e => {
                        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && text.trim()) onClose();
                        if (e.key === 'Escape') onClose();
                    }}
                />
            </div>
            {/* Toolbar */}
            <div className="flex items-center gap-1 px-3 pb-3">
                <button className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors" title="Adjuntar">
                    <Paperclip size={13} />
                </button>
                <button className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors" title="Mencionar">
                    <AtSign size={13} />
                </button>
                <button className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors" title="Emoji">
                    <Smile size={13} />
                </button>
                <div className="flex-1" />
                <span className="text-[9px] text-[hsl(var(--text-secondary))] mr-2 hidden sm:block">⌘↵ enviar</span>
                <button
                    onClick={onClose}
                    className={clsx(
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-bold transition-all',
                        text.trim()
                            ? 'bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary))] shadow-md shadow-blue-500/20 active:scale-95'
                            : 'bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] cursor-not-allowed'
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
    const priority = task._priority ?? task.priority ?? 'medium';
    const dueDate = task._due_date !== undefined ? task._due_date : task.due_date;
    const assignedUserId = task._assignedUser?.id != null ? String(task._assignedUser.id) : (task.assignee_id ?? null);

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
            className="flex items-center group border-b border-[hsl(var(--border))] dark:border-white/[0.04] hover:bg-[hsl(var(--surface-1))]/70 dark:hover:bg-white/[0.02] transition-colors relative min-h-[40px]"
        >
            {/* Checkbox */}
            <div className="w-8 flex-shrink-0 flex items-center justify-center pl-2">
                <button
                    onClick={() => onChange({ _status: status === 'completed' ? 'todo' : 'completed' })}
                    className={clsx(
                        'size-4 rounded-full border-2 flex items-center justify-center text-[9px] transition-all active:scale-95',
                        status === 'completed'
                            ? 'bg-emerald-500 border-emerald-500 text-white'
                            : 'border-[hsl(var(--border))] dark:border-white/20 text-transparent hover:border-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-500/10'
                    )}
                    aria-label={status === 'completed' ? 'Desmarcar tarea' : 'Completar tarea'}
                >
                    {status === 'completed' && <Check size={9} />}
                </button>
            </div>

            {/* Task name */}
            <button
                onClick={onOpen}
                className="flex-1 min-w-0 flex items-center gap-2 px-3 py-2.5 text-left min-h-[40px]"
            >
                <span className={clsx(
                    'text-[13px] font-medium truncate transition-colors',
                    status === 'completed'
                        ? 'line-through text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]'
                        : 'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] dark:group-hover:text-[hsl(var(--primary))]'
                )}>
                    {task.title}
                </span>
            </button>

            {/* ── PERSONA ASIGNADA ─────── */}
            <div className="w-28 flex-shrink-0 flex items-center justify-center px-1">
                <InlineUserPicker
                    value={assignedUserId}
                    onChange={(userId, userName) => onChange({ _assignedUser: userId ? { id: Number(userId), username: userName || '', email: '' } : null })}
                />
            </div>

            {/* ── FECHA LÍMITE ─────────── */}
            <div className="w-32 flex-shrink-0 flex items-center px-1">
                <InlineDatePicker
                    value={dueDate as string | null}
                    onChange={(date) => onChange({ _due_date: date })}
                />
            </div>

            {/* ── PRIORIDAD ────────────── */}
            <div className="w-20 flex-shrink-0 flex items-center justify-center px-1">
                <InlinePriorityPicker
                    value={priority}
                    onChange={(p) => onChange({ _priority: p })}
                />
            </div>

            {/* ── ESTADO ───────────────── */}
            <div className="w-36 flex-shrink-0 flex items-center px-2">
                <InlineStatusPicker
                    value={status}
                    onChange={(s) => onChange({ _status: s })}
                />
            </div>

            {/* ── COMENTARIOS ──────────── */}
            <div className="w-24 flex-shrink-0 flex items-center justify-center px-1 relative" ref={commentRef}>
                <button
                    onClick={handleCommentClick}
                    className={clsx(
                        'flex items-center justify-center size-8 rounded-lg border transition-all min-h-[40px] min-w-[32px]',
                        commentOpen
                            ? 'border-blue-300 dark:border-blue-500/40 bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))]'
                            : 'border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:border-blue-200 dark:hover:border-blue-500/30 hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10'
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
                <button className="size-6 rounded flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-colors">
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
    const isAddingHere = quickAddStatus === status;
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
                    className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors"
                    aria-expanded={!collapsed}
                >
                    {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                </button>
                <span className={clsx('px-3 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wide', pillCls)}>
                    {cfg.label}
                </span>
                <span className="text-[12px] font-bold text-[hsl(var(--text-secondary))]">{tasks.length}</span>
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
                        <div className="flex items-center border-b border-[hsl(var(--border))] dark:border-white/[0.04] bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.01]">
                            <div className="w-8 flex-shrink-0" />
                            <div className="flex-1 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Nombre</div>
                            <div className="w-28 flex-shrink-0 px-1 py-2 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] text-center whitespace-nowrap">Asignado</div>
                            <div className="w-32 flex-shrink-0 px-1 py-2 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] whitespace-nowrap">Fecha L&iacute;mite</div>
                            <div className="w-20 flex-shrink-0 px-1 py-2 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] text-center whitespace-nowrap">Prior.</div>
                            <div className="w-36 flex-shrink-0 px-2 py-2 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] whitespace-nowrap">Estado</div>
                            <div className="w-24 flex-shrink-0 px-1 py-2 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] text-center whitespace-nowrap">Coment.</div>
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
                            <div className="flex items-center gap-2 px-4 py-2 border-b border-[hsl(var(--border))] dark:border-white/[0.04] bg-blue-50/30 dark:bg-blue-500/5 min-h-[40px]">
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
                                    className="flex-1 text-[13px] font-medium bg-transparent outline-none text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))]"
                                />
                                <button
                                    onClick={onQuickAddConfirm}
                                    className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white text-[11px] font-bold rounded-lg hover:bg-[hsl(var(--primary))] active:scale-95 transition-all"
                                >
                                    Guardar
                                </button>
                                <button
                                    onClick={onQuickAddCancel}
                                    className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-lg transition-colors"
                                >
                                    <X size={14} />
                                </button>
                            </div>
                        ) : (
                            <button
                                onClick={() => onAddTask(status)}
                                className="flex items-center gap-2 px-4 py-2.5 text-[12px] font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] dark:hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] w-full transition-colors border-b border-[hsl(var(--border))] dark:border-white/[0.04] min-h-[40px]"
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
const STATUS_ORDER = ['todo', 'in_progress', 'review', 'completed'];

export default function ProjectListView({
    tasks: propTasks,
    onOpenTask,
    onAddTask,
    onTasksChange,
    onTaskUpdate,
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

        // Map local overlay fields to real task fields for persistence
        const apiPatch: Partial<ProjectTaskRecord> = {};
        if (patch._status !== undefined) apiPatch.status = patch._status;
        if (patch._priority !== undefined) apiPatch.priority = patch._priority;
        if (patch._due_date !== undefined) apiPatch.due_date = patch._due_date;
        if (patch._assignedUser !== undefined) apiPatch.assignee_id = patch._assignedUser ? String(patch._assignedUser.id) : null;

        if (Object.keys(apiPatch).length > 0) {
            onTaskUpdate?.(String(taskId), apiPatch);
        }

        // Also propagate upward if caller wants to persist
        if (onTasksChange) {
            const updated = propTasks.map(t =>
                t.id === taskId ? { ...t, ...patch } : t
            );
            onTasksChange(updated as ProjectTaskRecord[]);
        }
    }, [onTaskUpdate, propTasks, onTasksChange]);

    const groups = STATUS_ORDER.map(status => ({
        status,
        tasks: tasks.filter(t => {
            const s = (t._status ?? t.status ?? 'todo').toLowerCase();
            return s === status;
        }),
    })).filter(g => {
        const isTarget = quickAddStatus === g.status;
        return g.tasks.length > 0 || isTarget;
    });

    const ungrouped = tasks.filter(t => {
        const s = (t._status ?? t.status ?? 'todo').toLowerCase();
        return !STATUS_ORDER.includes(s);
    });

    return (
        <div className="h-full overflow-y-auto bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] scrollbar-thin">

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
                <div className="flex flex-col items-center justify-center py-1.5 gap-4">
                    <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                        <CheckCircle2 size={28} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
                    </div>
                    <div className="text-center">
                        <p className="text-sm font-bold text-[hsl(var(--text-secondary))]">Sin tareas en este proyecto</p>
                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">Haz clic en &quot;+ Nuevo&quot; para empezar</p>
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
                className="flex-1 text-[13px] font-medium bg-transparent outline-none text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))]"
            />
            <button
                onClick={onQuickAddConfirm}
                className="px-4 py-1.5 bg-[hsl(var(--primary))] text-white text-[11px] font-bold rounded-lg hover:bg-[hsl(var(--primary))] active:scale-95 transition-all shrink-0"
            >
                Guardar
            </button>
            <button
                onClick={onQuickAddCancel}
                className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-lg transition-colors"
            >
                <X size={14} />
            </button>
        </div>
    );
}

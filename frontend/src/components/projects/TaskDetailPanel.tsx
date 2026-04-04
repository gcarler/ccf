"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X, ChevronRight, ChevronDown, Paperclip, Star, Maximize2, Trash2,
    UserRound, CalendarDays, Flag, Tag, AlignLeft, MessageSquare,
    Plus, Check, Sparkles, MoreHorizontal, Map, Send, Circle,
    CheckCircle2, Loader2, GitBranch, Home, FolderOpen
} from 'lucide-react';
import clsx from 'clsx';
import { motion as m } from 'framer-motion';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import type { ProjectTaskRecord } from '@/types/projects';

// ─────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────
export interface Activity {
    id: number;
    title: string;
    completed: boolean;
    assignee?: { name: string; color?: string };
    children?: Activity[];
}

interface Comment {
    id: number;
    author: string;
    authorColor?: string;
    text: string;
    timestamp: Date;
}

interface TaskDetailPanelProps {
    task: ProjectTaskRecord | null;
    projectTitle?: string;
    onClose: () => void;
    onUpdate?: (updated: ProjectTaskRecord) => void;
    onDelete?: (taskId: number) => void;
    onVerRutaClick?: () => void; // abre S3 con el árbol
}

// ─────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────
const STATUS_MAP: Record<string, { label: string; color: string; bg: string; icon: React.ElementType }> = {
    todo:        { label: 'Pendiente',   color: 'text-slate-600',   bg: 'bg-slate-100 dark:bg-slate-800/60',      icon: Circle },
    in_progress: { label: 'En Progreso', color: 'text-blue-600',    bg: 'bg-blue-50 dark:bg-blue-500/10',         icon: Loader2 },
    done:        { label: 'Completada',  color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10',   icon: CheckCircle2 },
    blocked:     { label: 'Bloqueada',   color: 'text-rose-600',    bg: 'bg-rose-50 dark:bg-rose-500/10',         icon: X },
};

const PRIORITY_MAP: Record<string, { label: string; color: string; dot: string }> = {
    urgent: { label: 'Urgente', color: 'text-rose-600',   dot: 'bg-rose-500' },
    high:   { label: 'Alta',    color: 'text-orange-600', dot: 'bg-orange-500' },
    normal: { label: 'Normal',  color: 'text-blue-600',   dot: 'bg-blue-500' },
    low:    { label: 'Baja',    color: 'text-slate-400',  dot: 'bg-slate-400' },
};

const MIN_WIDTH = 400;
const DEFAULT_WIDTH = 520;
const MAX_RATIO = 0.88;

let nextId = Date.now();
const uid = () => ++nextId;

// ─────────────────────────────────────────────────────────────────
// RECURSIVE ACTIVITY ITEM
// ─────────────────────────────────────────────────────────────────
function ActivityItem({
    activity,
    depth = 0,
    onToggle,
    onAddChild,
    onUpdateTitle,
}: {
    activity: Activity;
    depth?: number;
    onToggle: (id: number) => void;
    onAddChild: (parentId: number) => void;
    onUpdateTitle: (id: number, title: string) => void;
}) {
    const [expanded, setExpanded] = useState(depth === 0);
    const [editing, setEditing] = useState(false);
    const [titleVal, setTitleVal] = useState(activity.title);
    const hasChildren = (activity.children?.length ?? 0) > 0;
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);

    return (
        <div>
            <div
                className={clsx(
                    'group flex items-center gap-1.5 py-1.5 px-2 rounded-lg transition-colors hover:bg-slate-50 dark:hover:bg-white/[0.04] relative',
                )}
                style={{ paddingLeft: depth * 20 + 8 }}
            >
                {/* Indent guide lines */}
                {depth > 0 && (
                    <div
                        className="absolute left-0 top-0 bottom-0 w-px bg-slate-200 dark:bg-white/[0.08]"
                        style={{ left: depth * 20 - 4 }}
                    />
                )}

                {/* Expand toggle */}
                <button
                    onClick={() => setExpanded(v => !v)}
                    className={clsx(
                        'size-4 flex items-center justify-center text-slate-300 hover:text-slate-500 transition-colors shrink-0',
                        !hasChildren && 'opacity-0 pointer-events-none'
                    )}
                >
                    {expanded
                        ? <ChevronDown size={12} />
                        : <ChevronRight size={12} />
                    }
                </button>

                {/* Checkbox */}
                <button
                    onClick={() => onToggle(activity.id)}
                    className={clsx(
                        'size-4 rounded border-2 flex items-center justify-center shrink-0 transition-all',
                        activity.completed
                            ? 'bg-emerald-500 border-emerald-500 text-white'
                            : 'border-slate-300 dark:border-slate-600 hover:border-blue-400'
                    )}
                >
                    {activity.completed && <Check size={9} strokeWidth={3} />}
                </button>

                {/* Title */}
                {editing ? (
                    <input
                        ref={inputRef}
                        value={titleVal}
                        onChange={e => setTitleVal(e.target.value)}
                        onBlur={() => {
                            onUpdateTitle(activity.id, titleVal);
                            setEditing(false);
                        }}
                        onKeyDown={e => {
                            if (e.key === 'Enter') { onUpdateTitle(activity.id, titleVal); setEditing(false); }
                            if (e.key === 'Escape') { setTitleVal(activity.title); setEditing(false); }
                        }}
                        className="flex-1 text-[12px] bg-transparent outline-none border-b border-blue-400 text-slate-800 dark:text-white"
                    />
                ) : (
                    <span
                        onDoubleClick={() => setEditing(true)}
                        className={clsx(
                            'flex-1 text-[12px] font-medium cursor-default select-none truncate',
                            activity.completed
                                ? 'line-through text-slate-400 dark:text-slate-500'
                                : 'text-slate-700 dark:text-slate-200'
                        )}
                    >
                        {activity.title}
                    </span>
                )}

                {/* Assignee avatar */}
                {activity.assignee && (
                    <div
                        title={activity.assignee.name}
                        className="size-5 rounded-full flex items-center justify-center text-[8px] font-black text-white shrink-0"
                        style={{ backgroundColor: activity.assignee.color ?? '#6366f1' }}
                    >
                        {activity.assignee.name.charAt(0).toUpperCase()}
                    </div>
                )}

                {/* Add child button */}
                <button
                    onClick={() => { onAddChild(activity.id); setExpanded(true); }}
                    className="size-4 rounded flex items-center justify-center text-slate-300 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-all"
                    title="Añadir sub-actividad"
                >
                    <Plus size={10} strokeWidth={2.5} />
                </button>
            </div>

            {/* Children */}
            <AnimatePresence initial={false}>
                {expanded && hasChildren && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className="overflow-hidden"
                    >
                        {activity.children!.map(child => (
                            <ActivityItem
                                key={child.id}
                                activity={child}
                                depth={depth + 1}
                                onToggle={onToggle}
                                onAddChild={onAddChild}
                                onUpdateTitle={onUpdateTitle}
                            />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────
// ACTIVITY TREE HELPERS (recursive)
// ─────────────────────────────────────────────────────────────────
function toggleActivity(activities: Activity[], id: number): Activity[] {
    return activities.map(a => {
        if (a.id === id) return { ...a, completed: !a.completed };
        if (a.children) return { ...a, children: toggleActivity(a.children, id) };
        return a;
    });
}

function addChild(activities: Activity[], parentId: number, newItem: Activity): Activity[] {
    return activities.map(a => {
        if (a.id === parentId) return { ...a, children: [...(a.children ?? []), newItem] };
        if (a.children) return { ...a, children: addChild(a.children, parentId, newItem) };
        return a;
    });
}

function updateTitle(activities: Activity[], id: number, title: string): Activity[] {
    return activities.map(a => {
        if (a.id === id) return { ...a, title };
        if (a.children) return { ...a, children: updateTitle(a.children, id, title) };
        return a;
    });
}

// ─────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────
export default function TaskDetailPanel({
    task,
    projectTitle = 'Proyecto',
    onClose,
    onUpdate,
    onDelete,
    onVerRutaClick,
}: TaskDetailPanelProps) {
    const { token } = useAuth();

    // ── Width / resize state ──────────────────────────────────────
    const [width, setWidth] = useState<number>(() => {
        if (typeof window === 'undefined') return DEFAULT_WIDTH;
        return Number(localStorage.getItem('taskDetailPanelWidth') || DEFAULT_WIDTH);
    });
    const resizing = useRef(false);
    const startX   = useRef(0);
    const startW   = useRef(0);

    const onMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        resizing.current = true;
        startX.current = e.clientX;
        startW.current = width;
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';
    }, [width]);

    useEffect(() => {
        const onMove = (e: MouseEvent) => {
            if (!resizing.current) return;
            const delta = startX.current - e.clientX; // dragging left = wider
            const maxW  = window.innerWidth * MAX_RATIO;
            const newW  = Math.min(maxW, Math.max(MIN_WIDTH, startW.current + delta));
            setWidth(newW);
        };
        const onUp = () => {
            if (resizing.current) {
                resizing.current = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                localStorage.setItem('taskDetailPanelWidth', String(width));
            }
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        return () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
    }, [width]);

    // ── Form state ────────────────────────────────────────────────
    const [title, setTitle]         = useState(task?.title ?? '');
    const [description, setDesc]    = useState(task?.description ?? '');
    const [starred, setStarred]     = useState(false);
    const [saving, setSaving]       = useState(false);

    // ── Activities ────────────────────────────────────────────────
    const [activities, setActivities] = useState<Activity[]>([
        {
            id: uid(), title: 'Actividad 1: organizar agenda', completed: false,
            assignee: { name: 'Admin', color: '#6366f1' },
            children: [
                { id: uid(), title: 'Revisar disponibilidad del equipo', completed: false, assignee: { name: 'Admin', color: '#6366f1' } },
                { id: uid(), title: 'Preparar orden del día', completed: true, assignee: { name: 'Admin', color: '#6366f1' } },
            ]
        },
    ]);
    const [newActivityTitle, setNewActivityTitle] = useState('');

    const handleToggle = (id: number) => setActivities(prev => toggleActivity(prev, id));
    const handleAddChild = (parentId: number) => {
        const item: Activity = { id: uid(), title: 'Nueva sub-actividad', completed: false };
        setActivities(prev => addChild(prev, parentId, item));
    };
    const handleUpdateTitle = (id: number, t: string) => setActivities(prev => updateTitle(prev, id, t));
    const handleAddTopLevel = () => {
        if (!newActivityTitle.trim()) return;
        setActivities(prev => [...prev, { id: uid(), title: newActivityTitle.trim(), completed: false }]);
        setNewActivityTitle('');
    };

    // ── Comments ──────────────────────────────────────────────────
    const [comments, setComments] = useState<Comment[]>([]);
    const [commentInput, setCommentInput] = useState('');
    const [sendingComment, setSendingComment] = useState(false);

    const handleSendComment = async () => {
        if (!commentInput.trim()) return;
        setSendingComment(true);
        await new Promise(r => setTimeout(r, 300)); // simulate network
        setComments(prev => [...prev, {
            id: uid(),
            author: 'Tú',
            authorColor: '#6366f1',
            text: commentInput.trim(),
            timestamp: new Date(),
        }]);
        setCommentInput('');
        setSendingComment(false);
    };

    // ── Sync on task change ───────────────────────────────────────
    useEffect(() => {
        if (task) {
            setTitle(task.title ?? '');
            setDesc((task as any).description ?? '');
            setComments([]);
        }
    }, [task?.id]);

    // ── Save ──────────────────────────────────────────────────────
    const handleSave = async () => {
        if (!task) return;
        setSaving(true);
        try {
            const updated = await apiFetch<ProjectTaskRecord>(
                `/projects/${task.project_id}/tasks/${task.id}`,
                { method: 'PATCH', token, body: { title, description } }
            );
            onUpdate?.({ ...task, ...updated });
        } catch {
            onUpdate?.({ ...task, title, description: description as any });
        } finally {
            setSaving(false);
        }
    };

    // ── File attach ───────────────────────────────────────────────
    const fileInputRef = useRef<HTMLInputElement>(null);

    if (!task) return null;

    const status   = STATUS_MAP[task.status ?? 'todo'] ?? STATUS_MAP.todo;
    const priority = PRIORITY_MAP[task.priority ?? 'normal'] ?? PRIORITY_MAP.normal;
    const StatusIcon = status.icon;

    return (
        <AnimatePresence>
            <motion.aside
                key="task-detail-panel"
                initial={{ x: width, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: width, opacity: 0 }}
                transition={{ type: 'spring', damping: 32, stiffness: 300 }}
                style={{ width, minWidth: MIN_WIDTH }}
                className="relative h-full flex flex-col bg-white dark:bg-[#18191c] border-l border-slate-100 dark:border-white/[0.07] shadow-[-16px_0_48px_rgba(0,0,0,0.08)] dark:shadow-[-16px_0_48px_rgba(0,0,0,0.35)] overflow-hidden"
            >
                {/* ── RESIZE HANDLE ──────────────────────────────── */}
                <div
                    onMouseDown={onMouseDown}
                    className="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize z-10 group flex items-center justify-center"
                    title="Arrastrar para redimensionar"
                >
                    <div className="w-[3px] h-16 rounded-full bg-slate-200 dark:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>

                {/* ── HEADER ─────────────────────────────────────── */}
                <header className="shrink-0 px-4 pt-3 pb-0 border-b border-slate-100 dark:border-white/[0.06]">
                    {/* Row 1: breadcrumbs + tools */}
                    <div className="flex items-center justify-between mb-2">
                        {/* Breadcrumbs */}
                        <div className="flex items-center gap-1 text-[11px] text-slate-400 min-w-0">
                            <Home size={11} className="shrink-0" />
                            <ChevronRight size={10} className="text-slate-300 shrink-0" />
                            <FolderOpen size={11} className="shrink-0" />
                            <span className="truncate max-w-[100px] hover:text-slate-600 dark:hover:text-slate-300 cursor-pointer transition-colors">
                                {projectTitle}
                            </span>
                            <ChevronRight size={10} className="text-slate-300 shrink-0" />
                            <span className="font-semibold text-slate-600 dark:text-slate-300 truncate max-w-[120px]">
                                {task.title}
                            </span>
                        </div>

                        {/* Toolbar actions */}
                        <div className="flex items-center gap-0.5 shrink-0">
                            {/* "Ver Ruta" — opens S3 */}
                            <button
                                onClick={onVerRutaClick}
                                title="Ver ruta jerárquica"
                                className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold text-violet-600 bg-violet-50 dark:bg-violet-500/10 hover:bg-violet-100 dark:hover:bg-violet-500/20 transition-all border border-violet-200/50 dark:border-violet-500/20"
                            >
                                <GitBranch size={11} />
                                Ver Ruta
                            </button>

                            {/* Attach */}
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                title="Adjuntar archivo"
                                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
                            >
                                <Paperclip size={14} />
                            </button>
                            <input ref={fileInputRef} type="file" multiple className="hidden" />

                            {/* Star / Priority toggle */}
                            <button
                                onClick={() => setStarred(v => !v)}
                                title={starred ? 'Quitar de favoritos' : 'Marcar como favorito'}
                                className={clsx(
                                    'p-1.5 rounded-lg transition-all',
                                    starred
                                        ? 'text-amber-500 bg-amber-50 dark:bg-amber-500/10'
                                        : 'text-slate-400 hover:text-amber-400 hover:bg-slate-100 dark:hover:bg-white/5'
                                )}
                            >
                                <Star size={14} fill={starred ? 'currentColor' : 'none'} />
                            </button>

                            {/* Expand (fullscreen placeholder) */}
                            <button
                                title="Expandir a pantalla completa"
                                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
                                onClick={() => {
                                    const maxW = Math.floor(window.innerWidth * MAX_RATIO);
                                    setWidth(prev => prev < maxW - 50 ? maxW : DEFAULT_WIDTH);
                                }}
                            >
                                <Maximize2 size={14} />
                            </button>

                            {/* Delete */}
                            <button
                                onClick={() => { onDelete?.(task.id); onClose(); }}
                                title="Eliminar tarea"
                                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-all"
                            >
                                <Trash2 size={14} />
                            </button>

                            {/* Close */}
                            <button
                                onClick={onClose}
                                title="Cerrar panel"
                                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-all ml-0.5"
                            >
                                <X size={14} />
                            </button>
                        </div>
                    </div>

                    {/* Status chip */}
                    <div className="mb-2.5">
                        <button className={clsx(
                            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold border border-current/15 transition-all hover:border-current/30',
                            status.color, status.bg
                        )}>
                            <StatusIcon size={11} strokeWidth={2.5}
                                className={task.status === 'in_progress' ? 'animate-spin' : ''} />
                            {status.label}
                        </button>
                    </div>

                    {/* Title */}
                    <textarea
                        value={title}
                        onChange={e => setTitle(e.target.value)}
                        onBlur={handleSave}
                        rows={1}
                        className="w-full text-[17px] font-bold text-slate-900 dark:text-white bg-transparent resize-none outline-none leading-snug placeholder:text-slate-300 dark:placeholder:text-slate-600 pb-3"
                        placeholder="Nombre de la tarea..."
                        style={{ minHeight: 28 }}
                        onInput={e => {
                            const t = e.currentTarget;
                            t.style.height = 'auto';
                            t.style.height = t.scrollHeight + 'px';
                        }}
                    />
                </header>

                {/* ── BODY (scrollable) ──────────────────────────── */}
                <div className="flex-1 overflow-y-auto scrollbar-thin">

                    {/* ─ META FIELDS ─ */}
                    <section className="px-4 py-3 border-b border-slate-100 dark:border-white/[0.05] space-y-2">

                        <MetaRow icon={<UserRound size={13} className="text-slate-400" />} label="Persona asignada">
                            <button className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12px] font-medium text-slate-400 hover:bg-slate-50 dark:hover:bg-white/[0.04] border border-transparent hover:border-slate-200 dark:hover:border-white/[0.08] transition-all">
                                <div className="size-5 rounded-full bg-violet-600/20 border border-violet-300/30 flex items-center justify-center">
                                    <UserRound size={10} className="text-violet-500" />
                                </div>
                                Sin asignar
                            </button>
                        </MetaRow>

                        <MetaRow icon={<CalendarDays size={13} className="text-slate-400" />} label="Fecha límite">
                            <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[12px] font-medium text-slate-400 hover:bg-slate-50 dark:hover:bg-white/[0.04] border border-transparent hover:border-slate-200 dark:hover:border-white/[0.08] transition-all">
                                {task.due_date
                                    ? new Date(task.due_date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
                                    : 'Sin fecha límite'
                                }
                            </button>
                        </MetaRow>

                        <MetaRow icon={<Flag size={13} className="text-slate-400" />} label="Prioridad">
                            <button className={clsx('flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12px] font-bold border border-transparent hover:border-slate-200 dark:hover:border-white/[0.08] transition-all', priority.color)}>
                                <span className={clsx('size-2 rounded-full', priority.dot)} />
                                {priority.label}
                            </button>
                        </MetaRow>

                        <MetaRow icon={<Tag size={13} className="text-slate-400" />} label="Etiquetas">
                            <button className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-slate-400 hover:bg-slate-50 dark:hover:bg-white/[0.04] border border-dashed border-slate-300 dark:border-white/[0.1] transition-all">
                                <Plus size={10} /> Añadir etiqueta
                            </button>
                        </MetaRow>
                    </section>

                    {/* ─ DESCRIPTION ─ */}
                    <section className="px-4 py-3 border-b border-slate-100 dark:border-white/[0.05]">
                        <p className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2 flex items-center gap-1.5">
                            <AlignLeft size={11} /> Descripción
                        </p>
                        <textarea
                            value={description}
                            onChange={e => setDesc(e.target.value)}
                            onBlur={handleSave}
                            rows={3}
                            placeholder="Añade una descripción..."
                            className="w-full text-[13px] font-medium text-slate-700 dark:text-slate-300 bg-transparent resize-none outline-none placeholder:text-slate-300 dark:placeholder:text-slate-600 leading-relaxed focus:ring-0"
                        />
                    </section>

                    {/* ─ ACTIVIDADES ─ */}
                    <section className="px-4 py-3 border-b border-slate-100 dark:border-white/[0.05]">
                        <div className="flex items-center justify-between mb-3">
                            <p className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 flex items-center gap-1.5">
                                <Check size={11} /> Actividades
                                <span className="px-1.5 py-0.5 bg-slate-100 dark:bg-white/[0.06] rounded text-slate-500 dark:text-slate-400 font-bold text-[9px]">
                                    {activities.length}
                                </span>
                            </p>
                        </div>

                        {/* Activities list */}
                        <div className="space-y-0.5">
                            {activities.map(a => (
                                <ActivityItem
                                    key={a.id}
                                    activity={a}
                                    depth={0}
                                    onToggle={handleToggle}
                                    onAddChild={handleAddChild}
                                    onUpdateTitle={handleUpdateTitle}
                                />
                            ))}
                        </div>

                        {/* Add new activity */}
                        <div className="flex items-center gap-2 mt-2 pl-2">
                            <Plus size={13} className="text-slate-300 shrink-0" />
                            <input
                                type="text"
                                value={newActivityTitle}
                                onChange={e => setNewActivityTitle(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && handleAddTopLevel()}
                                placeholder="Añadir actividad..."
                                className="flex-1 text-[12px] bg-transparent outline-none text-slate-600 dark:text-slate-300 placeholder:text-slate-300 dark:placeholder:text-slate-600"
                            />
                            {newActivityTitle.trim() && (
                                <button
                                    onClick={handleAddTopLevel}
                                    className="px-2 py-1 bg-blue-600 text-white rounded-lg text-[10px] font-bold hover:bg-blue-700 transition-all"
                                >
                                    + Añadir
                                </button>
                            )}
                        </div>
                    </section>

                    {/* ─ COMENTARIOS ─ */}
                    <section className="px-4 py-3">
                        <p className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-3 flex items-center gap-1.5">
                            <MessageSquare size={11} /> Actividad
                        </p>

                        {/* Comment list */}
                        <div className="space-y-3 mb-4">
                            {comments.length === 0 && (
                                <p className="text-[11px] text-slate-300 dark:text-slate-600 italic text-center py-2">
                                    Sin comentarios aún. Menciona a alguien con @
                                </p>
                            )}
                            {comments.map(c => (
                                <div key={c.id} className="flex gap-2.5">
                                    <div
                                        className="size-6 rounded-full flex items-center justify-center text-[9px] font-black text-white shrink-0 mt-0.5"
                                        style={{ backgroundColor: c.authorColor ?? '#6366f1' }}
                                    >
                                        {c.author.charAt(0).toUpperCase()}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-baseline gap-2 mb-1">
                                            <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">{c.author}</span>
                                            <span className="text-[10px] text-slate-400">
                                                {c.timestamp.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        <p className="text-[12px] text-slate-600 dark:text-slate-300 leading-relaxed">{c.text}</p>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Comment input */}
                        <div className="flex items-end gap-2">
                            <div className="size-6 rounded-full bg-violet-600 flex items-center justify-center text-[9px] font-black text-white shrink-0">
                                T
                            </div>
                            <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-50 dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.07] focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-400/40 transition-all">
                                <input
                                    type="text"
                                    value={commentInput}
                                    onChange={e => setCommentInput(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendComment()}
                                    placeholder="Menciona @Dzin para crear, encontrar y preguntar..."
                                    className="flex-1 text-[12px] bg-transparent outline-none text-slate-700 dark:text-slate-300 placeholder:text-slate-300 dark:placeholder:text-slate-600"
                                />
                                {commentInput.trim() && (
                                    <button
                                        onClick={handleSendComment}
                                        disabled={sendingComment}
                                        className="text-blue-500 hover:text-blue-700 transition-colors"
                                    >
                                        {sendingComment
                                            ? <Loader2 size={14} className="animate-spin" />
                                            : <Send size={14} />
                                        }
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Comment type selector */}
                        <div className="flex items-center gap-2 mt-2 pl-8">
                            <button className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold text-blue-600 bg-blue-50 dark:bg-blue-500/10 border border-blue-200/50 dark:border-blue-500/20">
                                <MessageSquare size={9} /> Comentario
                                <ChevronDown size={9} />
                            </button>
                        </div>
                    </section>

                </div>{/* end body */}

            </motion.aside>
        </AnimatePresence>
    );
}

// ─────────────────────────────────────────────────────────────────
// META ROW
// ─────────────────────────────────────────────────────────────────
function MetaRow({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
    return (
        <div className="flex items-center gap-0">
            <div className="w-[140px] shrink-0 flex items-center gap-2 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                {icon}
                {label}
            </div>
            {children}
        </div>
    );
}

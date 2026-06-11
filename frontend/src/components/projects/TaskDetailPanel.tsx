"use client";

import UserSelect from '@/components/ui/UserSelect';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord,TaskSupplyRecord } from '@/types/projects';
import clsx from 'clsx';
import { AnimatePresence,motion } from 'framer-motion';
import {
AlignLeft,
Boxes,
CalendarDays,
Check,
CheckCircle2,
ChevronDown,
ChevronRight,
Circle,
Flag,
FolderOpen,
GitBranch,Home,
Loader2,
Maximize2,
MessageSquare,
Paperclip,
Plus,
Send,
Star,
Tag,
Trash2,
UserRound,
X
} from 'lucide-react';
import React,{ useCallback,useEffect,useRef,useState } from 'react';

// Paleta de colores para etiquetas
const LABEL_COLORS = [
    { bg: 'bg-rose-100 dark:bg-rose-900/30',   text: 'text-rose-700 dark:text-rose-300',   border: 'border-rose-300/50 dark:border-rose-500/30',   dot: 'bg-rose-500' },
    { bg: 'bg-orange-100 dark:bg-orange-900/30', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-300/50 dark:border-orange-500/30', dot: 'bg-orange-500' },
    { bg: 'bg-amber-100 dark:bg-amber-900/30',  text: 'text-amber-700 dark:text-amber-300',  border: 'border-amber-300/50 dark:border-amber-500/30',  dot: 'bg-amber-500' },
    { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-300/50 dark:border-emerald-500/30', dot: 'bg-emerald-500' },
    { bg: 'bg-blue-100 dark:bg-blue-900/30',   text: 'text-[hsl(var(--primary))] dark:text-blue-300',   border: 'border-blue-300/50 dark:border-blue-500/30',   dot: 'bg-[hsl(var(--primary))]' },
    { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-[hsl(var(--primary))] dark:text-blue-300', border: 'border-blue-300/50 dark:border-blue-500/30', dot: 'bg-[hsl(var(--primary))]' },
    { bg: 'bg-pink-100 dark:bg-pink-900/30',   text: 'text-pink-700 dark:text-pink-300',   border: 'border-pink-300/50 dark:border-pink-500/30',   dot: 'bg-pink-500' },
    { bg: 'bg-slate-100 dark:bg-slate-800/60', text: 'text-slate-600 dark:text-slate-300', border: 'border-slate-300/50 dark:border-slate-600/30', dot: 'bg-slate-400' },
];

function getLabelColor(label: string) {
    let hash = 0;
    for (let i = 0; i < label.length; i++) hash = label.charCodeAt(i) + ((hash << 5) - hash);
    return LABEL_COLORS[Math.abs(hash) % LABEL_COLORS.length];
}

// ─────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────
export interface Activity {
    id: string;
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
    onDelete?: (taskId: string) => void;
    onActivityCreated?: () => void;
    onVerRutaClick?: () => void; // abre S3 con el árbol
}

// ─────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────
const STATUS_MAP: Record<string, { label: string; color: string; bg: string; icon: React.ElementType }> = {
    todo:        { label: 'Pendiente',   color: 'text-slate-600',   bg: 'bg-slate-100 dark:bg-slate-800/60',      icon: Circle },
    in_progress: { label: 'En Progreso', color: 'text-[hsl(var(--primary))]',    bg: 'bg-blue-50 dark:bg-blue-500/10',         icon: Loader2 },
    done:        { label: 'Completada',  color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10',   icon: CheckCircle2 },
    blocked:     { label: 'Bloqueada',   color: 'text-rose-600',    bg: 'bg-rose-50 dark:bg-rose-500/10',         icon: X },
};

const PRIORITY_MAP: Record<string, { label: string; color: string; dot: string }> = {
    urgent: { label: 'Urgente', color: 'text-rose-600',   dot: 'bg-rose-500' },
    high:   { label: 'Alta',    color: 'text-orange-600', dot: 'bg-orange-500' },
    normal: { label: 'Normal',  color: 'text-[hsl(var(--primary))]',   dot: 'bg-[hsl(var(--primary))]' },
    low:    { label: 'Baja',    color: 'text-slate-400',  dot: 'bg-slate-400' },
};

const MIN_WIDTH = 400;
const DEFAULT_WIDTH = 520;
const MAX_RATIO = 0.88;

let nextId = Date.now();
const uid = () => `tmp_${++nextId}`;

// ─────────────────────────────────────────────────────────────────
// RECURSIVE ACTIVITY ITEM
// ─────────────────────────────────────────────────────────────────
function ActivityItem({
    activity,
    depth = 0,
    onToggle,
    onAddChild,
    onUpdateTitle,
    onDelete,
}: {
    activity: Activity;
    depth?: number;
    onToggle: (id: string) => void;
    onAddChild: (parentId: string) => void;
    onUpdateTitle: (id: string, title: string) => void;
    onDelete: (id: string) => void;
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
                        className="size-5 rounded-full flex items-center justify-center font-semibold text-white shrink-0"
                        style={{ backgroundColor: activity.assignee.color ?? '#6366f1' }}
                    >
                        {activity.assignee.name.charAt(0).toUpperCase()}
                    </div>
                )}

                {/* Add child button */}
                <button
                    onClick={() => { onAddChild(activity.id); setExpanded(true); }}
                    className="size-4 rounded flex items-center justify-center text-slate-300 hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-all"
                    title="Añadir sub-actividad"
                >
                    <Plus size={10} strokeWidth={2.5} />
                </button>

                {/* Delete button */}
                <button
                    onClick={() => onDelete(activity.id)}
                    className="size-4 rounded flex items-center justify-center text-slate-300 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 opacity-0 group-hover:opacity-100 transition-all"
                    title="Eliminar actividad"
                >
                    <X size={10} strokeWidth={2.5} />
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
                                onDelete={onDelete}
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
function toggleActivity(activities: Activity[], id: string): Activity[] {
    return activities.map(a => {
        if (a.id === id) return { ...a, completed: !a.completed };
        if (a.children) return { ...a, children: toggleActivity(a.children, id) };
        return a;
    });
}

function addChild(activities: Activity[], parentId: string, newItem: Activity): Activity[] {
    return activities.map(a => {
        if (a.id === parentId) return { ...a, children: [...(a.children ?? []), newItem] };
        if (a.children) return { ...a, children: addChild(a.children, parentId, newItem) };
        return a;
    });
}

function updateTitle(activities: Activity[], id: string, title: string): Activity[] {
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
    onActivityCreated,
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
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [supplies, setSupplies] = useState<TaskSupplyRecord[]>(task?.supplies ?? []);
    const [newSupplyName, setNewSupplyName] = useState('');
    const [newSupplyQuantity, setNewSupplyQuantity] = useState(1);
    const [creatingSupply, setCreatingSupply] = useState(false);
    const [savingSupplyId, setSavingSupplyId] = useState<number | null>(null);

    // ── Labels / Etiquetas ─────────────────────────────────────────
    const [labels, setLabels]         = useState<string[]>((task as any)?.labels ?? []);
    const [labelPopoverOpen, setLabelPopoverOpen] = useState(false);
    const [newLabelInput, setNewLabelInput] = useState('');
    const labelInputRef = useRef<HTMLInputElement>(null);

    const handleAddLabel = async () => {
        if (!task) return;
        const trimmed = newLabelInput.trim();
        if (!trimmed || labels.includes(trimmed)) { setNewLabelInput(''); return; }
        const nextLabels = [...labels, trimmed];
        setLabels(nextLabels);
        setNewLabelInput('');
        setLabelPopoverOpen(false);
        // Persistir en backend
        try {
            await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}`, {
                method: 'PATCH', token, body: { labels: nextLabels }
            });
        } catch { /* optimistic — ignore */ }
    };

    const handleRemoveLabel = async (label: string) => {
        if (!task) return;
        const nextLabels = labels.filter(l => l !== label);
        setLabels(nextLabels);
        try {
            await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}`, {
                method: 'PATCH', token, body: { labels: nextLabels }
            });
        } catch { /* optimistic */ }
    };

    // ── Activities ────────────────────────────────────────────────
    const [activities, setActivities] = useState<Activity[]>([]);
    const [newActivityTitle, setNewActivityTitle] = useState('');

    const handleToggle = async (id: string) => {
        if (!task || !token) return;
        const findActivity = (items: Activity[], targetId: string): Activity | null => {
            for (const a of items) {
                if (a.id === targetId) return a;
                if (a.children) { const found = findActivity(a.children, targetId); if (found) return found; }
            }
            return null;
        };
        const activity = findActivity(activities, id);
        if (!activity) return;
        const newStatus = activity.completed ? 'todo' : 'completed';
        setActivities(prev => toggleActivity(prev, id));
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/subtasks/${id}`, {
                method: 'PATCH', token, body: { status: newStatus },
            });
        } catch { /* optimistic */ }
    };

    const handleAddChild = async (parentId: string) => {
        if (!task || !token) return;
        try {
            const created = await apiFetch<any>(`/projects/${task.project_id}/tasks/${task.id}/subtasks`, {
                method: 'POST', token, body: { title: 'Nueva sub-actividad', status: 'todo', priority: 'normal', parent_id: parentId },
            });
            const item: Activity = { id: created.id || uid(), title: created.title || 'Nueva sub-actividad', completed: false };
            setActivities(prev => addChild(prev, parentId, item));
            onActivityCreated?.();
        } catch {
            const item: Activity = { id: uid(), title: 'Nueva sub-actividad', completed: false };
            setActivities(prev => addChild(prev, parentId, item));
        }
    };

    const handleUpdateTitle = async (id: string, t: string) => {
        setActivities(prev => updateTitle(prev, id, t));
        if (!task || !token) return;
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/subtasks/${id}`, {
                method: 'PATCH', token, body: { title: t },
            });
        } catch { /* optimistic */ }
    };

    const handleAddTopLevel = async () => {
        if (!newActivityTitle.trim() || !task || !token) return;
        try {
            const created = await apiFetch<any>(`/projects/${task.project_id}/tasks/${task.id}/subtasks`, {
                method: 'POST', token, body: { title: newActivityTitle.trim(), status: 'todo', priority: 'normal' },
            });
            setActivities(prev => [...prev, { id: created.id || uid(), title: newActivityTitle.trim(), completed: false }]);
            onActivityCreated?.();
        } catch {
            setActivities(prev => [...prev, { id: uid(), title: newActivityTitle.trim(), completed: false }]);
        }
        setNewActivityTitle('');
    };

    const handleDeleteActivity = async (activityId: string) => {
        if (!task || !token) return;
        setActivities(prev => {
            const filterOut = (items: Activity[]): Activity[] =>
                items.filter(a => a.id !== activityId).map(a => a.children ? { ...a, children: filterOut(a.children) } : a);
            return filterOut(prev);
        });
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/subtasks/${activityId}`, {
                method: 'DELETE', token,
            });
        } catch { /* optimistic */ }
    };

    // ── Comments ──────────────────────────────────────────────────
    const [comments, setComments] = useState<Comment[]>([]);
    const [commentInput, setCommentInput] = useState('');
    const [sendingComment, setSendingComment] = useState(false);
    const [loadingComments, setLoadingComments] = useState(false);

    const loadComments = useCallback(async () => {
        if (!task || !token) return;
        setLoadingComments(true);
        try {
            const data = await apiFetch<any[]>(`/projects/comments?task_id=${task.id}`, { token });
            if (Array.isArray(data)) {
                setComments(data.map((c: any) => ({
                    id: c.id,
                    author: c.author_name || 'Usuario',
                    text: c.content,
                    timestamp: new Date(c.created_at),
                })));
            }
        } catch { /* ignore */ }
        finally { setLoadingComments(false); }
    }, [task, token]);

    useEffect(() => { loadComments(); }, [loadComments]);

    const handleSendComment = async () => {
        if (!commentInput.trim() || !task || !token) return;
        setSendingComment(true);
        try {
            const created = await apiFetch<any>(`/projects/${task.project_id}/comments`, {
                method: 'POST',
                token,
                body: { content: commentInput.trim(), task_id: task.id },
            });
            setComments(prev => [...prev, {
                id: created.id,
                author: created.author_name || 'Tú',
                text: created.content,
                timestamp: new Date(created.created_at),
            }]);
            onActivityCreated?.();
        } catch {
            // silently fail
        } finally {
            setSendingComment(false);
            setCommentInput('');
        }
    };

    // ── Sync on task change ───────────────────────────────────────
    useEffect(() => {
        if (task) {
            setTitle(task.title ?? '');
            setDesc((task as any).description ?? '');
            // Load activities from task subtasks
            const subs = (task as any).subtasks || [];
            setActivities(subs.map((s: any) => ({
                id: s.id,
                title: s.title,
                completed: s.status === 'completed',
                children: (s.subtasks || []).map((ss: any) => ({
                    id: ss.id,
                    title: ss.title,
                    completed: ss.status === 'completed',
                })),
            })));
            setNewActivityTitle('');
            // Sync labels from task
            setLabels((task as any).labels ?? []);
            setSupplies(task.supplies ?? []);
            setNewSupplyName('');
            setNewSupplyQuantity(1);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
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

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0 || !task || !token) return;
        setUploading(true);
        for (const file of Array.from(files)) {
            try {
                const formData = new FormData();
                formData.append('file', file);
                const updated = await apiFetch<Record<string, unknown>>(`/projects/${task.project_id}/tasks/${task.id}/attachments`, {
                    method: 'POST',
                    token,
                    body: formData,
                });
                onUpdate?.({ ...task, ...(updated || {}) });
                onActivityCreated?.();
            } catch (err) {
                console.error('Error uploading file', err);
            }
        }
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleAddSupply = async () => {
        if (!task || !token || !newSupplyName.trim()) return;
        setCreatingSupply(true);
        try {
            const created = await apiFetch<TaskSupplyRecord>(
                `/projects/${task.project_id}/tasks/${task.id}/supplies`,
                {
                    method: 'POST',
                    token,
                    body: {
                        item_name: newSupplyName.trim(),
                        quantity: Math.max(1, newSupplyQuantity || 1),
                        status: 'pending',
                    },
                }
            );
            const nextSupplies = [...supplies, created];
            setSupplies(nextSupplies);
            onUpdate?.({ ...task, supplies: nextSupplies });
            onActivityCreated?.();
            setNewSupplyName('');
            setNewSupplyQuantity(1);
        } finally {
            setCreatingSupply(false);
        }
    };

    const handleUpdateSupply = async (
        supply: TaskSupplyRecord,
        patch: Partial<Pick<TaskSupplyRecord, 'item_name' | 'quantity' | 'status'>>,
    ) => {
        if (!task || !token) return;
        const optimistic = supplies.map((item) => (
            item.id === supply.id ? { ...item, ...patch } : item
        ));
        setSupplies(optimistic);
        onUpdate?.({ ...task, supplies: optimistic });
        setSavingSupplyId(supply.id);
        try {
            const updated = await apiFetch<TaskSupplyRecord>(
                `/projects/${task.project_id}/tasks/${task.id}/supplies/${supply.id}`,
                {
                    method: 'PATCH',
                    token,
                    body: patch,
                }
            );
            const nextSupplies = optimistic.map((item) => (
                item.id === updated.id ? updated : item
            ));
            setSupplies(nextSupplies);
            onUpdate?.({ ...task, supplies: nextSupplies });
            onActivityCreated?.();
        } finally {
            setSavingSupplyId(null);
        }
    };

    // ── Status / Priority / Assignee handlers ──────────────────────
    const STATUS_CYCLE = ['todo', 'in_progress', 'review', 'completed'];
    const PRIORITY_CYCLE = ['low', 'normal', 'high', 'urgent'];

    const handleStatusCycle = async () => {
        if (!task) return;
        const currentIdx = STATUS_CYCLE.indexOf(task.status || 'todo');
        const nextStatus = STATUS_CYCLE[(currentIdx + 1) % STATUS_CYCLE.length];
        const updated = { ...task, status: nextStatus };
        onUpdate?.(updated);
        try {
            await apiFetch(`/projects/tasks/${task.id}`, {
                method: 'PATCH', token, body: { status: nextStatus },
            });
        } catch { /* optimistic */ }
    };

    const handlePriorityCycle = async () => {
        if (!task) return;
        const currentIdx = PRIORITY_CYCLE.indexOf(task.priority || 'normal');
        const nextPriority = PRIORITY_CYCLE[(currentIdx + 1) % PRIORITY_CYCLE.length];
        const updated = { ...task, priority: nextPriority };
        onUpdate?.(updated);
        try {
            await apiFetch(`/projects/tasks/${task.id}`, {
                method: 'PATCH', token, body: { priority: nextPriority },
            });
        } catch { /* optimistic */ }
    };

    const handleAssigneeChange = async (newAssigneeId: string | null) => {
        if (!task || !token) return;
        const updated = { ...task, assignee_id: newAssigneeId as any };
        onUpdate?.(updated);
        try {
            await apiFetch(`/projects/tasks/${task.id}`, {
                method: 'PATCH', token, body: { assignee_id: newAssigneeId },
            });
        } catch { /* optimistic */ }
    };

    const handleDeleteTask = async () => {
        if (!task || !token) return;
        onDelete?.(task.id);
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}`, {
                method: 'DELETE', token,
            });
        } catch { /* ignore */ }
        onClose();
    };

    if (!task) return null;

    const status   = STATUS_MAP[task.status ?? 'todo'] ?? STATUS_MAP.todo;
    const priority = PRIORITY_MAP[task.priority ?? 'normal'] ?? PRIORITY_MAP.normal;
    const StatusIcon = status.icon;
    const attachments = task.attachments ?? [];

    return (
        <AnimatePresence>
            <motion.aside
                key="task-detail-panel"
                initial={{ x: width, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: width, opacity: 0 }}
                transition={{ type: 'spring', damping: 32, stiffness: 300 }}
                style={{ width, minWidth: MIN_WIDTH }}
                className="relative h-full flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] border-l border-slate-100 dark:border-white/[0.07] shadow-[-16px_0_48px_rgba(0,0,0,0.08)] dark:shadow-[-16px_0_48px_rgba(0,0,0,0.35)] overflow-hidden"
            >
                {/* ── RESIZE HANDLE ──────────────────────────────── */}
                <div
                    onMouseDown={onMouseDown}
                    className="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize z-10 group flex items-center justify-center"
                    title="Arrastrar para redimensionar"
                >
                    <div className="w-[3px] h-8 rounded-full bg-slate-200 dark:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
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
                                className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10 hover:bg-blue-100 dark:hover:bg-blue-500/20 transition-all border border-blue-200/50 dark:border-blue-500/20"
                            >
                                <GitBranch size={11} />
                                Ver Ruta
                            </button>

                            {/* Attach */}
                            <button
                                onClick={() => fileInputRef.current?.click()}
                                disabled={uploading}
                                title={uploading ? "Subiendo archivo" : "Adjuntar archivo"}
                                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-all disabled:cursor-wait disabled:opacity-60"
                            >
                                {uploading ? <Loader2 size={14} className="animate-spin" /> : <Paperclip size={14} />}
                            </button>
                            <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileUpload} />

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
                                onClick={handleDeleteTask}
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
                        <button
                            onClick={handleStatusCycle}
                            title="Click para cambiar estado"
                            className={clsx(
                            'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold border border-current/15 transition-all hover:border-current/30 cursor-pointer',
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
                        className="w-full text-sm font-bold text-slate-900 dark:text-white bg-transparent resize-none outline-none leading-snug placeholder:text-slate-300 dark:placeholder:text-slate-600 pb-3"
                        placeholder="Nombre de la tarea..."
                        style={{ minHeight: 28 }}
                        onInput={e => {
                            const t = e.currentTarget;
                            t.style.height = 'auto';
                            t.style.height = t.scrollHeight + 'px';
                        }}
                    />
                    {saving && (
                        <p className="pb-3 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                            Guardando cambios...
                        </p>
                    )}
                </header>

                {/* ── BODY (scrollable) ──────────────────────────── */}
                <div className="flex-1 overflow-y-auto scrollbar-thin">

                    {/* ─ META FIELDS ─ */}
                    <section className="px-4 py-3 border-b border-slate-100 dark:border-white/[0.05] space-y-2">

                        <MetaRow icon={<UserRound size={13} className="text-slate-400" />} label="Persona asignada">
                            <UserSelect
                                value={task.assignee_id ?? null}
                                onChange={handleAssigneeChange}
                                placeholder="Sin asignar"
                                className="min-w-[180px]"
                            />
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
                            <button
                                onClick={handlePriorityCycle}
                                title="Click para cambiar prioridad"
                                className={clsx('flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12px] font-bold border border-transparent hover:border-slate-200 dark:hover:border-white/[0.08] transition-all cursor-pointer', priority.color)}>
                                <span className={clsx('size-2 rounded-full', priority.dot)} />
                                {priority.label}
                            </button>
                        </MetaRow>

                        <MetaRow icon={<Tag size={13} className="text-slate-400" />} label="Etiquetas">
                            <div className="flex flex-wrap items-center gap-1.5 relative">
                                {/* Chips de etiquetas activas */}
                                {labels.map(label => {
                                    const c = getLabelColor(label);
                                    return (
                                        <span key={label} className={clsx(
                                            'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border',
                                            c.bg, c.text, c.border
                                        )}>
                                            <span className={clsx('size-1.5 rounded-full', c.dot)} />
                                            {label}
                                            <button
                                                onClick={() => handleRemoveLabel(label)}
                                                className="ml-0.5 opacity-60 hover:opacity-100 transition-opacity"
                                                title={`Quitar etiqueta "${label}"`}
                                            >
                                                <X size={9} strokeWidth={3} />
                                            </button>
                                        </span>
                                    );
                                })}

                                {/* Botón añadir + popover inline */}
                                <div className="relative">
                                    <button
                                        onClick={() => { setLabelPopoverOpen(v => !v); setTimeout(() => labelInputRef.current?.focus(), 50); }}
                                        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-slate-400 hover:bg-slate-50 dark:hover:bg-white/[0.04] border border-dashed border-slate-300 dark:border-white/[0.1] transition-all"
                                    >
                                        <Plus size={10} /> Añadir etiqueta
                                    </button>

                                    <AnimatePresence>
                                        {labelPopoverOpen && (
                                            <motion.div
                                                initial={{ opacity: 0, scale: 0.95, y: -4 }}
                                                animate={{ opacity: 1, scale: 1, y: 0 }}
                                                exit={{ opacity: 0, scale: 0.95, y: -4 }}
                                                transition={{ duration: 0.12 }}
                                                className="absolute top-full left-0 mt-1.5 z-50 w-56 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-2xl p-3 space-y-2"
                                            >
                                                <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-1">Nueva etiqueta</p>
                                                <div className="flex gap-1.5">
                                                    <input
                                                        ref={labelInputRef}
                                                        type="text"
                                                        value={newLabelInput}
                                                        onChange={e => setNewLabelInput(e.target.value)}
                                                        onKeyDown={e => {
                                                            if (e.key === 'Enter') handleAddLabel();
                                                            if (e.key === 'Escape') { setLabelPopoverOpen(false); setNewLabelInput(''); }
                                                        }}
                                                        placeholder="Ej: Alabanza, Urgente..."
                                                        className="flex-1 text-[12px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-2 py-1.5 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
                                                    />
                                                    <button
                                                        onClick={handleAddLabel}
                                                        disabled={!newLabelInput.trim()}
                                                        className="px-2.5 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold hover:bg-[hsl(var(--primary))] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                                    >
                                                        <Check size={11} strokeWidth={3} />
                                                    </button>
                                                </div>
                                                {/* Sugerencias predefinidas */}
                                                <div className="flex flex-wrap gap-1 pt-1 border-t border-slate-100 dark:border-white/5">
                                                    {['Alabanza', 'Urgente', 'Reunión', 'Pastoral', 'Admin', 'Diseño'].filter(s => !labels.includes(s)).map(s => (
                                                        <button
                                                            key={s}
                                                            onClick={() => { setNewLabelInput(s); labelInputRef.current?.focus(); }}
                                                            className={clsx('px-2 py-0.5 rounded-full text-[10px] font-bold border transition-all hover:scale-105', getLabelColor(s).bg, getLabelColor(s).text, getLabelColor(s).border)}
                                                        >
                                                            {s}
                                                        </button>
                                                    ))}
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>

                                {/* Overlay para cerrar el popover */}
                                {labelPopoverOpen && (
                                    <div className="fixed inset-0 z-40" onClick={() => { setLabelPopoverOpen(false); setNewLabelInput(''); }} />
                                )}
                            </div>
                        </MetaRow>
                    </section>

                    {/* ─ DESCRIPTION ─ */}
                    <section className="px-4 py-3 border-b border-slate-100 dark:border-white/[0.05]">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
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

                    {/* ─ ARCHIVOS ─ */}
                    <section className="px-4 py-3 border-b border-slate-100 dark:border-white/[0.05]">
                        <div className="mb-3 flex items-center justify-between">
                            <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                <Paperclip size={11} /> Archivos
                                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[9px] font-bold text-slate-500 dark:bg-white/[0.06] dark:text-slate-400">
                                    {attachments.length}
                                </span>
                            </p>
                        </div>

                        {attachments.length === 0 ? (
                            <p className="text-[11px] italic text-slate-300 dark:text-slate-600">
                                Sin archivos adjuntos aun.
                            </p>
                        ) : (
                            <div className="space-y-2">
                                {attachments.map((attachment) => (
                                    <a
                                        key={attachment.id}
                                        href={attachment.file_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="flex items-center justify-between gap-3 rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-left transition hover:border-blue-200 hover:bg-blue-50/60 dark:border-white/[0.06] dark:bg-white/[0.03] dark:hover:border-blue-500/30 dark:hover:bg-blue-500/10"
                                    >
                                        <div className="min-w-0">
                                            <p className="truncate text-[12px] font-bold text-slate-700 dark:text-slate-200">
                                                {attachment.filename}
                                            </p>
                                            <p className="text-[10px] text-slate-400">
                                                {attachment.file_size ? `${Math.max(1, Math.round(attachment.file_size / 1024))} KB` : 'Archivo adjunto'}
                                            </p>
                                        </div>
                                        <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">
                                            Abrir
                                        </span>
                                    </a>
                                ))}
                            </div>
                        )}
                    </section>

                    {/* ─ ACTIVIDADES ─ */}
                    <section className="px-4 py-3 border-b border-slate-100 dark:border-white/[0.05]">
                        <div className="mb-3 flex items-center justify-between">
                            <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                                <Boxes size={11} /> Insumos
                                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[9px] font-bold text-slate-500 dark:bg-white/[0.06] dark:text-slate-400">
                                    {supplies.length}
                                </span>
                            </p>
                        </div>

                        <div className="space-y-2">
                            {supplies.length === 0 && (
                                <p className="text-[11px] italic text-slate-300 dark:text-slate-600">
                                    Sin insumos registrados.
                                </p>
                            )}

                            {supplies.map((supply) => (
                                <div
                                    key={supply.id}
                                    className="grid grid-cols-[minmax(0,1fr)_72px_110px] items-center gap-2 rounded-md border border-slate-100 bg-slate-50 px-3 py-2 dark:border-white/[0.06] dark:bg-white/[0.03]"
                                >
                                    <input
                                        value={supply.item_name}
                                        onChange={(event) => setSupplies((prev) => prev.map((item) => (
                                            item.id === supply.id ? { ...item, item_name: event.target.value } : item
                                        )))}
                                        onBlur={(event) => {
                                            const value = event.target.value.trim();
                                            const original = task.supplies?.find((item) => item.id === supply.id);
                                            if (value && value !== original?.item_name) {
                                                handleUpdateSupply(supply, { item_name: value });
                                            }
                                        }}
                                        className="min-w-0 bg-transparent text-[12px] font-bold text-slate-700 outline-none dark:text-slate-200"
                                    />
                                    <input
                                        type="number"
                                        min={1}
                                        value={supply.quantity}
                                        onChange={(event) => {
                                            const quantity = Math.max(1, Number(event.target.value) || 1);
                                            setSupplies((prev) => prev.map((item) => (
                                                item.id === supply.id ? { ...item, quantity } : item
                                            )));
                                        }}
                                        onBlur={(event) => {
                                            const quantity = Math.max(1, Number(event.target.value) || 1);
                                            const original = task.supplies?.find((item) => item.id === supply.id);
                                            if (quantity !== original?.quantity) {
                                                handleUpdateSupply(supply, { quantity });
                                            }
                                        }}
                                        className="rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-[11px] font-bold outline-none dark:border-white/10 dark:bg-white/5"
                                    />
                                    <select
                                        value={supply.status}
                                        disabled={savingSupplyId === supply.id}
                                        onChange={(event) => handleUpdateSupply(supply, { status: event.target.value })}
                                        className="rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-[11px] font-bold outline-none dark:border-white/10 dark:bg-white/5"
                                    >
                                        <option value="pending">Pendiente</option>
                                        <option value="ready">Listo</option>
                                        <option value="unavailable">No disponible</option>
                                    </select>
                                </div>
                            ))}
                        </div>

                        <div className="mt-3 grid grid-cols-[minmax(0,1fr)_72px_auto] gap-2">
                            <input
                                value={newSupplyName}
                                onChange={(event) => setNewSupplyName(event.target.value)}
                                onKeyDown={(event) => event.key === 'Enter' && handleAddSupply()}
                                placeholder="Nuevo insumo"
                                className="min-w-0 rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] px-3 py-2 text-[12px] font-medium outline-none dark:border-white/10 dark:bg-white/5"
                            />
                            <input
                                type="number"
                                min={1}
                                value={newSupplyQuantity}
                                onChange={(event) => setNewSupplyQuantity(Math.max(1, Number(event.target.value) || 1))}
                                className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] px-2 py-2 text-[12px] font-bold outline-none dark:border-white/10 dark:bg-white/5"
                            />
                            <button
                                onClick={handleAddSupply}
                                disabled={creatingSupply || !newSupplyName.trim()}
                                className="rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white disabled:opacity-50"
                            >
                                {creatingSupply ? '...' : 'Agregar'}
                            </button>
                        </div>
                    </section>

                    <section className="px-4 py-3 border-b border-slate-100 dark:border-white/[0.05]">
                        <div className="flex items-center justify-between mb-3">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
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
                                    onDelete={handleDeleteActivity}
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
                                    className="px-2 py-1 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold hover:bg-[hsl(var(--primary))] transition-all"
                                >
                                    + Añadir
                                </button>
                            )}
                        </div>
                    </section>

                    {/* ─ COMENTARIOS ─ */}
                    <section className="px-4 py-3">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
                            <MessageSquare size={11} /> Actividad
                        </p>

                        {/* Comment list */}
                        <div className="space-y-3 mb-4">
                            {loadingComments && (
                                <p className="text-[11px] text-slate-300 dark:text-slate-600 italic text-center py-2">
                                    Cargando actividad...
                                </p>
                            )}
                            {!loadingComments && comments.length === 0 && (
                                <p className="text-[11px] text-slate-300 dark:text-slate-600 italic text-center py-2">
                                    Sin comentarios aún. Menciona a alguien con @
                                </p>
                            )}
                            {comments.map(c => (
                                <div key={c.id} className="flex gap-2.5">
                                    <div
                                        className="size-6 rounded-full flex items-center justify-center font-semibold text-white shrink-0 mt-0.5"
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
                            <div className="size-6 rounded-full bg-[hsl(var(--primary))] flex items-center justify-center font-semibold text-white shrink-0">
                                T
                            </div>
                            <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-md bg-slate-50 dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.07] focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-400/40 transition-all">
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
                                        className="text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors"
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
                            <button className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10 border border-blue-200/50 dark:border-blue-500/20">
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

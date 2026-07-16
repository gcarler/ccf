"use client";

import PersonaSelect from '@/components/ui/PersonaSelect';
import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/ConfirmActionDrawer';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import {
    PRIORITY_CYCLE,
    STATUS_CYCLE,
    PRIORITY_LABELS,
    STATUS_LABELS,
    getValidStatus,
    getValidPriority,
} from '@/lib/projects/constants';
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
ChevronRight,    Circle,
    Eye,
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
import { toast } from "sonner";

// Paleta de colores para etiquetas
const LABEL_COLORS = [
    { bg: 'bg-rose-100 dark:bg-rose-900/30',   text: 'text-rose-700 dark:text-rose-300',   border: 'border-rose-300/50 dark:border-rose-500/30',   dot: 'bg-rose-500' },
    { bg: 'bg-orange-100 dark:bg-orange-900/30', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-300/50 dark:border-orange-500/30', dot: 'bg-orange-500' },
    { bg: 'bg-amber-100 dark:bg-amber-900/30',  text: 'text-amber-700 dark:text-amber-300',  border: 'border-amber-300/50 dark:border-amber-500/30',  dot: 'bg-amber-500' },
    { bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-300/50 dark:border-emerald-500/30', dot: 'bg-emerald-500' },
    { bg: 'bg-blue-100 dark:bg-blue-900/30',   text: 'text-[hsl(var(--primary))] dark:text-blue-300',   border: 'border-blue-300/50 dark:border-blue-500/30',   dot: 'bg-[hsl(var(--primary))]' },
    { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-[hsl(var(--primary))] dark:text-blue-300', border: 'border-blue-300/50 dark:border-blue-500/30', dot: 'bg-[hsl(var(--primary))]' },
    { bg: 'bg-pink-100 dark:bg-pink-900/30',   text: 'text-pink-700 dark:text-pink-300',   border: 'border-pink-300/50 dark:border-pink-500/30',   dot: 'bg-pink-500' },
    { bg: 'bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--surface-2))]/60', text: 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]', border: 'border-[hsl(var(--border))]/50 dark:border-[hsl(var(--border))]/30', dot: 'bg-[hsl(var(--surface-2))]' },
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
    id: string;
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
    todo:        { label: STATUS_LABELS.todo,        color: 'text-[hsl(var(--text-secondary))]',   bg: 'bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--surface-2))]/60',      icon: Circle },
    in_progress: { label: STATUS_LABELS.in_progress, color: 'text-[hsl(var(--primary))]',    bg: 'bg-blue-50 dark:bg-blue-500/10',         icon: Loader2 },
    review:      { label: STATUS_LABELS.review,      color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-500/10',       icon: Eye },
    completed:   { label: STATUS_LABELS.completed,   color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10',   icon: CheckCircle2 },
};

const PRIORITY_MAP: Record<string, { label: string; color: string; dot: string }> = {
    urgent: { label: PRIORITY_LABELS.urgent, color: 'text-rose-600',   dot: 'bg-rose-500' },
    high:   { label: PRIORITY_LABELS.high,   color: 'text-orange-600', dot: 'bg-orange-500' },
    medium: { label: PRIORITY_LABELS.medium, color: 'text-[hsl(var(--primary))]',   dot: 'bg-[hsl(var(--primary))]' },
    low:    { label: PRIORITY_LABELS.low,    color: 'text-slate-700 dark:text-slate-400',  dot: 'bg-slate-500' },
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
                    'group flex items-center gap-1.5 py-1.5 px-2 rounded-lg transition-colors hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.04] relative',
                )}
                style={{ paddingLeft: depth * 20 + 8 }}
            >
                {/* Indent guide lines */}
                {depth > 0 && (
                    <div
                        className="absolute left-0 top-0 bottom-0 w-px bg-[hsl(var(--surface-3))] dark:bg-white/[0.08]"
                        style={{ left: depth * 20 - 4 }}
                    />
                )}

                {/* Expand toggle */}
                <button
                    onClick={() => setExpanded(v => !v)}
                    className={clsx(
                        'size-4 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-colors shrink-0',
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
                            : 'border-[hsl(var(--border))] dark:border-[hsl(var(--border))] hover:border-blue-400'
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
                        className="flex-1 text-[12px] bg-transparent outline-none border-b border-blue-400 text-[hsl(var(--text-primary))] dark:text-white"
                    />
                ) : (
                    <span
                        onDoubleClick={() => setEditing(true)}
                        className={clsx(
                            'flex-1 text-[12px] font-medium cursor-default select-none truncate',
                            activity.completed
                                ? 'line-through text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]'
                                : 'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]'
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
                        style={{ backgroundColor: activity.assignee.color ?? 'hsl(var(--primary))' }}
                    >
                        {activity.assignee.name.charAt(0).toUpperCase()}
                    </div>
                )}

                {/* Add child button */}
                <button
                    onClick={() => { onAddChild(activity.id); setExpanded(true); }}
                    className="size-4 rounded flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-all"
                    title="Añadir sub-actividad"
                >
                    <Plus size={10} strokeWidth={2.5} />
                </button>

                {/* Delete button */}
                <button
                    onClick={() => onDelete(activity.id)}
                    className="size-4 rounded flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 opacity-0 group-hover:opacity-100 transition-all"
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
    const { token, loading: authLoading } = useAuth();

    // ── Width / resize state ──────────────────────────────────────
    const [width, setWidth] = useState<number>(() => {
        if (typeof window === 'undefined') return DEFAULT_WIDTH;
        return Number(localStorage.getItem('taskDetailPanelWidth') || DEFAULT_WIDTH);
    });
    const resizing = useRef(false);
    const startX   = useRef(0);
    const startW   = useRef(0);
    // Mirror of the latest ``width`` value. The drag listeners are attached
    // once at mousedown, so their ``onUp``/``onMove`` closures cannot rely on
    // React state directly — they read the most current width from this ref.
    const widthRef = useRef<number>(width);
    useEffect(() => { widthRef.current = width; }, [width]);

    /**
     * Resize handle: attach ``mousemove``/``mouseup`` listeners directly
     * inside ``onMouseDown`` (one attachment per drag) and tear them down
     * inside the same handlers. This avoids the previous
     * ``useEffect([width])`` churn that re-bound document listeners on every
     * state update during a drag, AND the stale-closure bug that persisted
     * the pre-drag width to ``localStorage`` instead of the dragged-to value.
     */
    const onMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        resizing.current = true;
        startX.current = e.clientX;
        // Use the ref so the starting width is the freshest value (not a stale
        // snapshot of the React state captured by this useCallback at mount).
        startW.current = widthRef.current;
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';

        const onMove = (moveEvt: MouseEvent) => {
            if (!resizing.current) return;
            const delta = startX.current - moveEvt.clientX; // dragging left = wider
            const maxW  = window.innerWidth * MAX_RATIO;
            const newW  = Math.min(maxW, Math.max(MIN_WIDTH, startW.current + delta));
            widthRef.current = newW;
            setWidth(newW);
        };
        const onUp = () => {
            if (resizing.current) {
                resizing.current = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                // Persist the FINAL width from the ref, not the pre-drag value.
                localStorage.setItem('taskDetailPanelWidth', String(widthRef.current));
            }
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
        // Safety net: if the user releases outside the window or switches tabs,
        // ``mouseup`` is never received and listeners leak. ``blur`` (once)
        // flushes the same teardown.
        const onBlur = () => onUp();
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        window.addEventListener('blur', onBlur, { once: true });
    }, []);

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
    // ``supply.id`` is a UUID string from types/projects.ts; tracking which
    // row is currently saving needs the matching ``string | null`` shape.
    // ``null`` is the "no row saving" sentinel state.
    const [savingSupplyId, setSavingSupplyId] = useState<string | null>(null);
    const [deletingSupplyId, setDeletingSupplyId] = useState<string | null>(null);
    const [deletingAttachmentId, setDeletingAttachmentId] = useState<string | null>(null);
    const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
    const [error, setError] = useState<string | null>(null);

    const requireAuth = useCallback((message: string) => {
        if (authLoading) return false;
        if (!token) {
            setError(message);
            return false;
        }
        return true;
    }, [authLoading, token]);

    // ── Labels / Etiquetas ─────────────────────────────────────────
    const [labels, setLabels]         = useState<string[]>(task?.labels ?? []);
    const [labelPopoverOpen, setLabelPopoverOpen] = useState(false);
    const [newLabelInput, setNewLabelInput] = useState('');
    const labelInputRef = useRef<HTMLInputElement>(null);

    const handleAddLabel = async () => {
        if (!task) return;
        if (!requireAuth('Debes iniciar sesión para actualizar etiquetas.')) return;
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
        if (!requireAuth('Debes iniciar sesión para actualizar etiquetas.')) return;
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
        if (!task || !requireAuth('Debes iniciar sesión para actualizar sub-actividades.')) return;
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
        } catch {
            setError('No se pudo actualizar la sub-actividad.');
        }
    };

    const handleAddChild = async (parentId: string) => {
        if (!task || !requireAuth('Debes iniciar sesión para crear sub-actividades.')) return;
        try {
            const created = await apiFetch<any>(`/projects/${task.project_id}/tasks/${task.id}/subtasks`, {
                method: 'POST', token, body: { title: 'Nueva sub-actividad', status: 'todo', priority: 'medium', parent_id: parentId },
            });
            const item: Activity = { id: created.id || uid(), title: created.title || 'Nueva sub-actividad', completed: false };
            setActivities(prev => addChild(prev, parentId, item));
            onActivityCreated?.();
        } catch {
            setError('No se pudo crear la sub-actividad.');
        }
    };

    const handleUpdateTitle = async (id: string, t: string) => {
        setActivities(prev => updateTitle(prev, id, t));
        if (!task || !requireAuth('Debes iniciar sesión para actualizar sub-actividades.')) return;
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/subtasks/${id}`, {
                method: 'PATCH', token, body: { title: t },
            });
        } catch {
            setError('No se pudo actualizar la sub-actividad.');
        }
    };

    const handleAddTopLevel = async () => {
        if (!newActivityTitle.trim() || !task || !requireAuth('Debes iniciar sesión para crear actividades.')) return;
        try {
            const created = await apiFetch<any>(`/projects/${task.project_id}/tasks/${task.id}/subtasks`, {
                method: 'POST', token, body: { title: newActivityTitle.trim(), status: 'todo', priority: 'medium' },
            });
            setActivities(prev => [...prev, { id: created.id || uid(), title: newActivityTitle.trim(), completed: false }]);
            onActivityCreated?.();
        } catch {
            setError('No se pudo crear la actividad.');
        }
        setNewActivityTitle('');
    };

    const handleDeleteActivity = async (activityId: string) => {
        if (!task || !requireAuth('Debes iniciar sesión para eliminar actividades.')) return;
        setActivities(prev => {
            const filterOut = (items: Activity[]): Activity[] =>
                items.filter(a => a.id !== activityId).map(a => a.children ? { ...a, children: filterOut(a.children) } : a);
            return filterOut(prev);
        });
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/subtasks/${activityId}`, {
                method: 'DELETE', token,
            });
        } catch {
            setError('No se pudo eliminar la actividad.');
        }
    };

    // ── Comments ──────────────────────────────────────────────────
    const [comments, setComments] = useState<Comment[]>([]);
    const [commentInput, setCommentInput] = useState('');
    const [sendingComment, setSendingComment] = useState(false);
    const [loadingComments, setLoadingComments] = useState(false);

    const loadComments = useCallback(async () => {
        if (!task || !requireAuth('Debes iniciar sesión para ver comentarios de la tarea.')) return;
        setLoadingComments(true);
        setError(null);
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
        } catch {
            setError('No se pudieron cargar los comentarios de la tarea.');
        }
        finally { setLoadingComments(false); }
    }, [task, token, requireAuth]);

    useEffect(() => { loadComments(); }, [loadComments]);

    const handleSendComment = async () => {
        if (!commentInput.trim() || !task || !requireAuth('Debes iniciar sesión para comentar la tarea.')) return;
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
            setError('No se pudo enviar el comentario.');
        } finally {
            setSendingComment(false);
            setCommentInput('');
        }
    };

    // ── Sync on task change ───────────────────────────────────────
    useEffect(() => {
        if (task) {
            setTitle(task.title ?? '');
            setDesc(task.description ?? '');
            // Load activities from task subtasks
            const subs = task.subtasks || [];
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
            setLabels(task.labels ?? []);
            setSupplies(task.supplies ?? []);
            setNewSupplyName('');
            setNewSupplyQuantity(1);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [task?.id]);

    // ── Save ──────────────────────────────────────────────────────
    const handleSave = async () => {
        if (!task || !requireAuth('Debes iniciar sesión para guardar cambios de la tarea.')) return;
        setSaving(true);
        try {
            const updated = await apiFetch<ProjectTaskRecord>(
                `/projects/${task.project_id}/tasks/${task.id}`,
                { method: 'PATCH', token, body: { title, description } }
            );
            onUpdate?.({ ...task, ...updated });
        } catch {
            setError('No se pudieron guardar los cambios de la tarea.');
            onUpdate?.({ ...task, title, description });
        } finally {
            setSaving(false);
        }
    };

    // ── File attach ───────────────────────────────────────────────
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0 || !task || !requireAuth('Debes iniciar sesión para adjuntar archivos.')) return;

        // NOTE: Nginx requires `client_max_body_size 10M;` in the site config
        // (e.g. /etc/nginx/sites-available/elfarocc.tech) to match this limit.
        const MAX_MB = 10;
        const MAX_BYTES = MAX_MB * 1024 * 1024;

        for (const file of Array.from(files)) {
            if (file.size > MAX_BYTES) {
                // eslint-disable-next-line no-alert
                alert(`Error: El archivo "${file.name}" supera el límite de ${MAX_MB}MB.`);
                if (fileInputRef.current) fileInputRef.current.value = '';
                return;
            }
        }

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
                toast.error('Error al subir archivo');
                setError('No se pudo subir uno de los archivos adjuntos.');
            }
        }
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleAddSupply = async () => {
        if (!task || !requireAuth('Debes iniciar sesión para crear insumos.')) return;
        if (!newSupplyName.trim()) return;
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
        } catch {
            setError('No se pudo crear el insumo.');
        } finally {
            setCreatingSupply(false);
        }
    };

    const handleUpdateSupply = async (
        supply: TaskSupplyRecord,
        patch: Partial<Pick<TaskSupplyRecord, 'item_name' | 'quantity' | 'status'>>,
    ) => {
        if (!task || !requireAuth('Debes iniciar sesión para actualizar insumos.')) return;
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
        } catch {
            setError('No se pudo actualizar el insumo.');
        } finally {
            setSavingSupplyId(null);
        }
    };

    // ── Status / Priority / Assignee handlers ──────────────────────
    const handleStatusCycle = async () => {
        if (!task || !requireAuth('Debes iniciar sesión para cambiar el estado de la tarea.')) return;
        const currentIdx = STATUS_CYCLE.indexOf(getValidStatus(task.status));
        const nextStatus = STATUS_CYCLE[(currentIdx + 1) % STATUS_CYCLE.length];
        const updated = { ...task, status: nextStatus };
        onUpdate?.(updated);
        try {
            await apiFetch(`/projects/tasks/${task.id}`, {
                method: 'PATCH', token, body: { status: nextStatus },
            });
        } catch {
            setError('No se pudo actualizar el estado de la tarea.');
        }
    };

    const handlePriorityCycle = async () => {
        if (!task || !requireAuth('Debes iniciar sesión para cambiar la prioridad de la tarea.')) return;
        const currentIdx = PRIORITY_CYCLE.indexOf(getValidPriority(task.priority));
        const nextPriority = PRIORITY_CYCLE[(currentIdx + 1) % PRIORITY_CYCLE.length];
        const updated = { ...task, priority: nextPriority };
        onUpdate?.(updated);
        try {
            await apiFetch(`/projects/tasks/${task.id}`, {
                method: 'PATCH', token, body: { priority: nextPriority },
            });
        } catch {
            setError('No se pudo actualizar la prioridad de la tarea.');
        }
    };

    const handleAssigneeChange = async (newAssigneeId: string | null) => {
        if (!task || !requireAuth('Debes iniciar sesión para reasignar la tarea.')) return;
        const updated = { ...task, assignee_id: newAssigneeId };
        onUpdate?.(updated);
        try {
            await apiFetch(`/projects/tasks/${task.id}`, {
                method: 'PATCH', token, body: { assignee_id: newAssigneeId },
            });
        } catch {
            setError('No se pudo reasignar la tarea.');
        }
    };

    const handleDeleteTask = async () => {
        if (!task || !requireAuth('Debes iniciar sesión para eliminar la tarea.')) return;
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}`, {
                method: 'DELETE', token,
            });
            onDelete?.(task.id);
            onClose();
        } catch {
            setError('No se pudo eliminar la tarea.');
        }
    };

    const handleDeleteComment = async (commentId: string) => {
        if (!task || !requireAuth('Debes iniciar sesión para eliminar comentarios.')) return;
        setConfirmAction({
            title: 'Eliminar comentario',
            description: '¿Estás seguro de que deseas eliminar este comentario? Esta acción no se puede deshacer.',
            destructive: true,
            confirmLabel: 'Eliminar',
            onConfirm: async () => {
                try {
                    await apiFetch(`/projects/comments/${commentId}`, { method: 'DELETE', token });
                    setComments(prev => prev.filter(c => c.id !== commentId));
                    onActivityCreated?.();
                } catch {
                    setError('No se pudo eliminar el comentario.');
                }
                setConfirmAction(null);
            },
        });
    };

    const handleDeleteSupply = async (supplyId: string) => {
        if (!task || !requireAuth('Debes iniciar sesión para eliminar insumos.')) return;
        setDeletingSupplyId(supplyId);
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/supplies/${supplyId}`, {
                method: 'DELETE', token,
            });
            const nextSupplies = supplies.filter(s => s.id !== supplyId);
            setSupplies(nextSupplies);
            onUpdate?.({ ...task, supplies: nextSupplies });
            onActivityCreated?.();
        } catch {
            setError('No se pudo eliminar el insumo.');
        }
        finally { setDeletingSupplyId(null); }
    };

    const handleDeleteAttachment = async (attachmentId: string) => {
        if (!task || !requireAuth('Debes iniciar sesión para eliminar archivos adjuntos.')) return;
        setDeletingAttachmentId(attachmentId);
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/attachments/${attachmentId}`, {
                method: 'DELETE', token,
            });
            const nextAttachments = (task.attachments ?? []).filter(a => a.id !== attachmentId);
            onUpdate?.({ ...task, attachments: nextAttachments });
            onActivityCreated?.();
        } catch {
            setError('No se pudo eliminar el archivo adjunto.');
        }
        finally { setDeletingAttachmentId(null); }
    };

    if (!task) return null;
    if (authLoading) return null;

    const status   = STATUS_MAP[task.status ?? 'todo'] ?? STATUS_MAP.todo;
    const priority = PRIORITY_MAP[task.priority ?? 'medium'] ?? PRIORITY_MAP.medium;
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
                role="complementary"
                aria-label="Detalle de tarea"
                className="relative h-full flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] border-l border-[hsl(var(--border))] dark:border-white/[0.07] shadow-[-16px_0_48px_rgba(0,0,0,0.08)] dark:shadow-[-16px_0_48px_rgba(0,0,0,0.35)] overflow-hidden"
            >
                {/* ── RESIZE HANDLE ──────────────────────────────── */}
                <div
                    onMouseDown={onMouseDown}
                    className="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize z-10 group flex items-center justify-center"
                    title="Arrastrar para redimensionar"
                >
                    <div className="w-[3px] h-8 rounded-full bg-[hsl(var(--surface-3))] dark:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>

                {/* ── HEADER ─────────────────────────────────────── */}
                <header className="shrink-0 px-4 pt-3 pb-0 border-b border-[hsl(var(--border))] dark:border-white/[0.06]">
                    {error && (
                        <div className="mb-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
                            <p className="text-[10px] font-bold uppercase tracking-wide">{error}</p>
                        </div>
                    )}
                    {/* Row 1: breadcrumbs + tools */}
                    <div className="flex items-center justify-between mb-2">
                        {/* Breadcrumbs */}
                        <div className="flex items-center gap-1 text-[11px] text-[hsl(var(--text-secondary))] min-w-0">
                            <Home size={11} className="shrink-0" />
                            <ChevronRight size={10} className="text-[hsl(var(--text-secondary))] shrink-0" />
                            <FolderOpen size={11} className="shrink-0" />
                            <span className="truncate max-w-[100px] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] cursor-pointer transition-colors">
                                {projectTitle}
                            </span>
                            <ChevronRight size={10} className="text-[hsl(var(--text-secondary))] shrink-0" />
                            <span className="font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] truncate max-w-[120px]">
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
                                className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all disabled:cursor-wait disabled:opacity-60"
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
                                        : 'text-[hsl(var(--text-secondary))] hover:text-amber-400 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5'
                                )}
                            >
                                <Star size={14} fill={starred ? 'currentColor' : 'none'} />
                            </button>

                            {/* Expand (fullscreen placeholder) */}
                            <button
                                title="Expandir a pantalla completa"
                                className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all"
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
                                className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-all"
                            >
                                <Trash2 size={14} />
                            </button>

                            {/* Close */}
                            <button
                                onClick={onClose}
                                title="Cerrar panel"
                                className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all ml-0.5"
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
                        className="w-full text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white bg-transparent resize-none outline-none leading-snug placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] pb-3"
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
                    <section className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.05] space-y-2">

                        <MetaRow icon={<UserRound size={13} className="text-[hsl(var(--text-secondary))]" />} label="Persona asignada">
                            <PersonaSelect
                                value={task.assignee_id ?? null}
                                onChange={handleAssigneeChange}
                                placeholder="Sin asignar"
                                className="min-w-[180px]"
                            />
                        </MetaRow>

                        <MetaRow icon={<CalendarDays size={13} className="text-[hsl(var(--text-secondary))]" />} label="Fecha límite">
                            <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[12px] font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.04] border border-transparent hover:border-[hsl(var(--border))] dark:hover:border-white/[0.08] transition-all">
                                {task.due_date
                                    ? new Date(task.due_date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
                                    : 'Sin fecha límite'
                                }
                            </button>
                        </MetaRow>

                        <MetaRow icon={<Flag size={13} className="text-[hsl(var(--text-secondary))]" />} label="Prioridad">
                            <button
                                onClick={handlePriorityCycle}
                                title="Click para cambiar prioridad"
                                className={clsx('flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12px] font-bold border border-transparent hover:border-[hsl(var(--border))] dark:hover:border-white/[0.08] transition-all cursor-pointer', priority.color)}>
                                <span className={clsx('size-2 rounded-full', priority.dot)} />
                                {priority.label}
                            </button>
                        </MetaRow>

                        <MetaRow icon={<Tag size={13} className="text-[hsl(var(--text-secondary))]" />} label="Etiquetas">
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
                                        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.04] border border-dashed border-[hsl(var(--border))] dark:border-white/[0.1] transition-all"
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
                                                className="absolute top-full left-0 mt-1.5 z-50 w-56 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-2xl p-3 space-y-2"
                                            >
                                                <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Nueva etiqueta</p>
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
                                                        className="flex-1 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg px-2 py-1.5 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 transition-all"
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
                                                <div className="flex flex-wrap gap-1 pt-1 border-t border-[hsl(var(--border))] dark:border-white/5">
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
                    <section className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.05]">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-2 flex items-center gap-1.5">
                            <AlignLeft size={11} /> Descripción
                        </p>
                        <textarea
                            value={description}
                            onChange={e => setDesc(e.target.value)}
                            onBlur={handleSave}
                            rows={3}
                            placeholder="Añade una descripción..."
                            className="w-full text-[13px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] bg-transparent resize-none outline-none placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] leading-relaxed focus:ring-0"
                        />
                    </section>

                    {/* ─ ARCHIVOS ─ */}
                    <section className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.05]">
                        <div className="mb-3 flex items-center justify-between">
                            <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                                <Paperclip size={11} /> Archivos
                                <span className="rounded bg-[hsl(var(--surface-2))] px-1.5 py-0.5 text-[9px] font-bold text-[hsl(var(--text-secondary))] dark:bg-white/[0.06] dark:text-[hsl(var(--text-secondary))]">
                                    {attachments.length}
                                </span>
                            </p>
                        </div>

                        {attachments.length === 0 ? (
                            <p className="text-[11px] italic text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                Sin archivos adjuntos aun.
                            </p>
                        ) : (
                            <div className="space-y-2">
                                {attachments.map((attachment) => (
                                    <div
                                        key={attachment.id}
                                        className="flex items-center justify-between gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 dark:border-white/[0.06] dark:bg-white/[0.03]"
                                    >
                                        <a
                                            href={attachment.file_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="min-w-0 flex-1 text-left transition hover:text-[hsl(var(--primary))]"
                                        >
                                            <p className="truncate text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                                {attachment.filename}
                                            </p>
                                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">
                                                {attachment.file_size ? `${Math.max(1, Math.round(attachment.file_size / 1024))} KB` : 'Archivo adjunto'}
                                            </p>
                                        </a>
                                        <div className="flex items-center gap-1 shrink-0">
                                            <a
                                                href={attachment.file_url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] hover:underline"
                                            >
                                                Abrir
                                            </a>
                                            <button
                                                onClick={() => handleDeleteAttachment(attachment.id)}
                                                disabled={deletingAttachmentId === attachment.id}
                                                title="Eliminar adjunto"
                                                className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors disabled:opacity-50"
                                            >
                                                {deletingAttachmentId === attachment.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    {/* ─ ACTIVIDADES ─ */}
                    <section className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.05]">
                        <div className="mb-3 flex items-center justify-between">
                            <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                                <Boxes size={11} /> Insumos
                                <span className="rounded bg-[hsl(var(--surface-2))] px-1.5 py-0.5 text-[9px] font-bold text-[hsl(var(--text-secondary))] dark:bg-white/[0.06] dark:text-[hsl(var(--text-secondary))]">
                                    {supplies.length}
                                </span>
                            </p>
                        </div>

                        <div className="space-y-2">
                            {supplies.length === 0 && (
                                <p className="text-[11px] italic text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                    Sin insumos registrados.
                                </p>
                            )}

                            {supplies.map((supply) => (
                                <div
                                    key={supply.id}
                                    className="grid grid-cols-[minmax(0,1fr)_72px_110px] items-center gap-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 dark:border-white/[0.06] dark:bg-white/[0.03]"
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
                                        className="min-w-0 bg-transparent text-[12px] font-bold text-[hsl(var(--text-primary))] outline-none dark:text-[hsl(var(--text-secondary))]"
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
                                        className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-[11px] font-bold outline-none dark:border-white/10 dark:bg-white/5"
                                    />
                                    <select
                                        value={supply.status}
                                        disabled={savingSupplyId === supply.id}
                                        onChange={(event) => handleUpdateSupply(supply, { status: event.target.value })}
                                        className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-[11px] font-bold outline-none dark:border-white/10 dark:bg-white/5"
                                    >
                                        <option value="pending">Pendiente</option>
                                        <option value="ready">Listo</option>
                                        <option value="unavailable">No disponible</option>
                                    </select>
                                    <button
                                        onClick={() => handleDeleteSupply(supply.id)}
                                        disabled={deletingSupplyId === supply.id}
                                        title="Eliminar insumo"
                                        className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors disabled:opacity-50"
                                    >
                                        {deletingSupplyId === supply.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                                    </button>
                                </div>
                            ))}
                        </div>

                        <div className="mt-3 grid grid-cols-[minmax(0,1fr)_72px_auto] gap-2">
                            <input
                                value={newSupplyName}
                                onChange={(event) => setNewSupplyName(event.target.value)}
                                onKeyDown={(event) => event.key === 'Enter' && handleAddSupply()}
                                placeholder="Nuevo insumo"
                                className="min-w-0 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-[12px] font-medium outline-none dark:border-white/10 dark:bg-white/5"
                            />
                            <input
                                type="number"
                                min={1}
                                value={newSupplyQuantity}
                                onChange={(event) => setNewSupplyQuantity(Math.max(1, Number(event.target.value) || 1))}
                                className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-2 text-[12px] font-bold outline-none dark:border-white/10 dark:bg-white/5"
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

                    <section className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.05]">
                        <div className="flex items-center justify-between mb-3">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                                <Check size={11} /> Actividades
                                <span className="px-1.5 py-0.5 bg-[hsl(var(--surface-2))] dark:bg-white/[0.06] rounded text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-bold text-[9px]">
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
                            <Plus size={13} className="text-[hsl(var(--text-secondary))] shrink-0" />
                            <input
                                type="text"
                                value={newActivityTitle}
                                onChange={e => setNewActivityTitle(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && handleAddTopLevel()}
                                placeholder="Añadir actividad..."
                                className="flex-1 text-[12px] bg-transparent outline-none text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))]"
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
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-3 flex items-center gap-1.5">
                            <MessageSquare size={11} /> Actividad
                        </p>

                        {/* Comment list */}
                        <div className="space-y-3 mb-4">
                            {loadingComments && (
                                <p className="text-[11px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] italic text-center py-2">
                                    Cargando actividad...
                                </p>
                            )}
                            {!loadingComments && comments.length === 0 && (
                                <p className="text-[11px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] italic text-center py-2">
                                    Sin comentarios aún. Menciona a alguien con @
                                </p>
                            )}
                            {comments.map(c => (
                                <div key={c.id} className="flex gap-2.5 group">
                                    <div
                                        className="size-6 rounded-full flex items-center justify-center font-semibold text-white shrink-0 mt-0.5"
                                        style={{ backgroundColor: c.authorColor ?? 'hsl(var(--primary))' }}
                                    >
                                        {c.author.charAt(0).toUpperCase()}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-baseline gap-2 mb-1">
                                            <span className="text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{c.author}</span>
                                            <span className="text-[10px] text-[hsl(var(--text-secondary))]">
                                                {c.timestamp.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                            <button
                                                onClick={() => handleDeleteComment(c.id)}
                                                title="Eliminar comentario"
                                                className="opacity-0 group-hover:opacity-100 transition-opacity text-[hsl(var(--text-secondary))] hover:text-rose-500"
                                            >
                                                <Trash2 size={12} />
                                            </button>
                                        </div>
                                        <p className="text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">{c.text}</p>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Comment input */}
                        <div className="flex items-end gap-2">
                            <div className="size-6 rounded-full bg-[hsl(var(--primary))] flex items-center justify-center font-semibold text-white shrink-0">
                                T
                            </div>
                            <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/[0.04] border border-[hsl(var(--border))] dark:border-white/[0.07] focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-400/40 transition-all">
                                <input
                                    type="text"
                                    value={commentInput}
                                    onChange={e => setCommentInput(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendComment()}
                                    placeholder="Menciona @Dzin para crear, encontrar y preguntar..."
                                    className="flex-1 text-[12px] bg-transparent outline-none text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))]"
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

            <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
        </AnimatePresence>
    );
}

// ─────────────────────────────────────────────────────────────────
// META ROW
// ─────────────────────────────────────────────────────────────────
function MetaRow({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
    return (
        <div className="flex items-center gap-0">
            <div className="w-[140px] shrink-0 flex items-center gap-2 text-[11px] font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                {icon}
                {label}
            </div>
            {children}
        </div>
    );
}

"use client";

import ConfirmActionDrawer, { type ConfirmActionState } from '@/components/ConfirmActionDrawer';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import {
    PRIORITY_CYCLE,
    STATUS_CYCLE,
    getValidStatus,
    getValidPriority,
    getPriorityOption,
} from '@/lib/projects/constants';
import type { TaskStatus, TaskPriority } from '@/lib/projects/constants';
import type { ProjectTaskRecord, TaskSupplyRecord } from '@/types/projects';
import { AlignLeft } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useCallback, useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';

import TaskDetailHeader from './TaskDetailHeader';
import TaskMetaFields from './TaskMetaFields';
import TaskAttachmentSection from './TaskAttachmentSection';
import TaskSupplySection from './TaskSupplySection';
import TaskActivitySection from './TaskActivitySection';
import type { Activity } from './TaskActivitySection';
import { toggleActivity, addChild, updateTitle } from './TaskActivitySection';
import TaskCommentSection from './TaskCommentSection';

const MIN_WIDTH = 400;
const DEFAULT_WIDTH = 520;
const MAX_RATIO = 0.88;

let nextId = Date.now();
const uid = () => `tmp_${++nextId}`;

function getPriorityMap(priority: TaskPriority) {
    const opt = getPriorityOption(priority);
    return { label: opt.label, color: opt.color, dot: opt.dot };
}

interface TaskDetailPanelProps {
    task: ProjectTaskRecord | null;
    projectTitle?: string;
    onClose: () => void;
    onUpdate?: (updated: ProjectTaskRecord) => void;
    onDelete?: (taskId: string) => void;
    onActivityCreated?: () => void;
    onVerRutaClick?: () => void;
}

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

    // ── Width / resize ──────────────────────────────────────────
    const [width, setWidth] = useState<number>(() => {
        if (typeof window === 'undefined') return DEFAULT_WIDTH;
        return Number(localStorage.getItem('taskDetailPanelWidth') || DEFAULT_WIDTH);
    });
    const resizing = useRef(false);
    const startX = useRef(0);
    const startW = useRef(0);
    const widthRef = useRef<number>(width);
    useEffect(() => { widthRef.current = width; }, [width]);

    const onMouseDown = useCallback((e: ReactMouseEvent) => {
        e.preventDefault();
        resizing.current = true;
        startX.current = e.clientX;
        startW.current = widthRef.current;
        document.body.style.cursor = 'ew-resize';
        document.body.style.userSelect = 'none';

        const onMove = (moveEvt: MouseEvent) => {
            if (!resizing.current) return;
            const delta = startX.current - moveEvt.clientX;
            const maxW = window.innerWidth * MAX_RATIO;
            const newW = Math.min(maxW, Math.max(MIN_WIDTH, startW.current + delta));
            widthRef.current = newW;
            setWidth(newW);
        };
        const onUp = () => {
            if (resizing.current) {
                resizing.current = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                localStorage.setItem('taskDetailPanelWidth', String(widthRef.current));
            }
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };
        const onBlur = () => onUp();
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        window.addEventListener('blur', onBlur, { once: true });
    }, []);

    // ── Form state ──────────────────────────────────────────────
    const [title, setTitle] = useState(task?.title ?? '');
    const [description, setDesc] = useState(task?.description ?? '');
    const [starred, setStarred] = useState(false);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [supplies, setSupplies] = useState<TaskSupplyRecord[]>(task?.supplies ?? []);
    const [deletingAttachmentId, setDeletingAttachmentId] = useState<string | null>(null);
    const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
    const [error, setError] = useState<string | null>(null);

    const requireAuth = useCallback((message: string) => {
        if (authLoading) return false;
        if (!token) { setError(message); return false; }
        return true;
    }, [authLoading, token]);

    // ── Labels ──────────────────────────────────────────────────
    const [labels, setLabels] = useState<string[]>(task?.labels ?? []);

    // ── Activities ──────────────────────────────────────────────
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
        } catch { setError('No se pudo actualizar la sub-actividad.'); }
    };

    const handleAddChild = async (parentId: string) => {
        if (!task || !requireAuth('Debes iniciar sesión para crear sub-actividades.')) return;
        try {
            const created = await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}/subtasks`, {
                method: 'POST', token, body: { title: 'Nueva sub-actividad', status: 'todo', priority: 'medium', parent_id: parentId },
            });
            const item: Activity = { id: created.id || uid(), title: created.title || 'Nueva sub-actividad', completed: false };
            setActivities(prev => addChild(prev, parentId, item));
            onActivityCreated?.();
        } catch { setError('No se pudo crear la sub-actividad.'); }
    };

    const handleUpdateTitle = async (id: string, t: string) => {
        setActivities(prev => updateTitle(prev, id, t));
        if (!task || !requireAuth('Debes iniciar sesión para actualizar sub-actividades.')) return;
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/subtasks/${id}`, {
                method: 'PATCH', token, body: { title: t },
            });
        } catch { setError('No se pudo actualizar la sub-actividad.'); }
    };

    const handleAddTopLevel = async () => {
        if (!newActivityTitle.trim() || !task || !requireAuth('Debes iniciar sesión para crear actividades.')) return;
        try {
            const created = await apiFetch<ProjectTaskRecord>(`/projects/${task.project_id}/tasks/${task.id}/subtasks`, {
                method: 'POST', token, body: { title: newActivityTitle.trim(), status: 'todo', priority: 'medium' },
            });
            setActivities(prev => [...prev, { id: created.id || uid(), title: newActivityTitle.trim(), completed: false }]);
            onActivityCreated?.();
        } catch { setError('No se pudo crear la actividad.'); }
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
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/subtasks/${activityId}`, { method: 'DELETE', token });
        } catch { setError('No se pudo eliminar la actividad.'); }
    };

    // ── Sync on task change ─────────────────────────────────────
    useEffect(() => {
        if (task) {
            setTitle(task.title ?? '');
            setDesc(task.description ?? '');
            const subs = task.subtasks || [];
            setActivities(subs.map(s => ({
                id: s.id, title: s.title, completed: s.status === 'completed',
                children: (s.subtasks || []).map(ss => ({ id: ss.id, title: ss.title, completed: ss.status === 'completed' })),
            })));
            setNewActivityTitle('');
            setLabels(task.labels ?? []);
            setSupplies(task.supplies ?? []);
        }
    }, [task?.id]);

    // ── Save ────────────────────────────────────────────────────
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
        } finally { setSaving(false); }
    };

    // ── Status / Priority / Assignee / Delete ───────────────────
    const handleStatusCycle = async () => {
        if (!task || !requireAuth('Debes iniciar sesión para cambiar el estado de la tarea.')) return;
        const currentIdx = STATUS_CYCLE.indexOf(getValidStatus(task.status));
        const nextStatus = STATUS_CYCLE[(currentIdx + 1) % STATUS_CYCLE.length];
        onUpdate?.({ ...task, status: nextStatus });
        try { await apiFetch(`/projects/tasks/${task.id}`, { method: 'PATCH', token, body: { status: nextStatus } }); }
        catch { setError('No se pudo actualizar el estado de la tarea.'); }
    };

    const handlePriorityCycle = async () => {
        if (!task || !requireAuth('Debes iniciar sesión para cambiar la prioridad de la tarea.')) return;
        const currentIdx = PRIORITY_CYCLE.indexOf(getValidPriority(task.priority));
        const nextPriority = PRIORITY_CYCLE[(currentIdx + 1) % PRIORITY_CYCLE.length];
        onUpdate?.({ ...task, priority: nextPriority });
        try { await apiFetch(`/projects/tasks/${task.id}`, { method: 'PATCH', token, body: { priority: nextPriority } }); }
        catch { setError('No se pudo actualizar la prioridad de la tarea.'); }
    };

    const handleAssigneeChange = async (newAssigneeId: string | null) => {
        if (!task || !requireAuth('Debes iniciar sesión para reasignar la tarea.')) return;
        onUpdate?.({ ...task, assignee_id: newAssigneeId });
        try { await apiFetch(`/projects/tasks/${task.id}`, { method: 'PATCH', token, body: { assignee_id: newAssigneeId } }); }
        catch { setError('No se pudo reasignar la tarea.'); }
    };

    const handleDeleteTask = async () => {
        if (!task || !requireAuth('Debes iniciar sesión para eliminar la tarea.')) return;
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}`, { method: 'DELETE', token });
            onDelete?.(task.id);
            onClose();
        } catch { setError('No se pudo eliminar la tarea.'); }
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
                    onActivityCreated?.();
                } catch { setError('No se pudo eliminar el comentario.'); }
                setConfirmAction(null);
            },
        });
    };

    const handleDeleteAttachment = async (attachmentId: string) => {
        if (!task || !requireAuth('Debes iniciar sesión para eliminar archivos adjuntos.')) return;
        setDeletingAttachmentId(attachmentId);
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/attachments/${attachmentId}`, { method: 'DELETE', token });
            const nextAttachments = (task.attachments ?? []).filter(a => a.id !== attachmentId);
            onUpdate?.({ ...task, attachments: nextAttachments });
            onActivityCreated?.();
        } catch { setError('No se pudo eliminar el archivo adjunto.'); }
        finally { setDeletingAttachmentId(null); }
    };

    if (!task) return null;
    if (authLoading) return null;

    const priority = getPriorityMap((task.priority ?? 'medium') as TaskPriority);

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
                {/* Resize handle */}
                <div
                    onMouseDown={onMouseDown}
                    className="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize z-10 group flex items-center justify-center"
                    title="Arrastrar para redimensionar"
                >
                    <div className="w-[3px] h-8 rounded-full bg-[hsl(var(--surface-3))] dark:bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>

                <TaskDetailHeader
                    task={task}
                    projectTitle={projectTitle}
                    title={title}
                    saving={saving}
                    uploading={uploading}
                    starred={starred}
                    error={error}
                    onClose={onClose}
                    onTitleChange={setTitle}
                    onSave={handleSave}
                    onStatusCycle={handleStatusCycle}
                    onFileClick={() => {}}
                    onStarToggle={() => setStarred(v => !v)}
                    onExpandToggle={() => {
                        const maxW = Math.floor(window.innerWidth * MAX_RATIO);
                        setWidth(prev => prev < maxW - 50 ? maxW : DEFAULT_WIDTH);
                    }}
                    onDeleteTask={handleDeleteTask}
                    onVerRutaClick={onVerRutaClick}
                />

                {/* Body (scrollable) */}
                <div className="flex-1 overflow-y-auto scrollbar-thin">
                    <TaskMetaFields
                        task={task}
                        labels={labels}
                        onLabelsChange={setLabels}
                        onAssigneeChange={handleAssigneeChange}
                        onPriorityCycle={handlePriorityCycle}
                        priority={priority}
                        token={token}
                    />

                    {/* Description */}
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

                    <TaskAttachmentSection
                        task={task}
                        uploading={uploading}
                        deletingAttachmentId={deletingAttachmentId}
                        onUpload={(updated) => onUpdate?.(updated)}
                        onDelete={handleDeleteAttachment}
                        onUploadingChange={setUploading}
                    />

                    <TaskSupplySection
                        task={task}
                        supplies={supplies}
                        onSuppliesChange={(next) => { setSupplies(next); onUpdate?.({ ...task, supplies: next }); }}
                        token={token}
                        onActivityCreated={onActivityCreated}
                    />

                    <TaskActivitySection
                        activities={activities}
                        newActivityTitle={newActivityTitle}
                        onNewActivityTitleChange={setNewActivityTitle}
                        onAddTopLevel={handleAddTopLevel}
                        onToggle={handleToggle}
                        onAddChild={handleAddChild}
                        onUpdateTitle={handleUpdateTitle}
                        onDelete={handleDeleteActivity}
                    />

                    {token && (
                        <TaskCommentSection
                            task={task}
                            token={token}
                            onDeleteComment={handleDeleteComment}
                            onActivityCreated={onActivityCreated}
                        />
                    )}
                </div>
            </motion.aside>

            <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
        </AnimatePresence>
    );
}

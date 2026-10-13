"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
    ChevronDown, ChevronRight, Plus,
    MessageSquare, MoreHorizontal, CheckCircle2, X, Send,
    Paperclip, AtSign, Smile, Check, Star, Pencil, Loader2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord, ProjectUserFavorite } from '@/types/projects';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { buildStatusOptions, getStatusOption, PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT, STATUS_GROUP_PILL } from '@/lib/projects/constants';
import { useProjectUpdate, type PhaseDef } from '@/context/ProjectUpdateContext';
import type { TaskStatus } from '@/lib/projects/constants';
import {
    InlineStatusPicker,
    InlinePriorityPicker,
    InlineDatePicker,
    InlineUserPicker,
} from '@/components/ui/inline-editors';

// ─── TYPE DEFINITIONS ─────────────────────────────────────────────────────────
interface Props {
    /** Project phases used as the canonical List grouping when customized. */
    phaseDefs?: readonly PhaseDef[];
    tasks: ProjectTaskRecord[];
    projectId?: string;
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: (status: string) => void;
    /** Parent-owned persistence callback; it also owns optimistic updates
     *  and rollback so List and Kanban share one source of truth. */
    onTaskUpdate?: (taskId: string, patch: Partial<ProjectTaskRecord>) => void;
    quickAddStatus?: string | null;
    quickAddTitle?: string;
    onQuickAddTitleChange?: (v: string) => void;
    onQuickAddConfirm?: () => void;
    onQuickAddCancel?: () => void;
}

// ─── Quick Comment Popover ────────────────────────────────────────────────────
interface CommentPopoverProps {
    onClose: () => void;
    placement?: 'bottom' | 'top';
    taskId?: string;
    projectId?: string;
}

const QUICK_EMOJIS = ['👍', '❤️', '🎉', '🚀', '👀', '💡', '✅', '👏'];

function CommentPopover({ onClose, placement = 'bottom', taskId, projectId }: CommentPopoverProps) {
    const { token } = useAuth();
    const [text, setText] = useState('');
    const [attachedFile, setAttachedFile] = useState<File | null>(null);
    const [showEmojiPicker, setShowEmojiPicker] = useState(false);
    const [sending, setSending] = useState(false);

    // Mentions state
    const [mentionState, setMentionState] = useState<{ query: string; start: number } | null>(null);
    const [candidates, setCandidates] = useState<Array<{ id: string; name: string }>>([]);
    const [selectedMentions, setSelectedMentions] = useState<Array<{ id: string; name: string }>>([]);
    const [activeMentionIndex, setActiveMentionIndex] = useState(0);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Fetch candidate mentions when mention query changes
    useEffect(() => {
        if (!mentionState) return;
        let active = true;
        const query = mentionState.query.trim();
        const queryParam = query ? `?search=${encodeURIComponent(query)}` : '';

        apiFetch<Array<any>>(`/projects/assignee-candidates${queryParam}`, { token: token ?? undefined })
            .catch(() => apiFetch<Array<any>>(`/crm/personas${queryParam}`, { token: token ?? undefined }))
            .then(data => {
                if (!active) return;
                const list = (Array.isArray(data) ? data : []).map(p => ({
                    id: String(p.user?.id ?? p.id),
                    name: p.nombre_completo || [p.first_name, p.last_name].filter(Boolean).join(' ') || p.username || `#${p.id}`,
                }));
                setCandidates(list);
                setActiveMentionIndex(0);
            })
            .catch(() => {
                if (active) setCandidates([]);
            });

        return () => { active = false; };
    }, [mentionState?.query, token]);

    const filteredCandidates = useMemo(() => {
        if (!mentionState) return [];
        const q = mentionState.query.toLowerCase().trim();
        if (!q) return candidates;
        return candidates.filter(c => c.name.toLowerCase().includes(q));
    }, [candidates, mentionState]);

    const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const val = e.target.value;
        setText(val);
        const pos = e.target.selectionStart ?? val.length;
        const before = val.slice(0, pos);
        const lastAt = before.lastIndexOf('@');
        if (lastAt !== -1) {
            const query = before.slice(lastAt + 1);
            if (!query.includes(' ') && !query.includes('\n')) {
                setMentionState({ query, start: lastAt });
                return;
            }
        }
        setMentionState(null);
    };

    const handleSelectMention = (candidate: { id: string; name: string }) => {
        if (!mentionState) return;
        const before = text.slice(0, mentionState.start);
        const after = text.slice(mentionState.start + 1 + mentionState.query.length);
        const next = `${before}@${candidate.name} ${after}`;
        setText(next);
        setSelectedMentions(prev => prev.some(m => m.id === candidate.id) ? prev : [...prev, candidate]);
        setMentionState(null);
        setTimeout(() => textareaRef.current?.focus(), 20);
    };

    const handleTriggerMention = () => {
        const textarea = textareaRef.current;
        const pos = textarea?.selectionStart ?? text.length;
        const before = text.slice(0, pos);
        const after = text.slice(pos);
        const needsSpace = before.length > 0 && !before.endsWith(' ');
        const insert = needsSpace ? ' @' : '@';
        const next = `${before}${insert}${after}`;
        setText(next);
        const newPos = pos + insert.length;
        setMentionState({ query: '', start: newPos - 1 });
        setTimeout(() => {
            if (textarea) {
                textarea.focus();
                textarea.setSelectionRange(newPos, newPos);
            }
        }, 20);
    };

    const handleAddEmoji = (emoji: string) => {
        const textarea = textareaRef.current;
        const pos = textarea?.selectionStart ?? text.length;
        const before = text.slice(0, pos);
        const after = text.slice(pos);
        const needsSpace = before.length > 0 && !before.endsWith(' ');
        const insert = needsSpace ? ` ${emoji} ` : `${emoji} `;
        const next = `${before}${insert}${after}`;
        setText(next);
        setShowEmojiPicker(false);
        setTimeout(() => {
            if (textarea) {
                textarea.focus();
                const newPos = pos + insert.length;
                textarea.setSelectionRange(newPos, newPos);
            }
        }, 20);
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setAttachedFile(file);
        }
    };

    const handleRemoveFile = () => {
        setAttachedFile(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleSend = async () => {
        if (!text.trim() || sending) return;
        setSending(true);
        try {
            const endpoint = projectId ? `/projects/${projectId}/comments` : '/projects/comments';
            const mentionIds = selectedMentions
                .filter(m => text.includes(`@${m.name}`))
                .map(m => m.id);

            const payload: any = {
                content: text.trim(),
                task_id: taskId,
                mentions: mentionIds,
            };
            if (projectId) {
                payload.project_id = projectId;
            }
            if (attachedFile) {
                payload.attachments = [{
                    name: attachedFile.name,
                    url: attachedFile.name,
                    type: attachedFile.type || 'document',
                    size: attachedFile.size,
                }];
            }

            await apiFetch(endpoint, {
                method: 'POST',
                token,
                body: payload,
            });

            toast.success('Comentario guardado');
            onClose();
        } catch {
            toast.error('No se pudo guardar el comentario');
        } finally {
            setSending(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (mentionState && filteredCandidates.length > 0) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setActiveMentionIndex(prev => (prev + 1) % filteredCandidates.length);
                return;
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                setActiveMentionIndex(prev => (prev - 1 + filteredCandidates.length) % filteredCandidates.length);
                return;
            }
            if ((e.key === 'Enter' || e.key === 'Tab') && !e.metaKey && !e.ctrlKey) {
                e.preventDefault();
                handleSelectMention(filteredCandidates[activeMentionIndex]);
                return;
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                setMentionState(null);
                return;
            }
        }

        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            handleSend();
            return;
        }

        if (e.key === 'Escape') {
            e.preventDefault();
            onClose();
        }
    };

    return (
        <div
            data-testid="quick-comment-popover"
            data-placement={placement}
            className="w-80 bg-[hsl(var(--surface-1))] rounded-lg shadow-xl border border-[hsl(var(--border))] z-[600] overflow-hidden relative"
        >
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-[hsl(var(--border))]">
                <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Comentario rápido</span>
                <button
                    onClick={onClose}
                    aria-label="Cerrar comentario rápido"
                    className="p-0.5 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                >
                    <X size={13}/>
                </button>
            </div>

            {/* Textarea */}
            <div className="relative">
                <textarea
                    ref={textareaRef}
                    autoFocus
                    value={text}
                    onChange={handleTextChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Escribe un comentario... @Brain para IA"
                    className="w-full resize-none text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] px-3 pt-3 pb-2 bg-transparent outline-none min-h-[68px] leading-relaxed"
                />

                {/* Autocomplete mention dropdown */}
                {mentionState && filteredCandidates.length > 0 && (
                    <div
                        role="listbox"
                        data-testid="mention-autocomplete-list"
                        className="absolute left-2 right-2 bottom-1 z-[700] max-h-40 overflow-y-auto rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-lg p-1 space-y-0.5"
                    >
                        {filteredCandidates.slice(0, 5).map((candidate, idx) => (
                            <button
                                key={candidate.id}
                                type="button"
                                role="option"
                                aria-selected={idx === activeMentionIndex}
                                onClick={() => handleSelectMention(candidate)}
                                className={clsx(
                                    "w-full text-left flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors",
                                    idx === activeMentionIndex
                                        ? "bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] font-semibold"
                                        : "text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))]"
                                )}
                            >
                                <span className="size-5 rounded-full bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center justify-center text-2xs font-bold shrink-0">
                                    {candidate.name.charAt(0).toUpperCase()}
                                </span>
                                <span className="truncate">{candidate.name}</span>
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Attachment preview if any */}
            {attachedFile && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 mx-3 mb-2 rounded-md bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-xs text-[hsl(var(--text-primary))]">
                    <Paperclip size={12} className="text-[hsl(var(--text-secondary))] shrink-0" />
                    <span className="truncate max-w-[200px] text-xs font-medium">{attachedFile.name}</span>
                    <button
                        type="button"
                        onClick={handleRemoveFile}
                        aria-label="Remover archivo"
                        className="ml-auto text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] transition-colors p-0.5"
                    >
                        <X size={12} />
                    </button>
                </div>
            )}

            {/* Quick emoji bar */}
            {showEmojiPicker && (
                <div className="flex items-center justify-between gap-1 px-3 py-1.5 border-t border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.5)]">
                    {QUICK_EMOJIS.map(emoji => (
                        <button
                            key={emoji}
                            type="button"
                            onClick={() => handleAddEmoji(emoji)}
                            className="p-1 hover:bg-[hsl(var(--surface-3))] rounded text-base active:scale-110 transition-transform"
                            aria-label={`Insertar emoji ${emoji}`}
                        >
                            {emoji}
                        </button>
                    ))}
                </div>
            )}

            {/* Hidden file input */}
            <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                data-testid="comment-file-input"
                onChange={handleFileChange}
            />

            {/* Toolbar */}
            <div className="flex items-center gap-1 px-3 pb-3">
                <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    aria-label="Adjuntar archivo"
                    className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.1)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                    title="Adjuntar"
                >
                    <Paperclip size={13} />
                </button>
                <button
                    type="button"
                    onClick={handleTriggerMention}
                    aria-label="Mencionar usuario"
                    className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.1)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                    title="Mencionar"
                >
                    <AtSign size={13} />
                </button>
                <button
                    type="button"
                    onClick={() => setShowEmojiPicker(prev => !prev)}
                    aria-label="Añadir emoji"
                    className={clsx(
                        "p-1.5 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2",
                        showEmojiPicker
                            ? "text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.15)]"
                            : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.1)]"
                    )}
                    title="Emoji"
                >
                    <Smile size={13} />
                </button>
                <div className="flex-1" />
                <span className="text-2xs text-[hsl(var(--text-secondary))] mr-2 hidden sm:block">⌘↵ enviar</span>
                <button
                    type="button"
                    onClick={handleSend}
                    className={clsx(
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all',
                        text.trim() && !sending
                            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:bg-[hsl(var(--primary))]/90 shadow-sm active:scale-95'
                            : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] cursor-not-allowed'
                    )}
                    disabled={!text.trim() || sending}
                >
                    {sending ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
                    {sending ? 'Enviando...' : 'Enviar'}
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
    phases,
}: {
    task: ProjectTaskRecord;
    onOpen: () => void;
    onChange: (patch: Partial<ProjectTaskRecord>) => void;
    phases?: readonly PhaseDef[];
}) {
    const { openLayer, setRightMode } = useSidebarLayers();
    const [commentOpen, setCommentOpen] = useState(false);
    const [commentPlacement, setCommentPlacement] = useState<'bottom' | 'top'>('bottom');
    const commentRef = useRef<HTMLDivElement>(null);

    const updateCommentPlacement = useCallback(() => {
        if (!commentRef.current) return;
        const rect = commentRef.current.getBoundingClientRect();
        const POPOVER_APPROX_HEIGHT = 220;
        const spaceBelow = window.innerHeight - rect.bottom;
        if (spaceBelow < POPOVER_APPROX_HEIGHT && rect.top > spaceBelow) {
            setCommentPlacement('top');
        } else {
            setCommentPlacement('bottom');
        }
    }, []);

    // Recalcular posicionamiento y registrar listeners al abrir el popover
    useEffect(() => {
        if (!commentOpen) return;
        updateCommentPlacement();
        window.addEventListener('resize', updateCommentPlacement);
        window.addEventListener('scroll', updateCommentPlacement, true);
        return () => {
            window.removeEventListener('resize', updateCommentPlacement);
            window.removeEventListener('scroll', updateCommentPlacement, true);
        };
    }, [commentOpen, updateCommentPlacement]);

    const status = task.status ?? 'todo';
    const priority = task.priority ?? 'medium';
    const dueDate = task.due_date;
    const assignedUserId = task.assignee_id ?? null;

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
        if (!commentOpen) {
            updateCommentPlacement();
            setRightMode('push');
            openLayer('RIGHT');
        }
        setCommentOpen(v => !v);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className={clsx(
                'flex items-center group border-b border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-1))] transition-colors relative min-h-[40px]',
                commentOpen ? 'z-30' : 'z-0'
            )}
        >
            {/* Checkbox */}
            <div className="w-8 flex-shrink-0 flex items-center justify-center pl-2">                    <button
                    onClick={() => onChange({ status: status === 'completed' ? 'todo' : 'completed' })}
                    className={clsx(
                        'size-4 rounded-full border-2 flex items-center justify-center text-2xs transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--success))] focus-visible:ring-offset-2',
                        status === 'completed'
                            ? 'bg-[hsl(var(--success))] border-[hsl(var(--success))] text-[hsl(var(--primary-foreground))]'
                            : 'border-[hsl(var(--border))] text-transparent hover:border-[hsl(var(--success)/0.4)] hover:bg-[hsl(var(--success)/0.1)]'
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
                    'text-base font-medium truncate transition-colors',
                    status === 'completed'
                        ? 'line-through text-[hsl(var(--text-secondary))]'
                        : 'text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--primary))]'
                )}>
                    {task.title}
                </span>
            </button>

            {/* ── PERSONA ASIGNADA ─────── */}
            <div className="w-28 flex-shrink-0 flex items-center justify-center px-1">
                <InlineUserPicker
                    endpoint={PROJECT_ASSIGNEE_CANDIDATES_ENDPOINT}
                    value={assignedUserId}
                    onChange={(userId) => onChange({ assignee_id: userId })}
                />
            </div>

            {/* ── FECHA LÍMITE ─────────── */}
            <div className="w-32 flex-shrink-0 flex items-center px-1">
                <InlineDatePicker
                    value={dueDate as string | null}
                    onChange={(date) => onChange({ due_date: date })}
                />
            </div>

            {/* ── PRIORIDAD ────────────── */}
            <div className="w-20 flex-shrink-0 flex items-center justify-center px-1">
                <InlinePriorityPicker
                    value={priority}
                    onChange={(p) => onChange({ priority: p })}
                />
            </div>

            {/* ── ESTADO ───────────────── */}
            <div className="w-36 flex-shrink-0 flex items-center px-2">
                <InlineStatusPicker
                    value={status}
                    phases={phases ? [...phases] : undefined}
                    onChange={(s) => onChange({ status: s })}
                />
            </div>

            {/* ── COMENTARIOS ──────────── */}
            <div
                className={clsx('w-24 flex-shrink-0 flex items-center justify-center px-1 relative', commentOpen && 'z-50')}
                ref={commentRef}
            >
                <button
                    onClick={handleCommentClick}
                    className={clsx(
                        'flex items-center justify-center size-8 rounded-lg border transition-all min-h-[40px] min-w-[32px]',
                        commentOpen
                            ? 'border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]'
                            : 'border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--primary)/0.3)] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.1)]'
                    )}
                    aria-label="Ver comentarios y actividad"
                >
                    <MessageSquare size={13} />
                </button>
                <AnimatePresence>
                    {commentOpen && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.96, y: commentPlacement === 'top' ? 4 : -4 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.96, y: commentPlacement === 'top' ? 4 : -4 }}
                            transition={{ duration: 0.1 }}
                            className={clsx(
                                'absolute right-0 z-[600]',
                                commentPlacement === 'top' ? 'bottom-full mb-1' : 'top-full mt-1'
                            )}
                        >
                            <CommentPopover
                                onClose={() => setCommentOpen(false)}
                                placement={commentPlacement}
                                taskId={task.id}
                                projectId={task.project_id}
                            />
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* ── DETALLE ──────────────── */}
            <div className="w-16 flex-shrink-0 flex items-center justify-center px-1">
                <button
                    type="button"
                    onClick={onOpen}
                    title="Ver detalle completo"
                    aria-label={`Ver detalle completo de ${task.title}`}
                    className="flex items-center justify-center size-8 rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--primary)/0.3)] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.1)] transition-all min-h-[40px] min-w-[32px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                >
                    <Pencil size={13} />
                </button>
            </div>

            {/* More */}
            <div className="w-8 flex-shrink-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="size-6 rounded flex items-center justify-center text-[hsl(var(--text-secondary))]">
                    <MoreHorizontal size={13} />
                </span>
            </div>
        </motion.div>
    );
}

// ─── Status Group ─────────────────────────────────────────────────────────────
function StatusGroup({
    status,
    statusLabel,
    tasks,
    onOpenTask,
    onAddTask,
    onStartInlineAdd,
    isFirst,
    onChangeTask,
    phaseDefs,
    quickAddStatus,
    quickAddTitle = '',
    onQuickAddTitleChange,
    onQuickAddConfirm,
    onQuickAddCancel,
    isAddingHere: isAddingHereProp,
    isSubmitting = false,
}: {
    status: string;
    statusLabel?: string;
    tasks: ProjectTaskRecord[];
    onOpenTask: (t: ProjectTaskRecord) => void;
    onAddTask?: (s: string) => void;
    onStartInlineAdd?: () => void;
    isFirst?: boolean;
    onChangeTask: (taskId: number | string, patch: Partial<ProjectTaskRecord>) => void;
    phaseDefs?: readonly PhaseDef[];
    quickAddStatus?: string | null;
    quickAddTitle?: string;
    onQuickAddTitleChange?: (v: string) => void;
    onQuickAddConfirm?: () => void;
    onQuickAddCancel?: () => void;
    isAddingHere?: boolean;
    isSubmitting?: boolean;
}) {
    const inputRef = useRef<HTMLInputElement>(null);
    const isAddingHere = isAddingHereProp !== undefined ? isAddingHereProp : (quickAddStatus === status);
    const [collapsed, setCollapsed] = useState(false);

    useEffect(() => {
        if (isAddingHere && inputRef.current) {
            setTimeout(() => {
                inputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                inputRef.current?.focus();
            }, 80);
        }
    }, [isAddingHere]);

    const cfg = getStatusOption(status);
    const pillCls = STATUS_GROUP_PILL[status as TaskStatus]
        ?? 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]';

    return (
        <div className="mb-0">
            {/* Group Header */}
            <div className={clsx('flex items-center gap-3 px-4 py-3', !isFirst && 'mt-3')}>
                <button
                    onClick={() => setCollapsed(v => !v)}
                    aria-label={collapsed ? 'Expandir grupo' : 'Contraer grupo'}
                    className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                    aria-expanded={!collapsed}
                >
                    {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                </button>
                <span className={clsx('px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wide', pillCls)}>
                    {statusLabel ?? cfg.label}
                </span>
                <span className="text-sm font-bold text-[hsl(var(--text-secondary))]">{tasks.length}</span>
            </div>

            <AnimatePresence initial={false}>
                {!collapsed && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                        className={collapsed ? "overflow-hidden" : "overflow-visible"}
                    >
                        {/* Column Headers */}
                        <div className="flex items-center border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                            <div className="w-8 flex-shrink-0" />
                            <div className="flex-1 px-3 py-2 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Nombre</div>
                            <div className="w-28 flex-shrink-0 px-1 py-2 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] text-center whitespace-nowrap">Asignado</div>
                            <div className="w-32 flex-shrink-0 px-1 py-2 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] whitespace-nowrap">Fecha L&iacute;mite</div>
                            <div className="w-20 flex-shrink-0 px-1 py-2 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] text-center whitespace-nowrap">Prior.</div>
                            <div className="w-36 flex-shrink-0 px-2 py-2 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] whitespace-nowrap">Estado</div>
                            <div className="w-24 flex-shrink-0 px-1 py-2 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] text-center whitespace-nowrap">Coment.</div>
                            <div className="w-16 flex-shrink-0 px-1 py-2 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] text-center whitespace-nowrap">Detalle</div>
                            <div className="w-8 flex-shrink-0" />
                        </div>

                        {/* Task Rows */}
                        {tasks.map(task => (
                            <TaskRow
                                key={task.id}
                                task={task}
                                onOpen={() => onOpenTask(task)}
                                onChange={(patch) => onChangeTask(task.id, patch)}
                                phases={phaseDefs}
                            />
                        ))}

                        {/* Quick-add row */}
                        {isAddingHere ? (
                            <div className="flex items-center gap-2 px-4 py-2 border-b border-[hsl(var(--border))] bg-[hsl(var(--primary)/0.05)] min-h-[40px]">
                                <div className="w-8 flex-shrink-0 flex items-center justify-center">
                                    <div className="size-4 rounded-full border-2 border-[hsl(var(--primary)/0.4)]" />
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
                                    placeholder="Nombre de la actividad... (Enter para crear)"
                                    disabled={isSubmitting}
                                    className="flex-1 text-base font-medium bg-transparent outline-none text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]"
                                />
                                <button
                                    type="button"
                                    onClick={onQuickAddConfirm}
                                    disabled={isSubmitting || !quickAddTitle.trim()}
                                    className="px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-bold rounded-lg hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all disabled:opacity-50"
                                >
                                    {isSubmitting ? 'Creando...' : 'Crear'}
                                </button>
                                <button
                                    type="button"
                                    onClick={onQuickAddCancel}
                                    disabled={isSubmitting}
                                    aria-label="Cancelar creación de actividad"
                                    className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                                >
                                    <X size={14} />
                                </button>
                            </div>
                        ) : (
                            <button
                                type="button"
                                onClick={onStartInlineAdd ?? (() => onAddTask?.(status))}
                                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-1))] w-full transition-colors border-b border-[hsl(var(--border))] min-h-[40px]"
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
export default function ProjectListView({
    phaseDefs,
    tasks,
    projectId,
    onOpenTask,
    onAddTask,
    onTaskUpdate,
    quickAddStatus,
    quickAddTitle,
    onQuickAddTitleChange,
    onQuickAddConfirm,
    onQuickAddCancel,
}: Props) {
    const { token } = useAuth();
    const { createTask } = useProjectUpdate();
    const [onlyFavorites, setOnlyFavorites] = useState(false);
    const [favoriteTaskIds, setFavoriteTaskIds] = useState<Set<string>>(new Set());
    const [internalInlineStatus, setInternalInlineStatus] = useState<string | null>(null);
    const [internalInlineTitle, setInternalInlineTitle] = useState('');
    const [isSubmittingInline, setIsSubmittingInline] = useState(false);

    const activeInlineStatus = quickAddStatus !== undefined ? quickAddStatus : internalInlineStatus;
    const activeInlineTitle = quickAddTitle !== undefined ? quickAddTitle : internalInlineTitle;

    const handleStartInlineAdd = (status: string) => {
        setInternalInlineStatus(status);
        setInternalInlineTitle('');
    };

    const handleInlineTitleChange = (v: string) => {
        setInternalInlineTitle(v);
        onQuickAddTitleChange?.(v);
    };

    const handleInlineConfirm = async (status: string) => {
        const title = activeInlineTitle.trim();
        if (!title) {
            setInternalInlineStatus(null);
            setInternalInlineTitle('');
            onQuickAddCancel?.();
            return;
        }
        if (onQuickAddConfirm) {
            onQuickAddConfirm();
            return;
        }
        setIsSubmittingInline(true);
        try {
            await createTask({
                title,
                status,
                priority: 'medium',
            });
            setInternalInlineTitle('');
            setInternalInlineStatus(null);
        } finally {
            setIsSubmittingInline(false);
        }
    };

    const handleInlineCancel = () => {
        setInternalInlineTitle('');
        setInternalInlineStatus(null);
        onQuickAddCancel?.();
    };

    const effectiveProjectId = projectId || tasks[0]?.project_id;

    useEffect(() => {
        let active = true;
        if (!effectiveProjectId || !token) return;
        apiFetch<(string | ProjectUserFavorite)[]>(`/projects/${effectiveProjectId}/favorites?entity_type=task`, { token })
            .then(favs => {
                if (active && Array.isArray(favs)) {
                    setFavoriteTaskIds(new Set(favs.map(f => typeof f === 'string' ? f : f.entity_id)));
                }
            })
            .catch(() => {});
        return () => { active = false; };
    }, [effectiveProjectId, token]);

    const displayedTasks = useMemo(() => {
        if (!onlyFavorites) return tasks;
        return tasks.filter(t => favoriteTaskIds.has(t.id));
    }, [tasks, onlyFavorites, favoriteTaskIds]);

    const handleChangeTask = useCallback((taskId: number | string, patch: Partial<ProjectTaskRecord>) => {
        onTaskUpdate?.(String(taskId), patch);
    }, [onTaskUpdate]);

    const statusOptions = buildStatusOptions(phaseDefs);
    const statusOrder = statusOptions.map(option => option.value.toLowerCase());
    const statusLabels = new Map(statusOptions.map(option => [option.value.toLowerCase(), option.label]));

    const groups = statusOrder.map(status => ({
        status,
        label: statusLabels.get(status) ?? status,
        tasks: displayedTasks.filter(t => (t.status ?? 'todo').toLowerCase() === status),
    })).filter(g => {
        const isTarget = activeInlineStatus === g.status;
        return g.tasks.length > 0 || isTarget;
    });

    const ungrouped = displayedTasks.filter(t => {
        const s = (t.status ?? 'todo').toLowerCase();
        return !statusOrder.includes(s);
    });

    return (
        <div className="h-full overflow-y-auto bg-[hsl(var(--surface-1))] scrollbar-thin">
            {/* ── TOOLBAR / FAVORITE FILTER ── */}
            <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                <button
                    type="button"
                    onClick={() => setOnlyFavorites(prev => !prev)}
                    className={clsx(
                        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all border',
                        onlyFavorites
                            ? 'bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))] border-[hsl(var(--warning)/0.3)] shadow-xs'
                            : 'text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--text-primary))]'
                    )}
                    title="Filtrar por tareas favoritas"
                >
                    <Star size={13} className={clsx(onlyFavorites ? 'fill-current text-[hsl(var(--warning-text))]' : '')} />
                    <span>Solo Mis Favoritas</span>
                    {favoriteTaskIds.size > 0 && (
                        <span className={clsx(
                            'px-1.5 py-0.5 rounded-full text-2xs font-bold',
                            onlyFavorites
                                ? 'bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))]'
                                : 'bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]'
                        )}>
                            {favoriteTaskIds.size}
                        </span>
                    )}
                </button>
                <span className="text-2xs text-[hsl(var(--text-secondary))]">
                    {displayedTasks.length} de {tasks.length} tareas
                </span>
            </div>

            {/* ── STICKY QUICK-ADD BAR ── */}
            <AnimatePresence>
                {quickAddStatus && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="overflow-hidden sticky top-0 z-30 border-b-2 border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.05)]"
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
                    statusLabel={g.label}
                    tasks={g.tasks}
                    onOpenTask={onOpenTask}
                    onAddTask={onAddTask}
                    onStartInlineAdd={() => handleStartInlineAdd(g.status)}
                    isFirst={i === 0}
                    onChangeTask={handleChangeTask}
                    phaseDefs={phaseDefs}
                    isAddingHere={activeInlineStatus === g.status}
                    quickAddTitle={activeInlineTitle}
                    onQuickAddTitleChange={handleInlineTitleChange}
                    onQuickAddConfirm={() => handleInlineConfirm(g.status)}
                    onQuickAddCancel={handleInlineCancel}
                    isSubmitting={isSubmittingInline}
                />
            ))}

            {ungrouped.length > 0 && (
                <StatusGroup
                    status="todo"
                    statusLabel="Otros"
                    tasks={ungrouped}
                    onOpenTask={onOpenTask}
                    onAddTask={onAddTask}
                    onStartInlineAdd={() => handleStartInlineAdd('todo')}
                    onChangeTask={handleChangeTask}
                    phaseDefs={phaseDefs}
                    isAddingHere={activeInlineStatus === 'todo'}
                    quickAddTitle={activeInlineTitle}
                    onQuickAddTitleChange={handleInlineTitleChange}
                    onQuickAddConfirm={() => handleInlineConfirm('todo')}
                    onQuickAddCancel={handleInlineCancel}
                    isSubmitting={isSubmittingInline}
                />
            )}

            {displayedTasks.length === 0 && (
                <div className="flex flex-col items-center justify-center py-8 gap-4">
                    <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] flex items-center justify-center">
                        <CheckCircle2 size={28} className="text-[hsl(var(--text-secondary))]" />
                    </div>
                    <div className="text-center">
                        <p className="text-sm font-bold text-[hsl(var(--text-secondary))]">
                            {onlyFavorites ? 'No tienes tareas favoritas en este proyecto' : 'Sin tareas en este proyecto'}
                        </p>
                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">
                            {onlyFavorites ? 'Marca tareas con la estrella para verlas aquí' : 'Haz clic en "+ Nuevo" para empezar'}
                        </p>
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
    const inputRef = useRef<HTMLInputElement>(null);
    useEffect(() => { setTimeout(() => inputRef.current?.focus(), 60); }, []);

    return (
        <div className="flex items-center gap-3 px-4 py-3 min-h-[40px]">
            <div className="size-5 rounded-full border-2 border-[hsl(var(--primary)/0.4)] shrink-0" />
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
                className="flex-1 text-base font-medium bg-transparent outline-none text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]"
            />
            <button
                onClick={onQuickAddConfirm}
                className="px-4 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-bold rounded-lg hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all shrink-0"
            >
                Guardar
            </button>
            <button
                onClick={onQuickAddCancel}
                aria-label="Cancelar tarea rápida"
                className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
            >
                <X size={14} />
            </button>
        </div>
    );
}

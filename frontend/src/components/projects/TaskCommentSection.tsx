"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord, ProjectCommentItem, ProjectCommentAttachment } from '@/types/projects';
import { Loader2, MessageSquare, Pin, Send, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';

interface Comment {
    id: string;
    author: string;
    authorColor?: string;
    text: string;
    timestamp: Date;
    attachments: ProjectCommentAttachment[];
    mentions?: string[];
    is_pinned?: boolean;
    pinned_at?: string | null;
    pinned_by?: string | null;
    pinner_name?: string | null;
}

const sortComments = (items: Comment[]): Comment[] => {
    return [...items].sort((a, b) => {
        if (Boolean(a.is_pinned) !== Boolean(b.is_pinned)) {
            return a.is_pinned ? -1 : 1;
        }
        return b.timestamp.getTime() - a.timestamp.getTime();
    });
};

export default function TaskCommentSection({
    task,
    token,
    onDeleteComment,
    onActivityCreated,
}: {
    task: ProjectTaskRecord;
    token: string | null;
    onDeleteComment: (commentId: string) => void;
    onActivityCreated?: () => void;
}) {
    const [comments, setComments] = useState<Comment[]>([]);
    const [commentInput, setCommentInput] = useState('');
    const [sendingComment, setSendingComment] = useState(false);
    const [loadingComments, setLoadingComments] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [mentionState, setMentionState] = useState<{ query: string; start: number } | null>(null);
    const [candidates, setCandidates] = useState<Array<{ id: string; name: string }>>([]);
    const [selectedMentions, setSelectedMentions] = useState<Array<{ id: string; name: string }>>([]);
    const [activeMentionIndex, setActiveMentionIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);

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

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setCommentInput(val);
        const pos = e.target.selectionStart ?? val.length;
        const before = val.slice(0, pos);
        const lastAt = before.lastIndexOf('@');
        if (lastAt !== -1) {
            const query = before.slice(lastAt + 1);
            if (!query.includes(' ')) {
                setMentionState({ query, start: lastAt });
                return;
            }
        }
        setMentionState(null);
    };

    const handleSelectMention = (candidate: { id: string; name: string }) => {
        if (!mentionState) return;
        const before = commentInput.slice(0, mentionState.start);
        const after = commentInput.slice(mentionState.start + 1 + mentionState.query.length);
        const next = `${before}@${candidate.name} ${after}`;
        setCommentInput(next);
        setSelectedMentions(prev => prev.some(m => m.id === candidate.id) ? prev : [...prev, candidate]);
        setMentionState(null);
        setTimeout(() => inputRef.current?.focus(), 20);
    };

    const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
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
            if (e.key === 'Enter' || e.key === 'Tab') {
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

        if (e.key === 'Enter' && !e.shiftKey) {
            handleSendComment();
        }
    };

    const loadComments = useCallback(async () => {
        if (!token) return;
        setLoadingComments(true);
        setError(null);
        try {
            const data = await apiFetch<ProjectCommentItem[]>(`/projects/comments?task_id=${task.id}`, { token });
            if (Array.isArray(data)) {
                const mapped: Comment[] = data.map((c: ProjectCommentItem) => ({
                    id: c.id,
                    author: c.author_name || 'Usuario',
                    text: c.content,
                    timestamp: new Date(c.created_at),
                    attachments: c.attachments || [],
                    mentions: c.mentions || [],
                    is_pinned: Boolean(c.is_pinned),
                    pinned_at: c.pinned_at,
                    pinned_by: c.pinned_by,
                    pinner_name: c.pinner_name,
                }));
                setComments(sortComments(mapped));
            }
        } catch {
            setError('No se pudieron cargar los comentarios de la tarea.');
        } finally { setLoadingComments(false); }
    }, [task.id, token]);

    useEffect(() => { loadComments(); }, [loadComments]);

    const handleTogglePin = async (comment: Comment) => {
        if (!token) return;
        const nextPinned = !comment.is_pinned;
        try {
            const res = await apiFetch<ProjectCommentItem>(
                `/projects/${task.project_id}/tasks/${task.id}/comments/${comment.id}/pin`,
                {
                    method: 'POST',
                    token,
                    body: { is_pinned: nextPinned },
                }
            );
            setComments(prev => {
                const updated = prev.map(c => c.id === comment.id ? {
                    ...c,
                    is_pinned: res.is_pinned ?? nextPinned,
                    pinned_at: res.pinned_at,
                    pinned_by: res.pinned_by,
                    pinner_name: res.pinner_name,
                } : c);
                return sortComments(updated);
            });
            toast.success(nextPinned ? 'Comentario fijado al inicio' : 'Comentario desfijado');
            onActivityCreated?.();
        } catch {
            toast.error('No se pudo actualizar la fijación del comentario.');
        }
    };

    const handleSendComment = async () => {
        if (!commentInput.trim() || !token) return;
        setSendingComment(true);
        try {
            const mentionIds = selectedMentions
                .filter(m => commentInput.includes(`@${m.name}`))
                .map(m => m.id);

            const created = await apiFetch<ProjectCommentItem>(`/projects/${task.project_id}/comments`, {
                method: 'POST',
                token,
                body: {
                    content: commentInput.trim(),
                    task_id: task.id,
                    mentions: mentionIds,
                },
            });
            const newComment: Comment = {
                id: created.id,
                author: created.author_name || 'Tú',
                text: created.content,
                timestamp: new Date(created.created_at),
                attachments: created.attachments || [],
                mentions: created.mentions || [],
                is_pinned: Boolean(created.is_pinned),
                pinned_at: created.pinned_at,
                pinned_by: created.pinned_by,
                pinner_name: created.pinner_name,
            };
            setComments(prev => sortComments([...prev, newComment]));
            setSelectedMentions([]);
            onActivityCreated?.();
        } catch {
            setError('No se pudo enviar el comentario.');
        } finally {
            setSendingComment(false);
            setCommentInput('');
        }
    };

    return (
        <section className="px-4 py-3">
            {error && (
                <div className="mb-2 rounded-md border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-2 text-[hsl(var(--warning))]">
                    <p className="text-2xs font-bold uppercase tracking-wide">{error}</p>
                </div>
            )}

            <p className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] mb-3 flex items-center gap-1.5">
                <MessageSquare size={11} /> Actividad
            </p>

            <div className="space-y-3 mb-4">
                {loadingComments && (
                    <p className="text-xs text-[hsl(var(--muted-foreground))] italic text-center py-2">
                        Cargando actividad...
                    </p>
                )}
                {!loadingComments && comments.length === 0 && (
                    <p className="text-xs text-[hsl(var(--muted-foreground))] italic text-center py-2">
                        Sin comentarios aún. Menciona a alguien con @
                    </p>
                )}
                {comments.map(c => (
                    <div
                        key={c.id}
                        className={clsx(
                            'flex gap-2.5 group p-2 rounded-lg transition-colors',
                            c.is_pinned
                                ? 'bg-[hsl(var(--warning)/0.06)] border border-[hsl(var(--warning)/0.25)] shadow-xs'
                                : 'hover:bg-[hsl(var(--surface-2)/0.4)]'
                        )}
                    >
                        <div
                            className="size-6 rounded-full flex items-center justify-center font-semibold text-[hsl(var(--primary-foreground))] shrink-0 mt-0.5"
                            style={{ backgroundColor: c.authorColor ?? 'hsl(var(--primary))' }}
                        >
                            {c.author.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                                <span className="text-sm font-bold text-[hsl(var(--foreground))]">{c.author}</span>
                                <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                                    {c.timestamp.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                                </span>
                                {c.is_pinned && (
                                    <span
                                        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-2xs font-bold uppercase tracking-wider bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))] border border-[hsl(var(--warning)/0.3)]"
                                        title={c.pinner_name ? `Fijado por ${c.pinner_name}` : 'Comentario fijado al inicio'}
                                    >
                                        <Pin size={9} className="rotate-45 fill-current" /> Fijado
                                    </span>
                                )}
                                <div className="ml-auto flex items-center gap-1">
                                    <button
                                        type="button"
                                        onClick={() => handleTogglePin(c)}
                                        title={c.is_pinned ? "Desfijar comentario" : "Fijar comentario al inicio"}
                                        aria-label={`${c.is_pinned ? 'Desfijar' : 'Fijar'} comentario de ${c.author}`}
                                        className={clsx(
                                            'transition-opacity transition-colors p-1 rounded hover:bg-[hsl(var(--surface-2))] opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100',
                                            c.is_pinned
                                                ? 'text-[hsl(var(--warning))]'
                                                : 'text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--warning))]'
                                        )}
                                    >
                                        <Pin size={12} className={c.is_pinned ? 'fill-current rotate-45' : ''} />
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => onDeleteComment(c.id)}
                                        title="Eliminar comentario"
                                        aria-label={`Eliminar comentario de ${c.author}`}
                                        className="opacity-100 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 transition-opacity p-1 rounded text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)]"
                                    >
                                        <Trash2 size={12} />
                                    </button>
                                </div>
                            </div>
                            <p className="text-sm text-[hsl(var(--foreground))] leading-relaxed">{c.text}</p>
                        </div>
                    </div>
                ))}
            </div>


            <div className="relative">
                {mentionState && filteredCandidates.length > 0 && (
                    <div
                        role="listbox"
                        data-testid="mention-autocomplete-list"
                        className="absolute left-8 right-0 bottom-full mb-1 z-50 max-h-40 overflow-y-auto rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-lg p-1 space-y-0.5"
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
                                        : "text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]"
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

                <div className="flex items-end gap-2">
                    <div className="size-6 rounded-full bg-[hsl(var(--primary))] flex items-center justify-center font-semibold text-[hsl(var(--primary-foreground))] shrink-0">
                        T
                    </div>
                    <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-md bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] focus-within:ring-2 focus-within:ring-[hsl(var(--primary)/0.2)] focus-within:border-[hsl(var(--primary))] transition-all">
                        <input
                            ref={inputRef}
                            type="text"
                            value={commentInput}
                            onChange={handleInputChange}
                            onKeyDown={handleInputKeyDown}
                            aria-label="Escribe un comentario"
                            placeholder="Menciona @Dzin para crear, encontrar y preguntar..."
                            className="flex-1 text-sm bg-transparent outline-none text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]"
                        />
                        {commentInput.trim() && (
                            <button
                                type="button"
                                onClick={handleSendComment}
                                disabled={sendingComment}
                                aria-label={sendingComment ? 'Enviando comentario' : 'Enviar comentario'}
                                className="text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors"
                            >
                                {sendingComment ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            </button>
                        )}
                    </div>
                </div>
            </div>

        </section>
    );
}

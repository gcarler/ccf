"use client";

import { useState, useCallback, useEffect } from 'react';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord, ProjectCommentItem } from '@/types/projects';
import { ChevronDown, Loader2, MessageSquare, Send, Trash2 } from 'lucide-react';

interface Comment {
    id: string;
    author: string;
    authorColor?: string;
    text: string;
    timestamp: Date;
}

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

    const loadComments = useCallback(async () => {
        if (!token) return;
        setLoadingComments(true);
        setError(null);
        try {
            const data = await apiFetch<ProjectCommentItem[]>(`/projects/comments?task_id=${task.id}`, { token });
            if (Array.isArray(data)) {
                setComments(data.map((c: ProjectCommentItem) => ({
                    id: c.id,
                    author: c.author_name || 'Usuario',
                    text: c.content,
                    timestamp: new Date(c.created_at),
                })));
            }
        } catch {
            setError('No se pudieron cargar los comentarios de la tarea.');
        } finally { setLoadingComments(false); }
    }, [task.id, token]);

    useEffect(() => { loadComments(); }, [loadComments]);

    const handleSendComment = async () => {
        if (!commentInput.trim() || !token) return;
        setSendingComment(true);
        try {
            const created = await apiFetch<ProjectCommentItem>(`/projects/${task.project_id}/comments`, {
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

    return (
        <section className="px-4 py-3">
            {error && (
                <div className="mb-2 rounded-md border border-[hsl(var(--warning)/25%)] bg-warning-soft p-2 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
                    <p className="text-[10px] font-bold uppercase tracking-wide">{error}</p>
                </div>
            )}

            <p className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-3 flex items-center gap-1.5">
                <MessageSquare size={11} /> Actividad
            </p>

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
                                    onClick={() => onDeleteComment(c.id)}
                                    title="Eliminar comentario"
                                    className="opacity-0 group-hover:opacity-100 transition-opacity text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))]"
                                >
                                    <Trash2 size={12} />
                                </button>
                            </div>
                            <p className="text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">{c.text}</p>
                        </div>
                    </div>
                ))}
            </div>

            <div className="flex items-end gap-2">
                <div className="size-6 rounded-full bg-[hsl(var(--primary))] flex items-center justify-center font-semibold text-white shrink-0">
                    T
                </div>
                <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/[0.04] border border-[hsl(var(--border))] dark:border-white/[0.07] focus-within:ring-2 focus-within:ring-[hsl(var(--primary))]/20 focus-within:border-[hsl(var(--info)/40%)]/40 transition-all">
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
                            {sendingComment ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                        </button>
                    )}
                </div>
            </div>

            <div className="flex items-center gap-2 mt-2 pl-8">
                <button className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold text-[hsl(var(--primary))] bg-info-soft dark:bg-[hsl(var(--info))]/10 border border-[hsl(var(--info)/25%)]/50 dark:border-[hsl(var(--info)/100%)]/20">
                    <MessageSquare size={9} /> Comentario
                    <ChevronDown size={9} />
                </button>
            </div>
        </section>
    );
}

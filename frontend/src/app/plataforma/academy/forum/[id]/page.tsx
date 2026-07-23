"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
    MessageSquare,
    ThumbsUp,
    ThumbsDown,
    CheckCircle2,
    Share2,
    MoreVertical,
    ChevronLeft,
    Send,
    Bot,
    Sparkles,
    ShieldCheck,
    Award
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import { motion } from 'framer-motion';
import clsx from 'clsx';

export default function ForumThreadDetail() {
    const params = useParams<{ id: string }>();
    const id = params?.id ?? '';
    const router = useRouter();
    const { token } = useAuth();
    const [thread, setThread] = useState<any>(null);
    const [replies, setReplies] = useState<any[]>([]);
    const [inputText, setInputText] = useState('');
    const [viewType, setViewType] = useState<ViewType>('list');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const ctrl = new AbortController();
        setLoading(true);

        const fetchThread = async () => {
            try {
                const data = await apiFetch<any>(`/academy/forum/threads/${id}`, { token, signal: ctrl.signal });
                setThread(data);
            } catch (err: any) {
                if (err?.name !== 'AbortError') {
                    toast.error('Error al cargar el debate');
                }
            }
        };

        const fetchReplies = async () => {
            try {
                const data = await apiFetch<any[]>(`/academy/forum/threads/${id}/comments`, { token, signal: ctrl.signal });
                setReplies((Array.isArray(data) ? data : []).map((c) => ({
                    ...c,
                    text: c.text || c.content || '',
                    time: c.time || (c.created_at ? new Date(c.created_at).toLocaleString('es-CO') : ''),
                    author: c.author || c.author_name || `Usuario ${c.author_id ?? ''}`.trim(),
                    upvotes: c.upvotes ?? 0,
                    is_accepted: c.is_accepted ?? false,
                    is_pastoral: c.is_pastoral ?? false,
                })));
            } catch (err: any) {
                if (err?.name !== 'AbortError') {
                    toast.error('Error al cargar las respuestas');
                }
            }
        };

        Promise.all([fetchThread(), fetchReplies()]).finally(() => setLoading(false));
        return () => ctrl.abort();
    }, [id, token]);

    const handleSendReply = async () => {
        if (!inputText.trim() || !token) return;
        const text = inputText;
        setInputText('');
        try {
            const created = await apiFetch<any>(`/academy/forum/threads/${id}/comments`, {
                method: 'POST',
                token,
                body: { content: text },
            });
            setReplies((prev) => [...prev, created]);
            toast.success('Respuesta publicada');
        } catch {
            setInputText(text);
            toast.error('Error al publicar la respuesta');
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]/50 dark:bg-[hsl(var(--surface-1))] overflow-hidden font-display">
                <WorkspaceToolbar
                    breadcrumbs={[
                        { label: 'Foro Academia', icon: MessageSquare },
                        { label: 'Detalle de Debate', icon: Share2 }
                    ]}
                    viewType={viewType}
                    setViewType={setViewType}
                    availableViews={['list', 'grid', 'table']}
                    rightActions={
                        <button onClick={() => router.back()} className="flex items-center gap-2 px-4 py-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all text-[11px] font-semibold uppercase tracking-wide">
                            <ChevronLeft size={16} /> Volver al Foro
                        </button>
                    }
                />
                <main className="flex-1 flex items-center justify-center">
                    <p className="text-sm font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide animate-pulse">Cargando...</p>
                </main>
            </div>
        );
    }

    if (!thread) return null;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]/50 dark:bg-[hsl(var(--surface-1))] overflow-hidden font-display">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Foro Academia', icon: MessageSquare },
                    { label: 'Detalle de Debate', icon: Share2 }
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['list', 'grid', 'table']}
                rightActions={
                    <button onClick={() => router.back()} className="flex items-center gap-2 px-4 py-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all text-[11px] font-semibold uppercase tracking-wide">
                        <ChevronLeft size={16} /> Volver al Foro
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4">
                {viewType === 'table' && (
 <div className="w-full overflow-x-auto rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-white/5">
                        <table className="w-full min-w-[480px] text-left">
                            <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                <tr>
                                    <th className="px-4 py-2">Autor</th>
                                    <th className="px-4 py-2">Respuesta</th>
                                    <th className="px-4 py-2">Votos</th>
                                    <th className="px-4 py-2">Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {replies.map((reply) => (
                                    <tr key={reply.id} className="border-t border-[hsl(var(--border))] dark:border-white/5">
                                        <td className="px-4 py-2 font-bold text-[hsl(var(--text-primary))] dark:text-white">{reply.author}</td>
                                        <td className="px-4 py-2 text-[hsl(var(--text-secondary))]">{reply.text}</td>
                                        <td className="px-4 py-2 text-[hsl(var(--text-secondary))]">{reply.upvotes}</td>
                                        <td className="px-4 py-2 text-[hsl(var(--text-secondary))]">{reply.is_accepted ? 'Mejor respuesta' : 'Abierta'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {viewType === 'grid' && (
 <div className="w-full grid gap-3 md:grid-cols-2">
                        {replies.map((reply) => (
                            <article key={reply.id} className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-white/5">
                                <div className="flex items-center justify-between gap-4">
                                    <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white">{reply.author}</h3>
                                    <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{reply.time}</span>
                                </div>
                                <p className="mt-4 text-sm leading-relaxed text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{reply.text}</p>
                            </article>
                        ))}
                    </div>
                )}

                {viewType === 'list' && (
 <div className="w-full space-y-4">
                    <section className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-3 shadow-xl space-y-3 relative overflow-hidden">
                        <div className="absolute top-0 right-0 -mr-12 -mt-3 size-10 bg-blue-600/5 rounded-full blur-3xl" />

                        <div className="relative z-10 flex flex-col gap-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <span className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] rounded-full text-[9px] font-semibold uppercase tracking-wide">{thread.category}</span>
                                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{thread.created_at}</span>
                                </div>
                                <button aria-label="Más opciones del debate" className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-colors"><MoreVertical size={20} aria-hidden="true" /></button>
                            </div>

                            <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight leading-tight">{thread.title}</h1>

                            <div className="p-4 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md border border-[hsl(var(--border))] dark:border-white/5">
                                <p className="text-[16px] leading-relaxed text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] font-medium">
                                    {thread.content}
                                </p>
                            </div>

                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="size-9 rounded-lg bg-[hsl(var(--bg-muted))] flex items-center justify-center text-white text-[10px] font-semibold uppercase">{thread.author.charAt(0)}</div>
                                    <div>
                                        <p className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase leading-none mb-1">{thread.author}</p>
                                        <p className="text-[10px] font-bold text-[hsl(var(--primary))] uppercase tracking-wide">{thread.author_role}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 bg-[hsl(var(--bg-primary))] dark:bg-white/5 p-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10">
                                    <button className="flex items-center gap-2 px-4 py-2 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 rounded-md font-semibold text-[hsl(var(--primary))] transition-all">
                                        <ThumbsUp size={16} /> {thread.upvotes}
                                    </button>
                                    <button className="p-2 text-[hsl(var(--text-secondary))] hover:text-rose-500 transition-all"><ThumbsDown size={16} /></button>
                                </div>
                            </div>
                        </div>
                    </section>

                    <section className="bg-blue-50 dark:bg-blue-900/10 rounded-lg p-3 border border-blue-100 dark:border-blue-500/20 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-10 -mt-3 size-10 bg-blue-600/10 rounded-full blur-3xl group-hover:bg-blue-600/20 transition-all duration-1000" />
                        <div className="relative z-10 flex gap-4 items-start">
                            <div className="size-9 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/20"><Bot size={24} className="text-white" /></div>
                            <div className="space-y-3">
                                <h4 className="font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] uppercase tracking-wide flex items-center gap-2">
                                    <Sparkles size={14} /> Optimus Teological Assistant
                                </h4>
                                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium italic">
                                    &ldquo;Basado en la hermenéutica clásica, Romanos 8:28 debe leerse en conexión con el verso 29. Esto sugiere que el bien es espiritual y eterno, más que circunstancial.&rdquo;
                                </p>
                            </div>
                        </div>
                    </section>

                    <div className="space-y-3 pb-4">
                        <h3 className="text-sm font-bold tracking-tight uppercase tracking-wide px-4 text-[hsl(var(--text-secondary))]">{replies.length} Respuestas</h3>
                        <div className="space-y-4">
                            {replies.map((reply) => (
                                <motion.div
                                    key={reply.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className={clsx(
                                        "p-4 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border rounded-md transition-all relative overflow-hidden",
                                        reply.is_accepted ? "border-emerald-500/30 shadow-emerald-500/5" : "border-[hsl(var(--border))] dark:border-white/10"
                                    )}
                                >
                                    {reply.is_accepted && (
                                        <div className="absolute top-0 right-0 p-4 opacity-10"><Award size={48} className="text-emerald-500" /></div>
                                    )}
                                    <div className="flex gap-4 items-start">
                                        <div className="flex flex-col items-center gap-2 shrink-0">
                                            <div className="size-8 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] font-black text-[10px] uppercase">{reply.author.charAt(0)}</div>
                                            {reply.is_pastoral && <ShieldCheck size={16} className="text-[hsl(var(--primary))]" />}
                                        </div>
                                        <div className="flex-1 space-y-4">
                                            <div className="flex justify-between items-center">
                                                <div>
                                                    <span className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase leading-none block mb-1">{reply.author}</span>
                                                    <span className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{reply.time}</span>
                                                </div>
                                                {reply.is_accepted && (
                                                    <span className="px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 rounded-full text-[9px] font-semibold uppercase tracking-wide flex items-center gap-1.5">
                                                        <CheckCircle2 size={12} /> Mejor Respuesta
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium leading-relaxed">{reply.text}</p>
                                            <div className="flex items-center gap-4 pt-4">
                                                <button aria-label={`Votar a favor (${reply.upvotes} votos)`} className="flex items-center gap-1.5 font-semibold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors uppercase"><ThumbsUp size={14} aria-hidden="true" /> {reply.upvotes}</button>
                                                <button aria-label={`Votar en contra`} className="p-2 text-[hsl(var(--text-secondary))] hover:text-rose-500 transition-all"><ThumbsDown size={16} aria-hidden="true" /></button>
                                                <button className="font-semibold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors uppercase">Responder</button>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>
                )}
            </main>

            <footer className="fixed bottom-0 left-0 right-0 md:left-64 z-20 p-4 bg-white/80 dark:bg-[hsl(var(--surface-1))]/80 backdrop-blur-xl border-t border-[hsl(var(--border))] dark:border-white/5">
                <div className="max-w-4xl mx-auto flex items-center gap-4 bg-[hsl(var(--surface-2))] dark:bg-black/20 rounded-md p-2 pl-6 pr-2 shadow-inner border border-[hsl(var(--border))] dark:border-white/10">
                    <input
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSendReply()}
                        placeholder="Añade tu comentario al debate..."
                        aria-label="Escribe tu respuesta al debate"
                        className="flex-1 bg-transparent border-none outline-none py-1.5 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white placeholder:text-[hsl(var(--text-secondary))]"
                    />
                    <button
                        onClick={handleSendReply}
                        aria-label="Publicar respuesta"
                        className="size-9 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] rounded-full flex items-center justify-center text-white shadow-xl shadow-blue-500/20 active:scale-90 transition-all"
                    >
                        <Send size={20} fill="currentColor" aria-hidden="true" />
                    </button>
                </div>
            </footer>
        </div>
    );
}

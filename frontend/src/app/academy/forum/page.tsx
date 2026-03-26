"use client";

import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Bell, Search, PlusCircle, MessageSquare, Grid, Book, History, Verified } from 'lucide-react';
import Link from 'next/link';
import AcademyDetailShell from '@/components/academy/AcademyDetailShell';
import { apiFetch } from '@/lib/http';
import type { CommunityBoardCard } from '@/types/community';
import { toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';

export default function TheologicalForum() {
    const { isAuthenticated, token, user } = useAuth();
    const [activeTab, setActiveTab] = useState('Todos');
    const [threads, setThreads] = useState<CommunityBoardCard[]>([]);
    const [loading, setLoading] = useState(true);
    const [composerOpen, setComposerOpen] = useState(false);
    const [formData, setFormData] = useState({ title: '', stage: 'General', description: '' });
    const [submitting, setSubmitting] = useState(false);

    const loadThreads = useCallback(async () => {
        if (!token) return;
        try {
            setLoading(true);
            const data = await apiFetch<CommunityBoardCard[]>(`/community/cards?column_id=academy-forum`, {
                token,
                cache: 'no-store',
            });
            setThreads(Array.isArray(data) && data.length ? data : []);
        } catch (err) {
            console.error(err);
            toast.error('No pudimos cargar el foro académico');
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        loadThreads();
    }, [loadThreads]);

    const categories = useMemo(() => {
        const unique = new Set<string>();
        threads.forEach((thread) => unique.add(thread.stage || 'General'));
        return ['Todos', ...Array.from(unique)];
    }, [threads]);

    const filteredThreads = useMemo(() => {
        if (activeTab === 'Todos') return threads;
        return threads.filter((thread) => (thread.stage || 'General') === activeTab);
    }, [threads, activeTab]);

    if (!isAuthenticated) return null;

    return (
        <AcademyDetailShell
            title="Foro teológico"
            description="Debates guiados por nivel de formación para fortalecer tu pensamiento bíblico."
            rightAction={
                <button className="flex items-center justify-center size-10 rounded-full bg-white/5 hover:bg-primary/20 transition-colors text-primary">
                    <Bell size={20} />
                </button>
            }
            variant="sky"
        >
            <div className="relative group mb-6">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                    <Search className="text-slate-500 group-focus-within:text-primary transition-colors" size={20} />
                </div>
                <input
                    className="w-full bg-slate-900/50 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm text-white placeholder-slate-500 focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all shadow-inner"
                    placeholder="Buscar debates teológicos..."
                    type="text"
                />
            </div>

             <div className="flex gap-3 overflow-x-auto hide-scrollbar pb-4">
                 {categories.map((tab) => (
                     <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`flex h-10 shrink-0 items-center justify-center gap-2 rounded-2xl px-5 text-xs font-bold uppercase tracking-widest transition-all whitespace-nowrap ${
                            activeTab === tab
                                ? 'bg-primary text-white shadow-lg shadow-primary/30 border border-primary/20'
                                : 'bg-slate-900 border border-white/5 text-slate-400 hover:text-white hover:border-white/20'
                        }`}
                    >
                        {tab === 'Todos' && <Grid size={14} />}
                        {tab !== 'Todos' && tab === 'Historia' && <History size={14} />}
                        {tab !== 'Todos' && tab === 'Doctrina' && <Verified size={14} />}
                        {tab !== 'Todos' && tab === 'Romanos 8' && <Book size={14} />}
                        {tab}
                    </button>
                ))}
            </div>

            <div className="space-y-5 animate-in fade-in slide-in-from-bottom-8 duration-700">
                <button
                    onClick={() => setComposerOpen(true)}
                    className="w-full flex items-center justify-center gap-3 bg-primary/10 text-primary h-14 rounded-2xl font-bold shadow-none active:scale-95 transition-transform border border-primary/20 hover:bg-primary hover:text-white group"
                >
                    <PlusCircle size={20} className="group-hover:rotate-90 transition-transform" />
                    <span className="uppercase tracking-widest text-[11px] font-black">Crear nuevo debate</span>
                </button>

                {loading && <p className="text-sm text-slate-500">Sincronizando discusiones...</p>}
                {!loading && filteredThreads.length === 0 && (
                    <p className="text-sm text-slate-400">No hay debates en esta categoría aún.</p>
                )}
                {filteredThreads.map((thread) => (
                    <Link
                        key={thread.id}
                        href={thread.link || '#'}
                        className="block bg-slate-900/50 backdrop-blur-xl border border-white/5 hover:border-primary/30 rounded-[2rem] p-6 shadow-xl transition-all group"
                    >
                        <div className="flex justify-between items-start mb-4">
                            <span className="text-[9px] font-black uppercase tracking-widest px-3 py-1.5 rounded-xl border bg-primary/10 text-primary border-primary/20">
                                {thread.stage || 'General'}
                            </span>
                            <span className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">{thread.priority}</span>
                        </div>
                        <h3 className="text-white font-bold text-xl leading-snug mb-2 group-hover:text-primary transition-colors">{thread.name}</h3>
                        <p className="text-slate-400 text-sm line-clamp-2 mb-5 leading-relaxed">{thread.comments || 'Aún no hay comentarios registrados.'}</p>
                        <div className="flex items-center justify-between border-t border-white/5 pt-4">
                            <div className="flex items-center gap-3">
                                <div className="size-8 rounded-full bg-slate-800 border border-white/20 shadow-inner text-xs font-black flex items-center justify-center">
                                    {thread.owner
                                        .split(' ')
                                        .map((part) => part[0])
                                        .slice(0, 2)
                                        .join('')}
                                </div>
                                <span className="text-slate-300 text-xs font-bold">{thread.owner}</span>
                            </div>
                            <div className="flex items-center gap-1.5 text-slate-500 group-hover:text-white transition-colors">
                                <MessageSquare size={16} />
                                <span className="text-xs font-black font-mono">{thread.status}</span>
                            </div>
                        </div>
                    </Link>
                ))}
            </div>
            <ComposeDialog
                open={composerOpen}
                onClose={() => setComposerOpen(false)}
                formData={formData}
                setFormData={setFormData}
                onSubmit={async () => {
                    if (!token) return;
                    if (!formData.title.trim()) {
                        toast.error('Agrega un título');
                        return;
                    }
                    setSubmitting(true);
                    try {
                        await apiFetch('/community/cards', {
                            method: 'POST',
                            token,
                            body: JSON.stringify({
                                column_id: 'academy-forum',
                                name: formData.title,
                                stage: formData.stage,
                                owner: user?.username || 'Docente',
                                comments: formData.description,
                                status: 'Abierto',
                                priority: 'Media',
                            }),
                        });
                        toast.success('Debate publicado');
                        setFormData({ title: '', stage: formData.stage, description: '' });
                        setComposerOpen(false);
                        await loadThreads();
                    } catch (err) {
                        console.error(err);
                        toast.error('No se pudo crear el debate');
                    } finally {
                        setSubmitting(false);
                    }
                }}
                submitting={submitting}
                stages={categories.filter((stage) => stage !== 'Todos')}
            />
        </AcademyDetailShell>
    );
}

function ComposeDialog({ open, onClose, formData, setFormData, onSubmit, submitting, stages }: any) {
    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.95, opacity: 0 }}
                        className="w-full max-w-md bg-[#0b0d11] border border-white/10 rounded-[2rem] p-6 space-y-4"
                    >
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-bold text-white">Nuevo debate</h3>
                            <button onClick={onClose} className="text-slate-400 hover:text-white">×</button>
                        </div>
                        <div className="space-y-3">
                            <input
                                value={formData.title}
                                onChange={(e) => setFormData((prev: any) => ({ ...prev, title: e.target.value }))}
                                placeholder="Título"
                                className="w-full rounded-xl bg-white/5 border border-white/10 px-4 py-3 text-sm text-white"
                            />
                            <select
                                value={formData.stage}
                                onChange={(e) => setFormData((prev: any) => ({ ...prev, stage: e.target.value }))}
                                className="w-full rounded-xl bg-white/5 border border-white/10 px-4 py-3 text-sm text-white"
                            >
                                {stages.map((stage: string) => (
                                    <option key={stage} value={stage}>{stage}</option>
                                ))}
                            </select>
                            <textarea
                                value={formData.description}
                                onChange={(e) => setFormData((prev: any) => ({ ...prev, description: e.target.value }))}
                                placeholder="Contexto y preguntas"
                                className="w-full rounded-xl bg-white/5 border border-white/10 px-4 py-3 text-sm text-white h-32"
                            />
                        </div>
                        <button
                            onClick={onSubmit}
                            disabled={submitting}
                            className="w-full flex items-center justify-center gap-2 bg-primary text-white rounded-2xl py-3 text-[11px] font-black uppercase tracking-[0.3em]"
                        >
                            {submitting ? 'Publicando...' : 'Publicar'}
                        </button>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

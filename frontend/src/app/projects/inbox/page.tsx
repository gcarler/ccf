"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    Inbox, MessageSquare, AtSign, CheckCircle2, MoreHorizontal, 
    ChevronRight, Clock, Star, Filter, Search, Shield, Layout,
    MessageCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Skeleton from '@/components/ui/Skeleton';

export default function ProjectsInboxPage() {
    const { token } = useAuth();
    const [messages, setMessages] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'mentions' | 'unread'>('all');

    useEffect(() => {
        const fetchInbox = async () => {
            if (!token) return;
            try {
                // Mocking data for UI
                const data = [
                    { id: 1, type: 'mention', user: 'Carlos Ernesto', content: '¿Puedes revisar el presupuesto de la Sede Norte?', project: 'Construcción', time: 'Hace 10m', is_read: false },
                    { id: 2, type: 'comment', user: 'Matias G.', content: 'He subido los planos actualizados al canal general.', project: 'Proyectos', time: 'Hace 1h', is_read: true },
                    { id: 3, type: 'update', user: 'System', content: 'Se ha completado el Hito 1 de Escuela de Líderes.', project: 'Academia', time: 'Ayer', is_read: true },
                ];
                setMessages(data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        };
        fetchInbox();
    }, [token]);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Inbox / Respuestas', icon: Inbox }]}
                viewType="list" setViewType={() => {}}
            />

            <div className="flex px-6 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shrink-0">
                <Tab active={filter === 'all'} onClick={() => setFilter('all')} label="Todo" />
                <Tab active={filter === 'unread'} onClick={() => setFilter('unread')} label="No leídos" />
                <Tab active={filter === 'mentions'} onClick={() => setFilter('mentions')} label="Menciones" />
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {loading ? (
                    <div className="p-8 space-y-4">
                        {[1,2,3].map(i => <Skeleton key={i} className="h-20 w-full rounded-2xl" />)}
                    </div>
                ) : (
                    <div className="divide-y divide-slate-100 dark:divide-white/5">
                        {messages.map((msg, idx) => (
                            <motion.div 
                                key={msg.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.05 }}
                                className={clsx(
                                    "p-6 flex gap-6 hover:bg-blue-50/30 dark:hover:bg-blue-500/5 transition-all cursor-pointer group relative",
                                    !msg.is_read && "bg-blue-50/50 dark:bg-blue-500/5"
                                )}
                            >
                                <div className="shrink-0 pt-1">
                                    <div className={clsx(
                                        "size-10 rounded-2xl flex items-center justify-center shadow-sm",
                                        msg.type === 'mention' ? "bg-purple-100 dark:bg-purple-900/30 text-purple-600" : "bg-blue-100 dark:bg-blue-900/30 text-blue-600"
                                    )}>
                                        {msg.type === 'mention' ? <AtSign size={20} /> : <MessageCircle size={20} />}
                                    </div>
                                </div>
                                <div className="flex-1 space-y-1">
                                    <div className="flex justify-between items-center">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[13px] font-black text-slate-800 dark:text-white uppercase tracking-tight">{msg.user}</span>
                                            <div className="size-1 rounded-full bg-slate-300" />
                                            <span className="text-[10px] font-black text-blue-600 uppercase tracking-widest">{msg.project}</span>
                                        </div>
                                        <span className="text-[10px] font-bold text-slate-400">{msg.time}</span>
                                    </div>
                                    <p className="text-[14px] text-slate-600 dark:text-slate-300 leading-relaxed font-medium">{msg.content}</p>
                                    <div className="pt-3 flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button className="px-3 py-1 bg-white dark:bg-white/10 border border-slate-200 dark:border-white/10 rounded-lg text-[10px] font-black uppercase text-slate-600 dark:text-slate-200">Responder</button>
                                        <button className="px-3 py-1 bg-blue-600 text-white rounded-lg text-[10px] font-black uppercase shadow-lg">Resolver</button>
                                    </div>
                                </div>
                                {!msg.is_read && <div className="absolute right-6 top-1/2 -translate-y-1/2 size-2 bg-blue-600 rounded-full shadow-[0_0_8px_rgba(37,99,235,0.5)]" />}
                            </motion.div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}

function Tab({ active, label, onClick }: any) {
    return (
        <button onClick={onClick} className={clsx("px-6 py-4 text-[11px] font-black uppercase tracking-widest transition-all border-b-2", active ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600")}>{label}</button>
    );
}

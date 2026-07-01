"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Bell, 
    Settings, Inbox, User, 
    Archive, CheckCircle2, Filter, Search
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket';
import { toast } from 'sonner';

export default function WorkspaceInbox({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    const { token, user } = useAuth();
    const [notifications, setNotifications] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'mentions' | 'assigned'>('all');

    const fetchNotifications = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/messaging/notifications', { token });
            if (Array.isArray(data)) setNotifications(data);
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => {
        if (isOpen) fetchNotifications();
    }, [isOpen, fetchNotifications]);

    const handleSocketEvent = useCallback((payload: any) => {
        if (payload?.event === 'notification:new' && payload.body) {
            setNotifications((prev) => {
                if (prev.some((item) => item.id === payload.body.id)) return prev;
                return [payload.body, ...prev];
            });
        }
    }, []);

    const { status: socketStatus } = useWorkspaceSocket({
        clientId: user?.id ? `user-${user.id}` : undefined,
        rooms: ['notifications'],
        enabled: isOpen,
        onEvent: handleSocketEvent
    });

    const handleClear = async (id: number) => {
        try {
            await apiFetch(`/messaging/notifications/${id}`, { method: 'PATCH', token });
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
            toast.success("Notificación marcada como leída");
        } catch (err) {
            toast.error("No se pudo actualizar");
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-x-0 bottom-0 top-10 z-[1000] bg-[hsl(var(--bg-muted))]/10 backdrop-blur-[2px]"
                    />
                    <motion.div 
                        initial={{ opacity: 0, x: 400 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 400 }}
                        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                        className="fixed top-10 right-0 h-[calc(100vh-2.5rem)] w-full max-w-[480px] bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] shadow-[-20px_0_60px_rgba(0,0,0,0.1)] border-l border-[hsl(var(--border))] dark:border-white/5 z-[1001] flex flex-col overflow-hidden"
                    >
                        {/* Header */}
                        <header className="h-8 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between px-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 shrink-0">
                            <div className="flex items-center gap-3">
                                <div className="size-8 rounded-md bg-[hsl(var(--primary))] flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
                                    <Inbox size={18} />
                                </div>
                                <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] tracking-tight">Inbox</h3>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className={clsx(
                                    'text-[10px] font-bold uppercase tracking-wide flex items-center gap-1',
                                    socketStatus === 'open'
                                        ? 'text-emerald-500'
                                        : socketStatus === 'connecting'
                                            ? 'text-amber-500'
                                            : socketStatus === 'error'
                                                ? 'text-rose-500'
                                                : 'text-[hsl(var(--text-secondary))]'
                                )}>
                                    <span className="size-2 rounded-full bg-current" />
                                    WS
                                </span>
                                <HeaderAction icon={CheckCircle2} tooltip="Marcar todo como leído" />
                                <HeaderAction icon={Filter} tooltip="Filtrar" />
                                <HeaderAction icon={Settings} tooltip="Ajustes" />
                                <div className="w-[1px] h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-2" />
                                <button onClick={onClose} className="p-2 hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 rounded-md transition-all text-[hsl(var(--text-secondary))]">
                                    <X size={20} />
                                </button>
                            </div>
                        </header>

                        {/* Search & Tabs */}
                        <div className="px-3 py-3 space-y-4">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={14} />
                                <input 
                                    type="text" placeholder="Buscar en notificaciones..." 
                                    className="w-full h-9 bg-[hsl(var(--surface-2))] dark:bg-black/20 border-transparent rounded-md pl-10 pr-4 text-[12px] font-medium focus:bg-[hsl(var(--bg-primary))] dark:focus:bg-black/40 focus:ring-2 focus:ring-blue-500/20 transition-all outline-none"
                                />
                            </div>
                            <div className="flex gap-1">
                                <Tab active={filter === 'all'} onClick={() => setFilter('all')} label="Todo" count={notifications.length} />
                                <Tab active={filter === 'mentions'} onClick={() => setFilter('mentions')} label="Menciones" />
                                <Tab active={filter === 'assigned'} onClick={() => setFilter('assigned')} label="Asignado" />
                            </div>
                        </div>

                        {/* List Area */}
                        <div className="flex-1 overflow-y-auto scrollbar-thin divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                            {loading ? (
                                <div className="p-3 space-y-4">
                                    {[1,2,3,4].map(i => <ShimmerNotification key={i} />)}
                                </div>
                            ) : notifications.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full text-center p-4 space-y-4">
                                    <div className="size-8 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-primary))]">
                                        <CheckCircle2 size={40} />
                                    </div>
                                    <div className="space-y-1">
                                        <h4 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Estás al día</h4>
                                        <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium">No tienes notificaciones pendientes de revisar.</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="pb-4">
                                    <div className="px-3 py-2 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 border-y border-[hsl(var(--border))] dark:border-white/5">
                                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Reciente</span>
                                    </div>
                                    {notifications.map((notif, idx) => (
                                        <motion.div 
                                            key={notif.id}
                                            initial={{ opacity: 0, x: 20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            className={clsx(
                                                "group relative px-3 py-2 flex gap-4 transition-all cursor-pointer",
                                                !notif.is_read ? "bg-blue-50/30 dark:bg-blue-500/5" : "hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
                                            )}
                                        >
                                            <div className="shrink-0 pt-1">
                                                <div className={clsx(
                                                    "size-10 rounded-lg flex items-center justify-center shadow-sm",
                                                    notif.notif_type === 'mention' ? "bg-sky-100 dark:bg-sky-900/30 text-sky-600" :
                                                    notif.notif_type === 'task' ? "bg-blue-100 dark:bg-blue-900/30 text-[hsl(var(--primary))]" :
                                                    "bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))]"
                                                )}>
                                                    {notif.notif_type === 'mention' ? <User size={20} /> : 
                                                     notif.notif_type === 'task' ? <CheckCircle2 size={20} /> : <Bell size={20} />}
                                                </div>
                                            </div>
                                            <div className="flex-1 space-y-1 overflow-hidden">
                                                <div className="flex justify-between items-start gap-2">
                                                    <h4 className="font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate tracking-tight">{notif.title}</h4>
                                                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] whitespace-nowrap">{new Date(notif.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                                                </div>
                                                <p className="text-[13px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium leading-relaxed line-clamp-2">{notif.content}</p>
                                                
                                                {/* Inline Actions */}
                                                <div className="pt-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button onClick={(e) => { e.stopPropagation(); handleClear(notif.id); }} className="px-3 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-white/10 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] transition-all">Archivar</button>
                                                    <button className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 active:scale-95 transition-all">Ver</button>
                                                </div>
                                            </div>
                                            {!notif.is_read && (
                                                <div className="absolute right-4 top-3 size-2 bg-[hsl(var(--primary))] rounded-full" />
                                            )}
                                        </motion.div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Multi-action footer */}
                        <footer className="p-4 border-t border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 flex justify-center">
                            <button className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors">
                                <Archive size={14} /> Ver archivo de notificaciones
                            </button>
                        </footer>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

function HeaderAction({ icon: Icon, tooltip }: any) {
    return (
        <button className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 rounded-md transition-all relative group/h">
            <Icon size={18} />
            <div className="absolute top-10 left-1/2 -translate-x-1/2 px-2 py-1 bg-[hsl(var(--bg-muted))] text-white text-[8px] font-semibold uppercase tracking-wide rounded opacity-0 group-hover/h:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-[200]">
                {tooltip}
            </div>
        </button>
    );
}

function Tab({ active, label, count, onClick }: any) {
    return (
        <button 
            onClick={onClick}
            className={clsx(
                "px-4 py-1.5 rounded-md text-[11px] font-semibold uppercase tracking-wide transition-all flex items-center gap-2",
                active ? "bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20" : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 hover:text-[hsl(var(--text-secondary))]"
            )}
        >
            {label}
            {count !== undefined && <span className={clsx("size-4 rounded-full flex items-center justify-center text-[9px]", active ? "bg-white/20 text-white" : "bg-[hsl(var(--surface-3))] dark:bg-white/10 text-[hsl(var(--text-secondary))]")}>{count}</span>}
        </button>
    );
}

function ShimmerNotification() {
    return (
        <div className="flex gap-4 animate-pulse">
            <div className="size-10 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5" />
            <div className="flex-1 space-y-2">
                <div className="h-4 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded w-1/3" />
                <div className="h-3 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded w-full" />
                <div className="h-3 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded w-2/3" />
            </div>
        </div>
    );
}

"use client";

import React, { useEffect, useMemo, useState } from 'react';
import {
    Bell,
    MessageSquare,
    CheckCircle2,
    AtSign,
    Layout,
    Search,
    Check,
    Clock,
    Bot,
    RefreshCw,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useNotifications } from '@/hooks/useNotifications';
import { NotificationKind, formatNotificationTime } from '@/lib/notifications';

type InboxFilter = 'all' | 'unread' | 'mention' | 'task' | 'ai';

const TYPE_CONFIG: Record<NotificationKind, { icon: React.ElementType; color: string; bg: string }> = {
    mention: { icon: AtSign, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    comment: { icon: MessageSquare, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    task: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
    system: { icon: Bell, color: 'text-slate-500', bg: 'bg-slate-100 dark:bg-white/5' },
    ai: { icon: Bot, color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-900/20' },
    reminder: { icon: Clock, color: 'text-orange-600', bg: 'bg-orange-50 dark:bg-orange-900/20' },
};

const FILTER_LABEL: Record<InboxFilter, string> = {
    all: 'Todo',
    unread: 'No leidos',
    mention: 'Menciones',
    task: 'Tareas',
    ai: 'MESH AI',
};

function hashToFilter(hash: string): InboxFilter {
    if (hash === '#menciones') return 'mention';
    if (hash === '#tareas') return 'task';
    if (hash === '#ai') return 'ai';
    return 'all';
}

export default function InboxPage() {
    const { user } = useAuth();
    const { notifications, loading, error, refresh, markRead, markAllRead } = useNotifications();
    const [filter, setFilter] = useState<InboxFilter>('all');
    const [search, setSearch] = useState('');

    useEffect(() => {
        const syncHash = () => setFilter(hashToFilter(window.location.hash));
        syncHash();
        window.addEventListener('hashchange', syncHash);
        return () => window.removeEventListener('hashchange', syncHash);
    }, []);

    const displayName = user?.username?.includes('@')
        ? user.username.split('@')[0]
        : user?.username || 'Miembro';

    const filtered = useMemo(() => notifications.filter((notification) => {
        if (filter === 'unread' && notification.read) return false;
        if (['mention', 'task', 'ai'].includes(filter) && notification.kind !== filter) return false;
        if (
            search &&
            !notification.title.toLowerCase().includes(search.toLowerCase()) &&
            !notification.body.toLowerCase().includes(search.toLowerCase())
        ) {
            return false;
        }
        return true;
    }), [filter, notifications, search]);

    const unreadCount = notifications.filter((notification) => !notification.read).length;

    return (
        <div className="h-full flex flex-col bg-white dark:bg-[#1E1F21] overflow-hidden font-display">
            <div className="h-12 border-b border-slate-100 dark:border-white/5 flex items-center px-6 gap-3 shrink-0 bg-slate-50/50 dark:bg-[#1E1F21]">
                <h1 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-700 dark:text-slate-300 flex items-center gap-2">
                    <Bell size={13} />
                    Bandeja de Entrada
                    {unreadCount > 0 && (
                        <span className="inline-flex items-center justify-center size-5 rounded-full bg-rose-500 text-white text-[9px] font-black">
                            {unreadCount}
                        </span>
                    )}
                </h1>
                <div className="flex-1" />

                <div className="relative">
                    <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                        type="text"
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Buscar..."
                        className="pl-8 pr-3 py-1.5 text-[11px] bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg outline-none focus:ring-2 focus:ring-blue-500/20 w-48 transition-all"
                    />
                </div>

                <div className="flex rounded-lg overflow-hidden border border-slate-200 dark:border-white/10">
                    {(['all', 'unread'] as const).map((item) => (
                        <button
                            key={item}
                            onClick={() => setFilter(item)}
                            className={clsx(
                                'px-3 py-1.5 text-[10px] font-black uppercase tracking-wide transition-colors',
                                filter === item
                                    ? 'bg-blue-600 text-white'
                                    : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200',
                            )}
                        >
                            {FILTER_LABEL[item]}
                        </button>
                    ))}
                </div>

                <button
                    onClick={() => void refresh()}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 transition-colors"
                >
                    <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                    Actualizar
                </button>

                {unreadCount > 0 && (
                    <button
                        onClick={() => void markAllRead()}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 transition-colors"
                    >
                        <Check size={12} />
                        Marcar todo como leido
                    </button>
                )}
            </div>

            <div className="px-6 py-2 border-b border-slate-100 dark:border-white/5 text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
                {FILTER_LABEL[filter]}
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-thin">
                <AnimatePresence initial={false}>
                    {loading ? (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex h-full items-center justify-center text-xs font-black uppercase tracking-[0.2em] text-slate-400"
                        >
                            Sincronizando notificaciones...
                        </motion.div>
                    ) : filtered.length === 0 ? (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex flex-col items-center justify-center h-full gap-4 text-center px-8"
                        >
                            <div className="size-16 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                                <Bell size={28} className="text-slate-300 dark:text-slate-600" />
                            </div>
                            <p className="text-sm font-bold text-slate-500">Sin notificaciones</p>
                            <p className="text-xs text-slate-400">Todo limpio por aqui, {displayName}.</p>
                            {error && <p className="text-xs font-semibold text-rose-500">{error}</p>}
                        </motion.div>
                    ) : (
                        <div className="divide-y divide-slate-50 dark:divide-white/[0.03]">
                            {filtered.map((notification, index) => {
                                const config = TYPE_CONFIG[notification.kind];
                                const Icon = config.icon;
                                return (
                                    <motion.button
                                        key={notification.id}
                                        type="button"
                                        initial={{ opacity: 0, x: -8 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, height: 0 }}
                                        transition={{ delay: index * 0.02 }}
                                        className={clsx(
                                            'w-full text-left flex items-start gap-4 px-6 py-4 group relative transition-colors',
                                            notification.read
                                                ? 'hover:bg-slate-50/50 dark:hover:bg-white/[0.02]'
                                                : 'bg-blue-50/30 dark:bg-blue-500/[0.04] hover:bg-blue-50/50 dark:hover:bg-blue-500/[0.07]',
                                        )}
                                        onClick={() => void markRead(notification.id)}
                                    >
                                        {!notification.read && (
                                            <div className="absolute left-2.5 top-1/2 -translate-y-1/2 size-1.5 rounded-full bg-blue-500" />
                                        )}

                                        <div className={clsx('size-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5', config.bg)}>
                                            <Icon size={16} className={config.color} />
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-0.5">
                                                <p
                                                    className={clsx(
                                                        'text-[13px] font-semibold truncate flex-1',
                                                        notification.read
                                                            ? 'text-slate-600 dark:text-slate-400'
                                                            : 'text-slate-900 dark:text-white font-bold',
                                                    )}
                                                >
                                                    {notification.title}
                                                </p>
                                                <span className="text-[10px] text-slate-400 shrink-0 font-medium">
                                                    {formatNotificationTime(notification.createdAt)}
                                                </span>
                                            </div>
                                            <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-snug line-clamp-2">
                                                {notification.body || 'Sin detalle adicional.'}
                                            </p>
                                            <div className="flex items-center gap-3 mt-2">
                                                <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
                                                    <Layout size={10} />
                                                    {notification.module}
                                                </span>
                                            </div>
                                        </div>
                                    </motion.button>
                                );
                            })}
                        </div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

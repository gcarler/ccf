"use client";

import React, { useState, useEffect } from 'react';
import {
    Bell, MessageSquare, CheckCircle2, AtSign, AlertCircle,
    Zap, Users, BookOpen, Layout, Calendar, MoreHorizontal,
    Check, Trash2, Filter, Search, Circle, Star, Archive,
    ChevronRight, Bot, TrendingUp, Clock, X, RefreshCcw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';

// ─── Types ──────────────────────────────────────────────────────────────────
type NotifType = 'mention' | 'comment' | 'task' | 'system' | 'ai' | 'reminder';

interface Notification {
    id: number;
    type: NotifType;
    title: string;
    body: string;
    time: string;
    read: boolean;
    starred: boolean;
    module: string;
    avatar?: string;
    sender?: string;
}

// ─── Mock notifications ──────────────────────────────────────────────────────
const INITIAL: Notification[] = [
    { id: 1,  type: 'mention',  title: 'Te mencionaron en un comentario',  body: '@admin ¿puedes revisar el reporte de Casas de Gloria esta semana?', time: 'Hace 5 min',    read: false, starred: true,  module: 'CRM',      sender: 'Carlos Díaz' },
    { id: 2,  type: 'task',     title: 'Tarea asignada a ti',               body: 'Llamar a visitantes nuevos — Sede Norte (vence hoy)', time: 'Hace 12 min',   read: false, starred: false, module: 'Tareas',    sender: 'Sistema' },
    { id: 3,  type: 'ai',       title: 'MESH AI tiene un hallazgo',         body: 'He detectado un patrón de reducción en la retención de visitantes (Sede Sur). ¿Deseas revisar el análisis?', time: 'Hace 20 min', read: false, starred: false, module: 'MESH AI' },
    { id: 4,  type: 'reminder', title: 'Recordatorio: Reunión hoy',         body: 'Reunión de liderazgo pastoral a las 7:00 PM en Sede Principal', time: 'Hace 1 hora',  read: false, starred: false, module: 'Calendario' },
    { id: 5,  type: 'comment',  title: 'Nuevo comentario en tarea',         body: 'La diapositiva del domingo quedó espectacular, gracias por el trabajo!', time: 'Hace 2 horas', read: true, starred: false, module: 'Proyectos', sender: 'Laura Méndez' },
    { id: 6,  type: 'system',   title: 'Academia: Nuevo módulo disponible', body: 'El módulo "Liderazgo Transformacional" ha sido publicado en la Academia Digital.', time: 'Hace 3 horas', read: true, starred: false, module: 'Academia' },
    { id: 7,  type: 'task',     title: 'Tarea completada por tu equipo',    body: 'Preparar diapositivas del domingo — Completada por Juan Ruiz', time: 'Hace 5 horas', read: true, starred: false, module: 'Proyectos', sender: 'Juan Ruiz' },
    { id: 8,  type: 'mention',  title: 'Mención en documento Wiki',         body: 'Se te ha asignado como responsable del protocolo de visitas.', time: 'Ayer', read: true, starred: false, module: 'Wiki', sender: 'Coord. Pastoral' },
];

const TYPE_CONFIG: Record<NotifType, { icon: React.ElementType; color: string; bg: string }> = {
    mention:  { icon: AtSign,       color: 'text-violet-600', bg: 'bg-violet-50 dark:bg-violet-900/20' },
    comment:  { icon: MessageSquare,color: 'text-blue-600',   bg: 'bg-blue-50 dark:bg-blue-900/20' },
    task:     { icon: CheckCircle2, color: 'text-emerald-600',bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
    system:   { icon: Bell,         color: 'text-slate-500',  bg: 'bg-slate-100 dark:bg-white/5' },
    ai:       { icon: Bot,          color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-900/20' },
    reminder: { icon: Clock,        color: 'text-orange-600', bg: 'bg-orange-50 dark:bg-orange-900/20' },
};

export default function InboxPage() {
    const { user } = useAuth();
    const [notifications, setNotifications] = useState(INITIAL);
    const [filter, setFilter] = useState<'all' | 'unread' | 'starred'>('all');
    const [search, setSearch] = useState('');
    const [selected, setSelected] = useState<number[]>([]);

    const displayName = user?.username?.includes('@')
        ? user.username.split('@')[0]
        : user?.username || 'Miembro';

    const filtered = notifications.filter(n => {
        if (filter === 'unread' && n.read) return false;
        if (filter === 'starred' && !n.starred) return false;
        if (search && !n.title.toLowerCase().includes(search.toLowerCase()) && !n.body.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    });

    const unreadCount = notifications.filter(n => !n.read).length;

    const markAllRead = () => setNotifications(prev => prev.map(n => ({ ...n, read: true })));

    const toggleRead = (id: number) =>
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: !n.read } : n));

    const toggleStar = (id: number) =>
        setNotifications(prev => prev.map(n => n.id === id ? { ...n, starred: !n.starred } : n));

    const deleteNotif = (id: number) =>
        setNotifications(prev => prev.filter(n => n.id !== id));

    return (
        <div className="h-full flex flex-col bg-white dark:bg-[#141517] overflow-hidden font-display">

                {/* Subheader */}
                <div className="h-12 border-b border-slate-100 dark:border-white/5 flex items-center px-6 gap-3 shrink-0 bg-slate-50/50 dark:bg-[#141517]">
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

                    {/* Search */}
                    <div className="relative">
                        <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar..."
                            className="pl-8 pr-3 py-1.5 text-[11px] bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg outline-none focus:ring-2 focus:ring-blue-500/20 w-48 transition-all"
                        />
                    </div>

                    {/* Filter pills */}
                    <div className="flex rounded-lg overflow-hidden border border-slate-200 dark:border-white/10">
                        {(['all', 'unread', 'starred'] as const).map(f => (
                            <button
                                key={f}
                                onClick={() => setFilter(f)}
                                className={clsx(
                                    'px-3 py-1.5 text-[10px] font-black uppercase tracking-wide transition-colors',
                                    filter === f
                                        ? 'bg-blue-600 text-white'
                                        : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                                )}
                            >
                                {f === 'all' ? 'Todo' : f === 'unread' ? 'No leídos' : 'Guardados'}
                            </button>
                        ))}
                    </div>

                    {unreadCount > 0 && (
                        <button
                            onClick={markAllRead}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 transition-colors"
                        >
                            <Check size={12} />
                            Marcar todo como leído
                        </button>
                    )}
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto scrollbar-thin">
                    <AnimatePresence initial={false}>
                        {filtered.length === 0 ? (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="flex flex-col items-center justify-center h-full gap-4 text-center px-8"
                            >
                                <div className="size-16 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center">
                                    <Bell size={28} className="text-slate-300 dark:text-slate-600" />
                                </div>
                                <p className="text-sm font-bold text-slate-500">Sin notificaciones</p>
                                <p className="text-xs text-slate-400">Todo limpio por aquí, {displayName} 🎉</p>
                            </motion.div>
                        ) : (
                            <div className="divide-y divide-slate-50 dark:divide-white/[0.03]">
                                {filtered.map((notif, idx) => {
                                    const cfg = TYPE_CONFIG[notif.type];
                                    const Icon = cfg.icon;
                                    return (
                                        <motion.div
                                            key={notif.id}
                                            initial={{ opacity: 0, x: -8 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            exit={{ opacity: 0, height: 0 }}
                                            transition={{ delay: idx * 0.02 }}
                                            className={clsx(
                                                'flex items-start gap-4 px-6 py-4 cursor-pointer group relative transition-colors',
                                                notif.read
                                                    ? 'hover:bg-slate-50/50 dark:hover:bg-white/[0.02]'
                                                    : 'bg-blue-50/30 dark:bg-blue-500/[0.04] hover:bg-blue-50/50 dark:hover:bg-blue-500/[0.07]'
                                            )}
                                            onClick={() => toggleRead(notif.id)}
                                        >
                                            {/* Unread dot */}
                                            {!notif.read && (
                                                <div className="absolute left-2.5 top-1/2 -translate-y-1/2 size-1.5 rounded-full bg-blue-500" />
                                            )}

                                            {/* Icon */}
                                            <div className={clsx('size-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5', cfg.bg)}>
                                                <Icon size={16} className={cfg.color} />
                                            </div>

                                            {/* Content */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-0.5">
                                                    <p className={clsx(
                                                        'text-[13px] font-semibold truncate flex-1',
                                                        notif.read ? 'text-slate-600 dark:text-slate-400' : 'text-slate-900 dark:text-white font-bold'
                                                    )}>
                                                        {notif.title}
                                                    </p>
                                                    <span className="text-[10px] text-slate-400 shrink-0 font-medium">{notif.time}</span>
                                                </div>
                                                <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-snug line-clamp-2">
                                                    {notif.body}
                                                </p>
                                                <div className="flex items-center gap-3 mt-2">
                                                    <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
                                                        <Layout size={10} />
                                                        {notif.module}
                                                    </span>
                                                    {notif.sender && (
                                                        <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
                                                            <Users size={10} />
                                                            {notif.sender}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Actions (visible on hover) */}
                                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                                                <button
                                                    onClick={e => { e.stopPropagation(); toggleStar(notif.id); }}
                                                    className={clsx(
                                                        'p-1.5 rounded-lg transition-colors',
                                                        notif.starred
                                                            ? 'text-amber-500 bg-amber-50 dark:bg-amber-900/20'
                                                            : 'text-slate-300 hover:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20'
                                                    )}
                                                >
                                                    <Star size={13} fill={notif.starred ? 'currentColor' : 'none'} />
                                                </button>
                                                <button
                                                    onClick={e => { e.stopPropagation(); deleteNotif(notif.id); }}
                                                    className="p-1.5 rounded-lg text-slate-300 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"
                                                >
                                                    <X size={13} />
                                                </button>
                                            </div>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        )}
                    </AnimatePresence>
                </div>
        </div>
    );
}


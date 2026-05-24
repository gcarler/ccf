"use client";

import React from 'react';
import { useAuth } from '@/context/AuthContext';
import { Bell, Calendar, Users, CheckCircle2, MessageSquare, Inbox, Bot, RefreshCw } from 'lucide-react';
import { useToast } from '@/context/ToastContext';
import { motion } from 'framer-motion';
import { useNotifications } from '@/hooks/useNotifications';
import { NotificationKind, formatNotificationTime, isRecentNotification } from '@/lib/notifications';

const TYPE_ICON: Record<NotificationKind, React.ReactNode> = {
    mention: <Users size={18} />,
    comment: <MessageSquare size={18} />,
    task: <CheckCircle2 size={18} />,
    system: <Bell size={18} />,
    ai: <Bot size={18} />,
    reminder: <Calendar size={18} />,
};

const TYPE_COLOR: Record<NotificationKind, string> = {
    mention: 'text-indigo-500 bg-indigo-500/10',
    comment: 'text-blue-500 bg-blue-500/10',
    task: 'text-emerald-500 bg-emerald-500/10',
    system: 'text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)]',
    ai: 'text-violet-500 bg-violet-500/10',
    reminder: 'text-amber-500 bg-amber-500/10',
};

export default function NotificationsCenter() {
    const { isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const { notifications, loading, error, refresh, markRead, markAllRead } = useNotifications();

    if (!isAuthenticated) return null;

    const recent = notifications.filter((notification) => isRecentNotification(notification.createdAt));
    const previous = notifications.filter((notification) => !isRecentNotification(notification.createdAt));

    const handleMarkAllRead = async () => {
        await markAllRead();
        addToast('Todas las notificaciones marcadas como leidas', 'success');
    };

    return (
 <div className="p-4 lg:p-4 animate-in fade-in duration-700 w-full">
            <header className="flex items-center justify-between mb-3">
                <div>
                    <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tighter">Centro de Notificaciones</h1>
                    <p className="text-[hsl(var(--text-secondary))] text-sm font-medium mt-1">Mantente al tanto de lo que sucede en tu comunidad</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => void refresh()}
                        className="px-4 py-2 hover:bg-[hsl(var(--surface-2))] rounded-md font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide transition-colors flex items-center gap-2"
                    >
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        Actualizar
                    </button>
                    <button
                        onClick={() => void handleMarkAllRead()}
                        className="px-4 py-2 hover:bg-[hsl(var(--surface-2))] rounded-md font-semibold text-[hsl(var(--primary))] uppercase tracking-wide transition-colors flex items-center gap-2"
                    >
                        <CheckCircle2 size={14} />
                        Marcar todo como leido
                    </button>
                </div>
            </header>

            {error && (
                <div className="mb-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-1.5 text-sm font-semibold text-rose-600">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="py-1.5 text-center text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                    Sincronizando notificaciones...
                </div>
            ) : notifications.length > 0 ? (
                <div className="space-y-3">
                    <NotificationSection title="Hoy" notifications={recent} onOpen={markRead} />
                    <NotificationSection title="Anteriormente" notifications={previous} onOpen={markRead} faded />
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-1.5 text-center space-y-3">
                    <div className="size-10 rounded-md bg-[hsl(var(--surface-2))] flex items-center justify-center text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] animate-pulse">
                        <Inbox size={40} />
                    </div>
                    <div className="space-y-1">
                        <h4 className="text-[hsl(var(--text-primary))] font-semibold uppercase tracking-wider">Bandeja Limpia</h4>
                        <p className="text-[hsl(var(--text-secondary))] text-xs font-medium max-w-[240px]">Todo al dia. Te notificaremos cuando ocurra algo nuevo.</p>
                    </div>
                </div>
            )}
        </div>
    );
}

function NotificationSection({
    title,
    notifications,
    onOpen,
    faded = false,
}: {
    title: string;
    notifications: ReturnType<typeof useNotifications>['notifications'];
    onOpen: (id: number) => Promise<void>;
    faded?: boolean;
}) {
    if (notifications.length === 0) return null;

    return (
        <section>
            <div className="flex items-center gap-4 mb-3">
                <h3 className="text-[hsl(var(--text-secondary))] text-[10px] font-semibold uppercase tracking-wide">{title}</h3>
                <div className="h-px flex-1 bg-[hsl(var(--border))] opacity-50" />
            </div>

            <div className="space-y-3">
                {notifications.map((notification, index) => (
                    <motion.button
                        type="button"
                        initial={{ opacity: 0, x: faded ? 0 : -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: (faded ? 0.3 : 0) + index * 0.1 }}
                        key={notification.id}
                        onClick={() => void onOpen(notification.id)}
                        className={`w-full text-left group surface-card p-3 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] flex gap-4 cursor-pointer hover:bg-[hsl(var(--surface-2))] transition-all relative ${
                            !notification.read ? 'border-l-4 border-l-[hsl(var(--primary))]' : ''
                        } ${faded ? 'opacity-80 hover:opacity-100' : ''}`}
                    >
                        <div className={`size-9 rounded-lg flex items-center justify-center shrink-0 shadow-inner group-hover:scale-110 transition-transform ${TYPE_COLOR[notification.kind]}`}>
                            {TYPE_ICON[notification.kind]}
                        </div>
                        <div className="flex-1 pr-8">
                            <div className="flex justify-between items-start mb-1">
                                <h4 className={`text-sm font-bold tracking-tight ${!notification.read ? 'text-[hsl(var(--text-primary))]' : 'text-[hsl(var(--text-secondary))]'}`}>
                                    {notification.title}
                                </h4>
                                <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                    {formatNotificationTime(notification.createdAt)}
                                </span>
                            </div>
                            <p className="text-[12px] text-[hsl(var(--text-secondary))] leading-relaxed font-medium">
                                {notification.body || 'Sin detalle adicional.'}
                            </p>
                        </div>
                        {!notification.read && (
                            <div className="absolute top-1/2 right-6 -translate-y-1/2">
                                <div className="size-2 rounded-full bg-[hsl(var(--primary))] shadow-[0_0_12px_hsl(var(--primary)/0.5)]" />
                            </div>
                        )}
                    </motion.button>
                ))}
            </div>
        </section>
    );
}

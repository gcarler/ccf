"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Bell, Heart, BookOpen, Calendar, Users, CheckCircle2, MessageSquare, Inbox } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

interface Notification {
    id: string;
    title: string;
    message: string;
    time: string;
    type: 'announcement' | 'prayer' | 'sermon' | 'event' | 'group';
    isRead: boolean;
}

import { motion } from 'framer-motion';

export default function NotificationsCenter() {
    const { isAuthenticated, user } = useAuth();
    const router = useRouter();
    const { addToast } = useToast();

    const [notifications, setNotifications] = useState<Notification[]>([
        {
            id: '1',
            title: 'Nuevo Anuncio de la Iglesia',
            message: 'No te pierdas el servicio especial de este domingo a las 10:00 AM. Tendremos invitados especiales.',
            time: 'Hace 15 min',
            type: 'announcement',
            isRead: false
        },
        {
            id: '2',
            title: 'Alguien oró por ti',
            message: 'Un miembro de la congregación ha respondido a tu petición de oración con un "Amén".',
            time: 'Hace 2 horas',
            type: 'prayer',
            isRead: false
        },
        {
            id: '3',
            title: 'Nuevo Sermón disponible',
            message: '"Caminando por Fe" - Pastor David García. Ya puedes escucharlo en la sección de Sermones.',
            time: 'Ayer, 08:30 PM',
            type: 'sermon',
            isRead: true
        },
        {
            id: '4',
            title: 'Recordatorio de Evento',
            message: 'Mañana es la reunión de jóvenes a las 7:00 PM en el salón principal.',
            time: '20 Oct, 10:00 AM',
            type: 'event',
            isRead: true
        },
        {
            id: '5',
            title: 'Bienvenido al Grupo de Estudio',
            message: 'Has sido añadido al grupo "Fundamentos de la Fe - Martes".',
            time: '19 Oct, 04:15 PM',
            type: 'group',
            isRead: true
        }
    ]);

    if (!isAuthenticated) return null;

    const markAllAsRead = () => {
        setNotifications(notifications.map(n => ({ ...n, isRead: true })));
        addToast('Todas las notificaciones marcadas como leídas', 'success');
    };

    const getIcon = (type: string) => {
        switch (type) {
            case 'announcement': return <Bell size={18} />;
            case 'prayer': return <Heart size={18} />;
            case 'sermon': return <BookOpen size={18} />;
            case 'event': return <Calendar size={18} />;
            case 'group': return <Users size={18} />;
            default: return <MessageSquare size={18} />;
        }
    };

    const getTypeColor = (type: string) => {
        switch (type) {
            case 'announcement': return 'text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)]';
            case 'prayer': return 'text-rose-500 bg-rose-500/10';
            case 'sermon': return 'text-emerald-500 bg-emerald-500/10';
            case 'event': return 'text-amber-500 bg-amber-500/10';
            case 'group': return 'text-indigo-500 bg-indigo-500/10';
            default: return 'text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-3))]';
        }
    };

    return (
        <div className="p-8 lg:p-12 animate-in fade-in duration-700 max-w-4xl mx-auto">
            {/* Header Section */}
            <header className="flex items-center justify-between mb-12">
                <div>
                    <h1 className="text-3xl font-black text-[hsl(var(--text-primary))] tracking-tighter">Centro de Notificaciones</h1>
                    <p className="text-[hsl(var(--text-secondary))] text-sm font-medium mt-1">Mantente al tanto de lo que sucede en tu comunidad</p>
                </div>
                <button
                    onClick={markAllAsRead}
                    className="px-4 py-2 hover:bg-[hsl(var(--surface-2))] rounded-xl text-[10px] font-black text-[hsl(var(--primary))] uppercase tracking-widest transition-colors flex items-center gap-2"
                >
                    <CheckCircle2 size={14} />
                    Marcar todo como leído
                </button>
            </header>

            <div className="space-y-12">
                {/* Today Section */}
                <section>
                    <div className="flex items-center gap-4 mb-6">
                        <h3 className="text-[hsl(var(--text-secondary))] text-[10px] font-black uppercase tracking-[0.2em]">Hoy</h3>
                        <div className="h-px flex-1 bg-[hsl(var(--border))] opacity-50"></div>
                    </div>
                    
                    <div className="space-y-3">
                        {notifications.filter(n => n.time.includes('min') || n.time.includes('horas')).map((notif, idx) => (
                            <motion.div
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                key={notif.id}
                                className={`group surface-card p-5 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] flex gap-6 cursor-pointer hover:bg-[hsl(var(--surface-2))] transition-all relative ${!notif.isRead ? 'border-l-4 border-l-[hsl(var(--primary))]' : ''}`}
                            >
                                <div className={`size-12 rounded-2xl flex items-center justify-center shrink-0 shadow-inner group-hover:scale-110 transition-transform ${getTypeColor(notif.type)}`}>
                                    {getIcon(notif.type)}
                                </div>
                                <div className="flex-1 pr-8">
                                    <div className="flex justify-between items-start mb-1">
                                        <h4 className={`text-sm font-black tracking-tight ${!notif.isRead ? 'text-[hsl(var(--text-primary))]' : 'text-[hsl(var(--text-secondary))]'}`}>{notif.title}</h4>
                                        <span className="text-[9px] font-black text-[hsl(var(--text-secondary))] uppercase tracking-widest">{notif.time}</span>
                                    </div>
                                    <p className="text-[12px] text-[hsl(var(--text-secondary))] leading-relaxed font-medium">{notif.message}</p>
                                </div>
                                {!notif.isRead && (
                                    <div className="absolute top-1/2 right-6 -translate-y-1/2">
                                        <div className="size-2 rounded-full bg-[hsl(var(--primary))] shadow-[0_0_12px_hsl(var(--primary)/0.5)]"></div>
                                    </div>
                                )}
                            </motion.div>
                        ))}
                    </div>
                </section>

                {/* Previously Section */}
                <section>
                    <div className="flex items-center gap-4 mb-6">
                        <h3 className="text-[hsl(var(--text-secondary))] text-[10px] font-black uppercase tracking-[0.2em]">Anteriormente</h3>
                        <div className="h-px flex-1 bg-[hsl(var(--border))] opacity-50"></div>
                    </div>
                    
                    <div className="space-y-3">
                        {notifications.filter(n => !n.time.includes('min') && !n.time.includes('horas')).map((notif, idx) => (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.3 + idx * 0.1 }}
                                key={notif.id}
                                className="group surface-card p-5 bg-[hsl(var(--surface-1))/0.4] border-[hsl(var(--border))] flex gap-6 cursor-pointer hover:bg-[hsl(var(--surface-2))] transition-all grayscale-[0.5] opacity-80 hover:grayscale-0 hover:opacity-100"
                            >
                                <div className="size-12 rounded-2xl bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-secondary))] shrink-0 border border-[hsl(var(--border))] group-hover:scale-110 transition-transform">
                                    {getIcon(notif.type)}
                                </div>
                                <div className="flex-1">
                                    <div className="flex justify-between items-start mb-1">
                                        <h4 className="text-sm font-bold text-[hsl(var(--text-secondary))] tracking-tight">{notif.title}</h4>
                                        <span className="text-[9px] font-black text-[hsl(var(--text-secondary))] uppercase tracking-widest">{notif.time}</span>
                                    </div>
                                    <p className="text-[12px] text-[hsl(var(--text-secondary))] leading-relaxed font-medium">{notif.message}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </section>
            </div>

            {/* Empty State */}
            {notifications.length === 0 && (
                <div className="flex flex-col items-center justify-center py-24 text-center space-y-6">
                    <div className="size-24 rounded-[2.5rem] bg-[hsl(var(--surface-2))] flex items-center justify-center text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] animate-pulse">
                        <Inbox size={40} />
                    </div>
                    <div className="space-y-1">
                        <h4 className="text-[hsl(var(--text-primary))] font-black uppercase tracking-[0.1em]">Bandeja Limpia</h4>
                        <p className="text-[hsl(var(--text-secondary))] text-xs font-medium max-w-[240px]">Todo al día. Te notificaremos cuando ocurra algo nuevo.</p>
                    </div>
                </div>
            )}
        </div>
    );
}


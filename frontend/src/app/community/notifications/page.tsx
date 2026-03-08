"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Bell, Heart, BookOpen, Calendar, Users, ArrowLeft, CheckCircle2, MessageSquare } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

interface Notification {
    id: string;
    title: string;
    message: string;
    time: string;
    type: 'announcement' | 'prayer' | 'sermon' | 'event' | 'group';
    isRead: boolean;
}

export default function NotificationsCenter() {
    const { isAuthenticated } = useAuth();
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
            case 'announcement': return <Bell size={20} />;
            case 'prayer': return <Heart size={20} />;
            case 'sermon': return <BookOpen size={20} />;
            case 'event': return <Calendar size={20} />;
            case 'group': return <Users size={20} />;
            default: return <MessageSquare size={20} />;
        }
    };

    const getTypeColor = (type: string) => {
        switch (type) {
            case 'announcement': return 'text-primary bg-primary/10';
            case 'prayer': return 'text-rose-500 bg-rose-500/10';
            case 'sermon': return 'text-emerald-500 bg-emerald-500/10';
            case 'event': return 'text-amber-500 bg-amber-500/10';
            case 'group': return 'text-indigo-500 bg-indigo-500/10';
            default: return 'text-slate-500 bg-slate-500/10';
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 left-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_left,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-60 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 py-6 border-b border-white/5 flex flex-col gap-4">
                    <div className="flex items-center justify-between">
                        <button onClick={() => router.back()} className="text-slate-400 flex size-10 items-center justify-center rounded-full bg-white/5 hover:bg-primary/20 hover:text-primary transition-all cursor-pointer">
                            <ArrowLeft size={18} />
                        </button>
                        <h2 className="text-white text-lg font-black tracking-tight flex-1 text-center pr-10">Notificaciones</h2>
                    </div>
                    <div className="flex justify-end pr-2">
                        <button
                            onClick={markAllAsRead}
                            className="text-[10px] font-black text-primary uppercase tracking-[0.2em] hover:text-primary-400 transition-colors"
                        >
                            Marcar todo como leído
                        </button>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto hide-scrollbar pt-6 px-6 pb-32 animate-in fade-in slide-in-from-bottom-8 duration-700">

                    {/* Today Section */}
                    <section className="mb-10">
                        <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-[0.3em] mb-6 pl-2 flex items-center gap-3">
                            Hoy
                            <div className="h-px flex-1 bg-white/5"></div>
                        </h3>
                        <div className="space-y-4">
                            {notifications.filter(n => n.time.includes('min') || n.time.includes('horas')).map((notif) => (
                                <div
                                    key={notif.id}
                                    className={`relative bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-5 flex gap-5 group transition-all hover:bg-slate-900/60 hover:border-white/10 ${!notif.isRead ? 'shadow-[0_0_20px_rgba(66,66,240,0.1)]' : ''}`}
                                >
                                    {!notif.isRead && (
                                        <div className="absolute top-5 right-5">
                                            <div className="size-2 rounded-full bg-primary shadow-[0_0_8px_#4242f0] animate-pulse"></div>
                                        </div>
                                    )}
                                    <div className={`size-12 rounded-2xl flex items-center justify-center shrink-0 shadow-inner group-hover:scale-110 transition-transform ${getTypeColor(notif.type)}`}>
                                        {getIcon(notif.type)}
                                    </div>
                                    <div className="flex flex-col gap-1.5 pr-4">
                                        <h4 className={`text-sm font-black tracking-tight ${!notif.isRead ? 'text-white' : 'text-slate-300'}`}>{notif.title}</h4>
                                        <p className="text-xs text-slate-400 leading-relaxed font-medium">{notif.message}</p>
                                        <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest mt-1">{notif.time}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Previously Section */}
                    <section>
                        <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-[0.3em] mb-6 pl-2 flex items-center gap-3">
                            Anteriormente
                            <div className="h-px flex-1 bg-white/5"></div>
                        </h3>
                        <div className="space-y-4">
                            {notifications.filter(n => !n.time.includes('min') && !n.time.includes('horas')).map((notif) => (
                                <div
                                    key={notif.id}
                                    className="bg-slate-900/20 backdrop-blur-sm border border-white/5 rounded-3xl p-5 flex gap-5 group transition-all hover:bg-slate-900/40 hover:border-white/10"
                                >
                                    <div className="size-12 rounded-2xl bg-white/5 flex items-center justify-center text-slate-500 shrink-0 shadow-inner border border-white/5 group-hover:scale-110 transition-transform">
                                        {getIcon(notif.type)}
                                    </div>
                                    <div className="flex flex-col gap-1.5 pr-4">
                                        <h4 className="text-sm font-bold text-slate-300 tracking-tight">{notif.title}</h4>
                                        <p className="text-xs text-slate-500 leading-relaxed font-medium">{notif.message}</p>
                                        <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mt-1">{notif.time}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Empty State Mock */}
                    {notifications.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                            <div className="size-20 rounded-full bg-white/5 flex items-center justify-center text-slate-600 border border-white/5">
                                <Bell size={40} />
                            </div>
                            <h4 className="text-white font-black">No hay notificaciones</h4>
                            <p className="text-slate-500 text-sm max-w-[200px]">Te avisaremos cuando pase algo importante en la comunidad.</p>
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
}

"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { 
    Calendar, 
    MapPin, 
    Users, 
    Clock, 
    CheckCircle2, 
    LayoutDashboard,
    ArrowLeft,
    Share2,
    Settings,
    MoreVertical,
    QrCode
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

const MOCK_EVENT = {
    id: 1,
    title: 'Noche de Milagros y Profecía',
    description: 'Servicio especial de adoración y ministración para toda la congregación.',
    event_date: '2026-04-25T19:00:00',
    location: 'Auditorio Central FARO',
    attendees_count: 450,
    status: 'scheduled'
};

export default function EventDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [event, setEvent] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadEvent = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/crm/events/${id}`, { token }).catch(() => MOCK_EVENT);
                setEvent(data);
            } catch (err) {
                toast.error('Error al cargar detalle del evento');
            } finally {
                setLoading(false);
            }
        };
        loadEvent();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Sincronizando calendario ministerial...</div>;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Eventos', icon: Calendar, href: '/crm/events' },
                { label: event.title, icon: Calendar },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <div className="max-w-5xl mx-auto space-y-10">
                    <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                        <div className="space-y-4">
                            <DSBadge tone={event.status === 'scheduled' ? 'blue' : 'emerald'} label={event.status === 'scheduled' ? 'PROGRAMADO' : 'REALIZADO'} />
                            <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-tight">
                                {event.title}
                            </h1>
                            <div className="flex flex-wrap items-center gap-6 text-sm font-bold text-slate-500">
                                <span className="flex items-center gap-2"><Calendar size={18} className="text-blue-600" /> {new Date(event.event_date).toLocaleDateString()}</span>
                                <span className="flex items-center gap-2"><Clock size={18} className="text-blue-600" /> {new Date(event.event_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                <span className="flex items-center gap-2"><MapPin size={18} className="text-blue-600" /> {event.location}</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <button className="p-3 rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:text-blue-600 transition-all">
                                <Share2 size={20} />
                            </button>
                            <button className="px-6 py-3 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/30 hover:scale-105 transition-all flex items-center gap-2">
                                <QrCode size={16} /> Gestionar Check-in
                            </button>
                        </div>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 space-y-8">
                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Descripción del Evento</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                                    {event.description}
                                </p>
                            </DSCard>

                            <section className="space-y-6">
                                <h3 className="text-sm font-black uppercase tracking-[0.3em] text-slate-400">Recursos y Logística</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="p-6 rounded-3xl bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 space-y-3">
                                        <Users size={24} className="text-blue-600" />
                                        <p className="text-2xl font-black">{event.attendees_count}</p>
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Inscritos Estimados</p>
                                    </div>
                                    <div className="p-6 rounded-3xl bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 space-y-3">
                                        <CheckCircle2 size={24} className="text-emerald-500" />
                                        <p className="text-2xl font-black">95%</p>
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Aforo Confirmado</p>
                                    </div>
                                </div>
                            </section>
                        </div>

                        <aside className="space-y-6">
                            <div className="bg-slate-900 rounded-[2.5rem] p-8 text-white space-y-6">
                                <h4 className="text-lg font-black uppercase tracking-tight">Acciones Rápidas</h4>
                                <div className="space-y-2">
                                    <button className="w-full py-3 bg-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-white/20 text-left px-4 flex items-center justify-between group">
                                        Enviar Recordatorio SMS
                                        <ArrowLeft size={14} className="rotate-180 opacity-0 group-hover:opacity-100 transition-all" />
                                    </button>
                                    <button className="w-full py-3 bg-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-white/20 text-left px-4 flex items-center justify-between group">
                                        Imprimir Listado
                                        <ArrowLeft size={14} className="rotate-180 opacity-0 group-hover:opacity-100 transition-all" />
                                    </button>
                                </div>
                            </div>
                        </aside>
                    </div>
                </div>
            </main>
        </CrmShell>
    );
}

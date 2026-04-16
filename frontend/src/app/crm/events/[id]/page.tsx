"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Calendar, Users, Clock, History, ArrowLeft, 
    MoreHorizontal, Edit3, ShieldCheck, Zap, 
    Sparkles, ChevronRight, CheckCircle2,
    BarChart3, MapPin, Share2, Star, 
    Scan, Save, X, Loader2, BookOpen, 
    TrendingUp, UserCheck, Activity
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '../../../context/AuthContext';
import { apiFetch } from '../../../lib/http';
import CrmShell from '../../../components/crm/CrmShell';

const MOCK_EVENT = {
    id: 1,
    name: 'Servicio Dominical E.P.',
    description: 'Encuentro principal de adoración y enseñanza ministerial para toda la red de miembros y liderazgo regional.',
    type: 'PERMANENT',
    day_name: 'Domingo',
    time: '09:00 AM',
    location: 'Auditorio Central Ebenezer',
    stats: {
        last_attendance: 450,
        avg_attendance: 425,
        growth: '+12%',
        retention: '88%'
    },
    upcoming: [
        { id: 101, date: '14 Abr', status: 'Confirmado' },
        { id: 102, date: '21 Abr', status: 'Programado' },
    ],
    recent_history: [
        { id: 1, title: 'Servicio 07 Abr', attendance: 432, success_rate: 98 },
        { id: 2, title: 'Servicio 31 Mar', attendance: 445, success_rate: 99 },
        { id: 3, title: 'Servicio 24 Mar', attendance: 398, success_rate: 95 },
    ]
};

export default function EventDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const [event, setEvent] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'overview' | 'attendance' | 'settings'>('overview');

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiFetch(`/crm/events/${params.id}`, { token }).catch(() => MOCK_EVENT);
            setEvent(data || MOCK_EVENT);
        } finally {
            setLoading(false);
        }
    }, [params.id, token]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    if (loading) {
        return (
            <CrmShell breadcrumbs={[{ label: 'Cargando...', icon: Loader2 }]}>
                <div className="flex flex-col items-center justify-center h-full gap-5">
                    <div className="size-14 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                    <p className="text-[10px] font-black uppercase tracking-[0.5em] text-slate-400 animate-pulse">Sincronizando Agenda Regional...</p>
                </div>
            </CrmShell>
        );
    }

    if (!event) return null;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM Pastoral', icon: Users },
                { label: 'Eventos', icon: Calendar, href: '/crm/events' },
                { label: event.name, icon: Sparkles }
            ]}
        >
            <div className="h-full flex flex-col overflow-hidden bg-white dark:bg-[#0b0d11]">
                
                {/* Cinematic Header */}
                <header className="shrink-0 p-8 lg:p-12 border-b border-slate-100 dark:border-white/5 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 -mr-20 -mt-20 size-96 bg-blue-600/5 dark:bg-blue-600/10 rounded-full blur-[100px] group-hover:bg-blue-600/20 transition-all duration-1000" />
                    
                    <div className="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-8">
                        <div className="space-y-6">
                            <button 
                                onClick={() => router.back()}
                                className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-blue-600 transition-all"
                            >
                                <ArrowLeft size={14} /> Volver a la Red de Eventos
                            </button>

                            <div className="flex items-center gap-6">
                                <div className="size-20 rounded-[2.5rem] bg-gradient-to-tr from-blue-600 to-indigo-700 flex items-center justify-center text-white shadow-2xl shadow-blue-500/20 relative">
                                    <Calendar size={32} />
                                    <div className="absolute -bottom-1 -right-1 size-8 bg-emerald-500 rounded-2xl border-4 border-white dark:border-[#0b0d11] flex items-center justify-center">
                                        <CheckCircle2 size={12} className="text-white" />
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-3">
                                        <h1 className="text-4xl lg:text-5xl font-black tracking-tighter text-slate-900 dark:text-white uppercase italic leading-none truncate max-w-xl">
                                            {event.name}
                                        </h1>
                                        <span className="px-3 py-1 bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400 rounded-full text-[9px] font-black uppercase tracking-widest">
                                            {event.type}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-slate-500 dark:text-slate-400 font-medium">
                                        <p className="flex items-center gap-1.5"><MapPin size={16} className="text-blue-500" /> {event.location}</p>
                                        <span className="size-1 rounded-full bg-slate-300 dark:bg-white/10" />
                                        <p className="flex items-center gap-1.5"><Clock size={16} /> Todos los {event.day_name}s - {event.time}</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <button className="p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-2xl text-slate-400 hover:text-blue-600 transition-all shadow-sm">
                                <Scan size={20} />
                            </button>
                            <button className="px-8 py-4 bg-slate-900 dark:bg-blue-600 text-white text-[11px] font-black uppercase tracking-widest rounded-3xl shadow-2xl shadow-blue-500/20 hover:scale-105 active:scale-95 transition-all flex items-center gap-3">
                                <Edit3 size={18} /> Gestionar Evento
                            </button>
                        </div>
                    </div>

                    {/* Dashboard Minicharts */}
                    <div className="mt-12 grid grid-cols-2 lg:grid-cols-4 gap-6 relative z-10">
                        <QuickMetric label="Última Asistencia" value={event.stats.last_attendance} icon={Users} color="blue" />
                        <QuickMetric label="Crecimiento" value={event.stats.growth} icon={TrendingUp} color="emerald" />
                        <QuickMetric label="Tasa de Éxito" value={event.stats.retention} icon={Activity} color="indigo" />
                        <QuickMetric label="Media Histórica" value={event.stats.avg_attendance} icon={BarChart3} color="amber" />
                    </div>
                </header>

                {/* Tab Navigation */}
                <div className="px-8 lg:px-12 border-b border-slate-100 dark:border-white/5 flex gap-10">
                    {['overview', 'attendance', 'settings'].map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab as any)}
                            className={clsx(
                                "py-6 text-[11px] font-black uppercase tracking-[0.2em] relative transition-all",
                                activeTab === tab ? "text-blue-600" : "text-slate-400 hover:text-slate-600"
                            )}
                        >
                            {tab === 'overview' ? 'Resumen' : tab === 'attendance' ? 'Asistencia' : 'Configuración'}
                            {activeTab === tab && (
                                <motion.div layoutId="tab-underline-event" className="absolute bottom-0 left-0 right-0 h-1 bg-blue-600 rounded-t-full" />
                            )}
                        </button>
                    ))}
                </div>

                <div className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12">
                    <AnimatePresence mode="wait">
                        {activeTab === 'overview' && (
                            <motion.div 
                                key="overview" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                                className="grid grid-cols-1 lg:grid-cols-12 gap-10"
                            >
                                {/* Description & Upcoming */}
                                <div className="lg:col-span-8 space-y-10">
                                    <section className="space-y-4">
                                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-4">Descripción del Evento</h3>
                                        <div className="p-10 bg-slate-50 dark:bg-white/[0.03] border border-slate-100 dark:border-white/10 rounded-[3.5rem] text-xl font-bold text-slate-800 dark:text-slate-200 leading-tight italic">
                                            &quot;{event.description}&quot;
                                        </div>
                                    </section>

                                    <section className="space-y-6">
                                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-4">Historial de Ejecuciones</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                            {event.recent_history.map((h: any) => (
                                                <div key={h.id} className="p-6 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[2.5rem] group hover:border-blue-500/30 transition-all cursor-pointer">
                                                    <div className="flex items-center justify-between mb-4">
                                                        <div className="size-10 rounded-xl bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-600"><History size={18} /></div>
                                                        <span className="text-[9px] font-black text-emerald-500">{h.success_rate}% Éxito</span>
                                                    </div>
                                                    <p className="font-black text-slate-800 dark:text-white uppercase leading-none">{h.title}</p>
                                                    <p className="text-xl font-black text-blue-600 mt-2">{h.attendance} <span className="text-[10px] text-slate-400 uppercase tracking-widest">Presentes</span></p>
                                                </div>
                                            ))}
                                        </div>
                                    </section>
                                </div>

                                {/* Sidebar Stats */}
                                <div className="lg:col-span-4 space-y-8">
                                    <section className="bg-slate-900 rounded-[3rem] p-8 text-white space-y-8 relative overflow-hidden group border border-blue-900/30">
                                        <div className="absolute -bottom-10 -right-10 p-10 opacity-10 group-hover:scale-125 transition-transform duration-1000">
                                            <Zap size={140} fill="currentColor" />
                                        </div>
                                        <div className="relative z-10 space-y-6">
                                            <div className="flex items-center gap-3 text-blue-400">
                                                <Sparkles size={18} />
                                                <h4 className="text-[10px] font-black uppercase tracking-[0.3em]">IA Predictiva</h4>
                                            </div>
                                            <p className="text-2xl font-black italic tracking-tighter leading-none">
                                                &quot;Se proyecta una asistencia de 465 personas para el próximo domingo basado en la tendencia de los últimos 3 meses.&quot;
                                            </p>
                                            <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                                                <div className="h-full bg-blue-500 w-[75%]" />
                                            </div>
                                            <button className="w-full py-4 bg-white text-slate-900 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:scale-105 active:scale-95 transition-all">Ver Informe Detallado</button>
                                        </div>
                                    </section>

                                    <div className="p-8 bg-slate-50 dark:bg-white/5 rounded-[3rem] border border-slate-100 dark:border-white/10 space-y-6">
                                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest underline decoration-blue-500 decoration-2 underline-offset-4">Próximas Fechas</h4>
                                        <div className="space-y-3">
                                            {event.upcoming.map((u: any) => (
                                                <div key={u.id} className="flex items-center justify-between p-4 bg-white dark:bg-black/20 rounded-2xl border border-transparent hover:border-blue-500/30 transition-all cursor-pointer">
                                                    <div className="flex items-center gap-3">
                                                        <Calendar size={16} className="text-blue-500" />
                                                        <span className="text-sm font-bold dark:text-white">{u.date}</span>
                                                    </div>
                                                    <span className="text-[8px] font-black uppercase tracking-widest px-2 py-1 bg-blue-50 text-blue-600 dark:bg-blue-500/10 rounded-lg">{u.status}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'attendance' && (
                            <motion.div key="attendance" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tighter">CONTROL DE ASISTENCIA Y ACCESO</h3>
                                    <button className="px-8 py-3 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 flex items-center gap-3">
                                        <Scan size={16} /> Iniciar Escaneo ASST
                                    </button>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                                    <div className="md:col-span-2 lg:col-span-2 bg-slate-50 dark:bg-white/5 p-10 rounded-[3rem] border border-slate-200 dark:border-white/10 flex flex-col items-center justify-center gap-6 text-center">
                                         <UserCheck size={48} className="text-blue-500" />
                                         <div className="space-y-1">
                                            <p className="text-3xl font-black dark:text-white">450 / 500</p>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Capacidad de Salón vs Asistencia Real</p>
                                         </div>
                                         <div className="h-2 w-full max-w-xs bg-slate-200 dark:bg-white/10 rounded-full overflow-hidden">
                                            <div className="h-full bg-blue-500 w-[90%]" />
                                         </div>
                                    </div>
                                    <div className="md:col-span-1 lg:col-span-1 bg-white dark:bg-white/5 p-8 rounded-[2.5rem] border border-slate-100 dark:border-white/10 flex flex-col justify-between">
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Nuevos Asistentes</p>
                                        <h4 className="text-4xl font-black text-blue-600 tracking-tighter">18</h4>
                                        <p className="text-[9px] font-bold text-emerald-500 mt-2 uppercase">+5% vs semana anterior</p>
                                    </div>
                                    <div className="md:col-span-1 lg:col-span-1 bg-white dark:bg-white/5 p-8 rounded-[2.5rem] border border-slate-100 dark:border-white/10 flex flex-col justify-between">
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Invitados V.I.P.</p>
                                        <h4 className="text-4xl font-black text-amber-500 tracking-tighter">12</h4>
                                        <p className="text-[9px] font-bold text-slate-400 mt-2 uppercase">Protocolo de acogida activo</p>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </CrmShell>
    );
}

function QuickMetric({ label, value, icon: Icon, color }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-500/10',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10',
        indigo: 'text-indigo-600 bg-indigo-50 dark:bg-indigo-500/10',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-500/10'
    };
    return (
        <div className="p-8 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[3rem] shadow-sm flex flex-col gap-6 group hover:shadow-xl transition-all">
            <div className={clsx("size-12 rounded-2xl flex items-center justify-center transition-transform group-hover:rotate-12", colors[color])}>
                <Icon size={24} />
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</p>
                <h4 className="text-2xl font-black text-slate-900 dark:text-white tracking-tighter uppercase leading-none">
                    {value}
                </h4>
            </div>
        </div>
    );
}

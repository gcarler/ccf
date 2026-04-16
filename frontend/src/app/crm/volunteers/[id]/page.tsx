"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    User, Heart, Star, Activity, 
    History, ArrowLeft, MoreHorizontal, Edit3, 
    ShieldCheck, Zap, Sparkles, ChevronRight, CheckCircle2,
    Calendar, TrendingUp, Clock, AlertCircle,
    UserCheck, Share2, Phone, Mail, Award,
    X, Loader2, Music, Coffee, Camera, Shield
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';

const iconMap: Record<string, any> = {
    'Alabanza': Music,
    'Hospitalidad': Coffee,
    'Media': Camera,
    'Seguridad': Shield,
};

const MOCK_VOLUNTEER = {
    id: 1,
    name: 'Samuel Torres',
    role: 'Líder de Alabanza',
    email: 's.torres@ccf.org',
    phone: '+57 300 987 6543',
    status: 'Activo',
    xp: 2850,
    join_date: '12 de Mayo, 2022',
    teams: ['Alabanza', 'Media'],
    stats: {
        attendance: '100%',
        punctuality: '98%',
        commitments: 124,
        health: 100
    },
    upcoming_shifts: [
        { id: 1, team: 'Alabanza', role: 'Guitarra Eléctrica', date: 'Dom 14 Abr', time: '07:30 AM' },
        { id: 2, team: 'Media', role: 'Streaming Op', date: 'Mie 17 Abr', time: '06:00 PM' },
    ],
    history: [
        { id: 1, text: 'Promovido a Líder de Turno', date: 'Hace 1 mes' },
        { id: 2, text: 'Certificado en Audio Profesional', date: 'Hace 3 meses' },
        { id: 3, text: 'Ingreso al equipo de Alabanza', date: 'May 2022' },
    ]
};

export default function VolunteerDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const [volunteer, setVolunteer] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'overview' | 'shifts' | 'achievements'>('overview');

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiFetch(`/crm/volunteers/${params.id}`, { token }).catch(() => MOCK_VOLUNTEER);
            setVolunteer(data || MOCK_VOLUNTEER);
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
                    <Loader2 className="size-12 animate-spin text-blue-600" />
                    <p className="text-[10px] font-black uppercase tracking-[0.5em] text-slate-400 animate-pulse">Sincronizando Hoja de Vida Ministerial...</p>
                </div>
            </CrmShell>
        );
    }

    if (!volunteer) return null;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM Pastoral', icon: UserCheck },
                { label: 'Servidores', icon: ShieldCheck, href: '/crm/volunteers' },
                { label: volunteer.name, icon: Star }
            ]}
        >
            <div className="h-full flex flex-col overflow-hidden bg-white dark:bg-[#0b0d11]">
                
                {/* Cinematic Header */}
                <header className="shrink-0 p-8 lg:p-12 border-b border-slate-100 dark:border-white/5 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 -mr-20 -mt-20 size-96 bg-emerald-600/5 dark:bg-emerald-600/10 rounded-full blur-[100px] group-hover:bg-emerald-600/20 transition-all duration-1000" />
                    
                    <div className="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-8">
                        <div className="space-y-6">
                            <button 
                                onClick={() => router.back()}
                                className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-emerald-600 transition-all"
                            >
                                <ArrowLeft size={14} /> Volver al Cronograma
                            </button>

                            <div className="flex items-center gap-6">
                                <div className="size-20 rounded-[2.5rem] bg-gradient-to-tr from-emerald-500 to-teal-600 flex items-center justify-center text-white shadow-2xl shadow-emerald-500/20 relative">
                                    <User size={32} />
                                    <div className="absolute -bottom-1 -right-1 size-8 bg-emerald-600 rounded-2xl border-4 border-white dark:border-[#0b0d11] flex items-center justify-center">
                                        <ShieldCheck size={14} />
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-3">
                                        <h1 className="text-4xl lg:text-5xl font-black tracking-tighter text-slate-900 dark:text-white uppercase italic leading-none">
                                            {volunteer.name}
                                        </h1>
                                        <span className="px-3 py-1 bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400 rounded-full text-[9px] font-black uppercase tracking-widest">
                                            {volunteer.status}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-slate-500 dark:text-slate-400 font-medium">
                                        <p className="flex items-center gap-1.5"><Award size={16} className="text-emerald-500" /> {volunteer.role}</p>
                                        <span className="size-1 rounded-full bg-slate-300 dark:bg-white/10" />
                                        <p className="flex items-center gap-1.5"><Star size={16} className="text-amber-500" /> {volunteer.xp} XP acumulados</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <button className="p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-2xl text-slate-400 hover:text-emerald-600 transition-all shadow-sm">
                                <Share2 size={20} />
                            </button>
                            <button className="px-8 py-4 bg-slate-900 dark:bg-emerald-600 text-white text-[11px] font-black uppercase tracking-widest rounded-3xl shadow-2xl shadow-emerald-500/20 hover:scale-105 active:scale-95 transition-all flex items-center gap-3">
                                <Edit3 size={18} /> Editar Hoja de Vida
                            </button>
                        </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-6 relative z-10">
                        <QuickStat label="Asistencia Total" value={volunteer.stats.attendance} icon={CheckCircle2} color="emerald" />
                        <QuickStat label="Puntualidad" value={volunteer.stats.punctuality} icon={Clock} color="blue" />
                        <QuickStat label="Servicios Realizados" value={volunteer.stats.commitments} icon={Activity} color="indigo" />
                        <QuickStat label="Fecha de Ingreso" value="May 2022" icon={Calendar} color="amber" />
                    </div>
                </header>

                {/* Tab Navigation */}
                <div className="px-8 lg:px-12 border-b border-slate-100 dark:border-white/5 flex gap-10">
                    {['overview', 'shifts', 'achievements'].map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab as any)}
                            className={clsx(
                                "py-6 text-[11px] font-black uppercase tracking-[0.2em] relative transition-all",
                                activeTab === tab ? "text-emerald-600" : "text-slate-400 hover:text-slate-600"
                            )}
                        >
                            {tab === 'overview' ? 'Resumen' : tab === 'shifts' ? 'Turnos' : 'Logros'}
                            {activeTab === tab && (
                                <motion.div layoutId="tab-underline-vol" className="absolute bottom-0 left-0 right-0 h-1 bg-emerald-600 rounded-t-full" />
                            )}
                        </button>
                    ))}
                </div>

                <div className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12">
                    <AnimatePresence mode="wait">
                        {activeTab === 'overview' && (
                            <motion.div 
                                key="overview" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                                className="grid grid-cols-1 lg:grid-cols-12 gap-10"
                            >
                                {/* Contact & Info */}
                                <div className="lg:col-span-4 space-y-8">
                                    <section className="bg-slate-50 dark:bg-white/5 rounded-[3rem] p-10 border border-slate-100 dark:border-white/10 space-y-8">
                                        <div className="space-y-4">
                                            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-4">Información de Contacto</h4>
                                            <div className="p-4 bg-white dark:bg-white/5 rounded-2xl flex items-center justify-between border border-transparent hover:border-emerald-500/30 transition-all cursor-pointer group">
                                                <div className="flex items-center gap-3">
                                                    <Phone size={16} className="text-emerald-500" />
                                                    <span className="text-sm font-bold text-slate-700 dark:text-slate-200">{volunteer.phone}</span>
                                                </div>
                                                <ChevronRight size={14} className="text-slate-300" />
                                            </div>
                                            <div className="p-4 bg-white dark:bg-white/5 rounded-2xl flex items-center justify-between border border-transparent hover:border-emerald-500/30 transition-all cursor-pointer group">
                                                <div className="flex items-center gap-3">
                                                    <Mail size={16} className="text-emerald-500" />
                                                    <span className="text-sm font-bold text-slate-700 dark:text-slate-200">{volunteer.email}</span>
                                                </div>
                                                <ChevronRight size={14} className="text-slate-300" />
                                            </div>
                                        </div>

                                        <div className="pt-4 border-t border-slate-200 dark:border-white/5">
                                            <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-4 mb-4">Equipos de Servicio</h4>
                                            <div className="grid grid-cols-2 gap-3 px-2">
                                                {volunteer.teams.map((team: string) => {
                                                    const Icon = iconMap[team] || User;
                                                    return (
                                                        <div key={team} className="p-5 bg-white dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/10 text-center space-y-2 group hover:bg-emerald-600 transition-all">
                                                            <Icon size={20} className="mx-auto text-emerald-500 group-hover:text-white" />
                                                            <p className="text-[9px] font-black uppercase text-slate-800 dark:text-white group-hover:text-white">{team}</p>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    </section>
                                </div>

                                {/* Timeline & Insights */}
                                <div className="lg:col-span-8 space-y-12">
                                    <section className="space-y-6">
                                        <h3 className="text-lg font-black text-slate-900 dark:text-white uppercase tracking-widest flex items-center gap-3">
                                            <History size={18} className="text-emerald-600" /> Trayectoria Ministerial
                                        </h3>
                                        <div className="space-y-4">
                                            {volunteer.history.map((item: any) => (
                                                <div key={item.id} className="p-6 bg-slate-50 dark:bg-white/5 rounded-[2rem] border border-slate-100 dark:border-white/10 flex items-start gap-5 group hover:border-emerald-500/30 transition-all">
                                                    <div className="size-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-emerald-500/20">
                                                        <Award size={18} />
                                                    </div>
                                                    <div className="flex-1">
                                                        <p className="text-[14px] font-bold text-slate-800 dark:text-white leading-tight">{item.text}</p>
                                                        <p className="text-[11px] font-medium text-slate-400 mt-1 uppercase tracking-widest">{item.date}</p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </section>

                                    <section className="p-10 bg-slate-900 rounded-[3.5rem] text-white overflow-hidden relative group border border-emerald-900/30 shadow-2xl">
                                        <div className="absolute top-0 right-0 p-10 opacity-10 group-hover:rotate-12 transition-all duration-1000">
                                            <ShieldCheck size={80} className="text-emerald-500" />
                                        </div>
                                        <div className="relative z-10 space-y-6">
                                            <div className="flex items-center gap-3 text-emerald-400">
                                                <Zap size={20} className="animate-pulse" fill="currentColor" />
                                                <h4 className="text-[11px] font-black uppercase tracking-[0.3em]">Optimus Evaluación</h4>
                                            </div>
                                            <p className="text-2xl font-black italic tracking-tight leading-none leading-relaxed">
                                                &quot;Servidor de alto rendimiento con 100% de asistencia este año. Potencial candidato para Mentoría de Nuevos Líderes.&quot;
                                            </p>
                                            <button className="px-8 py-3 bg-emerald-600 text-white text-[10px] font-black uppercase tracking-widest rounded-xl hover:bg-emerald-500 transition-all">Ver Plan de Crecimiento</button>
                                        </div>
                                    </section>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'shifts' && (
                            <motion.div key="shifts" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }} className="space-y-8">
                                <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tighter">PRÓXIMOS SERVICIOS</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {volunteer.upcoming_shifts.map((shift: any) => {
                                        const Icon = iconMap[shift.team] || User;
                                        return (
                                            <div key={shift.id} className="p-8 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[2.5rem] flex items-center justify-between group hover:shadow-xl transition-all">
                                                <div className="flex items-center gap-6">
                                                    <div className="size-16 rounded-2xl bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600">
                                                        <Icon size={32} />
                                                    </div>
                                                    <div>
                                                        <h4 className="text-xl font-black text-slate-800 dark:text-white uppercase leading-none mb-1">{shift.role}</h4>
                                                        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">{shift.team} • {shift.date} • {shift.time}</p>
                                                    </div>
                                                </div>
                                                <button className="p-3 bg-slate-50 dark:bg-white/10 rounded-xl text-slate-400 group-hover:text-emerald-500 transition-all"><ChevronRight size={20} /></button>
                                            </div>
                                        );
                                    })}
                                </div>
                            </motion.div>
                        )}
                        
                        {activeTab === 'achievements' && (
                             <motion.div key="achievements" className="py-20 text-center space-y-6">
                                <Award size={64} className="mx-auto text-amber-400 animate-bounce" />
                                <p className="text-xl font-black text-slate-800 dark:text-white uppercase tracking-tighter">SISTEMA DE LOGROS</p>
                                <p className="text-slate-400 max-w-sm mx-auto text-sm">Pronto podrás visualizar aquí las insignias y méritos obtenidos por {volunteer.name} en su camino ministerial.</p>
                             </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </CrmShell>
    );
}

function QuickStat({ label, value, total, icon: Icon, color }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-500/10',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10',
        indigo: 'text-indigo-600 bg-indigo-50 dark:bg-indigo-500/10',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-500/10'
    };
    return (
        <div className="p-8 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[3rem] shadow-sm flex flex-col gap-6 group hover:shadow-xl transition-all">
            <div className="flex justify-between items-start">
                <div className={clsx("size-12 rounded-2xl flex items-center justify-center transition-transform group-hover:rotate-12", colors[color])}>
                    <Icon size={24} />
                </div>
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</p>
                <h4 className="text-3xl font-black text-slate-900 dark:text-white tracking-tighter uppercase leading-none">
                    {value} {total && <span className="text-sm font-bold text-slate-400">/ {total}</span>}
                </h4>
            </div>
        </div>
    );
}

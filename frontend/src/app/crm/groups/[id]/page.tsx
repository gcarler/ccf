"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Home, MapPin, Users, Heart, Star, 
    ArrowLeft, MoreHorizontal, Edit3, 
    Zap, Sparkles, ChevronRight, CheckCircle2,
    Calendar, TrendingUp, Clock, AlertCircle,
    Map, Share2, Phone, Mail, UserPlus,
    X, Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';

// ─── Mock Data for the Single Group ───

const MOCK_GROUP = {
    id: 1,
    name: 'Casa de Paz Ebenezer',
    zone: 'Suroccidente',
    address: 'Calle 12 # 45-89, Barrio Las Acacias',
    leader: {
        id: 101,
        name: 'Carlos Mendoza',
        phone: '+57 320 123 4567',
        email: 'c.mendoza@ministerio.com',
        xp: 1250,
        role: 'Anfitrión / Líder'
    },
    stats: {
        members: 14,
        capacity: 15,
        target: 20,
        attendance_avg: '92%',
        health_score: 98
    },
    members: [
        { id: 1, name: 'Diana Castillo', joined: '2024-01-15', status: 'Activo', role: 'Asistente' },
        { id: 2, name: 'Marcos Ruiz', joined: '2024-02-10', status: 'Activo', role: 'Anfitrión' },
        { id: 3, name: 'Elena García', joined: '2024-03-05', status: 'Nuevo', role: 'Asistente' },
        { id: 4, name: 'Samuel Torres', joined: '2023-11-20', status: 'Activo', role: 'Asistente' },
    ],
    timeline: [
        { id: 1, type: 'status', text: 'Se alcanzó la meta de 12 miembros', date: 'Hace 2 semanas' },
        { id: 2, type: 'visit', text: 'Visita pastoral del Pastor Samuel', date: 'Hace 3 días' },
        { id: 3, type: 'training', text: 'Taller de hospitalidad completado', date: 'Ayer' },
    ]
};

export default function GroupDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const [group, setGroup] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'overview' | 'members' | 'history'>('overview');

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            // Real API call simulation
            const data = await apiFetch(`/crm/glory-houses/${params.id}`, { token }).catch(() => MOCK_GROUP);
            setGroup(data || MOCK_GROUP);
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
                    <div className="size-16 rounded-3xl border-4 border-blue-600 border-t-transparent animate-spin" />
                    <p className="text-[10px] font-black uppercase tracking-[0.5em] text-slate-400 animate-pulse">Analizando Red Geo-Pastoral...</p>
                </div>
            </CrmShell>
        );
    }

    if (!group) return null;

    const saturation = group.stats.members / group.stats.capacity;
    const tone = saturation >= 1 ? 'rose' : saturation >= 0.7 ? 'amber' : 'emerald';

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM Pastoral', icon: Users },
                { label: 'Grupos', icon: Home, href: '/crm/groups' },
                { label: group.name, icon: Sparkles }
            ]}
        >
            <div className="h-full flex flex-col overflow-hidden bg-white dark:bg-[#0b0d11]">
                
                {/* ─── Cinematic Header ─── */}
                <header className="shrink-0 p-8 lg:p-12 border-b border-slate-100 dark:border-white/5 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 -mr-20 -mt-20 size-96 bg-blue-600/5 dark:bg-blue-600/10 rounded-full blur-[100px] group-hover:bg-blue-600/20 transition-all duration-1000" />
                    
                    <div className="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-8">
                        <div className="space-y-6">
                            <button 
                                onClick={() => router.back()}
                                className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-blue-600 transition-colors"
                            >
                                <ArrowLeft size={14} /> Volver a la Red
                            </button>

                            <div className="flex items-center gap-6">
                                <div className="size-20 rounded-[2.5rem] bg-gradient-to-tr from-blue-600 to-indigo-700 flex items-center justify-center text-white shadow-2xl shadow-blue-500/20">
                                    <Home size={32} />
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-3">
                                        <h1 className="text-4xl lg:text-5xl font-black tracking-tighter text-slate-900 dark:text-white uppercase italic leading-none">
                                            {group.name}
                                        </h1>
                                        <span className={clsx(
                                            "px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest",
                                            tone === 'rose' ? "bg-rose-50 text-rose-600 dark:bg-rose-500/10" :
                                            tone === 'amber' ? "bg-amber-50 text-amber-600 dark:bg-amber-500/10" :
                                            "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10"
                                        )}>
                                            {Math.round(saturation * 100)}% Ocupación
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-slate-500 dark:text-slate-400 font-medium">
                                        <p className="flex items-center gap-1.5"><MapPin size={16} className="text-blue-500" /> {group.zone}</p>
                                        <span className="size-1 rounded-full bg-slate-300 dark:bg-white/10" />
                                        <p className="flex items-center gap-1.5"><Clock size={16} /> Activo hace 2 horas</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <button className="p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-2xl text-slate-400 hover:text-blue-600 transition-all shadow-sm">
                                <Share2 size={20} />
                            </button>
                            <button className="px-8 py-4 bg-slate-900 dark:bg-blue-600 text-white text-[11px] font-black uppercase tracking-widest rounded-3xl shadow-2xl shadow-blue-500/20 hover:scale-105 active:scale-95 transition-all flex items-center gap-3">
                                <Edit3 size={18} /> Gestionar Nodo
                            </button>
                        </div>
                    </div>

                    {/* Quick Stats Grid */}
                    <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-6 relative z-10">
                        <QuickStat label="Miembros Activos" value={group.stats.members} total={group.stats.capacity} icon={Users} color="blue" />
                        <QuickStat label="Asistencia Media" value={group.stats.attendance_avg} icon={TrendingUp} color="emerald" />
                        <QuickStat label="Salud de Casa" value={group.stats.health_score} total={100} icon={Heart} color="rose" />
                        <QuickStat label="Próxima Reunión" value="Hoy 7:30 PM" icon={Calendar} color="amber" />
                    </div>
                </header>

                {/* ─── Content Area ─── */}
                <main className="flex-1 overflow-hidden flex flex-col">
                    
                    {/* Tabs Navigation */}
                    <div className="px-8 lg:px-12 border-b border-slate-100 dark:border-white/5 flex gap-10">
                        {['overview', 'members', 'history'].map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab as any)}
                                className={clsx(
                                    "py-6 text-[11px] font-black uppercase tracking-[0.2em] relative transition-all",
                                    activeTab === tab ? "text-blue-600" : "text-slate-400 hover:text-slate-600"
                                )}
                            >
                                {tab}
                                {activeTab === tab && (
                                    <motion.div 
                                        layoutId="tab-underline"
                                        className="absolute bottom-0 left-0 right-0 h-1 bg-blue-600 rounded-t-full"
                                    />
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
                                    {/* Leader Card */}
                                    <div className="lg:col-span-4 space-y-8">
                                        <section className="bg-slate-50 dark:bg-white/5 rounded-[3rem] p-10 border border-slate-100 dark:border-white/10 space-y-8">
                                            <div className="flex flex-col items-center text-center space-y-4">
                                                <div className="size-24 rounded-[3rem] bg-gradient-to-tr from-amber-400 to-amber-600 flex items-center justify-center text-white text-2xl font-black shadow-2xl relative">
                                                    {group.leader.name.split(' ').map((n: string) => n[0]).join('')}
                                                    <div className="absolute -bottom-2 -right-2 size-8 bg-blue-600 rounded-2xl border-4 border-white dark:border-[#15171c] flex items-center justify-center">
                                                        <Star size={12} className="text-white fill-white" />
                                                    </div>
                                                </div>
                                                <div>
                                                    <h3 className="text-xl font-black text-slate-800 dark:text-white uppercase tracking-tighter">{group.leader.name}</h3>
                                                    <p className="text-[10px] font-black text-blue-600 uppercase tracking-widest">{group.leader.role}</p>
                                                </div>
                                            </div>

                                            <div className="space-y-4">
                                                <div className="p-4 bg-white dark:bg-white/5 rounded-2xl flex items-center justify-between group cursor-pointer hover:border-blue-500/50 border border-transparent transition-all">
                                                    <div className="flex items-center gap-3">
                                                        <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-400 group-hover:text-blue-600"><Phone size={16} /></div>
                                                        <span className="text-sm font-bold text-slate-700 dark:text-slate-200">{group.leader.phone}</span>
                                                    </div>
                                                    <ChevronRight size={14} className="text-slate-300" />
                                                </div>
                                                <div className="p-4 bg-white dark:bg-white/5 rounded-2xl flex items-center justify-between group cursor-pointer hover:border-blue-500/50 border border-transparent transition-all">
                                                    <div className="flex items-center gap-3">
                                                        <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-400 group-hover:text-blue-600"><Mail size={16} /></div>
                                                        <span className="text-sm font-bold text-slate-700 dark:text-slate-200">{group.leader.email}</span>
                                                    </div>
                                                    <ChevronRight size={14} className="text-slate-300" />
                                                </div>
                                            </div>

                                            <div className="pt-4 border-t border-slate-200 dark:border-white/5">
                                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Ubicación del Nodo</p>
                                                <div className="aspect-square bg-slate-200 dark:bg-white/5 rounded-[2.5rem] overflow-hidden relative">
                                                    <div className="absolute inset-0 bg-blue-600/10 animate-pulse" />
                                                    <div className="absolute inset-0 flex items-center justify-center flex-col gap-2 p-10 text-center">
                                                        <Map size={32} className="text-blue-500" />
                                                        <p className="text-[11px] font-black text-slate-900 dark:text-white uppercase leading-tight">{group.address}</p>
                                                    </div>
                                                </div>
                                            </div>
                                        </section>
                                    </div>

                                    {/* Main Content Info */}
                                    <div className="lg:col-span-8 space-y-12">
                                        <section className="space-y-6">
                                            <div className="flex items-center justify-between">
                                                <h3 className="text-lg font-black text-slate-900 dark:text-white uppercase tracking-widest flex items-center gap-3">
                                                    <History size={18} className="text-blue-600" /> Línea de Tiempo
                                                </h3>
                                                <button className="text-[10px] font-black text-blue-600 uppercase tracking-widest hover:underline">Ver Todo</button>
                                            </div>
                                            <div className="space-y-4">
                                                {group.timeline.map((item: any) => (
                                                    <div key={item.id} className="p-6 bg-slate-50 dark:bg-white/5 rounded-[2rem] border border-slate-100 dark:border-white/10 flex items-start gap-5">
                                                        <div className="size-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shrink-0 shadow-lg shadow-blue-500/20">
                                                            <CheckCircle2 size={18} />
                                                        </div>
                                                        <div className="flex-1">
                                                            <p className="text-[14px] font-bold text-slate-800 dark:text-white leading-tight">{item.text}</p>
                                                            <p className="text-[11px] font-medium text-slate-400 mt-1 uppercase tracking-widest">{item.date}</p>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </section>

                                        <section className="p-10 bg-gradient-to-br from-slate-900 to-indigo-900 rounded-[3.5rem] text-white overflow-hidden relative group">
                                            <div className="absolute bottom-0 right-0 -mr-10 -mb-10 size-64 bg-white/5 rounded-full blur-[80px] group-hover:bg-white/10 transition-all duration-1000" />
                                            <div className="relative z-10 space-y-6">
                                                <div className="flex items-center gap-3 text-blue-400">
                                                    <Zap size={20} fill="currentColor" />
                                                    <h4 className="text-[11px] font-black uppercase tracking-[0.3em]">Optimus Insight</h4>
                                                </div>
                                                <p className="text-2xl font-black tracking-tight leading-none italic">
                                                    &quot;Este grupo tiene la mayor tasa de retención de nuevos del sector. Recomendado como modelo para entrenamiento.&quot;
                                                </p>
                                                <div className="flex gap-4">
                                                    <button className="px-6 py-2.5 bg-white text-slate-900 text-[10px] font-black uppercase tracking-widest rounded-xl hover:scale-105 active:scale-95 transition-all">Ver Métricas</button>
                                                </div>
                                            </div>
                                        </section>
                                    </div>
                                </motion.div>
                            )}

                            {activeTab === 'members' && (
                                <motion.div 
                                    key="members" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                                    className="space-y-8"
                                >
                                    <div className="flex items-center justify-between mb-8">
                                        <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tighter underline decoration-blue-500 decoration-4 underline-offset-8">MIEMBROS DEL NODO ({group.members.length})</h3>
                                        <button className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center gap-2">
                                            <UserPlus size={14} /> Añadir al Grupo
                                        </button>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                        {group.members.map((member: any) => (
                                            <div key={member.id} className="p-8 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[2.5rem] shadow-sm hover:shadow-xl transition-all group cursor-pointer">
                                                <div className="flex items-center justify-between mb-6">
                                                    <div className="size-12 rounded-2xl bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-all">
                                                        <Users size={20} />
                                                    </div>
                                                    <span className="px-2.5 py-1 bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400 rounded-lg text-[8px] font-black uppercase tracking-[0.2em]">{member.status}</span>
                                                </div>
                                                <h4 className="text-lg font-black text-slate-800 dark:text-white uppercase leading-none mb-1">{member.name}</h4>
                                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">{member.role} desde {member.joined}</p>
                                                <div className="h-1 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                                    <div className="h-full bg-blue-600 w-full" />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </motion.div>
                            )}

                            {activeTab === 'history' && (
                                <motion.div key="history" className="p-20 text-center">
                                    <Clock size={64} className="mx-auto text-slate-200 mb-6" />
                                    <p className="text-xl font-black text-slate-400 uppercase tracking-tighter">Historial completo en construcción</p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </main>
            </div>
        </CrmShell>
    );
}

function QuickStat({ label, value, total, icon: Icon, color }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-500/10',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10',
        rose: 'text-rose-600 bg-rose-50 dark:bg-rose-500/10',
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

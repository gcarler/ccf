"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    Users,
    BookOpen,
    Mic2,
    TrendingUp,
    Upload,
    PlusCircle,
    FileText,
    ChevronRight,
    PlayCircle,
    Clock
} from 'lucide-react';

export default function AdminContent() {
    const { isAuthenticated, user } = useAuth();
    const router = useRouter();

    const stats = [
        { label: 'Usuarios', value: '1,240', trend: '+12%', icon: Users },
        { label: 'Cursos Activos', value: '18', trend: '+5%', icon: BookOpen },
        { label: 'Total Prédicas', value: '452', trend: '+8%', icon: Mic2 },
    ];

    const actions = [
        { title: 'Subir Prédica', desc: 'Audio o video HD', icon: Upload, primary: true },
        { title: 'Nuevo Curso', desc: 'Crear currículo bíblico', icon: PlusCircle, primary: false },
        { title: 'Cargar PDF', desc: 'Guías de estudio y recursos', icon: FileText, primary: false },
    ];

    const recent = [
        { title: 'Serie: Caminando en Fe', time: 'Hace 2h', status: 'Activo', img: 'https://images.unsplash.com/photo-1507692049790-de58290a4334?q=80&w=200&auto=format&fit=crop' },
        { title: 'Prédica Domingo: Renovación', time: 'Procesando video...', status: 'Pendiente', img: 'https://images.unsplash.com/photo-1438232992991-995b7058bbb3?q=80&w=200&auto=format&fit=crop' },
    ];

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Page Header */}
            <div className="px-8 pt-10 pb-6 space-y-2">
                <h1 className="text-2xl font-black text-white tracking-tight uppercase tracking-tight">Gestión de Contenidos</h1>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Resumen de actividad y control global</p>
            </div>

            <main className="flex-1 px-8 pb-32 space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                {/* Stats Grid */}
                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {stats.map((stat, i) => (
                        <div key={i} className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] p-8 flex flex-col justify-between group hover:border-primary/40 transition-all shadow-2xl">
                            <div className="flex justify-between items-start">
                                <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all shadow-lg">
                                    <stat.icon size={24} />
                                </div>
                                <div className="flex items-center gap-1 bg-emerald-500/10 text-emerald-500 text-[10px] font-black px-2 py-1 rounded-lg border border-emerald-500/20 uppercase tracking-widest">
                                    <TrendingUp size={12} /> {stat.trend}
                                </div>
                            </div>
                            <div className="mt-6">
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none mb-1">{stat.label}</p>
                                <p className="text-3xl font-black text-white tracking-tight">{stat.value}</p>
                            </div>
                        </div>
                    ))}
                </section>

                {/* Quick Actions */}
                <section className="space-y-6">
                    <div className="flex items-center justify-between px-2">
                        <h3 className="text-white text-lg font-black tracking-tight uppercase tracking-widest">Acciones Rápidas</h3>
                        <button className="text-[10px] font-black text-primary uppercase tracking-widest hover:underline">Ver todas</button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {actions.map((action, i) => (
                            <button
                                key={i}
                                className={`flex items-center gap-5 p-6 rounded-[2rem] transition-all border group relative overflow-hidden active:scale-95 shadow-2xl ${action.primary
                                    ? 'bg-primary border-primary hover:bg-primary-600 text-white shadow-primary/20'
                                    : 'bg-white/5 border-white/5 hover:border-white/10 text-slate-400'
                                    }`}
                            >
                                <div className={`size-12 rounded-2xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-110 ${action.primary ? 'bg-white/20' : 'bg-primary/10 text-primary'}`}>
                                    <action.icon size={24} />
                                </div>
                                <div className="text-left">
                                    <p className={`text-sm font-black tracking-tight ${action.primary ? 'text-white' : 'text-white'}`}>{action.title}</p>
                                    <p className={`text-[10px] font-black uppercase tracking-widest mt-0.5 ${action.primary ? 'text-white/70' : 'text-slate-500'}`}>{action.desc}</p>
                                </div>
                                <ChevronRight size={20} className={`ml-auto ${action.primary ? 'text-white/40' : 'text-slate-700'} group-hover:text-white transition-colors`} />
                            </button>
                        ))}
                    </div>
                </section>

                {/* Recent Status */}
                <section className="space-y-6">
                    <h3 className="text-white text-lg font-black tracking-tight uppercase tracking-widest px-2">Estado Reciente</h3>
                    <div className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2.5rem] overflow-hidden shadow-2xl">
                        {recent.map((item, i) => (
                            <div key={i} className="flex items-center gap-6 p-6 border-b border-white/5 group hover:bg-white/5 transition-all">
                                <div className="size-16 rounded-2xl overflow-hidden border-2 border-white/5 group-hover:border-primary/50 transition-all shadow-xl shadow-black/40 shrink-0">
                                    <div className="size-full bg-slate-800 flex items-center justify-center text-white text-[10px] font-bold">
                                        {item.title?.charAt(0)}
                                    </div>

                                </div>
                                <div className="flex-1 min-w-0">
                                    <h4 className="text-sm font-black text-white truncate uppercase tracking-tight group-hover:text-primary transition-colors">{item.title}</h4>
                                    <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mt-1.5 flex items-center gap-2">
                                        <Clock size={12} className="text-primary" /> {item.time}
                                    </p>
                                </div>
                                <span className={`px-3 py-1 text-[9px] font-black rounded-lg uppercase tracking-widest border ${item.status === 'Activo' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                                    }`}>
                                    {item.status}
                                </span>
                            </div>
                        ))}
                    </div>
                </section>
            </main>
        </div>
    );
}

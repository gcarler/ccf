"use client";

import React, { useState, useEffect } from 'react';
import { 
    Award, 
    Search, 
    Filter, 
    Plus, 
    ChevronRight, 
    CheckCircle2, 
    Users, 
    Calendar, 
    Zap,
    Heart,
    Star,
    Sparkles,
    Flame,
    Navigation,
    MoreHorizontal
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function SpiritualMilestones() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [milestones, setMilestones] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Quality Mock Data
        setMilestones([
            { id: 1, name: 'Bautismo en Aguas', count: 124, date: 'Próximo: 15 Abr', icon: Zap, color: 'blue' },
            { id: 2, name: 'Encuentro con Dios', count: 850, date: 'Próximo: 22 May', icon: Flame, color: 'rose' },
            { id: 3, name: 'Lanzamiento de Líderes', count: 12, date: 'Finalizado', icon: Star, color: 'amber' },
        ]);
        setLoading(false);
    }, []);

    if (!isAuthenticated) return null;

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Vida Espiritual', icon: Heart },
                { label: 'Hitos de Crecimiento', icon: Award }
            ]}
        >
            <AdminHero
                eyebrow="Growth Tracking"
                title="Consola de Hitos Espirituales"
                description="Registra y celebra los pasos de fe de la congregación. Gestiona bautismos, encuentros y graduaciones de forma masiva y eficiente."
                tags={['Crecimiento 2026', 'Impacto Real', 'Pastoral Core']}
                watchers={['Cuerpo Pastoral', 'Secretaría']}
                primaryAction={{ label: 'Nuevo Hito', icon: Plus, onClick: () => {} }}
                secondaryAction={{ label: 'Generar Diplomas', icon: Award, onClick: () => {} }}
            />

            <div className="space-y-10 pb-20">
                {/* Milestone Summary Cards */}
                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {milestones.map((m) => (
                        <div key={m.id} className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] shadow-sm hover:shadow-xl transition-all group overflow-hidden relative">
                            <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
                                <m.icon size={64} className={clsx(
                                    m.color === 'blue' ? 'text-blue-600' : m.color === 'rose' ? 'text-rose-600' : 'text-amber-600'
                                )} />
                            </div>
                            <div className="relative z-10 space-y-6">
                                <div className={clsx(
                                    "size-14 rounded-2xl flex items-center justify-center transition-transform group-hover:rotate-12",
                                    m.color === 'blue' ? 'bg-blue-50 text-blue-600' : m.color === 'rose' ? 'bg-rose-50 text-rose-600' : 'bg-amber-50 text-amber-600'
                                )}>
                                    <m.icon size={28} />
                                </div>
                                <div>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{m.name}</p>
                                    <h4 className="text-3xl font-black text-slate-900 dark:text-white tracking-tighter">{m.count} <span className="text-sm font-bold text-slate-400 uppercase tracking-normal">Personas</span></h4>
                                </div>
                                <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-white/5">
                                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{m.date}</span>
                                    <button className="flex items-center gap-2 text-[10px] font-black text-blue-600 uppercase tracking-widest">
                                        Gestionar <ChevronRight size={14} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </section>

                {/* Bulk Action Area */}
                <section className="bg-slate-900 rounded-[3rem] p-10 text-white shadow-2xl relative overflow-hidden group">
                    <div className="absolute top-0 right-0 -mr-20 -mt-20 size-64 bg-blue-600/20 rounded-full blur-[80px]" />
                    <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
                        <div className="space-y-6">
                            <div className="flex items-center gap-3">
                                <Sparkles size={24} className="text-blue-400" />
                                <h3 className="text-2xl font-black tracking-tight uppercase">Registro Masivo de Fe</h3>
                            </div>
                            <p className="text-slate-400 text-sm font-medium leading-relaxed uppercase tracking-wider">
                                Selecciona una categoría y sube la lista de personas que han alcanzado un hito. Optimus Brain procesará los certificados y actualizará los perfiles automáticamente.
                            </p>
                            <div className="flex gap-4">
                                <button className="px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] transition-all shadow-xl shadow-blue-500/20 active:scale-95">
                                    Iniciar Proceso
                                </button>
                                <button className="px-8 py-4 bg-white/5 hover:bg-white/10 rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] transition-all border border-white/10">
                                    Descargar Plantilla
                                </button>
                            </div>
                        </div>
                        <div className="hidden lg:flex justify-center">
                            <div className="relative">
                                <div className="size-48 rounded-[3rem] border-4 border-blue-500/30 flex items-center justify-center animate-pulse">
                                    <Navigation size={64} className="text-blue-500 rotate-45" />
                                </div>
                                <div className="absolute -top-4 -right-4 size-12 bg-white rounded-2xl flex items-center justify-center shadow-2xl">
                                    <Award size={24} className="text-blue-600" />
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </AdminShell>
    );
}

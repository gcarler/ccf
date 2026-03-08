"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    LayoutDashboard,
    Users,
    TrendingUp,
    Settings,
    Search,
    Bell,
    UserPlus,
    MessageSquare,
    ChevronRight,
    UserCheck,
    Clock,
    Calendar,
    CheckCircle,

    UserCircle,
    BarChart3,
    ArrowUpRight
} from 'lucide-react';
import Link from 'next/link';
import { apiUrl } from '@/lib/api';

export default function CRMDashboard() {
    const { isAuthenticated, token, user } = useAuth();
    const router = useRouter();
    const [metrics, setMetrics] = useState<any>(null);

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const res = await fetch(apiUrl('/dashboard/metrics'), {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) setMetrics(await res.json());
            } catch (err) {
                console.error("Error fetching metrics:", err);
            }
        };
        if (token) fetchMetrics();
    }, [token]);

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-60 blur-3xl mix-blend-screen"></div>
                <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_bottom_left,_var(--tw-gradient-stops))] from-indigo-600/10 via-slate-950 to-slate-950 opacity-40 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-6xl mx-auto flex flex-col min-h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-8 py-6 flex items-center justify-between border-b border-white/5">
                    <div className="flex items-center gap-4 group cursor-pointer">
                        <div className="bg-primary/20 p-2.5 rounded-2xl border border-primary/30 group-hover:bg-primary group-hover:text-white transition-all shadow-lg shadow-primary/20">
                            <LayoutDashboard size={24} />
                        </div>
                        <div className="flex flex-col">
                            <h1 className="text-xl font-black tracking-tight text-white uppercase tracking-[0.1em]">CRM Ministerial</h1>
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-0.5">Comunidad Cristiana El Faro</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <button className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl hover:bg-white/10 transition-all group overflow-hidden">
                            <Bell size={20} className="text-slate-400 group-hover:text-white transition-colors" />
                            <span className="absolute top-3 right-3 h-2 w-2 rounded-full bg-primary ring-4 ring-slate-950/40"></span>
                        </button>
                        <div className="flex items-center gap-3 pl-4 border-l border-white/10">
                            <div className="flex flex-col items-end mr-1">
                                <span className="text-xs font-black text-white">{user?.username || 'Pastor'}</span>
                                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Administrador</span>
                            </div>

                            <div className="size-11 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center p-0.5 shadow-lg shadow-primary/20">
                                <div className="size-full rounded-[0.9rem] bg-slate-900 flex items-center justify-center overflow-hidden">
                                    <UserCircle size={24} className="text-primary/70" />
                                </div>
                            </div>
                        </div>
                    </div>
                </header>

                <main className="flex-1 px-8 py-10 space-y-12 pb-32">
                    {/* Welcome Section */}
                    <section className="animate-in fade-in slide-in-from-left-6 duration-700">
                        <h2 className="text-4xl font-black tracking-tight text-white mb-2 leading-tight">Hola, {user?.username?.split(' ')[0] || 'Siervo'}</h2>
                        <p className="text-slate-400 font-medium text-lg">Resumen de impacto ministerial para hoy.</p>
                    </section>


                    {/* Stats Grid */}
                    <section className="grid grid-cols-1 md:grid-cols-3 gap-8 animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-100">
                        <div className="md:col-span-2 relative overflow-hidden bg-gradient-to-br from-primary/30 via-slate-900/60 to-slate-900/40 backdrop-blur-xl border border-primary/30 rounded-[3rem] p-10 group shadow-2xl">
                            <div className="absolute top-0 right-0 -mr-20 -mt-20 size-80 bg-primary/10 rounded-full blur-3xl group-hover:bg-primary/20 transition-all duration-1000"></div>
                            <div className="relative z-10 flex flex-col h-full justify-between">
                                <div className="flex justify-between items-start mb-10">
                                    <div className="bg-primary/90 p-4 rounded-3xl shadow-xl shadow-primary/30">
                                        <UserPlus size={28} className="text-white" />
                                    </div>
                                    <div className="flex items-center gap-2 bg-primary/10 px-4 py-2 rounded-2xl border border-primary/20">
                                        <ArrowUpRight size={16} className="text-primary" />
                                        <span className="text-xs font-black text-primary uppercase tracking-widest">12% Crecimiento</span>
                                    </div>
                                </div>
                                <div>
                                    <h3 className="text-slate-400 text-xs font-black uppercase tracking-[0.3em] mb-2">Nuevos Interesados</h3>
                                    <div className="flex items-end gap-4">
                                        <span className="text-6xl font-black text-white leading-none">48</span>
                                        <span className="text-slate-500 text-sm font-bold mb-1.5">+6 nuevos hoy</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-col gap-8">
                            <div className="flex-1 glass-card bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[3rem] p-8 group hover:border-amber-500/30 transition-all shadow-xl">
                                <Clock size={24} className="text-amber-500 mb-6 group-hover:scale-125 transition-transform" />
                                <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1.5">Seguimientos</h3>
                                <div className="text-4xl font-black text-white mb-2">24</div>
                                <div className="text-[10px] font-black text-amber-500 uppercase tracking-widest flex items-center gap-1.5">
                                    <div className="size-1.5 rounded-full bg-amber-500 animate-pulse"></div>
                                    8 urgentes hoy
                                </div>
                            </div>
                            <div className="flex-1 glass-card bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[3rem] p-8 group hover:border-emerald-500/30 transition-all shadow-xl">
                                <Users size={24} className="text-emerald-500 mb-6 group-hover:scale-125 transition-transform" />
                                <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1.5">Membresía Activa</h3>
                                <div className="text-4xl font-black text-white mb-2">{metrics?.total_enrollments || '1,240'}</div>
                                <div className="text-[10px] font-black text-emerald-500 uppercase tracking-widest flex items-center gap-1.5">
                                    92% retención mensual
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Conversion Pipeline */}
                    <section className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[3.5rem] p-12 shadow-2xl animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-200">
                        <div className="flex items-center justify-between mb-12">
                            <div className="flex items-center gap-4">
                                <div className="size-1.5 rounded-full bg-primary shadow-[0_0_8px_#4242f0]"></div>
                                <h2 className="text-xl font-black text-white tracking-tight uppercase tracking-[0.1em]">Pipeline de Conversión</h2>
                            </div>
                            <button className="text-[10px] font-black text-primary uppercase tracking-widest hover:text-primary-400 border-b border-primary/20 pb-0.5 transition-all">Ver estadísticas detalladas</button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 relative">
                            {/* Step 1 */}
                            <div className="relative group cursor-pointer">
                                <div className="bg-white/5 border border-white/10 p-8 rounded-[2rem] hover:bg-primary/10 hover:border-primary/30 transition-all shadow-lg">
                                    <div className="flex justify-between items-center mb-6">
                                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nivel 1</span>
                                        <span className="text-xs font-black text-white bg-slate-800 px-3 py-1 rounded-full">150</span>
                                    </div>
                                    <h4 className="text-xl font-black text-white mb-2">Primer Contacto</h4>
                                    <p className="text-xs text-slate-500 font-medium">Interesados recién registrados.</p>
                                </div>
                                <div className="hidden md:flex absolute -right-5 top-1/2 -translate-y-1/2 z-20 text-slate-700">
                                    <ChevronRight size={32} />
                                </div>
                            </div>

                            {/* Step 2 */}
                            <div className="relative group cursor-pointer">
                                <div className="bg-primary/5 border border-primary/20 p-8 rounded-[2rem] hover:bg-primary/10 hover:border-primary/40 transition-all shadow-lg">
                                    <div className="flex justify-between items-center mb-6">
                                        <span className="text-[10px] font-black text-primary uppercase tracking-widest">Nivel 2</span>
                                        <span className="text-xs font-black text-white bg-primary px-3 py-1 rounded-full shadow-lg shadow-primary/20">84</span>
                                    </div>
                                    <h4 className="text-xl font-black text-white mb-2">Consolidación</h4>
                                    <p className="text-xs text-slate-400 font-medium">En proceso de discipulado inicial.</p>
                                </div>
                                <div className="hidden md:flex absolute -right-5 top-1/2 -translate-y-1/2 z-20 text-slate-700">
                                    <ChevronRight size={32} />
                                </div>
                            </div>

                            {/* Step 3 */}
                            <div className="relative group cursor-pointer">
                                <div className="bg-emerald-500/5 border border-emerald-500/20 p-8 rounded-[2rem] hover:bg-emerald-500/10 hover:border-emerald-500/40 transition-all shadow-lg">
                                    <div className="flex justify-between items-center mb-6">
                                        <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest">Nivel 3</span>
                                        <span className="text-xs font-black text-white bg-emerald-500 px-3 py-1 rounded-full shadow-lg shadow-emerald-500/20">32</span>
                                    </div>
                                    <h4 className="text-xl font-black text-white mb-2">Miembro Activo</h4>
                                    <p className="text-xs text-emerald-400/60 font-medium">Bautizados y en servicio activo.</p>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Quick Actions */}
                    <section className="animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-300">
                        <h2 className="text-xl font-black text-white mb-8 uppercase tracking-[0.1em] flex items-center gap-4">
                            <div className="size-1.5 rounded-full bg-primary"></div>
                            Acciones Rápidas
                        </h2>
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                            {[
                                { title: 'Nuevo Prospecto', icon: UserPlus, color: 'text-primary', bg: 'bg-primary/10', href: '/crm/members' },
                                { title: 'Mensaje Masivo', icon: MessageSquare, color: 'text-indigo-400', bg: 'bg-indigo-500/10', href: '/crm/messaging' },
                                { title: 'Crear Culto', icon: Calendar, color: 'text-amber-500', bg: 'bg-amber-500/10', href: '/crm/events' },
                                { title: 'Reportes', icon: BarChart3, color: 'text-emerald-500', bg: 'bg-emerald-500/10', href: '/crm/reports' },
                            ].map((action, i) => (
                                <Link
                                    key={i}
                                    href={action.href}
                                    className="group flex flex-col items-center justify-center p-8 rounded-[2.5rem] bg-slate-900/40 border border-white/5 hover:border-primary/40 hover:bg-slate-900/60 transition-all shadow-xl active:scale-95"
                                >
                                    <div className={`size-16 rounded-[1.5rem] ${action.bg} flex items-center justify-center ${action.color} group-hover:scale-110 group-hover:bg-white group-hover:text-primary transition-all shadow-inner mb-5`}>
                                        <action.icon size={28} />
                                    </div>
                                    <span className="text-xs font-black text-white uppercase tracking-widest text-center">{action.title}</span>
                                </Link>
                            ))}
                        </div>
                    </section>
                </main>

                {/* Bottom Navigation Mockup for Admin Portal */}
                <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-950/60 pb-10 pt-4 backdrop-blur-2xl border-t border-white/5">
                    <div className="flex items-center justify-around px-8">
                        <Link href="/crm/dashboard" className="flex flex-col items-center gap-1.5 text-primary">
                            <LayoutDashboard size={24} />
                            <span className="text-[9px] font-black uppercase tracking-widest">Inicio</span>
                            <div className="size-1.5 rounded-full bg-primary shadow-[0_0_8px_#4242f0] mt-1"></div>
                        </Link>
                        <Link href="/crm/members" className="flex flex-col items-center gap-1.5 text-slate-500 hover:text-white transition-colors">
                            <Users size={24} />
                            <span className="text-[9px] font-black uppercase tracking-widest">Miembros</span>
                        </Link>
                        <Link href="/crm/pipeline" className="flex flex-col items-center gap-1.5 text-slate-500 hover:text-white transition-colors">
                            <TrendingUp size={24} />
                            <span className="text-[9px] font-black uppercase tracking-widest">Pipeline</span>
                        </Link>
                        <Link href="/crm/settings" className="flex flex-col items-center gap-1.5 text-slate-500 hover:text-white transition-colors">
                            <Settings size={24} />
                            <span className="text-[9px] font-black uppercase tracking-widest">Ajustes</span>
                        </Link>
                    </div>
                </nav>
            </div>
        </div>
    );
}

"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import {
    LayoutDashboard,
    Bell,
    TrendingUp,
    Users,
    Calendar,
    ChevronRight,
    UserPlus,
    Heart,
    Mail,
    Plus,
    Activity,
    Settings,
    CheckCircle2,
    Loader2
} from 'lucide-react';

type AdminStats = {
    users: number;
    donations: number;
    attendance: number;
};

export default function AdminDashboard() {
    const { isAuthenticated, user, token } = useAuth();
    const router = useRouter();
    const [stats, setStats] = useState<AdminStats>({ users: 0, donations: 0, attendance: 24 });
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        if (!token) return;
        try {
            const data = await apiFetch<AdminStats>('/auth/stats/summary', {
                token,
                cache: 'no-store'
            });
            setStats({
                users: data?.users ?? 0,
                donations: data?.donations ?? 0,
                attendance: data?.attendance ?? 0
            });
        } catch (e) {
            console.error("Dashboard fetch error", e);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (isAuthenticated) fetchData();
    }, [isAuthenticated, fetchData]);

    const tasks = [
        {
            id: '1',
            title: 'Nuevos Miembros',
            description: 'Aprobar solicitudes pendientes',
            icon: UserPlus,
            color: 'text-primary',
            bgColor: 'bg-primary/10',
            action: 'Revisar',
            badge: null
        },
        {
            id: '2',
            title: 'Ofrendas Especiales',
            description: 'Categorizar nuevos recibos',
            icon: Heart,
            color: 'text-amber-500',
            bgColor: 'bg-amber-500/10',
            action: 'Ir',
            badge: null
        }
    ];

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-primary/5 to-transparent pointer-events-none"></div>
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-40 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col min-h-screen w-full">
                {/* Header */}
                <header className="flex items-center justify-between p-6 pt-10">
                    <div className="flex items-center gap-4">
                        <div className="size-12 rounded-2xl bg-gradient-to-tr from-primary to-blue-400 p-0.5 shadow-lg shadow-primary/20">
                            <div className="size-full rounded-[0.9rem] bg-slate-950 flex items-center justify-center overflow-hidden border border-white/10">
                                <div className="size-full bg-slate-800 flex items-center justify-center text-white font-black uppercase">
                                    {String((user as any)?.username || 'A').charAt(0)}
                                </div>
                            </div>
                        </div>
                        <div>
                            <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em]">Panel de Control</h2>
                            <h1 className="text-xl font-black text-white tracking-tight">Gestión Central</h1>
                        </div>
                    </div>
                    <button className="size-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-primary hover:bg-white/10 transition-all relative">
                        <Bell size={20} />
                        <span className="absolute top-3.5 right-3.5 size-2 bg-primary rounded-full ring-2 ring-slate-950"></span>
                    </button>
                </header>

                <main className="flex-1 px-6 space-y-8 pb-32 animate-in fade-in slide-in-from-bottom-8 duration-700">

                    {/* Hero Stats */}
                    <section className="grid grid-cols-2 gap-4">
                        <div className="col-span-2 relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-primary via-primary-600 to-indigo-800 p-8 text-white shadow-2xl shadow-primary/30 group">
                            <div className="absolute top-0 right-0 -mr-16 -mt-16 bg-white/10 size-64 rounded-full blur-3xl group-hover:bg-white/20 transition-all duration-1000"></div>
                            <div className="relative z-10">
                                <p className="text-blue-100 text-[10px] font-black uppercase tracking-[0.2em]">Ofrendas del Mes</p>
                                <h3 className="text-4xl font-black mt-2 tracking-tight">${stats.donations.toLocaleString()}</h3>
                                <div className="flex items-center gap-2 mt-6 bg-white/10 backdrop-blur-md w-fit px-4 py-2 rounded-xl text-[10px] font-black border border-white/10 uppercase tracking-widest">
                                    <TrendingUp size={14} className="text-white" />
                                    <span>Datos en tiempo real</span>
                                </div>
                            </div>
                        </div>

                        <div className="rounded-[2rem] bg-slate-900/40 backdrop-blur-xl border border-white/5 p-6 flex flex-col gap-4 group hover:border-primary/30 transition-all">
                            <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-all">
                                <Users size={20} />
                            </div>
                            <div>
                                <p className="text-slate-500 text-[9px] font-black uppercase tracking-widest">Usuarios</p>
                                <p className="text-2xl font-black text-white">{loading ? '...' : stats.users}</p>
                            </div>
                        </div>

                        <div className="rounded-[2rem] bg-slate-900/40 backdrop-blur-xl border border-white/5 p-6 flex flex-col gap-4 group hover:border-emerald-500/30 transition-all">
                            <div className="size-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:bg-emerald-500 group-hover:text-white transition-all">
                                <Activity size={20} />
                            </div>
                            <div>
                                <p className="text-slate-500 text-[9px] font-black uppercase tracking-widest">Asistencia</p>
                                <p className="text-2xl font-black text-white">{loading ? '...' : stats.attendance}</p>
                            </div>
                        </div>
                    </section>

                    {/* Chart Mockup */}
                    <section className="space-y-4">
                        <div className="flex items-center justify-between px-2">
                            <h3 className="text-white text-lg font-black tracking-tight uppercase tracking-widest">Actividad</h3>
                            <button className="text-[10px] font-black text-primary uppercase tracking-widest hover:underline">Ver Detalles</button>
                        </div>
                        <div className="rounded-[2.5rem] bg-slate-900/40 backdrop-blur-xl border border-white/5 p-8 h-56 flex flex-col justify-end group hover:border-white/10 transition-all">
                            <div className="flex items-end justify-between h-full gap-3">
                                {[40, 60, 35, 90, 75, 50, 100].map((h, i) => (
                                    <div
                                        key={i}
                                        style={{ height: `${h}%` }}
                                        className={`w-full rounded-t-xl transition-all duration-500 group-hover:opacity-100 ${i === 6 ? 'bg-primary shadow-[0_0_15px_rgba(37,157,244,0.4)]' :
                                            i === 3 ? 'bg-primary/80' : 'bg-primary/20 opacity-40'
                                            }`}
                                    ></div>
                                ))}
                            </div>
                            <div className="flex justify-between mt-6 text-[9px] font-black text-slate-600 uppercase tracking-widest">
                                <span>Lun</span><span>Mar</span><span>Mie</span><span>Jue</span><span>Vie</span><span>Sab</span><span>Dom</span>
                            </div>
                        </div>
                    </section>

                    {/* Tasks Pending */}
                    <section className="space-y-6">
                        <div className="flex items-center justify-between px-2">
                            <h3 className="text-white text-lg font-black tracking-tight uppercase tracking-widest">Tareas Pendientes</h3>
                            <div className="size-7 bg-rose-500 text-white rounded-full flex items-center justify-center text-[10px] font-black shadow-lg shadow-rose-500/20">2</div>
                        </div>
                        <div className="space-y-4">
                            {tasks.map((task) => (
                                <div key={task.id} className="flex items-center gap-5 p-5 rounded-[2rem] bg-slate-900/20 backdrop-blur-md border border-white/5 hover:bg-slate-900/40 hover:border-white/10 transition-all group">
                                    <div className={`size-12 rounded-2xl ${task.bgColor} flex items-center justify-center ${task.color} group-hover:scale-110 transition-transform shadow-lg`}>
                                        <task.icon size={24} />
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm font-black text-white tracking-tight">{task.title}</p>
                                        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-0.5">{task.description}</p>
                                    </div>
                                    <button onClick={() => router.push(task.id === '1' ? '/admin/members' : '/admin/finance')} className="px-5 py-2.5 bg-primary hover:bg-primary-600 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all shadow-lg shadow-primary/20 active:scale-95 border border-primary-400/20">
                                        {task.action}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </section>
                </main>

                {/* Bottom Navigation */}
                <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-2xl border-t border-white/5 px-8 pb-10 pt-4 flex justify-between items-center">
                    <button className="flex flex-col items-center gap-1.5 text-primary">
                        <LayoutDashboard size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Inicio</span>
                        <div className="size-1 rounded-full bg-primary mt-1 shadow-[0_0_8px_#259df4]"></div>
                    </button>
                    <button onClick={() => router.push('/admin/metrics')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Activity size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Métricas</span>
                    </button>
                    <div className="relative -top-8 px-2">
                        <button onClick={() => router.push('/admin/cms')} className="bg-primary size-16 rounded-[2rem] text-white shadow-2xl shadow-primary/40 flex items-center justify-center border-4 border-slate-950 hover:scale-110 active:scale-90 transition-all">
                            <Plus size={32} />
                        </button>
                    </div>
                    <button onClick={() => router.push('/admin/tasks')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <CheckCircle2 size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Tareas</span>
                    </button>
                    <button onClick={() => router.push('/admin/settings')} className="flex flex-col items-center gap-1.5 text-slate-500">
                        <Settings size={24} />
                        <span className="text-[9px] font-black uppercase tracking-widest">Ajustes</span>
                    </button>
                </nav>
            </div>
        </div>
    );
}

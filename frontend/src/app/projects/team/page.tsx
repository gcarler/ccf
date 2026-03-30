"use client";

import React, { useEffect, useState } from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { 
    Users, 
    AlertTriangle, 
    CheckCircle2, 
    Clock, 
    TrendingUp,
    ShieldCheck,
    Zap,
    ChevronRight,
    Search
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import DSSkeleton from '@/components/ui/Skeleton';

export default function WorkloadPage() {
    const { token } = useAuth();
    const [team, setTeam] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchWorkload = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<any[]>('/system/workload', { token });
                setTeam(data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        };
        fetchWorkload();
    }, [token]);

    return (
        <WorkspaceLayout sidebarTitle="Portfolio / Gestión de Equipo">
            <div className="flex flex-col h-full bg-white dark:bg-[#141517] overflow-hidden font-display animate-fade-in">
                
                {/* Header Contextual */}
                <header className="p-10 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-black/20 relative overflow-hidden">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />
                    <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                <span className="px-3 py-1 bg-blue-600 text-white rounded-full text-[9px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20">Recursos Humanos</span>
                                <div className="size-1.5 rounded-full bg-green-400 animate-pulse" />
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Optimización de Talento</span>
                            </div>
                            <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight leading-none">Carga de Trabajo del Equipo</h1>
                            <p className="text-slate-500 font-medium mt-3">Visualiza la disponibilidad y saturación de tus servidores ministeriales en tiempo real.</p>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="px-6 py-4 bg-white dark:bg-[#1e1f21] rounded-3xl border border-slate-200 dark:border-white/10 shadow-sm">
                                <span className="text-[10px] font-black uppercase text-slate-400 block mb-1">Capacidad Promedio</span>
                                <div className="text-2xl font-black text-blue-600">74%</div>
                            </div>
                        </div>
                    </div>
                </header>

                <main className="flex-1 overflow-y-auto scrollbar-thin p-10 relative bg-white dark:bg-transparent">
                    {loading ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                            {[...Array(6)].map((_, i) => <DSSkeleton key={i} className="h-64 rounded-[3rem]" />)}
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 pb-20">
                            {team.map((member, idx) => (
                                <MemberLoadCard key={member.user_id} member={member} index={idx} />
                            ))}
                        </div>
                    )}
                </main>
            </div>
        </WorkspaceLayout>
    );
}

function MemberLoadCard({ member, index }: { member: any, index: number }) {
    const isOverloaded = member.load_status === 'sobrecargado';
    
    return (
        <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.05 }}
            className="group p-8 rounded-[3rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm hover:shadow-2xl transition-all relative overflow-hidden"
        >
            {/* Status Indicator Bar */}
            <div className={clsx(
                "absolute top-0 left-0 right-0 h-1.5",
                isOverloaded ? "bg-rose-500" : member.load_status === 'en_capacidad' ? "bg-amber-500" : "bg-emerald-500"
            )} />

            <div className="flex items-start justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="size-14 rounded-2xl bg-slate-100 dark:bg-white/10 flex items-center justify-center text-slate-400 group-hover:bg-blue-600 group-hover:text-white transition-all shadow-sm">
                        <span className="text-xl font-black">{member.name.substring(0, 2).toUpperCase()}</span>
                    </div>
                    <div>
                        <h4 className="text-lg font-black text-slate-900 dark:text-white leading-none mb-1">{member.name}</h4>
                        <span className={clsx(
                            "text-[9px] font-black uppercase tracking-widest",
                            isOverloaded ? "text-rose-500" : "text-slate-400"
                        )}>{member.load_status}</span>
                    </div>
                </div>
                {isOverloaded && <AlertTriangle className="text-rose-500 animate-bounce" size={20} />}
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="p-4 bg-slate-50 dark:bg-black/20 rounded-2xl border border-transparent group-hover:border-slate-100 dark:group-hover:border-white/5 transition-all">
                    <span className="text-[9px] font-black uppercase text-slate-400 block mb-1">Misiones Activas</span>
                    <div className="text-xl font-black text-slate-900 dark:text-white">{member.open}</div>
                </div>
                <div className="p-4 bg-slate-50 dark:bg-black/20 rounded-2xl border border-transparent group-hover:border-slate-100 dark:group-hover:border-white/5 transition-all">
                    <span className="text-[9px] font-black uppercase text-slate-400 block mb-1">Críticas / Hoy</span>
                    <div className={clsx("text-xl font-black", member.critical > 0 ? "text-rose-500" : "text-slate-900 dark:text-white")}>
                        {member.critical}
                    </div>
                </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
                <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest">
                    <span className="text-slate-400">Nivel de Saturación</span>
                    <span className={clsx(isOverloaded ? "text-rose-500" : "text-blue-600")}>{member.capacity_percent}%</span>
                </div>
                <div className="h-2.5 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden shadow-inner">
                    <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${member.capacity_percent}%` }}
                        transition={{ duration: 1, delay: 0.5 }}
                        className={clsx(
                            "h-full rounded-full shadow-[0_0_10px_rgba(37,99,235,0.3)]",
                            isOverloaded ? "bg-rose-500" : "bg-blue-600"
                        )} 
                    />
                </div>
            </div>

            {/* View Profile Action */}
            <div className="mt-8 pt-6 border-t border-slate-100 dark:border-white/5 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity translate-y-2 group-hover:translate-y-0 transition-transform">
                <span className="text-[10px] font-black uppercase text-blue-600 tracking-widest flex items-center gap-2">Ver Perfil Detallado <ChevronRight size={12} /></span>
                <div className="flex -space-x-2">
                    <div className="size-6 rounded-full bg-blue-100 border-2 border-white dark:border-[#1e1f21] flex items-center justify-center text-blue-600"><ShieldCheck size={10} /></div>
                    <div className="size-6 rounded-full bg-emerald-100 border-2 border-white dark:border-[#1e1f21] flex items-center justify-center text-emerald-600"><CheckCircle2 size={10} /></div>
                </div>
            </div>
        </motion.div>
    );
}

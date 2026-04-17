"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
    Users, 
    Search, 
    Filter, 
    ChevronRight, 
    Award, 
    TrendingUp, 
    CheckCircle2, 
    Star, 
    Zap,
    MoreHorizontal,
    Bot,
    Sparkles,
    ShieldCheck,
    ArrowUpRight,
    Target,
    Loader2,
    Clock
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface Candidate {
    id: number;
    username: string;
    email: string;
    progress: number;
    xp: number;
    status: string;
    target_level: string;
}

export default function CandidatesDashboard() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [candidates, setCandidates] = useState<Candidate[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    const fetchCandidates = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/academy/analytics/candidates', { token, cache: 'no-store' });
            // Transform backend data to frontend model
            const mapped = data.map(u => ({
                id: u.id,
                username: u.username,
                email: u.email,
                progress: u.progress || 0,
                xp: u.xp || 0,
                status: u.progress >= 100 ? 'ready' : 'near',
                target_level: u.progress >= 100 ? 'Discípulo' : 'Prospecto'
            }));
            setCandidates(mapped);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar candidatos", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchCandidates();
    }, [isAuthenticated, fetchCandidates]);

    const filteredCandidates = useMemo(() => {
        return candidates.filter(c => 
            c.username.toLowerCase().includes(search.toLowerCase())
        );
    }, [candidates, search]);

    const stats = useMemo(() => ({
        ready: candidates.filter(c => c.status === 'ready').length,
        evaluating: candidates.filter(c => c.status === 'near').length,
        highXp: candidates.filter(c => c.xp > 1000).length
    }), [candidates]);

    const columns = useMemo<ColumnDef<Candidate>[]>(() => [
        { 
            accessorKey: 'username', 
            header: 'Estudiante',
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-xl bg-slate-900 dark:bg-white/10 flex items-center justify-center text-white text-[10px] font-black uppercase border border-white/10">{row.original.username.charAt(0)}</div>
                    <div className="flex flex-col">
                        <span className="text-[13px] font-black text-slate-800 dark:text-slate-100 uppercase leading-none">{row.original.username}</span>
                        <span className="text-[10px] text-slate-400 font-bold tracking-widest mt-1">{row.original.email}</span>
                    </div>
                </div>
            )
        },
        { 
            accessorKey: 'progress', 
            header: 'Avance Formativo',
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="flex-1 h-1.5 w-32 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                        <motion.div initial={{ width: 0 }} animate={{ width: `${row.original.progress}%` }} className={clsx("h-full", row.original.progress >= 100 ? "bg-emerald-500" : "bg-blue-600")} />
                    </div>
                    <span className="text-[10px] font-black text-slate-500">{Math.round(row.original.progress)}%</span>
                </div>
            )
        },
        { 
            accessorKey: 'target_level', 
            header: 'Nivel Objetivo',
            cell: info => <span className="text-[11px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-[0.2em]">{info.getValue() as string}</span>
        },
        { 
            accessorKey: 'status', 
            header: 'Calificación IA',
            cell: ({ row }) => (
                <span className={clsx(
                    "px-4 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest border",
                    row.original.status === 'ready' ? "bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-900/20 dark:border-emerald-800" : "bg-blue-50 text-blue-600 border-blue-100 dark:bg-blue-900/20 dark:border-blue-800"
                )}>
                    {row.original.status === 'ready' ? 'Óptimo para Hito' : 'En Discipulado'}
                </span>
            )
        },
        {
            id: 'actions',
            header: '',
            cell: () => <button className="p-2 text-slate-300 hover:text-blue-600 transition-all hover:bg-blue-50 dark:hover:bg-white/5 rounded-xl"><ChevronRight size={18} /></button>
        }
    ], []);

    if (!isAuthenticated) return null;

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Analítica', icon: TrendingUp },
                { label: 'Candidatos a Hitos', icon: Award }
            ]}
        >
            <AdminHero
                eyebrow="Growth Analytics"
                title="Gestión de Candidatos"
                description="Identifica a los estudiantes que han cumplido con los requisitos académicos y de XP para avanzar en su ruta de crecimiento espiritual."
                tags={['Automated Screening', 'Real-time', 'Hitos']}
                watchers={['Coordinación Académica', 'Pastoral']}
                primaryAction={{ label: 'Aprobar Masivamente', icon: CheckCircle2, onClick: () => {} }}
                secondaryAction={{ label: 'Refrescar Lista', icon: Clock, onClick: fetchCandidates }}
            />

            <div className="space-y-10 pb-32">
                {/* Stats Grid Cinematic */}
                <section className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <CandidateStat label="Listos para Hito" value={stats.ready} icon={Award} color="emerald" auraColor="rgba(16, 185, 129, 0.15)" />
                    <CandidateStat label="En Evaluación" value={stats.evaluating} icon={Target} color="blue" auraColor="rgba(37, 99, 235, 0.15)" />
                    <CandidateStat label="Fidelidad Alta (XP)" value={stats.highXp} icon={Zap} color="amber" auraColor="rgba(245, 158, 11, 0.15)" />
                </section>

                {/* Main Table Area Cinematic */}
                <section className="bg-white dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 rounded-[3.5rem] p-10 shadow-xl space-y-10">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-8 px-4">
                        <div>
                            <h3 className="text-xl font-black tracking-tighter uppercase leading-none dark:text-white">Nómina de Candidatos</h3>
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-2">Basado en el rendimiento de los últimos 30 días</p>
                        </div>
                        <div className="relative w-full md:w-96 group">
                            <Search size={20} className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" />
                            <input 
                                value={search} onChange={e => setSearch(e.target.value)}
                                placeholder="Filtrar por nombre de estudiante..." 
                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-[2rem] py-5 px-14 text-sm font-bold outline-none focus:ring-8 focus:ring-blue-500/5 focus:border-blue-500 transition-all shadow-sm" 
                            />
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-20 flex flex-col items-center justify-center gap-4 text-slate-400 font-black uppercase tracking-[0.4em] animate-pulse">
                                <Loader2 className="animate-spin text-blue-600" size={48} /> Procesando Big Data...
                            </div>
                        ) : (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                                <DataTable data={filteredCandidates} columns={columns} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </section>
            </div>
        </AdminShell>
    );
}

function CandidateStat({ label, value, icon: Icon, color, auraColor }: any) {
    const colors: any = {
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-100 dark:border-emerald-800',
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-900/20 border-amber-100 dark:border-amber-800'
    };
    return (
        <div 
            className="p-10 bg-white dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 rounded-[3rem] shadow-sm flex items-center gap-8 group hover:shadow-2xl transition-all duration-500 relative overflow-hidden"
            style={{ '--aura-color': auraColor } as any}
        >
            <style jsx>{`
                .aura::after {
                    content: ''; position: absolute; inset: -1px; background: linear-gradient(45deg, var(--aura-color), transparent 60%);
                    z-index: -1; border-radius: inherit; opacity: 0; transition: opacity 0.5s ease;
                }
                .aura:hover::after { opacity: 1; }
            `}</style>
            <div className={clsx("aura size-16 rounded-[1.5rem] flex items-center justify-center transition-transform group-hover:rotate-12 duration-500 border shadow-inner shrink-0", colors[color])}>
                <Icon size={32} strokeWidth={1.5} />
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1 leading-none">{label}</p>
                <h4 className="text-4xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">{value}</h4>
            </div>
        </div>
    );
}



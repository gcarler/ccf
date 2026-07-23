"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
    Search, 
    ChevronRight, 
    Award, 
    TrendingUp, 
    CheckCircle2, 
    Zap,
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

interface CandidateRaw {
    id: number;
    username: string;
    email: string;
    progress?: number;
    xp?: number;
}

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

    const fetchCandidates = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<CandidateRaw[]>('/academy/analytics/candidates', { token, cache: 'no-store', signal });
            // Transform backend data to frontend model
            const mapped = data.map(u => ({
                id: u.id,
                username: u.username,
                email: u.email,
                progress: u.progress || 0,
                xp: u.xp || 0,
                status: (u.progress || 0) >= 100 ? 'ready' : 'near',
                target_level: (u.progress || 0) >= 100 ? 'Discípulo' : 'Prospecto'
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
        if (!isAuthenticated) return;
        const controller = new AbortController();
        fetchCandidates(controller.signal);
        return () => controller.abort();
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

    const handleApproveReady = () => {
        const readyCount = candidates.filter((candidate) => candidate.status === 'ready').length;
        addToast(`${readyCount} candidatos listos marcados para aprobación`, 'success');
    };

    const columns = useMemo<ColumnDef<Candidate>[]>(() => [
        { 
            accessorKey: 'username', 
            header: 'Estudiante',
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-md bg-[hsl(var(--bg-muted))] dark:bg-white/10 flex items-center justify-center text-white text-[10px] font-semibold uppercase border border-white/10">{row.original.username.charAt(0)}</div>
                    <div className="flex flex-col">
                        <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] uppercase leading-none">{row.original.username}</span>
                        <span className="text-[10px] text-[hsl(var(--text-secondary))] font-bold tracking-wide mt-1">{row.original.email}</span>
                    </div>
                </div>
            )
        },
        { 
            accessorKey: 'progress', 
            header: 'Avance Formativo',
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="flex-1 h-1.5 w-32 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                        <motion.div initial={{ width: 0 }} animate={{ width: `${row.original.progress}%` }} className={clsx("h-full", row.original.progress >= 100 ? "bg-emerald-500" : "bg-[hsl(var(--primary))]")} />
                    </div>
                    <span className="font-semibold text-[hsl(var(--text-secondary))]">{Math.round(row.original.progress)}%</span>
                </div>
            )
        },
        { 
            accessorKey: 'target_level', 
            header: 'Nivel Objetivo',
            cell: info => <span className="font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] uppercase tracking-wide">{info.getValue() as string}</span>
        },
        { 
            accessorKey: 'status', 
            header: 'Calificación IA',
            cell: ({ row }) => (
                <span className={clsx(
                    "px-4 py-1.5 rounded-md text-[9px] font-semibold uppercase tracking-wide border",
                    row.original.status === 'ready' ? "bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-900/20 dark:border-emerald-800" : "bg-blue-50 text-[hsl(var(--primary))] border-blue-100 dark:bg-blue-900/20 dark:border-blue-800"
                )}>
                    {row.original.status === 'ready' ? 'Óptimo para Hito' : 'En Discipulado'}
                </span>
            )
        },
        {
            id: 'actions',
            header: '',
            cell: () => <button className="p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all hover:bg-blue-50 dark:hover:bg-white/5 rounded-md"><ChevronRight size={18} /></button>
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
                description="Identifica a los participantes que han cumplido con los requisitos académicos y de XP para avanzar en su ruta de crecimiento espiritual."
                tags={['Automated Screening', 'Real-time', 'Hitos']}
                watchers={['Coordinación Académica', 'Pastoral']}
                primaryAction={{ label: 'Aprobar Masivamente', icon: CheckCircle2, onClick: handleApproveReady }}
                secondaryAction={{ label: 'Refrescar Lista', icon: Clock, onClick: fetchCandidates }}
            />

            <div className="space-y-3 pb-4">
                {/* Stats Grid Cinematic */}
                <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <CandidateStat label="Listos para Hito" value={stats.ready} icon={Award} color="emerald" auraColor="rgba(16, 185, 129, 0.15)" />
                    <CandidateStat label="En Evaluación" value={stats.evaluating} icon={Target} color="blue" auraColor="rgba(37, 99, 235, 0.15)" />
                    <CandidateStat label="Fidelidad Alta (XP)" value={stats.highXp} icon={Zap} color="amber" auraColor="rgba(245, 158, 11, 0.15)" />
                </section>

                {/* Main Table Area Cinematic */}
                <section className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 shadow-xl space-y-3">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 px-4">
                        <div>
                            <h3 className="text-xl font-bold tracking-tighter uppercase leading-none dark:text-white">Nómina de Candidatos</h3>
                            <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-2">Basado en el rendimiento de los últimos 30 días</p>
                        </div>
                        <div className="relative w-full md:w-96 group">
                            <Search size={20} className="absolute left-5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] group-focus-within:text-[hsl(var(--primary))] transition-colors" />
                            <input 
                                value={search} onChange={e => setSearch(e.target.value)}
                                placeholder="Filtrar por nombre de participante..." 
                                className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg py-2 px-4 text-sm font-bold outline-none focus:ring-8 focus:ring-[hsl(var(--primary))]/5 focus:border-blue-500 transition-all shadow-sm" 
                            />
                        </div>
                    </div>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-1.5 flex flex-col items-center justify-center gap-4 text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide animate-pulse">
                                <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={48} /> Procesando Big Data...
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
        blue: 'text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-900/20 border-amber-100 dark:border-amber-800'
    };
    return (
        <div
            className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg shadow-sm flex items-center gap-3 group hover:shadow-2xl transition-all duration-500 relative overflow-hidden"
            style={{ '--aura-color': auraColor } as any}
        >
            <style jsx>{`
                .aura::after {
                    content: ''; position: absolute; inset: -1px; background: linear-gradient(45deg, var(--aura-color), transparent 60%);
                    z-index: -1; border-radius: inherit; opacity: 0; transition: opacity 0.5s ease;
                }
                .aura:hover::after { opacity: 1; }
            `}</style>
            <div className={clsx("aura size-8 rounded-lg flex items-center justify-center transition-transform group-hover:rotate-12 duration-500 border shadow-inner shrink-0", colors[color])}>
                <Icon size={32} strokeWidth={1.5} />
            </div>
            <div>
                <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1 leading-none">{label}</p>
                <h4 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">{value}</h4>
            </div>
        </div>
    );
}



"use client";

import React, { useState, useEffect, useMemo } from 'react';
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
    Target
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import { motion } from 'framer-motion';
import clsx from 'clsx';

export default function CandidatesDashboard() {
    const { token, isAuthenticated } = useAuth();
    const [candidates, setCandidates] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    useEffect(() => {
        const fetchCandidates = async () => {
            if (!token) return;
            try {
                // Mock data for high-quality preview
                setCandidates([
                    { id: 1, name: 'Ricardo Mendez', progress: 95, xp: 480, target_level: 'Discípulo', status: 'ready' },
                    { id: 2, name: 'Elena Rodriguez', progress: 100, xp: 1950, target_level: 'Líder', status: 'ready' },
                    { id: 3, name: 'Marcos Lopez', progress: 85, xp: 420, target_level: 'Discípulo', status: 'near' },
                    { id: 4, name: 'Ana Victoria', progress: 100, xp: 4900, target_level: 'Pastor', status: 'ready' },
                ]);
            } finally {
                setLoading(false);
            }
        };
        fetchCandidates();
    }, [token]);

    const columns = useMemo<ColumnDef<any>[]>(() => [
        { 
            accessorKey: 'name', 
            header: 'Estudiante',
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-xl bg-slate-900 flex items-center justify-center text-white text-[10px] font-black uppercase">{row.original.name.charAt(0)}</div>
                    <span className="text-[13px] font-black text-slate-800 dark:text-white uppercase">{row.original.name}</span>
                </div>
            )
        },
        { 
            accessorKey: 'progress', 
            header: 'Progreso Academia',
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="flex-1 h-1.5 w-24 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-600" style={{ width: `${row.original.progress}%` }} />
                    </div>
                    <span className="text-[10px] font-black text-slate-500">{row.original.progress}%</span>
                </div>
            )
        },
        { 
            accessorKey: 'target_level', 
            header: 'Nivel Objetivo',
            cell: info => <span className="text-[11px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest">{info.getValue() as string}</span>
        },
        { 
            accessorKey: 'status', 
            header: 'Estatus',
            cell: ({ row }) => (
                <span className={clsx(
                    "px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest",
                    row.original.status === 'ready' ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-blue-600"
                )}>
                    {row.original.status === 'ready' ? 'Listo para Hito' : 'En camino'}
                </span>
            )
        },
        {
            id: 'actions',
            header: '',
            cell: () => <button className="p-2 text-slate-300 hover:text-blue-600"><ChevronRight size={18} /></button>
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
                secondaryAction={{ label: 'Exportar Lista', icon: ArrowUpRight, onClick: () => {} }}
            />

            <div className="space-y-8 pb-32">
                {/* Stats Grid */}
                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <CandidateStat label="Listos para Hito" value="12" icon={Award} color="emerald" />
                    <CandidateStat label="En Evaluación" value="45" icon={Target} color="blue" />
                    <CandidateStat label="Próximos (90%+)" value="8" icon={Zap} color="amber" />
                </section>

                {/* Main Table Area */}
                <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 px-4">
                        <h3 className="text-xl font-black tracking-tight uppercase tracking-widest leading-none">Listado de Seguimiento</h3>
                        <div className="relative w-full md:w-80">
                            <input 
                                value={search} onChange={e => setSearch(e.target.value)}
                                placeholder="Buscar por nombre..." 
                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl py-3 px-12 text-sm font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all" 
                            />
                            <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                        </div>
                    </div>

                    <DataTable data={candidates} columns={columns} />
                </section>
            </div>
        </AdminShell>
    );
}

function CandidateStat({ label, value, icon: Icon, color }: any) {
    const colors: any = {
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20',
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-900/20'
    };
    return (
        <div className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm flex items-center gap-6 group hover:shadow-xl transition-all">
            <div className={clsx("size-14 rounded-2xl flex items-center justify-center transition-transform group-hover:rotate-12", colors[color])}>
                <Icon size={28} />
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 leading-none">{label}</p>
                <h4 className="text-3xl font-black text-slate-900 dark:text-white tracking-tighter">{value}</h4>
            </div>
        </div>
    );
}

"use client";

import React, { useEffect, useState } from 'react';
import {
    Users, AlertTriangle,
    ChevronRight, UserPlus
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import ProjectsShell from '@/components/projects/ProjectsShell';
import Skeleton from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';
import RightPanel from '@/components/ui/RightPanel';
import { useSidebarLayers } from '@/context/SidebarLayerContext';

interface TeamPersona {
    persona_id: string;
    name: string;
    load_status: string;
    open: number;
    critical: number;
    capacity_percent: number;
}

export default function TeamPage() {
    const { token } = useAuth();
    const { openLayer, closeLayer, setRightMode, layers } = useSidebarLayers();
    const [team, setTeam] = useState<TeamPersona[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedPersona, setSelectedPersona] = useState<TeamPersona | null>(null);

    useEffect(() => {
        if (!layers.RIGHT && selectedPersona) setSelectedPersona(null);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [layers.RIGHT]);

    useEffect(() => {
        if (!token) return;
        apiFetch<TeamPersona[]>('/system/workload', { token })
            .then(data => setTeam(Array.isArray(data) ? data : []))
            .catch(() => setTeam([]))
            .finally(() => setLoading(false));
    }, [token]);

    const handleSelect = (persona: TeamPersona) => {
        setSelectedPersona(persona);
        setRightMode('overlay');
        openLayer('RIGHT');
    };

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Users }, { label: 'Equipo', icon: Users }]}
        >
            <div className="flex-1 flex flex-col font-display">
                <div className="w-full mx-auto p-3 space-y-3 pb-4">

                    {/* Sub-header */}
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center">
                                    <Users size={14} className="text-[hsl(var(--primary))]" />
                                </div>
                                <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Recursos Humanos</span>
                            </div>
                            <h1 className="text-xl font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white leading-none">
                                Equipo del Proyecto
                            </h1>
                            <p className="text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-0.5 font-medium">
                                Disponibilidad y saturación del equipo ministerial en tiempo real.
                            </p>
                        </div>
                        <div className="flex items-center gap-3">
                            {!loading && team.length > 0 && (
                                <div className="px-4 py-2 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] rounded-md border border-[hsl(var(--border))] dark:border-white/[0.06] shadow-sm text-center">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Cap. Prom.</p>
                                    <p className="text-sm font-semibold text-[hsl(var(--primary))]">
                                        {Math.round(team.reduce((a, m) => a + m.capacity_percent, 0) / team.length)}%
                                    </p>
                                </div>
                            )}
                            <button className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all">
                                <UserPlus size={13} /> Invitar
                            </button>
                        </div>
                    </div>
                    {loading ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-48 rounded-lg" />)}
                        </div>
                    ) : team.length === 0 ? (
                        <EmptyState
                            icon={Users}
                            title="No hay personas en el equipo"
                            description="Invita colaboradores al proyecto para visualizar su carga y disponibilidad aquí."
                        />
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {team.map((persona, idx) => {
                                const isOverloaded = persona.load_status === 'sobrecargado';
                                return (
                                    <motion.div
                                        key={persona.persona_id}
                                        initial={{ opacity: 0, scale: 0.97 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: idx * 0.05 }}
                                        onClick={() => handleSelect(persona)}
                                        className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/[0.06] p-3 shadow-sm hover:shadow-xl hover:shadow-black/10/60 dark:hover:shadow-black/30 transition-all cursor-pointer overflow-hidden active:scale-[0.99]"
                                    >
                                        {/* Status bar */}
                                        <div className={clsx(
                                            "absolute top-0 left-0 right-0 h-[3px]",
                                            isOverloaded ? "bg-rose-500" :
                                            persona.load_status === 'en_capacidad' ? "bg-amber-500" : "bg-emerald-500"
                                        )} />

                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex items-center gap-3">
                                                <div className="size-8 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all shadow-sm font-bold text-xs">
                                                    {persona.name.substring(0, 2).toUpperCase()}
                                                </div>
                                                <div>
                                                    <p className="text-[13px] font-medium text-[hsl(var(--text-primary))] dark:text-white leading-none">{persona.name}</p>
                                                    <span className={clsx(
                                                        "text-[9px] font-semibold uppercase tracking-wide mt-0.5 block",
                                                        isOverloaded ? "text-rose-500" : "text-[hsl(var(--text-secondary))]"
                                                    )}>{persona.load_status}</span>
                                                </div>
                                            </div>
                                            {isOverloaded && <AlertTriangle className="text-rose-500 shrink-0" size={16} />}
                                        </div>

                                        <div className="grid grid-cols-2 gap-2 mb-3">
                                            <div className="p-2 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md">
                                                <p className="text-[9px] font-bold uppercase text-[hsl(var(--text-secondary))] mb-0.5">Activas</p>
                                                <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">{persona.open}</p>
                                            </div>
                                            <div className="p-2 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md">
                                                <p className="text-[9px] font-bold uppercase text-[hsl(var(--text-secondary))] mb-0.5">Criticas</p>
                                                <p className={clsx("text-lg font-bold", persona.critical > 0 ? "text-rose-500" : "text-[hsl(var(--text-primary))] dark:text-white")}>
                                                    {persona.critical}
                                                </p>
                                            </div>
                                        </div>

                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wide">
                                                <span className="text-[hsl(var(--text-secondary))]">Saturación</span>
                                                <span className={isOverloaded ? "text-rose-500" : "text-[hsl(var(--primary))]"}>{persona.capacity_percent}%</span>
                                            </div>
                                            <div className="h-1.5 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                                                <motion.div
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${persona.capacity_percent}%` }}
                                                    transition={{ duration: 0.8, delay: idx * 0.05 + 0.3 }}
                                                    className={clsx("h-full rounded-full", isOverloaded ? "bg-rose-500" : "bg-[hsl(var(--primary))]")}
                                                />
                                            </div>
                                        </div>

                                        <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-[10px] font-semibold uppercase text-[hsl(var(--primary))] tracking-wide">
                                            Ver detalle <ChevronRight size={11} />
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Right Panel — Persona Detail (no modal) */}
            {selectedPersona && (
                <RightPanel title="Perfil de Carga" width={360}>
                    <div className="p-3 space-y-3">
                        <div className="flex items-center gap-3">
                            <div className="size-10 rounded-md bg-[hsl(var(--primary))] flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-blue-500/20">
                                {selectedPersona.name.substring(0, 2).toUpperCase()}
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">{selectedPersona.name}</h3>
                                <span className={clsx(
                                    "text-[9px] font-semibold uppercase tracking-wide",
                                    selectedPersona.load_status === 'sobrecargado' ? "text-rose-500" : "text-emerald-500"
                                )}>{selectedPersona.load_status}</span>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            {[
                                { label: 'Tareas Activas', value: selectedPersona.open, color: 'text-[hsl(var(--primary))]' },
                                { label: 'Criticas Hoy', value: selectedPersona.critical, color: 'text-rose-500' },
                                { label: 'Saturacion', value: `${selectedPersona.capacity_percent}%`, color: selectedPersona.capacity_percent > 80 ? 'text-rose-500' : 'text-[hsl(var(--primary))]' },
                                { label: 'Estado', value: selectedPersona.load_status === 'disponible' ? 'Disponible' : 'Ocupado', color: 'text-emerald-500' },
                            ].map(item => (
                                <div key={item.label} className="bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-md p-2 border border-[hsl(var(--border))] dark:border-white/5">
                                    <p className="text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{item.label}</p>
                                    <p className={clsx("text-lg font-bold mt-0.5", item.color)}>{item.value}</p>
                                </div>
                            ))}
                        </div>

                        <button
                            onClick={() => closeLayer('RIGHT')}
                            className="w-full py-2 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all"
                        >
                            Cerrar
                        </button>
                    </div>
                </RightPanel>
            )}
        </ProjectsShell>
    );
}

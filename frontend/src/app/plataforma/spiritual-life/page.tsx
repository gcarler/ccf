"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
    Heart, Zap, Waves, Star, Shield, Award, ChevronRight,
    Calendar, BookOpen, TrendingUp, Users,
    Sparkles, CheckCircle2, Circle, Lock
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import Link from 'next/link';
import clsx from 'clsx';

// ── Types
interface AcademyProgress {
    completed_courses: number;
    total_courses: number;
    level: string;
}

// ── Milestone definitions
const MILESTONE_DEFS = [
    { key: 'Decision_Fe',      label: 'Decisión de Fe',         icon: Zap,    color: 'text-[hsl(var(--warning))]',  bg: 'bg-warning-soft dark:bg-[hsl(var(--warning))]/20',  border: 'border-[hsl(var(--warning)/25%)] dark:border-[hsl(var(--warning)/100%)]/20' },
    { key: 'Bautismo_Aguas',   label: 'Bautismo en Aguas',      icon: Waves,  color: 'text-[hsl(var(--domain-cyan)/90%)]',   bg: 'bg-[hsl(var(--domain-cyan)/10%)] dark:bg-[hsl(var(--domain-cyan)/20%)]',    border: 'border-[hsl(var(--domain-cyan)/30%)] dark:border-[hsl(var(--domain-cyan)/20%)]' },
    { key: 'Bautismo_Espiritu',label: 'Bautismo del Espíritu',  icon: Star,   color: 'text-[hsl(var(--primary))]', bg: 'bg-info-soft dark:bg-[hsl(var(--info))]/20',border: 'border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/100%)]/20' },
    { key: 'Persona_Oficial',  label: 'Participación Oficial',      icon: Shield, color: 'text-success-text',bg: 'bg-success-soft dark:bg-[hsl(var(--success))]/20',border: 'border-[hsl(var(--success)/25%)] dark:border-[hsl(var(--success)/100%)]/20' },
    { key: 'Liderazgo',        label: 'Llamado al Liderazgo',   icon: Users,  color: 'text-[hsl(var(--primary))]',   bg: 'bg-info-soft dark:bg-[hsl(var(--info))]/20',    border: 'border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/100%)]/20' },
];

// ── Discipleship steps
const DISCIPULADO_STEPS = [
    { id: 1, label: 'Descubriendo a Jesús',     desc: 'Las bases del evangelio y la salvación', done: true  },
    { id: 2, label: 'Vida Nueva',               desc: 'Fundamentos de la vida cristiana',        done: true  },
    { id: 3, label: 'Creciendo en Cristo',       desc: 'Hábitos espirituales y comunidad',        done: false },
    { id: 4, label: 'Sirviendo con Propósito',  desc: 'Identificación y activación de dones',     done: false },
    { id: 5, label: 'Multiplicando Vidas',      desc: 'Discipulado y reproducción ministerial',   done: false },
];

export default function SpiritualLifePage() {
    const { token, user } = useAuth();
    const [milestones, setMilestones] = useState<string[]>([]);
    const [academyProgress, setAcademyProgress] = useState<AcademyProgress | null>(null);
    const [loading, setLoading] = useState(true);

    const loadSpiritualMilestones = useCallback(async (signal?: AbortSignal) => {
        if (!token || !user?.id) { setLoading(false); return; }
        try {
            const data = await apiFetch<{ type: string }[]>(`/spiritual-life/milestones/${user.id}`, { token, cache: 'no-store', signal });
            setMilestones(Array.isArray(data) ? data.map((m) => m.type) : []);
        } catch {
            setMilestones([]);
        } finally {
            setLoading(false);
        }
    }, [token, user]);

    const loadAcademyProgress = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        try {
            const courses = await apiFetch<any>('/academy/enrollments', { token, cache: 'no-store', signal });
            if (Array.isArray(courses)) {
                const completed = courses.filter((c: any) => c.completed).length;
                setAcademyProgress({ completed_courses: completed, total_courses: courses.length, level: 'Fundamentos' });
            }
        } catch {
            setAcademyProgress({ completed_courses: 0, total_courses: 0, level: 'Fundamentos' });
        }
    }, [token]);

    useEffect(() => {
        const controller = new AbortController();
        loadSpiritualMilestones(controller.signal);
        loadAcademyProgress(controller.signal);
        return () => controller.abort();
    }, [loadSpiritualMilestones, loadAcademyProgress]);

    const nextMilestone = MILESTONE_DEFS.find(m => !milestones.includes(m.key));
    const progressPct = Math.round((milestones.length / MILESTONE_DEFS.length) * 100);
    const discipuladoDone = DISCIPULADO_STEPS.filter(s => s.done).length;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] dark:bg-[#111213] overflow-y-auto font-display">
                <div className="w-full p-4 md:p-6 space-y-4">

                    {/* ── HERO HEADER ─────────────────────────────────────────────── */}
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <div className="size-8 rounded-md bg-[hsl(var(--danger-muted))] dark:bg-[hsl(var(--danger))]/30 flex items-center justify-center">
                                    <Heart size={16} className="text-danger-text" fill="currentColor" />
                                </div>
                                <span className="text-[10px] font-semibold uppercase tracking-wide text-danger-text">Vida Espiritual</span>
                            </div>
                            <h1 className="text-xl font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white leading-none">
                                Tu Caminar con Cristo
                            </h1>
                            <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-1 font-medium">
                                Registra y celebra cada hito de tu vida espiritual en CCF.
                            </p>
                        </div>

                        <Link href="/plataforma/spiritual-life/timeline">
                            <motion.button
                                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                className="flex items-center gap-2 px-3 py-2.5 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/25%)]"
                            >
                                <Calendar size={14} /> Ver Línea de Tiempo
                            </motion.button>
                        </Link>
                    </div>

                    {/* ── KPI CARDS ──────────────────────────────────────────────── */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        {[
                            { label: 'Hitos Espirituales', value: `${milestones.length}/${MILESTONE_DEFS.length}`, icon: Zap, color: 'text-warning-text', bg: 'bg-warning-soft dark:bg-[hsl(var(--warning))]/20' },
                            { label: 'Progreso Espiritual', value: `${progressPct}%`, icon: TrendingUp, color: 'text-[hsl(var(--primary))]', bg: 'bg-info-soft dark:bg-[hsl(var(--info))]/20' },
                            { label: 'Cursos en Academia', value: `${academyProgress?.completed_courses ?? '–'}/${academyProgress?.total_courses ?? '–'}`, icon: BookOpen, color: 'text-success-text', bg: 'bg-success-soft dark:bg-[hsl(var(--success))]/20' },
                            { label: 'Nivel de Discipulado', value: `${discipuladoDone}/5`, icon: Star, color: 'text-[hsl(var(--primary))]', bg: 'bg-info-soft dark:bg-[hsl(var(--info))]/20' },
                        ].map((kpi, i) => (
                            <motion.div key={i}
                                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
                                className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] border border-[hsl(var(--border))] dark:border-white/7 rounded-lg p-3 shadow-sm hover:shadow-md transition-all"
                            >
                                <div className={clsx("size-9 rounded-md flex items-center justify-center mb-3", kpi.bg)}>
                                    <kpi.icon size={17} className={kpi.color} />
                                </div>
                                <div className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">{kpi.value}</div>
                                <div className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mt-0.5">{kpi.label}</div>
                            </motion.div>
                        ))}
                    </div>

                    {/* ── MAIN GRID ──────────────────────────────────────────────── */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">

                        {/* Left: Milestones journey ── */}
                        <div className="lg:col-span-2 space-y-4">
                            <div className="flex items-center justify-between mb-1">
                                <h2 className="text-[11px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Hitos Espirituales</h2>
                                <span className="text-[10px] font-bold text-[hsl(var(--primary))] bg-info-soft dark:bg-[hsl(var(--info))]/20 px-2 py-0.5 rounded-full">
                                    {milestones.length} alcanzados
                                </span>
                            </div>

                            <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] border border-[hsl(var(--border))] dark:border-white/7 rounded-lg overflow-hidden shadow-sm">
                                {MILESTONE_DEFS.map((m, i) => {
                                    const reached = milestones.includes(m.key);
                                    const isNext = !reached && m.key === nextMilestone?.key;
                                    return (
                                        <motion.div key={m.key}
                                            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}
                                            className={clsx(
                                                "flex items-center gap-4 px-3 py-1.5 border-b border-[hsl(var(--border))] dark:border-white/5 last:border-0 transition-all",
                                                reached ? "opacity-100" : isNext ? "opacity-90" : "opacity-40"
                                            )}
                                        >
                                            {/* Icon */}
                                            <div className={clsx("size-10 rounded-md flex items-center justify-center border shrink-0", m.bg, m.border)}>
                                                <m.icon size={18} className={m.color} />
                                            </div>

                                            {/* Text */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white truncate">{m.label}</p>
                                                    {isNext && (
                                                        <span className="px-2 py-0.5 bg-info-soft dark:bg-[hsl(var(--info))]/30 text-[hsl(var(--primary))] text-[9px] font-semibold uppercase tracking-wide rounded-full">
                                                            Siguiente
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Status */}
                                            {reached ? (
                                                <CheckCircle2 size={18} className="text-[hsl(var(--success))] shrink-0" />
                                            ) : isNext ? (
                                                <Circle size={18} className="text-[hsl(var(--primary))] shrink-0 animate-pulse" />
                                            ) : (
                                                <Lock size={15} className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] shrink-0" />
                                            )}
                                        </motion.div>
                                    );
                                })}
                            </div>

                            {/* Spiritual progress bar */}
                            <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] border border-[hsl(var(--border))] dark:border-white/7 rounded-lg p-3 shadow-sm">
                                <div className="flex items-center justify-between mb-3">
                                    <span className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Progreso espiritual</span>
                                    <span className="font-semibold text-[hsl(var(--primary))]">{progressPct}%</span>
                                </div>
                                <div className="h-2.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full bg-gradient-to-r from-[hsl(var(--info))] to-[hsl(var(--info))] rounded-full"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progressPct}%` }}
                                        transition={{ duration: 1.2, ease: 'easeOut' }}
                                    />
                                </div>
                                <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-2">
                                    {nextMilestone
                                        ? `Próximo hito: ${nextMilestone.label}`
                                        : '¡Has completado todos los hitos! 🎉'
                                    }
                                </p>
                            </div>
                        </div>

                        {/* Right column ── */}
                        <div className="space-y-4">

                            {/* Discipleship path */}
                            <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] border border-[hsl(var(--border))] dark:border-white/7 rounded-lg overflow-hidden shadow-sm">
                                <div className="px-3 py-1.5 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between">
                                    <h3 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ruta de Discipulado</h3>
                                    <span className="font-semibold text-[hsl(var(--text-secondary))]">{discipuladoDone}/5</span>
                                </div>
                                <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                                    {DISCIPULADO_STEPS.map(step => (
                                        <div key={step.id} className={clsx(
                                            "flex items-start gap-3 px-3 py-3 transition-all",
                                            !step.done && "opacity-50"
                                        )}>
                                            <div className={clsx(
                                                "size-5 rounded-full shrink-0 flex items-center justify-center mt-0.5",
                                                step.done
                                                    ? "bg-[hsl(var(--success-muted))] dark:bg-[hsl(var(--success))]/30"
                                                    : "bg-[hsl(var(--surface-2))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10"
                                            )}>
                                                {step.done
                                                    ? <CheckCircle2 size={12} className="text-success-text" />
                                                    : <span className="font-semibold text-[hsl(var(--text-secondary))]">{step.id}</span>
                                                }
                                            </div>
                                            <div>
                                                <p className="text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{step.label}</p>
                                                <p className="text-[10px] text-[hsl(var(--text-secondary))] leading-snug">{step.desc}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Quick links */}
                            <div className="space-y-2">
                                <Link href="/plataforma/spiritual-life/timeline">
                                    <div className="flex items-center gap-3 p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] border border-[hsl(var(--border))] dark:border-white/7 rounded-lg shadow-sm hover:shadow-md hover:border-[hsl(var(--info)/25%)] dark:hover:border-white/15 transition-all cursor-pointer group">
                                        <div className="size-9 rounded-md bg-info-soft dark:bg-[hsl(var(--info))]/20 flex items-center justify-center">
                                            <Calendar size={16} className="text-[hsl(var(--primary))]" />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white">Línea de Tiempo</p>
                                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">Todos tus hitos cronológicos</p>
                                        </div>
                                        <ChevronRight size={14} className="text-[hsl(var(--text-secondary))] group-hover:translate-x-1 transition-transform" />
                                    </div>
                                </Link>

                                <Link href="/plataforma/spiritual-life/certificates">
                                    <div className="flex items-center gap-3 p-4 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] border border-[hsl(var(--border))] dark:border-white/7 rounded-lg shadow-sm hover:shadow-md hover:border-[hsl(var(--info)/25%)] dark:hover:border-white/15 transition-all cursor-pointer group">
                                        <div className="size-9 rounded-md bg-[hsl(var(--domain-cyan)/10%)] dark:bg-[hsl(var(--domain-cyan)/20%)] flex items-center justify-center">
                                            <Award size={16} className="text-[hsl(var(--domain-cyan)/90%)]" />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white">Mis Certificados</p>
                                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">Descarga tus actas y diplomas</p>
                                        </div>
                                        <ChevronRight size={14} className="text-[hsl(var(--text-secondary))] group-hover:translate-x-1 transition-transform" />
                                    </div>
                                </Link>

                                <Link href="/plataforma/academy">
                                    <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-[hsl(var(--info))] to-[hsl(var(--info))] rounded-lg shadow-lg shadow-[hsl(var(--info)/20%)] hover:shadow-[hsl(var(--info)/30%)] transition-all cursor-pointer group">
                                        <div className="size-9 rounded-md bg-white/20 flex items-center justify-center">
                                            <Sparkles size={16} className="text-white" />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[13px] font-bold text-white">Academia CCF</p>
                                            <p className="text-[10px] text-white/70">Continúa tu formación ministerial</p>
                                        </div>
                                        <ChevronRight size={14} className="text-white/60 group-hover:translate-x-1 transition-transform" />
                                    </div>
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
        </div>
    );
}


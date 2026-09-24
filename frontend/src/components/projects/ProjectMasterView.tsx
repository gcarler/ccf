"use client";

import { useState, useEffect, useCallback, ElementType } from 'react';
import { motion } from 'framer-motion';
import {
    Radio, Share2, Globe, CheckCircle2, Clock,
    Zap, Trophy, Calendar, TrendingUp, AlertCircle,
    ArrowUpRight, BarChart3, Plus, Trash2,
    Target, Sliders, Activity, AlertTriangle, AlertOctagon, Sparkles,
    Wallet, TrendingDown, ShieldAlert, Users, Scale,
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectRecord, ProjectTaskRecord, ProjectMilestoneRecord, ProjectAnalytics, ProjectKPI, ProjectBudgetSummary, ProjectRiskSummary, ProjectWorkloadSummary } from '@/types/projects';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { InlineTextArea } from '@/components/ui/inline-editors/InlineTextArea';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import { InlineUserPicker } from '@/components/ui/inline-editors';
import { InlineDatePicker } from '@/components/ui/inline-editors/InlineDatePicker';
import { ProjectKpiDrawer } from '@/components/projects/ProjectKpiDrawer';
import { ProgressSettingsDrawer } from '@/components/projects/ProgressSettingsDrawer';
import { ProjectBudgetDrawer } from '@/components/projects/ProjectBudgetDrawer';
import { ProjectRiskMatrixDrawer } from '@/components/projects/ProjectRiskMatrixDrawer';
import { ProjectWorkloadDrawer } from '@/components/projects/ProjectWorkloadDrawer';
import { useProjectUpdate } from '@/context/ProjectUpdateContext';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';

interface ProjectMasterViewProps {
    project: ProjectRecord;
    tasks: ProjectTaskRecord[];
    onOpenTask?: (task: ProjectTaskRecord) => void;
}

/**
 * Vista maulla del proyecto (sustituye al antiguo card de hitos en `page.tsx`).
 *
 * Autosuficiente: consume `useProjectUpdate()` para mutar proyecto / tareas y
 * hace sus propias llamadas a `/projects/{id}/milestones[/...]`. Solo necesita
 * `onOpenTask` para delegar al TaskDetailPanel externo.
 *
 * Decisiones de scope:
 *  - "Nodos operativos" hoy son un agrupador visual por prefijo semántico en
 *    `task.title`. Persistir la pertenencia es scope de otra fase; este
 *    cambio solo añade edición inline de cada tarea (status + título con
 *    preservación del prefijo).
 *  - Hitos: CRUD completo inline (PATCH / DELETE / POST) + confirm nativo.
 */
export function ProjectMasterView({ project, tasks, onOpenTask }: ProjectMasterViewProps) {
    const { token } = useAuth();
    const { addToast } = useToast();
    const { reloadProject, updateProject, updateTask } = useProjectUpdate();
    const [busyMilestoneId, setBusyMilestoneId] = useState<string | null>(null);
    const [newMilestone, setNewMilestone] = useState<{ title: string; date: string | null }>({ title: '', date: null });
    const [addingMilestone, setAddingMilestone] = useState(false);
    const [analytics, setAnalytics] = useState<ProjectAnalytics | null>(null);

    // Indicadores (KPIs) & Avance Inteligente (PRO)
    const [kpis, setKpis] = useState<ProjectKPI[]>(project.kpis || []);
    const [showKpiDrawer, setShowKpiDrawer] = useState(false);
    const [showProgressDrawer, setShowProgressDrawer] = useState(false);

    // Control Presupuestario (Super-PRO)
    const [budgetSummary, setBudgetSummary] = useState<ProjectBudgetSummary | null>(project.budget_summary || null);
    const [showBudgetDrawer, setShowBudgetDrawer] = useState(false);

    // Matriz RAID de Riesgos (Super-PRO Fase 2)
    const [risksSummary, setRisksSummary] = useState<ProjectRiskSummary | null>(project.risks_summary || null);
    const [showRiskDrawer, setShowRiskDrawer] = useState(false);

    // Carga de Trabajo y Capacidad (Super-PRO Fase 3)
    const [workloadSummary, setWorkloadSummary] = useState<ProjectWorkloadSummary | null>(project.workload_summary || null);
    const [showWorkloadDrawer, setShowWorkloadDrawer] = useState(false);

    const loadKpis = useCallback(async () => {
        if (!project.id || !token) return;
        try {
            const data = await apiFetch<ProjectKPI[]>(`/projects/${project.id}/kpis`, { token });
            if (Array.isArray(data)) setKpis(data);
        } catch {
            if (project.kpis) setKpis(project.kpis);
        }
    }, [project.id, project.kpis, token]);

    const loadBudgetSummary = useCallback(async () => {
        if (!project.id || !token) return;
        try {
            const data = await apiFetch<ProjectBudgetSummary>(`/projects/${project.id}/budget-summary`, { token });
            if (data) setBudgetSummary(data);
        } catch {
            // fallback silencioso
        }
    }, [project.id, token]);

    const loadRisksSummary = useCallback(async () => {
        if (!project.id || !token) return;
        try {
            const data = await apiFetch<ProjectRiskSummary>(`/projects/${project.id}/risks-summary`, { token });
            if (data) setRisksSummary(data);
        } catch {
            // fallback silencioso
        }
    }, [project.id, token]);

    const loadWorkloadSummary = useCallback(async () => {
        if (!project.id || !token) return;
        try {
            const data = await apiFetch<ProjectWorkloadSummary>(`/projects/${project.id}/workload`, { token });
            if (data) setWorkloadSummary(data);
        } catch {
            // fallback silencioso
        }
    }, [project.id, token]);

    useEffect(() => {
        loadKpis();
        loadBudgetSummary();
        loadRisksSummary();
        loadWorkloadSummary();
    }, [loadKpis, loadBudgetSummary, loadRisksSummary, loadWorkloadSummary]);

    const handleKpisUpdated = async () => {
        await loadKpis();
        await reloadProject();
    };

    const handleProgressSaved = async () => {
        await reloadProject();
    };

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const data = await apiFetch<ProjectAnalytics>(`/projects/${project.id}/analytics`, { token });
                if (!cancelled) setAnalytics(data);
            } catch {
                if (!cancelled) setAnalytics(null);
            }
        })();
        return () => { cancelled = true; };
    }, [project.id, token]);

    // Nodos operativos reales (F2): agrupación por la columna persistida ``node``
    // (antes por prefijo en ``task.title``).
    const nutritionTasks = tasks.filter(t => t.node === 'nutrition');
    const webTasks = tasks.filter(t => t.node === 'digital');

    const milestones = project.milestones || [];
    const dbProgress = project.progress_percent || 0;

    // ── HITOS ─────────────────────────────────────────────────────────────
    const milestonePatch = async (id: string, patch: Partial<ProjectMilestoneRecord>) => {
        setBusyMilestoneId(id);
        try {
            await apiFetch(`/projects/${project.id}/milestones/${id}`, {
                method: 'PATCH', token, body: patch,
            });
            await reloadProject();
        } catch {
            addToast('Error al guardar hito', 'error');
        } finally {
            setBusyMilestoneId(null);
        }
    };

    const milestoneDelete = async (milestone: ProjectMilestoneRecord) => {
        if (!window.confirm(`¿Eliminar el hito "${milestone.title}"?`)) return;
        setBusyMilestoneId(milestone.id);
        try {
            await apiFetch(`/projects/${project.id}/milestones/${milestone.id}`, {
                method: 'DELETE', token,
            });
            await reloadProject();
            addToast('Hito eliminado', 'success');
        } catch {
            addToast('Error al eliminar hito', 'error');
        } finally {
            setBusyMilestoneId(null);
        }
    };

    const milestoneCreate = async () => {
        if (!newMilestone.title.trim()) return;
        setAddingMilestone(true);
        try {
            await apiFetch(`/projects/${project.id}/milestones`, {
                method: 'POST', token,
                body: {
                    title: newMilestone.title.trim(),
                    target_date: newMilestone.date ? new Date(newMilestone.date).toISOString() : null,
                },
            });
            await reloadProject();
            setNewMilestone({ title: '', date: null });
            addToast('Hito creado', 'success');
        } catch {
            addToast('Error al crear hito', 'error');
        } finally {
            setAddingMilestone(false);
        }
    };

    // ── TAREAS EN NODOS ───────────────────────────────────────────────────
    const taskToggleStatus = async (task: ProjectTaskRecord) => {
        const newStatus = task.status === 'completed' ? 'todo' : 'completed';
        try {
            await updateTask(task.id, { status: newStatus });
            await reloadProject();
        } catch {
            addToast('Error al actualizar tarea', 'error');
        }
    };

    const taskSaveTitle = async (task: ProjectTaskRecord, cleanTitle: string) => {
        const newTitle = cleanTitle.trim();
        if (!newTitle || newTitle === task.title) return;
        try {
            await updateTask(task.id, { title: newTitle });
            await reloadProject();
        } catch {
            addToast('Error al renombrar tarea', 'error');
        }
    };

    return (
        <div className="space-y-4 pb-4 overflow-y-auto h-full pr-2 scrollbar-thin">
            {/* 1. Header de Misión con Pulso de Salud */}
            <header className="relative p-4 rounded-lg bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] overflow-hidden shadow-md border border-[hsl(var(--border))]">
                <div className="absolute inset-0 bg-gradient-to-br to-[hsl(var(--info)/20%)] to-[hsl(var(--info)/20%)]" />
                <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Radio size={220} />
                </div>

                <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="max-w-2xl space-y-3">
                        <div className="flex items-center gap-2">
                            <span className="px-2 py-1 bg-[hsl(var(--primary))] rounded-full text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary-foreground))] shadow-lg shadow-[hsl(var(--info)/40%)]">Misión Proactiva</span>
                            <div className="size-2 rounded-full bg-[hsl(var(--success))] animate-ping" />
                            <span className="text-2xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wide">Sincronizado en tiempo real</span>
                        </div>
                        <h1 className="text-xl font-bold tracking-tight leading-none text-[hsl(var(--foreground))]">
                            <InlineTextInput
                                value={project.title || ''}
                                onChange={(v) => updateProject({ title: v })}
                                placeholder="Título del proyecto"
                                className="text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]"
                                inputClassName="text-[hsl(var(--foreground))] border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] placeholder:text-[hsl(var(--muted-foreground))]"
                            />
                        </h1>
                        <div className="text-[hsl(var(--muted-foreground))] text-base font-medium leading-relaxed max-w-xl">
                            <InlineTextArea
                                value={project.description || ''}
                                onChange={(v) => updateProject({ description: v })}
                                placeholder="Iniciativa estratégica para la expansión del reino en el ecosistema digital."
                                rows={3}
                                className="text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]"
                                inputClassName="text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] placeholder:text-[hsl(var(--muted-foreground))]"
                            />
                        </div>
                        <div className="flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                            <InlineProjectStatusPicker
                                value={project.status || 'planning'}
                                onChange={(v) => updateProject({ status: v })}
                                size="sm"
                            />
                            <span className="font-semibold">Responsable:</span>
                            <InlineUserPicker
                                value={project.owner_id ?? null}
                                onChange={(id) => updateProject({ owner_id: id })}
                            />
                        </div>
                    </div>

                    {/* Widget Bento de Salud y Avance Inteligente */}
                    <div className="bg-[hsl(var(--surface-2))] rounded-xl p-3 border border-[hsl(var(--border))] flex items-center justify-between gap-3 shadow-md shrink-0">
                        <div className="flex items-center gap-3">
                            <div className="relative size-12">
                                <svg className="size-full -rotate-90" viewBox="0 0 36 36">
                                    <circle cx="18" cy="18" r="16" fill="none" className="stroke-[hsl(var(--border))]" strokeWidth="3"></circle>
                                    <motion.circle
                                        cx="18" cy="18" r="16" fill="none" className="stroke-[hsl(var(--primary))]" strokeWidth="3"
                                        initial={{ strokeDasharray: "0, 100" }}
                                        animate={{ strokeDasharray: `${dbProgress}, 100` }}
                                        transition={{ duration: 1.5, ease: "easeOut" }}
                                        strokeLinecap="round"
                                    ></motion.circle>
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <Zap className={clsx("size-5", dbProgress > 50 ? "text-[hsl(var(--warning))]" : "text-[hsl(var(--primary))]")} fill="currentColor" />
                                </div>
                            </div>
                            <div>
                                <div className="flex items-center gap-1.5 mb-0.5">
                                    <span className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                                        Avance Inteligente
                                    </span>
                                    <span className="px-1.5 py-0.2 rounded text-3xs font-black uppercase tracking-wider bg-[hsl(var(--surface-3))] text-[hsl(var(--primary))]">
                                        {project.progress_mode === 'manual' ? 'Manual' : project.progress_mode === 'milestones' ? 'Hitos' : 'Tareas'}
                                    </span>
                                </div>
                                <div className="text-xl font-black tracking-tight">{dbProgress}%</div>
                                <div className="flex items-center gap-2 mt-1">
                                    <div className={clsx(
                                        "px-2 py-0.5 rounded text-3xs font-bold uppercase tracking-wider border flex items-center gap-1",
                                        project.health_status === 'on_track' && "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]",
                                        project.health_status === 'at_risk' && "bg-[hsl(var(--warning))]/10 border-[hsl(var(--warning))]/30 text-[hsl(var(--warning))]",
                                        project.health_status === 'off_track' && "bg-[hsl(var(--destructive))]/10 border-[hsl(var(--destructive))]/30 text-[hsl(var(--destructive))]",
                                        project.health_status === 'completed' && "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]",
                                        !project.health_status && (
                                            analytics?.health_label === 'óptima' || analytics?.health_label === 'buena'
                                                ? "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]"
                                                : analytics?.health_label === 'en riesgo'
                                                ? "bg-[hsl(var(--warning))]/10 border-[hsl(var(--warning))]/30 text-[hsl(var(--warning))]"
                                                : analytics?.health_label === 'crítica'
                                                ? "bg-[hsl(var(--destructive))]/10 border-[hsl(var(--destructive))]/30 text-[hsl(var(--destructive))]"
                                                : "bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]"
                                        )
                                    )}>
                                        <Activity size={10} />
                                        Salud: {project.health_status ? (
                                            project.health_status === 'on_track' ? 'En Camino' :
                                            project.health_status === 'at_risk' ? 'En Riesgo' :
                                            project.health_status === 'off_track' ? 'Retrasado' : 'Completado'
                                        ) : (analytics ? analytics.health_label : '…')}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <button
                            onClick={() => setShowProgressDrawer(true)}
                            className="p-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-all active:scale-95 flex flex-col items-center gap-0.5 shrink-0"
                            title="Configurar motor de avance y salud"
                        >
                            <Sliders size={14} />
                            <span className="text-3xs font-bold uppercase">Motor</span>
                        </button>
                    </div>
                </div>
            </header>

            {/* 2. Analítica de Impacto */}
            <section className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <AnalyticCard title="Velocidad" value={analytics ? String(analytics.velocity) : '—'} detail="Tareas/Día" icon={TrendingUp} color="text-[hsl(var(--primary))]" />
                <AnalyticCard
                    title="Retraso"
                    value={analytics ? String(analytics.overdue_days) : '—'}
                    detail={analytics && analytics.overdue_days > 0 ? "Días de lag" : "Sin retraso"}
                    icon={Clock}
                    color={analytics && analytics.overdue_days > 0 ? "text-[hsl(var(--destructive))]" : "text-[hsl(var(--success))]"}
                />
                <AnalyticCard title="Hitos" value={`${milestones.filter(m => m.is_completed).length}/${milestones.length}`} detail="Metas logradas" icon={Trophy} color="text-[hsl(var(--warning))]" />
                <AnalyticCard
                    title="Riesgo"
                    value={analytics ? capitalize(analytics.risk_level) : '—'}
                    detail={analytics ? analytics.risk_reason : 'Calculando…'}
                    icon={AlertCircle}
                    color={analytics?.risk_level === 'alto' ? "text-[hsl(var(--destructive))]" : analytics?.risk_level === 'medio' ? "text-[hsl(var(--warning))]" : "text-[hsl(var(--muted-foreground))]"}
                />
            </section>

            {/* 3. Indicadores Clave y KPIs (PRO) */}
            <section className="space-y-3">
                <div className="flex items-center justify-between px-2">
                    <div className="flex items-center gap-2">
                        <Target className="text-[hsl(var(--primary))]" size={16} />
                        <h2 className="text-base font-bold text-[hsl(var(--foreground))] uppercase tracking-tight">
                            Indicadores Clave y KPIs
                        </h2>
                        <span className="text-3xs font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]">
                            {kpis.length} {kpis.length === 1 ? 'meta' : 'metas'}
                        </span>
                    </div>
                    <button
                        onClick={() => setShowKpiDrawer(true)}
                        className="px-2.5 py-1 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-2xs font-bold uppercase tracking-wide hover:opacity-90 active:scale-95 transition-all flex items-center gap-1.5 shadow-xs"
                    >
                        <Plus size={12} /> Gestionar KPIs
                    </button>
                </div>

                {kpis.length === 0 ? (
                    <div
                        onClick={() => setShowKpiDrawer(true)}
                        className="p-4 rounded-xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]/50 hover:bg-[hsl(var(--surface-2))] transition-colors cursor-pointer flex flex-col items-center justify-center text-center group"
                    >
                        <Target size={24} className="text-[hsl(var(--muted-foreground))]/40 group-hover:text-[hsl(var(--primary))] transition-colors mb-1.5" />
                        <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                            Sin indicadores configurados
                        </p>
                        <p className="text-3xs text-[hsl(var(--muted-foreground))] mt-0.5">
                            Haz clic para establecer metas de impacto, cobertura y finanzas con semáforo y progreso.
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                        {kpis.map((kpi) => {
                            const pct = kpi.target_value > 0
                                ? Math.min(100, Math.round((kpi.current_value / kpi.target_value) * 100))
                                : 0;
                            const isCompleted = pct >= 100;
                            const isGood = pct >= 70;
                            const isAtRisk = pct >= 40 && pct < 70;

                            const statusColor = isCompleted
                                ? "text-[hsl(var(--success))]"
                                : isGood
                                ? "text-[hsl(var(--primary))]"
                                : isAtRisk
                                ? "text-[hsl(var(--warning))]"
                                : "text-[hsl(var(--destructive))]";

                            const statusBg = isCompleted
                                ? "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]"
                                : isGood
                                ? "bg-[hsl(var(--primary))]/10 border-[hsl(var(--primary))]/30 text-[hsl(var(--primary))]"
                                : isAtRisk
                                ? "bg-[hsl(var(--warning))]/10 border-[hsl(var(--warning))]/30 text-[hsl(var(--warning))]"
                                : "bg-[hsl(var(--destructive))]/10 border-[hsl(var(--destructive))]/30 text-[hsl(var(--destructive))]";

                            const barBg = isCompleted
                                ? "bg-[hsl(var(--success))]"
                                : isGood
                                ? "bg-[hsl(var(--primary))]"
                                : isAtRisk
                                ? "bg-[hsl(var(--warning))]"
                                : "bg-[hsl(var(--destructive))]";

                            const statusLabel = isCompleted
                                ? "Completado"
                                : isGood
                                ? "En Camino"
                                : isAtRisk
                                ? "En Riesgo"
                                : "Crítico";

                            const StatusIcon = isCompleted
                                ? CheckCircle2
                                : isGood
                                ? TrendingUp
                                : isAtRisk
                                ? AlertTriangle
                                : AlertOctagon;

                            return (
                                <div
                                    key={kpi.id}
                                    onClick={() => setShowKpiDrawer(true)}
                                    className="p-3.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary))]/50 transition-all cursor-pointer shadow-xs space-y-2 group"
                                >
                                    <div className="flex items-start justify-between gap-1.5">
                                        <span className="text-3xs font-black uppercase tracking-wider px-1.5 py-0.5 rounded bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]">
                                            {kpi.category}
                                        </span>
                                        <span className={clsx("px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider border flex items-center gap-1", statusBg)}>
                                            <StatusIcon size={10} />
                                            {statusLabel}
                                        </span>
                                    </div>

                                    <div>
                                        <h4 className="text-xs font-bold text-[hsl(var(--foreground))] group-hover:text-[hsl(var(--primary))] transition-colors truncate">
                                            {kpi.title}
                                        </h4>
                                        {kpi.description && (
                                            <p className="text-3xs text-[hsl(var(--muted-foreground))] truncate mt-0.5">
                                                {kpi.description}
                                            </p>
                                        )}
                                    </div>

                                    <div className="space-y-1 pt-1">
                                        <div className="flex items-baseline justify-between text-2xs">
                                            <span className="font-bold text-[hsl(var(--foreground))]">
                                                {kpi.current_value.toLocaleString()} / {kpi.target_value.toLocaleString()}{' '}
                                                <span className="text-3xs text-[hsl(var(--muted-foreground))] font-normal">
                                                    {kpi.unit}
                                                </span>
                                            </span>
                                            <span className={clsx("font-black tracking-tight", statusColor)}>
                                                {pct}%
                                            </span>
                                        </div>

                                        <div className="h-1.5 w-full rounded-full bg-[hsl(var(--surface-2))] overflow-hidden">
                                            <div
                                                className={clsx("h-full rounded-full transition-all duration-500", barBg)}
                                                style={{ width: `${pct}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </section>

            {/* 3b. Control Presupuestario y Desglose Financiero (Super-PRO) */}
            <section className="space-y-3">
                <div className="flex items-center justify-between px-2">
                    <h2 className="text-lg font-bold text-[hsl(var(--foreground))] uppercase tracking-tighter flex items-center gap-2">
                        <Wallet className="text-[hsl(var(--primary))]" size={16} /> Control Presupuestario
                    </h2>
                    <button
                        onClick={() => setShowBudgetDrawer(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold uppercase tracking-wider bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/30 hover:bg-[hsl(var(--primary))]/20 transition-all cursor-pointer"
                    >
                        <Plus size={12} /> Gestionar Presupuesto
                    </button>
                </div>

                <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl p-4 shadow-xs space-y-4">
                    {/* Grid de Métricas Financieras */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Asignado</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--foreground))] mt-0.5">
                                ${(budgetSummary?.budget_allocated ?? project.budget_allocated ?? 0).toLocaleString("es-CO")}
                            </div>
                            <span className="text-3xs text-[hsl(var(--muted-foreground))]">Límite Aprobado</span>
                        </div>

                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Desembolsado</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--success))] mt-0.5">
                                ${(budgetSummary?.paid_amount ?? project.budget_spent ?? 0).toLocaleString("es-CO")}
                            </div>
                            <span className="text-3xs text-[hsl(var(--muted-foreground))]">Pagos Efectivos</span>
                        </div>

                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Comprometido</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--warning))] mt-0.5">
                                ${(budgetSummary?.committed_amount ?? 0).toLocaleString("es-CO")}
                            </div>
                            <span className="text-3xs text-[hsl(var(--muted-foreground))]">Órdenes / Contratos</span>
                        </div>

                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Fondos Restantes</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--primary))] mt-0.5">
                                ${(budgetSummary?.remaining_budget ?? (project.budget_allocated ? project.budget_allocated - (project.budget_spent || 0) : 0)).toLocaleString("es-CO")}
                            </div>
                            <span className="text-3xs text-[hsl(var(--muted-foreground))]">Saldo Disponible</span>
                        </div>
                    </div>

                    {/* Barra de Quema Presupuestaria */}
                    <div className="space-y-1.5 pt-1">
                        <div className="flex items-center justify-between text-2xs">
                            <span className="font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wider flex items-center gap-1.5">
                                <TrendingDown size={13} className="text-[hsl(var(--primary))]" />
                                Tasa de Quema Presupuestaria (Burn Rate)
                            </span>
                            <span className={clsx(
                                "font-black tracking-tight text-xs",
                                (budgetSummary?.burn_rate_percent ?? 0) > 90 ? "text-[hsl(var(--destructive))]" :
                                (budgetSummary?.burn_rate_percent ?? 0) > 70 ? "text-[hsl(var(--warning))]" :
                                "text-[hsl(var(--success))]"
                            )}>
                                {(budgetSummary?.burn_rate_percent ?? 0).toFixed(1)}%
                            </span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-[hsl(var(--surface-2))] overflow-hidden">
                            <div
                                className={clsx(
                                    "h-full rounded-full transition-all duration-500",
                                    (budgetSummary?.burn_rate_percent ?? 0) > 90 ? "bg-[hsl(var(--destructive))]" :
                                    (budgetSummary?.burn_rate_percent ?? 0) > 70 ? "bg-[hsl(var(--warning))]" :
                                    "bg-[hsl(var(--success))]"
                                )}
                                style={{ width: `${Math.min(100, Math.max(0, budgetSummary?.burn_rate_percent ?? 0))}%` }}
                            />
                        </div>
                    </div>

                    {/* Desglose Semántico por Categorías */}
                    {budgetSummary && Object.keys(budgetSummary.by_category || {}).length > 0 && (
                        <div className="pt-2 border-t border-[hsl(var(--border))] flex items-center gap-2 flex-wrap text-2xs">
                            <span className="font-semibold text-[hsl(var(--muted-foreground))]">Partidas por Categoría:</span>
                            {Object.entries(budgetSummary.by_category).map(([cat, amt]) => (
                                <span
                                    key={cat}
                                    className="px-2 py-0.5 rounded-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] font-medium text-[hsl(var(--foreground))]"
                                >
                                    {cat}: <strong className="font-bold">${amt.toLocaleString("es-CO")}</strong>
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </section>

            {/* 3.1 Matriz RAID de Riesgos y Supuestos (Super-PRO Fase 2) */}
            <section className="space-y-3">
                <div className="flex items-center justify-between px-2">
                    <h2 className="text-lg font-bold text-[hsl(var(--foreground))] uppercase tracking-tighter flex items-center gap-2">
                        <ShieldAlert className="text-[hsl(var(--destructive))]" size={16} /> Matriz RAID de Riesgos y Supuestos
                    </h2>
                    <button
                        onClick={() => setShowRiskDrawer(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold uppercase tracking-wider bg-[hsl(var(--destructive))]/10 text-[hsl(var(--destructive))] border border-[hsl(var(--destructive))]/30 hover:bg-[hsl(var(--destructive))]/20 transition-all cursor-pointer"
                    >
                        <Plus size={12} /> Gestionar Riesgos (RAID)
                    </button>
                </div>

                <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl p-4 shadow-xs space-y-4">
                    {/* Alerta semántica si hay riesgos críticos activos */}
                    {(risksSummary?.critical_count ?? 0) > 0 && (
                        <div className="p-3 rounded-lg bg-[hsl(var(--destructive))]/10 border border-[hsl(var(--destructive))]/30 flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2">
                                <AlertOctagon size={16} className="text-[hsl(var(--destructive))] shrink-0" />
                                <span className="text-xs font-bold text-[hsl(var(--destructive))]">
                                    Atención: {risksSummary?.critical_count} riesgo(s) de severidad crítica requieren plan de contingencia inmediata.
                                </span>
                            </div>
                            <button
                                onClick={() => setShowRiskDrawer(true)}
                                className="text-3xs font-black uppercase tracking-wider px-2 py-1 rounded bg-[hsl(var(--destructive))] text-[hsl(var(--surface-1))] hover:opacity-90 shrink-0 cursor-pointer"
                            >
                                Ver Matriz
                            </button>
                        </div>
                    )}

                    {/* Grid de Severidad RAID */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Riesgos Totales</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--foreground))] mt-0.5">
                                {risksSummary?.total_risks ?? 0}
                            </div>
                            <span className="text-3xs text-[hsl(var(--muted-foreground))]">{risksSummary?.active_risks ?? 0} activos / latentes</span>
                        </div>

                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--destructive))]">Críticos (15-25)</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--destructive))] mt-0.5">
                                {risksSummary?.critical_count ?? 0}
                            </div>
                            <span className="text-3xs text-[hsl(var(--destructive))]/80 font-medium">Severidad Extrema</span>
                        </div>

                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(28_90%_55%)]">Altos (10-14)</span>
                            <div className="text-base md:text-lg font-black text-[hsl(28_90%_55%)] mt-0.5">
                                {risksSummary?.high_count ?? 0}
                            </div>
                            <span className="text-3xs text-[hsl(28_90%_55%)]/80 font-medium">Mitigación Activa</span>
                        </div>

                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--success))]">Mitigados</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--success))] mt-0.5">
                                {risksSummary?.mitigated_risks ?? 0}
                            </div>
                            <span className="text-3xs text-[hsl(var(--success))]/80 font-medium">Bajo Control</span>
                        </div>
                    </div>

                    {/* Distribución de Riesgos por Categoría */}
                    {risksSummary && Object.keys(risksSummary.by_category || {}).length > 0 && (
                        <div className="pt-2 border-t border-[hsl(var(--border))] flex items-center gap-2 flex-wrap text-2xs">
                            <span className="font-semibold text-[hsl(var(--muted-foreground))]">Riesgos por Categoría:</span>
                            {Object.entries(risksSummary.by_category).map(([cat, count]) => (
                                <span
                                    key={cat}
                                    className="px-2 py-0.5 rounded-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] font-medium text-[hsl(var(--foreground))]"
                                >
                                    {cat}: <strong className="font-bold">{count}</strong>
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </section>

            {/* 3.2 Capacidad de Equipo y Carga de Trabajo (Super-PRO Fase 3) */}
            <section className="space-y-3">
                <div className="flex items-center justify-between px-2">
                    <h2 className="text-lg font-bold text-[hsl(var(--foreground))] uppercase tracking-tighter flex items-center gap-2">
                        <Users className="text-[hsl(var(--primary))]" size={16} /> Capacidad de Equipo y Carga de Trabajo
                    </h2>
                    <button
                        onClick={() => setShowWorkloadDrawer(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold uppercase tracking-wider bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] border border-[hsl(var(--primary))]/30 hover:bg-[hsl(var(--primary))]/20 transition-all cursor-pointer"
                    >
                        <Plus size={12} /> Planificar Carga
                    </button>
                </div>

                <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-xl p-4 shadow-xs space-y-4">
                    {/* Alerta semántica si hay miembros sobrecargados */}
                    {(workloadSummary?.overloaded_count ?? 0) > 0 && (
                        <div className="p-3 rounded-lg bg-[hsl(var(--destructive))]/10 border border-[hsl(var(--destructive))]/30 flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2">
                                <AlertOctagon size={16} className="text-[hsl(var(--destructive))] shrink-0" />
                                <span className="text-xs font-bold text-[hsl(var(--destructive))]">
                                    Atención: {workloadSummary?.overloaded_count} miembro(s) con sobrecarga de trabajo. Rebalancea las tareas para evitar cuellos de botella.
                                </span>
                            </div>
                            <button
                                onClick={() => setShowWorkloadDrawer(true)}
                                className="text-3xs font-black uppercase tracking-wider px-2 py-1 rounded bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] hover:opacity-90 shrink-0 cursor-pointer"
                            >
                                Rebalancear
                            </button>
                        </div>
                    )}

                    {/* Grid de Capacidad del Equipo */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">Equipo Asignado</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--foreground))] mt-0.5">
                                {workloadSummary?.total_members ?? 0}
                            </div>
                            <span className="text-3xs text-[hsl(var(--muted-foreground))]">Miembros con tareas</span>
                        </div>

                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--destructive))]">Sobrecargados</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--destructive))] mt-0.5">
                                {workloadSummary?.overloaded_count ?? 0}
                            </div>
                            <span className="text-3xs text-[hsl(var(--destructive))]/80 font-medium">≥ 5 tareas o vencidas</span>
                        </div>

                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--primary))]">Balanceados</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--primary))] mt-0.5">
                                {workloadSummary?.balanced_count ?? 0}
                            </div>
                            <span className="text-3xs text-[hsl(var(--primary))]/80 font-medium">2-4 tareas activas</span>
                        </div>

                        <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            <span className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--success))]">Disponibles</span>
                            <div className="text-base md:text-lg font-black text-[hsl(var(--success))] mt-0.5">
                                {workloadSummary?.available_count ?? 0}
                            </div>
                            <span className="text-3xs text-[hsl(var(--success))]/80 font-medium">Capacidad libre</span>
                        </div>
                    </div>

                    {/* Preview de miembros con barras de saturación */}
                    {workloadSummary && workloadSummary.members.length > 0 && (
                        <div className="pt-2 border-t border-[hsl(var(--border))] space-y-2.5">
                            <div className="flex items-center justify-between text-2xs">
                                <span className="font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
                                    Distribución de Carga por Responsable
                                </span>
                                <button
                                    onClick={() => setShowWorkloadDrawer(true)}
                                    className="text-3xs font-bold text-[hsl(var(--primary))] hover:underline cursor-pointer"
                                >
                                    Ver todos ({workloadSummary.members.length}) →
                                </button>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                                {workloadSummary.members.slice(0, 4).map((m) => {
                                    const statusColor = m.capacity_status === 'overloaded'
                                        ? 'text-[hsl(var(--destructive))]'
                                        : m.capacity_status === 'balanced'
                                            ? 'text-[hsl(var(--primary))]'
                                            : 'text-[hsl(var(--success))]';
                                    const barColor = m.capacity_status === 'overloaded'
                                        ? 'bg-[hsl(var(--destructive))]'
                                        : m.capacity_status === 'balanced'
                                            ? 'bg-[hsl(var(--primary))]'
                                            : 'bg-[hsl(var(--success))]';
                                    return (
                                        <div key={m.member_id} className="p-2.5 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] space-y-1.5">
                                            <div className="flex items-center justify-between text-2xs">
                                                <div className="flex items-center gap-1.5 min-w-0">
                                                    <span className="font-bold text-[hsl(var(--foreground))] truncate max-w-[140px]">
                                                        {m.member_name}
                                                    </span>
                                                    {m.overdue_tasks > 0 && (
                                                        <span className="px-1 py-0.2 rounded text-3xs font-black bg-[hsl(var(--destructive))]/20 text-[hsl(var(--destructive))]">
                                                            {m.overdue_tasks} vencida(s)
                                                        </span>
                                                    )}
                                                </div>
                                                <span className={clsx("font-black tracking-tight", statusColor)}>
                                                    {m.active_tasks} activas ({m.capacity_percent}%)
                                                </span>
                                            </div>
                                            <div className="h-1.5 w-full rounded-full bg-[hsl(var(--surface-1))] overflow-hidden">
                                                <div
                                                    className={clsx("h-full rounded-full transition-all duration-500", barColor)}
                                                    style={{ width: `${Math.min(100, Math.max(0, m.capacity_percent))}%` }}
                                                />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            </section>

            {/* 4. Línea de Tiempo de Hitos — auto-gestionada */}
            <section className="space-y-3">
                <div className="flex items-center justify-between px-2">
                    <h2 className="text-lg font-bold text-[hsl(var(--foreground))] uppercase tracking-tighter flex items-center gap-2">
                        <BarChart3 className="text-[hsl(var(--primary))]" size={16} /> Hitos Estratégicos
                    </h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {milestones.map((m) => {
                        const isBusy = busyMilestoneId === m.id;
                        return (
                            <div key={m.id} className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg p-3 hover:shadow-md transition-all relative">
                                <div className="flex items-start justify-between gap-2 mb-3">
                                    <button
                                        onClick={() => milestonePatch(m.id, { is_completed: !m.is_completed })}
                                        disabled={isBusy}
                                        aria-label={m.is_completed ? 'Reabrir hito' : 'Completar hito'}
                                        className={clsx(
                                            "size-8 rounded-md flex items-center justify-center shadow-lg transition-colors shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--success))] focus-visible:ring-offset-2",
                                            m.is_completed ? "bg-[hsl(var(--success))] text-[hsl(var(--primary-foreground))]"
                                                : "bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--success))]/10 hover:text-[hsl(var(--success))]",
                                            isBusy && "opacity-60 cursor-wait"
                                        )}
                                        title={m.is_completed ? 'Reabrir hito' : 'Completar hito'}
                                    >
                                        {m.is_completed ? <CheckCircle2 size={16} /> : <Calendar size={16} />}
                                    </button>
                                    <div className="flex-1 min-w-0">
                                        <InlineDatePicker
                                            value={m.target_date ? m.target_date.slice(0, 10) : null}
                                            onChange={(d) => milestonePatch(m.id, {
                                                target_date: d ? new Date(d).toISOString() : null,
                                            })}
                                            disabled={isBusy}
                                        />
                                    </div>
                                    <button
                                        onClick={() => milestoneDelete(m)}
                                        disabled={isBusy}
                                        title="Eliminar hito"
                                        aria-label="Eliminar hito"
                                        className="p-1.5 rounded-lg text-[hsl(var(--destructive))]/60 hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] transition-colors shrink-0 disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--destructive))] focus-visible:ring-offset-2"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                                <InlineTextInput
                                    value={m.title}
                                    onChange={(v) => milestonePatch(m.id, { title: v })}
                                    placeholder="Título del hito"
                                    className="block"
                                    inputClassName="text-base font-bold text-[hsl(var(--foreground))] leading-tight"
                                />
                                {m.description && (
                                    <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium leading-relaxed mt-1">{m.description}</p>
                                )}
                            </div>
                        );
                    })}
                    {/* Card de creación inline */}
                    <div className="border border-dashed border-[hsl(var(--border))] rounded-lg p-3 flex flex-col gap-2 justify-center">
                        <input
                            value={newMilestone.title}
                            onChange={e => setNewMilestone((s) => ({ ...s, title: e.target.value }))}
                            onKeyDown={e => { if (e.key === 'Enter') milestoneCreate(); }}
                            placeholder="+ Nuevo hito..."
                            disabled={addingMilestone}
                            className="w-full bg-transparent border-none text-base font-bold outline-none placeholder:text-[hsl(var(--muted-foreground))] text-[hsl(var(--foreground))]"
                        />
                        <div className="flex items-center gap-1.5">
                            <div className="flex-1 min-w-0">
                                <InlineDatePicker
                                    value={newMilestone.date}
                                    onChange={(d) => setNewMilestone((s) => ({ ...s, date: d }))}
                                    disabled={addingMilestone}
                                />
                            </div>
                            <button
                                onClick={milestoneCreate}
                                disabled={addingMilestone || !newMilestone.title.trim()}
                                title="Crear hito"
                                aria-label="Crear hito"
                                className="p-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                            >
                                <Plus size={14} />
                            </button>
                        </div>
                    </div>
                </div>
            </section>

            {/* 4. Grid de Nodos Operativos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <NodeCard
                    title="Nodo de Nutrición"
                    icon={Share2}
                    color="bg-[hsl(var(--warning))]"
                    tasks={nutritionTasks}
                    onOpenTask={onOpenTask}
                    onToggle={taskToggleStatus}
                    onTitleSave={taskSaveTitle}
                />
                <NodeCard
                    title="Nodo Digital"
                    icon={Globe}
                    color="bg-[hsl(var(--primary))]"
                    tasks={webTasks}
                    onOpenTask={onOpenTask}
                    onToggle={taskToggleStatus}
                    onTitleSave={taskSaveTitle}
                />
            </div>

            {/* Drawers Pro (SidePanel) */}
            <ProjectKpiDrawer
                projectId={project.id}
                isOpen={showKpiDrawer}
                onClose={() => setShowKpiDrawer(false)}
                onKpisUpdated={handleKpisUpdated}
            />

            <ProgressSettingsDrawer
                projectId={project.id}
                isOpen={showProgressDrawer}
                onClose={() => setShowProgressDrawer(false)}
                currentMode={project.progress_mode}
                manualProgress={project.manual_progress}
                currentHealthOverride={project.health_override}
                onSaved={handleProgressSaved}
            />

            <ProjectBudgetDrawer
                projectId={project.id}
                isOpen={showBudgetDrawer}
                onClose={() => setShowBudgetDrawer(false)}
                budgetAllocated={project.budget_allocated}
                onBudgetUpdated={() => {
                    loadBudgetSummary();
                    reloadProject();
                }}
            />

            <ProjectRiskMatrixDrawer
                projectId={project.id}
                isOpen={showRiskDrawer}
                onClose={() => setShowRiskDrawer(false)}
                onRiskUpdated={() => {
                    loadRisksSummary();
                    reloadProject();
                }}
            />

            <ProjectWorkloadDrawer
                projectId={project.id}
                isOpen={showWorkloadDrawer}
                onClose={() => setShowWorkloadDrawer(false)}
                onWorkloadUpdated={() => {
                    loadWorkloadSummary();
                    reloadProject();
                }}
            />
        </div>
    );
}

interface AnalyticCardProps {
    title: string;
    value: string;
    detail: string;
    icon: ElementType;
    color: string;
}

function capitalize(value: string): string {
    return value.charAt(0).toUpperCase() + value.slice(1);
}

function AnalyticCard({ title, value, detail, icon: Icon, color }: AnalyticCardProps) {
    return (
        <div className="p-3 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg shadow-sm hover:shadow-md transition-all">
            <div className="flex items-center gap-2 mb-2">
                <div className={clsx("p-1.5 rounded-md bg-[hsl(var(--surface-2))]", color)}>
                    <Icon size={14} />
                </div>
                <span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{title}</span>
            </div>
            <div className="text-xl font-bold text-[hsl(var(--foreground))] leading-none">{value}</div>
            <p className="text-2xs font-medium text-[hsl(var(--muted-foreground))] mt-1 uppercase tracking-tight">{detail}</p>
        </div>
    );
}

interface NodeCardProps {
    title: string;
    icon: ElementType;
    color: string;
    tasks: ProjectTaskRecord[];
    onOpenTask?: (task: ProjectTaskRecord) => void;
    onToggle: (task: ProjectTaskRecord) => void;
    onTitleSave: (task: ProjectTaskRecord, cleanTitle: string) => void;
}

function NodeCard({ title, icon: Icon, color, tasks, onOpenTask, onToggle, onTitleSave }: NodeCardProps) {
    return (
        <div className="p-3 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] shadow-sm hover:shadow-md transition-all group">
            <div className="flex items-center gap-3 mb-3">
                <div className={clsx("size-10 rounded-md flex items-center justify-center text-[hsl(var(--primary-foreground))] shadow-md transition-transform group-hover:scale-110", color)}>
                    <Icon size={18} />
                </div>
                <div>
                    <h3 className="text-base font-bold text-[hsl(var(--foreground))] leading-tight">{title}</h3>
                    <p className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mt-0.5">Avance por Nodo</p>
                </div>
            </div>
            <div className="space-y-2">
                {tasks.slice(0, 4).map((t) => {
                    return (
                        <div
                            key={t.id}
                            className="flex items-center gap-3 p-2 rounded-md bg-[hsl(var(--surface-2))] border border-transparent hover:border-[hsl(var(--border))] transition-all"
                        >
                            <button
                                onClick={() => onToggle(t)}
                                title={t.status === 'completed' ? 'Reabrir tarea' : 'Completar tarea'}
                                aria-label={t.status === 'completed' ? 'Reabrir tarea' : 'Completar tarea'}
                                className={clsx(
                                    "size-3 rounded-full shadow-sm shrink-0 transition-all hover:scale-125 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--success))] focus-visible:ring-offset-2",
                                    t.status === 'completed' ? "bg-[hsl(var(--success))]" : "bg-[hsl(var(--primary))]",
                                )}
                            />
                            <InlineTextInput
                                value={t.title}
                                onChange={(v) => onTitleSave(t, v)}
                                placeholder="Título de la tarea..."
                                className="flex-1 min-w-0"
                                inputClassName="text-base font-bold text-[hsl(var(--foreground))]"
                            />
                            <button
                                onClick={() => onOpenTask?.(t)}
                                title="Abrir detalle"
                                aria-label="Abrir detalle"
                                className="text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] transition-colors shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--primary))] focus-visible:ring-offset-2"
                            >
                                <ArrowUpRight size={14} />
                            </button>
                        </div>
                    );
                })}
                {tasks.length === 0 && (
                    <p className="text-xs text-[hsl(var(--muted-foreground))] italic px-2 py-1">Sin tareas en este nodo</p>
                )}
            </div>
        </div>
    );
}

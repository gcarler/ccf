"use client";

import { useState, useEffect, ElementType } from 'react';
import { motion } from 'framer-motion';
import {
    Radio, Share2, Globe, CheckCircle2, Clock,
    Zap, Trophy, Calendar, TrendingUp, AlertCircle,
    ArrowUpRight, BarChart3, Plus, Trash2,
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectRecord, ProjectTaskRecord, ProjectMilestoneRecord, ProjectAnalytics } from '@/types/projects';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { InlineTextArea } from '@/components/ui/inline-editors/InlineTextArea';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import { InlineUserPicker } from '@/components/ui/inline-editors';
import { InlineDatePicker } from '@/components/ui/inline-editors/InlineDatePicker';
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

                    {/* Widget Bento de Salud Persistida */}
                    <div className="bg-[hsl(var(--surface-2))] rounded-lg p-3 border border-[hsl(var(--border))] flex items-center gap-4 shadow-md">
                        <div className="relative size-8">
                            <svg className="size-full -rotate-90" viewBox="0 0 36 36">
                                <circle cx="18" cy="18" r="16" fill="none" className="stroke-[hsl(var(--border))]" strokeWidth="3"></circle>
                                <motion.circle
                                    cx="18" cy="18" r="16" fill="none" className="stroke-[hsl(var(--info))]" strokeWidth="3"
                                    initial={{ strokeDasharray: "0, 100" }}
                                    animate={{ strokeDasharray: `${dbProgress}, 100` }}
                                    transition={{ duration: 1.5, ease: "easeOut" }}
                                    strokeLinecap="round"
                                ></motion.circle>
                            </svg>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Zap className={clsx("size-8", dbProgress > 50 ? "text-[hsl(var(--warning))]" : "text-[hsl(var(--primary))]")} fill="currentColor" />
                            </div>
                        </div>
                        <div>
                            <span className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))] block mb-0.5">Avance Real</span>
                            <div className="text-xl font-bold tracking-tighter">{dbProgress}%</div>
                            <div className="flex items-center gap-2 mt-2">
                                <div className={clsx(
                                    "px-2 py-0.5 rounded text-2xs font-semibold uppercase",
                                    analytics?.health_label === 'óptima' && "bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]",
                                    analytics?.health_label === 'buena' && "bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]",
                                    analytics?.health_label === 'en riesgo' && "bg-[hsl(var(--warning))]/10 text-[hsl(var(--warning))]",
                                    analytics?.health_label === 'crítica' && "bg-[hsl(var(--destructive))]/10 text-[hsl(var(--destructive))]",
                                    !analytics && "bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))]",
                                )}>
                                    Salud: {analytics ? analytics.health_label : '…'}
                                </div>
                            </div>
                        </div>
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

            {/* 3. Línea de Tiempo de Hitos — auto-gestionada */}
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

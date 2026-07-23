"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
    Radio, Share2, Globe, CheckCircle2, Clock,
    Zap, Trophy, Calendar, TrendingUp, AlertCircle,
    ArrowUpRight, BarChart3, Plus, Trash2,
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectRecord, ProjectTaskRecord, ProjectMilestoneRecord } from '@/types/projects';
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

    // Agrupación por prefijo semántico (transicional hasta que se persista)
    const nutritionTasks = tasks.filter(t => /\[(Gesti[oó]n|Nutrici[oó]n)\]/i.test(t.title));
    const webTasks = tasks.filter(t => /\[(Web|Digital)\]/i.test(t.title));

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
        const prefixMatch = task.title.match(/^(\[[^\]]+\]\s*)/);
        const prefix = prefixMatch ? prefixMatch[1] : '';
        const newTitle = (prefix + cleanTitle).trim();
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
            <header className="relative p-4 rounded-lg bg-[hsl(var(--bg-muted))] text-white overflow-hidden shadow-2xl border border-white/5">
                <div className="absolute inset-0 bg-gradient-to-br to-[hsl(var(--info)/20%)] to-[hsl(var(--info)/20%)]" />
                <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Radio size={220} />
                </div>

                <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="max-w-2xl space-y-3">
                        <div className="flex items-center gap-2">
                            <span className="px-2 py-1 bg-[hsl(var(--primary))] rounded-full text-[10px] font-bold uppercase tracking-wide text-white shadow-lg shadow-[hsl(var(--info)/40%)]">Misión Proactiva</span>
                            <div className="size-2 rounded-full bg-[hsl(var(--success))] animate-ping" />
                            <span className="text-[10px] font-medium text-[hsl(var(--text-secondary))] uppercase tracking-wide">Sincronizado en tiempo real</span>
                        </div>
                        <h1 className="text-xl font-bold tracking-tight leading-none text-white">
                            <InlineTextInput
                                value={project.title || ''}
                                onChange={(v) => updateProject({ title: v })}
                                placeholder="Título del proyecto"
                                className="text-white hover:bg-white/10"
                                inputClassName="text-white border-white/20 bg-white/10 placeholder:text-white/50"
                            />
                        </h1>
                        <div className="text-[hsl(var(--text-secondary))] text-base font-medium leading-relaxed max-w-xl">
                            <InlineTextArea
                                value={project.description || ''}
                                onChange={(v) => updateProject({ description: v })}
                                placeholder="Iniciativa estratégica para la expansión del reino en el ecosistema digital."
                                rows={3}
                                className="text-[hsl(var(--text-secondary))] hover:bg-white/5"
                                inputClassName="text-[hsl(var(--text-secondary))] border-white/20 bg-white/10 placeholder:text-white/30"
                            />
                        </div>
                        <div className="flex items-center gap-2 text-[12px] text-[hsl(var(--text-secondary))]">
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
                    <div className="bg-white/5 backdrop-blur-2xl rounded-lg p-3 border border-white/10 flex items-center gap-4 shadow-2xl">
                        <div className="relative size-8">
                            <svg className="size-full -rotate-90" viewBox="0 0 36 36">
                                <circle cx="18" cy="18" r="16" fill="none" className="stroke-white/5" strokeWidth="3"></circle>
                                <motion.circle
                                    cx="18" cy="18" r="16" fill="none" className="stroke-[hsl(var(--info))]" strokeWidth="3"
                                    initial={{ strokeDasharray: "0, 100" }}
                                    animate={{ strokeDasharray: `${dbProgress}, 100` }}
                                    transition={{ duration: 1.5, ease: "easeOut" }}
                                    strokeLinecap="round"
                                ></motion.circle>
                            </svg>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <Zap className={clsx("size-8", dbProgress > 50 ? "text-yellow-400" : "text-[hsl(var(--primary))]")} fill="currentColor" />
                            </div>
                        </div>
                        <div>
                            <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] block mb-0.5">Avance Real</span>
                            <div className="text-xl font-bold tracking-tighter">{dbProgress}%</div>
                            <div className="flex items-center gap-2 mt-2">
                                <div className="px-2 py-0.5 bg-[hsl(var(--success))]/10 text-[hsl(var(--success))] rounded text-[9px] font-semibold uppercase">Salud: Óptima</div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* 2. Analítica de Impacto */}
            <section className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <AnalyticCard title="Velocidad" value="4.2" detail="Tareas/Día" icon={TrendingUp} color="text-[hsl(var(--primary))]" />
                <AnalyticCard title="Retraso" value="0" detail="Días de lag" icon={Clock} color="text-[hsl(var(--success))]" />
                <AnalyticCard title="Hitos" value={`${milestones.filter(m => m.is_completed).length}/${milestones.length}`} detail="Metas logradas" icon={Trophy} color="text-yellow-500" />
                <AnalyticCard title="Riesgo" value="Bajo" detail="Sin bloqueos" icon={AlertCircle} color="text-[hsl(var(--text-secondary))]" />
            </section>

            {/* 3. Línea de Tiempo de Hitos — auto-gestionada */}
            <section className="space-y-3">
                <div className="flex items-center justify-between px-2">
                    <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tighter flex items-center gap-2">
                        <BarChart3 className="text-[hsl(var(--primary))]" size={16} /> Hitos Estratégicos
                    </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {milestones.map((m) => {
                        const isBusy = busyMilestoneId === m.id;
                        return (
                            <div key={m.id} className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 hover:shadow-2xl transition-all relative">
                                <div className="flex items-start justify-between gap-2 mb-3">
                                    <button
                                        onClick={() => milestonePatch(m.id, { is_completed: !m.is_completed })}
                                        disabled={isBusy}
                                        className={clsx(
                                            "size-8 rounded-md flex items-center justify-center shadow-lg transition-colors shrink-0",
                                            m.is_completed ? "bg-[hsl(var(--success))] text-white"
                                                : "bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--success))]/10 hover:text-[hsl(var(--success))]",
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
                                        className="p-1.5 rounded-lg text-[hsl(var(--danger))]/60 hover:text-[hsl(var(--danger))] hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 transition-colors shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                                <InlineTextInput
                                    value={m.title}
                                    onChange={(v) => milestonePatch(m.id, { title: v })}
                                    placeholder="Título del hito"
                                    className="block"
                                    inputClassName="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white leading-tight"
                                />
                                {m.description && (
                                    <p className="text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium leading-relaxed mt-1">{m.description}</p>
                                )}
                            </div>
                        );
                    })}
                    {/* Card de creación inline */}
                    <div className="border border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-3 flex flex-col gap-2 justify-center">
                        <input
                            value={newMilestone.title}
                            onChange={e => setNewMilestone((s) => ({ ...s, title: e.target.value }))}
                            onKeyDown={e => { if (e.key === 'Enter') milestoneCreate(); }}
                            placeholder="+ Nuevo hito..."
                            disabled={addingMilestone}
                            className="w-full bg-transparent border-none text-[13px] font-bold outline-none placeholder:text-[hsl(var(--text-secondary))] text-[hsl(var(--text-primary))] dark:text-white"
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
                                className="p-1.5 rounded-lg bg-[hsl(var(--primary))] text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity shrink-0"
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
                    color="bg-orange-500"
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

function AnalyticCard({ title, value, detail, icon: Icon, color }: any) {
    return (
        <div className="p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg shadow-sm hover:shadow-xl transition-all">
            <div className="flex items-center gap-2 mb-2">
                <div className={clsx("p-1.5 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5", color)}>
                    <Icon size={14} />
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{title}</span>
            </div>
            <div className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white leading-none">{value}</div>
            <p className="text-[10px] font-medium text-[hsl(var(--text-secondary))] mt-1 uppercase tracking-tight">{detail}</p>
        </div>
    );
}

interface NodeCardProps {
    title: string;
    icon: React.ElementType;
    color: string;
    tasks: ProjectTaskRecord[];
    onOpenTask?: (task: ProjectTaskRecord) => void;
    onToggle: (task: ProjectTaskRecord) => void;
    onTitleSave: (task: ProjectTaskRecord, cleanTitle: string) => void;
}

function NodeCard({ title, icon: Icon, color, tasks, onOpenTask, onToggle, onTitleSave }: NodeCardProps) {
    return (
        <div className="p-3 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 shadow-sm hover:shadow-2xl transition-all group">
            <div className="flex items-center gap-3 mb-3">
                <div className={clsx("size-10 rounded-md flex items-center justify-center text-white shadow-xl transition-transform group-hover:scale-110", color)}>
                    <Icon size={18} />
                </div>
                <div>
                    <h4 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white leading-tight">{title}</h4>
                    <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-0.5">Avance por Nodo</p>
                </div>
            </div>
            <div className="space-y-2">
                {tasks.slice(0, 4).map((t) => {
                    const match = t.title.match(/^(\[[^\]]+\]\s*)(.*)$/);
                    const cleanTitle = match ? match[2] : t.title;
                    return (
                        <div
                            key={t.id}
                            className="flex items-center gap-3 p-2 rounded-md bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-transparent hover:border-[hsl(var(--border))] transition-all"
                        >
                            <button
                                onClick={() => onToggle(t)}
                                title={t.status === 'completed' ? 'Reabrir tarea' : 'Completar tarea'}
                                aria-label={t.status === 'completed' ? 'Reabrir tarea' : 'Completar tarea'}
                                className={clsx(
                                    "size-3 rounded-full shadow-sm shrink-0 transition-all hover:scale-125",
                                    t.status === 'completed' ? "bg-[hsl(var(--success))]" : "bg-[hsl(var(--primary))]",
                                )}
                            />
                            <InlineTextInput
                                value={cleanTitle}
                                onChange={(v) => onTitleSave(t, v)}
                                placeholder="Título de la tarea..."
                                className="flex-1 min-w-0"
                                inputClassName="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
                            />
                            <button
                                onClick={() => onOpenTask?.(t)}
                                title="Abrir detalle"
                                className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors shrink-0"
                            >
                                <ArrowUpRight size={14} />
                            </button>
                        </div>
                    );
                })}
                {tasks.length === 0 && (
                    <p className="text-[11px] text-[hsl(var(--text-secondary))] italic px-2 py-1">Sin tareas en este nodo</p>
                )}
            </div>
        </div>
    );
}

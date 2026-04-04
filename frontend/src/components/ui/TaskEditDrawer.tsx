"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X, CheckCircle2, Circle, CalendarDays, FolderOpen,
    MoreHorizontal, Sparkles, Loader2, ChevronDown, AlignLeft,
    Clock, Zap, Trash2, Copy, ExternalLink,
    Save, MessageSquare, Link2, AlertTriangle, CheckCheck,
    Hash, ArrowRight
} from 'lucide-react';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';

// ─────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────
export interface TaskDetail {
    id: number;
    title: string;
    status: string;
    priority: string | null;
    due_date: string | null;
    project_id: number;
    project_title?: string;
    description?: string | null;
    done?: boolean;
}

interface TaskEditDrawerProps {
    task: TaskDetail | null;
    onClose: () => void;
    onTaskUpdated: (updatedTask: TaskDetail) => void;
    onTaskDeleted: (taskId: number) => void;
}

// ─────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────
const PRIORITY_OPTIONS = [
    {
        value: 'urgent', label: 'Urgente',
        color: 'text-rose-600', bg: 'bg-rose-50 dark:bg-rose-500/10',
        border: 'border-rose-200 dark:border-rose-500/30',
        dot: 'bg-rose-500', bar: 'bg-rose-500',
        glow: 'shadow-rose-500/20',
    },
    {
        value: 'high', label: 'Alta',
        color: 'text-orange-600', bg: 'bg-orange-50 dark:bg-orange-500/10',
        border: 'border-orange-200 dark:border-orange-500/30',
        dot: 'bg-orange-500', bar: 'bg-orange-500',
        glow: 'shadow-orange-500/20',
    },
    {
        value: 'medium', label: 'Media',
        color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-500/10',
        border: 'border-amber-200 dark:border-amber-500/30',
        dot: 'bg-amber-500', bar: 'bg-amber-500',
        glow: 'shadow-amber-500/20',
    },
    {
        value: 'low', label: 'Baja',
        color: 'text-slate-500', bg: 'bg-slate-50 dark:bg-slate-800/40',
        border: 'border-slate-200 dark:border-slate-700/50',
        dot: 'bg-slate-400', bar: 'bg-slate-400',
        glow: 'shadow-slate-500/10',
    },
];

const STATUS_OPTIONS = [
    { value: 'todo',        label: 'Por hacer',   color: 'text-slate-600 dark:text-slate-400',   bg: 'bg-slate-100 dark:bg-slate-800/60',      icon: Circle },
    { value: 'in_progress', label: 'En progreso', color: 'text-blue-600 dark:text-blue-400',     bg: 'bg-blue-50 dark:bg-blue-500/10',          icon: Clock },
    { value: 'done',        label: 'Completada',  color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-500/10',  icon: CheckCircle2 },
    { value: 'blocked',     label: 'Bloqueada',   color: 'text-rose-600 dark:text-rose-400',     bg: 'bg-rose-50 dark:bg-rose-500/10',          icon: AlertTriangle },
];

const XP_MAP: Record<string, number> = { urgent: 100, high: 60, medium: 40, low: 20 };

// ─────────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────────
export default function TaskEditDrawer({
    task,
    onClose,
    onTaskUpdated,
    onTaskDeleted,
}: TaskEditDrawerProps) {
    const { token } = useAuth();
    const [form, setForm]                   = useState<TaskDetail | null>(null);
    const [dirty, setDirty]                 = useState(false);
    const [saving, setSaving]               = useState(false);
    const [saved, setSaved]                 = useState(false);
    const [aiLoading, setAiLoading]         = useState(false);
    const [aiSuggestion, setAiSuggestion]   = useState<string | null>(null);
    const [showPriorityPicker, setShowPriorityPicker] = useState(false);
    const [showStatusPicker, setShowStatusPicker]     = useState(false);
    const [showDeleteConfirm, setShowDeleteConfirm]   = useState(false);
    const titleRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (task) {
            setForm({ ...task });
            setDirty(false);
            setSaved(false);
            setAiSuggestion(null);
            setShowDeleteConfirm(false);
            setShowPriorityPicker(false);
            setShowStatusPicker(false);
        }
    }, [task]);

    useEffect(() => {
        if (titleRef.current) {
            titleRef.current.style.height = 'auto';
            titleRef.current.style.height = `${titleRef.current.scrollHeight}px`;
        }
    }, [form?.title]);

    const updateField = <K extends keyof TaskDetail>(key: K, value: TaskDetail[K]) => {
        setForm(prev => prev ? { ...prev, [key]: value } : prev);
        setDirty(true);
        setSaved(false);
    };

    const handleSave = async () => {
        if (!form || !dirty) return;
        setSaving(true);
        try {
            const updated = await apiFetch<TaskDetail>(
                `/projects/${form.project_id}/tasks/${form.id}`,
                {
                    method: 'PATCH', token,
                    body: {
                        title: form.title,
                        status: form.status,
                        priority: form.priority,
                        due_date: form.due_date,
                        description: form.description,
                    },
                }
            );
            onTaskUpdated({ ...form, ...updated });
            setDirty(false);
            setSaved(true);
            setTimeout(() => setSaved(false), 2500);
        } catch {
            onTaskUpdated(form);
            setDirty(false);
            setSaved(true);
            setTimeout(() => setSaved(false), 2500);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!form) return;
        try {
            await apiFetch(`/projects/${form.project_id}/tasks/${form.id}`, { method: 'DELETE', token });
        } catch { /* silent */ }
        onTaskDeleted(form.id);
        onClose();
    };

    const handleAiSuggest = async () => {
        if (!form) return;
        setAiLoading(true);
        try {
            const ctx = `Tarea: "${form.title}". Prioridad: ${form.priority || 'no definida'}. Estado: ${form.status}. Proyecto: ${form.project_title || 'sin proyecto'}.`;
            const data = await apiFetch<{ response: string }>('/system/ai/generate', {
                method: 'POST', token,
                body: {
                    prompt: 'Actúa como un asistente de productividad pastoral. Sugiere cómo abordar esta tarea: un paso de acción específico y un consejo ministerial (máximo 2 oraciones breves). Responde en español.',
                    context: ctx,
                },
            });
            setAiSuggestion(data.response);
        } catch {
            setAiSuggestion('No se pudo conectar con MESH AI en este momento.');
        } finally {
            setAiLoading(false);
        }
    };

    const cp = PRIORITY_OPTIONS.find(p => p.value === form?.priority) ?? PRIORITY_OPTIONS[3];
    const cs = STATUS_OPTIONS.find(s => s.value === form?.status) ?? STATUS_OPTIONS[0];
    const xp = XP_MAP[form?.priority || 'low'];

    return (
        <AnimatePresence>
            {task && form && (
                <>
                    {/* ── BACKDROP ── */}
                    <motion.div
                        key="tdr-backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 z-[100] bg-slate-950/30 backdrop-blur-[3px]"
                        onClick={onClose}
                        aria-hidden
                    />

                    {/* ── DRAWER ── */}
                    <motion.aside
                        key="tdr-panel"
                        initial={{ x: '100%', opacity: 0.5 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: '100%', opacity: 0 }}
                        transition={{ type: 'spring', damping: 30, stiffness: 280 }}
                        className="fixed right-0 top-0 bottom-0 w-full max-w-[460px] z-[101] flex flex-col bg-white dark:bg-[#18191c] shadow-[-32px_0_80px_rgba(0,0,0,0.14)] dark:shadow-[-32px_0_80px_rgba(0,0,0,0.5)]"
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Priority accent bar — top */}
                        <div className={clsx('h-[3px] w-full shrink-0', cp.bar)} />

                        {/* ── HEADER ── */}
                        <header className="shrink-0 px-5 pt-3.5 pb-3 border-b border-slate-100 dark:border-white/[0.06]">
                            <div className="flex items-center justify-between mb-3">

                                {/* Left: status + xp */}
                                <div className="flex items-center gap-2">
                                    {/* Status picker */}
                                    <div className="relative">
                                        <button
                                            id="status-trigger"
                                            onClick={() => { setShowStatusPicker(v => !v); setShowPriorityPicker(false); }}
                                            className={clsx(
                                                'flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all border',
                                                cs.color, cs.bg,
                                                'border-current/20 hover:border-current/40'
                                            )}
                                        >
                                            <cs.icon size={11} strokeWidth={2.5} />
                                            {cs.label}
                                            <ChevronDown size={10} className="opacity-60" />
                                        </button>
                                        <AnimatePresence>
                                            {showStatusPicker && (
                                                <motion.div
                                                    initial={{ opacity: 0, y: -6, scale: 0.96 }}
                                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                                    exit={{ opacity: 0, y: -6, scale: 0.96 }}
                                                    transition={{ duration: 0.13 }}
                                                    className="absolute left-0 top-full mt-2 w-48 bg-white dark:bg-[#222326] border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl z-[200] overflow-hidden py-1"
                                                >
                                                    {STATUS_OPTIONS.map(opt => (
                                                        <button key={opt.value}
                                                            onClick={() => { updateField('status', opt.value); setShowStatusPicker(false); }}
                                                            className={clsx(
                                                                'w-full flex items-center gap-2.5 px-3.5 py-2.5 text-[12px] font-semibold transition-colors',
                                                                form.status === opt.value
                                                                    ? `${opt.color} ${opt.bg}`
                                                                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5'
                                                            )}
                                                        >
                                                            <opt.icon size={13} strokeWidth={2} />
                                                            {opt.label}
                                                            {form.status === opt.value && <CheckCheck size={11} className="ml-auto opacity-70" />}
                                                        </button>
                                                    ))}
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>

                                    {/* XP badge */}
                                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 rounded-lg text-[10px] font-black tracking-wide border border-amber-200/50 dark:border-amber-500/20">
                                        <Zap size={9} fill="currentColor" /> +{xp} XP
                                    </span>
                                </div>

                                {/* Right: actions */}
                                <div className="flex items-center gap-0.5">
                                    <AnimatePresence mode="wait">
                                        {saving ? (
                                            <motion.div key="saving" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold text-blue-600 bg-blue-50 dark:bg-blue-500/10">
                                                <Loader2 size={11} className="animate-spin" /> Guardando...
                                            </motion.div>
                                        ) : saved ? (
                                            <motion.div key="saved" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10">
                                                <CheckCheck size={11} /> Guardado
                                            </motion.div>
                                        ) : dirty ? (
                                            <motion.button key="save" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                                                onClick={handleSave}
                                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-blue-600 text-white shadow-md shadow-blue-500/25 hover:bg-blue-700 active:scale-95 transition-all">
                                                <Save size={11} /> Guardar
                                            </motion.button>
                                        ) : null}
                                    </AnimatePresence>
                                    <button className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-all ml-0.5">
                                        <MoreHorizontal size={15} />
                                    </button>
                                    <button onClick={onClose} aria-label="Cerrar"
                                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-all">
                                        <X size={15} />
                                    </button>
                                </div>
                            </div>

                            {/* Task title */}
                            <textarea
                                ref={titleRef}
                                value={form.title}
                                onChange={e => updateField('title', e.target.value)}
                                rows={1}
                                placeholder="Nombre de la tarea..."
                                className="w-full text-[19px] font-bold text-slate-900 dark:text-white bg-transparent resize-none outline-none leading-snug placeholder:text-slate-300 dark:placeholder:text-slate-600 focus:ring-0 -mx-0.5"
                            />
                        </header>

                        {/* ── BODY ── */}
                        <div className="flex-1 overflow-y-auto scrollbar-thin">

                            {/* ─ META FIELDS ─ */}
                            <div className="px-5 py-4 space-y-3 border-b border-slate-100 dark:border-white/[0.05]">

                                {/* Priority row */}
                                <MetaRow label="Prioridad">
                                    <div className="relative">
                                        <button
                                            onClick={() => { setShowPriorityPicker(v => !v); setShowStatusPicker(false); }}
                                            className={clsx(
                                                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-[12px] font-bold border transition-all',
                                                cp.color, cp.bg, cp.border, 'hover:shadow-md', cp.glow
                                            )}
                                        >
                                            <span className={clsx('size-2 rounded-full shrink-0', cp.dot)} />
                                            {cp.label}
                                            <ChevronDown size={11} className="opacity-50 ml-0.5" />
                                        </button>
                                        <AnimatePresence>
                                            {showPriorityPicker && (
                                                <motion.div
                                                    initial={{ opacity: 0, y: -6, scale: 0.96 }}
                                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                                    exit={{ opacity: 0, y: -6, scale: 0.96 }}
                                                    transition={{ duration: 0.13 }}
                                                    className="absolute left-0 top-full mt-2 w-44 bg-white dark:bg-[#222326] border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl z-[200] overflow-hidden py-1"
                                                >
                                                    {PRIORITY_OPTIONS.map(opt => (
                                                        <button key={opt.value}
                                                            onClick={() => { updateField('priority', opt.value); setShowPriorityPicker(false); }}
                                                            className={clsx(
                                                                'w-full flex items-center gap-2.5 px-3.5 py-2.5 text-[12px] font-semibold transition-colors',
                                                                form.priority === opt.value
                                                                    ? `${opt.color} ${opt.bg}`
                                                                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5'
                                                            )}
                                                        >
                                                            <span className={clsx('size-2 rounded-full shrink-0', opt.dot)} />
                                                            {opt.label}
                                                            {form.priority === opt.value && <CheckCheck size={11} className="ml-auto opacity-60" />}
                                                        </button>
                                                    ))}
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                </MetaRow>

                                {/* Due date row */}
                                <MetaRow label="Fecha límite" icon={<CalendarDays size={13} className="text-slate-400" />}>
                                    <div className="relative">
                                        <input
                                            type="date"
                                            value={form.due_date ? form.due_date.split('T')[0] : ''}
                                            onChange={e => updateField('due_date', e.target.value || null)}
                                            className="h-8 px-3 rounded-lg bg-slate-50 dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.08] text-[12px] font-semibold text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all"
                                        />
                                    </div>
                                </MetaRow>

                                {/* Project row */}
                                <MetaRow label="Proyecto" icon={<FolderOpen size={13} className="text-slate-400" />}>
                                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.08] max-w-[220px]">
                                        <span className="text-[12px] font-semibold text-slate-600 dark:text-slate-300 truncate">
                                            {form.project_title || `Proyecto #${form.project_id}`}
                                        </span>
                                        <ExternalLink size={11} className="ml-auto text-slate-300 dark:text-slate-600 shrink-0" />
                                    </div>
                                </MetaRow>
                            </div>

                            {/* ─ DESCRIPTION ─ */}
                            <div className="px-5 py-4 border-b border-slate-100 dark:border-white/[0.05]">
                                <p className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2 flex items-center gap-1.5">
                                    <AlignLeft size={11} /> Descripción
                                </p>
                                <textarea
                                    value={form.description || ''}
                                    onChange={e => updateField('description', e.target.value || null)}
                                    rows={3}
                                    placeholder="Añade contexto o detalles sobre esta tarea..."
                                    className="w-full px-3 py-2.5 rounded-xl bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/[0.07] text-[13px] font-medium text-slate-700 dark:text-slate-300 placeholder:text-slate-300 dark:placeholder:text-slate-600 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400/50 resize-none transition-all leading-relaxed"
                                />
                            </div>

                            {/* ─ MESH AI ─ */}
                            <div className="px-5 py-4 border-b border-slate-100 dark:border-white/[0.05]">
                                <div className="rounded-2xl bg-gradient-to-br from-violet-50 via-indigo-50/50 to-blue-50/30 dark:from-violet-900/15 dark:via-indigo-900/10 dark:to-transparent border border-violet-200/60 dark:border-violet-500/20 overflow-hidden">
                                    {/* AI header */}
                                    <div className="flex items-center justify-between px-4 py-3 border-b border-violet-200/40 dark:border-violet-500/15">
                                        <div className="flex items-center gap-2">
                                            <div className="size-6 rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-sm">
                                                <Sparkles size={11} className="text-white" />
                                            </div>
                                            <span className="text-[11px] font-black text-violet-700 dark:text-violet-300 tracking-wide uppercase">MESH AI</span>
                                            <span className="px-1.5 py-0.5 bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400 text-[9px] font-black rounded-md uppercase tracking-wider">Beta</span>
                                        </div>
                                        <button
                                            onClick={handleAiSuggest}
                                            disabled={aiLoading}
                                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-white text-[10px] font-bold shadow-md shadow-violet-500/25 hover:opacity-90 active:scale-95 transition-all disabled:opacity-50"
                                        >
                                            {aiLoading ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
                                            {aiLoading ? 'Analizando...' : 'Sugerir'}
                                        </button>
                                    </div>

                                    {/* AI body */}
                                    <div className="px-4 py-3 min-h-[60px] flex items-center">
                                        <AnimatePresence mode="wait">
                                            {aiSuggestion ? (
                                                <motion.p key="ai-text"
                                                    initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                                                    className="text-[13px] text-slate-700 dark:text-slate-300 leading-relaxed font-medium italic"
                                                >
                                                    &ldquo;{aiSuggestion}&rdquo;
                                                </motion.p>
                                            ) : aiLoading ? (
                                                <motion.div key="ai-loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                                    className="flex items-center gap-2 text-violet-500">
                                                    <Loader2 size={14} className="animate-spin" />
                                                    <span className="text-[12px] font-medium">Analizando la tarea...</span>
                                                </motion.div>
                                            ) : (
                                                <motion.p key="ai-placeholder" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                                    className="text-[12px] text-violet-400/70 dark:text-violet-400/50 font-medium">
                                                    Haz clic en "Sugerir" para recibir orientación contextual de MESH sobre esta tarea.
                                                </motion.p>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                </div>
                            </div>

                            {/* ─ QUICK ACTIONS ─ */}
                            <div className="px-5 py-4">
                                <p className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-3">Acciones</p>
                                <div className="grid grid-cols-2 gap-2">
                                    <QuickBtn icon={MessageSquare} label="Comentar" />
                                    <QuickBtn icon={Link2} label="Adjuntar" />
                                    <QuickBtn icon={Copy} label="Duplicar" onClick={() => {}} />
                                    <QuickBtn icon={Trash2} label="Eliminar" danger onClick={() => setShowDeleteConfirm(true)} />
                                </div>

                                <AnimatePresence>
                                    {showDeleteConfirm && (
                                        <motion.div
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            className="overflow-hidden mt-3"
                                        >
                                            <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-500/30 space-y-3">
                                                <p className="text-[12px] font-bold text-rose-700 dark:text-rose-300">
                                                    ¿Eliminar &ldquo;{form.title.slice(0, 40)}{form.title.length > 40 ? '...' : ''}&rdquo;?
                                                </p>
                                                <p className="text-[11px] text-rose-500/80 dark:text-rose-400/60">Esta acción no se puede deshacer.</p>
                                                <div className="flex gap-2">
                                                    <button onClick={handleDelete}
                                                        className="flex-1 py-2.5 bg-rose-600 text-white rounded-xl text-[11px] font-bold hover:bg-rose-700 active:scale-95 transition-all shadow-md shadow-rose-500/20">
                                                        Sí, eliminar
                                                    </button>
                                                    <button onClick={() => setShowDeleteConfirm(false)}
                                                        className="flex-1 py-2.5 bg-white dark:bg-white/5 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-white/10 rounded-xl text-[11px] font-bold hover:bg-slate-50 dark:hover:bg-white/8 transition-all">
                                                        Cancelar
                                                    </button>
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                        </div>

                        {/* ── FOOTER ── */}
                        <footer className="shrink-0 px-5 py-3 border-t border-slate-100 dark:border-white/[0.06] bg-slate-50/70 dark:bg-white/[0.02] flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className={clsx('size-2 rounded-full shrink-0', cp.dot)} />
                                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                                    {cp.label}
                                </span>
                                <span className="text-slate-200 dark:text-white/10">·</span>
                                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                                    {cs.label}
                                </span>
                                {form.due_date && (
                                    <>
                                        <span className="text-slate-200 dark:text-white/10">·</span>
                                        <span className="flex items-center gap-1 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                                            <CalendarDays size={10} />
                                            {new Date(form.due_date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}
                                        </span>
                                    </>
                                )}
                                <span className="ml-1 flex items-center gap-0.5 text-[10px] text-slate-300 dark:text-slate-600 font-mono">
                                    <Hash size={9} />
                                    {form.id}
                                </span>
                            </div>

                            <button
                                onClick={handleSave}
                                disabled={!dirty || saving}
                                className={clsx(
                                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all',
                                    dirty
                                        ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/20 hover:bg-blue-700 active:scale-95'
                                        : saved
                                        ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                        : 'bg-transparent text-slate-300 dark:text-slate-600 cursor-default'
                                )}
                            >
                                {saving ? <Loader2 size={11} className="animate-spin" /> : saved ? <CheckCheck size={11} /> : <Save size={11} />}
                                {saving ? 'Guardando...' : saved ? 'Guardado' : dirty ? 'Guardar' : 'Sin cambios'}
                            </button>
                        </footer>

                    </motion.aside>
                </>
            )}
        </AnimatePresence>
    );
}

// ─────────────────────────────────────────────────────────────────
// SUB-COMPONENTS
// ─────────────────────────────────────────────────────────────────
function MetaRow({ label, icon, children }: { label: string; icon?: React.ReactNode; children: React.ReactNode }) {
    return (
        <div className="flex items-center gap-0">
            <div className="w-[110px] shrink-0 flex items-center gap-1.5">
                {icon}
                <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500">{label}</span>
            </div>
            {children}
        </div>
    );
}

function QuickBtn({ icon: Icon, label, onClick, danger = false }: { icon: any; label: string; onClick?: () => void; danger?: boolean }) {
    return (
        <button
            onClick={onClick}
            className={clsx(
                'flex items-center gap-2 px-3 py-2.5 rounded-xl text-[11px] font-semibold border transition-all group hover:-translate-y-[1px] hover:shadow-sm active:scale-95',
                danger
                    ? 'text-rose-500 dark:text-rose-400 bg-transparent border-rose-200 dark:border-rose-500/20 hover:bg-rose-50 dark:hover:bg-rose-500/10'
                    : 'text-slate-500 dark:text-slate-400 bg-white dark:bg-white/[0.03] border-slate-200 dark:border-white/[0.07] hover:bg-slate-50 dark:hover:bg-white/[0.06] hover:text-slate-700 dark:hover:text-slate-200'
            )}
        >
            <Icon size={13} className="transition-transform group-hover:scale-110" />
            {label}
        </button>
    );
}

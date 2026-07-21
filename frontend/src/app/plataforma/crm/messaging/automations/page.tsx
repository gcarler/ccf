"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
    Zap, Plus, Settings2, Trash2, ToggleLeft, ToggleRight,
    Loader2, Send, CheckCircle2, MessageSquare, CheckSquare,
    Users, Bell, Clock, AlertTriangle, Heart
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import Skeleton from '@/components/ui/Skeleton';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { AutomationRule } from '@/types/crm';

// ─── Constants ───────────────────────────────────────────
const TRIGGERS = [
    { value: 'new_persona', label: 'Nuevo Persona', icon: Users, color: 'blue' },
    { value: 'birthday', label: 'Cumpleaños', icon: Bell, color: 'amber' },
    { value: 'inactivity', label: 'Inactividad (30 días)', icon: Clock, color: 'rose' },
    { value: 'low_attendance', label: 'Baja Asistencia', icon: AlertTriangle, color: 'orange' },
    { value: 'anniversary', label: 'Aniversario Espiritual', icon: Heart, color: 'blue' },
    { value: 'stage_change', label: 'Cambio de Etapa Pipeline', icon: Zap, color: 'sky' },
];

const ACTIONS = [
    { value: 'send_whatsapp', label: 'Enviar WhatsApp', icon: MessageSquare },
    { value: 'send_sms', label: 'Enviar SMS', icon: MessageSquare },
    { value: 'create_task', label: 'Crear Tarea de Consolidación', icon: CheckSquare },
    { value: 'send_email', label: 'Enviar Email', icon: Send },
];

const TRIGGER_COLORS: Record<string, string> = {
    new_persona: 'bg-blue-500/10 text-[hsl(var(--primary))] border-blue-500/20',
    birthday: 'bg-amber-500/10 text-amber-600 border-amber-500/20',
    inactivity: 'bg-rose-500/10 text-rose-600 border-rose-500/20',
    low_attendance: 'bg-orange-500/10 text-orange-600 border-orange-500/20',
    anniversary: 'bg-sky-500/10 text-sky-600 border-sky-500/20',
    stage_change: 'bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] border-[hsl(var(--primary))]/20',
};

const EMPTY_FORM = { name: '', trigger: 'new_persona', action: 'send_whatsapp', message: '', taskTitle: '' };

export default function AutomationsPage() {
    const { token, loading: authLoading } = useAuth();
    const { addToast } = useToast();

    const [rules, setRules] = useState<AutomationRule[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [editingRule, setEditingRule] = useState<AutomationRule | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [form, setForm] = useState(EMPTY_FORM);
    const [reloadKey, setReloadKey] = useState(0);

    const fetchRules = useCallback(async (signal?: AbortSignal) => {
        if (!token) {
            setLoading(false);
            setRules([]);
            setError('Debes iniciar sesión para ver las automatizaciones');
            return;
        }
        setLoading(true);
        try {
            setError(null);
            const data = await apiFetch<{ items: AutomationRule[]; total: number }>('/admin/automations', { token, signal });
            setRules(data?.items ?? []);
        } catch (err) {
            setRules([]);
            setError('No se pudieron cargar las automatizaciones');
            addToast('Error al cargar automatizaciones', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (authLoading) return;
        const controller = new AbortController();
        fetchRules(controller.signal);
        return () => controller.abort();
    }, [authLoading, fetchRules, reloadKey]);

    const openCreate = () => {
        setEditingRule(null);
        setForm(EMPTY_FORM);
        setIsDrawerOpen(true);
    };

    const openEdit = (rule: AutomationRule) => {
        setEditingRule(rule);
        setForm({
            name: rule.name,
            trigger: rule.trigger,
            action: rule.action,
            message: rule.payload?.message || '',
            taskTitle: rule.payload?.task_title || '',
        });
        setIsDrawerOpen(true);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) return;
        setIsSaving(true);
        const body = {
            name: form.name,
            trigger: form.trigger,
            action: form.action,
            payload: form.action === 'create_task'
                ? { task_title: form.taskTitle }
                : { message: form.message },
        };
        try {
            if (editingRule) {
                await apiFetch(`/admin/automations/${editingRule.id}`, { method: 'PATCH', token, body });
                addToast('Regla actualizada', 'success');
            } else {
                await apiFetch('/admin/automations', { method: 'POST', token, body });
                addToast('Regla creada exitosamente', 'success');
            }
            setIsDrawerOpen(false);
            fetchRules();
        } catch {
            addToast('Error al guardar la regla', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleToggle = async (rule: AutomationRule) => {
        try {
            await apiFetch(`/admin/automations/${rule.id}`, {
                method: 'PATCH', token,
                body: { active: !rule.active }
            });
            setRules(prev => prev.map(r => r.id === rule.id ? { ...r, active: !r.active } : r));
        } catch {
            addToast('Error al actualizar estado', 'error');
        }
    };

    const handleDelete = async (id: string) => {
        setDeletingId(id);
        try {
            await apiFetch(`/admin/automations/${id}`, { method: 'DELETE', token });
            setRules(prev => prev.filter(r => r.id !== id));
            addToast('Regla eliminada', 'success');
        } catch {
            addToast('Error al eliminar regla', 'error');
        } finally {
            setDeletingId(null);
        }
    };

    const getTriggerMeta = (t: string) => TRIGGERS.find(tr => tr.value === t);
    const getActionMeta = (a: string) => ACTIONS.find(ac => ac.value === a);

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Consolidación', icon: Users },
                { label: 'Automatizaciones', icon: Zap }
            ]}
            rightActions={
                <button
                    onClick={openCreate}
                    className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all"
                >
                    <Plus size={14} /> Nueva Regla
                </button>
            }
        >
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {authLoading ? (
                    <div className="flex justify-center py-12">
                        <Loader2 className="animate-spin text-[hsl(var(--text-secondary))]" size={24} />
                    </div>
                ) : error && (
                    <div className="flex flex-col gap-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200 md:flex-row md:items-center md:justify-between">
                        <div>
                            <p className="text-[11px] font-bold uppercase tracking-wide">No se pudieron cargar las automatizaciones</p>
                            <p className="text-xs">{error}</p>
                        </div>
                        <button
                            onClick={() => setReloadKey(key => key + 1)}
                            className="rounded-md border border-amber-300 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide hover:bg-amber-100 dark:border-amber-400/30 dark:hover:bg-amber-500/20"
                        >
                            Reintentar
                        </button>
                    </div>
                )}

                {/* Stats bar */}
                <div className="grid grid-cols-3 gap-3 mb-2">
                    {[
                        { label: 'Total Reglas', val: rules.length, color: 'text-[hsl(var(--text-primary))] dark:text-white' },
                        { label: 'Activas', val: rules.filter(r => r.active).length, color: 'text-emerald-600' },
                        { label: 'Inactivas', val: rules.filter(r => !r.active).length, color: 'text-[hsl(var(--text-secondary))]' },
                    ].map(s => (
                        <div key={s.label} className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 text-center">
                            <p className={`text-lg font-bold ${s.color}`}>{s.val}</p>
                            <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-0.5">{s.label}</p>
                        </div>
                    ))}
                </div>

                {/* Rules list */}
                {loading ? (
                    [...Array(3)].map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-md" />)
                ) : !error && rules.length === 0 ? (
                    <div className="py-1.5 flex flex-col items-center justify-center gap-4 text-center">
                        <div className="size-10 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))]">
                            <Zap size={48} strokeWidth={1} />
                        </div>
                        <div>
                            <h3 className="text-[hsl(var(--text-primary))] dark:text-white font-bold text-base">Sin automatizaciones</h3>
                            <p className="text-[hsl(var(--text-secondary))] text-sm mt-1">Crea reglas que disparen acciones pastorales automáticamente</p>
                        </div>
                        <button
                            onClick={openCreate}
                            className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-xs font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20"
                        >
                            Crear primera regla
                        </button>
                    </div>
                ) : !error ? (
                    <AnimatePresence>
                        {rules.map(rule => {
                            const trig = getTriggerMeta(rule.trigger);
                            const act = getActionMeta(rule.action);
                            const TrigIcon = trig?.icon || Zap;
                            const ActIcon = act?.icon || Send;
                            return (
                                <motion.div
                                    key={rule.id}
                                    layout
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, scale: 0.97 }}
                                    className={clsx(
                                        "bg-[hsl(var(--surface-1))] dark:bg-white/5 border rounded-md p-3 transition-all",
                                        rule.active
                                            ? "border-[hsl(var(--border))] dark:border-white/10 shadow-sm"
                                            : "border-dashed border-[hsl(var(--border))] dark:border-white/5 opacity-60"
                                    )}
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex items-center gap-4 flex-1 min-w-0">
                                            <div className={clsx("size-9 rounded-lg border flex items-center justify-center shrink-0", TRIGGER_COLORS[rule.trigger] || 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))]')}>
                                                <TrigIcon size={20} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white text-base tracking-tight truncate">{rule.name}</h3>
                                                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                                                    <span className={clsx("px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase tracking-wide border", TRIGGER_COLORS[rule.trigger] || 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))]')}>
                                                        {trig?.label || rule.trigger}
                                                    </span>
                                                    <span className="text-[hsl(var(--text-secondary))] text-xs">→</span>
                                                    <div className="flex items-center gap-1 px-2 py-0.5 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/10 border border-[hsl(var(--border))] dark:border-white/10 text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                                        <ActIcon size={10} />
                                                        {act?.label || rule.action}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2 shrink-0">
                                            <button
                                                onClick={() => handleToggle(rule)}
                                                className="transition-all"
                                                title={rule.active ? 'Desactivar' : 'Activar'}
                                            >
                                                {rule.active
                                                    ? <ToggleRight size={28} className="text-emerald-500" />
                                                    : <ToggleLeft size={28} className="text-[hsl(var(--text-secondary))]" />
                                                }
                                            </button>
                                            <button
                                                onClick={() => openEdit(rule)}
                                                className="p-2 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all"
                                            >
                                                <Settings2 size={16} />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(rule.id)}
                                                disabled={deletingId === rule.id}
                                                className="p-2 rounded-md text-[hsl(var(--text-secondary))] hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-all disabled:opacity-50"
                                            >
                                                {deletingId === rule.id
                                                    ? <Loader2 size={16} className="animate-spin" />
                                                    : <Trash2 size={16} />
                                                }
                                            </button>
                                        </div>
                                    </div>
                                    {rule.payload?.message && (
                                        <div className="mt-3 ml-16 p-3 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md border border-[hsl(var(--border))] dark:border-white/5">
                                            <p className="text-[11px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] italic">&quot;{rule.payload.message}&quot;</p>
                                        </div>
                                    )}
                                </motion.div>
                            );
                        })}
                    </AnimatePresence>
                ) : null}
            </div>

            {/* ─── Drawer: Crear / Editar Regla ─── */}
            <WorkspaceDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                title={editingRule ? 'Editar Regla' : 'Nueva Regla de Automatización'}
                subtitle="Dispara acciones pastorales de forma automática"
                actions={
                    <>
                        <button type="button" onClick={() => setIsDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]">
                            Cancelar
                        </button>
                        <button
                            form="automation-form"
                            type="submit"
                            disabled={isSaving}
                            className="px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2"
                        >
                            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                            {editingRule ? 'Guardar Cambios' : 'Crear Regla'}
                        </button>
                    </>
                }
            >
                <form id="automation-form" onSubmit={handleSave} className="space-y-2">
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Nombre de la regla *</label>
                        <input
                            required
                            value={form.name}
                            onChange={e => setForm({ ...form, name: e.target.value })}
                            placeholder="Ej: Bienvenida a nuevos personas"
                            className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Disparador (Trigger)</label>
                        <div className="grid grid-cols-1 gap-2">
                            {TRIGGERS.map(t => {
                                const Icon = t.icon;
                                const selected = form.trigger === t.value;
                                return (
                                    <button
                                        key={t.value}
                                        type="button"
                                        onClick={() => setForm({ ...form, trigger: t.value })}
                                        className={clsx(
                                            "flex items-center gap-3 px-4 py-1.5 rounded-lg border text-left transition-all",
                                            selected
                                                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                                                : "border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:border-blue-300"
                                        )}
                                    >
                                        <div className={clsx("size-8 rounded-md flex items-center justify-center", selected ? 'bg-[hsl(var(--primary))] text-white' : 'bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))]')}>
                                            <Icon size={16} />
                                        </div>
                                        <span className={clsx("text-[11px] font-bold uppercase tracking-wide", selected ? 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]')}>
                                            {t.label}
                                        </span>
                                        {selected && <CheckCircle2 size={16} className="ml-auto text-[hsl(var(--primary))]" />}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Acción a ejecutar</label>
                        <select
                            value={form.action}
                            onChange={e => setForm({ ...form, action: e.target.value })}
                            className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white appearance-none"
                        >
                            {ACTIONS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                        </select>
                    </div>

                    {form.action === 'create_task' ? (
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Título de la tarea pastoral</label>
                            <input
                                value={form.taskTitle}
                                onChange={e => setForm({ ...form, taskTitle: e.target.value })}
                                placeholder="Ej: Visitar al nuevo persona"
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                            />
                        </div>
                    ) : (
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                Mensaje a enviar <span className="normal-case font-bold">(usa {'{'+'nombre'+'}'} para personalizar)</span>
                            </label>
                            <textarea
                                value={form.message}
                                onChange={e => setForm({ ...form, message: e.target.value })}
                                placeholder="Hola {nombre}, bienvenido a CCF..."
                                rows={4}
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white resize-none"
                            />
                        </div>
                    )}
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}

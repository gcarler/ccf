"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
    BookOpen, Plus, Search, MessageSquare, Mail, Smartphone,
    Globe, FileText, Zap, Star, Copy, Send, Edit3, Trash2,
    X, ChevronRight, Check, Eye,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import { toast } from 'sonner';
import clsx from 'clsx';
import CrmShell from '@/components/crm/CrmShell';
import type { CrmResource, ResourceType, ResourceChannel, ResourceCategory } from '@/types/crm';

// ── Constants ───────────────────────────────────────────────────────────────

const TYPE_OPTIONS: { value: ResourceType | ''; label: string; icon: React.ElementType }[] = [
    { value: '', label: 'Todos', icon: BookOpen },
    { value: 'message', label: 'Plantilla', icon: FileText },
    { value: 'script', label: 'Guión', icon: Star },
    { value: 'quick_reply', label: 'Resp. rápida', icon: Zap },
];

const CHANNEL_OPTIONS: { value: ResourceChannel | ''; label: string; icon: React.ElementType; color: string }[] = [
    { value: '', label: 'Todos', icon: Globe, color: 'text-slate-400' },
    { value: 'whatsapp', label: 'WhatsApp', icon: MessageSquare, color: 'text-emerald-500' },
    { value: 'email', label: 'Email', icon: Mail, color: 'text-[hsl(var(--primary))]' },
    { value: 'sms', label: 'SMS', icon: Smartphone, color: 'text-amber-500' },
    { value: 'general', label: 'General', icon: Globe, color: 'text-slate-400' },
];

const CATEGORY_LABELS: Record<string, string> = {
    bienvenida: 'Bienvenida', seguimiento: 'Seguimiento', invitacion: 'Invitación',
    pastoral: 'Pastoral', consolidacion: 'Consolidación', anuncio: 'Anuncio', general: 'General',
};

const CATEGORY_COLORS: Record<string, string> = {
    bienvenida: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400',
    seguimiento: 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400',
    invitacion: 'bg-purple-50 text-purple-700 dark:bg-purple-900/20 dark:text-purple-400',
    pastoral: 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400',
    consolidacion: 'bg-rose-50 text-rose-700 dark:bg-rose-900/20 dark:text-rose-400',
    anuncio: 'bg-sky-50 text-sky-700 dark:bg-sky-900/20 dark:text-sky-400',
    general: 'bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-400',
};

const VARIABLES_CATALOG = ['{{nombre}}', '{{apellido}}', '{{fecha}}', '{{sede}}', '{{pastor}}', '{{telefono}}'];

const EMPTY_FORM = {
    name: '', description: '', type: 'message' as ResourceType,
    channel: 'whatsapp' as ResourceChannel, category: 'general' as ResourceCategory,
    subject: '', body: '', variables: [] as string[], tags: [] as string[],
};

// ── Channel icon helper ──────────────────────────────────────────────────────

function ChannelIcon({ channel, size = 16 }: { channel?: string | null; size?: number }) {
    const opt = CHANNEL_OPTIONS.find(c => c.value === channel);
    if (!opt) return <Globe size={size} className="text-slate-400" />;
    const Icon = opt.icon;
    return <Icon size={size} className={opt.color} />;
}

// ── Resource Card ────────────────────────────────────────────────────────────

function ResourceCard({
    resource, selected, onSelect, onEdit, onDelete, onUse,
}: {
    resource: CrmResource; selected: boolean;
    onSelect: () => void; onEdit: () => void;
    onDelete: () => void; onUse: () => void;
}) {
    return (
        <div
            onClick={onSelect}
            className={clsx(
                'group relative rounded-xl border p-4 cursor-pointer transition-all duration-200',
                selected
                    ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.04)] shadow-md'
                    : 'border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 hover:border-slate-300 dark:hover:border-white/20 hover:shadow-sm'
            )}
        >
            {/* Header */}
            <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 min-w-0">
                    <div className={clsx(
                        'size-8 rounded-lg flex items-center justify-center shrink-0',
                        selected ? 'bg-[hsl(var(--primary)/0.1)]' : 'bg-slate-50 dark:bg-white/5'
                    )}>
                        <ChannelIcon channel={resource.channel} size={15} />
                    </div>
                    <p className="text-[12px] font-bold text-slate-800 dark:text-white truncate">{resource.name}</p>
                </div>
                <span className={clsx('shrink-0 text-[9px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full', CATEGORY_COLORS[resource.category])}>
                    {CATEGORY_LABELS[resource.category] ?? resource.category}
                </span>
            </div>

            {/* Body preview */}
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed line-clamp-2 mb-3">
                {resource.body || '—'}
            </p>

            {/* Footer */}
            <div className="flex items-center justify-between">
                <span className="text-[9px] font-semibold uppercase text-slate-400">
                    {resource.usage_count > 0 ? `${resource.usage_count} usos` : 'Sin usar'}
                </span>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                        onClick={e => { e.stopPropagation(); onUse(); }}
                        className="p-1.5 rounded-md bg-[hsl(var(--primary))] text-white hover:opacity-90 transition-opacity"
                        title="Usar esta plantilla"
                    >
                        <Send size={11} />
                    </button>
                    <button
                        onClick={e => { e.stopPropagation(); onEdit(); }}
                        className="p-1.5 rounded-md bg-slate-100 dark:bg-white/10 text-slate-500 hover:text-slate-700 transition-colors"
                        title="Editar"
                    >
                        <Edit3 size={11} />
                    </button>
                    <button
                        onClick={e => { e.stopPropagation(); onDelete(); }}
                        className="p-1.5 rounded-md bg-rose-50 dark:bg-rose-500/10 text-rose-500 hover:bg-rose-100 transition-colors"
                        title="Archivar"
                    >
                        <Trash2 size={11} />
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Preview Panel ────────────────────────────────────────────────────────────

function PreviewPanel({ resource, onClose, onEdit, onUse }: {
    resource: CrmResource; onClose: () => void;
    onEdit: () => void; onUse: () => void;
}) {
    const [previewVars, setPreviewVars] = useState<Record<string, string>>({});
    const [copied, setCopied] = useState(false);

    const vars = resource.variables ?? [];

    const resolvedBody = vars.reduce((text, v) => {
        const key = v.replace(/[{}]/g, '');
        return text.replaceAll(v, previewVars[key] || v);
    }, resource.body);

    const handleCopy = () => {
        navigator.clipboard.writeText(resolvedBody);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        onUse();
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-white/10 shrink-0">
                <div className="flex items-center gap-2">
                    <ChannelIcon channel={resource.channel} size={16} />
                    <span className="text-[11px] font-bold text-slate-700 dark:text-white uppercase tracking-wide truncate max-w-[200px]">
                        {resource.name}
                    </span>
                </div>
                <div className="flex items-center gap-1.5">
                    <button onClick={onEdit} className="p-1.5 rounded-md bg-slate-100 dark:bg-white/5 text-slate-500 hover:text-slate-700 transition-colors" title="Editar">
                        <Edit3 size={14} />
                    </button>
                    <button onClick={onClose} className="p-1.5 rounded-md bg-slate-100 dark:bg-white/5 text-slate-400 hover:text-slate-700 transition-colors">
                        <X size={14} />
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
                {/* Meta */}
                <div className="flex flex-wrap gap-2">
                    <span className={clsx('text-[9px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full', CATEGORY_COLORS[resource.category])}>
                        {CATEGORY_LABELS[resource.category]}
                    </span>
                    {resource.subject && (
                        <span className="text-[9px] font-semibold text-slate-500 dark:text-slate-400">
                            Asunto: {resource.subject}
                        </span>
                    )}
                </div>

                {/* Variable filler */}
                {vars.length > 0 && (
                    <div className="space-y-2">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Personalizar preview</p>
                        {vars.map(v => {
                            const key = v.replace(/[{}]/g, '');
                            return (
                                <div key={v} className="flex items-center gap-2">
                                    <span className="text-[10px] font-mono text-[hsl(var(--primary))] w-28 shrink-0">{v}</span>
                                    <input
                                        value={previewVars[key] ?? ''}
                                        onChange={e => setPreviewVars(p => ({ ...p, [key]: e.target.value }))}
                                        placeholder={`Valor de ${key}`}
                                        className="flex-1 text-[11px] px-2 py-1 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-700 dark:text-white outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.4)]"
                                    />
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Resolved body */}
                <div>
                    <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-2">Vista previa</p>
                    <div className="rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 p-4">
                        <p className="text-[12px] text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                            {resolvedBody}
                        </p>
                    </div>
                </div>

                {/* Script steps */}
                {resource.type === 'script' && resource.steps && resource.steps.length > 0 && (
                    <div>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-2">Pasos del guión</p>
                        <ol className="space-y-2">
                            {resource.steps.map((step, i) => (
                                <li key={i} className="flex gap-3">
                                    <span className="size-5 rounded-full bg-[hsl(var(--primary))] text-white text-[9px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                                        {step.order ?? i + 1}
                                    </span>
                                    <p className="text-[12px] text-slate-600 dark:text-slate-300">{step.text}</p>
                                </li>
                            ))}
                        </ol>
                    </div>
                )}
            </div>

            {/* Actions */}
            <div className="px-5 py-4 border-t border-slate-200 dark:border-white/10 shrink-0 flex gap-2">
                <button
                    onClick={handleCopy}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-[hsl(var(--primary))] text-white text-[11px] font-bold uppercase tracking-wide hover:opacity-90 transition-opacity"
                >
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? 'Copiado' : 'Copiar mensaje'}
                </button>
                <button
                    onClick={onUse}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 text-[11px] font-bold uppercase tracking-wide hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                    title="Abrir en mensajería"
                >
                    <Send size={14} />
                </button>
            </div>
        </div>
    );
}

// ── Resource Drawer (create / edit) ─────────────────────────────────────────

function ResourceDrawer({ resource, onClose, onSaved }: {
    resource: Partial<CrmResource> | null;
    onClose: () => void;
    onSaved: (r: CrmResource) => void;
}) {
    const { token } = useAuth();
    const isEdit = !!resource?.id;
    const [form, setForm] = useState({ ...EMPTY_FORM, ...(resource ?? {}) });
    const [saving, setSaving] = useState(false);
    const [tagInput, setTagInput] = useState('');

    const set = (field: string, value: unknown) => setForm(f => ({ ...f, [field]: value }));

    const insertVariable = (v: string) => {
        set('body', form.body + (form.body.endsWith(' ') || !form.body ? '' : ' ') + v);
        const vars = form.variables ?? [];
        if (!vars.includes(v)) set('variables', [...vars, v]);
    };

    const addTag = () => {
        const t = tagInput.trim();
        const tags = form.tags ?? [];
        if (t && !tags.includes(t)) { set('tags', [...tags, t]); setTagInput(''); }
    };

    const handleSubmit = async () => {
        if (!form.name.trim() || !form.body.trim()) {
            toast.error('Nombre y cuerpo son obligatorios');
            return;
        }
        setSaving(true);
        try {
            const payload = {
                name: form.name.trim(), description: form.description || null,
                type: form.type, channel: form.channel || null,
                category: form.category, subject: form.subject || null,
                body: form.body, variables: form.variables, tags: form.tags,
            };
            let saved: CrmResource;
            if (isEdit) {
                saved = await apiFetch<CrmResource>(`/crm/resources/${resource!.id}`, { method: 'PATCH', token, body: payload });
            } else {
                saved = await apiFetch<CrmResource>('/crm/resources', { method: 'POST', token, body: payload });
            }
            toast.success(isEdit ? 'Recurso actualizado' : 'Recurso creado');
            onSaved(saved);
        } catch {
            toast.error('Error al guardar el recurso');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-y-0 right-0 z-[500] w-full max-w-lg bg-white dark:bg-[#1e1f21] shadow-2xl border-l border-slate-200 dark:border-white/10 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-white/10 shrink-0">
                <span className="text-[12px] font-bold text-slate-700 dark:text-white uppercase tracking-wide">
                    {isEdit ? 'Editar recurso' : 'Nuevo recurso'}
                </span>
                <button onClick={onClose} className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 transition-colors"><X size={16} /></button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
                {/* Tipo */}
                <div>
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 block">Tipo</label>
                    <div className="flex gap-2">
                        {(['message', 'script', 'quick_reply'] as ResourceType[]).map(t => (
                            <button key={t}
                                onClick={() => set('type', t)}
                                className={clsx('flex-1 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wide border transition-all',
                                    form.type === t ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]' : 'border-slate-200 dark:border-white/10 text-slate-500 hover:border-slate-300'
                                )}
                            >
                                {t === 'message' ? 'Plantilla' : t === 'script' ? 'Guión' : 'Resp. rápida'}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Canal */}
                {form.type !== 'script' && (
                    <div>
                        <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 block">Canal</label>
                        <div className="flex gap-2 flex-wrap">
                            {CHANNEL_OPTIONS.filter(c => c.value).map(c => {
                                const Icon = c.icon;
                                return (
                                    <button key={c.value}
                                        onClick={() => set('channel', c.value)}
                                        className={clsx('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold border transition-all',
                                            form.channel === c.value ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]' : 'border-slate-200 dark:border-white/10 text-slate-500 hover:border-slate-300'
                                        )}
                                    >
                                        <Icon size={12} /> {c.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Categoría */}
                <div>
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 block">Categoría</label>
                    <select
                        value={form.category}
                        onChange={e => set('category', e.target.value)}
                        className="w-full text-[12px] px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-700 dark:text-white outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.4)]"
                    >
                        {Object.entries(CATEGORY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                </div>

                {/* Nombre */}
                <div>
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 block">Nombre *</label>
                    <input
                        value={form.name}
                        onChange={e => set('name', e.target.value)}
                        placeholder="Ej: Bienvenida primer contacto"
                        className="w-full text-[12px] px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-700 dark:text-white outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.4)]"
                    />
                </div>

                {/* Asunto (solo email) */}
                {form.channel === 'email' && (
                    <div>
                        <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 block">Asunto del email</label>
                        <input
                            value={form.subject || ''}
                            onChange={e => set('subject', e.target.value)}
                            placeholder="Ej: ¡Bienvenido a El Faro!"
                            className="w-full text-[12px] px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-700 dark:text-white outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.4)]"
                        />
                    </div>
                )}

                {/* Variables helper */}
                <div>
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 block">Variables disponibles</label>
                    <div className="flex flex-wrap gap-1.5">
                        {VARIABLES_CATALOG.map(v => (
                            <button key={v} onClick={() => insertVariable(v)}
                                className="text-[10px] font-mono px-2 py-1 rounded-md bg-[hsl(var(--primary)/0.08)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)] hover:bg-[hsl(var(--primary)/0.15)] transition-colors"
                            >
                                {v}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Cuerpo */}
                <div>
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 block">Mensaje *</label>
                    <textarea
                        value={form.body}
                        onChange={e => set('body', e.target.value)}
                        rows={6}
                        placeholder="Hola {{nombre}}, te damos la bienvenida a El Faro..."
                        className="w-full text-[12px] px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-700 dark:text-white outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.4)] resize-none leading-relaxed"
                    />
                </div>

                {/* Descripción */}
                <div>
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 block">Descripción (opcional)</label>
                    <input
                        value={form.description || ''}
                        onChange={e => set('description', e.target.value)}
                        placeholder="Para qué sirve este recurso"
                        className="w-full text-[12px] px-3 py-2 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-700 dark:text-white outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.4)]"
                    />
                </div>

                {/* Tags */}
                <div>
                    <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-1.5 block">Etiquetas</label>
                    <div className="flex gap-2 mb-2">
                        <input
                            value={tagInput}
                            onChange={e => setTagInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && addTag()}
                            placeholder="Nueva etiqueta + Enter"
                            className="flex-1 text-[11px] px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-700 dark:text-white outline-none"
                        />
                        <button onClick={addTag} className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-white text-[11px] font-semibold">+</button>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                        {(form.tags ?? []).map(tag => (
                            <span key={tag} className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300">
                                {tag}
                                <button onClick={() => set('tags', (form.tags ?? []).filter(t => t !== tag))}><X size={9} /></button>
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="px-5 py-4 border-t border-slate-200 dark:border-white/10 shrink-0 flex gap-2">
                <button onClick={onClose} className="px-4 py-2.5 rounded-lg border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 text-[11px] font-bold uppercase tracking-wide hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                    Cancelar
                </button>
                <button onClick={handleSubmit} disabled={saving}
                    className="flex-1 py-2.5 rounded-lg bg-[hsl(var(--primary))] text-white text-[11px] font-bold uppercase tracking-wide hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                    {saving ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear recurso'}
                </button>
            </div>
        </div>
    );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function ResourcesPage() {
    const { token } = useAuth();
    const { canEditCrm } = useCrmAccess();
    const [resources, setResources] = useState<CrmResource[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterType, setFilterType] = useState<ResourceType | ''>('');
    const [filterChannel, setFilterChannel] = useState<ResourceChannel | ''>('');
    const [filterCategory, setFilterCategory] = useState<ResourceCategory | ''>('');
    const [search, setSearch] = useState('');
    const [selected, setSelected] = useState<CrmResource | null>(null);
    const [drawerResource, setDrawerResource] = useState<Partial<CrmResource> | null | false>(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filterType) params.set('type', filterType);
            if (filterChannel) params.set('channel', filterChannel);
            if (filterCategory) params.set('category', filterCategory);
            if (search) params.set('q', search);
            const data = await apiFetch<CrmResource[]>(`/crm/resources?${params}`, { token });
            setResources(Array.isArray(data) ? data : []);
        } catch {
            toast.error('Error al cargar recursos');
        } finally {
            setLoading(false);
        }
    }, [token, filterType, filterChannel, filterCategory, search]);

    useEffect(() => { load(); }, [load]);

    const handleDelete = async (id: string) => {
        try {
            await apiFetch(`/crm/resources/${id}`, { method: 'DELETE', token });
            toast.success('Recurso archivado');
            setSelected(null);
            load();
        } catch { toast.error('Error al archivar'); }
    };

    const handleUse = async (resource: CrmResource) => {
        try {
            await apiFetch(`/crm/resources/${resource.id}/use`, { method: 'POST', token });
            load();
        } catch { /* silent */ }
    };

    const handleSaved = (saved: CrmResource) => {
        setDrawerResource(false);
        setSelected(saved);
        load();
    };

    return (
        <CrmShell breadcrumbs={[{ label: 'Recursos', icon: BookOpen }]}>
            <div className="flex h-full min-h-0 overflow-hidden">

                {/* ── Left: Filters + Grid ── */}
                <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                    {/* Top bar */}
                    <div className="px-4 py-3 border-b border-slate-200 dark:border-white/10 shrink-0 space-y-3">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <BookOpen size={16} className="text-[hsl(var(--primary))]" />
                                <h1 className="text-[13px] font-bold text-slate-800 dark:text-white uppercase tracking-wide">Biblioteca de Recursos</h1>
                                <span className="text-[10px] font-semibold text-slate-400 bg-slate-100 dark:bg-white/10 px-2 py-0.5 rounded-full">
                                    {resources.length}
                                </span>
                            </div>
                            {canEditCrm && (
                                <button
                                    onClick={() => setDrawerResource({})}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide hover:opacity-90 transition-opacity shadow-sm"
                                >
                                    <Plus size={13} /> Nuevo recurso
                                </button>
                            )}
                        </div>

                        {/* Search */}
                        <div className="relative">
                            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                placeholder="Buscar por nombre o contenido..."
                                className="w-full pl-8 pr-3 py-1.5 text-[11px] rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-700 dark:text-white outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.4)]"
                            />
                        </div>

                        {/* Filters */}
                        <div className="flex gap-2 flex-wrap">
                            {/* Type */}
                            <div className="flex gap-1">
                                {TYPE_OPTIONS.map(opt => {
                                    const Icon = opt.icon;
                                    return (
                                        <button key={opt.value}
                                            onClick={() => setFilterType(opt.value)}
                                            className={clsx('flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-semibold border transition-all',
                                                filterType === opt.value ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]' : 'border-slate-200 dark:border-white/10 text-slate-500 hover:border-slate-300'
                                            )}
                                        >
                                            <Icon size={11} /> {opt.label}
                                        </button>
                                    );
                                })}
                            </div>
                            {/* Channel */}
                            <div className="flex gap-1">
                                {CHANNEL_OPTIONS.map(opt => {
                                    const Icon = opt.icon;
                                    return (
                                        <button key={opt.value}
                                            onClick={() => setFilterChannel(opt.value as ResourceChannel | '')}
                                            className={clsx('flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-semibold border transition-all',
                                                filterChannel === opt.value ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]' : 'border-slate-200 dark:border-white/10 text-slate-500 hover:border-slate-300'
                                            )}
                                        >
                                            <Icon size={11} className={filterChannel === opt.value ? 'text-white' : opt.color} /> {opt.label}
                                        </button>
                                    );
                                })}
                            </div>
                            {/* Category */}
                            <select
                                value={filterCategory}
                                onChange={e => setFilterCategory(e.target.value as ResourceCategory | '')}
                                className="text-[10px] font-semibold px-2 py-1 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-slate-500 dark:text-slate-400 outline-none"
                            >
                                <option value="">Todas las categorías</option>
                                {Object.entries(CATEGORY_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                            </select>
                        </div>
                    </div>

                    {/* Grid */}
                    <div className="flex-1 overflow-y-auto p-4">
                        {loading ? (
                            <div className="flex items-center justify-center h-40">
                                <div className="animate-spin size-6 border-2 border-[hsl(var(--primary))] border-t-transparent rounded-full" />
                            </div>
                        ) : resources.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-40 gap-3">
                                <BookOpen size={32} className="text-slate-300 dark:text-slate-600" />
                                <p className="text-[12px] text-slate-400">No hay recursos todavía</p>
                                {canEditCrm && (
                                    <button onClick={() => setDrawerResource({})} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase">
                                        <Plus size={12} /> Crear el primero
                                    </button>
                                )}
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                                {resources.map(r => (
                                    <ResourceCard
                                        key={r.id}
                                        resource={r}
                                        selected={selected?.id === r.id}
                                        onSelect={() => setSelected(selected?.id === r.id ? null : r)}
                                        onEdit={() => setDrawerResource(r)}
                                        onDelete={() => handleDelete(r.id)}
                                        onUse={() => handleUse(r)}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Right: Preview Panel ── */}
                {selected && (
                    <div className="w-80 xl:w-96 shrink-0 border-l border-slate-200 dark:border-white/10 bg-white dark:bg-[#1a1b1d] overflow-hidden flex flex-col">
                        <PreviewPanel
                            resource={selected}
                            onClose={() => setSelected(null)}
                            onEdit={() => setDrawerResource(selected)}
                            onUse={() => handleUse(selected)}
                        />
                    </div>
                )}
            </div>

            {/* Drawer overlay */}
            {drawerResource !== false && (
                <>
                    <div className="fixed inset-0 z-[499] bg-black/20 backdrop-blur-sm" onClick={() => setDrawerResource(false)} />
                    <ResourceDrawer
                        resource={drawerResource}
                        onClose={() => setDrawerResource(false)}
                        onSaved={handleSaved}
                    />
                </>
            )}
        </CrmShell>
    );
}

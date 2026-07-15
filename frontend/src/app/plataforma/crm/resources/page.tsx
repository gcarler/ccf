'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import {
    BookOpen, Check, ChevronRight, Download, FileText,
    Loader2, Mail, Megaphone, MessageSquare, Palette, Paperclip, Plus,
    Search, Send, Trash2, Upload, Users, X, Pencil, Clock,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type {
    BitacoraEnvio, CampaignResult, CanalEnvio, CategoriaRecurso,
    PlantillaMensaje, RecursoAdjunto,
} from '@/types/crm';
import ResourceBankGallery from './ResourceBankGallery';

// ── Helpers ───────────────────────────────────────────────────────────────────

const CANAL_META: Record<CanalEnvio, { label: string; icon: React.ElementType; color: string; bg: string }> = {
    WHATSAPP: { label: 'WhatsApp', icon: MessageSquare, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
    EMAIL:    { label: 'Email',    icon: Mail,          color: 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]',    bg: 'bg-blue-50 dark:bg-blue-900/20' },
    SMS:      { label: 'SMS',      icon: Send,          color: 'text-amber-600 dark:text-amber-400',  bg: 'bg-amber-50 dark:bg-amber-900/20' },
};

const ESTADO_META: Record<string, { label: string; cls: string }> = {
    PROCESANDO: { label: 'Procesando', cls: 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/10 dark:text-[hsl(var(--text-secondary))]' },
    ENVIADO:    { label: 'Enviado',    cls: 'bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-900/20 dark:text-[hsl(var(--primary))]' },
    ENTREGADO:  { label: 'Entregado', cls: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400' },
    LEIDO:      { label: 'Leído',     cls: 'bg-teal-50 text-teal-700 dark:bg-teal-900/20 dark:text-teal-400' },
    FALLIDO:    { label: 'Fallido',   cls: 'bg-rose-50 text-rose-700 dark:bg-rose-900/20 dark:text-rose-400' },
};

function fmt(iso: string) {
    return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fmtBytes(b: number) {
    if (b < 1024) return `${b} B`;
    if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
    return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

function hydrate(text: string, vars: Record<string, string>) {
    return Object.entries(vars).reduce(
        (t, [k, v]) => t.replaceAll(`{{${k}}}`, v || `{{${k}}}`),
        text,
    );
}

// ── Canal icon ────────────────────────────────────────────────────────────────

function CanalBadge({ canal }: { canal: CanalEnvio }) {
    const m = CANAL_META[canal];
    const Icon = m.icon;
    return (
        <span className={clsx('inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full', m.bg, m.color)}>
            <Icon size={11} />{m.label}
        </span>
    );
}

// ── Category dot ──────────────────────────────────────────────────────────────

function CategoriaDot({ color, size = 8 }: { color: string; size?: number }) {
    return <span className="rounded-full shrink-0 inline-block" style={{ width: size, height: size, background: color }} />;
}

// ── Template Card ─────────────────────────────────────────────────────────────

function PlantillaCard({
    plantilla, selected, onSelect, onEdit, onDelete,
}: {
    plantilla: PlantillaMensaje; selected: boolean;
    onSelect: () => void; onEdit: () => void; onDelete: () => void;
}) {
    return (
        <div
            onClick={onSelect}
            className={clsx(
                'group relative rounded-xl border p-4 cursor-pointer transition-all duration-150',
                selected
                    ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.04)] shadow-md'
                    : 'border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 hover:border-[hsl(var(--border))] dark:hover:border-white/20 hover:shadow-sm',
            )}
        >
            {/* Header */}
            <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-1.5 min-w-0">
                    {plantilla.categoria && (
                        <CategoriaDot color={plantilla.categoria.color_ui_hex ?? '#6B7280'} />
                    )}
                    <span className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{plantilla.titulo}</span>
                </div>
                <CanalBadge canal={plantilla.canal} />
            </div>

            {/* Preview */}
            <p className="text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] line-clamp-2 mb-3">
                {plantilla.contenido_texto}
            </p>

            {/* Variables */}
            {(plantilla.variables_requeridas ?? []).length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                    {(plantilla.variables_requeridas ?? []).slice(0, 4).map(v => (
                        <span key={v} className="text-[10px] font-mono bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] px-1.5 py-0.5 rounded">
                            {`{{${v}}}`}
                        </span>
                    ))}
                    {(plantilla.variables_requeridas ?? []).length > 4 && (
                        <span className="text-[10px] text-[hsl(var(--text-secondary))]">+{(plantilla.variables_requeridas ?? []).length - 4}</span>
                    )}
                </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-between text-[10px] text-[hsl(var(--text-secondary))]">
                <span>{plantilla.total_envios ?? 0} envíos</span>
                <span>{plantilla.fecha_creacion ? fmt(plantilla.fecha_creacion) : '—'}</span>
            </div>

            {/* Hover actions */}
            <div className="absolute top-3 right-3 hidden group-hover:flex items-center gap-1">
                <button
                    onClick={e => { e.stopPropagation(); onEdit(); }}
                    className="size-6 flex items-center justify-center rounded-md bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white shadow-sm transition-colors"
                >
                    <Pencil size={12} />
                </button>
                <button
                    onClick={e => { e.stopPropagation(); onDelete(); }}
                    className="size-6 flex items-center justify-center rounded-md bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border border-rose-200 dark:border-rose-500/30 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 shadow-sm transition-colors"
                >
                    <Trash2 size={12} />
                </button>
            </div>
        </div>
    );
}

// ── Right detail panel ────────────────────────────────────────────────────────

function DetailPanel({
    plantilla, token,
    onEdit, onSend, onClose,
    onAdjuntoDeleted, onAdjuntoUploaded,
}: {
    plantilla: PlantillaMensaje; token: string;
    onEdit: () => void; onSend: () => void; onClose: () => void;
    onAdjuntoDeleted: (id: string) => void;
    onAdjuntoUploaded: (a: RecursoAdjunto) => void;
}) {
    const [tab, setTab] = useState<'preview' | 'adjuntos' | 'historial'>('preview');
    const [vars, setVars] = useState<Record<string, string>>({});
    const [copied, setCopied] = useState(false);
    const [bitacora, setBitacora] = useState<BitacoraEnvio[]>([]);
    const [loadingBit, setLoadingBit] = useState(false);
    const [uploading, setUploading] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const initial: Record<string, string> = {};
        (plantilla.variables_requeridas ?? []).forEach(v => { initial[v] = vars[v] ?? ''; });
        setVars(initial);
    }, [plantilla.id]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        if (tab === 'historial' && bitacora.length === 0) {
            setLoadingBit(true);
            apiFetch<BitacoraEnvio[]>(`/crm/resources/plantillas/${plantilla.id}/bitacora`, { token })
                .then(data => setBitacora(data ?? []))
                .finally(() => setLoadingBit(false));
        }
    }, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

    const previewText = hydrate(plantilla.contenido_texto, vars);

    function copyText() {
        navigator.clipboard.writeText(previewText).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    }

    async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        const form = new FormData();
        form.append('file', file);
        form.append('nombre_recurso', file.name);
        try {
            const res = await apiFetch<RecursoAdjunto>(
                `/crm/resources/plantillas/${plantilla.id}/adjuntos`,
                { token, method: 'POST', body: form },
            );
            if (res) onAdjuntoUploaded(res);
        } finally {
            setUploading(false);
            if (fileRef.current) fileRef.current.value = '';
        }
    }

    async function handleDeleteAdjunto(id: string) {
        await apiFetch(`/crm/resources/adjuntos/${id}`, { token, method: 'DELETE' });
        onAdjuntoDeleted(id);
    }

    const tabs = [
        { key: 'preview',   label: 'Vista previa',    icon: BookOpen },
        { key: 'adjuntos',  label: `Adjuntos (${plantilla.adjuntos?.length ?? 0})`, icon: Paperclip },
        { key: 'historial', label: 'Historial',        icon: Clock },
    ] as const;

    return (
        <div className="flex flex-col h-full border-l border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--bg-muted))]/50">
            {/* Header */}
            <div className="flex items-start justify-between gap-2 px-4 pt-4 pb-3 border-b border-[hsl(var(--border))] dark:border-white/10">
                <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <CanalBadge canal={plantilla.canal} />
                        {plantilla.categoria && (
                            <span className="text-xs font-medium" style={{ color: plantilla.categoria.color_ui_hex ?? '#6B7280' }}>
                                {plantilla.categoria.nombre}
                            </span>
                        )}
                    </div>
                    <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white leading-tight">{plantilla.titulo}</h3>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                    <button onClick={onEdit} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-colors">
                        <Pencil size={14} />
                    </button>
                    <button onClick={onClose} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-colors">
                        <X size={14} />
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-[hsl(var(--border))] dark:border-white/10 px-4">
                {tabs.map(t => {
                    const Icon = t.icon;
                    return (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key)}
                            className={clsx(
                                'flex items-center gap-1.5 text-xs font-medium py-2.5 px-2 border-b-2 -mb-px transition-colors',
                                tab === t.key
                                    ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))]'
                                    : 'border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))]',
                            )}
                        >
                            <Icon size={12} />{t.label}
                        </button>
                    );
                })}
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {tab === 'preview' && (
                    <>
                        {plantilla.canal === 'EMAIL' && plantilla.asunto && (
                            <div>
                                <p className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-1">Asunto</p>
                                <p className="text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{plantilla.asunto}</p>
                            </div>
                        )}

                        {/* Variable inputs */}
                        {(plantilla.variables_requeridas ?? []).length > 0 && (
                            <div>
                                <p className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2">Variables</p>
                                <div className="space-y-2">
                                    {(plantilla.variables_requeridas ?? []).map(v => (
                                        <div key={v} className="flex items-center gap-2">
                                            <span className="text-xs font-mono text-[hsl(var(--text-secondary))] w-24 shrink-0">{`{{${v}}}`}</span>
                                            <input
                                                value={vars[v] ?? ''}
                                                onChange={e => setVars(p => ({ ...p, [v]: e.target.value }))}
                                                placeholder={`Valor de ${v}`}
                                                className="flex-1 text-xs px-2 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.5)]"
                                            />
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Preview */}
                        <div>
                            <p className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2">Vista previa</p>
                            {plantilla.contenido_html ? (
                                <div className="rounded-xl border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden">
                                    <div className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary)/0.05)] dark:bg-[hsl(var(--primary)/0.1)] border-b border-[hsl(var(--border))] dark:border-white/10">
                                        <span className="text-[10px] font-medium text-[hsl(var(--primary))]">Vista previa HTML</span>
                                    </div>
                                    <iframe
                                        srcDoc={plantilla.contenido_html}
                                        title="Vista previa HTML"
                                        className="w-full h-[400px] bg-white"
                                        sandbox="allow-same-origin"
                                    />
                                </div>
                            ) : (
                                <div className="rounded-xl bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 p-3 text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] whitespace-pre-wrap leading-relaxed">
                                    {previewText}
                                </div>
                            )}
                        </div>

                        {/* Actions */}
                        <div className="flex gap-2">
                            <button
                                onClick={copyText}
                                className="flex-1 flex items-center justify-center gap-1.5 text-xs font-medium h-8 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/10 transition-colors"
                            >
                                {copied ? <Check size={12} className="text-emerald-500" /> : null}
                                {copied ? 'Copiado' : 'Copiar texto'}
                            </button>
                            {plantilla.canal === 'EMAIL' && (
                                <a
                                    href={`/plataforma/crm/resources/builder/${plantilla.id}`}
                                    className="flex-1 flex items-center justify-center gap-1.5 text-xs font-medium h-8 rounded-lg border border-[hsl(var(--primary)/0.3)] dark:border-[hsl(var(--primary)/0.4)] bg-[hsl(var(--primary)/0.05)] dark:bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.1)] dark:hover:bg-[hsl(var(--primary)/0.15)] transition-colors"
                                >
                                    <Palette size={12} />Diseñar
                                </a>
                            )}
                            <button
                                onClick={onSend}
                                className="flex-1 flex items-center justify-center gap-1.5 text-xs font-medium h-8 rounded-lg bg-[hsl(var(--primary))] text-white hover:opacity-90 transition-opacity"
                            >
                                <Send size={12} />Registrar envío
                            </button>
                        </div>
                    </>
                )}

                {tab === 'adjuntos' && (
                    <>
                        <div className="space-y-2">
                            {(plantilla.adjuntos ?? []).map(a => (
                                <div key={a.id} className="flex items-center gap-3 p-2.5 rounded-xl bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10">
                                    <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/10 flex items-center justify-center shrink-0">
                                        <FileText size={14} className="text-[hsl(var(--text-secondary))]" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-medium text-[hsl(var(--text-primary))] dark:text-white truncate">{a.nombre_recurso}</p>
                                        <p className="text-[10px] text-[hsl(var(--text-secondary))]">{a.tipo_mime} · {fmtBytes(a.peso_bytes)}</p>
                                    </div>
                                    <a href={a.url_acceso} target="_blank" rel="noopener noreferrer"
                                        className="size-6 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white transition-colors">
                                        <Download size={12} />
                                    </a>
                                    <button onClick={() => handleDeleteAdjunto(a.id)}
                                        className="size-6 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:text-rose-500 transition-colors">
                                        <Trash2 size={12} />
                                    </button>
                                </div>
                            ))}
                            {(plantilla.adjuntos ?? []).length === 0 && (
                                <p className="text-xs text-[hsl(var(--text-secondary))] text-center py-6">Sin adjuntos</p>
                            )}
                        </div>
                        <input ref={fileRef} type="file" className="hidden" onChange={handleUpload} />
                        <button
                            onClick={() => fileRef.current?.click()}
                            disabled={uploading}
                            className="w-full flex items-center justify-center gap-2 h-9 rounded-xl border-2 border-dashed border-[hsl(var(--border))] dark:border-white/20 text-xs font-medium text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--primary)/0.5)] hover:text-[hsl(var(--primary))] transition-colors disabled:opacity-50"
                        >
                            {uploading ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
                            {uploading ? 'Subiendo…' : 'Subir archivo'}
                        </button>
                    </>
                )}

                {tab === 'historial' && (
                    <>
                        {loadingBit && (
                            <div className="flex justify-center py-8"><Loader2 className="animate-spin text-[hsl(var(--text-secondary))]" size={20} /></div>
                        )}
                        {!loadingBit && bitacora.length === 0 && (
                            <p className="text-xs text-[hsl(var(--text-secondary))] text-center py-6">Sin envíos registrados</p>
                        )}
                        <div className="space-y-2">
                            {bitacora.map(b => {
                                const em = ESTADO_META[b.estado] ?? { label: b.estado, cls: '' };
                                return (
                                    <div key={b.id} className="p-3 rounded-xl bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10">
                                        <div className="flex items-center justify-between mb-1">
                                            <span className={clsx('text-[10px] font-medium px-2 py-0.5 rounded-full', em.cls)}>{em.label}</span>
                                            <span className="text-[10px] text-[hsl(var(--text-secondary))]">{fmt(b.fecha_envio)}</span>
                                        </div>
                                        <p className="text-[10px] text-[hsl(var(--text-secondary))] font-mono">→ {b.destinatario_id.slice(0, 8)}…</p>
                                        {b.log_error && (
                                            <p className="text-[10px] text-rose-500 mt-1">{b.log_error}</p>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

// ── Template drawer (create / edit) ──────────────────────────────────────────

const EMPTY_FORM = {
    titulo: '', canal: 'WHATSAPP' as CanalEnvio, categoria_id: '',
    asunto: '', contenido_texto: '', variables_requeridas: [] as string[],
    meta_template_id: '',
};

function PlantillaDrawer({
    open, onClose, categorias, token, editing,
    onSaved,
}: {
    open: boolean; onClose: () => void;
    categorias: CategoriaRecurso[]; token: string;
    editing: PlantillaMensaje | null;
    onSaved: (p: PlantillaMensaje) => void;
}) {
    const [form, setForm] = useState(EMPTY_FORM);
    const [newVar, setNewVar] = useState('');
    const [saving, setSaving] = useState(false);
    const bodyRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        if (!open) return;
        if (editing) {
            setForm({
                titulo: editing.titulo,
                canal: editing.canal,
                categoria_id: editing.categoria_id,
                asunto: editing.asunto ?? '',
                contenido_texto: editing.contenido_texto,
                variables_requeridas: [...editing.variables_requeridas],
                meta_template_id: editing.meta_template_id ?? '',
            });
        } else {
            setForm({ ...EMPTY_FORM, categoria_id: categorias[0]?.id ?? '' });
        }
        setNewVar('');
    }, [open, editing, categorias]);

    function setF<K extends keyof typeof EMPTY_FORM>(k: K, v: (typeof EMPTY_FORM)[K]) {
        setForm(p => ({ ...p, [k]: v }));
    }

    function insertVar(v: string) {
        const ta = bodyRef.current;
        if (!ta) return;
        const s = ta.selectionStart ?? form.contenido_texto.length;
        const e = ta.selectionEnd ?? s;
        const text = form.contenido_texto;
        const next = text.slice(0, s) + `{{${v}}}` + text.slice(e);
        setF('contenido_texto', next);
        setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + v.length + 4; ta.focus(); }, 0);
    }

    function addVar() {
        const v = newVar.trim().replace(/\s+/g, '_');
        if (!v || form.variables_requeridas.includes(v)) return;
        setF('variables_requeridas', [...form.variables_requeridas, v]);
        setNewVar('');
    }

    function removeVar(v: string) {
        setF('variables_requeridas', form.variables_requeridas.filter(x => x !== v));
    }

    async function submit() {
        if (!form.titulo || !form.contenido_texto || !form.categoria_id) return;
        setSaving(true);
        try {
            const body = {
                titulo: form.titulo, canal: form.canal,
                categoria_id: form.categoria_id,
                asunto: form.canal === 'EMAIL' ? form.asunto || null : null,
                contenido_texto: form.contenido_texto,
                variables_requeridas: form.variables_requeridas,
                meta_template_id: form.meta_template_id || null,
            };
            const url = editing
                ? `/crm/resources/plantillas/${editing.id}`
                : '/crm/resources/plantillas';
            const method = editing ? 'PATCH' : 'POST';
            const res = await apiFetch<PlantillaMensaje>(url, {
                token, method,
                body,
                headers: { 'Content-Type': 'application/json' },
            });
            if (res) { onSaved(res); onClose(); }
        } finally {
            setSaving(false);
        }
    }

    if (!open) return null;

    return (
        <>
            <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />
            <div className="fixed right-0 top-0 bottom-0 w-[480px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] border-l border-[hsl(var(--border))] dark:border-white/10 z-50 flex flex-col shadow-2xl">
                <div className="flex items-center justify-between px-5 py-4 border-b border-[hsl(var(--border))] dark:border-white/10">
                    <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">
                        {editing ? 'Editar plantilla' : 'Nueva plantilla'}
                    </h2>
                    <button onClick={onClose} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors">
                        <X size={15} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
                    {/* Título */}
                    <div>
                        <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">Título *</label>
                        <input
                            value={form.titulo}
                            onChange={e => setF('titulo', e.target.value)}
                            className="w-full text-sm px-3 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                            placeholder="Nombre de la plantilla"
                        />
                    </div>

                    {/* Canal */}
                    <div>
                        <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">Canal *</label>
                        <div className="flex gap-2">
                            {(['WHATSAPP', 'EMAIL', 'SMS'] as CanalEnvio[]).map(c => {
                                const m = CANAL_META[c]; const Icon = m.icon;
                                return (
                                    <button
                                        key={c}
                                        onClick={() => setF('canal', c)}
                                        className={clsx(
                                            'flex-1 flex items-center justify-center gap-1.5 h-9 rounded-lg border text-xs font-medium transition-all',
                                            form.canal === c
                                                ? `${m.bg} ${m.color} border-current`
                                                : 'border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5',
                                        )}
                                    >
                                        <Icon size={13} />{m.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Categoría */}
                    <div>
                        <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">Categoría *</label>
                        <select
                            value={form.categoria_id}
                            onChange={e => setF('categoria_id', e.target.value)}
                            className="w-full text-sm px-3 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                        >
                            <option value="">Seleccionar categoría…</option>
                            {categorias.map(c => (
                                <option key={c.id} value={c.id}>{c.nombre}</option>
                            ))}
                        </select>
                    </div>

                    {/* Asunto (solo email) */}
                    {form.canal === 'EMAIL' && (
                        <div>
                            <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">Asunto del email</label>
                            <input
                                value={form.asunto}
                                onChange={e => setF('asunto', e.target.value)}
                                className="w-full text-sm px-3 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                                placeholder="Asunto del correo"
                            />
                        </div>
                    )}

                    {/* Variables */}
                    <div>
                        <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">Variables requeridas</label>
                        <div className="flex gap-2 mb-2">
                            <input
                                value={newVar}
                                onChange={e => setNewVar(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && addVar()}
                                placeholder="nombre_variable"
                                className="flex-1 text-xs px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                            />
                            <button onClick={addVar} className="px-3 h-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] text-xs font-medium hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/20 transition-colors">
                                + Agregar
                            </button>
                        </div>
                        {form.variables_requeridas.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                                {form.variables_requeridas.map(v => (
                                    <span key={v} className="inline-flex items-center gap-1 text-xs font-mono bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] px-2 py-0.5 rounded-md">
                                        {`{{${v}}}`}
                                        <button onClick={() => removeVar(v)} className="text-[hsl(var(--text-secondary))] hover:text-rose-500 ml-0.5">
                                            <X size={10} />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Contenido */}
                    <div>
                        <div className="flex items-center justify-between mb-1">
                            <label className="text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Contenido *</label>
                            {form.variables_requeridas.length > 0 && (
                                <div className="flex gap-1 flex-wrap justify-end">
                                    {form.variables_requeridas.map(v => (
                                        <button key={v} onClick={() => insertVar(v)}
                                            className="text-[10px] font-mono bg-[hsl(var(--surface-2))] dark:bg-white/10 hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/20 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] px-1.5 py-0.5 rounded transition-colors">
                                            {`{{${v}}}`}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                        <textarea
                            ref={bodyRef}
                            value={form.contenido_texto}
                            onChange={e => setF('contenido_texto', e.target.value)}
                            rows={8}
                            className="w-full text-sm px-3 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)] resize-none font-mono leading-relaxed"
                            placeholder="Hola {{nombre}}, te escribimos desde {{sede}}…"
                        />
                    </div>

                    {/* Meta template id */}
                    <div>
                        <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">ID plantilla Meta (WhatsApp Business API)</label>
                        <input
                            value={form.meta_template_id}
                            onChange={e => setF('meta_template_id', e.target.value)}
                            className="w-full text-sm px-3 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                            placeholder="Opcional — ej: bienvenida_nuevo_v1"
                        />
                    </div>
                </div>

                <div className="px-5 py-4 border-t border-[hsl(var(--border))] dark:border-white/10 flex gap-2">
                    <button onClick={onClose} className="flex-1 h-9 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">
                        Cancelar
                    </button>
                    <button
                        onClick={submit}
                        disabled={saving || !form.titulo || !form.contenido_texto || !form.categoria_id}
                        className="flex-1 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-1.5"
                    >
                        {saving && <Loader2 size={13} className="animate-spin" />}
                        {editing ? 'Guardar cambios' : 'Crear plantilla'}
                    </button>
                </div>
            </div>
        </>
    );
}

// ── Category drawer ───────────────────────────────────────────────────────────

const DEFAULT_COLORS = ['#6B7280', '#10B981', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6'];

function CatDrawer({
    open, onClose, token, onSaved,
}: {
    open: boolean; onClose: () => void; token: string;
    onSaved: (c: CategoriaRecurso) => void;
}) {
    const [nombre, setNombre] = useState('');
    const [color, setColor] = useState('#6B7280');
    const [descripcion, setDescripcion] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (open) { setNombre(''); setColor('#6B7280'); setDescripcion(''); }
    }, [open]);

    async function submit() {
        if (!nombre.trim()) return;
        setSaving(true);
        try {
            const res = await apiFetch<CategoriaRecurso>('/crm/resources/categorias', {
                token, method: 'POST',
                body: { nombre: nombre.trim(), descripcion: descripcion.trim() || null, color_ui_hex: color },
                headers: { 'Content-Type': 'application/json' },
            });
            if (res) { onSaved(res); onClose(); }
        } finally {
            setSaving(false);
        }
    }

    if (!open) return null;

    return (
        <>
            <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />
            <div className="fixed right-0 top-0 bottom-0 w-80 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] border-l border-[hsl(var(--border))] dark:border-white/10 z-50 flex flex-col shadow-2xl">
                <div className="flex items-center justify-between px-5 py-4 border-b border-[hsl(var(--border))] dark:border-white/10">
                    <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">Nueva categoría</h2>
                    <button onClick={onClose} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors">
                        <X size={15} />
                    </button>
                </div>
                <div className="flex-1 px-5 py-4 space-y-4">
                    <div>
                        <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">Nombre *</label>
                        <input value={nombre} onChange={e => setNombre(e.target.value)}
                            className="w-full text-sm px-3 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                            placeholder="Ej: Bienvenida nuevos" />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">Descripción</label>
                        <input value={descripcion} onChange={e => setDescripcion(e.target.value)}
                            className="w-full text-sm px-3 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                            placeholder="Opcional" />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-2">Color</label>
                        <div className="flex flex-wrap gap-2">
                            {DEFAULT_COLORS.map(c => (
                                <button key={c} onClick={() => setColor(c)}
                                    className={clsx('size-7 rounded-full border-2 transition-transform', color === c ? 'scale-110 border-[hsl(var(--border))] dark:border-white/60' : 'border-transparent')}
                                    style={{ background: c }} />
                            ))}
                            <input type="color" value={color} onChange={e => setColor(e.target.value)}
                                className="size-7 rounded-full border-2 border-transparent cursor-pointer overflow-hidden" />
                        </div>
                    </div>
                </div>
                <div className="px-5 py-4 border-t border-[hsl(var(--border))] dark:border-white/10 flex gap-2">
                    <button onClick={onClose} className="flex-1 h-9 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">Cancelar</button>
                    <button onClick={submit} disabled={saving || !nombre.trim()}
                        className="flex-1 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-1.5 transition-opacity">
                        {saving && <Loader2 size={13} className="animate-spin" />}Crear
                    </button>
                </div>
            </div>
        </>
    );
}

// ── Send drawer ───────────────────────────────────────────────────────────────

const SEGMENTOS = ['active', 'new', 'staff', 'groups', 'low', 'vip'] as const;
const LABEL_SEGMENTO: Record<string, string> = {
    active: 'Personas activas',
    new: 'Nuevos',
    staff: 'Staff / Pastores',
    groups: 'En grupos',
    low: 'Poco contacto',
    vip: 'Donantes frecuentes',
};

type ModoEnvio = 'individual' | 'campaign';

function SendDrawer({
    open, onClose, plantilla, token, onSent,
}: {
    open: boolean; onClose: () => void;
    plantilla: PlantillaMensaje | null; token: string;
    onSent: (b: BitacoraEnvio) => void;
}) {
    const [modo, setModo] = useState<ModoEnvio>('individual');
    const [search, setSearch] = useState('');
    const [results, setResults] = useState<{ id: string; nombre: string }[]>([]);
    const [searching, setSearching] = useState(false);
    const [destinatario, setDestinatario] = useState<{ id: string; nombre: string } | null>(null);
    const [vars, setVars] = useState<Record<string, string>>({});
    const [sending, setSending] = useState(false);

    // Campaign state
    const [selectedSegments, setSelectedSegments] = useState<string[]>([]);
    const [campaignName, setCampaignName] = useState('');
    const [campResult, setCampResult] = useState<CampaignResult | null>(null);

    useEffect(() => {
        if (!open) {
            setSearch(''); setDestinatario(null); setResults([]); setVars({});
            setModo('individual'); setSelectedSegments([]); setCampaignName(''); setCampResult(null);
        }
    }, [open]);

    useEffect(() => {
        if (!plantilla) return;
        const init: Record<string, string> = {};
        plantilla.variables_requeridas.forEach(v => { init[v] = ''; });
        setVars(init);
        setCampaignName(plantilla.titulo);
    }, [plantilla?.id]); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        if (modo !== 'individual' || search.length < 2) { setResults([]); return; }
        const t = setTimeout(async () => {
            setSearching(true);
            try {
                const data = await apiFetch<{ id: string; nombre_completo?: string; first_name?: string; last_name?: string }[]>(
                    `/crm/personas?q=${encodeURIComponent(search)}&limit=10`, { token }
                );
                setResults((data ?? []).map(p => ({
                    id: p.id,
                    nombre: p.nombre_completo || `${p.first_name ?? ''} ${p.last_name ?? ''}`.trim(),
                })));
            } finally { setSearching(false); }
        }, 300);
        return () => clearTimeout(t);
    }, [search, token, modo]);

    async function send() {
        if (!plantilla) return;
        setSending(true);
        try {
            if (modo === 'campaign') {
                if (selectedSegments.length === 0) return;
                const res = await apiFetch<CampaignResult>(`/crm/resources/plantillas/${plantilla.id}/campaign`, {
                    token, method: 'POST',
                    body: {
                        campaign_name: campaignName || plantilla.titulo,
                        target_segments: selectedSegments,
                        default_variables: vars,
                    },
                    headers: { 'Content-Type': 'application/json' },
                });
                if (res) setCampResult(res);
            } else {
                if (!destinatario) return;
                const res = await apiFetch<BitacoraEnvio>(`/crm/resources/plantillas/${plantilla.id}/enviar`, {
                    token, method: 'POST',
                    body: { destinatario_id: destinatario.id, variables: vars },
                    headers: { 'Content-Type': 'application/json' },
                });
                if (res) { onSent(res); onClose(); }
            }
        } finally { setSending(false); }
    }

    function toggleSegment(seg: string) {
        setSelectedSegments(prev =>
            prev.includes(seg) ? prev.filter(s => s !== seg) : [...prev, seg]
        );
    }

    const previewText = plantilla ? hydrate(plantilla.contenido_texto, vars) : '';

    if (!open || !plantilla) return null;

    // ── Result screen (campaign) ──────────────────────────────────────────────
    if (campResult) {
        return (
            <>
                <div className="fixed inset-0 bg-black/40 z-40" onClick={() => { setCampResult(null); onClose(); }} />
                <div className="fixed right-0 top-0 bottom-0 w-[420px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] border-l border-[hsl(var(--border))] dark:border-white/10 z-50 flex flex-col shadow-2xl">
                    <div className="flex items-center justify-between px-5 py-4 border-b border-[hsl(var(--border))] dark:border-white/10">
                        <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">Campaña enviada</h2>
                        <button onClick={() => { setCampResult(null); onClose(); }} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors">
                            <X size={15} />
                        </button>
                    </div>
                    <div className="flex-1 flex flex-col items-center justify-center px-5 gap-5 text-center">
                        <div className="size-16 rounded-full bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
                            <Megaphone size={28} className="text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <div>
                            <p className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">{campResult.campaign_name}</p>
                            <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">ID: {campResult.external_id}</p>
                        </div>
                        <div className="flex gap-6">
                            <div className="text-center">
                                <p className="text-2xl font-bold text-[hsl(var(--text-primary))] dark:text-white">{campResult.target_count}</p>
                                <p className="text-[10px] font-semibold uppercase text-[hsl(var(--text-secondary))]">Destinatarios</p>
                            </div>
                            <div className="text-center">
                                <p className="text-2xl font-bold text-emerald-600">{campResult.delivered_count}</p>
                                <p className="text-[10px] font-semibold uppercase text-emerald-600">Enviados</p>
                            </div>
                            {campResult.failed_count > 0 && (
                                <div className="text-center">
                                    <p className="text-2xl font-bold text-rose-600">{campResult.failed_count}</p>
                                    <p className="text-[10px] font-semibold uppercase text-rose-600">Fallidos</p>
                                </div>
                            )}
                        </div>
                        <button onClick={() => { setCampResult(null); onClose(); }}
                            className="mt-4 h-9 px-6 rounded-lg bg-[hsl(var(--primary))] text-white text-sm font-medium hover:opacity-90 transition-opacity">
                            Cerrar
                        </button>
                    </div>
                </div>
            </>
        );
    }

    return (
        <>
            <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />
            <div className="fixed right-0 top-0 bottom-0 w-[460px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] border-l border-[hsl(var(--border))] dark:border-white/10 z-50 flex flex-col shadow-2xl">
                <div className="flex items-center justify-between px-5 py-4 border-b border-[hsl(var(--border))] dark:border-white/10">
                    <div>
                        <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">Registrar envío</h2>
                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">{plantilla.titulo}</p>
                    </div>
                    <button onClick={onClose} className="size-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors">
                        <X size={15} />
                    </button>
                </div>

                {/* Mode toggle */}
                <div className="flex border-b border-[hsl(var(--border))] dark:border-white/10">
                    <button onClick={() => setModo('individual')}
                        className={clsx('flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-semibold uppercase tracking-wide transition-colors',
                            modo === 'individual'
                                ? 'text-[hsl(var(--primary))] border-b-2 border-[hsl(var(--primary))]'
                                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]'
                        )}>
                        <Send size={12} />Individual
                    </button>
                    <button onClick={() => setModo('campaign')}
                        className={clsx('flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-semibold uppercase tracking-wide transition-colors',
                            modo === 'campaign'
                                ? 'text-[hsl(var(--primary))] border-b-2 border-[hsl(var(--primary))]'
                                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]'
                        )}>
                        <Users size={12} />Campaña
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
                    {modo === 'individual' ? (
                        <>
                            {/* Destinatario */}
                            <div>
                                <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">Destinatario *</label>
                                {destinatario ? (
                                    <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-500/30">
                                        <span className="text-sm text-emerald-700 dark:text-emerald-400 font-medium">{destinatario.nombre}</span>
                                        <button onClick={() => setDestinatario(null)} className="text-emerald-500 hover:text-emerald-700 dark:hover:text-emerald-300">
                                            <X size={13} />
                                        </button>
                                    </div>
                                ) : (
                                    <div className="relative">
                                        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                                        <input
                                            value={search}
                                            onChange={e => setSearch(e.target.value)}
                                            placeholder="Buscar persona por nombre…"
                                            className="w-full text-sm pl-8 pr-3 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                                        />
                                        {(searching || results.length > 0) && (
                                            <div className="absolute top-full left-0 right-0 mt-1 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] dark:border-white/10 rounded-xl shadow-lg z-10 overflow-hidden">
                                                {searching && <div className="p-3 text-xs text-[hsl(var(--text-secondary))] text-center"><Loader2 size={12} className="animate-spin inline mr-1" />Buscando…</div>}
                                                {results.map(r => (
                                                    <button key={r.id} onClick={() => { setDestinatario(r); setSearch(''); setResults([]); }}
                                                        className="w-full text-left px-4 py-2.5 text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors flex items-center gap-2">
                                                        <ChevronRight size={12} className="text-[hsl(var(--text-secondary))]" />{r.nombre}
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <>
                            {/* Campaign name */}
                            <div>
                                <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-1">Nombre de campaña</label>
                                <input
                                    value={campaignName}
                                    onChange={e => setCampaignName(e.target.value)}
                                    placeholder="Nombre de la campaña"
                                    className="w-full text-sm px-3 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                                />
                            </div>

                            {/* Segments */}
                            <div>
                                <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-2">Segmentos de audiencia</label>
                                <div className="space-y-1.5">
                                    {SEGMENTOS.map(seg => (
                                        <label key={seg}
                                            onClick={() => toggleSegment(seg)}
                                            className={clsx(
                                                'flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors',
                                                selectedSegments.includes(seg)
                                                    ? 'border-[hsl(var(--primary)/0.5)] bg-[hsl(var(--primary)/0.04)]'
                                                    : 'border-[hsl(var(--border))] dark:border-white/10 hover:border-[hsl(var(--border))] dark:hover:border-white/20'
                                            )}
                                        >
                                            <div className={clsx(
                                                'size-4 rounded border-2 flex items-center justify-center transition-colors',
                                                selectedSegments.includes(seg)
                                                    ? 'bg-[hsl(var(--primary))] border-[hsl(var(--primary))]'
                                                    : 'border-[hsl(var(--border))] dark:border-[hsl(var(--border))]'
                                            )}>
                                                {selectedSegments.includes(seg) && <Check size={10} className="text-white" />}
                                            </div>
                                            <span className="text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{LABEL_SEGMENTO[seg]}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}

                    {/* Variables */}
                    {plantilla.variables_requeridas.length > 0 && (
                        <div>
                            <label className="block text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-2">
                                {modo === 'campaign' ? 'Variables (aplican a todos)' : 'Variables'}
                            </label>
                            <div className="space-y-2">
                                {plantilla.variables_requeridas.map(v => (
                                    <div key={v} className="flex items-center gap-2">
                                        <span className="text-xs font-mono text-[hsl(var(--text-secondary))] w-20 shrink-0">{`{{${v}}}`}</span>
                                        <input
                                            value={vars[v] ?? ''}
                                            onChange={e => setVars(p => ({ ...p, [v]: e.target.value }))}
                                            placeholder={v}
                                            className="flex-1 text-xs px-2 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary)/0.4)]"
                                        />
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Preview */}
                    <div>
                        <p className="text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-2">Mensaje hidratado</p>
                        {plantilla?.contenido_html ? (
                            <div className="rounded-xl border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden">
                                <div className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary)/0.05)] dark:bg-[hsl(var(--primary)/0.1)] border-b border-[hsl(var(--border))] dark:border-white/10">
                                    <span className="text-[10px] font-medium text-[hsl(var(--primary))]">Vista previa HTML</span>
                                </div>
                                <iframe
                                    srcDoc={plantilla.contenido_html}
                                    title="Vista previa HTML"
                                    className="w-full h-[300px] bg-white"
                                    sandbox="allow-same-origin"
                                />
                            </div>
                        ) : (
                            <div className="rounded-xl bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 p-3 text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] whitespace-pre-wrap leading-relaxed min-h-[80px]">
                                {previewText}
                            </div>
                        )}
                    </div>
                </div>

                <div className="px-5 py-4 border-t border-[hsl(var(--border))] dark:border-white/10 flex gap-2">
                    <button onClick={onClose} className="flex-1 h-9 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">Cancelar</button>
                    <button onClick={send} disabled={sending || (modo === 'individual' ? !destinatario : selectedSegments.length === 0)}
                        className="flex-1 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-1.5 transition-opacity">
                        {sending && <Loader2 size={13} className="animate-spin" />}
                        {modo === 'campaign' ? <><Users size={13} />Enviar campaña</> : <><Send size={13} />Registrar envío</>}
                    </button>
                </div>
            </div>
        </>
    );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function RecursosPage() {
    const { token } = useAuth();

    const [categorias, setCategorias] = useState<CategoriaRecurso[]>([]);
    const [plantillas, setPlantillas] = useState<PlantillaMensaje[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [reloadKey, setReloadKey] = useState(0);

    const [filterCat, setFilterCat] = useState<string | null>(null);
    const [filterCanal, setFilterCanal] = useState<CanalEnvio | null>(null);
    const [search, setSearch] = useState('');

    const [selected, setSelected] = useState<PlantillaMensaje | null>(null);
    const [editing, setEditing] = useState<PlantillaMensaje | null>(null);

    const [drawerOpen, setDrawerOpen] = useState(false);
    const [catDrawerOpen, setCatDrawerOpen] = useState(false);
    const [sendOpen, setSendOpen] = useState(false);
    const [galleryOpen, setGalleryOpen] = useState(false);

    const fetchAll = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            setError(null);
            const params = new URLSearchParams();
            if (filterCat) params.set('categoria_id', filterCat);
            if (filterCanal) params.set('canal', filterCanal);
            if (search) params.set('q', search);

            const [cats, plts] = await Promise.all([
                apiFetch<CategoriaRecurso[]>('/crm/resources/categorias', { token }),
                apiFetch<PlantillaMensaje[]>(`/crm/resources/plantillas?${params}`, { token }),
            ]);
            setCategorias(cats ?? []);
            setPlantillas(plts ?? []);
        } catch (err) {
            console.error(err);
            setCategorias([]);
            setPlantillas([]);
            setError('No se pudo cargar el banco de recursos');
        } finally {
            setLoading(false);
        }
    }, [token, filterCat, filterCanal, search]);

    useEffect(() => { fetchAll(); }, [fetchAll, reloadKey]);

    function openCreate() { setEditing(null); setDrawerOpen(true); }
    function openEdit(p: PlantillaMensaje) { setEditing(p); setDrawerOpen(true); }

    function onSaved(p: PlantillaMensaje) {
        setPlantillas(prev => {
            const idx = prev.findIndex(x => x.id === p.id);
            if (idx >= 0) { const next = [...prev]; next[idx] = p; return next; }
            return [p, ...prev];
        });
        setSelected(p);
    }

    async function handleDelete(p: PlantillaMensaje) {
        await apiFetch(`/crm/resources/plantillas/${p.id}`, { token, method: 'DELETE' });
        setPlantillas(prev => prev.filter(x => x.id !== p.id));
        if (selected?.id === p.id) setSelected(null);
    }

    function onAdjuntoUploaded(adjunto: RecursoAdjunto) {
        if (!selected) return;
        const updated = { ...selected, adjuntos: [...selected.adjuntos, adjunto] };
        setSelected(updated);
        setPlantillas(prev => prev.map(p => p.id === selected.id ? updated : p));
    }

    function onAdjuntoDeleted(adjuntoId: string) {
        if (!selected) return;
        const updated = { ...selected, adjuntos: (selected.adjuntos ?? []).filter(a => a.id !== adjuntoId) };
        setSelected(updated);
        setPlantillas(prev => prev.map(p => p.id === selected.id ? updated : p));
    }

    function onSent() {
        if (!selected) return;
        const updated = { ...selected, total_envios: (selected.total_envios ?? 0) + 1 };
        setSelected(updated);
        setPlantillas(prev => prev.map(p => p.id === selected.id ? updated : p));
    }

    return (
        <div className="flex h-full overflow-hidden">
            {/* ── Category sidebar ── */}
            <div className="w-52 shrink-0 flex flex-col border-r border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] overflow-y-auto">
                <div className="px-4 pt-5 pb-3">
                    <p className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2">Categorías</p>
                    <button
                        onClick={() => setFilterCat(null)}
                        className={clsx(
                            'w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors mb-1',
                            filterCat === null
                                ? 'bg-[hsl(var(--primary)/0.08)] text-[hsl(var(--primary))] font-medium'
                                : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5',
                        )}
                    >
                        <BookOpen size={14} />Todas
                    </button>
                    {categorias.map(c => (
                        <button
                            key={c.id}
                            onClick={() => setFilterCat(c.id === filterCat ? null : c.id)}
                            className={clsx(
                                'w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors mb-0.5',
                                filterCat === c.id
                                    ? 'bg-[hsl(var(--primary)/0.08)] text-[hsl(var(--primary))] font-medium'
                                    : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5',
                            )}
                        >
                            <CategoriaDot color={c.color_ui_hex} />
                            <span className="truncate">{c.nombre}</span>
                        </button>
                    ))}
                </div>
                <div className="mt-auto px-4 pb-4">
                    <button
                        onClick={() => setCatDrawerOpen(true)}
                        className="w-full flex items-center justify-center gap-1.5 h-8 rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/20 text-xs text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--primary)/0.5)] hover:text-[hsl(var(--primary))] transition-colors"
                    >
                        <Plus size={12} />Nueva categoría
                    </button>
                </div>
            </div>

            {/* ── Main area ── */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Toolbar */}
                <div className="flex items-center gap-3 px-5 py-3 border-b border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] shrink-0">
                    <div className="flex gap-1.5">
                        <button
                            onClick={() => setFilterCanal(null)}
                            className={clsx('h-7 px-3 rounded-full text-xs font-medium transition-all', filterCanal === null ? 'bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))]' : 'bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/20')}
                        >
                            Todos
                        </button>
                        {(['WHATSAPP', 'EMAIL', 'SMS'] as CanalEnvio[]).map(c => {
                            const m = CANAL_META[c]; const Icon = m.icon;
                            return (
                                <button key={c} onClick={() => setFilterCanal(filterCanal === c ? null : c)}
                                    className={clsx('h-7 px-3 rounded-full text-xs font-medium flex items-center gap-1 transition-all',
                                        filterCanal === c ? `${m.bg} ${m.color} ring-1 ring-current` : 'bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/20')}>
                                    <Icon size={11} />{m.label}
                                </button>
                            );
                        })}
                    </div>
                    <div className="flex-1 relative">
                        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        <input
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Buscar plantillas…"
                            className="w-full pl-8 pr-3 h-8 text-xs rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/10 border border-transparent text-[hsl(var(--text-primary))] dark:text-white placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
                        />
                    </div>
                    <button
                        onClick={() => setGalleryOpen(true)}
                        className="h-8 px-3 rounded-lg border border-[hsl(var(--primary))] text-[hsl(var(--primary))] text-xs font-medium flex items-center gap-1.5 hover:bg-[hsl(var(--primary)/0.05)] transition-colors shrink-0"
                    >
                        <BookOpen size={13} />Explorar galería
                    </button>
                    <button
                        onClick={openCreate}
                        className="h-8 px-3 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-medium flex items-center gap-1.5 hover:opacity-90 transition-opacity shrink-0"
                    >
                        <Plus size={13} />Nueva plantilla
                    </button>
                </div>

                {/* Grid */}
                <div className="flex-1 overflow-y-auto p-5">
                    {!loading && error && (
                        <div className="mb-4 flex flex-col gap-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200 md:flex-row md:items-center md:justify-between">
                            <div>
                                <p className="text-[11px] font-bold uppercase tracking-wide">No se pudo cargar el módulo</p>
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
                    {loading && (
                        <div className="flex justify-center py-16"><Loader2 className="animate-spin text-[hsl(var(--text-secondary))]" size={24} /></div>
                    )}
                    {!loading && !error && plantillas.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-20 text-center">
                            <BookOpen size={40} className="text-[hsl(var(--text-secondary))] dark:text-white/20 mb-3" />
                            <p className="text-sm font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Sin plantillas</p>
                            <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">Crea tu primera plantilla con el botón de arriba</p>
                        </div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                        {plantillas.map(p => (
                            <PlantillaCard
                                key={p.id}
                                plantilla={p}
                                selected={selected?.id === p.id}
                                onSelect={() => setSelected(selected?.id === p.id ? null : p)}
                                onEdit={() => openEdit(p)}
                                onDelete={() => handleDelete(p)}
                            />
                        ))}
                    </div>
                </div>
            </div>

            {/* ── Right detail panel ── */}
            {selected && (
                <div className="w-80 xl:w-96 shrink-0 overflow-y-auto">
                    <DetailPanel
                        plantilla={selected}
                        token={token ?? ""}
                        onEdit={() => openEdit(selected)}
                        onSend={() => setSendOpen(true)}
                        onClose={() => setSelected(null)}
                        onAdjuntoDeleted={onAdjuntoDeleted}
                        onAdjuntoUploaded={onAdjuntoUploaded}
                    />
                </div>
            )}

            {/* ── Drawers ── */}
            <PlantillaDrawer
                open={drawerOpen}
                onClose={() => setDrawerOpen(false)}
                categorias={categorias}
                token={token ?? ""}
                editing={editing}
                onSaved={onSaved}
            />
            <CatDrawer
                open={catDrawerOpen}
                onClose={() => setCatDrawerOpen(false)}
                token={token ?? ""}
                onSaved={c => { setCategorias(prev => [...prev, c].sort((a, b) => a.nombre.localeCompare(b.nombre))); }}
            />
            <SendDrawer
                open={sendOpen}
                onClose={() => setSendOpen(false)}
                plantilla={selected}
                token={token ?? ""}
                onSent={onSent}
            />
            <ResourceBankGallery
                open={galleryOpen}
                onClose={() => setGalleryOpen(false)}
                token={token ?? ""}
                onApplied={p => { onSaved(p); setSelected(p); }}
            />
        </div>
    );
}

"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import { apiFetch } from '@/lib/http';
import {
    LayoutDashboard, Church, Plus, Pencil, Trash2, X, Save, Loader2,
    Users, Target,
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const INPUT = "w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-lg px-4 py-1.5 text-sm font-bold outline-none focus:border-[hsl(var(--info)/100%)]/50 focus:ring-4 focus:ring-[hsl(var(--primary))]/5 transition-all text-[hsl(var(--text-primary))] dark:text-white placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-white/20";
const LABEL = "text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]";

interface Ministry {
    id: number;
    name: string;
    description?: string;
    leader_id?: number;
    leader_name?: string;
    personas_count?: number;
}

const EMPTY_FORM = { name: '', description: '', leader_id: '' };

export default function MinisteriosPage() {
    const { token } = useAuth();
    const [ministries, setMinistries] = useState<Ministry[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [viewType, setViewType] = useState<ViewType>('table');

    const [drawerOpen, setDrawerOpen] = useState(false);
    const [editing, setEditing] = useState<Ministry | null>(null);
    const [form, setForm] = useState(EMPTY_FORM);
    const [saving, setSaving] = useState(false);
    const [deleteId, setDeleteId] = useState<number | null>(null);

    const load = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        try {
            setLoading(true);
            const data = await apiFetch<Ministry[]>('/admin/ministerios', { token, cache: 'no-store', signal });
            setMinistries(Array.isArray(data) ? data : []);
        } catch {
            setMinistries([]);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        const controller = new AbortController();
        load(controller.signal);
        return () => controller.abort();
    }, [load]);

    const openCreate = () => {
        setEditing(null);
        setForm(EMPTY_FORM);
        setDrawerOpen(true);
    };

    const openEdit = (m: Ministry) => {
        setEditing(m);
        setForm({ name: m.name, description: m.description ?? '', leader_id: String(m.leader_id ?? '') });
        setDrawerOpen(true);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        setSaving(true);
        const body = {
            name: form.name,
            description: form.description || null,
            leader_id: form.leader_id ? Number(form.leader_id) : null,
        };
        try {
            if (editing) {
                await apiFetch(`/admin/ministerios/${editing.id}`, { method: 'PATCH', token, body });
                toast.success('Ministerio actualizado');
            } else {
                await apiFetch('/admin/ministerios', { method: 'POST', token, body });
                toast.success('Ministerio creado');
            }
            setDrawerOpen(false);
            load();
        } catch {
            toast.error('Error al guardar el ministerio');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!token) return;
        try {
            await apiFetch(`/admin/ministerios/${id}`, { method: 'DELETE', token });
            toast.success('Ministerio eliminado');
            setDeleteId(null);
            load();
        } catch {
            toast.error('Error al eliminar');
        }
    };

    const filtered = ministries.filter(m =>
        m.name.toLowerCase().includes(search.toLowerCase()) ||
        (m.description ?? '').toLowerCase().includes(search.toLowerCase())
    );

    const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
        setForm(f => ({ ...f, [field]: e.target.value }));

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1E1F21] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard, href: '/plataforma/admin' },
                    { label: 'Ministerios', icon: Church },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['table', 'grid', 'list']}
                onSearch={setSearch}
                rightActions={
                    <button onClick={openCreate}
                        className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all">
                        <Plus size={16} strokeWidth={3} /> Nuevo Ministerio
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-3">

                {/* Stats */}
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-3">
                    {[
                        { label: 'Total Ministerios', value: ministries.length, icon: Church, color: 'text-[hsl(var(--primary))]', bg: 'bg-info-soft dark:bg-[hsl(var(--info))]/10' },
                        { label: 'Con Líder Asignado', value: ministries.filter(m => m.leader_id).length, icon: Target, color: 'text-success-text', bg: 'bg-success-soft dark:bg-[hsl(var(--success))]/10' },
                        { label: 'Total Personas', value: ministries.reduce((acc, m) => acc + (m.personas_count ?? 0), 0), icon: Users, color: 'text-[hsl(var(--primary))]', bg: 'bg-info-soft dark:bg-[hsl(var(--info))]/10' },
                    ].map(stat => {
                        const Icon = stat.icon;
                        return (
                            <motion.div key={stat.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3 shadow-sm flex items-center gap-4">
                                <div className={clsx("size-6 rounded-md flex items-center justify-center flex-shrink-0", stat.bg, stat.color)}>
                                    <Icon size={20} />
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">{stat.value}</p>
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{stat.label}</p>
                                </div>
                            </motion.div>
                        );
                    })}
                </div>

                {loading ? (
                    <div className="flex justify-center items-center h-48">
                        <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={32} />
                    </div>
                ) : filtered.length === 0 ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        className="flex flex-col items-center justify-center h-48 gap-4 text-center">
                        <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]">
                            <Church size={36} />
                        </div>
                        <div>
                            <h3 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white">
                                {search ? 'Sin resultados' : 'Sin ministerios registrados'}
                            </h3>
                            <p className="text-sm text-[hsl(var(--text-secondary))] mt-1">
                                {search ? `No se encontró "${search}"` : 'Registra el primer ministerio de la iglesia.'}
                            </p>
                        </div>
                        {!search && (
                            <button onClick={openCreate}
                                className="flex items-center gap-2 px-3 py-3 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--primary))] active:scale-95 transition-all">
                                <Plus size={16} strokeWidth={3} /> Nuevo Ministerio
                            </button>
                        )}
                    </motion.div>
                ) : viewType === 'table' ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-sm overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left min-w-[600px]">
                                <thead className="bg-[hsl(var(--surface-1))] dark:bg-black/20">
                                    <tr>
                                        {['Ministerio', 'Descripción', 'Líder', 'Personas', 'Acciones'].map(h => (
                                            <th key={h} className="py-2.5 px-4 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] border-b border-[hsl(var(--border))] dark:border-white/5">
                                                {h}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtered.map((m, idx) => (
                                        <motion.tr key={m.id}
                                            initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.04 }}
                                            className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.03] transition-colors border-b border-[hsl(var(--border))] dark:border-white/5 last:border-0 group">
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-8 rounded-md bg-info-soft dark:bg-[hsl(var(--info))]/10 flex items-center justify-center text-[hsl(var(--primary))] flex-shrink-0">
                                                        <Church size={14} />
                                                    </div>
                                                    <p className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white">{m.name}</p>
                                                </div>
                                            </td>
                                            <td className="py-3 px-4">
                                                <p className="text-xs text-[hsl(var(--text-secondary))] max-w-xs truncate">{m.description || '—'}</p>
                                            </td>
                                            <td className="py-3 px-4">
                                                {m.leader_name ? (
                                                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                                        <div className="size-4 rounded-full bg-[hsl(var(--primary))] text-white flex items-center justify-center font-semibold">
                                                            {m.leader_name.charAt(0)}
                                                        </div>
                                                        {m.leader_name}
                                                    </span>
                                                ) : (
                                                    <span className="text-[10px] text-[hsl(var(--text-secondary))] dark:text-white/20 font-bold">Sin asignar</span>
                                                )}
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className="text-xs font-semibold text-[hsl(var(--text-secondary))]">{m.personas_count ?? 0}</span>
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button onClick={() => openEdit(m)}
                                                        className="p-2 hover:bg-info-soft dark:hover:bg-[hsl(var(--info))]/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all">
                                                        <Pencil size={14} />
                                                    </button>
                                                    {deleteId === m.id ? (
                                                        <div className="flex items-center gap-1">
                                                            <button onClick={() => handleDelete(m.id)}
                                                                className="px-2 py-1 rounded-lg font-semibold bg-[hsl(var(--danger-muted))] dark:bg-[hsl(var(--danger))]/10 text-danger-text hover:bg-[hsl(var(--danger))] hover:text-white transition-all">
                                                                Confirmar
                                                            </button>
                                                            <button onClick={() => setDeleteId(null)} className="p-1.5 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-lg text-[hsl(var(--text-secondary))]"><X size={12} /></button>
                                                        </div>
                                                    ) : (
                                                        <button onClick={() => setDeleteId(m.id)}
                                                            className="p-2 hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-danger-text transition-all">
                                                            <Trash2 size={14} />
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                        </motion.tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </motion.div>
                ) : viewType === 'grid' ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        {filtered.map((m, idx) => (
                            <motion.div key={m.id}
                                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.06 }}
                                className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3 shadow-sm hover:border-[hsl(var(--info)/100%)]/20 transition-all group">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="size-6 rounded-md bg-info-soft dark:bg-[hsl(var(--info))]/10 flex items-center justify-center text-[hsl(var(--primary))]">
                                        <Church size={20} />
                                    </div>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={() => openEdit(m)} className="p-2 hover:bg-info-soft dark:hover:bg-[hsl(var(--info))]/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all"><Pencil size={14} /></button>
                                        <button onClick={() => setDeleteId(m.id)} className="p-2 hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-danger-text transition-all"><Trash2 size={14} /></button>
                                    </div>
                                </div>
                                <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white mb-1">{m.name}</h3>
                                <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed line-clamp-2">{m.description || 'Sin descripción registrada.'}</p>
                                <div className="flex items-center gap-3 mt-4 pt-4 border-t border-[hsl(var(--border))] dark:border-white/5">
                                    <div className="flex items-center gap-1.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">
                                        <Users size={12} /> {m.personas_count ?? 0} personas
                                    </div>
                                    {m.leader_name && (
                                        <div className="flex items-center gap-1.5 font-semibold text-[hsl(var(--primary))] uppercase tracking-wider">
                                            <div className="size-4 rounded-full bg-[hsl(var(--primary))] text-white flex items-center justify-center text-[7px]">{m.leader_name.charAt(0)}</div>
                                            {m.leader_name}
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        ))}
                    </div>
                ) : (
                    <div className="max-w-3xl mx-auto space-y-2">
                        {filtered.map((m, idx) => (
                            <motion.div key={m.id}
                                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.04 }}
                                className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-md border border-[hsl(var(--border))] dark:border-white/5 p-4 flex items-center gap-4 group hover:border-[hsl(var(--info)/100%)]/20 transition-all">
                                <div className="size-10 rounded-md bg-info-soft dark:bg-[hsl(var(--info))]/10 flex items-center justify-center text-[hsl(var(--primary))] flex-shrink-0"><Church size={18} /></div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">{m.name}</p>
                                    <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-0.5 truncate">{m.description || 'Sin descripción'}</p>
                                </div>
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onClick={() => openEdit(m)} className="p-2 hover:bg-info-soft dark:hover:bg-[hsl(var(--info))]/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all"><Pencil size={14} /></button>
                                    <button onClick={() => setDeleteId(m.id)} className="p-2 hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-danger-text transition-all"><Trash2 size={14} /></button>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                )}
            </main>

            {/* Drawer */}
            <AnimatePresence>
                {drawerOpen && (
                    <>
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-x-0 bottom-0 top-10 z-[90] bg-black/30 backdrop-blur-sm"
                            onClick={() => setDrawerOpen(false)} />
                        <motion.aside
                            initial={{ x: '100%', opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                            exit={{ x: '100%', opacity: 0 }}
                            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
                            className="fixed top-10 right-0 h-[calc(100vh-2.5rem)] z-[100] w-full max-w-md bg-[hsl(var(--bg-primary))] dark:bg-[#1E1F21] shadow-2xl border-l border-[hsl(var(--border))] dark:border-white/10 flex flex-col">

                            <div className="flex items-center justify-between px-3 py-1.5 border-b border-[hsl(var(--border))] dark:border-white/5 flex-shrink-0">
                                <div className="flex items-center gap-3">
                                    <div className="size-8 rounded-md bg-info-soft dark:bg-[hsl(var(--info))]/10 flex items-center justify-center text-[hsl(var(--primary))]">
                                        <Church size={16} />
                                    </div>
                                    <div>
                                        <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{editing ? 'Editar' : 'Nuevo'} Ministerio</p>
                                        <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">{editing ? editing.name : 'Sin nombre'}</h3>
                                    </div>
                                </div>
                                <button onClick={() => setDrawerOpen(false)} className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] transition-all">
                                    <X size={18} />
                                </button>
                            </div>

                            <form onSubmit={handleSave} className="flex-1 overflow-y-auto p-3 space-y-5">
                                <div className="space-y-2">
                                    <label className={LABEL}>Nombre del Ministerio *</label>
                                    <input required type="text" placeholder="Ej: Ministerio de Alabanza" value={form.name} onChange={set('name')} className={INPUT} />
                                </div>
                                <div className="space-y-2">
                                    <label className={LABEL}>Descripción</label>
                                    <textarea rows={4} placeholder="Propósito y visión del ministerio..." value={form.description} onChange={set('description')}
                                        className={clsx(INPUT, "resize-none leading-relaxed")} />
                                </div>
                                <div className="space-y-2">
                                    <label className={LABEL}>ID del Líder (Persona)</label>
                                    <input type="number" min={1} placeholder="ID del persona líder" value={form.leader_id} onChange={set('leader_id')} className={INPUT} />
                                    <p className="text-[10px] text-[hsl(var(--text-secondary))] ml-4">Ingresa el ID del persona que liderará este ministerio.</p>
                                </div>
                            </form>

                            <div className="flex items-center gap-3 px-3 py-1.5 border-t border-[hsl(var(--border))] dark:border-white/5 flex-shrink-0">
                                <button type="button" onClick={() => setDrawerOpen(false)}
                                    className="flex-1 py-3 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleSave} disabled={saving}
                                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-50">
                                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                    {saving ? 'Guardando...' : (editing ? 'Actualizar' : 'Crear')}
                                </button>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            {/* Delete confirm global (grid view) */}
            <AnimatePresence>
                {deleteId !== null && !drawerOpen && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[110] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
                        <motion.div initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.92, opacity: 0 }}
                            className="bg-[hsl(var(--bg-primary))] dark:bg-[#1E1F21] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 shadow-2xl max-w-sm w-full">
                            <div className="size-7 bg-danger-soft dark:bg-[hsl(var(--danger))]/10 rounded-md flex items-center justify-center text-danger-text mb-4">
                                <Trash2 size={20} />
                            </div>
                            <h3 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white">¿Eliminar ministerio?</h3>
                            <p className="text-sm text-[hsl(var(--text-secondary))] mt-1 mb-5">Esta acción no se puede deshacer.</p>
                            <div className="flex gap-3">
                                <button onClick={() => setDeleteId(null)} className="flex-1 py-3 rounded-md border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all">
                                    Cancelar
                                </button>
                                <button onClick={() => handleDelete(deleteId!)}
                                    className="flex-1 py-3 rounded-md bg-[hsl(var(--danger))] text-white text-[11px] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--danger))] active:scale-95 transition-all shadow-lg shadow-[hsl(var(--danger)/20%)]">
                                    Eliminar
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

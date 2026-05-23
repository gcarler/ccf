"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import { apiFetch } from '@/lib/http';
import {
    LayoutDashboard, Home, Plus, Pencil, Trash2, X, Save, Loader2,
    Phone, MapPin, Calendar, Users,
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const INPUT = "w-full bg-slate-50 dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-lg px-4 py-1.5 text-sm font-bold outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/5 transition-all text-slate-900 dark:text-white placeholder:text-slate-300 dark:placeholder:text-white/20";
const LABEL = "text-[10px] font-semibold uppercase tracking-wide text-slate-400";

interface Family {
    id: number;
    name: string;
    address?: string;
    phone?: string;
    first_contact_date?: string;
    members_count?: number;
}

const EMPTY_FORM = { name: '', address: '', phone: '', first_contact_date: '' };

function formatDate(date?: string) {
    if (!date) return '—';
    return new Date(date).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function FamiliasPage() {
    const { token } = useAuth();
    const [families, setFamilies] = useState<Family[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [viewType, setViewType] = useState<ViewType>('table');

    const [drawerOpen, setDrawerOpen] = useState(false);
    const [editing, setEditing] = useState<Family | null>(null);
    const [form, setForm] = useState(EMPTY_FORM);
    const [saving, setSaving] = useState(false);
    const [deleteId, setDeleteId] = useState<number | null>(null);

    const load = useCallback(async () => {
        if (!token) return;
        try {
            setLoading(true);
            const data = await apiFetch<Family[]>('/crm/families', { token, cache: 'no-store' });
            setFamilies(Array.isArray(data) ? data : []);
        } catch {
            setFamilies([]);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => { load(); }, [load]);

    const openCreate = () => {
        setEditing(null);
        setForm(EMPTY_FORM);
        setDrawerOpen(true);
    };

    const openEdit = (f: Family) => {
        setEditing(f);
        setForm({
            name: f.name,
            address: f.address ?? '',
            phone: f.phone ?? '',
            first_contact_date: f.first_contact_date ? f.first_contact_date.slice(0, 10) : '',
        });
        setDrawerOpen(true);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        setSaving(true);
        const body = {
            name: form.name,
            address: form.address || null,
            phone: form.phone || null,
            first_contact_date: form.first_contact_date || null,
        };
        try {
            if (editing) {
                await apiFetch(`/crm/families/${editing.id}`, { method: 'PATCH', token, body });
                toast.success('Familia actualizada');
            } else {
                await apiFetch('/crm/families', { method: 'POST', token, body });
                toast.success('Familia registrada');
            }
            setDrawerOpen(false);
            load();
        } catch {
            toast.error('Error al guardar la familia');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!token) return;
        try {
            await apiFetch(`/crm/families/${id}`, { method: 'DELETE', token });
            toast.success('Familia eliminada');
            setDeleteId(null);
            load();
        } catch {
            toast.error('Error al eliminar');
        }
    };

    const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
        setForm(f => ({ ...f, [field]: e.target.value }));

    const filtered = families.filter(f =>
        f.name.toLowerCase().includes(search.toLowerCase()) ||
        (f.phone ?? '').includes(search) ||
        (f.address ?? '').toLowerCase().includes(search.toLowerCase())
    );

    const thisMonth = families.filter(f => {
        if (!f.first_contact_date) return false;
        const d = new Date(f.first_contact_date);
        const now = new Date();
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    }).length;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard, href: '/admin' },
                    { label: 'Familias', icon: Home },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['table', 'grid', 'list']}
                onSearch={setSearch}
                rightActions={
                    <button onClick={openCreate}
                        className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                        <Plus size={16} strokeWidth={3} /> Nueva Familia
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-3">

                {/* Stats */}
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-3">
                    {[
                        { label: 'Total Familias', value: families.length, icon: Home, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-500/10' },
                        { label: 'Primer Contacto Este Mes', value: thisMonth, icon: Calendar, color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
                        { label: 'Total Integrantes', value: families.reduce((acc, f) => acc + (f.members_count ?? 0), 0), icon: Users, color: 'text-violet-600', bg: 'bg-violet-50 dark:bg-violet-500/10' },
                    ].map(stat => {
                        const Icon = stat.icon;
                        return (
                            <motion.div key={stat.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 shadow-sm flex items-center gap-4">
                                <div className={clsx("size-6 rounded-md flex items-center justify-center flex-shrink-0", stat.bg, stat.color)}>
                                    <Icon size={20} />
                                </div>
                                <div>
                                    <p className="text-lg font-black text-slate-900 dark:text-white tracking-tighter">{stat.value}</p>
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{stat.label}</p>
                                </div>
                            </motion.div>
                        );
                    })}
                </div>

                {loading ? (
                    <div className="flex justify-center items-center h-48">
                        <Loader2 className="animate-spin text-blue-600" size={32} />
                    </div>
                ) : filtered.length === 0 ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        className="flex flex-col items-center justify-center h-48 gap-4 text-center">
                        <div className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                            <Home size={36} />
                        </div>
                        <div>
                            <h3 className="text-base font-black text-slate-800 dark:text-white">
                                {search ? 'Sin resultados' : 'Sin familias registradas'}
                            </h3>
                            <p className="text-sm text-slate-400 mt-1">
                                {search ? `No se encontró "${search}"` : 'Registra la primera familia de la comunidad.'}
                            </p>
                        </div>
                        {!search && (
                            <button onClick={openCreate}
                                className="flex items-center gap-2 px-3 py-3 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg hover:bg-blue-700 active:scale-95 transition-all">
                                <Plus size={16} strokeWidth={3} /> Nueva Familia
                            </button>
                        )}
                    </motion.div>
                ) : viewType === 'table' ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left min-w-[700px]">
                                <thead className="bg-slate-50 dark:bg-black/20">
                                    <tr>
                                        {['Familia', 'Teléfono', 'Dirección', 'Primer Contacto', 'Integrantes', 'Acciones'].map(h => (
                                            <th key={h} className="py-2.5 px-4 text-[10px] font-semibold uppercase tracking-wide text-slate-400 border-b border-slate-100 dark:border-white/5">{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtered.map((fam, idx) => (
                                        <motion.tr key={fam.id}
                                            initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.04 }}
                                            className="hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors border-b border-slate-100 dark:border-white/5 last:border-0 group">
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-8 rounded-md bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center font-black text-sm flex-shrink-0">
                                                        {fam.name.charAt(0).toUpperCase()}
                                                    </div>
                                                    <p className="text-xs font-semibold text-slate-800 dark:text-white">Familia {fam.name}</p>
                                                </div>
                                            </td>
                                            <td className="py-3 px-4">
                                                {fam.phone ? (
                                                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                                                        <Phone size={11} className="text-slate-300" /> {fam.phone}
                                                    </div>
                                                ) : <span className="text-[10px] text-slate-300 dark:text-white/20 font-bold">—</span>}
                                            </td>
                                            <td className="py-3 px-4">
                                                {fam.address ? (
                                                    <div className="flex items-center gap-1.5 text-xs text-slate-500 max-w-[180px] truncate">
                                                        <MapPin size={11} className="text-slate-300 flex-shrink-0" /> {fam.address}
                                                    </div>
                                                ) : <span className="text-[10px] text-slate-300 dark:text-white/20 font-bold">—</span>}
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className="text-xs font-bold text-slate-500">{formatDate(fam.first_contact_date)}</span>
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className="text-xs font-semibold text-slate-500">{fam.members_count ?? 0}</span>
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button onClick={() => openEdit(fam)} className="p-2 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-md text-slate-400 hover:text-blue-600 transition-all"><Pencil size={14} /></button>
                                                    {deleteId === fam.id ? (
                                                        <div className="flex items-center gap-1">
                                                            <button onClick={() => handleDelete(fam.id)} className="px-2 py-1 rounded-lg font-semibold bg-rose-100 dark:bg-rose-500/10 text-rose-600 hover:bg-rose-600 hover:text-white transition-all">Confirmar</button>
                                                            <button onClick={() => setDeleteId(null)} className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-400"><X size={12} /></button>
                                                        </div>
                                                    ) : (
                                                        <button onClick={() => setDeleteId(fam.id)} className="p-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-md text-slate-400 hover:text-rose-600 transition-all"><Trash2 size={14} /></button>
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
                        {filtered.map((fam, idx) => (
                            <motion.div key={fam.id}
                                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.06 }}
                                className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 shadow-sm hover:border-blue-500/20 transition-all group">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="size-7 rounded-md bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center font-black text-xl">
                                        {fam.name.charAt(0).toUpperCase()}
                                    </div>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={() => openEdit(fam)} className="p-2 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-md text-slate-400 hover:text-blue-600 transition-all"><Pencil size={14} /></button>
                                        <button onClick={() => setDeleteId(fam.id)} className="p-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-md text-slate-400 hover:text-rose-600 transition-all"><Trash2 size={14} /></button>
                                    </div>
                                </div>
                                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Familia {fam.name}</h3>
                                <div className="space-y-2 mt-3">
                                    {fam.phone && (
                                        <div className="flex items-center gap-2 text-[11px] text-slate-400">
                                            <Phone size={12} /> {fam.phone}
                                        </div>
                                    )}
                                    {fam.address && (
                                        <div className="flex items-center gap-2 text-[11px] text-slate-400">
                                            <MapPin size={12} /> <span className="truncate">{fam.address}</span>
                                        </div>
                                    )}
                                    {fam.first_contact_date && (
                                        <div className="flex items-center gap-2 text-[11px] text-slate-400">
                                            <Calendar size={12} /> {formatDate(fam.first_contact_date)}
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center gap-1.5 mt-4 pt-4 border-t border-slate-100 dark:border-white/5 font-semibold text-slate-400 uppercase tracking-wider">
                                    <Users size={12} /> {fam.members_count ?? 0} integrantes
                                </div>
                            </motion.div>
                        ))}
                    </div>
                ) : (
                    <div className="max-w-3xl mx-auto space-y-2">
                        {filtered.map((fam, idx) => (
                            <motion.div key={fam.id}
                                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.04 }}
                                className="bg-white dark:bg-[#15171c] rounded-md border border-slate-200 dark:border-white/5 p-4 flex items-center gap-4 group hover:border-blue-500/20 transition-all">
                                <div className="size-10 rounded-md bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center font-black text-base flex-shrink-0">
                                    {fam.name.charAt(0).toUpperCase()}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-slate-800 dark:text-white">Familia {fam.name}</p>
                                    <p className="text-[10px] text-slate-400 mt-0.5 truncate">{fam.address ?? fam.phone ?? 'Sin datos de contacto'}</p>
                                </div>
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onClick={() => openEdit(fam)} className="p-2 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-md text-slate-400 hover:text-blue-600 transition-all"><Pencil size={14} /></button>
                                    <button onClick={() => setDeleteId(fam.id)} className="p-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-md text-slate-400 hover:text-rose-600 transition-all"><Trash2 size={14} /></button>
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
                            className="fixed inset-0 z-[90] bg-black/30 backdrop-blur-sm"
                            onClick={() => setDrawerOpen(false)} />
                        <motion.aside
                            initial={{ x: '100%', opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                            exit={{ x: '100%', opacity: 0 }}
                            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
                            className="fixed top-0 right-0 h-screen z-[100] w-full max-w-md bg-white dark:bg-[#1E1F21] shadow-2xl border-l border-slate-200 dark:border-white/10 flex flex-col">

                            <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-100 dark:border-white/5 flex-shrink-0">
                                <div className="flex items-center gap-3">
                                    <div className="size-8 rounded-md bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-600"><Home size={16} /></div>
                                    <div>
                                        <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">{editing ? 'Editar' : 'Nueva'} Familia</p>
                                        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{editing ? `Familia ${editing.name}` : 'Sin nombre'}</h3>
                                    </div>
                                </div>
                                <button onClick={() => setDrawerOpen(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md text-slate-400 transition-all"><X size={18} /></button>
                            </div>

                            <form onSubmit={handleSave} className="flex-1 overflow-y-auto p-3 space-y-5">
                                <div className="space-y-2">
                                    <label className={LABEL}>Apellido de Familia *</label>
                                    <input required type="text" placeholder="Ej: González" value={form.name} onChange={set('name')} className={INPUT} />
                                </div>
                                <div className="space-y-2">
                                    <label className={LABEL}>Teléfono</label>
                                    <input type="tel" placeholder="+1 (555) 000-0000" value={form.phone} onChange={set('phone')} className={INPUT} />
                                </div>
                                <div className="space-y-2">
                                    <label className={LABEL}>Dirección</label>
                                    <input type="text" placeholder="Calle, ciudad, país" value={form.address} onChange={set('address')} className={INPUT} />
                                </div>
                                <div className="space-y-2">
                                    <label className={LABEL}>Fecha de Primer Contacto</label>
                                    <input type="date" value={form.first_contact_date} onChange={set('first_contact_date')} className={INPUT} />
                                </div>
                            </form>

                            <div className="flex items-center gap-3 px-3 py-1.5 border-t border-slate-100 dark:border-white/5 flex-shrink-0">
                                <button type="button" onClick={() => setDrawerOpen(false)}
                                    className="flex-1 py-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400 hover:text-slate-700 dark:hover:text-white transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleSave} disabled={saving}
                                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-50">
                                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                    {saving ? 'Guardando...' : (editing ? 'Actualizar' : 'Registrar')}
                                </button>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            <AnimatePresence>
                {deleteId !== null && !drawerOpen && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[110] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
                        <motion.div initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.92, opacity: 0 }}
                            className="bg-white dark:bg-[#1E1F21] rounded-lg border border-slate-200 dark:border-white/10 p-3 shadow-2xl max-w-sm w-full">
                            <div className="size-7 bg-rose-50 dark:bg-rose-500/10 rounded-md flex items-center justify-center text-rose-600 mb-4"><Trash2 size={20} /></div>
                            <h3 className="text-base font-black text-slate-900 dark:text-white">¿Eliminar familia?</h3>
                            <p className="text-sm text-slate-400 mt-1 mb-5">Esta acción eliminará el registro permanentemente.</p>
                            <div className="flex gap-3">
                                <button onClick={() => setDeleteId(null)} className="flex-1 py-3 rounded-md border border-slate-200 dark:border-white/10 text-[11px] font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 transition-all">Cancelar</button>
                                <button onClick={() => handleDelete(deleteId!)} className="flex-1 py-3 rounded-md bg-rose-600 text-white text-[11px] font-semibold uppercase tracking-wide hover:bg-rose-700 active:scale-95 transition-all shadow-lg shadow-rose-500/20">Eliminar</button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

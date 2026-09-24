"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import ConfirmActionDrawer from '@/components/ConfirmActionDrawer';
import type { ViewType } from '@/components/ViewSwitcher';
import { apiFetch } from '@/lib/http';
import { formatDate } from '@/lib/format';
import {
    LayoutDashboard, Home, Plus, Pencil, Trash2, X, Save, Loader2,
    Phone, MapPin, Calendar, Users,
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const INPUT = "w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg px-4 py-1.5 text-sm font-bold outline-none focus:border-[hsl(var(--primary))] focus:ring-4 focus:ring-[hsl(var(--primary)/0.1)] transition-all text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]";
const LABEL = "text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]";

interface Family {
    id: number;
    name: string;
    address?: string;
    phone?: string;
    first_contact_date?: string;
    personas_count?: number;
}

const EMPTY_FORM = { name: '', address: '', phone: '', first_contact_date: '' };

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

    const load = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        try {
            setLoading(true);
            const data = await apiFetch<Family[]>('/crm/families', { token, cache: 'no-store', signal });
            setFamilies(Array.isArray(data) ? data : []);
        } catch {
            setFamilies([]);
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
        <div className="flex flex-col h-full bg-[hsl(var(--background))] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard, href: '/plataforma/admin' },
                    { label: 'Familias', icon: Home },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['table', 'grid', 'list']}
                onSearch={setSearch}
                rightActions={
                    <button onClick={openCreate}
                        className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-xs font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary)/0.2)] hover:bg-[hsl(var(--primary)/0.9)] active:scale-95 transition-all">
                        <Plus size={16} strokeWidth={3} /> Nueva Familia
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-3">

                {/* Stats */}
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-3">
                    {[
                        { label: 'Total Familias', value: families.length, icon: Home, color: 'text-[hsl(var(--primary))]', bg: 'bg-[hsl(var(--primary)/0.1)]' },
                        { label: 'Primer Contacto Este Mes', value: thisMonth, icon: Calendar, color: 'text-[hsl(var(--success))]', bg: 'bg-[hsl(var(--success)/0.15)]' },
                        { label: 'Total Integrantes', value: families.reduce((acc, f) => acc + (f.personas_count ?? 0), 0), icon: Users, color: 'text-[hsl(var(--primary))]', bg: 'bg-[hsl(var(--primary)/0.1)]' },
                    ].map(stat => {
                        const Icon = stat.icon;
                        return (
                            <motion.div key={stat.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                                className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] p-3 shadow-sm flex items-center gap-4">
                                <div className={clsx("size-6 rounded-md flex items-center justify-center flex-shrink-0", stat.bg, stat.color)}>
                                    <Icon size={20} />
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-[hsl(var(--foreground))] tracking-tighter">{stat.value}</p>
                                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{stat.label}</p>
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
                        <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] flex items-center justify-center text-[hsl(var(--muted-foreground))]">
                            <Home size={36} />
                        </div>
                        <div>
                            <h3 className="text-base font-bold text-[hsl(var(--foreground))]">
                                {search ? 'Sin resultados' : 'Sin familias registradas'}
                            </h3>
                            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
                                {search ? `No se encontró "${search}"` : 'Registra la primera familia de la comunidad.'}
                            </p>
                        </div>
                        {!search && (
                            <button onClick={openCreate}
                                className="flex items-center gap-2 px-3 py-3 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-xs font-semibold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--primary)/0.9)] active:scale-95 transition-all">
                                <Plus size={16} strokeWidth={3} /> Nueva Familia
                            </button>
                        )}
                    </motion.div>
                ) : viewType === 'table' ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] shadow-sm overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left min-w-[700px]">
                                <thead className="bg-[hsl(var(--surface-2))]">
                                    <tr>
                                        {['Familia', 'Teléfono', 'Dirección', 'Primer Contacto', 'Integrantes', 'Acciones'].map(h => (
                                            <th key={h} className="py-2.5 px-4 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] border-b border-[hsl(var(--border))]">{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtered.map((fam, idx) => (
                                        <motion.tr key={fam.id}
                                            initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.04 }}
                                            className="hover:bg-[hsl(var(--surface-2)/0.5)] transition-colors border-b border-[hsl(var(--border))] last:border-0 group">
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-8 rounded-md bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] flex items-center justify-center font-black text-sm flex-shrink-0">
                                                        {fam.name.charAt(0).toUpperCase()}
                                                    </div>
                                                    <p className="text-xs font-semibold text-[hsl(var(--foreground))]">Familia {fam.name}</p>
                                                </div>
                                            </td>
                                            <td className="py-3 px-4">
                                                {fam.phone ? (
                                                    <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                                                        <Phone size={11} className="text-[hsl(var(--muted-foreground))]" /> {fam.phone}
                                                    </div>
                                                ) : <span className="text-2xs text-[hsl(var(--muted-foreground))] font-bold">—</span>}
                                            </td>
                                            <td className="py-3 px-4">
                                                {fam.address ? (
                                                    <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))] max-w-[180px] truncate">
                                                        <MapPin size={11} className="text-[hsl(var(--muted-foreground))] flex-shrink-0" /> {fam.address}
                                                    </div>
                                                ) : <span className="text-2xs text-[hsl(var(--muted-foreground))] font-bold">—</span>}
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className="text-xs font-bold text-[hsl(var(--muted-foreground))]">{formatDate(fam.first_contact_date, { locale: 'es-ES', day: 'numeric' })}</span>
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className="text-xs font-semibold text-[hsl(var(--muted-foreground))]">{fam.personas_count ?? 0}</span>
                                            </td>
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button onClick={() => openEdit(fam)} className="p-2 hover:bg-[hsl(var(--primary)/0.1)] rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] transition-all"><Pencil size={14} /></button>
                                                    {deleteId === fam.id ? (
                                                        <div className="flex items-center gap-1">
                                                            <button onClick={() => handleDelete(fam.id)} className="px-2 py-1 rounded-lg font-semibold bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive))] hover:text-[hsl(var(--destructive-foreground))] transition-all">Confirmar</button>
                                                            <button onClick={() => setDeleteId(null)} className="p-1.5 hover:bg-[hsl(var(--surface-2))] rounded-lg text-[hsl(var(--muted-foreground))]"><X size={12} /></button>
                                                        </div>
                                                    ) : (
                                                        <button onClick={() => setDeleteId(fam.id)} className="p-2 hover:bg-[hsl(var(--destructive)/0.15)] rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] transition-all"><Trash2 size={14} /></button>
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
                                className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] p-3 shadow-sm hover:border-[hsl(var(--primary)/0.5)] transition-all group">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="size-7 rounded-md bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] flex items-center justify-center font-black text-xl">
                                        {fam.name.charAt(0).toUpperCase()}
                                    </div>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={() => openEdit(fam)} className="p-2 hover:bg-[hsl(var(--primary)/0.1)] rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] transition-all"><Pencil size={14} /></button>
                                        <button onClick={() => setDeleteId(fam.id)} className="p-2 hover:bg-[hsl(var(--destructive)/0.15)] rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] transition-all"><Trash2 size={14} /></button>
                                    </div>
                                </div>
                                <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">Familia {fam.name}</h3>
                                <div className="space-y-2 mt-3">
                                    {fam.phone && (
                                        <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                                            <Phone size={12} /> {fam.phone}
                                        </div>
                                    )}
                                    {fam.address && (
                                        <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                                            <MapPin size={12} /> <span className="truncate">{fam.address}</span>
                                        </div>
                                    )}
                                    {fam.first_contact_date && (
                                        <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                                            <Calendar size={12} /> {formatDate(fam.first_contact_date, { locale: 'es-ES', day: 'numeric' })}
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center gap-1.5 mt-4 pt-4 border-t border-[hsl(var(--border))] font-semibold text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
                                    <Users size={12} /> {fam.personas_count ?? 0} integrantes
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
                                className="bg-[hsl(var(--surface-1))] rounded-md border border-[hsl(var(--border))] p-4 flex items-center gap-4 group hover:border-[hsl(var(--primary)/0.5)] transition-all">
                                <div className="size-10 rounded-md bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] flex items-center justify-center font-black text-base flex-shrink-0">
                                    {fam.name.charAt(0).toUpperCase()}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-[hsl(var(--foreground))]">Familia {fam.name}</p>
                                    <p className="text-2xs text-[hsl(var(--muted-foreground))] mt-0.5 truncate">{fam.address ?? fam.phone ?? 'Sin datos de contacto'}</p>
                                </div>
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onClick={() => openEdit(fam)} className="p-2 hover:bg-[hsl(var(--primary)/0.1)] rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] transition-all"><Pencil size={14} /></button>
                                    <button onClick={() => setDeleteId(fam.id)} className="p-2 hover:bg-[hsl(var(--destructive)/0.15)] rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] transition-all"><Trash2 size={14} /></button>
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
                            className="fixed inset-x-0 bottom-0 top-10 z-[90] bg-[hsl(var(--background)/0.7)] backdrop-blur-sm"
                            onClick={() => setDrawerOpen(false)} />
                        <motion.aside
                            initial={{ x: '100%', opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                            exit={{ x: '100%', opacity: 0 }}
                            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
                            className="fixed top-10 right-0 h-[calc(100vh-2.5rem)] z-[100] w-full max-w-md bg-[hsl(var(--surface-1))] shadow-2xl border-l border-[hsl(var(--border))] flex flex-col">

                            <div className="flex items-center justify-between px-3 py-1.5 border-b border-[hsl(var(--border))] flex-shrink-0">
                                <div className="flex items-center gap-3">
                                    <div className="size-8 rounded-md bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))]"><Home size={16} /></div>
                                    <div>
                                        <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{editing ? 'Editar' : 'Nueva'} Familia</p>
                                        <h3 className="text-sm font-semibold text-[hsl(var(--foreground))]">{editing ? `Familia ${editing.name}` : 'Sin nombre'}</h3>
                                    </div>
                                </div>
                                <button onClick={() => setDrawerOpen(false)} className="p-2 hover:bg-[hsl(var(--surface-2))] rounded-md text-[hsl(var(--muted-foreground))] transition-all"><X size={18} /></button>
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

                            <div className="flex items-center gap-3 px-3 py-1.5 border-t border-[hsl(var(--border))] flex-shrink-0">
                                <button type="button" onClick={() => setDrawerOpen(false)}
                                    className="flex-1 py-3 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleSave} disabled={saving}
                                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-xs font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary)/0.2)] hover:bg-[hsl(var(--primary)/0.9)] active:scale-95 transition-all disabled:opacity-50">
                                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                    {saving ? 'Guardando...' : (editing ? 'Actualizar' : 'Registrar')}
                                </button>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            <ConfirmActionDrawer
                action={deleteId !== null ? {
                    title: '¿Eliminar familia?',
                    description: 'Esta acción eliminará el registro permanentemente.',
                    destructive: true,
                    confirmLabel: 'Eliminar',
                    onConfirm: () => handleDelete(deleteId),
                } : null}
                onClose={() => setDeleteId(null)}
            />
        </div>
    );
}

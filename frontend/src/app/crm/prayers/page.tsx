"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { 
    Heart,
    Plus,
    Users,
    Sparkles,
    Flame,
    Quote,
    Stethoscope,
    Briefcase,
    Home,
    Loader2,
    Send
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import clsx from 'clsx';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';
import CrmShell from '@/components/crm/CrmShell';

const PRAYER_STATUS_OPTIONS: StatusOption[] = [
    { label: 'ACTIVA', value: 'active', color: 'bg-rose-500', text: 'text-rose-600', bg: 'bg-rose-50' },
    { label: 'CONTESTADA', value: 'answered', color: 'bg-emerald-500', text: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'EN PROCESO', value: 'praying', color: 'bg-blue-500', text: 'text-blue-600', bg: 'bg-blue-50' },
];

const CATEGORIES = ['Salud', 'Familia', 'Trabajo', 'Espiritual', 'Finanzas', 'Otra'];
const PRAYER_PROGRESS: Record<string, number> = { pending: 20, active: 40, praying: 70, answered: 100 };

export default function PrayerSupportCenter() {
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();
    const [requests, setRequests] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedRequest, setSelectedRequest] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isCreateDrawerOpen, setIsCreateDrawerOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [newPrayer, setNewPrayer] = useState({ name: '', request: '', category: 'General', is_urgent: false });
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_prayers_view', 'table'));
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('crm_prayers_wiki_notes', {
        title: 'Wiki de intercesion CRM',
    });

    const fetchRequests = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/crm/prayer-requests', { token });
            if (Array.isArray(data)) {
                setRequests(data.map((r: any) => ({
                    id: r.id,
                    name: r.requester_name || r.name || 'Anónimo',
                    request: r.request_text || r.request,
                    category: r.category || 'General',
                    status: r.status || (r.is_answered ? 'answered' : 'pending'),
                    is_urgent: r.is_urgent || false,
                    time: new Date(r.created_at).toLocaleDateString()
                })));
            }
        } catch { /* silent */ }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => { fetchRequests(); }, [fetchRequests]);


    const updateRequestStatus = useCallback(async (id: number, newStatus: string) => {
        setRequests(prev => prev.map(r => r.id === id ? { ...r, status: newStatus } : r));
        // Sync selected request if open
        setSelectedRequest((prev: any) => prev?.id === id ? { ...prev, status: newStatus } : prev);
        try {
            await apiFetch(`/crm/prayer-requests/${id}`, {
                method: 'PATCH', token,
                body: { status: newStatus }
            });
            addToast(`Petición marcada como ${newStatus.toUpperCase()}`, 'success');
        } catch {
            addToast('Error al actualizar estado', 'error');
        }
    }, [token, addToast]);

    const handleCreatePrayer = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newPrayer.request.trim()) return;
        setIsSaving(true);
        try {
            await apiFetch('/crm/prayer-requests', { method: 'POST', token, body: newPrayer });
            addToast('Petición registrada', 'success');
            setIsCreateDrawerOpen(false);
            setNewPrayer({ name: '', request: '', category: 'General', is_urgent: false });
            fetchRequests();
        } catch {
            addToast('Error al registrar petición', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const columns = useMemo<ColumnDef<any>[]>(() => [
        {
            accessorKey: 'name',
            header: 'Miembro / Solicitante',
            size: 250,
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-xl bg-rose-500 flex items-center justify-center text-white text-[10px] font-black shadow-lg shadow-rose-500/20">
                        {row.original.name.substring(0, 1)}
                    </div>
                    <div>
                        <p className="text-[13px] font-black text-slate-800 dark:text-white leading-tight">{row.original.name}</p>
                        <p className="text-[10px] text-slate-400 font-medium uppercase tracking-widest">{row.original.time}</p>
                    </div>
                </div>
            )
        },
        {
            accessorKey: 'request',
            header: 'Petición',
            size: 400,
            cell: info => <p className="text-[13px] text-slate-600 dark:text-slate-300 line-clamp-1 italic font-medium">&quot;{info.getValue() as string}&quot;</p>
        },
        {
            accessorKey: 'status',
            header: 'Estado',
            cell: ({ row }) => <StatusPicker currentValue={row.original.status} options={PRAYER_STATUS_OPTIONS} onSelect={(val) => updateRequestStatus(row.original.id, val)} />
        },
        {
            accessorKey: 'category',
            header: 'Categoría',
            cell: info => {
                const cat = info.getValue() as string;
                return (
                    <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
                        {cat === 'Salud' ? <Stethoscope size={12} /> : cat === 'Familia' ? <Home size={12} /> : <Briefcase size={12} />}
                        {cat}
                    </div>
                );
            }
        },
        {
            accessorKey: 'is_urgent',
            header: 'Urgencia',
            cell: ({ row }) => row.original.is_urgent ? (
                <span className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-600 text-[9px] font-black uppercase">Urgente</span>
            ) : null
        }
    ], [updateRequestStatus]);

    const handleOpenRequest = (req: any) => {
        router.push(`/crm/prayers/${req.id}`);
    };

    // Dynamic stats
    const stats = useMemo(() => ({
        active: requests.filter(r => r.status === 'active').length,
        answered: requests.filter(r => r.status === 'answered').length,
        urgent: requests.filter(r => r.is_urgent).length,
        total: requests.length,
    }), [requests]);

    const filtered = useMemo(() =>
        requests.filter(r => r.name.toLowerCase().includes(search.toLowerCase()) || r.request.toLowerCase().includes(search.toLowerCase())),
        [requests, search]
    );

    const groupedByDate = useMemo(() => {
        const map = {} as Record<string, { label: string; items: any[] }>;
        for (const req of filtered) {
            const raw = req.time ? new Date(req.time) : new Date();
            const date = Number.isNaN(raw.getTime()) ? new Date() : raw;
            const key = date.toISOString().slice(0, 10);
            const label = date.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
            if (!map[key]) map[key] = { label, items: [] };
            map[key].items.push(req);
        }
        return Object.entries(map).sort((a, b) => b[0].localeCompare(a[0]));
    }, [filtered]);

    const statusColumns = useMemo(() => {
        const ordered = ['pending', 'active', 'praying', 'answered'];
        return ordered.map(status => ({
            status,
            label: PRAYER_STATUS_OPTIONS.find(o => o.value === status)?.label ?? status.toUpperCase(),
            items: filtered.filter(r => r.status === status),
        }));
    }, [filtered]);

    return (
        <CrmShell
            breadcrumbs={[{ label: 'Consolidación', icon: Users }, { label: 'Muro de Intercesión', icon: Heart }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki']}
            onSearch={setSearch}
            rightActions={
                <button
                    onClick={() => setIsCreateDrawerOpen(true)}
                    className="flex items-center gap-2 px-4 py-1.5 bg-rose-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-rose-500/20 active:scale-95 transition-all"
                >
                    <Plus size={14} /> Nueva Petición
                </button>
            }
        >
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#f43f5e05_0%,_transparent_50%)] pointer-events-none" />

            {/* Prayer Dashboard Hero */}
            <section className="p-6 lg:p-10">
                    <div className="bg-gradient-to-br from-rose-600 to-rose-800 rounded-[3rem] p-10 text-white shadow-2xl relative overflow-hidden group border border-white/10">
                        <div className="absolute top-0 right-0 p-10 opacity-10 group-hover:scale-110 transition-transform duration-1000"><Flame size={160} /></div>
                        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center gap-10">
                            <div className="space-y-4 flex-1 max-w-2xl">
                                <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 backdrop-blur-xl border border-white/20 rounded-full text-[10px] font-black uppercase tracking-[0.3em]">
                                    <Sparkles size={14} className="animate-pulse" /> Centro de Intercesión CCF
                                </div>
                                <h2 className="text-4xl lg:text-5xl font-black tracking-tighter leading-none">
                                    Uniendo fuerzas en <span className="text-rose-200 italic">oración.</span>
                                </h2>
                            </div>
                            {/* Dynamic stats */}
                            <div className="grid grid-cols-2 gap-4 shrink-0">
                                {[
                                    { label: 'Activas', val: stats.active, bg: 'bg-white/10' },
                                    { label: 'Contestadas', val: stats.answered, bg: 'bg-emerald-500/20' },
                                    { label: 'Urgentes', val: stats.urgent, bg: 'bg-rose-900/40' },
                                    { label: 'Total', val: stats.total, bg: 'bg-white/5' },
                                ].map(s => (
                                    <div key={s.label} className={`${s.bg} rounded-2xl p-4 text-center backdrop-blur-sm border border-white/10`}>
                                        <p className="text-2xl font-black">{s.val}</p>
                                        <p className="text-[9px] font-black uppercase tracking-widest text-white/70">{s.label}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </section>

                <div className="flex-1 flex flex-col bg-white dark:bg-black/20 rounded-t-[3rem] border-t border-slate-100 dark:border-white/5 overflow-hidden">
                    <div className="px-10 py-6 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                        <h3 className="text-[12px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                            <div className="size-2 rounded-full bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]" />
                            Peticiones Activas
                        </h3>
                        {stats.urgent > 0 && (
                            <div className="flex items-center gap-2 text-[10px] font-black uppercase text-slate-400">
                                <span>Urgente</span>
                                <div className="size-5 rounded-full bg-rose-500 text-white flex items-center justify-center text-[9px] font-black shadow-lg shadow-rose-500/30">{stats.urgent}</div>
                            </div>
                        )}
                    </div>
                    {loading ? (
                        <div className="p-8 space-y-4">
                            {[1, 2, 3].map(i => <Skeleton key={i} className="h-14 w-full rounded-2xl" />)}
                        </div>
                    ) : viewType === 'table' ? (
                        <DataTable data={filtered} columns={columns} onRowClick={handleOpenRequest} />
                    ) : viewType === 'list' || viewType === 'grid' ? (
                        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                            {filtered.map(req => (
                                <button key={req.id} onClick={() => handleOpenRequest(req)} className="text-left rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 hover:border-rose-300 dark:hover:border-rose-700 transition-all">
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <p className="text-sm font-black text-slate-800 dark:text-slate-100">{req.name}</p>
                                            <p className="text-[10px] text-slate-400 uppercase tracking-widest">{req.category}</p>
                                        </div>
                                        {req.is_urgent && <span className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-600 text-[9px] font-black uppercase">Urgente</span>}
                                    </div>
                                    <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 line-clamp-2">{req.request}</p>
                                </button>
                            ))}
                            {filtered.length === 0 && <div className="col-span-full py-10 text-center text-slate-400 text-sm">Sin peticiones</div>}
                        </div>
                    ) : viewType === 'board' || viewType === 'kanban' ? (
                        <div className="p-6 grid grid-cols-1 lg:grid-cols-4 gap-4">
                            {statusColumns.map(col => (
                                <div key={col.status} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3">
                                    <div className="mb-3 flex items-center justify-between">
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{col.label}</p>
                                        <span className="text-[10px] font-black text-slate-400">{col.items.length}</span>
                                    </div>
                                    <div className="space-y-2">
                                        {col.items.map(req => (
                                            <button key={req.id} onClick={() => handleOpenRequest(req)} className="w-full text-left rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-3">
                                                <p className="text-xs font-black text-slate-800 dark:text-slate-100">{req.name}</p>
                                                <p className="text-[10px] text-slate-400 line-clamp-2">{req.request}</p>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : viewType === 'calendar' ? (
                        <div className="p-6 space-y-4">
                            {groupedByDate.length === 0 ? (
                                <div className="py-10 text-center text-slate-400 text-sm">Sin actividad</div>
                            ) : groupedByDate.map(([key, payload]) => (
                                <div key={key} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4">
                                    <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">{payload.label}</p>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {payload.items.map(req => (
                                            <button key={req.id} onClick={() => handleOpenRequest(req)} className="rounded-xl border border-slate-200 dark:border-white/10 p-3 text-left">
                                                <p className="text-sm font-black text-slate-800 dark:text-slate-100">{req.name}</p>
                                                <p className="text-[10px] text-slate-400">{req.category}</p>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : viewType === 'gantt' ? (
                        <div className="p-6">
                            <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Avance de intercesión</p>
                                {filtered.map(req => (
                                    <div key={req.id} className="space-y-1">
                                        <div className="flex items-center justify-between text-[11px]">
                                            <span className="font-bold text-slate-700 dark:text-slate-300">{req.name}</span>
                                            <span className="font-black text-slate-400">{PRAYER_PROGRESS[req.status] ?? 0}%</span>
                                        </div>
                                        <div className="h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                                            <div className="h-full bg-rose-600" style={{ width: `${PRAYER_PROGRESS[req.status] ?? 0}%` }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : viewType === 'wiki' ? (
                        <div className="p-6">
                            <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Wiki de intercesión</p>
                                <textarea
                                    value={wikiNotes}
                                    onChange={(e) => setWikiNotes(e.target.value)}
                                    placeholder="Documenta protocolos de atención, escalamiento por urgencia y guías pastorales..."
                                    className="w-full min-h-[320px] rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 text-sm font-medium text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-rose-500/20"
                                />
                            </div>
                        </div>
                    ) : (
                        <div className="p-6">
                            <CrmViewPlaceholder moduleName="Muro de Intercesion" viewType={viewType} />
                        </div>
                    )}
                </div>

            {/* ─── Drawer: Detalle de Petición ─── */}
            <WorkspaceDrawer
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedRequest?.name || 'Detalle de Petición'}
                subtitle={`CATEGORÍA: ${selectedRequest?.category?.toUpperCase()}`}
                actions={
                    <>
                        <button onClick={() => setIsDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500">Cerrar</button>
                        <button
                            onClick={() => selectedRequest && updateRequestStatus(selectedRequest.id, 'answered')}
                            className="px-6 py-2 bg-emerald-600 text-white rounded-lg text-[11px] font-bold shadow-lg shadow-emerald-500/20"
                        >
                            Marcar Contestada
                        </button>
                    </>
                }
            >
                <div className="space-y-8 animate-fade-in">
                    <section className="p-6 bg-slate-50 dark:bg-black/20 rounded-[2.5rem] border border-slate-100 dark:border-white/5 relative">
                        <Quote className="absolute top-4 left-4 size-10 text-rose-500/10" />
                        <p className="text-base text-slate-700 dark:text-slate-200 font-medium leading-relaxed italic relative z-10 pt-3">
                            &ldquo;{selectedRequest?.request}&rdquo;
                        </p>
                    </section>

                    <section className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-2xl">
                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Impacto</p>
                            <p className="text-sm font-black text-slate-800 dark:text-white uppercase">{selectedRequest?.is_urgent ? 'ALTA PRIORIDAD' : 'Normal'}</p>
                        </div>
                        <div className="p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-2xl">
                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Recibido</p>
                            <p className="text-sm font-black text-slate-800 dark:text-white uppercase">{selectedRequest?.time}</p>
                        </div>
                        <div className="p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-2xl">
                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Estado</p>
                            <p className="text-sm font-black text-slate-800 dark:text-white uppercase">{selectedRequest?.status}</p>
                        </div>
                        <div className="p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-2xl">
                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">Categoría</p>
                            <p className="text-sm font-black text-slate-800 dark:text-white uppercase">{selectedRequest?.category}</p>
                        </div>
                    </section>

                    <section className="space-y-4">
                        <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <Flame size={14} className="text-rose-500" /> Actualizar Estado
                        </h4>
                        <div className="flex gap-2">
                            {PRAYER_STATUS_OPTIONS.map(opt => (
                                <button
                                    key={opt.value}
                                    onClick={() => selectedRequest && updateRequestStatus(selectedRequest.id, opt.value)}
                                    className={clsx(
                                        "flex-1 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border",
                                        selectedRequest?.status === opt.value
                                            ? `${opt.bg} ${opt.text} border-current`
                                            : 'bg-slate-50 dark:bg-white/5 text-slate-400 border-transparent hover:border-slate-200'
                                    )}
                                >
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>

            {/* ─── Drawer: Nueva Petición ─── */}
            <WorkspaceDrawer
                isOpen={isCreateDrawerOpen}
                onClose={() => setIsCreateDrawerOpen(false)}
                title="Nueva Petición de Oración"
                subtitle="Registrar en el muro de intercesión"
                actions={
                    <>
                        <button type="button" onClick={() => setIsCreateDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                            Cancelar
                        </button>
                        <button
                            form="create-prayer-form"
                            type="submit"
                            disabled={isSaving}
                            className="px-8 py-2 bg-rose-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-rose-500/20 hover:bg-rose-700 active:scale-95 transition-all flex items-center gap-2"
                        >
                            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            Registrar
                        </button>
                    </>
                }
            >
                <form id="create-prayer-form" onSubmit={handleCreatePrayer} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Nombre del Solicitante</label>
                        <input
                            value={newPrayer.name}
                            onChange={e => setNewPrayer({ ...newPrayer, name: e.target.value })}
                            placeholder="Nombre o 'Anónimo'"
                            className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-rose-500/20 font-bold text-sm dark:text-white"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Petición *</label>
                        <textarea
                            required
                            value={newPrayer.request}
                            onChange={e => setNewPrayer({ ...newPrayer, request: e.target.value })}
                            placeholder="Describe la petición de oración..."
                            rows={5}
                            className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-rose-500/20 font-bold text-sm dark:text-white resize-none"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Categoría</label>
                            <select
                                value={newPrayer.category}
                                onChange={e => setNewPrayer({ ...newPrayer, category: e.target.value })}
                                className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-rose-500/20 font-bold text-sm dark:text-white appearance-none"
                            >
                                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Urgencia</label>
                            <button
                                type="button"
                                onClick={() => setNewPrayer({ ...newPrayer, is_urgent: !newPrayer.is_urgent })}
                                className={clsx(
                                    "w-full px-4 py-3 rounded-2xl border font-black text-sm transition-all",
                                    newPrayer.is_urgent
                                        ? "bg-rose-50 dark:bg-rose-900/20 border-rose-300 dark:border-rose-700 text-rose-600"
                                        : "bg-slate-50 dark:bg-black/20 border-slate-200 dark:border-white/10 text-slate-400"
                                )}
                            >
                                {newPrayer.is_urgent ? '🔴 URGENTE' : 'Normal'}
                            </button>
                        </div>
                    </div>
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}


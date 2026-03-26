"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
    Heart, 
    MessageSquare, 
    Plus, 
    Search, 
    Filter, 
    ChevronRight, 
    MoreHorizontal,
    CheckCircle2,
    Clock,
    Layout,
    Users,
    Shield,
    Sparkles,
    Flame,
    Quote,
    Stethoscope,
    Briefcase,
    Home,
    AlertCircle
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const PRAYER_STATUS_OPTIONS: StatusOption[] = [
    { label: 'ACTIVA', value: 'active', color: 'bg-rose-500', text: 'text-rose-600', bg: 'bg-rose-50' },
    { label: 'CONTESTADA', value: 'answered', color: 'bg-emerald-500', text: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'EN PROCESO', value: 'praying', color: 'bg-blue-500', text: 'text-blue-600', bg: 'bg-blue-50' },
];

export default function PrayerSupportCenter() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [requests, setRequests] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedRequest, setSelectedRequest] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    const fetchRequests = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/crm/prayer-requests', { token });
            if (Array.isArray(data)) {
                setRequests(data.map((r: any) => ({
                    id: r.id,
                    name: r.name || 'Anónimo',
                    request: r.request,
                    category: r.category,
                    status: r.is_answered ? 'answered' : 'active',
                    is_urgent: r.request.length > 100, // Simple logic for mock
                    time: new Date(r.created_at).toLocaleDateString()
                })));
            }
        } catch (err) { console.error(err); }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => { fetchRequests(); }, [fetchRequests]);

    const updateRequestStatus = useCallback(async (id: number, newStatus: string) => {
        setRequests(prev => prev.map(r => r.id === id ? { ...r, status: newStatus } : r));
        try {
            await apiFetch(`/crm/prayer-requests/${id}`, {
                method: 'PATCH',
                token,
                body: { is_answered: newStatus === 'answered' }
            });
            addToast(`Petición marcada como ${newStatus.toUpperCase()}`, 'success');
        } catch (err) {
            addToast('Error al actualizar estado', 'error');
        }
    }, [token, addToast]);

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
        }
    ], [updateRequestStatus]);

    const handleOpenRequest = (req: any) => {
        setSelectedRequest(req);
        setIsDrawerOpen(true);
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'CRM Pastoral', icon: Users }, { label: 'Muro de Intercesión', icon: Heart }]}
                viewType="table" setViewType={() => {}} onSearch={setSearch}
                rightActions={
                    <button className="flex items-center gap-2 px-4 py-1.5 bg-rose-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-rose-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Nueva Petición
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin relative flex flex-col">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#f43f5e05_0%,_transparent_50%)] pointer-events-none" />

                {/* Prayer Dashboard Hero */}
                <section className="p-6 lg:p-10">
                    <div className="bg-gradient-to-br from-rose-600 to-rose-800 rounded-[3rem] p-10 text-white shadow-2xl relative overflow-hidden group border border-white/10">
                        <div className="absolute top-0 right-0 p-10 opacity-10 group-hover:scale-110 transition-transform duration-1000"><Flame size={160} /></div>
                        <div className="relative z-10 space-y-6 max-w-2xl">
                            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 backdrop-blur-xl border border-white/20 rounded-full text-[10px] font-black uppercase tracking-[0.3em]">
                                <Sparkles size={14} className="animate-pulse" /> Centro de Intercesión CCF
                            </div>
                            <h2 className="text-4xl lg:text-6xl font-black tracking-tighter leading-none">
                                Uniendo fuerzas en <span className="text-rose-200 italic">oración.</span>
                            </h2>
                            <p className="text-xl text-rose-100/80 font-medium leading-relaxed">Monitorea y responde a las necesidades espirituales de la casa con prontitud y amor.</p>
                        </div>
                    </div>
                </section>

                <div className="flex-1 flex flex-col bg-white dark:bg-black/20 rounded-t-[3rem] border-t border-slate-100 dark:border-white/5 overflow-hidden">
                    <div className="px-10 py-6 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                        <h3 className="text-[12px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                            <div className="size-2 rounded-full bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]" />
                            Peticiones Activas
                        </h3>
                        <div className="flex items-center gap-2 text-[10px] font-black uppercase text-slate-400">
                            <span>Urgente</span>
                            <div className="size-4 rounded-full bg-rose-500 text-white flex items-center justify-center text-[8px]">1</div>
                        </div>
                    </div>
                    {loading ? (
                        <div className="p-8 space-y-4">
                            {[1,2,3].map(i => <Skeleton key={i} className="h-14 w-full rounded-2xl" />)}
                        </div>
                    ) : (
                        <DataTable data={requests.filter(r => r.name.toLowerCase().includes(search.toLowerCase()))} columns={columns} onRowClick={handleOpenRequest} />
                    )}
                </div>
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedRequest?.name || 'Detalle de Petición'}
                subtitle={`CATEGORÍA: ${selectedRequest?.category?.toUpperCase()}`}
                actions={<><button className="px-4 py-2 text-[11px] font-bold text-slate-500">Archivar</button><button className="px-6 py-2 bg-rose-600 text-white rounded-lg text-[11px] font-bold shadow-lg shadow-rose-500/20">Registrar Respuesta</button></>}
            >
                <div className="space-y-10 animate-fade-in">
                    <section className="p-8 bg-slate-50 dark:bg-black/20 rounded-[2.5rem] border border-slate-100 dark:border-white/5 relative">
                        <Quote className="absolute top-6 left-6 size-12 text-rose-500/10" />
                        <p className="text-lg text-slate-700 dark:text-slate-200 font-medium leading-relaxed italic relative z-10 pt-4">
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
                    </section>

                    <section className="space-y-4">
                        <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2"><Flame size={14} className="text-rose-500" /> Bitácora de Intercesión</h4>
                        <div className="space-y-3">
                            <div className="p-4 bg-emerald-50 dark:bg-emerald-900/10 rounded-2xl border border-emerald-100 dark:border-emerald-900/30 flex items-center gap-4">
                                <div className="size-8 rounded-xl bg-white dark:bg-white/10 flex items-center justify-center text-emerald-600"><CheckCircle2 size={18} /></div>
                                <p className="text-xs text-emerald-700 dark:text-emerald-400 font-bold">Líder asignado: Pastor Samuel</p>
                            </div>
                            <button className="w-full py-3 border-2 border-dashed border-slate-100 dark:border-white/5 rounded-2xl text-[10px] font-black uppercase text-slate-400 hover:text-rose-600 transition-all">+ Añadir Nota de Seguimiento</button>
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

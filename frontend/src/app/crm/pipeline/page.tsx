"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    Phone,
    Smartphone,
    UserPlus,
    Search,
    Filter,
    Layout,
    List as ListIcon,
    MoreHorizontal,
    Target,
    Bot,
    Sparkles,
    Calendar,
    ChevronRight,
    MessageCircle,
    Send,
    FileText,
    TrendingUp,
    Users,
    Zap,
    Clock,
    CheckCircle2,
    User,
    Mail,
    Loader2,
    ExternalLink,
    ArrowRight
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { useRouter } from 'next/navigation';
import CrmShell from '@/components/crm/CrmShell';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

// ─── Stage definitions ────────────────────────────────────────
const PIPELINE_STAGES: (StatusOption & { dot: string; colBg: string; emptyIcon: any })[] = [
    { label: 'NUEVO', value: 'new', color: 'bg-blue-500', dot: 'bg-blue-500', text: 'text-blue-600', bg: 'bg-blue-50', colBg: 'bg-blue-500/5' },
    { label: 'POR LLAMAR', value: 'call', color: 'bg-amber-500', dot: 'bg-amber-500', text: 'text-amber-600', bg: 'bg-amber-50', colBg: 'bg-amber-500/5', emptyIcon: Phone },
    { label: 'VISITA', value: 'visit', color: 'bg-purple-500', dot: 'bg-purple-500', text: 'text-purple-600', bg: 'bg-purple-50', colBg: 'bg-purple-500/5', emptyIcon: Calendar },
    { label: 'DISCIPULADO', value: 'discipleship', color: 'bg-indigo-500', dot: 'bg-indigo-500', text: 'text-indigo-600', bg: 'bg-indigo-50', colBg: 'bg-indigo-500/5', emptyIcon: Sparkles },
    { label: 'CONSOLIDADO', value: 'consolidated', color: 'bg-emerald-500', dot: 'bg-emerald-500', text: 'text-emerald-600', bg: 'bg-emerald-50', colBg: 'bg-emerald-500/5', emptyIcon: CheckCircle2 },
];

const STAGE_LABEL: Record<string, string> = {
    new: 'Nuevo', call: 'Por Llamar', visit: 'Visita',
    discipleship: 'Discipulado', consolidated: 'Consolidado',
    contacted: 'Contactado', in_process: 'En Proceso', lost: 'Perdido',
};

const SOURCES: Record<string, string> = {
    Visitante: '🧑‍🤝‍🧑', Referido: '🤝', Web: '🌐',
    'Redes Sociales': '📱', Evento: '🎯', Otro: '📌',
};

export default function ConsolidationPipelinePage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [leads, setLeads] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_pipeline_view', 'board'));
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban'];
    const [selectedLead, setSelectedLead] = useState<any>(null);

    // New Lead drawer
    const [isNewLeadDrawerOpen, setIsNewLeadDrawerOpen] = useState(false);
    const [isSavingLead, setIsSavingLead] = useState(false);
    const [newLeadForm, setNewLeadForm] = useState({
        first_name: '', last_name: '', phone: '', source: 'Visitante', notes: '', stage: 'new'
    });

    const fetchPipeline = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/crm/consolidation/pipeline', { token });
            if (Array.isArray(data)) setLeads(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => { fetchPipeline(); }, [fetchPipeline]);

    const handleCreateLead = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSavingLead(true);
        try {
            await apiFetch('/crm/consolidation/pipeline', {
                method: 'POST', token,
                body: { ...newLeadForm, spiritual_status: 'Prospecto' }
            });
            addToast('✅ Prospecto creado exitosamente', 'success');
            setIsNewLeadDrawerOpen(false);
            setNewLeadForm({ first_name: '', last_name: '', phone: '', source: 'Visitante', notes: '', stage: 'new' });
            fetchPipeline();
        } catch {
            addToast('Error al crear el prospecto', 'error');
        } finally {
            setIsSavingLead(false);
        }
    };

    const handleUpdateStage = useCallback(async (leadId: number, newStage: string) => {
        // Optimistic update
        setLeads(prev => prev.map(l => l.id === leadId ? { ...l, stage: newStage } : l));
        try {
            await apiFetch(`/crm/consolidation/pipeline/${leadId}`, {
                method: 'PATCH', token, body: { stage: newStage }
            });
            addToast(`Movido a ${STAGE_LABEL[newStage] ?? newStage}`, 'success');
        } catch {
            addToast('Error al actualizar etapa', 'error');
            fetchPipeline(); // Revert
        }
    }, [token, addToast, fetchPipeline]);

    // Table columns with proper labels
    const columns = useMemo<ColumnDef<any>[]>(() => [
        {
            accessorKey: 'name',
            header: 'Prospecto',
            size: 280,
            cell: ({ row }) => {
                const l = row.original;
                const initials = `${l.first_name?.[0] ?? ''}${l.last_name?.[0] ?? ''}`.toUpperCase();
                return (
                    <div className="flex items-center gap-3">
                        <div className="size-9 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-xs shadow-lg shadow-blue-500/20 shrink-0">
                            {initials}
                        </div>
                        <div>
                            <p className="font-black text-slate-800 dark:text-white text-[13px] leading-tight">{l.first_name} {l.last_name}</p>
                            <p className="text-[10px] font-medium text-slate-400">{l.phone}</p>
                        </div>
                    </div>
                );
            }
        },
        {
            accessorKey: 'stage',
            header: 'Etapa',
            size: 160,
            cell: ({ row }) => {
                const stage = PIPELINE_STAGES.find(s => s.value === row.original.stage);
                return stage ? (
                    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-widest', stage.bg, stage.text)}>
                        <span className={clsx('size-1.5 rounded-full', stage.color)} />
                        {stage.label}
                    </span>
                ) : (
                    <span className="text-[10px] text-slate-400">{STAGE_LABEL[row.original.stage] ?? row.original.stage}</span>
                );
            }
        },
        {
            accessorKey: 'source',
            header: 'Fuente',
            size: 130,
            cell: ({ row }) => (
                <span className="text-[11px] text-slate-500 font-medium">
                    {SOURCES[row.original.source] ?? '📌'} {row.original.source ?? 'General'}
                </span>
            )
        },
        {
            accessorKey: 'created_at',
            header: 'Registrado',
            size: 120,
            cell: ({ row }) => (
                <span className="text-[10px] text-slate-400 font-medium">
                    {row.original.created_at ? new Date(row.original.created_at).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }) : '—'}
                </span>
            )
        },
        {
            id: 'actions',
            header: '',
            size: 60,
            cell: ({ row }) => (
                <button
                    onClick={(e) => { e.stopPropagation(); router.push(`/crm/contacts/${row.original.id}`); }}
                    className="p-1.5 rounded-lg text-slate-300 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-950/40 transition-all"
                >
                    <ArrowRight size={14} />
                </button>
            )
        }
    ], [router]);

    // Filtered leads
    const filteredLeads = useMemo(() => {
        if (!search.trim()) return leads;
        const q = search.toLowerCase();
        return leads.filter(l =>
            `${l.first_name} ${l.last_name}`.toLowerCase().includes(q) ||
            l.phone?.includes(q) ||
            l.source?.toLowerCase().includes(q)
        );
    }, [leads, search]);

    // Stats
    const stats = useMemo(() => ({
        total: leads.length,
        new: leads.filter(l => l.stage === 'new').length,
        consolidated: leads.filter(l => l.stage === 'consolidated').length,
        conversion: leads.length > 0 ? Math.round((leads.filter(l => l.stage === 'consolidated').length / leads.length) * 100) : 0,
    }), [leads]);

    const leadSidebarContent = selectedLead ? (
        <div className="flex flex-col h-full overflow-hidden">
            {/* Name header */}
            <div className="p-6 pb-4 border-b border-slate-100 dark:border-white/5 space-y-3 bg-gradient-to-b from-slate-50 dark:from-black/20 to-transparent">
                <div className="size-14 rounded-2xl bg-blue-600 flex items-center justify-center text-white shadow-xl shadow-blue-500/25 text-xl font-black">
                    {selectedLead.first_name?.[0]}{selectedLead.last_name?.[0]}
                </div>
                <div>
                    <h3 className="text-base font-black tracking-tight text-slate-800 dark:text-white leading-tight">
                        {selectedLead.first_name} {selectedLead.last_name}
                    </h3>
                    <p className="text-[10px] font-medium text-slate-400 mt-0.5">{selectedLead.phone}</p>
                </div>
                {/* Stage badge */}
                {(() => {
                    const s = PIPELINE_STAGES.find(st => st.value === selectedLead.stage);
                    return s ? (
                        <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-widest', s.bg, s.text)}>
                            <span className={clsx('size-1.5 rounded-full', s.color)} />
                            {s.label}
                        </span>
                    ) : null;
                })()}
            </div>
            {/* Actions */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest px-2 mb-3">Acciones Pastorales</p>
                <button
                    onClick={() => router.push(`/crm/contacts/${selectedLead.id}`)}
                    className="w-full flex items-center gap-3 px-4 py-3 bg-blue-600 text-white rounded-2xl text-xs font-black hover:bg-blue-700 transition-all shadow-lg shadow-blue-500/20"
                >
                    <ExternalLink size={14} /> Ver Ficha Completa
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 bg-white dark:bg-white/5 rounded-2xl border border-slate-200 dark:border-white/10 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/10 transition-all">
                    <Phone size={14} className="text-emerald-500" /> Registrar Llamada
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 bg-white dark:bg-white/5 rounded-2xl border border-slate-200 dark:border-white/10 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/10 transition-all">
                    <MessageCircle size={14} className="text-blue-500" /> WhatsApp Directo
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 bg-white dark:bg-white/5 rounded-2xl border border-slate-200 dark:border-white/10 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/10 transition-all">
                    <FileText size={14} className="text-purple-500" /> Notas Pastorales
                </button>
                <div className="h-px bg-slate-100 dark:bg-white/5 my-2 mx-2" />
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest px-2 mb-2">Cambiar Etapa</p>
                <div className="space-y-1.5">
                    {PIPELINE_STAGES.map(s => (
                        <button
                            key={s.value}
                            onClick={() => { handleUpdateStage(selectedLead.id, s.value); setSelectedLead((prev: any) => ({ ...prev, stage: s.value })); }}
                            className={clsx(
                                "w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-wide transition-all border",
                                selectedLead.stage === s.value
                                    ? `${s.bg} ${s.text} border-current`
                                    : 'bg-transparent border-transparent hover:bg-slate-50 dark:hover:bg-white/5 text-slate-500'
                            )}
                        >
                            <span className={clsx('size-2 rounded-full', s.color)} />
                            {s.label}
                            {selectedLead.stage === s.value && <CheckCircle2 size={12} className="ml-auto" />}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    ) : null;

    if (loading && leads.length === 0) return (
        <div className="p-10 space-y-6">
            <div className="grid grid-cols-4 gap-4">
                {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-8 rounded-full" />)}
            </div>
            <div className="grid grid-cols-5 gap-4">
                {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-64 rounded-3xl" />)}
            </div>
        </div>
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM Pastoral', icon: Users },
                { label: 'Pipeline de Consolidación', icon: Target },
                ...(selectedLead ? [{ label: `${selectedLead.first_name} ${selectedLead.last_name}`, icon: User }] : [])
            ]}
            viewOptions={ALL_VIEWS}
            viewType={viewType}
            onViewChange={setViewType}
            rightActions={
                <SplitDropdownButton
                    mainLabel="Nuevo Lead"
                    icon={UserPlus}
                    onMainClick={() => setIsNewLeadDrawerOpen(true)}
                    options={[
                        { id: 'lead', label: 'Nuevo Prospecto', icon: UserPlus, onClick: () => setIsNewLeadDrawerOpen(true) },
                        { id: 'call', label: 'Registrar Llamada', icon: Phone, onClick: () => {} },
                        { id: 'mail', label: 'Enviar Email', icon: Mail, onClick: () => {} }
                    ]}
                />
            }
        >
            <div className="flex flex-col md:flex-row h-full w-full overflow-hidden">

                {/* ── Inner Left Sidebar ── */}
                <motion.div
                    initial={false}
                    animate={{ width: 248, opacity: 1 }}
                    className="shrink-0 border-r border-slate-200 dark:border-white/5 bg-white dark:bg-[#1e1f21] flex flex-col z-10"
                >
                    {selectedLead ? (
                        <>
                            <div className="h-10 border-b border-slate-100 dark:border-white/5 flex items-center px-4 gap-3 bg-slate-50 dark:bg-black/20 shrink-0">
                                <button
                                    onClick={() => setSelectedLead(null)}
                                    className="p-1.5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-lg text-slate-500 transition-all"
                                >
                                    <ChevronRight size={14} className="rotate-180" />
                                </button>
                                <p className="text-[11px] font-bold text-slate-600 dark:text-slate-300 truncate">Volver al Pipeline</p>
                            </div>
                            <div className="flex-1 overflow-hidden">{leadSidebarContent}</div>
                        </>
                    ) : (
                        <div className="flex flex-col h-full">
                            {/* Stats */}
                            <div className="p-4 border-b border-slate-100 dark:border-white/5 space-y-3">
                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Métricas</p>
                                <div className="grid grid-cols-2 gap-2">
                                    {[
                                        { label: 'Total', val: stats.total, color: 'text-slate-800 dark:text-white' },
                                        { label: 'Nuevos', val: stats.new, color: 'text-blue-600' },
                                        { label: 'Consolidados', val: stats.consolidated, color: 'text-emerald-600' },
                                        { label: 'Conversión', val: `${stats.conversion}%`, color: 'text-purple-600' },
                                    ].map(s => (
                                        <div key={s.label} className="bg-slate-50 dark:bg-white/5 rounded-xl p-2.5 text-center">
                                            <p className={`text-lg font-black ${s.color}`}>{s.val}</p>
                                            <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">{s.label}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            {/* Filters */}
                            <div className="px-4 py-5 flex-1">
                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3">Filtros</p>
                                <div className="space-y-1">
                                    {[
                                        { id: 'all', label: 'Todos los Prospectos', icon: Users, count: stats.total },
                                        { id: 'new', label: 'Solo Nuevos', icon: UserPlus, count: stats.new },
                                        { id: 'consolidated', label: 'Consolidados', icon: CheckCircle2, count: stats.consolidated },
                                    ].map(s => (
                                        <button key={s.id} className="w-full flex items-center gap-3 px-3 py-2.5 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/10 rounded-xl transition-all">
                                            <s.icon size={14} className="text-slate-400 shrink-0" />
                                            <span className="flex-1 text-left">{s.label}</span>
                                            <span className="text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-white/10 rounded-full font-black text-slate-500">{s.count}</span>
                                        </button>
                                    ))}
                                </div>
                                {/* Search */}
                                <div className="mt-4 relative">
                                    <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                    <input
                                        value={search}
                                        onChange={e => setSearch(e.target.value)}
                                        placeholder="Buscar prospecto..."
                                        className="w-full pl-8 pr-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 dark:text-white"
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </motion.div>

                {/* ── Main Board ── */}
                <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-50/50 dark:bg-[#1a1b1d]">
                    <main className="flex-1 overflow-hidden flex flex-col">
                        <AnimatePresence mode="wait">
                            {viewType === 'board' || viewType === 'kanban' ? (
                                <motion.div
                                    key="board"
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -12 }}
                                    className="flex-1 flex gap-5 p-6 overflow-x-auto"
                                >
                                    {PIPELINE_STAGES.map(stage => (
                                        <KanbanColumn
                                            key={stage.value}
                                            stage={stage}
                                            leads={filteredLeads.filter(l => l.stage === stage.value)}
                                            onLeadClick={(l: any) => setSelectedLead(l)}
                                            onDropLead={handleUpdateStage}
                                            onNewLead={() => {
                                                setNewLeadForm(f => ({ ...f, stage: stage.value }));
                                                setIsNewLeadDrawerOpen(true);
                                            }}
                                        />
                                    ))}
                                </motion.div>
                            ) : viewType === 'grid' ? (
                                <motion.div key="grid" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex-1 p-6 overflow-y-auto">
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {filteredLeads.map((lead: any) => {
                                            const stage = PIPELINE_STAGES.find(s => s.value === lead.stage);
                                            return (
                                                <div
                                                    key={lead.id}
                                                    onClick={() => setSelectedLead(lead)}
                                                    className="p-5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-3xl shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all cursor-pointer group"
                                                >
                                                    <div className="flex items-center gap-3 mb-3">
                                                        <div className="size-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-xs shadow-lg shadow-blue-500/20">
                                                            {lead.first_name?.[0]}{lead.last_name?.[0]}
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <p className="font-black text-slate-800 dark:text-white text-sm truncate">{lead.first_name} {lead.last_name}</p>
                                                            <p className="text-[10px] text-slate-400">{lead.phone}</p>
                                                        </div>
                                                        <ChevronRight size={14} className="text-slate-300 group-hover:text-blue-500 transition-all" />
                                                    </div>
                                                    <div className="flex items-center justify-between">
                                                        {stage ? (
                                                            <span className={clsx('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest', stage.bg, stage.text)}>
                                                                <span className={clsx('size-1.5 rounded-full', stage.color)} /> {stage.label}
                                                            </span>
                                                        ) : null}
                                                        <span className="text-[9px] text-slate-400">
                                                            {SOURCES[lead.source] ?? '📌'} {lead.source}
                                                        </span>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </motion.div>
                            ) : (
                                <motion.div key="list" className="flex-1 overflow-y-auto bg-white dark:bg-[#1e1f21]">
                                    <DataTable
                                        data={filteredLeads}
                                        columns={columns}
                                        onRowClick={(l) => setSelectedLead(l)}
                                    />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </main>
                </div>
            </div>

            {/* ─── Drawer: Nuevo Lead ─── */}
            <WorkspaceDrawer
                isOpen={isNewLeadDrawerOpen}
                onClose={() => setIsNewLeadDrawerOpen(false)}
                title="Nuevo Prospecto"
                subtitle="Registrar en el pipeline de consolidación pastoral"
                actions={
                    <>
                        <button
                            type="button"
                            onClick={() => setIsNewLeadDrawerOpen(false)}
                            className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                        >
                            Cancelar
                        </button>
                        <button
                            form="new-lead-form"
                            type="submit"
                            disabled={isSavingLead}
                            className="px-7 py-2.5 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/25 hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60"
                        >
                            {isSavingLead ? <Loader2 size={13} className="animate-spin" /> : <UserPlus size={13} />}
                            Registrar Prospecto
                        </button>
                    </>
                }
            >
                <form id="new-lead-form" onSubmit={handleCreateLead} className="space-y-5 pt-2">
                    {/* Nombre / Apellido */}
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Nombre <span className="text-blue-500">*</span></label>
                            <input
                                required
                                value={newLeadForm.first_name}
                                onChange={e => setNewLeadForm({ ...newLeadForm, first_name: e.target.value })}
                                placeholder="Juan"
                                className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/30 font-bold text-sm dark:text-white placeholder-slate-300 transition-all"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Apellido <span className="text-blue-500">*</span></label>
                            <input
                                required
                                value={newLeadForm.last_name}
                                onChange={e => setNewLeadForm({ ...newLeadForm, last_name: e.target.value })}
                                placeholder="Pérez"
                                className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/30 font-bold text-sm dark:text-white placeholder-slate-300 transition-all"
                            />
                        </div>
                    </div>

                    {/* Teléfono */}
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Teléfono / WhatsApp <span className="text-blue-500">*</span></label>
                        <div className="relative">
                            <Phone size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                required
                                value={newLeadForm.phone}
                                onChange={e => setNewLeadForm({ ...newLeadForm, phone: e.target.value })}
                                placeholder="+57 300 000 0000"
                                className="w-full pl-10 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/30 font-bold text-sm dark:text-white placeholder-slate-300 transition-all"
                            />
                        </div>
                    </div>

                    {/* Fuente / Etapa */}
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Fuente de Contacto</label>
                            <select
                                value={newLeadForm.source}
                                onChange={e => setNewLeadForm({ ...newLeadForm, source: e.target.value })}
                                className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/30 font-bold text-sm dark:text-white appearance-none transition-all"
                            >
                                {Object.keys(SOURCES).map(s => <option key={s} value={s}>{SOURCES[s]} {s}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Etapa Inicial</label>
                            <select
                                value={newLeadForm.stage}
                                onChange={e => setNewLeadForm({ ...newLeadForm, stage: e.target.value })}
                                className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/30 font-bold text-sm dark:text-white appearance-none transition-all"
                            >
                                {PIPELINE_STAGES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                            </select>
                        </div>
                    </div>

                    {/* Notas */}
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Notas del Primer Contacto</label>
                        <textarea
                            value={newLeadForm.notes}
                            onChange={e => setNewLeadForm({ ...newLeadForm, notes: e.target.value })}
                            placeholder="¿Cómo llegó? ¿Qué contó? ¿Tiene familia en la iglesia?..."
                            rows={4}
                            className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/30 font-bold text-sm dark:text-white placeholder-slate-300 resize-none transition-all"
                        />
                    </div>

                    {/* Preview chip */}
                    {(newLeadForm.first_name || newLeadForm.last_name) && (
                        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-2xl border border-blue-100 dark:border-blue-700/30 flex items-center gap-3">
                            <div className="size-8 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black text-xs shadow">
                                {newLeadForm.first_name?.[0] ?? ''}{newLeadForm.last_name?.[0] ?? ''}
                            </div>
                            <div>
                                <p className="text-sm font-black text-blue-800 dark:text-blue-300">{newLeadForm.first_name} {newLeadForm.last_name}</p>
                                <p className="text-[9px] text-blue-500 uppercase tracking-widest font-bold">Vista previa del prospecto</p>
                            </div>
                        </div>
                    )}
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}

// ─── KanbanColumn Component ───────────────────────────────────
interface KanbanColumnProps {
    stage: typeof PIPELINE_STAGES[number];
    leads: any[];
    onLeadClick: (lead: any) => void;
    onDropLead: (leadId: number, stage: string) => void;
    onNewLead: () => void;
}

function KanbanColumn({ stage, leads, onLeadClick, onDropLead, onNewLead }: KanbanColumnProps) {
    const [isDragOver, setIsDragOver] = useState(false);

    return (
        <div
            className={clsx(
                "flex-shrink-0 w-72 flex flex-col gap-3 rounded-3xl transition-all duration-200",
                isDragOver ? `${stage.colBg} ring-2 ring-inset ring-blue-400/30 p-3` : "p-3"
            )}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
                setIsDragOver(false);
                const leadId = e.dataTransfer.getData('leadId');
                if (leadId) onDropLead(parseInt(leadId), stage.value);
            }}
        >
            {/* Column Header */}
            <div className="flex items-center justify-between px-1 mb-1">
                <div className="flex items-center gap-2.5">
                    <div className={clsx("size-3 rounded-full shadow-sm", stage.color)} />
                    <h3 className="text-[10px] font-black text-slate-600 dark:text-slate-400 uppercase tracking-[0.25em]">
                        {stage.label}
                    </h3>
                    <span className={clsx(
                        "min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full text-[9px] font-black",
                        leads.length > 0 ? `${stage.bg} ${stage.text}` : 'bg-slate-100 dark:bg-white/10 text-slate-400'
                    )}>
                        {leads.length}
                    </span>
                </div>
                <button
                    onClick={onNewLead}
                    className={clsx(
                        "size-6 rounded-lg flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 hover:opacity-100",
                        `hover:${stage.bg} ${stage.text} opacity-40 hover:opacity-100`
                    )}
                    title={`Agregar a ${stage.label}`}
                >
                    <UserPlus size={11} />
                </button>
            </div>

            {/* Lead Cards */}
            <div className="flex flex-col gap-2.5 flex-1">
                {leads.map((lead: any) => (
                    <LeadCard
                        key={lead.id}
                        lead={lead}
                        stage={stage}
                        onClick={() => onLeadClick(lead)}
                    />
                ))}

                {/* Empty state */}
                {leads.length === 0 && (
                    <div className={clsx(
                        "flex flex-col items-center justify-center gap-2 py-8 rounded-2xl border-2 border-dashed transition-all",
                        isDragOver
                            ? `${stage.colBg} border-current ${stage.text} scale-[1.02]`
                            : 'border-slate-200 dark:border-white/5 text-slate-300 dark:text-slate-700'
                    )}>
                        <UserPlus size={20} className={isDragOver ? stage.text : ''} />
                        <p className="text-[9px] font-black uppercase tracking-widest text-center px-4">
                            {isDragOver ? 'Suelta aquí' : 'Sin prospectos'}
                        </p>
                    </div>
                )}

                {/* Add button at bottom */}
                <button
                    onClick={onNewLead}
                    className="w-full py-2.5 rounded-2xl border border-dashed border-slate-200 dark:border-white/5 text-[10px] font-bold text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:border-slate-300 dark:hover:border-white/15 transition-all flex items-center justify-center gap-1.5 hover:bg-white dark:hover:bg-white/5"
                >
                    <UserPlus size={11} /> Agregar
                </button>
            </div>
        </div>
    );
}

// ─── LeadCard Component ───────────────────────────────────────
function LeadCard({ lead, stage, onClick }: { lead: any; stage: any; onClick: () => void }) {
    const daysSince = lead.created_at
        ? Math.floor((Date.now() - new Date(lead.created_at).getTime()) / (1000 * 60 * 60 * 24))
        : null;

    return (
        <div
            onClick={onClick}
            draggable
            onDragStart={(e) => {
                e.dataTransfer.setData('leadId', lead.id.toString());
                e.dataTransfer.effectAllowed = 'move';
            }}
            className="group p-4 bg-white dark:bg-[#252628] border border-slate-200 dark:border-white/8 rounded-2xl shadow-sm hover:shadow-lg hover:shadow-slate-200/60 dark:hover:shadow-black/20 hover:border-blue-400/30 dark:hover:border-blue-500/20 transition-all cursor-grab active:cursor-grabbing active:scale-[0.98] active:shadow-xl"
        >
            {/* Top row: avatar + name */}
            <div className="flex items-center gap-3 mb-3">
                <div className={clsx(
                    "size-9 rounded-xl flex items-center justify-center text-white font-black text-xs shadow-sm shrink-0",
                    stage.color
                )}>
                    {lead.first_name?.[0] ?? ''}{lead.last_name?.[0] ?? ''}
                </div>
                <div className="flex-1 min-w-0">
                    <p className="font-black text-slate-800 dark:text-white text-[13px] leading-tight truncate">
                        {lead.first_name} {lead.last_name}
                    </p>
                    <p className="text-[10px] text-slate-400 font-medium">{lead.phone}</p>
                </div>
                <ChevronRight size={13} className="text-slate-300 group-hover:text-blue-500 transition-all shrink-0" />
            </div>

            {/* Bottom row: source + days */}
            <div className="flex items-center justify-between">
                {lead.source && (
                    <span className="text-[9px] text-slate-400 font-medium flex items-center gap-1">
                        {SOURCES[lead.source] ?? '📌'} {lead.source}
                    </span>
                )}
                {daysSince !== null && (
                    <span className={clsx(
                        "text-[9px] font-black px-1.5 py-0.5 rounded-full",
                        daysSince > 14 ? 'bg-rose-50 text-rose-500 dark:bg-rose-900/20' :
                        daysSince > 7 ? 'bg-amber-50 text-amber-600 dark:bg-amber-900/20' :
                        'bg-slate-100 dark:bg-white/5 text-slate-400'
                    )}>
                        {daysSince === 0 ? 'Hoy' : `${daysSince}d`}
                    </span>
                )}
            </div>
        </div>
    );
}

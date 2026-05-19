"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    Phone,
    UserPlus,
    Target,
    Sparkles,
    ChevronRight,
    FileText,
    Users,
    Clock,
    User,
    Mail,
    Loader2,
    ArrowRight
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import { useRouter } from 'next/navigation';
import CrmShell from '@/components/crm/CrmShell';

import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

// Standardized Sidebars
import PipelineFiltersSidebar from '@/components/crm/PipelineFiltersSidebar';
import PipelineLeadSidebar from '@/components/crm/PipelineLeadSidebar';

import { 
    PIPELINE_STAGES, 
    STAGE_LABEL, 
    SOURCES, 
    STAGE_PROGRESS 
} from './constants';
import { PipelineKanbanBoard } from '@/components/crm/PipelineKanbanBoard';

export default function ConsolidationPipelinePage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [leads, setLeads] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_pipeline_view', 'board'));
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
    const [selectedLead, setSelectedLead] = useState<any>(null);
    const { pushSidebarPanel, resetSidebarStack } = useSidebarLayers();

    const handleLeadSelect = useCallback((lead: any) => {
        setSelectedLead(lead);
    }, []);
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('crm_pipeline_wiki_notes', {
        title: 'Wiki del pipeline CRM',
    });

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
                    onClick={(e) => { e.stopPropagation(); handleLeadSelect(row.original); }}
                    className="p-1.5 rounded-lg text-slate-300 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-950/40 transition-all"
                >
                    <ArrowRight size={14} />
                </button>
            )
        }
    ], [handleLeadSelect]);

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

    const groupedByDate = useMemo(() => {
        const map: Record<string, { label: string; items: any[] }> = {};
        for (const lead of filteredLeads) {
            const date = lead.created_at ? new Date(lead.created_at) : new Date();
            const isoKey = date.toISOString().slice(0, 10);
            const label = date.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
            if (!map[isoKey]) map[isoKey] = { label, items: [] };
            map[isoKey].items.push(lead);
        }
        return Object.entries(map).sort((a, b) => b[0].localeCompare(a[0]));
    }, [filteredLeads]);



    // ── Push lead detail panel when a lead is selected ──────────────────────────
    useEffect(() => {
        if (!selectedLead) return;
        pushSidebarPanel({
            id: `pipeline-lead-${selectedLead.id}`,
            title: selectedLead.first_name + ' ' + selectedLead.last_name,
            onBack: () => setSelectedLead(null),
            content: (
                <PipelineLeadSidebar 
                    lead={selectedLead}
                    stages={PIPELINE_STAGES}
                    onUpdateStage={(leadId, newStage) => {
                        handleUpdateStage(leadId, newStage);
                        setSelectedLead((prev: any) => ({ ...prev, stage: newStage }));
                    }}
                    onViewFullProfile={(id) => router.push(`/crm/contacts/${id}`)}
                />
            )
        });
    }, [selectedLead, pushSidebarPanel, router, handleUpdateStage]);

    // ── Push filters panel when no lead is selected (Level 3) ─────────────────
    useEffect(() => {
        if (selectedLead) return; 
        pushSidebarPanel({
            id: 'pipeline-filters',
            title: 'Pipeline de Consolidación',
            content: (
                <PipelineFiltersSidebar 
                    stats={stats}
                    search={search}
                    onSearchChange={setSearch}
                />
            )
        });
    }, [stats, search, selectedLead, pushSidebarPanel]);

    // Reset when unmounting pipeline
    useEffect(() => {
        setTimeout(() => resetSidebarStack(), 500); // Small delay allows smooth transitions when navigating away
        return () => resetSidebarStack();
    }, [resetSidebarStack]);

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
                { label: 'Consolidación', icon: Users },
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
                        { id: 'call', label: 'Registrar Llamada', icon: Phone, onClick: () => router.push('/crm/tasks/assign') },
                        { id: 'mail', label: 'Enviar Email', icon: Mail, onClick: () => router.push('/crm/messaging') }
                    ]}
                />
            }
        >
            <div className="flex flex-col md:flex-row h-full w-full overflow-hidden">
                {/* ── Main Board ── */}
                <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-50/50 dark:bg-[#1a1b1d]">
                    <main className="flex-1 overflow-hidden flex flex-col">
                        <AnimatePresence mode="wait">
                            {viewType === 'board' || viewType === 'kanban' ? (
                                <motion.div key="board" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 overflow-hidden">
                                    <PipelineKanbanBoard
                                        leads={filteredLeads}
                                        onLeadClick={handleLeadSelect}
                                        onDropLead={handleUpdateStage}
                                        onNewLead={(s) => {
                                            if (s) setNewLeadForm(prev => ({ ...prev, stage: s }));
                                            setIsNewLeadDrawerOpen(true);
                                        }}
                                    />
                                </motion.div>
                            ) : viewType === 'grid' ? (
                                <motion.div key="grid" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex-1 p-6 overflow-y-auto">
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {filteredLeads.map((lead: any) => {
                                            const stage = PIPELINE_STAGES.find(s => s.value === lead.stage);
                                            return (
                                                <div
                                                    key={lead.id}
                                                    onClick={() => handleLeadSelect(lead)}
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
                            ) : viewType === 'calendar' ? (
                                <motion.div key="calendar" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex-1 p-6 overflow-y-auto space-y-4">
                                    {groupedByDate.length === 0 ? (
                                        <div className="rounded-2xl border border-dashed border-slate-200 dark:border-white/10 p-10 text-center text-slate-400">Sin actividad de pipeline</div>
                                    ) : groupedByDate.map(([key, payload]) => (
                                        <div key={key} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4">
                                            <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">{payload.label}</p>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                {payload.items.map((lead: any) => (
                                                    <button key={lead.id} onClick={() => setSelectedLead(lead)} className="rounded-xl border border-slate-200 dark:border-white/10 px-3 py-2 text-left hover:border-blue-300 dark:hover:border-blue-700 transition-all">
                                                        <p className="text-sm font-black text-slate-800 dark:text-slate-100">{lead.first_name} {lead.last_name}</p>
                                                        <p className="text-[10px] text-slate-400">{STAGE_LABEL[lead.stage] ?? lead.stage}</p>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </motion.div>
                            ) : viewType === 'gantt' ? (
                                <motion.div key="gantt" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex-1 p-6 overflow-y-auto">
                                    <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Evolucion de prospectos</p>
                                        {filteredLeads.map((lead: any) => (
                                            <div key={lead.id} className="space-y-1">
                                                <div className="flex items-center justify-between text-[11px]">
                                                    <span className="font-bold text-slate-700 dark:text-slate-300">{lead.first_name} {lead.last_name}</span>
                                                    <span className="font-black text-slate-400">{STAGE_PROGRESS[lead.stage] ?? 0}%</span>
                                                </div>
                                                <div className="h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                                                    <div className="h-full bg-blue-600" style={{ width: `${STAGE_PROGRESS[lead.stage] ?? 0}%` }} />
                                                </div>
                                            </div>
                                        ))}
                                        {filteredLeads.length === 0 && <div className="py-8 text-center text-[10px] font-bold uppercase tracking-widest text-slate-400">Sin prospectos</div>}
                                    </div>
                                </motion.div>
                            ) : viewType === 'wiki' ? (
                                <motion.div key="wiki" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex-1 p-8 overflow-y-auto space-y-8 max-w-6xl mx-auto">
                                    {/* Wiki Header */}
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h2 className="text-2xl font-black text-slate-900 dark:text-white flex items-center gap-3 italic uppercase">
                                                <FileText className="text-blue-600" size={28} />
                                                Manual de Consolidación
                                            </h2>
                                            <p className="text-slate-500 font-medium text-sm mt-1">Playbooks pastorales y acuerdos de nivel de servicio (SLA)</p>
                                        </div>
                                        <div className="px-5 py-2 rounded-2xl bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-700/30 flex items-center gap-2">
                                            <Sparkles size={16} className="text-blue-600" />
                                            <span className="text-[10px] font-black text-blue-700 dark:text-blue-300 uppercase tracking-widest">Guía de Consolidación IA</span>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                        {/* Playbooks Section */}
                                        <div className="lg:col-span-2 space-y-6">
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                {[
                                                    { title: 'Primer Encuentro', icon: Users, desc: 'Contactar en menos de 24h. Usar tono cálido y empático.', color: 'text-blue-500 bg-blue-50' },
                                                    { title: 'Cierre de Etapa', icon: Target, desc: 'Validar disposición al bautismo o membresía activa.', color: 'text-emerald-500 bg-emerald-50' }
                                                ].map((card, i) => (
                                                    <div key={i} className="p-6 rounded-[2rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 shadow-sm hover:shadow-xl transition-all group">
                                                        <div className={clsx("size-10 rounded-xl flex items-center justify-center mb-4 transition-transform group-hover:scale-110", card.color.split(' ')[1])}>
                                                            <card.icon className={card.color.split(' ')[0]} size={20} />
                                                        </div>
                                                        <h4 className="font-black text-slate-800 dark:text-white mb-2 uppercase italic">{card.title}</h4>
                                                        <p className="text-xs text-slate-500 leading-relaxed font-medium">{card.desc}</p>
                                                    </div>
                                                ))}
                                            </div>

                                            {/* Notes Area with Premium Styling */}
                                            <div className="p-1 rounded-[2.5rem] bg-gradient-to-br from-blue-500/10 via-transparent to-indigo-500/10">
                                                <div className="p-6 rounded-[2.4rem] bg-white dark:bg-[#1e1f21] border border-white/20 shadow-2xl space-y-4">
                                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] block pl-1">Notas Dinámicas de Proceso</label>
                                                    <textarea
                                                        value={wikiNotes}
                                                        onChange={(e) => setWikiNotes(e.target.value)}
                                                        placeholder="Documenta aquí lineamientos específicos de tu sede o equipo..."
                                                        className="w-full min-h-[400px] border-none bg-transparent outline-none text-slate-700 dark:text-slate-200 font-medium leading-loose resize-none placeholder-slate-300"
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        {/* SLA & Stats Sidebar */}
                                        <div className="space-y-6">
                                            <div className="p-6 rounded-[2rem] bg-slate-900 text-white shadow-2xl relative overflow-hidden">
                                                <div className="absolute top-0 right-0 p-4 opacity-10">
                                                    <Clock size={80} />
                                                </div>
                                                <h4 className="font-black text-[10px] tracking-[0.25em] uppercase text-blue-400 mb-4 relative z-10">Tiempos de Respuesta (SLA)</h4>
                                                <div className="space-y-4 relative z-10">
                                                    {[
                                                        { label: 'Nuevo → Llamado', time: '24 Horas', progress: 100 },
                                                        { label: 'Llamado → Visita', time: '3 Días', progress: 75 },
                                                        { label: 'Visita → Mentoría', time: '7 Días', progress: 50 },
                                                    ].map((item, i) => (
                                                        <div key={i} className="space-y-1">
                                                            <div className="flex justify-between text-[11px] font-bold">
                                                                <span className="text-slate-400">{item.label}</span>
                                                                <span>{item.time}</span>
                                                            </div>
                                                            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                                                                <div className="h-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" style={{ width: `${item.progress}%` }} />
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            <div className="p-6 rounded-[2rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10">
                                                <h4 className="font-black text-[10px] tracking-[0.25em] uppercase text-slate-500 mb-4">Ayuda de Sistema</h4>
                                                <div className="space-y-3">
                                                    <div className="flex items-center gap-3 text-xs font-bold text-slate-600 dark:text-slate-300">
                                                        <div className="size-2 rounded-full bg-blue-500" />
                                                        Arrastra para mover etapas
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs font-bold text-slate-600 dark:text-slate-300">
                                                        <div className="size-2 rounded-full bg-amber-500" />
                                                        Click para ver detalles
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            ) : viewType === 'table' || viewType === 'list' ? (
                                <motion.div key="list" className="flex-1 overflow-y-auto bg-white dark:bg-[#1e1f21]">
                                    <DataTable
                                        data={filteredLeads}
                                        columns={columns}
                                        onRowClick={(l) => handleLeadSelect(l)}
                                    />
                                </motion.div>
                            ) : null}
                        </AnimatePresence>
                    </main>
                </div>
            </div>

            {/* ─── Drawer: Nuevo Lead ─── */}
            <WorkspaceDrawer
                isOpen={isNewLeadDrawerOpen}
                onClose={() => setIsNewLeadDrawerOpen(false)}
                title="Nuevo Prospecto"
                subtitle="Registrar en el pipeline de consolidación"
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




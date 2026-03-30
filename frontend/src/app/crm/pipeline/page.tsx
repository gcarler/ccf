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
    User
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const PIPELINE_STAGES: StatusOption[] = [
    { label: 'NUEVO', value: 'new', color: 'bg-blue-500', text: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'POR LLAMAR', value: 'call', color: 'bg-amber-500', text: 'text-amber-600', bg: 'bg-amber-50' },
    { label: 'VISITA', value: 'visit', color: 'bg-purple-500', text: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'DISCIPULADO', value: 'discipleship', color: 'bg-indigo-500', text: 'text-indigo-600', bg: 'bg-indigo-50' },
    { label: 'CONSOLIDADO', value: 'consolidated', color: 'bg-emerald-500', text: 'text-emerald-600', bg: 'bg-emerald-50' },
];

export default function ConsolidationPipelinePage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [leads, setLeads] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [viewType, setViewType] = useState<any>('board');
    const [selectedLead, setSelectedLead] = useState<any>(null);

    const fetchPipeline = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/crm/consolidation/pipeline', { token });
            if (Array.isArray(data)) setLeads(data);
        } catch (err) { 
            console.error(err);
            setLeads([
                { id: 1, first_name: 'Ricardo', last_name: 'Mendez', phone: '+57 300 123 4567', stage: 'new', source: 'Web' },
                { id: 2, first_name: 'Elena', last_name: 'Rodriguez', phone: '+57 311 987 6543', stage: 'call', source: 'Visitante' },
            ]);
        }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => { fetchPipeline(); }, [fetchPipeline]);

    const handleUpdateStage = useCallback(async (leadId: number, newStage: string) => {
        try {
            await apiFetch(`/crm/consolidation/pipeline/${leadId}`, {
                method: 'PATCH', token, body: { stage: newStage }
            });
            addToast(`Estado actualizado a ${newStage.toUpperCase()}`, 'success');
            fetchPipeline();
        } catch (err) { addToast('Error al actualizar etapa', 'error'); }
    }, [token, addToast, fetchPipeline]);

    const columns = useMemo<ColumnDef<any>[]>(() => [
        { 
            accessorKey: 'name', 
            header: 'Nombre / Prospecto', 
            size: 300,
            cell: ({ row }) => (
                <div className="flex items-center gap-4">
                    <div className="size-10 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-600 font-black text-xs">
                        {row.original.first_name[0]}{row.original.last_name[0]}
                    </div>
                    <div>
                        <p className="font-bold text-slate-800 dark:text-white leading-none mb-1">{row.original.first_name} {row.original.last_name}</p>
                        <p className="text-[10px] font-medium text-slate-400 uppercase tracking-widest">{row.original.phone}</p>
                    </div>
                </div>
            )
        },
        { accessorKey: 'stage', header: 'Etapa' }
    ], []);

    const sidebarSections = [
        { id: 'all', label: 'Todos los Prospectos', icon: Users, href: '/crm/pipeline' },
        { id: 'assigned', label: 'Mis Asignados', icon: Target, href: '/crm/pipeline?filter=mine' },
        { id: 'history', label: 'Historial', icon: Clock, href: '/crm/pipeline/history' },
    ];

    const leadSidebarContent = selectedLead ? (
        <div className="flex flex-col h-full overflow-hidden">
            <div className="p-8 border-b border-slate-100 dark:border-white/5 space-y-4 bg-slate-50/50 dark:bg-black/20">
                <div className="size-16 rounded-3xl bg-blue-600 flex items-center justify-center text-white shadow-xl">
                    <User size={32} />
                </div>
                <div>
                    <h3 className="text-xl font-black tracking-tight text-slate-800 dark:text-white">{selectedLead.first_name} {selectedLead.last_name}</h3>
                    <p className="text-[10px] font-bold text-blue-500 uppercase tracking-[0.2em]">{selectedLead.stage}</p>
                </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
                <button className="w-full flex items-center gap-3 px-4 py-3 bg-white dark:bg-white/5 rounded-2xl border border-slate-200 dark:border-white/10 text-xs font-bold hover:bg-slate-50 transition-all"><Phone size={16} /> Registro de Llamada</button>
                <button className="w-full flex items-center gap-3 px-4 py-3 bg-white dark:bg-white/5 rounded-2xl border border-slate-200 dark:border-white/10 text-xs font-bold hover:bg-slate-50 transition-all"><FileText size={16} /> Notas Pastorales</button>
                <button className="w-full flex items-center gap-3 px-4 py-3 bg-white dark:bg-white/5 rounded-2xl border border-slate-200 dark:border-white/10 text-xs font-bold hover:bg-slate-50 transition-all"><MessageCircle size={16} /> WhatsApp Directo</button>
                <div className="h-[1px] bg-slate-100 dark:bg-white/5 my-4 mx-2" />
                <button className="w-full flex items-center gap-3 px-4 py-3 bg-white dark:bg-white/5 rounded-2xl border border-slate-200 dark:border-white/10 text-xs font-bold hover:bg-slate-50 transition-all"><Send size={16} /> Asignar a Discipulado</button>
            </div>
        </div>
    ) : null;

    if (loading && leads.length === 0) return <div className="p-20 text-center"><Skeleton className="h-12 w-48 mx-auto mb-8" /><div className="grid grid-cols-4 gap-6"><Skeleton className="h-64 rounded-[3rem]" /><Skeleton className="h-64 rounded-[3rem]" /><Skeleton className="h-64 rounded-[3rem]" /><Skeleton className="h-64 rounded-[3rem]" /></div></div>;

    return (
        <div className="flex flex-col md:flex-row h-full w-full bg-slate-50 dark:bg-[#111213] overflow-hidden">
            {/* INNER CONTEXTUAL SIDEBAR (Fixes double layout redundancy) */}
            <motion.div 
                initial={false}
                animate={{ width: 280, opacity: 1 }}
                className="shrink-0 border-r border-slate-200 dark:border-white/5 bg-white dark:bg-[#1e1f21] flex flex-col transition-all z-10 shadow-sm"
            >
                {selectedLead ? (
                    <>
                        <div className="h-10 border-b border-slate-100 dark:border-white/5 flex items-center px-4 gap-3 bg-slate-50 dark:bg-black/20">
                            <button onClick={() => setSelectedLead(null)} className="p-1.5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-lg text-slate-500 transition-all">
                                <ChevronRight size={16} className="rotate-180" />
                            </button>
                            <p className="text-[11px] font-bold text-slate-800 dark:text-white truncate">Volver al Pipeline</p>
                        </div>
                        <div className="flex-1 overflow-hidden">{leadSidebarContent}</div>
                    </>
                ) : (
                    <div className="flex flex-col h-full w-full">
                        <div className="px-6 py-8">
                            <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-6 flex items-center gap-2"><Target size={14}/> Filtros</h2>
                            <div className="space-y-1">
                                {sidebarSections.map(s => (
                                    <button key={s.id} className="w-full flex items-center gap-3 px-4 py-3 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/10 rounded-2xl transition-all">
                                        <s.icon size={16} className={s.id === 'all' ? 'text-blue-500' : 'text-slate-400'} /> 
                                        {s.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </motion.div>

            {/* MAIN CONTENT BOARD */}
            <div className="flex-1 flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden relative">
                <WorkspaceToolbar 
                    breadcrumbs={[
                        { label: 'CRM Pastoral', icon: Users },
                        { label: 'Embudo de Consolidación', icon: Target },
                        ...(selectedLead ? [{ label: `${selectedLead.first_name} ${selectedLead.last_name}`, icon: User }] : [])
                    ]}
                    viewType={viewType} setViewType={setViewType}
                />

                <main className="flex-1 overflow-hidden flex flex-col">
                    <AnimatePresence mode="wait">
                        {viewType === 'board' ? (
                            <motion.div 
                                key="board" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                                className="flex-1 flex gap-6 p-6 overflow-x-auto bg-slate-50/50 dark:bg-black/10"
                            >
                                {PIPELINE_STAGES.map(stage => (
                                    <KanbanColumn 
                                        key={stage.value} 
                                        stage={stage} 
                                        leads={leads.filter(l => l.stage === stage.value)} 
                                        onLeadClick={(l: any) => setSelectedLead(l)}
                                        onDropLead={handleUpdateStage}
                                    />
                                ))}
                            </motion.div>
                        ) : (
                            <motion.div key="list" className="flex-1 p-6">
                                <DataTable data={leads} columns={columns} onRowClick={(l) => setSelectedLead(l)} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </main>
            </div>
        </div>
    );
}

function KanbanColumn({ stage, leads, onLeadClick, onDropLead }: any) {
    return (
        <div 
            className="flex-shrink-0 w-80 flex flex-col gap-6"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
                const leadId = e.dataTransfer.getData('leadId');
                if (leadId) onDropLead(parseInt(leadId), stage.value);
            }}
        >
            <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-3">
                    <div className={clsx("size-2.5 rounded-full", stage.color)} />
                    <h3 className="text-[11px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-[0.2em]">{stage.label}</h3>
                    <span className="px-2 py-0.5 bg-slate-200 dark:bg-white/10 rounded-full text-[9px] font-black text-slate-500">{leads.length}</span>
                </div>
            </div>
            
            <div className="flex-1 space-y-4">
                {leads.map((lead: any) => (
                    <div 
                        key={lead.id} onClick={() => onLeadClick(lead)}
                        draggable onDragStart={(e) => e.dataTransfer.setData('leadId', lead.id.toString())}
                        className="p-6 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2rem] shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all cursor-grab active:cursor-grabbing group"
                    >
                        <p className="font-bold text-slate-800 dark:text-white mb-1">{lead.first_name} {lead.last_name}</p>
                        <p className="text-[10px] text-slate-400 uppercase tracking-widest">{lead.phone}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

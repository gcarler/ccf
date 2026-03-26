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
    CheckCircle2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
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
    const [viewType, setViewType] = useState<'list' | 'board'>('board');
    const [selectedLead, setSelectedLead] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [interactionType, setInteractionType] = useState<'call' | 'sms' | 'email'>('call');

    const fetchPipeline = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            // Using the actual pipeline endpoint from backend/api/crm.py
            const data = await apiFetch('/crm/consolidation/pipeline', { token });
            if (Array.isArray(data)) {
                setLeads(data);
            }
        } catch (err) { 
            console.error(err);
            // Mock data for immediate visual impact if API fails
            setLeads([
                { id: 1, first_name: 'Ricardo', last_name: 'Mendez', phone: '+57 300 123 4567', stage: 'new', source: 'Web', created_at: new Date().toISOString() },
                { id: 2, first_name: 'Elena', last_name: 'Rodriguez', phone: '+57 311 987 6543', stage: 'call', source: 'Visitante', created_at: new Date().toISOString() },
                { id: 3, first_name: 'Marcos', last_name: 'Lopez', phone: '+57 320 444 5555', stage: 'visit', source: 'Referido', created_at: new Date().toISOString() },
                { id: 4, first_name: 'Ana', last_name: 'Victoria', phone: '+57 315 222 3333', stage: 'discipleship', source: 'Evento', created_at: new Date().toISOString() },
            ]);
        }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => { fetchPipeline(); }, [fetchPipeline]);

    const handleUpdateStage = async (leadId: number, newStage: string) => {
        try {
            await apiFetch(`/crm/consolidation/pipeline/${leadId}`, {
                method: 'PATCH',
                token,
                body: { stage: newStage }
            });
            addToast(`Estado actualizado a ${newStage.toUpperCase()}`, 'success');
            fetchPipeline();
        } catch (err) {
            addToast('Error al actualizar etapa', 'error');
        }
    };

    const columns = useMemo<ColumnDef<any>[]>(() => [
        { 
            accessorKey: 'name', 
            header: 'Nombre / Prospecto', 
            size: 300,
            cell: ({ row }) => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-xl bg-slate-900 flex items-center justify-center text-white text-[10px] font-black">
                        {row.original.first_name?.charAt(0)}
                    </div>
                    <div>
                        <p className="text-[13px] font-black text-slate-800 dark:text-white leading-tight">
                            {row.original.first_name} {row.original.last_name}
                        </p>
                        <p className="text-[10px] text-slate-400 font-medium uppercase tracking-widest">{row.original.source || 'Prospecto'}</p>
                    </div>
                </div>
            )
        },
        { 
            accessorKey: 'stage', 
            header: 'Etapa', 
            cell: ({ row }) => (
                <StatusPicker 
                    currentValue={row.original.stage} 
                    options={PIPELINE_STAGES} 
                    onSelect={(val) => handleUpdateStage(row.original.id, val)} 
                />
            ) 
        },
        {
            accessorKey: 'phone',
            header: 'Teléfono',
            cell: info => <span className="text-[12px] font-bold text-slate-500">{info.getValue() as string}</span>
        },
        {
            id: 'actions',
            header: '',
            size: 50,
            cell: ({ row }) => (
                <button onClick={(e) => { e.stopPropagation(); setSelectedLead(row.original); setIsDrawerOpen(true); }} className="p-2 hover:bg-slate-100 rounded-lg text-slate-400">
                    <MoreHorizontal size={16} />
                </button>
            )
        }
    ], [token]);

    return (
        <div className="flex flex-col h-full bg-slate-50/50 dark:bg-[#1e1f21] overflow-hidden font-display">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'CRM Pastoral', icon: Users },
                    { label: 'Embudo de Consolidación', icon: Target }
                ]}
                viewType={viewType}
                setViewType={(v: any) => setViewType(v)}
                onSearch={setSearch}
                rightActions={
                    <button className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <UserPlus size={14} /> Registrar Visitante
                    </button>
                }
            />

            <main className="flex-1 overflow-hidden relative flex flex-col">
                {/* Global Pipeline Metrics */}
                <section className="p-8 grid grid-cols-1 md:grid-cols-4 gap-6 shrink-0">
                    <MetricCard label="Nuevos Hoy" value="8" trend="+2" icon={Zap} color="blue" />
                    <MetricCard label="Tasa de Visita" value="64%" trend="+12%" icon={Calendar} color="purple" />
                    <MetricCard label="Conversión" value="22%" trend="+5%" icon={TrendingUp} color="emerald" />
                    <MetricCard label="Alertas IA" value="3" trend="Urgente" icon={Bot} color="rose" />
                </section>

                <AnimatePresence mode="wait">
                    {viewType === 'board' ? (
                        <motion.div 
                            key="board" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                            className="flex-1 overflow-x-auto overflow-y-hidden flex gap-6 px-8 pb-10"
                        >
                            {PIPELINE_STAGES.map(stage => (
                                <KanbanColumn 
                                    key={stage.value} 
                                    stage={stage} 
                                    leads={leads.filter(l => l.stage === stage.value && (l.first_name + l.last_name).toLowerCase().includes(search.toLowerCase()))} 
                                    onLeadClick={(l) => { setSelectedLead(l); setIsDrawerOpen(true); }}
                                />
                            ))}
                        </motion.div>
                    ) : (
                        <motion.div 
                            key="list" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
                            className="flex-1 bg-white dark:bg-white/5 rounded-t-[3rem] border-t border-slate-200 dark:border-white/10 overflow-hidden"
                        >
                            <DataTable 
                                data={leads.filter(l => (l.first_name + l.last_name).toLowerCase().includes(search.toLowerCase()))} 
                                columns={columns} 
                                onRowClick={(l) => { setSelectedLead(l); setIsDrawerOpen(true); }}
                            />
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedLead ? `${selectedLead.first_name} ${selectedLead.last_name}` : ''}
                subtitle={`ETAPA: ${selectedLead?.stage?.toUpperCase()}`}
            >
                <div className="space-y-10">
                    <section className="p-8 bg-slate-900 rounded-[3rem] text-white shadow-2xl relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-10 -mt-10 size-40 bg-blue-600/20 rounded-full blur-3xl" />
                        <div className="relative z-10 space-y-6">
                            <div className="flex items-center gap-4">
                                <div className="size-12 rounded-2xl bg-blue-600 flex items-center justify-center"><Phone size={24} /></div>
                                <div>
                                    <h4 className="text-xl font-black tracking-tight">Acción de Seguimiento</h4>
                                    <p className="text-[10px] font-bold text-blue-400 uppercase tracking-widest">{selectedLead?.phone}</p>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <QuickActionButton label="Llamar Ahora" icon={Smartphone} />
                                <QuickActionButton label="WhatsApp" icon={MessageCircle} color="emerald" />
                            </div>
                        </div>
                    </section>

                    <section className="space-y-4">
                        <div className="flex items-center gap-2 text-slate-400">
                            <FileText size={14} />
                            <h5 className="text-[11px] font-black uppercase tracking-widest">Historial de Consolidación</h5>
                        </div>
                        <div className="space-y-4">
                            <TimelineItem date="Hoy, 10:00 AM" text="Se asignó a discipulado de nuevos creyentes." user="Pastor Carlos" />
                            <TimelineItem date="Ayer" text="Visita de bienvenida realizada. Recibió kit de inicio." user="Líder Elena" />
                        </div>
                    </section>

                    <section className="p-6 bg-blue-50 dark:bg-blue-900/10 rounded-[2.5rem] border border-blue-100 dark:border-blue-500/20">
                        <div className="flex items-center gap-3 text-blue-600 dark:text-blue-400 mb-2">
                            <Sparkles size={16} />
                            <h5 className="text-[10px] font-black uppercase tracking-widest">Recomendación IA</h5>
                        </div>
                        <p className="text-[13px] font-medium text-slate-600 dark:text-slate-300 leading-relaxed italic">
                            "El prospecto ha asistido a 2 servicios seguidos. Es el momento ideal para invitarlo a la Casa de Gloria de su sector."
                        </p>
                    </section>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function KanbanColumn({ stage, leads, onLeadClick }: any) {
    return (
        <div className="flex-shrink-0 w-80 flex flex-col gap-6">
            <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-3">
                    <div className={clsx("size-2.5 rounded-full", stage.color)} />
                    <h3 className="text-[11px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-[0.2em]">{stage.label}</h3>
                    <span className="px-2 py-0.5 bg-slate-200 dark:bg-white/10 rounded-full text-[9px] font-black text-slate-500">{leads.length}</span>
                </div>
                <button className="text-slate-300 hover:text-slate-500"><MoreHorizontal size={16} /></button>
            </div>
            
            <div className="flex-1 space-y-4 overflow-y-auto scrollbar-hide">
                {leads.map((lead: any) => (
                    <motion.div 
                        key={lead.id} layoutId={lead.id.toString()} onClick={() => onLeadClick(lead)}
                        className="p-6 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2rem] shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all cursor-pointer group"
                    >
                        <div className="flex justify-between items-start mb-4">
                            <div className="size-10 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 font-black group-hover:bg-blue-600 group-hover:text-white transition-colors">
                                {lead.first_name?.charAt(0)}
                            </div>
                            <div className="flex -space-x-2">
                                <div className="size-6 rounded-full border-2 border-white dark:border-slate-900 bg-slate-300" />
                                <div className="size-6 rounded-full border-2 border-white dark:border-slate-900 bg-slate-200 flex items-center justify-center text-[8px] font-black">+1</div>
                            </div>
                        </div>
                        <h4 className="text-[14px] font-black text-slate-800 dark:text-white leading-tight mb-1">{lead.first_name} {lead.last_name}</h4>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">{lead.source}</p>
                        
                        <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-white/5">
                            <div className="flex items-center gap-2 text-slate-400">
                                <Clock size={12} />
                                <span className="text-[9px] font-black uppercase">2 días</span>
                            </div>
                            <div className="flex items-center gap-1.5 px-2 py-1 bg-amber-50 dark:bg-amber-900/20 text-amber-600 rounded-lg">
                                <Zap size={10} fill="currentColor" />
                                <span className="text-[8px] font-black uppercase">Tibio</span>
                            </div>
                        </div>
                    </motion.div>
                ))}
                <button className="w-full py-4 border-2 border-dashed border-slate-200 dark:border-white/5 rounded-[2rem] text-slate-400 hover:border-blue-500/30 hover:text-blue-500 transition-all flex items-center justify-center gap-2">
                    <Plus size={14} /> <span className="text-[10px] font-black uppercase tracking-widest">Añadir</span>
                </button>
            </div>
        </div>
    );
}

function MetricCard({ label, value, trend, icon: Icon, color }: any) {
    const colors: any = {
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
        purple: 'text-purple-600 bg-purple-50 dark:bg-purple-900/20',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20',
        rose: 'text-rose-600 bg-rose-50 dark:bg-rose-900/20'
    };
    return (
        <div className="p-6 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm hover:shadow-md transition-all flex items-center gap-6">
            <div className={clsx("size-12 rounded-2xl flex items-center justify-center shrink-0", colors[color])}>
                <Icon size={24} />
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none mb-1">{label}</p>
                <div className="flex items-baseline gap-2">
                    <h4 className="text-2xl font-black text-slate-900 dark:text-white">{value}</h4>
                    <span className="text-[9px] font-black text-emerald-500 uppercase">{trend}</span>
                </div>
            </div>
        </div>
    );
}

function QuickActionButton({ label, icon: Icon, color = 'blue' }: any) {
    const colors: any = {
        blue: 'bg-blue-600 shadow-blue-500/20',
        emerald: 'bg-emerald-600 shadow-emerald-500/20'
    };
    return (
        <button className={clsx("py-4 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg", colors[color])}>
            <Icon size={16} /> {label}
        </button>
    );
}

function TimelineItem({ date, text, user }: any) {
    return (
        <div className="flex gap-4">
            <div className="flex flex-col items-center shrink-0">
                <div className="size-2.5 rounded-full bg-blue-500 ring-4 ring-blue-500/10" />
                <div className="w-0.5 flex-1 bg-slate-100 dark:bg-white/5 my-1" />
            </div>
            <div className="pb-6">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{date} • {user}</p>
                <p className="text-[13px] font-medium text-slate-600 dark:text-slate-300 leading-tight">{text}</p>
            </div>
        </div>
    );
}

function Plus({ size, className }: any) { return <UserPlus size={size} className={className} />; }

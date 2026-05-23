"use client";

import React, { useState, useEffect } from 'react';
import { 
    Phone, 
    MessageCircle, 
    FileText, 
    CheckCircle2, 
    Zap, 
    ExternalLink,
    User,
    Smartphone,
    History,
    Clock,
    UserCircle2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { STAGE_LABEL } from '@/app/crm/pipeline/constants';

interface PipelineLeadSidebarProps {
    lead: any;
    stages: any[];
    onUpdateStage: (leadId: number, stage: string) => void;
    onViewFullProfile: (leadId: number) => void;
}

export default function PipelineLeadSidebar({ lead, stages, onUpdateStage, onViewFullProfile }: PipelineLeadSidebarProps) {
    const { token } = useAuth();
    const [auditLogs, setAuditLogs] = useState<any[]>([]);
    const [loadingAudit, setLoadingAudit] = useState(false);

    useEffect(() => {
        if (!lead?.id || !token) return;

        const fetchAudit = async () => {
            try {
                setLoadingAudit(true);
                const logs = await apiFetch<any[]>(`/crm/consolidation/pipeline/${lead.id}/audit`, { token });
                setAuditLogs(logs || []);
            } catch (err) {
                console.error("Error fetching audit:", err);
            } finally {
                setLoadingAudit(false);
            }
        };

        fetchAudit();
    }, [lead?.id, token]);

    if (!lead) return null;

    const currentStage = stages.find(s => s.value === lead.stage);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0f1113]">
            {/* Header Cinematic */}
            <div className="p-4 border-b border-slate-100 dark:border-white/[0.04] bg-slate-50/50 dark:bg-[#0f1113]/50 backdrop-blur-3xl shrink-0 relative overflow-hidden rounded-t-lg">
                <div className="absolute top-0 right-0 p-4 opacity-[0.03] pointer-events-none text-blue-600 dark:text-white">
                    <User size={160} />
                </div>

                <div className="flex items-center gap-4 relative z-10">
                    <div className="relative">
                        <motion.div 
                            whileHover={{ scale: 1.05 }}
                            className="size-10 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center font-bold text-xl shadow-2xl shadow-blue-500/30 border-4 border-white dark:border-[#1e1f21]"
                        >
                            {lead.first_name?.[0]}{lead.last_name?.[0]}
                        </motion.div>
                        <div className="absolute -bottom-1 -right-1 size-8 rounded-lg bg-white dark:bg-[#0f1113] border-[3px] border-slate-50 dark:border-[#0f1113] flex items-center justify-center text-blue-600 shadow-xl overflow-hidden">
                            <Zap size={12} fill="currentColor" className="animate-pulse" />
                        </div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-[-0.04em] leading-[0.9] mb-2">
                            {lead.first_name} <br/>
                            <span className="text-blue-600 dark:text-blue-400">{lead.last_name}</span>
                        </h2>
                        <div className="flex items-center gap-2.5">
                            {currentStage && (
                                <span className={clsx('px-3 py-1 rounded-xl text-[9px] font-bold uppercase tracking-wider border flex items-center gap-2', currentStage.bg, currentStage.text, currentStage.border)}>
                                    <div className={clsx("size-1.5 rounded-full animate-pulse", currentStage.color)} />
                                    {currentStage.label}
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-white/40 dark:bg-white/[0.03] backdrop-blur-sm rounded-xl border border-slate-100 dark:border-white/[0.05] shadow-sm mt-3 relative z-10 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-blue-500/10 rounded-xl text-blue-600"><Smartphone size={16} /></div>
                        <div>
                            <p className="text-[11px] font-bold text-slate-800 dark:text-slate-100">{lead.phone || 'Sin teléfono'}</p>
                            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">WhatsApp Disponible</p>
                        </div>
                    </div>
                    <button className="p-2.5 bg-blue-600 text-white rounded-xl shadow-lg shadow-blue-500/20 active:scale-90 transition-all">
                        <Phone size={14} />
                    </button>
                </div>
            </div>

            {/* Actions & Detail */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                <section className="space-y-4">
                    <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wide flex items-center gap-3">
                        <Zap size={14} className="text-blue-600" /> Acciones de Consolidación
                    </h3>
                    <div className="space-y-2">
                        <button
                            onClick={() => onViewFullProfile(lead.id)}
                            className="w-full flex items-center gap-4 p-3 bg-blue-600 text-white rounded-xl text-[11px] font-bold uppercase tracking-[0.1em] hover:bg-blue-700 transition-all shadow-xl shadow-blue-500/20 active:scale-95 group"
                        >
                            <ExternalLink size={16} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" /> 
                            Ver Expediente Completo
                        </button>
                        <div className="grid grid-cols-2 gap-2">
                            <button className="flex items-center justify-center gap-2 p-4 bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.05] rounded-lg text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-white/[0.05] transition-all">
                                <MessageCircle size={14} className="text-emerald-500" /> WhatsApp
                            </button>
                            <button className="flex items-center justify-center gap-2 p-4 bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.05] rounded-lg text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-white/[0.05] transition-all">
                                <FileText size={14} className="text-sky-500" /> Notas
                            </button>
                        </div>
                    </div>
                </section>

                <section className="space-y-4">
                    <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wide flex items-center gap-3">
                        <History size={14} className="text-blue-600" /> Modificar Etapa
                    </h3>
                    <div className="grid grid-cols-1 gap-1.5 focus-within:ring-2 focus-within:ring-blue-500/10 p-1.5 bg-slate-50 dark:bg-black/20 rounded-lg border border-slate-100 dark:border-white/[0.05]">
                        {stages.map(s => (
                            <button
                                key={s.value}
                                onClick={() => onUpdateStage(lead.id, s.value)}
                                className={clsx(
                                    "w-full flex items-center gap-3 px-4 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all group",
                                    lead.stage === s.value
                                        ? `${s.bg} ${s.text} shadow-sm border border-current/20`
                                        : 'bg-transparent text-slate-500 hover:bg-white dark:hover:bg-white/5'
                                )}
                            >
                                <div className={clsx("size-1.5 rounded-full", s.color)} />
                                <span className="flex-1 text-left">{s.label}</span>
                                {lead.stage === s.value && <CheckCircle2 size={14} className="animate-pulse" />}
                            </button>
                        ))}
                    </div>
                </section>
                


                <section className="space-y-3 pb-12">
                    <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wide flex items-center gap-3">
                        <History size={14} className="text-blue-600" /> Historial de Actividad
                    </h3>
                    
                    <div className="relative pl-4 space-y-3 before:absolute before:left-0 before:top-2 before:bottom-2 before:w-px before:bg-slate-100 dark:before:bg-white/5">
                        <AnimatePresence mode="popLayout">
                            {auditLogs.length > 0 ? (
                                auditLogs.map((log, idx) => (
                                    <motion.div 
                                        key={log.id}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: idx * 0.05 }}
                                        className="relative"
                                    >
                                        <div className="absolute -left-[21px] top-0 size-[13px] rounded-full bg-white dark:bg-[#0f1113] border-2 border-blue-500 shadow-sm z-10" />
                                        
                                        <div className="space-y-2">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] font-bold text-slate-900 dark:text-white uppercase">
                                                        {log.action === 'update_pipeline_lead' ? 'Movimiento de Etapa' : log.action}
                                                    </span>
                                                </div>
                                                <span className="text-[9px] font-bold text-slate-400 uppercase flex items-center gap-1">
                                                    <Clock size={10} /> {new Date(log.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                            
                                            <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.04] text-[11px] leading-relaxed">
                                                <p className="text-slate-600 dark:text-slate-400 font-medium">
                                                    {log.metadata?.stage ? (
                                                        <>Se movió a <span className="font-bold text-blue-600 dark:text-blue-400">{STAGE_LABEL[log.metadata.stage] || log.metadata.stage}</span></>
                                                    ) : (
                                                        'Actualización de datos generales'
                                                    )}
                                                </p>
                                                <div className="mt-2 flex items-center gap-2 text-[9px] font-bold text-slate-400 uppercase tracking-wide">
                                                    <UserCircle2 size={12} /> Responsable: System Audit
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))
                            ) : (
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide pl-2">
                                    {loadingAudit ? 'Cargando registros...' : 'No hay actividad reciente registrada'}
                                </p>
                            )}
                        </AnimatePresence>
                    </div>
                </section>
            </div>
        </div>
    );
}

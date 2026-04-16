"use client";

import React from 'react';
import { 
    Phone, 
    MessageCircle, 
    FileText, 
    CheckCircle2, 
    Zap, 
    ExternalLink,
    ChevronLeft,
    User,
    Mail,
    Smartphone
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface PipelineLeadSidebarProps {
    lead: any;
    stages: any[];
    onUpdateStage: (leadId: number, stage: string) => void;
    onViewFullProfile: (leadId: number) => void;
}

export default function PipelineLeadSidebar({ lead, stages, onUpdateStage, onViewFullProfile }: PipelineLeadSidebarProps) {
    if (!lead) return null;

    const currentStage = stages.find(s => s.value === lead.stage);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0f1113]">
            {/* Header Cinematic */}
            <div className="p-8 border-b border-slate-100 dark:border-white/[0.04] bg-slate-50/50 dark:bg-[#0f1113]/50 backdrop-blur-3xl shrink-0 relative overflow-hidden rounded-t-[2.5rem]">
                <div className="absolute top-0 right-0 p-12 opacity-[0.03] pointer-events-none text-blue-600 dark:text-white">
                    <User size={160} />
                </div>

                <div className="flex items-center gap-6 relative z-10">
                    <div className="relative">
                        <motion.div 
                            whileHover={{ scale: 1.05 }}
                            className="size-20 rounded-[2.2rem] bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center font-black text-3xl shadow-2xl shadow-blue-500/30 border-4 border-white dark:border-[#1e1f21]"
                        >
                            {lead.first_name?.[0]}{lead.last_name?.[0]}
                        </motion.div>
                        <div className="absolute -bottom-1 -right-1 size-8 rounded-2xl bg-white dark:bg-[#0f1113] border-[3px] border-slate-50 dark:border-[#0f1113] flex items-center justify-center text-blue-600 shadow-xl overflow-hidden">
                            <Zap size={12} fill="currentColor" className="animate-pulse" />
                        </div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-[-0.04em] leading-[0.9] mb-2">
                            {lead.first_name} <br/>
                            <span className="text-blue-600 dark:text-blue-400">{lead.last_name}</span>
                        </h2>
                        <div className="flex items-center gap-2.5">
                            {currentStage && (
                                <span className={clsx('px-3 py-1 rounded-xl text-[9px] font-black uppercase tracking-[0.15em] border flex items-center gap-2', currentStage.bg, currentStage.text, currentStage.border)}>
                                    <div className={clsx("size-1.5 rounded-full animate-pulse", currentStage.color)} />
                                    {currentStage.label}
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-white/40 dark:bg-white/[0.03] backdrop-blur-sm rounded-3xl border border-slate-100 dark:border-white/[0.05] shadow-sm mt-8 relative z-10 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-blue-500/10 rounded-xl text-blue-600"><Smartphone size={16} /></div>
                        <div>
                            <p className="text-[11px] font-black text-slate-800 dark:text-slate-100">{lead.phone || 'Sin teléfono'}</p>
                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">WhatsApp Disponible</p>
                        </div>
                    </div>
                    <button className="p-2.5 bg-blue-600 text-white rounded-xl shadow-lg shadow-blue-500/20 active:scale-90 transition-all">
                        <Phone size={14} />
                    </button>
                </div>
            </div>

            {/* Actions & Detail */}
            <div className="flex-1 overflow-y-auto p-8 space-y-10 custom-scrollbar">
                <section className="space-y-4">
                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-3">
                        <Zap size={14} className="text-blue-600" /> Acciones Pastorales
                    </h3>
                    <div className="space-y-2">
                        <button
                            onClick={() => onViewFullProfile(lead.id)}
                            className="w-full flex items-center gap-4 p-5 bg-blue-600 text-white rounded-[2rem] text-[11px] font-black uppercase tracking-[0.1em] hover:bg-blue-700 transition-all shadow-xl shadow-blue-500/20 active:scale-95 group"
                        >
                            <ExternalLink size={16} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" /> 
                            Ver Expediente Completo
                        </button>
                        <div className="grid grid-cols-2 gap-2">
                            <button className="flex items-center justify-center gap-2 p-4 bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.05] rounded-[1.8rem] text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-white/[0.05] transition-all">
                                <MessageCircle size={14} className="text-emerald-500" /> WhatsApp
                            </button>
                            <button className="flex items-center justify-center gap-2 p-4 bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.05] rounded-[1.8rem] text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-white/[0.05] transition-all">
                                <FileText size={14} className="text-purple-500" /> Notas
                            </button>
                        </div>
                    </div>
                </section>

                <section className="space-y-4">
                    <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-3">
                        <History size={14} className="text-blue-600" /> Modificar Etapa
                    </h3>
                    <div className="grid grid-cols-1 gap-1.5 focus-within:ring-2 focus-within:ring-blue-500/10 p-1.5 bg-slate-50 dark:bg-black/20 rounded-[2.2rem] border border-slate-100 dark:border-white/[0.05]">
                        {stages.map(s => (
                            <button
                                key={s.value}
                                onClick={() => onUpdateStage(lead.id, s.value)}
                                className={clsx(
                                    "w-full flex items-center gap-3 px-4 py-3.5 rounded-[1.8rem] text-[10px] font-black uppercase tracking-widest transition-all group",
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
                
                {lead.notes && (
                    <section className="space-y-4">
                        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-3">
                            <Mail size={14} className="text-blue-600" /> Notas de Captación
                        </h3>
                        <div className="p-6 bg-amber-50 dark:bg-amber-900/5 border border-amber-100 dark:border-amber-500/10 rounded-[2.2rem]">
                            <p className="text-xs font-bold text-amber-900 dark:text-amber-200 leading-relaxed italic group-hover:not-italic transition-all">
                                &quot;{lead.notes}&quot;
                            </p>
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
}

function History({ size, className }: { size: number, className: string }) {
    return <Zap size={size} className={className} />;
}

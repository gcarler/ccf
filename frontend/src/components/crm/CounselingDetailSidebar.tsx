"use client";

import React, { useState, useEffect } from 'react';
import { 
    X as CloseIcon, 
    Heart, 
    History, 
    Zap, 
    XCircle, 
    Eye, 
    EyeOff,
    CheckCircle2,
    Lock,
    User,
    BookOpen,
    Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import clsx from 'clsx';

interface CounselingDetailSidebarProps {
    session: any;
    onUpdate?: () => void;
    onClose?: () => void;
}

export default function CounselingDetailSidebar({ session: initialSession, onUpdate, onClose }: CounselingDetailSidebarProps) {
    const { token } = useAuth();
    const { addToast } = useToast();
    
    const [session, setSession] = useState(initialSession);
    const [loading, setLoading] = useState(false);
    const [showNotes, setShowNotes] = useState(false);
    const [activeTab, setActiveTab] = useState<'details' | 'timeline' | 'ai'>('details');

    useEffect(() => {
        if (!initialSession?.id) return;
        fetchSessionDetails(initialSession.id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialSession]);

    const fetchSessionDetails = async (id: number) => {
        setLoading(true);
        try {
            const data = await apiFetch(`/crm/counseling/${id}`, { token });
            if (data) setSession(data);
        } catch (err) {
            console.error("Error fetching session details", err);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateStatus = async (status: string) => {
        if (!token) return;
        try {
            await apiFetch(`/crm/counseling/${session.id}`, { 
                method: 'PATCH', 
                token, 
                body: { status } 
            });
            addToast(`Estado actualizado a ${status}`, 'success');
            fetchSessionDetails(session.id);
            if (onUpdate) onUpdate();
        } catch {
            addToast('Error al actualizar estado', 'error');
        }
    };

    if (loading && !session) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-4">
                <Loader2 className="animate-spin text-sky-600" size={32} />
                <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Cargando expediente...</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0f1113]">
            {/* Header Cinematic */}
            <div className="p-4 border-b border-slate-100 dark:border-white/[0.04] bg-slate-50/50 dark:bg-[#0f1113]/50 backdrop-blur-3xl shrink-0 relative overflow-hidden rounded-t-lg">
                <div className="absolute top-0 right-0 p-4 opacity-[0.03] pointer-events-none text-sky-600 dark:text-white">
                    <Heart size={160} />
                </div>
                
                <div className="flex justify-between items-start mb-3 relative z-10">
                    <button 
                        onClick={onClose} 
                        className="p-2.5 bg-white dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 rounded-lg text-slate-400 hover:text-slate-900 dark:hover:text-white transition-all shadow-sm border border-slate-100 dark:border-white/5 active:scale-95"
                    >
                        <CloseIcon size={20} />
                    </button>
                    <div className="flex gap-2">
                        <span className={clsx(
                            "px-3 py-2.5 rounded-lg text-[10px] font-bold uppercase tracking-wider flex items-center gap-2 shadow-lg",
                            session.status === 'Realizada' ? "bg-emerald-600 text-white shadow-emerald-500/20" : "bg-amber-500 text-white shadow-amber-500/20"
                        )}>
                            <div className="size-1.5 rounded-full bg-white animate-pulse" />
                            {session.status}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-4 relative z-10">
                    <motion.div 
                        whileHover={{ scale: 1.05 }}
                        className="size-10 rounded-lg bg-gradient-to-br from-sky-600 to-indigo-700 flex items-center justify-center text-white shadow-2xl shadow-sky-500/30 border-4 border-white dark:border-[#1e1f21]"
                    >
                        <Heart size={28} />
                    </motion.div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-[-0.04em] leading-[0.9] mb-2">
                            {session.topic || 'Sin tema <br/> asignado'}
                        </h2>
                        <p className="text-[11px] font-bold text-slate-400 flex items-center gap-1.5 uppercase tracking-wide opacity-70">
                            <span className="p-1.5 bg-sky-500/10 rounded-lg text-sky-600"><User size={12} /></span> {session.member_name || 'Miembro CCF'}
                        </p>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-3 relative z-10">
                    <div className="bg-white/40 dark:bg-white/[0.03] backdrop-blur-sm p-4 rounded-xl border border-slate-100 dark:border-white/[0.05] shadow-sm">
                        <p className="text-[8px] font-bold text-slate-400 uppercase tracking-wide mb-1.5">Fecha de Sesión</p>
                        <p className="text-[11px] font-bold text-slate-800 dark:text-slate-100 uppercase tracking-tight">
                            {session.scheduled_at ? new Date(session.scheduled_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Pendiente'}
                        </p>
                    </div>
                    <div className="bg-white/40 dark:bg-white/[0.03] backdrop-blur-sm p-4 rounded-xl border border-slate-100 dark:border-white/[0.05] shadow-sm">
                        <p className="text-[8px] font-bold text-slate-400 uppercase tracking-wide mb-1.5">Duración Est.</p>
                        <p className="text-[11px] font-bold text-slate-800 dark:text-slate-100 uppercase tracking-tight">{session.duration_minutes || 60} MINUTOS</p>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex px-4 border-b border-slate-50 dark:border-white/[0.04] shrink-0 bg-white dark:bg-transparent overflow-x-auto no-scrollbar sticky top-0 z-30">
                {[
                    { id: 'details', label: 'Expediente', icon: BookOpen },
                    { id: 'timeline', label: 'Historial', icon: History },
                    { id: 'ai', label: 'Análisis IA', icon: Zap }
                ].map(tab => (
                    <button 
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)} 
                        className={clsx(
                            "px-3 py-2 text-[10px] font-bold uppercase tracking-wide border-b-2 transition-all flex items-center gap-2.5 shrink-0",
                            activeTab === tab.id ? "border-sky-600 text-sky-600" : "border-transparent text-slate-400 hover:text-slate-800 dark:hover:text-white"
                        )}
                    >
                        <tab.icon size={12} className={activeTab === tab.id ? "animate-pulse" : ""} /> {tab.label}
                    </button>
                ))}
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                <AnimatePresence mode="wait">
                    {activeTab === 'details' && (
                        <motion.div key="details" initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="space-y-3">
                            <section className="space-y-4">
                                <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wide flex items-center gap-2">
                                    <BookOpen size={14} className="text-sky-600" /> Resumen
                                </h3>
                                <div className="p-4 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-xl text-sm text-slate-700 dark:text-slate-300 italic leading-relaxed">
                                    &quot;{session.summary || 'No hay un resumen registrado para esta sesión.'}&quot;
                                </div>
                            </section>

                            <section className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wide flex items-center gap-2">
                                        <Lock size={14} className="text-rose-500" /> Notas Confidenciales
                                    </h3>
                                    <button 
                                        onClick={() => setShowNotes(!showNotes)}
                                        className="text-[9px] font-bold text-sky-600 uppercase tracking-wider flex items-center gap-1.5 p-1 px-2.5 bg-sky-50 dark:bg-white/5 rounded-xl border border-sky-100 dark:border-white/10 active:scale-90 transition-all"
                                    >
                                        {showNotes ? <EyeOff size={12} /> : <Eye size={12} />} {showNotes ? 'Ocultar' : 'Revelar Portal'}
                                    </button>
                                </div>
                                <div className="relative group overflow-hidden rounded-xl">
                                    <AnimatePresence>
                                        {!showNotes && (
                                            <motion.div 
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                                exit={{ opacity: 0 }}
                                                className="absolute inset-0 bg-slate-900/10 dark:bg-black/40 backdrop-blur-md z-10 flex flex-col items-center justify-center gap-4 border-2 border-dashed border-slate-200 dark:border-white/10 cursor-pointer"
                                                onClick={() => setShowNotes(true)}
                                            >
                                                <div className="size-9 rounded-lg bg-white dark:bg-white/10 flex items-center justify-center text-slate-400 shadow-xl group-hover:scale-110 transition-transform">
                                                    <Lock size={20} />
                                                </div>
                                                <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">Sesión Encriptada</p>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                    <div className={clsx(
                                        "p-4 rounded-xl border transition-all duration-700 min-h-[140px]",
                                        showNotes 
                                            ? "bg-rose-50 dark:bg-rose-500/[0.03] border-rose-100 dark:border-rose-500/20" 
                                            : "bg-slate-50 dark:bg-white/[0.02] border-slate-100 dark:border-white/[0.05]"
                                    )}>
                                        <p className={clsx(
                                            "text-sm font-medium leading-relaxed transition-all duration-700",
                                            showNotes ? "text-slate-800 dark:text-rose-100 tracking-tight" : "text-transparent"
                                        )}>
                                            {session.confidential_notes || 'Sin notas confidenciales registradas para este encuentro pastoral.'}
                                        </p>
                                    </div>
                                    {showNotes && (
                                        <motion.div 
                                            initial={{ y: -100 }}
                                            animate={{ y: 300 }}
                                            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                                            className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-rose-500/50 to-transparent z-20 pointer-events-none"
                                        />
                                    )}
                                </div>
                            </section>

                            {session.status === 'Pendiente' && (
                                <div className="grid grid-cols-2 gap-3 pt-4">
                                    <button 
                                        onClick={() => handleUpdateStatus('Realizada')}
                                        className="py-2 bg-emerald-600 text-white rounded-lg text-[9px] font-bold uppercase tracking-wide shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2"
                                    >
                                        <CheckCircle2 size={14} /> Completar
                                    </button>
                                    <button 
                                        onClick={() => handleUpdateStatus('Cancelada')}
                                        className="py-2 bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 rounded-lg text-[9px] font-bold uppercase tracking-wide border border-slate-200 dark:border-white/10 flex items-center justify-center gap-2"
                                    >
                                        <XCircle size={14} /> Cancelar
                                    </button>
                                </div>
                            )}
                        </motion.div>
                    )}

                    {activeTab === 'timeline' && (
                        <motion.div key="timeline" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="space-y-3">
                            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Seguimiento Histórico</h3>
                            {session.history?.length > 0 ? (
                                <div className="relative border-l-2 border-slate-100 dark:border-white/5 ml-2 space-y-3 pl-6">
                                    {session.history.map((h: any) => (
                                        <div key={h.id} className="relative">
                                            <div className="absolute -left-[31px] top-1 size-4 rounded-full border-4 border-white dark:border-[#1e1f21] bg-sky-600 shadow-sm" />
                                            <div className="p-4 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/10">
                                                <p className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-1">{h.text}</p>
                                                <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">{h.date}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="p-3 text-center border-2 border-dashed border-slate-100 dark:border-white/10 rounded-xl text-[10px] font-bold uppercase tracking-wide text-slate-300">
                                    Sin historial previo
                                </div>
                            )}
                        </motion.div>
                    )}

                    {activeTab === 'ai' && (
                        <motion.div key="ai" initial={{opacity:0, scale:0.95}} animate={{opacity:1, scale:1}} exit={{opacity:0, scale:0.95}} className="py-2 text-center space-y-3">
                            <div className="size-8 rounded-lg bg-indigo-600 mx-auto flex items-center justify-center text-white shadow-xl">
                                <Zap size={24} fill="currentColor" />
                            </div>
                            <div className="space-y-2">
                                <h4 className="text-sm font-bold dark:text-white uppercase tracking-tighter italic">Análisis Optimus</h4>
                                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-xs mx-auto leading-relaxed">
                                    IA analizando indicadores emocionales para salud espiritual de 360°.
                                </p>
                            </div>
                            <div className="p-4 bg-slate-50 dark:bg-white/5 rounded-xl border border-dashed border-slate-200 dark:border-white/10 flex flex-col items-center gap-4">
                                <Loader2 size={24} className="animate-spin text-indigo-400" />
                                <span className="text-[9px] font-bold uppercase tracking-wide text-slate-400 animate-pulse">Sincronizando Grafo...</span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

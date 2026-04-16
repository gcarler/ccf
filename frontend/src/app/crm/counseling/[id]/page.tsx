"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Heart, MessageSquare, History, ArrowLeft, 
    MoreHorizontal, Edit3, ShieldCheck, Zap, 
    Sparkles, ChevronRight, CheckCircle2,
    Calendar, Clock, AlertCircle, Share2, 
    User, Lock, Eye, EyeOff, Save,
    X, Loader2, BookOpen, Send, TrendingUp
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '../../../context/AuthContext';
import { apiFetch } from '../../../lib/http';
import CrmShell from '../../../components/crm/CrmShell';

const MOCK_SESSION = {
    id: 1,
    member_name: 'Diana Castillo',
    pastor_name: 'Pastor Samuel Torres',
    topic: 'Restauración Familiar y Perdón',
    status: 'Realizada',
    priority: 'ALTA',
    scheduled_at: '2024-04-12T15:30:00Z',
    duration: 60,
    summary: 'Se abordaron temas de estancamiento espiritual relacionados con conflictos no resueltos en el hogar. La sesión fue productiva y se estableció un plan de oración diaria.',
    confidential_notes: 'La persona muestra una disposición genuina pero tiene miedo al rechazo. Se recomienda seguimiento semanal y posible integración a un grupo de sanidad interior.',
    sentiment: 'POSITIVE',
    history: [
        { id: 1, text: 'Sesión inicial - Diagnóstico espiritual', date: 'Hace 2 semanas' },
        { id: 2, text: 'Seguimiento telefónico - Compromiso de oración', date: 'Hace 1 semana' },
        { id: 3, text: 'Sesión presencial - Ministración de perdón', date: 'Hace 2 días' },
    ]
};

export default function CounselingDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const [session, setSession] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [showNotes, setShowNotes] = useState(false);
    const [activeTab, setActiveTab] = useState<'details' | 'timeline' | 'ai'>('details');

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiFetch(`/crm/counseling/${params.id}`, { token }).catch(() => MOCK_SESSION);
            setSession(data || MOCK_SESSION);
        } finally {
            setLoading(false);
        }
    }, [params.id, token]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    if (loading) {
        return (
            <CrmShell breadcrumbs={[{ label: 'Cargando...', icon: Loader2 }]}>
                <div className="flex flex-col items-center justify-center h-full gap-5">
                    <div className="size-14 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
                    <p className="text-[10px] font-black uppercase tracking-[0.5em] text-slate-400 animate-pulse">Sincronizando Expediente Confidencial...</p>
                </div>
            </CrmShell>
        );
    }

    if (!session) return null;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM Pastoral', icon: Heart },
                { label: 'Consejería', icon: MessageSquare, href: '/crm/counseling' },
                { label: session.topic, icon: Lock }
            ]}
        >
            <div className="h-full flex flex-col overflow-hidden bg-white dark:bg-[#0b0d11]">
                
                {/* ─── Confidential Header ─── */}
                <header className="shrink-0 p-8 lg:p-12 border-b border-slate-100 dark:border-white/5 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 -mr-20 -mt-20 size-96 bg-purple-600/5 dark:bg-purple-600/10 rounded-full blur-[100px] group-hover:bg-purple-600/20 transition-all duration-1000" />
                    
                    <div className="relative z-10 flex flex-col lg:flex-row lg:items-end justify-between gap-8">
                        <div className="space-y-6">
                            <button 
                                onClick={() => router.back()}
                                className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-purple-600 transition-all"
                            >
                                <ArrowLeft size={14} /> Volver al Registro
                            </button>

                            <div className="flex items-center gap-6">
                                <div className="size-20 rounded-[2.5rem] bg-gradient-to-tr from-purple-600 to-indigo-700 flex items-center justify-center text-white shadow-2xl shadow-purple-500/20 relative">
                                    <Heart size={32} />
                                    <div className="absolute -bottom-1 -right-1 size-8 bg-black rounded-2xl border-4 border-white dark:border-[#0b0d11] flex items-center justify-center">
                                        <Lock size={12} className="text-purple-400" />
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-3">
                                        <h1 className="text-4xl lg:text-5xl font-black tracking-tighter text-slate-900 dark:text-white uppercase italic leading-none truncate max-w-xl">
                                            {session.topic}
                                        </h1>
                                        <span className={clsx(
                                            "px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest",
                                            session.status === 'Realizada' ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10" : "bg-amber-50 text-amber-600"
                                        )}>
                                            {session.status}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-slate-500 dark:text-slate-400 font-medium">
                                        <p className="flex items-center gap-1.5"><User size={16} className="text-purple-500" /> {session.member_name}</p>
                                        <span className="size-1 rounded-full bg-slate-300 dark:bg-white/10" />
                                        <p className="flex items-center gap-1.5"><Lock size={16} /> Prioridad {session.priority}</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <button className="p-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-2xl text-slate-400 hover:text-purple-600 transition-all shadow-sm">
                                <Share2 size={20} />
                            </button>
                            <button className="px-8 py-4 bg-slate-900 dark:bg-purple-600 text-white text-[11px] font-black uppercase tracking-widest rounded-3xl shadow-2xl shadow-purple-500/20 hover:scale-105 active:scale-95 transition-all flex items-center gap-3">
                                <Save size={18} /> Guardar Cambios
                            </button>
                        </div>
                    </div>

                    {/* Stats / Info Bar */}
                    <div className="mt-12 grid grid-cols-2 lg:grid-cols-4 gap-6 relative z-10">
                        <QuickInfo label="Fecha de Sesión" value={new Date(session.scheduled_at).toLocaleDateString()} icon={Calendar} color="purple" />
                        <QuickInfo label="Duración Real" value={`${session.duration} min`} icon={Clock} color="blue" />
                        <QuickInfo label="Sentimiento IA" value={session.sentiment === 'POSITIVE' ? 'Radiante' : 'Sereno'} icon={TrendingUp} color="emerald" />
                        <QuickInfo label="Responsable" value="Pbro. Samuel Torres" icon={ShieldCheck} color="amber" />
                    </div>
                </header>

                {/* ─── Tab Navigation ─── */}
                <div className="px-8 lg:px-12 border-b border-slate-100 dark:border-white/5 flex gap-10">
                    {['details', 'timeline', 'ai'].map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab as any)}
                            className={clsx(
                                "py-6 text-[11px] font-black uppercase tracking-[0.2em] relative transition-all",
                                activeTab === tab ? "text-purple-600" : "text-slate-400 hover:text-slate-600"
                            )}
                        >
                            {tab === 'details' ? 'Expediente' : tab === 'timeline' ? 'Seguimiento' : 'Análisis Optimus'}
                            {activeTab === tab && (
                                <motion.div layoutId="tab-underline-counsel" className="absolute bottom-0 left-0 right-0 h-1 bg-purple-600 rounded-t-full" />
                            )}
                        </button>
                    ))}
                </div>

                {/* ─── Content Scroll Area ─── */}
                <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12">
                    <AnimatePresence mode="wait">
                        {activeTab === 'details' && (
                            <motion.div 
                                key="details" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                                className="grid grid-cols-1 lg:grid-cols-12 gap-10"
                            >
                                {/* Left Side: Summary & Notes */}
                                <div className="lg:col-span-8 space-y-10">
                                    <section className="space-y-4">
                                        <div className="flex items-center justify-between">
                                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                                <BookOpen size={14} className="text-purple-600" /> Resumen de la Sesión
                                            </h3>
                                        </div>
                                        <div className="p-8 bg-slate-50 dark:bg-white/[0.03] border border-slate-100 dark:border-white/10 rounded-[3rem] text-slate-700 dark:text-slate-300 leading-relaxed text-lg italic">
                                            &quot;{session.summary}&quot;
                                        </div>
                                    </section>

                                    <section className="space-y-6">
                                        <div className="flex items-center justify-between">
                                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                                <Lock size={14} className="text-rose-500" /> Notas Confidenciales de Seguridad
                                            </h3>
                                            <button 
                                                onClick={() => setShowNotes(!showNotes)}
                                                className="flex items-center gap-2 text-[10px] font-black text-purple-600 uppercase tracking-widest"
                                            >
                                                {showNotes ? <EyeOff size={14} /> : <Eye size={14} />} {showNotes ? 'Ocultar' : 'Revelar'} Notas
                                            </button>
                                        </div>
                                        <div className={clsx(
                                            "relative p-8 rounded-[3rem] border transition-all duration-700 overflow-hidden",
                                            showNotes 
                                                ? "bg-rose-50 dark:bg-rose-500/5 border-rose-200 dark:border-rose-500/20" 
                                                : "bg-slate-100 dark:bg-white/5 border-slate-200 dark:border-white/10 blur-md select-none pointer-events-none"
                                        )}>
                                            <p className="text-slate-800 dark:text-rose-100 font-medium leading-relaxed">
                                                {showNotes ? session.confidential_notes : "ALTA SEGURIDAD: Haz clic en revelar para visualizar las notas confidenciales."}
                                            </p>
                                            {!showNotes && (
                                                <div className="absolute inset-0 flex items-center justify-center">
                                                    <Lock size={32} className="text-slate-400 opacity-20" />
                                                </div>
                                            )}
                                        </div>
                                    </section>
                                </div>

                                {/* Right Side: Quick Actions & Sidebar Info */}
                                <div className="lg:col-span-4 space-y-8">
                                    <section className="bg-slate-900 rounded-[3rem] p-8 text-white space-y-8 relative overflow-hidden group">
                                        <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform duration-1000">
                                            <ShieldCheck size={100} />
                                        </div>
                                        <div className="relative z-10 space-y-6">
                                            <div className="space-y-1">
                                                <p className="text-[10px] font-black text-purple-400 uppercase tracking-[0.2em]">Próximo Paso Sugerido</p>
                                                <h4 className="text-xl font-black italic tracking-tighter">Inscripción a Materia &quot;Sanidad Interior&quot;</h4>
                                            </div>
                                            <div className="p-5 bg-white/5 rounded-2xl space-y-3">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-2 rounded-full bg-emerald-500" />
                                                    <p className="text-xs font-bold opacity-80 uppercase tracking-widest">Estado: Recomendado</p>
                                                </div>
                                                <p className="text-[10px] opacity-60">La IA ha detectado patrones que sugieren un crecimiento óptimo mediante formación académica específica.</p>
                                            </div>
                                            <button className="w-full py-4 bg-purple-600 hover:bg-purple-500 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-2xl shadow-purple-500/20 transition-all">Generar Referencia</button>
                                        </div>
                                    </section>
                                    
                                    <div className="p-8 bg-slate-50 dark:bg-white/5 rounded-[3rem] border border-slate-200 dark:border-white/10 space-y-6">
                                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Vincular con Miembro</h4>
                                        <div className="flex items-center gap-4 p-4 bg-white dark:bg-black/20 rounded-2xl border border-transparent hover:border-purple-500/30 transition-all cursor-pointer">
                                            <div className="size-10 rounded-xl bg-purple-500 flex items-center justify-center text-white font-black text-xs">DC</div>
                                            <div className="flex-1">
                                                <p className="text-sm font-bold dark:text-white">Diana Castillo</p>
                                                <p className="text-[10px] text-slate-400 uppercase font-black tracking-widest">Ver Perfil CRM</p>
                                            </div>
                                            <ChevronRight size={14} className="text-slate-300" />
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )}

                        {activeTab === 'timeline' && (
                            <motion.div key="timeline" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }} className="space-y-8">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tighter uppercase">HISTORIAL DE ACOMPAÑAMIENTO</h3>
                                    <button className="px-6 py-2.5 bg-purple-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center gap-2">
                                        <Plus size={14} /> Nueva Nota Histórica
                                    </button>
                                </div>
                                <div className="space-y-6 relative ml-6 border-l-2 border-slate-100 dark:border-white/5 pl-10">
                                    {session.history.map((h: any) => (
                                        <div key={h.id} className="relative group">
                                            <div className="absolute -left-14 top-2 size-8 rounded-xl bg-white dark:bg-slate-900 border-2 border-slate-100 dark:border-white/10 flex items-center justify-center text-purple-500 group-hover:bg-purple-600 group-hover:text-white transition-all">
                                                <History size={14} />
                                            </div>
                                            <div className="p-8 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[2.5rem] hover:shadow-xl transition-all">
                                                <p className="text-lg font-black text-slate-800 dark:text-white uppercase leading-none mb-2">{h.text}</p>
                                                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">{h.date}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                        
                        {activeTab === 'ai' && (
                             <motion.div key="ai" className="py-20 text-center space-y-8">
                                <div className="size-24 rounded-[3rem] bg-indigo-600 mx-auto flex items-center justify-center text-white shadow-2xl shadow-indigo-500/20">
                                    <Zap size={40} fill="currentColor" />
                                </div>
                                <div className="space-y-2">
                                    <h3 className="text-3xl font-black text-slate-900 dark:text-white italic uppercase tracking-tighter">ANÁLISIS DE OPTIMUS BRAIN</h3>
                                    <p className="text-slate-400 max-w-lg mx-auto text-sm">Nuestro motor de inteligencia está analizando los descriptores emocionales de esta sesión para ofrecerte una perspectiva de 360° sobre la salud espiritual del acompañado.</p>
                                </div>
                                <div className="bg-slate-50 dark:bg-white/5 rounded-[4rem] p-12 border border-dashed border-slate-200 dark:border-white/10 max-w-2xl mx-auto flex flex-col items-center gap-6">
                                    <Loader2 size={32} className="animate-spin text-indigo-400" />
                                    <p className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-400 animate-pulse">Generando Grafo de Emociones...</p>
                                </div>
                             </motion.div>
                        )}
                    </AnimatePresence>
                </main>
            </div>
        </CrmShell>
    );
}

function QuickInfo({ label, value, icon: Icon, color }: any) {
    const colors: any = {
        purple: 'text-purple-600 bg-purple-50 dark:bg-purple-500/10',
        blue: 'text-blue-600 bg-blue-50 dark:bg-blue-500/10',
        emerald: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10',
        amber: 'text-amber-600 bg-amber-50 dark:bg-amber-500/10'
    };
    return (
        <div className="p-8 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[3rem] shadow-sm flex flex-col gap-6 group hover:shadow-xl transition-all">
            <div className={clsx("size-12 rounded-2xl flex items-center justify-center transition-transform group-hover:rotate-12", colors[color])}>
                <Icon size={24} />
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</p>
                <h4 className="text-xl font-black text-slate-900 dark:text-white tracking-tighter uppercase leading-none">
                    {value}
                </h4>
            </div>
        </div>
    );
}

function Plus(props: any) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M5 12h14" />
            <path d="M12 5v14" />
        </svg>
    );
}

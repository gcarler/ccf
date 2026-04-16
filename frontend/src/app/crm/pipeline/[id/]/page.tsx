"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Users, 
    Phone, 
    Smartphone, 
    Mail, 
    MapPin, 
    ChevronLeft, 
    Target, 
    Zap, 
    History, 
    MoreHorizontal, 
    CheckCircle2, 
    Clock, 
    MessageSquare, 
    Briefcase,
    Bot,
    Sparkles,
    Calendar,
    ArrowRight,
    Send
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const PIPELINE_STAGES = [
    { label: 'NUEVO', value: 'new', color: 'blue', dot: 'bg-blue-500' },
    { label: 'POR LLAMAR', value: 'call', color: 'amber', dot: 'bg-amber-500' },
    { label: 'VISITA', value: 'visit', color: 'purple', dot: 'bg-purple-500' },
    { label: 'DISCIPULADO', value: 'discipleship', color: 'indigo', dot: 'bg-indigo-500' },
    { label: 'CONSOLIDADO', value: 'consolidated', color: 'emerald', dot: 'bg-emerald-500' },
];

export default function LeadDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();

    const [lead, setLead] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('perfil');
    const [isUpdating, setIsUpdating] = useState(false);

    const fetchLead = useCallback(async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            const data = await apiFetch<any>(`/crm/consolidation/pipeline/${id}`, { token });
            setLead({
                ...data,
                fullName: `${data.first_name} ${data.last_name}`,
                interactions: [
                    { id: 1, type: 'Cita', text: 'Primera llamada realizada. Miembro interesado en asistir al servicio dominical.', date: 'Hace 1 día', user: 'Ana G.' },
                    { id: 2, type: 'Visita', text: 'Visita a casa programada para el próximo martes.', date: 'Programado', user: 'Pedro M.' }
                ]
            });
        } catch (err) {
            // Mock if fail
            setLead({
                id,
                first_name: 'Mateo',
                last_name: 'García',
                fullName: 'Mateo García',
                phone: '+57 321 456 7890',
                email: 'mateo.garcia@gmail.com',
                source: 'Visitante',
                stage: 'call',
                notes: 'Buscando grupo de jóvenes.',
                interactions: [
                    { id: 1, type: 'WhatsApp', text: 'Se le envió mensaje de bienvenida.', date: 'Hace 4 horas', user: 'Sistema' }
                ]
            });
        } finally {
            setLoading(false);
        }
    }, [token, id]);

    useEffect(() => { fetchLead(); }, [fetchLead]);

    const handleUpdateStage = async (newStage: string) => {
        setIsUpdating(true);
        try {
            await apiFetch(`/crm/consolidation/pipeline/${id}`, {
                method: 'PATCH',
                token,
                body: { stage: newStage }
            });
            setLead((prev: any) => ({ ...prev, stage: newStage }));
            addToast('Fase del pipeline actualizada', 'success');
        } catch {
            addToast('Error al actualizar fase', 'error');
        } finally {
            setIsUpdating(false);
        }
    };

    if (loading) return (
        <CrmShell breadcrumbs={[{ label: 'CRM', icon: Users }, { label: 'Consolidación', icon: Target }, { label: 'Cargando...' }]}>
            <div className="flex flex-col items-center justify-center h-full">
                <Bot size={48} className="text-blue-500 animate-bounce mb-4" />
                <p className="text-sm font-black text-slate-400 tracking-[0.3em] uppercase">Analizando prospecto...</p>
            </div>
        </CrmShell>
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Users },
                { label: 'Pipeline de Consolidación', icon: Target },
                { label: 'Perfil del Lead', icon: Smartphone }
            ]}
        >
            <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0c0d0f]">
                
                <div className="px-6 py-4">
                    <button 
                        onClick={() => router.push('/crm/pipeline')}
                        className="flex items-center gap-1.5 text-slate-400 hover:text-blue-600 transition-colors text-[10px] font-black uppercase tracking-widest mb-4"
                    >
                        <ChevronLeft size={14} /> Volver al Pipeline
                    </button>

                    <AdminHero 
                        eyebrow={`Origen: ${lead.source || 'Directo'}`}
                        title={lead.fullName}
                        description={lead.notes || 'Persona en proceso de consolidación ministerial.'}
                        tags={[lead.source, 'Prioridad A', 'Visitante']}
                        watchers={['Pedro Martínez', 'Ana Gómez']}
                        primaryAction={{ 
                            label: 'Llamar', 
                            icon: Phone, 
                            onClick: () => window.location.href = `tel:${lead.phone}` 
                        }}
                        secondaryAction={{
                            label: 'WhatsApp',
                            icon: MessageSquare,
                            onClick: () => window.open(`https://wa.me/${lead.phone}`, '_blank')
                        }}
                    />
                </div>

                <div className="flex-1 px-6 pb-6 overflow-y-auto">
                    <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
                        
                        {/* ── Left Column: Details ── */}
                        <div className="lg:col-span-8 space-y-6">
                            
                            {/* Tabs */}
                            <div className="flex items-center gap-8 border-b border-slate-200 dark:border-white/5 mb-4">
                                {[
                                    { id: 'perfil', label: 'Perfil Completo', icon: User },
                                    { id: 'actividad', label: 'Bitácora de Seguimiento', icon: History },
                                    { id: 'insights', label: 'IA Insights', icon: Sparkles },
                                ].map(tab => (
                                    <button
                                        key={tab.id}
                                        onClick={() => setActiveTab(tab.id)}
                                        className={clsx(
                                            "flex items-center gap-2 py-4 text-[11px] font-black uppercase tracking-widest transition-all relative",
                                            activeTab === tab.id ? "text-blue-600" : "text-slate-400 hover:text-slate-600"
                                        )}
                                    >
                                        <tab.icon size={14} />
                                        {tab.label}
                                        {activeTab === tab.id && (
                                            <motion.div layoutId="pipeline-tab-underline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />
                                        )}
                                    </button>
                                ))}
                            </div>

                            <AnimatePresence mode="wait">
                                {activeTab === 'perfil' && (
                                    <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="space-y-6">
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {[
                                                { label: 'Teléfono', val: lead.phone, icon: Smartphone },
                                                { label: 'Correo Electrónico', val: lead.email || 'No registrado', icon: Mail },
                                                { label: 'Dirección', val: lead.address || 'Pendiente por capturar', icon: MapPin },
                                                { label: 'Profesión', val: lead.job || 'No especificado', icon: Briefcase },
                                            ].map(info => (
                                                <div key={info.label} className="p-5 bg-white dark:bg-white/5 rounded-3xl border border-slate-200 dark:border-white/10 flex items-center gap-4">
                                                    <div className="size-10 rounded-2xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center">
                                                        <info.icon size={18} />
                                                    </div>
                                                    <div>
                                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{info.label}</p>
                                                        <p className="font-bold text-slate-800 dark:text-white">{info.val}</p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>

                                        <div className="p-8 bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-200 dark:border-white/10 shadow-sm">
                                            <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
                                                <Users size={16} /> Composición Familiar
                                            </h3>
                                            <div className="bg-slate-50 dark:bg-black/20 rounded-3xl p-12 text-center border-2 border-dashed border-slate-200 dark:border-white/10">
                                                <p className="text-slate-400 text-sm font-medium">Buscando parientes en el CRM... No se encontraron familiares vinculados.</p>
                                                <button className="mt-4 px-6 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest">Vincular Familia</button>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}

                                {activeTab === 'actividad' && (
                                    <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="space-y-4">
                                        <div className="space-y-4">
                                            {(lead.interactions || []).map((log: any) => (
                                                <div key={log.id} className="flex gap-4 group">
                                                    <div className="shrink-0 flex flex-col items-center">
                                                        <div className="size-8 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
                                                            <CheckCircle2 size={14} />
                                                        </div>
                                                        <div className="flex-1 w-px bg-slate-200 dark:bg-white/10 my-2" />
                                                    </div>
                                                    <div className="flex-1 pb-6">
                                                        <div className="bg-white dark:bg-white/5 p-5 rounded-3xl border border-slate-200 dark:border-white/10 shadow-sm transition-transform group-hover:-translate-y-1">
                                                            <div className="flex items-center justify-between mb-2">
                                                                <span className="px-2.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 text-[10px] font-black uppercase">{log.type}</span>
                                                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{log.date} · {log.user}</span>
                                                            </div>
                                                            <p className="text-sm text-slate-700 dark:text-slate-300 font-medium leading-relaxed">{log.text}</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        <div className="p-2 bg-white dark:bg-white/5 rounded-[2rem] border border-slate-200 dark:border-white/10 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
                                            <input className="w-full bg-transparent px-6 py-4 outline-none text-sm" placeholder="Nueva nota de seguimiento..." />
                                            <div className="flex items-center justify-between px-2 pb-2">
                                                <div className="flex gap-1">
                                                    <button className="p-2 hover:bg-slate-50 dark:hover:bg-white/5 rounded-lg text-slate-400"><Calendar size={14} /></button>
                                                    <button className="p-2 hover:bg-slate-50 dark:hover:bg-white/5 rounded-lg text-slate-400"><Clock size={14} /></button>
                                                </div>
                                                <button className="px-6 py-2 bg-slate-900 dark:bg-white text-white dark:text-black rounded-xl text-[10px] font-black uppercase tracking-widest">Guardar</button>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* ── Right Column: Control & AI ── */}
                        <div className="lg:col-span-4 space-y-6">
                            
                            {/* Pipeline Progress */}
                            <div className="p-6 bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-200 dark:border-white/10 shadow-sm">
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Fase Actual</h3>
                                <div className="space-y-3">
                                    {PIPELINE_STAGES.map((s, i) => {
                                        const isActive = lead.stage === s.value;
                                        const isPast = PIPELINE_STAGES.findIndex(x => x.value === lead.stage) >= i;
                                        return (
                                            <button
                                                key={s.value}
                                                onClick={() => handleUpdateStage(s.value)}
                                                disabled={isUpdating}
                                                className={clsx(
                                                    "w-full flex items-center gap-4 p-4 rounded-2xl border transition-all text-left",
                                                    isActive 
                                                        ? `bg-${s.color}-50 border-${s.color}-500/30 text-${s.color}-700` 
                                                        : isPast 
                                                            ? "bg-emerald-50/50 border-emerald-500/20 text-emerald-700 opacity-60" 
                                                            : "bg-transparent border-transparent text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5"
                                                )}
                                            >
                                                <div className={clsx("size-6 rounded-lg flex items-center justify-center text-white", isActive ? s.dot : isPast ? "bg-emerald-500" : "bg-slate-200 dark:bg-white/10")}>
                                                    {isPast && !isActive ? <CheckCircle2 size={12} /> : <span className="text-[10px] font-black">{i + 1}</span>}
                                                </div>
                                                <div className="flex-1">
                                                    <p className="text-[11px] font-black tracking-widest uppercase">{s.label}</p>
                                                    {isActive && <p className="text-[9px] font-bold mt-0.5 opacity-80 italic">En proceso ahora</p>}
                                                </div>
                                                {isActive && <div className="size-2 rounded-full bg-blue-500 animate-ping" />}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* AI Insights Card */}
                            <div className="p-8 bg-gradient-to-br from-[#1e1f21] to-[#141517] text-white rounded-[2.5rem] shadow-2xl relative overflow-hidden group">
                                <div className="absolute -top-4 -right-4 size-32 bg-blue-600/10 blur-3xl" />
                                <div className="relative z-10 flex flex-col gap-6">
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-2xl bg-blue-600 flex items-center justify-center shadow-[0_0_20px_rgba(37,99,235,0.4)]">
                                            <Bot size={20} className="text-white" />
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-black uppercase tracking-widest text-blue-400">Optimus Analytics</h3>
                                            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">Scoring de Fidelidad</p>
                                        </div>
                                    </div>
                                    
                                    <div className="space-y-4">
                                        <div className="flex items-end justify-between">
                                            <span className="text-4xl font-black italic">84</span>
                                            <span className="text-[10px] font-black text-rose-400 uppercase tracking-widest bg-rose-400/10 px-2 py-0.5 rounded">Alta Probabilidad</span>
                                        </div>
                                        <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                                            <motion.div initial={{ width: 0 }} animate={{ width: '84%' }} className="h-full bg-gradient-to-r from-blue-500 to-emerald-500" />
                                        </div>
                                    </div>

                                    <div className="p-4 bg-white/5 rounded-2xl border border-white/5">
                                        <p className="text-xs font-medium leading-relaxed italic text-slate-300">
                                            "El lead muestra un patrón de interés en actividades sociales. Recomendamos invitarlo al próximo festival de jóvenes el 15 de Mayo."
                                        </p>
                                    </div>

                                    <button className="w-full py-3 bg-white text-black rounded-xl text-[10px] font-black uppercase tracking-widest hover:scale-[1.02] transition-transform">
                                        Enviar Acción Sugerida
                                    </button>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>
            </div>
        </CrmShell>
    );
}

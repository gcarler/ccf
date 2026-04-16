"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Heart, 
    Calendar, 
    Clock, 
    User, 
    CheckCircle2, 
    Flame, 
    MessageSquare, 
    History, 
    MoreHorizontal, 
    Shield, 
    ChevronLeft,
    Send,
    Loader2,
    Sparkles,
    Activity
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const STATUS_OPTIONS = [
    { label: 'PENDIENTE', value: 'pending', color: 'slate', dot: 'bg-slate-400', bg: 'bg-slate-50 dark:bg-white/5' },
    { label: 'ACTIVA', value: 'active', color: 'rose', dot: 'bg-rose-500', bg: 'bg-rose-50 dark:bg-rose-900/10' },
    { label: 'ORANDO', value: 'praying', color: 'blue', dot: 'bg-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/10' },
    { label: 'CONTESTADA', value: 'answered', color: 'emerald', dot: 'bg-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-900/10' },
];

export default function PrayerDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();

    const [request, setRequest] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('detalle');
    const [isUpdating, setIsUpdating] = useState(false);
    const [newComment, setNewComment] = useState('');

    const fetchRequest = useCallback(async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            const data = await apiFetch<any>(`/crm/prayer-requests/${id}`, { token });
            setRequest({
                ...data,
                name: data.requester_name || data.name || 'Anónimo',
                request_text: data.request_text || data.request,
                status: data.status || (data.is_answered ? 'answered' : 'pending'),
                updates: data.updates || [
                    { id: 1, text: 'Petición recibida y enviada al equipo de intercesión.', date: 'Hace 2 días', user: 'Sistema FARO' }
                ]
            });
        } catch (err) {
            addToast('No pudimos cargar los detalles de la petición', 'error');
            // Mock for demo if needed
        } finally {
            setLoading(false);
        }
    }, [token, id, addToast]);

    useEffect(() => { fetchRequest(); }, [fetchRequest]);

    const handleUpdateStatus = async (newStatus: string) => {
        setIsUpdating(true);
        try {
            await apiFetch(`/crm/prayer-requests/${id}`, {
                method: 'PATCH',
                token,
                body: { status: newStatus }
            });
            setRequest((prev: any) => ({ ...prev, status: newStatus }));
            addToast('Estado actualizado correctamente', 'success');
        } catch {
            addToast('Error al actualizar el estado', 'error');
        } finally {
            setIsUpdating(false);
        }
    };

    if (loading) return (
        <CrmShell breadcrumbs={[{ label: 'CRM', icon: Heart }, { label: 'Peticiones', icon: MessageSquare }, { label: 'Cargando...' }]}>
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm font-black text-slate-400 uppercase tracking-widest">Sincronizando intercesión...</p>
            </div>
        </CrmShell>
    );

    if (!request) return (
        <CrmShell breadcrumbs={[{ label: 'CRM', icon: Heart }, { label: 'Peticiones', icon: MessageSquare }, { label: 'Error' }]}>
            <div className="p-12 text-center">
                <h1 className="text-2xl font-black">Petición no encontrada</h1>
                <p className="text-slate-500 mt-2">Es posible que el registro haya sido archivado.</p>
                <button onClick={() => router.push('/crm/prayers')} className="mt-6 px-6 py-2 bg-slate-900 text-white rounded-xl text-xs font-black uppercase">Volver al listado</button>
            </div>
        </CrmShell>
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Heart },
                { label: 'Apoyo Espiritual', icon: Sparkles },
                { label: 'Expediente de Oración', icon: MessageSquare }
            ]}
        >
            <div className="flex flex-col h-full bg-slate-50/50 dark:bg-black/20">
                
                {/* ─── Hero Section ─── */}
                <div className="px-6 py-4">
                    <button 
                        onClick={() => router.push('/crm/prayers')}
                        className="flex items-center gap-1.5 text-slate-400 hover:text-blue-600 transition-colors text-[10px] font-black uppercase tracking-widest mb-4"
                    >
                        <ChevronLeft size={14} /> Volver a Peticiones
                    </button>

                    <AdminHero 
                        eyebrow={`ID: #${id} · ${request.category.toUpperCase()}`}
                        title={request.name}
                        description={request.request_text}
                        tags={['Urgente', 'Salud', 'Familia']}
                        watchers={['Equipo Pastoral', 'Intercesión CCF']}
                        primaryAction={{ 
                            label: 'Contactar', 
                            icon: Send, 
                            onClick: () => addToast('Abriendo canal de comunicación...', 'info') 
                        }}
                    />
                </div>

                {/* ─── Tabs & Content ─── */}
                <div className="flex-1 px-6 pb-6 overflow-y-auto">
                    <div className="max-w-6xl mx-auto space-y-6">
                        
                        {/* Tab Headers */}
                        <div className="flex items-center gap-8 border-b border-slate-200 dark:border-white/5 mb-6">
                            {[
                                { id: 'detalle', label: 'Detalles del Caso', icon: Activity },
                                { id: 'historial', label: 'Línea de Vida', icon: History },
                                { id: 'intercesores', label: 'Intercesores', icon: Shield },
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
                                        <motion.div layoutId="tab-underline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />
                                    )}
                                </button>
                            ))}
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            
                            {/* Main Content Column */}
                            <div className="lg:col-span-2 space-y-6">
                                <AnimatePresence mode="wait">
                                    {activeTab === 'detalle' && (
                                        <motion.div 
                                            initial={{ opacity: 0, y: 10 }} 
                                            animate={{ opacity: 1, y: 0 }} 
                                            exit={{ opacity: 0, y: -10 }}
                                            className="space-y-6"
                                        >
                                            <div className="p-8 bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-200 dark:border-white/10 shadow-sm">
                                                <h3 className="text-xl font-black mb-4 flex items-center gap-2 italic uppercase">
                                                    Petición Original
                                                </h3>
                                                <p className="text-lg text-slate-700 dark:text-slate-300 leading-relaxed font-medium italic">
                                                    "{request.request_text}"
                                                </p>
                                                <div className="mt-8 flex flex-wrap gap-4">
                                                    <div className="p-4 rounded-3xl bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5 flex-1 min-w-[200px]">
                                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Categoría</p>
                                                        <p className="font-black text-slate-800 dark:text-white">{request.category}</p>
                                                    </div>
                                                    <div className="p-4 rounded-3xl bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5 flex-1 min-w-[200px]">
                                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Fecha de Ingreso</p>
                                                        <p className="font-black text-slate-800 dark:text-white">{request.time || 'N/A'}</p>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="p-8 bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-4">
                                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Acciones Ministeriales</h3>
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                    <button className="p-6 rounded-3xl border border-slate-100 dark:border-white/5 hover:border-blue-500/50 hover:bg-blue-500/5 transition-all text-left group">
                                                        <Flame size={24} className="text-rose-500 mb-3" />
                                                        <p className="text-sm font-black group-hover:text-blue-600 transition-colors uppercase">Prioridad Máxima</p>
                                                        <p className="text-xs text-slate-500 mt-1">Notificar de inmediato a los pastores principales.</p>
                                                    </button>
                                                    <button className="p-6 rounded-3xl border border-slate-100 dark:border-white/5 hover:border-emerald-500/50 hover:bg-emerald-500/5 transition-all text-left group">
                                                        <CheckCircle2 size={24} className="text-emerald-500 mb-3" />
                                                        <p className="text-sm font-black group-hover:text-emerald-700 transition-colors uppercase">Marcar Testimonio</p>
                                                        <p className="text-xs text-slate-500 mt-1">Convertir esta petición en un testimonio público.</p>
                                                    </button>
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}

                                    {activeTab === 'historial' && (
                                        <motion.div 
                                            initial={{ opacity: 0, y: 10 }} 
                                            animate={{ opacity: 1, y: 0 }} 
                                            className="space-y-4"
                                        >
                                            <div className="relative pl-8 space-y-8 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-px before:bg-slate-200 dark:before:bg-white/10">
                                                {(request.updates || []).map((update: any) => (
                                                    <div key={update.id} className="relative">
                                                        <div className="absolute -left-[25px] top-1 size-4 rounded-full border-4 border-slate-50 dark:border-[#141517] bg-blue-600 shadow-xl shadow-blue-500/20" />
                                                        <div className="bg-white dark:bg-white/5 p-5 rounded-3xl border border-slate-200 dark:border-white/10 shadow-sm">
                                                            <div className="flex items-center justify-between mb-2">
                                                                <span className="text-[10px] font-black uppercase tracking-widest text-blue-600">{update.user}</span>
                                                                <span className="text-[10px] font-bold text-slate-400">{update.date}</span>
                                                            </div>
                                                            <p className="text-sm text-slate-700 dark:text-slate-300 font-medium">{update.text}</p>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                            <div className="pt-4 drop-shadow-sm">
                                                <div className="flex gap-3">
                                                    <input 
                                                        value={newComment}
                                                        onChange={(e) => setNewComment(e.target.value)}
                                                        placeholder="Escribir una actualización o progreso..."
                                                        className="flex-1 px-5 py-4 rounded-2xl bg-white dark:bg-white/10 border border-slate-200 dark:border-white/10 outline-none focus:ring-2 focus:ring-blue-500/20 text-sm font-medium"
                                                    />
                                                    <button className="px-6 rounded-2xl bg-blue-600 text-white font-black uppercase text-[10px] tracking-widest shadow-lg shadow-blue-500/20 active:scale-95 transition-all">
                                                        Publicar
                                                    </button>
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* Sidebar Column */}
                            <div className="space-y-6">
                                <div className="p-6 bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-6">
                                    <div>
                                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4">Estado de Intercesión</h3>
                                        <div className="space-y-2">
                                            {STATUS_OPTIONS.map(opt => (
                                                <button
                                                    key={opt.value}
                                                    onClick={() => handleUpdateStatus(opt.value)}
                                                    disabled={isUpdating}
                                                    className={clsx(
                                                        "w-full flex items-center justify-between px-4 py-3 rounded-2xl border transition-all text-left",
                                                        request.status === opt.value
                                                            ? `${opt.bg} border-${opt.color}-500/30 text-${opt.color}-600`
                                                            : "bg-transparent border-transparent text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5"
                                                    )}
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <div className={clsx("size-2.5 rounded-full", opt.dot)} />
                                                        <span className="text-[11px] font-black uppercase tracking-widest">{opt.label}</span>
                                                    </div>
                                                    {request.status === opt.value && <CheckCircle2 size={14} className="text-emerald-600" />}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="pt-6 border-t border-slate-100 dark:border-white/5">
                                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4 text-center">Impacto de la Petición</h3>
                                        <div className="flex items-center justify-center py-6">
                                            <div className="relative size-32">
                                                <svg className="size-full" viewBox="0 0 36 36">
                                                    <path className="text-slate-100 dark:text-white/5" strokeDasharray="100, 100" strokeWidth="3" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" stroke="currentColor"/>
                                                    <path className="text-blue-500 transition-all duration-1000" strokeDasharray="65, 100" strokeWidth="3" strokeLinecap="round" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" stroke="currentColor"/>
                                                </svg>
                                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                                    <span className="text-2xl font-black text-slate-800 dark:text-white italic">65%</span>
                                                    <span className="text-[8px] font-black uppercase text-slate-400 tracking-widest">Atendida</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="p-6 bg-slate-900 text-white rounded-[2.5rem] shadow-2xl shadow-blue-900/40 space-y-4">
                                    <h3 className="text-[11px] font-black uppercase tracking-[0.3em] text-blue-400 flex items-center gap-2">
                                        <Flame size={14} /> Optimus Brain Insight
                                    </h3>
                                    <p className="text-xs font-medium leading-relaxed opacity-90">
                                        Esta solicitud parece estar vinculada a una crisis familiar recurrente. Se recomienda asignar un consejero del módulo pastoral para seguimiento directo.
                                    </p>
                                    <button className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
                                        Solicitar Consejería
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

"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Heart, Calendar, User, MessageCircle, 
    CheckCircle2, Clock, Share2, MoreHorizontal,
    HandHelping, Shield, Quote, Trash2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmDetailShell from '@/components/crm/CrmDetailShell';
import { DSBadge, DSCard } from '@/design';
import clsx from 'clsx';

export default function PrayerRequestDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();

    const [request, setRequest] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const fetchRequest = useCallback(async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            // Real fetch: const data = await apiFetch<any>(`/api/crm/prayer-requests/${id}`, { token });
            // Mocking for now
            setTimeout(() => {
                setRequest({
                    id,
                    requester_name: 'María García',
                    request_text: 'Pido oración por la salud de mi madre que está en el hospital. Los médicos dicen que es un cuadro complicado, pero confiamos en el Señor.',
                    is_public: true,
                    status: 'active',
                    created_at: '2026-04-12T09:15:00Z',
                    category: 'Salud',
                    intercessor_count: 12,
                    updates: [
                        { id: 1, text: 'Visitada por el equipo de pastoral.', date: '2026-04-13T10:00:00Z' }
                    ]
                });
                setLoading(false);
            }, 800);
        } catch (err) {
            console.error("Error fetching prayer request:", err);
            setLoading(false);
        }
    }, [token, id]);

    useEffect(() => { fetchRequest(); }, [fetchRequest]);

    const handleUpdateStatus = async (newStatus: string) => {
        addToast(`Actualizando estado a ${newStatus}...`, 'info');
        // Real update: await apiFetch(`/api/crm/prayer-requests/${id}`, { method: 'PATCH', body: { status: newStatus }, token });
        setRequest({ ...request, status: newStatus });
        addToast('Estado actualizado', 'success');
    };

    if (loading) return (
        <CrmDetailShell title="Cargando petición..." variant="indigo">
            <div className="flex items-center justify-center h-64">
                <Heart className="text-blue-500 animate-pulse" size={48} />
            </div>
        </CrmDetailShell>
    );

    if (!request) return (
        <CrmDetailShell title="Error" variant="rose">
            <div className="p-8 text-center text-rose-500 font-bold">Petición no encontrada</div>
        </CrmDetailShell>
    );

    return (
        <CrmDetailShell
            title={`Petición de ${request.requester_name}`}
            description={`Recibida el ${new Date(request.created_at).toLocaleDateString()}`}
            variant="indigo"
            rightAction={
                <div className="flex items-center gap-2">
                    <DSBadge 
                        tone={request.status === 'active' ? 'blue' : 'emerald'} 
                        label={request.status === 'active' ? 'ACTIVA' : 'RESPONDIDA'} 
                    />
                </div>
            }
        >
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                
                {/* ─── Main Content ─── */}
                <div className="lg:col-span-8 space-y-8">
                    
                    {/* Request Card */}
                    <DSCard tone="glass" className="relative overflow-hidden p-10">
                        <Quote size={80} className="absolute -top-4 -right-4 opacity-5 text-blue-500" />
                        <div className="flex items-start gap-6 relative z-10">
                            <div className="size-16 rounded-[1.5rem] bg-blue-500/10 flex items-center justify-center text-blue-500 shrink-0">
                                <Heart size={32} />
                            </div>
                            <div className="space-y-4">
                                <p className="text-xl font-medium leading-relaxed text-slate-700 dark:text-slate-200 italic">
                                    "{request.request_text}"
                                </p>
                                <div className="flex items-center gap-4 text-xs font-bold uppercase tracking-widest text-slate-400">
                                    <span className="flex items-center gap-1.5"><User size={14} /> {request.requester_name}</span>
                                    <span className="flex items-center gap-1.5"><Calendar size={14} /> {new Date(request.created_at).toLocaleDateString()}</span>
                                    <DSBadge tone="slate" label={request.category} className="scale-75" />
                                </div>
                            </div>
                        </div>
                    </DSCard>

                    {/* Follow-up Timeline */}
                    <DSCard tone="glass" className="p-8 space-y-6">
                        <div className="flex items-center justify-between">
                            <h3 className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">Seguimiento Pastoral</h3>
                            <button className="text-[10px] font-black uppercase tracking-widest text-blue-500 hover:text-blue-600">Añadir Nota</button>
                        </div>
                        
                        <div className="space-y-6">
                            {request.updates.map((update: any) => (
                                <div key={update.id} className="flex gap-4">
                                    <div className="flex flex-col items-center shrink-0">
                                        <div className="size-3 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
                                        <div className="w-px h-full bg-slate-200 dark:bg-white/10 mt-2" />
                                    </div>
                                    <div className="pb-4">
                                        <p className="text-sm text-slate-700 dark:text-slate-300 font-medium">{update.text}</p>
                                        <p className="text-[10px] text-slate-400 font-bold uppercase mt-1">
                                            {new Date(update.date).toLocaleString()}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </DSCard>
                </div>

                {/* ─── Sidebar / Actions ─── */}
                <div className="lg:col-span-4 space-y-8">
                    
                    {/* Metrics */}
                    <DSCard tone="glass" className="p-8 space-y-6">
                        <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Estado de Intercesión</h3>
                        <div className="flex items-center justify-between">
                            <div className="space-y-1">
                                <p className="text-3xl font-black text-slate-800 dark:text-white">{request.intercessor_count}</p>
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Intercesores Activos</p>
                            </div>
                            <div className="size-14 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                                <HandHelping size={28} />
                            </div>
                        </div>
                        <button className="w-full py-3 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-900/20">
                            Asignar a Grupo de Oración
                        </button>
                    </DSCard>

                    {/* Visibility & Settings */}
                    <DSCard tone="glass" className="p-8 space-y-6">
                        <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Privacidad y Acceso</h3>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Shield size={18} className="text-blue-500" />
                                    <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase">Petición Pública</span>
                                </div>
                                <DSBadge tone={request.is_public ? 'blue' : 'slate'} label={request.is_public ? 'SÍ' : 'NO'} />
                            </div>
                            <div className="p-4 rounded-xl bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10">
                                <p className="text-[10px] text-slate-500 font-medium">
                                    Las peticiones públicas son visibles en el muro de oración de la comunidad. Las privadas solo para el equipo pastoral.
                                </p>
                            </div>
                        </div>
                    </DSCard>

                    {/* Admin Actions */}
                    <div className="flex flex-col gap-3">
                        {request.status === 'active' ? (
                            <button 
                                onClick={() => handleUpdateStatus('answered')}
                                className="w-full py-4 rounded-[2rem] bg-emerald-500 text-white text-[10px] font-black uppercase tracking-[0.2em] flex items-center justify-center gap-2 shadow-xl shadow-emerald-500/20 hover:scale-[1.02] transition-transform"
                            >
                                <CheckCircle2 size={16} /> Marcar como Respondida
                            </button>
                        ) : (
                            <button 
                                onClick={() => handleUpdateStatus('active')}
                                className="w-full py-4 rounded-[2rem] bg-blue-500 text-white text-[10px] font-black uppercase tracking-[0.2em] flex items-center justify-center gap-2 shadow-xl shadow-blue-500/20 hover:scale-[1.02] transition-transform"
                            >
                                <Clock size={16} /> Reabrir Petición
                            </button>
                        )}
                        <button className="w-full py-4 rounded-[2rem] border border-rose-500/30 text-rose-500 text-[10px] font-black uppercase tracking-[0.2em] flex items-center justify-center gap-2 hover:bg-rose-500/5 transition-colors">
                            <Trash2 size={16} /> Eliminar Registro
                        </button>
                    </div>

                </div>
            </div>
        </CrmDetailShell>
    );
}

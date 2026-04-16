"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Send, MessageSquare, Mail, Smartphone, ChevronLeft, 
    BarChart3, Users, Clock, CheckCircle2, AlertCircle, 
    Zap, Bot, Sparkles, History, Eye, MousePointer2, Layout
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import { DSBadge, DSCard } from '@/design';
import clsx from 'clsx';

const CHANNEL_ICONS = {
    whatsapp: MessageSquare,
    email: Mail,
    sms: Smartphone
};

export default function MessagingCampaignDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();

    const [campaign, setCampaign] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const fetchCampaign = useCallback(async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            // In a real scenario, this would be apiFetch<any>(`/api/crm/messaging/history/${id}`, { token });
            // For now, we use a mock that matches the expected schema
            setTimeout(() => {
                setCampaign({
                    id,
                    name: 'Bienvenida Nuevos Miembros',
                    channel: 'whatsapp',
                    status: 'delivered',
                    count: 154,
                    content: '¡Hola! Bienvenido a la familia CCF. Estamos felices de tenerte con nosotros. Aquí tienes una guía de inicio: faro.ccf/bienvenida',
                    stats: { delivered: 154, opened: 132, clicked: 45, failed: 3 },
                    audience: ['Nuevos Miembros', 'Consolidación'],
                    created_at: '2026-04-10T10:00:00Z'
                });
                setLoading(false);
            }, 800);
        } catch (err) {
            console.error("Error fetching campaign:", err);
            setLoading(false);
        }
    }, [token, id]);

    useEffect(() => { fetchCampaign(); }, [fetchCampaign]);

    if (loading) return (
        <CrmShell breadcrumbs={[{ label: 'Comunicación', icon: MessageSquare }, { label: 'Mensajería', icon: Send }, { label: 'Cargando...' }]}>
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <Send size={48} className="text-blue-500 animate-bounce opacity-20" />
                <p className="text-[10px] font-black text-slate-400 tracking-[0.4em] uppercase">Rastreando Campaña...</p>
            </div>
        </CrmShell>
    );

    if (!campaign) return (
        <CrmShell breadcrumbs={[{ label: 'Comunicación', icon: MessageSquare }, { label: 'Error' }]}>
            <div className="p-8 text-center text-rose-500">Campaña no encontrada</div>
        </CrmShell>
    );

    const ChannelIcon = CHANNEL_ICONS[campaign.channel as keyof typeof CHANNEL_ICONS] || MessageSquare;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Users },
                { label: 'Centro de Mensajería', icon: MessageSquare },
                { label: 'Detalle de Campaña', icon: BarChart3 }
            ]}
        >
            <div className="flex flex-col h-full">
                
                {/* ─── Hero Section ─── */}
                <div className="mb-8">
                    <button 
                        onClick={() => router.push('/crm/messaging')}
                        className="flex items-center gap-1.5 text-slate-400 hover:text-blue-600 transition-colors text-[10px] font-black uppercase tracking-widest mb-4"
                    >
                        <ChevronLeft size={14} /> Volver al Historial
                    </button>

                    <AdminHero 
                        eyebrow={`${campaign.channel.toUpperCase()} · ENVIADO EL ${new Date(campaign.created_at).toLocaleDateString()}`}
                        title={campaign.name}
                        description={campaign.content}
                        primaryAction={{ 
                            label: 'Reenviar a Fallidos', 
                            icon: Zap, 
                            onClick: () => addToast('Preparando reenvío segmentado...', 'info') 
                        }}
                        secondaryAction={{
                            label: 'Duplicar Campaña',
                            icon: Layout,
                            onClick: () => addToast('Campaña clonada en borradores', 'success')
                        }}
                    />
                </div>

                {/* ─── Analytics & Data ─── */}
                <div className="space-y-8">
                    
                    {/* Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {[
                            { label: 'Entregados', value: campaign.stats.delivered, icon: CheckCircle2, color: 'text-emerald-500', tone: 'emerald' as const },
                            { label: 'Aperturas', value: campaign.stats.opened, icon: Eye, color: 'text-blue-500', tone: 'blue' as const },
                            { label: 'Clics', value: campaign.stats.clicked, icon: MousePointer2, color: 'text-violet-500', tone: 'violet' as const },
                            { label: 'Fallidos', value: campaign.stats.failed, icon: AlertCircle, color: 'text-amber-500', tone: 'amber' as const },
                        ].map(stat => (
                            <DSCard key={stat.label} tone="glass" padding="lg" className="flex items-center gap-4 group hover:border-blue-500/30 transition-all">
                                <div className={clsx("size-12 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110 bg-white/5", stat.color)}>
                                    <stat.icon size={24} />
                                </div>
                                <div>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none mb-1">{stat.label}</p>
                                    <p className="text-2xl font-black text-slate-800 dark:text-white leading-none">{stat.value}</p>
                                    <DSBadge tone={stat.tone} label="En Tiempo Real" className="mt-2 scale-75 origin-left" />
                                </div>
                            </DSCard>
                        ))}
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                        
                        {/* Left Column: Content Review */}
                        <div className="lg:col-span-8 space-y-8">
                            
                            <DSCard tone="glass" className="p-10 space-y-8">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">Contenido del Mensaje</h3>
                                    <DSBadge tone="emerald" label="VISTA PREVIA REAL" />
                                </div>
                                
                                <div className="relative max-w-md mx-auto">
                                    {/* Mock Phone UI */}
                                    <div className="bg-slate-900 rounded-[3rem] p-3 shadow-2xl border-4 border-slate-800">
                                        <div className="bg-white dark:bg-[#1a1c1e] aspect-[9/16] rounded-[2.2rem] overflow-hidden flex flex-col">
                                            <div className="h-12 bg-slate-50 dark:bg-black/20 flex items-center px-4 gap-3 border-b border-slate-100 dark:border-white/5">
                                                <div className="size-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-[10px] font-black">CCF</div>
                                                <span className="text-xs font-bold">Comunidad Cristiana</span>
                                            </div>
                                            <div className="flex-1 p-4 bg-[#e5ddd5] dark:bg-[#0b141a] space-y-2 overflow-y-auto">
                                                <div className="max-w-[85%] bg-white dark:bg-[#202c33] p-3 rounded-2xl rounded-tl-none shadow-sm space-y-1">
                                                    <p className="text-[13px] leading-relaxed text-slate-800 dark:text-white">{campaign.content}</p>
                                                    <p className="text-[9px] text-slate-400 text-right">10:45 AM</p>
                                                </div>
                                            </div>
                                            <div className="h-12 bg-slate-50 dark:bg-black/20" />
                                        </div>
                                    </div>
                                </div>
                            </DSCard>

                            {/* Audience Breakdown */}
                            <DSCard tone="glass" className="p-8 space-y-6">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Segmentación de Audiencia</h3>
                                <div className="flex flex-wrap gap-2">
                                    {campaign.audience.map((tag: string) => (
                                        <DSBadge key={tag} tone="blue" label={tag} />
                                    ))}
                                </div>
                                <div className="pt-4 border-t border-white/5">
                                    <p className="text-xs text-slate-500 font-medium italic">
                                        Esta campaña fue dirigida a los miembros que cumplen con los criterios de "Actividad Reciente" y "Ubicación Sede Central".
                                    </p>
                                </div>
                            </DSCard>
                        </div>

                        {/* Right Column: AI Insights & Management */}
                        <div className="lg:col-span-4 space-y-8">
                            
                            <DSCard tone="glass" className="p-8 space-y-8">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Detalles de Envío</h3>
                                
                                <div className="space-y-6">
                                    <div className="flex items-center justify-between">
                                        <div className="space-y-1">
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Canal</p>
                                            <div className="flex items-center gap-2">
                                                <ChannelIcon className="text-blue-500" size={16} />
                                                <span className="text-sm font-black text-slate-800 dark:text-white uppercase">{campaign.channel}</span>
                                            </div>
                                        </div>
                                        <div className="space-y-1 text-right">
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Estado</p>
                                            <DSBadge tone="emerald" label="COMPLETADO" />
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Tasa de Entrega</p>
                                        <div className="h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                                            <div className="h-full bg-emerald-500" style={{ width: '98%' }} />
                                        </div>
                                        <p className="text-[10px] text-right font-black text-slate-400 mt-1">98.2% de éxito</p>
                                    </div>
                                </div>
                            </DSCard>

                            <div className="p-10 bg-gradient-to-br from-blue-600 to-indigo-800 text-white rounded-[3rem] shadow-2xl relative overflow-hidden group">
                                <Bot size={120} className="absolute -bottom-8 -right-8 opacity-10 rotate-12 transition-transform group-hover:scale-110" />
                                <h3 className="text-[11px] font-black uppercase tracking-[0.4em] text-blue-200 mb-4 flex items-center gap-2">
                                    <Sparkles size={14} /> Optimus Analytics
                                </h3>
                                <p className="text-sm font-medium leading-relaxed italic opacity-90">
                                    "La tasa de apertura (65%) es superior al promedio histórico (42%). El horario de las 10:45 AM parece ser el momento óptimo para tu congregación."
                                </p>
                                <button className="mt-8 w-full py-4 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-2xl text-[10px] font-black uppercase tracking-widest border border-white/20 transition-all">
                                    Exportar Análisis Full
                                </button>
                            </div>

                            <div className="flex items-center justify-center">
                                <button className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-blue-500 transition-colors">
                                    <History size={14} /> Ver Logs de Envío
                                </button>
                            </div>

                        </div>

                    </div>
                </div>
            </div>
        </CrmShell>
    );
}

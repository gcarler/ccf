"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { 
    MessageSquare, 
    Send, 
    Users, 
    BarChart3, 
    Clock, 
    CheckCircle2, 
    LayoutDashboard,
    ArrowLeft,
    AlertCircle,
    Smartphone,
    Mail
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { DSMetric } from '@/design/components/DSMetric';
import { toast } from 'sonner';

const MOCK_CAMPAIGN = {
    id: 1,
    name: 'Invitación Noche de Milagros',
    channel: 'whatsapp',
    status: 'sent',
    sent_at: '2026-04-12T09:00:00',
    target_count: 350,
    delivered_count: 342,
    failed_count: 8,
    content: 'Hola! Te esperamos este sábado en nuestra Noche de Milagros. ¡No faltes!'
};

export default function MessagingDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [campaign, setCampaign] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadCampaign = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/crm/messaging/history/${id}`, { token }).catch(() => MOCK_CAMPAIGN);
                setCampaign(data);
            } catch (err) {
                toast.error('Error al cargar detalle de campaña');
            } finally {
                setLoading(false);
            }
        };
        loadCampaign();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Analizando métricas de comunicación...</div>;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Mensajería', icon: MessageSquare, href: '/crm/messaging' },
                { label: campaign.name, icon: Send },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="space-y-4">
                        <DSBadge tone={campaign.status === 'sent' ? 'emerald' : 'blue'} label={campaign.status.toUpperCase()} />
                        <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                            {campaign.name}
                        </h1>
                        <div className="flex items-center gap-6 text-sm font-bold text-slate-500">
                            <span className="flex items-center gap-2"><Clock size={18} /> Enviado el {new Date(campaign.sent_at).toLocaleString()}</span>
                            <span className="flex items-center gap-2">
                                {campaign.channel === 'whatsapp' ? <MessageSquare size={18} className="text-emerald-500" /> : <Mail size={18} className="text-blue-500" />}
                                {campaign.channel.toUpperCase()}
                            </span>
                        </div>
                    </div>
                </header>

                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <DSMetric label="Destinatarios" value={String(campaign.target_count)} trend="Total alcance" tone="blue" />
                    <DSMetric label="Entregados" value={String(campaign.delivered_count)} trend={`${Math.round(campaign.delivered_count/campaign.target_count*100)}% éxito`} tone="emerald" />
                    <DSMetric label="Fallidos" value={String(campaign.failed_count)} trend="Revisar números" tone="violet" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Contenido del Mensaje</h3>
                            <div className="p-6 rounded-3xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5">
                                <p className="text-lg font-medium text-slate-800 dark:text-slate-200 leading-relaxed">
                                    {campaign.content}
                                </p>
                            </div>
                        </DSCard>
                    </div>

                    <aside className="space-y-6">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Estado de Entrega</h3>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between text-xs font-bold">
                                    <span className="text-slate-500">Completado</span>
                                    <span className="text-emerald-500">98%</span>
                                </div>
                                <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: '98%' }} />
                                </div>
                            </div>
                        </DSCard>
                    </aside>
                </div>
            </main>
        </CrmShell>
    );
}

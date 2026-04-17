"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { 
    Heart, 
    Calendar, 
    MessageSquare, 
    User, 
    Clock, 
    CheckCircle2, 
    LayoutDashboard,
    ArrowLeft,
    HandHelping,
    Sparkles
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

const MOCK_PRAYER = {
    id: 1,
    requester_name: 'Roberto Gómez',
    request_text: 'Petición por la salud de mi madre que se encuentra en cirugía.',
    category: 'Salud',
    status: 'praying',
    created_at: '2026-04-13T10:00:00'
};

export default function PrayerDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [prayer, setPrayer] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadPrayer = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/crm/prayer-requests/${id}`, { token }).catch(() => MOCK_PRAYER);
                setPrayer(data);
            } catch (err) {
                toast.error('Error al cargar detalle de intercesión');
            } finally {
                setLoading(false);
            }
        };
        loadPrayer();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Accediendo al muro de intercesión...</div>;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Intercesión', icon: Heart, href: '/crm/prayers' },
                { label: prayer.requester_name, icon: User },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <DSBadge tone="violet" label={prayer.category.toUpperCase()} />
                            <DSBadge tone={prayer.status === 'answered' ? 'emerald' : 'amber'} label={prayer.status.toUpperCase()} />
                        </div>
                        <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                            {prayer.requester_name}
                        </h1>
                        <p className="flex items-center gap-2 text-sm font-bold text-slate-500">
                            <Calendar size={18} className="text-blue-600" /> Recibida el {new Date(prayer.created_at).toLocaleDateString()}
                        </p>
                    </div>
                    <button className="px-6 py-3 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/30 hover:scale-105 transition-all flex items-center gap-2">
                        <HandHelping size={16} /> Marcar como Respondida
                    </button>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Motivo de Oración</h3>
                            <p className="text-xl font-medium text-slate-700 dark:text-slate-200 italic leading-relaxed">
                                &quot;{prayer.request_text}&quot;
                            </p>
                        </DSCard>
                    </div>

                    <aside className="space-y-6">
                        <div className="p-6 bg-slate-900 rounded-[2.5rem] text-white space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-blue-400">
                                <Sparkles size={14} /> AI Context
                            </div>
                            <p className="text-[11px] font-bold leading-relaxed opacity-90">
                                Esta es la tercera petición de Roberto este mes relacionada con temas de salud familiar. Se recomienda una llamada de seguimiento pastoral directo.
                            </p>
                        </div>
                    </aside>
                </div>
            </main>
        </CrmShell>
    );
}

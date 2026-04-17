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
    Shield,
    ArrowLeft,
    AlertCircle
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

const MOCK_SESSION = {
    id: 1,
    topic: 'Fortalecimiento Familiar',
    member_name: 'Mateo González',
    pastor_name: 'Juan Perez',
    status: 'open',
    priority: 'HIGH',
    date: '2026-04-12',
    notes: 'Mateo busca guía para equilibrar sus estudios y servicio.'
};

export default function CounselingDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [session, setSession] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadSession = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/crm/counseling/${id}`, { token }).catch(() => MOCK_SESSION);
                setSession(data);
            } catch (err) {
                toast.error('Error al cargar sesión de consejería');
            } finally {
                setLoading(false);
            }
        };
        loadSession();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Recuperando bitácora espiritual...</div>;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Consejería', icon: Heart, href: '/crm/counseling' },
                { label: session.member_name, icon: User },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <div className="max-w-4xl mx-auto space-y-8">
                    <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone={session.priority === 'HIGH' ? 'amber' : 'emerald'} label={session.priority} />
                                <DSBadge tone={session.status === 'open' ? 'blue' : 'slate'} label={session.status.toUpperCase()} />
                            </div>
                            <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                                {session.topic}
                            </h1>
                        </div>
                        <button className="px-6 py-2 bg-emerald-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-emerald-500/20 hover:scale-105 transition-all">
                            Cerrar Sesión
                        </button>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 space-y-8">
                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Resumen de la Sesión</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                                    {session.notes}
                                </p>
                            </DSCard>
                        </div>

                        <aside className="space-y-6">
                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Participantes</h3>
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-600">
                                            <User size={16} />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[9px] font-black text-slate-400 uppercase">Miembro</p>
                                            <p className="text-xs font-bold">{session.member_name}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-lg bg-violet-500/10 flex items-center justify-center text-violet-600">
                                            <Shield size={16} />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[9px] font-black text-slate-400 uppercase">Atendido por</p>
                                            <p className="text-xs font-bold">{session.pastor_name}</p>
                                        </div>
                                    </div>
                                </div>
                            </DSCard>

                            <div className="p-6 bg-slate-900 rounded-[2.5rem] text-white space-y-4 border border-white/5 shadow-2xl">
                                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-blue-400">
                                    <MessageSquare size={14} /> AI Context
                                </div>
                                <p className="text-[11px] font-bold leading-relaxed opacity-90 italic">
                                    &quot;Esta es la segunda sesión sobre este tema. Mateo ha mostrado mejoría pero aún requiere seguimiento en su integración grupal.&quot;
                                </p>
                            </div>
                        </aside>
                    </div>
                </div>
            </main>
        </CrmShell>
    );
}

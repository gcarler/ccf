"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { 
    Home, 
    MapPin, 
    Users, 
    Calendar, 
    MessageSquare, 
    Clock, 
    LayoutDashboard,
    ArrowLeft,
    Shield,
    History
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

const MOCK_GROUP = {
    id: 1,
    name: 'Casa de Bendición Sector Sur',
    address: 'Calle 123 #45-67',
    leader_name: 'David Espitia',
    members_count: 15,
    meeting_day: 'Jueves',
    meeting_time: '19:00'
};

export default function GroupDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [group, setGroup] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadGroup = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/crm/glory-houses/${id}`, { token }).catch(() => MOCK_GROUP);
                setGroup(data);
            } catch (err) {
                toast.error('Error al cargar detalle de la Casa');
            } finally {
                setLoading(false);
            }
        };
        loadGroup();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Recuperando información de la Casa de Bendición...</div>;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Casas de Bendición', icon: Home, href: '/crm/groups' },
                { label: group.name, icon: MapPin },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="space-y-4">
                        <DSBadge tone="blue" label="GRUPO ACTIVO" />
                        <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                            {group.name}
                        </h1>
                        <div className="flex items-center gap-6 text-sm font-bold text-slate-500">
                            <span className="flex items-center gap-2"><Calendar size={18} className="text-blue-600" /> {group.meeting_day}s a las {group.meeting_time}</span>
                            <span className="flex items-center gap-2"><MapPin size={18} className="text-blue-600" /> {group.address}</span>
                        </div>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Liderazgo</h3>
                            <div className="flex items-center gap-4">
                                <div className="size-12 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-600">
                                    <Shield size={24} />
                                </div>
                                <div>
                                    <p className="text-xs font-black text-slate-900 dark:text-white uppercase">{group.leader_name}</p>
                                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Líder de Casa</p>
                                </div>
                            </div>
                        </DSCard>

                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Estadísticas del Grupo</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-6 rounded-3xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5">
                                    <Users size={20} className="text-blue-600 mb-2" />
                                    <p className="text-2xl font-black">{group.members_count}</p>
                                    <p className="text-[9px] font-black text-slate-400 uppercase">Miembros Frecuentes</p>
                                </div>
                                <div className="p-6 rounded-3xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5">
                                    <History size={20} className="text-emerald-500 mb-2" />
                                    <p className="text-2xl font-black">92%</p>
                                    <p className="text-[9px] font-black text-slate-400 uppercase">Retención</p>
                                </div>
                            </div>
                        </DSCard>
                    </div>

                    <aside className="space-y-6">
                        <div className="p-6 bg-slate-900 rounded-[2.5rem] text-white space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-blue-400">
                                <History size={14} /> Línea de Tiempo
                            </div>
                            <div className="space-y-3">
                                <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-[10px]">
                                    <p className="font-bold">Reunión de Crecimiento</p>
                                    <p className="opacity-50">Ayer • 15 asistentes</p>
                                </div>
                            </div>
                        </div>
                    </aside>
                </div>
            </main>
        </CrmShell>
    );
}

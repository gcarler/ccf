"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { 
    User, 
    Calendar, 
    Shield, 
    Clock, 
    CheckCircle2, 
    LayoutDashboard,
    ArrowLeft,
    Heart,
    Star,
    Award
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

const MOCK_VOLUNTEER = {
    id: 1,
    name: 'Ana María Restrepo',
    role: 'Líder de Alabanza',
    team: 'Ministerio de Música',
    status: 'active',
    joined_date: '2024-05-10',
    total_hours: 120,
    skills: ['Canto', 'Guitarra', 'Liderazgo']
};

export default function VolunteerDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [volunteer, setVolunteer] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadVolunteer = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/crm/volunteers/${id}`, { token }).catch(() => MOCK_VOLUNTEER);
                setVolunteer(data);
            } catch (err) {
                toast.error('Error al cargar perfil de servidor');
            } finally {
                setLoading(false);
            }
        };
        loadVolunteer();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Consultando registro de servidores...</div>;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: LayoutDashboard, href: '/crm' },
                { label: 'Voluntariado', icon: Heart, href: '/crm/volunteers' },
                { label: volunteer.name, icon: User },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <div className="max-w-4xl mx-auto space-y-8">
                    <header className="flex items-center gap-6">
                        <div className="size-20 rounded-3xl bg-blue-500/10 flex items-center justify-center text-blue-600 shadow-xl border border-blue-500/20">
                            <User size={40} />
                        </div>
                        <div className="space-y-1">
                            <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">{volunteer.name}</h1>
                            <div className="flex items-center gap-3">
                                <DSBadge tone="blue" label={volunteer.role.toUpperCase()} />
                                <DSBadge tone="emerald" label={volunteer.status.toUpperCase()} />
                            </div>
                        </div>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 space-y-8">
                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Información del Servidor</h3>
                                <div className="grid grid-cols-2 gap-6">
                                    <div className="space-y-1">
                                        <p className="text-[9px] font-black text-slate-400 uppercase">Equipo</p>
                                        <p className="text-sm font-bold">{volunteer.team}</p>
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-[9px] font-black text-slate-400 uppercase">Miembro desde</p>
                                        <p className="text-sm font-bold">{volunteer.joined_date}</p>
                                    </div>
                                </div>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Habilidades y Dones</h3>
                                <div className="flex flex-wrap gap-2">
                                    {volunteer.skills?.map((skill: string) => (
                                        <DSBadge key={skill} tone="violet" label={skill} />
                                    ))}
                                </div>
                            </DSCard>
                        </div>

                        <aside className="space-y-6">
                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Métricas de Servicio</h3>
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-medium text-slate-500">Horas Totales</span>
                                        <span className="text-sm font-black">{volunteer.total_hours}h</span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-medium text-slate-500">Fidelidad</span>
                                        <div className="flex items-center gap-0.5 text-amber-400">
                                            <Star size={12} fill="currentColor" />
                                            <Star size={12} fill="currentColor" />
                                            <Star size={12} fill="currentColor" />
                                            <Star size={12} fill="currentColor" />
                                            <Star size={12} fill="currentColor" />
                                        </div>
                                    </div>
                                </div>
                            </DSCard>
                        </aside>
                    </div>
                </div>
            </main>
        </CrmShell>
    );
}

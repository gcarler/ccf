"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    User, 
    Calendar, 
    Shield, 
    Phone, 
    Mail, 
    MapPin, 
    Heart, 
    Award, 
    History, 
    ArrowLeft,
    CheckCircle2,
    LayoutDashboard,
    Briefcase,
    Zap
} from 'lucide-react';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';

const MOCK_MEMBER = {
    id: 1,
    first_name: 'Ana María',
    last_name: 'Restrepo',
    email: 'ana.restrepo@example.com',
    phone: '+57 310 987 6543',
    church_role: 'Servidor',
    spiritual_status: 'Discípulo',
    is_baptized: true,
    joined_date: '2023-11-20'
};

export default function MemberDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();
    
    const [member, setMember] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadMember = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/crm/members/${id}`, { token }).catch(() => MOCK_MEMBER);
                setMember(data);
            } catch (err) {
                toast.error('Error al cargar expediente de miembro');
            } finally {
                setLoading(false);
            }
        };
        loadMember();
    }, [id, token]);

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Accediendo al registro vital del miembro...</div>;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Administración', icon: LayoutDashboard, href: '/admin' },
                    { label: 'Membresía', icon: User, href: '/admin/members' },
                    { label: `${member.first_name} ${member.last_name}`, icon: User },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all">
                            Editar Expediente
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <div className="max-w-5xl mx-auto space-y-10">
                    <header className="flex flex-col md:flex-row md:items-center gap-8">
                        <div className="size-32 rounded-[2.5rem] bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-2xl border-4 border-white dark:border-slate-900">
                            <User size={64} />
                        </div>
                        <div className="space-y-3">
                            <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase">{member.first_name} {member.last_name}</h1>
                            <div className="flex flex-wrap items-center gap-3">
                                <DSBadge tone="violet" label={member.church_role.toUpperCase()} />
                                <DSBadge tone="emerald" label={member.spiritual_status.toUpperCase()} />
                                {member.is_baptized && <DSBadge tone="blue" label="BAUTIZADO" />}
                            </div>
                        </div>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 space-y-8">
                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-8">Canales de Comunicación</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-2xl bg-blue-50 dark:bg-white/5 flex items-center justify-center text-blue-600">
                                            <Phone size={20} />
                                        </div>
                                        <div>
                                            <p className="text-[9px] font-black text-slate-400 uppercase">Teléfono Móvil</p>
                                            <p className="text-sm font-bold">{member.phone}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-2xl bg-blue-50 dark:bg-white/5 flex items-center justify-center text-blue-600">
                                            <Mail size={20} />
                                        </div>
                                        <div>
                                            <p className="text-[9px] font-black text-slate-400 uppercase">Correo Electrónico</p>
                                            <p className="text-sm font-bold">{member.email}</p>
                                        </div>
                                    </div>
                                </div>
                            </DSCard>

                            <section className="space-y-6">
                                <h3 className="text-sm font-black uppercase tracking-[0.3em] text-slate-400">Hitos en CCF</h3>
                                <div className="space-y-4">
                                    <div className="p-6 rounded-3xl bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/30 transition-all">
                                        <div className="flex items-center gap-4">
                                            <div className="size-10 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-600">
                                                <Zap size={20} />
                                            </div>
                                            <div>
                                                <p className="text-sm font-black text-slate-800 dark:text-white">Ingreso a la Congregación</p>
                                                <p className="text-[10px] text-slate-400 uppercase font-black">{new Date(member.joined_date).toLocaleDateString()}</p>
                                            </div>
                                        </div>
                                        <DSBadge tone="emerald" label="HISTÓRICO" />
                                    </div>
                                </div>
                            </section>
                        </div>

                        <aside className="space-y-6">
                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Ubicación Ministerial</h3>
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3">
                                        <MapPin size={18} className="text-rose-500" />
                                        <span className="text-sm font-bold">Sector Sur - Casa de Gloria #12</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <Briefcase size={18} className="text-blue-500" />
                                        <span className="text-sm font-bold">Ministerio de Consolidación</span>
                                    </div>
                                </div>
                            </DSCard>
                        </aside>
                    </div>
                </div>
            </main>
        </div>
    );
}

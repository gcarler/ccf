"use client";

import React, { useState, useEffect } from 'react';
import {
    Users,
    UserPlus,
    Heart,
    MessageCircle,
    Mail,
    Phone,
    Calendar,
    ArrowUpRight,
    Search,
    User,
    Users as FamilyIcon,
    LayoutDashboard,
    List
} from 'lucide-react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import DashboardEmbed from '@/components/DashboardEmbed';
import { DSCard } from '@/design/components/DSCard';
import { DSMetric } from '@/design/components/DSMetric';
import { DSChart } from '@/design/components/DSChart';
import { toast } from 'sonner';
import DSSkeleton from '@/components/ui/Skeleton';
import { ViewType } from '@/components/ViewSwitcher';
import Link from 'next/link';

export default function CRMClient() {
    const { token } = useAuth();
    const router = useRouter();
    const [dashboard, setDashboard] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token) return;
        const loadDashboard = async () => {
            setLoading(true);
            try {
                const data = await apiFetch<any>('/dashboard/crm', { token });
                setDashboard(data);
            } catch (err) {
                console.error('Error fetching CRM dashboard', err);
                toast.error("Error al cargar el dashboard");
            } finally {
                setLoading(false);
            }
        };
        loadDashboard();
    }, [token]);

    return (
        <WorkspaceLayout
            breadcrumbs={[{ label: 'Consolidación', icon: Users }, { label: 'Dashboard Pastoral', icon: Heart }]}
            rightActions={
                <SplitDropdownButton
                    mainLabel="Nuevo"
                    icon={UserPlus}
                    onMainClick={() => router.push('/plataforma/crm/personas')}
                    options={[
                        { id: 'member', label: 'Miembro', icon: User, onClick: () => router.push('/plataforma/crm/personas') },
                        { id: 'family', label: 'Familia', icon: FamilyIcon, onClick: () => router.push('/plataforma/crm/personas') },
                        { id: 'appointment', label: 'Cita', icon: Calendar, onClick: () => router.push('/plataforma/crm/counseling') },
                        { id: 'call', label: 'Llamada', icon: Phone, onClick: () => router.push('/plataforma/crm/pipeline') },
                        { id: 'mail', label: 'Email', icon: Mail, onClick: () => router.push('/plataforma/crm/pipeline') },
                        { id: 'sms', label: 'SMS', icon: MessageCircle, onClick: () => router.push('/plataforma/crm/pipeline') }
                    ]}
                />
            }
        >
            <main className="flex-1 overflow-y-auto scrollbar-thin p-3 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />

                <div className="w-full space-y-3 relative z-10">
                    {loading ? (
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            {[...Array(4)].map((_, i) => <DSSkeleton key={i} className="h-24 rounded-md" />)}
                        </div>
                    ) : (
                        <>
                            {/* 📊 Pastoral Metrics */}
                            <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                {dashboard?.cards?.length > 0 ? (
                                    dashboard.cards.map((card: any, idx: number) => (
                                        <DSMetric
                                            key={idx}
                                            label={card.title}
                                            value={card.value}
                                            trend={card.trend}
                                            tone={card.color}
                                        />
                                    ))
                                ) : (
                                    <>
                                        <DSMetric label="Personas Registradas" value="—" tone="blue" icon={Users} />
                                        <DSMetric label="Roles Asignados" value="—" tone="emerald" icon={Heart} />
                                        <DSMetric label="En Directorio" value="—" tone="amber" icon={List} />
                                        <DSMetric label="Actividad" value="—" tone="violet" icon={Calendar} />
                                    </>
                                )}
                            </section>

                            {/* 📈 Growth & Distribution */}
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                                <div className="lg:col-span-2">
                                    <DSCard>
                                        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Crecimiento de Membresía</h3>
                                        <DSChart type="area" data={dashboard?.growth_chart} color="#10b981" height={220} />
                                    </DSCard>
                                </div>
                                <div>
                                    <DSCard>
                                        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Distribución por Rol</h3>
                                        <DSChart type="bar" data={dashboard?.pipeline_distribution} color="#3b82f6" height={220} />
                                    </DSCard>
                                </div>
                            </div>

                            {/* Quick Access */}
                            <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <Link
                                    href="/plataforma/crm/members"
                                    className="group relative overflow-hidden rounded-lg border-2 border-dashed border-slate-200 dark:border-white/10 p-5 hover:border-ccf-blue/40 dark:hover:border-ccf-blue/40 transition-all bg-white dark:bg-white/5 hover:bg-ccf-blue/5 dark:hover:bg-ccf-blue/10 no-underline"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2.5 rounded-lg bg-ccf-blue/10 dark:bg-ccf-blue/20">
                                            <Users className="size-5 text-ccf-blue" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-slate-900 dark:text-white">Directorio de Miembros</h4>
                                            <p className="text-[11px] text-slate-400 font-medium mt-0.5">Gestiona y filtra las personas registradas</p>
                                        </div>
                                    </div>
                                    <ArrowUpRight className="absolute top-3 right-3 size-4 text-slate-300 group-hover:text-ccf-blue transition-colors" />
                                </Link>

                                <Link
                                    href="/plataforma/crm/pipeline"
                                    className="group relative overflow-hidden rounded-lg border-2 border-dashed border-slate-200 dark:border-white/10 p-5 hover:border-emerald-400/40 dark:hover:border-emerald-400/40 transition-all bg-white dark:bg-white/5 hover:bg-emerald-50/50 dark:hover:bg-emerald-900/10 no-underline"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2.5 rounded-lg bg-emerald-100 dark:bg-emerald-900/30">
                                            <Heart className="size-5 text-emerald-600 dark:text-emerald-400" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-slate-900 dark:text-white">Pipeline de Consolidación</h4>
                                            <p className="text-[11px] text-slate-400 font-medium mt-0.5">Seguimiento de casos activos</p>
                                        </div>
                                    </div>
                                    <ArrowUpRight className="absolute top-3 right-3 size-4 text-slate-300 group-hover:text-emerald-500 transition-colors" />
                                </Link>

                                <Link
                                    href="/plataforma/crm/counseling"
                                    className="group relative overflow-hidden rounded-lg border-2 border-dashed border-slate-200 dark:border-white/10 p-5 hover:border-violet-400/40 dark:hover:border-violet-400/40 transition-all bg-white dark:bg-white/5 hover:bg-violet-50/50 dark:hover:bg-violet-900/10 no-underline"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2.5 rounded-lg bg-violet-100 dark:bg-violet-900/30">
                                            <MessageCircle className="size-5 text-violet-600 dark:text-violet-400" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-slate-900 dark:text-white">Consejería y Citas</h4>
                                            <p className="text-[11px] text-slate-400 font-medium mt-0.5">Agenda de acompañamiento pastoral</p>
                                        </div>
                                    </div>
                                    <ArrowUpRight className="absolute top-3 right-3 size-4 text-slate-300 group-hover:text-violet-500 transition-colors" />
                                </Link>
                            </section>
                        </>
                    )}
                </div>
            </main>
            <div className="px-6 pb-4"><DashboardEmbed module="crm" label="CRM Pastoral" /></div>
        </WorkspaceLayout>
    );
}

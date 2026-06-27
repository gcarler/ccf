"use client";

import DashboardEmbed from '@/components/DashboardEmbed';
import DSSkeleton from '@/components/ui/Skeleton';
import { useAuth } from '@/context/AuthContext';
import { DSCard } from '@/design/components/DSCard';
import { DSChart } from '@/design/components/DSChart';
import { DSMetric } from '@/design/components/DSMetric';
import { apiFetch } from '@/lib/http';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import {
ArrowUpRight,
Calendar,
Users as _FamilyIcon,
Heart,
List,
MessageCircle,
Users,
} from 'lucide-react'
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect,useState } from 'react';
import { toast } from 'sonner';

export default function CRMClient() {
    const { token } = useAuth();
    const { canEditCrm: _canEditCrm } = useCrmAccess();
    const _router = useRouter();
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
        <>
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
                                        <DSMetric label="Actividad" value="—" tone="blue" icon={Calendar} />
                                    </>
                                )}
                            </section>

                            {/* 📈 Growth & Distribution */}
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                                <div className="lg:col-span-2">
                                    <DSCard>
                                        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Crecimiento de Participación</h3>
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
                                    href="/plataforma/crm/personas"
                                    className="group relative overflow-hidden rounded-lg border-2 border-dashed border-slate-200 dark:border-white/10 p-5 hover:border-ccf-blue/40 dark:hover:border-ccf-blue/40 transition-all bg-white dark:bg-white/5 hover:bg-ccf-blue/5 dark:hover:bg-ccf-blue/10 no-underline"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2.5 rounded-lg bg-ccf-blue/10 dark:bg-ccf-blue/20">
                                            <Users className="size-5 text-ccf-blue" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-slate-900 dark:text-white">Directorio de Personas</h4>
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
                                    className="group relative overflow-hidden rounded-lg border-2 border-dashed border-slate-200 dark:border-white/10 p-5 hover:border-blue-400/40 dark:hover:border-blue-400/40 transition-all bg-white dark:bg-white/5 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 no-underline"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2.5 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                                            <MessageCircle className="size-5 text-blue-600 dark:text-blue-400" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-slate-900 dark:text-white">Consejería y Citas</h4>
                                            <p className="text-[11px] text-slate-400 font-medium mt-0.5">Agenda de acompañamiento pastoral</p>
                                        </div>
                                    </div>
                                    <ArrowUpRight className="absolute top-3 right-3 size-4 text-slate-300 group-hover:text-blue-500 transition-colors" />
                                </Link>
                            </section>
                        </>
                    )}
                </div>
                <div className="px-6 pb-4"><DashboardEmbed module="crm" label="CRM Pastoral" /></div>
            </main>
        </>
    );
}

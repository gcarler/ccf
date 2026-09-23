"use client";

import DashboardEmbed from '@/components/DashboardEmbed';
import { DSSkeleton } from '@/design';
import { useAuth } from '@/context/AuthContext';
import type { DashboardCRM, DashboardMetricCard } from '@/types/crm';
import { DSCard } from '@/design';
import { DSChart } from '@/design';
import { DSMetric } from '@/design';
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
    const [dashboard, setDashboard] = useState<DashboardCRM | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token) return;
        const loadDashboard = async () => {
            setLoading(true);
            try {
                const data = await apiFetch<DashboardCRM>('/dashboard/crm', { token });
                setDashboard(data);
            } catch (err) {
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
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_hsl(var(--primary)/0.05)_0%,_transparent_50%)] pointer-events-none" />

                <div className="w-full space-y-3 relative z-10">
                    {loading ? (
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            {[...Array(4)].map((_, i) => <DSSkeleton key={i} className="h-24 rounded-md" />)}
                        </div>
                    ) : (
                        <>
                            {/* 📊 Pastoral Metrics */}
                            <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                {dashboard?.cards && dashboard.cards.length > 0 ? (
                                    dashboard.cards.map((card: DashboardMetricCard, idx: number) => (
                                        <DSMetric
                                            key={idx}
                                            label={card.title}
                                            value={card.value}
                                            trend={card.trend}
                                            tone={card.color as "emerald" | "amber" | "blue" | undefined}
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
                                        <h3 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] mb-3">Crecimiento de Participación</h3>
                                        <DSChart type="area" data={dashboard?.growth_chart} color="hsl(var(--success))" height={220} />
                                    </DSCard>
                                </div>
                                <div>
                                    <DSCard>
                                        <h3 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] mb-3">Distribución por Rol</h3>
                                        <DSChart type="bar" data={(dashboard?.pipeline_funnel ?? []).map((p: { stage: string; count: number }) => ({ label: p.stage, value: p.count }))} color="hsl(var(--primary))" height={220} />
                                    </DSCard>
                                </div>
                            </div>

                            {/* Quick Access */}
                            <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <Link
                                    href="/plataforma/crm/personas"
                                    className="group relative overflow-hidden rounded-lg border-2 border-dashed border-[hsl(var(--border))] p-5 hover:border-[hsl(var(--primary)/0.4)] transition-all bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--primary)/0.05)] no-underline"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2.5 rounded-lg bg-[hsl(var(--primary)/0.1)]">
                                            <Users className="size-5 text-[hsl(var(--primary))]" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-[hsl(var(--foreground))]">Directorio de Personas</h4>
                                            <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium mt-0.5">Gestiona y filtra las personas registradas</p>
                                        </div>
                                    </div>
                                    <ArrowUpRight className="absolute top-3 right-3 size-4 text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--primary))] transition-colors" />
                                </Link>

                                <Link
                                    href="/plataforma/crm/pipeline"
                                    className="group relative overflow-hidden rounded-lg border-2 border-dashed border-[hsl(var(--border))] p-5 hover:border-[hsl(var(--success)/0.4)] transition-all bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--success)/0.05)] no-underline"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2.5 rounded-lg bg-[hsl(var(--success)/0.1)]">
                                            <Heart className="size-5 text-[hsl(var(--success))]" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-[hsl(var(--foreground))]">Pipeline de Consolidación</h4>
                                            <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium mt-0.5">Seguimiento de casos activos</p>
                                        </div>
                                    </div>
                                    <ArrowUpRight className="absolute top-3 right-3 size-4 text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--success))] transition-colors" />
                                </Link>

                                <Link
                                    href="/plataforma/crm/counseling"
                                    className="group relative overflow-hidden rounded-lg border-2 border-dashed border-[hsl(var(--border))] p-5 hover:border-[hsl(var(--primary)/0.4)] transition-all bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--primary)/0.05)] no-underline"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2.5 rounded-lg bg-[hsl(var(--primary)/0.1)]">
                                            <MessageCircle className="size-5 text-[hsl(var(--primary))]" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-bold text-[hsl(var(--foreground))]">Consejería y Citas</h4>
                                            <p className="text-xs text-[hsl(var(--muted-foreground))] font-medium mt-0.5">Agenda de acompañamiento pastoral</p>
                                        </div>
                                    </div>
                                    <ArrowUpRight className="absolute top-3 right-3 size-4 text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--primary))] transition-colors" />
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

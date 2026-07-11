"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart3, Home, RefreshCw, Users } from "lucide-react";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

type GroupRecord = {
    id: number;
    name: string;
    personas_count?: number;
    capacity?: number;
    leader_name?: string | null;
    status?: string | null;
};

const normalize = (value: number | undefined) => (typeof value === "number" && Number.isFinite(value) ? value : 0);

export default function GroupsAnalyticsPage() {
    const { token } = useAuth();
    const [groups, setGroups] = useState<GroupRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadGroups = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const data = await apiFetch<GroupRecord[]>("/crm/groups", { token }).catch(() => []);
            setGroups(Array.isArray(data) ? data : []);
        } catch {
            setError("No fue posible cargar las metricas de grupos.");
            toast.error("Error al cargar analitica de grupos");
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        void loadGroups();
    }, [loadGroups]);

    const metrics = useMemo(() => {
        const total = groups.length;
        const totalPersonas = groups.reduce((acc, item) => acc + normalize(item.personas_count), 0);
        const totalCapacity = groups.reduce((acc, item) => acc + normalize(item.capacity), 0);
        const withoutLeader = groups.filter((item) => !item.leader_name).length;
        const active = groups.filter((item) => (item.status || "").toLowerCase().includes("activo") || (item.status || "").toLowerCase() === "active").length;
        const occupancyPct = totalCapacity > 0 ? Math.round((totalPersonas / totalCapacity) * 100) : 0;
        const topGroups = [...groups]
            .sort((a, b) => normalize(b.personas_count) - normalize(a.personas_count))
            .slice(0, 5);

        return {
            total,
            totalPersonas,
            totalCapacity,
            withoutLeader,
            active,
            occupancyPct,
            topGroups,
        };
    }, [groups]);

    return (
        <div className="flex h-full flex-col overflow-hidden bg-[#f8fafc] dark:bg-[#1E1F21]">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Grupos", icon: Home },
                    { label: "Analitica", icon: BarChart3 },
                ]}
            />

            <main className="flex-1 space-y-3 overflow-y-auto p-4 lg:p-4">
                <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
                    <MetricCard label="Total casas" value={String(metrics.total)} tone="blue" />
                    <MetricCard label="Casas activas" value={String(metrics.active)} tone="emerald" />
                    <MetricCard label="Personas" value={String(metrics.totalPersonas)} tone="sky" />
                    <MetricCard label="Capacidad" value={String(metrics.totalCapacity)} tone="amber" />
                    <MetricCard label="Ocupacion" value={`${metrics.occupancyPct}%`} tone="rose" />
                </section>

                {loading && (
                    <div className="rounded-md border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 text-center text-sm font-bold text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.02] dark:text-[hsl(var(--text-secondary))]">
                        Cargando metricas de grupos...
                    </div>
                )}

                {!loading && error && (
                    <div className="rounded-md border border-rose-200 bg-rose-50 p-4 dark:border-rose-500/20 dark:bg-rose-500/10">
                        <p className="text-sm font-bold text-rose-600 dark:text-rose-300">{error}</p>
                        <button
                            type="button"
                            onClick={() => void loadGroups()}
                            className="mt-4 inline-flex items-center gap-2 rounded-md border border-rose-300 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-rose-600 transition hover:bg-rose-100 dark:border-rose-400/30 dark:text-rose-200"
                        >
                            <RefreshCw size={12} /> Reintentar
                        </button>
                    </div>
                )}

                {!loading && !error && groups.length === 0 && (
                    <div className="rounded-md border-2 border-dashed border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 text-center dark:border-white/10 dark:bg-white/[0.02]">
                        <Users size={40} className="mx-auto text-[hsl(var(--text-secondary))]" />
                        <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">No hay datos de grupos para analizar</p>
                    </div>
                )}

                {!loading && !error && groups.length > 0 && (
                    <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <article className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-white/[0.03]">
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Top grupos por personas</p>
                            <div className="mt-5 space-y-3">
                                {metrics.topGroups.map((group) => {
                                    const cap = Math.max(1, normalize(group.capacity));
                                    const personas = normalize(group.personas_count);
                                    const pct = Math.min(100, Math.round((personas / cap) * 100));

                                    return (
                                        <div key={group.id} className="rounded-lg border border-[hsl(var(--border))] p-4 dark:border-white/10">
                                            <div className="flex items-center justify-between gap-3">
                                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{group.name}</p>
                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{personas}/{cap}</p>
                                            </div>
                                            <div className="mt-2 h-2 overflow-hidden rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10">
                                                <div className="h-full rounded-full bg-[hsl(var(--primary))]" style={{ width: `${pct}%` }} />
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </article>

                        <article className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-white/[0.03]">
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Riesgos operativos</p>
                            <div className="mt-5 space-y-4">
                                <RiskRow
                                    label="Casas sin lider asignado"
                                    value={metrics.withoutLeader}
                                    description="Asignar liderazgo para mejorar acompanamiento y seguimiento." 
                                />
                                <RiskRow
                                    label="Casas con capacidad al limite"
                                    value={groups.filter((g) => normalize(g.personas_count) >= normalize(g.capacity) && normalize(g.capacity) > 0).length}
                                    description="Evaluar apertura de nuevas casas en zonas saturadas."
                                />
                                <RiskRow
                                    label="Casas inactivas"
                                    value={groups.filter((g) => !((g.status || "").toLowerCase().includes("activo") || (g.status || "").toLowerCase() === "active")).length}
                                    description="Revisar estado y plan de reactivacion pastoral."
                                />
                            </div>
                        </article>
                    </section>
                )}
            </main>
        </div>
    );
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone: "blue" | "emerald" | "sky" | "amber" | "rose" }) {
    const toneClass: Record<typeof tone, string> = {
        blue: "text-[hsl(var(--primary))]",
        emerald: "text-emerald-600",
        sky: "text-[hsl(var(--primary))]",
        amber: "text-amber-500",
        rose: "text-rose-500",
    };

    return (
        <article className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-white/[0.03]">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p>
            <p className={`mt-2 text-xl font-bold ${toneClass[tone]}`}>{value}</p>
        </article>
    );
}

function RiskRow({ label, value, description }: { label: string; value: number; description: string }) {
    return (
        <div className="rounded-lg border border-[hsl(var(--border))] p-4 dark:border-white/10">
            <div className="flex items-center justify-between gap-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{label}</p>
                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{value}</p>
            </div>
            <p className="mt-2 text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{description}</p>
        </div>
    );
}

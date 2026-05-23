"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarClock, History, Home, RefreshCw } from "lucide-react";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

type GroupRecord = {
    id: number;
    name: string;
    zone?: string | null;
    leader_name?: string | null;
    created_at?: string | null;
    status?: string | null;
};

const monthFormatter = new Intl.DateTimeFormat("es-CO", { month: "long", year: "numeric" });
const dayFormatter = new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "short", year: "numeric" });

export default function GroupsHistoryPage() {
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
            setError("No fue posible cargar el historial de grupos.");
            toast.error("Error al cargar historial");
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        void loadGroups();
    }, [loadGroups]);

    const timeline = useMemo(() => {
        const parsed = groups
            .map((item) => {
                const date = item.created_at ? new Date(item.created_at) : null;
                return { ...item, date };
            })
            .filter((item) => item.date && !Number.isNaN(item.date.valueOf())) as Array<GroupRecord & { date: Date }>;

        parsed.sort((a, b) => b.date.valueOf() - a.date.valueOf());

        const byMonth = parsed.reduce<Record<string, Array<GroupRecord & { date: Date }>>>((acc, item) => {
            const key = `${item.date.getFullYear()}-${String(item.date.getMonth() + 1).padStart(2, "0")}`;
            if (!acc[key]) acc[key] = [];
            acc[key].push(item);
            return acc;
        }, {});

        return Object.entries(byMonth).map(([key, items]) => ({ key, monthLabel: monthFormatter.format(items[0].date), items }));
    }, [groups]);

    return (
        <div className="flex h-full flex-col overflow-hidden bg-[#f8fafc] dark:bg-[#1E1F21]">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Casas de Bendicion", icon: Home },
                    { label: "Historial", icon: History },
                ]}
            />

            <main className="flex-1 space-y-3 overflow-y-auto p-4 lg:p-4">
                <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <article className="rounded-md border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-white/[0.03]">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Total registros</p>
                        <p className="mt-2 text-xl font-black text-slate-800 dark:text-slate-100">{groups.length}</p>
                    </article>
                    <article className="rounded-md border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-white/[0.03]">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Meses con actividad</p>
                        <p className="mt-2 text-xl font-black text-indigo-600">{timeline.length}</p>
                    </article>
                    <article className="rounded-md border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-white/[0.03]">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Con lider asignado</p>
                        <p className="mt-2 text-xl font-black text-emerald-600">{groups.filter((item) => !!item.leader_name).length}</p>
                    </article>
                </section>

                {loading && (
                    <div className="rounded-md border border-dashed border-slate-300 bg-white p-4 text-center text-sm font-bold text-slate-500 dark:border-white/10 dark:bg-white/[0.02] dark:text-slate-300">
                        Cargando historial...
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

                {!loading && !error && timeline.length === 0 && (
                    <div className="rounded-md border-2 border-dashed border-slate-200 bg-white p-4 text-center dark:border-white/10 dark:bg-white/[0.02]">
                        <CalendarClock size={40} className="mx-auto text-slate-300" />
                        <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">No hay eventos historicos disponibles</p>
                    </div>
                )}

                {!loading && !error && timeline.length > 0 && (
                    <section className="space-y-3">
                        {timeline.map((month) => (
                            <article key={month.key} className="rounded-md border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/[0.03]">
                                <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">{month.monthLabel}</h2>
                                <div className="mt-3 space-y-4">
                                    {month.items.map((item) => (
                                        <div key={item.id} className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 p-4 dark:border-white/10 md:grid-cols-[180px_1fr_auto] md:items-center">
                                            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{item.date ? dayFormatter.format(item.date) : "Sin fecha"}</p>
                                            <div>
                                                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{item.name}</p>
                                                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                                    Zona: {item.zone || "Sin zona"} · Lider: {item.leader_name || "No asignado"}
                                                </p>
                                            </div>
                                            <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:bg-white/10 dark:text-slate-200">
                                                {item.status || "Estado no definido"}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </article>
                        ))}
                    </section>
                )}
            </main>
        </div>
    );
}

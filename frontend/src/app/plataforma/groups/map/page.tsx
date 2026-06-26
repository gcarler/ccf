"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Home, MapPin, Navigation, RefreshCw } from "lucide-react";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

type GroupRecord = {
    id: number;
    name: string;
    address?: string | null;
    zone?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    leader_name?: string | null;
    personas_count?: number;
    capacity?: number;
    status?: string | null;
    created_at?: string | null;
};

export default function GroupsMapPage() {
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
            setError("No fue posible cargar el mapa de casas.");
            toast.error("Error al cargar grupos con ubicacion");
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        void loadGroups();
    }, [loadGroups]);

    const geolocated = useMemo(
        () => groups.filter((g) => typeof g.latitude === "number" && typeof g.longitude === "number"),
        [groups],
    );

    return (
        <div className="flex h-full flex-col overflow-hidden bg-[#f8fafc] dark:bg-[#1E1F21]">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Casas de Bendicion", icon: Home },
                    { label: "Mapa", icon: MapPin },
                ]}
                rightActions={
                    <Link
                        href="/groups"
                        className="rounded-md border border-slate-200 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 dark:border-white/10 dark:text-slate-200"
                    >
                        Ver dashboard
                    </Link>
                }
            />

            <main className="flex-1 space-y-3 overflow-y-auto p-4 lg:p-4">
                <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <article className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-white/[0.03]">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Total casas</p>
                        <p className="mt-2 text-xl font-bold text-slate-800 dark:text-slate-100">{groups.length}</p>
                    </article>
                    <article className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-white/[0.03]">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Con coordenadas</p>
                        <p className="mt-2 text-xl font-bold text-emerald-600">{geolocated.length}</p>
                    </article>
                    <article className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-white/[0.03]">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Sin coordenadas</p>
                        <p className="mt-2 text-xl font-bold text-amber-500">{Math.max(0, groups.length - geolocated.length)}</p>
                    </article>
                </section>

                {loading && (
                    <div className="rounded-md border border-dashed border-slate-300 bg-[hsl(var(--bg-primary))] p-4 text-center text-sm font-bold text-slate-500 dark:border-white/10 dark:bg-white/[0.02] dark:text-slate-300">
                        Cargando ubicaciones...
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

                {!loading && !error && geolocated.length === 0 && (
                    <div className="rounded-md border-2 border-dashed border-slate-200 bg-[hsl(var(--bg-primary))] p-4 text-center dark:border-white/10 dark:bg-white/[0.02]">
                        <MapPin size={40} className="mx-auto text-slate-300" />
                        <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">
                            No hay casas con coordenadas registradas
                        </p>
                    </div>
                )}

                {!loading && !error && geolocated.length > 0 && (
                    <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                        {geolocated.map((group) => {
                            const mapUrl = `https://www.google.com/maps?q=${group.latitude},${group.longitude}`;
                            return (
                                <article
                                    key={group.id}
                                    className="rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:border-white/10 dark:bg-white/[0.03]"
                                >
                                    <div className="flex items-start justify-between gap-4">
                                        <div>
                                            <h2 className="text-sm font-semibold uppercase tracking-tight text-slate-800 dark:text-slate-100">
                                                {group.name}
                                            </h2>
                                            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{group.address || "Direccion pendiente"}</p>
                                        </div>
                                        <span className="rounded-full bg-blue-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:bg-blue-500/15 dark:text-blue-300">
                                            {group.zone || "Zona sin definir"}
                                        </span>
                                    </div>

                                    <div className="mt-5 grid grid-cols-2 gap-3 text-[11px]">
                                        <div className="rounded-md border border-slate-200 px-3 py-2 dark:border-white/10">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Latitud</p>
                                            <p className="mt-1 font-bold text-slate-700 dark:text-slate-200">{group.latitude}</p>
                                        </div>
                                        <div className="rounded-md border border-slate-200 px-3 py-2 dark:border-white/10">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Longitud</p>
                                            <p className="mt-1 font-bold text-slate-700 dark:text-slate-200">{group.longitude}</p>
                                        </div>
                                    </div>

                                    <div className="mt-5 flex items-center justify-between">
                                        <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                            Lider: <span className="font-bold text-slate-700 dark:text-slate-200">{group.leader_name || "No asignado"}</span>
                                        </p>
                                        <a
                                            href={mapUrl}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 dark:border-white/10 dark:text-slate-200"
                                        >
                                            <Navigation size={12} /> Abrir mapa
                                        </a>
                                    </div>
                                </article>
                            );
                        })}
                    </section>
                )}
            </main>
        </div>
    );
}

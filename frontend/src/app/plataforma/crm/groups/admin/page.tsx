"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { FileText, Home, Loader2, MapPin, Plus, Star, Users, Zap } from "lucide-react";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import AdminHero from "@/components/admin/AdminHero";
import AdminShell from "@/components/admin/AdminShell";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";

type House = { id: number; name: string; zone?: string; leader_name?: string; members_count?: number; status?: string };
type Season = { id: number; name: string; status: string };
type Attendee = { persona_id: string; name: string };

export default function GloryHouseAdmin() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [houses, setHouses] = useState<House[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedHouse, setSelectedHouse] = useState<House | null>(null);
    const [reportDate, setReportDate] = useState(new Date().toISOString().split("T")[0]);
    const [seasons, setSeasons] = useState<Season[]>([]);
    const [seasonId, setSeasonId] = useState<number | "">("");
    const [attendees, setAttendees] = useState<Attendee[]>([]);
    const [selectedIds, setSelectedIds] = useState<string[]>([]);
    const [submitting, setSubmitting] = useState(false);

    const fetchHouses = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<House[]>("/community/glory-houses", { token });
            setHouses(Array.isArray(data) ? data : []);
        } catch {
            setHouses([]);
            addToast("No se pudieron cargar las casas", "error");
        } finally {
            setLoading(false);
        }
    }, [addToast, token]);

    useEffect(() => {
        if (isAuthenticated) fetchHouses();
    }, [fetchHouses, isAuthenticated]);

    const totalMembers = useMemo(() => houses.reduce((sum, house) => sum + (house.members_count || 0), 0), [houses]);

    const openReport = async (house: House) => {
        if (!token) return;
        setSelectedHouse(house);
        try {
            const [seasonData, detail] = await Promise.all([
                apiFetch<Season[]>("/evangelism/faro/seasons", { token }),
                apiFetch<any>(`/evangelism/glory-houses/${house.id}`, { token }),
            ]);
            const nextSeasons = Array.isArray(seasonData) ? seasonData : [];
            const baseAttendees = Array.isArray(detail.base_attendees) ? detail.base_attendees : [];
            setSeasons(nextSeasons);
            setSeasonId((nextSeasons.find((season) => season.status === "Activa") || nextSeasons[0])?.id || "");
            setAttendees(baseAttendees);
            setSelectedIds(baseAttendees.map((member: Attendee) => member.persona_id));
        } catch {
            addToast("No se pudo preparar el reporte", "error");
        }
    };

    const sendReport = async () => {
        if (!token || !selectedHouse || !seasonId) {
            addToast("Selecciona una temporada", "error");
            return;
        }
        setSubmitting(true);
        try {
            const session = await apiFetch<any>("/evangelism/faro/sessions", {
                method: "POST",
                token,
                body: { season_id: seasonId, glory_house_id: selectedHouse.id, session_date: reportDate },
            });
            await apiFetch(`/evangelism/faro/sessions/${session.id}/attendance`, {
                method: "POST",
                token,
                body: { persona_ids: selectedIds },
            });
            addToast(`Reporte enviado para ${selectedHouse.name}`, "success");
            setSelectedHouse(null);
        } catch {
            addToast("No se pudo enviar el reporte", "error");
        } finally {
            setSubmitting(false);
        }
    };

    const createHouse = async () => {
        const name = window.prompt("Nombre de la nueva casa");
        if (!token || !name?.trim()) return;
        try {
            const created = await apiFetch<House>("/community/glory-houses", { method: "POST", token, body: { name: name.trim(), status: "active" } });
            setHouses((prev) => [created, ...prev]);
            addToast("Casa creada correctamente", "success");
        } catch {
            addToast("No se pudo crear la casa", "error");
        }
    };

    if (!isAuthenticated) return null;

    return (
        <AdminShell breadcrumbs={[{ label: "Operacion de Campo", icon: Home }, { label: "Faros en Casa", icon: Star }]}>
            <AdminHero
                eyebrow="Gestion de Redes"
                title="Consola de Faros en Casa"
                description="Gestion operativa real de casas, temporadas y reportes semanales de asistencia."
                tags={["Campo Activo", "Reportes", "Faro"]}
                watchers={["Coordinacion General", "Consolidacion"]}
                primaryAction={{ label: "Nueva Casa", icon: Plus, onClick: createHouse }}
                secondaryAction={{ label: "Exportar Reportes", icon: FileText, onClick: () => window.print() }}
            />

            <main className="space-y-4 pb-4">
                <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <Stat label="Casas Activas" value={loading ? "..." : houses.length.toString()} />
                    <Stat label="Miembros Base" value={loading ? "..." : totalMembers.toString()} />
                    <Stat label="Temporadas" value={seasons.length.toString()} />
                </section>

                <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {houses.map((house) => (
                        <motion.button
                            key={house.id}
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            onClick={() => openReport(house)}
                            className="rounded-md border border-slate-200 bg-white p-4 text-left shadow-sm transition-all hover:-translate-y-1 hover:shadow-xl dark:border-white/10 dark:bg-white/5"
                        >
                            <div className="mb-3 flex items-start justify-between">
                                <div className="flex size-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-900/20"><Home size={24} /></div>
                                <span className="rounded-lg bg-emerald-50 px-2 py-1 text-[8px] font-bold uppercase text-emerald-600 dark:bg-emerald-900/20">{house.status || "Activa"}</span>
                            </div>
                            <h4 className="text-base font-bold uppercase tracking-tight">{house.name}</h4>
                            <p className="mt-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wide text-slate-400"><MapPin size={12} /> {house.zone || "Sin zona"}</p>
                            <div className="mt-3 flex items-center gap-2 border-t border-slate-100 pt-6 text-[11px] font-bold text-slate-500 dark:border-white/5"><Users size={14} /> {house.members_count || 0} miembros</div>
                        </motion.button>
                    ))}
                </section>
            </main>

            <WorkspaceDrawer isOpen={Boolean(selectedHouse)} onClose={() => setSelectedHouse(null)} title={selectedHouse?.name || "Reporte"} subtitle="REPORTE OPERATIVO SEMANAL">
                <div className="space-y-3 pb-4">
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Fecha"><input type="date" value={reportDate} onChange={(event) => setReportDate(event.target.value)} className="w-full bg-transparent text-sm font-bold outline-none" /></Field>
                        <Field label="Temporada">
                            <select value={seasonId} onChange={(event) => setSeasonId(Number(event.target.value) || "")} className="w-full bg-transparent text-sm font-bold outline-none">
                                <option value="">Selecciona</option>
                                {seasons.map((season) => <option key={season.id} value={season.id}>{season.name}</option>)}
                            </select>
                        </Field>
                    </div>

                    <section className="space-y-4">
                        <div className="flex items-center justify-between px-2">
                            <h5 className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Asistencia</h5>
                            <button onClick={() => setSelectedIds(attendees.map((attendee) => attendee.persona_id))} className="text-[9px] font-bold uppercase text-blue-600">Seleccionar Todos</button>
                        </div>
                        <div className="space-y-2">
                            {attendees.map((attendee) => (
                                <label key={attendee.persona_id} className="flex items-center justify-between rounded-lg border border-slate-100 bg-white p-4 dark:border-white/5 dark:bg-white/5">
                                    <span className="text-xs font-bold">{attendee.name}</span>
                                    <input
                                        type="checkbox"
                                        checked={selectedIds.includes(attendee.persona_id)}
                                        onChange={(event) => setSelectedIds((prev) => event.target.checked ? [...prev, attendee.persona_id] : prev.filter((id) => id !== attendee.persona_id))}
                                    />
                                </label>
                            ))}
                            {attendees.length === 0 && <div className="rounded-lg border border-dashed border-slate-200 p-4 text-center text-sm text-slate-400 dark:border-white/10">No hay miembros base asignados.</div>}
                        </div>
                    </section>

                    <button onClick={sendReport} disabled={submitting} className="flex w-full items-center justify-center gap-3 rounded-lg bg-blue-600 py-2 text-[11px] font-bold uppercase tracking-wide text-white disabled:opacity-50">
                        {submitting ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} fill="currentColor" />}
                        Enviar Reporte Semanal
                    </button>
                </div>
            </WorkspaceDrawer>
        </AdminShell>
    );
}

function Stat({ label, value }: { label: string; value: string }) {
    return <div className="rounded-md border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-white/5"><p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</p><h4 className="mt-2 text-lg font-bold">{value}</h4></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return <div className="rounded-md border border-slate-100 bg-slate-50 p-4 dark:border-white/5 dark:bg-white/5"><p className="mb-1 text-[9px] font-bold uppercase tracking-wide text-slate-400">{label}</p>{children}</div>;
}

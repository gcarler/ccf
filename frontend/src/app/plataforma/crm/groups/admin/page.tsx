"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { FileText, Home, Loader2, MapPin, Plus, Star, Users, Zap } from "lucide-react";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import AdminHero from "@/components/admin/AdminHero";
import CrmShell from '@/components/crm/CrmShell';
import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import TextPromptDrawer from "@/components/ui/TextPromptDrawer";
import { Grupo, GrupoApi, Season, Attendee } from "@/types/crm";
import {
    createCrmEvangelismAttendanceSession,
    loadCrmEvangelismGroupReportContext,
    submitCrmEvangelismAttendance,
} from "./evangelismBridge";

export default function GrupoAdmin() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [grupos, setGrupos] = useState<Grupo[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedGrupo, setSelectedGrupo] = useState<Grupo | null>(null);
    const [reportDate, setReportDate] = useState(new Date().toISOString().split("T")[0]);
    const [seasons, setSeasons] = useState<Season[]>([]);
    const [seasonId, setSeasonId] = useState<string>("");
    const [attendees, setAttendees] = useState<Attendee[]>([]);
    const [selectedIds, setSelectedIds] = useState<string[]>([]);
    const [submitting, setSubmitting] = useState(false);
    const [loadingDrawer, setLoadingDrawer] = useState(false);
    const [groupNameDraft, setGroupNameDraft] = useState('');
    const [groupPromptOpen, setGroupPromptOpen] = useState(false);
    const [reloadKey, setReloadKey] = useState(0);

    const fetchGrupos = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            setError(null);
            const data = await apiFetch<GrupoApi[]>("/community/grupos", { token });
            setGrupos(
                Array.isArray(data)
                    ? data.map(({ personas_count, ...grupo }) => ({
                        ...grupo,
                        total_personas: grupo.total_personas ?? personas_count ?? 0,
                    }))
                    : []
            );
        } catch {
            setGrupos([]);
            setError("No se pudieron cargar los grupos");
            addToast("No se pudieron cargar los grupos", "error");
        } finally {
            setLoading(false);
        }
    }, [addToast, token]);

    useEffect(() => {
        if (isAuthenticated) fetchGrupos();
    }, [fetchGrupos, isAuthenticated, reloadKey]);

    const totalPersonas = useMemo(() => grupos.reduce((sum, grupo) => sum + (grupo.total_personas || 0), 0), [grupos]);

    const openReport = async (grupo: Grupo) => {
        if (!token) return;
        setSelectedGrupo(grupo);
        setLoadingDrawer(true);
        try {
            setError(null);
            const reportContext = await loadCrmEvangelismGroupReportContext(token, grupo.id);
            setSeasons(reportContext.seasons);
            setSeasonId(reportContext.selectedSeasonId);
            setAttendees(reportContext.attendees);
            setSelectedIds(reportContext.selectedIds);
            setSelectedGrupo((prev) => prev ? {
                ...prev,
                leader_id: reportContext.leaderId,
                assistant_id: reportContext.assistantId,
                host_id: reportContext.hostId,
            } : prev);
        } catch {
            setSelectedGrupo(null);
            addToast("No se pudo preparar el reporte", "error");
        } finally {
            setLoadingDrawer(false);
        }
    };

    const sendReport = async () => {
        if (!token || !selectedGrupo || !seasonId) {
            addToast("Selecciona una temporada", "error");
            return;
        }
        if (!reportDate) {
            addToast("Selecciona una fecha para el reporte", "error");
            return;
        }
        setSubmitting(true);
        try {
            const session = await createCrmEvangelismAttendanceSession(token, {
                season_id: seasonId,
                grupo_id: selectedGrupo.id,
                session_date: reportDate,
            });
            await submitCrmEvangelismAttendance(token, session.id, selectedIds);
            addToast(`Reporte enviado para ${selectedGrupo.name}`, "success");
            setSelectedGrupo(null);
        } catch {
            addToast("No se pudo enviar el reporte", "error");
        } finally {
            setSubmitting(false);
        }
    };

    const createGrupo = async () => {
        setGroupNameDraft('');
        setGroupPromptOpen(true);
    };

    const submitCreateGrupo = async () => {
        const name = groupNameDraft.trim();
        if (!token || !name) {
            addToast("El nombre del grupo es obligatorio", "error");
            return;
        }
        try {
            const created = await apiFetch<Grupo>("/community/grupos", { method: "POST", token, body: { name: name.trim(), status: "active" } });
            setGrupos((prev) => [created, ...prev]);
            addToast("Grupo creado correctamente", "success");
        } catch {
            addToast("No se pudo crear el grupo", "error");
        } finally {
            setGroupPromptOpen(false);
        }
    };

    if (!isAuthenticated) return null;

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CRM', icon: Home, href: '/plataforma/crm' },
                { label: 'Grupos Admin', icon: Star },
            ]}
        >
            <TextPromptDrawer
                isOpen={groupPromptOpen}
                onClose={() => setGroupPromptOpen(false)}
                onSubmit={submitCreateGrupo}
                title="Crear nuevo grupo"
                subtitle="Define el nombre del grupo"
                label="Nombre del grupo"
                value={groupNameDraft}
                onChange={setGroupNameDraft}
                placeholder="Ej. Jóvenes 20-25"
                submitLabel="Crear grupo"
            />
            <AdminHero
                eyebrow="Gestion de Redes"
                title="Consola de Grupos"
                description="Gestion operativa real de grupos, temporadas y reportes semanales de asistencia."
                tags={["Campo Activo", "Reportes", "Grupo"]}
                watchers={["Coordinacion General", "Consolidacion"]}
                primaryAction={{ label: "Nuevo Grupo", icon: Plus, onClick: createGrupo }}
                secondaryAction={{ label: "Exportar Reportes", icon: FileText, onClick: () => window.print() }}
            />

            <main className="space-y-4 pb-4">
                {error && (
                    <div className="flex flex-col gap-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200 md:flex-row md:items-center md:justify-between">
                        <div>
                            <p className="text-[11px] font-bold uppercase tracking-wide">No se pudo cargar el módulo</p>
                            <p className="text-xs">{error}</p>
                        </div>
                        <button
                            onClick={() => setReloadKey(key => key + 1)}
                            className="rounded-md border border-amber-300 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide hover:bg-amber-100 dark:border-amber-400/30 dark:hover:bg-amber-500/20"
                        >
                            Reintentar
                        </button>
                    </div>
                )}

                <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <Stat label="Grupos Activos" value={loading ? "..." : grupos.length.toString()} />
                    <Stat label="Integrantes Base" value={loading ? "..." : totalPersonas.toString()} />
                    <Stat label="Temporadas" value={seasons.length.toString()} />
                </section>

                {loading && !error && (
                    <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="h-40 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] dark:border-white/10 dark:bg-white/5 animate-pulse p-4 space-y-3">
                                <div className="flex items-start justify-between">
                                    <div className="size-9 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                    <div className="h-5 w-16 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                </div>
                                <div className="h-4 w-2/3 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                                <div className="h-3 w-1/3 rounded bg-[hsl(var(--surface-2))] dark:bg-white/10" />
                            </div>
                        ))}
                    </section>
                )}

                {!loading && !error && grupos.length === 0 && (
                    <div className="rounded-md border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-6 text-center text-sm text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/5">
                        No hay grupos activos para mostrar.
                    </div>
                )}

                {!loading && (
                <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {grupos.map((grupo) => (
                        <motion.button
                            key={grupo.id}
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            onClick={() => openReport(grupo)}
                            className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 text-left shadow-sm transition-all hover:-translate-y-1 hover:shadow-xl dark:border-white/10 dark:bg-white/5"
                        >
                            <div className="mb-3 flex items-start justify-between">
                                <div className="flex size-9 items-center justify-center rounded-lg bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-900/20"><Home size={24} /></div>
                                <span className="rounded-lg bg-emerald-50 px-2 py-1 text-[8px] font-bold uppercase text-emerald-600 dark:bg-emerald-900/20">{grupo.status || "Activo"}</span>
                            </div>
                            <h4 className="text-base font-bold uppercase tracking-tight">{grupo.name}</h4>
                            <p className="mt-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]"><MapPin size={12} /> {grupo.zone || "Sin zona"}</p>
                            <div className="mt-3 flex items-center gap-2 border-t border-[hsl(var(--border))] pt-6 text-[11px] font-bold text-[hsl(var(--text-secondary))] dark:border-white/5"><Users size={14} /> {grupo.total_personas || 0} integrantes</div>
                        </motion.button>
                    ))}
                </section>
                )}
            </main>

            <WorkspaceDrawer isOpen={Boolean(selectedGrupo)} onClose={() => setSelectedGrupo(null)} title={selectedGrupo?.name || "Reporte"} subtitle="REPORTE OPERATIVO SEMANAL">
                <div className="space-y-3 pb-4">
                    {loadingDrawer ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 size={32} className="animate-spin text-[hsl(var(--primary))]" />
                        </div>
                    ) : (
                        <>
                            <div className="grid grid-cols-2 gap-4">
                                <Field label="Fecha"><input type="date" required value={reportDate} onChange={(event) => setReportDate(event.target.value)} className="w-full bg-transparent text-sm font-bold outline-none" /></Field>
                                <Field label="Temporada">
                                    <select required value={seasonId} onChange={(event) => setSeasonId(event.target.value)} className="w-full bg-transparent text-sm font-bold outline-none">
                                        <option value="">Selecciona</option>
                                        {seasons.map((season) => <option key={season.id} value={season.id}>{season.name}</option>)}
                                    </select>
                                </Field>
                            </div>

                            <section className="space-y-4">
                                <div className="flex items-center justify-between px-2">
                                    <h5 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Asistencia</h5>
                                    <button onClick={() => setSelectedIds(attendees.map((attendee) => attendee.persona_id))} className="text-[9px] font-bold uppercase text-[hsl(var(--primary))]">Seleccionar Todos</button>
                                </div>
                                <div className="space-y-2">
                                    {attendees.map((attendee) => (
                                        <label key={attendee.persona_id} className="flex items-center justify-between rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 dark:border-white/5 dark:bg-white/5">
                                            <span className="text-xs font-bold">{attendee.name}</span>
                                            <input
                                                type="checkbox"
                                                checked={selectedIds.includes(attendee.persona_id)}
                                                onChange={(event) => setSelectedIds((prev) => event.target.checked ? [...prev, attendee.persona_id] : prev.filter((id) => id !== attendee.persona_id))}
                                            />
                                        </label>
                                    ))}
                                    {attendees.length === 0 && <div className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-center text-sm text-[hsl(var(--text-secondary))] dark:border-white/10">No hay integrantes base asignados.</div>}
                                </div>
                            </section>

                            <button onClick={sendReport} disabled={submitting} className="flex w-full items-center justify-center gap-3 rounded-lg bg-[hsl(var(--primary))] py-2 text-[11px] font-bold uppercase tracking-wide text-white disabled:opacity-50">
                                {submitting ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} fill="currentColor" />}
                                Enviar Reporte Semanal
                            </button>
                        </>
                    )}
                </div>
            </WorkspaceDrawer>
        </CrmShell>
    );
}

function Stat({ label, value }: { label: string; value: string }) {
    return <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm dark:border-white/10 dark:bg-white/5"><p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p><h4 className="mt-2 text-lg font-bold">{value}</h4></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 dark:border-white/5 dark:bg-white/5"><p className="mb-1 text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p>{children}</div>;
}

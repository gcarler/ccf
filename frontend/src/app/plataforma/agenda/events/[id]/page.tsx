"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Calendar, Clock, FileText, MapPin, Repeat, Save, Trash2 } from "lucide-react";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import type { AgendaEvent } from "@/types/agenda";

/** Desplaza una fecha ISO al día de la ocurrencia conservando hora y duración. */
function shiftToOccurrenceDay(startIso: string, occurrenceDate: string): string | null {
    const anchor = new Date(startIso);
    if (Number.isNaN(anchor.getTime())) return null;
    const anchorDay = anchor.toISOString().slice(0, 10);
    const deltaMs = Date.parse(`${occurrenceDate}T00:00:00Z`) - Date.parse(`${anchorDay}T00:00:00Z`);
    if (Number.isNaN(deltaMs)) return null;
    return new Date(anchor.getTime() + deltaMs).toISOString();
}

export default function AgendaEventDetailPage() {
    const { token } = useAuth();
    const router = useRouter();
    const params = useParams();
    const id = params?.id as string;

    const [event, setEvent] = useState<AgendaEvent | null>(null);
    const [initialEvent, setInitialEvent] = useState<AgendaEvent | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [occurrenceDate, setOccurrenceDate] = useState<string | null>(null);
    const [editScope, setEditScope] = useState<"occurrence" | "series">("series");

    const loadEvent = async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            const data = await apiFetch<AgendaEvent>(`/agenda/events/${id}`, { token, cache: "no-store" });
            setEvent(data);
            setInitialEvent(data);

            // Una llegada desde el calendario de una serie trae la ocurrencia
            // concreta: ?occurrence=YYYY-MM-DD. Precarga sus fechas (mismo hora
            // y duración que el ancla) y activa el alcance por ocurrencia.
            const occurrenceParam = new URLSearchParams(window.location.search).get("occurrence");
            if (occurrenceParam && data.is_recurring) {
                const shiftedStart = shiftToOccurrenceDay(data.start_at, occurrenceParam);
                const shiftedEnd = data.end_at ? shiftToOccurrenceDay(data.end_at, occurrenceParam) : null;
                if (shiftedStart) {
                    setOccurrenceDate(occurrenceParam);
                    setEditScope("occurrence");
                    setEvent((prev) =>
                        prev
                            ? { ...prev, start_at: shiftedStart, end_at: shiftedEnd ?? prev.end_at }
                            : prev,
                    );
                }
            }
        } catch {
            toast.error("No se pudo cargar el evento de agenda");
            router.push("/plataforma/agenda/events");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadEvent();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token, id]);

    const handleSave = async () => {
        if (!token || !event) return;
        setSaving(true);
        try {
            if (editScope === "occurrence" && occurrenceDate) {
                // v2: la ocurrencia editada se materializa como evento puntual.
                const standalone = await apiFetch<AgendaEvent>(
                    `/agenda/events/${event.id}?occurrence_date=${occurrenceDate}`,
                    {
                        method: "PUT",
                        token,
                        body: {
                            title: event.title,
                            description: event.description || null,
                            start_at: event.start_at,
                            end_at: event.end_at,
                            location: event.location || null,
                            is_all_day: event.is_all_day,
                            color_hex: event.color_hex || null,
                            url_conferencia: event.url_conferencia || null,
                            visibilidad: event.visibilidad || "SEDE",
                        },
                    },
                );
                toast.success("Ocurrencia guardada como evento independiente");
                router.replace(`/plataforma/agenda/events/${standalone.id}`);
                return;
            }
            const updated = await apiFetch<AgendaEvent>(`/agenda/events/${event.id}`, {
                method: "PUT",
                token,
                body: event,
            });
            setEvent(updated);
            setInitialEvent(updated);
            toast.success("Evento de agenda actualizado");
        } catch {
            toast.error("No se pudo actualizar el evento");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!token || !event) return;
        setDeleting(true);
        try {
            if (editScope === "occurrence" && occurrenceDate) {
                await apiFetch(`/agenda/events/${event.id}?occurrence_date=${occurrenceDate}`, {
                    method: "DELETE",
                    token,
                });
                toast.success("Ocurrencia eliminada de la serie");
                router.push("/plataforma/agenda/events");
                return;
            }
            await apiFetch(`/agenda/events/${event.id}`, {
                method: "DELETE",
                token,
            });
            toast.success("Evento de agenda eliminado");
            router.push("/plataforma/agenda/events");
        } catch {
            toast.error("No se pudo eliminar el evento");
        } finally {
            setDeleting(false);
        }
    };

    const switchScope = (scope: "occurrence" | "series") => {
        setEditScope(scope);
        if (!initialEvent) return;
        if (scope === "series") {
            // Volver a los valores del ancla: editar la serie edita la serie.
            setEvent(initialEvent);
        } else if (occurrenceDate) {
            const shiftedStart = shiftToOccurrenceDay(initialEvent.start_at, occurrenceDate);
            const shiftedEnd = initialEvent.end_at ? shiftToOccurrenceDay(initialEvent.end_at, occurrenceDate) : null;
            if (shiftedStart) {
                setEvent({ ...initialEvent, start_at: shiftedStart, end_at: shiftedEnd ?? initialEvent.end_at });
            }
        }
    };
    const hasUnsavedChanges = Boolean(
        event &&
        initialEvent &&
        JSON.stringify(event) !== JSON.stringify(initialEvent)
    );

    return (
        <WorkspaceLayout
            breadcrumbs={[
                { label: "CCF", icon: Calendar },
                { label: "Agenda simple", icon: FileText },
                { label: event?.title || "Detalle", icon: Clock },
            ]}
        >
            <div className="h-full overflow-y-auto bg-[hsl(var(--surface-1))] dark:bg-[#141517]">
                <div className="mx-auto max-w-4xl space-y-3 p-3 p-4">
                    <section className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--surface-1))]">
                        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                            <div>
                                <button
                                    onClick={() => router.push("/plataforma/agenda/events")}
                                    className="mb-3 inline-flex items-center gap-2 text-sm font-bold text-[hsl(var(--primary))]"
                                >
                                    <ArrowLeft size={16} />
                                    Volver a agenda
                                </button>
                                <h1 className="text-xl font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white">
                                    {loading ? "Cargando..." : event?.title || "Evento de agenda"}
                                </h1>
                                <p className="mt-2 text-sm font-medium text-[hsl(var(--text-secondary))]">
                                    Reunión o evento general sin asistencia ni flujo de evangelismo.
                                </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                                {event?.derived_from ? (
                                    <span className="inline-flex items-center gap-1 rounded-full bg-warning-soft px-3 py-1 text-2xs font-semibold uppercase tracking-wide text-warning-text dark:bg-[hsl(var(--warning))]/10 dark:text-warning-text">
                                        <Repeat size={10} />
                                        Originada de una serie
                                    </span>
                                ) : null}
                                <span className="rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]">
                                    {saving ? "Guardando" : "Edición activa"}
                                </span>
                                <span
                                    className={`rounded-full px-3 py-1 text-2xs font-semibold uppercase tracking-wide ${
                                        saving
                                            ? "bg-info-soft text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/10 dark:text-info-text"
                                            : hasUnsavedChanges
                                                ? "bg-warning-soft text-warning-text dark:bg-[hsl(var(--warning))]/10 dark:text-warning-text"
                                                : "bg-success-soft text-success-text dark:bg-[hsl(var(--success))]/10 dark:text-success-text"
                                    }`}
                                >
                                    {saving
                                        ? "Sincronizando cambios"
                                        : hasUnsavedChanges
                                            ? "Cambios pendientes"
                                            : "Sin cambios"}
                                </span>
                            </div>
                            <div className="flex gap-3">
                                <button
                                    onClick={handleDelete}
                                    disabled={!event || deleting}
                                    className="inline-flex items-center gap-2 rounded-lg border border-destructive/20 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-destructive transition-all hover:bg-destructive/10 disabled:opacity-50"
                                >
                                    <Trash2 size={14} />
                                    {deleting
                                        ? "Eliminando..."
                                        : editScope === "occurrence" && occurrenceDate
                                            ? "Eliminar ocurrencia"
                                            : "Eliminar"}
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={!event || saving}
                                    className="inline-flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-4 py-3 text-xs font-semibold uppercase tracking-wide text-white transition-all hover:bg-[hsl(var(--primary))] disabled:opacity-50"
                                >
                                    <Save size={14} />
                                    {saving
                                        ? "Guardando..."
                                        : editScope === "occurrence" && occurrenceDate
                                            ? "Guardar ocurrencia"
                                            : "Guardar cambios"}
                                </button>
                            </div>
                        </div>
                    </section>

                    {event?.is_recurring && occurrenceDate ? (
                        <section className="rounded-lg border border-[hsl(var(--info)/30%)] bg-info-soft p-3 dark:border-[hsl(var(--info)/100%)]/30 dark:bg-[hsl(var(--info))]/10">
                            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                <div className="flex items-start gap-3">
                                    <Repeat size={16} className="mt-0.5 shrink-0 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" />
                                    <div>
                                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
                                            Ocurrencia del {occurrenceDate ? format(parseISO(`${occurrenceDate}T12:00:00Z`), "EEEE d 'de' MMMM", { locale: es }) : ""}
                                        </p>
                                        <p className="mt-1 text-xs font-medium text-[hsl(var(--text-secondary))]">
                                            {editScope === "occurrence"
                                                ? "Guardar creará un evento independiente y excluirá esta fecha de la serie; el resto de la serie no cambia."
                                                : "Editando toda la serie: los cambios aplican al ancla y a todas las ocurrencias restantes."}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex shrink-0 gap-2">
                                    <button
                                        onClick={() => switchScope("occurrence")}
                                        className={`rounded-lg border px-3 py-2 text-2xs font-semibold uppercase tracking-wide transition-colors ${
                                            editScope === "occurrence"
                                                ? "border-[hsl(var(--info)/100%)] bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]"
                                                : "border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:hover:bg-white/5"
                                        }`}
                                    >
                                        Sólo esta ocurrencia
                                    </button>
                                    <button
                                        onClick={() => switchScope("series")}
                                        className={`rounded-lg border px-3 py-2 text-2xs font-semibold uppercase tracking-wide transition-colors ${
                                            editScope === "series"
                                                ? "border-[hsl(var(--info)/100%)] bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]"
                                                : "border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:hover:bg-white/5"
                                        }`}
                                    >
                                        Toda la serie
                                    </button>
                                </div>
                            </div>
                        </section>
                    ) : null}

                    {event?.is_recurring && !occurrenceDate && !event.derived_from ? (
                        <p className="flex items-center gap-2 px-1 text-xs font-medium text-[hsl(var(--text-secondary))]">
                            <Repeat size={12} />
                            Serie recurrente: para editar o eliminar una ocurrencia concreta, ábrela desde el calendario general.
                        </p>
                    ) : null}

                    <section className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--surface-1))]">
                        {loading || !event ? (
                            <div className="h-48 animate-pulse rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                        ) : (
                            <div className="space-y-5">
                                <div className="space-y-1.5">
                                    <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Título</label>
                                    <input
                                        value={event.title}
                                        onChange={(e) => setEvent({ ...event, title: e.target.value })}
                                        className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-4 py-3 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--info)/100%)] dark:border-white/10 dark:bg-black/20 dark:text-white"
                                    />
                                </div>

                                <div className="grid gap-4 md:grid-cols-2">
                                    <div className="space-y-1.5">
                                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Inicio</label>
                                        <input
                                            type="datetime-local"
                                            value={event.start_at.slice(0, 16)}
                                            onChange={(e) => setEvent({ ...event, start_at: new Date(e.target.value).toISOString() })}
                                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-4 py-3 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--info)/100%)] dark:border-white/10 dark:bg-black/20 dark:text-white"
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fin</label>
                                        <input
                                            type="datetime-local"
                                            value={(event.end_at || event.start_at).slice(0, 16)}
                                            onChange={(e) => setEvent({ ...event, end_at: new Date(e.target.value).toISOString() })}
                                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-4 py-3 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--info)/100%)] dark:border-white/10 dark:bg-black/20 dark:text-white"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ubicación</label>
                                    <div className="relative">
                                        <MapPin size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                                        <input
                                            value={event.location || ""}
                                            onChange={(e) => setEvent({ ...event, location: e.target.value })}
                                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] py-3 pl-10 pr-4 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--info)/100%)] dark:border-white/10 dark:bg-black/20 dark:text-white"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Descripción</label>
                                    <textarea
                                        rows={5}
                                        value={event.description || ""}
                                        onChange={(e) => setEvent({ ...event, description: e.target.value })}
                                        className="w-full resize-none rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-4 py-3 text-sm font-medium text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--info)/100%)] dark:border-white/10 dark:bg-black/20 dark:text-white"
                                    />
                                </div>
                            </div>
                        )}
                    </section>
                </div>
            </div>
        </WorkspaceLayout>
    );
}

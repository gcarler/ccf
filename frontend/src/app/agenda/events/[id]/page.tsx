"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Calendar, Clock, FileText, MapPin, Save, Trash2 } from "lucide-react";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

type AgendaEvent = {
    id: number;
    title: string;
    description?: string | null;
    start_at: string;
    end_at?: string | null;
    location?: string | null;
    is_all_day: boolean;
};

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

    const loadEvent = async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            const data = await apiFetch<AgendaEvent>(`/agenda/events/${id}`, { token, cache: "no-store" });
            setEvent(data);
            setInitialEvent(data);
        } catch {
            toast.error("No se pudo cargar el evento de agenda");
            router.push("/agenda/events");
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
            await apiFetch(`/agenda/events/${event.id}`, {
                method: "DELETE",
                token,
            });
            toast.success("Evento de agenda eliminado");
            router.push("/agenda/events");
        } catch {
            toast.error("No se pudo eliminar el evento");
        } finally {
            setDeleting(false);
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
            <div className="h-full overflow-y-auto bg-slate-50 dark:bg-[#141517]">
                <div className="mx-auto max-w-4xl space-y-6 p-3 p-4">
                    <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-[#1e1f21]">
                        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                            <div>
                                <button
                                    onClick={() => router.push("/agenda/events")}
                                    className="mb-3 inline-flex items-center gap-2 text-sm font-bold text-blue-600"
                                >
                                    <ArrowLeft size={16} />
                                    Volver a agenda
                                </button>
                                <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
                                    {loading ? "Cargando..." : event?.title || "Evento de agenda"}
                                </h1>
                                <p className="mt-2 text-sm font-medium text-slate-500">
                                    Reunión o evento general sin asistencia ni flujo de evangelismo.
                                </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
                                    {saving ? "Guardando" : "Edición activa"}
                                </span>
                                <span
                                    className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                                        saving
                                            ? "bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300"
                                            : hasUnsavedChanges
                                                ? "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300"
                                                : "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
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
                                    className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-red-600 transition-all hover:bg-red-50 disabled:opacity-50"
                                >
                                    <Trash2 size={14} />
                                    {deleting ? "Eliminando..." : "Eliminar"}
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={!event || saving}
                                    className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-white transition-all hover:bg-blue-700 disabled:opacity-50"
                                >
                                    <Save size={14} />
                                    {saving ? "Guardando..." : "Guardar cambios"}
                                </button>
                            </div>
                        </div>
                    </section>

                    <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-[#1e1f21]">
                        {loading || !event ? (
                            <div className="h-48 animate-pulse rounded-lg bg-slate-100 dark:bg-white/5" />
                        ) : (
                            <div className="space-y-5">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Título</label>
                                    <input
                                        value={event.title}
                                        onChange={(e) => setEvent({ ...event, title: e.target.value })}
                                        className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                    />
                                </div>

                                <div className="grid gap-4 md:grid-cols-2">
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Inicio</label>
                                        <input
                                            type="datetime-local"
                                            value={event.start_at.slice(0, 16)}
                                            onChange={(e) => setEvent({ ...event, start_at: new Date(e.target.value).toISOString() })}
                                            className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Fin</label>
                                        <input
                                            type="datetime-local"
                                            value={(event.end_at || event.start_at).slice(0, 16)}
                                            onChange={(e) => setEvent({ ...event, end_at: new Date(e.target.value).toISOString() })}
                                            className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Ubicación</label>
                                    <div className="relative">
                                        <MapPin size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                        <input
                                            value={event.location || ""}
                                            onChange={(e) => setEvent({ ...event, location: e.target.value })}
                                            className="w-full rounded-lg border border-slate-200 bg-white py-3 pl-10 pr-4 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Descripción</label>
                                    <textarea
                                        rows={5}
                                        value={event.description || ""}
                                        onChange={(e) => setEvent({ ...event, description: e.target.value })}
                                        className="w-full resize-none rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
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

"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Calendar, MapPin, Plus, Clock, FileText, Pencil, Save, Trash2, X } from "lucide-react";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import { format } from "date-fns";
import { es } from "date-fns/locale";

type AgendaEvent = {
    id: number;
    title: string;
    description?: string | null;
    start_at: string;
    end_at?: string | null;
    location?: string | null;
    is_all_day: boolean;
};

type AgendaFormState = {
    title: string;
    description: string;
    start_at: string;
    end_at: string;
    location: string;
};

function formatEventWindow(event: AgendaEvent) {
    const start = new Date(event.start_at);
    const end = event.end_at ? new Date(event.end_at) : null;

    if (event.is_all_day) {
        return format(start, "EEEE d 'de' MMMM", { locale: es });
    }

    const startLabel = format(start, "EEEE d 'de' MMMM, h:mm a", { locale: es });
    if (!end) return startLabel;
    const endLabel = format(end, "h:mm a", { locale: es });
    return `${startLabel} - ${endLabel}`;
}

export default function AgendaEventsPage() {
    const { token } = useAuth();
    const router = useRouter();
    const [events, setEvents] = useState<AgendaEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [editingEventId, setEditingEventId] = useState<number | null>(null);
    const [editingEventSaving, setEditingEventSaving] = useState(false);
    const [deletingEventId, setDeletingEventId] = useState<number | null>(null);
    const [form, setForm] = useState<AgendaFormState>({
        title: "",
        description: "",
        start_at: new Date().toISOString().slice(0, 10),
        end_at: new Date().toISOString().slice(0, 10),
        location: "",
    });
    const [editForm, setEditForm] = useState<AgendaFormState>({
        title: "",
        description: "",
        start_at: new Date().toISOString().slice(0, 10),
        end_at: new Date().toISOString().slice(0, 10),
        location: "",
    });

    const sortedEvents = useMemo(
        () => [...events].sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime()),
        [events],
    );
    const isAgendaEditing = editingEventId !== null;

    const loadEvents = async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<AgendaEvent[]>("/agenda/events", { token, cache: "no-store" });
            setEvents(Array.isArray(data) ? data : []);
        } catch {
            toast.error("No se pudo cargar la agenda general");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadEvents();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token || !form.title.trim()) return;

        setSaving(true);
        try {
            await apiFetch("/agenda/events", {
                method: "POST",
                token,
                body: {
                    title: form.title.trim(),
                    description: form.description.trim() || null,
                    start_at: new Date(form.start_at).toISOString(),
                    end_at: new Date(form.end_at).toISOString(),
                    location: form.location.trim() || null,
                    is_all_day: true,
                },
            });
            toast.success("Evento de agenda creado");
            setForm({
                title: "",
                description: "",
                start_at: new Date().toISOString().slice(0, 10),
                end_at: new Date().toISOString().slice(0, 10),
                location: "",
            });
            await loadEvents();
        } catch {
            toast.error("No se pudo crear el evento de agenda");
        } finally {
            setSaving(false);
        }
    };

    const startInlineEdit = (event: AgendaEvent) => {
        setEditingEventId(event.id);
        setEditForm({
            title: event.title,
            description: event.description || "",
            start_at: event.start_at.slice(0, 10),
            end_at: (event.end_at || event.start_at).slice(0, 10),
            location: event.location || "",
        });
    };

    const handleInlineUpdate = async (eventId: number) => {
        if (!token || !editForm.title.trim()) return;
        setEditingEventSaving(true);
        try {
            await apiFetch(`/agenda/events/${eventId}`, {
                method: "PUT",
                token,
                body: {
                    title: editForm.title.trim(),
                    description: editForm.description.trim() || null,
                    start_at: new Date(editForm.start_at).toISOString(),
                    end_at: new Date(editForm.end_at).toISOString(),
                    location: editForm.location.trim() || null,
                    is_all_day: true,
                },
            });
            toast.success("Evento actualizado");
            setEditingEventId(null);
            await loadEvents();
        } catch {
            toast.error("No se pudo actualizar el evento");
        } finally {
            setEditingEventSaving(false);
        }
    };

    const handleInlineDelete = async (eventId: number) => {
        if (!token) return;
        setDeletingEventId(eventId);
        try {
            await apiFetch(`/agenda/events/${eventId}`, {
                method: "DELETE",
                token,
            });
            toast.success("Evento eliminado");
            if (editingEventId === eventId) {
                setEditingEventId(null);
            }
            await loadEvents();
        } catch {
            toast.error("No se pudo eliminar el evento");
        } finally {
            setDeletingEventId(null);
        }
    };

    return (
        <WorkspaceLayout
            breadcrumbs={[
                { label: "CCF", icon: Calendar },
                { label: "Calendario", icon: Calendar },
                { label: "Agenda simple", icon: FileText },
            ]}
        >
            <div className="h-full overflow-y-auto bg-slate-50 dark:bg-[#141517]">
                <div className="mx-auto max-w-6xl space-y-6 p-3 p-4">
                    <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-[#1e1f21]">
                        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                            <div>
                                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Agenda de iglesia</p>
                                <h1 className="mt-2 text-xl font-bold tracking-tight text-slate-900 dark:text-white">Eventos sin seguimiento de asistencia</h1>
                                <p className="mt-2 max-w-2xl text-sm font-medium text-slate-500">
                                    Usa esta agenda para reuniones, avisos y actividades internas que deben aparecer en el calendario general, sin QR ni analítica ministerial.
                                </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
                                    {isAgendaEditing ? "Edición rápida" : "Agenda completa"}
                                </span>
                                <span
                                    className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                                        isAgendaEditing
                                            ? "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300"
                                            : "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"
                                    }`}
                                >
                                    {isAgendaEditing ? "1 evento en edición" : `${sortedEvents.length} eventos visibles`}
                                </span>
                            </div>
                        </div>
                    </section>

                    <section className="grid gap-3 lg:grid-cols-[380px,1fr]">
                        <form onSubmit={handleCreate} className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-[#1e1f21]">
                            <div className="mb-5 flex items-center gap-3">
                                <div className="flex size-6 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400">
                                    <Plus size={18} />
                                </div>
                                <div>
                                    <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-900 dark:text-white">Nuevo evento de agenda</h2>
                                    <p className="text-xs font-medium text-slate-500">Sólo calendario general</p>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Título</label>
                                    <input
                                        value={form.title}
                                        onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                                        placeholder="Ej: Reunión de liderazgo"
                                        className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Inicio</label>
                                        <input
                                            type="date"
                                            value={form.start_at}
                                            onChange={(e) => setForm((prev) => ({ ...prev, start_at: e.target.value }))}
                                            className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Fin</label>
                                        <input
                                            type="date"
                                            value={form.end_at}
                                            onChange={(e) => setForm((prev) => ({ ...prev, end_at: e.target.value }))}
                                            className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Ubicación</label>
                                    <input
                                        value={form.location}
                                        onChange={(e) => setForm((prev) => ({ ...prev, location: e.target.value }))}
                                        placeholder="Ej: Salón principal"
                                        className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                    />
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Descripción</label>
                                    <textarea
                                        rows={4}
                                        value={form.description}
                                        onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                                        placeholder="Notas de la reunión o contexto para la agenda"
                                        className="w-full resize-none rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={saving || !form.title.trim()}
                                className="mt-5 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-3 text-[11px] font-semibold uppercase tracking-wide text-white transition-all hover:bg-blue-700 disabled:opacity-50"
                            >
                                <Plus size={14} />
                                {saving ? "Guardando..." : "Crear evento"}
                            </button>
                        </form>

                        <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-[#1e1f21]">
                            <div className="mb-5 flex items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-900 dark:text-white">Próximos eventos</h2>
                                    <p className="text-xs font-medium text-slate-500">Se reflejan también en el calendario general</p>
                                </div>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:bg-white/5 dark:text-slate-300">
                                    {sortedEvents.length} registrados
                                </span>
                            </div>

                            {loading ? (
                                <div className="grid gap-4">
                                    {Array.from({ length: 4 }).map((_, index) => (
                                        <div key={index} className="h-28 animate-pulse rounded-lg bg-slate-100 dark:bg-white/5" />
                                    ))}
                                </div>
                            ) : sortedEvents.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-slate-200 px-3 py-1.5 text-center dark:border-white/10">
                                    <p className="text-sm font-bold text-slate-500">No hay eventos de agenda todavía.</p>
                                    <p className="mt-1 text-xs font-medium text-slate-400">Crea reuniones simples aquí; evangelismo queda aparte.</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {sortedEvents.map((event) => (
                                        <article
                                            key={event.id}
                                            className="rounded-lg border border-slate-200 p-3 transition-colors hover:border-blue-300 dark:border-white/10 dark:hover:border-blue-500/30"
                                        >
                                            {editingEventId === event.id ? (
                                                <div className="space-y-4">
                                                    <div className="flex items-center justify-between gap-3">
                                                        <span className="rounded-full bg-amber-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-600 dark:bg-amber-500/10 dark:text-amber-400">
                                                            Edición rápida
                                                        </span>
                                                        <div className="flex gap-2">
                                                            <button
                                                                onClick={() => handleInlineDelete(event.id)}
                                                                disabled={deletingEventId === event.id}
                                                                className="inline-flex items-center gap-1 rounded-md border border-red-200 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-red-600 transition-all hover:bg-red-50 disabled:opacity-50 dark:border-red-500/20 dark:hover:bg-red-500/10"
                                                            >
                                                                <Trash2 size={12} />
                                                                {deletingEventId === event.id ? "Eliminando..." : "Eliminar"}
                                                            </button>
                                                            <button
                                                                onClick={() => setEditingEventId(null)}
                                                                className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500 transition-all hover:bg-slate-50 dark:border-white/10 dark:hover:bg-white/5"
                                                            >
                                                                <X size={12} />
                                                                Cancelar
                                                            </button>
                                                            <button
                                                                onClick={() => handleInlineUpdate(event.id)}
                                                                disabled={editingEventSaving}
                                                                className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-white transition-all hover:bg-blue-700 disabled:opacity-50"
                                                            >
                                                                <Save size={12} />
                                                                {editingEventSaving ? "Guardando..." : "Guardar"}
                                                            </button>
                                                        </div>
                                                    </div>

                                                    <div className="grid gap-4 md:grid-cols-2">
                                                        <div className="space-y-1.5 md:col-span-2">
                                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Título</label>
                                                            <input
                                                                value={editForm.title}
                                                                onChange={(e) => setEditForm((prev) => ({ ...prev, title: e.target.value }))}
                                                                className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                                            />
                                                        </div>
                                                        <div className="space-y-1.5">
                                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Inicio</label>
                                                            <input
                                                                type="date"
                                                                value={editForm.start_at}
                                                                onChange={(e) => setEditForm((prev) => ({ ...prev, start_at: e.target.value }))}
                                                                className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                                            />
                                                        </div>
                                                        <div className="space-y-1.5">
                                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Fin</label>
                                                            <input
                                                                type="date"
                                                                value={editForm.end_at}
                                                                onChange={(e) => setEditForm((prev) => ({ ...prev, end_at: e.target.value }))}
                                                                className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                                            />
                                                        </div>
                                                        <div className="space-y-1.5 md:col-span-2">
                                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Ubicación</label>
                                                            <input
                                                                value={editForm.location}
                                                                onChange={(e) => setEditForm((prev) => ({ ...prev, location: e.target.value }))}
                                                                className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                                            />
                                                        </div>
                                                        <div className="space-y-1.5 md:col-span-2">
                                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Descripción</label>
                                                            <textarea
                                                                rows={3}
                                                                value={editForm.description}
                                                                onChange={(e) => setEditForm((prev) => ({ ...prev, description: e.target.value }))}
                                                                className="w-full resize-none rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-800 outline-none focus:border-blue-500 dark:border-white/10 dark:bg-black/20 dark:text-white"
                                                            />
                                                        </div>
                                                    </div>
                                                </div>
                                            ) : (
                                                <>
                                                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                                        <div className="space-y-2">
                                                            <button
                                                                onClick={() => router.push(`/agenda/events/${event.id}`)}
                                                                className="text-left"
                                                            >
                                                                <h3 className="text-lg font-bold text-slate-900 transition-colors hover:text-blue-600 dark:text-white dark:hover:text-blue-400">{event.title}</h3>
                                                            </button>
                                                            {event.description ? (
                                                                <p className="max-w-2xl text-sm font-medium text-slate-500">{event.description}</p>
                                                            ) : null}
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <span className="rounded-full bg-blue-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-blue-600 dark:bg-blue-500/10 dark:text-blue-400">
                                                                Agenda simple
                                                            </span>
                                                            <button
                                                                onClick={() => handleInlineDelete(event.id)}
                                                                disabled={deletingEventId === event.id}
                                                                className="inline-flex items-center gap-1 rounded-md border border-red-200 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-red-600 transition-all hover:bg-red-50 disabled:opacity-50 dark:border-red-500/20 dark:hover:bg-red-500/10"
                                                            >
                                                                <Trash2 size={12} />
                                                                {deletingEventId === event.id ? "Eliminando..." : "Eliminar"}
                                                            </button>
                                                            <button
                                                                onClick={() => startInlineEdit(event)}
                                                                className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500 transition-all hover:bg-slate-50 dark:border-white/10 dark:hover:bg-white/5"
                                                            >
                                                                <Pencil size={12} />
                                                                Editar
                                                            </button>
                                                        </div>
                                                    </div>

                                                    <div className="mt-4 flex flex-col gap-2 text-sm font-bold text-slate-600 dark:text-slate-300">
                                                        <div className="flex items-center gap-2">
                                                            <Clock size={14} className="text-slate-400" />
                                                            <span>{formatEventWindow(event)}</span>
                                                        </div>
                                                        <div className="flex items-center gap-2">
                                                            <MapPin size={14} className="text-slate-400" />
                                                            <span>{event.location || "Sin ubicación definida"}</span>
                                                        </div>
                                                    </div>
                                                </>
                                            )}
                                        </article>
                                    ))}
                                </div>
                            )}
                        </section>
                    </section>
                </div>
            </div>
        </WorkspaceLayout>
    );
}

"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import CrmShell from "@/components/crm/CrmShell";
import { Heart, MessageSquare, User, LayoutDashboard, Shield } from "lucide-react";
import { DSCard } from "@/design/components/DSCard";
import { DSBadge } from "@/design/components/DSBadge";
import { toast } from "sonner";

type CounselingDetail = {
    id: string;
    persona_id: string;
    persona_name: string;
    pastor_id: string | null;
    topic: string;
    summary: string | null;
    notes: string | null;
    confidential_notes: string | null;
    status: string;
    priority_level: string;
    scheduled_at: string | null;
    duration_minutes: number;
    created_at: string | null;
    history: Array<{ id: number; text: string; date: string | null }>;
};

export default function CounselingDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token, loading: authLoading } = useAuth();
    const [session, setSession] = useState<CounselingDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [reloadKey, setReloadKey] = useState(0);
    const [isEditing, setIsEditing] = useState(false);
    const [editedNotes, setEditedNotes] = useState("");
    const [copilotLoading, setCopilotLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    const handleCopilot = async () => {
        try {
            setCopilotLoading(true);
            const data = await apiFetch<{ draft: string }>(`/crm/counseling/${id}/copilot-draft`, { token });
            const draft = data.draft;
            if (draft) {
                setEditedNotes((prev) => (prev ? `${prev}\n\n${draft}` : draft));
                toast.success("Borrador de copilot generado correctamente");
            } else {
                toast.error("No se pudo obtener el borrador");
            }
        } catch (err) {
            toast.error("Error al llamar a AI Copilot");
        } finally {
            setCopilotLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            const updated = await apiFetch<Partial<CounselingDetail>>(`/crm/counseling/${id}`, {
                method: "PATCH",
                body: { notes: editedNotes },
                token,
            });
            setSession((prev) => prev ? { ...prev, ...updated } : null);
            setIsEditing(false);
            toast.success("Notas guardadas correctamente");
        } catch (err) {
            toast.error("Error al guardar las notas");
        } finally {
            setSaving(false);
        }
    };


    useEffect(() => {
        if (authLoading) return;
        if (!id) {
            setLoading(false);
            setError("No se encontró la sesión de consejería.");
            return;
        }
        if (!token) {
            setLoading(false);
            setError("Debes iniciar sesión para ver esta sesión.");
            return;
        }
        const loadSession = async () => {
            try {
                setError(null);
                setLoading(true);
                const data = await apiFetch<CounselingDetail>(`/crm/counseling/${id}`, { token });
                setSession(data);
            } catch (err) {
                setSession(null);
                setError("No se pudo cargar la sesión de consejería.");
                toast.error("Error al cargar la sesion de consejeria");
            } finally {
                setLoading(false);
            }
        };
        loadSession();
    }, [authLoading, id, reloadKey, token]);

    if (authLoading) {
        return <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Verificando sesión...</div>;
    }

    if (error) {
        return (
            <div className="mx-auto flex max-w-xl flex-col items-center gap-3 p-4 text-center">
                <p className="font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{error}</p>
                <button
                    onClick={() => setReloadKey(key => key + 1)}
                    className="rounded-md border border-[hsl(var(--border))] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:hover:bg-white/5"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Recuperando bitacora espiritual...
            </div>
        );
    }

    if (!session) {
        return (
            <div className="mx-auto flex max-w-xl flex-col items-center gap-3 p-4 text-center">
                <p className="font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                    No se pudo cargar la sesion.
                </p>
                <button
                    onClick={() => setReloadKey(key => key + 1)}
                    className="rounded-md border border-[hsl(var(--border))] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:hover:bg-white/5"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CRM", icon: LayoutDashboard, href: "/plataforma/crm" },
                { label: "Consejeria", icon: Heart, href: "/plataforma/crm/counseling" },
                { label: session.persona_name, icon: User },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
 <div className="w-full space-y-3">
                    <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone={session.priority_level === "HIGH" ? "amber" : "emerald"} label={session.priority_level ?? 'NORMAL'} />
                                <DSBadge tone={session.status === "open" ? "blue" : "slate"} label={String(session.status ?? 'open').toUpperCase()} />
                            </div>
                            <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase leading-none">
                                {session.topic}
                            </h1>
                            <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                Persona: {session.persona_name}
                            </p>
                        </div>
                        <button className="px-4 py-2 bg-[hsl(var(--secondary))] text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--secondary))/20] hover:scale-105 transition-all">
                            Cerrar sesion
                        </button>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div className="lg:col-span-2 space-y-3">
                            <DSCard>
                                <div className="flex justify-between items-center mb-3">
                                    <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Resumen de la Sesion</h3>
                                    {!isEditing && (
                                        <button
                                            onClick={() => {
                                                setIsEditing(true);
                                                setEditedNotes(session.notes || session.summary || "");
                                            }}
                                            className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] hover:underline"
                                        >
                                            Editar
                                        </button>
                                    )}
                                </div>
                                {isEditing ? (
                                    <div className="space-y-3">
                                        <textarea
                                            value={editedNotes}
                                            onChange={(e) => setEditedNotes(e.target.value)}
                                            rows={6}
                                            className="w-full p-2 text-sm bg-transparent border border-[hsl(var(--border))] dark:border-white/10 rounded-md focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))] text-[hsl(var(--text-primary))] dark:text-white"
                                            placeholder="Escribe el resumen de la sesión aquí..."
                                        />
                                        <div className="flex flex-wrap items-center gap-2">
                                            <button
                                                onClick={handleCopilot}
                                                disabled={copilotLoading}
                                                className="px-3 py-1.5 bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide rounded hover:opacity-90 disabled:opacity-50 flex items-center gap-1"
                                            >
                                                {copilotLoading ? "Generando..." : "AI Copilot"}
                                            </button>
                                            <button
                                                onClick={handleSave}
                                                disabled={saving}
                                                className="px-3 py-1.5 bg-emerald-600 text-white text-[10px] font-bold uppercase tracking-wide rounded hover:bg-emerald-700 disabled:opacity-50"
                                            >
                                                {saving ? "Guardando..." : "Guardar"}
                                            </button>
                                            <button
                                                onClick={() => setIsEditing(false)}
                                                disabled={saving || copilotLoading}
                                                className="px-3 py-1.5 bg-slate-600 text-white text-[10px] font-bold uppercase tracking-wide rounded hover:bg-slate-700 disabled:opacity-50"
                                            >
                                                Cancelar
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium whitespace-pre-wrap">
                                        {session.notes || session.summary || "Sin resumen registrado."}
                                    </p>
                                )}
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Notas confidenciales</h3>
                                <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium">
                                    {session.confidential_notes || "Sin notas confidenciales registradas."}
                                </p>
                            </DSCard>
                        </div>

                        <aside className="space-y-3">
                            <DSCard>
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Participantes</h3>
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-lg bg-[hsl(var(--primary))/10] flex items-center justify-center text-[hsl(var(--primary))]">
                                            <User size={16} />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase">Persona</p>
                                            <p className="text-xs font-bold">{session.persona_name}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-lg bg-[hsl(var(--primary))/10] flex items-center justify-center text-[hsl(var(--primary))]">
                                            <Shield size={16} />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase">Pastor ID</p>
                                            <p className="text-xs font-bold">{session.pastor_id ?? "Sin asignar"}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-lg bg-[hsl(var(--primary))/10] flex items-center justify-center text-[hsl(var(--secondary))]">
                                            <MessageSquare size={16} />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase">Duracion</p>
                                            <p className="text-xs font-bold">{session.duration_minutes} minutos</p>
                                        </div>
                                    </div>
                                </div>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Historial</h3>
                                <div className="space-y-3">
                                    {session.history.length > 0 ? session.history.map((item) => (
                                        <div key={item.id} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3">
                                            <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{item.text}</p>
                                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">{item.date ? new Date(item.date).toLocaleDateString("es-CO") : "Sin fecha"}</p>
                                        </div>
                                    )) : (
                                        <p className="text-sm text-[hsl(var(--text-secondary))]">Sin historial relacionado.</p>
                                    )}
                                </div>
                            </DSCard>
                        </aside>
                    </div>
                </div>
            </main>
        </CrmShell>
    );
}

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
    id: number;
    member_id: number;
    member_name: string;
    pastor_id: number | null;
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
    const { token } = useAuth();
    const [session, setSession] = useState<CounselingDetail | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadSession = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<CounselingDetail>(`/crm/counseling/${id}`, { token });
                setSession(data);
            } catch (err) {
                console.error(err);
                toast.error("Error al cargar la sesion de consejeria");
            } finally {
                setLoading(false);
            }
        };
        loadSession();
    }, [id, token]);

    if (loading) {
        return (
            <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-slate-400">
                Recuperando bitacora espiritual...
            </div>
        );
    }

    if (!session) {
        return (
            <div className="p-4 text-center font-bold uppercase tracking-wide text-slate-400">
                No se pudo cargar la sesion.
            </div>
        );
    }

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CRM", icon: LayoutDashboard, href: "/crm" },
                { label: "Consejeria", icon: Heart, href: "/crm/counseling" },
                { label: session.member_name, icon: User },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
 <div className="w-full space-y-3">
                    <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone={session.priority_level === "HIGH" ? "amber" : "emerald"} label={session.priority_level} />
                                <DSBadge tone={session.status === "open" ? "blue" : "slate"} label={session.status.toUpperCase()} />
                            </div>
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                                {session.topic}
                            </h1>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                                Miembro: {session.member_name}
                            </p>
                        </div>
                        <button className="px-4 py-2 bg-emerald-600 text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-emerald-500/20 hover:scale-105 transition-all">
                            Cerrar sesion
                        </button>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div className="lg:col-span-2 space-y-3">
                            <DSCard>
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-3">Resumen de la Sesion</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                                    {session.summary || session.notes || "Sin resumen registrado."}
                                </p>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-3">Notas confidenciales</h3>
                                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                                    {session.confidential_notes || "Sin notas confidenciales registradas."}
                                </p>
                            </DSCard>
                        </div>

                        <aside className="space-y-3">
                            <DSCard>
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-3">Participantes</h3>
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-600">
                                            <User size={16} />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[9px] font-bold text-slate-400 uppercase">Miembro</p>
                                            <p className="text-xs font-bold">{session.member_name}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-600">
                                            <Shield size={16} />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[9px] font-bold text-slate-400 uppercase">Pastor ID</p>
                                            <p className="text-xs font-bold">{session.pastor_id ?? "Sin asignar"}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-600">
                                            <MessageSquare size={16} />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[9px] font-bold text-slate-400 uppercase">Duracion</p>
                                            <p className="text-xs font-bold">{session.duration_minutes} minutos</p>
                                        </div>
                                    </div>
                                </div>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-3">Historial</h3>
                                <div className="space-y-3">
                                    {session.history.length > 0 ? session.history.map((item) => (
                                        <div key={item.id} className="rounded-lg border border-slate-100 dark:border-white/5 p-3">
                                            <p className="text-xs font-bold text-slate-800 dark:text-slate-100">{item.text}</p>
                                            <p className="text-[10px] text-slate-400">{item.date ? new Date(item.date).toLocaleDateString("es-CO") : "Sin fecha"}</p>
                                        </div>
                                    )) : (
                                        <p className="text-sm text-slate-500">Sin historial relacionado.</p>
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

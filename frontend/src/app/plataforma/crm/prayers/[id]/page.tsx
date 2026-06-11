"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import CrmShell from "@/components/crm/CrmShell";
import { Heart, Calendar, User, LayoutDashboard, HandHelping, Sparkles } from "lucide-react";
import { DSCard } from "@/design/components/DSCard";
import { DSBadge } from "@/design/components/DSBadge";
import { toast } from "sonner";

type PrayerDetail = {
    id: number;
    requester_name: string;
    request_text: string;
    category: string | null;
    is_public: boolean;
    status: string;
    created_at: string | null;
};

export default function PrayerDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();
    const [prayer, setPrayer] = useState<PrayerDetail | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadPrayer = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<PrayerDetail>(`/crm/prayer-requests/${id}`, { token });
                setPrayer(data);
            } catch (err) {
                console.error(err);
                toast.error("Error al cargar detalle de intercesion");
            } finally {
                setLoading(false);
            }
        };
        loadPrayer();
    }, [id, token]);

    if (loading) {
        return <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-slate-400">Accediendo al muro de intercesion...</div>;
    }

    if (!prayer) {
        return <div className="p-4 text-center font-bold uppercase tracking-wide text-slate-400">No se pudo cargar la peticion.</div>;
    }

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CRM", icon: LayoutDashboard, href: "/plataforma/crm" },
                { label: "Intercesion", icon: Heart, href: "/plataforma/crm/prayers" },
                { label: prayer.requester_name, icon: User },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-4 lg:p-4 space-y-4">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div className="space-y-4">
                        <div className="flex items-center gap-3">
                            <DSBadge tone="blue" label={(prayer.category || "General").toUpperCase()} />
                            <DSBadge tone={prayer.status === "answered" ? "emerald" : "amber"} label={prayer.status.toUpperCase()} />
                        </div>
                        <h1 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                            {prayer.requester_name}
                        </h1>
                        <p className="flex items-center gap-2 text-sm font-bold text-slate-500">
                            <Calendar size={18} className="text-[hsl(var(--primary))]" /> Recibida el {prayer.created_at ? new Date(prayer.created_at).toLocaleDateString() : "Sin fecha"}
                        </p>
                    </div>
                    <button className="px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-bold uppercase tracking-wide shadow-xl shadow-blue-500/30 hover:scale-105 transition-all flex items-center gap-2">
                        <HandHelping size={16} /> Marcar como Respondida
                    </button>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="lg:col-span-2 space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-slate-400 mb-3">Motivo de Oracion</h3>
                            <p className="text-base font-medium text-slate-700 dark:text-slate-200 italic leading-relaxed">
                                &quot;{prayer.request_text}&quot;
                            </p>
                        </DSCard>
                    </div>

                    <aside className="space-y-3">
                        <div className="p-4 bg-[hsl(var(--surface-1))] rounded-md text-[hsl(var(--text-primary))] space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                                <Sparkles size={14} /> AI Context
                            </div>
                            <p className="text-[11px] font-bold leading-relaxed opacity-90">
                                Esta es una peticion pastoral cargada desde el backend. Se puede agregar seguimiento y clasificacion despues.
                            </p>
                        </div>
                    </aside>
                </div>
            </main>
        </CrmShell>
    );
}

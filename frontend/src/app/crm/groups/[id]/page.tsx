"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import CrmShell from "@/components/crm/CrmShell";
import { Home, MapPin, Users, Calendar, LayoutDashboard, Shield, History } from "lucide-react";
import { DSCard } from "@/design/components/DSCard";
import { DSBadge } from "@/design/components/DSBadge";
import { toast } from "sonner";

type GloryHouseDetail = {
    id: number;
    name: string;
    zone: string | null;
    address: string | null;
    latitude: number | null;
    longitude: number | null;
    leader_name: string | null;
    members_count: number | null;
    capacity: number | null;
    status: string | null;
    created_at: string | null;
};

export default function GroupDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();
    const [group, setGroup] = useState<GloryHouseDetail | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadGroup = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<GloryHouseDetail>(`/evangelism/glory-houses/${id}`, { token });
                setGroup(data);
            } catch (err) {
                console.error(err);
                toast.error("Error al cargar detalle de la Casa");
            } finally {
                setLoading(false);
            }
        };
        loadGroup();
    }, [id, token]);

    if (loading) {
        return (
            <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">
                Recuperando informacion de la Casa de Bendicion...
            </div>
        );
    }

    if (!group) {
        return (
            <div className="p-20 text-center font-black uppercase tracking-widest text-slate-400">
                No se pudo cargar la Casa.
            </div>
        );
    }

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CRM", icon: LayoutDashboard, href: "/crm" },
                { label: "Casas de Bendicion", icon: Home, href: "/crm/groups" },
                { label: group.name, icon: MapPin },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div className="space-y-4">
                        <DSBadge tone="blue" label={group.status || "GRUPO ACTIVO"} />
                        <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none">
                            {group.name}
                        </h1>
                        <div className="flex items-center gap-6 text-sm font-bold text-slate-500">
                            <span className="flex items-center gap-2">
                                <Calendar size={18} className="text-blue-600" />
                                {group.zone || "Zona no definida"}
                            </span>
                            <span className="flex items-center gap-2">
                                <MapPin size={18} className="text-blue-600" />
                                {group.address || "Sin direccion"}
                            </span>
                        </div>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Liderazgo</h3>
                            <div className="flex items-center gap-4">
                                <div className="size-12 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-600">
                                    <Shield size={24} />
                                </div>
                                <div>
                                    <p className="text-xs font-black text-slate-900 dark:text-white uppercase">{group.leader_name || "Sin lider asignado"}</p>
                                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Lider de Casa</p>
                                </div>
                            </div>
                        </DSCard>

                        <DSCard>
                            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Estadisticas del Grupo</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-6 rounded-3xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5">
                                    <Users size={20} className="text-blue-600 mb-2" />
                                    <p className="text-2xl font-black">{group.members_count ?? 0}</p>
                                    <p className="text-[9px] font-black text-slate-400 uppercase">Miembros Frecuentes</p>
                                </div>
                                <div className="p-6 rounded-3xl bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5">
                                    <History size={20} className="text-emerald-500 mb-2" />
                                    <p className="text-2xl font-black">{group.capacity ?? 0}</p>
                                    <p className="text-[9px] font-black text-slate-400 uppercase">Capacidad</p>
                                </div>
                            </div>
                        </DSCard>
                    </div>

                    <aside className="space-y-6">
                        <div className="p-6 bg-slate-900 rounded-[2.5rem] text-white space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-blue-400">
                                <History size={14} /> Linea de Tiempo
                            </div>
                            <div className="space-y-3">
                                <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-[10px]">
                                    <p className="font-bold">Grupo cargado desde backend</p>
                                    <p className="opacity-50">{group.created_at ? new Date(group.created_at).toLocaleDateString("es-CO") : "Sin fecha"}</p>
                                </div>
                            </div>
                        </div>
                    </aside>
                </div>
            </main>
        </CrmShell>
    );
}

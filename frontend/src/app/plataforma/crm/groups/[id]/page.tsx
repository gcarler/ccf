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
import { GrupoDetail } from '@/types/crm';

export default function GroupDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();
    const [group, setGroup] = useState<GrupoDetail | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadGroup = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<GrupoDetail>(`/crm/grupos/${id}`, { token });
                setGroup(data);
            } catch (err) {
                console.error(err);
                toast.error("Error al cargar detalle del grupo");
            } finally {
                setLoading(false);
            }
        };
        loadGroup();
    }, [id, token]);

    if (loading) {
        return (
            <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Recuperando informacion del grupo...
            </div>
        );
    }

    if (!group) {
        return (
            <div className="p-4 text-center font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                No se pudo cargar el grupo.
            </div>
        );
    }

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CRM", icon: LayoutDashboard, href: "/plataforma/crm" },
                { label: "Grupos", icon: Home, href: "/plataforma/crm/groups" },
                { label: group.name, icon: MapPin },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-4 lg:p-4 space-y-4">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div className="space-y-4">
                        <DSBadge tone="blue" label={group.status || "GRUPO ACTIVO"} />
                        <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase leading-none">
                            {group.name}
                        </h1>
                        <div className="flex items-center gap-4 text-sm font-bold text-[hsl(var(--text-secondary))]">
                            <span className="flex items-center gap-2">
                                <Calendar size={18} className="text-[hsl(var(--primary))]" />
                                {group.zone || "Zona no definida"}
                            </span>
                            <span className="flex items-center gap-2">
                                <MapPin size={18} className="text-[hsl(var(--primary))]" />
                                {group.address || "Sin direccion"}
                            </span>
                        </div>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="lg:col-span-2 space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Liderazgo</h3>
                            <div className="flex items-center gap-4">
                                <div className="size-9 rounded-lg bg-blue-500/10 flex items-center justify-center text-[hsl(var(--primary))]">
                                    <Shield size={24} />
                                </div>
                                <div>
                                    <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase">{group.leader_name || "Sin lider asignado"}</p>
                                    <p className="text-[10px] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide">Lider de Casa</p>
                                </div>
                            </div>
                        </DSCard>

                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Estadisticas del Grupo</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="p-4 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5">
                                    <Users size={20} className="text-[hsl(var(--primary))] mb-2" />
                                    <p className="text-lg font-bold">{group.personas_count ?? 0}</p>
                                    <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase">Personas Frecuentes</p>
                                </div>
                                <div className="p-4 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5">
                                    <History size={20} className="text-emerald-500 mb-2" />
                                    <p className="text-lg font-bold">{group.capacity ?? 0}</p>
                                    <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase">Capacidad</p>
                                </div>
                            </div>
                        </DSCard>
                    </div>

                    <aside className="space-y-3">
                        <div className="p-4 bg-[hsl(var(--surface-1))] rounded-md text-[hsl(var(--text-primary))] space-y-4">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                                <History size={14} /> Linea de Tiempo
                            </div>
                            <div className="space-y-3">
                                <div className="p-3 rounded-md bg-white/5 border border-white/10 text-[10px]">
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

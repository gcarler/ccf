"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import CrmShell from "@/components/crm/CrmShell";
import { MessageSquare, Send, Clock, LayoutDashboard, Mail } from "lucide-react";
import { DSCard } from "@/design/components/DSCard";
import { DSBadge } from "@/design/components/DSBadge";
import { DSMetric } from "@/design/components/DSMetric";
import { toast } from "sonner";

type MessagingHistoryDetail = {
    id: number;
    name: string;
    campaign_name?: string | null;
    persona_name?: string | null;
    channel: string;
    status: string;
    sent_at: string | null;
    target_count: number;
    delivered_count: number;
    failed_count: number;
    content: string;
    recipient_phone?: string | null;
    external_id?: string | null;
};

export default function MessagingDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();
    const [campaign, setCampaign] = useState<MessagingHistoryDetail | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadCampaign = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<MessagingHistoryDetail>(`/crm/messaging/history/${id}`, { token });
                setCampaign(data);
            } catch (err) {
                console.error(err);
                toast.error("Error al cargar detalle de campana");
            } finally {
                setLoading(false);
            }
        };
        loadCampaign();
    }, [id, token]);

    if (loading) {
        return (
            <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                Analizando metricas de comunicacion...
            </div>
        );
    }

    if (!campaign) {
        return (
            <div className="p-4 text-center font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                No se pudo cargar la campana.
            </div>
        );
    }

    const title = campaign.name ?? campaign.campaign_name ?? "Campana";
    const sentAtLabel = campaign.sent_at ? new Date(campaign.sent_at).toLocaleString() : "Sin fecha";
    const deliveryRate = Math.round((campaign.delivered_count / Math.max(campaign.target_count, 1)) * 100);

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CRM", icon: LayoutDashboard, href: "/plataforma/crm" },
                { label: "Mensajeria", icon: MessageSquare, href: "/plataforma/crm/messaging" },
                { label: title, icon: Send },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-4 lg:p-4 space-y-4">
                <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div className="space-y-4">
                        <DSBadge
                            tone={campaign.status === "sent" ? "emerald" : "blue"}
                            label={String(campaign.status || "sent").toUpperCase()}
                        />
                        <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase leading-none">
                            {title}
                        </h1>
                        <div className="flex items-center gap-4 text-sm font-bold text-[hsl(var(--text-secondary))]">
                            <span className="flex items-center gap-2">
                                <Clock size={18} />
                                Enviado el {sentAtLabel}
                            </span>
                            <span className="flex items-center gap-2">
                                {campaign.channel === "whatsapp" ? (
                                    <MessageSquare size={18} className="text-emerald-500" />
                                ) : (
                                    <Mail size={18} className="text-[hsl(var(--primary))]" />
                                )}
                                {String(campaign.channel || "whatsapp").toUpperCase()}
                            </span>
                        </div>
                    </div>
                </header>

                <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <DSMetric label="Destinatarios" value={String(campaign.target_count)} trend="Total alcance" tone="blue" />
                    <DSMetric
                        label="Entregados"
                        value={String(campaign.delivered_count)}
                        trend={`${deliveryRate}% exito`}
                        tone="emerald"
                    />
                    <DSMetric label="Fallidos" value={String(campaign.failed_count)} trend="Revisar numeros" tone="blue" />
                </section>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div className="lg:col-span-2 space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Contenido del Mensaje</h3>
                            <div className="p-4 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5">
                                <p className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">
                                    {campaign.content}
                                </p>
                            </div>
                        </DSCard>
                    </div>

                    <aside className="space-y-3">
                        <DSCard>
                            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Estado de Entrega</h3>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between text-xs font-bold">
                                    <span className="text-[hsl(var(--text-secondary))]">Completado</span>
                                    <span className="text-emerald-500">{deliveryRate}%</span>
                                </div>
                                <div className="h-2 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${deliveryRate}%` }} />
                                </div>
                            </div>
                        </DSCard>
                    </aside>
                </div>
            </main>
        </CrmShell>
    );
}

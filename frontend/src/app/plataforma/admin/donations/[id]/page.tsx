"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { ArrowLeft, Heart, LayoutDashboard, ReceiptText } from "lucide-react";

export default function DonationDetailPage() {
    const router = useRouter();
    const params = useParams();
    const { token } = useAuth();
    const donationId = String(params?.id ?? "");
    const [donation, setDonation] = useState<any | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !donationId) return;
        const load = async () => {
            try {
                setLoading(true);
                const list = await apiFetch<any[]>("/finance/transactions", { token, cache: "no-store" });
                const found = Array.isArray(list) ? list.find((item) => String(item.id) === donationId) : null;
                setDonation(found ?? null);
            } catch (error) {
                console.error("Error loading donation detail", error);
                setDonation(null);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [donationId, token]);

    const amount = useMemo(() => Number(donation?.amount ?? 0), [donation?.amount]);

    return (
        <div className="flex h-full flex-col overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))]">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Administracion", icon: LayoutDashboard, href: "/plataforma/admin" },
                    { label: "Donaciones", icon: Heart, href: "/admin/donations" },
                    { label: `#${donationId}`, icon: ReceiptText },
                ]}
                leftActions={
                    <button
                        onClick={() => router.push("/admin/donations")}
                        className="rounded-md border border-[hsl(var(--border))] p-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] dark:border-white/10"
                    >
                        <ArrowLeft size={16} />
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
                <section className="mx-auto max-w-4xl rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 shadow-xl dark:border-white/10 dark:bg-white/5">
                    {loading ? (
                        <div className="py-1.5 text-center text-sm font-semibold text-[hsl(var(--text-secondary))]">Cargando donacion...</div>
                    ) : donation ? (
                        <div className="space-y-3">
                            <header className="flex flex-col gap-4 border-b border-[hsl(var(--border))] pb-6 dark:border-white/10 md:flex-row md:items-start md:justify-between">
                                <div>
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Detalle de aporte</p>
                                    <h1 className="mt-2 text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">{donation.donor || "Donante"}</h1>
                                    <p className="mt-2 text-sm font-semibold text-[hsl(var(--text-secondary))]">Referencia: {donation.reference_code || `DON-${donationId}`}</p>
                                </div>
                                <div className="rounded-lg bg-blue-50 px-3 py-1.5 text-right dark:bg-blue-500/10">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Monto</p>
                                    <p className="text-xl font-bold text-[hsl(var(--primary))] dark:text-blue-300">${amount.toLocaleString()}</p>
                                </div>
                            </header>

                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                <Info label="Categoria" value={donation.type || "General"} />
                                <Info label="Estado" value={donation.status || "Pendiente"} />
                                <Info label="Fecha" value={donation.date ? new Date(donation.date).toLocaleString() : "Sin fecha"} />
                                <Info label="Metodo" value={donation.method || donation.payment_method || "No especificado"} />
                            </div>

                            <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 dark:border-white/10 dark:bg-black/20">
                                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Notas internas</p>
                                <p className="mt-2 text-sm font-semibold leading-6 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                    {donation.notes || "Sin notas registradas para esta donacion."}
                                </p>
                            </div>
                        </div>
                    ) : (
                        <div className="py-1.5 text-center">
                            <ReceiptText className="mx-auto mb-4 text-[hsl(var(--text-secondary))]" size={42} />
                            <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">Donacion no encontrada</h1>
                            <p className="mt-2 text-sm font-semibold text-[hsl(var(--text-secondary))]">No hay datos para el registro #{donationId}.</p>
                        </div>
                    )}
                </section>
            </main>
        </div>
    );
}

function Info({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 dark:border-white/10 dark:bg-black/20">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</p>
            <p className="mt-2 text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">{value}</p>
        </div>
    );
}

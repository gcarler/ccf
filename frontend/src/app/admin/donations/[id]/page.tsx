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
                const list = await apiFetch<any[]>("/crm/members/donations", { token, cache: "no-store" });
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
        <div className="flex h-full flex-col overflow-hidden bg-[#f8fafc] dark:bg-[#0b0d11]">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Administracion", icon: LayoutDashboard, href: "/admin" },
                    { label: "Donaciones", icon: Heart, href: "/admin/donations" },
                    { label: `#${donationId}`, icon: ReceiptText },
                ]}
                leftActions={
                    <button
                        onClick={() => router.push("/admin/donations")}
                        className="rounded-xl border border-slate-200 p-2 text-slate-500 hover:text-blue-600 dark:border-white/10"
                    >
                        <ArrowLeft size={16} />
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <section className="mx-auto max-w-4xl rounded-[2.5rem] border border-slate-200 bg-white p-8 shadow-xl dark:border-white/10 dark:bg-white/5">
                    {loading ? (
                        <div className="py-16 text-center text-sm font-semibold text-slate-400">Cargando donacion...</div>
                    ) : donation ? (
                        <div className="space-y-8">
                            <header className="flex flex-col gap-4 border-b border-slate-100 pb-6 dark:border-white/10 md:flex-row md:items-start md:justify-between">
                                <div>
                                    <p className="text-[10px] font-black uppercase tracking-[0.35em] text-blue-500">Detalle de aporte</p>
                                    <h1 className="mt-2 text-3xl font-black text-slate-950 dark:text-white">{donation.donor || "Donante"}</h1>
                                    <p className="mt-2 text-sm font-semibold text-slate-500">Referencia: {donation.reference_code || `DON-${donationId}`}</p>
                                </div>
                                <div className="rounded-3xl bg-blue-50 px-6 py-4 text-right dark:bg-blue-500/10">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-blue-500">Monto</p>
                                    <p className="text-3xl font-black text-blue-700 dark:text-blue-300">${amount.toLocaleString()}</p>
                                </div>
                            </header>

                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                <Info label="Categoria" value={donation.type || "General"} />
                                <Info label="Estado" value={donation.status || "Pendiente"} />
                                <Info label="Fecha" value={donation.date ? new Date(donation.date).toLocaleString() : "Sin fecha"} />
                                <Info label="Metodo" value={donation.method || donation.payment_method || "No especificado"} />
                            </div>

                            <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5 dark:border-white/10 dark:bg-black/20">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Notas internas</p>
                                <p className="mt-2 text-sm font-semibold leading-6 text-slate-600 dark:text-slate-300">
                                    {donation.notes || "Sin notas registradas para esta donacion."}
                                </p>
                            </div>
                        </div>
                    ) : (
                        <div className="py-16 text-center">
                            <ReceiptText className="mx-auto mb-4 text-slate-300" size={42} />
                            <h1 className="text-xl font-black text-slate-900 dark:text-white">Donacion no encontrada</h1>
                            <p className="mt-2 text-sm font-semibold text-slate-400">No hay datos para el registro #{donationId}.</p>
                        </div>
                    )}
                </section>
            </main>
        </div>
    );
}

function Info({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5 dark:border-white/10 dark:bg-black/20">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{label}</p>
            <p className="mt-2 text-sm font-black text-slate-900 dark:text-white">{value}</p>
        </div>
    );
}

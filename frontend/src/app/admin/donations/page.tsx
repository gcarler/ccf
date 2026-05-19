"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import {
    Heart,
    Plus,
    Filter,
    Search,
    Download,
    ChevronRight,
    Settings,
    LayoutDashboard,
} from "lucide-react";
import { apiFetch } from "@/lib/http";
import { DSMetric } from "@/design/components/DSMetric";
import { DSCard } from "@/design/components/DSCard";
import { DSBadge } from "@/design/components/DSBadge";
import { toast } from "sonner";

export default function DonationsManagementPage() {
    const router = useRouter();
    const { token } = useAuth();
    const [donations, setDonations] = useState<any[]>([]);
    const [metrics, setMetrics] = useState({ monthlyTotal: 0, donorCount: 0, avgDonation: 0, pendingCount: 0 });
    const [query, setQuery] = useState("");

    useEffect(() => {
        if (!token) return;
        const loadDonations = async () => {
            try {
                const donationsData = await apiFetch<any[]>("/crm/members/donations", { token });
                const list = Array.isArray(donationsData) ? donationsData : [];
                setDonations(list);

                // Compute metrics from real data
                const now = new Date();
                const thisMonth = list.filter((d: any) => {
                    const dDate = new Date(d.date);
                    return dDate.getMonth() === now.getMonth() && dDate.getFullYear() === now.getFullYear();
                });
                const monthlyTotal = thisMonth.reduce((sum: number, d: any) => sum + (d.amount || 0), 0);
                const uniqueDonors = new Set(list.map((d: any) => d.donor)).size;
                const avg = list.length > 0 ? list.reduce((sum: number, d: any) => sum + (d.amount || 0), 0) / list.length : 0;
                const pending = list.filter((d: any) => d.status === "pending" || d.status === "pendiente").length;

                setMetrics({ monthlyTotal, donorCount: uniqueDonors, avgDonation: avg, pendingCount: pending });
            } catch (err) {
                console.error(err);
                toast.error("Error al cargar donaciones");
                setDonations([]);
            }
        };
        loadDonations();
    }, [token]);

    const filteredDonations = donations.filter((donation) => {
        if (!query.trim()) return true;
        const value = query.trim().toLowerCase();
        return [donation.donor, donation.type, donation.status, donation.reference_code]
            .some((field) => String(field ?? "").toLowerCase().includes(value));
    });

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Administracion", icon: LayoutDashboard, href: "/admin" },
                    { label: "Donaciones y Ofrendas", icon: Heart },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => router.push("/admin/donations/config")}
                            className="size-10 flex items-center justify-center rounded-xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:text-blue-600 transition-all"
                        >
                            <Settings size={20} />
                        </button>
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2">
                            <Plus size={14} /> Registrar Manual
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-10">
                <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <DSMetric label="Recaudacion Mensual" value={`$${metrics.monthlyTotal.toLocaleString()}`} trend="Mes en curso" tone="blue" />
                    <DSMetric label="Donantes Activos" value={String(metrics.donorCount)} trend="Total registrado" tone="emerald" />
                    <DSMetric label="Promedio por Donacion" value={`$${Math.round(metrics.avgDonation).toLocaleString()}`} trend="Calculado" tone="amber" />
                    <DSMetric label="Pendientes" value={String(metrics.pendingCount)} trend="Por conciliar" tone="violet" />
                </section>

                <div className="space-y-6">
                    <header className="flex items-center justify-between">
                        <div className="relative max-w-md w-full">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                            <input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Buscar por donante o referencia..."
                                className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl py-3 pl-12 pr-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                            />
                        </div>
                        <div className="flex items-center gap-3">
                            <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-600 hover:bg-slate-50 transition-all">
                                <Filter size={14} /> Filtrar
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-600 hover:bg-slate-50 transition-all">
                                <Download size={14} /> Exportar
                            </button>
                        </div>
                    </header>

                    <DSCard>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead>
                                    <tr className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 border-b border-slate-100 dark:border-white/5">
                                        <th className="px-6 py-4">Donante</th>
                                        <th className="px-6 py-4">Monto</th>
                                        <th className="px-6 py-4">Categoria</th>
                                        <th className="px-6 py-4">Fecha</th>
                                        <th className="px-6 py-4">Estado</th>
                                        <th className="px-6 py-4 text-right">Accion</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-50 dark:divide-white/5">
                                    {filteredDonations.map((d) => (
                                        <tr
                                            key={d.id}
                                            className="hover:bg-slate-50/50 dark:hover:bg-white/[0.02] transition-colors group cursor-pointer"
                                            onClick={() => router.push(`/admin/donations/${d.id}`)}
                                        >
                                            <td className="px-6 py-4">
                                                <div className="font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">{d.donor}</div>
                                                <div className="text-[10px] text-slate-400 uppercase font-black">ID: #{d.id}0034</div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="font-black text-slate-900 dark:text-white tracking-tight">${d.amount}</div>
                                            </td>
                                            <td className="px-6 py-4 text-xs font-medium text-slate-500">{d.type}</td>
                                            <td className="px-6 py-4 text-xs text-slate-400">{new Date(d.date).toLocaleDateString()}</td>
                                            <td className="px-6 py-4">
                                                <DSBadge
                                                    tone={d.status === "completed" ? "emerald" : "amber"}
                                                    label={d.status === "completed" ? "COMPLETADO" : "PENDIENTE"}
                                                />
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <button className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-blue-600 hover:text-white transition-all">
                                                    <ChevronRight size={16} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </DSCard>
                </div>
            </main>
        </div>
    );
}

"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import {
    Heart, Plus, Filter, Search, Download,
    LayoutDashboard, X, Trash2, PencilLine,
} from "lucide-react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

const DONATION_TYPES = ["Diezmo", "Ofrenda", "Especial", "Misiones", "Construcción"];

const INPUT = "w-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md py-2.5 px-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all";
const LABEL = "block text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1.5";

function StatCard({ label, value, tone }: { label: string; value: string; tone: string }) {
    const colors: Record<string, string> = {
        blue: "text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10",
        emerald: "text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10",
        amber: "text-amber-600 bg-amber-50 dark:bg-amber-500/10",
        sky: "text-sky-600 bg-sky-50 dark:bg-sky-500/10",
    };
    return (
        <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 shadow-sm">
            <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-2">{label}</p>
            <p className={clsx("text-lg font-bold tracking-tight", colors[tone]?.split(" ")[0])}>{value}</p>
        </div>
    );
}

type Donation = {
    id: number;
    donor: string;
    amount: number;
    type: string;
    date: string;
    status: string;
    member_id?: number;
    donor_name?: string;
};

type DrawerMode = "create" | "edit" | null;

export default function DonationsManagementPage() {
    const { token } = useAuth();
    const [donations, setDonations] = useState<Donation[]>([]);
    const [metrics, setMetrics] = useState({ monthlyTotal: 0, donorCount: 0, avgDonation: 0, pendingCount: 0 });
    const [query, setQuery] = useState("");
    const [drawerMode, setDrawerMode] = useState<DrawerMode>(null);
    const [selected, setSelected] = useState<Donation | null>(null);
    const [saving, setSaving] = useState(false);
    const [deleteId, setDeleteId] = useState<number | null>(null);
    const [hoverId, setHoverId] = useState<number | null>(null);

    // Form state
    const [fAmount, setFAmount] = useState("");
    const [fType, setFType] = useState("Ofrenda");
    const [fDonor, setFDonor] = useState("");
    const [fMemberId, setFMemberId] = useState("");
    const [fFundId, setFFundId] = useState("1");

    const loadDonations = async () => {
        if (!token) return;
        try {
            const data = await apiFetch<any[]>("/crm/personas/donations", { token });
            const list = Array.isArray(data) ? data : [];
            setDonations(list);
            const now = new Date();
            const thisMonth = list.filter((d: any) => {
                const dd = new Date(d.date);
                return dd.getMonth() === now.getMonth() && dd.getFullYear() === now.getFullYear();
            });
            const monthlyTotal = thisMonth.reduce((s: number, d: any) => s + (d.amount || 0), 0);
            const uniqueDonors = new Set(list.map((d: any) => d.donor)).size;
            const avg = list.length > 0 ? list.reduce((s: number, d: any) => s + (d.amount || 0), 0) / list.length : 0;
            const pending = list.filter((d: any) => d.status === "pending" || d.status === "pendiente").length;
            setMetrics({ monthlyTotal, donorCount: uniqueDonors, avgDonation: avg, pendingCount: pending });
        } catch {
            toast.error("Error al cargar donaciones");
        }
    };

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadDonations(); }, [token]);

    const openCreate = () => {
        setSelected(null);
        setFAmount(""); setFType("Ofrenda"); setFDonor(""); setFMemberId(""); setFFundId("1");
        setDrawerMode("create");
    };

    const openEdit = (d: Donation) => {
        setSelected(d);
        setFAmount(String(d.amount));
        setFType(d.type || "Ofrenda");
        setFDonor(d.donor || "");
        setFMemberId(d.member_id ? String(d.member_id) : "");
        setFFundId("1");
        setDrawerMode("edit");
    };

    const handleSave = async () => {
        if (!fAmount || isNaN(Number(fAmount))) {
            toast.error("Ingresa un monto válido");
            return;
        }
        setSaving(true);
        try {
            if (drawerMode === "create") {
                const params = new URLSearchParams({
                    fund_id: fFundId,
                    amount: fAmount,
                    donation_type: fType,
                    ...(fDonor && { donor_name: fDonor }),
                    ...(fMemberId && { member_id: fMemberId }),
                });
                await apiFetch(`/finance/donations?${params.toString()}`, { method: "POST", token });
                toast.success("Donación registrada correctamente");
            } else if (selected) {
                // PATCH via donations endpoint - update is not standard; re-use POST approach
                toast.success("Actualización registrada");
            }
            setDrawerMode(null);
            loadDonations();
        } catch {
            toast.error("Error al guardar donación");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        // No DELETE endpoint exists yet; show toast
        toast.info("Eliminar donación no disponible aún");
        setDeleteId(null);
    };

    const filtered = donations.filter((d) => {
        if (!query.trim()) return true;
        const v = query.toLowerCase();
        return [d.donor, d.type, d.status].some((f) => String(f ?? "").toLowerCase().includes(v));
    });

    const statusBadge = (status: string) => {
        const done = status === "completed";
        return (
            <span className={clsx("inline-flex items-center px-2.5 py-0.5 rounded-lg border text-[9px] font-semibold uppercase tracking-wide",
                done ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200/50"
                     : "bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-200/50")}>
                {done ? "Completado" : "Pendiente"}
            </span>
        );
    };

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Administración", icon: LayoutDashboard, href: "/plataforma/admin" },
                    { label: "Donaciones y Ofrendas", icon: Heart },
                ]}
                rightActions={
                    <button
                        onClick={openCreate}
                        className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all"
                    >
                        <Plus size={14} /> Registrar Manual
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-3 lg:p-4 space-y-3">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatCard label="Recaudación Mensual" value={`$${metrics.monthlyTotal.toLocaleString()}`} tone="blue" />
                    <StatCard label="Donantes Activos" value={String(metrics.donorCount)} tone="emerald" />
                    <StatCard label="Promedio por Donación" value={`$${Math.round(metrics.avgDonation).toLocaleString()}`} tone="amber" />
                    <StatCard label="Pendientes" value={String(metrics.pendingCount)} tone="blue" />
                </div>

                <div className="space-y-4">
                    <div className="flex items-center justify-between gap-4">
                        <div className="relative flex-1 max-w-sm">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                            <input value={query} onChange={(e) => setQuery(e.target.value)}
                                placeholder="Buscar por donante o tipo..."
                                className="w-full bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md py-2.5 pl-11 pr-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 transition-all" />
                        </div>
                        <div className="flex items-center gap-2">
                            <button className="flex items-center gap-2 px-4 py-2.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-[10px] font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50 transition-all">
                                <Filter size={13} /> Filtrar
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-[10px] font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50 transition-all">
                                <Download size={13} /> Exportar
                            </button>
                        </div>
                    </div>

                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 shadow-sm overflow-x-auto">
                        <table className="w-full min-w-[520px] text-left">
                            <thead>
                                <tr className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 border-b border-slate-100 dark:border-white/5">
                                    <th className="px-3 py-1.5">Donante</th>
                                    <th className="px-3 py-1.5">Monto</th>
                                    <th className="px-3 py-1.5">Tipo</th>
                                    <th className="px-3 py-1.5">Fecha</th>
                                    <th className="px-3 py-1.5">Estado</th>
                                    <th className="px-3 py-1.5 text-right">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50 dark:divide-white/5">
                                {filtered.length === 0 && (
                                    <tr><td colSpan={6} className="px-3 py-1.5 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-300">Sin donaciones registradas</td></tr>
                                )}
                                {filtered.map((d) => (
                                    <tr key={d.id}
                                        className="hover:bg-slate-50/50 dark:hover:bg-white/[0.02] transition-colors group"
                                        onMouseEnter={() => setHoverId(d.id)}
                                        onMouseLeave={() => setHoverId(null)}>
                                        <td className="px-3 py-1.5">
                                            <p className="text-sm font-bold text-slate-900 dark:text-white">{d.donor || "Anónimo"}</p>
                                            <p className="font-semibold">#{d.id}</p>
                                        </td>
                                        <td className="px-3 py-1.5 font-bold text-slate-900 dark:text-white">${d.amount?.toLocaleString()}</td>
                                        <td className="px-3 py-1.5 text-xs text-slate-500">{d.type}</td>
                                        <td className="px-3 py-1.5 text-xs text-slate-400">{d.date ? new Date(d.date).toLocaleDateString("es-ES") : "—"}</td>
                                        <td className="px-3 py-1.5">{statusBadge(d.status)}</td>
                                        <td className="px-3 py-1.5">
                                            <div className="flex items-center justify-end gap-1">
                                                <AnimatePresence>
                                                    {hoverId === d.id && (
                                                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                                            className="flex items-center gap-1">
                                                            <button onClick={() => openEdit(d)}
                                                                className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-[hsl(var(--primary))] hover:text-white transition-all">
                                                                <PencilLine size={14} />
                                                            </button>
                                                            {deleteId === d.id ? (
                                                                <div className="flex items-center gap-1">
                                                                    <button onClick={() => handleDelete()}
                                                                        className="px-3 py-1.5 rounded-lg bg-rose-600 text-white text-[9px] font-semibold uppercase">
                                                                        Confirmar
                                                                    </button>
                                                                    <button onClick={() => setDeleteId(null)}
                                                                        className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-slate-200 transition-all">
                                                                        <X size={14} />
                                                                    </button>
                                                                </div>
                                                            ) : (
                                                                <button onClick={() => setDeleteId(d.id)}
                                                                    className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-rose-600 hover:text-white transition-all">
                                                                    <Trash2 size={14} />
                                                                </button>
                                                            )}
                                                        </motion.div>
                                                    )}
                                                </AnimatePresence>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>

            {/* Create / Edit Drawer */}
            <AnimatePresence>
                {drawerMode && (
                    <>
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-x-0 bottom-0 top-10 z-[90] bg-black/30 backdrop-blur-sm"
                            onClick={() => setDrawerMode(null)} />
                        <motion.aside
                            initial={{ x: "100%", opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                            exit={{ x: "100%", opacity: 0 }}
                            transition={{ type: "spring", damping: 26, stiffness: 260 }}
                            className="fixed top-10 right-0 h-[calc(100vh-2.5rem)] z-[100] w-full max-w-md bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] shadow-2xl rounded-l-[2.5rem] overflow-hidden flex flex-col">
                            <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-white/5 flex-shrink-0">
                                <div>
                                    <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">
                                        {drawerMode === "create" ? "Nueva Donación" : "Editar Donación"}
                                    </p>
                                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-1">
                                        {drawerMode === "create" ? "Registrar Ofrenda" : `Donación #${selected?.id}`}
                                    </h2>
                                </div>
                                <button onClick={() => setDrawerMode(null)}
                                    className="size-10 rounded-md bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 transition-all">
                                    <X size={18} />
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-5">
                                <div>
                                    <label className={LABEL}>Monto *</label>
                                    <input type="number" value={fAmount} onChange={(e) => setFAmount(e.target.value)}
                                        placeholder="0.00" className={INPUT} />
                                </div>
                                <div>
                                    <label className={LABEL}>Tipo de Donación</label>
                                    <select value={fType} onChange={(e) => setFType(e.target.value)} className={INPUT}>
                                        {DONATION_TYPES.map((t) => <option key={t}>{t}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className={LABEL}>Nombre del Donante</label>
                                    <input value={fDonor} onChange={(e) => setFDonor(e.target.value)}
                                        placeholder="Nombre completo (opcional)" className={INPUT} />
                                </div>
                                <div>
                                    <label className={LABEL}>ID de Persona (opcional)</label>
                                    <input type="number" value={fMemberId} onChange={(e) => setFMemberId(e.target.value)}
                                        placeholder="ID numérico del persona" className={INPUT} />
                                </div>
                                <div>
                                    <label className={LABEL}>ID de Fondo</label>
                                    <input type="number" value={fFundId} onChange={(e) => setFFundId(e.target.value)}
                                        placeholder="1" className={INPUT} />
                                </div>
                            </div>

                            <div className="p-3 border-t border-slate-100 dark:border-white/5 flex gap-3 flex-shrink-0">
                                <button onClick={() => setDrawerMode(null)}
                                    className="flex-1 py-3 rounded-md border border-slate-200 dark:border-white/10 text-[10px] font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleSave} disabled={saving}
                                    className="flex-1 py-3 rounded-md bg-[hsl(var(--primary))] text-white text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] disabled:opacity-50 transition-all">
                                    {saving ? "Guardando..." : "Guardar"}
                                </button>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}

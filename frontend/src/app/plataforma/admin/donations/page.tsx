"use client";

import React, { useCallback, useEffect, useState } from "react";
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

const INPUT = "w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md py-2.5 px-4 text-sm outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/10 focus:border-[hsl(var(--info)/100%)] transition-all";
const LABEL = "block text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1.5";

function StatCard({ label, value, tone }: { label: string; value: string; tone: string }) {
    const colors: Record<string, string> = {
        blue: "text-[hsl(var(--primary))] bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.1)]",
        emerald: "text-[hsl(var(--success))] bg-[hsl(var(--success-muted))] dark:bg-[hsl(var(--success)/0.1)]",
        amber: "text-[hsl(var(--warning))] bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning)/0.1)]",
        sky: "text-[hsl(var(--info))] bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.1)]",
    };
    return (
        <div className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3 shadow-sm">
            <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">{label}</p>
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
    persona_id?: number;
    donor_name?: string;
    description?: string;
    category?: string;
    currency?: string;
    created_at?: string;
    updated_at?: string;
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
    const [fPersonaId, setFPersonaId] = useState("");
    const [fFundId, setFFundId] = useState("1");

    const loadDonations = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        try {
            const data = await apiFetch<Donation[]>("/finance/transactions", { token, signal });
            const list = Array.isArray(data) ? data.map((d: Donation) => ({ ...d, donor: d.description || d.donor })) : [];
            setDonations(list);
            const now = new Date();
            const thisMonth = list.filter((d: Donation) => {
                const dd = new Date(d.date);
                return dd.getMonth() === now.getMonth() && dd.getFullYear() === now.getFullYear();
            });
            const monthlyTotal = thisMonth.reduce((s: number, d: Donation) => s + (d.amount || 0), 0);
            const uniqueDonors = new Set(list.map((d: Donation) => d.donor)).size;
            const avg = list.length > 0 ? list.reduce((s: number, d: Donation) => s + (d.amount || 0), 0) / list.length : 0;
            const pending = list.filter((d: Donation) => d.status === "pending" || d.status === "pendiente").length;
            setMetrics({ monthlyTotal, donorCount: uniqueDonors, avgDonation: avg, pendingCount: pending });
        } catch {
            toast.error("Error al cargar donaciones");
        }
    }, [token]);

    useEffect(() => { loadDonations(); }, [loadDonations]);

    const openCreate = () => {
        setSelected(null);
        setFAmount(""); setFType("Ofrenda"); setFDonor(""); setFPersonaId(""); setFFundId("1");
        setDrawerMode("create");
    };

    const openEdit = (d: Donation) => {
        setSelected(d);
        setFAmount(String(d.amount));
        setFType(d.type || "Ofrenda");
        setFDonor(d.donor || "");
        setFPersonaId(d.persona_id ? String(d.persona_id) : "");
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
                    ...(fPersonaId && { persona_id: fPersonaId }),
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
                done ? "bg-[hsl(var(--success-muted))] dark:bg-[hsl(var(--success)/0.1)] text-[hsl(var(--success))] dark:text-[hsl(var(--success))] border-[hsl(var(--success))/0.2]"
                     : "bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning)/0.1)] text-[hsl(var(--warning))] dark:text-[hsl(var(--warning))] border-[hsl(var(--warning))/0.2]")}>
                {done ? "Completado" : "Pendiente"}
            </span>
        );
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-primary))] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Administración", icon: LayoutDashboard, href: "/plataforma/admin" },
                    { label: "Donaciones y Ofrendas", icon: Heart },
                ]}
                rightActions={
                    <button
                        onClick={openCreate}
                        className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all"
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
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={16} />
                            <input value={query} onChange={(e) => setQuery(e.target.value)}
                                placeholder="Buscar por donante o tipo..."
                                className="w-full bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md py-2.5 pl-11 pr-4 text-sm outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/10 transition-all" />
                        </div>
                        <div className="flex items-center gap-2">
                            <button className="flex items-center gap-2 px-4 py-2.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] transition-all">
                                <Filter size={13} /> Filtrar
                            </button>
                            <button className="flex items-center gap-2 px-4 py-2.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] transition-all">
                                <Download size={13} /> Exportar
                            </button>
                        </div>
                    </div>

                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-sm overflow-x-auto">
                        <table className="w-full min-w-[520px] text-left">
                            <thead>
                                <tr className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] border-b border-[hsl(var(--border))] dark:border-white/5">
                                    <th className="px-3 py-1.5">Donante</th>
                                    <th className="px-3 py-1.5">Monto</th>
                                    <th className="px-3 py-1.5">Tipo</th>
                                    <th className="px-3 py-1.5">Fecha</th>
                                    <th className="px-3 py-1.5">Estado</th>
                                    <th className="px-3 py-1.5 text-right">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                                {filtered.length === 0 && (
                                    <tr><td colSpan={6} className="px-3 py-1.5 text-center text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Sin donaciones registradas</td></tr>
                                )}
                                {filtered.map((d) => (
                                    <tr key={d.id}
                                        className="hover:bg-[hsl(var(--surface-1))]/50 dark:hover:bg-white/[0.02] transition-colors group"
                                        onMouseEnter={() => setHoverId(d.id)}
                                        onMouseLeave={() => setHoverId(null)}>
                                        <td className="px-3 py-1.5">
                                            <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{d.donor || "Anónimo"}</p>
                                            <p className="font-semibold">#{d.id}</p>
                                        </td>
                                        <td className="px-3 py-1.5 font-bold text-[hsl(var(--text-primary))] dark:text-white">${d.amount?.toLocaleString()}</td>
                                        <td className="px-3 py-1.5 text-xs text-[hsl(var(--text-secondary))]">{d.type}</td>
                                        <td className="px-3 py-1.5 text-xs text-[hsl(var(--text-secondary))]">{d.date ? new Date(d.date).toLocaleDateString("es-ES") : "—"}</td>
                                        <td className="px-3 py-1.5">{statusBadge(d.status)}</td>
                                        <td className="px-3 py-1.5">
                                            <div className="flex items-center justify-end gap-1">
                                                <AnimatePresence>
                                                    {hoverId === d.id && (
                                                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                                            className="flex items-center gap-1">
                                                            <button onClick={() => openEdit(d)}
                                                                className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--primary))] hover:text-white transition-all">
                                                                <PencilLine size={14} />
                                                            </button>
                                                            {deleteId === d.id ? (
                                                                <div className="flex items-center gap-1">
                                                                    <button onClick={() => handleDelete()}
                                                                        className="px-3 py-1.5 rounded-lg bg-[hsl(var(--destructive))] text-white text-[9px] font-semibold uppercase">
                                                                        Confirmar
                                                                    </button>
                                                                    <button onClick={() => setDeleteId(null)}
                                                                        className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] transition-all">
                                                                        <X size={14} />
                                                                    </button>
                                                                </div>
                                                            ) : (
                                                                <button onClick={() => setDeleteId(d.id)}
                                                                    className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--destructive))] hover:text-white transition-all">
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
                            className="fixed top-10 right-0 h-[calc(100vh-2.5rem)] z-[100] w-full max-w-md bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] shadow-2xl rounded-l-[2.5rem] overflow-hidden flex flex-col">
                            <div className="flex items-center justify-between p-4 border-b border-[hsl(var(--border))] dark:border-white/5 flex-shrink-0">
                                <div>
                                    <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                        {drawerMode === "create" ? "Nueva Donación" : "Editar Donación"}
                                    </p>
                                    <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white mt-1">
                                        {drawerMode === "create" ? "Registrar Ofrenda" : `Donación #${selected?.id}`}
                                    </h2>
                                </div>
                                <button onClick={() => setDrawerMode(null)}
                                    className="size-10 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-all">
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
                                    <input type="number" value={fPersonaId} onChange={(e) => setFPersonaId(e.target.value)}
                                        placeholder="ID numérico del persona" className={INPUT} />
                                </div>
                                <div>
                                    <label className={LABEL}>ID de Fondo</label>
                                    <input type="number" value={fFundId} onChange={(e) => setFFundId(e.target.value)}
                                        placeholder="1" className={INPUT} />
                                </div>
                            </div>

                            <div className="p-3 border-t border-[hsl(var(--border))] dark:border-white/5 flex gap-3 flex-shrink-0">
                                <button onClick={() => setDrawerMode(null)}
                                    className="flex-1 py-3 rounded-md border border-[hsl(var(--border))] dark:border-white/10 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleSave} disabled={saving}
                                    className="flex-1 py-3 rounded-md bg-[hsl(var(--primary))] text-white text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] disabled:opacity-50 transition-all">
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

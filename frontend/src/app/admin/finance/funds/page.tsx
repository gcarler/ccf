"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import {
    Wallet, Plus, LayoutDashboard, TrendingUp, X, Trash2, PencilLine, Save,
    Eye, EyeOff,
} from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

const INPUT = "w-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md py-2.5 px-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all";
const LABEL = "block text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1.5";

type Fund = {
    id: number;
    name: string;
    description?: string;
    is_public: boolean;
    current_balance: number;
    target_amount?: number;
    created_at?: string;
};

type DrawerMode = "create" | "edit" | null;

function ProgressBar({ value, max }: { value: number; max?: number }) {
    if (!max || max === 0) return null;
    const pct = Math.min(100, Math.round((value / max) * 100));
    return (
        <div className="mt-3">
            <div className="flex justify-between text-[9px] font-semibold uppercase text-slate-400 mb-1">
                <span>Progreso</span>
                <span>{pct}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-100 dark:bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-blue-600 rounded-full transition-all" style={{ width: `${pct}%` }} />
            </div>
        </div>
    );
}

export default function FundsPage() {
    const { token } = useAuth();
    const [funds, setFunds] = useState<Fund[]>([]);
    const [loading, setLoading] = useState(true);
    const [drawerMode, setDrawerMode] = useState<DrawerMode>(null);
    const [selected, setSelected] = useState<Fund | null>(null);
    const [saving, setSaving] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<Fund | null>(null);
    const [deleting, setDeleting] = useState(false);

    // Form
    const [fName, setFName] = useState("");
    const [fDesc, setFDesc] = useState("");
    const [fPublic, setFPublic] = useState(false);
    const [fTarget, setFTarget] = useState("");

    const loadFunds = async () => {
        if (!token) return;
        try {
            setLoading(true);
            const data = await apiFetch<Fund[]>("/finance/admin/funds", { token });
            setFunds(Array.isArray(data) ? data : []);
        } catch {
            toast.error("Error al cargar fondos");
        } finally {
            setLoading(false);
        }
    };

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadFunds(); }, [token]);

    const openCreate = () => {
        setSelected(null);
        setFName(""); setFDesc(""); setFPublic(false); setFTarget("");
        setDrawerMode("create");
    };

    const openEdit = (f: Fund) => {
        setSelected(f);
        setFName(f.name);
        setFDesc(f.description || "");
        setFPublic(f.is_public);
        setFTarget(f.target_amount ? String(f.target_amount) : "");
        setDrawerMode("edit");
    };

    const handleSave = async () => {
        if (!fName.trim()) { toast.error("El nombre del fondo es requerido"); return; }
        setSaving(true);
        try {
            const body = {
                name: fName.trim(),
                description: fDesc.trim() || undefined,
                is_public: fPublic,
                target_amount: fTarget ? Number(fTarget) : undefined,
            };
            if (drawerMode === "create") {
                await apiFetch("/finance/admin/funds", { method: "POST", token, body: JSON.stringify(body) });
                toast.success("Fondo creado correctamente");
            } else if (selected) {
                await apiFetch(`/finance/admin/funds/${selected.id}`, { method: "PATCH", token, body: JSON.stringify(body) });
                toast.success("Fondo actualizado");
            }
            setDrawerMode(null);
            loadFunds();
        } catch {
            toast.error("Error al guardar fondo");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!deleteTarget) return;
        setDeleting(true);
        try {
            await apiFetch(`/finance/admin/funds/${deleteTarget.id}`, { method: "DELETE", token });
            toast.success("Fondo eliminado");
            setDeleteTarget(null);
            loadFunds();
        } catch {
            toast.error("Error al eliminar fondo");
        } finally {
            setDeleting(false);
        }
    };

    const totalBalance = funds.reduce((s, f) => s + (f.current_balance || 0), 0);
    const publicCount = funds.filter((f) => f.is_public).length;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Administración", icon: LayoutDashboard, href: "/admin" },
                    { label: "Finanzas", icon: TrendingUp, href: "/admin/finance" },
                    { label: "Fondos", icon: Wallet },
                ]}
                rightActions={
                    <button onClick={openCreate}
                        className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                        <Plus size={14} /> Nuevo Fondo
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-3 lg:p-4 space-y-3">
                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {[
                        { label: "Total de Fondos", value: String(funds.length), color: "text-blue-600" },
                        { label: "Balance Total", value: `$${totalBalance.toLocaleString()}`, color: "text-emerald-600" },
                        { label: "Fondos Públicos", value: String(publicCount), color: "text-violet-600" },
                    ].map((s) => (
                        <div key={s.label} className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 shadow-sm">
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-2">{s.label}</p>
                            <p className={clsx("text-lg font-bold tracking-tight", s.color)}>{s.value}</p>
                        </div>
                    ))}
                </div>

                {/* Grid */}
                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 shadow-sm animate-pulse h-36" />
                        ))}
                    </div>
                ) : funds.length === 0 ? (
                    <div className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-4 text-center shadow-sm">
                        <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center mx-auto mb-4">
                            <Wallet className="text-blue-600" size={28} />
                        </div>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Sin fondos registrados</p>
                        <p className="text-xs text-slate-300 mt-1">Crea el primer fondo ministerial</p>
                        <button onClick={openCreate}
                            className="mt-5 px-3 py-2.5 bg-blue-600 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 transition-all">
                            Crear Fondo
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {funds.map((f) => (
                            <motion.div key={f.id} layout
                                className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 shadow-sm group hover:shadow-md hover:border-blue-200 dark:hover:border-blue-500/20 transition-all">
                                <div className="flex items-start justify-between gap-3 mb-3">
                                    <div className="size-10 rounded-md bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-600 flex-shrink-0">
                                        <Wallet size={18} />
                                    </div>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={() => openEdit(f)}
                                            className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-blue-600 hover:text-white transition-all">
                                            <PencilLine size={13} />
                                        </button>
                                        <button onClick={() => setDeleteTarget(f)}
                                            className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-rose-600 hover:text-white transition-all">
                                            <Trash2 size={13} />
                                        </button>
                                    </div>
                                </div>

                                <h3 className="font-black text-slate-900 dark:text-white text-sm leading-tight mb-1">{f.name}</h3>
                                {f.description && (
                                    <p className="text-[11px] text-slate-400 line-clamp-2 mb-3">{f.description}</p>
                                )}

                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-[9px] font-semibold uppercase text-slate-400">Balance</p>
                                        <p className="text-lg font-bold text-emerald-600">${f.current_balance.toLocaleString()}</p>
                                    </div>
                                    <span className={clsx(
                                        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[9px] font-semibold uppercase tracking-wide",
                                        f.is_public
                                            ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200/50"
                                            : "bg-slate-50 dark:bg-white/5 text-slate-500 border-slate-200 dark:border-white/10"
                                    )}>
                                        {f.is_public ? <Eye size={10} /> : <EyeOff size={10} />}
                                        {f.is_public ? "Público" : "Interno"}
                                    </span>
                                </div>

                                <ProgressBar value={f.current_balance} max={f.target_amount} />
                            </motion.div>
                        ))}
                    </div>
                )}
            </main>

            {/* Create / Edit Drawer */}
            <AnimatePresence>
                {drawerMode && (
                    <>
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-0 z-[90] bg-black/30 backdrop-blur-sm"
                            onClick={() => setDrawerMode(null)} />
                        <motion.aside
                            initial={{ x: "100%", opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                            exit={{ x: "100%", opacity: 0 }}
                            transition={{ type: "spring", damping: 26, stiffness: 260 }}
                            className="fixed top-0 right-0 h-screen z-[100] w-full max-w-md bg-white dark:bg-[#15171c] shadow-2xl rounded-l-[2.5rem] overflow-hidden flex flex-col">
                            <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-white/5 flex-shrink-0">
                                <div>
                                    <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">
                                        {drawerMode === "create" ? "Nuevo Fondo" : "Editar Fondo"}
                                    </p>
                                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-1">
                                        {drawerMode === "create" ? "Crear Fondo Ministerial" : selected?.name}
                                    </h2>
                                </div>
                                <button onClick={() => setDrawerMode(null)}
                                    className="size-10 rounded-md bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 transition-all">
                                    <X size={18} />
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-5">
                                <div>
                                    <label className={LABEL}>Nombre del Fondo *</label>
                                    <input value={fName} onChange={(e) => setFName(e.target.value)}
                                        placeholder="Ej: Fondo de Misiones" className={INPUT} />
                                </div>
                                <div>
                                    <label className={LABEL}>Descripción</label>
                                    <textarea value={fDesc} onChange={(e) => setFDesc(e.target.value)}
                                        rows={3} placeholder="Propósito del fondo..."
                                        className={INPUT + " resize-none"} />
                                </div>
                                <div>
                                    <label className={LABEL}>Meta Financiera (opcional)</label>
                                    <input type="number" value={fTarget} onChange={(e) => setFTarget(e.target.value)}
                                        placeholder="0.00" className={INPUT} />
                                </div>
                                <div className="flex items-center gap-3 p-4 bg-slate-50 dark:bg-white/5 rounded-md">
                                    <button onClick={() => setFPublic(!fPublic)}
                                        className={clsx("size-10 rounded-md flex items-center justify-center transition-all flex-shrink-0",
                                            fPublic ? "bg-emerald-500 text-white" : "bg-slate-200 dark:bg-white/10 text-slate-400")}>
                                        {fPublic ? <Eye size={16} /> : <EyeOff size={16} />}
                                    </button>
                                    <div>
                                        <p className="text-xs font-semibold text-slate-800 dark:text-white">
                                            {fPublic ? "Visible al público" : "Solo uso interno"}
                                        </p>
                                        <p className="text-[10px] text-slate-400">
                                            {fPublic ? "Aparece en el portal público de la iglesia" : "Solo visible para el equipo admin"}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="p-3 border-t border-slate-100 dark:border-white/5 flex gap-3 flex-shrink-0">
                                <button onClick={() => setDrawerMode(null)}
                                    className="flex-1 py-3 rounded-md border border-slate-200 dark:border-white/10 text-[10px] font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleSave} disabled={saving}
                                    className="flex-1 py-3 rounded-md bg-blue-600 text-white text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 disabled:opacity-50 transition-all flex items-center justify-center gap-2">
                                    <Save size={14} /> {saving ? "Guardando..." : "Guardar"}
                                </button>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            {/* Delete Confirm Modal */}
            <AnimatePresence>
                {deleteTarget && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[110] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
                        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-white dark:bg-[#15171c] rounded-lg p-4 max-w-sm w-full shadow-2xl border border-slate-200 dark:border-white/10">
                            <div className="size-7 rounded-lg bg-rose-50 dark:bg-rose-500/10 flex items-center justify-center text-rose-600 mb-5">
                                <Trash2 size={24} />
                            </div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">¿Eliminar fondo?</h3>
                            <p className="text-sm text-slate-500 mb-3">
                                Se eliminará <span className="font-bold">{deleteTarget.name}</span>. Esta acción no se puede deshacer.
                            </p>
                            <div className="flex gap-3">
                                <button onClick={() => setDeleteTarget(null)}
                                    className="flex-1 py-3 rounded-md border border-slate-200 dark:border-white/10 text-[10px] font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50 transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleDelete} disabled={deleting}
                                    className="flex-1 py-3 rounded-md bg-rose-600 text-white text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-rose-500/20 hover:bg-rose-700 disabled:opacity-50 transition-all">
                                    {deleting ? "Eliminando..." : "Sí, eliminar"}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

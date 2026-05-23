"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import CrmShell from "@/components/crm/CrmShell";
import {
    User, LayoutDashboard, Heart, Star, PencilLine, Trash2, X, Save,
} from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

const INPUT = "w-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl py-2.5 px-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all";
const LABEL = "block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1.5";

type Volunteer = {
    id: number;
    name: string;
    role: string;
    team: string;
    status: string;
    joined_date: string | null;
    total_hours: number;
    skills: string[];
};

function Badge({ label, tone = "blue" }: { label: string; tone?: string }) {
    const styles: Record<string, string> = {
        blue: "bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-200/50",
        emerald: "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200/50",
        violet: "bg-violet-50 dark:bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-200/50",
    };
    return (
        <span className={clsx("inline-flex items-center px-3 py-1 rounded-xl border text-[9px] font-black uppercase tracking-widest", styles[tone] ?? styles.blue)}>
            {label}
        </span>
    );
}

export default function VolunteerDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;
    const { token } = useAuth();

    const [volunteer, setVolunteer] = useState<Volunteer | null>(null);
    const [loading, setLoading] = useState(true);
    const [editOpen, setEditOpen] = useState(false);
    const [deleteConfirm, setDeleteConfirm] = useState(false);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);

    // Edit form
    const [fRole, setFRole] = useState("");

    const loadVolunteer = async () => {
        if (!token || !id) return;
        try {
            setLoading(true);
            const data = await apiFetch<Volunteer>(`/crm/volunteers/${id}`, { token });
            setVolunteer(data);
        } catch {
            toast.error("Error al cargar perfil de servidor");
        } finally {
            setLoading(false);
        }
    };

    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => { loadVolunteer(); }, [id, token]);

    const openEdit = () => {
        if (!volunteer) return;
        setFRole(volunteer.role || "");
        setEditOpen(true);
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await apiFetch(`/crm/volunteers/${id}`, {
                method: "PATCH",
                token,
                body: JSON.stringify({ church_role: fRole }),
            });
            toast.success("Servidor actualizado");
            setEditOpen(false);
            loadVolunteer();
        } catch {
            toast.error("Error al actualizar");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        setDeleting(true);
        try {
            await apiFetch(`/crm/volunteers/${id}`, { method: "DELETE", token });
            toast.success("Servidor eliminado");
            router.push("/crm/volunteers");
        } catch {
            toast.error("Error al eliminar");
            setDeleting(false);
            setDeleteConfirm(false);
        }
    };

    if (loading) {
        return (
            <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">
                Consultando registro de servidores...
            </div>
        );
    }

    if (!volunteer) {
        return <div className="p-20 text-center font-black uppercase tracking-widest text-slate-400">No se pudo cargar el servidor.</div>;
    }

    const initials = volunteer.name?.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CRM", icon: LayoutDashboard, href: "/crm" },
                { label: "Voluntariado", icon: Heart, href: "/crm/volunteers" },
                { label: volunteer.name, icon: User },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-6 lg:p-10">
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                    className="max-w-4xl mx-auto space-y-6">

                    {/* Hero */}
                    <header className="bg-white dark:bg-[#15171c] rounded-3xl border border-slate-200 dark:border-white/5 p-6 lg:p-8 shadow-sm flex items-center gap-6">
                        <div className="size-20 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white flex items-center justify-center font-black text-2xl shadow-xl flex-shrink-0">
                            {initials}
                        </div>
                        <div className="flex-1 min-w-0">
                            <h1 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tight">{volunteer.name}</h1>
                            <div className="flex items-center gap-2 mt-2">
                                <Badge label={volunteer.role?.toUpperCase() || "SIN ROL"} tone="blue" />
                                <Badge label={(volunteer.status || "inactive").toUpperCase()} tone="emerald" />
                            </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                            <button onClick={openEdit}
                                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 transition-all">
                                <PencilLine size={13} /> Editar
                            </button>
                            <button onClick={() => setDeleteConfirm(true)}
                                className="size-10 rounded-xl bg-rose-50 dark:bg-rose-500/10 text-rose-600 flex items-center justify-center hover:bg-rose-100 transition-all border border-rose-200/50">
                                <Trash2 size={15} />
                            </button>
                        </div>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2 space-y-6">
                            <div className="bg-white dark:bg-[#15171c] rounded-2xl border border-slate-200 dark:border-white/5 p-6 shadow-sm">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-5">Información del Servidor</p>
                                <div className="grid grid-cols-2 gap-5">
                                    <div>
                                        <p className="text-[9px] font-black text-slate-400 uppercase mb-1">Equipo</p>
                                        <p className="text-sm font-bold text-slate-800 dark:text-white">{volunteer.team || "Sin equipo"}</p>
                                    </div>
                                    <div>
                                        <p className="text-[9px] font-black text-slate-400 uppercase mb-1">Fecha de Ingreso</p>
                                        <p className="text-sm font-bold text-slate-800 dark:text-white">
                                            {volunteer.joined_date ? new Date(volunteer.joined_date).toLocaleDateString("es-ES") : "Sin fecha"}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white dark:bg-[#15171c] rounded-2xl border border-slate-200 dark:border-white/5 p-6 shadow-sm">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4">Habilidades y Dones</p>
                                <div className="flex flex-wrap gap-2">
                                    {volunteer.skills.length > 0
                                        ? volunteer.skills.map((s) => <Badge key={s} label={s} tone="violet" />)
                                        : <p className="text-sm text-slate-400">Sin habilidades registradas.</p>}
                                </div>
                            </div>
                        </div>

                        <aside className="space-y-6">
                            <div className="bg-white dark:bg-[#15171c] rounded-2xl border border-slate-200 dark:border-white/5 p-6 shadow-sm">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-5">Métricas de Servicio</p>
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-medium text-slate-500">Horas Totales</span>
                                        <span className="text-sm font-black text-slate-900 dark:text-white">{volunteer.total_hours}h</span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-medium text-slate-500">Fidelidad</span>
                                        <div className="flex items-center gap-0.5 text-amber-400">
                                            {[...Array(5)].map((_, i) => <Star key={i} size={12} fill="currentColor" />)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </aside>
                    </div>
                </motion.div>
            </main>

            {/* Edit Drawer */}
            <AnimatePresence>
                {editOpen && (
                    <>
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-0 z-[90] bg-black/30 backdrop-blur-sm"
                            onClick={() => setEditOpen(false)} />
                        <motion.aside
                            initial={{ x: "100%", opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                            exit={{ x: "100%", opacity: 0 }}
                            transition={{ type: "spring", damping: 26, stiffness: 260 }}
                            className="fixed top-0 right-0 h-screen z-[100] w-full max-w-md bg-white dark:bg-[#15171c] shadow-2xl rounded-l-[2.5rem] overflow-hidden flex flex-col">
                            <div className="flex items-center justify-between p-8 border-b border-slate-100 dark:border-white/5">
                                <div>
                                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Editar Servidor</p>
                                    <h2 className="text-xl font-black text-slate-900 dark:text-white mt-1">{volunteer.name}</h2>
                                </div>
                                <button onClick={() => setEditOpen(false)}
                                    className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 transition-all">
                                    <X size={18} />
                                </button>
                            </div>
                            <div className="flex-1 overflow-y-auto p-8 space-y-5">
                                <div>
                                    <label className={LABEL}>Rol / Cargo</label>
                                    <input value={fRole} onChange={(e) => setFRole(e.target.value)}
                                        placeholder="Ej: Ujier, Música, Tecnología..."
                                        className={INPUT} />
                                </div>
                            </div>
                            <div className="p-6 border-t border-slate-100 dark:border-white/5 flex gap-3">
                                <button onClick={() => setEditOpen(false)}
                                    className="flex-1 py-3 rounded-xl border border-slate-200 dark:border-white/10 text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-50 transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleSave} disabled={saving}
                                    className="flex-1 py-3 rounded-xl bg-blue-600 text-white text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 disabled:opacity-50 transition-all flex items-center justify-center gap-2">
                                    <Save size={14} /> {saving ? "Guardando..." : "Guardar"}
                                </button>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            {/* Delete Confirm Modal */}
            <AnimatePresence>
                {deleteConfirm && (
                    <>
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-0 z-[110] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
                            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
                                className="bg-white dark:bg-[#15171c] rounded-3xl p-8 max-w-sm w-full shadow-2xl border border-slate-200 dark:border-white/10">
                                <div className="size-14 rounded-2xl bg-rose-50 dark:bg-rose-500/10 flex items-center justify-center text-rose-600 mb-5">
                                    <Trash2 size={24} />
                                </div>
                                <h3 className="text-lg font-black text-slate-900 dark:text-white mb-2">¿Eliminar servidor?</h3>
                                <p className="text-sm text-slate-500 mb-6">
                                    Esta acción eliminará a <span className="font-bold">{volunteer.name}</span> del sistema. No se puede deshacer.
                                </p>
                                <div className="flex gap-3">
                                    <button onClick={() => setDeleteConfirm(false)}
                                        className="flex-1 py-3 rounded-xl border border-slate-200 dark:border-white/10 text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-50 transition-all">
                                        Cancelar
                                    </button>
                                    <button onClick={handleDelete} disabled={deleting}
                                        className="flex-1 py-3 rounded-xl bg-rose-600 text-white text-[10px] font-black uppercase tracking-widest shadow-lg shadow-rose-500/20 hover:bg-rose-700 disabled:opacity-50 transition-all">
                                        {deleting ? "Eliminando..." : "Sí, eliminar"}
                                    </button>
                                </div>
                            </motion.div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </CrmShell>
    );
}

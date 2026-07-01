"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useCrmAccess } from "@/hooks/useCrmAccess";
import { apiFetch } from "@/lib/http";
import CrmShell from "@/components/crm/CrmShell";
import {
    User, LayoutDashboard, Heart, Star, PencilLine, Trash2, X, Save,
} from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import ConfirmActionDrawer, { type ConfirmActionState } from "@/components/ConfirmActionDrawer";

const INPUT = "w-full bg-[hsl(var(--bg-muted))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md py-2.5 px-4 text-sm text-[hsl(var(--text-primary))] outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all";
const LABEL = "block text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1.5";

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
        blue: "bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))] dark:text-blue-300 border-blue-200/50",
        emerald: "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-200/50",
        sky: "bg-sky-50 dark:bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-200/50",
    };
    return (
        <span className={clsx("inline-flex items-center px-3 py-1 rounded-md border text-[9px] font-bold uppercase tracking-wide", styles[tone] ?? styles.blue)}>
            {label}
        </span>
    );
}

export default function VolunteerDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;
    const { token } = useAuth();
    const { canEditCrm } = useCrmAccess();

    const [volunteer, setVolunteer] = useState<Volunteer | null>(null);
    const [loading, setLoading] = useState(true);
    const [editOpen, setEditOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [confirmDelete, setConfirmDelete] = useState<ConfirmActionState>(null);

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
                body: { church_role: fRole },
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
        try {
            await apiFetch(`/crm/volunteers/${id}`, { method: "DELETE", token });
            toast.success("Servidor eliminado");
            router.push("/plataforma/crm/volunteers");
        } catch {
            toast.error("Error al eliminar");
            throw new Error("Error al eliminar");
        }
    };

    if (loading) {
        return (
            <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-slate-400">
                Consultando registro de servidores...
            </div>
        );
    }

    if (!volunteer) {
        return <div className="p-4 text-center font-bold uppercase tracking-wide text-slate-400">No se pudo cargar el servidor.</div>;
    }

    const initials = volunteer.name?.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CRM", icon: LayoutDashboard, href: "/plataforma/crm" },
                { label: "Voluntariado", icon: Heart, href: "/plataforma/crm/volunteers" },
                { label: volunteer.name, icon: User },
            ]}
        >
            <main className="flex-1 overflow-y-auto p-3 lg:p-4">
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
 className="w-full space-y-3">

                    {/* Hero */}
                    <header className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 lg:p-4 shadow-sm flex items-center gap-3">
                        <div className="size-10 rounded-lg bg-gradient-to-br from-blue-500 to-sky-600 text-white flex items-center justify-center font-bold text-lg shadow-xl flex-shrink-0">
                            {initials}
                        </div>
                        <div className="flex-1 min-w-0">
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-tight">{volunteer.name}</h1>
                            <div className="flex items-center gap-2 mt-2">
                                <Badge label={volunteer.role?.toUpperCase() || "SIN ROL"} tone="blue" />
                                <Badge label={(volunteer.status || "inactive").toUpperCase()} tone="emerald" />
                            </div>
                        </div>
                        {canEditCrm && (
                            <div className="flex items-center gap-2 flex-shrink-0">
                                <button onClick={openEdit}
                                    className="flex items-center gap-2 px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] transition-all">
                                    <PencilLine size={13} /> Editar
                                </button>
                                <button
                                    onClick={() => setConfirmDelete({
                                        title: "¿Eliminar servidor?",
                                        description: `Esta acción eliminará a ${volunteer.name} del sistema. No se puede deshacer.`,
                                        confirmLabel: "Sí, eliminar",
                                        destructive: true,
                                        onConfirm: handleDelete,
                                    })}
                                    className="size-10 rounded-md bg-rose-50 dark:bg-rose-500/10 text-rose-600 flex items-center justify-center hover:bg-rose-100 transition-all border border-rose-200/50">
                                    <Trash2 size={15} />
                                </button>
                            </div>
                        )}
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                        <div className="lg:col-span-2 space-y-3">
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3 shadow-sm">
                                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-5">Información del Servidor</p>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Equipo</p>
                                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{volunteer.team || "Sin equipo"}</p>
                                    </div>
                                    <div>
                                        <p className="text-[9px] font-bold text-[hsl(var(--text-secondary))] uppercase mb-1">Fecha de Ingreso</p>
                                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
                                            {volunteer.joined_date ? new Date(volunteer.joined_date).toLocaleDateString("es-ES") : "Sin fecha"}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3 shadow-sm">
                                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-4">Habilidades y Dones</p>
                                <div className="flex flex-wrap gap-2">
                                    {volunteer.skills.length > 0
                                        ? volunteer.skills.map((s) => <Badge key={s} label={s} tone="blue" />)
                                        : <p className="text-sm text-[hsl(var(--text-secondary))]">Sin habilidades registradas.</p>}
                                </div>
                            </div>
                        </div>

                        <aside className="space-y-3">
                            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#15171c] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-3 shadow-sm">
                                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-5">Métricas de Servicio</p>
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-medium text-[hsl(var(--text-secondary))]">Horas Totales</span>
                                        <span className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{volunteer.total_hours}h</span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-medium text-[hsl(var(--text-secondary))]">Fidelidad</span>
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
                            className="fixed inset-x-0 bottom-0 top-10 z-[90] bg-black/30 backdrop-blur-sm"
                            onClick={() => setEditOpen(false)} />
                        <motion.aside
                            initial={{ x: "100%", opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                            exit={{ x: "100%", opacity: 0 }}
                            transition={{ type: "spring", damping: 26, stiffness: 260 }}
                            className="fixed top-10 right-0 h-[calc(100vh-2.5rem)] z-[100] w-full max-w-md bg-[hsl(var(--surface-1))] dark:bg-[#15171c] shadow-2xl rounded-l-lg overflow-hidden flex flex-col">
                            <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-white/5">
                                <div>
                                    <p className="text-[9px] font-bold uppercase tracking-wide text-slate-400">Editar Servidor</p>
                                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mt-1">{volunteer.name}</h2>
                                </div>
                                <button onClick={() => setEditOpen(false)}
                                    className="size-10 rounded-md bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 transition-all">
                                    <X size={18} />
                                </button>
                            </div>
                            <div className="flex-1 overflow-y-auto p-4 space-y-5">
                                <div>
                                    <label className={LABEL}>Rol / Cargo</label>
                                    <input value={fRole} onChange={(e) => setFRole(e.target.value)}
                                        placeholder="Ej: Ujier, Música, Tecnología..."
                                        className={INPUT} />
                                </div>
                            </div>
                            <div className="p-3 border-t border-slate-100 dark:border-white/5 flex gap-3">
                                <button onClick={() => setEditOpen(false)}
                                    className="flex-1 py-3 rounded-md border border-slate-200 dark:border-white/10 text-[10px] font-bold uppercase tracking-wide text-slate-500 hover:bg-slate-50 transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleSave} disabled={saving}
                                    className="flex-1 py-3 rounded-md bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] disabled:opacity-50 transition-all flex items-center justify-center gap-2">
                                    <Save size={14} /> {saving ? "Guardando..." : "Guardar"}
                                </button>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            <ConfirmActionDrawer action={confirmDelete} onClose={() => setConfirmDelete(null)} />
        </CrmShell>
    );
}

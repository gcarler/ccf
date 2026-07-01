"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Users, Shield, Mail, Phone, ArrowRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import Skeleton from "@/components/ui/Skeleton";
import { motion } from "framer-motion";

export default function AdminPersonasPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [personas, setPersonas] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");

    useEffect(() => {
        if (!token) return;
        const load = async () => {
            setLoading(true);
            try {
                const data = await apiFetch<any[]>("/admin/personas", { token, cache: "no-store" });
                setPersonas(Array.isArray(data) ? data : []);
            } catch {
                addToast("Error al cargar personas", "error");
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [token, addToast]);

    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase();
        if (!q) return personas;
        return personas.filter((p) =>
            [p.first_name, p.last_name, p.email, p.phone, p.church_role]
                .filter(Boolean)
                .some((value) => String(value).toLowerCase().includes(q))
        );
    }, [personas, search]);

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Administración", icon: Shield, href: "/plataforma/admin" },
                    { label: "Personas", icon: Users, href: "/plataforma/admin/personas" },
                ]}
                onSearch={setSearch}
            />

            <main className="flex-1 overflow-y-auto p-3 lg:p-4">
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
                    <header className="space-y-1">
                        <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Personas</h1>
                        <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                            Base de datos central de la congregación.
                        </p>
                    </header>

                    <section className="bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 shadow-xl shadow-black/10/20 dark:shadow-none overflow-hidden">
                        {loading ? (
                            <div className="p-4 space-y-3">
                                {[1, 2, 3, 4, 5].map((i) => (
                                    <Skeleton key={i} className="h-12 w-full rounded-md" />
                                ))}
                            </div>
                        ) : filtered.length === 0 ? (
                            <div className="p-6 text-sm text-[hsl(var(--text-secondary))]">
                                No hay personas para mostrar.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="bg-[hsl(var(--surface-1))]/60 dark:bg-black/20 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                            <th className="px-4 py-3">Nombre</th>
                                            <th className="px-4 py-3">Correo</th>
                                            <th className="px-4 py-3">Teléfono</th>
                                            <th className="px-4 py-3">Rol Iglesia</th>
                                            <th className="px-4 py-3 text-right">Acciones</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                                        {filtered.map((persona) => (
                                            <tr key={persona.id} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">
                                                <td className="px-4 py-3">
                                                    <div className="flex items-center gap-3">
                                                        <div className="size-9 rounded-md bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))] flex items-center justify-center font-bold text-xs">
                                                            {(persona.first_name || "P").slice(0, 1)}
                                                            {(persona.last_name || "").slice(0, 1)}
                                                        </div>
                                                        <div>
                                                            <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">
                                                                {persona.first_name} {persona.last_name}
                                                            </p>
                                                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">ID: {String(persona.id)}</p>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                                    <div className="flex items-center gap-2">
                                                        <Mail size={13} className="text-[hsl(var(--text-secondary))]" />
                                                        {persona.email || "Sin correo"}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                                    <div className="flex items-center gap-2">
                                                        <Phone size={13} className="text-[hsl(var(--text-secondary))]" />
                                                        {persona.phone || "Sin teléfono"}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className="inline-flex items-center rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                        {persona.church_role || "Sin rol"}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-right">
                                                    <button
                                                        onClick={() => router.push(`/plataforma/admin/personas/${persona.id}`)}
                                                        className="inline-flex items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white shadow-sm hover:opacity-95"
                                                    >
                                                        Ver expediente <ArrowRight size={13} />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </section>
                </motion.div>
            </main>
        </div>
    );
}

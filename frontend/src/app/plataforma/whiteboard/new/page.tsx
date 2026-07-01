"use client";

import React, { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import CrmShell from "@/components/crm/CrmShell";
import { LayoutDashboard, PenTool, Sparkles } from "lucide-react";
import { upsertWhiteboard } from "@/lib/whiteboards";

export default function NewWhiteboardPage() {
    const router = useRouter();
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const previewTitle = useMemo(() => title.trim() || "Nueva pizarra CCF", [title]);

    const handleCreate = () => {
        const id = `local-${Date.now()}`;
        if (typeof window !== "undefined") {
            upsertWhiteboard(window.localStorage, {
                id,
                title: previewTitle,
                description,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
            });
        }
        router.push(`/plataforma/whiteboard/${id}`);
    };

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CCF Tools", icon: LayoutDashboard, href: "/plataforma/whiteboard" },
                { label: "Nueva Pizarra", icon: PenTool },
            ]}
        >
            <div className="mx-auto flex h-full max-w-5xl items-center px-4 py-1.5">
                <section className="grid w-full grid-cols-1 overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] shadow-2xl dark:border-white/10 dark:bg-white/5 lg:grid-cols-[1fr_0.9fr]">
                    <div className="space-y-3 p-4 lg:p-4">
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Lienzo colaborativo</p>
                            <h1 className="mt-2 text-lg font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white">Crear pizarra</h1>
                            <p className="mt-3 max-w-xl text-sm font-medium leading-6 text-[hsl(var(--text-secondary))]">
                                Activa un espacio de trabajo para mapas, diagramas, lluvia de ideas y planeacion asistida.
                            </p>
                        </div>

                        <label className="block space-y-2">
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Nombre</span>
                            <input
                                value={title}
                                onChange={(event) => setTitle(event.target.value)}
                                placeholder="Ej: Planeacion Faro Q2"
                                className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-3 text-sm font-bold outline-none focus:border-blue-400 dark:border-white/10 dark:bg-black/20"
                            />
                        </label>

                        <label className="block space-y-2">
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Objetivo</span>
                            <textarea
                                value={description}
                                onChange={(event) => setDescription(event.target.value)}
                                placeholder="Describe que se va a construir en este lienzo..."
                                className="min-h-[140px] w-full resize-none rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-3 text-sm font-semibold outline-none focus:border-blue-400 dark:border-white/10 dark:bg-black/20"
                            />
                        </label>

                        <div className="flex items-center gap-3">
                            <button
                                onClick={handleCreate}
                                className="rounded-lg bg-[hsl(var(--primary))] px-3 py-3 text-[11px] font-semibold uppercase tracking-wide text-white shadow-xl shadow-blue-500/20"
                            >
                                Crear pizarra
                            </button>
                            <button
                                onClick={() => router.push("/plataforma/whiteboard")}
                                className="rounded-lg border border-[hsl(var(--border))] px-3 py-3 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:border-white/10"
                            >
                                Cancelar
                            </button>
                        </div>
                    </div>

                    <div className="relative min-h-[420px] overflow-hidden bg-[hsl(var(--bg-muted))] p-4 text-white">
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(59,130,246,0.35),transparent_35%),radial-gradient(circle_at_80%_70%,rgba(14,165,233,0.2),transparent_30%)]" />
                        <div className="relative flex h-full flex-col justify-between rounded-lg border border-white/10 bg-white/10 p-3 backdrop-blur">
                            <Sparkles className="text-blue-300" size={36} />
                            <div>
                                <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-200">Preview</p>
                                <h2 className="mt-2 text-xl font-bold">{previewTitle}</h2>
                                <p className="mt-3 text-sm font-medium text-[hsl(var(--text-secondary))]">{description || "Sin objetivo definido todavia."}</p>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </CrmShell>
    );
}

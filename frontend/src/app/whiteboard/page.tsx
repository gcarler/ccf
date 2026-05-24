"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import CrmShell from "@/components/crm/CrmShell";
import AdminHero from "@/components/admin/AdminHero";
import { LayoutDashboard, Sparkles, Plus, Search, Clock, Trash2 } from "lucide-react";
import {
    readWhiteboards,
    whiteboardCanvasKey,
    WhiteboardRecord,
    writeWhiteboards,
} from "@/lib/whiteboards";

export default function WhiteboardPage() {
    const router = useRouter();
    const [query, setQuery] = useState("");
    const [boards, setBoards] = useState<WhiteboardRecord[]>([]);

    useEffect(() => {
        if (typeof window === "undefined") return;
        setBoards(readWhiteboards(window.localStorage));
    }, []);

    const filtered = useMemo(() => {
        const normalized = query.trim().toLowerCase();
        if (!normalized) return boards;
        return boards.filter((board) =>
            board.title.toLowerCase().includes(normalized) ||
            (board.description || "").toLowerCase().includes(normalized)
        );
    }, [boards, query]);

    const deleteBoard = (id: string) => {
        if (typeof window === "undefined") return;
        const next = boards.filter((board) => board.id !== id);
        writeWhiteboards(window.localStorage, next);
        window.localStorage.removeItem(whiteboardCanvasKey(id));
        setBoards(next);
    };

    return (
        <CrmShell
            breadcrumbs={[
                { label: "CCF Tools", icon: LayoutDashboard },
                { label: "Lienzo Colaborativo", icon: Sparkles },
            ]}
        >
            <div className="space-y-3 px-4 py-8">
                <AdminHero
                    eyebrow="PRODUCTIVIDAD"
                    title="Pizarras Infinitas"
                    description="Espacios de trabajo visuales con canvas real, capas y guardado local persistente."
                    tags={["Canvas", "Local-first"]}
                    watchers={["Equipo Estrategico", "Diseno"]}
                    primaryAction={{ label: "Nueva Pizarra", icon: Plus, onClick: () => router.push("/whiteboard/new") }}
                />

                <div className="max-w-7xl mx-auto space-y-3">
                    <div className="relative max-w-md">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder="Buscar en tus lienzos..."
                            className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg py-3 pl-12 pr-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                        />
                    </div>

                    {filtered.length > 0 ? (
                        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                            {filtered.map((board) => (
                                <article
                                    key={board.id}
                                    className="group rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition-all hover:border-blue-300 hover:shadow-xl dark:border-white/10 dark:bg-white/5"
                                >
                                    <button
                                        onClick={() => router.push(`/whiteboard/${board.id}`)}
                                        className="block w-full text-left"
                                    >
                                        <div className="mb-5 flex h-36 items-center justify-center rounded-lg border border-slate-100 bg-slate-50 bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] [background-size:20px_20px] dark:border-white/10 dark:bg-black/20 dark:bg-[radial-gradient(#334155_1px,transparent_1px)]">
                                            <Sparkles className="text-blue-500 opacity-70" size={34} />
                                        </div>
                                        <h3 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">{board.title}</h3>
                                        <p className="mt-1 line-clamp-2 text-sm font-medium text-slate-500">
                                            {board.description || "Sin objetivo documentado."}
                                        </p>
                                        <div className="mt-4 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                            <Clock size={12} />
                                            {formatBoardDate(board.updated_at || board.created_at)}
                                        </div>
                                    </button>
                                    <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 dark:border-white/10">
                                        <button
                                            onClick={() => router.push(`/whiteboard/${board.id}`)}
                                            className="rounded-md bg-blue-600 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-white shadow-lg shadow-blue-500/20"
                                        >
                                            Abrir
                                        </button>
                                        <button
                                            onClick={() => deleteBoard(board.id)}
                                            className="rounded-md p-2 text-slate-300 transition-all hover:bg-rose-50 hover:text-rose-500 dark:hover:bg-rose-500/10"
                                            title="Eliminar pizarra local"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </article>
                            ))}
                        </div>
                    ) : (
                        <div className="border-2 border-dashed border-slate-200 dark:border-white/10 rounded-lg p-4 text-center bg-white/60 dark:bg-white/[0.03]">
                            <Sparkles size={40} className="mx-auto text-slate-300 mb-3" />
                            <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                                {boards.length === 0 ? "No hay pizarras registradas todavia" : "Sin resultados"}
                            </p>
                            <p className="text-xs text-slate-400 mt-2">
                                {boards.length === 0 ? "Crea una nueva pizarra para empezar a colaborar." : "Ajusta la busqueda para encontrar otro lienzo."}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </CrmShell>
    );
}

function formatBoardDate(value: string) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Sin fecha";
    return date.toLocaleDateString("es-CO", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

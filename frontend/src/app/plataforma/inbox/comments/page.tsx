"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import {
    AtSign,
    Calendar,
    FolderKanban,
    MessageSquare,
    Paperclip,
    RefreshCw,
    Search,
    User,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import { useCommentCenter, CommentCenterTab, CommentModuleType } from "@/hooks/useCommentCenter";

const TAB_LABEL: Record<CommentCenterTab, string> = {
    created: "Mis comentarios",
    mentions: "Menciones",
};

const TYPE_LABEL: Record<"all" | CommentModuleType, string> = {
    all: "Todos",
    project: "Proyectos",
    agenda: "Agenda",
};

function formatCommentTime(iso: string) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "Sin fecha";
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.round(diffMs / 60000);
    if (diffMin < 1) return "Ahora";
    if (diffMin < 60) return `Hace ${diffMin} min`;
    const diffH = Math.round(diffMin / 60);
    if (diffH < 24) return `Hace ${diffH} h`;
    if (diffH < 48) return "Ayer";
    return new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "short" }).format(date);
}

function ContextLink({
    module_type,
    project_id,
    context_title,
}: {
    module_type: CommentModuleType;
    project_id: string;
    context_title: string | null;
}) {
    const href = module_type === "project" ? `/plataforma/projects/${project_id}` : `/plataforma/agenda/${project_id}`;
    const Icon = module_type === "project" ? FolderKanban : Calendar;
    const label = context_title || (module_type === "project" ? "Proyecto" : "Evento");
    return (
        <Link
            href={href}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-[hsl(var(--primary))] hover:underline truncate max-w-full"
        >
            <Icon size={12} />
            {label}
        </Link>
    );
}

export default function CommentCenterPage() {
    const [tab, setTab] = useState<CommentCenterTab>("created");
    const [typeFilter, setTypeFilter] = useState<"all" | CommentModuleType>("all");
    const [search, setSearch] = useState("");
    const { items, loading, error, refresh } = useCommentCenter({ tab, typeFilter });

    const filtered = useMemo(() => {
        if (!search.trim()) return items;
        const term = search.toLowerCase();
        return items.filter(
            (item) =>
                item.content.toLowerCase().includes(term) ||
                (item.context_title && item.context_title.toLowerCase().includes(term)) ||
                item.author_name.toLowerCase().includes(term)
        );
    }, [items, search]);

    return (
        <div className="h-full flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[#1E1F21] overflow-hidden font-display">
            <div className="h-14 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-4 gap-3 shrink-0 bg-[hsl(var(--surface-1))]/50 dark:bg-[#1E1F21]">
                <h1 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] flex items-center gap-2">
                    <MessageSquare size={14} />
                    Centro de comentarios
                </h1>
                <div className="flex-1" />

                <div className="relative">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                    <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Buscar..."
                        className="pl-9 pr-3 py-1.5 text-xs bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] w-56 transition-all"
                    />
                </div>

                <button
                    onClick={() => void refresh()}
                    className="flex items-center gap-1.5 px-3 py-1.5 font-semibold text-xs text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--primary))] transition-colors"
                >
                    <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
                    Actualizar
                </button>
            </div>

            <div className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/5 flex flex-col sm:flex-row sm:items-center gap-3 shrink-0">
                <div className="flex rounded-lg overflow-hidden border border-[hsl(var(--border))] dark:border-white/10">
                    {(['created', 'mentions'] as const).map((t) => (
                        <button
                            key={t}
                            onClick={() => setTab(t)}
                            className={clsx(
                                'px-4 py-2 text-xs font-semibold transition-colors flex items-center gap-2',
                                tab === t
                                    ? 'bg-[hsl(var(--primary))] text-white'
                                    : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]'
                            )}
                        >
                            {t === 'mentions' && <AtSign size={12} />}
                            {TAB_LABEL[t]}
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-2">
                    {(['all', 'project', 'agenda'] as const).map((f) => (
                        <button
                            key={f}
                            onClick={() => setTypeFilter(f)}
                            className={clsx(
                                'px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors',
                                typeFilter === f
                                    ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]'
                                    : 'bg-transparent text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] dark:border-white/10 hover:border-[hsl(var(--primary))]'
                            )}
                        >
                            {TYPE_LABEL[f]}
                        </button>
                    ))}
                </div>

                <span className="ml-auto text-xs font-semibold text-[hsl(var(--text-secondary))]">
                    {filtered.length} resultado{filtered.length !== 1 ? "s" : ""}
                </span>
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-thin">
                <AnimatePresence initial={false}>
                    {loading ? (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex h-full items-center justify-center text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]"
                        >
                            Cargando comentarios…
                        </motion.div>
                    ) : error ? (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex flex-col items-center justify-center h-full gap-2 text-center px-4"
                        >
                            <p className="text-sm font-semibold text-[hsl(var(--danger))]">{error}</p>
                            <button
                                onClick={() => void refresh()}
                                className="text-xs text-[hsl(var(--primary))] font-semibold hover:underline"
                            >
                                Reintentar
                            </button>
                        </motion.div>
                    ) : filtered.length === 0 ? (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex flex-col items-center justify-center h-full gap-4 text-center px-4"
                        >
                            <div className="size-10 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                                <MessageSquare size={24} className="text-[hsl(var(--text-secondary))]" />
                            </div>
                            <p className="text-sm font-bold text-[hsl(var(--text-secondary))]">
                                {tab === "created" ? "Aún no has comentado" : "Aún no te han mencionado"}
                            </p>
                            <p className="text-xs text-[hsl(var(--text-secondary))]">
                                {tab === "created"
                                    ? "Tus comentarios en proyectos y agenda aparecerán aquí."
                                    : "Cuando alguien te mencione con @, verás el mensaje aquí."}
                            </p>
                        </motion.div>
                    ) : (
                        <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/[0.03]">
                            {filtered.map((item, index) => (
                                <motion.div
                                    key={item.id}
                                    initial={{ opacity: 0, x: -8 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, height: 0 }}
                                    transition={{ delay: index * 0.03 }}
                                    className="flex items-start gap-4 px-4 py-3 group hover:bg-[hsl(var(--surface-1))]/50 dark:hover:bg-white/[0.02] transition-colors"
                                >
                                    <div className="size-10 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center shrink-0">
                                        <User size={18} className="text-[hsl(var(--text-secondary))]" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap mb-1">
                                            <span className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
                                                {item.author_name || "Usuario"}
                                            </span>
                                            <span className="text-xs text-[hsl(var(--text-secondary))]">
                                                {tab === "created" ? "comentó en" : "te mencionó en"}
                                            </span>
                                            <ContextLink
                                                module_type={item.module_type}
                                                project_id={item.project_id}
                                                context_title={item.context_title}
                                            />
                                        </div>
                                        <p className="text-sm text-[hsl(var(--text-secondary))] leading-snug line-clamp-3 whitespace-pre-line">
                                            {item.content}
                                        </p>
                                        <div className="flex items-center gap-4 mt-2">
                                            <span className="text-2xs font-medium text-[hsl(var(--text-secondary))]">
                                                {formatCommentTime(item.created_at)}
                                            </span>
                                            {item.attachments.length > 0 && (
                                                <span className="inline-flex items-center gap-1 text-2xs font-medium text-[hsl(var(--primary))]">
                                                    <Paperclip size={10} />
                                                    {item.attachments.length} adjunto{item.attachments.length !== 1 ? "s" : ""}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

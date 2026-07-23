"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
    BookOpen,
    Bot,
    CheckCircle2,
    ChevronRight,
    Clock,
    MessageSquare,
    Plus,
    Search,
    ThumbsUp,
    User,
} from "lucide-react";
import clsx from "clsx";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";

const categories = ["Todos", "Teologia", "Liderazgo", "Academico", "Misiones", "Testimonios"];

export default function AcademyForumPage() {
    const { token, user } = useAuth();
    const [threads, setThreads] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewMode, setViewType] = useState<"grid" | "list">("list");
    const [activeCategory, setActiveCategory] = useState("Todos");
    const [search, setSearch] = useState("");
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [newThread, setNewThread] = useState({ title: "", category: "Teologia" });

    useEffect(() => {
        const ctrl = new AbortController();
        const fetchThreads = async () => {
            if (!token) return;
            setLoading(true);
            try {
                const data = await apiFetch<any[]>("/academy/forum/threads", { token, signal: ctrl.signal });
                setThreads((Array.isArray(data) ? data : []).map((thread) => normalizeThread(thread)));
            } catch (err) {
                console.error(err);
                toast.error('Error al cargar hilos del foro');
            } finally {
                setLoading(false);
            }
        };
        fetchThreads();
        return () => ctrl.abort();
    }, [token]);

    const visibleThreads = useMemo(() => {
        const term = search.trim().toLowerCase();
        return threads.filter((thread) => {
            const matchesCategory = activeCategory === "Todos" || thread.category === activeCategory;
            const matchesSearch = !term || thread.title.toLowerCase().includes(term);
            return matchesCategory && matchesSearch;
        });
    }, [activeCategory, search, threads]);

    const handleCreateThread = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!token || !newThread.title.trim()) return;
        setSaving(true);
        try {
            const created = await apiFetch<any>("/academy/forum/threads", {
                method: "POST",
                token,
                body: newThread,
            });
            setThreads((prev) => [normalizeThread(created, user?.username), ...prev]);
            setNewThread({ title: "", category: "Teologia" });
            setIsCreateOpen(false);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="flex h-full flex-col overflow-hidden bg-[hsl(var(--surface-1))]/50 font-display dark:bg-[hsl(var(--surface-1))]">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Academia", icon: BookOpen },
                    { label: "Foros de Discusion", icon: MessageSquare },
                ]}
                viewType={viewMode}
                setViewType={(value: any) => setViewType(value)}
                rightActions={
                    <button
                        onClick={() => setIsCreateOpen(true)}
                        className="flex items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-white shadow-xl shadow-blue-500/20 transition-all active:scale-95"
                    >
                        <Plus size={14} /> Iniciar Debate
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 scrollbar-thin lg:p-4">
                <div className="mx-auto grid max-w-7xl grid-cols-1 gap-3 lg:grid-cols-12">
                    <aside className="space-y-3 lg:col-span-3">
                        <section className="space-y-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 shadow-xl dark:border-white/10 dark:bg-white/5">
                            <h3 className="px-2 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Categorias</h3>
                            <div className="space-y-1">
                                {categories.map((category) => (
                                    <button
                                        key={category}
                                        onClick={() => setActiveCategory(category)}
                                        className={clsx(
                                            "flex w-full items-center justify-between rounded-lg p-4 text-[12px] font-bold transition-all",
                                            activeCategory === category
                                                ? "bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-600/10"
                                                : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
                                        )}
                                    >
                                        {category}
                                        {activeCategory === category && <div className="size-1.5 rounded-full bg-[hsl(var(--primary))] shadow-[0_0_8px_#2563eb]" />}
                                    </button>
                                ))}
                            </div>
                        </section>

                        <section className="relative overflow-hidden rounded-lg bg-[hsl(var(--primary))] p-4 text-white shadow-2xl">
                            <div className="absolute -right-10 -top-5 size-10 rounded-full bg-white/10 blur-3xl" />
                            <div className="relative z-10 space-y-4">
                                <div className="flex items-center gap-3">
                                    <Bot size={20} fill="currentColor" />
                                    <h4 className="text-[11px] font-semibold uppercase tracking-wide">IA Moderator</h4>
                                </div>
                                <p className="text-xs font-medium italic leading-relaxed text-blue-50">
                                    Optimus sugiere revisar los debates recientes antes de abrir uno nuevo para evitar duplicados.
                                </p>
                            </div>
                        </section>
                    </aside>

                    <div className="space-y-3 pb-4 lg:col-span-9">
                        <div className="flex flex-col justify-between gap-4 px-4 md:flex-row md:items-center">
                            <h2 className="text-lg font-semibold uppercase tracking-tight text-[hsl(var(--text-primary))] dark:text-white">Debates Populares</h2>
                            <div className="relative w-full md:w-80">
                                <input
                                    value={search}
                                    onChange={(event) => setSearch(event.target.value)}
                                    placeholder="Buscar temas..."
                                    className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-4 py-1.5 text-sm font-bold outline-none transition-all focus:ring-4 focus:ring-[hsl(var(--primary))]/10 dark:border-white/10 dark:bg-white/5"
                                />
                                <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                            </div>
                        </div>

                        <div className={clsx("gap-4", viewMode === "grid" ? "grid md:grid-cols-2" : "space-y-4")}>
                            {!loading && visibleThreads.length === 0 && (
                                <div className="rounded-md border border-[hsl(var(--border))] bg-white/50 py-1.5 text-center dark:border-white/10 dark:bg-white/5">
                                    <MessageSquare className="mx-auto h-8 w-16 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]" />
                                    <h3 className="mt-4 text-base font-bold text-[hsl(var(--text-primary))] dark:text-white">Aun no hay debates</h3>
                                    <p className="text-[hsl(var(--text-secondary))]">Inicia una conversacion en esta categoria.</p>
                                </div>
                            )}
                            {visibleThreads.map((thread) => (
                                <motion.div
                                    key={thread.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="group cursor-pointer rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 shadow-sm transition-all hover:border-blue-500/20 hover:shadow-xl dark:border-white/10 dark:bg-white/5"
                                >
                                    <div className="flex flex-col items-start gap-4 md:flex-row md:items-center">
                                        <div className="flex shrink-0 flex-col items-center gap-1 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 dark:border-white/5 dark:bg-white/5">
                                            <ThumbsUp size={18} className="text-[hsl(var(--text-secondary))] transition-colors group-hover:text-[hsl(var(--primary))]" />
                                            <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{thread.upvotes}</span>
                                        </div>
                                        <div className="flex-1 space-y-3">
                                            <div className="flex items-center gap-3">
                                                <span className="rounded-full bg-blue-50 px-3 py-1 text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:bg-blue-900/20 dark:text-[hsl(var(--primary))]">{thread.category}</span>
                                                {thread.is_resolved && <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-[9px] font-semibold uppercase tracking-wide text-emerald-600 dark:bg-emerald-900/20"><CheckCircle2 size={12} /> Resuelto</span>}
                                            </div>
                                            <h4 className="text-base font-bold tracking-tight text-[hsl(var(--text-primary))] transition-colors group-hover:text-[hsl(var(--primary))] dark:text-white">{thread.title}</h4>
                                            <div className="flex items-center gap-4 text-[hsl(var(--text-secondary))]">
                                                <div className="flex items-center gap-1.5"><User size={14} /><span className="text-[11px] font-bold">{thread.author}</span></div>
                                                <div className="size-1 rounded-full bg-[hsl(var(--surface-2))]" />
                                                <div className="flex items-center gap-1.5"><Clock size={14} /><span className="text-[11px] font-bold">{thread.last_activity}</span></div>
                                            </div>
                                        </div>
                                        <div className="flex shrink-0 items-center gap-4 md:border-l md:border-[hsl(var(--border))] md:pl-8 dark:md:border-white/5">
                                            <div className="text-center">
                                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">{thread.replies}</p>
                                                <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Respuestas</p>
                                            </div>
                                            <ChevronRight size={24} className="text-[hsl(var(--text-secondary))] transition-all group-hover:translate-x-1 group-hover:text-[hsl(var(--primary))]" />
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </div>
            </main>

            <WorkspaceDrawer
                isOpen={isCreateOpen}
                onClose={() => setIsCreateOpen(false)}
                title="Iniciar Debate"
                subtitle="Publicar una nueva conversacion academica"
            >
                <form onSubmit={handleCreateThread} className="space-y-2">
                    <div className="space-y-2">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Titulo</label>
                        <input
                            required
                            value={newThread.title}
                            onChange={(event) => setNewThread((prev) => ({ ...prev, title: event.target.value }))}
                            placeholder="Tema del debate"
                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:border-white/10 dark:bg-white/5 dark:text-white"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Categoria</label>
                        <select
                            value={newThread.category}
                            onChange={(event) => setNewThread((prev) => ({ ...prev, category: event.target.value }))}
                            className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] dark:border-white/10 dark:bg-white/5 dark:text-white"
                        >
                            {categories.filter((category) => category !== "Todos").map((category) => <option key={category} value={category}>{category}</option>)}
                        </select>
                    </div>
                    <button disabled={saving} className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-white disabled:opacity-60">
                        {saving ? "Publicando..." : "Publicar debate"}
                    </button>
                </form>
            </WorkspaceDrawer>
        </div>
    );
}

function normalizeThread(thread: any, fallbackAuthor?: string) {
    return {
        ...thread,
        author: thread.author || fallbackAuthor || `Usuario ${thread.author_id ?? ""}`.trim(),
        replies: thread.replies ?? 0,
        upvotes: thread.upvotes ?? 0,
        last_activity: thread.last_activity || (thread.created_at ? new Date(thread.created_at).toLocaleDateString("es-CO") : "Sin fecha"),
    };
}

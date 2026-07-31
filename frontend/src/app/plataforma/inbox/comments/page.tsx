"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AtSign,
  Calendar,
  ChevronRight,
  FileText,
  Image as ImageIcon,
  Layout,
  MessageSquare,
  Music,
  RefreshCw,
  Search,
  Send,
  Video,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import type { ProjectCommentItem } from "@/types/projects";

const TAB_LABEL: Record<CommentAdminTab, string> = {
  authored: "Mis comentarios",
  mentions: "Menciones",
};

type CommentAdminTab = "authored" | "mentions";
type CommentModule = "all" | "project" | "activity" | "agenda";

const MODULE_OPTIONS: { value: CommentModule; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "project", label: "Proyectos" },
  { value: "activity", label: "Actividades" },
  { value: "agenda", label: "Agenda" },
];

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

function moduleLabel(type: string) {
  switch (type) {
    case "project":
      return "Proyecto";
    case "activity":
      return "Actividad";
    case "agenda":
      return "Agenda";
    default:
      return "Comentario";
  }
}

function moduleIcon(type: string) {
  switch (type) {
    case "project":
      return <Layout size={14} />;
    case "activity":
      return <Send size={14} />;
    case "agenda":
      return <Calendar size={14} />;
    default:
      return <MessageSquare size={14} />;
  }
}

function attachmentIcon(type: string | null | undefined) {
  switch (type) {
    case "image":
      return <ImageIcon size={14} />;
    case "video":
      return <Video size={14} />;
    case "audio":
      return <Music size={14} />;
    default:
      return <FileText size={14} />;
  }
}

function buildHref(item: ProjectCommentItem) {
  if (item.module_type === "activity" && item.task_id) {
    return `/plataforma/proyectos/${item.project_id}?task=${item.task_id}`;
  }
  if (item.module_type === "agenda") {
    return `/plataforma/agenda?event=${item.project_id}`;
  }
  return `/plataforma/proyectos/${item.project_id}`;
}

export default function CommentAdminPage() {
  const { token } = useAuth();
  const [tab, setTab] = useState<CommentAdminTab>("authored");
  const [moduleFilter, setModuleFilter] = useState<CommentModule>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [items, setItems] = useState<ProjectCommentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const LIMIT = 50;

  // Debounce local search to avoid excessive aria-live announcements while typing
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const fetchItems = React.useCallback(async (reset = true) => {
    if (!token) return;
    const currentOffset = reset ? 0 : offset;
    if (reset) {
      setLoading(true);
      setHasMore(true);
    } else {
      setLoadingMore(true);
    }
    setError(null);

    try {
      const endpoint = tab === "authored" ? "/comments/me/created" : "/comments/me/mentions";
      const query: Record<string, string> = {
        limit: String(LIMIT),
        offset: String(currentOffset),
      };
      if (moduleFilter && moduleFilter !== "all") {
        query.type = moduleFilter;
      }
      const data = await apiFetch<ProjectCommentItem[]>(endpoint, { token, query });
      setItems((prev) => (reset ? data : [...prev, ...data]));
      setHasMore(data.length === LIMIT);
      setOffset(currentOffset + LIMIT);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar comentarios");
      if (reset) setItems([]);
    } finally {
      if (reset) setLoading(false);
      else setLoadingMore(false);
    }
  }, [tab, token, offset, moduleFilter]);

  React.useEffect(() => {
    setOffset(0);
    setHasMore(true);
    fetchItems(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, token, moduleFilter]);

  const filtered = useMemo(() => {
    if (!debouncedSearch.trim()) return items;
    const term = debouncedSearch.toLowerCase();
    return items.filter(
      (item) =>
        item.content.toLowerCase().includes(term) ||
        (item.context_title && item.context_title.toLowerCase().includes(term)) ||
        item.author_name.toLowerCase().includes(term)
    );
  }, [items, debouncedSearch]);

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
            aria-label="Buscar comentarios"
            className="pl-9 pr-3 py-1.5 text-xs bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] w-56 transition-all"
          />
        </div>

        <button
          onClick={() => void fetchItems(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 font-semibold text-xs text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--primary))] transition-colors"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Actualizar
        </button>
      </div>

      <div className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/5 flex flex-col sm:flex-row sm:items-center gap-3 shrink-0">
        <div
          role="tablist"
          aria-label="Tipo de comentarios"
          className="flex rounded-lg overflow-hidden border border-[hsl(var(--border))] dark:border-white/10"
        >
          {(["authored", "mentions"] as const).map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              id={`comment-tab-${t}`}
              aria-controls="comment-panel"
              onClick={() => setTab(t)}
              className={clsx(
                "px-4 py-2 text-xs font-semibold transition-colors flex items-center gap-2",
                tab === t
                  ? "bg-[hsl(var(--primary))] text-white"
                  : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]"
              )}
            >
              {t === "mentions" && <AtSign size={12} />}
              {t === "authored" && <Send size={12} />}
              {TAB_LABEL[t]}
            </button>
          ))}
        </div>

        <select
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value as CommentModule)}
          aria-label="Filtrar por módulo"
          className="px-3 py-2 text-xs bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] transition-all"
        >
          {MODULE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        <span
          className="ml-auto text-xs font-semibold text-[hsl(var(--text-secondary))]"
          aria-live="polite"
          aria-atomic="true"
        >
          {filtered.length} resultado{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div
        id="comment-panel"
        role="tabpanel"
        aria-labelledby={`comment-tab-${tab}`}
        className="flex-1 overflow-y-auto scrollbar-thin"
      >
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
                onClick={() => void fetchItems(true)}
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
                {tab === "authored" ? "Aún no has comentado" : "Aún no te han mencionado"}
              </p>
              <p className="text-xs text-[hsl(var(--text-secondary))]">
                {tab === "authored"
                  ? "Tus comentarios en proyectos, actividades y agenda aparecerán aquí."
                  : "Cuando alguien te mencione con @ en un comentario, lo verás aquí."}
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
                >
                  <Link
                    href={buildHref(item)}
                    className="flex items-start gap-4 px-4 py-3 group hover:bg-[hsl(var(--surface-1))]/50 dark:hover:bg-white/[0.02] transition-colors"
                  >
                    <div className="size-10 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center shrink-0">
                      <span className="text-xs font-bold text-[hsl(var(--text-secondary))] uppercase">
                        {item.author_name.charAt(0)}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
                          {item.author_name}
                        </span>
                        <span className="text-xs text-[hsl(var(--text-secondary))]">
                          {tab === "authored" ? "comentó en" : "te mencionó en"}
                        </span>
                        <span className="text-xs font-semibold text-[hsl(var(--primary))]">
                          {item.context_title || moduleLabel(item.module_type || "project")}
                        </span>
                        <span
                          className={clsx(
                            "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-2xs font-bold",
                            item.module_type === "agenda"
                              ? "bg-[hsl(var(--info))]/10 text-[hsl(var(--info))]"
                              : item.module_type === "activity"
                              ? "bg-[hsl(var(--warning))]/10 text-[hsl(var(--warning))]"
                              : "bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]"
                          )}
                        >
                          {moduleIcon(item.module_type || "project")}
                          {moduleLabel(item.module_type || "project")}
                        </span>
                      </div>
                      <p className="text-sm text-[hsl(var(--text-secondary))] leading-snug line-clamp-3 whitespace-pre-line">
                        {item.content}
                      </p>
                      <div className="flex items-center gap-4 mt-2">
                        <span className="text-2xs font-medium text-[hsl(var(--text-secondary))]">
                          {formatCommentTime(item.created_at)}
                        </span>
                        {item.mentions && item.mentions.length > 0 && (
                          <span className="inline-flex items-center gap-1 text-2xs font-medium text-[hsl(var(--info))]">
                            <AtSign size={10} />
                            {item.mentions.length} mención{item.mentions.length !== 1 ? "es" : ""}
                          </span>
                        )}
                        {item.attachments && item.attachments.length > 0 && (
                          <span className="inline-flex items-center gap-1 text-2xs font-medium text-[hsl(var(--primary))]">
                            {attachmentIcon(item.attachments[0].type)}
                            {item.attachments.length} adjunto{item.attachments.length !== 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="self-center opacity-0 group-hover:opacity-100 transition-opacity text-[hsl(var(--primary))]">
                      <ChevronRight size={16} />
                    </div>
                  </Link>
                </motion.div>
              ))}

              {hasMore && !search.trim() && !loadingMore && (
                <div className="flex justify-center py-4">
                  <button
                    onClick={() => void fetchItems(false)}
                    aria-label="Cargar más comentarios"
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white transition-colors"
                  >
                    Cargar más
                  </button>
                </div>
              )}
              {loadingMore && (
                <div className="flex justify-center py-4 text-xs font-semibold text-[hsl(var(--text-secondary))]">
                    <span className="sr-only" aria-live="polite">
                      Cargando más comentarios…
                    </span>
                    <span aria-hidden="true">Cargando más…</span>
                  </div>
              )}
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

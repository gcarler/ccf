"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import {
  Archive,
  Heart, MessageCircle, CheckCircle2, XCircle, Clock,
  Search, Plus, Users, ChevronRight, X, ImageIcon, PlayCircle, Headphones, Save, RotateCcw
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import TestimonialForm from "@/components/TestimonialForm";
import clsx from "clsx";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";
import ViewSwitcher, { ViewType } from "@/components/ViewSwitcher";
import UniversalCalendarView from "@/components/ui/UniversalCalendarView";
import UniversalGanttView from "@/components/ui/UniversalGanttView";
import UniversalWikiView from "@/components/ui/UniversalWikiView";
import {
  activeTestimonialMediaAssets,
  inferTestimonialMediaType,
  normalizeTestimonialMediaType,
  TestimonialMediaType,
} from "@/lib/cms/testimonialMedia";

interface Testimonial {
  id: number;
  content: string;
  emotion: string;
  media_type?: "text" | "image" | "video" | "podcast" | string;
  media_url?: string | null;
  image_url?: string | null;
  video_url?: string | null;
  podcast_url?: string | null;
  created_at: string;
  author_id: number;
  published?: boolean;
  is_approved?: boolean;
  show_on_home?: boolean;
  status?: "pending" | "approved" | "archived" | string;
}

interface MediaItem {
  id: number;
  url: string;
  filename?: string;
  mime_type?: string;
  alt_text?: string;
  status?: string;
}

const EMOTION_CONFIG: Record<string, { color: string; bg: string; border: string; emoji: string }> = {
  "Sanidad":       { color: "text-rose-600",    bg: "bg-rose-50 dark:bg-rose-900/20",    border: "border-rose-200 dark:border-rose-700/30",    emoji: "💊" },
  "Provisión":     { color: "text-emerald-600", bg: "bg-emerald-50 dark:bg-emerald-900/20", border: "border-emerald-200 dark:border-emerald-700/30", emoji: "🙌" },
  "Restauración":  { color: "text-blue-600",    bg: "bg-blue-50 dark:bg-blue-900/20",    border: "border-blue-200 dark:border-blue-700/30",    emoji: "✨" },
  "Fe":            { color: "text-blue-600",  bg: "bg-blue-50 dark:bg-blue-900/20", border: "border-blue-200 dark:border-blue-700/30", emoji: "🙏" },
};
const defaultEmotion = { color: "text-slate-500", bg: "bg-slate-50 dark:bg-white/5", border: "border-slate-200 dark:border-white/10", emoji: "💬" };

const EMOTION_FILTERS = ["Todos", "Sanidad", "Provisión", "Restauración", "Fe"];
const TESTIMONIAL_VIEWS: ViewType[] = ["grid", "list", "table", "board", "kanban", "calendar", "gantt", "wiki"];

function getTestimonialMediaUrl(testimonial: Pick<Testimonial, "media_type" | "media_url" | "image_url" | "video_url" | "podcast_url">): string {
  if (testimonial.media_type === "image") return testimonial.image_url || testimonial.media_url || "";
  if (testimonial.media_type === "video") return testimonial.video_url || testimonial.media_url || "";
  if (testimonial.media_type === "podcast") return testimonial.podcast_url || testimonial.media_url || "";
  return testimonial.media_url || testimonial.image_url || testimonial.video_url || testimonial.podcast_url || "";
}

function getMediaLabel(testimonial: Pick<Testimonial, "media_type" | "media_url" | "image_url" | "video_url" | "podcast_url">): string {
  const url = getTestimonialMediaUrl(testimonial);
  if (!url) return "Sin medio";
  if (testimonial.media_type === "image") return "Imagen";
  if (testimonial.media_type === "video") return "Video";
  if (testimonial.media_type === "podcast") return "Podcast";
  return "Medio";
}

function getInitials(id: number): string {
  const names = ["AL", "MR", "JC", "PS", "LG", "DA", "CR", "FM", "BT", "NK"];
  return names[id % names.length];
}

function getAvatarColor(id: number): string {
  const colors = [
    "bg-blue-600", "bg-blue-600", "bg-emerald-600", "bg-rose-600",
    "bg-amber-600", "bg-cyan-600", "bg-pink-600", "bg-teal-600"
  ];
  return colors[id % colors.length];
}

export default function CmsTestimonialsPage() {
  const { token, user } = useAuth();
  const [testimonials, setTestimonials] = useState<Testimonial[]>([]);
  const [filter, setFilter] = useState("Todos");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "approved" | "pending" | "archived">("all");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selected, setSelected] = useState<Testimonial | null>(null);
  const [processing, setProcessing] = useState<number | null>(null);
  const [viewType, setViewType] = useState<ViewType>("grid");
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [mediaLoading, setMediaLoading] = useState(true);
  const [mediaSearch, setMediaSearch] = useState("");

  const fetchTestimonials = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    try {
      const data = await apiFetch<Testimonial[]>("/admin/testimonials", { token, cache: "no-store" });
      setTestimonials(
        Array.isArray(data)
          ? data.map(row => ({ ...row, status: row.status || (row.is_approved ? "approved" : "pending"), published: row.published ?? row.is_approved ?? false }))
          : []
      );
    } catch {
      setTestimonials([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchTestimonials(); }, [fetchTestimonials]);

  const fetchMedia = useCallback(async () => {
    if (!token) {
      setMediaItems([]);
      setMediaLoading(false);
      return;
    }

    setMediaLoading(true);
    try {
      const data = await apiFetch<MediaItem[]>("/cms/media", { token, cache: "no-store" });
      setMediaItems(Array.isArray(data) ? data : []);
    } catch {
      setMediaItems([]);
    } finally {
      setMediaLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchMedia(); }, [fetchMedia]);

  const handleToggle = async (t: Testimonial) => {
    if (!token) return;
    const next = !t.published;
    const nextStatus = next ? "approved" : "pending";
    setTestimonials(prev => prev.map(i => i.id === t.id ? { ...i, published: next, status: nextStatus } : i));
    setProcessing(t.id);
    try {
      const updated = await apiFetch<Testimonial>(`/admin/testimonials/${t.id}`, {
        method: "PATCH", token, body: { status: nextStatus }
      });
      if (selected?.id === t.id) setSelected(prev => prev ? { ...prev, ...updated, published: next, status: nextStatus } : null);
    } catch {
      setTestimonials(prev => prev.map(i => i.id === t.id ? { ...i, published: t.published } : i));
    } finally {
      setProcessing(null);
    }
  };

  const toggleArchive = async (t: Testimonial) => {
    if (!token) return;
    const restore = t.status === "archived";
    const nextStatus = restore ? "pending" : "archived";
    setProcessing(t.id);
    try {
      if (restore) {
        const updated = await apiFetch<Testimonial>(`/admin/testimonials/${t.id}`, {
          method: "PATCH",
          token,
          body: { status: nextStatus },
        });
        const normalized = { ...updated, published: false, status: nextStatus };
        setTestimonials(prev => prev.map(item => item.id === t.id ? normalized : item));
        if (selected?.id === t.id) setSelected(normalized);
      } else {
        await apiFetch(`/admin/testimonials/${t.id}`, { method: "DELETE", token });
        const archived = { ...t, published: false, is_approved: false, show_on_home: false, status: "archived" };
        setTestimonials(prev => prev.map(item => item.id === t.id ? archived : item));
        if (selected?.id === t.id) setSelected(archived);
      }
    } finally {
      setProcessing(null);
    }
  };

  const saveSelected = async () => {
    if (!token || !selected) return;
    setProcessing(selected.id);
    const mediaType = normalizeTestimonialMediaType(selected.media_type);
    const mediaUrl = mediaType === "text" ? "" : getTestimonialMediaUrl(selected);
    try {
      const updated = await apiFetch<Testimonial>(`/admin/testimonials/${selected.id}`, {
        method: "PATCH",
        token,
        body: {
          content: selected.content,
          emotion: selected.emotion,
          media_type: mediaType,
          media_url: mediaUrl || null,
          image_url: mediaType === "image" ? mediaUrl || null : null,
          video_url: mediaType === "video" ? mediaUrl || null : null,
          podcast_url: mediaType === "podcast" ? mediaUrl || null : null,
          status: selected.status === "archived" ? "archived" : selected.published ? "approved" : "pending",
          show_on_home: selected.show_on_home ?? false,
        },
      });
      const normalized = { ...updated, status: updated.status || (updated.is_approved ? "approved" : "pending"), published: updated.is_approved ?? selected.published ?? false };
      setSelected(normalized);
      setTestimonials(prev => prev.map(item => item.id === selected.id ? normalized : item));
    } finally {
      setProcessing(null);
    }
  };

  const compatibleMedia = useMemo(
    () => selected ? activeTestimonialMediaAssets(mediaItems, selected.media_type, mediaSearch, 8) : [],
    [mediaItems, mediaSearch, selected],
  );

  const changeSelectedMediaType = (nextType: TestimonialMediaType) => {
    setMediaSearch("");
    setSelected(prev => {
      if (!prev) return prev;
      if (nextType === "text") {
        return { ...prev, media_type: "text", media_url: null, image_url: null, video_url: null, podcast_url: null };
      }
      if (normalizeTestimonialMediaType(prev.media_type) === nextType) return prev;
      return { ...prev, media_type: nextType, media_url: null, image_url: null, video_url: null, podcast_url: null };
    });
  };

  const assignMediaToSelected = (item: MediaItem) => {
    const mediaType = inferTestimonialMediaType(item.mime_type);
    if (!mediaType) return;
    setSelected(prev => prev ? {
      ...prev,
      media_type: mediaType,
      media_url: item.url,
      image_url: mediaType === "image" ? item.url : null,
      video_url: mediaType === "video" ? item.url : null,
      podcast_url: mediaType === "podcast" ? item.url : null,
    } : prev);
  };

  const stats = useMemo(() => ({
    total: testimonials.length,
    approved: testimonials.filter(t => t.status !== "archived" && t.published).length,
    pending: testimonials.filter(t => t.status !== "archived" && !t.published).length,
    byEmotion: EMOTION_FILTERS.slice(1).map(e => ({
      label: e,
      count: testimonials.filter(t => t.emotion?.toLowerCase() === e.toLowerCase()).length,
    })),
  }), [testimonials]);

  const filtered = useMemo(() => {
    return testimonials.filter(t => {
      const matchEmotion = filter === "Todos" || t.emotion?.toLowerCase() === filter.toLowerCase();
      const matchStatus = statusFilter === "all"
        || (statusFilter === "approved" ? t.status !== "archived" && t.published : statusFilter === "pending" ? t.status !== "archived" && !t.published : t.status === "archived");
      const matchSearch = !search || t.content.toLowerCase().includes(search.toLowerCase());
      return matchEmotion && matchStatus && matchSearch;
    });
  }, [testimonials, filter, statusFilter, search]);

  const testimonialGroups = useMemo(() => ([
    { id: "approved", label: "Aprobados", items: filtered.filter(t => t.status !== "archived" && t.published) },
    { id: "pending", label: "Pendientes", items: filtered.filter(t => t.status !== "archived" && !t.published) },
    { id: "archived", label: "Archivados", items: filtered.filter(t => t.status === "archived") },
  ]), [filtered]);

  const calendarEvents = useMemo(() => filtered.map(t => ({
    id: t.id,
    title: `${t.emotion || "Testimonio"} #${t.id}`,
    date: (t.created_at || new Date().toISOString()).split("T")[0],
    color: t.published ? "emerald" as const : "amber" as const,
    location: `Miembro #${t.author_id}`,
  })), [filtered]);

  const ganttItems = useMemo(() => filtered.map(t => ({
    id: t.id,
    title: `${t.emotion || "Testimonio"} #${t.id}`,
    subtitle: t.published ? "Publicado" : "Pendiente",
    start_date: t.created_at || new Date().toISOString(),
    end_date: t.created_at || new Date().toISOString(),
    color: t.published ? "emerald" as const : "amber" as const,
    progress: t.published ? 100 : 35,
  })), [filtered]);

  const renderTestimonialList = () => (
    <div className="space-y-3 max-w-5xl mx-auto">
      {filtered.map(t => {
        const cfg = EMOTION_CONFIG[t.emotion] ?? defaultEmotion;
        return (
          <button key={t.id} onClick={() => setSelected(t)} className={clsx("w-full text-left bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/10 rounded-lg p-4 hover:border-rose-300 transition-all flex items-center gap-4", t.status === "archived" && "opacity-70 bg-amber-50/40 dark:bg-amber-500/5")}>
            <div className={clsx("size-10 rounded-lg flex items-center justify-center text-white text-[11px] font-semibold shrink-0", getAvatarColor(t.author_id))}>{getInitials(t.author_id)}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={clsx("text-[10px] font-semibold uppercase tracking-wide", cfg.color)}>{cfg.emoji} {t.emotion || "Testimonio"}</span>
                <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", t.status === "archived" ? "bg-slate-100 text-slate-500" : t.published ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>{t.status === "archived" ? "Archivado" : t.published ? "Publicado" : "Pendiente"}</span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-300 line-clamp-1 mt-1">{t.content}</p>
            </div>
            <span className="text-[10px] font-bold text-slate-400">{new Date(t.created_at).toLocaleDateString("es-CO")}</span>
          </button>
        );
      })}
    </div>
  );

  const renderTestimonialTable = () => (
    <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden">
      <table className="w-full text-left">
        <thead className="bg-slate-50 dark:bg-white/5">
          <tr>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Testimonio</th>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden md:table-cell">Emoción</th>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden lg:table-cell">Estado</th>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden xl:table-cell">Fecha</th>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Acción</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-white/5">
          {filtered.map(t => (
            <tr key={t.id} onClick={() => setSelected(t)} className={clsx("hover:bg-slate-50 dark:hover:bg-white/[0.02] cursor-pointer", t.status === "archived" && "opacity-70 bg-amber-50/40 dark:bg-amber-500/5")}>
              <td className="px-4 py-3 text-sm text-slate-700 dark:text-slate-200 line-clamp-1 max-w-[420px]">{t.content}</td>
              <td className="px-4 py-3 hidden md:table-cell text-[11px] font-bold text-slate-500">{t.emotion || "—"}</td>
              <td className="px-4 py-3 hidden lg:table-cell"><span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", t.status === "archived" ? "bg-slate-100 text-slate-500" : t.published ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>{t.status === "archived" ? "Archivado" : t.published ? "Publicado" : "Pendiente"}</span></td>
              <td className="px-4 py-3 hidden xl:table-cell text-[11px] text-slate-400">{new Date(t.created_at).toLocaleDateString("es-CO")}</td>
              <td className="px-4 py-3">
                <button onClick={e => { e.stopPropagation(); toggleArchive(t); }} disabled={processing === t.id} className="text-[9px] font-semibold uppercase tracking-wide text-amber-600 disabled:opacity-50">{t.status === "archived" ? "Restaurar" : "Archivar"}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderTestimonialBoard = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-full">
      {testimonialGroups.map(group => (
        <section key={group.id} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-4">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{group.label}</span>
            <span className="text-[10px] font-semibold text-slate-400">{group.items.length}</span>
          </div>
          <div className="space-y-3">
            {group.items.map(t => (
              <button key={t.id} onClick={() => setSelected(t)} className={clsx("w-full text-left bg-white dark:bg-white/[0.04] border border-slate-200 dark:border-white/5 rounded-lg p-4 hover:border-rose-300 transition-all", t.status === "archived" && "opacity-70 bg-amber-50/40 dark:bg-amber-500/5")}>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">Miembro #{t.author_id} · {t.emotion || "Testimonio"}</p>
                <p className="text-sm text-slate-700 dark:text-slate-200 line-clamp-3">{t.content}</p>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-white dark:bg-[#0d0e11] overflow-hidden">
      {/* ── Header toolbar ── */}
      <header className="shrink-0 border-b border-slate-100 dark:border-white/5 px-3 py-1.5 flex items-center gap-4">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <MessageCircle size={18} className="text-rose-500 shrink-0" />
          <h1 className="text-[13px] font-semibold uppercase tracking-wide text-slate-800 dark:text-white">
            Testimonios
          </h1>
        </div>
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar..."
            className="pl-8 pr-4 py-2 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm outline-none w-48 focus:ring-2 focus:ring-rose-500/20"
          />
        </div>
        <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={TESTIMONIAL_VIEWS} />
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-3 py-2 bg-rose-500 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-rose-500/20 hover:bg-rose-600 active:scale-95 transition-all"
        >
          <Plus size={14} /> Nuevo Testimonio
        </button>
      </header>

      {/* ── Stats bar ── */}
      <div className="shrink-0 border-b border-slate-100 dark:border-white/5 px-3 py-3 flex items-center gap-3">
        <div className="flex items-center gap-3">
          {[
            { label: "Total", value: stats.total, icon: Users, color: "text-slate-600" },
            { label: "Aprobados", value: stats.approved, icon: CheckCircle2, color: "text-emerald-600" },
            { label: "Pendientes", value: stats.pending, icon: Clock, color: "text-amber-500" },
            { label: "Archivados", value: testimonials.filter(t => t.status === "archived").length, icon: Archive, color: "text-slate-500" },
          ].map(s => (
            <button
              key={s.label}
              onClick={() => setStatusFilter(
                s.label === "Total" ? "all" : s.label === "Aprobados" ? "approved" : s.label === "Pendientes" ? "pending" : "archived"
              )}
              className={clsx(
                "flex items-center gap-2 transition-all",
                statusFilter === (s.label === "Total" ? "all" : s.label === "Aprobados" ? "approved" : s.label === "Pendientes" ? "pending" : "archived")
                  ? "opacity-100"
                  : "opacity-50 hover:opacity-75"
              )}
            >
              <s.icon size={14} className={s.color} />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{s.label}</span>
              <span className={clsx("text-xl font-semibold tabular-nums leading-none", s.color)}>{s.value}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Filter pills ── */}
      <div className="shrink-0 px-3 py-3 flex items-center gap-2 border-b border-slate-100 dark:border-white/5">
        {EMOTION_FILTERS.map(f => {
          const cfg = EMOTION_CONFIG[f] ?? defaultEmotion;
          const count = f === "Todos" ? stats.total : stats.byEmotion.find(e => e.label === f)?.count ?? 0;
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide border transition-all",
                filter === f
                  ? `${cfg.bg} ${cfg.border} ${cfg.color}`
                  : "bg-slate-100 dark:bg-white/5 border-transparent text-slate-500 hover:text-slate-700"
              )}
            >
              {f !== "Todos" && <span>{cfg.emoji}</span>}
              {f}
              <span className={clsx("ml-0.5 font-semibold", filter === f ? cfg.color : "text-slate-400")}>{count}</span>
            </button>
          );
        })}
      </div>

      {/* ── Content area ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Grid */}
        <div className="flex-1 overflow-y-auto p-3">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-48 rounded-lg bg-slate-100 dark:bg-white/5 animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-4 py-1.5">
              <div className="size-8 rounded-lg bg-slate-50 dark:bg-white/5 flex items-center justify-center">
                <MessageCircle size={36} strokeWidth={1} className="text-slate-300" />
              </div>
              <div className="space-y-1">
                <p className="font-semibold text-slate-700 dark:text-white uppercase tracking-tight">Sin testimonios</p>
                <p className="text-sm text-slate-400">Ajusta los filtros o agrega uno nuevo</p>
              </div>
            </div>
          ) : viewType === "list" ? (
            renderTestimonialList()
          ) : viewType === "table" ? (
            renderTestimonialTable()
          ) : viewType === "board" || viewType === "kanban" ? (
            renderTestimonialBoard()
          ) : viewType === "calendar" ? (
            <UniversalCalendarView
              title="Calendario de testimonios"
              events={calendarEvents}
              onEventClick={(event) => {
                const testimonial = filtered.find(item => item.id === event.id);
                if (testimonial) setSelected(testimonial);
              }}
            />
          ) : viewType === "gantt" ? (
            <UniversalGanttView
              moduleName="Testimonios CMS"
              items={ganttItems}
              onItemClick={(item) => {
                const testimonial = filtered.find(entry => entry.id === item.id);
                if (testimonial) setSelected(testimonial);
              }}
            />
          ) : viewType === "wiki" ? (
            <UniversalWikiView moduleName="Testimonios CMS" storageKey="cms-testimonials-wiki" />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filtered.map(t => {
                const cfg = EMOTION_CONFIG[t.emotion] ?? defaultEmotion;
                const isSelected = selected?.id === t.id;
                return (
                  <motion.div
                    key={t.id}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    onClick={() => setSelected(isSelected ? null : t)}
                    className={clsx(
                      "group relative rounded-lg border p-3 flex flex-col gap-4 cursor-pointer transition-all",
                      isSelected
                        ? `${cfg.bg} ${cfg.border} ring-2 ring-current`
                        : "bg-white dark:bg-white/[0.02] border-slate-200 dark:border-white/10 hover:border-slate-300 dark:hover:border-white/20 hover:shadow-lg"
                    )}
                  >
                    {/* Status badge */}
                    <div className="absolute top-4 right-4">
                      <span className={clsx(
                        "px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide border",
                        t.published
                          ? "bg-emerald-50 text-emerald-600 border-emerald-200"
                          : "bg-amber-50 text-amber-600 border-amber-200"
                      )}>
                        {t.published ? "Publicado" : "Pendiente"}
                      </span>
                    </div>

                    {/* Author */}
                    <div className="flex items-center gap-3 pr-20">
                      <div className={clsx("size-10 rounded-lg flex items-center justify-center text-white text-[11px] font-semibold shrink-0", getAvatarColor(t.author_id))}>
                        {getInitials(t.author_id)}
                      </div>
                      <div>
                        <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">Miembro #{t.author_id}</p>
                        <div className={clsx("flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide", cfg.color)}>
                          <span>{cfg.emoji}</span>
                          <span>{t.emotion || "Testimonio"}</span>
                        </div>
                        {getTestimonialMediaUrl(t) && (
                          <div className="mt-1 flex items-center gap-1 text-[9px] font-semibold uppercase tracking-wide text-slate-400">
                            {t.media_type === "video" ? <PlayCircle size={10} /> : t.media_type === "podcast" ? <Headphones size={10} /> : <ImageIcon size={10} />}
                            {getMediaLabel(t)}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Content */}
                    <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed line-clamp-3 flex-1">
                      &ldquo;{t.content}&rdquo;
                    </p>

                    {/* Footer */}
                    <div className="flex items-center justify-between pt-1 border-t border-slate-100 dark:border-white/5">
                      <p className="text-[9px] font-bold text-slate-400 uppercase">
                        {new Date(t.created_at).toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" })}
                      </p>
                      <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={e => { e.stopPropagation(); handleToggle(t); }}
                          disabled={processing === t.id || t.status === "archived"}
                          className={clsx(
                            "flex items-center gap-1 px-2.5 py-1 rounded-lg text-[9px] font-semibold uppercase tracking-wide transition-all border",
                            t.published
                              ? "bg-rose-50 text-rose-600 border-rose-200 hover:bg-rose-100"
                              : "bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-100"
                          )}
                        >
                          {t.published ? <><XCircle size={10} /> Rechazar</> : <><CheckCircle2 size={10} /> Aprobar</>}
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); toggleArchive(t); }}
                          disabled={processing === t.id}
                          className={clsx(
                            "flex items-center gap-1 px-2.5 py-1 rounded-lg text-[9px] font-semibold uppercase tracking-wide transition-all border",
                            t.status === "archived"
                              ? "bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-100"
                              : "bg-amber-50 text-amber-600 border-amber-200 hover:bg-amber-100"
                          )}
                        >
                          {t.status === "archived" ? <><RotateCcw size={10} /> Restaurar</> : <><Archive size={10} /> Archivar</>}
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); setSelected(isSelected ? null : t); }}
                          className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-white/10 transition-all"
                        >
                          <ChevronRight size={14} />
                        </button>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Detail panel ── */}
        <AnimatePresence>
          {selected && (
            <motion.aside
              key="detail"
              initial={{ x: 380, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 380, opacity: 0 }}
              transition={{ type: "spring", damping: 28, stiffness: 280 }}
              className="w-96 shrink-0 border-l border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-[#111418] flex flex-col overflow-y-auto"
            >
              {/* Panel header */}
              <div className="p-3 flex items-center justify-between border-b border-slate-200 dark:border-white/5 shrink-0">
                <div className="flex items-center gap-2">
                  <MessageCircle size={14} className="text-rose-500" />
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Testimonio #{selected.id}</p>
                </div>
                <button onClick={() => setSelected(null)} className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-white/10 text-slate-400 transition-all">
                  <X size={14} />
                </button>
              </div>

              {/* Author header */}
              {(() => {
                const cfg = EMOTION_CONFIG[selected.emotion] ?? defaultEmotion;
                return (
                  <div className={clsx("p-3 flex items-center gap-4 border-b border-slate-200 dark:border-white/5", cfg.bg)}>
                    <div className={clsx("size-7 rounded-lg flex items-center justify-center text-white text-base font-semibold shrink-0", getAvatarColor(selected.author_id))}>
                      {getInitials(selected.author_id)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-800 dark:text-white">Miembro #{selected.author_id}</p>
                      <div className={clsx("flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide mt-0.5", cfg.color)}>
                        <span>{cfg.emoji}</span>
                        <span>{selected.emotion || "Sin categoría"}</span>
                      </div>
                    </div>
                    <span className={clsx(
                      "px-2 py-1 rounded-md text-[9px] font-semibold uppercase tracking-wide border",
                      selected.status === "archived" ? "bg-slate-100 text-slate-500 border-slate-200" : selected.published ? "bg-emerald-50 text-emerald-600 border-emerald-200" : "bg-amber-50 text-amber-600 border-amber-200"
                    )}>
                      {selected.status === "archived" ? "Archivado" : selected.published ? "✓ Publicado" : "⏳ Pendiente"}
                    </span>
                  </div>
                );
              })()}

              {/* Full content */}
              <div className="p-3 flex-1 space-y-4">
                <div className="space-y-2">
                  <p className="text-[9px] font-semibold text-slate-400 uppercase tracking-wide">Contenido completo</p>
                  <textarea
                    value={selected.content}
                    onChange={event => setSelected(prev => prev ? { ...prev, content: event.target.value } : prev)}
                    rows={5}
                    className="w-full resize-none text-sm text-slate-700 dark:text-slate-200 leading-relaxed bg-white dark:bg-white/5 rounded-lg p-4 border border-slate-200 dark:border-white/10 outline-none focus:ring-2 focus:ring-rose-500/20"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: "text", label: "Texto", icon: MessageCircle },
                    { id: "image", label: "Imagen", icon: ImageIcon },
                    { id: "video", label: "Video", icon: PlayCircle },
                    { id: "podcast", label: "Podcast", icon: Headphones },
                  ].map(option => (
                    <button
                      key={option.id}
                      onClick={() => changeSelectedMediaType(option.id as TestimonialMediaType)}
                      className={clsx(
                        "flex items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-[9px] font-semibold uppercase tracking-wide transition-all",
                        (selected.media_type || "text") === option.id
                          ? "border-rose-300 bg-rose-50 text-rose-600"
                          : "border-slate-200 dark:border-white/10 text-slate-400 hover:text-slate-700"
                      )}
                    >
                      <option.icon size={12} /> {option.label}
                    </button>
                  ))}
                </div>

                {(selected.media_type || "text") !== "text" && (
                  <div className="space-y-2">
                    <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-3">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <p className="text-[9px] font-semibold text-slate-400 uppercase tracking-wide">Seleccionar desde media</p>
                        <Link href="/cms/media" className="text-[9px] font-semibold uppercase tracking-wide text-rose-500 hover:underline">
                          Subir archivo
                        </Link>
                      </div>
                      <input
                        value={mediaSearch}
                        onChange={event => setMediaSearch(event.target.value)}
                        placeholder="Buscar imagen, video o audio..."
                        className="mb-3 w-full text-xs bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-md px-3 py-2 outline-none focus:ring-2 focus:ring-rose-500/20"
                      />
                      {mediaLoading ? (
                        <p className="rounded-md bg-slate-50 dark:bg-white/5 px-3 py-3 text-xs font-bold text-slate-400">Cargando biblioteca...</p>
                      ) : compatibleMedia.length === 0 ? (
                        <p className="rounded-md bg-slate-50 dark:bg-white/5 px-3 py-3 text-xs font-medium text-slate-500">
                          No hay archivos compatibles para este tipo. Sube o restaura media desde la biblioteca.
                        </p>
                      ) : (
                        <div className="grid grid-cols-2 gap-2 max-h-44 overflow-y-auto pr-1">
                          {compatibleMedia.map(item => {
                            const active = getTestimonialMediaUrl(selected) === item.url;
                            const mediaKind = inferTestimonialMediaType(item.mime_type);
                            return (
                              <button
                                key={item.id}
                                type="button"
                                onClick={() => assignMediaToSelected(item)}
                                className={clsx(
                                  "flex items-center gap-2 rounded-md border px-3 py-2 text-left transition-all",
                                  active
                                    ? "border-rose-300 bg-rose-50 text-rose-600"
                                    : "border-slate-200 dark:border-white/10 text-slate-500 hover:border-rose-300"
                                )}
                              >
                                {mediaKind === "image" ? <ImageIcon size={13} /> : mediaKind === "video" ? <PlayCircle size={13} /> : <Headphones size={13} />}
                                <span className="min-w-0 truncate text-[10px] font-bold">{item.filename || item.url}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    <p className="text-[9px] font-semibold text-slate-400 uppercase tracking-wide">URL multimedia</p>
                    <input
                      value={getTestimonialMediaUrl(selected)}
                      onChange={event => {
                        const value = event.target.value;
                        setSelected(prev => {
                          if (!prev) return prev;
                          if (prev.media_type === "image") return { ...prev, image_url: value, media_url: value };
                          if (prev.media_type === "video") return { ...prev, video_url: value, media_url: value };
                          if (prev.media_type === "podcast") return { ...prev, podcast_url: value, media_url: value };
                          return { ...prev, media_url: value };
                        });
                      }}
                      placeholder="Pega URL desde /cms/media"
                      className="w-full text-xs bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md px-3 py-2 outline-none focus:ring-2 focus:ring-rose-500/20"
                    />
                    {getTestimonialMediaUrl(selected) && (
                      <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 overflow-hidden">
                        {selected.media_type === "image" ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={getTestimonialMediaUrl(selected)} alt="" className="w-full max-h-48 object-cover" />
                        ) : selected.media_type === "video" ? (
                          <video controls className="w-full max-h-48 bg-black">
                            <source src={getTestimonialMediaUrl(selected)} />
                          </video>
                        ) : (
                          <div className="p-4">
                            <audio controls src={getTestimonialMediaUrl(selected)} className="w-full" />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <label className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Mostrar en inicio</span>
                  <input
                    type="checkbox"
                    checked={!!selected.show_on_home}
                    onChange={event => setSelected(prev => prev ? { ...prev, show_on_home: event.target.checked } : prev)}
                    className="size-4"
                  />
                </label>

                <div className="space-y-2">
                  <p className="text-[9px] font-semibold text-slate-400 uppercase tracking-wide">Categoria / emocion</p>
                  <input
                    value={selected.emotion || ""}
                    onChange={event => setSelected(prev => prev ? { ...prev, emotion: event.target.value } : prev)}
                    className="w-full text-xs bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md px-3 py-2 outline-none focus:ring-2 focus:ring-rose-500/20"
                  />
                </div>

                <div className="flex items-center justify-between text-[10px] font-bold text-slate-400">
                  <span className="flex items-center gap-1">
                    <Clock size={11} />
                    {new Date(selected.created_at).toLocaleString("es-CO", { dateStyle: "long", timeStyle: "short" })}
                  </span>
                  <span className="flex items-center gap-1">
                    <Heart size={11} />
                    {selected.emotion}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="p-3 border-t border-slate-200 dark:border-white/5 space-y-3 shrink-0">
                <button
                  onClick={saveSelected}
                  disabled={processing === selected.id}
                  className="flex items-center justify-center gap-2 w-full py-3 rounded-lg text-[11px] font-semibold uppercase tracking-wide bg-slate-900 text-white dark:bg-white dark:text-slate-900 transition-all active:scale-95 disabled:opacity-60"
                >
                  <Save size={16} /> Guardar cambios
                </button>
                <button
                  onClick={() => handleToggle(selected)}
                  disabled={processing === selected.id || selected.status === "archived"}
                  className={clsx(
                    "flex items-center justify-center gap-2 w-full py-3 rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg transition-all active:scale-95 disabled:opacity-60",
                    selected.published
                      ? "bg-rose-500 text-white shadow-rose-500/20 hover:bg-rose-600"
                      : "bg-emerald-600 text-white shadow-emerald-500/20 hover:bg-emerald-700"
                  )}
                >
                  {selected.published
                    ? <><XCircle size={16} /> Retirar del Sitio Web</>
                    : <><CheckCircle2 size={16} /> Aprobar y Publicar</>
                  }
                </button>
                <button
                  onClick={() => toggleArchive(selected)}
                  disabled={processing === selected.id}
                  className={clsx(
                    "flex items-center justify-center gap-2 w-full py-3 rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg transition-all active:scale-95 disabled:opacity-60",
                    selected.status === "archived"
                      ? "bg-emerald-600 text-white shadow-emerald-500/20 hover:bg-emerald-700"
                      : "bg-amber-500 text-white shadow-amber-500/20 hover:bg-amber-600"
                  )}
                >
                  {selected.status === "archived"
                    ? <><RotateCcw size={16} /> Restaurar a pendientes</>
                    : <><Archive size={16} /> Archivar testimonio</>
                  }
                </button>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>

      {/* ── DRAWER New testimonial form ── */}
      <WorkspaceDrawer
          isOpen={showForm}
          onClose={() => setShowForm(false)}
          title="Nuevo Testimonio"
          subtitle="Registrar experiencia"
      >
          <div className="mt-4">
              <TestimonialForm userId={(user as any)?.id ?? 0} token={token ?? ''} onSubmitted={() => { setShowForm(false); fetchTestimonials(); }} />
          </div>
      </WorkspaceDrawer>
    </div>
  );
}

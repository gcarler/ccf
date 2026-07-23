"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import OptimizedImage from "@/components/ui/OptimizedImage";
import {
  Archive,
  Copy,
  FileImage,
  FileText,
  Film,
  Loader2,
  Plus,
  Search,
  RotateCcw,
  Trash2,
  Upload,
  Check,
  Headphones,
  Zap,
} from "lucide-react"
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import clsx from "clsx";
import ViewSwitcher, { ViewType } from "@/components/ViewSwitcher";
import UniversalCalendarView from "@/components/ui/UniversalCalendarView";
import UniversalGanttView from "@/components/ui/UniversalGanttView";
import UniversalWikiView from "@/components/ui/UniversalWikiView";

interface MediaItem {
  id: number;
  url: string;
  filename: string;
  mime_type?: string;
  alt_text?: string;
  section?: string;
  tags?: string[];
  file_size?: number;
  width?: number;
  height?: number;
  status?: string;
  created_at?: string;
}

const MEDIA_VIEWS: ViewType[] = ["grid", "list", "table", "board", "kanban", "calendar", "gantt", "wiki"];
type FilterType = "all" | "image" | "video" | "audio" | "document";

const FILTER_OPTIONS: { id: FilterType; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "image", label: "Imágenes" },
  { id: "video", label: "Videos" },
  { id: "audio", label: "Audio/Podcast" },
  { id: "document", label: "Documentos" },
];

function formatBytes(bytes?: number): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileTypeIcon(mime?: string) {
  if (!mime) return FileText;
  if (mime.startsWith("image/")) return FileImage;
  if (mime.startsWith("video/")) return Film;
  if (mime.startsWith("audio/")) return Headphones;
  return FileText;
}

function isImage(mime?: string): boolean {
  return !!mime && mime.startsWith("image/");
}

function matchesFilter(item: MediaItem, filter: FilterType): boolean {
  if (filter === "all") return true;
  if (filter === "image") return isImage(item.mime_type);
  if (filter === "video") return !!item.mime_type?.startsWith("video/");
  if (filter === "audio") return !!item.mime_type?.startsWith("audio/");
  if (filter === "document") return !isImage(item.mime_type) && !item.mime_type?.startsWith("video/") && !item.mime_type?.startsWith("audio/");
  return true;
}

export default function CmsMediaLibrary() {
  const { token } = useAuth();
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterType>("all");
  const [viewType, setViewType] = useState<ViewType>("grid");
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [optimizingId, setOptimizingId] = useState<number | null>(null);
  const [_metadataSaving, setMetadataSaving] = useState(false);
  const [tagsText, setTagsText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchMedia = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    try {
      const data = await apiFetch<{ items: MediaItem[]; total: number }>("/cms/media", { token, cache: "no-store", query: { include_archived: true } });
      setItems(data?.items || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchMedia(); }, [fetchMedia]);

  useEffect(() => {
    setTagsText((selectedItem?.tags || []).join(", "));
  }, [selectedItem]);

  const uploadFiles = async (files: FileList | File[]) => {
    if (!token || !files.length) return;
    setUploading(true);
    const fileArray = Array.from(files);
    try {
      for (const file of fileArray) {
        const form = new FormData();
        form.append("file", file);
        form.append("alt_text", file.name);
        form.append("section", file.type.startsWith("audio/") ? "podcasts" : file.type.startsWith("video/") ? "videos" : file.type.startsWith("image/") ? "imagenes" : "general");
        form.append("tags", file.type.startsWith("audio/") ? "podcast,audio" : file.type.startsWith("video/") ? "video" : file.type.startsWith("image/") ? "imagen" : "documento");
        await apiFetch("/cms/media/upload", {
          method: "POST",
          token,
          body: form,
        });
      }
      await fetchMedia();
    } catch (err) {
      toast.error("Error al subir archivo");
    } finally {
      setUploading(false);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) uploadFiles(e.target.files);
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(false);
    if (e.dataTransfer.files) uploadFiles(e.dataTransfer.files);
  };

  const copyUrl = (item: MediaItem) => {
    navigator.clipboard.writeText(item.url);
    setCopiedId(item.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const _updateSelectedItem = (patch: Partial<MediaItem>) => {
    setSelectedItem(prev => prev ? { ...prev, ...patch } : prev);
  };

  const _saveMetadata = async () => {
    if (!token || !selectedItem) return;
    setMetadataSaving(true);
    const tags = tagsText.split(",").map(tag => tag.trim()).filter(Boolean);
    try {
      const updated = await apiFetch<MediaItem>(`/cms/media/${selectedItem.id}`, {
        method: "PATCH",
        token,
        body: {
          alt_text: selectedItem.alt_text || "",
          section: selectedItem.section || "general",
          tags,
          filename: selectedItem.filename,
        },
      });
      const normalized = { ...selectedItem, ...updated, tags };
      setSelectedItem(normalized);
      setItems(prev => prev.map(item => item.id === selectedItem.id ? normalized : item));
      setTagsText(tags.join(", "));
    } catch (err) {
      toast.error("Error al guardar metadatos");
    } finally {
      setMetadataSaving(false);
    }
  };

  const toggleArchiveItem = async (item: MediaItem) => {
    if (!token) return;
    setDeletingId(item.id);
    try {
      const nextStatus = item.status === "archived" ? "active" : "archived";
      const updated = item.status === "archived"
        ? await apiFetch<MediaItem>(`/cms/media/${item.id}`, { method: "PATCH", token, body: { status: nextStatus } })
        : await apiFetch<MediaItem | undefined>(`/cms/media/${item.id}`, { method: "DELETE", token }).then(() => ({ ...item, status: "archived" }));
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, ...updated, status: nextStatus } : i));
      if (selectedItem?.id === item.id) setSelectedItem(prev => prev ? { ...prev, ...updated, status: nextStatus } : prev);
    } catch (err) {
      toast.error("Error al archivar medio");
    } finally {
      setDeletingId(null);
    }
  };

  const deleteItem = async (item: MediaItem) => {
    if (!token || !confirm("¿Eliminar permanentemente este archivo? Esta acción no se puede deshacer.")) return;
    setDeletingId(item.id);
    try {
      await apiFetch(`/cms/media/${item.id}?permanent=true`, { method: "DELETE", token });
      setItems(prev => prev.filter(i => i.id !== item.id));
      if (selectedItem?.id === item.id) setSelectedItem(null);
      toast.success("Archivo eliminado permanentemente");
    } catch (err) {
      toast.error("Error al eliminar archivo");
    } finally {
      setDeletingId(null);
    }
  };

  const optimizeItem = async (item: MediaItem) => {
    if (!token) return;
    setOptimizingId(item.id);
    try {
      const updated = await apiFetch<MediaItem>(`/cms/media/${item.id}/optimize`, { method: "POST", token });
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, ...updated } : i));
      if (selectedItem?.id === item.id) setSelectedItem(prev => prev ? { ...prev, ...updated } : prev);
      toast.success("Imagen optimizada para web");
    } catch (err) {
      toast.error("Error al optimizar imagen");
    } finally {
      setOptimizingId(null);
    }
  };

  const filtered = items.filter(item => {
    const matchSearch = !search || item.filename?.toLowerCase().includes(search.toLowerCase()) || item.alt_text?.toLowerCase().includes(search.toLowerCase());
    return matchSearch && matchesFilter(item, filter);
  });

  const mediaGroups = FILTER_OPTIONS.slice(1).map(group => ({
    ...group,
    items: filtered.filter(item => matchesFilter(item, group.id)),
  }));

  const calendarEvents = filtered.map(item => ({
    id: item.id,
    title: item.filename || "Archivo",
    date: (item.created_at || new Date().toISOString()).split("T")[0],
    color: isImage(item.mime_type) ? "blue" as const : item.mime_type?.startsWith("video/") ? "rose" as const : "amber" as const,
    location: item.mime_type || "Archivo",
  }));

  const ganttItems = filtered.map(item => {
    const date = item.created_at || new Date().toISOString();
    return {
      id: item.id,
      title: item.filename || "Archivo",
      subtitle: `${item.mime_type || "Sin tipo"} · ${formatBytes(item.file_size)}`,
      start_date: date,
      end_date: date,
      color: isImage(item.mime_type) ? "blue" as const : item.mime_type?.startsWith("video/") ? "rose" as const : "amber" as const,
      progress: 100,
    };
  });

  const renderMediaTable = () => (
    <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto">
      <table className="w-full text-left min-w-[480px]">
        <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
          <tr>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Archivo</th>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Tipo</th>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden lg:table-cell">TamaÃ±o</th>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden xl:table-cell">Subido</th>
            <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Acciones</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
          {filtered.map(item => {
            const FileIcon = getFileTypeIcon(item.mime_type);
            return (
              <tr key={item.id} onClick={() => setSelectedItem(item)} className={clsx("hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] cursor-pointer", item.status === "archived" && "opacity-70 bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning)/0.05)]")}>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="size-9 rounded-md overflow-hidden bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                      {isImage(item.mime_type) ? <OptimizedImage src={item.url} alt="" width={36} height={36} className="w-full h-full object-cover" /> : <FileIcon size={16} className="text-[hsl(var(--text-secondary))]" />}
                    </div>
                    <span className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate max-w-[260px]">{item.filename || "Archivo"}</span>
                    {item.status === "archived" && <span className="rounded-full bg-[hsl(var(--warning-muted))] px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--warning))]">Archivado</span>}
                  </div>
                </td>
                <td className="px-4 py-3 hidden md:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{item.mime_type || "—"}</td>
                <td className="px-4 py-3 hidden lg:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{formatBytes(item.file_size)}</td>
                <td className="px-4 py-3 hidden xl:table-cell text-[11px] text-[hsl(var(--text-secondary))]">{item.created_at ? new Date(item.created_at).toLocaleDateString() : "—"}</td>
                <td className="px-4 py-3">
                  <button onClick={e => { e.stopPropagation(); copyUrl(item); }} className="p-2 rounded-md hover:bg-[hsl(var(--info-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))]">
                    {copiedId === item.id ? <Check size={14} /> : <Copy size={14} />}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  const renderMediaBoard = () => (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-full">
      {mediaGroups.map(group => (
        <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-4">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{group.label}</span>
            <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))]">{group.items.length}</span>
          </div>
          <div className="space-y-3">
            {group.items.map(item => {
              const FileIcon = getFileTypeIcon(item.mime_type);
              return (
                <button key={item.id} onClick={() => setSelectedItem(item)} className={clsx("w-full text-left bg-[hsl(var(--bg-primary))] dark:bg-white/[0.04] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 hover:border-[hsl(var(--primary)/0.4)] transition-all flex items-center gap-3", item.status === "archived" && "opacity-70 border-[hsl(var(--warning)/0.2)] bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning)/0.05)]")}>
                  <div className="size-10 rounded-md overflow-hidden bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center shrink-0">
                    {isImage(item.mime_type) ? <OptimizedImage src={item.url} alt="" width={36} height={36} className="w-full h-full object-cover" /> : <FileIcon size={18} className="text-[hsl(var(--text-secondary))]" />}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white truncate">{item.filename || "Archivo"}</p>
                    {item.status === "archived" && <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--warning))]">Archivado</p>}
                    <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-1">{formatBytes(item.file_size)}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );

  return (
    <div
      className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-deep))] overflow-hidden"
      onDragOver={(e) => { e.preventDefault(); setIsDraggingOver(true); }}
      onDragLeave={() => setIsDraggingOver(false)}
      onDrop={handleDrop}
    >
      {/* ── Drag overlay ── */}
      <AnimatePresence>
        {isDraggingOver && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-[hsl(var(--primary))/0.2] backdrop-blur-sm flex flex-col items-center justify-center pointer-events-none border-4 border-dashed border-[hsl(var(--primary))] rounded-lg m-4"
          >
            <Upload size={64} className="text-[hsl(var(--primary))] mb-4" strokeWidth={1} />
            <p className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] font-semibold text-xl uppercase tracking-wide">
              Suelta para subir
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Toolbar ── */}
      <header className="shrink-0 border-b border-[hsl(var(--border))] dark:border-white/5 px-3 py-1.5 flex items-center gap-4">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <FileImage size={18} className="text-[hsl(var(--primary))] shrink-0" />
          <h1 className="text-[13px] font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white truncate">
            Biblioteca de Medios
          </h1>
          <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full shrink-0">
            {filtered.length} archivos
          </span>
        </div>

        {/* Search */}
        <div className="relative w-60 shrink-0">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar archivos..."
            className="w-full pl-9 pr-4 py-2 rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 font-medium"
          />
        </div>

        <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={MEDIA_VIEWS} />

        {/* Upload button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-60 shrink-0"
        >
          {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          {uploading ? "Subiendo..." : "Subir Archivos"}
        </button>
        <input ref={fileInputRef} type="file" multiple accept="image/*,video/*,audio/*,.pdf,.doc,.docx" className="hidden" onChange={handleFileInput} />
      </header>

      {/* ── Filter bar ── */}
      <div className="shrink-0 px-3 py-3 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center gap-2">
        {FILTER_OPTIONS.map(opt => (
          <button
            key={opt.id}
            onClick={() => setFilter(opt.id)}
            className={clsx(
              "px-4 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all",
              filter === opt.id
                ? "bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20"
                : "bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10"
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* ── Main content ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Media grid/list */}
        <div className="flex-1 overflow-y-auto p-3">
          {loading ? (
            <div className={clsx("gap-4", viewType === "grid" ? "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6" : "space-y-2")}>
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className={clsx("animate-pulse bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-lg", viewType === "grid" ? "aspect-square" : "h-8")} />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-3 py-1.5">
              <div className="size-10 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center">
                <FileImage size={40} strokeWidth={1} className="text-[hsl(var(--text-secondary))]" />
              </div>
              <div className="space-y-2">
                <p className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">
                  {search ? "Sin resultados" : "Biblioteca vacía"}
                </p>
                <p className="text-sm text-[hsl(var(--text-secondary))] font-medium">
                  {search ? "Intenta con otros términos" : "Arrastra archivos aquí o haz clic en «Subir Archivos»"}
                </p>
              </div>
              {!search && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-2 px-3 py-3 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] transition-all"
                >
                  <Plus size={16} /> Subir primer archivo
                </button>
              )}
            </div>
          ) : viewType === "grid" ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {filtered.map(item => {
                const FileIcon = getFileTypeIcon(item.mime_type);
                return (
                  <motion.div
                    key={item.id}
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    onClick={() => setSelectedItem(item)}
                    className={clsx(
                      "group relative aspect-square rounded-lg border overflow-hidden cursor-pointer transition-all",
                      item.status === "archived" && "opacity-70 bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning)/0.05)]",
                      selectedItem?.id === item.id
                        ? "border-[hsl(var(--primary))] ring-2 ring-[hsl(var(--primary))/0.3]"
                        : "border-[hsl(var(--border))] dark:border-white/10 hover:border-[hsl(var(--primary)/0.4)] hover:shadow-lg"
                    )}
                  >
                    {isImage(item.mime_type) ? (
                      <OptimizedImage src={item.url} alt="" width={40} height={40} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-[hsl(var(--surface-1))] dark:bg-white/5 flex flex-col items-center justify-center gap-2">
                        <FileIcon size={32} strokeWidth={1} className="text-[hsl(var(--text-secondary))]" />
                        <p className="text-[9px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-center px-2 line-clamp-2">{item.filename}</p>
                      </div>
                    )}

                    {/* Hover overlay */}
                    {item.status === "archived" && (
                      <span className="absolute left-2 top-2 rounded-full bg-[hsl(var(--warning-muted))] px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--warning))]">
                        Archivado
                      </span>
                    )}
                    <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-all flex flex-col items-center justify-center gap-2 p-2">
                      <button
                        onClick={e => { e.stopPropagation(); copyUrl(item); }}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--bg-primary))] rounded-lg text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--info-muted))] transition-all w-full justify-center"
                      >
                        {copiedId === item.id ? <Check size={10} className="text-[hsl(var(--success))]" /> : <Copy size={10} />}
                        {copiedId === item.id ? "¡Copiado!" : "Copiar URL"}
                      </button>
                      {isImage(item.mime_type) && item.status !== "archived" && (
                        <button
                          onClick={e => { e.stopPropagation(); optimizeItem(item); }}
                          disabled={optimizingId === item.id}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-[9px] font-semibold uppercase tracking-wide text-white transition-all w-full justify-center disabled:opacity-60"
                        >
                          {optimizingId === item.id ? <Loader2 size={10} className="animate-spin" /> : <Zap size={10} />}
                          Optimizar
                        </button>
                      )}
                      <button
                        onClick={e => { e.stopPropagation(); toggleArchiveItem(item); }}
                        disabled={deletingId === item.id}
                        className={clsx(
                          "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-semibold uppercase tracking-wide text-white transition-all w-full justify-center disabled:opacity-60",
                          item.status === "archived" ? "bg-[hsl(var(--success))] hover:bg-[hsl(var(--success))]" : "bg-[hsl(var(--warning))] hover:bg-[hsl(var(--warning))]"
                        )}
                      >
                        {deletingId === item.id ? <Loader2 size={10} className="animate-spin" /> : item.status === "archived" ? <RotateCcw size={10} /> : <Archive size={10} />}
                        {item.status === "archived" ? "Restaurar" : "Archivar"}
                      </button>
                      <button
                        onClick={e => { e.stopPropagation(); deleteItem(item); }}
                        disabled={deletingId === item.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive))] rounded-lg text-[9px] font-semibold uppercase tracking-wide text-white transition-all w-full justify-center disabled:opacity-60"
                      >
                        {deletingId === item.id ? <Loader2 size={10} className="animate-spin" /> : <Trash2 size={10} />}
                        Eliminar
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          ) : viewType === "table" ? (
            renderMediaTable()
          ) : viewType === "board" || viewType === "kanban" ? (
            renderMediaBoard()
          ) : viewType === "calendar" ? (
            <UniversalCalendarView
              title="Calendario de medios"
              events={calendarEvents}
              onEventClick={(event) => {
                const item = filtered.find(entry => entry.id === event.id);
                if (item) setSelectedItem(item);
              }}
            />
          ) : viewType === "gantt" ? (
            <UniversalGanttView
              moduleName="Media CMS"
              items={ganttItems}
              onItemClick={(item) => {
                const media = filtered.find(entry => entry.id === item.id);
                if (media) setSelectedItem(media);
              }}
            />
          ) : viewType === "wiki" ? (
            <UniversalWikiView moduleName="Media CMS" storageKey="cms-media-wiki" />
          ) : (
            /* List view */
            <div className="space-y-2">
              {filtered.map(item => {
                const FileIcon = getFileTypeIcon(item.mime_type);
                return (
                  <motion.div
                    key={item.id}
                    layout
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    onClick={() => setSelectedItem(item)}
                    className={clsx(
                      "group flex items-center gap-4 p-3 rounded-lg border cursor-pointer transition-all",
                      item.status === "archived" && "opacity-70 border-[hsl(var(--warning)/0.2)] bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning)/0.05)]",
                      selectedItem?.id === item.id
                        ? "border-[hsl(var(--primary))] bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--primary)/0.1)]"
                        : "border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/[0.02] hover:border-blue-300 dark:hover:border-blue-700"
                    )}
                  >
                    <div className="size-10 rounded-md overflow-hidden flex-shrink-0 bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center">
                      {isImage(item.mime_type) ? (
                        <OptimizedImage src={item.url} alt={item.alt_text || item.filename || ""} width={40} height={40} className="w-full h-full object-cover" />
                      ) : (
                        <FileIcon size={18} className="text-[hsl(var(--text-secondary))]" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{item.filename || "Archivo"}</p>
                        {item.status === "archived" && (
                          <span className="rounded-full bg-[hsl(var(--warning-muted))] px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--warning))]">Archivado</span>
                        )}
                      </div>
                      <p className="text-[11px] text-[hsl(var(--text-secondary))] truncate">{item.mime_type || "Sin tipo"} · {formatBytes(item.file_size)}</p>
                    </div>
                    <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={e => { e.stopPropagation(); copyUrl(item); }}
                        className="p-2 rounded-md hover:bg-[hsl(var(--info-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
                        aria-label="Copiar URL"
                      >
                        {copiedId === item.id ? <Check size={14} /> : <Copy size={14} />}
                      </button>
                      {isImage(item.mime_type) && item.status !== "archived" && (
                        <button
                          onClick={e => { e.stopPropagation(); optimizeItem(item); }}
                          disabled={optimizingId === item.id}
                          className="p-2 rounded-md hover:bg-[hsl(var(--info-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors disabled:opacity-60"
                          aria-label="Optimizar"
                        >
                          {optimizingId === item.id ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                        </button>
                      )}
                      <button
                        onClick={e => { e.stopPropagation(); toggleArchiveItem(item); }}
                        disabled={deletingId === item.id}
                        className="p-2 rounded-md hover:bg-[hsl(var(--warning-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--warning))] transition-colors disabled:opacity-60"
                        aria-label={item.status === "archived" ? "Restaurar" : "Archivar"}
                      >
                        {deletingId === item.id ? <Loader2 size={14} className="animate-spin" /> : item.status === "archived" ? <RotateCcw size={14} /> : <Archive size={14} />}
                      </button>
                      <button
                        onClick={e => { e.stopPropagation(); deleteItem(item); }}
                        disabled={deletingId === item.id}
                        className="p-2 rounded-md hover:bg-[hsl(var(--destructive)/0.08)] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] transition-colors disabled:opacity-60"
                        aria-label="Eliminar"
                      >
                        {deletingId === item.id ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

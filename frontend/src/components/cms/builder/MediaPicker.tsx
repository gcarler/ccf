"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Check,
  FileImage,
  ImageIcon,
  Search,
  Upload,
  X,
} from "lucide-react";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { apiFetch } from "@/lib/http";

// ── Types ───────────────────────────────────────────────────────────────────

interface CmsMediaItem {
  id: number;
  url: string;
  filename?: string | null;
  mime_type?: string | null;
  alt_text?: string | null;
  section?: string;
  tags?: string[];
  created_at?: string;
}

interface MediaPickerProps {
  open: boolean;
  token?: string | null;
  selectedUrl?: string;
  onClose: () => void;
  onSelect: (item: CmsMediaItem) => void;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function MediaPicker({
  open,
  token,
  selectedUrl,
  onClose,
  onSelect,
}: MediaPickerProps) {
  const [items, setItems] = useState<CmsMediaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open || !token) return;
    setLoading(true);
    apiFetch<{ items: CmsMediaItem[]; total: number }>("/cms/media", {
      token,
      cache: "no-store",
    })
      .then((data) => setItems(data?.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [open, token]);

  const uploadImage = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !token) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("section", "builder");
      form.append("alt_text", file.name);
      form.append("tags", "builder,imagen");
      const created = await apiFetch<CmsMediaItem>("/cms/media/upload", {
        method: "POST",
        token,
        body: form,
      });
      setItems((prev) => [created, ...prev]);
      onSelect(created);
    } finally {
      setUploading(false);
    }
  };

  const imageItems = useMemo(
    () =>
      items.filter((item) => {
        const mime = item.mime_type || "";
        return (
          mime.startsWith("image/") ||
          /\.(png|jpe?g|webp|gif|svg)$/i.test(item.url)
        );
      }),
    [items]
  );

  const normalizedSearch = search.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      imageItems.filter((item) => {
        if (!normalizedSearch) return true;
        return [item.filename, item.alt_text, item.url, item.section]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(normalizedSearch));
      }),
    [imageItems, normalizedSearch]
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-950/50 backdrop-blur-sm p-4 flex items-center justify-center"
      onClick={onClose}
    >
      <div
        className="w-full max-w-5xl max-h-[86vh] overflow-hidden rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-[#111418] border border-slate-200 dark:border-white/10 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/10 px-3 py-1.5">
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-md bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-blue-300 flex items-center justify-center">
              <ImageIcon size={18} />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Biblioteca CMS
              </p>
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                Seleccionar imagen
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-md text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex items-center gap-3 border-b border-slate-200 dark:border-white/10 px-3 py-3">
          <div className="relative flex-1">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por archivo, alt text o seccion"
              className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-transparent py-2 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
            />
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-white disabled:opacity-50">
            <Upload size={14} />
            {uploading ? "Subiendo..." : "Subir imagen"}
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={uploadImage}
              disabled={uploading}
            />
          </label>
        </div>

        <div className="max-h-[62vh] overflow-y-auto p-3">
          {loading ? (
            <div className="py-1.5 text-center text-sm font-bold text-slate-400">
              Cargando biblioteca...
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-1.5 text-center">
              <FileImage size={34} className="mx-auto text-slate-300" />
              <p className="mt-3 text-sm font-bold text-slate-500">
                No hay imagenes disponibles.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
              {filtered.map((item) => {
                const isSelected = selectedUrl === item.url;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelect(item)}
                    className={`group text-left rounded-lg border overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-white/[0.03] transition-all ${isSelected ? "border-blue-500 ring-2 ring-blue-500/20" : "border-slate-200 dark:border-white/10 hover:border-blue-300"}`}
                  >
                    <div className="relative aspect-video bg-slate-100 dark:bg-white/5">
                      <OptimizedImage
                        src={item.url}
                        alt={item.alt_text || item.filename || ""}
                        fill
                        sizes="200px"
                        className="h-full w-full object-cover"
                      />
                      {isSelected && (
                        <span className="absolute right-2 top-2 size-7 rounded-full bg-[hsl(var(--primary))] text-white flex items-center justify-center shadow-lg">
                          <Check size={15} />
                        </span>
                      )}
                    </div>
                    <div className="p-3">
                      <p className="truncate text-xs font-semibold text-slate-800 dark:text-slate-100">
                        {item.filename || "Imagen CMS"}
                      </p>
                      <p className="mt-1 truncate text-[10px] text-slate-400">
                        {item.alt_text || item.section || "Sin alt text"}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

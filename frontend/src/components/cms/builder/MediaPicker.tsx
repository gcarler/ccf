"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Check,
  FileImage,
  Search,
  Upload,
} from "lucide-react";
import clsx from "clsx";
import SidePanel from "@/components/ui/SidePanel";
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
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open || !token) return;
    setLoading(true);
    apiFetch<{ items: CmsMediaItem[]; total: number }>("/cms/media", {
      token,
      cache: "no-store",
      query: { skip: 0, limit: 500 },
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
      items.filter((item: any) => {
        const mime = item.mime_type || item.mimetype || "";
        return (
          mime.startsWith("image/") ||
          /\.(png|jpe?g|webp|gif|svg)$/i.test(item.url || "")
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

  if (!mounted) return null;

  return (
    <SidePanel
      isOpen={open}
      onClose={onClose}
      title="Biblioteca CMS"
      subtitle="Seleccionar imagen"
      width="w-full max-w-3xl"
    >
      <div data-testid="media-picker" className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]"
            />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por archivo, alt text o sección"
              className="w-full rounded-md border border-[hsl(var(--border))] bg-transparent py-2 pl-9 pr-3 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] outline-none focus:border-[hsl(var(--primary))]"
            />
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity disabled:opacity-50">
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

        <div>
          {loading ? (
            <div className="py-12 text-center text-sm font-semibold text-[hsl(var(--muted-foreground))]">
              Cargando biblioteca...
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center">
              <FileImage size={34} className="mx-auto text-[hsl(var(--muted-foreground))]" />
              <p className="mt-3 text-sm font-semibold text-[hsl(var(--muted-foreground))]">
                No hay imágenes disponibles.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {filtered.map((item) => {
                const isSelected = selectedUrl === item.url;
                return (
                  <button
                    key={item.id}
                    type="button"
                    data-testid="media-item-button"
                    aria-pressed={isSelected}
                    onClick={() => onSelect(item)}
                    className={clsx(
                      "group text-left rounded-lg border overflow-hidden bg-[hsl(var(--surface-1))] transition-all",
                      isSelected
                        ? "border-[hsl(var(--primary))] ring-2 ring-[hsl(var(--primary))]/20"
                        : "border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]/40"
                    )}
                  >
                    <div className="relative aspect-video bg-[hsl(var(--surface-2))]">
                      <OptimizedImage
                        src={item.url}
                        alt={item.alt_text || item.filename || ""}
                        fill
                        sizes="200px"
                        className="h-full w-full object-cover"
                      />
                      {isSelected && (
                        <span className="absolute right-2 top-2 size-7 rounded-full bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center justify-center shadow-lg">
                          <Check size={15} />
                        </span>
                      )}
                    </div>
                    <div className="p-3">
                      <p className="truncate text-xs font-semibold text-[hsl(var(--foreground))]">
                        {item.filename || "Imagen CMS"}
                      </p>
                      <p className="mt-1 truncate text-2xs text-[hsl(var(--muted-foreground))]">
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
    </SidePanel>
  );
}

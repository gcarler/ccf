"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import AdminHero from "@/components/admin/AdminHero";
import { Image as ImageIcon, Plus, Save, Search, Trash2, Upload } from "lucide-react";

interface MediaItem {
  id: number;
  url: string;
  alt_text?: string;
  section: string;
  tags: string[];
}

interface DraftItem {
  id?: number;
  url: string;
  alt_text: string;
  section: string;
  tags: string;
}

const EMPTY_ITEM: DraftItem = { url: "", alt_text: "", section: "general", tags: "" };

export default function CmsMediaPage() {
  const { token, isAuthenticated } = useAuth();
  const [items, setItems] = useState<MediaItem[]>([]);
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [query, setQuery] = useState("");
  const [sectionFilter, setSectionFilter] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    if (!token) return;
    setLoading(true);
    setMessage(null);
    try {
      const data = await apiFetch<MediaItem[]>("/cms/media", {
        token,
        cache: "no-store",
        query: {
          query: query || undefined,
          section: sectionFilter || undefined
        }
      });
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setItems([]);
      setMessage("No se pudo cargar la biblioteca.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, query, sectionFilter]);

  const saveDrafts = async () => {
    if (!token || drafts.length === 0) return;
    setSaving(true);
    setMessage(null);
    try {
      for (const draft of drafts) {
        const payload = {
          url: draft.url,
          alt_text: draft.alt_text || null,
          section: draft.section || "general",
          tags: draft.tags.split(",").map((tag) => tag.trim()).filter(Boolean)
        };
        if (draft.id) {
          await apiFetch(`/cms/media/${draft.id}`, { method: "PATCH", token, body: payload });
        } else {
          await apiFetch(`/cms/media`, { method: "POST", token, body: payload });
        }
      }
      setDrafts([]);
      setMessage("Biblioteca actualizada.");
      await load();
    } catch {
      setMessage("No se pudo guardar la biblioteca.");
    } finally {
      setSaving(false);
    }
  };

  const totalBySection = useMemo(() => {
    const acc: Record<string, number> = {};
    for (const item of items) {
      acc[item.section] = (acc[item.section] || 0) + 1;
    }
    return acc;
  }, [items]);

  const pushItemToDraft = (item?: MediaItem) => {
    setDrafts((prev) => [
      ...prev,
      item
        ? {
            id: item.id,
            url: item.url,
            alt_text: item.alt_text || "",
            section: item.section,
            tags: (item.tags || []).join(", ")
          }
        : { ...EMPTY_ITEM }
    ]);
  };

  const uploadFile = async (file: File) => {
    if (!token) return;
    const form = new FormData();
    form.append("file", file);
    setUploading(true);
    setMessage(null);
    try {
      await apiFetch("/cms/media/upload?section=general", {
        method: "POST",
        token,
        body: form
      });
      setMessage("Archivo subido y agregado a biblioteca.");
      await load();
    } catch {
      setMessage("No se pudo subir el archivo.");
    } finally {
      setUploading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-3xl mx-auto py-24 text-center space-y-3">
        <h1 className="text-3xl font-black">Inicia sesion</h1>
        <p className="text-slate-500">Necesitas una sesion valida para administrar media.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 px-4 py-8">
      <AdminHero
        eyebrow="CMS"
        title="Media manager"
        description="Biblioteca con filtros, metadatos, etiquetas y subida de archivos para contenido FARO."
        tags={["Media", "Assets", "FARO"]}
        watchers={["Comunicaciones", "Diseno"]}
        primaryAction={{ label: saving ? "Guardando..." : "Guardar cambios", icon: Save, onClick: saveDrafts }}
      />

      <section className="rounded-[2rem] border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <label className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar por URL o alt"
              className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent pl-10 pr-3 py-2 text-sm outline-none"
            />
          </label>
          <input
            value={sectionFilter}
            onChange={(event) => setSectionFilter(event.target.value)}
            placeholder="Filtrar por seccion"
            className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none"
          />
          <label className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-white/10 px-3 py-2 text-xs font-black uppercase tracking-[0.2em] cursor-pointer">
            <Upload size={14} />
            {uploading ? "Subiendo" : "Subir archivo"}
            <input
              type="file"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) uploadFile(file);
              }}
            />
          </label>
        </div>

        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">Activos: {items.length}</p>
          <button
            onClick={() => pushItemToDraft()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 text-xs font-black uppercase tracking-[0.2em]"
          >
            <Plus size={14} />
            Nuevo item
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {Object.entries(totalBySection).map(([section, count]) => (
            <span key={section} className="text-[10px] uppercase tracking-[0.2em] px-2 py-1 rounded-full border border-slate-200 text-slate-500">
              {section}: {count}
            </span>
          ))}
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Cargando biblioteca...</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {items.map((item) => (
              <div key={item.id} className="rounded-2xl border border-slate-100 dark:border-white/10 p-4 space-y-2">
                <p className="text-xs font-black uppercase tracking-[0.2em] text-primary">{item.section}</p>
                <p className="text-xs text-slate-500 break-all">{item.url}</p>
                <p className="text-sm text-slate-700 dark:text-slate-300">{item.alt_text || "Sin alt"}</p>
                <p className="text-[10px] text-slate-400">{(item.tags || []).join(", ") || "Sin tags"}</p>
                <div className="flex items-center justify-between">
                  <button onClick={() => pushItemToDraft(item)} className="text-xs font-black uppercase tracking-[0.2em] text-primary">
                    Editar
                  </button>
                  <button
                    onClick={async () => {
                      if (!token) return;
                      await apiFetch(`/cms/media/${item.id}`, { method: "DELETE", token });
                      await load();
                    }}
                    className="inline-flex items-center gap-1 text-xs font-black uppercase tracking-[0.2em] text-rose-500"
                  >
                    <Trash2 size={12} /> Eliminar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {drafts.length > 0 && (
          <div className="space-y-3 rounded-2xl border border-dashed border-slate-200 dark:border-white/10 p-4">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Pendientes por guardar</p>
            {drafts.map((draft, index) => (
              <div key={`${draft.id || "new"}-${index}`} className="grid grid-cols-1 md:grid-cols-4 gap-2">
                <input
                  value={draft.url}
                  onChange={(event) => setDrafts((prev) => prev.map((row, i) => (i === index ? { ...row, url: event.target.value } : row)))}
                  placeholder="https://..."
                  className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
                <input
                  value={draft.alt_text}
                  onChange={(event) => setDrafts((prev) => prev.map((row, i) => (i === index ? { ...row, alt_text: event.target.value } : row)))}
                  placeholder="Texto alternativo"
                  className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
                <input
                  value={draft.section}
                  onChange={(event) => setDrafts((prev) => prev.map((row, i) => (i === index ? { ...row, section: event.target.value } : row)))}
                  placeholder="Seccion"
                  className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
                <input
                  value={draft.tags}
                  onChange={(event) => setDrafts((prev) => prev.map((row, i) => (i === index ? { ...row, tags: event.target.value } : row)))}
                  placeholder="tag1, tag2"
                  className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
              </div>
            ))}
          </div>
        )}

        {message && (
          <p className="text-sm text-slate-500 flex items-center gap-2">
            <ImageIcon size={14} /> {message}
          </p>
        )}
      </section>
    </div>
  );
}

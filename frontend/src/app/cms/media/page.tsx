"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import AdminHero from "@/components/admin/AdminHero";
import { FARO_MEDIA_BLOCK_KEY } from "@/lib/cms/blocks";
import { Image as ImageIcon, Plus, Save, Trash2 } from "lucide-react";

interface MediaItem {
  url: string;
  alt: string;
  section: string;
}

interface ContentRecord {
  content?: string;
}

const EMPTY_ITEM: MediaItem = { url: "", alt: "", section: "general" };

export default function CmsMediaPage() {
  const { token, isAuthenticated } = useAuth();
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    const load = async () => {
      setLoading(true);
      setMessage(null);
      try {
        const data = await apiFetch<ContentRecord>(`/content/${FARO_MEDIA_BLOCK_KEY}`, { token, cache: "no-store" });
        const parsed = data?.content ? JSON.parse(data.content) : [];
        setItems(Array.isArray(parsed) ? parsed : []);
      } catch {
        setItems([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [token]);

  const save = async () => {
    if (!token) return;
    setSaving(true);
    setMessage(null);
    const payload = { content: JSON.stringify(items, null, 2) };
    try {
      try {
        await apiFetch(`/content/${FARO_MEDIA_BLOCK_KEY}`, { method: "PUT", token, body: payload });
      } catch {
        await apiFetch(`/content/${FARO_MEDIA_BLOCK_KEY}`, { method: "POST", token, body: payload });
      }
      setMessage("Galeria guardada.");
    } catch {
      setMessage("No se pudo guardar la galeria.");
    } finally {
      setSaving(false);
    }
  };

  const totalValid = useMemo(() => items.filter((item) => item.url.trim()).length, [items]);

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
        title="Biblioteca visual"
        description="Gestiona imagenes reutilizables por seccion. Este modulo trabaja con URLs publicas."
        tags={["Media", "Galeria", "FARO"]}
        watchers={["Comunicaciones", "Diseno"]}
        primaryAction={{ label: saving ? "Guardando..." : "Guardar galeria", icon: Save, onClick: save }}
      />

      <section className="rounded-[2rem] border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Items activos</p>
            <p className="text-3xl font-black mt-1">{totalValid}</p>
          </div>
          <button
            onClick={() => setItems((prev) => [...prev, { ...EMPTY_ITEM }])}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 text-xs font-black uppercase tracking-[0.2em]"
          >
            <Plus size={14} />
            Nuevo
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Cargando galeria...</p>
        ) : items.length === 0 ? (
          <button
            onClick={() => setItems([{ ...EMPTY_ITEM }])}
            className="w-full rounded-2xl border border-dashed border-slate-200 dark:border-white/10 p-10 text-center text-sm text-slate-500"
          >
            Crear primer item
          </button>
        ) : (
          <div className="space-y-4">
            {items.map((item, index) => (
              <div key={index} className="rounded-2xl border border-slate-100 dark:border-white/10 p-4 space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <input
                    value={item.url}
                    onChange={(event) => {
                      const value = event.target.value;
                      setItems((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, url: value } : row)));
                    }}
                    placeholder="https://..."
                    className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary/40"
                  />
                  <input
                    value={item.alt}
                    onChange={(event) => {
                      const value = event.target.value;
                      setItems((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, alt: value } : row)));
                    }}
                    placeholder="Texto alternativo"
                    className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary/40"
                  />
                  <input
                    value={item.section}
                    onChange={(event) => {
                      const value = event.target.value;
                      setItems((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, section: value } : row)));
                    }}
                    placeholder="home, eventos, cursos..."
                    className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary/40"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <ImageIcon size={14} />
                    {item.section || "general"}
                  </div>
                  <button
                    onClick={() => setItems((prev) => prev.filter((_, rowIndex) => rowIndex !== index))}
                    className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em] text-rose-500"
                  >
                    <Trash2 size={13} />
                    Eliminar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={save}
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-primary text-white text-xs font-black uppercase tracking-[0.2em] disabled:opacity-60"
          >
            <Save size={14} />
            {saving ? "Guardando" : "Guardar"}
          </button>
          {message && <p className="text-sm text-slate-500">{message}</p>}
        </div>
      </section>
    </div>
  );
}

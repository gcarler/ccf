"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import AdminHero from "@/components/admin/AdminHero";
import { FARO_EVENTS_BLOCK_KEY } from "@/lib/cms/blocks";
import { Archive, CalendarRange, Plus, RotateCcw, Save } from "lucide-react";

interface PublicEvent {
  title: string;
  date: string;
  location: string;
  excerpt: string;
  category: string;
  featured?: boolean;
  status?: "published" | "archived" | string;
}

interface ContentRecord {
  content?: string;
}

const EMPTY_EVENT: PublicEvent = {
  title: "",
  date: "",
  location: "",
  excerpt: "",
  category: "General",
  featured: false,
  status: "published"
};

export default function CmsEventsPage() {
  const { token, isAuthenticated } = useAuth();
  const [events, setEvents] = useState<PublicEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    const load = async () => {
      setLoading(true);
      try {
        const data = await apiFetch<ContentRecord>(`/content/${FARO_EVENTS_BLOCK_KEY}`, { token, cache: "no-store" });
        const parsed = data?.content ? JSON.parse(data.content) : [];
        setEvents(
          Array.isArray(parsed)
            ? parsed.map((event) => ({ ...event, status: event.status || "published" }))
            : [],
        );
      } catch {
        setEvents([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [token]);

  const activeEvents = useMemo(() => events.filter((event) => event.status !== "archived"), [events]);
  const archivedCount = events.length - activeEvents.length;
  const featuredCount = useMemo(() => activeEvents.filter((event) => event.featured).length, [activeEvents]);

  const save = async () => {
    if (!token) return;
    setSaving(true);
    setMessage(null);
    const payload = { content: JSON.stringify(events, null, 2) };
    try {
      try {
        await apiFetch(`/content/${FARO_EVENTS_BLOCK_KEY}`, { method: "PUT", token, body: payload });
      } catch {
        await apiFetch(`/content/${FARO_EVENTS_BLOCK_KEY}`, { method: "POST", token, body: payload });
      }
      setMessage("Agenda publica actualizada.");
    } catch {
      setMessage("No se pudo guardar la agenda.");
    } finally {
      setSaving(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-3xl mx-auto py-24 text-center space-y-3">
        <h1 className="text-3xl font-black">Inicia sesion</h1>
        <p className="text-slate-500">Necesitas una sesion valida para administrar eventos publicos.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 px-4 py-8">
      <AdminHero
        eyebrow="CMS"
        title="Eventos publicos"
        description="Administra la agenda publicada en FARO desde un flujo editorial simple."
        tags={["Eventos", "Agenda", "Publico"]}
        watchers={["Comunicaciones", "Eventos"]}
        primaryAction={{ label: saving ? "Guardando..." : "Guardar agenda", icon: Save, onClick: save }}
      />

      <section className="rounded-[2rem] border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Eventos</p>
              <p className="text-3xl font-black mt-1">{activeEvents.length}</p>
            </div>
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Destacados</p>
              <p className="text-3xl font-black mt-1">{featuredCount}</p>
            </div>
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Archivados</p>
              <p className="text-3xl font-black mt-1">{archivedCount}</p>
            </div>
          </div>
          <button
            onClick={() => setEvents((prev) => [...prev, { ...EMPTY_EVENT }])}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 text-xs font-black uppercase tracking-[0.2em]"
          >
            <Plus size={14} />
            Nuevo evento
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Cargando agenda...</p>
        ) : events.length === 0 ? (
          <button
            onClick={() => setEvents([{ ...EMPTY_EVENT }])}
            className="w-full rounded-2xl border border-dashed border-slate-200 dark:border-white/10 p-10 text-center text-sm text-slate-500"
          >
            Crear primer evento
          </button>
        ) : (
          <div className="space-y-4">
            {events.map((event, index) => {
              const isArchived = event.status === "archived";
              return (
              <div key={index} className={`rounded-2xl border p-4 space-y-3 ${isArchived ? "border-slate-200 bg-slate-50 text-slate-500 dark:border-white/10 dark:bg-white/[0.03]" : "border-slate-100 dark:border-white/10"}`}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <input
                    value={event.title}
                    onChange={(value) => {
                      const next = value.target.value;
                      setEvents((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, title: next } : row)));
                    }}
                    placeholder="Titulo"
                    className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary/40"
                  />
                  <input
                    value={event.category}
                    onChange={(value) => {
                      const next = value.target.value;
                      setEvents((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, category: next } : row)));
                    }}
                    placeholder="Categoria"
                    className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary/40"
                  />
                  <input
                    value={event.date}
                    onChange={(value) => {
                      const next = value.target.value;
                      setEvents((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, date: next } : row)));
                    }}
                    placeholder="24 JUN 2026"
                    className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary/40"
                  />
                  <input
                    value={event.location}
                    onChange={(value) => {
                      const next = value.target.value;
                      setEvents((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, location: next } : row)));
                    }}
                    placeholder="Auditorio Central"
                    className="rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary/40"
                  />
                </div>
                <textarea
                  rows={3}
                  value={event.excerpt}
                  onChange={(value) => {
                    const next = value.target.value;
                    setEvents((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, excerpt: next } : row)));
                  }}
                  placeholder="Descripcion corta del evento"
                  className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none focus:border-primary/40"
                />

                <div className="flex items-center justify-between">
                  <label className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em] text-slate-500">
                    <input
                      type="checkbox"
                      checked={!!event.featured}
                      onChange={(value) => {
                        const checked = value.target.checked;
                        setEvents((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, featured: checked } : row)));
                      }}
                    />
                    Destacado
                  </label>
                  <button
                    onClick={() => {
                      const nextStatus = isArchived ? "published" : "archived";
                      setEvents((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, status: nextStatus } : row)));
                    }}
                    className={`inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em] ${isArchived ? "text-emerald-600" : "text-amber-700"}`}
                  >
                    {isArchived ? <RotateCcw size={13} /> : <Archive size={13} />}
                    {isArchived ? "Restaurar" : "Archivar"}
                  </button>
                </div>
              </div>
              );
            })}
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

        <div className="rounded-xl border border-slate-200 dark:border-white/10 p-4 flex items-start gap-3">
          <CalendarRange className="w-4 h-4 mt-0.5 text-primary" />
          <p className="text-xs text-slate-500 leading-relaxed">
            Este modulo persiste la agenda en el bloque <span className="font-mono">{FARO_EVENTS_BLOCK_KEY}</span> para ser consumida por la web publica.
          </p>
        </div>
      </section>
    </div>
  );
}


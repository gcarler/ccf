"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import AdminHero from "@/components/admin/AdminHero";
import { FARO_BLOCKS } from "@/lib/cms/blocks";
import { FileText, Save, Eye } from "lucide-react";

interface ContentRecord {
  page_key?: string;
  title?: string;
  content?: string;
}

export default function CmsContentPage() {
  const { token, isAuthenticated } = useAuth();
  const [selectedKey, setSelectedKey] = useState(FARO_BLOCKS[0]?.key ?? "");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("{}");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const currentBlock = useMemo(
    () => FARO_BLOCKS.find((block) => block.key === selectedKey),
    [selectedKey]
  );

  useEffect(() => {
    if (!selectedKey || !token) return;

    const loadBlock = async () => {
      setLoading(true);
      setMessage(null);
      try {
        const data = await apiFetch<ContentRecord>(`/content/${selectedKey}`, {
          token,
          cache: "no-store"
        });
        setTitle(data?.title || "");
        setContent(data?.content || JSON.stringify(currentBlock?.sample ?? {}, null, 2));
      } catch {
        setTitle("");
        setContent(JSON.stringify(currentBlock?.sample ?? {}, null, 2));
      } finally {
        setLoading(false);
      }
    };

    loadBlock();
  }, [selectedKey, token, currentBlock?.sample]);

  const parsedPreview = useMemo(() => {
    try {
      return JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      return "JSON invalido. Corrige el contenido para previsualizar.";
    }
  }, [content]);

  const save = async () => {
    if (!selectedKey || !token) return;
    setSaving(true);
    setMessage(null);

    const payload = { title, content };

    try {
      try {
        await apiFetch(`/content/${selectedKey}`, { method: "PUT", token, body: payload });
      } catch {
        try {
          await apiFetch(`/content/${selectedKey}`, { method: "PATCH", token, body: payload });
        } catch {
          await apiFetch(`/content/${selectedKey}`, { method: "POST", token, body: payload });
        }
      }
      setMessage("Contenido guardado y listo para publicar.");
    } catch {
      setMessage("No se pudo guardar. Revisa permisos o endpoint de contenido.");
    } finally {
      setSaving(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-3xl mx-auto py-24 text-center space-y-3">
        <h1 className="text-3xl font-black">Inicia sesion</h1>
        <p className="text-slate-500">Necesitas una sesion valida para administrar contenido.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 px-4 py-8">
      <AdminHero
        eyebrow="CMS"
        title="Editor de contenido"
        description="Gestiona copys y estructuras JSON de las paginas FARO sin tocar codigo."
        tags={["FARO", "Bloques", "Publicacion"]}
        watchers={["Comunicaciones", "Web Team"]}
        primaryAction={{ label: saving ? "Guardando..." : "Guardar bloque", icon: Save, onClick: save }}
        secondaryAction={currentBlock ? { label: "Abrir pagina", icon: Eye, onClick: () => window.open(currentBlock.page, "_blank") } : undefined}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        <aside className="rounded-[2rem] border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-2">
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 px-2 py-2">Bloques FARO</p>
          {FARO_BLOCKS.map((block) => (
            <button
              key={block.key}
              onClick={() => setSelectedKey(block.key)}
              className={`w-full text-left rounded-2xl p-3 border transition-colors ${
                selectedKey === block.key
                  ? "border-primary/40 bg-primary/5"
                  : "border-slate-100 dark:border-white/10 hover:border-primary/30"
              }`}
            >
              <p className="text-sm font-bold text-slate-900 dark:text-white">{block.label}</p>
              <p className="text-xs text-slate-500 mt-1">{block.description}</p>
              <p className="text-[10px] uppercase tracking-[0.25em] text-primary mt-2">{block.page}</p>
            </button>
          ))}
        </aside>

        <section className="rounded-[2rem] border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-6 space-y-5">
          <div className="space-y-1">
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Llave</p>
            <p className="font-mono text-sm text-primary">{selectedKey}</p>
          </div>

          <label className="block space-y-2">
            <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Titulo (opcional)</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Titulo editorial"
              className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-4 py-3 text-sm outline-none focus:border-primary/40"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Contenido JSON</span>
            <textarea
              value={content}
              onChange={(event) => setContent(event.target.value)}
              rows={16}
              className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-4 py-3 text-sm font-mono outline-none focus:border-primary/40"
            />
          </label>

          <div className="flex items-center gap-3">
            <button
              onClick={save}
              disabled={saving || loading}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-primary text-white text-xs font-black uppercase tracking-[0.2em] disabled:opacity-60"
            >
              <Save size={14} />
              {saving ? "Guardando" : "Guardar"}
            </button>
            {loading && <p className="text-sm text-slate-500">Cargando bloque...</p>}
            {message && <p className="text-sm text-slate-500">{message}</p>}
          </div>

          <div className="rounded-xl border border-dashed border-slate-200 dark:border-white/10 p-4 space-y-3">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Vista de estructura</p>
            <pre className="text-xs whitespace-pre-wrap text-slate-600 dark:text-slate-300">{parsedPreview}</pre>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-white/10 p-4 flex items-start gap-3">
            <FileText className="w-4 h-4 mt-0.5 text-primary" />
            <p className="text-xs text-slate-500 leading-relaxed">
              Recomendacion: mantener llaves cortas en snake_case y evitar HTML. El frontend renderiza con componentes del sistema de diseno.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}

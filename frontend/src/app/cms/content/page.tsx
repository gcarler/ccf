"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { ApiError, apiFetch } from "@/lib/http";
import AdminHero from "@/components/admin/AdminHero";
import { FARO_BLOCKS } from "@/lib/cms/blocks";
import { CheckCircle2, Eye, FileText, RotateCcw, Save, Send, ShieldCheck, ImageIcon, Copy } from "lucide-react";

interface MediaItem {
  id: number;
  url: string;
  alt_text?: string;
}

export default function CmsContentPage() {
  const { token, isAuthenticated } = useAuth();
  const [selectedKey, setSelectedKey] = useState(FARO_BLOCKS[0]?.key ?? "");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("{}");
  const [workflow, setWorkflow] = useState<ContentWorkflow | null>(null);
  const [versions, setVersions] = useState<ContentVersion[]>([]);
  const [publishAt, setPublishAt] = useState("");
  const [expireAt, setExpireAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  
  // Quick Media Access
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [showMedia, setShowMedia] = useState(false);

  const currentBlock = useMemo(
    () => FARO_BLOCKS.find((block) => block.key === selectedKey),
    [selectedKey]
  );

  const loadMedia = async () => {
    if (!token) return;
    try {
      const data = await apiFetch<MediaItem[]>("/cms/media", { token });
      setMedia(Array.isArray(data) ? data : []);
    } catch { console.error("Error loading media"); }
  };

  useEffect(() => {
    if (showMedia) loadMedia();
  }, [showMedia, token]);

  const parsedPreview = useMemo(() => {
    try {
      return JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      return "JSON invalido. Corrige el contenido para previsualizar.";
    }
  }, [content]);

  const loadBlock = async () => {
    if (!selectedKey || !token) return;
    setLoading(true);
    setMessage(null);
    try {
      const [data, wf, ver] = await Promise.all([
        apiFetch<ContentRecord>(`/content/${selectedKey}`, { token, cache: "no-store" }),
        apiFetch<ContentWorkflow>(`/content/${selectedKey}/workflow`, { token, cache: "no-store" }),
        apiFetch<ContentVersion[]>(`/content/${selectedKey}/versions`, { token, cache: "no-store" })
      ]);
      setTitle(data?.title || "");
      setContent(data?.content || JSON.stringify(currentBlock?.sample ?? {}, null, 2));
      setWorkflow(wf);
      setPublishAt(wf?.publish_at ? wf.publish_at.slice(0, 16) : "");
      setExpireAt(wf?.expire_at ? wf.expire_at.slice(0, 16) : "");
      setVersions(Array.isArray(ver) ? ver.slice(0, 6) : []);
    } catch {
      setTitle("");
      setContent(JSON.stringify(currentBlock?.sample ?? {}, null, 2));
      setWorkflow(null);
      setVersions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBlock();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedKey, token]);

  const save = async () => {
    if (!selectedKey || !token) return;
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch(`/content/${selectedKey}`, {
        method: "PUT",
        token,
        body: { title, content }
      });
      setMessage("Bloque guardado como borrador.");
      await loadBlock();
    } catch (err) {
      const detail = err instanceof ApiError ? JSON.stringify(err.detail) : "";
      setMessage(`No se pudo guardar. ${detail}`);
    } finally {
      setSaving(false);
    }
  };

  const transition = async (action: string) => {
    if (!selectedKey || !token) return;
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch(`/content/${selectedKey}/workflow`, {
        method: "PATCH",
        token,
        body: {
          action,
          publish_at: publishAt ? new Date(publishAt).toISOString() : null,
          expire_at: expireAt ? new Date(expireAt).toISOString() : null
        }
      });
      setMessage(`Estado actualizado: ${action}.`);
      await loadBlock();
    } catch (err) {
      const detail = err instanceof ApiError ? JSON.stringify(err.detail) : "";
      setMessage(`No se pudo cambiar estado. ${detail}`);
    } finally {
      setSaving(false);
    }
  };

  const rollback = async (versionId: number) => {
    if (!selectedKey || !token) return;
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch(`/content/${selectedKey}/rollback/${versionId}`, { method: "POST", token });
      setMessage(`Version ${versionId} restaurada.`);
      await loadBlock();
    } catch {
      setMessage("No se pudo restaurar la version seleccionada.");
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
        description="Gestiona copys, flujo editorial, versionado y publicacion desde una sola vista."
        tags={["FARO", "Workflow", "Versionado"]}
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
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Llave</p>
              <p className="font-mono text-sm text-primary">{selectedKey}</p>
            </div>
            {workflow && (
              <span className="text-xs font-black uppercase tracking-[0.2em] px-3 py-1 rounded-full border border-primary/30 text-primary bg-primary/10">
                {STATUS_LABEL[workflow.status]}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="block space-y-2">
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Publicar en</span>
              <input
                type="datetime-local"
                value={publishAt}
                onChange={(event) => setPublishAt(event.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Expirar en</span>
              <input
                type="datetime-local"
                value={expireAt}
                onChange={(event) => setExpireAt(event.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm outline-none"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button onClick={() => transition("submit_review")} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 text-xs font-black uppercase tracking-[0.2em]">
              <Send size={13} /> Revision
            </button>
            <button onClick={() => transition("approve")} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 text-xs font-black uppercase tracking-[0.2em]">
              <ShieldCheck size={13} /> Aprobar
            </button>
            <button onClick={() => transition("publish")} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-primary text-white text-xs font-black uppercase tracking-[0.2em]">
              <CheckCircle2 size={13} /> Publicar
            </button>
            <button onClick={() => transition("revert_draft")} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 text-xs font-black uppercase tracking-[0.2em]">
              Borrador
            </button>
            <button 
              onClick={() => setShowMedia(!showMedia)} 
              className={`inline-flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-black uppercase tracking-[0.2em] transition-colors ${showMedia ? "bg-primary/10 border-primary text-primary" : "border-slate-200"}`}
            >
              <ImageIcon size={13} /> {showMedia ? "Cerrar biblioteca" : "Ver biblioteca"}
            </button>
          </div>

          <div className="flex flex-col lg:flex-row gap-6">
            <div className="flex-1 space-y-5">
              <label className="block space-y-2">
                <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Titulo (opcional)</span>
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Titulo editorial"
                  className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-4 py-3 text-sm outline-none"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Contenido JSON</span>
                <textarea
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  rows={16}
                  className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-4 py-3 text-sm font-mono outline-none"
                />
              </label>
            </div>

            {showMedia && (
              <div className="lg:w-80 h-[600px] rounded-2xl border border-slate-200 dark:border-white/10 p-4 overflow-y-auto space-y-4 bg-slate-50 dark:bg-black/20">
                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Biblioteca de Medios</p>
                {media.length === 0 ? (
                  <p className="text-xs text-slate-500">No hay archivos. Súbelos en el Media Manager.</p>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    {media.map((item) => (
                      <div key={item.id} className="group relative aspect-square rounded-xl overflow-hidden border border-slate-200 bg-white shadow-sm">
                        <img src={item.url} alt="" className="w-full h-full object-cover" />
                        <button 
                          onClick={() => {
                            navigator.clipboard.writeText(item.url);
                            alert("URL copiada al portapapeles");
                          }}
                          className="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity text-white text-[10px] font-black uppercase"
                        >
                          <Copy size={12} className="mr-1" /> Copiar
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

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

          <div className="rounded-xl border border-slate-200 dark:border-white/10 p-4 space-y-2">
            <p className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Versiones recientes</p>
            {versions.length === 0 ? (
              <p className="text-xs text-slate-500">Sin versiones registradas aun.</p>
            ) : (
              <div className="space-y-2">
                {versions.map((version) => (
                  <div key={version.id} className="flex items-center justify-between rounded-xl border border-slate-100 dark:border-white/10 px-3 py-2">
                    <p className="text-xs text-slate-500">#{version.id} · {new Date(version.created_at).toLocaleString()}</p>
                    <button onClick={() => rollback(version.id)} className="inline-flex items-center gap-1 text-xs font-black uppercase tracking-[0.2em] text-primary">
                      <RotateCcw size={12} /> Restaurar
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-white/10 p-4 flex items-start gap-3">
            <FileText className="w-4 h-4 mt-0.5 text-primary" />
            <p className="text-xs text-slate-500 leading-relaxed">
              Recomendacion: usa llaves consistentes por bloque y evita HTML libre. Este editor valida estructura para proteger la UI publica.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}

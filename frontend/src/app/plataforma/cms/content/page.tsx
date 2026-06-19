"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import OptimizedImage from "@/components/ui/OptimizedImage";
import Link from "next/link";
import {
  Bold,
  CheckCircle2,
  Copy,
  Eye,
  FileText,
  ImageIcon,
  Italic,
  LinkIcon,
  List,
  Plus,
  RotateCcw,
  Save,
  Send,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { ApiError, apiFetch } from "@/lib/http";
import AdminHero from "@/components/admin/AdminHero";
import { SITE_BLOCKS } from "@/lib/cms/blocks";

interface MediaItem {
  id: number;
  url: string;
  alt_text?: string;
  filename?: string;
  mime_type?: string;
}

interface ContentRecord {
  id?: number;
  page_key?: string;
  title: string;
  content: string;
  updated_at?: string;
}

interface ContentWorkflow {
  status: string;
  publish_at?: string;
  expire_at?: string;
}

interface ContentVersion {
  id: number;
  created_at: string;
}

type Primitive = string | number | boolean | null;
type EditableValue = Primitive | EditableValue[] | { [key: string]: EditableValue };
type EditorMode = "structured" | "rich";

const STATUS_LABEL: Record<string, string> = {
  draft: "Borrador",
  in_review: "En revision",
  approved: "Aprobado",
  published: "Publicado",
  scheduled: "Programado",
  expired: "Expirado",
};

const FIELD_LABELS: Record<string, string> = {
  eyebrow: "Sobrelinea",
  title: "Titulo",
  title_lead: "Titulo inicial",
  title_accent: "Titulo destacado",
  title_tail: "Titulo final",
  description: "Descripcion",
  cta: "Boton principal",
  primary_cta: "Boton principal",
  secondary_cta: "Boton secundario",
  search_placeholder: "Texto del buscador",
  label: "Etiqueta",
  href: "Enlace",
  content: "Contenido",
  category: "Categoria",
  emotion: "Emocion",
  image_url: "Imagen",
  video_url: "Video",
  podcast_url: "Podcast",
  media_url: "Medio",
  is_active: "Activo",
  is_approved: "Aprobado",
  show_on_home: "Mostrar en inicio",
  created_at: "Fecha",
  username: "Nombre",
  role: "Rol",
  items: "Elementos",
  author: "Autor",
};

const RICH_SUFFIXES = ["_html", "_text", "_body", "_body_html", "_copy", "_rich_text"];

function isRecord(value: unknown): value is { [key: string]: EditableValue } {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toEditableValue(value: unknown): EditableValue {
  if (Array.isArray(value)) return value.map(toEditableValue);
  if (isRecord(value)) {
    return Object.fromEntries(Object.entries(value).map(([key, val]) => [key, toEditableValue(val)]));
  }
  if (["string", "number", "boolean"].includes(typeof value) || value === null) return value as Primitive;
  return String(value ?? "");
}

function parseStructuredContent(raw: string, fallback: unknown): EditableValue {
  try {
    return toEditableValue(JSON.parse(raw));
  } catch {
    return toEditableValue(fallback ?? {});
  }
}

function formatLabel(key: string): string {
  return FIELD_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, char => char.toUpperCase());
}

function isLongTextField(key: string): boolean {
  return ["content", "description", "body", "subtitle", "notes"].some(fragment => key.toLowerCase().includes(fragment));
}

function isRichTextKey(key: string): boolean {
  const normalized = key.toLowerCase();
  return normalized.includes("wiki") || RICH_SUFFIXES.some(suffix => normalized.endsWith(suffix));
}

function getAtPath(root: EditableValue, path: Array<string | number>): EditableValue {
  return path.reduce<EditableValue>((current, segment) => {
    if (Array.isArray(current)) return current[Number(segment)] ?? "";
    if (isRecord(current)) return current[String(segment)] ?? "";
    return "";
  }, root);
}

function updateAtPath(root: EditableValue, path: Array<string | number>, next: EditableValue): EditableValue {
  if (path.length === 0) return next;
  const [segment, ...rest] = path;
  if (Array.isArray(root)) {
    const copy = [...root];
    const index = Number(segment);
    copy[index] = updateAtPath(copy[index] ?? "", rest, next);
    return copy;
  }
  if (isRecord(root)) {
    return { ...root, [String(segment)]: updateAtPath(root[String(segment)] ?? "", rest, next) };
  }
  return root;
}

function removeAtPath(root: EditableValue, path: Array<string | number>): EditableValue {
  const parentPath = path.slice(0, -1);
  const last = path[path.length - 1];
  const parent = getAtPath(root, parentPath);
  if (Array.isArray(parent)) {
    return updateAtPath(root, parentPath, parent.filter((_, index) => index !== Number(last)));
  }
  if (isRecord(parent)) {
    const nextParent = { ...parent };
    delete nextParent[String(last)];
    return updateAtPath(root, parentPath, nextParent);
  }
  return root;
}

function cloneTemplate(value: EditableValue | undefined): EditableValue {
  if (Array.isArray(value)) return value.map(cloneTemplate);
  if (isRecord(value)) return Object.fromEntries(Object.entries(value).map(([key, val]) => [key, cloneTemplate(val)]));
  if (typeof value === "number") return 0;
  if (typeof value === "boolean") return false;
  return "";
}

function RichTextEditor({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const editorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (editorRef.current && document.activeElement !== editorRef.current && editorRef.current.innerHTML !== value) {
      editorRef.current.innerHTML = value || "";
    }
  }, [value]);

  const runCommand = (command: string, commandValue?: string) => {
    editorRef.current?.focus();
    document.execCommand(command, false, commandValue);
    onChange(editorRef.current?.innerHTML || "");
  };

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-[#0f1318]">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-2 dark:border-white/10">
        <button type="button" onClick={() => runCommand("bold")} className="rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
          <Bold size={13} />
        </button>
        <button type="button" onClick={() => runCommand("italic")} className="rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
          <Italic size={13} />
        </button>
        <button type="button" onClick={() => runCommand("formatBlock", "h2")} className="rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
          H2
        </button>
        <button type="button" onClick={() => runCommand("insertUnorderedList")} className="rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
          <List size={13} />
        </button>
        <button
          type="button"
          onClick={() => {
            const url = window.prompt("URL del enlace");
            if (url) runCommand("createLink", url);
          }}
          className="rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide"
        >
          <LinkIcon size={13} />
        </button>
      </div>
      <div
        ref={editorRef}
        contentEditable
        suppressContentEditableWarning
        onInput={() => onChange(editorRef.current?.innerHTML || "")}
        className="prose prose-slate dark:prose-invert min-h-[340px] max-w-none p-3 text-sm outline-none"
      />
    </div>
  );
}

function EditableNode({
  root,
  path,
  label,
  onChange,
}: {
  root: EditableValue;
  path: Array<string | number>;
  label: string;
  onChange: (value: EditableValue) => void;
}) {
  const value = getAtPath(root, path);
  const fieldKey = String(path[path.length - 1] ?? label);
  const setValue = (next: EditableValue) => onChange(updateAtPath(root, path, next));

  if (Array.isArray(value)) {
    const template = value[0] ?? { title: "", content: "" };
    return (
      <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50/70 p-4 dark:border-white/10 dark:bg-white/[0.03]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{formatLabel(label)}</p>
            <p className="text-[11px] text-slate-400">{value.length} elementos editables</p>
          </div>
          <button
            type="button"
            onClick={() => setValue([...value, cloneTemplate(template)])}
            className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white dark:bg-[hsl(var(--bg-primary))] dark:text-slate-900"
          >
            <Plus size={12} /> Agregar
          </button>
        </div>
        <div className="space-y-3">
          {value.map((_, index) => (
            <div key={index} className="rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-[#0f1318]">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Elemento {index + 1}</p>
                <button type="button" onClick={() => onChange(removeAtPath(root, [...path, index]))} className="text-rose-500">
                  <Trash2 size={14} />
                </button>
              </div>
              <EditableNode root={root} path={[...path, index]} label={`${label} ${index + 1}`} onChange={onChange} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isRecord(value)) {
    return (
      <div className="space-y-4 rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-[#111418]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{formatLabel(label)}</p>
          <p className="text-[11px] text-slate-400">{Object.keys(value).length} campos</p>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {Object.keys(value).map(key => (
            <div key={key} className={Array.isArray(value[key]) || isRecord(value[key]) || isLongTextField(key) ? "md:col-span-2" : ""}>
              <EditableNode root={root} path={[...path, key]} label={key} onChange={onChange} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (typeof value === "boolean") {
    return (
      <label className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-[#0f1318]">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{formatLabel(fieldKey)}</span>
        <input type="checkbox" checked={value} onChange={event => setValue(event.target.checked)} className="size-4" />
      </label>
    );
  }

  if (typeof value === "number") {
    return (
      <label className="block space-y-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{formatLabel(fieldKey)}</span>
        <input
          type="number"
          value={value}
          onChange={event => setValue(Number(event.target.value))}
          className="w-full rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] px-4 py-3 text-sm outline-none dark:border-white/10 dark:bg-[#0f1318]"
        />
      </label>
    );
  }

  const stringValue = String(value ?? "");
  const className = "w-full rounded-md border border-slate-200 bg-[hsl(var(--bg-primary))] px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/20 dark:border-white/10 dark:bg-[#0f1318]";
  return (
    <label className="block space-y-2">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{formatLabel(fieldKey)}</span>
      {isLongTextField(fieldKey) ? (
        <textarea value={stringValue} onChange={event => setValue(event.target.value)} rows={4} className={`${className} resize-y`} />
      ) : (
        <input value={stringValue} onChange={event => setValue(event.target.value)} className={className} />
      )}
    </label>
  );
}

export default function CmsContentPage() {
  const { token, isAuthenticated } = useAuth();
  const [selectedKey, setSelectedKey] = useState(SITE_BLOCKS[0]?.key ?? "");
  const [records, setRecords] = useState<ContentRecord[]>([]);
  const [title, setTitle] = useState("");
  const [structuredValue, setStructuredValue] = useState<EditableValue>({});
  const [richContent, setRichContent] = useState("");
  const [editorMode, setEditorMode] = useState<EditorMode>("structured");
  const [workflow, setWorkflow] = useState<ContentWorkflow | null>(null);
  const [versions, setVersions] = useState<ContentVersion[]>([]);
  const [publishAt, setPublishAt] = useState("");
  const [expireAt, setExpireAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [showMedia, setShowMedia] = useState(false);
  const [copiedMediaId, setCopiedMediaId] = useState<number | null>(null);
  const [newBlockName, setNewBlockName] = useState("");
  const [isDirty, setIsDirty] = useState(false);

  const currentBlock = useMemo(() => SITE_BLOCKS.find(block => block.key === selectedKey), [selectedKey]);
  const knownKeys = useMemo(() => new Set(SITE_BLOCKS.map(block => block.key)), []);
  const extraBlocks = useMemo(() => records.filter(record => record.page_key && !knownKeys.has(record.page_key)), [knownKeys, records]);

  const loadRecords = async () => {
    if (!token) return;
    try {
      const data = await apiFetch<ContentRecord[]>("/content", { token, cache: "no-store" });
      setRecords(Array.isArray(data) ? data : []);
    } catch {
      setRecords([]);
    }
  };

  const loadMedia = async () => {
    if (!token) return;
    try {
      const data = await apiFetch<{ items: MediaItem[]; total: number }>("/cms/media", { token, cache: "no-store" });
      setMedia(data?.items || []);
    } catch {
      setMedia([]);
    }
  };

  const loadBlock = async () => {
    if (!selectedKey || !token) return;
    setLoading(true);
    setMessage(null);
    try {
      const [data, wf, ver] = await Promise.all([
        apiFetch<ContentRecord>(`/content/${selectedKey}`, { token, cache: "no-store" }),
        apiFetch<ContentWorkflow>(`/content/${selectedKey}/workflow`, { token, cache: "no-store" }),
        apiFetch<ContentVersion[]>(`/content/${selectedKey}/versions`, { token, cache: "no-store" }),
      ]);
      const rich = isRichTextKey(selectedKey);
      setTitle(data?.title || currentBlock?.label || selectedKey);
      setEditorMode(rich ? "rich" : "structured");
      setRichContent(rich ? (data?.content === "{}" ? "" : data?.content || "") : "");
      setStructuredValue(rich ? {} : parseStructuredContent(data?.content || "", currentBlock?.sample ?? {}));
      setWorkflow(wf);
      setPublishAt(wf?.publish_at ? wf.publish_at.slice(0, 16) : "");
      setExpireAt(wf?.expire_at ? wf.expire_at.slice(0, 16) : "");
      setVersions(Array.isArray(ver) ? ver.slice(0, 6) : []);
    } catch {
      const rich = isRichTextKey(selectedKey);
      setTitle(currentBlock?.label || selectedKey);
      setEditorMode(rich ? "rich" : "structured");
      setRichContent("");
      setStructuredValue(parseStructuredContent("", currentBlock?.sample ?? {}));
      setWorkflow(null);
      setVersions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    loadBlock();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedKey, token]);

  useEffect(() => {
    if (showMedia) loadMedia();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showMedia, token]);

  // Reset dirty when block changes
  useEffect(() => { setIsDirty(false); }, [selectedKey]);

  // Warn before leaving with unsaved changes
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!isDirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

  // Ctrl+S / Cmd+S to save
  const saveRef = useRef<() => void>(() => {});
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        saveRef.current();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const save = useCallback(async () => {
    if (!selectedKey || !token) return;
    setSaving(true);
    setMessage(null);
    try {
      const content = editorMode === "rich" ? richContent : JSON.stringify(structuredValue, null, 2);
      await apiFetch(`/content/${selectedKey}`, { method: "PUT", token, body: { title, content } });
      setIsDirty(false);
      setMessage("Bloque guardado.");
      await Promise.all([loadBlock(), loadRecords()]);
    } catch (err) {
      const detail = err instanceof ApiError ? JSON.stringify(err.detail) : "";
      setMessage(`No se pudo guardar. ${detail}`);
    } finally {
      setSaving(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedKey, token, editorMode, richContent, structuredValue, title]);

  useEffect(() => { saveRef.current = save; }, [save]);

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
          expire_at: expireAt ? new Date(expireAt).toISOString() : null,
        },
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

  const createRichBlock = () => {
    const slug = newBlockName.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
    if (!slug) return;
    const nextKey = slug.endsWith("_html") ? slug : `${slug}_html`;
    setSelectedKey(nextKey);
    setTitle(newBlockName.trim());
    setEditorMode("rich");
    setRichContent("<p>Nuevo contenido enriquecido.</p>");
    setStructuredValue({});
    setNewBlockName("");
  };

  const copyMediaUrl = (item: MediaItem) => {
    navigator.clipboard.writeText(item.url);
    setCopiedMediaId(item.id);
    setTimeout(() => setCopiedMediaId(null), 1600);
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-3xl mx-auto py-1.5 text-center space-y-3">
        <h1 className="text-xl font-semibold">Inicia sesion</h1>
        <p className="text-slate-500">Necesitas una sesion valida para administrar contenido.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 px-4 py-8">
      <AdminHero
        eyebrow="CMS"
        title="Editor visual de contenido"
        description="Edita textos, heroes, menus y bloques enriquecidos sin tocar JSON. La estructura se serializa solo al guardar."
        tags={["FARO", "Texto enriquecido", "Media"]}
        watchers={["Comunicaciones", "Web Team"]}
        primaryAction={{ label: saving ? "Guardando..." : isDirty ? "Guardar cambios ●" : "Guardar bloque", icon: Save, onClick: save }}
        secondaryAction={currentBlock ? { label: "Abrir pagina", icon: Eye, onClick: () => window.open(currentBlock.page, "_blank") } : undefined}
      />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[320px_1fr_300px]">
        <aside className="space-y-4 rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-[#111418]">
          <div>
            <p className="px-2 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Bloques FARO</p>
            <div className="space-y-2">
              {SITE_BLOCKS.map(block => (
                <button
                  key={block.key}
                  onClick={() => setSelectedKey(block.key)}
                  className={`w-full rounded-lg border p-3 text-left transition-colors ${
                    selectedKey === block.key ? "border-primary/40 bg-primary/5" : "border-slate-100 hover:border-primary/30 dark:border-white/10"
                  }`}
                >
                  <p className="text-sm font-bold text-slate-900 dark:text-white">{block.label}</p>
                  <p className="mt-1 text-xs text-slate-500">{block.description}</p>
                  <p className="mt-2 text-[10px] uppercase tracking-wider text-primary">{block.page}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-dashed border-slate-200 p-3 dark:border-white/10">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Nuevo texto enriquecido</p>
            <div className="mt-3 flex gap-2">
              <input
                value={newBlockName}
                onChange={event => setNewBlockName(event.target.value)}
                placeholder="ej. site_about_body"
                className="min-w-0 flex-1 rounded-md border border-slate-200 bg-transparent px-3 py-2 text-xs outline-none dark:border-white/10"
              />
              <button type="button" onClick={createRichBlock} className="rounded-md bg-primary px-3 text-white">
                <Plus size={14} />
              </button>
            </div>
          </div>

          {extraBlocks.length > 0 && (
            <div>
              <p className="px-2 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Otros bloques</p>
              <div className="max-h-48 space-y-2 overflow-y-auto pr-1">
                {extraBlocks.map(record => (
                  <button
                    key={record.page_key}
                    onClick={() => setSelectedKey(record.page_key || "")}
                    className={`w-full rounded-lg border p-3 text-left transition-colors ${
                      selectedKey === record.page_key ? "border-primary/40 bg-primary/5" : "border-slate-100 hover:border-primary/30 dark:border-white/10"
                    }`}
                  >
                    <p className="text-sm font-bold text-slate-900 dark:text-white">{record.title || record.page_key}</p>
                    <p className="mt-1 font-mono text-[10px] text-slate-400">{record.page_key}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>

        <section className="space-y-5 rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-[#111418]">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Llave</p>
              <p className="font-mono text-sm text-primary">{selectedKey}</p>
              <p className="text-xs text-slate-500">Modo: {editorMode === "rich" ? "texto enriquecido" : "campos estructurados"}</p>
            </div>
            {workflow && (
              <span className="w-fit rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary">
                {STATUS_LABEL[workflow.status] || workflow.status}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="block space-y-2 md:col-span-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Titulo editorial</span>
              <input
                value={title}
                onChange={event => setTitle(event.target.value)}
                placeholder="Titulo editorial"
                className="w-full rounded-md border border-slate-200 bg-transparent px-4 py-3 text-sm outline-none dark:border-white/10"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Publicar en</span>
              <input
                type="datetime-local"
                value={publishAt}
                onChange={event => setPublishAt(event.target.value)}
                className="w-full rounded-md border border-slate-200 bg-transparent px-3 py-2 text-sm outline-none dark:border-white/10"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Expirar en</span>
              <input
                type="datetime-local"
                value={expireAt}
                onChange={event => setExpireAt(event.target.value)}
                className="w-full rounded-md border border-slate-200 bg-transparent px-3 py-2 text-sm outline-none dark:border-white/10"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button onClick={() => transition("submit_review")} className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
              <Send size={13} /> Revision
            </button>
            <button onClick={() => transition("approve")} className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
              <ShieldCheck size={13} /> Aprobar
            </button>
            <button onClick={() => transition("publish")} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white">
              <CheckCircle2 size={13} /> Publicar
            </button>
            <button onClick={() => transition("revert_draft")} className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide">
              Borrador
            </button>
            <button
              onClick={() => setShowMedia(prev => !prev)}
              className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-xs font-semibold uppercase tracking-wide transition-colors ${
                showMedia ? "border-primary bg-primary/10 text-primary" : "border-slate-200"
              }`}
            >
              <ImageIcon size={13} /> {showMedia ? "Ocultar media" : "Abrir media"}
            </button>
          </div>

          {editorMode === "rich" ? (
            <RichTextEditor value={richContent} onChange={v => { setRichContent(v); setIsDirty(true); }} />
          ) : (
            <EditableNode root={structuredValue} path={[]} label="Contenido" onChange={v => { setStructuredValue(v); setIsDirty(true); }} />
          )}

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={save}
              disabled={saving || loading}
              className={`inline-flex items-center gap-2 rounded-md px-3 py-3 text-xs font-semibold uppercase tracking-wide text-white disabled:opacity-60 transition-colors ${isDirty ? "bg-amber-500 hover:bg-amber-600" : "bg-primary"}`}
            >
              {saving ? (
                <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
              ) : (
                <Save size={14} />
              )}
              {saving ? "Guardando…" : isDirty ? "Guardar cambios ●" : "Guardar"}
            </button>
            {isDirty && !saving && <p className="text-xs text-amber-500 font-medium">Cambios sin guardar · Ctrl+S</p>}
            {!isDirty && message && <p className="text-xs text-emerald-500 font-medium">{message}</p>}
            {loading && <p className="text-sm text-slate-500">Cargando bloque...</p>}
          </div>

          <div className="rounded-md border border-slate-200 p-4 dark:border-white/10">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Versiones recientes</p>
            {versions.length === 0 ? (
              <p className="mt-2 text-xs text-slate-500">Sin versiones registradas aun.</p>
            ) : (
              <div className="mt-3 space-y-2">
                {versions.map(version => (
                  <div key={version.id} className="flex items-center justify-between rounded-md border border-slate-100 px-3 py-2 dark:border-white/10">
                    <p className="text-xs text-slate-500">#{version.id} - {new Date(version.created_at).toLocaleString()}</p>
                    <button onClick={() => rollback(version.id)} className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-primary">
                      <RotateCcw size={12} /> Restaurar
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-start gap-3 rounded-md border border-slate-200 p-4 dark:border-white/10">
            <FileText className="mt-0.5 h-4 w-4 text-primary" />
            <p className="text-xs leading-relaxed text-slate-500">
              Los heroes, menus y feeds siguen guardandose de forma estructurada para proteger la UI publica, pero esta pantalla ya no exige editar JSON manualmente.
            </p>
          </div>
        </section>

        <aside className={`rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 dark:border-white/10 dark:bg-[#111418] ${showMedia ? "block" : "hidden xl:block"}`}>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Media</p>
              <p className="text-xs text-slate-500">Copia URLs para imagenes, videos y podcasts.</p>
            </div>
            <Link href="/cms/media" className="text-[10px] font-semibold uppercase tracking-wide text-primary">
              Gestionar
            </Link>
          </div>
          {media.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-200 p-4 text-xs text-slate-500 dark:border-white/10">
              Abre la biblioteca o sube archivos en Media Manager.
            </div>
          ) : (
            <div className="max-h-[720px] space-y-3 overflow-y-auto pr-1">
              {media.map(item => (
                <div key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                  <div className="relative mb-3 aspect-video overflow-hidden rounded-md bg-slate-200 dark:bg-white/5">
                    {item.mime_type?.startsWith("image/") ? (
                      <OptimizedImage src={item.url} alt={item.alt_text || ""} fill sizes="(max-width: 768px) 100vw, 33vw" />
                    ) : (
                      <div className="flex h-full items-center justify-center text-xs font-semibold uppercase tracking-wide text-slate-400">
                        {item.mime_type?.startsWith("video/") ? "Video" : item.mime_type?.startsWith("audio/") ? "Podcast" : "Archivo"}
                      </div>
                    )}
                  </div>
                  <p className="truncate text-xs font-bold text-slate-800 dark:text-white">{item.filename || item.alt_text || item.url}</p>
                  <p className="mt-1 truncate text-[10px] text-slate-400">{item.mime_type || "archivo"}</p>
                  <button
                    type="button"
                    onClick={() => copyMediaUrl(item)}
                    className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white dark:bg-[hsl(var(--bg-primary))] dark:text-slate-900"
                  >
                    <Copy size={12} /> {copiedMediaId === item.id ? "Copiado" : "Copiar URL"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

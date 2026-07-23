"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CheckCircle,
  FileText,
  Landmark,
  Plus,
  Search,
  Tag,
  Trash2,
  Upload,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import clsx from "clsx";

const SECTIONS = [
  {
    title: "Módulos",
    items: [
      { id: "contabilidad", label: "Contabilidad", href: "/plataforma/contabilidad", icon: Landmark },
      { id: "facturacion", label: "Facturación", href: "/plataforma/facturacion", icon: FileText },
      { id: "gastos", label: "Gastos", href: "/plataforma/gastos", icon: Upload },
      { id: "documentos", label: "Documentos", href: "/plataforma/documentos", icon: FileText },
      { id: "firma", label: "Firma Digital", href: "/plataforma/firma", icon: CheckCircle },
    ],
  },
];

export default function DocumentosPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [documents, setDocuments] = useState<any[]>([]);
  const [tags, setTags] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showTagCreate, setShowTagCreate] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", file_url: "", file_name: "", file_size: 0, mime_type: "", document_type: "other", tag_ids: [] as string[] });
  const [tagForm, setTagForm] = useState({ name: "", color: "#6B7280" });

  const fetchData = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    try {
      const [d, t] = await Promise.all([
        apiFetch<any[]>("/finance-suite/documents?limit=100", { token, cache: "no-store" }),
        apiFetch<any[]>("/finance-suite/document-tags", { token, cache: "no-store" }),
      ]);
      if (Array.isArray(d)) setDocuments(d);
      if (Array.isArray(t)) setTags(t);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filtered = documents.filter((d) => {
    const matchesSearch = d.title?.toLowerCase().includes(search.toLowerCase()) || d.description?.toLowerCase().includes(search.toLowerCase());
    const matchesTag = selectedTag ? d.tags?.some((t: any) => t.id === selectedTag) : true;
    return matchesSearch && matchesTag;
  });

  const handleCreate = async () => {
    if (!token) return;
    try {
      await apiFetch("/finance-suite/documents", { token, method: "POST", body: form });
      setShowCreate(false);
      setForm({ title: "", description: "", file_url: "", file_name: "", file_size: 0, mime_type: "", document_type: "other", tag_ids: [] });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleCreateTag = async () => {
    if (!token) return;
    try {
      await apiFetch("/finance-suite/document-tags", { token, method: "POST", body: tagForm });
      setShowTagCreate(false);
      setTagForm({ name: "", color: "#6B7280" });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleDelete = async (id: string) => {
    if (!token) return;
    try {
      await apiFetch(`/finance-suite/documents/${id}`, { token, method: "DELETE" });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const typeIcons: Record<string, React.ElementType> = { invoice: FileText, contract: FileText, receipt: FileText, report: FileText, other: FileText };

  return (
    <WorkspaceLayout sidebarTitle="Documentos" sidebarSections={SECTIONS}>
      <div className="h-full overflow-y-auto bg-[#f8fafc] dark:bg-[#1E1F21] font-display scrollbar-thin">
        <div className="w-full px-4 py-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={() => router.push("/plataforma/contabilidad")} className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))]">
                <ArrowLeft size={16} />
              </button>
              <div>
                <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase">Documentos</h1>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mt-0.5">Archivo centralizado · Etiquetas · IA</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setShowTagCreate(true)} className="px-3 py-1.5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-[10px] font-semibold text-[hsl(var(--text-secondary))]"><Tag size={12} className="inline mr-1" /> Etiqueta</button>
              <button onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold shadow-sm"><Plus size={12} /> Subir</button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
              <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar documentos..." className="pl-9 pr-4 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[12px] w-full focus:ring-2 focus:ring-blue-500/20" />
            </div>
          </div>

          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              <button onClick={() => setSelectedTag(null)} className={clsx("px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide", selectedTag === null ? "bg-[hsl(var(--primary))] text-white" : "bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))]")}>Todas</button>
              {tags.map((tag) => (
                <button key={tag.id} onClick={() => setSelectedTag(tag.id)} className={clsx("px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide", selectedTag === tag.id ? "bg-[hsl(var(--primary))] text-white" : "bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))]")} style={selectedTag !== tag.id ? { borderLeft: `3px solid ${tag.color}` } : undefined}>{tag.name}</button>
              ))}
            </div>
          )}

          {showCreate && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 space-y-3">
              <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Nuevo Documento</h3>
              <input type="text" placeholder="Título" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              <input type="text" placeholder="Descripción" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              <input type="text" placeholder="URL del archivo" value={form.file_url} onChange={(e) => setForm({ ...form, file_url: e.target.value, file_name: e.target.value.split("/").pop() || "" })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              <select value={form.document_type} onChange={(e) => setForm({ ...form, document_type: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg">
                <option value="invoice">Factura</option>
                <option value="contract">Contrato</option>
                <option value="receipt">Recibo</option>
                <option value="report">Reporte</option>
                <option value="other">Otro</option>
              </select>
              <div className="flex gap-2">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-semibold">Cancelar</button>
                <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[11px] font-semibold">Guardar</button>
              </div>
            </motion.div>
          )}

          {showTagCreate && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 space-y-3">
              <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Nueva Etiqueta</h3>
              <input type="text" placeholder="Nombre" value={tagForm.name} onChange={(e) => setTagForm({ ...tagForm, name: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              <input type="color" value={tagForm.color} onChange={(e) => setTagForm({ ...tagForm, color: e.target.value })} className="w-full h-8 rounded-lg" />
              <div className="flex gap-2">
                <button onClick={() => setShowTagCreate(false)} className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-semibold">Cancelar</button>
                <button onClick={handleCreateTag} className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[11px] font-semibold">Crear</button>
              </div>
            </motion.div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {loading ? (
              <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando...</p>
            ) : filtered.length === 0 ? (
              <p className="text-sm text-[hsl(var(--text-secondary))]">Sin documentos.</p>
            ) : (
              filtered.map((doc) => {
                const Icon = typeIcons[doc.document_type] || FileText;
                return (
                  <motion.div key={doc.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 shadow-sm hover:shadow-lg hover:border-blue-500/20 transition-all group">
                    <div className="flex items-start justify-between mb-2">
                      <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] flex items-center justify-center"><Icon size={16} /></div>
                      <button onClick={() => handleDelete(doc.id)} className="opacity-0 group-hover:opacity-100 p-1.5 rounded-md hover:bg-rose-50 dark:hover:bg-rose-900/20 text-rose-500 transition-all"><Trash2 size={12} /></button>
                    </div>
                    <h3 className="text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-white truncate mb-1">{doc.title}</h3>
                    <p className="text-[10px] text-[hsl(var(--text-secondary))] line-clamp-2 mb-2">{doc.description || "Sin descripción"}</p>
                    {doc.ai_summary && (
                      <div className="mb-2 p-1.5 rounded-md bg-fuchsia-50 dark:bg-fuchsia-900/10 text-[10px] text-fuchsia-700 dark:text-fuchsia-300">
                        <span className="font-bold">IA:</span> {doc.ai_summary}
                      </div>
                    )}
                    <div className="flex flex-wrap gap-1">
                      {doc.tags?.map((t: any) => (
                        <span key={t.id} className="px-1.5 py-0.5 rounded-full text-[9px] font-bold text-white" style={{ backgroundColor: t.color }}>{t.name}</span>
                      ))}
                      {doc.ai_tags?.map((tag: string, idx: number) => (
                        <span key={idx} className="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/20 dark:text-fuchsia-300">{tag}</span>
                      ))}
                    </div>
                    <a href={doc.file_url} target="_blank" rel="noopener noreferrer" className="mt-2 block text-[10px] font-bold text-[hsl(var(--primary))] hover:underline">Abrir archivo →</a>
                  </motion.div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </WorkspaceLayout>
  );
}

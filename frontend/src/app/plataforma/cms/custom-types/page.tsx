"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import {Puzzle, Plus, Trash2, ChevronRight} from "lucide-react";
import SidePanel from "@/components/ui/SidePanel";

interface CustomType { id: string; type_key: string; label: string; label_plural: string | null; icon: string | null; supports: string[]; fields_schema: Record<string, unknown>; }
interface CustomEntry { id: string; type_key: string; slug: string; title: string; excerpt: string | null; status: string; version: number; view_count: number; created_at: string; }

export default function CustomTypesPage() {
  const [types, setTypes] = useState<CustomType[]>([]);
  const [entries, setEntries] = useState<CustomEntry[]>([]);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTypeForm, setShowTypeForm] = useState(false);
  const [showEntryForm, setShowEntryForm] = useState(false);
  const [pendingArchiveEntry, setPendingArchiveEntry] = useState<CustomEntry | null>(null);
  const [typeForm, setTypeForm] = useState({ type_key: "", label: "", label_plural: "" });
  const [entryForm, setEntryForm] = useState({ slug: "", title: "", content_html: "", status: "draft" });

  const loadTypes = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<CustomType[]>(`/cms/v2/custom-types?site_key=${SITE_KEY}`, { silent: true });
      setTypes(Array.isArray(data) ? data : []);
    } catch { setTypes([]); }
    setLoading(false);
  };

  const loadEntries = async (typeKey: string) => {
    setSelectedType(typeKey);
    try {
      const data = await apiFetch<CustomEntry[]>(`/cms/v2/custom-entries?site_key=${SITE_KEY}&type_key=${typeKey}`, { silent: true });
      setEntries(Array.isArray(data) ? data : []);
    } catch { setEntries([]); }
  };

  useEffect(() => { loadTypes(); }, []);

  const createType = async () => {
    if (!typeForm.type_key || !typeForm.label) return;
    await apiFetch("/cms/v2/custom-types", { method: "POST", body: { site_key: SITE_KEY, supports: ["title", "editor", "excerpt"], ...typeForm }, silent: true });
    setTypeForm({ type_key: "", label: "", label_plural: "" });
    setShowTypeForm(false);
    loadTypes();
  };

  const createEntry = async () => {
    if (!entryForm.slug || !entryForm.title || !selectedType) return;
    await apiFetch("/cms/v2/custom-entries", { method: "POST", body: { site_key: SITE_KEY, type_key: selectedType, ...entryForm }, silent: true });
    setEntryForm({ slug: "", title: "", content_html: "", status: "draft" });
    setShowEntryForm(false);
    loadEntries(selectedType);
  };

  const deleteEntry = async () => {
    if (!pendingArchiveEntry) return;
    await apiFetch(`/cms/v2/custom-entries/${pendingArchiveEntry.id}`, { method: "DELETE", silent: true });
    setPendingArchiveEntry(null);
    if (selectedType) loadEntries(selectedType);
  };

  const statusColors: Record<string, string> = {
    draft: "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]", in_review: "bg-amber-100 text-amber-700",
    approved: "bg-blue-100 text-[hsl(var(--primary))]", published: "bg-green-100 text-[hsl(var(--secondary))]",
    archived: "bg-red-100 text-[hsl(var(--destructive))]", obsolete: "bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]",
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Puzzle size={24} className="text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl font-bold">Tipos de Contenido Custom</h1>
            <p className="text-sm text-[hsl(var(--text-secondary))]">Politicas, Wiki, Glosario, Noticias, Activos y mas</p>
          </div>
        </div>
        <button onClick={() => setShowTypeForm(!showTypeForm)} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">
          <Plus size={14} /> Nuevo Tipo
        </button>
      </div>

      {showTypeForm && (
        <div className="p-4 border rounded-xl bg-[hsl(var(--surface-1))] space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <input placeholder="type_key (ej: policy)" value={typeForm.type_key} onChange={e => setTypeForm(f => ({ ...f, type_key: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
            <input placeholder="Label (ej: Politica)" value={typeForm.label} onChange={e => setTypeForm(f => ({ ...f, label: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
            <input placeholder="Label plural (ej: Politicas)" value={typeForm.label_plural} onChange={e => setTypeForm(f => ({ ...f, label_plural: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
          </div>
          <div className="flex gap-2">
            <button onClick={createType} className="px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">Crear</button>
            <button onClick={() => setShowTypeForm(false)} className="px-4 py-2 text-sm font-medium rounded-lg border">Cancelar</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="md:col-span-1 border rounded-xl p-4 space-y-2">
          <p className="text-xs font-medium text-[hsl(var(--text-secondary))] mb-3">TIPOS</p>
          {loading ? <p className="text-xs text-[hsl(var(--text-secondary))]">Cargando...</p> : types.map(t => (
            <button key={t.id} onClick={() => loadEntries(t.type_key)} className={`w-full text-left px-3 py-2.5 rounded-lg text-sm flex items-center justify-between ${selectedType === t.type_key ? "bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] font-medium" : "hover:bg-[hsl(var(--surface-1))]"}`}>
              <span>{t.label}</span>
              <ChevronRight size={12} />
            </button>
          ))}
        </div>

        <div className="md:col-span-3">
          {selectedType ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-medium">{types.find(t => t.type_key === selectedType)?.label || selectedType}</h2>
                <button onClick={() => setShowEntryForm(!showEntryForm)} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-[hsl(var(--primary))] text-white">
                  <Plus size={12} /> Nueva Entrada
                </button>
              </div>

              {showEntryForm && (
                <div className="p-4 border rounded-xl bg-[hsl(var(--surface-1))] space-y-3">
                  <input placeholder="slug" value={entryForm.slug} onChange={e => setEntryForm(f => ({ ...f, slug: e.target.value }))} className="w-full px-3 py-2 text-sm border rounded-lg" />
                  <input placeholder="Titulo" value={entryForm.title} onChange={e => setEntryForm(f => ({ ...f, title: e.target.value }))} className="w-full px-3 py-2 text-sm border rounded-lg" />
                  <textarea placeholder="Contenido HTML..." value={entryForm.content_html} onChange={e => setEntryForm(f => ({ ...f, content_html: e.target.value }))} className="w-full px-3 py-2 text-sm border rounded-lg h-32" />
                  <div className="flex gap-2">
                    <button onClick={createEntry} className="px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">Crear</button>
                    <button onClick={() => setShowEntryForm(false)} className="px-4 py-2 text-sm font-medium rounded-lg border">Cancelar</button>
                  </div>
                </div>
              )}

              <div className="overflow-x-auto border rounded-xl">
                <table className="w-full text-sm">
                  <thead className="bg-[hsl(var(--surface-1))] border-b">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Titulo</th>
                      <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Slug</th>
                      <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Estado</th>
                      <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">v</th>
                      <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Visitas</th>
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {entries.length === 0 ? (
                      <tr><td colSpan={6} className="px-4 py-8 text-center text-[hsl(var(--text-secondary))]">Sin entradas</td></tr>
                    ) : entries.map(e => (
                      <tr key={e.id} className="hover:bg-[hsl(var(--surface-1))]/50">
                        <td className="px-4 py-3 font-medium">{e.title}</td>
                        <td className="px-4 py-3 text-xs text-[hsl(var(--text-secondary))] font-mono">{e.slug}</td>
                        <td className="px-4 py-3"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${statusColors[e.status] || ""}`}>{e.status}</span></td>
                        <td className="px-4 py-3 text-xs text-[hsl(var(--text-secondary))]">v{e.version}</td>
                        <td className="px-4 py-3 text-xs text-[hsl(var(--text-secondary))]">{e.view_count}</td>
                        <td className="px-4 py-3">
                          <button onClick={() => setPendingArchiveEntry(e)} className="p-1 rounded hover:bg-red-50"><Trash2 size={12} className="text-[hsl(var(--destructive))]" /></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-[hsl(var(--text-secondary))] text-sm">Selecciona un tipo para ver sus entradas</div>
          )}
        </div>
      </div>
      <SidePanel
        isOpen={!!pendingArchiveEntry}
        onClose={() => setPendingArchiveEntry(null)}
        title="Archivar entrada"
        subtitle={pendingArchiveEntry?.title}
      >
        <div className="space-y-4">
          <p className="text-sm text-[hsl(var(--text-secondary))]">La entrada quedara archivada dentro del tipo seleccionado.</p>
          <div className="flex gap-2">
            <button onClick={() => setPendingArchiveEntry(null)} className="flex-1 rounded-lg border px-3 py-2 text-sm font-medium">Cancelar</button>
            <button onClick={deleteEntry} className="flex-1 rounded-lg bg-amber-500 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600">Archivar</button>
          </div>
        </div>
      </SidePanel>
    </div>
  );
}
import { SITE_KEY } from "@/lib/site-config";

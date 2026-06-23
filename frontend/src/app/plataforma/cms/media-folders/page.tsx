"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { FolderTree, Plus, ChevronRight, ChevronDown } from "lucide-react";

interface MediaFolder { id: string; name: string; slug: string; path: string; parent_id: string | null; }

export default function MediaFoldersPage() {
  const [folders, setFolders] = useState<MediaFolder[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", slug: "", parent_id: "" });

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<MediaFolder[]>("/cms/v2/media-folders?site_key=faro", { silent: true });
      setFolders(Array.isArray(data) ? data : []);
    } catch { setFolders([]); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.name || !form.slug) return;
    await apiFetch("/cms/v2/media-folders", { method: "POST", body: { site_key: "faro", ...form, parent_id: form.parent_id || undefined }, silent: true });
    setForm({ name: "", slug: "", parent_id: "" });
    setShowForm(false);
    load();
  };

  const buildTree = (parentId: string | null = null): MediaFolder[] => {
    return folders.filter(f => f.parent_id === parentId).sort((a, b) => a.name.localeCompare(b.name));
  };

  const FolderNode = ({ folder, depth = 0 }: { folder: MediaFolder; depth?: number }) => {
    const [expanded, setExpanded] = useState(true);
    const children = buildTree(folder.id);
    return (
      <div>
        <div className="flex items-center gap-2 py-1.5 px-2 hover:bg-slate-50 rounded-lg" style={{ paddingLeft: `${depth * 20 + 8}px` }}>
          {children.length > 0 ? (
            <button onClick={() => setExpanded(!expanded)} className="p-0.5">
              {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </button>
          ) : <div className="w-3" />}
          <FolderTree size={14} className="text-amber-500" />
          <span className="text-sm">{folder.name}</span>
          <span className="text-[10px] text-slate-400 font-mono">{folder.path}</span>
        </div>
        {expanded && children.map(child => <FolderNode key={child.id} folder={child} depth={depth + 1} />)}
      </div>
    );
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FolderTree size={24} className="text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl font-bold">Carpetas de Media</h1>
            <p className="text-sm text-slate-500">{folders.length} carpetas</p>
          </div>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">
          <Plus size={14} /> Nueva Carpeta
        </button>
      </div>

      {showForm && (
        <div className="p-4 border rounded-xl bg-slate-50 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <input placeholder="Nombre" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
            <input placeholder="slug" value={form.slug} onChange={e => setForm(f => ({ ...f, slug: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
            <select value={form.parent_id} onChange={e => setForm(f => ({ ...f, parent_id: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg">
              <option value="">Raiz</option>
              {folders.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </div>
          <div className="flex gap-2">
            <button onClick={create} className="px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">Crear</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm font-medium rounded-lg border">Cancelar</button>
          </div>
        </div>
      )}

      <div className="border rounded-xl p-4 bg-white">
        {loading ? <div className="py-8 text-center text-slate-400">Cargando...</div> : folders.length === 0 ? (
          <div className="py-8 text-center text-slate-400">Sin carpetas</div>
        ) : buildTree(null).map(folder => <FolderNode key={folder.id} folder={folder} />)}
      </div>
    </div>
  );
}

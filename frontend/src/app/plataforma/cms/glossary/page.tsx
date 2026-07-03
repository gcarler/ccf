"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import {BookOpen, Plus, Search} from "lucide-react";

interface GlossaryTerm { id: string; term: string; definition: string; aliases: string[]; category: string | null; language: string; }

export default function GlossaryPage() {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ term: "", definition: "", aliases: "", category: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = search ? `?search=${encodeURIComponent(search)}` : "";
      const data = await apiFetch<GlossaryTerm[]>(`/cms/v2/glossary?site_key=ccf${params}`, { silent: true });
      setTerms(Array.isArray(data) ? data : []);
    } catch { setTerms([]); }
    setLoading(false);
  }, [search]);

  useEffect(() => { load(); }, [search, load]);

  const create = async () => {
    if (!form.term || !form.definition) return;
    await apiFetch("/cms/v2/glossary", { method: "POST", body: { site_key: "ccf", ...form, aliases: form.aliases.split(",").map(a => a.trim()).filter(Boolean) }, silent: true });
    setForm({ term: "", definition: "", aliases: "", category: "" });
    setShowForm(false);
    load();
  };

  const grouped = terms.reduce((acc, t) => { const cat = t.category || "General"; (acc[cat] = acc[cat] || []).push(t); return acc; }, {} as Record<string, GlossaryTerm[]>);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BookOpen size={24} className="text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl font-bold">Glosario Corporativo</h1>
            <p className="text-sm text-[hsl(var(--text-secondary))]">{terms.length} terminos definidos</p>
          </div>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">
          <Plus size={14} /> Nuevo Termino
        </button>
      </div>

      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
        <input placeholder="Buscar termino..." value={search} onChange={e => setSearch(e.target.value)} className="w-full pl-10 pr-4 py-2.5 text-sm border rounded-xl" />
      </div>

      {showForm && (
        <div className="p-4 border rounded-xl bg-[hsl(var(--surface-1))] space-y-3">
          <input placeholder="Termino" value={form.term} onChange={e => setForm(f => ({ ...f, term: e.target.value }))} className="w-full px-3 py-2 text-sm border rounded-lg" />
          <textarea placeholder="Definicion..." value={form.definition} onChange={e => setForm(f => ({ ...f, definition: e.target.value }))} className="w-full px-3 py-2 text-sm border rounded-lg h-24" />
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Aliases (separados por coma)" value={form.aliases} onChange={e => setForm(f => ({ ...f, aliases: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
            <input placeholder="Categoria" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
          </div>
          <div className="flex gap-2">
            <button onClick={create} className="px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">Crear</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm font-medium rounded-lg border">Cancelar</button>
          </div>
        </div>
      )}

      {loading ? <div className="py-12 text-center text-[hsl(var(--text-secondary))]">Cargando...</div> : Object.entries(grouped).map(([cat, catTerms]) => (
        <div key={cat}>
          <h3 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-3">{cat}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {catTerms.map(t => (
              <div key={t.id} className="p-4 border rounded-xl bg-[hsl(var(--bg-primary))] hover:shadow-sm transition-shadow">
                <div className="flex items-start justify-between">
                  <h4 className="font-bold text-sm">{t.term}</h4>
                  {t.aliases.length > 0 && <span className="text-[10px] bg-[hsl(var(--surface-2))] px-1.5 py-0.5 rounded">{t.aliases.join(", ")}</span>}
                </div>
                <p className="text-xs text-[hsl(var(--text-secondary))] mt-2 leading-relaxed">{t.definition}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

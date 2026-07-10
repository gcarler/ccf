"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import {Search, Star, Plus, TrendingUp} from "lucide-react";

interface SearchResult { entity_type: string; entity_id: string; entity_slug: string; title: string; category: string | null; boost_score: number; }
interface Promotion { id: string; query_text: string; entity_type: string; entity_id: string; entity_slug: string | null; title: string | null; boost_score: number; is_active: boolean; }

export default function SearchAdminPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [promoted, setPromoted] = useState<Promotion[]>([]);
  const [_loading, setLoading] = useState(false);
  const [showPromoForm, setShowPromoForm] = useState(false);
  const [promoForm, setPromoForm] = useState({ query_text: "", entity_type: "cms_page", entity_id: "", title: "", boost_score: 100 });

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await apiFetch<{ results: SearchResult[]; promoted: Promotion[] }>(`/cms/v2/search`, { method: "POST", body: { site_key: SITE_KEY, query }, silent: true });
      setResults(data?.results || []);
    } catch { toast.error("Error al cargar datos"); setResults([]); }
    setLoading(false);
  };

  const loadPromos = async () => {
    try {
      const data = await apiFetch<Promotion[]>("/cms/v2/search/promotions?site_key=${SITE_KEY}", { silent: true });
      setPromoted(Array.isArray(data) ? data : []);
    } catch { toast.error("Error al cargar datos"); setPromoted([]); }
  };

  useEffect(() => { loadPromos(); }, []);

  const createPromo = async () => {
    if (!promoForm.query_text || !promoForm.entity_id) return;
    await apiFetch("/cms/v2/search/promotions", { method: "POST", body: { site_key: SITE_KEY, ...promoForm }, silent: true });
    setPromoForm({ query_text: "", entity_type: "cms_page", entity_id: "", title: "", boost_score: 100 });
    setShowPromoForm(false);
    loadPromos();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Search size={24} className="text-[hsl(var(--primary))]" />
        <div>
          <h1 className="text-xl font-bold">Busqueda y Promociones</h1>
          <p className="text-sm text-[hsl(var(--text-secondary))]">Gestionar resultados de busqueda y rankings</p>
        </div>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
          <input placeholder="Buscar contenido..." value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && search()} className="w-full pl-10 pr-4 py-2.5 text-sm border rounded-xl" />
        </div>
        <button onClick={search} className="px-5 py-2.5 text-sm font-medium rounded-xl bg-[hsl(var(--primary))] text-white">Buscar</button>
      </div>

      {results.length > 0 && (
        <div className="border rounded-xl overflow-hidden">
          <div className="px-4 py-3 bg-[hsl(var(--surface-1))] border-b text-xs font-medium text-[hsl(var(--text-secondary))]">{results.length} resultados para &quot;{query}&quot;</div>
          <div className="divide-y">
            {results.map((r, i) => (
              <div key={i} className="px-4 py-3 flex items-center gap-3 hover:bg-[hsl(var(--surface-1))]/50">
                <span className="text-xs font-bold text-[hsl(var(--text-secondary))] w-6">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{r.title || r.entity_slug}</p>
                  <p className="text-xs text-[hsl(var(--text-secondary))]">{r.entity_type} · {r.entity_slug}</p>
                </div>
                {r.boost_score > 0 && <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-bold">+{r.boost_score}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h2 className="font-medium flex items-center gap-2"><Star size={16} /> Resultados Promocionados</h2>
        <button onClick={() => setShowPromoForm(!showPromoForm)} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-[hsl(var(--primary))] text-white">
          <Plus size={12} /> Promocionar
        </button>
      </div>

      {showPromoForm && (
        <div className="p-4 border rounded-xl bg-[hsl(var(--surface-1))] space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Keyword (ej: vacaciones)" value={promoForm.query_text} onChange={e => setPromoForm(f => ({ ...f, query_text: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
            <input placeholder="Entity ID" value={promoForm.entity_id} onChange={e => setPromoForm(f => ({ ...f, entity_id: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
            <input placeholder="Titulo visible" value={promoForm.title} onChange={e => setPromoForm(f => ({ ...f, title: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg" />
            <input type="number" placeholder="Boost score" value={promoForm.boost_score} onChange={e => setPromoForm(f => ({ ...f, boost_score: parseInt(e.target.value) || 100 }))} className="px-3 py-2 text-sm border rounded-lg" />
          </div>
          <div className="flex gap-2">
            <button onClick={createPromo} className="px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">Crear</button>
            <button onClick={() => setShowPromoForm(false)} className="px-4 py-2 text-sm font-medium rounded-lg border">Cancelar</button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {promoted.map(p => (
          <div key={p.id} className="flex items-center gap-3 p-3 border rounded-xl bg-[hsl(var(--bg-primary))]">
            <TrendingUp size={14} className="text-amber-500" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{p.title || p.entity_slug}</p>
              <p className="text-xs text-[hsl(var(--text-secondary))]">&quot;{p.query_text}&quot; → {p.entity_type}/{p.entity_id}</p>
            </div>
            <span className="text-xs font-bold bg-amber-100 text-amber-700 px-2 py-0.5 rounded">+{p.boost_score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
import { SITE_KEY } from "@/lib/site-config";
import { toast } from "sonner";

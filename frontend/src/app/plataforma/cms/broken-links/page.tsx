"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { AlertTriangle, CheckCircle, ExternalLink } from "lucide-react";

interface BrokenLink { id: string; source_url: string; target_url: string; status_code: number | null; error_message: string | null; is_broken: boolean; resolved_at: string | null; checked_at: string; }

export default function BrokenLinksPage() {
  const [links, setLinks] = useState<BrokenLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"broken" | "resolved" | "all">("broken");

  const load = async () => {
    setLoading(true);
    try {
      const params = filter === "broken" ? "?resolved=false" : filter === "resolved" ? "?resolved=true" : "";
      const data = await apiFetch<BrokenLink[]>(`/cms/v2/broken-links?site_key=faro${params}`, { silent: true });
      setLinks(Array.isArray(data) ? data : []);
    } catch { setLinks([]); }
    setLoading(false);
  };

  useEffect(() => { load(); }, [filter, load]);

  const resolve = async (id: string) => {
    await apiFetch(`/cms/v2/broken-links/${id}/resolve`, { method: "POST", silent: true });
    load();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <AlertTriangle size={24} className="text-[hsl(var(--primary))]" />
        <div>
          <h1 className="text-xl font-bold">Enlaces Rotos</h1>
          <p className="text-sm text-slate-500">Escaneo periodico de links internos muertos</p>
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={() => setFilter("broken")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "broken" ? "bg-red-100 text-red-700" : "border hover:bg-slate-50"}`}>Rotos ({links.filter(l => l.is_broken && !l.resolved_at).length})</button>
        <button onClick={() => setFilter("resolved")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "resolved" ? "bg-green-100 text-green-700" : "border hover:bg-slate-50"}`}>Resueltos</button>
        <button onClick={() => setFilter("all")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "all" ? "bg-slate-100" : "border hover:bg-slate-50"}`}>Todos</button>
      </div>

      <div className="space-y-2">
        {loading ? <div className="py-12 text-center text-slate-400">Cargando...</div> : links.length === 0 ? (
          <div className="py-12 text-center text-slate-400">Sin enlaces {filter === "broken" ? "rotos" : ""}</div>
        ) : links.map(l => (
          <div key={l.id} className={`flex items-center gap-4 p-4 border rounded-xl ${l.resolved_at ? "bg-green-50/50 border-green-200" : "bg-white"}`}>
            <div className="shrink-0">
              {l.resolved_at ? <CheckCircle size={18} className="text-green-500" /> : <AlertTriangle size={18} className="text-red-400" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{l.target_url}</p>
              <p className="text-xs text-slate-400 mt-0.5">Fuente: {l.source_url}</p>
              {l.error_message && <p className="text-xs text-red-500 mt-1">{l.error_message}</p>}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {l.status_code && <span className="text-[10px] font-bold bg-slate-100 px-2 py-0.5 rounded">{l.status_code}</span>}
              {!l.resolved_at && (
                <button onClick={() => resolve(l.id)} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-green-100 text-green-700 hover:bg-green-200">Marcar resuelto</button>
              )}
              <a href={l.target_url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg hover:bg-slate-100"><ExternalLink size={12} className="text-slate-400" /></a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

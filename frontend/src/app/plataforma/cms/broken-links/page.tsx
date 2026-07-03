"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { AlertTriangle, CheckCircle, ExternalLink } from "lucide-react";

interface BrokenLink { id: string; source_url: string; target_url: string; status_code: number | null; error_message: string | null; is_broken: boolean; resolved_at: string | null; checked_at: string; }

export default function BrokenLinksPage() {
  const [links, setLinks] = useState<BrokenLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"broken" | "resolved" | "all">("broken");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = filter === "broken" ? "?resolved=false" : filter === "resolved" ? "?resolved=true" : "";
      const data = await apiFetch<BrokenLink[]>(`/cms/v2/broken-links?site_key=ccf${params}`, { silent: true });
      setLinks(Array.isArray(data) ? data : []);
    } catch { setLinks([]); }
    setLoading(false);
  }, [filter]);

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
          <p className="text-sm text-[hsl(var(--text-secondary))]">Escaneo periodico de links internos muertos</p>
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={() => setFilter("broken")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "broken" ? "bg-red-100 text-[hsl(var(--destructive))]" : "border hover:bg-[hsl(var(--surface-1))]"}`}>Rotos ({links.filter(l => l.is_broken && !l.resolved_at).length})</button>
        <button onClick={() => setFilter("resolved")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "resolved" ? "bg-green-100 text-[hsl(var(--secondary))]" : "border hover:bg-[hsl(var(--surface-1))]"}`}>Resueltos</button>
        <button onClick={() => setFilter("all")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "all" ? "bg-[hsl(var(--surface-2))]" : "border hover:bg-[hsl(var(--surface-1))]"}`}>Todos</button>
      </div>

      <div className="space-y-2">
        {loading ? <div className="py-12 text-center text-[hsl(var(--text-secondary))]">Cargando...</div> : links.length === 0 ? (
          <div className="py-12 text-center text-[hsl(var(--text-secondary))]">Sin enlaces {filter === "broken" ? "rotos" : ""}</div>
        ) : links.map(l => (
          <div key={l.id} className={`flex items-center gap-4 p-4 border rounded-xl ${l.resolved_at ? "bg-green-50/50 border-green-200" : "bg-[hsl(var(--bg-primary))]"}`}>
            <div className="shrink-0">
              {l.resolved_at ? <CheckCircle size={18} className="text-[hsl(var(--secondary))]" /> : <AlertTriangle size={18} className="text-[hsl(var(--destructive))]" />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{l.target_url}</p>
              <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">Fuente: {l.source_url}</p>
              {l.error_message && <p className="text-xs text-[hsl(var(--destructive))] mt-1">{l.error_message}</p>}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {l.status_code && <span className="text-[10px] font-bold bg-[hsl(var(--surface-2))] px-2 py-0.5 rounded">{l.status_code}</span>}
              {!l.resolved_at && (
                <button onClick={() => resolve(l.id)} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-green-100 text-[hsl(var(--secondary))] hover:bg-green-200">Marcar resuelto</button>
              )}
              <a href={l.target_url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-2))]"><ExternalLink size={12} className="text-[hsl(var(--text-secondary))]" /></a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

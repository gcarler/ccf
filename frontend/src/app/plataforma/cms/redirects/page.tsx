"use client";

import { useEffect, useState, useMemo } from "react";
import { apiFetch } from "@/lib/http";
import { RotateCcw, Plus, Trash2, Search, Link as LinkIcon } from "lucide-react";
import SidePanel from "@/components/ui/SidePanel";
import { SITE_KEY } from "@/lib/site-config";
import { toast } from "sonner";
import clsx from "clsx";

interface Redirect { id: string; from_path: string; to_path: string; status_code: number; hit_count: number; }

export default function RedirectsPage() {
  const [redirects, setRedirects] = useState<Redirect[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Redirect | null>(null);
  const [form, setForm] = useState({ from_path: "", to_path: "", status_code: 301 });
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "301" | "302">("all");

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<Redirect[]>(`/cms/v2/redirects?site_key=${SITE_KEY}`, { silent: true });
      setRedirects(Array.isArray(data) ? data : []);
    } catch { 
      toast.error("Error al cargar datos"); 
      setRedirects([]); 
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.from_path || !form.to_path) return;
    try {
      await apiFetch("/cms/v2/redirects", { method: "POST", body: { site_key: SITE_KEY, ...form }, silent: true });
      toast.success("Redirección creada con éxito");
      setForm({ from_path: "", to_path: "", status_code: 301 });
      setShowForm(false);
      load();
    } catch {
      toast.error("Error al crear redirección");
    }
  };

  const remove = async () => {
    if (!pendingDelete) return;
    try {
      await apiFetch(`/cms/v2/redirects/${pendingDelete.id}`, { method: "DELETE", silent: true });
      toast.success("Redirección eliminada");
      setPendingDelete(null);
      load();
    } catch {
      toast.error("Error al eliminar redirección");
    }
  };

  const filteredRedirects = useMemo(() => {
    return redirects.filter(r => {
      const matchSearch = (r.from_path || '').toLowerCase().includes(search.toLowerCase()) || (r.to_path || '').toLowerCase().includes(search.toLowerCase());
      const matchType = typeFilter === "all" || r.status_code.toString() === typeFilter;
      return matchSearch && matchType;
    });
  }, [redirects, search, typeFilter]);

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))]">
      <header className="h-14 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-4 gap-4 shrink-0">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <RotateCcw size={18} className="text-[hsl(var(--primary))] shrink-0" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white truncate">
            Redirecciones
          </h2>
          <span className="text-2xs font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full shrink-0">
            {redirects.length}
          </span>
        </div>

        <div className="relative shrink-0 hidden md:block">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
          <input
            type="text"
            placeholder="Buscar por URL..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 border border-transparent rounded-lg text-sm focus:border-[hsl(var(--primary))/30%] focus:ring-1 focus:ring-[hsl(var(--primary))/30%] w-56 transition-all outline-none"
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as any)}
          className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 px-3 py-1.5 text-sm shrink-0 outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/20%]"
        >
          <option value="all">Todos</option>
          <option value="301">301 - Permanente</option>
          <option value="302">302 - Temporal</option>
        </select>

        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-[hsl(var(--primary))] text-white px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--primary))/20%] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 shrink-0"
        >
          <Plus size={14} /> Nueva
        </button>
      </header>

      {showForm && (
        <div className="p-4 border-b border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 space-y-3 shrink-0">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input placeholder="/ruta-antigua" value={form.from_path} onChange={e => setForm(f => ({ ...f, from_path: e.target.value }))} className="px-3 py-2 text-sm border border-[hsl(var(--border))] dark:border-white/10 rounded-lg font-mono bg-[hsl(var(--bg-primary))] dark:bg-white/5 outline-none focus:border-[hsl(var(--primary))]" />
            <input placeholder="/ruta-nueva" value={form.to_path} onChange={e => setForm(f => ({ ...f, to_path: e.target.value }))} className="px-3 py-2 text-sm border border-[hsl(var(--border))] dark:border-white/10 rounded-lg font-mono bg-[hsl(var(--bg-primary))] dark:bg-white/5 outline-none focus:border-[hsl(var(--primary))]" />
            <select value={form.status_code} onChange={e => setForm(f => ({ ...f, status_code: parseInt(e.target.value) }))} className="px-3 py-2 text-sm border border-[hsl(var(--border))] dark:border-white/10 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 outline-none focus:border-[hsl(var(--primary))]">
              <option value={301}>301 - Permanente</option>
              <option value={302}>302 - Temporal</option>
            </select>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide rounded-lg border border-[hsl(var(--border))] dark:border-white/10 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors">Cancelar</button>
            <button onClick={create} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide rounded-lg bg-[hsl(var(--primary))] text-white hover:opacity-90 transition-opacity">Crear Redirección</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-16 w-full rounded-xl bg-[hsl(var(--surface-1))] dark:bg-white/5 animate-pulse" />
            ))}
          </div>
        ) : filteredRedirects.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-70">
            <div className="size-12 rounded-xl bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]">
              <LinkIcon size={24} />
            </div>
            <div>
              <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white">Sin redirecciones</p>
              <p className="text-sm text-[hsl(var(--text-secondary))] mt-1">Crea tu primera redirección para gestionar el tráfico.</p>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-transparent">
            <table className="w-full text-left">
              <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5 border-b border-[hsl(var(--border))] dark:border-white/10">
                <tr>
                  <th className="px-4 py-3 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Desde</th>
                  <th className="px-4 py-3 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Hacia</th>
                  <th className="px-4 py-3 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Código</th>
                  <th className="px-4 py-3 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden sm:table-cell">Hits</th>
                  <th className="px-4 py-3 w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                {filteredRedirects.map(r => (
                  <tr key={r.id} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] transition-colors group">
                    <td className="px-4 py-3 font-mono text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{r.from_path}</td>
                    <td className="px-4 py-3 font-mono text-sm text-[hsl(var(--primary))]">{r.to_path}</td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        "px-2 py-0.5 rounded-full text-2xs font-bold uppercase tracking-wide",
                        r.status_code === 301 
                          ? "bg-[hsl(var(--success-muted))] text-[hsl(var(--success-text))] dark:bg-[hsl(var(--success))]/20 dark:text-[hsl(var(--success))]" 
                          : "bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))] dark:bg-[hsl(var(--warning))]/20 dark:text-[hsl(var(--warning))]"
                      )}>
                        {r.status_code}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-[hsl(var(--text-secondary))] hidden sm:table-cell">{r.hit_count}</td>
                    <td className="px-4 py-3">
                      <button 
                        onClick={() => setPendingDelete(r)} 
                        className="p-2 rounded-md hover:bg-[hsl(var(--danger-muted))] dark:hover:bg-[hsl(var(--danger))]/20 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                        title="Eliminar"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <SidePanel
        isOpen={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Eliminar redirección"
        subtitle={pendingDelete?.from_path}
      >
        <div className="space-y-4">
          <div className="rounded-lg border border-[hsl(var(--danger)/25%)] bg-danger-soft dark:bg-[hsl(var(--danger))]/10 p-4">
            <p className="text-sm text-danger-text dark:text-[hsl(var(--danger))]">
              ¿Estás seguro de eliminar esta redirección? El tráfico hacia <span className="font-mono font-bold">{pendingDelete?.from_path}</span> dejará de ser redirigido.
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setPendingDelete(null)} className="flex-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide transition-colors hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5">
              Cancelar
            </button>
            <button onClick={remove} className="flex-1 rounded-lg bg-[hsl(var(--danger))] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-white transition-opacity hover:opacity-90">
              Eliminar
            </button>
          </div>
        </div>
      </SidePanel>
    </div>
  );
}

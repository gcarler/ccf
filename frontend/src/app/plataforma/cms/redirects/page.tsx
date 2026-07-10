"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import {RotateCcw, Plus, Trash2} from "lucide-react";
import SidePanel from "@/components/ui/SidePanel";

interface Redirect { id: string; from_path: string; to_path: string; status_code: number; hit_count: number; }

export default function RedirectsPage() {
  const [redirects, setRedirects] = useState<Redirect[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Redirect | null>(null);
  const [form, setForm] = useState({ from_path: "", to_path: "", status_code: 301 });

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<Redirect[]>("/cms/v2/redirects?site_key=${SITE_KEY}", { silent: true });
      setRedirects(Array.isArray(data) ? data : []);
    } catch { setRedirects([]); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.from_path || !form.to_path) return;
    await apiFetch("/cms/v2/redirects", { method: "POST", body: { site_key: SITE_KEY, ...form }, silent: true });
    setForm({ from_path: "", to_path: "", status_code: 301 });
    setShowForm(false);
    load();
  };

  const remove = async () => {
    if (!pendingDelete) return;
    await apiFetch(`/cms/v2/redirects/${pendingDelete.id}`, { method: "DELETE", silent: true });
    setPendingDelete(null);
    load();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <RotateCcw size={24} className="text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl font-bold">Redirecciones</h1>
            <p className="text-sm text-[hsl(var(--text-secondary))]">{redirects.length} redirecciones activas</p>
          </div>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">
          <Plus size={14} /> Nueva Redireccion
        </button>
      </div>

      {showForm && (
        <div className="p-4 border rounded-xl bg-[hsl(var(--surface-1))] space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <input placeholder="/ruta-antigua" value={form.from_path} onChange={e => setForm(f => ({ ...f, from_path: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg font-mono" />
            <input placeholder="/ruta-nueva" value={form.to_path} onChange={e => setForm(f => ({ ...f, to_path: e.target.value }))} className="px-3 py-2 text-sm border rounded-lg font-mono" />
            <select value={form.status_code} onChange={e => setForm(f => ({ ...f, status_code: parseInt(e.target.value) }))} className="px-3 py-2 text-sm border rounded-lg">
              <option value={301}>301 - Permanente</option>
              <option value={302}>302 - Temporal</option>
            </select>
          </div>
          <div className="flex gap-2">
            <button onClick={create} className="px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">Crear</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm font-medium rounded-lg border">Cancelar</button>
          </div>
        </div>
      )}

      <div className="overflow-x-auto border rounded-xl">
        <table className="w-full text-sm">
          <thead className="bg-[hsl(var(--surface-1))] border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Desde</th>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Hacia</th>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Codigo</th>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Hits</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-[hsl(var(--text-secondary))]">Cargando...</td></tr>
            ) : redirects.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-[hsl(var(--text-secondary))]">Sin redirecciones</td></tr>
            ) : redirects.map(r => (
              <tr key={r.id} className="hover:bg-[hsl(var(--surface-1))]/50">
                <td className="px-4 py-3 font-mono text-xs">{r.from_path}</td>
                <td className="px-4 py-3 font-mono text-xs text-[hsl(var(--primary))]">{r.to_path}</td>
                <td className="px-4 py-3"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${r.status_code === 301 ? "bg-green-100 text-[hsl(var(--secondary))]" : "bg-amber-100 text-amber-700"}`}>{r.status_code}</span></td>
                <td className="px-4 py-3 text-xs text-[hsl(var(--text-secondary))]">{r.hit_count}</td>
                <td className="px-4 py-3">
                  <button onClick={() => setPendingDelete(r)} className="p-1 rounded hover:bg-red-50"><Trash2 size={12} className="text-[hsl(var(--destructive))]" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <SidePanel
        isOpen={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Eliminar redireccion"
        subtitle={pendingDelete?.from_path}
      >
        <div className="space-y-4">
          <p className="text-sm text-[hsl(var(--text-secondary))]">Esta accion eliminara la redireccion seleccionada.</p>
          <div className="flex gap-2">
            <button onClick={() => setPendingDelete(null)} className="flex-1 rounded-lg border px-3 py-2 text-sm font-medium">Cancelar</button>
            <button onClick={remove} className="flex-1 rounded-lg bg-[hsl(var(--destructive))] px-3 py-2 text-sm font-medium text-white hover:bg-[hsl(var(--destructive))]">Eliminar</button>
          </div>
        </div>
      </SidePanel>
    </div>
  );
}
import { SITE_KEY } from "@/lib/site-config";

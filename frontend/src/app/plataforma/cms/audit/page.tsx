"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Shield, Filter, Download } from "lucide-react";
import { toast } from "sonner";

interface AuditLogEntry {
  id: string;
  actor_email: string | null;
  actor_role: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  entity_slug: string | null;
  changes_json: Record<string, unknown> | null;
  ip_address: string | null;
  severity: string;
  created_at: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  info: "bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))]",
  warning: "bg-[hsl(var(--warning-muted))] text-warning-text",
  critical: "bg-red-100 text-[hsl(var(--destructive))]",
};

export default function AuditPage() {
  const { user: _user } = useAuth();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ entity_type: "", action: "", severity: "", actor_email: "" });
  const [page, setPage] = useState(0);
  const limit = 50;

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: String(limit), offset: String(page * limit) });
      if (filters.entity_type) params.set("entity_type", filters.entity_type);
      if (filters.action) params.set("action", filters.action);
      if (filters.severity) params.set("severity", filters.severity);
      if (filters.actor_email) params.set("actor_email", filters.actor_email);
      const data = await apiFetch<AuditLogEntry[]>(`/cms/v2/audit-logs?${params}`, { silent: true });
      setLogs(Array.isArray(data) ? data : []);
    } catch { toast.error("Error al cargar datos"); setLogs([]); }
    setLoading(false);
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [page, filters]);

  const exportCsv = () => {
    const header = "Fecha,Actor,Email,Rol,Accion,Entidad,Slug,IP,Severidad\n";
    const rows = logs.map(l =>
      `"${l.created_at}","${l.actor_email || ""}","${l.actor_email || ""}","${l.actor_role || ""}","${l.action}","${l.entity_type}","${l.entity_slug || ""}","${l.ip_address || ""}","${l.severity}"`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`; a.click();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield size={24} className="text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl font-bold">Audit Trail</h1>
            <p className="text-sm text-[hsl(var(--text-secondary))]">Registro inmutable de todas las acciones en el CMS</p>
          </div>
        </div>
        <button onClick={exportCsv} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border hover:bg-[hsl(var(--surface-1))]">
          <Download size={14} /> Exportar CSV
        </button>
      </div>

      <div className="flex flex-wrap gap-3 p-4 bg-[hsl(var(--surface-1))] rounded-xl">
        <Filter size={16} className="text-[hsl(var(--text-secondary))] mt-1" />
        <input placeholder="Actor email..." value={filters.actor_email} onChange={e => setFilters(f => ({ ...f, actor_email: e.target.value }))} className="px-3 py-1.5 text-sm border rounded-lg w-48" />
        <select value={filters.entity_type} onChange={e => setFilters(f => ({ ...f, entity_type: e.target.value }))} className="px-3 py-1.5 text-sm border rounded-lg">
          <option value="">Todas las entidades</option>
          <option value="cms_page">Pagina</option>
          <option value="cms_section">Seccion</option>
          <option value="cms_menu">Menu</option>
          <option value="cms_theme">Tema</option>
          <option value="webhook">Webhook</option>
          <option value="custom_entry">Entrada Custom</option>
          <option value="content_permission">Permiso</option>
          <option value="search_promotion">Busqueda</option>
        </select>
        <input placeholder="Accion (ej: page.create)" value={filters.action} onChange={e => setFilters(f => ({ ...f, action: e.target.value }))} className="px-3 py-1.5 text-sm border rounded-lg w-48" />
        <select value={filters.severity} onChange={e => setFilters(f => ({ ...f, severity: e.target.value }))} className="px-3 py-1.5 text-sm border rounded-lg">
          <option value="">Todas</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </select>
      </div>

      <div className="overflow-x-auto border rounded-xl">
        <table className="w-full text-sm">
          <thead className="bg-[hsl(var(--surface-1))] border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Fecha</th>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Actor</th>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Accion</th>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Entidad</th>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Slug</th>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">IP</th>
              <th className="px-4 py-3 text-left font-medium text-[hsl(var(--text-secondary))]">Sev</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-12 text-center text-[hsl(var(--text-secondary))]">Cargando...</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-12 text-center text-[hsl(var(--text-secondary))]">Sin registros</td></tr>
            ) : logs.map(log => (
              <tr key={log.id} className="hover:bg-[hsl(var(--surface-1))]/50">
                <td className="px-4 py-3 whitespace-nowrap text-xs text-[hsl(var(--text-secondary))]">{new Date(log.created_at).toLocaleString("es")}</td>
                <td className="px-4 py-3">
                  <div className="text-sm font-medium">{log.actor_email || "system"}</div>
                  <div className="text-xs text-[hsl(var(--text-secondary))]">{log.actor_role || ""}</div>
                </td>
                <td className="px-4 py-3"><code className="text-xs bg-[hsl(var(--surface-2))] px-1.5 py-0.5 rounded">{log.action}</code></td>
                <td className="px-4 py-3 text-xs text-[hsl(var(--text-secondary))]">{log.entity_type}</td>
                <td className="px-4 py-3 text-xs">{log.entity_slug || log.entity_id || "-"}</td>
                <td className="px-4 py-3 text-xs text-[hsl(var(--text-secondary))] font-mono">{log.ip_address || "-"}</td>
                <td className="px-4 py-3"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${SEVERITY_COLORS[log.severity] || "bg-[hsl(var(--surface-2))]"}`}>{log.severity}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-between items-center text-sm text-[hsl(var(--text-secondary))]">
        <span>Mostrando {logs.length} registros</span>
        <div className="flex gap-2">
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-3 py-1 border rounded-lg disabled:opacity-40">Anterior</button>
          <button disabled={logs.length < limit} onClick={() => setPage(p => p + 1)} className="px-3 py-1 border rounded-lg disabled:opacity-40">Siguiente</button>
        </div>
      </div>
    </div>
  );
}

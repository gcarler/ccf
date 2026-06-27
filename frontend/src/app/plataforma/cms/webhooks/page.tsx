"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Webhook, Plus, Trash2, Power, PowerOff, ChevronDown, ChevronUp } from "lucide-react";
import SidePanel from "@/components/ui/SidePanel";

interface WebhookItem {
  id: string;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
  last_triggered_at: string | null;
  failure_count: number;
}

interface WebhookDelivery {
  id: string;
  event: string;
  response_status: number | null;
  success: boolean;
  duration_ms: number | null;
  created_at: string;
}

const AVAILABLE_EVENTS = [
  "page.created", "page.updated", "page.published", "page.archived",
  "section.created", "section.updated", "section.deleted",
  "menu.updated", "theme.activated",
  "custom_entry.created", "custom_entry.published",
  "*",
];

export default function WebhooksPage() {
  const { user: _user } = useAuth();
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<WebhookItem | null>(null);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [form, setForm] = useState({ name: "", url: "", events: [] as string[] });

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<WebhookItem[]>("/cms/v2/webhooks?site_key=faro", { silent: true });
      setWebhooks(Array.isArray(data) ? data : []);
    } catch { setWebhooks([]); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.name || !form.url) return;
    await apiFetch("/cms/v2/webhooks", { method: "POST", body: { site_key: "faro", ...form }, silent: true });
    setForm({ name: "", url: "", events: [] });
    setShowForm(false);
    load();
  };

  const toggle = async (id: string, active: boolean) => {
    await apiFetch(`/cms/v2/webhooks/${id}`, { method: "PATCH", body: { is_active: !active }, silent: true });
    load();
  };

  const remove = async () => {
    if (!pendingDelete) return;
    await apiFetch(`/cms/v2/webhooks/${pendingDelete.id}`, { method: "DELETE", silent: true });
    setPendingDelete(null);
    load();
  };

  const loadDeliveries = async (id: string) => {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    try {
      const data = await apiFetch<WebhookDelivery[]>(`/cms/v2/webhooks/${id}/deliveries`, { silent: true });
      setDeliveries(Array.isArray(data) ? data : []);
    } catch { setDeliveries([]); }
  };

  const toggleEvent = (event: string) => {
    setForm(f => ({
      ...f,
      events: f.events.includes(event) ? f.events.filter(e => e !== event) : [...f.events, event],
    }));
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Webhook size={24} className="text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl font-bold">Webhooks</h1>
            <p className="text-sm text-slate-500">Notificar a sistemas externos cuando ocurran eventos</p>
          </div>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white hover:opacity-90">
          <Plus size={14} /> Nuevo Webhook
        </button>
      </div>

      {showForm && (
        <div className="p-4 border rounded-xl bg-slate-50 space-y-3">
          <input placeholder="Nombre" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="w-full px-3 py-2 text-sm border rounded-lg" />
          <input placeholder="URL (https://...)" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} className="w-full px-3 py-2 text-sm border rounded-lg" />
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">Eventos:</p>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_EVENTS.map(ev => (
                <button key={ev} onClick={() => toggleEvent(ev)} className={`px-2 py-1 text-xs rounded-lg border ${form.events.includes(ev) ? "bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]" : ""}`}>{ev}</button>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={create} className="px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--primary))] text-white">Crear</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm font-medium rounded-lg border">Cancelar</button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {loading ? <div className="py-12 text-center text-slate-400">Cargando...</div> : webhooks.length === 0 ? (
          <div className="py-12 text-center text-slate-400">Sin webhooks configurados</div>
        ) : webhooks.map(wh => (
          <div key={wh.id} className="border rounded-xl overflow-hidden">
            <div className="flex items-center justify-between p-4 bg-white">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${wh.is_active ? "bg-green-500" : "bg-slate-300"}`} />
                  <span className="font-medium text-sm">{wh.name}</span>
                </div>
                <p className="text-xs text-slate-400 mt-1 truncate font-mono">{wh.url}</p>
                <div className="flex gap-1 mt-2 flex-wrap">
                  {wh.events.map(ev => <span key={ev} className="text-[10px] bg-slate-100 px-1.5 py-0.5 rounded">{ev}</span>)}
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0 ml-3">
                <button onClick={() => loadDeliveries(wh.id)} className="p-1.5 rounded-lg hover:bg-slate-100" title="Entregas">
                  {expandedId === wh.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                <button onClick={() => toggle(wh.id, wh.is_active)} className="p-1.5 rounded-lg hover:bg-slate-100" title={wh.is_active ? "Desactivar" : "Activar"}>
                  {wh.is_active ? <PowerOff size={14} className="text-amber-500" /> : <Power size={14} className="text-green-500" />}
                </button>
                <button onClick={() => setPendingDelete(wh)} className="p-1.5 rounded-lg hover:bg-red-50" title="Eliminar">
                  <Trash2 size={14} className="text-red-400" />
                </button>
              </div>
            </div>
            {expandedId === wh.id && (
              <div className="border-t bg-slate-50 p-4">
                <p className="text-xs font-medium text-slate-500 mb-2">Ultimas entregas:</p>
                {deliveries.length === 0 ? <p className="text-xs text-slate-400">Sin entregas</p> : (
                  <div className="space-y-1">
                    {deliveries.map(d => (
                      <div key={d.id} className="flex items-center gap-3 text-xs">
                        <span className={`w-1.5 h-1.5 rounded-full ${d.success ? "bg-green-500" : "bg-red-500"}`} />
                        <span className="font-mono">{d.event}</span>
                        <span className="text-slate-400">{d.response_status || "?"}</span>
                        <span className="text-slate-400">{d.duration_ms || "?"}ms</span>
                        <span className="text-slate-400">{new Date(d.created_at).toLocaleString("es")}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      <SidePanel
        isOpen={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Eliminar webhook"
        subtitle={pendingDelete?.name}
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Esta accion eliminara el webhook seleccionado.</p>
          <div className="flex gap-2">
            <button onClick={() => setPendingDelete(null)} className="flex-1 rounded-lg border px-3 py-2 text-sm font-medium">Cancelar</button>
            <button onClick={remove} className="flex-1 rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700">Eliminar</button>
          </div>
        </div>
      </SidePanel>
    </div>
  );
}

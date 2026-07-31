"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { Webhook, Plus, Trash2, Power, PowerOff, ChevronDown, ChevronUp, Link as LinkIcon, Key, Check } from "lucide-react";
import SidePanel from "@/components/ui/SidePanel";
import { SITE_KEY } from "@/lib/site-config";
import { toast } from "sonner";
import clsx from "clsx";

interface WebhookItem {
  id: string;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
  secret_key?: string;
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
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<WebhookItem | null>(null);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [form, setForm] = useState({ name: "", url: "", events: [] as string[], secret_key: "" });

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<WebhookItem[]>(`/cms/v2/webhooks?site_key=${SITE_KEY}`, { silent: true });
      setWebhooks(Array.isArray(data) ? data : []);
    } catch { toast.error("Error al cargar datos"); setWebhooks([]); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.name || !form.url) {
      toast.error("El nombre y la URL son obligatorios");
      return;
    }
    if (form.events.length === 0) {
      toast.error("Debe seleccionar al menos un evento");
      return;
    }
    try {
      await apiFetch("/cms/v2/webhooks", { method: "POST", body: { site_key: SITE_KEY, ...form }, silent: true });
      toast.success("Webhook creado exitosamente");
      setForm({ name: "", url: "", events: [], secret_key: "" });
      setShowForm(false);
      load();
    } catch { toast.error("Error al crear webhook"); }
  };

  const toggle = async (id: string, active: boolean) => {
    try {
      await apiFetch(`/cms/v2/webhooks/${id}`, { method: "PATCH", body: { is_active: !active }, silent: true });
      toast.success(`Webhook ${!active ? 'activado' : 'desactivado'}`);
      load();
    } catch { toast.error("Error al cambiar estado del webhook"); }
  };

  const remove = async () => {
    if (!pendingDelete) return;
    try {
      await apiFetch(`/cms/v2/webhooks/${pendingDelete.id}`, { method: "DELETE", silent: true });
      toast.success("Webhook eliminado");
      setPendingDelete(null);
      load();
    } catch { toast.error("Error al eliminar webhook"); }
  };

  const loadDeliveries = async (id: string) => {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    try {
      const data = await apiFetch<WebhookDelivery[]>(`/cms/v2/webhooks/${id}/deliveries`, { silent: true });
      setDeliveries(Array.isArray(data) ? data : []);
    } catch { toast.error("Error al cargar entregas"); setDeliveries([]); }
  };

  const toggleEvent = (event: string) => {
    setForm(f => ({
      ...f,
      events: f.events.includes(event) ? f.events.filter(e => e !== event) : [...f.events, event],
    }));
  };

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))]">
      <header className="h-14 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-4 gap-4 shrink-0 justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <Webhook size={18} className="text-[hsl(var(--primary))] shrink-0" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white truncate">
            Webhooks
          </h2>
          <span className="text-2xs font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full shrink-0">
            {webhooks.length}
          </span>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-[hsl(var(--primary))] text-white px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--primary))/20%] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 shrink-0"
        >
          <Plus size={14} /> Nuevo Webhook
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {showForm && (
          <div className="mb-6 p-5 border border-[hsl(var(--border))] dark:border-white/10 rounded-xl bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--admin-bg-secondary))] shadow-lg space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white border-b border-[hsl(var(--border))] dark:border-white/10 pb-2">Configurar Webhook</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[hsl(var(--text-secondary))]">Nombre descriptivo</label>
                <input
                  placeholder="Ej: Notificar a Slack"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg outline-none focus:border-[hsl(var(--primary))]"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[hsl(var(--text-secondary))]">URL de destino (Payload URL)</label>
                <div className="relative">
                  <LinkIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                  <input
                    placeholder="https://..."
                    value={form.url}
                    onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
                    className="w-full pl-9 pr-3 py-2 text-sm font-mono border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg outline-none focus:border-[hsl(var(--primary))]"
                  />
                </div>
              </div>
              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-semibold text-[hsl(var(--text-secondary))]">Secret (Opcional - Para firmar el payload HMAC SHA256)</label>
                <div className="relative">
                  <Key size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                  <input
                    placeholder="Dejar vacío para no usar firma"
                    value={form.secret_key}
                    onChange={e => setForm(f => ({ ...f, secret_key: e.target.value }))}
                    className="w-full pl-9 pr-3 py-2 text-sm font-mono border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg outline-none focus:border-[hsl(var(--primary))]"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-[hsl(var(--text-secondary))]">Eventos que activarán este webhook</label>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
                {AVAILABLE_EVENTS.map(ev => (
                  <button
                    key={ev}
                    onClick={() => toggleEvent(ev)}
                    className={clsx(
                      "flex items-center gap-1.5 px-3 py-2 text-2xs font-semibold rounded-lg border transition-all text-left",
                      form.events.includes(ev)
                        ? "bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]"
                        : "border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--primary))/50%] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"
                    )}
                  >
                    <div className={clsx("size-3.5 rounded-sm border flex items-center justify-center shrink-0", form.events.includes(ev) ? "border-white bg-white/20" : "border-[hsl(var(--text-secondary))/30%]")}>
                      {form.events.includes(ev) && <Check size={10} />}
                    </div>
                    <span className="truncate">{ev}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-[hsl(var(--border))] dark:border-white/10">
              <button onClick={() => setShowForm(false)} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide rounded-lg border border-[hsl(var(--border))] dark:border-white/10 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors">Cancelar</button>
              <button onClick={create} className="px-6 py-2 text-xs font-semibold uppercase tracking-wide rounded-lg bg-[hsl(var(--primary))] text-white hover:opacity-90 transition-opacity shadow-lg shadow-[hsl(var(--primary))/20%]">Crear Webhook</button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-40 rounded-xl bg-[hsl(var(--surface-1))] dark:bg-white/5 animate-pulse" />
            ))}
          </div>
        ) : webhooks.length === 0 && !showForm ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-70">
            <div className="size-16 rounded-2xl bg-[hsl(var(--primary))/10%] flex items-center justify-center text-[hsl(var(--primary))] shadow-inner">
              <Webhook size={32} />
            </div>
            <div>
              <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">Sin webhooks</p>
              <p className="text-sm text-[hsl(var(--text-secondary))] mt-1 max-w-sm">Conecta tu CMS con servicios externos en tiempo real añadiendo tu primer webhook.</p>
            </div>
            <button onClick={() => setShowForm(true)} className="px-4 py-2 mt-2 bg-[hsl(var(--primary))] text-white text-xs font-semibold uppercase tracking-wide rounded-lg shadow-lg hover:bg-[hsl(var(--primary))] transition-all active:scale-95">
              Crear Webhook
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {webhooks.map(wh => (
              <div key={wh.id} className="border border-[hsl(var(--border))] dark:border-white/10 rounded-xl overflow-hidden bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] flex flex-col shadow-sm hover:shadow-md transition-shadow">
                <div className="p-4 flex-1">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className={clsx("size-2.5 rounded-full shrink-0", wh.is_active ? "bg-[hsl(var(--success))]" : "bg-[hsl(var(--text-secondary))]")} />
                      <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white truncate" title={wh.name}>{wh.name}</h3>
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => toggle(wh.id, wh.is_active)} className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-colors" title={wh.is_active ? "Desactivar" : "Activar"}>
                        {wh.is_active ? <PowerOff size={14} className="text-[hsl(var(--text-secondary))]" /> : <Power size={14} className="text-[hsl(var(--success))]" />}
                      </button>
                      <button onClick={() => setPendingDelete(wh)} className="p-1.5 rounded-lg hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 text-[hsl(var(--text-secondary))] hover:text-danger-text dark:hover:text-[hsl(var(--danger))] transition-colors" title="Eliminar">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  <div className="mb-4 bg-[hsl(var(--surface-1))] dark:bg-black/20 p-2.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 flex items-center gap-2">
                    <LinkIcon size={12} className="text-[hsl(var(--text-secondary))] shrink-0" />
                    <p className="text-xs text-[hsl(var(--text-secondary))] truncate font-mono select-all" title={wh.url}>{wh.url}</p>
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {wh.events.map(ev => (
                      <span key={ev} className="text-2xs font-semibold bg-info-soft text-info-text dark:bg-[hsl(var(--info))]/10 dark:text-[hsl(var(--info))] border border-[hsl(var(--info))/20%] px-2 py-0.5 rounded-full">
                        {ev}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="border-t border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5">
                  <button
                    onClick={() => loadDeliveries(wh.id)}
                    className="w-full p-3 flex items-center justify-between text-xs font-semibold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white transition-colors"
                  >
                    <span>Últimas entregas ({expandedId === wh.id && deliveries.length > 0 ? deliveries.length : '?'})</span>
                    {expandedId === wh.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {expandedId === wh.id && (
                    <div className="p-3 pt-0 max-h-48 overflow-y-auto custom-scrollbar border-t border-[hsl(var(--border))] dark:border-white/5 mt-2">
                      {deliveries.length === 0 ? (
                         <p className="text-xs text-[hsl(var(--text-secondary))] text-center py-2">No hay entregas registradas</p>
                      ) : (
                        <div className="space-y-2 pt-2">
                          {deliveries.map(d => (
                            <div key={d.id} className="flex flex-col gap-1 text-xs bg-[hsl(var(--bg-primary))] dark:bg-black/20 p-2 rounded border border-[hsl(var(--border))] dark:border-white/5">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span className={clsx("size-1.5 rounded-full shrink-0", d.success ? "bg-[hsl(var(--success))]" : "bg-[hsl(var(--danger))]")} />
                                  <span className="font-mono font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{d.event}</span>
                                </div>
                                <span className="text-2xs text-[hsl(var(--text-secondary))]">{new Date(d.created_at).toLocaleString("es-CO")}</span>
                              </div>
                              <div className="flex items-center gap-3 ml-3.5 text-2xs">
                                <span className={clsx("font-bold px-1.5 py-0.5 rounded-sm",
                                  d.success ? "bg-success-soft text-success-text dark:bg-[hsl(var(--success))]/20 dark:text-[hsl(var(--success))]" :
                                  "bg-danger-soft text-danger-text dark:bg-[hsl(var(--danger))]/20 dark:text-[hsl(var(--danger))]"
                                )}>
                                  {d.response_status ? `HTTP ${d.response_status}` : "Error"}
                                </span>
                                <span className="text-[hsl(var(--text-secondary))]">{d.duration_ms ? `${d.duration_ms}ms` : ""}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <SidePanel
        isOpen={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Eliminar Webhook"
        subtitle={pendingDelete?.name}
      >
        <div className="space-y-4">
          <div className="rounded-lg border border-[hsl(var(--danger)/25%)] bg-danger-soft dark:bg-[hsl(var(--danger))]/10 p-4">
            <p className="text-sm text-danger-text dark:text-[hsl(var(--danger))]">
              ¿Estás seguro de eliminar este webhook? Las aplicaciones externas dejarán de recibir eventos inmediatamente.
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

"use client";

import clsx from "clsx";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  MessageCircle,
  RefreshCw,
  Search,
} from "lucide-react";

import { API_BASE_URL, apiUrl } from "@/lib/api";

type PipelineLead = {
  id: number;
  first_name: string;
  last_name: string;
  stage: string;
  source?: string;
  phone?: string;
  notes?: string | null;
  assigned_pastor_id?: number | null;
  is_automation_paused?: boolean;
};

type ActivityItem = {
  id: string;
  event: string;
  description: string;
  stage?: string;
  timestamp: string;
};

const STAGE_ORDER = ["new", "contacted", "discipling", "engaged", "celebration"] as const;

const STAGE_CONFIG: Record<string, { label: string; accent: string; chip: string; empty: string }> = {
  new: {
    label: "Nuevos",
    accent: "from-sky-500/20 to-slate-900/40",
    chip: "bg-sky-500/15 text-sky-200",
    empty: "Esperando nuevos registros",
  },
  contacted: {
    label: "Contactados",
    accent: "from-slate-700/40 to-slate-900/60",
    chip: "bg-slate-500/20 text-slate-200",
    empty: "Necesitamos hacer algunas llamadas",
  },
  discipling: {
    label: "Discipulado",
    accent: "from-amber-500/20 to-orange-900/50",
    chip: "bg-amber-500/20 text-amber-100",
    empty: "Aún no hay grupos activos",
  },
  engaged: {
    label: "Comunidad",
    accent: "from-emerald-500/20 to-emerald-900/50",
    chip: "bg-emerald-500/20 text-emerald-100",
    empty: "Sin actividades recientes",
  },
  celebration: {
    label: "Graduados",
    accent: "from-purple-500/20 to-purple-900/50",
    chip: "bg-purple-500/20 text-purple-100",
    empty: "Aún sin historias que celebrar",
  },
};

const FALLBACK_PIPELINE: PipelineLead[] = [
  {
    id: 1001,
    first_name: "Isabel",
    last_name: "Romero",
    stage: "new",
    source: "Landing Page",
    phone: "+52 55 0101 0101",
    notes: "Pidió seguimiento vía WhatsApp",
  },
  {
    id: 1002,
    first_name: "Mateo",
    last_name: "Cárdenas",
    stage: "contacted",
    source: "Evento Juvenil",
    phone: "+57 313 111 22",
    notes: "Interesado en academia",
  },
  {
    id: 1003,
    first_name: "Renata",
    last_name: "López",
    stage: "discipling",
    source: "Facebook Ads",
    phone: "+58 412 554 87",
    notes: "Cursando módulo 2",
  },
  {
    id: 1004,
    first_name: "Diego",
    last_name: "Cruz",
    stage: "engaged",
    source: "Casa de Gloria",
    phone: "+57 321 553 12",
    notes: "Coordinando voluntariado",
  },
  {
    id: 1005,
    first_name: "Valeria",
    last_name: "Gómez",
    stage: "celebration",
    source: "Ref. interna",
    phone: "+51 991 771 42",
    notes: "Recibió certificado",
  },
];

const GRAPHQL_QUERY = `# tasks-board.graphql
query PipelineBoard($stage: Stage!, $limit: Int = 30) {
  pipeline(stage: $stage, limit: $limit) {
    id
    firstName
    lastName
    stage
    source
    metrics {
      lastContact
      energy
    }
  }
}`;

const WS_BASE_URL = API_BASE_URL.replace(/^http/i, "ws");

function normalizeLead(lead: PipelineLead): PipelineLead {
  return {
    id: lead.id,
    first_name: lead.first_name,
    last_name: lead.last_name,
    stage: lead.stage?.toLowerCase?.() || "new",
    source: lead.source,
    phone: lead.phone,
    notes: lead.notes,
    assigned_pastor_id: lead.assigned_pastor_id,
    is_automation_paused: lead.is_automation_paused,
  };
}

export default function TasksDashboardPage() {
  const [leads, setLeads] = useState<PipelineLead[]>([]);
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [presence, setPresence] = useState<string[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [connectionState, setConnectionState] = useState<"connecting" | "online" | "offline">("connecting");
  const [loading, setLoading] = useState(true);
  const [graphqlCopied, setGraphqlCopied] = useState(false);

  const selectedLead = useMemo(() => {
    if (!selectedLeadId) {
      return leads[0] ?? FALLBACK_PIPELINE[0];
    }
    return leads.find((lead) => lead.id === selectedLeadId) ?? leads[0] ?? FALLBACK_PIPELINE[0];
  }, [leads, selectedLeadId]);

  const filteredLeads = useMemo(() => {
    if (!searchTerm) return leads;
    const query = searchTerm.toLowerCase();
    return leads.filter((lead) =>
      `${lead.first_name} ${lead.last_name}`.toLowerCase().includes(query) ||
      lead.source?.toLowerCase().includes(query) ||
      lead.stage.toLowerCase().includes(query)
    );
  }, [leads, searchTerm]);

  const stageBuckets = useMemo(() => {
    return STAGE_ORDER.map((stageKey) => ({
      stage: stageKey,
      items: filteredLeads.filter((lead) => lead.stage === stageKey),
    }));
  }, [filteredLeads]);

  const upsertLead = useCallback((incoming: PipelineLead) => {
    setLeads((prev) => {
      const exists = prev.some((lead) => lead.id === incoming.id);
      if (exists) {
        return prev.map((lead) => (lead.id === incoming.id ? normalizeLead({ ...lead, ...incoming }) : lead));
      }
      return [normalizeLead(incoming), ...prev];
    });
  }, []);

  const pushActivity = useCallback((item: Omit<ActivityItem, "id" | "timestamp">) => {
    setActivities((prev) => [
      {
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        ...item,
      },
      ...prev,
    ].slice(0, 10));
  }, []);

  const fetchPipeline = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl("/crm/consolidation/pipeline?limit=120"), { cache: "no-store" });
      if (!res.ok) throw new Error("Pipeline request failed");
      const data: PipelineLead[] = await res.json();
      setLeads(data.map(normalizeLead));
    } catch (error) {
      console.warn("Using fallback pipeline data", error);
      setLeads(FALLBACK_PIPELINE);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPresence = useCallback(async () => {
    try {
      const res = await fetch(apiUrl("/messaging/presence/pipeline"), { cache: "no-store" });
      if (!res.ok) throw new Error("presence unauthorized");
      const data = await res.json();
      setPresence(data?.clients ?? []);
    } catch {
      setPresence([]);
    }
  }, []);

  useEffect(() => {
    fetchPipeline();
    fetchPresence();
    const interval = setInterval(fetchPresence, 15000);
    return () => clearInterval(interval);
  }, [fetchPipeline, fetchPresence]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const clientId = crypto.randomUUID();
    const rooms = "pipeline";
    const ws = new WebSocket(`${WS_BASE_URL}/ws/${clientId}?rooms=${rooms}`);
    setConnectionState("connecting");

    ws.onopen = () => setConnectionState("online");
    ws.onclose = () => setConnectionState("offline");
    ws.onerror = () => setConnectionState("offline");

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (!payload) return;
        switch (payload.event) {
          case "pipeline_lead_created":
            if (payload.lead) {
              upsertLead(payload.lead);
              pushActivity({
                event: "Nuevo lead",
                description: `${payload.lead.first_name} ${payload.lead.last_name} registrado`,
                stage: payload.lead.stage,
              });
            }
            break;
          case "pipeline_lead_updated":
            if (payload.lead) {
              upsertLead(payload.lead);
              pushActivity({
                event: "Movimiento de etapa",
                description: `${payload.lead.first_name} avanzó a ${STAGE_CONFIG[payload.lead.stage]?.label ?? payload.lead.stage}`,
                stage: payload.lead.stage,
              });
            }
            break;
          case "pastoral_call_logged":
            pushActivity({
              event: "Contacto registrado",
              description: `Se documentó una llamada (${payload.outcome || "sin resultado"})`,
            });
            break;
          default:
            break;
        }
      } catch (error) {
        console.warn("WS payload error", error);
      }
    };

    return () => ws.close();
  }, [pushActivity, upsertLead]);

  useEffect(() => {
    if (!selectedLeadId && leads.length > 0) {
      setSelectedLeadId(leads[0].id);
    }
  }, [leads, selectedLeadId]);

  const presencePreview = presence.slice(0, 4);

  const graphqlResponse = useMemo(() => {
    if (!selectedLead) return null;
    return {
      pipeline: [
        {
          id: selectedLead.id,
          firstName: selectedLead.first_name,
          lastName: selectedLead.last_name,
          stage: selectedLead.stage,
          source: selectedLead.source,
        },
      ],
    };
  }, [selectedLead]);

  const handleCopyQuery = async () => {
    try {
      await navigator.clipboard.writeText(GRAPHQL_QUERY);
      setGraphqlCopied(true);
      setTimeout(() => setGraphqlCopied(false), 2000);
    } catch (error) {
      console.warn("Clipboard not available", error);
    }
  };

  return (
    <div className="min-h-screen bg-[#030711] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_#132347_0%,_#030711_55%)] opacity-90" aria-hidden />
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
        <header className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.4em] text-slate-400 font-semibold">Panel Operativo</p>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white mt-2">Command Center de Tareas</h1>
            <p className="text-sm text-slate-400 mt-3 max-w-2xl">
              Vista consolidada inspirada en ClickUp con métricas de pipeline, presencia en vivo y consultas GraphQL listas para copiar.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">
            <span className={clsx("px-4 py-2 rounded-2xl border", connectionState === "online" ? "border-emerald-400/40 text-emerald-300" : "border-slate-700 text-slate-500")}>{connectionState}</span>
            <button
              onClick={fetchPipeline}
              className="px-4 py-2 rounded-2xl border border-white/10 hover:border-white/30 flex items-center gap-2 text-white/80"
            >
              <RefreshCw size={14} /> Actualizar
            </button>
          </div>
        </header>

        <section className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex-1">
            <label className="text-[10px] uppercase tracking-[0.5em] text-slate-500 block mb-2 font-semibold">Búsqueda Semántica</label>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
              <input
                type="text"
                placeholder="Filtrar por nombre, fuente o etapa"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-2xl pl-12 pr-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-1">
            {STAGE_ORDER.map((stage) => (
              <button
                key={stage}
                onClick={() => setSelectedLeadId(stageBuckets.find((bucket) => bucket.items.length)?.items[0]?.id ?? null)}
                className="px-5 py-3 rounded-2xl text-xs font-black uppercase tracking-[0.2em] bg-white/5 border border-white/10 text-slate-300"
              >
                {STAGE_CONFIG[stage]?.label || stage}
              </button>
            ))}
          </div>
        </section>

        <section className="grid xl:grid-cols-[1.55fr_0.8fr] gap-8">
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {stageBuckets.map(({ stage, items }) => (
                <div
                  key={stage}
                  className={clsx(
                    "rounded-[28px] p-5 border border-white/5 bg-gradient-to-br h-full",
                    STAGE_CONFIG[stage]?.accent ?? "from-slate-800/40 to-slate-900/60"
                  )}
                >
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-[10px] uppercase tracking-[0.4em] text-slate-400">{STAGE_CONFIG[stage]?.label || stage}</p>
                      <p className="text-3xl font-black">{items.length}</p>
                    </div>
                    <span className={clsx("text-[10px] px-3 py-1 rounded-xl font-black", STAGE_CONFIG[stage]?.chip)}>
                      {Math.round((items.length / Math.max(leads.length, 1)) * 100) || 0}%
                    </span>
                  </div>
                  <div className="space-y-3">
                    {loading && items.length === 0 ? (
                      <p className="text-slate-500 text-sm">Cargando...</p>
                    ) : items.length > 0 ? (
                      items.slice(0, 4).map((item) => (
                        <button
                          key={item.id}
                          onClick={() => setSelectedLeadId(item.id)}
                          className={clsx(
                            "w-full text-left p-4 rounded-2xl bg-white/5 hover:bg-white/10 transition-all border border-white/5",
                            selectedLead?.id === item.id && "border-primary/40"
                          )}
                        >
                          <p className="font-semibold text-sm">{item.first_name} {item.last_name}</p>
                          <p className="text-[11px] uppercase tracking-[0.3em] text-slate-400 mt-1">{item.source || "Sin fuente"}</p>
                        </button>
                      ))
                    ) : (
                      <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500">
                        {STAGE_CONFIG[stage]?.empty}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-[32px] border border-white/5 bg-white/5 text-slate-100 p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.4em] text-slate-400">Actividad Reciente</p>
                  <h3 className="text-xl font-black">Bitácora automática</h3>
                </div>
                <Activity size={20} className="text-primary" />
              </div>
              <div className="space-y-4">
                {activities.length === 0 ? (
                  <p className="text-sm text-slate-400">Interactúa con el pipeline para ver movimientos en tiempo real.</p>
                ) : (
                  activities.map((item) => (
                    <div key={item.id} className="flex items-start gap-4 border-b border-white/5 pb-3 last:border-0">
                      <div className="size-10 rounded-2xl bg-white/10 flex items-center justify-center">
                        <MessageCircle size={16} className="text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">{item.event}</p>
                        <p className="text-xs text-slate-400">{item.description}</p>
                        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mt-1">
                          {new Date(item.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-[32px] border border-white/10 bg-gradient-to-br from-slate-900/80 to-slate-900/30 p-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.4em] text-slate-400">Lead Seleccionado</p>
                  <h3 className="text-2xl font-black">{selectedLead.first_name} {selectedLead.last_name}</h3>
                </div>
                <span className="px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-[0.3em] bg-primary/20 text-primary">
                  {STAGE_CONFIG[selectedLead.stage]?.label ?? selectedLead.stage}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <InfoChip label="Fuente" value={selectedLead.source || "Directo"} />
                <InfoChip label="Pastor asignado" value={selectedLead.assigned_pastor_id ? `ID ${selectedLead.assigned_pastor_id}` : "Sin asignar"} />
                <InfoChip label="Contacto" value={selectedLead.phone || "-"} />
                <InfoChip label="Automatización" value={selectedLead.is_automation_paused ? "En pausa" : "Activa"} />
              </div>
              <p className="text-xs text-slate-400 mt-6 leading-relaxed">
                {selectedLead.notes || "Sin notas registradas"}
              </p>
              <div className="mt-6 flex items-center gap-4">
                <div className="flex -space-x-2">
                  {presencePreview.map((client) => (
                    <span
                      key={client}
                      className="size-9 rounded-full bg-white/10 border border-white/10 flex items-center justify-center text-xs font-bold"
                    >
                      {client.slice(0, 2).toUpperCase()}
                    </span>
                  ))}
                  {presence.length > presencePreview.length && (
                    <span className="size-9 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-black">
                      +{presence.length - presencePreview.length}
                    </span>
                  )}
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-[0.4em] text-slate-400">Presencia</p>
                  <p className="text-sm font-semibold">Coaches conectados: {presence.length || "solo tú"}</p>
                </div>
              </div>
              <Link
                href="/crm"
                className="mt-8 inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.3em] text-primary hover:text-primary/80"
              >
                Abrir tablero CRM <ArrowRight size={14} />
              </Link>
            </div>

            <div className="rounded-[32px] border border-white/10 bg-slate-900/70 p-7 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.4em] text-slate-400">Consulta GraphQL</p>
                  <h4 className="text-lg font-black">tasks-board.graphql</h4>
                </div>
                <button
                  onClick={handleCopyQuery}
                  className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400 hover:text-white"
                >
                  {graphqlCopied ? "Copiado" : "Copiar"}
                </button>
              </div>
              <pre className="bg-black/40 border border-white/5 rounded-2xl p-4 text-[11px] leading-relaxed overflow-auto">
{GRAPHQL_QUERY}
              </pre>
              <div className="bg-slate-950/40 border border-white/5 rounded-2xl p-4 text-[11px] text-slate-300">
                <p className="uppercase tracking-[0.4em] text-[9px] text-slate-500 mb-1">Variables</p>
                <pre>{JSON.stringify({ stage: selectedLead.stage.toUpperCase(), limit: 10 }, null, 2)}</pre>
                <p className="uppercase tracking-[0.4em] text-[9px] text-slate-500 mb-1 mt-4">Response</p>
                <pre>{JSON.stringify(graphqlResponse, null, 2)}</pre>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function InfoChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl px-4 py-3">
      <p className="text-[9px] uppercase tracking-[0.4em] text-slate-500">{label}</p>
      <p className="text-sm font-semibold mt-1 text-white/90">{value}</p>
    </div>
  );
}

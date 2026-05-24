"use client";

import React, { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Network, Search, RefreshCw } from "lucide-react";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import type { ViewType } from "@/components/ViewSwitcher";
import Skeleton from "@/components/ui/Skeleton";
import { useRegisterCommands } from "@/context/CommandCenterContext";
import { useGraphInsights } from "@/hooks/useGraphInsights";
import type { GraphNode } from "@/types/graph";
import { useConfig } from "@/context/ConfigContext";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d").then((mod) => mod.default), { ssr: false });

const palette: Record<string, string> = {
  course: "#2563eb",
  person: "#059669",
  donor: "#059669",
  lead: "#7c3aed",
  project: "#f59e0b",
  task: "#f97316",
  family: "#0ea5e9",
  fund: "#8b5cf6",
  asset: "#d97706",
  maintenance_log: "#e11d48",
  pastor: "#334155",
};

export default function KnowledgeGraphPage() {
  const { isFeatureEnabled, loading: configLoading } = useConfig();
  const [query, setQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [viewType, setViewType] = useState<ViewType>("grid");
  const enabled = isFeatureEnabled('knowledge_graph');
  const { snapshot, loading, error, refresh } = useGraphInsights({ limit: 240, enabled });

  const allTypes = useMemo(() => {
    if (!snapshot) return [] as string[];
    return Array.from(new Set(snapshot.nodes.map((node) => node.type))).sort();
  }, [snapshot]);

  const filtered = useMemo(() => {
    if (!snapshot) return { nodes: [], edges: [] };
    const q = query.trim().toLowerCase();
    const nodes = snapshot.nodes.filter((node) => {
      if (selectedType !== "all" && node.type !== selectedType) return false;
      if (!q) return true;
      return (
        node.label.toLowerCase().includes(q) ||
        (node.detail || "").toLowerCase().includes(q) ||
        node.id.toLowerCase().includes(q)
      );
    });
    const ids = new Set(nodes.map((node) => node.id));
    const edges = snapshot.edges.filter((edge) => ids.has(edge.from) && ids.has(edge.to));
    return { nodes, edges };
  }, [snapshot, selectedType, query]);

  const graphData = useMemo(
    () => ({
      nodes: filtered.nodes.map((node) => ({ ...node })),
      links: filtered.edges.map((edge) => ({ ...edge, source: edge.from, target: edge.to })),
    }),
    [filtered],
  );

  useRegisterCommands("knowledge-graph", [
    { id: "graph-refresh", label: "Actualizar grafo", group: "Datos", action: refresh },
    { id: "graph-clear-filter", label: "Limpiar filtros", group: "Datos", action: () => { setQuery(""); setSelectedType("all"); } },
  ]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-white font-display dark:bg-[#0f1114]">
      <WorkspaceToolbar
        breadcrumbs={[{ label: "Insights", icon: Network }, { label: "Knowledge Graph", icon: Network }]}
        viewType={viewType}
        setViewType={setViewType}
        availableViews={["grid", "list", "table"]}
      />
      <main className="relative flex flex-1 flex-col gap-3 overflow-hidden p-3 p-4">
        <header className="space-y-2">
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">Knowledge Graph</h1>
          <p className="max-w-3xl text-sm text-slate-500 dark:text-slate-400">Vista interactiva con pan/zoom, busqueda de nodos y filtros por tipo para insights de CRM, Academy y Projects.</p>
        </header>

        {viewType === "list" && (
          <section className="space-y-4 overflow-y-auto">
            {filtered.nodes.map((node) => (
              <article key={node.id} className="rounded-lg border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-white/5">
                <h3 className="font-bold text-slate-900 dark:text-white">{node.label}</h3>
                <p className="mt-1 text-sm text-slate-500">{node.type}</p>
              </article>
            ))}
          </section>
        )}

        {viewType === "table" && (
          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-white/10 dark:bg-white/5">
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:bg-white/5">
                <tr><th className="px-3 py-1.5">Nodo</th><th className="px-3 py-1.5">Tipo</th><th className="px-3 py-1.5">Conexiones</th></tr>
              </thead>
              <tbody>
                {filtered.nodes.map((node) => (
                  <tr key={node.id} className="border-t border-slate-100 dark:border-white/5">
                    <td className="px-3 py-1.5 font-bold text-slate-900 dark:text-white">{node.label}</td>
                    <td className="px-3 py-1.5 text-slate-500">{node.type}</td>
                    <td className="px-3 py-1.5 text-slate-500">{filtered.edges.filter((edge) => edge.from === node.id || edge.to === node.id).length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {viewType === "grid" && (
        <section className="grid gap-4 lg:grid-cols-[1fr_320px]">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative w-full max-w-sm">
                <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Buscar nodo por nombre, id o detalle..."
                  className="h-10 w-full rounded-md border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none ring-blue-500/20 transition focus:ring-4 dark:border-white/10 dark:bg-white/5"
                />
              </div>

              <button
                onClick={refresh}
                className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 px-3 text-xs font-semibold uppercase tracking-wide text-slate-500 transition hover:bg-slate-100 dark:border-white/10 dark:hover:bg-white/10"
              >
                <RefreshCw size={14} /> Refrescar
              </button>

              <div className="flex flex-wrap gap-1">
                <TypeChip active={selectedType === "all"} label="Todos" onClick={() => setSelectedType("all")} />
                {allTypes.map((type) => (
                  <TypeChip key={type} active={selectedType === type} label={type} onClick={() => setSelectedType(type)} />
                ))}
              </div>
            </div>

            <div className="h-[60vh] overflow-hidden rounded-lg border border-slate-200 bg-slate-50 dark:border-white/10 dark:bg-black/20">
              {configLoading ? (
                <div className="grid h-full place-items-center">
                  <Skeleton className="h-[60%] w-[90%] rounded-lg" />
                </div>
              ) : !enabled ? (
                <div className="grid h-full place-items-center text-sm font-semibold text-slate-500">
                  El módulo Knowledge Graph está desactivado por feature flag.
                </div>
              ) : loading ? (
                <div className="grid h-full place-items-center">
                  <Skeleton className="h-[60%] w-[90%] rounded-lg" />
                </div>
              ) : error ? (
                <div className="grid h-full place-items-center text-sm font-semibold text-rose-500">{error}</div>
              ) : (
                <ForceGraph2D
                  graphData={graphData}
                  nodeLabel={(node: any) => `${node.label} (${node.type})`}
                  linkWidth={0.6}
                  linkColor={() => "rgba(148,163,184,0.45)"}
                  cooldownTicks={100}
                  onNodeClick={(node: any) => setSelectedNode(node as GraphNode)}
                  nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                    const label = node.label as string;
                    const color = palette[node.type] || "#475569";
                    const fontSize = Math.max(10, 14 / globalScale);

                    ctx.beginPath();
                    ctx.fillStyle = color;
                    ctx.arc(node.x, node.y, 4.8, 0, 2 * Math.PI, false);
                    ctx.fill();

                    if (globalScale < 1.8) return;
                    ctx.font = `${fontSize}px sans-serif`;
                    ctx.fillStyle = "#0f172a";
                    ctx.fillText(label, node.x + 7, node.y + 3);
                  }}
                />
              )}
            </div>
          </div>

          <aside className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
            <h2 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Panel de Nodo</h2>
            {selectedNode ? (
              <>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-black/20">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{selectedNode.type}</p>
                  <h3 className="mt-1 text-lg font-bold text-slate-900 dark:text-white">{selectedNode.label}</h3>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{selectedNode.detail || "Sin detalle"}</p>
                </div>
                {selectedNode.meta ? (
                  <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-black/20">
                    <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Metadata</h4>
                    <dl className="space-y-2">
                      {Object.entries(selectedNode.meta).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between gap-3 text-xs">
                          <dt className="font-semibold uppercase tracking-wide text-slate-400">{key}</dt>
                          <dd className="max-w-[170px] truncate font-semibold text-slate-700 dark:text-slate-200">{String(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                ) : null}
              </>
            ) : (
              <p className="text-sm text-slate-500">Selecciona un nodo para ver su detalle y metadata.</p>
            )}

            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-black/20">
              <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Resumen</h4>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <SummaryBox label="Nodos" value={String(filtered.nodes.length)} />
                <SummaryBox label="Edges" value={String(filtered.edges.length)} />
              </div>
            </div>
          </aside>
        </section>
        )}
      </main>
    </div>
  );
}

function TypeChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wide transition ${
        active
          ? "bg-blue-600 text-white"
          : "border border-slate-200 bg-white text-slate-500 hover:bg-slate-100 dark:border-white/10 dark:bg-white/5"
      }`}
    >
      {label}
    </button>
  );
}

function SummaryBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-center dark:border-white/10 dark:bg-white/5">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="text-lg font-bold text-slate-800 dark:text-white">{value}</p>
    </div>
  );
}


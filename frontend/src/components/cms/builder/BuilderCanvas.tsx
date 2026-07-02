"use client";

import React from "react";
import { LayoutPanelTop, Eye, Monitor, Smartphone, Plus, ArrowUp, ArrowDown } from "lucide-react";
import { SectionPreview, SectionRenderPreview } from "@/components/cms/builder/SectionPreview";
import { SECTION_TYPES, SECTION_TYPE_LABEL } from "@/components/cms/builder/constants";
import { safeString } from "@/components/cms/builder/utils";
import { reorderCmsSections } from "@/lib/cms/v2";
import type { PageBuilderState } from "@/hooks/usePageBuilder";

export default function BuilderCanvas({
  builder,
}: {
  builder: PageBuilderState;
}) {
  const {
    sections,
    activeSectionId,
    setActiveSectionId,
    activeSlug,
    canEdit,
    siteKey,
    canvasMode,
    setCanvasMode,
    previewDevice,
    setPreviewDevice,
    showHeatmap,
    heatmapType,
    draggedSectionId,
    setDraggedSectionId,
    moveSection,
    moveSectionToIndex,
    loadSectionsAndVersions,
    newSectionType,
    setNewSectionType,
    addSection,
    token,
  } = builder;
  return (
        <section className="lg:col-span-6 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418] p-4 space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Canvas · {activeSlug ? `/${activeSlug}` : "Selecciona página"}</h2>
            <div className="flex items-center gap-2">
              {/* Canvas mode toggle */}
              <div className="inline-flex rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden">
                <button
                  onClick={() => setCanvasMode("esquema")}
                  className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${canvasMode === "esquema" ? "bg-primary text-white" : "bg-transparent"}`}
                  title="Vista esquemática"
                >
                  <LayoutPanelTop size={11} /> Esquema
                </button>
                <button
                  onClick={() => setCanvasMode("render")}
                  className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${canvasMode === "render" ? "bg-primary text-white" : "bg-transparent"}`}
                  title="Vista render real"
                >
                  <Eye size={11} /> Render
                </button>
              </div>
              {/* Device toggle */}
              <div className="inline-flex rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden">
                <button
                  onClick={() => setPreviewDevice("desktop")}
                  className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${previewDevice === "desktop" ? "bg-primary text-white" : "bg-transparent"}`}
                >
                  <Monitor size={11} /> Desktop
                </button>
                <button
                  onClick={() => setPreviewDevice("mobile")}
                  className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${previewDevice === "mobile" ? "bg-primary text-white" : "bg-transparent"}`}
                >
                  <Smartphone size={11} /> Mobile
                </button>
              </div>
              <select value={newSectionType} onChange={(e) => setNewSectionType(e.target.value)} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-sm">
                {SECTION_TYPES.map((type) => <option key={type} value={type}>{SECTION_TYPE_LABEL[type] ?? type}</option>)}
              </select>
              <button onClick={() => addSection()} disabled={!activeSlug || !canEdit} className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50">
                <Plus size={12} /> Añadir
              </button>
            </div>
          </div>

          <div className={`space-y-3 ${previewDevice === "mobile" ? "max-w-[420px] mx-auto" : ""}`}>
            {sections.map((section) => (
              <div
                key={section.id}
                draggable={canEdit}
                onDragStart={() => setDraggedSectionId(section.id)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={async () => {
                  if (draggedSectionId && draggedSectionId !== section.id) {
                    await moveSectionToIndex(draggedSectionId, section.id);
                  }
                  setDraggedSectionId(null);
                }}
                onDragEnd={() => setDraggedSectionId(null)}
                className={`rounded-md border p-3 cursor-grab active:cursor-grabbing ${section.status === "archived" ? "opacity-70 border-amber-200 bg-amber-50/40 dark:bg-amber-500/5" : section.id === activeSectionId ? "border-primary/40 bg-primary/5" : "border-[hsl(var(--border))] dark:border-white/10"}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <button onClick={() => setActiveSectionId(section.id)} className="text-left">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      {section.type} {section.status === "archived" ? "· archivada" : ""}
                    </p>
                    <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{safeString(section.props_json?.title) || "Sección"}</p>
                  </button>
                  <div className="flex items-center gap-1">
                    <button onClick={() => moveSection(section.id, "up")} disabled={!canEdit} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-1.5 disabled:opacity-50"><ArrowUp size={12} /></button>
                    <button onClick={() => moveSection(section.id, "down")} disabled={!canEdit} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-1.5 disabled:opacity-50"><ArrowDown size={12} /></button>
                  </div>
                </div>
                <div className="relative mt-3">
                  {canvasMode === "render" ? (
                    <SectionRenderPreview section={section} mobile={previewDevice === "mobile"} />
                  ) : (
                    <SectionPreview section={section} />
                  )}
                  {showHeatmap && (
                    <div className="absolute inset-0 pointer-events-none z-10 overflow-hidden rounded-lg">
                      {heatmapType === "clicks" && (
                        <div className="absolute inset-0 bg-red-500/[0.02] backdrop-blur-[0.2px]">
                          <div className="absolute top-1/4 left-1/4 w-12 h-12 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.75)_0%,rgba(245,158,11,0.4)_50%,rgba(0,0,0,0)_100%)] animate-pulse inline-flex items-center justify-center"><span className="text-[7px] text-white font-bold opacity-60">72%</span></div>
                          <div className="absolute top-2/3 left-1/2 w-18 h-18 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.65)_0%,rgba(16,185,129,0.3)_60%,rgba(0,0,0,0)_100%)]" style={{ animationDelay: "300ms" }} />
                          <div className="absolute top-1/3 left-2/3 w-14 h-14 rounded-full bg-[radial-gradient(circle,rgba(59,130,246,0.65)_0%,rgba(0,0,0,0)_80%)]" style={{ animationDelay: "600ms" }} />
                          <div className="absolute top-1/2 left-[80%] w-10 h-10 rounded-full bg-[radial-gradient(circle,rgba(245,158,11,0.75)_0%,rgba(0,0,0,0)_90%)]" />
                        </div>
                      )}
                      {heatmapType === "scroll" && (
                        <div className="absolute inset-0 flex flex-col justify-between text-[8px] font-bold text-white/90">
                          <div className="w-full h-[25%] bg-gradient-to-b from-emerald-500/20 to-transparent border-t border-emerald-500/40 p-1">100% de usuarios visualizan esta zona (Above the fold)</div>
                          <div className="w-full h-[25%] bg-gradient-to-b from-yellow-500/20 to-transparent border-t border-yellow-500/40 p-1">78% de usuarios se desplazan hasta aquí</div>
                          <div className="w-full h-[25%] bg-gradient-to-b from-orange-500/20 to-transparent border-t border-orange-500/40 p-1">45% de usuarios continúan leyendo</div>
                          <div className="w-full h-[25%] bg-gradient-to-b from-red-500/20 to-red-500/5 border-t border-red-500/40 p-1">22% de usuarios llegan al final</div>
                        </div>
                      )}
                      {heatmapType === "attention" && (
                        <div className="absolute inset-0 bg-blue-500/[0.02]">
                          <div className="absolute top-[30%] left-[20%] w-32 h-32 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.45)_0%,rgba(245,158,11,0.25)_40%,rgba(59,130,246,0.1)_70%,transparent_100%)] blur-[4px]" />
                          <div className="absolute top-[60%] left-[60%] w-44 h-44 rounded-full bg-[radial-gradient(circle,rgba(245,158,11,0.4)_0%,rgba(16,185,129,0.2)_50%,transparent_100%)] blur-[6px]" />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {sections.length === 0 && <p className="text-sm text-[hsl(var(--text-secondary))]">No hay secciones en esta página.</p>}
            {sections.length > 0 && (
              <div
                onDragOver={(event) => event.preventDefault()}
                onDrop={async () => {
                  if (!canEdit || !token || !activeSlug || !draggedSectionId) return;
                  const moved = sections.find((item) => item.id === draggedSectionId);
                  if (!moved) return;
                  const next = [...sections.filter((item) => item.id !== draggedSectionId), moved];
                  const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
                  await reorderCmsSections(siteKey, activeSlug, payload, token);
                  setDraggedSectionId(null);
                  await loadSectionsAndVersions(activeSlug);
                }}
                className="rounded-md border border-dashed border-[hsl(var(--border))] dark:border-white/20 p-3 text-center text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]"
              >
                Soltar aquí para mover al final
              </div>
            )}
          </div>
        </section>

  );
}

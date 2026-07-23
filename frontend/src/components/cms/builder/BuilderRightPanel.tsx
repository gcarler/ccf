"use client";

import React, { useEffect, useState } from "react";
import {
  Eye, ExternalLink, FileImage, ImageIcon, Save, Send, Settings,
  Sparkles, BarChart3, CheckCircle2, AlertTriangle, XCircle, Wand2, RefreshCw,
  Upload, Undo2,
} from "lucide-react";
import { SITE_URL } from "@/lib/site-config";
import { asObject } from "@/components/cms/builder/utils";
import OptimizedImage from "@/components/ui/OptimizedImage";
import BuilderSectionInspector from "./BuilderSectionInspector";
import { getPageAnalytics, type PageAnalytics } from "@/lib/cms/v2";
import type { PageBuilderState, AiTemplate, AiTone } from "@/hooks/usePageBuilder";

/* ── JSON-LD Preview Component ─────────────────────────────────────── */

interface JsonLdPreviewProps {
  pageTitle: string;
  slug: string;
  seoTitle: string;
  seoDescription: string;
  seoImage: string;
  canonicalUrl: string;
  sections: Array<{ type: string; props_json: Record<string, unknown> }>;
  siteUrl: string;
}

function JsonLdPreview({ pageTitle, slug, seoTitle, seoDescription, seoImage, canonicalUrl, sections, siteUrl }: JsonLdPreviewProps) {
  const baseUrl = siteUrl.startsWith("http") ? siteUrl : `https://${siteUrl}`;
  const url = canonicalUrl || `${baseUrl.replace(/\/$/, "")}/${slug}`;
  const title = seoTitle || pageTitle || "Página";
  const description = seoDescription || undefined;
  const image = seoImage || undefined;

  // Detect FAQ sections
  const faqItems: Array<{ question: string; answer: string }> = [];
  sections.forEach((s) => {
    if (s.type === "faq") {
      const props = s.props_json || {};
      const items = (props.items as Array<Record<string, string>>) || (props.faqs as Array<Record<string, string>>) || [];
      items.forEach((item) => {
        const q = item.q || item.question || "";
        const a = item.a || item.answer || "";
        if (q && a) faqItems.push({ question: q, answer: a });
      });
    }
  });

  // Detect Article signals (rich_text heavy)
  const hasArticle = sections.some((s) => s.type === "rich_text" || s.type === "rich_text_columns");

  let jsonLd: Record<string, unknown> | null = null;

  if (faqItems.length > 0) {
    jsonLd = {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: faqItems.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: {
          "@type": "Answer",
          text: item.answer,
        },
      })),
      url,
    };
  } else if (hasArticle) {
    let wordCount = 0;
    sections.forEach((s) => {
      const body = (s.props_json?.body as string) || "";
      wordCount += body.split(/\s+/).filter(Boolean).length;
    });
    jsonLd = {
      "@context": "https://schema.org",
      "@type": "Article",
      headline: title,
      url,
      ...(description ? { description } : {}),
      ...(image ? { image } : {}),
      ...(wordCount > 0 ? { wordCount } : {}),
    };
  } else {
    jsonLd = {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: title,
      url,
      ...(description ? { description } : {}),
      ...(image ? { image } : {}),
    };
  }

  const jsonString = JSON.stringify(jsonLd, null, 2);

  return (
    <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
          Vista previa JSON-LD (Schema.org)
        </p>
        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[hsl(var(--info-muted))] text-[hsl(var(--info))]">
          {faqItems.length > 0 ? "FAQPage" : hasArticle ? "Article" : "WebPage"}
        </span>
      </div>
      <pre className="text-[10px] font-mono bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md p-2 max-h-40 overflow-y-auto whitespace-pre-wrap break-all">
        <code>{jsonString}</code>
      </pre>
      <p className="text-[9px] text-[hsl(var(--text-secondary))]">
        Este structured data se inyecta automáticamente en el &lt;head&gt; de la página pública.
      </p>
    </div>
  );
}

export default function BuilderRightPanel({
  builder,
}: {
  builder: PageBuilderState;
}) {
  const {
    activePage, activeSlug, siteKey, canEdit, canPublish, note, setNote,
    versions, publishLogs, runWorkflow, rollback, savePageMetadata, togglePageArchive,
    pageTitleDraft, setPageTitleDraft, pageSlugDraft, setPageSlugDraft,
    seoTitleDraft, setSeoTitleDraft, seoDescriptionDraft, setSeoDescriptionDraft,
    seoImageDraft, setSeoImageDraft, seoCanonicalDraft, setSeoCanonicalDraft, seoRobotsDraft, setSeoRobotsDraft,
    seoKeyword, setSeoKeyword, seoAnalysis, readabilityScore,
    serpPreviewDevice, setSerpPreviewDevice, activeRightTab, setActiveRightTab,
    aiPrompt, setAiPrompt, aiGenerating, aiOutput, aiTone, setAiTone, aiTemplate, setAiTemplate,
    handleAiGenerate, handleAiImageGenerate, handleInsertAiAsSection, handleReplaceActiveSectionWithAi,
    aiImagePrompt, setAiImagePrompt, aiImageResult, setAiImageResult, aiImageGenerating,
    showHeatmap, setShowHeatmap, timeframe, setTimeframe, heatmapType, setHeatmapType,
    abTestingActive, setAbTestingActive, abTrafficSplit, setAbTrafficSplit,
    activeSite, setMediaPickerOpen, setMediaPickerTarget,
    activeSectionId, activeSection, updateSectionPropsLocal, saveSectionProps,
  } = builder;

  // Fetch real analytics data for the active page
  const [analytics, setAnalytics] = useState<PageAnalytics | null>(null);
  useEffect(() => {
    if (!activeSlug || activeRightTab !== "analytics") return;
    const days = timeframe === "7d" ? 7 : timeframe === "30d" ? 30 : 365;
    getPageAnalytics(activeSlug, days)
      .then(setAnalytics)
      .catch(() => setAnalytics(null));
  }, [activeSlug, activeRightTab, timeframe]);

  return (
        <aside className="lg:col-span-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-4 space-y-4 max-h-[90vh] overflow-y-auto">
          {/* Tab Selection Header */}
          <div className="flex border-b border-[hsl(var(--border))] dark:border-white/10 pb-2 gap-1 overflow-x-auto">
            <button
              onClick={() => setActiveRightTab("config")}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all ${activeRightTab === "config" ? "bg-[hsl(var(--primary))] text-white" : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"}`}
            >
              <Settings size={12} /> Config
            </button>
            <button
              onClick={() => setActiveRightTab("seo")}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all ${activeRightTab === "seo" ? "bg-[hsl(var(--primary))] text-white" : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"}`}
            >
              <Sparkles size={12} /> SEO
            </button>
            <button
              onClick={() => setActiveRightTab("ai")}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all ${activeRightTab === "ai" ? "bg-[hsl(var(--primary))] text-white" : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"}`}
            >
              <Wand2 size={12} /> Asistente IA
            </button>
            <button
              onClick={() => setActiveRightTab("analytics")}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all ${activeRightTab === "analytics" ? "bg-[hsl(var(--primary))] text-white" : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"}`}
            >
              <BarChart3 size={12} /> Métricas
            </button>
          </div>

          {/* TAB 1: CONFIG */}
          {activeRightTab === "config" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Estado página</p>
                <p className="text-sm font-bold">{activePage?.title || "Sin página"}</p>
                <p className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))]">{activePage?.status || "-"}</p>
                <input
                  value={pageTitleDraft}
                  onChange={(e) => setPageTitleDraft(e.target.value)}
                  placeholder="Título de página"
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />
                <input
                  value={pageSlugDraft}
                  onChange={(e) => setPageSlugDraft(e.target.value)}
                  placeholder="slug-de-pagina"
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />
                <div className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 p-3 space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">SEO Básico</p>
                  <input
                    value={seoTitleDraft}
                    onChange={(e) => setSeoTitleDraft(e.target.value)}
                    placeholder="Titulo SEO"
                    className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                  />
                  <textarea
                    value={seoDescriptionDraft}
                    onChange={(e) => setSeoDescriptionDraft(e.target.value)}
                    placeholder="Descripcion para buscadores y redes"
                    className="w-full min-h-[72px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                  />
                  {seoImageDraft ? (
                    <div className="overflow-hidden rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5">
                      <OptimizedImage src={seoImageDraft} alt="Imagen SEO" width={200} height={96} className="h-24 w-full object-cover" />
                    </div>
                  ) : (
                    <div className="rounded-md border border-dashed border-[hsl(var(--border))] dark:border-white/20 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-3 text-center text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      Sin imagen social
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setMediaPickerTarget("seo");
                      setMediaPickerOpen(true);
                    }}
                    disabled={!canEdit}
                    className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <ImageIcon size={13} /> Elegir imagen SEO
                  </button>
                  <input
                    value={seoImageDraft}
                    onChange={(e) => setSeoImageDraft(e.target.value)}
                    placeholder="URL de imagen social"
                    className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                  />
                </div>
                <button
                  onClick={savePageMetadata}
                  disabled={!activePage || !canEdit}
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50"
                >
                  Guardar pagina/SEO
                </button>
                <textarea value={note} onChange={(e) => setNote(e.target.value)} disabled={!canEdit && !canPublish} placeholder="Nota para workflow..." className="w-full rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs disabled:opacity-60" />
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => runWorkflow("submit_review")} disabled={!activeSlug || !canEdit} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"><Send size={11} /> Review</button>
                  <button onClick={() => runWorkflow("approve")} disabled={!activeSlug || !canPublish} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"><Save size={11} /> Aprobar</button>
                  <button onClick={() => runWorkflow("publish")} disabled={!activeSlug || !canPublish} className="rounded-lg bg-primary text-white px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"><Upload size={11} /> Publicar</button>
                  <button onClick={() => runWorkflow("revert_draft")} disabled={!activeSlug || !canEdit} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"><Undo2 size={11} /> Draft</button>
                  <button onClick={() => runWorkflow("archive")} disabled={!activeSlug || !canPublish} className="col-span-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50">Archivar</button>
                </div>
                <button
                  onClick={() => {
                    if (!activeSlug) return;
                    window.open(`/plataforma/cms/preview?site=${encodeURIComponent(siteKey)}&page=${encodeURIComponent(activeSlug)}`, "_blank");
                  }}
                  disabled={!activeSlug}
                  className="w-full rounded-lg border border-[hsl(var(--info-muted))] text-[hsl(var(--info))] px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <Eye size={11} /> Vista previa borrador
                </button>
                <button
                  onClick={() => {
                    if (!activeSlug) return;
                    const base = activeSite?.base_path || `/${siteKey}`;
                    const normalized = base.endsWith("/") ? base.slice(0, -1) : base;
                    window.open(`${normalized}/${activeSlug}`, "_blank");
                  }}
                  disabled={!activeSlug}
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <ExternalLink size={11} /> Ver página pública
                </button>
                <button
                  onClick={togglePageArchive}
                  disabled={!activePage || !canEdit}
                  className={`w-full rounded-lg border px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50 ${activePage?.status === "archived" ? "border-[hsl(var(--success)/0.3)] text-[hsl(var(--success))]" : "border-[hsl(var(--warning)/0.3)] text-[hsl(var(--warning))]"}`}
                >
                  {activePage?.status === "archived" ? "Restaurar pagina" : "Archivar pagina"}
                </button>
              </div>

              <div className="space-y-2 pt-2 border-t border-[hsl(var(--border))] dark:border-white/10">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Versiones</p>
                <div className="max-h-40 overflow-auto space-y-2 pr-1">
                  {versions.map((version) => (
                    <button key={version.id} onClick={() => rollback(version.id)} disabled={!canPublish} className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-2 text-left text-xs hover:border-primary/40 transition-all disabled:opacity-50 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                      <p className="font-semibold">v{version.version_number}</p>
                      <p className="text-[10px] text-[hsl(var(--text-secondary))]">{new Date(version.created_at).toLocaleString()}</p>
                    </button>
                  ))}
                  {versions.length === 0 && <p className="text-xs text-[hsl(var(--text-secondary))]">Aún sin versiones publicadas.</p>}
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-[hsl(var(--border))] dark:border-white/10">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Historial de Cambios</p>
                <div className="max-h-40 overflow-auto space-y-2 pr-1">
                  {publishLogs.map((entry) => {
                    const notes = typeof entry.metadata_json?.notes === "string" ? entry.metadata_json.notes : "";
                    return (
                      <div key={entry.id} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-2 text-xs bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-semibold uppercase tracking-wide text-[9px]">{entry.action}</p>
                          <p className="text-[9px] text-[hsl(var(--text-secondary))]">{new Date(entry.created_at).toLocaleTimeString()}</p>
                        </div>
                        <p className="mt-0.5 text-[9px] text-[hsl(var(--text-secondary))]">{entry.from_status || "sin estado"} &rarr; {entry.to_status || "sin estado"}</p>
                        {notes && <p className="mt-1 text-[9px] text-[hsl(var(--text-secondary))] line-clamp-2">{notes}</p>}
                      </div>
                    );
                  })}
                  {publishLogs.length === 0 && <p className="text-xs text-[hsl(var(--text-secondary))]">Aun sin eventos de workflow.</p>}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: SEO ANALYZER */}
          {activeRightTab === "seo" && (
            <div className="space-y-4 animate-fade-in">
              <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Palabra Clave Objetivo</p>
                <input
                  value={seoKeyword}
                  onChange={(e) => setSeoKeyword(e.target.value)}
                  placeholder="Ej: jóvenes, adoración, testimonios"
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                />
                <p className="text-[9px] text-[hsl(var(--text-secondary))]">Palabra clave principal para medir el SEO on-page.</p>
              </div>

              <div className="space-y-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Puntaje SEO</p>
                  <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold text-white ${seoAnalysis.score >= 80 ? "bg-[hsl(var(--success))]" : seoAnalysis.score >= 50 ? "bg-[hsl(var(--warning))]" : "bg-[hsl(var(--destructive))]"}`}>
                    {seoAnalysis.score}%
                  </span>
                </div>
                <div className="w-full bg-[hsl(var(--surface-3))] dark:bg-white/10 h-2.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${seoAnalysis.score >= 80 ? "bg-[hsl(var(--success))]" : seoAnalysis.score >= 50 ? "bg-[hsl(var(--warning))]" : "bg-[hsl(var(--destructive))]"}`}
                    style={{ width: `${seoAnalysis.score}%` }}
                  />
                </div>
                <p className="text-[10px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                  {seoAnalysis.score >= 80
                    ? "¡Excelente! Tu página cumple con los estándares óptimos de SEO on-page."
                    : seoAnalysis.score >= 50
                    ? "Aceptable. Considera añadir la palabra clave y mejorar las descripciones."
                    : "Crítico. Agrega título SEO, descripción y alt text para mejorar el ranking."}
                </p>
              </div>

              {/* READABILITY SCORE */}
              <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                  <span>Legibilidad de Lectura</span>
                  <span className="text-[hsl(var(--success))] font-bold">{readabilityScore.score}/100</span>
                </div>
                <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{readabilityScore.label}</p>
                <p className="text-[9px] text-[hsl(var(--text-secondary))]">Medido utilizando la densidad silábica y longitud de oraciones de las secciones activas.</p>
              </div>

              {/* SERP PREVIEW */}
              <div className="space-y-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Simulador SERP Google</p>
                  <div className="inline-flex rounded border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden">
                    <button
                      onClick={() => setSerpPreviewDevice("desktop")}
                      className={`px-1.5 py-0.5 text-[8px] font-bold uppercase transition-all ${serpPreviewDevice === "desktop" ? "bg-primary text-white" : "bg-transparent text-[hsl(var(--text-secondary))]"}`}
                    >
                      PC
                    </button>
                    <button
                      onClick={() => setSerpPreviewDevice("mobile")}
                      className={`px-1.5 py-0.5 text-[8px] font-bold uppercase transition-all ${serpPreviewDevice === "mobile" ? "bg-primary text-white" : "bg-transparent text-[hsl(var(--text-secondary))]"}`}
                    >
                      Móvil
                    </button>
                  </div>
                </div>

                <div className={`rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] font-sans ${serpPreviewDevice === "mobile" ? "max-w-[280px]" : "w-full"}`}>
                  {serpPreviewDevice === "mobile" ? (
                    <div className="space-y-1">
                      <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--text-secondary))]">
                        <span className="w-4 h-4 rounded-full bg-[hsl(var(--surface-3))] flex items-center justify-center text-[8px] font-bold">⛪</span>
                        <div className="truncate text-left">{SITE_URL || siteKey} &rsaquo; {activeSlug || "slug"}</div>
                      </div>
                      <div className="text-base text-[hsl(var(--info))] hover:underline cursor-pointer font-medium leading-tight line-clamp-2 text-left">
                        {seoTitleDraft || activePage?.title || "Sin título SEO"}
                      </div>
                      <div className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed line-clamp-3 text-left">
                        {seoDescriptionDraft || "Define una descripción para ver la vista previa social..."}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1 text-left">
                      <div className="text-[12px] text-[hsl(var(--text-secondary))] leading-none">
                        https://{SITE_URL || siteKey} &rsaquo; {activeSlug || "slug"}
                      </div>
                      <div className="text-lg text-[hsl(var(--info))] hover:underline cursor-pointer font-normal leading-normal line-clamp-1">
                        {seoTitleDraft || activePage?.title || "Sin título SEO"}
                      </div>
                      <div className="text-[13px] text-[hsl(var(--text-secondary))] leading-relaxed line-clamp-2">
                        {seoDescriptionDraft || "Define una descripción para ver la vista previa social..."}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* ADVANCED SEO */}
              <div className="space-y-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">SEO Técnico</p>
                <div className="space-y-2">
                  <div>
                    <label className="text-[9px] uppercase tracking-wide font-bold text-[hsl(var(--text-secondary))] block mb-1">Canonical URL</label>
                    <input
                      value={seoCanonicalDraft}
                      onChange={(e) => setSeoCanonicalDraft(e.target.value)}
                      placeholder={`${SITE_URL || "https://ejemplo.com"}/${activePage?.slug || ""}`}
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <p className="text-[9px] text-[hsl(var(--text-secondary))] mt-1">Si se deja vacío, se usa la URL automática de la página.</p>
                  </div>
                  <div>
                    <label className="text-[9px] uppercase tracking-wide font-bold text-[hsl(var(--text-secondary))] block mb-1">Meta Robots</label>
                    <select
                      value={seoRobotsDraft}
                      onChange={(e) => setSeoRobotsDraft(e.target.value)}
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    >
                      <option value="">index, follow (por defecto)</option>
                      <option value="index, nofollow">index, nofollow</option>
                      <option value="noindex, follow">noindex, follow</option>
                      <option value="noindex, nofollow">noindex, nofollow</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* JSON-LD PREVIEW */}
              <JsonLdPreview
                pageTitle={activePage?.title || ""}
                slug={activePage?.slug || ""}
                seoTitle={seoTitleDraft}
                seoDescription={seoDescriptionDraft}
                seoImage={seoImageDraft}
                canonicalUrl={seoCanonicalDraft}
                sections={builder.sections}
                siteUrl={SITE_URL || siteKey}
              />

              <div className="space-y-2">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Recomendaciones SEO</p>
                <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                  {seoAnalysis.checks.map((check) => (
                    <div key={check.id} className="flex gap-2.5 items-start p-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))]/30 dark:bg-white/[0.01]">
                      {check.type === "success" && <CheckCircle2 className="text-[hsl(var(--success))] mt-0.5 shrink-0" size={14} />}
                      {check.type === "warning" && <AlertTriangle className="text-[hsl(var(--warning))] mt-0.5 shrink-0" size={14} />}
                      {check.type === "error" && <XCircle className="text-[hsl(var(--destructive))] mt-0.5 shrink-0" size={14} />}
                      <div>
                        <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{check.label}</p>
                        <p className="text-[10px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-0.5">{check.tip}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: AI ASSISTANT */}
          {activeRightTab === "ai" && (
            <div className="space-y-4 animate-fade-in">
              <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Asistente IA Editorial</p>
                
                <div className="space-y-3">
                  <div>
                    <label className="text-[9px] uppercase tracking-wide font-bold text-[hsl(var(--text-secondary))] block mb-1">Plantilla IA</label>
                    <select
                      value={aiTemplate}
                      onChange={(e) => setAiTemplate(e.target.value as AiTemplate)}
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    >
                      <option value="aida">Fórmula AIDA (Atención-Interés-Deseo-Acción)</option>
                      <option value="pas">Fórmula PAS (Problema-Agitación-Solución)</option>
                      <option value="headlines">Titulares de Alto Impacto para Hero</option>
                      <option value="improve">Mejorar Texto / Optimizar Mensaje</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[9px] uppercase tracking-wide font-bold text-[hsl(var(--text-secondary))] block mb-1">Tono de Voz</label>
                    <select
                      value={aiTone}
                      onChange={(e) => setAiTone(e.target.value as AiTone)}
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    >
                      <option value="warm">Cálido y Cercano (Comunidad)</option>
                      <option value="inspiration">Inspiracional y Profundo (Fe)</option>
                      <option value="formal">Respetuoso e Institucional (Iglesia)</option>
                      <option value="dynamic">Dinámico y Moderno (Jóvenes)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[9px] uppercase tracking-wide font-bold text-[hsl(var(--text-secondary))] block mb-1">Temática / Contexto</label>
                    <textarea
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder="Ej: Queremos invitar a las familias al pícnic de este domingo..."
                      className="w-full min-h-[64px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                </div>

                <button
                  onClick={handleAiGenerate}
                  disabled={aiGenerating || !aiPrompt.trim()}
                  className="w-full mt-3 rounded-lg bg-[hsl(var(--primary))] px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {aiGenerating ? (
                    <>
                      <RefreshCw size={12} className="animate-spin" /> Asistente IA redactando...
                    </>
                  ) : (
                    <>
                      <Wand2 size={12} /> Generar Contenido IA
                    </>
                  )}
                </button>
              </div>

              {aiOutput && (
                <div className="space-y-3 mt-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Resultado Generado</p>
                  <div className="p-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[11px] font-mono max-h-[180px] overflow-y-auto whitespace-pre-wrap animate-fade-in">
                    {aiOutput}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={handleInsertAiAsSection}
                      className="rounded-lg bg-[hsl(var(--success))] text-white px-2 py-1.5 text-[9px] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--success)/0.8)] transition-all inline-flex items-center justify-center gap-1"
                    >
                      Insertar final
                    </button>
                    <button
                      onClick={handleReplaceActiveSectionWithAi}
                      disabled={!activeSectionId}
                      className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-[9px] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all inline-flex items-center justify-center gap-1 disabled:opacity-40"
                    >
                      Reemplazar activa
                    </button>
                  </div>
                </div>
              )}

              {/* MOCK AI IMAGE GENERATOR */}
              <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02] mt-3">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Generador de Imágenes IA</p>
                <input
                  value={aiImagePrompt}
                  onChange={(e) => setAiImagePrompt(e.target.value)}
                  placeholder="Ej: Jóvenes cantando, picnic de iglesia, Biblia..."
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs mb-2"
                />
                <button
                  onClick={handleAiImageGenerate}
                  disabled={aiImageGenerating || !aiImagePrompt.trim()}
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {aiImageGenerating ? (
                    <>
                      <RefreshCw size={12} className="animate-spin" /> Generando...
                    </>
                  ) : (
                    <>
                      <FileImage size={12} /> Generar Imagen Premium
                    </>
                  )}
                </button>

                {aiImageResult && (
                  <div className="space-y-2 mt-2 animate-fade-in">
                    <OptimizedImage src={aiImageResult} alt="Resultado IA" width={200} height={112} className="h-28 w-full object-cover rounded-lg border border-[hsl(var(--border))] dark:border-white/10" />
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => {
                          if (!activeSection) return;
                          const nextProps = { ...asObject(activeSection.props_json), image_url: aiImageResult };
                          updateSectionPropsLocal(nextProps);
                          saveSectionProps(nextProps);
                          setAiImageResult("");
                        }}
                        disabled={!activeSectionId}
                        className="rounded-lg bg-[hsl(var(--success))] text-white px-2 py-1 text-[9px] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--success)/0.8)] disabled:opacity-40"
                      >
                        Usar en Sección
                      </button>
                      <button
                        onClick={() => {
                          setSeoImageDraft(aiImageResult);
                          setAiImageResult("");
                        }}
                        className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"
                      >
                        Usar en SEO
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: METRICS & HEATMAP */}
          {activeRightTab === "analytics" && (
            <div className="space-y-4 animate-fade-in">
              {/* TIMEFRAME SELECTOR */}
              <div className="flex border border-[hsl(var(--border))] dark:border-white/10 rounded-lg overflow-hidden text-[9px] font-semibold uppercase tracking-wide">
                <button
                  onClick={() => setTimeframe("7d")}
                  className={`flex-1 py-1.5 text-center transition-all ${timeframe === "7d" ? "bg-primary text-white" : "bg-transparent text-[hsl(var(--text-secondary))]"}`}
                >
                  7 días
                </button>
                <button
                  onClick={() => setTimeframe("30d")}
                  className={`flex-1 py-1.5 text-center transition-all border-x border-[hsl(var(--border))] dark:border-white/10 ${timeframe === "30d" ? "bg-primary text-white" : "bg-transparent text-[hsl(var(--text-secondary))]"}`}
                >
                  30 días
                </button>
                <button
                  onClick={() => setTimeframe("all")}
                  className={`flex-1 py-1.5 text-center transition-all ${timeframe === "all" ? "bg-primary text-white" : "bg-transparent text-[hsl(var(--text-secondary))]"}`}
                >
                  Histórico
                </button>
              </div>

              {/* DYNAMIC METRIC CARDS */}
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                  <p className="text-[8px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Visitas Totales</p>
                  <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white mt-1">
                    {analytics?.total_views?.toLocaleString() ?? "—"}
                  </p>
                  <span className="text-[9px] font-bold text-[hsl(var(--success))] inline-flex items-center gap-0.5 mt-1">
                    {analytics ? `${analytics.days}d` : "Sin datos"}
                  </span>
                </div>
                <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                  <p className="text-[8px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Visitas / Día</p>
                  <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white mt-1">
                    {analytics?.daily_views?.length
                      ? Math.round(analytics.total_views / analytics.daily_views.length).toLocaleString()
                      : "—"}
                  </p>
                  <span className="text-[9px] font-bold text-[hsl(var(--success))] inline-flex items-center gap-0.5 mt-1">
                    Promedio
                  </span>
                </div>
                <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                  <p className="text-[8px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Pico Máximo</p>
                  <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white mt-1">
                    {analytics?.daily_views?.length
                      ? Math.max(...analytics.daily_views.map(d => d.views)).toLocaleString()
                      : "—"}
                  </p>
                  <span className="text-[9px] font-bold text-[hsl(var(--success))] inline-flex items-center gap-0.5 mt-1">
                    {analytics?.daily_views?.length ? `en ${analytics.daily_views.length} días` : "Sin datos"}
                  </span>
                </div>
                <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                  <p className="text-[8px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Días con Actividad</p>
                  <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white mt-1">
                    {analytics?.daily_views?.filter(d => d.views > 0).length ?? "—"}
                  </p>
                  <span className="text-[9px] font-bold text-[hsl(var(--success))] inline-flex items-center gap-0.5 mt-1">
                    de {analytics?.days ?? "—"} días
                  </span>
                </div>
              </div>

              {/* AB TESTING SIMULATOR */}
              <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02] space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] font-bold text-primary">Test A/B Integrado</p>
                  <button
                    onClick={() => setAbTestingActive(!abTestingActive)}
                    className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase transition-all ${abTestingActive ? "bg-[hsl(var(--success))] text-white animate-pulse" : "bg-[hsl(var(--surface-3))] dark:bg-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"}`}
                  >
                    {abTestingActive ? "Activo" : "Inactivo"}
                  </button>
                </div>
                
                {abTestingActive ? (
                  <div className="space-y-2.5 animate-fade-in text-[10px]">
                    <div className="space-y-1">
                      <div className="flex justify-between text-[hsl(var(--text-secondary))]">
                        <span>Tráfico Variante A (Original)</span>
                        <span className="font-bold">{100 - abTrafficSplit}%</span>
                      </div>
                      <div className="flex justify-between text-[hsl(var(--text-secondary))]">
                        <span>Tráfico Variante B (Alternativa)</span>
                        <span className="font-bold">{abTrafficSplit}%</span>
                      </div>
                      <input
                        type="range"
                        min="10"
                        max="90"
                        value={abTrafficSplit}
                        onChange={(e) => setAbTrafficSplit(Number(e.target.value))}
                        className="w-full accent-primary h-1 bg-[hsl(var(--surface-3))] dark:bg-white/10 rounded-lg cursor-pointer"
                      />
                    </div>

                    <div className="rounded border p-2 bg-[hsl(var(--surface-2))]/40 dark:bg-white/[0.01] space-y-1">
                      <p className="font-bold uppercase tracking-wider text-[8px] text-[hsl(var(--text-secondary))]">Simulación de Conversión</p>
                      <div className="flex justify-between">
                        <span>Conversión Variante A:</span>
                        <span className="font-mono">3.2%</span>
                      </div>
                      <div className="flex justify-between text-[hsl(var(--success))] font-bold">
                        <span>Conversión Variante B:</span>
                        <span className="font-mono">4.9% (▲ +53%)</span>
                      </div>
                      <p className="text-[8px] text-[hsl(var(--text-secondary))] mt-1">Confianza estadística: <strong className="text-[hsl(var(--success))] font-bold">97.4%</strong> (Resultado Significativo)</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-[9px] text-[hsl(var(--text-secondary))]">WordPress requiere plugins complejos para test A/B. Activa esta opción para diseñar variantes y dividir el tráfico automáticamente.</p>
                )}
              </div>

              {/* HEATMAP / LIVE CLICK MAP */}
              <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02] space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] font-bold">Mapa de Calor (Live)</p>
                  <button
                    onClick={() => setShowHeatmap(!showHeatmap)}
                    className={`px-3 py-1 rounded-md text-[9px] font-semibold uppercase tracking-wide transition-all ${showHeatmap ? "bg-[hsl(var(--destructive))] text-white animate-pulse" : "bg-[hsl(var(--surface-3))] dark:bg-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"}`}
                  >
                    {showHeatmap ? "Ver Activo" : "Activar"}
                  </button>
                </div>

                {showHeatmap && (
                  <div className="space-y-2 animate-fade-in">
                    <label className="text-[9px] uppercase tracking-wide font-bold text-[hsl(var(--text-secondary))] block mb-1">Tipo de Visualización</label>
                    <div className="flex rounded border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden text-[9px] font-bold text-center">
                      <button
                        onClick={() => setHeatmapType("clicks")}
                        className={`flex-1 py-1 transition-all ${heatmapType === "clicks" ? "bg-primary text-white" : "bg-transparent text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"}`}
                      >
                        Clics
                      </button>
                      <button
                        onClick={() => setHeatmapType("scroll")}
                        className={`flex-1 py-1 transition-all border-x border-[hsl(var(--border))] dark:border-white/10 ${heatmapType === "scroll" ? "bg-primary text-white" : "bg-transparent text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"}`}
                      >
                        Scroll
                      </button>
                      <button
                        onClick={() => setHeatmapType("attention")}
                        className={`flex-1 py-1 transition-all ${heatmapType === "attention" ? "bg-primary text-white" : "bg-transparent text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"}`}
                      >
                        Atención
                      </button>
                    </div>
                  </div>
                )}
                
                <p className="text-[9px] text-[hsl(var(--text-secondary))]">Representación visual interactiva en tiempo real sobre el canvas del comportamiento del usuario.</p>
              </div>
            </div>
          )}

      <BuilderSectionInspector builder={builder} />
    </aside>
  );
}

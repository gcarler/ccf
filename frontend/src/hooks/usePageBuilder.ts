"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  createCmsPage,
  createCmsSection,
  listCmsPageVersions,
  listCmsPagePublishLog,
  listCmsPages,
  listCmsSections,
  listCmsSites,
  patchCmsPage,
  patchCmsSection,
  reorderCmsSections,
  rollbackCmsPageVersion,
  workflowCmsPage,
} from "@/lib/cms/v2";
import { PAGE_TEMPLATES } from "@/components/cms/builder/constants";
import type { CmsPage, CmsPageVersion, CmsPublishLog, CmsSection, CmsTheme } from "@/types/cms-v2";
import { apiFetch } from "@/lib/http";
import { SITE_KEY } from "@/lib/site-config";
import { safeString, asObject, CANVAS_PREVIEW_TOKENS } from "@/components/cms/builder/utils";
import { toast } from "sonner";
import { notifyPreviewSync } from "@/lib/cms/preview-sync";

export type CanvasMode = "esquema" | "render";
export type PreviewDevice = "desktop" | "mobile";
export type RightTab = "config" | "seo" | "ai" | "analytics";
export type Timeframe = "7d" | "30d" | "all";
export type HeatmapType = "clicks" | "scroll" | "attention";
export type AiTemplate = "aida" | "pas" | "headlines" | "improve";
export type AiTone = "warm" | "inspiration" | "formal" | "dynamic";

export interface SeoCheck {
  id: string;
  label: string;
  passed: boolean;
  tip: string;
  type: "success" | "warning" | "error";
}

export interface UsePageBuilderOptions {
  token: string | null;
  userRole?: string;
  canEdit: boolean;
  canPublish: boolean;
}

export type PageBuilderState = ReturnType<typeof usePageBuilder>;

export function usePageBuilder({ token, canEdit, canPublish }: UsePageBuilderOptions) {
  const searchParams = useSearchParams();
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<Array<{ site_key: string; name: string; base_path: string }>>([]);
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [activeSlug, setActiveSlug] = useState("");
  const [sections, setSections] = useState<CmsSection[]>([]);
  const [versions, setVersions] = useState<CmsPageVersion[]>([]);
  const [publishLogs, setPublishLogs] = useState<CmsPublishLog[]>([]);
  const [newPageTitle, setNewPageTitle] = useState("");
  const [newSectionType, setNewSectionType] = useState("rich_text");
  const [pageTemplateKey, setPageTemplateKey] = useState("simple");
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [draggedSectionId, setDraggedSectionId] = useState<string | null>(null);
  const [previewDevice, setPreviewDevice] = useState<PreviewDevice>("desktop");
  const [canvasMode, setCanvasMode] = useState<CanvasMode>("esquema");
  const [pageTitleDraft, setPageTitleDraft] = useState("");
  const [pageSlugDraft, setPageSlugDraft] = useState("");
  const [seoTitleDraft, setSeoTitleDraft] = useState("");
  const [seoDescriptionDraft, setSeoDescriptionDraft] = useState("");
  const [seoImageDraft, setSeoImageDraft] = useState("");
  const [seoCanonicalDraft, setSeoCanonicalDraft] = useState("");
  const [seoRobotsDraft, setSeoRobotsDraft] = useState("");
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const [mediaPickerTarget, setMediaPickerTarget] = useState<"section" | "seo">("section");
  const [activeRightTab, setActiveRightTab] = useState<RightTab>("config");
  const [seoKeyword, setSeoKeyword] = useState("");
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiOutput, setAiOutput] = useState("");
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [timeframe, setTimeframe] = useState<Timeframe>("7d");
  const [heatmapType, setHeatmapType] = useState<HeatmapType>("clicks");
  const [abTestingActive, setAbTestingActive] = useState(false);
  const [abTrafficSplit, setAbTrafficSplit] = useState(50);
  const [serpPreviewDevice, setSerpPreviewDevice] = useState<PreviewDevice>("desktop");
  const [aiTone, setAiTone] = useState<AiTone>("warm");
  const [aiTemplate, setAiTemplate] = useState<AiTemplate>("aida");
  const [aiImagePrompt, setAiImagePrompt] = useState("");
  const [aiImageResult, setAiImageResult] = useState("");
  const [aiImageGenerating, setAiImageGenerating] = useState(false);
  const [canvasTokens, setCanvasTokens] = useState<React.CSSProperties>(CANVAS_PREVIEW_TOKENS);
  const [canvasThemeName, setCanvasThemeName] = useState<string>("Por defecto");
  const [themeLoading, setThemeLoading] = useState(false);
  const themeLoadingRef = useRef(false);
  const isMountedRef = useRef(true);
  const pendingLocalChangesRef = useRef(false);
  const autoSaveSectionRef = useRef<CmsSection | null>(null);

  // ── Derived state ────────────────────────────────────────────────────────
  const activePage = useMemo(() => pages.find((p) => p.slug === activeSlug) ?? null, [pages, activeSlug]);
  const activeSection = useMemo(() => sections.find((s) => s.id === activeSectionId) ?? null, [sections, activeSectionId]);
  const activeSite = useMemo(() => sites.find((site) => site.site_key === siteKey) ?? null, [sites, siteKey]);

  // ── Loaders ──────────────────────────────────────────────────────────────
  const loadPages = useCallback(async (targetSite: string) => {
    if (!token) return;
    const [nextSites, nextPages] = await Promise.all([
      listCmsSites(token),
      listCmsPages(targetSite, token),
    ]);
    setSites((nextSites || []).map((site) => ({
      site_key: site.site_key,
      name: site.name,
      base_path: site.base_path,
    })));
    setPages(nextPages || []);
    if ((nextPages || []).length > 0 && !activeSlug) {
      setActiveSlug(nextPages[0].slug);
    }
  }, [token, activeSlug]);

  const loadSectionsAndVersions = useCallback(async (slug: string) => {
    if (!token || !slug) return;
    const [nextSections, nextVersions, nextPublishLogs] = await Promise.all([
      listCmsSections(siteKey, slug, token),
      listCmsPageVersions(siteKey, slug, token),
      listCmsPagePublishLog(siteKey, slug, token),
    ]);
    const ordered = (nextSections || []).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    setSections(ordered);
    setVersions(nextVersions || []);
    setPublishLogs(nextPublishLogs || []);
    if (ordered.length > 0) {
      setActiveSectionId((prev) => {
        if (!prev || !ordered.some((item) => item.id === prev)) {
          return ordered[0].id;
        }
        return prev;
      });
    }
  }, [token, siteKey]);

  // ── Effects ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const querySite = searchParams?.get("site");
    const queryPage = searchParams?.get("page");
    if (querySite) setSiteKey(querySite);
    if (queryPage) setActiveSlug(queryPage);
  }, [searchParams]);

  useEffect(() => {
    setPageTitleDraft(activePage?.title || "");
    setPageSlugDraft(activePage?.slug || "");
    setSeoTitleDraft(safeString(activePage?.seo_json?.meta_title));
    setSeoDescriptionDraft(safeString(activePage?.seo_json?.meta_description));
    setSeoImageDraft(safeString(activePage?.seo_json?.meta_image));
    setSeoCanonicalDraft(safeString(activePage?.seo_json?.canonical_url));
    setSeoRobotsDraft(safeString(activePage?.seo_json?.robots_meta));
  }, [activePage]);

  useEffect(() => {
    loadPages(siteKey).catch(() => undefined);
  }, [siteKey, loadPages]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  const reloadTheme = useCallback(async () => {
    if (!siteKey || themeLoadingRef.current) return;
    themeLoadingRef.current = true;
    setThemeLoading(true);
    try {
      const theme = await apiFetch<CmsTheme>(`/cms/v2/public/sites/${siteKey}/theme`, { method: "GET", silent: true });
      if (!isMountedRef.current) return;
      if (theme?.tokens_json) {
        const vars: Record<string, string> = {};
        Object.entries(theme.tokens_json).forEach(([k, v]) => {
          vars[`--site-${k}`] = v;
        });
        setCanvasTokens({ ...CANVAS_PREVIEW_TOKENS, ...vars } as React.CSSProperties);
      }
      const themeName = theme?.name || "Por defecto";
      setCanvasThemeName(themeName);
      toast.success(`Tema "${themeName}" cargado`);
    } catch {
      toast.error("No se pudo recargar el tema");
    } finally {
      themeLoadingRef.current = false;
      if (isMountedRef.current) setThemeLoading(false);
    }
  }, [siteKey]);

  useEffect(() => {
    reloadTheme().catch(() => undefined);
  }, [reloadTheme]);

  useEffect(() => {
    loadSectionsAndVersions(activeSlug).catch(() => undefined);
  }, [activeSlug, loadSectionsAndVersions]);

  // ── Auto-save: persist local-only changes every 2 seconds ──────────────
  useEffect(() => {
    if (!canEdit || !token || !activeSlug) return;
    const interval = setInterval(async () => {
      if (!pendingLocalChangesRef.current || !autoSaveSectionRef.current) return;
      const section = autoSaveSectionRef.current;
      pendingLocalChangesRef.current = false;
      try {
        await patchCmsSection(siteKey, activeSlug, section.id, { props_json: section.props_json }, token);
        await loadSectionsAndVersions(activeSlug);
        notifyPreviewSync({ type: "section-saved", siteKey, slug: activeSlug, sectionId: section.id });
      } catch {
        // Auto-save failure is non-critical; next manual save will retry
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [canEdit, token, activeSlug, siteKey, loadSectionsAndVersions]);

  // ── Save on tab close ──────────────────────────────────────────────────
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (!pendingLocalChangesRef.current || !autoSaveSectionRef.current) return;
      const section = autoSaveSectionRef.current;
      const url = `/api/cms/v2/sites/${siteKey}/pages/${activeSlug}/sections/${section.id}`;
      const body = JSON.stringify({ props_json: section.props_json });
      navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [siteKey, activeSlug]);

  // ── SEO Analysis ─────────────────────────────────────────────────────────
  const seoAnalysis = useMemo(() => {
    const checks: SeoCheck[] = [];
    let score = 0;

    const titleLen = seoTitleDraft?.length || 0;
    if (titleLen >= 30 && titleLen <= 60) {
      checks.push({ id: "title_len", label: "Longitud del título SEO", passed: true, tip: `Correcto (${titleLen} caracteres).`, type: "success" });
      score += 15;
    } else if (titleLen > 0) {
      checks.push({ id: "title_len", label: "Longitud del título SEO", passed: false, tip: `Tiene ${titleLen} caracteres. Recomendado entre 30 y 60.`, type: "warning" });
      score += 5;
    } else {
      checks.push({ id: "title_len", label: "Título SEO vacío", passed: false, tip: "Por favor define un título SEO para indexación básica.", type: "error" });
    }

    const descLen = seoDescriptionDraft?.length || 0;
    if (descLen >= 110 && descLen <= 160) {
      checks.push({ id: "desc_len", label: "Longitud de meta descripción", passed: true, tip: `Correcto (${descLen} caracteres).`, type: "success" });
      score += 15;
    } else if (descLen > 0) {
      checks.push({ id: "desc_len", label: "Longitud de meta descripción", passed: false, tip: `Tiene ${descLen} caracteres. Recomendado entre 110 y 160.`, type: "warning" });
      score += 5;
    } else {
      checks.push({ id: "desc_len", label: "Meta descripción vacía", passed: false, tip: "La descripción es clave para convencer en los buscadores.", type: "error" });
    }

    if (seoKeyword.trim()) {
      const kw = seoKeyword.toLowerCase().trim();
      const titleMatch = seoTitleDraft?.toLowerCase().includes(kw) || false;
      if (titleMatch) {
        checks.push({ id: "kw_title", label: "Palabra clave en el título", passed: true, tip: "La palabra clave principal está dentro del título.", type: "success" });
        score += 15;
      } else {
        checks.push({ id: "kw_title", label: "Falta palabra clave en el título", passed: false, tip: `El título SEO no contiene "${seoKeyword}".`, type: "warning" });
      }

      const descMatch = seoDescriptionDraft?.toLowerCase().includes(kw) || false;
      if (descMatch) {
        checks.push({ id: "kw_desc", label: "Palabra clave en descripción", passed: true, tip: "La palabra clave se encuentra en la meta descripción.", type: "success" });
        score += 15;
      } else {
        checks.push({ id: "kw_desc", label: "Falta palabra clave en descripción", passed: false, tip: `La descripción no contiene "${seoKeyword}".`, type: "warning" });
      }

      let kwCount = 0;
      sections.forEach((s) => {
        const text = (safeString(s.props_json?.title) + " " + safeString(s.props_json?.body)).toLowerCase();
        kwCount += text.split(kw).length - 1;
      });
      if (kwCount >= 2) {
        checks.push({ id: "kw_content", label: "Densidad de palabra clave", passed: true, tip: `Encontrada ${kwCount} veces en las secciones. Densidad óptima.`, type: "success" });
        score += 15;
      } else if (kwCount === 1) {
        checks.push({ id: "kw_content", label: "Densidad de palabra clave baja", passed: false, tip: "Encontrada solo 1 vez. Añádela en subtítulos o descripciones.", type: "warning" });
        score += 5;
      } else {
        checks.push({ id: "kw_content", label: "Palabra clave ausente del contenido", passed: false, tip: `No se encuentra "${seoKeyword}" en ninguna sección.`, type: "error" });
      }
    } else {
      checks.push({ id: "kw_none", label: "Sin palabra clave definida", passed: false, tip: "Escribe una palabra clave arriba para analizar el SEO semántico.", type: "warning" });
    }

    let totalImages = 0;
    let missingAlt = 0;
    sections.forEach((s) => {
      if (s.type === "hero" || s.type === "image_text") {
        const url = safeString(s.props_json?.image_url);
        const alt = safeString(s.props_json?.image_alt);
        if (url) { totalImages++; if (!alt.trim()) missingAlt++; }
      } else if (s.type === "gallery") {
        const items = Array.isArray(s.props_json?.items) ? s.props_json.items : [];
        items.forEach((item: unknown) => {
          const itemObj = asObject(item);
          if (itemObj.url) { totalImages++; if (!safeString(itemObj.alt).trim()) missingAlt++; }
        });
      }
    });

    if (totalImages > 0) {
      if (missingAlt === 0) {
        checks.push({ id: "images_alt", label: "Textos alternativos en imágenes", passed: true, tip: "Todas las imágenes tienen etiqueta alt definida.", type: "success" });
        score += 15;
      } else {
        checks.push({ id: "images_alt", label: "Falta alt text en imágenes", passed: false, tip: `Hay ${missingAlt} de ${totalImages} imágenes sin texto descriptivo alt.`, type: "warning" });
        score += Math.max(0, 15 - missingAlt * 5);
      }
    } else {
      checks.push({ id: "images_alt", label: "Sin imágenes detectadas", passed: true, tip: "No se requiere alt text si no hay imágenes.", type: "success" });
      score += 15;
    }

    const hasHero = sections.some((s) => s.type === "hero" || s.type === "video_hero");
    if (hasHero) {
      checks.push({ id: "hierarchy", label: "Estructura de encabezados", passed: true, tip: "Se detectó sección Hero al inicio (encabezado principal H1).", type: "success" });
      score += 10;
    } else {
      checks.push({ id: "hierarchy", label: "Sin sección Hero principal", passed: false, tip: "Se recomienda un Hero al inicio para jerarquía H1.", type: "warning" });
    }

    return { score: Math.min(100, score), checks };
  }, [seoTitleDraft, seoDescriptionDraft, seoKeyword, sections]);

  const readabilityScore = useMemo(() => {
    let wordCount = 0;
    let sentenceCount = 0;
    sections.forEach((s) => {
      const text = safeString(s.props_json?.title) + " " + safeString(s.props_json?.body);
      wordCount += text.split(/\s+/).filter(Boolean).length;
      sentenceCount += text.split(/[.!?]+/).filter(Boolean).length;
    });
    if (wordCount === 0) return { score: 100, label: "Sin contenido" };
    const avgSentenceLength = wordCount / Math.max(1, sentenceCount);
    const score = Math.max(0, Math.min(100, Math.round(206.835 - 1.015 * avgSentenceLength - 84.6)));
    let label = "Fácil de leer";
    if (score < 50) label = "Complejo / Académico";
    else if (score < 75) label = "Estándar";
    else label = "Muy fácil de leer";
    return { score, label };
  }, [sections]);

  // ── Actions ──────────────────────────────────────────────────────────────
  const createPage = useCallback(async () => {
    if (!token || !newPageTitle.trim() || !canEdit) return;
    const slug = newPageTitle.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    if (!slug) return;
    const row = await createCmsPage(siteKey, { slug, title: newPageTitle }, token);
    setNewPageTitle("");
    await loadPages(siteKey);
    setActiveSlug(row.slug);
  }, [token, newPageTitle, canEdit, siteKey, loadPages]);

  const createPageFromTemplate = useCallback(async () => {
    if (!token || !newPageTitle.trim() || !canEdit) return;
    const slug = newPageTitle.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    if (!slug) return;
    const page = await createCmsPage(siteKey, { slug, title: newPageTitle }, token);
    const template = PAGE_TEMPLATES.find((item) => item.key === pageTemplateKey);
    if (template) {
      for (let i = 0; i < template.sections.length; i++) {
        await createCmsSection(siteKey, page.slug, {
          type: template.sections[i].type,
          sort_order: i,
          props_json: template.sections[i].props_json,
        }, token);
      }
    }
    setNewPageTitle("");
    await loadPages(siteKey);
    setActiveSlug(page.slug);
    await loadSectionsAndVersions(page.slug);
  }, [token, newPageTitle, canEdit, siteKey, pageTemplateKey, loadPages, loadSectionsAndVersions]);

  const addTemplateSection = useCallback(async (template: { type: string; props_json: Record<string, unknown> }) => {
    if (!token || !activeSlug || !canEdit) return;
    await createCmsSection(siteKey, activeSlug, {
      type: template.type,
      sort_order: sections.length,
      props_json: template.props_json,
    }, token);
    await loadSectionsAndVersions(activeSlug);
    notifyPreviewSync({ type: "section-created", siteKey, slug: activeSlug });
  }, [token, activeSlug, canEdit, siteKey, sections.length, loadSectionsAndVersions]);

  const addSection = useCallback(async (type?: string, props?: Record<string, unknown>) => {
    if (!token || !activeSlug || !canEdit) return;
    await createCmsSection(siteKey, activeSlug, {
      type: type || newSectionType,
      sort_order: sections.length,
      props_json: props || { title: "Nueva sección", body: "Edita este contenido", cta_label: "Ver más", cta_href: "/" },
    }, token);
    await loadSectionsAndVersions(activeSlug);
    notifyPreviewSync({ type: "section-created", siteKey, slug: activeSlug });
  }, [token, activeSlug, canEdit, siteKey, sections.length, loadSectionsAndVersions, newSectionType]);

  const saveSectionField = useCallback(async (field: string, value: string) => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    setSaving(true);
    const nextProps = { ...(activeSection.props_json || {}), [field]: value };
    try {
      await patchCmsSection(siteKey, activeSlug, activeSection.id, { props_json: nextProps }, token);
      await loadSectionsAndVersions(activeSlug);
      notifyPreviewSync({ type: "section-saved", siteKey, slug: activeSlug, sectionId: activeSection.id });
    } finally {
      setSaving(false);
    }
  }, [token, activeSection, activeSlug, canEdit, siteKey, loadSectionsAndVersions]);

  const saveSectionProps = useCallback(async (nextProps: Record<string, unknown>) => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    setSaving(true);
    try {
      await patchCmsSection(siteKey, activeSlug, activeSection.id, { props_json: nextProps }, token);
      await loadSectionsAndVersions(activeSlug);
      notifyPreviewSync({ type: "section-saved", siteKey, slug: activeSlug, sectionId: activeSection.id });
    } finally {
      setSaving(false);
    }
  }, [token, activeSection, activeSlug, canEdit, siteKey, loadSectionsAndVersions]);

  const upsertArrayItem = useCallback((
    key: "items",
    index: number,
    patch: Record<string, unknown>,
  ) => {
    if (!activeSection) return;
    const currentProps = asObject(activeSection.props_json);
    const currentItems = Array.isArray(currentProps[key]) ? [...(currentProps[key] as Array<Record<string, unknown>>)] : [];
    const currentItem = asObject(currentItems[index]);
    currentItems[index] = { ...currentItem, ...patch };
    const nextProps = { ...currentProps, [key]: currentItems };
    const updated = { ...activeSection, props_json: nextProps };
    setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: nextProps } : s));
    pendingLocalChangesRef.current = true;
    autoSaveSectionRef.current = updated;
    return nextProps;
  }, [activeSection]);

  const addArrayItem = useCallback((key: "items", template: Record<string, unknown>) => {
    if (!activeSection) return;
    const currentProps = asObject(activeSection.props_json);
    const currentItems = Array.isArray(currentProps[key]) ? [...(currentProps[key] as Array<Record<string, unknown>>)] : [];
    const nextItems = [...currentItems, template];
    const nextProps = { ...currentProps, [key]: nextItems };
    const updated = { ...activeSection, props_json: nextProps };
    setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: nextProps } : s));
    pendingLocalChangesRef.current = true;
    autoSaveSectionRef.current = updated;
    return nextProps;
  }, [activeSection]);

  const setSectionVisibility = useCallback(async (visible: boolean) => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    await patchCmsSection(siteKey, activeSlug, activeSection.id, { is_visible: visible }, token);
    await loadSectionsAndVersions(activeSlug);
    notifyPreviewSync({ type: "section-saved", siteKey, slug: activeSlug, sectionId: activeSection.id });
  }, [token, activeSection, activeSlug, canEdit, siteKey, loadSectionsAndVersions]);

  const updateSectionPropsLocal = useCallback((nextProps: Record<string, unknown>) => {
    if (!activeSection) return;
    setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: nextProps } : s));
  }, [activeSection]);

  const moveSection = useCallback(async (sectionId: string, direction: "up" | "down") => {
    if (!canEdit) return;
    const idx = sections.findIndex((s) => s.id === sectionId);
    if (idx < 0) return;
    const targetIdx = direction === "up" ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= sections.length) return;
    const next = [...sections];
    const temp = next[idx];
    next[idx] = next[targetIdx];
    next[targetIdx] = temp;
    const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
    setSections(next.map((item, index) => ({ ...item, sort_order: index })));
    if (!token || !activeSlug) return;
    await reorderCmsSections(siteKey, activeSlug, payload, token);
    await loadSectionsAndVersions(activeSlug);
    notifyPreviewSync({ type: "section-reordered", siteKey, slug: activeSlug });
  }, [canEdit, sections, token, activeSlug, siteKey, loadSectionsAndVersions]);

  const moveSectionToIndex = useCallback(async (sourceId: string, targetId: string) => {
    if (!canEdit) return;
    const sourceIndex = sections.findIndex((s) => s.id === sourceId);
    const targetIndex = sections.findIndex((s) => s.id === targetId);
    if (sourceIndex < 0 || targetIndex < 0 || sourceIndex === targetIndex) return;
    const next = [...sections];
    const [moved] = next.splice(sourceIndex, 1);
    next.splice(targetIndex, 0, moved);
    const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
    setSections(next.map((item, index) => ({ ...item, sort_order: index })));
    if (!token || !activeSlug) return;
    await reorderCmsSections(siteKey, activeSlug, payload, token);
    await loadSectionsAndVersions(activeSlug);
  }, [canEdit, sections, token, activeSlug, siteKey, loadSectionsAndVersions]);

  const duplicateSection = useCallback(async () => {
    if (!token || !activeSlug || !activeSection || !canEdit) return;
    await createCmsSection(siteKey, activeSlug, {
      type: activeSection.type,
      sort_order: sections.length,
      props_json: { ...(activeSection.props_json || {}) },
    }, token);
    await loadSectionsAndVersions(activeSlug);
  }, [token, activeSlug, activeSection, canEdit, siteKey, sections.length, loadSectionsAndVersions]);

  const toggleSectionArchive = useCallback(async () => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    const nextStatus = activeSection.status === "archived" ? "active" : "archived";
    await patchCmsSection(siteKey, activeSlug, activeSection.id, { status: nextStatus }, token);
    await loadSectionsAndVersions(activeSlug);
    notifyPreviewSync({ type: "section-deleted", siteKey, slug: activeSlug, sectionId: activeSection.id });
  }, [token, activeSection, activeSlug, canEdit, siteKey, loadSectionsAndVersions]);

  const runWorkflow = useCallback(async (action: "submit_review" | "approve" | "publish" | "archive" | "revert_draft") => {
    if (!token || !activeSlug) return;
    if (["approve", "publish", "archive"].includes(action) && !canPublish) return;
    if (!["approve", "publish", "archive"].includes(action) && !canEdit) return;
    await workflowCmsPage(siteKey, activeSlug, action, note || undefined, token);
    await loadPages(siteKey);
    await loadSectionsAndVersions(activeSlug);
    notifyPreviewSync({ type: "section-saved", siteKey, slug: activeSlug });
    setNote("");
  }, [token, activeSlug, canPublish, canEdit, siteKey, note, loadPages, loadSectionsAndVersions]);

  const rollback = useCallback(async (versionId: string) => {
    if (!token || !activeSlug || !canPublish) return;
    await rollbackCmsPageVersion(siteKey, activeSlug, versionId, token);
    await loadPages(siteKey);
    await loadSectionsAndVersions(activeSlug);
  }, [token, activeSlug, canPublish, siteKey, loadPages, loadSectionsAndVersions]);

  const savePageMetadata = useCallback(async () => {
    if (!token || !activePage || !canEdit) return;
    const slug = pageSlugDraft.toLowerCase().trim().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    if (!slug) return;
    const seo_json = {
      ...asObject(activePage.seo_json),
      meta_title: seoTitleDraft.trim(),
      meta_description: seoDescriptionDraft.trim(),
      meta_image: seoImageDraft.trim(),
      canonical_url: seoCanonicalDraft.trim() || undefined,
      robots_meta: seoRobotsDraft.trim() || undefined,
    };
    const updated = await patchCmsPage(siteKey, activePage.slug, { title: pageTitleDraft || activePage.title, slug, seo_json }, token);
    await loadPages(siteKey);
    setActiveSlug(updated.slug);
  }, [token, activePage, canEdit, siteKey, pageSlugDraft, pageTitleDraft, seoTitleDraft, seoDescriptionDraft, seoImageDraft, seoCanonicalDraft, seoRobotsDraft, loadPages]);

  const togglePageArchive = useCallback(async () => {
    if (!token || !activePage || !canEdit) return;
    const action = activePage.status === "archived" ? "revert_draft" : "archive";
    const notes = activePage.status === "archived" ? "Restaurada desde builder" : "Archivada desde builder";
    await workflowCmsPage(siteKey, activePage.slug, action, notes, token);
    await loadPages(siteKey);
    setActiveSlug(activePage.slug);
  }, [token, activePage, canEdit, siteKey, loadPages]);

  // ── AI ───────────────────────────────────────────────────────────────────
  const handleAiGenerate = useCallback(async () => {
    if (!aiPrompt.trim()) return;
    setAiGenerating(true);
    setAiOutput("");

    try {
      const toneLabels: Record<string, string> = {
        inspiration: "Inspiracional & Espiritual",
        formal: "Institucional & Respetuoso",
        warm: "Cercano & Familiar",
        dynamic: "Joven & Moderno",
      };
      const toneText = toneLabels[aiTone] || "Cercano & Familiar";
      const pageTitle = pageTitleDraft || activePage?.title || "Nuestra Iglesia";
      const kw = aiPrompt.trim();

      let fullPrompt = "";
      if (aiTemplate === "aida") {
        fullPrompt = `Genera contenido editorial usando el modelo AIDA (Atención-Interés-Deseo-Acción) con tono ${toneText} para la página "${pageTitle}" sobre: ${kw}. Incluye un título sugerido y un texto para botón CTA al final.`;
      } else if (aiTemplate === "pas") {
        fullPrompt = `Genera contenido editorial usando el modelo PAS (Problema-Agitación-Solución) con tono ${toneText} para la página "${pageTitle}" sobre: ${kw}. Incluye un título sugerido y un texto para botón CTA al final.`;
      } else if (aiTemplate === "headlines") {
        fullPrompt = `Genera 5 titulares impactantes en tono ${toneText} para una sección Hero de la página "${pageTitle}" relacionada con: ${kw}. Numera cada propuesta.`;
      } else if (aiTemplate === "improve") {
        fullPrompt = `Mejora el siguiente texto con un tono más profesional, persuasivo y en tono ${toneText}: "${kw}". Devuelve el texto mejorado directamente.`;
      }

      const result = await apiFetch<{ response: string }>("/system/ai/generate", {
        method: "POST",
        token,
        body: { prompt: fullPrompt, context: `Página: ${pageTitle}, Plantilla: ${aiTemplate}, Tono: ${toneText}` },
      });

      if (result?.response) {
        setAiOutput(result.response);
      } else {
        throw new Error("Respuesta vacía de la IA");
      }
    } catch (err) {
      toast.warning("Servicio de IA no disponible, usando contenido de ejemplo");
      // Fallback mock content preserved from original implementation
      const toneLabels: Record<string, string> = {
        inspiration: "Inspiracional & Espiritual",
        formal: "Institucional & Respetuoso",
        warm: "Cercano & Familiar",
        dynamic: "Joven & Moderno",
      };
      const toneText = toneLabels[aiTone] || "Cercano & Familiar";
      const pageTitle = pageTitleDraft || activePage?.title || "Nuestra Iglesia";
      const kw = aiPrompt.trim();
      let fallbackText = "";

      if (aiTemplate === "aida") {
        fallbackText = `### 🌟 MODELO AIDA (Tono: ${toneText}) 🌟\n\n` +
          `**[ATENCIÓN]**\n¿Buscas un lugar donde pertenecer y crecer de verdad? Descubre una comunidad apasionada en ${pageTitle} que te recibe con los brazos abiertos.\n\n` +
          `**[INTERÉS]**\nAquí no solo vienes a escuchar; vienes a conectar. Con grupos de crecimiento adaptados a tu etapa de vida, enseñanzas relevantes basadas en la Palabra de Dios y proyectos sociales en los que puedes activar tus dones, encontrarás un espacio para vivir tu fe de manera activa y real: "${kw}".\n\n` +
          `**[DESEO]**\nImagina caminar al lado de personas que comparten tus valores, te apoyan en tus dificultades y celebran tus victorias. Un lugar donde tu familia puede florecer y donde tu propósito de vida se alinea con el plan de Dios.\n\n` +
          `**[ACCIÓN]**\n¡Haz clic en el botón de abajo y acompáñanos en nuestra próxima reunión! Te estamos esperando.\n\n` +
          `**Título:** ¡Te damos la Bienvenida a Casa!\n**Botón:** Planificar Visita`;
      } else if (aiTemplate === "pas") {
        fallbackText = `### 🎯 MODELO PAS: Problema-Agitación-Solución (Tono: ${toneText}) 🎯\n\n` +
          `**[PROBLEMA]**\nEn un mundo hiperconectado pero cada vez más aislado, es fácil sentirse solo, abrumado o sin un rumbo espiritual claro.\n\n` +
          `**[AGITACIÓN]**\nEl ritmo acelerado del día a día nos aleja de lo que realmente importa. La falta de propósito y la ausencia de una comunidad de apoyo real terminan desgastando nuestra fe y nuestras relaciones familiares.\n\n` +
          `**[SOLUCIÓN]**\nEn ${pageTitle}, creemos que fuimos creados para la comunión. A través de nuestra iniciativa de "${kw}", te ofrecemos una ruta clara de integración, apoyo pastoral y grupos pequeños donde sanar, crecer y servir con gozo.\n\n` +
          `**Título:** Encuentra Conexión y Propósito Real\n**Mensaje Principal:** Una comunidad viva y comprometida para apoyarte en cada paso de tu vida espiritual.\n**Botón:** Conectar Ahora`;
      } else if (aiTemplate === "headlines") {
        fallbackText = `### ✍️ TITULARES OPTIMIZADOS PARA HERO (Tono: ${toneText}) ✍️\n\n` +
          `Propuestas premium basadas en tu búsqueda "${kw}":\n\n` +
          `1. **Propuesta de Impacto:** "Una casa de esperanza, una familia para crecer."\n` +
          `2. **Propuesta Espiritual:** "Conectando corazones con el propósito eterno de Dios."\n` +
          `3. **Propuesta Comunitaria:** "Tu lugar de encuentro en ${pageTitle}. ¡Bienvenidos a casa!"\n` +
          `4. **Propuesta Dinámica:** "Fe activa, relaciones reales, impacto real."\n` +
          `5. **Propuesta Corta & Fuerte:** "Crecer en fe, servir con amor."\n\n` +
          `*Selecciona cualquiera de estos titulares para copiarlo directamente en tu sección Hero.*`;
      } else if (aiTemplate === "improve") {
        fallbackText = `### ✨ TEXTO MEJORADO POR CCFGPT (Tono: ${toneText}) ✨\n\n` +
          `**Texto Original Analizado:**\n"${kw}"\n\n` +
          `**Versión Optimizada y Pulida:**\nQueremos invitarte a ser parte activa de lo que Dios está haciendo en nuestra casa. A través de esta iniciativa en ${pageTitle}, no solo encontrarás un canal para canalizar tu vocación de servicio, sino también una comunidad dispuesta a caminar contigo. Creemos firmemente que cada pequeño esfuerzo sumado produce una gran transformación.\n\n` +
          `*Este texto ha sido enriquecido para mejorar la retención de usuarios y el impacto emocional.*`;
      }
      setAiOutput(fallbackText);
    } finally {
      setAiGenerating(false);
    }
  }, [aiPrompt, aiTone, aiTemplate, pageTitleDraft, activePage?.title, token]);

  const handleAiImageGenerate = useCallback(() => {
    if (!aiImagePrompt.trim()) return;
    setAiImageGenerating(true);
    setAiImageResult("");
    const term = aiImagePrompt.toLowerCase().trim();
    const imageMap: Record<string, string[]> = {
      default: ["https://images.unsplash.com/photo-1438232992991-995b7058bbb3?auto=format&fit=crop&w=1200&q=80"],
      children: ["https://images.unsplash.com/photo-1472241139007-df4e38e764f2?auto=format&fit=crop&w=1200&q=80"],
      music: ["https://images.unsplash.com/photo-1465847899084-d164df4dedc6?auto=format&fit=crop&w=1200&q=80"],
      community: ["https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&w=1200&q=80"],
      bible: ["https://images.unsplash.com/photo-1504052434569-70ad58c63172?auto=format&fit=crop&w=1200&q=80"],
      youth: ["https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1200&q=80"],
      nature: ["https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1200&q=80"],
      prayer: ["https://images.unsplash.com/photo-1478040049072-2c2cf0a143db?auto=format&fit=crop&w=1200&q=80"],
      church: ["https://images.unsplash.com/photo-1438232992991-995b7058bbb3?auto=format&fit=crop&w=1200&q=80"],
      hands: ["https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?auto=format&fit=crop&w=1200&q=80"],
      family: ["https://images.unsplash.com/photo-1511895426328-dc8714191300?auto=format&fit=crop&w=1200&q=80"],
      hero: ["https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1200&q=80"],
    };
    const categories: Array<{ keys: string[]; name: string }> = [
      { keys: ["niño", "kids", "children", "infant", "niños", "infantes"], name: "children" },
      { keys: ["musica", "worship", "adoracion", "cantar", "music", "alabanza"], name: "music" },
      { keys: ["comunidad", "community", "grupo", "reunion", "people", "personas"], name: "community" },
      { keys: ["biblia", "bible", "estudio", "study", "lectura", "reading"], name: "bible" },
      { keys: ["jovenes", "youth", "jóvenes", "chicos", "adolescent"], name: "youth" },
      { keys: ["naturaleza", "nature", "creacion", "creation", "paisaje", "landscape"], name: "nature" },
      { keys: ["oracion", "prayer", "oración", "rezar", "pray"], name: "prayer" },
      { keys: ["iglesia", "church", "templo", "temple"], name: "church" },
      { keys: ["manos", "hands", "ayuda", "help", "voluntario", "volunteer", "servicio"], name: "hands" },
      { keys: ["familia", "family", "hogar", "home"], name: "family" },
      { keys: ["hero", "heroe", "héroe", "banner", "portada", "cover"], name: "hero" },
    ];
    const matched = categories.find((c) => c.keys.some((k) => term.includes(k)));
    const pool = matched ? imageMap[matched.name] : imageMap.default;
    const url = pool[Math.floor(Math.random() * pool.length)];
    setAiImageResult(url);
    setAiImageGenerating(false);
  }, [aiImagePrompt]);

  const handleInsertAiAsSection = useCallback(async () => {
    if (!aiOutput || !token || !activeSlug || !canEdit) return;
    setSaving(true);
    try {
      const lines = aiOutput.split("\n");
      const titleLine = lines.find((l) => l.startsWith("**Título:**") || l.startsWith("###")) || "";
      const cleanTitle = titleLine.replace(/\*\*Título:\*\*|###|✨|📋|❤️|🤝/g, "").trim() || "Sección Generada con IA";
      const bodyLines = lines.filter((l) => !l.startsWith("###") && !l.startsWith("**Título:**") && !l.startsWith("✨") && !l.startsWith("📋") && !l.startsWith("❤️") && !l.startsWith("🤝"));
      const cleanBody = bodyLines.join("\n").replace(/\*\*Mensaje:\*\*|\*\*Mensaje Principal:\*\*/g, "").trim();
      await createCmsSection(siteKey, activeSlug, {
        type: "rich_text",
        sort_order: sections.length,
        props_json: { title: cleanTitle, body: cleanBody, cta_label: "Saber más", cta_href: "/" },
      }, token);
      await loadSectionsAndVersions(activeSlug);
      setActiveRightTab("config");
    } finally {
      setSaving(false);
    }
  }, [aiOutput, token, activeSlug, canEdit, siteKey, sections.length, loadSectionsAndVersions]);

  const handleReplaceActiveSectionWithAi = useCallback(async () => {
    if (!aiOutput || !activeSection || !token || !activeSlug || !canEdit) return;
    setSaving(true);
    try {
      const lines = aiOutput.split("\n");
      const titleLine = lines.find((l) => l.startsWith("**Título:**") || l.startsWith("###")) || "";
      const cleanTitle = titleLine.replace(/\*\*Título:\*\*|###|✨|📋|❤️|🤝/g, "").trim() || (activeSection.props_json?.title as string) || "Sección Actualizada";
      const bodyLines = lines.filter((l) => !l.startsWith("###") && !l.startsWith("**Título:**") && !l.startsWith("✨") && !l.startsWith("📋") && !l.startsWith("❤️") && !l.startsWith("🤝"));
      const cleanBody = bodyLines.join("\n").replace(/\*\*Mensaje:\*\*|\*\*Mensaje Principal:\*\*/g, "").trim();
      const nextProps = { ...(activeSection.props_json || {}), title: cleanTitle, body: cleanBody };
      await patchCmsSection(siteKey, activeSlug, activeSection.id, { props_json: nextProps }, token);
      await loadSectionsAndVersions(activeSlug);
    } finally {
      setSaving(false);
    }
  }, [aiOutput, activeSection, token, activeSlug, canEdit, siteKey, loadSectionsAndVersions]);

  // ── Return ───────────────────────────────────────────────────────────────
  return {
    // State
    siteKey, setSiteKey,
    sites,
    pages,
    activeSlug, setActiveSlug,
    sections, setSections,
    versions,
    publishLogs,
    newPageTitle, setNewPageTitle,
    newSectionType, setNewSectionType,
    pageTemplateKey, setPageTemplateKey,
    activeSectionId, setActiveSectionId,
    note, setNote,
    saving,
    draggedSectionId, setDraggedSectionId,
    previewDevice, setPreviewDevice,
    canvasMode, setCanvasMode,
    pageTitleDraft, setPageTitleDraft,
    pageSlugDraft, setPageSlugDraft,
    seoTitleDraft, setSeoTitleDraft,
    seoDescriptionDraft, setSeoDescriptionDraft,
    seoImageDraft, setSeoImageDraft,
    seoCanonicalDraft, setSeoCanonicalDraft,
    seoRobotsDraft, setSeoRobotsDraft,
    mediaPickerOpen, setMediaPickerOpen,
    mediaPickerTarget, setMediaPickerTarget,
    activeRightTab, setActiveRightTab,
    seoKeyword, setSeoKeyword,
    aiPrompt, setAiPrompt,
    aiGenerating,
    aiOutput,
    showHeatmap, setShowHeatmap,
    timeframe, setTimeframe,
    heatmapType, setHeatmapType,
    abTestingActive, setAbTestingActive,
    abTrafficSplit, setAbTrafficSplit,
    serpPreviewDevice, setSerpPreviewDevice,
    aiTone, setAiTone,
    aiTemplate, setAiTemplate,
    aiImagePrompt, setAiImagePrompt,
    aiImageResult, setAiImageResult,
    aiImageGenerating,
    canvasTokens,
    canvasThemeName,
    themeLoading,

    // Derived
    activePage,
    activeSection,
    activeSite,
    canEdit,
    canPublish,
    seoAnalysis,
    readabilityScore,

    // Actions
    loadPages,
    loadSectionsAndVersions,
    createPage,
    createPageFromTemplate,
    addTemplateSection,
    addSection,
    saveSectionField,
    saveSectionProps,
    updateSectionPropsLocal,
    moveSection,
    moveSectionToIndex,
    duplicateSection,
    toggleSectionArchive,
    setSectionVisibility,
    runWorkflow,
    rollback,
    savePageMetadata,
    togglePageArchive,
    handleAiGenerate,
    handleAiImageGenerate,
    handleInsertAiAsSection,
    handleReplaceActiveSectionWithAi,
    upsertArrayItem,
    addArrayItem,
    reloadTheme,

    // Direct lib access (for advanced use in child components)
    token,
  };
}

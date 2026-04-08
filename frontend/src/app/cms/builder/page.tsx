"use client";

import React, { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Copy, Eye, EyeOff, ExternalLink, LayoutPanelTop, Monitor, Plus, Save, Send, Smartphone, Trash2, Upload, Undo2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
  createCmsPage,
  createCmsSection,
  deleteCmsPage,
  deleteCmsSection,
  listCmsPageVersions,
  listCmsPages,
  listCmsSections,
  listCmsSites,
  patchCmsPage,
  patchCmsSection,
  reorderCmsSections,
  rollbackCmsPageVersion,
  workflowCmsPage,
} from "@/lib/cms/v2";
import { CmsPage, CmsPageVersion, CmsSection } from "@/types/cms-v2";
import { useSearchParams } from "next/navigation";
import { canEditCms, canPublishCms } from "@/lib/cms/permissions";

const SECTION_TYPES = ["hero", "rich_text", "cards", "cta_banner", "gallery", "faq", "embed"];

const PAGE_TEMPLATES: Array<{ key: string; label: string; sections: Array<{ type: string; props_json: Record<string, unknown> }> }> = [
  {
    key: "landing",
    label: "Landing completa",
    sections: [
      {
        type: "hero",
        props_json: {
          title: "Bienvenido a nuestra comunidad",
          body: "Una casa para crecer en fe y servir con propósito.",
          cta_label: "Conocer más",
          cta_href: "/faro/nosotros",
        },
      },
      {
        type: "cards",
        props_json: {
          title: "Nuestra ruta",
          body: "Conecta, crece y sirve.",
          items: [
            { title: "Conecta", body: "Únete a una comunidad cercana." },
            { title: "Crece", body: "Profundiza en la Palabra." },
            { title: "Sirve", body: "Impacta tu entorno." },
          ],
        },
      },
      {
        type: "faq",
        props_json: {
          title: "Preguntas frecuentes",
          items: [
            { q: "¿Cómo llegar?", a: "Revisa nuestra sección de sedes." },
            { q: "¿Cómo empezar?", a: "Visítanos y te acompañamos en tu proceso." },
          ],
        },
      },
      {
        type: "cta_banner",
        props_json: {
          title: "Da tu siguiente paso",
          body: "Queremos caminar contigo.",
          cta_label: "Planificar visita",
          cta_href: "/faro/conocer-a-jesus",
        },
      },
    ],
  },
  {
    key: "simple",
    label: "Página simple",
    sections: [
      { type: "rich_text", props_json: { title: "Título", body: "Contenido principal" } },
      { type: "cta_banner", props_json: { title: "Llamado a la acción", body: "Invita al usuario a avanzar", cta_label: "Continuar", cta_href: "/" } },
    ],
  },
];

const SECTION_TEMPLATES: Array<{ label: string; type: string; props_json: Record<string, unknown> }> = [
  {
    label: "Hero principal",
    type: "hero",
    props_json: {
      title: "Una comunidad que transforma vidas",
      body: "Conecta con Jesús, crece en discipulado y sirve con propósito.",
      cta_label: "Planifica tu visita",
      cta_href: "/faro/conocer-a-jesus",
    },
  },
  {
    label: "Bloque de tarjetas",
    type: "cards",
    props_json: {
      title: "Nuestra ruta de crecimiento",
      body: "Explora los pasos clave de formación y servicio.",
      items: [
        { title: "Conecta", body: "Conoce la casa y encuentra comunidad." },
        { title: "Crece", body: "Fortalece tu fe con formación continua." },
        { title: "Sirve", body: "Activa tus dones para impactar la ciudad." },
      ],
    },
  },
  {
    label: "Banner CTA",
    type: "cta_banner",
    props_json: {
      title: "¿Listo para dar el siguiente paso?",
      body: "Conoce nuestros próximos eventos y grupos de conexión.",
      cta_label: "Ver eventos",
      cta_href: "/faro/eventos",
    },
  },
  {
    label: "FAQ rápido",
    type: "faq",
    props_json: {
      title: "Preguntas frecuentes",
      body: "Resuelve dudas comunes antes de visitarnos.",
      items: [
        { q: "¿Dónde están ubicados?", a: "Puedes ver todas nuestras sedes en la sección de Sedes." },
        { q: "¿Cómo puedo empezar?", a: "Comienza visitándonos o escribiéndonos desde Conocer a Jesús." },
      ],
    },
  },
];

function safeString(value: unknown) {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function asObject(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as Record<string, unknown>;
  return {};
}

function SectionPreview({ section }: { section: CmsSection }) {
  const title = safeString(section.props_json?.title);
  const body = safeString(section.props_json?.body);
  const imageUrl = safeString(section.props_json?.image_url);
  if (section.type === "hero") {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 dark:border-white/20 p-4">
        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Hero</p>
        <h3 className="mt-2 text-xl font-black text-slate-900 dark:text-white">{title || "Título hero"}</h3>
        <p className="mt-2 text-sm text-slate-500">{body || "Subtítulo hero"}</p>
      </div>
    );
  }
  if (section.type === "cards") {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 dark:border-white/20 p-4">
        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Cards</p>
        <p className="mt-2 text-sm font-bold text-slate-800 dark:text-slate-200">{title || "Bloque de tarjetas"}</p>
      </div>
    );
  }
  if (section.type === "gallery") {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 dark:border-white/20 p-4">
        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Gallery</p>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{imageUrl ? `Imagen principal: ${imageUrl}` : "Define image_url en props"}</p>
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 dark:border-white/20 p-4">
      <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{section.type}</p>
      <h4 className="mt-2 text-base font-black text-slate-800 dark:text-slate-100">{title || "Título"}</h4>
      <p className="mt-1 text-sm text-slate-500 line-clamp-3">{body || "Contenido de sección"}</p>
    </div>
  );
}

export default function CmsBuilderPage() {
  const { token, user } = useAuth();
  const searchParams = useSearchParams();
  const [siteKey, setSiteKey] = useState("faro");
  const [sites, setSites] = useState<Array<{ site_key: string; name: string; base_path: string }>>([]);
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [activeSlug, setActiveSlug] = useState("");
  const [sections, setSections] = useState<CmsSection[]>([]);
  const [versions, setVersions] = useState<CmsPageVersion[]>([]);
  const [newPageTitle, setNewPageTitle] = useState("");
  const [newSectionType, setNewSectionType] = useState("rich_text");
  const [pageTemplateKey, setPageTemplateKey] = useState("simple");
  const [activeSectionId, setActiveSectionId] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [draggedSectionId, setDraggedSectionId] = useState<number | null>(null);
  const [previewDevice, setPreviewDevice] = useState<"desktop" | "mobile">("desktop");
  const [rawPropsDraft, setRawPropsDraft] = useState("");
  const [rawPropsError, setRawPropsError] = useState<string | null>(null);
  const [pageTitleDraft, setPageTitleDraft] = useState("");
  const [pageSlugDraft, setPageSlugDraft] = useState("");

  useEffect(() => {
    const querySite = searchParams?.get("site");
    const queryPage = searchParams?.get("page");
    if (querySite) setSiteKey(querySite);
    if (queryPage) setActiveSlug(queryPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activePage = useMemo(() => pages.find((p) => p.slug === activeSlug) ?? null, [pages, activeSlug]);
  const activeSection = useMemo(() => sections.find((s) => s.id === activeSectionId) ?? null, [sections, activeSectionId]);
  const activeSite = useMemo(() => sites.find((site) => site.site_key === siteKey) ?? null, [sites, siteKey]);
  const canEdit = canEditCms(user?.role);
  const canPublish = canPublishCms(user?.role);

  useEffect(() => {
    if (!activeSection) {
      setRawPropsDraft("");
      setRawPropsError(null);
      return;
    }
    setRawPropsDraft(JSON.stringify(activeSection.props_json ?? {}, null, 2));
    setRawPropsError(null);
  }, [activeSection]);

  useEffect(() => {
    setPageTitleDraft(activePage?.title || "");
    setPageSlugDraft(activePage?.slug || "");
  }, [activePage]);

  const loadPages = async (targetSite: string) => {
    if (!token) return;
    const [nextSites, nextPages] = await Promise.all([listCmsSites(token), listCmsPages(targetSite, token)]);
    setSites((nextSites || []).map((site) => ({ site_key: site.site_key, name: site.name, base_path: site.base_path })));
    setPages(nextPages || []);
    if ((nextPages || []).length > 0 && !activeSlug) {
      setActiveSlug(nextPages[0].slug);
    }
  };

  const loadSectionsAndVersions = async (slug: string) => {
    if (!token || !slug) return;
    const [nextSections, nextVersions] = await Promise.all([
      listCmsSections(siteKey, slug, token),
      listCmsPageVersions(siteKey, slug, token),
    ]);
    const ordered = (nextSections || []).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    setSections(ordered);
    setVersions(nextVersions || []);
    if (ordered.length > 0 && (!activeSectionId || !ordered.some((item) => item.id === activeSectionId))) {
      setActiveSectionId(ordered[0].id);
    }
  };

  useEffect(() => {
    loadPages(siteKey).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteKey, token]);

  useEffect(() => {
    loadSectionsAndVersions(activeSlug).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSlug, token]);

  const createPage = async () => {
    if (!token || !newPageTitle.trim() || !canEdit) return;
    const slug = newPageTitle.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    if (!slug) return;
    const row = await createCmsPage(siteKey, { slug, title: newPageTitle }, token);
    setNewPageTitle("");
    await loadPages(siteKey);
    setActiveSlug(row.slug);
  };

  const createPageFromTemplate = async () => {
    if (!token || !newPageTitle.trim() || !canEdit) return;
    const slug = newPageTitle.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    if (!slug) return;
    const page = await createCmsPage(siteKey, { slug, title: newPageTitle }, token);
    const template = PAGE_TEMPLATES.find((item) => item.key === pageTemplateKey);
    if (template) {
      for (let i = 0; i < template.sections.length; i += 1) {
        const section = template.sections[i];
        await createCmsSection(
          siteKey,
          page.slug,
          {
            type: section.type,
            sort_order: i,
            props_json: section.props_json,
          },
          token,
        );
      }
    }
    setNewPageTitle("");
    await loadPages(siteKey);
    setActiveSlug(page.slug);
    await loadSectionsAndVersions(page.slug);
  };

  const addSection = async () => {
    if (!token || !activeSlug || !canEdit) return;
    await createCmsSection(
      siteKey,
      activeSlug,
      {
        type: newSectionType,
        sort_order: sections.length,
        props_json: { title: "Nueva sección", body: "Edita este contenido", cta_label: "Ver más", cta_href: "/" },
      },
      token,
    );
    await loadSectionsAndVersions(activeSlug);
  };

  const addTemplateSection = async (template: { type: string; props_json: Record<string, unknown> }) => {
    if (!token || !activeSlug || !canEdit) return;
    await createCmsSection(
      siteKey,
      activeSlug,
      {
        type: template.type,
        sort_order: sections.length,
        props_json: template.props_json,
      },
      token,
    );
    await loadSectionsAndVersions(activeSlug);
  };

  const saveSectionField = async (field: string, value: string) => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    setSaving(true);
    const nextProps = { ...(activeSection.props_json || {}), [field]: value };
    try {
      await patchCmsSection(siteKey, activeSlug, activeSection.id, { props_json: nextProps }, token);
      await loadSectionsAndVersions(activeSlug);
    } finally {
      setSaving(false);
    }
  };

  const saveSectionProps = async (nextProps: Record<string, unknown>) => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    setSaving(true);
    try {
      await patchCmsSection(siteKey, activeSlug, activeSection.id, { props_json: nextProps }, token);
      await loadSectionsAndVersions(activeSlug);
    } finally {
      setSaving(false);
    }
  };

  const updateSectionPropsLocal = (nextProps: Record<string, unknown>) => {
    if (!activeSection) return;
    setSections((prev) => prev.map((section) => section.id === activeSection.id ? { ...section, props_json: nextProps } : section));
  };

  const upsertArrayItem = (
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
    updateSectionPropsLocal(nextProps);
    return nextProps;
  };

  const addArrayItem = (key: "items", template: Record<string, unknown>) => {
    if (!activeSection) return;
    const currentProps = asObject(activeSection.props_json);
    const currentItems = Array.isArray(currentProps[key]) ? [...(currentProps[key] as Array<Record<string, unknown>>)] : [];
    const nextItems = [...currentItems, template];
    const nextProps = { ...currentProps, [key]: nextItems };
    updateSectionPropsLocal(nextProps);
    return nextProps;
  };

  const removeArrayItem = (key: "items", index: number) => {
    if (!activeSection) return;
    const currentProps = asObject(activeSection.props_json);
    const currentItems = Array.isArray(currentProps[key]) ? [...(currentProps[key] as Array<Record<string, unknown>>)] : [];
    const nextItems = currentItems.filter((_, i) => i !== index);
    const nextProps = { ...currentProps, [key]: nextItems };
    updateSectionPropsLocal(nextProps);
    return nextProps;
  };

  const setSectionVisibility = async (visible: boolean) => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    await patchCmsSection(siteKey, activeSlug, activeSection.id, { is_visible: visible }, token);
    await loadSectionsAndVersions(activeSlug);
  };

  const removeSection = async () => {
    if (!token || !activeSection || !activeSlug || !canEdit) return;
    await deleteCmsSection(siteKey, activeSlug, activeSection.id, token);
    setActiveSectionId(null);
    await loadSectionsAndVersions(activeSlug);
  };

  const duplicateSection = async () => {
    if (!token || !activeSlug || !activeSection || !canEdit) return;
    await createCmsSection(
      siteKey,
      activeSlug,
      {
        type: activeSection.type,
        sort_order: sections.length,
        props_json: { ...(activeSection.props_json || {}) },
      },
      token,
    );
    await loadSectionsAndVersions(activeSlug);
  };

  const moveSection = async (sectionId: number, direction: "up" | "down") => {
    if (!canEdit) return;
    const idx = sections.findIndex((s) => s.id === sectionId);
    if (idx < 0) return;
    const targetIdx = direction === "up" ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= sections.length) return;
    const next = [...sections];
    const current = next[idx];
    next[idx] = next[targetIdx];
    next[targetIdx] = current;
    const payload = next.map((item, index) => ({ id: item.id, sort_order: index }));
    setSections(next.map((item, index) => ({ ...item, sort_order: index })));
    if (!token || !activeSlug) return;
    await reorderCmsSections(siteKey, activeSlug, payload, token);
    await loadSectionsAndVersions(activeSlug);
  };

  const moveSectionToIndex = async (sourceId: number, targetId: number) => {
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
  };

  const runWorkflow = async (action: "submit_review" | "approve" | "publish" | "archive" | "revert_draft") => {
    if (!token || !activeSlug) return;
    if (["approve", "publish", "archive"].includes(action) && !canPublish) return;
    if (!["approve", "publish", "archive"].includes(action) && !canEdit) return;
    await workflowCmsPage(siteKey, activeSlug, action, note || undefined, token);
    await loadPages(siteKey);
    await loadSectionsAndVersions(activeSlug);
    setNote("");
  };

  const rollback = async (versionId: number) => {
    if (!token || !activeSlug || !canPublish) return;
    await rollbackCmsPageVersion(siteKey, activeSlug, versionId, token);
    await loadPages(siteKey);
    await loadSectionsAndVersions(activeSlug);
  };

  const savePageMetadata = async () => {
    if (!token || !activePage || !canEdit) return;
    const slug = pageSlugDraft.toLowerCase().trim().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    if (!slug) return;
    const updated = await patchCmsPage(
      siteKey,
      activePage.slug,
      { title: pageTitleDraft || activePage.title, slug },
      token,
    );
    await loadPages(siteKey);
    setActiveSlug(updated.slug);
  };

  const removePage = async () => {
    if (!token || !activePage || !canEdit) return;
    await deleteCmsPage(siteKey, activePage.slug, token);
    const remaining = pages.filter((page) => page.id !== activePage.id);
    await loadPages(siteKey);
    setActiveSlug(remaining[0]?.slug || "");
  };

  return (
    <div className="space-y-6 p-6">
      <div className="rounded-3xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-6 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">CMS V2 Builder</p>
          <h1 className="mt-2 text-2xl font-black">Constructor visual multisitio</h1>
        </div>
        <div className="rounded-xl bg-primary/10 px-3 py-2 text-primary text-xs font-black uppercase tracking-widest inline-flex items-center gap-2">
          <LayoutPanelTop size={14} /> Beta
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <aside className="lg:col-span-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-3">
          <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Sitio</label>
          <select value={siteKey} onChange={(e) => setSiteKey(e.target.value)} className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm">
            {sites.length === 0 && <option value="faro">faro</option>}
            {sites.map((site) => (
              <option key={site.site_key} value={site.site_key}>{site.name} ({site.site_key})</option>
            ))}
          </select>

          <div className="rounded-xl border border-slate-200 dark:border-white/10 p-3 space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Nueva página</p>
            <input value={newPageTitle} onChange={(e) => setNewPageTitle(e.target.value)} placeholder="Ej: Página de bienvenida" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm" disabled={!canEdit} />
            <button onClick={createPage} disabled={!canEdit} className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-[10px] font-black uppercase tracking-widest text-white disabled:opacity-50"><Plus size={12} /> Crear vacía</button>
            <select value={pageTemplateKey} onChange={(e) => setPageTemplateKey(e.target.value)} className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs">
              {PAGE_TEMPLATES.map((template) => (
                <option key={template.key} value={template.key}>{template.label}</option>
              ))}
            </select>
            <button onClick={createPageFromTemplate} disabled={!canEdit} className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest disabled:opacity-50">
              <Plus size={12} /> Crear con plantilla
            </button>
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Páginas</p>
            {pages.map((page) => (
              <button key={page.id} onClick={() => setActiveSlug(page.slug)} className={`w-full text-left rounded-lg border px-3 py-2 text-sm ${activeSlug === page.slug ? "border-primary/40 bg-primary/5" : "border-slate-200 dark:border-white/10"}`}>
                <p className="font-bold">{page.title}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-400">/{page.slug} · {page.status}</p>
              </button>
            ))}
          </div>

          <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-white/10">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Plantillas rápidas</p>
            {SECTION_TEMPLATES.map((template) => (
              <button
                key={template.label}
                onClick={() => addTemplateSection(template)}
                disabled={!activeSlug || !canEdit}
                className="w-full text-left rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-xs font-bold hover:border-primary/40 transition-all disabled:opacity-50"
              >
                {template.label}
              </button>
            ))}
          </div>
        </aside>

        <section className="lg:col-span-6 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-lg font-black">Canvas · {activeSlug ? `/${activeSlug}` : "Selecciona página"}</h2>
            <div className="flex items-center gap-2">
              <div className="inline-flex rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden">
                <button
                  onClick={() => setPreviewDevice("desktop")}
                  className={`px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center gap-1 ${previewDevice === "desktop" ? "bg-primary text-white" : "bg-transparent"}`}
                >
                  <Monitor size={11} /> Desktop
                </button>
                <button
                  onClick={() => setPreviewDevice("mobile")}
                  className={`px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center gap-1 ${previewDevice === "mobile" ? "bg-primary text-white" : "bg-transparent"}`}
                >
                  <Smartphone size={11} /> Mobile
                </button>
              </div>
              <select value={newSectionType} onChange={(e) => setNewSectionType(e.target.value)} className="rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm">
                {SECTION_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
              <button onClick={addSection} disabled={!activeSlug || !canEdit} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest disabled:opacity-50">
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
                className={`rounded-xl border p-3 cursor-grab active:cursor-grabbing ${section.id === activeSectionId ? "border-primary/40 bg-primary/5" : "border-slate-200 dark:border-white/10"}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <button onClick={() => setActiveSectionId(section.id)} className="text-left">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{section.type}</p>
                    <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{safeString(section.props_json?.title) || "Sección"}</p>
                  </button>
                  <div className="flex items-center gap-1">
                    <button onClick={() => moveSection(section.id, "up")} disabled={!canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 p-1.5 disabled:opacity-50"><ArrowUp size={12} /></button>
                    <button onClick={() => moveSection(section.id, "down")} disabled={!canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 p-1.5 disabled:opacity-50"><ArrowDown size={12} /></button>
                  </div>
                </div>
                <div className="mt-3">
                  <SectionPreview section={section} />
                </div>
              </div>
            ))}
            {sections.length === 0 && <p className="text-sm text-slate-500">No hay secciones en esta página.</p>}
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
                className="rounded-xl border border-dashed border-slate-300 dark:border-white/20 p-3 text-center text-[10px] font-black uppercase tracking-widest text-slate-400"
              >
                Soltar aquí para mover al final
              </div>
            )}
          </div>
        </section>

        <aside className="lg:col-span-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-4">
          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Estado página</p>
            <p className="text-sm font-bold">{activePage?.title || "Sin página"}</p>
            <p className="text-[10px] uppercase tracking-widest text-slate-400">{activePage?.status || "-"}</p>
            <input
              value={pageTitleDraft}
              onChange={(e) => setPageTitleDraft(e.target.value)}
              placeholder="Título de página"
              className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
            />
            <input
              value={pageSlugDraft}
              onChange={(e) => setPageSlugDraft(e.target.value)}
              placeholder="slug-de-pagina"
              className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs"
            />
            <button
              onClick={savePageMetadata}
              disabled={!activePage || !canEdit}
              className="w-full rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
            >
              Guardar título/slug
            </button>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} disabled={!canEdit && !canPublish} placeholder="Nota para workflow..." className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-xs disabled:opacity-60" />
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => runWorkflow("submit_review")} disabled={!activeSlug || !canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"><Send size={11} /> Review</button>
              <button onClick={() => runWorkflow("approve")} disabled={!activeSlug || !canPublish} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"><Save size={11} /> Aprobar</button>
              <button onClick={() => runWorkflow("publish")} disabled={!activeSlug || !canPublish} className="rounded-lg bg-primary text-white px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"><Upload size={11} /> Publicar</button>
              <button onClick={() => runWorkflow("revert_draft")} disabled={!activeSlug || !canEdit} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"><Undo2 size={11} /> Draft</button>
              <button onClick={() => runWorkflow("archive")} disabled={!activeSlug || !canPublish} className="col-span-2 rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50">Archivar</button>
            </div>
            <button
              onClick={() => {
                if (!activeSlug) return;
                const base = activeSite?.base_path || `/${siteKey}`;
                const normalized = base.endsWith("/") ? base.slice(0, -1) : base;
                window.open(`${normalized}/${activeSlug}`, "_blank");
              }}
              disabled={!activeSlug}
              className="w-full rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1 disabled:opacity-50"
            >
              <ExternalLink size={11} /> Ver página pública
            </button>
              <button
                onClick={removePage}
                disabled={!activePage || !canEdit}
                className="w-full rounded-lg border border-rose-200 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest text-rose-600 disabled:opacity-50"
              >
                Eliminar página
              </button>
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Inspector sección</p>
            {!activeSection ? (
              <p className="text-xs text-slate-500">Selecciona una sección del canvas.</p>
            ) : (
              <fieldset disabled={!canEdit} className="space-y-0 disabled:opacity-60">
                <p className="text-xs font-bold uppercase tracking-widest text-slate-500">{activeSection.type}</p>
                <input
                  value={safeString(activeSection.props_json?.title)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("title", e.target.value)}
                  placeholder="Título"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
                <textarea
                  value={safeString(activeSection.props_json?.body)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), body: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("body", e.target.value)}
                  placeholder="Contenido"
                  className="w-full min-h-[90px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
                <input
                  value={safeString(activeSection.props_json?.cta_label)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), cta_label: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("cta_label", e.target.value)}
                  placeholder="Texto CTA"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
                <input
                  value={safeString(activeSection.props_json?.cta_href)}
                  onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), cta_href: e.target.value } } : s))}
                  onBlur={(e) => saveSectionField("cta_href", e.target.value)}
                  placeholder="URL CTA"
                  className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />

                {activeSection.type === "gallery" && (
                  <input
                    value={safeString(activeSection.props_json?.image_url)}
                    onChange={(e) => {
                      const nextProps = { ...asObject(activeSection.props_json), image_url: e.target.value };
                      updateSectionPropsLocal(nextProps);
                    }}
                    onBlur={(e) => saveSectionField("image_url", e.target.value)}
                    placeholder="URL de imagen"
                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                  />
                )}

                {activeSection.type === "embed" && (
                  <input
                    value={safeString(activeSection.props_json?.embed_url)}
                    onChange={(e) => {
                      const nextProps = { ...asObject(activeSection.props_json), embed_url: e.target.value };
                      updateSectionPropsLocal(nextProps);
                    }}
                    onBlur={(e) => saveSectionField("embed_url", e.target.value)}
                    placeholder="URL embed (YouTube, Vimeo, etc.)"
                    className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                  />
                )}

                {activeSection.type === "cards" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Items de tarjetas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => (
                      <div key={`card-${index}`} className="space-y-2 rounded-lg border border-slate-200/70 dark:border-white/10 p-2">
                        <input
                          value={safeString(asObject(item).title)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { title: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { title: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Título tarjeta"
                          className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <textarea
                          value={safeString(asObject(item).body)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { body: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { body: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Descripción tarjeta"
                          className="w-full min-h-[64px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <button
                          onClick={() => {
                            const nextProps = removeArrayItem("items", index);
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          className="rounded-md border border-rose-200 px-2 py-1 text-[10px] font-black uppercase tracking-widest text-rose-600"
                        >
                          Eliminar item
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => {
                        const nextProps = addArrayItem("items", { title: "Nueva tarjeta", body: "Descripción" });
                        if (nextProps) saveSectionProps(nextProps);
                      }}
                      className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-black uppercase tracking-widest"
                    >
                      + Añadir tarjeta
                    </button>
                  </div>
                )}

                {activeSection.type === "faq" && (
                  <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Preguntas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => (
                      <div key={`faq-${index}`} className="space-y-2 rounded-lg border border-slate-200/70 dark:border-white/10 p-2">
                        <input
                          value={safeString(asObject(item).q)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { q: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { q: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Pregunta"
                          className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <textarea
                          value={safeString(asObject(item).a)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { a: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { a: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Respuesta"
                          className="w-full min-h-[64px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <button
                          onClick={() => {
                            const nextProps = removeArrayItem("items", index);
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          className="rounded-md border border-rose-200 px-2 py-1 text-[10px] font-black uppercase tracking-widest text-rose-600"
                        >
                          Eliminar pregunta
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => {
                        const nextProps = addArrayItem("items", { q: "Nueva pregunta", a: "Respuesta" });
                        if (nextProps) saveSectionProps(nextProps);
                      }}
                      className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-black uppercase tracking-widest"
                    >
                      + Añadir pregunta
                    </button>
                  </div>
                )}

                <div className="space-y-2 rounded-lg border border-slate-200 dark:border-white/10 p-3">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">JSON avanzado</p>
                  <textarea
                    value={rawPropsDraft}
                    onChange={(e) => {
                      setRawPropsDraft(e.target.value);
                      setRawPropsError(null);
                    }}
                    className="w-full min-h-[120px] rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-2 py-1.5 text-xs font-mono"
                  />
                  <button
                    onClick={() => {
                      try {
                        const parsed = JSON.parse(rawPropsDraft);
                        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
                          setRawPropsError("El JSON debe ser un objeto.");
                          return;
                        }
                        setRawPropsError(null);
                        saveSectionProps(parsed as Record<string, unknown>);
                      } catch {
                        setRawPropsError("JSON inválido.");
                      }
                    }}
                    className="rounded-md border border-slate-200 dark:border-white/10 px-2 py-1 text-[10px] font-black uppercase tracking-widest"
                  >
                    Guardar JSON
                  </button>
                  {rawPropsError && <p className="text-[10px] text-rose-500">{rawPropsError}</p>}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => setSectionVisibility(!activeSection.is_visible)} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1">
                    {activeSection.is_visible ? <EyeOff size={11} /> : <Eye size={11} />} {activeSection.is_visible ? "Ocultar" : "Mostrar"}
                  </button>
                  <button onClick={duplicateSection} className="rounded-lg border border-slate-200 dark:border-white/10 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1">
                    <Copy size={11} /> Duplicar
                  </button>
                  <button onClick={removeSection} className="col-span-2 rounded-lg border border-rose-200 text-rose-600 px-2 py-1.5 text-[10px] font-black uppercase tracking-widest inline-flex items-center justify-center gap-1">
                    <Trash2 size={11} /> Eliminar
                  </button>
                </div>
                <p className="text-[10px] text-slate-400">{saving ? "Guardando..." : "Cambios guardados al salir del campo"}</p>
              </fieldset>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Versiones</p>
            <div className="max-h-44 overflow-auto space-y-2 pr-1">
              {versions.map((version) => (
                <button key={version.id} onClick={() => rollback(version.id)} disabled={!canPublish} className="w-full rounded-lg border border-slate-200 dark:border-white/10 p-2 text-left text-xs hover:border-primary/40 transition-all disabled:opacity-50">
                  <p className="font-black">v{version.version_number}</p>
                  <p className="text-[10px] text-slate-400">{new Date(version.created_at).toLocaleString()}</p>
                </button>
              ))}
              {versions.length === 0 && <p className="text-xs text-slate-500">Aún sin versiones publicadas.</p>}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import { LayoutPanelTop, Plus } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { createCmsPage, createCmsSection, listCmsPages, listCmsSections, listCmsSites } from "@/lib/cms/v2";

const SECTION_TYPES = ["hero", "rich_text", "cards", "cta_banner", "gallery", "faq", "embed"];

export default function CmsBuilderPage() {
  const { token } = useAuth();
  const [siteKey, setSiteKey] = useState("faro");
  const [sites, setSites] = useState<Array<{ site_key: string; name: string }>>([]);
  const [pages, setPages] = useState<Array<{ id: number; slug: string; title: string; status: string }>>([]);
  const [activeSlug, setActiveSlug] = useState("");
  const [sections, setSections] = useState<Array<{ id: number; type: string; sort_order: number; props_json: Record<string, unknown> }>>([]);
  const [newPageTitle, setNewPageTitle] = useState("");
  const [newSectionType, setNewSectionType] = useState("rich_text");

  const loadPages = async (targetSite: string) => {
    if (!token) return;
    const [nextSites, nextPages] = await Promise.all([listCmsSites(token), listCmsPages(targetSite, token)]);
    setSites((nextSites || []).map((site) => ({ site_key: site.site_key, name: site.name })));
    setPages(nextPages || []);
    if ((nextPages || []).length > 0 && !activeSlug) {
      setActiveSlug(nextPages[0].slug);
    }
  };

  const loadSections = async (slug: string) => {
    if (!token || !slug) return;
    const next = await listCmsSections(siteKey, slug, token);
    setSections((next || []).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)));
  };

  useEffect(() => {
    loadPages(siteKey).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteKey, token]);

  useEffect(() => {
    loadSections(activeSlug).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSlug, token]);

  const createPage = async () => {
    if (!token || !newPageTitle.trim()) return;
    const slug = newPageTitle.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "");
    const row = await createCmsPage(siteKey, { slug, title: newPageTitle }, token);
    setNewPageTitle("");
    await loadPages(siteKey);
    setActiveSlug(row.slug);
  };

  const addSection = async () => {
    if (!token || !activeSlug) return;
    await createCmsSection(
      siteKey,
      activeSlug,
      {
        type: newSectionType,
        sort_order: sections.length,
        props_json: { title: "Nueva sección", body: "Edita este contenido" },
      },
      token,
    );
    await loadSections(activeSlug);
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
            <input value={newPageTitle} onChange={(e) => setNewPageTitle(e.target.value)} placeholder="Ej: Página de bienvenida" className="w-full rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm" />
            <button onClick={createPage} className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-[10px] font-black uppercase tracking-widest text-white"><Plus size={12} /> Crear</button>
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Páginas</p>
            {pages.map((page) => (
              <button key={page.id} onClick={() => setActiveSlug(page.slug)} className={`w-full text-left rounded-lg border px-3 py-2 text-sm ${activeSlug === page.slug ? "border-primary/40 bg-primary/5" : "border-slate-200 dark:border-white/10"}`}>
                <p className="font-bold">{page.title}</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-400">/{page.slug}</p>
              </button>
            ))}
          </div>
        </aside>

        <section className="lg:col-span-9 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-black">Secciones · {activeSlug ? `/${activeSlug}` : "Selecciona página"}</h2>
            <div className="flex items-center gap-2">
              <select value={newSectionType} onChange={(e) => setNewSectionType(e.target.value)} className="rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm">
                {SECTION_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
              <button onClick={addSection} disabled={!activeSlug} className="inline-flex items-center gap-2 rounded-lg border border-slate-200 dark:border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-widest disabled:opacity-50">
                <Plus size={12} /> Añadir sección
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {sections.map((section) => (
              <div key={section.id} className="rounded-xl border border-slate-200 dark:border-white/10 p-3">
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{section.type}</p>
                <pre className="mt-2 overflow-auto text-xs text-slate-600 dark:text-slate-300">{JSON.stringify(section.props_json, null, 2)}</pre>
              </div>
            ))}
            {sections.length === 0 && <p className="text-sm text-slate-500">No hay secciones en esta página.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}

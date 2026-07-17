"use client";

import React from "react";
import { Plus } from "lucide-react";
import { SITE_KEY } from "@/lib/site-config";
import { PAGE_TEMPLATES, SECTION_TEMPLATES } from "@/components/cms/builder/constants";
import type { PageBuilderState } from "@/hooks/usePageBuilder";

export default function BuilderSidebar({
  builder,
}: {
  builder: PageBuilderState;
}) {
  const {
    siteKey,
    setSiteKey,
    sites,
    pages,
    activeSlug,
    setActiveSlug,
    newPageTitle,
    setNewPageTitle,
    canEdit,
    createPage,
    pageTemplateKey,
    setPageTemplateKey,
    createPageFromTemplate,
    addTemplateSection,
  } = builder;
  const popupTemplate = SECTION_TEMPLATES.find((template) => template.type === "popup_banner");
  return (
        <aside className="lg:col-span-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-4 space-y-3">
          <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Sitio</label>
          <select value={siteKey} onChange={(e) => setSiteKey(e.target.value)} className="w-full rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-sm">
            {sites.length === 0 && <option value={SITE_KEY}>{SITE_KEY}</option>}
            {sites.map((site) => (
              <option key={site.site_key} value={site.site_key}>{site.name} ({site.site_key})</option>
            ))}
          </select>

          <div className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 p-3 space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Nueva página</p>
            <input value={newPageTitle} onChange={(e) => setNewPageTitle(e.target.value)} placeholder="Ej: Página de bienvenida" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-sm" disabled={!canEdit} />
            <button onClick={createPage} disabled={!canEdit} className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white disabled:opacity-50"><Plus size={12} /> Crear vacía</button>
            <select value={pageTemplateKey} onChange={(e) => setPageTemplateKey(e.target.value)} className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs">
              {PAGE_TEMPLATES.map((template) => (
                <option key={template.key} value={template.key}>{template.label}</option>
              ))}
            </select>
            <button onClick={createPageFromTemplate} disabled={!canEdit} className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50">
              <Plus size={12} /> Crear con plantilla
            </button>
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Páginas</p>
            {pages.map((page) => (
              <button key={page.id} onClick={() => setActiveSlug(page.slug)} className={`w-full text-left rounded-lg border px-3 py-2 text-sm ${activeSlug === page.slug ? "border-primary/40 bg-primary/5" : "border-[hsl(var(--border))] dark:border-white/10"}`}>
                <p className="font-bold">{page.title}</p>
                <p className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))]">/{page.slug} · {page.status}</p>
              </button>
            ))}
          </div>

          <div className="space-y-2 pt-2 border-t border-[hsl(var(--border))] dark:border-white/10">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Plantillas rápidas</p>
            {popupTemplate && (
              <div className="rounded-lg border border-rose-200 bg-rose-50/70 p-3 dark:border-rose-500/20 dark:bg-rose-500/5">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-rose-700 dark:text-rose-200">Pop-up</p>
                <p className="mt-1 text-[11px] text-[hsl(var(--text-secondary))]">
                  Crea un aviso temporal sin editar el contenido principal de la página.
                </p>
                <button
                  type="button"
                  onClick={() => addTemplateSection(popupTemplate)}
                  disabled={!activeSlug || !canEdit}
                  className="mt-2 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-rose-600 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white disabled:opacity-50"
                >
                  <Plus size={12} /> Crear pop-up
                </button>
              </div>
            )}
            {SECTION_TEMPLATES.map((template) => (
              <button
                key={template.label}
                onClick={() => addTemplateSection(template)}
                disabled={!activeSlug || !canEdit}
                className="w-full text-left rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-xs font-bold hover:border-primary/40 transition-all disabled:opacity-50"
              >
                {template.label}
              </button>
            ))}
          </div>
        </aside>

  );
}

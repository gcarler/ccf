"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Calendar, FileText, Globe, Plus, Search, Trash2, Zap } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import SidePanel from "@/components/ui/SidePanel";
import clsx from "clsx";
import { createCmsPage, deleteCmsPage, listCmsPages, listCmsSites, patchCmsPage } from "@/lib/cms/v2";
import { CmsPage } from "@/types/cms-v2";
import { canEditCms } from "@/lib/cms/permissions";

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "").replace(/-+/g, "-");
}

export default function CmsPagesManagement() {
  const router = useRouter();
  const { token, user } = useAuth();
  const [siteKey, setSiteKey] = useState("faro");
  const [sites, setSites] = useState<Array<{ site_key: string; name: string }>>([]);
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [selectedPage, setSelectedPage] = useState<CmsPage | null>(null);
  const canEdit = canEditCms(user?.role);

  const fetchPages = async (targetSite: string) => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [nextSites, nextPages] = await Promise.all([listCmsSites(token), listCmsPages(targetSite, token)]);
      const siteList = (nextSites || []).map((site) => ({ site_key: site.site_key, name: site.name }));
      setSites(siteList);
      // If the current siteKey is not in the fetched sites, default to the first one
      if (!siteList.find((s) => s.site_key === targetSite) && siteList.length > 0) {
        setSiteKey(siteList[0].site_key);
      }
      setPages(nextPages || []);
      console.log('Fetched pages:', nextPages?.length || 0);
    } catch (error) {
      console.error("Error fetching pages:", error);
      setPages([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPages(siteKey).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, siteKey]);

  const visiblePages = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return pages;
    return pages.filter((page) => page.title.toLowerCase().includes(term) || page.slug.toLowerCase().includes(term));
  }, [pages, search]);

  const handleCreatePage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!newTitle.trim() || !token || !canEdit) return;
    try {
      const slug = slugify(newTitle);
      if (!slug) return;
      await createCmsPage(siteKey, { title: newTitle, slug }, token);
      setNewTitle("");
      setIsQuickAddOpen(false);
      await fetchPages(siteKey);
    } catch (error) {
      console.error("Error creating page:", error);
    }
  };

  const handleDeletePage = async (page: CmsPage) => {
    if (!token || !canEdit) return;
    try {
      await deleteCmsPage(siteKey, page.slug, token);
      if (selectedPage?.id === page.id) setSelectedPage(null);
      await fetchPages(siteKey);
    } catch (error) {
      console.error("Error deleting page:", error);
    }
  };

  const handleSavePage = async () => {
    if (!token || !selectedPage || !canEdit) return;
    try {
      const nextSlug = slugify(selectedPage.slug);
      const updated = await patchCmsPage(
        siteKey,
        selectedPage.slug,
        {
          title: selectedPage.title,
          slug: nextSlug,
        },
        token,
      );
      setSelectedPage(updated);
      await fetchPages(siteKey);
    } catch (error) {
      console.error("Error updating page:", error);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-[#141517]">
      <header className="h-14 border-b border-slate-100 dark:border-white/5 flex items-center px-6 gap-4 shrink-0">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <FileText size={16} className="text-blue-600" />
          <h2 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Gestión de páginas v2</h2>
        </div>

        <select value={siteKey} onChange={(e) => setSiteKey(e.target.value)} className="rounded-lg border border-slate-200 dark:border-white/10 bg-transparent px-3 py-1.5 text-[12px]">
          {sites.length === 0 && <option value="faro">faro</option>}
          {sites.map((site) => (
            <option key={site.site_key} value={site.site_key}>{site.name} ({site.site_key})</option>
          ))}
        </select>

        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar páginas..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-1.5 bg-slate-100 dark:bg-white/5 border-none rounded-lg text-[12px] focus:ring-2 focus:ring-blue-500/20 w-64 transition-all"
          />
        </div>
        <button
          onClick={() => setIsQuickAddOpen((prev) => !prev)}
          disabled={!canEdit}
          className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50"
        >
          <Plus size={14} /> Nueva página
        </button>
      </header>

      <AnimatePresence>
        {isQuickAddOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="bg-violet-50 dark:bg-violet-900/10 border-b-2 border-violet-300 dark:border-violet-500/30 overflow-hidden shrink-0"
          >
            <form onSubmit={handleCreatePage} className="px-6 py-4 flex items-center gap-4">
              <div className="size-8 rounded-lg bg-violet-600 text-white flex items-center justify-center shrink-0">
                <Zap size={16} />
              </div>
              <input
                autoFocus
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Escape" && setIsQuickAddOpen(false)}
                placeholder="Título de la nueva página (Enter para crear)"
                disabled={!canEdit}
                className="flex-1 bg-transparent border-none text-[15px] font-bold text-violet-900 dark:text-violet-200 placeholder:text-violet-400 focus:ring-0"
              />
              <button type="submit" disabled={!canEdit} className="bg-violet-600 text-white px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest disabled:opacity-50">Guardar</button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
        {loading ? (
          <div className="space-y-4">{[1, 2, 3].map((i) => <div key={i} className="h-20 bg-slate-50 dark:bg-white/5 rounded-2xl animate-pulse" />)}</div>
        ) : visiblePages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
            <div className="size-16 rounded-[2rem] bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400"><FileText size={32} /></div>
            <div>
              <p className="font-bold text-slate-900 dark:text-white">No hay páginas creadas</p>
              <p className="text-sm text-slate-500">Usa la barra superior para crear tu primera página.</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {visiblePages.map((page, index) => (
              <motion.div
                key={page.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.04 }}
                onClick={() => router.push(`/cms/pages/${page.id}`)}
                className="group bg-white dark:bg-[#252528] rounded-2xl border border-slate-200/70 dark:border-white/5 p-4 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all duration-300 cursor-pointer active:scale-[0.99] flex items-center gap-4"
              >
                <div className="size-12 rounded-xl bg-blue-50 dark:bg-blue-500/10 text-blue-600 flex items-center justify-center shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-all">
                  <FileText size={20} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <h3 className="text-[13px] font-semibold text-slate-900 dark:text-white truncate">{page.title}</h3>
                    <span className={clsx("px-2 py-0.5 rounded-full text-[10px] font-bold uppercase", page.status === "published" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700")}>{page.status}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1 text-[11px] text-slate-400"><Globe size={12} /><span>/{page.slug}</span></div>
                    <div className="size-1 bg-slate-200 dark:bg-white/10 rounded-full" />
                    <div className="flex items-center gap-1 text-[11px] text-slate-400"><Calendar size={12} /><span>Actualizado {new Date(page.updated_at).toLocaleDateString()}</span></div>
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeletePage(page);
                  }}
                  disabled={!canEdit}
                  className="opacity-0 group-hover:opacity-100 transition-all p-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-xl text-slate-400 hover:text-rose-600"
                >
                  <Trash2 size={16} />
                </button>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      <SidePanel
        isOpen={!!selectedPage}
        onClose={() => setSelectedPage(null)}
        title={selectedPage?.title || ""}
        subtitle={selectedPage ? `Slug: /${selectedPage.slug}` : undefined}
        fullViewHref={selectedPage ? `/cms/builder?site=${siteKey}&page=${selectedPage.slug}` : undefined}
      >
        {selectedPage && (
          <div className="space-y-6">
            <section className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">Configuración general</label>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-slate-700 dark:text-slate-300">Título</span>
                  <input type="text" value={selectedPage.title} onChange={(e) => setSelectedPage({ ...selectedPage, title: e.target.value })} className="w-full px-3 py-2 text-[13px] bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-xl" disabled={!canEdit} />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-slate-700 dark:text-slate-300">Slug</span>
                  <input type="text" value={selectedPage.slug} onChange={(e) => setSelectedPage({ ...selectedPage, slug: e.target.value })} className="w-full px-3 py-2 text-[13px] bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-xl" disabled={!canEdit} />
                </div>
              </div>
            </section>

            <div className="pt-6 border-t border-slate-100 dark:border-white/5">
              <button onClick={handleSavePage} disabled={!canEdit} className="w-full bg-blue-600 text-white py-3 rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-50">
                Guardar cambios
              </button>
            </div>
          </div>
        )}
      </SidePanel>
    </div>
  );
}

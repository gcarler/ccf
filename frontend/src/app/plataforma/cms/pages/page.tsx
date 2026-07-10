"use client";

import React, { useEffect, useMemo, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { Archive, Calendar, Eye, FileText, Globe, Plus, RotateCcw, Search, Zap, PenTool, Check } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import SidePanel from "@/components/ui/SidePanel";
import clsx from "clsx";
import { createCmsPage, listCmsPages, listCmsSites, patchCmsPage, workflowCmsPage, scheduleEventColor, isScheduledPage, isExpiringPage } from "@/lib/cms/v2";
import { CmsPage } from "@/types/cms-v2";
import { canEditCms } from "@/lib/cms/permissions";
import ViewSwitcher, { ViewType } from "@/components/ViewSwitcher";
import UniversalCalendarView from "@/components/ui/UniversalCalendarView";
import UniversalGanttView from "@/components/ui/UniversalGanttView";
import UniversalWikiView from "@/components/ui/UniversalWikiView";

const CMS_PAGE_VIEWS: ViewType[] = ["grid", "list", "table", "board", "kanban", "calendar", "gantt", "wiki"];

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  published: { label: "Publicado",   color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400" },
  draft:     { label: "Borrador",    color: "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]" },
  in_review: { label: "En revision", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" },
  archived:  { label: "Archivado",   color: "bg-rose-100 text-rose-600 dark:bg-rose-900/10 dark:text-rose-400" },
};

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "").replace(/-+/g, "-");
}

export default function CmsPagesManagement() {
  const router = useRouter();
  const { token, user } = useAuth();
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<Array<{ site_key: string; name: string }>>([]);
  const [pages, setPages] = useState<CmsPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [viewType, setViewType] = useState<ViewType>("grid");
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [selectedPage, setSelectedPage] = useState<CmsPage | null>(null);
  const [pendingArchivePage, setPendingArchivePage] = useState<CmsPage | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
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
    } catch (error) {
      toast.error("Error fetching pages");
      toast.error("Error al cargar páginas");
      setPages([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPages(siteKey).catch(() => toast.error("Error al cargar páginas"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, siteKey]);

  const visiblePages = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return pages;
    return pages.filter((page) => page.title.toLowerCase().includes(term) || page.slug.toLowerCase().includes(term));
  }, [pages, search]);

  const groupedPages = useMemo(() => {
    return ["published", "draft", "in_review", "archived"].map((status) => ({
      status,
      pages: visiblePages.filter((page) => (page.status || "draft") === status),
    }));
  }, [visiblePages]);

  const calendarEvents = useMemo(() => {
    const events: Array<{
      id: string;
      title: string;
      date: string;
      color: "blue" | "emerald" | "amber" | "rose";
      location: string;
      meta?: Record<string, string>;
    }> = [];
    for (const page of visiblePages) {
      const slugHref = `/${page.slug}`;
      // 1) Publish event: scheduled.publish_at OR a published page's first seen date.
      if (isScheduledPage(page) && page.publish_at) {
        const iso = page.publish_at;
        events.push({
          id: `${page.id}::publish`,
          title: `📅 ${page.title}`,
          date: iso.split("T")[0],
          color: scheduleEventColor(page.status, "publish"),
          location: slugHref,
          meta: { kind: "publish", pageId: page.id, slug: page.slug, status: page.status || "draft" },
        });
      }
      // 2) Expiry event: published pages with expires_at.
      if (isExpiringPage(page) && page.expires_at) {
        events.push({
          id: `${page.id}::expire`,
          title: `⏳ ${page.title}`,
          date: page.expires_at.split("T")[0],
          color: scheduleEventColor(page.status, "expiry"),
          location: slugHref,
          meta: { kind: "expire", pageId: page.id, slug: page.slug, status: page.status || "draft" },
        });
      }
    }
    // 3) Fallback: pages without schedule metadata use updated_at so the
    //    calendar still shows them. Last-write-wins semantics preserved.
    for (const page of visiblePages) {
      if ((page as { publish_at?: string | null }).publish_at || (page as { expires_at?: string | null }).expires_at) {
        continue;
      }
      events.push({
        id: `${page.id}::updated`,
        title: page.title,
        date: (page.updated_at || page.created_at || new Date().toISOString()).split("T")[0],
        color: page.status === "published" ? "emerald" as const : page.status === "in_review" ? "amber" as const : page.status === "archived" ? "rose" as const : "blue" as const,
        location: `/${page.slug}`,
      });
    }
    return events;
  }, [visiblePages]);

  const upcomingSchedules = useMemo(() => {
    const now = Date.now();
    const horizonMs = 7 * 24 * 60 * 60 * 1000;
    return visiblePages
      .filter((page) => (page.publish_at || page.expires_at) && (page.status !== "archived"))
      .map((page) => ({
        page,
        publishTs: page.publish_at ? new Date(page.publish_at).getTime() : Infinity,
        expireTs: page.expires_at ? new Date(page.expires_at).getTime() : Infinity,
        soonestTs: Math.min(
          page.publish_at ? new Date(page.publish_at).getTime() : Infinity,
          page.expires_at ? new Date(page.expires_at).getTime() : Infinity,
        ),
      }))
      .filter((row) => row.soonestTs >= now && row.soonestTs <= now + horizonMs)
      .sort((a, b) => a.soonestTs - b.soonestTs);
  }, [visiblePages]);

  const ganttItems = useMemo(() => visiblePages.map((page) => {
    const start = page.created_at || page.updated_at || new Date().toISOString();
    const end = page.updated_at || start;
    return {
      id: page.id,
      title: page.title,
      subtitle: `/${page.slug}`,
      start_date: start,
      end_date: end,
      color: page.status === "published" ? "emerald" as const : page.status === "in_review" ? "amber" as const : page.status === "archived" ? "rose" as const : "blue" as const,
      progress: page.status === "published" || page.status === "archived" ? 100 : page.status === "in_review" ? 65 : 25,
    };
  }), [visiblePages]);

  const handleCreatePage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmedTitle = newTitle.trim();
    if (!trimmedTitle || !token || !canEdit) return;
    const slug = slugify(trimmedTitle);
    if (!slug) {
      toast.error("El título no produce un slug válido");
      return;
    }
    try {
      await createCmsPage(siteKey, { title: trimmedTitle, slug }, token);
      toast.success(`Página "${trimmedTitle}" creada`);
      setNewTitle("");
      setIsQuickAddOpen(false);
      await fetchPages(siteKey);
    } catch (error) {
      toast.error("Error creating page");
      toast.error("Error al crear página. El slug puede estar en uso.");
    }
  };

  const handleArchivePage = async (page: CmsPage) => {
    if (!token || !canEdit) return;
    setPendingArchivePage(page);
  };

  const confirmArchivePage = async () => {
    const page = pendingArchivePage;
    if (!token || !canEdit) return;
    if (!page) return;
    try {
      await workflowCmsPage(siteKey, page.slug, "archive", "Archivada desde gestion de paginas", token);
      if (selectedPage?.id === page.id) {
        setSelectedPage({ ...page, status: "archived" });
      }
      setPendingArchivePage(null);
      await fetchPages(siteKey);
    } catch (error) {
      toast.error("Error archiving page");
      toast.error("Error al archivar página");
    }
  };

  const handleRestorePage = async (page: CmsPage) => {
    if (!token || !canEdit) return;
    try {
      const updated = await workflowCmsPage(siteKey, page.slug, "revert_draft", "Restaurada desde archivo", token);
      if (selectedPage?.id === page.id) {
        setSelectedPage(updated);
      }
      await fetchPages(siteKey);
    } catch (error) {
      toast.error("Error restoring page");
      toast.error("Error al restaurar página");
    }
  };

  const handleArchiveSelected = async () => {
    if (!token || !canEdit || selectedIds.size === 0) return;
    const selectedPages = pages.filter((page) => selectedIds.has(page.id) && page.status !== "archived");
    try {
      await Promise.all(
        selectedPages.map((page) =>
          workflowCmsPage(siteKey, page.slug, "archive", "Archivada desde seleccion multiple", token),
        ),
      );
      setSelectedIds(new Set());
      await fetchPages(siteKey);
    } catch (error) {
      toast.error("Error archiving selected pages");
      toast.error("Error al archivar páginas seleccionadas");
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
          seo_json: selectedPage.seo_json,
        },
        token,
      );
      setSelectedPage(updated);
      await fetchPages(siteKey);
    } catch (error) {
      toast.error("Error updating page");
      toast.error("Error al actualizar página");
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const openPage = (page: CmsPage) => router.push(`/cms/pages/${page.slug}`);

  const openPreview = (page: CmsPage) => {
    window.open(`/plataforma/cms/preview?site=${encodeURIComponent(siteKey)}&page=${encodeURIComponent(page.slug)}`, "_blank");
  };

  const renderPageList = () => (
 <div className="space-y-3 w-full">
      {visiblePages.map((page, index) => {
        const st = STATUS_CONFIG[page.status] ?? STATUS_CONFIG["draft"];
        return (
          <motion.div
            key={page.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.025 }}
            onClick={() => openPage(page)}
            className="group bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 p-4 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all cursor-pointer flex items-center gap-4"
          >
            <div className="size-6 rounded-md bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))] flex items-center justify-center shrink-0 group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all">
              <FileText size={18} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{page.title}</h3>
                <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide", st.color)}>{st.label}</span>
              </div>
              <div className="flex items-center gap-3 text-[11px] text-[hsl(var(--text-secondary))]">
                <span className="flex items-center gap-1"><Globe size={11} />/{page.slug}</span>
                <span className="flex items-center gap-1"><Calendar size={11} />{page.updated_at ? new Date(page.updated_at).toLocaleDateString() : "Sin fecha"}</span>
              </div>
            </div>                    <button
                      onClick={(e) => { e.stopPropagation(); openPreview(page); }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 text-[9px] font-semibold uppercase tracking-wide hover:bg-emerald-100 transition-all"
                    >
                      <Eye size={11} /> Preview
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); router.push(`/cms/builder?site=${siteKey}&page=${page.slug}`); }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] text-[9px] font-semibold uppercase tracking-wide hover:bg-blue-100 transition-all"
                    >
                      <PenTool size={11} /> Editar
                    </button>
          </motion.div>
        );
      })}
    </div>
  );

  const renderBoard = () => (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-full">
      {groupedPages.map((column) => {
        const st = STATUS_CONFIG[column.status] ?? STATUS_CONFIG["draft"];
        return (
          <section key={column.status} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-4">
            <div className="flex items-center justify-between mb-4">
              <span className={clsx("px-2.5 py-1 rounded-full text-[9px] font-semibold uppercase tracking-wide", st.color)}>{st.label}</span>
              <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))]">{column.pages.length}</span>
            </div>
            <div className="space-y-3">
              {column.pages.map((page) => (
                <button
                  key={page.id}
                  onClick={() => openPage(page)}
                  className="w-full text-left bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 hover:border-blue-400 hover:shadow-lg transition-all"
                >
                  <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white truncate">{page.title}</p>
                  <p className="text-[10px] font-mono text-[hsl(var(--text-secondary))] mt-2 truncate">/{page.slug}</p>
                </button>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
      <header className="h-8 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-3 gap-3 shrink-0">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <FileText size={16} className="text-[hsl(var(--primary))] shrink-0" />
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] truncate">Gestion de paginas</h2>
          <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full shrink-0">{visiblePages.length}</span>
        </div>

        <select value={siteKey} onChange={(e) => setSiteKey(e.target.value)} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-1.5 text-[12px] shrink-0">
          {sites.length === 0 && <option value={SITE_KEY}>{SITE_KEY}</option>}
          {sites.map((site) => (
            <option key={site.site_key} value={site.site_key}>{site.name} ({site.site_key})</option>
          ))}
        </select>

        <div className="relative shrink-0">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
          <input
            type="text"
            placeholder="Buscar paginas..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 border-none rounded-lg text-[12px] focus:ring-2 focus:ring-blue-500/20 w-52 transition-all"
          />
        </div>

        <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={CMS_PAGE_VIEWS} />

        <button
          onClick={() => setIsQuickAddOpen((prev) => !prev)}
          disabled={!canEdit}
          className="bg-[hsl(var(--primary))] text-white px-4 py-1.5 rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50 shrink-0"
        >
          <Plus size={14} /> Nueva pagina
        </button>
      </header>

      <AnimatePresence>
        {isQuickAddOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="bg-blue-50 dark:bg-blue-900/10 border-b-2 border-blue-300 dark:border-blue-500/30 overflow-hidden shrink-0"
          >
            <form onSubmit={handleCreatePage} className="px-3 py-1.5 flex items-center gap-4">
              <div className="size-8 rounded-lg bg-[hsl(var(--primary))] text-white flex items-center justify-center shrink-0">
                <Zap size={16} />
              </div>
              <input
                autoFocus
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Escape" && setIsQuickAddOpen(false)}
                placeholder="Titulo de la nueva pagina (Enter para crear)"
                disabled={!canEdit}
                className="flex-1 bg-transparent border-none text-sm font-bold text-blue-900 dark:text-blue-200 placeholder:text-[hsl(var(--primary))] focus:ring-0"
              />
              <button type="submit" disabled={!canEdit} className="bg-[hsl(var(--primary))] text-white px-3 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50">Guardar</button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-3">
        {loading ? (
          <div className="space-y-4">{[1, 2, 3].map((i) => <div key={i} className="h-20 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg animate-pulse" />)}</div>
        ) : visiblePages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50 py-1.5">
            <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]"><FileText size={32} /></div>
            <div>
              <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white">No hay paginas creadas</p>
              <p className="text-sm text-[hsl(var(--text-secondary))]">Usa la barra superior para crear tu primera pagina.</p>
            </div>
          </div>
        ) : viewType === "grid" ? (
          <div className="grid grid-cols-1 gap-3">
            {visiblePages.map((page, index) => {
              const st = STATUS_CONFIG[page.status] ?? STATUS_CONFIG["draft"];
              return (
                <motion.div
                  key={page.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04 }}
                  className="group bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 p-4 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all duration-200 flex items-center gap-4"
                >
                  {/* Checkbox */}
                  <button
                    onClick={() => toggleSelect(page.id)}
                    className={clsx(
                      "size-5 rounded-lg border-2 flex items-center justify-center shrink-0 transition-all",
                      selectedIds.has(page.id) ? "bg-[hsl(var(--primary))] border-blue-600" : "border-[hsl(var(--border))] dark:border-white/20 hover:border-blue-400"
                    )}
                  >
                    {selectedIds.has(page.id) && <Check size={11} className="text-white" strokeWidth={3} />}
                  </button>

                  <div
                    onClick={() => router.push(`/cms/pages/${page.slug}`)}
                    className="size-7 rounded-md bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))] flex items-center justify-center shrink-0 group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all cursor-pointer"
                  >
                    <FileText size={20} />
                  </div>

                  <div className="flex-1 min-w-0 cursor-pointer" onClick={() => router.push(`/cms/pages/${page.slug}`)}>
                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{page.title}</h3>
                      <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide", st.color)}>{st.label}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1 text-[11px] text-[hsl(var(--text-secondary))]"><Globe size={11} /><span>/{page.slug}</span></div>
                      {page.updated_at && <>
                        <div className="size-1 bg-[hsl(var(--surface-3))] dark:bg-white/10 rounded-full" />
                        <div className="flex items-center gap-1 text-[11px] text-[hsl(var(--text-secondary))]"><Calendar size={11} /><span>{new Date(page.updated_at).toLocaleDateString()}</span></div>
                      </>}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => openPreview(page)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 text-[9px] font-semibold uppercase tracking-wide hover:bg-emerald-100 transition-all"
                    >
                      <Eye size={11} /> Preview
                    </button>
                    <button
                      onClick={() => router.push(`/cms/builder?site=${siteKey}&page=${page.slug}`)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] text-[9px] font-semibold uppercase tracking-wide hover:bg-blue-100 transition-all"
                    >
                      <PenTool size={11} /> Editar
                    </button>
                    {page.status === "archived" ? (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleRestorePage(page); }}
                        disabled={!canEdit}
                        className="p-2 hover:bg-emerald-50 dark:hover:bg-emerald-500/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-emerald-600 transition-all disabled:opacity-50"
                        title="Restaurar a borrador"
                      >
                        <RotateCcw size={15} />
                      </button>
                    ) : (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleArchivePage(page); }}
                        disabled={!canEdit}
                        className="p-2 hover:bg-amber-50 dark:hover:bg-amber-500/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-amber-600 transition-all disabled:opacity-50"
                        title="Archivar pagina"
                      >
                        <Archive size={15} />
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        ) : viewType === "list" ? (
          renderPageList()
        ) : viewType === "board" || viewType === "kanban" ? (
          renderBoard()
        ) : viewType === "calendar" ? (
          <div className="space-y-4">
            <UniversalCalendarView
              title="Calendario de paginas"
              events={calendarEvents}
              onEventClick={(event) => {
                const meta = (event as { meta?: { pageId?: string; slug?: string } }).meta;
                const page = meta?.pageId
                  ? visiblePages.find((item) => item.id === meta.pageId)
                  : visiblePages.find((item) => `${item.id}::updated` === event.id || item.id === event.id);
                if (page) openPage(page);
              }}
            />
            {upcomingSchedules.length > 0 && (
              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] p-4 space-y-3"
              >
                <header className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar size={14} className="text-[hsl(var(--primary))]" />
                    <h3 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white">Próximos 7 días</h3>
                  </div>
                  <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{upcomingSchedules.length} eventos</span>
                </header>
                <div className="space-y-2">
                  {upcomingSchedules.map((row) => {
                    const isPublish = row.publishTs < row.expireTs && Number.isFinite(row.publishTs);
                    const target = isPublish ? row.page.publish_at : row.page.expires_at;
                    if (!target) return null;
                    const color = scheduleEventColor(row.page.status, isPublish ? "publish" : "expiry");
                    return (
                      <button
                        key={row.page.id}
                        onClick={() => openPage(row.page)}
                        className="w-full flex items-center gap-3 p-3 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-[#141517] border border-[hsl(var(--border))] dark:border-white/5 hover:border-[hsl(var(--primary))] transition-all group text-left"
                      >
                        <div className={clsx(
                          "size-2 rounded-full shrink-0",
                          color === "blue" && "bg-[hsl(var(--primary))]",
                          color === "emerald" && "bg-emerald-500",
                          color === "amber" && "bg-amber-500",
                          color === "rose" && "bg-rose-500",
                        )} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{row.page.title}</p>
                          <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-0.5">
                            {isPublish ? "📅 Publicación" : "⏳ Auto-archivado"} · {new Date(target).toLocaleString()}
                          </p>
                        </div>
                        <span className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors">Abrir →</span>
                      </button>
                    );
                  })}
                </div>
              </motion.section>
            )}
          </div>
        ) : viewType === "gantt" ? (
          <UniversalGanttView
            moduleName="CMS Pages"
            items={ganttItems}
            onItemClick={(item) => {
              const page = visiblePages.find((entry) => entry.id === item.id);
              if (page) openPage(page);
            }}
          />
        ) : viewType === "wiki" ? (
          <UniversalWikiView moduleName="CMS Pages" storageKey={`cms-pages-wiki-${siteKey}`} />
        ) : (
          /* TABLE VIEW */
          <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto">
            <table className="w-full min-w-[480px] text-left">
              <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                <tr>
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === visiblePages.length && visiblePages.length > 0}
                      onChange={e => setSelectedIds(e.target.checked ? new Set(visiblePages.map(p => p.id)) : new Set())}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Pagina</th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Slug</th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden lg:table-cell">Estado</th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden xl:table-cell">Actualizado</th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                {visiblePages.map(page => {
                  const st = STATUS_CONFIG[page.status] ?? STATUS_CONFIG["draft"];
                  return (
                    <tr key={page.id} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] group transition-colors">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(page.id)}
                          onChange={() => toggleSelect(page.id)}
                          className="rounded"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="size-8 rounded-md bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] flex items-center justify-center shrink-0">
                            <FileText size={14} />
                          </div>
                          <span className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate max-w-[200px]">{page.title}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className="text-[11px] font-mono text-[hsl(var(--text-secondary))]">/{page.slug}</span>
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide", st.color)}>{st.label}</span>
                      </td>
                      <td className="px-4 py-3 hidden xl:table-cell">
                        <span className="text-[11px] text-[hsl(var(--text-secondary))]">{page.updated_at ? new Date(page.updated_at).toLocaleDateString() : "-"}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => openPreview(page)}
                            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 text-[9px] font-semibold uppercase hover:bg-emerald-100 transition-all"
                          >
                            <Eye size={10} /> Preview
                          </button>
                          <button
                            onClick={() => router.push(`/cms/builder?site=${siteKey}&page=${page.slug}`)}
                            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] text-[9px] font-semibold uppercase hover:bg-blue-100 transition-all"
                          >
                            <PenTool size={10} /> Editar
                          </button>
                          <button
                            onClick={() => page.status === "archived" ? handleRestorePage(page) : handleArchivePage(page)}
                            disabled={!canEdit}
                            className={clsx(
                              "p-1.5 rounded-lg transition-all opacity-0 group-hover:opacity-100 disabled:opacity-40",
                              page.status === "archived"
                                ? "hover:bg-emerald-50 dark:hover:bg-emerald-500/10 text-[hsl(var(--text-secondary))] hover:text-emerald-600"
                                : "hover:bg-amber-50 dark:hover:bg-amber-500/10 text-[hsl(var(--text-secondary))] hover:text-amber-600"
                            )}
                          >
                            {page.status === "archived" ? <RotateCcw size={13} /> : <Archive size={13} />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {/* Bulk actions */}
            {selectedIds.size > 0 && (
              <div className="px-4 py-3 bg-blue-50 dark:bg-blue-900/10 border-t border-blue-200 dark:border-blue-700/30 flex items-center gap-3">
                <span className="text-[10px] font-semibold text-[hsl(var(--primary))] uppercase tracking-wide">{selectedIds.size} seleccionadas</span>
                <button
                  onClick={handleArchiveSelected}
                  disabled={!canEdit}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 text-white text-[9px] font-semibold uppercase tracking-wide hover:bg-amber-600 transition-all disabled:opacity-50"
                >
                  <Archive size={10} /> Archivar seleccion
                </button>
                <button onClick={() => setSelectedIds(new Set())} className="text-[9px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]">
                  Cancelar
                </button>
              </div>
            )}
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
          <div className="space-y-3">
            <section className="space-y-3">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Configuracion general</label>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Titulo</span>
                  <input type="text" value={selectedPage.title} onChange={(e) => setSelectedPage({ ...selectedPage, title: e.target.value })} className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md" disabled={!canEdit} />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Slug</span>
                  <input type="text" value={selectedPage.slug} onChange={(e) => setSelectedPage({ ...selectedPage, slug: e.target.value })} className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md" disabled={!canEdit} />
                </div>
              </div>
            </section>

            <section className="space-y-3">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">SEO (Optimizacion y redes)</label>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Meta descripcion</span>
                  <textarea
                    rows={3}
                    value={(selectedPage.seo_json?.meta_description as string) || ""}
                    onChange={(e) => setSelectedPage({ ...selectedPage, seo_json: { ...(selectedPage.seo_json || {}), meta_description: e.target.value } })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md resize-none custom-scrollbar"
                    disabled={!canEdit}
                    placeholder="Breve descripcion para Google..."
                  />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Imagen Open Graph (URL)</span>
                  <input
                    type="url"
                    value={(selectedPage.seo_json?.meta_image as string) || ""}
                    onChange={(e) => setSelectedPage({ ...selectedPage, seo_json: { ...(selectedPage.seo_json || {}), meta_image: e.target.value } })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                    placeholder="https://..."
                  />
                  {(selectedPage.seo_json?.meta_image as string) && (
                    <div className="mt-2 rounded-md overflow-hidden border border-[hsl(var(--border))] dark:border-white/10 h-32 bg-[hsl(var(--surface-2))] dark:bg-white/5 relative">
                       <OptimizedImage src={selectedPage.seo_json?.meta_image as string} alt="OG Preview" fill sizes="400px" className="absolute inset-0 w-full h-full object-cover" />
                    </div>
                  )}
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Canonical URL (opcional)</span>
                  <input
                    type="url"
                    value={(selectedPage.seo_json?.canonical_url as string) || ""}
                    onChange={(e) => setSelectedPage({ ...selectedPage, seo_json: { ...(selectedPage.seo_json || {}), canonical_url: e.target.value } })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                    placeholder="https://ejemplo.com/pagina-canonical"
                  />
                  <p className="text-[10px] text-[hsl(var(--text-secondary))]">Si se deja vacío, se usa la URL automática de la página.</p>
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Meta Robots (opcional)</span>
                  <select
                    value={(selectedPage.seo_json?.robots_meta as string) || ""}
                    onChange={(e) => setSelectedPage({ ...selectedPage, seo_json: { ...(selectedPage.seo_json || {}), robots_meta: e.target.value || undefined } })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                  >
                    <option value="">index, follow (por defecto)</option>
                    <option value="index, nofollow">index, nofollow</option>
                    <option value="noindex, follow">noindex, follow</option>
                    <option value="noindex, nofollow">noindex, nofollow</option>
                  </select>
                </div>
              </div>
            </section>

            <div className="pt-6 border-t border-[hsl(var(--border))] dark:border-white/5">
              <button onClick={handleSavePage} disabled={!canEdit} className="w-full bg-[hsl(var(--primary))] text-white py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-50">
                Guardar cambios
              </button>
              {selectedPage.status === "archived" ? (
                <button
                  onClick={() => handleRestorePage(selectedPage)}
                  disabled={!canEdit}
                  className="mt-3 w-full border border-emerald-200 text-emerald-700 dark:text-emerald-300 py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-emerald-50 dark:hover:bg-emerald-500/10 active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <RotateCcw size={14} /> Restaurar a borrador
                </button>
              ) : (
                <button
                  onClick={() => handleArchivePage(selectedPage)}
                  disabled={!canEdit}
                  className="mt-3 w-full border border-amber-200 text-amber-700 dark:text-amber-300 py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-amber-50 dark:hover:bg-amber-500/10 active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <Archive size={14} /> Archivar pagina
                </button>
              )}
            </div>
          </div>
        )}
      </SidePanel>

      <SidePanel
        isOpen={!!pendingArchivePage}
        onClose={() => setPendingArchivePage(null)}
        title="Archivar pagina"
        subtitle={pendingArchivePage ? `/${pendingArchivePage.slug}` : undefined}
      >
        {pendingArchivePage && (
          <div className="space-y-4">
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
              <p className="text-sm font-semibold">{pendingArchivePage.title}</p>
              <p className="mt-2 text-xs leading-5 text-amber-800 dark:text-amber-200">
                La pagina quedara archivada y podras restaurarla despues.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPendingArchivePage(null)}
                className="flex-1 rounded-md border border-[hsl(var(--border))] px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5"
              >
                Cancelar
              </button>
              <button
                onClick={confirmArchivePage}
                disabled={!canEdit}
                className="flex-1 rounded-md bg-amber-500 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-white transition-all hover:bg-amber-600 disabled:opacity-50"
              >
                Archivar
              </button>
            </div>
          </div>
        )}
      </SidePanel>
    </div>
  );
}

"use client";

import React, { useEffect, useMemo, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";

import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Archive,
  Calendar,
  FileText,
  Globe,
  Plus,
  RotateCcw,
  Search,
  Zap,
  PenTool,
  Check,
  Tag,
  FolderOpen,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import SidePanel from "@/components/ui/SidePanel";
import clsx from "clsx";
import {
  createCmsPost,
  listCmsCategories,
  listCmsPosts,
  listCmsSites,
  listCmsTags,
  patchCmsPost,
} from "@/lib/cms/v2";
import { CmsCategory, CmsPostWithTaxonomies, CmsSite, CmsTag } from "@/types/cms-v2";
import { canEditCms } from "@/lib/cms/permissions";
import ViewSwitcher, { ViewType } from "@/components/ViewSwitcher";

const CMS_POST_VIEWS: ViewType[] = ["grid", "list", "table", "board", "kanban"];

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  published: { label: "Publicado", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400" },
  draft: { label: "Borrador", color: "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]" },
  in_review: { label: "En revisión", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" },
  approved: { label: "Aprobado", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400" },
  archived: { label: "Archivado", color: "bg-rose-100 text-rose-600 dark:bg-rose-900/10 dark:text-rose-400" },
};

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/\s+/g, "-").replace(/[^a-z0-9\-/]/g, "").replace(/-+/g, "-");
}

export default function CmsPostsManagement() {
  const { token, user } = useAuth();
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [posts, setPosts] = useState<CmsPostWithTaxonomies[]>([]);
  const [categories, setCategories] = useState<CmsCategory[]>([]);
  const [tags, setTags] = useState<CmsTag[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [viewType, setViewType] = useState<ViewType>("grid");
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [selectedPost, setSelectedPost] = useState<CmsPostWithTaxonomies | null>(null);
  const [pendingArchivePost, setPendingArchivePost] = useState<CmsPostWithTaxonomies | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const canEdit = canEditCms(user?.role);

  const fetchData = async (targetSite: string) => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [nextSites, nextPosts, nextCategories, nextTags] = await Promise.all([
        listCmsSites(token),
        listCmsPosts(targetSite, token),
        listCmsCategories(targetSite, token),
        listCmsTags(targetSite, token),
      ]);
      setSites(nextSites || []);
      setPosts(nextPosts || []);
      setCategories(nextCategories || []);
      setTags(nextTags || []);
    } catch (error) {
      toast.error("Error fetching posts");
      toast.error("Error al cargar posts");
      setPosts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(siteKey);
  }, [token, siteKey]);

  const visiblePosts = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return posts;
    return posts.filter(
      (post) =>
        post.title.toLowerCase().includes(term) ||
        post.slug.toLowerCase().includes(term) ||
        (post.excerpt || "").toLowerCase().includes(term)
    );
  }, [posts, search]);

  const groupedPosts = useMemo(() => {
    return ["published", "draft", "in_review", "approved", "archived"].map((status) => ({
      status,
      posts: visiblePosts.filter((post) => (post.status || "draft") === status),
    }));
  }, [visiblePosts]);

  const handleCreatePost = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmedTitle = newTitle.trim();
    if (!trimmedTitle || !token || !canEdit) return;
    const slug = slugify(trimmedTitle);
    if (!slug) {
      toast.error("El título no produce un slug válido");
      return;
    }
    try {
      await createCmsPost(siteKey, { title: trimmedTitle, slug, status: "draft" }, token);
      toast.success(`Post "${trimmedTitle}" creado`);
      setNewTitle("");
      setIsQuickAddOpen(false);
      await fetchData(siteKey);
    } catch (error) {
      toast.error("Error creating post");
      toast.error("Error al crear post. El slug puede estar en uso.");
    }
  };

  const handleArchivePost = async (post: CmsPostWithTaxonomies) => {
    if (!token || !canEdit) return;
    setPendingArchivePost(post);
  };

  const confirmArchivePost = async () => {
    const post = pendingArchivePost;
    if (!token || !canEdit || !post) return;
    try {
      await patchCmsPost(siteKey, post.slug, { status: "archived" }, token);
      if (selectedPost?.id === post.id) {
        setSelectedPost({ ...post, status: "archived" });
      }
      setPendingArchivePost(null);
      await fetchData(siteKey);
      toast.success("Post archivado");
    } catch (error) {
      toast.error("Error archiving post");
      toast.error("Error al archivar post");
    }
  };

  const handleRestorePost = async (post: CmsPostWithTaxonomies) => {
    if (!token || !canEdit) return;
    try {
      const updated = await patchCmsPost(siteKey, post.slug, { status: "draft" }, token);
      if (selectedPost?.id === post.id) {
        setSelectedPost(updated);
      }
      await fetchData(siteKey);
      toast.success("Post restaurado a borrador");
    } catch (error) {
      toast.error("Error restoring post");
      toast.error("Error al restaurar post");
    }
  };

  const handleSavePost = async () => {
    if (!token || !selectedPost || !canEdit) return;
    try {
      const nextSlug = slugify(selectedPost.slug);
      const categoryIds = selectedPost.categories?.map((c) => c.id) || [];
      const tagIds = selectedPost.tags?.map((t) => t.id) || [];
      const updated = await patchCmsPost(
        siteKey,
        selectedPost.slug,
        {
          title: selectedPost.title,
          slug: nextSlug,
          excerpt: selectedPost.excerpt,
          content: selectedPost.content,
          featured_image_url: selectedPost.featured_image_url,
          seo_json: selectedPost.seo_json,
          category_ids: categoryIds,
          tag_ids: tagIds,
        },
        token
      );
      setSelectedPost(updated);
      await fetchData(siteKey);
      toast.success("Post actualizado");
    } catch (error) {
      toast.error("Error updating post");
      toast.error("Error al actualizar post");
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const openPost = (post: CmsPostWithTaxonomies) => {
    setSelectedPost(post);
  };

  const renderBoard = () => (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 min-h-full">
      {groupedPosts.map((column) => {
        const st = STATUS_CONFIG[column.status] ?? STATUS_CONFIG["draft"];
        return (
          <section key={column.status} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-4">
            <div className="flex items-center justify-between mb-4">
              <span className={clsx("px-2.5 py-1 rounded-full text-[9px] font-semibold uppercase tracking-wide", st.color)}>{st.label}</span>
              <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))]">{column.posts.length}</span>
            </div>
            <div className="space-y-3">
              {column.posts.map((post) => (
                <button
                  key={post.id}
                  onClick={() => openPost(post)}
                  className="w-full text-left bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4 hover:border-blue-400 hover:shadow-lg transition-all"
                >
                  <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white truncate">{post.title}</p>
                  <p className="text-[10px] font-mono text-[hsl(var(--text-secondary))] mt-2 truncate">/{post.slug}</p>
                  {post.categories && post.categories.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {post.categories.map((cat) => (
                        <span key={cat.id} className="px-1.5 py-0.5 rounded text-[9px] bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300">
                          {cat.name}
                        </span>
                      ))}
                    </div>
                  )}
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
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] truncate">
            Posts / Blog
          </h2>
          <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full shrink-0">
            {visiblePosts.length}
          </span>
        </div>

        <select
          value={siteKey}
          onChange={(e) => setSiteKey(e.target.value)}
          className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-1.5 text-[12px] shrink-0"
        >
          {sites.length === 0 && <option value={SITE_KEY}>{SITE_KEY}</option>}
          {sites.map((site) => (
            <option key={site.site_key} value={site.site_key}>
              {site.name} ({site.site_key})
            </option>
          ))}
        </select>

        <div className="relative shrink-0">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
          <input
            type="text"
            placeholder="Buscar posts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 border-none rounded-lg text-[12px] focus:ring-2 focus:ring-blue-500/20 w-52 transition-all"
          />
        </div>

        <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={CMS_POST_VIEWS} />

        <button
          onClick={() => setIsQuickAddOpen((prev) => !prev)}
          disabled={!canEdit}
          className="bg-[hsl(var(--primary))] text-white px-4 py-1.5 rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50 shrink-0"
        >
          <Plus size={14} /> Nuevo post
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
            <form onSubmit={handleCreatePost} className="px-3 py-1.5 flex items-center gap-4">
              <div className="size-8 rounded-lg bg-[hsl(var(--primary))] text-white flex items-center justify-center shrink-0">
                <Zap size={16} />
              </div>
              <input
                autoFocus
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Escape" && setIsQuickAddOpen(false)}
                placeholder="Título del nuevo post (Enter para crear)"
                disabled={!canEdit}
                className="flex-1 bg-transparent border-none text-sm font-bold text-blue-900 dark:text-blue-200 placeholder:text-[hsl(var(--primary))] focus:ring-0"
              />
              <button type="submit" disabled={!canEdit} className="bg-[hsl(var(--primary))] text-white px-3 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50">
                Guardar
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-3">
        {loading ? (
          <div className="space-y-4">{[1, 2, 3].map((i) => <div key={i} className="h-20 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg animate-pulse" />)}</div>
        ) : visiblePosts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50 py-1.5">
            <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]"><FileText size={32} /></div>
            <div>
              <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white">No hay posts creados</p>
              <p className="text-sm text-[hsl(var(--text-secondary))]">Usa la barra superior para crear tu primer post.</p>
            </div>
          </div>
        ) : viewType === "grid" ? (
          <div className="grid grid-cols-1 gap-3">
            {visiblePosts.map((post, index) => {
              const st = STATUS_CONFIG[post.status] ?? STATUS_CONFIG["draft"];
              return (
                <motion.div
                  key={post.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04 }}
                  className="group bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 p-4 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all duration-200 flex items-center gap-4"
                >
                  <button
                    onClick={() => toggleSelect(post.id)}
                    className={clsx(
                      "size-5 rounded-lg border-2 flex items-center justify-center shrink-0 transition-all",
                      selectedIds.has(post.id) ? "bg-[hsl(var(--primary))] border-blue-600" : "border-[hsl(var(--border))] dark:border-white/20 hover:border-blue-400"
                    )}
                  >
                    {selectedIds.has(post.id) && <Check size={11} className="text-white" strokeWidth={3} />}
                  </button>

                  <div
                    onClick={() => openPost(post)}
                    className="size-7 rounded-md bg-fuchsia-50 dark:bg-fuchsia-500/10 text-fuchsia-600 flex items-center justify-center shrink-0 cursor-pointer"
                  >
                    <FileText size={20} />
                  </div>

                  <div className="flex-1 min-w-0 cursor-pointer" onClick={() => openPost(post)}>
                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{post.title}</h3>
                      <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide", st.color)}>{st.label}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1 text-[11px] text-[hsl(var(--text-secondary))]"><Globe size={11} /><span>/{post.slug}</span></div>
                      {post.updated_at && <>
                        <div className="size-1 bg-[hsl(var(--surface-3))] dark:bg-white/10 rounded-full" />
                        <div className="flex items-center gap-1 text-[11px] text-[hsl(var(--text-secondary))]"><Calendar size={11} /><span>{new Date(post.updated_at).toLocaleDateString()}</span></div>
                      </>}
                      {post.categories && post.categories.length > 0 && <>
                        <div className="size-1 bg-[hsl(var(--surface-3))] dark:bg-white/10 rounded-full" />
                        <div className="flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-400">
                          <FolderOpen size={11} />
                          {post.categories.map((c) => c.name).join(", ")}
                        </div>
                      </>}
                      {post.tags && post.tags.length > 0 && <>
                        <div className="size-1 bg-[hsl(var(--surface-3))] dark:bg-white/10 rounded-full" />
                        <div className="flex items-center gap-1 text-[11px] text-fuchsia-600 dark:text-fuchsia-400">
                          <Tag size={11} />
                          {post.tags.map((t) => t.name).join(", ")}
                        </div>
                      </>}
                    </div>
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {post.status === "archived" ? (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleRestorePost(post); }}
                        disabled={!canEdit}
                        className="p-2 hover:bg-emerald-50 dark:hover:bg-emerald-500/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-emerald-600 transition-all disabled:opacity-50"
                        title="Restaurar a borrador"
                      >
                        <RotateCcw size={15} />
                      </button>
                    ) : (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleArchivePost(post); }}
                        disabled={!canEdit}
                        className="p-2 hover:bg-amber-50 dark:hover:bg-amber-500/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-amber-600 transition-all disabled:opacity-50"
                        title="Archivar post"
                      >
                        <Archive size={15} />
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        ) : viewType === "board" || viewType === "kanban" ? (
          renderBoard()
        ) : viewType === "table" ? (
          <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto">
            <table className="w-full min-w-[480px] text-left">
              <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                <tr>
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === visiblePosts.length && visiblePosts.length > 0}
                      onChange={(e) => setSelectedIds(e.target.checked ? new Set(visiblePosts.map((p) => p.id)) : new Set())}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Post</th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">Slug</th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden lg:table-cell">Estado</th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden xl:table-cell">Categorías</th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                {visiblePosts.map((post) => {
                  const st = STATUS_CONFIG[post.status] ?? STATUS_CONFIG["draft"];
                  return (
                    <tr key={post.id} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] group transition-colors">
                      <td className="px-4 py-3">
                        <input type="checkbox" checked={selectedIds.has(post.id)} onChange={() => toggleSelect(post.id)} className="rounded" />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="size-8 rounded-md bg-fuchsia-50 dark:bg-fuchsia-900/20 text-fuchsia-600 flex items-center justify-center shrink-0">
                            <FileText size={14} />
                          </div>
                          <span className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate max-w-[200px]">{post.title}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className="text-[11px] font-mono text-[hsl(var(--text-secondary))]">/{post.slug}</span>
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell">
                        <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide", st.color)}>{st.label}</span>
                      </td>
                      <td className="px-4 py-3 hidden xl:table-cell">
                        <span className="text-[11px] text-[hsl(var(--text-secondary))]">
                          {post.categories?.map((c) => c.name).join(", ") || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => openPost(post)}
                            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] text-[9px] font-semibold uppercase hover:bg-blue-100 transition-all"
                          >
                            <PenTool size={10} /> Editar
                          </button>
                          <button
                            onClick={() => post.status === "archived" ? handleRestorePost(post) : handleArchivePost(post)}
                            disabled={!canEdit}
                            className={clsx(
                              "p-1.5 rounded-lg transition-all opacity-0 group-hover:opacity-100 disabled:opacity-40",
                              post.status === "archived"
                                ? "hover:bg-emerald-50 dark:hover:bg-emerald-500/10 text-[hsl(var(--text-secondary))] hover:text-emerald-600"
                                : "hover:bg-amber-50 dark:hover:bg-amber-500/10 text-[hsl(var(--text-secondary))] hover:text-amber-600"
                            )}
                          >
                            {post.status === "archived" ? <RotateCcw size={13} /> : <Archive size={13} />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="space-y-3 w-full">
            {visiblePosts.map((post, index) => {
              const st = STATUS_CONFIG[post.status] ?? STATUS_CONFIG["draft"];
              return (
                <motion.div
                  key={post.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.025 }}
                  onClick={() => openPost(post)}
                  className="group bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 p-4 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all cursor-pointer flex items-center gap-4"
                >
                  <div className="size-6 rounded-md bg-fuchsia-50 dark:bg-fuchsia-500/10 text-fuchsia-600 flex items-center justify-center shrink-0 group-hover:bg-fuchsia-600 group-hover:text-white transition-all">
                    <FileText size={18} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{post.title}</h3>
                      <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide", st.color)}>{st.label}</span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-[hsl(var(--text-secondary))]">
                      <span className="flex items-center gap-1"><Globe size={11} />/{post.slug}</span>
                      <span className="flex items-center gap-1"><Calendar size={11} />{post.updated_at ? new Date(post.updated_at).toLocaleDateString() : "Sin fecha"}</span>
                      {post.categories && post.categories.length > 0 && (
                        <span className="flex items-center gap-1"><FolderOpen size={11} />{post.categories.map((c) => c.name).join(", ")}</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); openPost(post); }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] text-[9px] font-semibold uppercase tracking-wide hover:bg-blue-100 transition-all"
                  >
                    <PenTool size={11} /> Editar
                  </button>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Edit Post SidePanel */}
      <SidePanel
        isOpen={!!selectedPost}
        onClose={() => setSelectedPost(null)}
        title={selectedPost?.title || ""}
        subtitle={selectedPost ? `Slug: /${selectedPost.slug}` : undefined}
      >
        {selectedPost && (
          <div className="space-y-4">
            <section className="space-y-3">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Información básica
              </label>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Título</span>
                  <input
                    type="text"
                    value={selectedPost.title}
                    onChange={(e) => setSelectedPost({ ...selectedPost, title: e.target.value })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                  />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Slug</span>
                  <input
                    type="text"
                    value={selectedPost.slug}
                    onChange={(e) => setSelectedPost({ ...selectedPost, slug: e.target.value })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                  />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Extracto</span>
                  <textarea
                    rows={3}
                    value={selectedPost.excerpt || ""}
                    onChange={(e) => setSelectedPost({ ...selectedPost, excerpt: e.target.value })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md resize-none custom-scrollbar"
                    disabled={!canEdit}
                    placeholder="Breve resumen del post..."
                  />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Contenido</span>
                  <textarea
                    rows={8}
                    value={selectedPost.content || ""}
                    onChange={(e) => setSelectedPost({ ...selectedPost, content: e.target.value })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md resize-none custom-scrollbar font-mono"
                    disabled={!canEdit}
                    placeholder="Contenido del post (puede ser Markdown o HTML)..."
                  />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Imagen destacada (URL)</span>
                  <input
                    type="url"
                    value={selectedPost.featured_image_url || ""}
                    onChange={(e) => setSelectedPost({ ...selectedPost, featured_image_url: e.target.value })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                    placeholder="https://..."
                  />
                </div>
              </div>
            </section>

            <section className="space-y-3">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Taxonomías
              </label>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Categorías</span>
                  <div className="flex flex-wrap gap-2">
                    {categories.map((cat) => {
                      const isSelected = selectedPost.categories?.some((c) => c.id === cat.id);
                      return (
                        <button
                          key={cat.id}
                          onClick={() => {
                            if (!canEdit) return;
                            const current = selectedPost.categories || [];
                            const next = isSelected
                              ? current.filter((c) => c.id !== cat.id)
                              : [...current, cat];
                            setSelectedPost({ ...selectedPost, categories: next });
                          }}
                          disabled={!canEdit}
                          className={clsx(
                            "px-3 py-1.5 rounded-md text-[11px] font-medium transition-all disabled:opacity-50",
                            isSelected
                              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30"
                              : "bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/10 hover:border-emerald-300"
                          )}
                        >
                          {cat.name}
                        </button>
                      );
                    })}
                  </div>
                  {categories.length === 0 && (
                    <p className="text-[11px] text-[hsl(var(--text-secondary))]">No hay categorías. Crea algunas primero en /cms/categories.</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Etiquetas</span>
                  <div className="flex flex-wrap gap-2">
                    {tags.map((tag) => {
                      const isSelected = selectedPost.tags?.some((t) => t.id === tag.id);
                      return (
                        <button
                          key={tag.id}
                          onClick={() => {
                            if (!canEdit) return;
                            const current = selectedPost.tags || [];
                            const next = isSelected
                              ? current.filter((t) => t.id !== tag.id)
                              : [...current, tag];
                            setSelectedPost({ ...selectedPost, tags: next });
                          }}
                          disabled={!canEdit}
                          className={clsx(
                            "px-3 py-1.5 rounded-md text-[11px] font-medium transition-all disabled:opacity-50",
                            isSelected
                              ? "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/20 dark:text-fuchsia-300 border border-fuchsia-200 dark:border-fuchsia-500/30"
                              : "bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/10 hover:border-fuchsia-300"
                          )}
                        >
                          {tag.name}
                        </button>
                      );
                    })}
                  </div>
                  {tags.length === 0 && (
                    <p className="text-[11px] text-[hsl(var(--text-secondary))]">No hay etiquetas. Crea algunas primero en /cms/tags.</p>
                  )}
                </div>
              </div>
            </section>

            <section className="space-y-3">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                SEO
              </label>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Meta descripción</span>
                  <textarea
                    rows={2}
                    value={(selectedPost.seo_json?.meta_description as string) || ""}
                    onChange={(e) => setSelectedPost({ ...selectedPost, seo_json: { ...(selectedPost.seo_json || {}), meta_description: e.target.value } })}
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#252528] border border-[hsl(var(--border))] dark:border-white/10 rounded-md resize-none custom-scrollbar"
                    disabled={!canEdit}
                    placeholder="Breve descripción para Google..."
                  />
                </div>
              </div>
            </section>

            <div className="pt-6 border-t border-[hsl(var(--border))] dark:border-white/5">
              <button onClick={handleSavePost} disabled={!canEdit} className="w-full bg-[hsl(var(--primary))] text-white py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-50">
                Guardar cambios
              </button>
              {selectedPost.status === "archived" ? (
                <button
                  onClick={() => handleRestorePost(selectedPost)}
                  disabled={!canEdit}
                  className="mt-3 w-full border border-emerald-200 text-emerald-700 dark:text-emerald-300 py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-emerald-50 dark:hover:bg-emerald-500/10 active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <RotateCcw size={14} /> Restaurar a borrador
                </button>
              ) : (
                <button
                  onClick={() => handleArchivePost(selectedPost)}
                  disabled={!canEdit}
                  className="mt-3 w-full border border-amber-200 text-amber-700 dark:text-amber-300 py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-amber-50 dark:hover:bg-amber-500/10 active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <Archive size={14} /> Archivar post
                </button>
              )}
            </div>
          </div>
        )}
      </SidePanel>

      {/* Confirm Archive SidePanel */}
      <SidePanel
        isOpen={!!pendingArchivePost}
        onClose={() => setPendingArchivePost(null)}
        title="Archivar post"
        subtitle={pendingArchivePost ? `/${pendingArchivePost.slug}` : undefined}
      >
        {pendingArchivePost && (
          <div className="space-y-4">
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
              <p className="text-sm font-semibold">{pendingArchivePost.title}</p>
              <p className="mt-2 text-xs leading-5 text-amber-800 dark:text-amber-200">
                El post quedará archivado y podrás restaurarlo después.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPendingArchivePost(null)}
                className="flex-1 rounded-md border border-[hsl(var(--border))] px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--surface-1))] dark:border-white/10 dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5"
              >
                Cancelar
              </button>
              <button
                onClick={confirmArchivePost}
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

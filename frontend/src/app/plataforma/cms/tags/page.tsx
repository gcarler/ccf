"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  Archive,
  Tag,
  Globe,
  Plus,
  RotateCcw,
  Search,
  Zap,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import SidePanel from "@/components/ui/SidePanel";
import clsx from "clsx";
import {
  createCmsTag,
  deleteCmsTag,
  listCmsSites,
  listCmsTags,
  patchCmsTag,
} from "@/lib/cms/v2";
import { CmsSite, CmsTag } from "@/types/cms-v2";
import { canEditCms } from "@/lib/cms/permissions";

function slugify(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9\-_]/g, "")
    .replace(/-+/g, "-");
}

export default function CmsTagsManagement() {
  const { token, user } = useAuth();
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [tags, setTags] = useState<CmsTag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [selectedTag, setSelectedTag] = useState<CmsTag | null>(null);
  const canEdit = canEditCms(user?.role);

  const fetchData = useCallback(async (targetSite: string) => {
    if (!token) {
      setLoading(false);
      setTags([]);
      setError("Debes iniciar sesión para gestionar etiquetas.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [nextSites, nextTags] = await Promise.all([
        listCmsSites(token),
        listCmsTags(targetSite, token),
      ]);
      setSites(nextSites || []);
      setTags(nextTags || []);
    } catch (error) {
      toast.error("Error al cargar etiquetas");
      setTags([]);
      setError("No se pudieron cargar las etiquetas.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData(siteKey);
  }, [fetchData, siteKey]);

  const visibleTags = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return tags;
    return tags.filter(
      (tag) =>
        tag.name.toLowerCase().includes(term) ||
        tag.slug.toLowerCase().includes(term)
    );
  }, [tags, search]);

  const handleCreate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmedName = newName.trim();
    if (!trimmedName) return;
    if (!token) {
      setError("Debes iniciar sesión para crear etiquetas.");
      return;
    }
    if (!canEdit) return;
    const slug = slugify(trimmedName);
    if (!slug) {
      toast.error("El nombre no produce un slug válido");
      return;
    }
    try {
      await createCmsTag(siteKey, { name: trimmedName, slug }, token);
      toast.success(`Etiqueta "${trimmedName}" creada`);
      setNewName("");
      setIsQuickAddOpen(false);
      await fetchData(siteKey);
    } catch (error) {
      toast.error("Error al crear etiqueta. El slug puede estar en uso.");
    }
  };

  const handleArchive = async (tag: CmsTag) => {
    if (!token || !canEdit) return;
    try {
      await deleteCmsTag(siteKey, tag.slug, token);
      toast.success("Etiqueta archivada");
      await fetchData(siteKey);
    } catch (error) {
      toast.error("Error al archivar etiqueta");
    }
  };

  const handleRestore = async (tag: CmsTag) => {
    if (!token || !canEdit) return;
    try {
      await patchCmsTag(siteKey, tag.slug, { is_active: true }, token);
      toast.success("Etiqueta restaurada");
      await fetchData(siteKey);
    } catch (error) {
      toast.error("Error al restaurar etiqueta");
    }
  };

  const handleSave = async () => {
    if (!token || !selectedTag || !canEdit) return;
    try {
      const nextSlug = slugify(selectedTag.slug);
      await patchCmsTag(
        siteKey,
        selectedTag.slug,
        {
          name: selectedTag.name,
          slug: nextSlug,
        },
        token
      );
      toast.success("Etiqueta actualizada");
      setSelectedTag(null);
      await fetchData(siteKey);
    } catch (error) {
      toast.error("Error al actualizar etiqueta");
    }
  };

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))]">
      <header className="h-8 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-3 gap-3 shrink-0">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Tag size={16} className="text-[hsl(var(--primary))] shrink-0" />
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] truncate">
            Etiquetas
          </h2>
          <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full shrink-0">
            {visibleTags.length}
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
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
          />
          <input
            type="text"
            placeholder="Buscar..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 border-none rounded-lg text-[12px] focus:ring-2 focus:ring-blue-500/20 w-52 transition-all"
          />
        </div>

        <button
          onClick={() => setIsQuickAddOpen((prev) => !prev)}
          disabled={!canEdit}
          className="bg-[hsl(var(--primary))] text-white px-4 py-1.5 rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50 shrink-0"
        >
          <Plus size={14} /> Nueva etiqueta
        </button>
      </header>

      {error && (
        <div className="mx-3 mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
          <p className="text-[11px] font-bold uppercase tracking-wide">{error}</p>
        </div>
      )}

      {isQuickAddOpen && (
        <div className="bg-blue-50 dark:bg-blue-900/10 border-b-2 border-blue-300 dark:border-blue-500/30 overflow-hidden shrink-0">
          <form onSubmit={handleCreate} className="px-3 py-1.5 flex items-center gap-4">
            <div className="size-8 rounded-lg bg-[hsl(var(--primary))] text-white flex items-center justify-center shrink-0">
              <Zap size={16} />
            </div>
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setIsQuickAddOpen(false)}
              placeholder="Nombre de la etiqueta (Enter para crear)"
              disabled={!canEdit}
              className="flex-1 bg-transparent border-none text-sm font-bold text-blue-900 dark:text-blue-200 placeholder:text-[hsl(var(--primary))] focus:ring-0"
            />
            <button
              type="submit"
              disabled={!canEdit}
              className="bg-[hsl(var(--primary))] text-white px-3 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50"
            >
              Guardar
            </button>
          </form>
        </div>
      )}

      <div className="flex-1 overflow-y-auto custom-scrollbar p-3">
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-20 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg animate-pulse"
              />
            ))}
          </div>
        ) : visibleTags.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50 py-1.5">
            <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]">
              <Tag size={32} />
            </div>
            <div>
              <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white">
                Sin etiquetas
              </p>
              <p className="text-sm text-[hsl(var(--text-secondary))]">
                Crea tu primera etiqueta para organizar posts.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-3">
            {visibleTags.map((tag, index) => {
              const isArchived = !tag.is_active;
              return (
                <motion.div
                  key={tag.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04 }}
                  className={clsx(
                    "group bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-lg border px-4 py-3 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all duration-200 flex items-center gap-3",
                    isArchived
                      ? "border-dashed border-[hsl(var(--border))] dark:border-white/10 opacity-60"
                      : "border-[hsl(var(--border))]/70 dark:border-white/5"
                  )}
                >
                  <div
                    onClick={() => setSelectedTag(tag)}
                    className="size-6 rounded-md bg-fuchsia-50 dark:bg-fuchsia-500/10 text-fuchsia-600 flex items-center justify-center shrink-0 cursor-pointer"
                  >
                    <Tag size={14} />
                  </div>

                  <div
                    className="cursor-pointer"
                    onClick={() => setSelectedTag(tag)}
                  >
                    <div className="flex items-center gap-2">
                      <h3 className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-white">
                        {tag.name}
                      </h3>
                      {isArchived && (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
                          Archivada
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1 text-[11px] text-[hsl(var(--text-secondary))]">
                      <Globe size={11} />/{tag.slug}
                    </div>
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
                    {isArchived ? (
                      <button
                        onClick={() => handleRestore(tag)}
                        disabled={!canEdit}
                        className="p-2 hover:bg-emerald-50 dark:hover:bg-emerald-500/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-emerald-600 transition-all disabled:opacity-50"
                        title="Restaurar"
                      >
                        <RotateCcw size={15} />
                      </button>
                    ) : (
                      <button
                        onClick={() => handleArchive(tag)}
                        disabled={!canEdit}
                        className="p-2 hover:bg-amber-50 dark:hover:bg-amber-500/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-amber-600 transition-all disabled:opacity-50"
                        title="Archivar"
                      >
                        <Archive size={15} />
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      <SidePanel
        isOpen={!!selectedTag}
        onClose={() => setSelectedTag(null)}
        title={selectedTag?.name || ""}
        subtitle={selectedTag ? `Slug: /${selectedTag.slug}` : undefined}
      >
        {selectedTag && (
          <div className="space-y-3">
            <section className="space-y-3">
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Configuración
              </label>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                    Nombre
                  </span>
                  <input
                    type="text"
                    value={selectedTag.name}
                    onChange={(e) =>
                      setSelectedTag({ ...selectedTag, name: e.target.value })
                    }
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                  />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                    Slug
                  </span>
                  <input
                    type="text"
                    value={selectedTag.slug}
                    onChange={(e) =>
                      setSelectedTag({ ...selectedTag, slug: e.target.value })
                    }
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                  />
                </div>
              </div>
            </section>

            <div className="pt-6 border-t border-[hsl(var(--border))] dark:border-white/5">
              <button
                onClick={handleSave}
                disabled={!canEdit}
                className="w-full bg-[hsl(var(--primary))] text-white py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-50"
              >
                Guardar cambios
              </button>
              {!selectedTag.is_active ? (
                <button
                  onClick={() => handleRestore(selectedTag)}
                  disabled={!canEdit}
                  className="mt-3 w-full border border-emerald-200 text-emerald-700 dark:text-emerald-300 py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-emerald-50 dark:hover:bg-emerald-500/10 active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <RotateCcw size={14} /> Restaurar
                </button>
              ) : (
                <button
                  onClick={() => handleArchive(selectedTag)}
                  disabled={!canEdit}
                  className="mt-3 w-full border border-amber-200 text-amber-700 dark:text-amber-300 py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-amber-50 dark:hover:bg-amber-500/10 active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <Archive size={14} /> Archivar
                </button>
              )}
            </div>
          </div>
        )}
      </SidePanel>
    </div>
  );
}

"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  Archive,
  FolderOpen,
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
  createCmsCategory,
  deleteCmsCategory,
  listCmsCategories,
  listCmsSites,
  patchCmsCategory,
} from "@/lib/cms/v2";
import { CmsCategory, CmsSite } from "@/types/cms-v2";
import { canEditCms } from "@/lib/cms/permissions";

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/\s+/g, "-").replace(/[^a-z0-9\-_]/g, "").replace(/-+/g, "-");
}

export default function CmsCategoriesManagement() {
  const { token, user } = useAuth();
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [categories, setCategories] = useState<CmsCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<CmsCategory | null>(null);
  const canEdit = canEditCms(user?.role);

  const fetchData = useCallback(async (targetSite: string) => {
    if (!token) {
      setLoading(false);
      setCategories([]);
      setError("Debes iniciar sesión para gestionar categorías.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [nextSites, nextCategories] = await Promise.all([
        listCmsSites(token),
        listCmsCategories(targetSite, token),
      ]);
      setSites(nextSites || []);
      setCategories(nextCategories || []);
    } catch (error) {
      toast.error("Error al cargar categorías");
      setCategories([]);
      setError("No se pudieron cargar las categorías.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData(siteKey);
  }, [fetchData, siteKey]);

  const visibleCategories = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return categories;
    return categories.filter(
      (cat) =>
        cat.name.toLowerCase().includes(term) ||
        cat.slug.toLowerCase().includes(term)
    );
  }, [categories, search]);

  const handleCreate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmedName = newName.trim();
    if (!trimmedName) return;
    if (!token) {
      setError("Debes iniciar sesión para crear categorías.");
      return;
    }
    if (!canEdit) return;
    const slug = slugify(trimmedName);
    if (!slug) {
      toast.error("El nombre no produce un slug válido");
      return;
    }
    try {
      await createCmsCategory(siteKey, { name: trimmedName, slug }, token);
      toast.success(`Categoría "${trimmedName}" creada`);
      setNewName("");
      setIsQuickAddOpen(false);
      await fetchData(siteKey);
    } catch (error) {
      toast.error("Error al crear categoría. El slug puede estar en uso.");
    }
  };

  const handleArchive = async (cat: CmsCategory) => {
    if (!token || !canEdit) return;
    try {
      await deleteCmsCategory(siteKey, cat.slug, token);
      toast.success("Categoría archivada");
      await fetchData(siteKey);
    } catch (error) {
      toast.error("Error al archivar categoría");
    }
  };

  const handleRestore = async (cat: CmsCategory) => {
    if (!token || !canEdit) return;
    try {
      await patchCmsCategory(siteKey, cat.slug, { is_active: true }, token);
      toast.success("Categoría restaurada");
      await fetchData(siteKey);
    } catch (error) {
      toast.error("Error al restaurar categoría");
    }
  };

  const handleSave = async () => {
    if (!token || !selectedCategory || !canEdit) return;
    try {
      const nextSlug = slugify(selectedCategory.slug);
      await patchCmsCategory(
        siteKey,
        selectedCategory.slug,
        {
          name: selectedCategory.name,
          slug: nextSlug,
          description: selectedCategory.description,
          parent_id: selectedCategory.parent_id,
        },
        token,
      );
      toast.success("Categoría actualizada");
      setSelectedCategory(null);
      await fetchData(siteKey);
    } catch (error) {
      toast.error("Error al actualizar categoría");
    }
  };

  const parentOptions = useMemo(() => {
    return categories.filter((c) => !selectedCategory || c.id !== selectedCategory.id);
  }, [categories, selectedCategory]);

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))]">
      <header className="h-8 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center px-3 gap-3 shrink-0">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <FolderOpen size={16} className="text-[hsl(var(--primary))] shrink-0" />
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] truncate">
            Categorías
          </h2>
          <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-0.5 rounded-full shrink-0">
            {visibleCategories.length}
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
            placeholder="Buscar..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 border-none rounded-lg text-[12px] focus:ring-2 focus:ring-[hsl(var(--primary))]/20 w-52 transition-all"
          />
        </div>

        <button
          onClick={() => setIsQuickAddOpen((prev) => !prev)}
          disabled={!canEdit}
          className="bg-[hsl(var(--primary))] text-white px-4 py-1.5 rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50 shrink-0"
        >
          <Plus size={14} /> Nueva categoría
        </button>
      </header>

      {error && (
        <div className="mx-3 mt-3 rounded-md border border-[hsl(var(--warning)/25%)] bg-warning-soft p-3 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
          <p className="text-[11px] font-bold uppercase tracking-wide">{error}</p>
        </div>
      )}

      {isQuickAddOpen && (
        <div className="bg-info-soft dark:bg-[hsl(var(--info))]/10 border-b-2 border-[hsl(var(--info)/30%)] dark:border-[hsl(var(--info)/100%)]/30 overflow-hidden shrink-0">
          <form onSubmit={handleCreate} className="px-3 py-1.5 flex items-center gap-4">
            <div className="size-8 rounded-lg bg-[hsl(var(--primary))] text-white flex items-center justify-center shrink-0">
              <Zap size={16} />
            </div>
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setIsQuickAddOpen(false)}
              placeholder="Nombre de la categoría (Enter para crear)"
              disabled={!canEdit}
              className="flex-1 bg-transparent border-none text-sm font-bold text-info-text dark:text-[hsl(var(--info))] placeholder:text-[hsl(var(--primary))] focus:ring-0"
            />
            <button type="submit" disabled={!canEdit} className="bg-[hsl(var(--primary))] text-white px-3 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50">
              Guardar
            </button>
          </form>
        </div>
      )}

      <div className="flex-1 overflow-y-auto custom-scrollbar p-3">
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : visibleCategories.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50 py-1.5">
            <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]">
              <FolderOpen size={32} />
            </div>
            <div>
              <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white">Sin categorías</p>
              <p className="text-sm text-[hsl(var(--text-secondary))]">Crea tu primera categoría para organizar posts.</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {visibleCategories.map((cat, index) => {
              const isArchived = !cat.is_active;
              return (
                <motion.div
                  key={cat.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04 }}
                  className={clsx(
                    "group bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-lg border p-4 shadow-sm hover:shadow-xl hover:border-[hsl(var(--info)/100%)]/30 transition-all duration-200 flex items-center gap-4",
                    isArchived
                      ? "border-dashed border-[hsl(var(--border))] dark:border-white/10 opacity-60"
                      : "border-[hsl(var(--border))]/70 dark:border-white/5"
                  )}
                >
                  <div
                    onClick={() => setSelectedCategory(cat)}
                    className="size-7 rounded-md bg-success-soft dark:bg-[hsl(var(--success))]/10 text-success-text flex items-center justify-center shrink-0 cursor-pointer"
                  >
                    <FolderOpen size={18} />
                  </div>

                  <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setSelectedCategory(cat)}>
                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">
                        {cat.name}
                      </h3>
                      {isArchived && (
                        <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide bg-[hsl(var(--warning-muted))] text-warning-text dark:bg-[hsl(var(--warning))]/20 dark:text-[hsl(var(--warning))]">
                          Archivada
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1 text-[11px] text-[hsl(var(--text-secondary))]">
                        <Globe size={11} />/{cat.slug}
                      </div>
                      {cat.description && (
                        <>
                          <div className="size-1 bg-[hsl(var(--surface-3))] dark:bg-white/10 rounded-full" />
                          <div className="text-[11px] text-[hsl(var(--text-secondary))] truncate max-w-xs">
                            {cat.description}
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {isArchived ? (
                      <button
                        onClick={() => handleRestore(cat)}
                        disabled={!canEdit}
                        className="p-2 hover:bg-success-soft dark:hover:bg-[hsl(var(--success))]/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-success-text transition-all disabled:opacity-50"
                        title="Restaurar"
                      >
                        <RotateCcw size={15} />
                      </button>
                    ) : (
                      <button
                        onClick={() => handleArchive(cat)}
                        disabled={!canEdit}
                        className="p-2 hover:bg-warning-soft dark:hover:bg-[hsl(var(--warning))]/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-warning-text transition-all disabled:opacity-50"
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
        isOpen={!!selectedCategory}
        onClose={() => setSelectedCategory(null)}
        title={selectedCategory?.name || ""}
        subtitle={selectedCategory ? `Slug: /${selectedCategory.slug}` : undefined}
      >
        {selectedCategory && (
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
                    value={selectedCategory.name}
                    onChange={(e) =>
                      setSelectedCategory({ ...selectedCategory, name: e.target.value })
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
                    value={selectedCategory.slug}
                    onChange={(e) =>
                      setSelectedCategory({ ...selectedCategory, slug: e.target.value })
                    }
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                  />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                    Descripción
                  </span>
                  <textarea
                    rows={3}
                    value={selectedCategory.description || ""}
                    onChange={(e) =>
                      setSelectedCategory({ ...selectedCategory, description: e.target.value })
                    }
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md resize-none custom-scrollbar"
                    disabled={!canEdit}
                  />
                </div>
                <div className="space-y-1.5">
                  <span className="text-[12px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                    Categoría padre
                  </span>
                  <select
                    value={selectedCategory.parent_id || ""}
                    onChange={(e) =>
                      setSelectedCategory({
                        ...selectedCategory,
                        parent_id: e.target.value || null,
                      })
                    }
                    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md"
                    disabled={!canEdit}
                  >
                    <option value="">Sin padre (raíz)</option>
                    {parentOptions.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </section>

            <div className="pt-6 border-t border-[hsl(var(--border))] dark:border-white/5">
              <button
                onClick={handleSave}
                disabled={!canEdit}
                className="w-full bg-[hsl(var(--primary))] text-white py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-50"
              >
                Guardar cambios
              </button>
              {!selectedCategory.is_active ? (
                <button
                  onClick={() => handleRestore(selectedCategory)}
                  disabled={!canEdit}
                  className="mt-3 w-full border border-[hsl(var(--success)/25%)] text-success-text dark:text-success-text py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-success-soft dark:hover:bg-[hsl(var(--success))]/10 active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <RotateCcw size={14} /> Restaurar
                </button>
              ) : (
                <button
                  onClick={() => handleArchive(selectedCategory)}
                  disabled={!canEdit}
                  className="mt-3 w-full border border-[hsl(var(--warning)/25%)] text-warning-text dark:text-warning-text py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-warning-soft dark:hover:bg-[hsl(var(--warning))]/10 active:scale-95 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
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

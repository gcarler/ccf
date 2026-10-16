"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Tag, Plus, Edit2, Trash2, Check, X, Search, RefreshCw, AlertCircle } from "lucide-react";
import clsx from "clsx";
import { toast } from "sonner";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import { useOptionalProjectUpdate } from "@/context/ProjectUpdateContext";
import RightPanel from "@/components/ui/RightPanel";

export interface ProjectLabelItem {
  name: string;
  task_count: number;
}

export interface ProjectLabelsDrawerProps {
  projectId: string;
  isOpen?: boolean;
  open?: boolean;
  onClose?: () => void;
  embedded?: boolean;
  onUpdated?: () => void;
}

const LABEL_COLORS = [
  { bg: 'bg-[hsl(var(--destructive)/0.15)]', text: 'text-[hsl(var(--destructive))]', border: 'border-[hsl(var(--destructive)/0.3)]', dot: 'bg-[hsl(var(--destructive))]' },
  { bg: 'bg-[hsl(var(--warning)/0.15)]', text: 'text-[hsl(var(--warning))]', border: 'border-[hsl(var(--warning)/0.3)]', dot: 'bg-[hsl(var(--warning))]' },
  { bg: 'bg-[hsl(var(--warning)/0.2)]',  text: 'text-[hsl(var(--warning))]', border: 'border-[hsl(var(--warning)/0.4)]', dot: 'bg-[hsl(var(--warning))]' },
  { bg: 'bg-[hsl(var(--success)/0.15)]', text: 'text-[hsl(var(--success))]', border: 'border-[hsl(var(--success)/0.3)]', dot: 'bg-[hsl(var(--success))]' },
  { bg: 'bg-[hsl(var(--primary)/0.15)]', text: 'text-[hsl(var(--primary))]', border: 'border-[hsl(var(--primary)/0.3)]', dot: 'bg-[hsl(var(--primary))]' },
  { bg: 'bg-[hsl(var(--primary)/0.2)]', text: 'text-[hsl(var(--primary))]', border: 'border-[hsl(var(--primary)/0.4)]', dot: 'bg-[hsl(var(--primary))]' },
  { bg: 'bg-[hsl(var(--domain-pink)/0.2)]', text: 'text-[hsl(var(--domain-pink))]', border: 'border-[hsl(var(--domain-pink)/0.3)]', dot: 'bg-[hsl(var(--domain-pink))]' },
  { bg: 'bg-[hsl(var(--surface-2))]', text: 'text-[hsl(var(--muted-foreground))]', border: 'border-[hsl(var(--border))]', dot: 'bg-[hsl(var(--muted-foreground))]' },
];

export function getLabelColor(label: string) {
  let hash = 0;
  for (let i = 0; i < label.length; i++) hash = label.charCodeAt(i) + ((hash << 5) - hash);
  return LABEL_COLORS[Math.abs(hash) % LABEL_COLORS.length];
}

export function ProjectLabelsDrawer({
  projectId,
  isOpen,
  open,
  onClose,
  embedded = false,
  onUpdated,
}: ProjectLabelsDrawerProps) {
  const { token } = useAuth();
  const projectUpdateContext = useOptionalProjectUpdate();

  const [apiLabels, setApiLabels] = useState<ProjectLabelItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Create state
  const [newLabelName, setNewLabelName] = useState("");
  const [creating, setCreating] = useState(false);

  // Edit / Rename state
  const [editingLabel, setEditingLabel] = useState<string | null>(null);
  const [renameInput, setRenameInput] = useState("");
  const [renaming, setRenaming] = useState(false);

  // Inline Delete confirmation state
  const [deletingLabel, setDeletingLabel] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const localCatalogKey = `projectLabelsCatalog:${projectId}`;

  // Helper to read local catalog
  const getLocalCatalog = useCallback((): string[] => {
    if (typeof window === "undefined") return [];
    try {
      const raw = localStorage.getItem(localCatalogKey);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }, [localCatalogKey]);

  // Helper to persist local catalog
  const saveLocalCatalog = useCallback(
    (labelsList: string[]) => {
      if (typeof window === "undefined") return;
      try {
        localStorage.setItem(localCatalogKey, JSON.stringify(labelsList));
      } catch {
        // Ignore quota/storage errors
      }
    },
    [localCatalogKey]
  );

  // Fetch labels from API
  const fetchLabels = useCallback(async () => {
    if (!projectId || !token) return;
    try {
      setLoading(true);
      const data = await apiFetch<ProjectLabelItem[]>(`/projects/${projectId}/labels`, {
        token,
      });
      if (Array.isArray(data)) {
        setApiLabels(data);
      }
    } catch (err) {
      console.error("Error fetching project labels:", err);
    } finally {
      setLoading(false);
    }
  }, [projectId, token]);

  useEffect(() => {
    fetchLabels();
  }, [fetchLabels]);

  // Combine labels from:
  // 1) API response
  // 2) Context tasks (if any active tasks have labels not yet in API)
  // 3) localStorage catalog (user-created tags not yet assigned to any task)
  const mergedLabels = useMemo(() => {
    const countsMap = new Map<string, number>();

    // Seed from API
    for (const item of apiLabels) {
      if (item && item.name) {
        countsMap.set(item.name.trim(), item.task_count);
      }
    }

    // Check context tasks
    if (projectUpdateContext?.tasks) {
      for (const t of projectUpdateContext.tasks) {
        if (!t.deleted_at && Array.isArray(t.labels)) {
          for (const raw of t.labels) {
            const name = raw?.trim();
            if (name) {
              if (!countsMap.has(name)) {
                countsMap.set(name, 1);
              }
            }
          }
        }
      }
    }

    // Merge local catalog (task_count = 0 if not present)
    const local = getLocalCatalog();
    for (const name of local) {
      const trimmed = name?.trim();
      if (trimmed && !countsMap.has(trimmed)) {
        countsMap.set(trimmed, 0);
      }
    }

    const result: ProjectLabelItem[] = [];
    countsMap.forEach((task_count, name) => {
      result.push({ name, task_count });
    });

    result.sort((a, b) => a.name.localeCompare(b.name, "es", { sensitivity: "base" }));
    return result;
  }, [apiLabels, projectUpdateContext?.tasks, getLocalCatalog]);

  const filteredLabels = useMemo(() => {
    if (!searchQuery.trim()) return mergedLabels;
    const query = searchQuery.trim().toLowerCase();
    return mergedLabels.filter((l) => l.name.toLowerCase().includes(query));
  }, [mergedLabels, searchQuery]);

  // Create a new label
  const handleCreateLabel = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = newLabelName.trim();
    if (!trimmed) return;

    if (mergedLabels.some((l) => l.name.toLowerCase() === trimmed.toLowerCase())) {
      toast.info(`La etiqueta "${trimmed}" ya existe en el proyecto`);
      return;
    }

    try {
      setCreating(true);
      const currentLocal = getLocalCatalog();
      if (!currentLocal.includes(trimmed)) {
        const nextLocal = [...currentLocal, trimmed];
        saveLocalCatalog(nextLocal);
      }
      setNewLabelName("");
      toast.success(`Etiqueta "${trimmed}" creada`);
      onUpdated?.();
      projectUpdateContext?.reloadProject?.();
    } catch {
      toast.error("Error al registrar la etiqueta");
    } finally {
      setCreating(false);
    }
  };

  // Start inline rename
  const handleStartRename = (name: string) => {
    setEditingLabel(name);
    setRenameInput(name);
    setDeletingLabel(null);
  };

  // Submit rename
  const handleConfirmRename = async (oldName: string) => {
    const trimmedNew = renameInput.trim();
    if (!trimmedNew || trimmedNew === oldName) {
      setEditingLabel(null);
      return;
    }

    if (
      mergedLabels.some(
        (l) => l.name.toLowerCase() === trimmedNew.toLowerCase() && l.name !== oldName
      )
    ) {
      toast.error(`Ya existe una etiqueta con el nombre "${trimmedNew}"`);
      return;
    }

    try {
      setRenaming(true);
      if (token) {
        await apiFetch<ProjectLabelItem[]>(`/projects/${projectId}/labels`, {
          method: "PATCH",
          token,
          body: { old_name: oldName, new_name: trimmedNew },
        });
      }

      // Update local catalog
      const currentLocal = getLocalCatalog();
      const nextLocal = currentLocal.map((l) => (l === oldName ? trimmedNew : l));
      if (!nextLocal.includes(trimmedNew)) nextLocal.push(trimmedNew);
      saveLocalCatalog(nextLocal);

      toast.success(`Etiqueta renombrada a "${trimmedNew}"`);
      setEditingLabel(null);
      await fetchLabels();
      onUpdated?.();
      projectUpdateContext?.reloadProject?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al renombrar la etiqueta";
      toast.error(msg);
    } finally {
      setRenaming(false);
    }
  };

  // Start inline delete
  const handleStartDelete = (name: string) => {
    setDeletingLabel(name);
    setEditingLabel(null);
  };

  // Confirm delete
  const handleConfirmDelete = async (name: string) => {
    try {
      setDeleting(true);
      if (token) {
        await apiFetch<ProjectLabelItem[]>(
          `/projects/${projectId}/labels?name=${encodeURIComponent(name)}`,
          {
            method: "DELETE",
            token,
          }
        );
      }

      // Remove from local catalog
      const currentLocal = getLocalCatalog();
      const nextLocal = currentLocal.filter((l) => l !== name);
      saveLocalCatalog(nextLocal);

      toast.success(`Etiqueta "${name}" eliminada`);
      setDeletingLabel(null);
      await fetchLabels();
      onUpdated?.();
      projectUpdateContext?.reloadProject?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al eliminar la etiqueta";
      toast.error(msg);
    } finally {
      setDeleting(false);
    }
  };

  const isPanelOpen = Boolean(open ?? isOpen);

  const drawerContent = (
    <div className="flex flex-col h-full min-h-0 space-y-5 p-4 sm:p-6 bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))]">
      {/* Header Info */}
      <div className="flex items-center justify-between gap-3 pb-3 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.25)]">
            <Tag size={18} aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-sm font-bold tracking-tight text-[hsl(var(--foreground))]">
              Gestor de Etiquetas
            </h2>
            <p className="text-2xs text-[hsl(var(--muted-foreground))]">
              Organiza, crea, renombra y limpia etiquetas de actividades
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => fetchLabels()}
          disabled={loading}
          aria-label="Actualizar etiquetas"
          title="Actualizar etiquetas"
          className="flex size-8 items-center justify-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-1))] transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={clsx(loading && "animate-spin")} />
        </button>
      </div>

      {/* Creation form */}
      <form onSubmit={handleCreateLabel} className="space-y-1.5">
        <label
          htmlFor="new-label-input"
          className="block text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]"
        >
          Nueva etiqueta
        </label>
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <input
              id="new-label-input"
              type="text"
              value={newLabelName}
              onChange={(e) => setNewLabelName(e.target.value)}
              placeholder="Ej: Urgente, Frontend, Pastoral..."
              maxLength={40}
              className="w-full h-9 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] px-3 text-xs text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] outline-none transition-all focus:border-[hsl(var(--primary))] focus:ring-1 focus:ring-[hsl(var(--primary))]"
            />
          </div>
          <button
            type="submit"
            disabled={!newLabelName.trim() || creating}
            className="flex h-9 shrink-0 items-center gap-1.5 rounded-lg bg-[hsl(var(--primary))] px-3.5 text-xs font-semibold text-[hsl(var(--primary-foreground))] shadow-sm transition-all hover:opacity-90 active:scale-95 disabled:opacity-40 disabled:pointer-events-none"
          >
            <Plus size={14} strokeWidth={2.5} />
            <span>Crear</span>
          </button>
        </div>
      </form>

      {/* Search Bar */}
      {mergedLabels.length > 3 && (
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar entre las etiquetas..."
            className="w-full h-8 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] pl-9 pr-3 text-xs text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] outline-none transition-all focus:border-[hsl(var(--primary))]"
          />
        </div>
      )}

      {/* Labels List */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1">
        <div className="flex items-center justify-between text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] px-1">
          <span>Etiquetas disponibles ({filteredLabels.length})</span>
          <span>Uso en actividades</span>
        </div>

        {loading && mergedLabels.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center text-xs text-[hsl(var(--muted-foreground))] space-y-2">
            <RefreshCw size={20} className="animate-spin text-[hsl(var(--primary))]" />
            <p>Cargando etiquetas del proyecto...</p>
          </div>
        ) : filteredLabels.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 rounded-xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)] p-6 text-center space-y-2">
            <div className="flex size-10 items-center justify-center rounded-full bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]">
              <Tag size={18} />
            </div>
            <p className="text-xs font-medium text-[hsl(var(--foreground))]">
              {searchQuery ? "Sin resultados de búsqueda" : "Aún no hay etiquetas"}
            </p>
            <p className="text-2xs text-[hsl(var(--muted-foreground))] max-w-xs">
              {searchQuery
                ? `No encontramos ninguna etiqueta que coincida con "${searchQuery}".`
                : "Crea tu primera etiqueta con el formulario superior para clasificar actividades."}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[hsl(var(--border))] rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.3)]">
            {filteredLabels.map((item) => {
              const isEditing = editingLabel === item.name;
              const isDeleting = deletingLabel === item.name;
              const color = getLabelColor(item.name);

              return (
                <div
                  key={item.name}
                  className="group flex flex-col gap-2 p-3 transition-colors hover:bg-[hsl(var(--surface-2)/0.6)]"
                >
                  {isEditing ? (
                    /* Inline Rename Form */
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={renameInput}
                        onChange={(e) => setRenameInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleConfirmRename(item.name);
                          if (e.key === "Escape") setEditingLabel(null);
                        }}
                        autoFocus
                        disabled={renaming}
                        className="flex-1 h-8 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--primary))] px-2.5 text-xs text-[hsl(var(--foreground))] outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => handleConfirmRename(item.name)}
                        disabled={renaming || !renameInput.trim()}
                        className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 disabled:opacity-40"
                        title="Guardar nombre"
                        aria-label="Guardar nombre"
                      >
                        <Check size={14} strokeWidth={2.5} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingLabel(null)}
                        disabled={renaming}
                        className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                        title="Cancelar"
                        aria-label="Cancelar edición"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ) : isDeleting ? (
                    /* Inline Delete Confirmation (NO modals/AlertDialog) */
                    <div className="flex flex-col gap-2 rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.08)] p-2.5 text-xs">
                      <div className="flex items-start gap-2 text-[hsl(var(--destructive))] font-medium">
                        <AlertCircle size={15} className="shrink-0 mt-0.5" />
                        <div>
                          <p>¿Eliminar la etiqueta &quot;{item.name}&quot;?</p>
                          <p className="text-2xs font-normal text-[hsl(var(--muted-foreground))] mt-0.5">
                            Se retirará de {item.task_count} actividad(es) asociada(s).
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center justify-end gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => setDeletingLabel(null)}
                          disabled={deleting}
                          className="px-2.5 py-1 text-2xs font-semibold rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]"
                        >
                          Cancelar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleConfirmDelete(item.name)}
                          disabled={deleting}
                          className="px-2.5 py-1 text-2xs font-semibold rounded-md bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))] hover:opacity-90 disabled:opacity-50"
                        >
                          {deleting ? "Eliminando..." : "Sí, eliminar"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* Default Label Row */
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className={clsx(
                            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border",
                            color.bg,
                            color.text,
                            color.border
                          )}
                        >
                          <span className={clsx("size-1.5 rounded-full shrink-0", color.dot)} />
                          <span className="truncate max-w-[12rem]">{item.name}</span>
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-2xs font-medium text-[hsl(var(--muted-foreground))] tabular-nums">
                          {item.task_count} {item.task_count === 1 ? "actividad" : "actividades"}
                        </span>

                        <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity">
                          <button
                            type="button"
                            onClick={() => handleStartRename(item.name)}
                            className="flex size-7 items-center justify-center rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                            title={`Renombrar etiqueta "${item.name}"`}
                            aria-label={`Renombrar etiqueta ${item.name}`}
                          >
                            <Edit2 size={12} />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleStartDelete(item.name)}
                            className="flex size-7 items-center justify-center rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] transition-colors"
                            title={`Eliminar etiqueta "${item.name}"`}
                            aria-label={`Eliminar etiqueta ${item.name}`}
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );

  if (embedded) {
    return drawerContent;
  }

  return (
    <RightPanel
      open={isPanelOpen}
      isOpen={isPanelOpen}
      onClose={onClose || (() => {})}
      title="Etiquetas del proyecto"
      subtitle="Gestiona, renombra y elimina etiquetas de actividades"
      width="w-full sm:w-[480px] max-w-none"
    >
      {drawerContent}
    </RightPanel>
  );
}

export default ProjectLabelsDrawer;

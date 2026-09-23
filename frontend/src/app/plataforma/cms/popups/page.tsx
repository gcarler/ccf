"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { SITE_KEY } from "@/lib/site-config";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  Layers,
  Plus,
  Search,
  Clock,
  ScrollText,
  LogOut,
  Zap,
  Edit2,
  Trash2,
  Globe,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import SidePanel from "@/components/ui/SidePanel";
import clsx from "clsx";
import {
  createCmsPopup,
  deleteCmsPopup,
  listCmsPopups,
  listCmsSites,
  patchCmsPopup,
} from "@/lib/cms/v2";
import { CmsPopup, CmsSite, PopupTriggerType } from "@/types/cms-v2";
import { canEditCms } from "@/lib/cms/permissions";

const RichEditor = dynamic(() => import("@/components/cms/RichEditor"), { ssr: false });

const TRIGGER_TYPES: { id: PopupTriggerType; label: string; icon: React.ComponentType<{ className?: string }>; description: string }[] = [
  { id: "time_delay", label: "Tiempo", icon: Clock, description: "Se dispara tras X segundos" },
  { id: "scroll_percent", label: "Scroll", icon: ScrollText, description: "Se dispara al desplazar el % de página" },
  { id: "exit_intent", label: "Exit Intent", icon: LogOut, description: "Se dispara al mover el cursor hacia arriba fuera de la página" },
  { id: "on_load", label: "Al cargar", icon: Zap, description: "Se muestra de inmediato al entrar" },
];

export default function CmsPopupsManagement() {
  const { token, user } = useAuth();
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [popups, setPopups] = useState<CmsPopup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Drawer / SidePanel State
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [editingPopup, setEditingPopup] = useState<CmsPopup | null>(null);
  const [saving, setSaving] = useState(false);

  // Form State
  const [formName, setFormName] = useState("");
  const [formContentHtml, setFormContentHtml] = useState("");
  const [formTriggerType, setFormTriggerType] = useState<PopupTriggerType>("on_load");
  const [formTriggerValue, setFormTriggerValue] = useState<number | "">(5);
  const [formIsActive, setFormIsActive] = useState(true);
  const [formPagesInput, setFormPagesInput] = useState("*");

  // Delete modal state
  const [pendingDelete, setPendingDelete] = useState<CmsPopup | null>(null);
  const [deleting, setDeleting] = useState(false);

  const canEdit = canEditCms(user?.role);

  const fetchData = useCallback(async (targetSite: string) => {
    if (!token) {
      setLoading(false);
      setPopups([]);
      setError("Debes iniciar sesión para gestionar popups.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [nextSites, nextPopups] = await Promise.all([
        listCmsSites(token),
        listCmsPopups(targetSite, token),
      ]);
      setSites(nextSites || []);
      setPopups(nextPopups || []);
    } catch (err) {
      toast.error("Error al cargar popups");
      setPopups([]);
      setError("No se pudieron cargar los popups.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData(siteKey);
  }, [fetchData, siteKey]);

  const visiblePopups = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return popups;
    return popups.filter(
      (p) =>
        p.name.toLowerCase().includes(term) ||
        p.trigger_type.toLowerCase().includes(term)
    );
  }, [popups, search]);

  const handleOpenCreate = () => {
    setEditingPopup(null);
    setFormName("");
    setFormContentHtml("<h2>¡Promoción Especial!</h2><p>Suscríbete a nuestro boletín para recibir novedades.</p>");
    setFormTriggerType("on_load");
    setFormTriggerValue(5);
    setFormIsActive(true);
    setFormPagesInput("*");
    setIsDrawerOpen(true);
  };

  const handleOpenEdit = (popup: CmsPopup) => {
    setEditingPopup(popup);
    setFormName(popup.name);
    setFormContentHtml(popup.content_html);
    setFormTriggerType(popup.trigger_type);
    setFormTriggerValue(popup.trigger_value ?? 5);
    setFormIsActive(popup.is_active);
    setFormPagesInput(popup.show_on_pages?.join(", ") || "*");
    setIsDrawerOpen(true);
  };

  const handleToggleActive = async (popup: CmsPopup) => {
    if (!token || !canEdit) return;
    const nextState = !popup.is_active;
    // Optimistic UI update
    setPopups((prev) =>
      prev.map((p) => (p.id === popup.id ? { ...p, is_active: nextState } : p))
    );
    try {
      await patchCmsPopup(siteKey, popup.id, { is_active: nextState }, token);
      toast.success(`Popup "${popup.name}" ${nextState ? "activado" : "desactivado"}`);
    } catch (err) {
      toast.error("Error al cambiar estado del popup");
      fetchData(siteKey);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !canEdit) return;
    const trimmedName = formName.trim();
    if (!trimmedName) {
      toast.error("Ingresa un nombre para el popup");
      return;
    }

    const pagesArray = formPagesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    setSaving(true);
    try {
      const payload = {
        name: trimmedName,
        content_html: formContentHtml,
        trigger_type: formTriggerType,
        trigger_value: typeof formTriggerValue === "number" ? formTriggerValue : null,
        is_active: formIsActive,
        show_on_pages: pagesArray.length > 0 ? pagesArray : ["*"],
      };

      if (editingPopup) {
        await patchCmsPopup(siteKey, editingPopup.id, payload, token);
        toast.success(`Popup "${trimmedName}" actualizado`);
      } else {
        await createCmsPopup(siteKey, payload, token);
        toast.success(`Popup "${trimmedName}" creado`);
      }
      setIsDrawerOpen(false);
      await fetchData(siteKey);
    } catch (err) {
      toast.error("Error al guardar el popup");
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!token || !canEdit || !pendingDelete) return;
    setDeleting(true);
    try {
      await deleteCmsPopup(siteKey, pendingDelete.id, token);
      toast.success("Popup eliminado correctamente");
      await fetchData(siteKey);
    } catch (err) {
      toast.error("Error al eliminar popup");
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  };

  const renderBadge = (type: PopupTriggerType, val: number | null) => {
    switch (type) {
      case "time_delay":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)]">
            <Clock className="w-3.5 h-3.5" /> Tiempo ({val ?? 5}s)
          </span>
        );
      case "scroll_percent":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] border border-[hsl(var(--border))]">
            <ScrollText className="w-3.5 h-3.5" /> Scroll ({val ?? 50}%)
          </span>
        );
      case "exit_intent":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
            <LogOut className="w-3.5 h-3.5" /> Exit Intent
          </span>
        );
      case "on_load":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)]">
            <Zap className="w-3.5 h-3.5" /> Al Cargar
          </span>
        );
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[hsl(var(--text-primary))] flex items-center gap-2">
            <Layers className="w-7 h-7 text-[hsl(var(--primary))]" />
            Gestión de Popups Nativos
          </h1>
          <p className="text-sm text-[hsl(var(--text-secondary))] mt-1">
            Configura ventanas emergentes disparadas por tiempo, scroll, exit intent o al cargar.
          </p>
        </div>

        {canEdit && (
          <button
            onClick={handleOpenCreate}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-[hsl(var(--primary))] hover:opacity-90 text-white font-medium rounded-lg shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" /> Nuevo Popup
          </button>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-[hsl(var(--destructive)/0.1)] border border-[hsl(var(--destructive)/0.2)] rounded-xl text-sm text-[hsl(var(--destructive))]">
          {error}
        </div>
      )}

      {/* Filters and Site Selector */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-[hsl(var(--surface-1))] p-4 rounded-xl border border-[hsl(var(--border))] shadow-sm">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--text-secondary))]" />
          <input
            type="text"
            placeholder="Buscar por nombre o disparador..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
          />
        </div>

        {sites.length > 1 && (
          <div className="flex items-center gap-2 shrink-0">
            <Globe className="w-4 h-4 text-[hsl(var(--text-secondary))]" />
            <select
              value={siteKey}
              onChange={(e) => setSiteKey(e.target.value)}
              className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            >
              {sites.map((s) => (
                <option key={s.site_key} value={s.site_key}>
                  {s.name} ({s.site_key})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Content State: Skeleton Loader, Empty State, or Card Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 bg-[hsl(var(--surface-1))] animate-pulse rounded-xl border border-[hsl(var(--border))] p-5 space-y-3">
              <div className="h-5 bg-[hsl(var(--surface-2))] rounded w-1/2" />
              <div className="h-4 bg-[hsl(var(--surface-2))] rounded w-1/3" />
              <div className="h-10 bg-[hsl(var(--surface-2))] rounded w-full mt-4" />
            </div>
          ))}
        </div>
      ) : visiblePopups.length === 0 ? (
        <div className="bg-[hsl(var(--surface-1))] border-2 border-dashed border-[hsl(var(--border))] rounded-2xl p-12 text-center flex flex-col items-center justify-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))]">
            <Sparkles className="w-8 h-8" />
          </div>
          <div className="max-w-md">
            <h3 className="text-lg font-semibold text-[hsl(var(--text-primary))]">No hay popups configurados</h3>
            <p className="text-sm text-[hsl(var(--text-secondary))] mt-1">
              Crea tu primer popup emergente para promociones, avisos o captación de prospectos.
            </p>
          </div>
          {canEdit && (
            <button
              onClick={handleOpenCreate}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[hsl(var(--primary))] text-white font-medium rounded-lg shadow hover:opacity-90 transition-colors"
            >
              <Plus className="w-4 h-4" /> Crear Primer Popup
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence>
            {visiblePopups.map((popup) => (
              <motion.div
                key={popup.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-[hsl(var(--surface-1))] rounded-xl border border-[hsl(var(--border))] p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-[hsl(var(--text-primary))] text-base truncate">
                      {popup.name}
                    </h3>
                    <button
                      onClick={() => handleToggleActive(popup)}
                      title={popup.is_active ? "Desactivar" : "Activar"}
                      className={clsx(
                        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                        popup.is_active ? "bg-[hsl(var(--primary))]" : "bg-[hsl(var(--border))]"
                      )}
                    >
                      <span
                        className={clsx(
                          "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                          popup.is_active ? "translate-x-5" : "translate-x-0"
                        )}
                      />
                    </button>
                  </div>

                  <div className="mt-3 flex items-center gap-2 flex-wrap">
                    {renderBadge(popup.trigger_type, popup.trigger_value)}
                  </div>

                  <p className="text-xs text-[hsl(var(--text-secondary))] mt-3 line-clamp-2">
                    Scope: <code className="bg-[hsl(var(--surface-2))] px-1 py-0.5 rounded text-[hsl(var(--text-secondary))]">{popup.show_on_pages?.join(", ") || "*"}</code>
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-[hsl(var(--border))] flex items-center justify-end gap-2">
                  {canEdit && (
                    <>
                      <button
                        onClick={() => handleOpenEdit(popup)}
                        className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] rounded-md hover:bg-[hsl(var(--surface-2))] transition-colors"
                        title="Editar"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setPendingDelete(popup)}
                        className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] rounded-md hover:bg-[hsl(var(--destructive)/0.1)] transition-colors"
                        title="Eliminar"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* SidePanel Drawer for Create / Edit */}
      <SidePanel
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={editingPopup ? "Editar Popup" : "Nuevo Popup"}
        subtitle="Configura el contenido y la regla de activación"
        width="w-[550px]"
      >
        <form onSubmit={handleSave} className="p-6 space-y-6">
          {/* Name */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[hsl(var(--text-primary))]">
              Nombre Interno del Popup *
            </label>
            <input
              type="text"
              required
              placeholder="ej. Promo Verano 2026"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full px-3 py-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] rounded-lg text-sm focus:ring-2 focus:ring-[hsl(var(--primary))] focus:outline-none"
            />
          </div>

          {/* Trigger Type Selector Cards */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-[hsl(var(--text-primary))]">
              Tipo de Disparador (Trigger) *
            </label>
            <div className="grid grid-cols-2 gap-2">
              {TRIGGER_TYPES.map((t) => {
                const Icon = t.icon;
                const isSelected = formTriggerType === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setFormTriggerType(t.id)}
                    className={clsx(
                      "p-3 text-left rounded-xl border transition-all flex flex-col justify-between space-y-1.5",
                      isSelected
                        ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] ring-1 ring-[hsl(var(--primary))]"
                        : "border-[hsl(var(--border))] hover:border-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                    )}
                  >
                    <div className="flex items-center gap-2 font-medium text-sm">
                      <Icon className="w-4 h-4 text-[hsl(var(--primary))]" />
                      {t.label}
                    </div>
                    <p className="text-xs text-[hsl(var(--text-secondary))] leading-tight">
                      {t.description}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Trigger Value Input (Conditional) */}
          {(formTriggerType === "time_delay" || formTriggerType === "scroll_percent") && (
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[hsl(var(--text-primary))]">
                {formTriggerType === "time_delay" ? "Tiempo de espera (segundos)" : "Porcentaje de scroll (%)"} *
              </label>
              <input
                type="number"
                min={1}
                max={formTriggerType === "scroll_percent" ? 100 : 3600}
                required
                value={formTriggerValue}
                onChange={(e) => setFormTriggerValue(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full px-3 py-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] rounded-lg text-sm focus:ring-2 focus:ring-[hsl(var(--primary))] focus:outline-none"
              />
            </div>
          )}

          {/* Target Pages */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[hsl(var(--text-primary))]">
              Páginas Objetivo (separadas por coma, use * para todas)
            </label>
            <input
              type="text"
              placeholder="*, /cursos, /eventos"
              value={formPagesInput}
              onChange={(e) => setFormPagesInput(e.target.value)}
              className="w-full px-3 py-2 bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] rounded-lg text-sm focus:ring-2 focus:ring-[hsl(var(--primary))] focus:outline-none"
            />
          </div>

          {/* Active Switch */}
          <div className="flex items-center justify-between p-3 bg-[hsl(var(--surface-2))] rounded-xl border border-[hsl(var(--border))]">
            <div>
              <p className="text-sm font-medium text-[hsl(var(--text-primary))]">Popup Activo</p>
              <p className="text-xs text-[hsl(var(--text-secondary))]">Si está desactivado no se mostrará a los visitantes.</p>
            </div>
            <input
              type="checkbox"
              checked={formIsActive}
              onChange={(e) => setFormIsActive(e.target.checked)}
              className="w-4 h-4 text-[hsl(var(--primary))] rounded focus:ring-[hsl(var(--primary))]"
            />
          </div>

          {/* RichEditor for HTML content */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-[hsl(var(--text-primary))]">
              Contenido del Popup (HTML / Rich Text) *
            </label>
            <RichEditor
              content={formContentHtml}
              onChange={(html) => setFormContentHtml(html)}
              placeholder="Escribe el mensaje del popup..."
              token={token || undefined}
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[hsl(var(--border))]">
            <button
              type="button"
              onClick={() => setIsDrawerOpen(false)}
              className="px-4 py-2 text-sm font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-[hsl(var(--primary))] hover:opacity-90 text-white rounded-lg shadow transition-colors disabled:opacity-50"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {editingPopup ? "Guardar Cambios" : "Crear Popup"}
            </button>
          </div>
        </form>
      </SidePanel>

      {/* Delete Confirmation Drawer */}
      <SidePanel
        isOpen={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        title="Eliminar Popup"
        subtitle={pendingDelete?.name}
      >
        {pendingDelete && (
          <div className="p-6 space-y-5">
            <div className="rounded-xl border border-[hsl(var(--destructive)/0.2)] bg-[hsl(var(--destructive)/0.1)] p-4">
              <p className="text-sm text-[hsl(var(--destructive))]">
                ¿Estás seguro de eliminar el popup <strong>&quot;{pendingDelete.name}&quot;</strong>? Esta acción no se puede deshacer.
              </p>
            </div>
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-[hsl(var(--border))]">
              <button
                type="button"
                onClick={() => setPendingDelete(null)}
                className="px-4 py-2 text-sm font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={deleting}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-[hsl(var(--destructive))] hover:opacity-90 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {deleting && <Loader2 className="w-4 h-4 animate-spin" />}
                Eliminar
              </button>
            </div>
          </div>
        )}
      </SidePanel>
    </div>
  );
}

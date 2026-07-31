"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
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
import RichEditor from "@/components/cms/RichEditor";
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
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
            <Clock className="w-3.5 h-3.5" /> Tiempo ({val ?? 5}s)
          </span>
        );
      case "scroll_percent":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-sky-100 text-sky-800 dark:bg-sky-950/60 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
            <ScrollText className="w-3.5 h-3.5" /> Scroll ({val ?? 50}%)
          </span>
        );
      case "exit_intent":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            <LogOut className="w-3.5 h-3.5" /> Exit Intent
          </span>
        );
      case "on_load":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
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
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Layers className="w-7 h-7 text-blue-600 dark:text-blue-400" />
            Gestión de Popups Nativos
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            Configura ventanas emergentes disparadas por tiempo, scroll, exit intent o al cargar.
          </p>
        </div>

        {canEdit && (
          <button
            onClick={handleOpenCreate}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" /> Nuevo Popup
          </button>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Filters and Site Selector */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-white dark:bg-zinc-900 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 shadow-sm">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <input
            type="text"
            placeholder="Buscar por nombre o disparador..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {sites.length > 1 && (
          <div className="flex items-center gap-2 shrink-0">
            <Globe className="w-4 h-4 text-zinc-400" />
            <select
              value={siteKey}
              onChange={(e) => setSiteKey(e.target.value)}
              className="bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            <div key={i} className="h-44 bg-zinc-100 dark:bg-zinc-800 animate-pulse rounded-xl border border-zinc-200 dark:border-zinc-700 p-5 space-y-3">
              <div className="h-5 bg-zinc-200 dark:bg-zinc-700 rounded w-1/2" />
              <div className="h-4 bg-zinc-200 dark:bg-zinc-700 rounded w-1/3" />
              <div className="h-10 bg-zinc-200 dark:bg-zinc-700 rounded w-full mt-4" />
            </div>
          ))}
        </div>
      ) : visiblePopups.length === 0 ? (
        <div className="bg-white dark:bg-zinc-900 border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-2xl p-12 text-center flex flex-col items-center justify-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-blue-50 dark:bg-blue-950/50 flex items-center justify-center text-blue-600 dark:text-blue-400">
            <Sparkles className="w-8 h-8" />
          </div>
          <div className="max-w-md">
            <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">No hay popups configurados</h3>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
              Crea tu primer popup emergente para promociones, avisos o captación de prospectos.
            </p>
          </div>
          {canEdit && (
            <button
              onClick={handleOpenCreate}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-lg shadow hover:bg-blue-700 transition-colors"
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
                className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 text-base truncate">
                      {popup.name}
                    </h3>
                    <button
                      onClick={() => handleToggleActive(popup)}
                      title={popup.is_active ? "Desactivar" : "Activar"}
                      className={clsx(
                        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                        popup.is_active ? "bg-blue-600" : "bg-zinc-300 dark:bg-zinc-700"
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

                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-3 line-clamp-2">
                    Scope: <code className="bg-zinc-100 dark:bg-zinc-800 px-1 py-0.5 rounded text-zinc-700 dark:text-zinc-300">{popup.show_on_pages?.join(", ") || "*"}</code>
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-end gap-2">
                  {canEdit && (
                    <>
                      <button
                        onClick={() => handleOpenEdit(popup)}
                        className="p-1.5 text-zinc-600 dark:text-zinc-400 hover:text-blue-600 dark:hover:text-blue-400 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                        title="Editar"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setPendingDelete(popup)}
                        className="p-1.5 text-zinc-600 dark:text-zinc-400 hover:text-red-600 dark:hover:text-red-400 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
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
            <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
              Nombre Interno del Popup *
            </label>
            <input
              type="text"
              required
              placeholder="ej. Promo Verano 2026"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Trigger Type Selector Cards */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
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
                        ? "border-blue-600 bg-blue-50/50 dark:bg-blue-950/30 text-blue-900 dark:text-blue-200 ring-1 ring-blue-600"
                        : "border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600 text-zinc-700 dark:text-zinc-300"
                    )}
                  >
                    <div className="flex items-center gap-2 font-medium text-sm">
                      <Icon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      {t.label}
                    </div>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-tight">
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
              <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {formTriggerType === "time_delay" ? "Tiempo de espera (segundos)" : "Porcentaje de scroll (%)"} *
              </label>
              <input
                type="number"
                min={1}
                max={formTriggerType === "scroll_percent" ? 100 : 3600}
                required
                value={formTriggerValue}
                onChange={(e) => setFormTriggerValue(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
          )}

          {/* Target Pages */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
              Páginas Objetivo (separadas por coma, use * para todas)
            </label>
            <input
              type="text"
              placeholder="*, /cursos, /eventos"
              value={formPagesInput}
              onChange={(e) => setFormPagesInput(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          {/* Active Switch */}
          <div className="flex items-center justify-between p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-xl border border-zinc-200 dark:border-zinc-700">
            <div>
              <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Popup Activo</p>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Si está desactivado no se mostrará a los visitantes.</p>
            </div>
            <input
              type="checkbox"
              checked={formIsActive}
              onChange={(e) => setFormIsActive(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
            />
          </div>

          {/* RichEditor for HTML content */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
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
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <button
              type="button"
              onClick={() => setIsDrawerOpen(false)}
              className="px-4 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow transition-colors disabled:opacity-50"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {editingPopup ? "Guardar Cambios" : "Crear Popup"}
            </button>
          </div>
        </form>
      </SidePanel>

      {/* Delete Confirmation Modal */}
      {pendingDelete && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">Eliminar Popup</h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              ¿Estás seguro de eliminar el popup <strong className="text-zinc-900 dark:text-zinc-100">&quot;{pendingDelete.name}&quot;</strong>? Esta acción no se puede deshacer.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setPendingDelete(null)}
                className="px-4 py-2 text-sm font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {deleting && <Loader2 className="w-4 h-4 animate-spin" />}
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

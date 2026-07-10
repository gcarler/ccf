"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Archive,
  CheckCircle2,
  Layers3,
  Pencil,
  Plus,
  RotateCcw,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import AdminHero from "@/components/admin/AdminHero";
import SidePanel from "@/components/ui/SidePanel";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/http";
import { canEditCms, canPublishCms } from "@/lib/cms/permissions";
import {
  createCmsSectionType,
  deleteCmsSectionType,
  listCmsSectionTypes,
  patchCmsSectionType,
} from "@/lib/cms/v2";
import type { CmsSectionType } from "@/types/cms-v2";

type DrawerMode = "create" | "edit" | "delete-confirm" | null;

interface FormState {
  name: string;
  description: string;
  is_active: boolean;
}

const EMPTY_FORM: FormState = { name: "", description: "", is_active: true };

function formatDate(value?: string | null) {
  if (!value) return "Sin fecha";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin fecha";
  return date.toLocaleDateString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function statusBadge(isActive: boolean) {
  return isActive
    ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
    : "bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))]";
}

export default function SectionTypesPage() {
  const { token, user, loading: authLoading } = useAuth();
  const [types, setTypes] = useState<CmsSectionType[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [onlyActive, setOnlyActive] = useState(false);
  const [drawerMode, setDrawerMode] = useState<DrawerMode>(null);
  const [target, setTarget] = useState<CmsSectionType | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Permissions are derived ONCE for the lifetime of this render so the
  // Rules of Hooks are honored (no conditional useAuth() after the
  // early-return guard further down).
  const canView = canEditCms(user?.role);
  const canPublish = canPublishCms(user?.role);

  const fetchTypes = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await listCmsSectionTypes(onlyActive, token);
      setTypes(Array.isArray(data) ? data : []);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast.error("Sesion expirada. Inicia sesion nuevamente.");
      } else {
        toast.error("No se pudieron cargar los tipos de seccion.");
      }
      setTypes([]);
    } finally {
      setLoading(false);
    }
  }, [token, onlyActive]);

  useEffect(() => {
    if (authLoading) return;
    fetchTypes();
  }, [authLoading, fetchTypes]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return types;
    return types.filter(
      (row) =>
        row.name.toLowerCase().includes(q) ||
        (row.description || "").toLowerCase().includes(q),
    );
  }, [types, search]);

  const openCreateDrawer = () => {
    setForm(EMPTY_FORM);
    setFormError(null);
    setTarget(null);
    setDrawerMode("create");
  };

  const openEditDrawer = (row: CmsSectionType) => {
    setTarget(row);
    setForm({
      name: row.name,
      description: row.description || "",
      is_active: row.is_active,
    });
    setFormError(null);
    setDrawerMode("edit");
  };

  const openDeleteDrawer = (row: CmsSectionType) => {
    setTarget(row);
    setFormError(null);
    setDrawerMode("delete-confirm");
  };

  const closeDrawer = () => {
    setDrawerMode(null);
    setTarget(null);
    setFormError(null);
    setSaving(false);
    setForm(EMPTY_FORM);
  };

  const validateForm = (mode: "create" | "edit"): string | null => {
    if (mode === "create") {
      const name = form.name.trim().toLowerCase();
      if (!name) return "El nombre es obligatorio.";
      if (name.length > 80) return "El nombre no puede superar 80 caracteres.";
      const re = /^[a-z0-9_-]+$/;
      if (!re.test(name)) {
        return "El nombre solo admite letras minusculas, digitos, guion y guion bajo.";
      }
      if (types.some((row) => row.name === name)) {
        return "Ya existe un tipo de seccion con ese nombre.";
      }
    }
    if (form.description.length > 255) {
      return "La descripcion no puede superar 255 caracteres.";
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    if (drawerMode !== "create" && drawerMode !== "edit") return;

    const err = validateForm(drawerMode);
    if (err) {
      setFormError(err);
      return;
    }
    setSaving(true);
    setFormError(null);

    const trimmedDescription = form.description.trim();

    try {
      if (drawerMode === "create") {
        const created = await createCmsSectionType(
          {
            name: form.name.trim().toLowerCase(),
            description: trimmedDescription || null,
            is_active: form.is_active,
          },
          token,
        );
        toast.success(`Tipo "${created.name}" creado.`);
      } else {
        if (!target) return;
        const updated = await patchCmsSectionType(
          target.name,
          {
            description: trimmedDescription || null,
            is_active: form.is_active,
          },
          token,
        );
        toast.success(`Tipo "${updated.name}" actualizado.`);
      }
      closeDrawer();
      fetchTypes();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setFormError("Ya existe un tipo de seccion con ese nombre.");
      } else if (err instanceof ApiError && err.status === 422) {
        setFormError(
          "El backend rechazo el payload. Revisa nombre y descripcion.",
        );
      } else if (err instanceof ApiError && err.status === 403) {
        setFormError("Tu rol no permite modificar tipos de seccion.");
        toast.error("Tu rol no permite modificar tipos de seccion.");
      } else {
        setFormError("Error al guardar los cambios.");
        toast.error("Error al guardar los cambios.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleSoftDelete = async (row: CmsSectionType) => {
    if (!token) return;
    setSaving(true);
    try {
      await deleteCmsSectionType(row.name, token);
      toast.success(`Tipo "${row.name}" desactivado.`);
      closeDrawer();
      fetchTypes();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        toast.error("Tu rol no permite desactivar tipos de seccion.");
      } else {
        toast.error("Error al desactivar el tipo de seccion.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleReactivate = async (row: CmsSectionType) => {
    if (!token) return;
    try {
      await patchCmsSectionType(row.name, { is_active: true }, token);
      toast.success(`Tipo "${row.name}" reactivado.`);
      fetchTypes();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        toast.error("Tu rol no permite reactivar tipos de seccion.");
      } else {
        toast.error("Error al reactivar el tipo de seccion.");
      }
    }
  };

  if (!canView) {
    return (
      <div className="h-full overflow-y-auto bg-[hsl(var(--surface-1))]/60 dark:bg-[hsl(var(--admin-bg-primary))]">
        <div className="mx-auto max-w-3xl px-4 py-1.5 text-center">
          <h1 className="text-xl font-semibold">Acceso restringido</h1>
          <p className="mt-3 text-[hsl(var(--text-secondary))]">
            Necesitas un rol editorial para ver esta seccion.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-[hsl(var(--surface-1))]/60 dark:bg-[hsl(var(--admin-bg-primary))]">
      <div className="space-y-4 px-4 py-2 lg:px-6">
        <AdminHero
          eyebrow="CMS"
          title="Tipos de Seccion"
          description="Catalogo global que define los bloques que un editor puede usar al construir paginas. Los seeds en deploy preservan las desactivaciones administrativas."
          tags={["Catalog", "Secciones", "Plataforma"]}
          watchers={["Comunicaciones", "Web"]}
          primaryAction={
            canPublish
              ? {
                  label: "Nuevo tipo",
                  icon: Plus,
                  onClick: openCreateDrawer,
                }
              : {
                  label: "Nuevo tipo",
                  icon: Plus,
                  onClick: () =>
                    toast(
                      "Tu rol no permite crear tipos de seccion. Coordinar con un publisher.",
                      { icon: <AlertCircle className="h-4 w-4 text-amber-700" /> },
                    ),
                }
          }
        />

        {/* ── Filter Bar ── */}
        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] px-4 py-3 shadow-sm flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-56">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
            />
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por nombre o descripcion..."
              className="w-full pl-9 pr-4 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
            />
          </div>

          <label className="flex items-center gap-2 select-none cursor-pointer">
            <input
              type="checkbox"
              checked={onlyActive}
              onChange={(event) => setOnlyActive(event.target.checked)}
              className="w-4 h-4 rounded border-[hsl(var(--border))] dark:border-white/20 text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))/0.3]"
            />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
              Solo activos
            </span>
          </label>

          <div className="text-[10px] uppercase tracking-wider font-bold text-[hsl(var(--text-secondary))]">
            {filtered.length} de {types.length}
          </div>
        </div>

        {/* ── Table / Loading / Empty ── */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-7 h-7 rounded-full border-2 border-[hsl(var(--primary))] border-t-transparent animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/10 p-10 text-center bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <Layers3
              size={32}
              className="mx-auto text-[hsl(var(--text-secondary))]"
            />
            <p className="mt-3 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
              {search || onlyActive
                ? "Sin resultados para los filtros activos."
                : "Aun no hay tipos de seccion catalogados."}
            </p>
            <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">
              {canPublish
                ? "Usa el boton Nuevo tipo para registrar uno nuevo."
                : "Los seeds los crean al deploy. Coordinar con un publisher para anadir uno nuevo."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border-b border-[hsl(var(--border))] dark:border-white/10">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-[10px]">
                    Nombre
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-[10px]">
                    Descripcion
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-[10px]">
                    Estado
                  </th>
                  <th className="px-4 py-3 text-left font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-[10px]">
                    Creado
                  </th>
                  <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/10">
                {filtered.map((row) => (
                  <tr
                    key={row.id}
                    className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] transition-colors"
                  >
                    <td className="px-4 py-3 align-top">
                      <button
                        type="button"
                        onClick={() => openEditDrawer(row)}
                        disabled={!canPublish}
                        className="font-mono text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-white hover:text-[hsl(var(--primary))] disabled:cursor-not-allowed disabled:hover:text-[hsl(var(--text-primary))] transition-colors"
                      >
                        {row.name}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-[hsl(var(--text-secondary))] max-w-md align-top">
                      <p className="text-xs leading-relaxed line-clamp-2">
                        {row.description || (
                          <span className="italic opacity-60">Sin descripcion</span>
                        )}
                      </p>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${statusBadge(row.is_active)}`}
                      >
                        {row.is_active ? (
                          <span className="inline-flex items-center gap-1">
                            <CheckCircle2 size={10} />
                            ACTIVO
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1">
                            <Archive size={10} />
                            INACTIVO
                          </span>
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-[hsl(var(--text-secondary))] align-top">
                      {formatDate(row.created_at)}
                    </td>
                    <td className="px-4 py-3 align-top">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => openEditDrawer(row)}
                          disabled={!canPublish}
                          title={canPublish ? "Editar" : "Sin permisos"}
                          className="p-2 rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-[hsl(var(--text-secondary))] transition-all"
                        >
                          <Pencil size={14} />
                        </button>
                        {row.is_active ? (
                          <button
                            type="button"
                            onClick={() => openDeleteDrawer(row)}
                            disabled={!canPublish}
                            title={canPublish ? "Desactivar (soft-delete)" : "Sin permisos"}
                            className="p-2 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-500/10 text-[hsl(var(--text-secondary))] hover:text-amber-700 disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-[hsl(var(--text-secondary))] transition-all"
                          >
                            <Archive size={14} />
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleReactivate(row)}
                            disabled={!canPublish}
                            title={canPublish ? "Reactivar" : "Sin permisos"}
                            className="p-2 rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-500/10 text-[hsl(var(--text-secondary))] hover:text-emerald-700 disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-[hsl(var(--text-secondary))] transition-all"
                          >
                            <RotateCcw size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!canPublish && (
          <div className="rounded-lg border border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 px-4 py-3 text-xs text-amber-800 dark:text-amber-200 flex items-start gap-2">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Tu rol&nbsp;
              <strong>({user?.role || "lector"})</strong>&nbsp;permite leer el
              catalogo pero no modificarlo. Coordinar con un publisher del modulo
              CMS para anadir, editar o desactivar tipos.
            </span>
          </div>
        )}
      </div>

      {/* ── Create / Edit Drawer ── */}
      <SidePanel
        isOpen={drawerMode === "create" || drawerMode === "edit"}
        onClose={closeDrawer}
        title={
          drawerMode === "create"
            ? "Nuevo tipo de seccion"
            : `Editar ${target?.name || ""}`
        }
        subtitle={
          drawerMode === "edit"
            ? "El nombre es inmutable. Para renombrar, desactivar este y crear uno nuevo."
            : "Catalogo global. Available en builder y validacion de props."
        }
        width="w-[500px]"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="rounded-lg border border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10 px-3 py-2.5 text-xs text-red-700 dark:text-red-300 flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
              NOMBRE
              <span className="ml-1 text-[hsl(var(--text-secondary))]/70 font-normal normal-case">
                ({form.name.length}/80)
              </span>
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, name: event.target.value }))
              }
              maxLength={80}
              disabled={drawerMode === "edit" || saving}
              placeholder="hero, cta_banner, custom_widget..."
              className="w-full px-3 py-2 text-[13px] font-mono bg-[hsl(var(--bg-primary))] dark:bg-[#1a1c20] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            />
            {drawerMode === "edit" && (
              <p className="text-[10px] text-amber-700 dark:text-amber-300">
                El nombre es inmutable. Para cambiarlo: desactivar este + crear uno nuevo.
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
              DESCRIPCION
              <span className="ml-1 text-[hsl(var(--text-secondary))]/70 font-normal normal-case">
                ({form.description.length}/255, opcional)
              </span>
            </label>
            <textarea
              value={form.description}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, description: event.target.value }))
              }
              maxLength={255}
              rows={4}
              disabled={saving}
              placeholder="Proposito y notas internas sobre este tipo de seccion..."
              className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[#1a1c20] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] transition-all resize-none disabled:opacity-60 disabled:cursor-not-allowed"
            />
          </div>

          <label className="flex items-start gap-3 p-3 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 cursor-pointer hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] transition-colors">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  is_active: event.target.checked,
                }))
              }
              disabled={saving}
              className="mt-1 w-4 h-4 rounded border-[hsl(var(--border))] dark:border-white/20 text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))/0.3] disabled:opacity-60"
            />
            <div className="flex-1">
              <span className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white">
                Activo en el validador del builder
              </span>
              <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-0.5 leading-relaxed">
                Si esta apagado, los editores no podran anadir secciones de este tipo.
                Los ya existentes seguiran renderizando.
              </p>
            </div>
          </label>

          <div className="flex items-center gap-3 pt-3 border-t border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={closeDrawer}
              className="flex-1 py-2.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[12px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-all"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-2.5 rounded-lg bg-[hsl(var(--primary))] text-white text-[12px] font-bold uppercase tracking-wide hover:opacity-90 disabled:opacity-50 transition-all"
            >
              {saving ? "Guardando..." : drawerMode === "create" ? "Crear" : "Guardar"}
            </button>
          </div>
        </form>
      </SidePanel>

      {/* ── Confirm Deactivate Drawer ── */}
      <SidePanel
        isOpen={drawerMode === "delete-confirm"}
        onClose={closeDrawer}
        title="Desactivar tipo de seccion"
        subtitle={target?.name}
        width="w-[440px]"
      >
        {target && (
          <div className="space-y-4">
            <div className="rounded-lg border border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 px-3 py-2.5 text-xs text-amber-800 dark:text-amber-200 flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                Soft-delete: el registro queda para auditoria pero
                <code className="mx-1 px-1 bg-amber-100 dark:bg-amber-500/20 rounded">
                  get_allowed_section_types()
                </code>
                lo filtra y los editores no podran anadir secciones nuevas de este tipo.
                Las existentes seguiran renderizando.
              </span>
            </div>

            <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 text-xs space-y-1.5 bg-[hsl(var(--surface-1))]/40 dark:bg-white/[0.02]">
              <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white">
                {target.name}
              </p>
              <p className="text-[hsl(var(--text-secondary))]">
                {target.description || (
                  <span className="italic opacity-60">Sin descripcion</span>
                )}
              </p>
            </div>

            <div className="flex items-center gap-3 pt-3 border-t border-[hsl(var(--border))] dark:border-white/10">
              <button
                type="button"
                onClick={closeDrawer}
                className="flex-1 py-2.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-[12px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-all"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => handleSoftDelete(target)}
                disabled={saving}
                className="flex-1 py-2.5 rounded-lg bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-[12px] font-bold uppercase tracking-wide transition-all"
              >
                {saving ? "Procesando..." : "Desactivar"}
              </button>
            </div>
          </div>
        )}
      </SidePanel>
    </div>
  );
}

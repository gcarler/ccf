"use client";

import React, { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  UserPlus,
  Users,
  Pencil,
  ImageIcon,
  Trash2,
  ExternalLink,
  Sparkles,
  Check,
  X,
  BookOpen,
  Loader2,
  Instagram,
  Facebook,
  Twitter,
  Quote,
  AlertTriangle,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { toast } from "sonner";
import {
  PastoralProfile,
  getCmsPastoralTeam,
  createCmsPastoralProfile,
  updateCmsPastoralProfile,
  deleteCmsPastoralProfile,
} from "@/lib/cms/v2";
import MediaPicker from "@/components/cms/builder/MediaPicker";

interface PublicPastoralManagerProps {
  token: string;
}

interface PastorFormData {
  name: string;
  role: string;
  photo_url: string;
  bio_short: string;
  bio_full: string;
  social_instagram: string;
  social_facebook: string;
  social_twitter: string;
  is_main_pastor: boolean;
  is_pastoral_published: boolean;
  pastoral_sort_order: number;
}

const emptyFormData: PastorFormData = {
  name: "",
  role: "Pastor",
  photo_url: "",
  bio_short: "",
  bio_full: "",
  social_instagram: "",
  social_facebook: "",
  social_twitter: "",
  is_main_pastor: false,
  is_pastoral_published: true,
  pastoral_sort_order: 0,
};

export default function PublicPastoralManager({
  token,
}: PublicPastoralManagerProps): React.ReactElement | null {
  const [pastors, setPastors] = useState<PastoralProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Modals state
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedPastor, setSelectedPastor] = useState<PastoralProfile | null>(null);

  // Form states
  const [formData, setFormData] = useState<PastorFormData>(emptyFormData);

  // MediaPicker state
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const [mediaPickerTarget, setMediaPickerTarget] = useState<"form" | "direct">("form");
  const [directPhotoPastorId, setDirectPhotoPastorId] = useState<string | null>(null);

  const fetchPastors = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getCmsPastoralTeam(token);
      setPastors(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Error al cargar el equipo pastoral");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchPastors();
  }, [fetchPastors]);

  // Open Create
  const handleOpenCreate = () => {
    setFormData({
      ...emptyFormData,
      pastoral_sort_order: pastors.length * 10,
    });
    setCreateModalOpen(true);
  };

  // Open Edit
  const handleOpenEdit = (p: PastoralProfile) => {
    setSelectedPastor(p);
    setFormData({
      name: p.name || "",
      role: p.role || "Pastor",
      photo_url: p.photo_url || "",
      bio_short: p.bio_short || "",
      bio_full: p.bio_full || "",
      social_instagram: p.social_instagram || "",
      social_facebook: p.social_facebook || "",
      social_twitter: p.social_twitter || "",
      is_main_pastor: Boolean(p.is_main_pastor),
      is_pastoral_published: p.is_pastoral_published !== false,
      pastoral_sort_order: p.pastoral_sort_order ?? 0,
    });
    setEditModalOpen(true);
  };

  // Open Delete
  const handleOpenDelete = (p: PastoralProfile) => {
    setSelectedPastor(p);
    setDeleteModalOpen(true);
  };

  // Save Create
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error("El nombre del pastor es obligatorio");
      return;
    }
    setSaving(true);
    try {
      await createCmsPastoralProfile(
        {
          name: formData.name.trim(),
          church_role: formData.role.trim() || "Pastor",
          role: formData.role.trim() || "Pastor",
          photo_url: formData.photo_url.trim() || null,
          bio_short: formData.bio_short.trim() || null,
          bio_full: formData.bio_full.trim() || null,
          social_instagram: formData.social_instagram.trim() || null,
          social_facebook: formData.social_facebook.trim() || null,
          social_twitter: formData.social_twitter.trim() || null,
          is_main_pastor: formData.is_main_pastor,
          is_pastoral_published: formData.is_pastoral_published,
          pastoral_sort_order: Number(formData.pastoral_sort_order) || 0,
        },
        token
      );
      toast.success("Nuevo pastor creado correctamente");
      setCreateModalOpen(false);
      setFormData(emptyFormData);
      await fetchPastors();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al crear el nuevo pastor");
    } finally {
      setSaving(false);
    }
  };

  // Save Edit
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPastor) return;
    if (!formData.name.trim()) {
      toast.error("El nombre del pastor no puede estar vacío");
      return;
    }
    setSaving(true);
    try {
      await updateCmsPastoralProfile(
        selectedPastor.id,
        {
          name: formData.name.trim(),
          church_role: formData.role.trim() || "Pastor",
          role: formData.role.trim() || "Pastor",
          photo_url: formData.photo_url.trim() || null,
          bio_short: formData.bio_short.trim() || null,
          bio_full: formData.bio_full.trim() || null,
          social_instagram: formData.social_instagram.trim() || null,
          social_facebook: formData.social_facebook.trim() || null,
          social_twitter: formData.social_twitter.trim() || null,
          is_main_pastor: formData.is_main_pastor,
          is_pastoral_published: formData.is_pastoral_published,
          pastoral_sort_order: Number(formData.pastoral_sort_order) || 0,
        },
        token
      );
      toast.success("Perfil e historia pastoral actualizados");
      setEditModalOpen(false);
      setSelectedPastor(null);
      await fetchPastors();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al actualizar el pastor");
    } finally {
      setSaving(false);
    }
  };

  // Confirm Delete
  const handleDeleteConfirm = async () => {
    if (!selectedPastor) return;
    setSaving(true);
    try {
      await deleteCmsPastoralProfile(selectedPastor.id, token);
      toast.success("Pastor removido del equipo pastoral");
      setDeleteModalOpen(false);
      setSelectedPastor(null);
      await fetchPastors();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al remover el pastor");
    } finally {
      setSaving(false);
    }
  };

  // Quick reorder
  const handleQuickReorder = async (index: number, direction: "up" | "down") => {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= pastors.length) return;
    const current = pastors[index];
    const target = pastors[targetIndex];
    if (!current || !target) return;

    const currentSort = current.pastoral_sort_order ?? index * 10;
    const targetSort = target.pastoral_sort_order ?? targetIndex * 10;

    let newCurrentSort = targetSort;
    let newTargetSort = currentSort;
    if (newCurrentSort === newTargetSort) {
      newCurrentSort = direction === "up" ? targetSort - 1 : targetSort + 1;
    }

    // Optimistically update local state
    const updated = [...pastors];
    updated[index] = { ...current, pastoral_sort_order: newCurrentSort };
    updated[targetIndex] = { ...target, pastoral_sort_order: newTargetSort };
    updated.sort((a, b) => (a.pastoral_sort_order ?? 0) - (b.pastoral_sort_order ?? 0));
    setPastors(updated);

    try {
      await Promise.all([
        updateCmsPastoralProfile(current.id, { pastoral_sort_order: newCurrentSort }, token),
        updateCmsPastoralProfile(target.id, { pastoral_sort_order: newTargetSort }, token),
      ]);
      toast.success(`Orden actualizado: ${current.name} movido hacia ${direction === "up" ? "arriba" : "abajo"}`);
      await fetchPastors();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al guardar el nuevo orden");
      await fetchPastors();
    }
  };

  // Direct photo change from card button
  const handleDirectPhotoClick = (pastorId: string) => {
    setDirectPhotoPastorId(pastorId);
    setMediaPickerTarget("direct");
    setMediaPickerOpen(true);
  };

  // Form photo button
  const handleFormPhotoClick = () => {
    setMediaPickerTarget("form");
    setMediaPickerOpen(true);
  };

  // Media select callback
  const handleMediaSelect = async (item: { url?: string } | string) => {
    const url = typeof item === "string" ? item : item?.url || "";
    if (!url) return;

    if (mediaPickerTarget === "form") {
      setFormData((prev) => ({ ...prev, photo_url: url }));
      setMediaPickerOpen(false);
    } else if (mediaPickerTarget === "direct" && directPhotoPastorId) {
      try {
        await updateCmsPastoralProfile(
          directPhotoPastorId,
          { photo_url: url },
          token
        );
        toast.success("Foto del pastor actualizada");
        await fetchPastors();
      } catch (err: unknown) {
        toast.error(err instanceof Error ? err.message : "No se pudo actualizar la foto");
      } finally {
        setMediaPickerOpen(false);
        setDirectPhotoPastorId(null);
      }
    }
  };

  return (
    <div className="bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border-t border-[hsl(var(--border))] dark:border-white/10 p-4 md:p-6">
      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] flex items-center justify-center">
              <Users size={18} />
            </div>
            <h3 className="font-bold text-base text-[hsl(var(--text-primary))] dark:text-white">
              Equipo Pastoral CCF
            </h3>
            <span className="px-2 py-0.5 rounded-full text-2xs font-semibold bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))]">
              {pastors.length} líderes
            </span>
          </div>
          <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">
            Crea nuevos pastores, actualiza sus fotos y edita sus historias de vida visibles en{" "}
            <Link
              href="/pastores"
              target="_blank"
              className="text-[hsl(var(--primary))] hover:underline inline-flex items-center gap-1 font-mono"
            >
              /pastores <ExternalLink size={10} />
            </Link>{" "}
            y{" "}
            <code className="text-2xs bg-[hsl(var(--surface-2))] px-1 py-0.5 rounded font-mono">
              /pastores/[slug]
            </code>
          </p>
        </div>

        <button
          type="button"
          onClick={handleOpenCreate}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-all shadow-md shadow-[hsl(var(--primary))/0.2]"
        >
          <UserPlus size={14} />
          Nuevo Pastor
        </button>
      </div>

      {/* ── Pastors Cards ── */}
      {loading ? (
        <div className="flex items-center justify-center py-12 text-sm text-[hsl(var(--text-secondary))] gap-2">
          <Loader2 className="animate-spin" size={16} /> Cargando equipo pastoral...
        </div>
      ) : pastors.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-[hsl(var(--border))] rounded-2xl p-6">
          <Users size={32} className="mx-auto text-[hsl(var(--text-secondary))] opacity-40 mb-2" />
          <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">
            No hay pastores registrados todavía
          </p>
          <p className="text-xs text-[hsl(var(--text-secondary))] mt-1 mb-4">
            Comienza agregando el primer líder o pastor de la comunidad.
          </p>
          <button
            type="button"
            onClick={handleOpenCreate}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wider"
          >
            <UserPlus size={14} /> Crear primer pastor
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {pastors.map((p, idx) => (
            <div
              key={p.id}
              className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-deep))] rounded-2xl border border-[hsl(var(--border))] dark:border-white/10 p-4 flex flex-col justify-between hover:shadow-lg hover:border-[hsl(var(--primary))/0.4] transition-all"
            >
              <div>
                {/* Pastor info header */}
                <div className="flex items-start gap-3">
                  <div className="relative w-14 h-14 rounded-xl overflow-hidden bg-[hsl(var(--surface-2))] shrink-0 ring-2 ring-[hsl(var(--border))] dark:ring-white/10">
                    {p.photo_url ? (
                      <Image
                        src={p.photo_url}
                        alt={p.name}
                        fill
                        className="object-cover"
                        sizes="56px"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.15] to-transparent font-bold text-lg text-[hsl(var(--primary))]">
                        {p.name.charAt(0)}
                      </div>
                    )}
                    {/* Change photo button on hover */}
                    <button
                      type="button"
                      onClick={() => handleDirectPhotoClick(p.id)}
                      title="Cambiar fotografía"
                      className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center text-white transition-opacity text-2xs font-semibold"
                    >
                      <ImageIcon size={14} />
                    </button>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <h4 className="font-bold text-sm text-[hsl(var(--text-primary))] dark:text-white truncate">
                        {p.name}
                      </h4>
                      {p.is_main_pastor && (
                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))] text-3xs font-bold uppercase">
                          <Sparkles size={9} /> Principal
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[hsl(var(--text-secondary))] font-medium">
                      {p.role || "Pastor"}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      {p.is_pastoral_published !== false ? (
                        <span className="inline-flex items-center gap-1 text-3xs text-[hsl(var(--success))] font-semibold">
                          <span className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--success))]" /> Publicado
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-3xs text-[hsl(var(--text-secondary))] font-semibold">
                          <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" /> Oculto
                        </span>
                      )}
                      <span className="text-3xs text-[hsl(var(--text-secondary))] font-mono">
                        #{p.pastoral_sort_order ?? 0}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Excerpt / Story indicators */}
                <div className="mt-3 pt-2.5 border-t border-[hsl(var(--border))]/60 dark:border-white/5 space-y-1.5">
                  {p.bio_short ? (
                    <p className="text-xs text-[hsl(var(--text-secondary))] line-clamp-2 italic">
                      &ldquo;{p.bio_short.replace(/<[^>]*>/g, "")}&rdquo;
                    </p>
                  ) : (
                    <p className="text-2xs text-[hsl(var(--text-secondary))] opacity-60 italic">
                      Sin versículo o lema configurado
                    </p>
                  )}

                  <div className="flex items-center gap-3 text-2xs text-[hsl(var(--text-secondary))] pt-1">
                    <span
                      className={`inline-flex items-center gap-1 font-semibold ${
                        p.bio_full
                          ? "text-[hsl(var(--primary))]"
                          : "opacity-60"
                      }`}
                    >
                      <BookOpen size={11} />
                      {p.bio_full ? "Historia redactada" : "Sin historia detallada"}
                    </span>
                    {(p.social_instagram || p.social_facebook || p.social_twitter) && (
                      <span className="flex items-center gap-1.5 ml-auto opacity-70">
                        {p.social_instagram && <Instagram size={11} />}
                        {p.social_facebook && <Facebook size={11} />}
                        {p.social_twitter && <Twitter size={11} />}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="mt-4 pt-3 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between gap-2">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={idx === 0}
                    onClick={() => handleQuickReorder(idx, "up")}
                    className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] disabled:opacity-30 disabled:hover:bg-transparent transition-all"
                    title="Mover arriba"
                  >
                    <ChevronUp size={14} />
                  </button>
                  <button
                    type="button"
                    disabled={idx === pastors.length - 1}
                    onClick={() => handleQuickReorder(idx, "down")}
                    className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] disabled:opacity-30 disabled:hover:bg-transparent transition-all"
                    title="Mover abajo"
                  >
                    <ChevronDown size={14} />
                  </button>
                  <Link
                    href={`/pastores/${p.slug}`}
                    target="_blank"
                    className="inline-flex items-center gap-1 text-2xs font-semibold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors ml-1"
                  >
                    <ExternalLink size={11} /> Ver página
                  </Link>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => handleOpenEdit(p)}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 hover:bg-[hsl(var(--primary))/0.15] text-[hsl(var(--text-primary))] dark:text-white hover:text-[hsl(var(--primary))] text-2xs font-bold uppercase transition-all"
                  >
                    <Pencil size={11} /> Editar Historia
                  </button>

                  <button
                    type="button"
                    onClick={() => handleOpenDelete(p)}
                    title="Remover pastor"
                    className="p-1.5 rounded-lg hover:bg-red-500/10 text-[hsl(var(--text-secondary))] hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── CREATE / EDIT DRAWER (SidePanel) ── */}
      {(createModalOpen || editModalOpen) && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn"
            onClick={() => {
              setCreateModalOpen(false);
              setEditModalOpen(false);
            }}
          />
          <div className="relative w-full max-w-2xl h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="px-6 py-4 border-b border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-between shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))]">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] flex items-center justify-center">
                  {createModalOpen ? <UserPlus size={16} /> : <Pencil size={16} />}
                </div>
                <h3 className="font-bold text-sm text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wider">
                  {createModalOpen ? "Crear Nuevo Pastor" : "Editar Pastor e Historia"}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setCreateModalOpen(false);
                  setEditModalOpen(false);
                }}
                className="w-8 h-8 rounded-lg hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-secondary))]"
              >
                <X size={16} />
              </button>
            </div>

            {/* Scrollable Form */}
            <form
              onSubmit={createModalOpen ? handleCreateSubmit : handleEditSubmit}
              className="flex-1 overflow-y-auto p-6 space-y-5"
            >
              {/* Name and Role */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Nombre Completo *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Ej: Pastor Luis Ricardo"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>

                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Rol o Cargo Ministerial
                  </label>
                  <input
                    type="text"
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    placeholder="Ej: Pastor Principal, Pastora..."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Photo Selector */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                  Fotografía del Pastor
                </label>
                <div className="flex gap-3 items-center">
                  <div className="relative w-16 h-16 rounded-xl overflow-hidden bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))] shrink-0">
                    {formData.photo_url ? (
                      <Image
                        src={formData.photo_url}
                        alt="Preview"
                        fill
                        className="object-cover"
                        sizes="64px"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[hsl(var(--text-secondary))] opacity-40">
                        <ImageIcon size={20} />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 space-y-1.5">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={formData.photo_url}
                        onChange={(e) => setFormData({ ...formData, photo_url: e.target.value })}
                        placeholder="URL de la fotografía o selecciona una..."
                        className="flex-1 px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                      />
                      <button
                        type="button"
                        onClick={handleFormPhotoClick}
                        className="px-3 py-2 rounded-xl bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))/0.2] text-xs font-bold uppercase tracking-wider transition-colors shrink-0 flex items-center gap-1.5"
                      >
                        <ImageIcon size={14} /> Seleccionar
                      </button>
                    </div>
                    <p className="text-3xs text-[hsl(var(--text-secondary))]">
                      Recomendado: proporción 4:5 o vertical, mínimo 600x750 px.
                    </p>
                  </div>
                </div>
              </div>

              {/* Verse / Short Bio */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1.5">
                  <Quote size={12} /> Frase Lema o Versículo Bíblico (Extracto para tarjeta)
                </label>
                <textarea
                  rows={2}
                  value={formData.bio_short}
                  onChange={(e) => setFormData({ ...formData, bio_short: e.target.value })}
                  placeholder="Ej: Un testimonio de transformación profunda y pasión inagotable por la enseñanza de la Palabra."
                  className="w-full px-3.5 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] resize-none"
                />
                <p className="text-3xs text-[hsl(var(--text-secondary))] mt-1">
                  Se muestra en la tarjeta del listado público y como cita destacada en la página de detalle.
                </p>
              </div>

              {/* Full Bio / Story */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1.5">
                  <BookOpen size={12} /> Historia Completa y Testimonio de Vida
                </label>
                <textarea
                  rows={6}
                  value={formData.bio_full}
                  onChange={(e) => setFormData({ ...formData, bio_full: e.target.value })}
                  placeholder="Redacta la historia completa del pastor, su llamado, trayectoria y ministerio (soporta párrafos normales o etiquetas HTML como <p>, <blockquote>, <strong>)..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] font-sans"
                />
                <p className="text-3xs text-[hsl(var(--text-secondary))] mt-1">
                  Aparece en la sección destacada &quot;Su Historia&quot; dentro de la página individual de cada pastor (
                  <code className="text-3xs bg-[hsl(var(--surface-3))] px-1 py-0.5 rounded">/pastores/[slug]</code>).
                </p>
              </div>

              {/* Social Networks */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1 flex items-center gap-1">
                    <Instagram size={10} /> Instagram
                  </label>
                  <input
                    type="text"
                    value={formData.social_instagram}
                    onChange={(e) => setFormData({ ...formData, social_instagram: e.target.value })}
                    placeholder="@usuario o https://instagram.com/..."
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
                <div>
                  <label className="block text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1 flex items-center gap-1">
                    <Facebook size={10} /> Facebook
                  </label>
                  <input
                    type="text"
                    value={formData.social_facebook}
                    onChange={(e) => setFormData({ ...formData, social_facebook: e.target.value })}
                    placeholder="@usuario o https://facebook.com/..."
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
                <div>
                  <label className="block text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1 flex items-center gap-1">
                    <Twitter size={10} /> X (Twitter)
                  </label>
                  <input
                    type="text"
                    value={formData.social_twitter}
                    onChange={(e) => setFormData({ ...formData, social_twitter: e.target.value })}
                    placeholder="@usuario o https://x.com/..."
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Settings: Main Pastor, Published, Sort Order */}
              <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-[hsl(var(--surface-2))] dark:bg-white/[0.02] border border-[hsl(var(--border))]">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_main_pastor}
                    onChange={(e) => setFormData({ ...formData, is_main_pastor: e.target.checked })}
                    className="w-4 h-4 rounded text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))/0.3]"
                  />
                  <div>
                    <span className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">
                      Pastor Principal
                    </span>
                    <p className="text-3xs text-[hsl(var(--text-secondary))]">
                      Destacado con insignia dorada
                    </p>
                  </div>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_pastoral_published}
                    onChange={(e) => setFormData({ ...formData, is_pastoral_published: e.target.checked })}
                    className="w-4 h-4 rounded text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))/0.3]"
                  />
                  <div>
                    <span className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">
                      Visible en Sitio Web
                    </span>
                    <p className="text-3xs text-[hsl(var(--text-secondary))]">
                      Aparece en las páginas públicas
                    </p>
                  </div>
                </label>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[hsl(var(--text-primary))]">
                    Orden:
                  </span>
                  <input
                    type="number"
                    value={formData.pastoral_sort_order}
                    onChange={(e) => setFormData({ ...formData, pastoral_sort_order: parseInt(e.target.value) || 0 })}
                    className="w-16 px-2 py-1 rounded-lg border border-[hsl(var(--border))] bg-transparent text-xs text-center font-mono"
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="sticky bottom-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-t border-[hsl(var(--border))] dark:border-white/[0.06] -mx-6 -mb-6 p-6 flex items-center justify-end gap-3 z-10">
                <button
                  type="button"
                  onClick={() => {
                    setCreateModalOpen(false);
                    setEditModalOpen(false);
                  }}
                  className="px-4 py-2.5 rounded-xl bg-[hsl(var(--surface-2))] text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-all shadow-md shadow-[hsl(var(--primary))/0.2]"
                >
                  {saving ? (
                    <>
                      <Loader2 size={14} className="animate-spin" /> Guardando...
                    </>
                  ) : (
                    <>
                      <Check size={14} /> {createModalOpen ? "Crear Pastor" : "Guardar Cambios"}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── DELETE CONFIRMATION DRAWER (SidePanel) ── */}
      {deleteModalOpen && selectedPastor && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn"
            onClick={() => {
              setDeleteModalOpen(false);
              setSelectedPastor(null);
            }}
          />
          <div className="relative w-full max-w-md h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl p-6 flex flex-col justify-between z-10 animate-in slide-in-from-right duration-300">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))] flex items-center justify-center mb-4">
                <AlertTriangle size={24} />
              </div>
              <h3 className="font-bold text-base text-[hsl(var(--text-primary))] dark:text-white mb-2">
                ¿Remover a {selectedPastor.name} del equipo pastoral?
              </h3>
              <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed mb-6">
                El pastor dejará de mostrarse en la página pública de pastores y en su URL de historia.
                Sus datos personales en el CRM se conservan intactos.
              </p>
            </div>
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-[hsl(var(--border))] dark:border-white/[0.06]">
              <button
                type="button"
                onClick={() => {
                  setDeleteModalOpen(false);
                  setSelectedPastor(null);
                }}
                disabled={saving}
                className="px-4 py-2 rounded-xl bg-[hsl(var(--surface-2))] text-xs font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[hsl(var(--destructive))] hover:opacity-90 text-white text-xs font-bold uppercase tracking-wider transition-all shadow-md shadow-[hsl(var(--destructive)/0.2)]"
              >
                {saving ? "Removiendo..." : "Confirmar Remoción"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MEDIAPICKER ── */}
      {mediaPickerOpen && (
        <MediaPicker
          open={mediaPickerOpen}
          token={token}
          selectedUrl={formData.photo_url || undefined}
          onClose={() => {
            setMediaPickerOpen(false);
            setDirectPhotoPastorId(null);
          }}
          onSelect={handleMediaSelect}
        />
      )}
    </div>
  );
}

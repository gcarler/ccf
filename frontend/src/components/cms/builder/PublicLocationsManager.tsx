"use client";

import React, { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Building2,
  Plus,
  Pencil,
  ImageIcon,
  Trash2,
  ExternalLink,
  Sparkles,
  Check,
  X,
  MapPin,
  Loader2,
  ChevronUp,
  ChevronDown,
  Clock,
  User,
  Phone,
  AlertTriangle,
  Navigation,
  Globe,
} from "lucide-react";
import { toast } from "sonner";
import {
  CmsLocation,
  getCmsLocations,
  createCmsLocation,
  updateCmsLocation,
  deleteCmsLocation,
} from "@/lib/cms/v2";
import MediaPicker from "@/components/cms/builder/MediaPicker";

interface PublicLocationsManagerProps {
  token: string;
}

interface LocationFormData {
  name: string;
  address: string;
  city: string;
  phone: string;
  pastor: string;
  schedule: string;
  midweek: string;
  image: string;
  maps_url: string;
  map_embed_url: string;
  lat: number | null;
  lng: number | null;
  is_main: boolean;
  is_active: boolean;
  sort_order: number;
}

const emptyFormData: LocationFormData = {
  name: "",
  address: "",
  city: "Cartagena",
  phone: "",
  pastor: "",
  schedule: "Domingos: 8:00 AM y 10:30 AM",
  midweek: "Miércoles: 7:00 PM",
  image: "",
  maps_url: "",
  map_embed_url: "",
  lat: null,
  lng: null,
  is_main: false,
  is_active: true,
  sort_order: 0,
};

export default function PublicLocationsManager({
  token,
}: PublicLocationsManagerProps): React.ReactElement | null {
  const [locations, setLocations] = useState<CmsLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Drawers state (STRICT: Drawers/SidePanels only, no modals)
  const [createDrawerOpen, setCreateDrawerOpen] = useState(false);
  const [editDrawerOpen, setEditDrawerOpen] = useState(false);
  const [deleteDrawerOpen, setDeleteDrawerOpen] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState<CmsLocation | null>(null);

  // Form states
  const [formData, setFormData] = useState<LocationFormData>(emptyFormData);

  // MediaPicker state
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const [mediaPickerTarget, setMediaPickerTarget] = useState<"form" | "direct">("form");
  const [directPhotoLocationId, setDirectPhotoLocationId] = useState<string | null>(null);

  const fetchLocations = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getCmsLocations(token);
      setLocations(Array.isArray(data) ? data : []);
    } catch {
      toast.error("Error al cargar las sedes de la iglesia");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchLocations();
    }
  }, [token, fetchLocations]);

  // Open Create Drawer
  const handleOpenCreate = () => {
    setFormData({
      ...emptyFormData,
      sort_order: locations.length > 0 ? (locations[locations.length - 1].sort_order ?? 0) + 10 : 10,
    });
    setCreateDrawerOpen(true);
  };

  // Open Edit Drawer
  const handleOpenEdit = (loc: CmsLocation) => {
    setSelectedLocation(loc);
    setFormData({
      name: loc.name || "",
      address: loc.address || "",
      city: loc.city || "",
      phone: loc.phone || "",
      pastor: loc.pastor || "",
      schedule: loc.schedule || "",
      midweek: loc.midweek || "",
      image: loc.image || "",
      maps_url: loc.maps_url || "",
      map_embed_url: loc.map_embed_url || "",
      lat: loc.lat ?? null,
      lng: loc.lng ?? null,
      is_main: loc.is_main ?? false,
      is_active: loc.is_active ?? true,
      sort_order: loc.sort_order ?? 0,
    });
    setEditDrawerOpen(true);
  };

  // Open Delete Drawer
  const handleOpenDelete = (loc: CmsLocation) => {
    setSelectedLocation(loc);
    setDeleteDrawerOpen(true);
  };

  // Submit Create
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error("El nombre de la sede es obligatorio");
      return;
    }
    if (!formData.address.trim()) {
      toast.error("La dirección física de la sede es obligatoria para ubicarla en el mapa");
      return;
    }

    try {
      setSaving(true);
      const res = await createCmsLocation(formData, token);
      toast.success(`Sede "${res.name}" creada exitosamente`);
      setCreateDrawerOpen(false);
      await fetchLocations();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al crear la sede");
    } finally {
      setSaving(false);
    }
  };

  // Submit Edit
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLocation) return;
    if (!formData.name.trim()) {
      toast.error("El nombre de la sede es obligatorio");
      return;
    }
    if (!formData.address.trim()) {
      toast.error("La dirección de la sede es obligatoria");
      return;
    }

    try {
      setSaving(true);
      const res = await updateCmsLocation(selectedLocation.id, formData, token);
      toast.success(`Sede "${res.name}" actualizada exitosamente`);
      setEditDrawerOpen(false);
      setSelectedLocation(null);
      await fetchLocations();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al actualizar la sede");
    } finally {
      setSaving(false);
    }
  };

  // Submit Delete
  const handleDeleteConfirm = async () => {
    if (!selectedLocation) return;

    try {
      setSaving(true);
      await deleteCmsLocation(selectedLocation.id, token);
      toast.success("Sede archivada exitosamente");
      setDeleteDrawerOpen(false);
      setSelectedLocation(null);
      await fetchLocations();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al archivar la sede");
    } finally {
      setSaving(false);
    }
  };

  // Quick Reordering (Swap sort_order with adjacent item)
  const handleQuickReorder = async (index: number, direction: "up" | "down") => {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= locations.length) return;

    const current = locations[index];
    const target = locations[targetIndex];

    const currentSort = current.sort_order ?? index * 10;
    const targetSort = target.sort_order ?? targetIndex * 10;

    let newCurrentSort = targetSort;
    let newTargetSort = currentSort;
    if (newCurrentSort === newTargetSort) {
      newCurrentSort = direction === "up" ? targetSort - 1 : targetSort + 1;
    }

    // Optimistically update local state
    const updated = [...locations];
    updated[index] = { ...current, sort_order: newCurrentSort };
    updated[targetIndex] = { ...target, sort_order: newTargetSort };
    updated.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    setLocations(updated);

    try {
      await Promise.all([
        updateCmsLocation(current.id, { sort_order: newCurrentSort }, token),
        updateCmsLocation(target.id, { sort_order: newTargetSort }, token),
      ]);
      toast.success(
        `Orden actualizado: "${current.name}" ${direction === "up" ? "subió al puesto #" + (targetIndex + 1) : "bajó al puesto #" + (targetIndex + 1)}`
      );
      await fetchLocations();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al guardar el nuevo orden");
      await fetchLocations();
    }
  };

  // Direct photo change from card button
  const handleDirectPhotoClick = (locationId: string) => {
    setDirectPhotoLocationId(locationId);
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
      setFormData((prev) => ({ ...prev, image: url }));
      setMediaPickerOpen(false);
    } else if (mediaPickerTarget === "direct" && directPhotoLocationId) {
      try {
        await updateCmsLocation(directPhotoLocationId, { image: url }, token);
        toast.success("Fotografía de la sede actualizada exitosamente");
        await fetchLocations();
      } catch (err: unknown) {
        toast.error(err instanceof Error ? err.message : "No se pudo actualizar la fotografía");
      } finally {
        setMediaPickerOpen(false);
        setDirectPhotoLocationId(null);
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
              <MapPin size={18} />
            </div>
            <h2 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">
              Gestión de Sedes y Mapa (/sedes)
            </h2>
            <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] uppercase tracking-wider">
              {locations.length} Sedes
            </span>
          </div>
          <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">
            Personaliza las sedes, direcciones, horarios, pastores a cargo y su ubicación interactiva en el mapa público.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/sedes"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
          >
            <ExternalLink size={13} />
            Ver Mapa Público
          </Link>
          <button
            type="button"
            onClick={handleOpenCreate}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary))/0.9] shadow-sm transition-all uppercase tracking-wider"
          >
            <Plus size={14} />
            Nueva Sede
          </button>
        </div>
      </div>

      {/* ── Banner Informativo de Mapa y Ubicación ── */}
      <div className="mb-6 p-4 rounded-xl border border-[hsl(var(--primary))/0.2] bg-[hsl(var(--primary))/0.05] flex items-start gap-3">
        <Sparkles className="w-5 h-5 text-[hsl(var(--primary))] shrink-0 mt-0.5" />
        <div className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
          <span className="font-bold text-[hsl(var(--text-primary))]">Ubicación Dinámica en el Mapa: </span>
          Cada sede con dirección o coordenadas se visualiza de forma automática en el mapa de{" "}
          <code className="text-2xs px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] font-mono">/sedes</code>. La sede marcada como <strong className="text-[hsl(var(--primary))]">Sede Principal</strong> es la primera que se enfoca y se selecciona automáticamente al entrar a la página.
        </div>
      </div>

      {/* ── Loading Skeleton ── */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((idx) => (
            <div
              key={idx}
              className="h-56 rounded-2xl bg-[hsl(var(--surface-2))] animate-pulse border border-[hsl(var(--border))] dark:border-white/5"
            />
          ))}
        </div>
      ) : locations.length === 0 ? (
        /* ── Empty State ── */
        <div className="text-center py-12 px-4 rounded-2xl border border-dashed border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-2))]">
          <div className="w-12 h-12 rounded-xl bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] mx-auto flex items-center justify-center mb-3">
            <Building2 size={24} />
          </div>
          <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] mb-1">
            No hay sedes registradas
          </h3>
          <p className="text-xs text-[hsl(var(--text-secondary))] max-w-sm mx-auto mb-4">
            Crea tu primera sede para que aparezca en el mapa interactivo y listado público.
          </p>
          <button
            type="button"
            onClick={handleOpenCreate}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary))/0.9] transition-all uppercase tracking-wider"
          >
            <Plus size={14} /> Crear Sede
          </button>
        </div>
      ) : (
        /* ── Locations Cards Grid ── */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {locations.map((loc, index) => (
            <div
              key={loc.id}
              className={`group relative rounded-2xl border transition-all duration-200 overflow-hidden flex flex-col justify-between ${
                loc.is_main
                  ? "border-amber-500/40 bg-[hsl(var(--surface-2))] shadow-md ring-1 ring-amber-500/20"
                  : "border-[hsl(var(--border))] dark:border-white/[0.06] bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--primary))/0.4]"
              }`}
            >
              {/* Card Header with Badges and Reordering Controls */}
              <div className="p-3 border-b border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-between bg-[hsl(var(--surface-3))/0.5]">
                <div className="flex items-center gap-1.5 flex-wrap">
                  {loc.is_main ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-3xs font-black uppercase tracking-wider bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                      <Sparkles size={10} /> Sede Principal
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-3xs font-bold uppercase tracking-wider bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
                      Posición #{index + 1}
                    </span>
                  )}

                  {loc.is_active ? (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-3xs font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                      <Check size={9} /> Activa
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-3xs font-semibold bg-zinc-500/15 text-zinc-500">
                      Oculta
                    </span>
                  )}

                  {loc.city && (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-3xs font-semibold bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))]">
                      <Globe size={9} /> {loc.city}
                    </span>
                  )}
                </div>

                {/* Quick Reordering Arrows */}
                <div className="flex items-center gap-0.5 bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-0.5 shadow-2xs">
                  <button
                    type="button"
                    disabled={index === 0}
                    onClick={() => handleQuickReorder(index, "up")}
                    title="Mover arriba"
                    className="p-1 rounded hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                  >
                    <ChevronUp size={14} />
                  </button>
                  <button
                    type="button"
                    disabled={index === locations.length - 1}
                    onClick={() => handleQuickReorder(index, "down")}
                    title="Mover abajo"
                    className="p-1 rounded hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
                  >
                    <ChevronDown size={14} />
                  </button>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-4 flex gap-4 items-start">
                {/* Image Thumbnail with Direct Change Button */}
                <div className="relative w-24 h-24 rounded-xl overflow-hidden bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))] dark:border-white/10 shrink-0 group/img">
                  {loc.image ? (
                    <Image
                      src={loc.image}
                      alt={loc.name}
                      fill
                      className="object-cover transition-transform duration-300 group-hover/img:scale-105"
                      sizes="96px"
                    />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-[hsl(var(--text-secondary))] opacity-60">
                      <Building2 size={28} />
                      <span className="text-3xs mt-1 font-semibold uppercase">Sin Fachada</span>
                    </div>
                  )}

                  {/* Direct Change Button Overlay */}
                  <button
                    type="button"
                    onClick={() => handleDirectPhotoClick(loc.id)}
                    title="Cambiar fotografía de la sede"
                    className="absolute inset-0 bg-black/60 opacity-0 group-hover/img:opacity-100 flex flex-col items-center justify-center text-white text-3xs font-bold uppercase tracking-wider transition-opacity duration-200 gap-1 p-1 text-center"
                  >
                    <ImageIcon size={16} />
                    <span>Cambiar Foto</span>
                  </button>
                </div>

                {/* Location Metadata */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-sm text-[hsl(var(--text-primary))] dark:text-white leading-snug line-clamp-1 mb-1">
                    {loc.name}
                  </h3>

                  <p className="text-xs text-[hsl(var(--text-secondary))] flex items-start gap-1 mb-1.5 leading-relaxed">
                    <MapPin size={12} className="shrink-0 mt-0.5 text-[hsl(var(--primary))]" />
                    <span className="line-clamp-2">{loc.address || "Dirección no especificada"}</span>
                  </p>

                  {loc.pastor && (
                    <div className="flex items-center gap-1 text-xs text-[hsl(var(--text-primary))] font-medium mb-1">
                      <User size={12} className="text-[hsl(var(--primary))]" />
                      <span className="truncate">{loc.pastor}</span>
                    </div>
                  )}

                  {loc.schedule && (
                    <div className="flex items-center gap-1 text-3xs text-[hsl(var(--text-secondary))]">
                      <Clock size={10} />
                      <span className="truncate">{loc.schedule}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Card Footer with Meta & Actions */}
              <div className="px-4 py-3 border-t border-[hsl(var(--border))] dark:border-white/[0.06] bg-[hsl(var(--surface-3))/0.3] flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-3xs text-[hsl(var(--text-secondary))] truncate">
                  {loc.phone && (
                    <span className="flex items-center gap-1">
                      <Phone size={11} /> {loc.phone}
                    </span>
                  )}
                  {(loc.lat && loc.lng) ? (
                    <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                      <Navigation size={10} /> GPS listo
                    </span>
                  ) : null}
                </div>

                <div className="flex items-center gap-1">
                  <a
                    href={
                      loc.maps_url ||
                      `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(loc.address || loc.name)}`
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                    title="Ver ubicación en Google Maps"
                    className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors"
                  >
                    <ExternalLink size={14} />
                  </a>
                  <button
                    type="button"
                    onClick={() => handleOpenEdit(loc)}
                    title="Editar detalles de la sede"
                    className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleOpenDelete(loc)}
                    title="Archivar sede"
                    className="p-1.5 rounded-lg hover:bg-[hsl(var(--destructive))/0.1] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── CREATE / EDIT DRAWER (SidePanel Sliding from Right) ── */}
      {(createDrawerOpen || editDrawerOpen) && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn"
            onClick={() => {
              setCreateDrawerOpen(false);
              setEditDrawerOpen(false);
            }}
          />
          <div className="relative w-full max-w-2xl h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-300">
            {/* Drawer Header */}
            <div className="px-6 py-4 border-b border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-between shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))]">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] flex items-center justify-center">
                  {createDrawerOpen ? <Plus size={16} /> : <Pencil size={16} />}
                </div>
                <h3 className="font-bold text-sm text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-wider">
                  {createDrawerOpen ? "Crear Nueva Sede" : "Editar Sede y Ubicación"}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setCreateDrawerOpen(false);
                  setEditDrawerOpen(false);
                }}
                className="w-8 h-8 rounded-lg hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-secondary))]"
              >
                <X size={16} />
              </button>
            </div>

            {/* Scrollable Form */}
            <form
              onSubmit={createDrawerOpen ? handleCreateSubmit : handleEditSubmit}
              className="flex-1 overflow-y-auto p-6 space-y-5"
            >
              {/* Name and City */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Nombre de la Sede *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Ej: Sede Central El Faro"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>

                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Ciudad / Municipio
                  </label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="Cartagena, Barú..."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Physical Address */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                  Dirección Física (Se usa para ubicar en el mapa) *
                </label>
                <input
                  type="text"
                  required
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="Ej: Carrera 15 # 32-45, Barrio Pie de la Popa, Cartagena"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                />
              </div>

              {/* Photo / Facade with MediaPicker */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                  Fotografía de Fachada / Auditorio
                </label>
                <div className="flex gap-3 items-center">
                  <div className="relative w-20 h-20 rounded-xl overflow-hidden bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))] shrink-0">
                    {formData.image ? (
                      <Image
                        src={formData.image}
                        alt="Preview"
                        fill
                        className="object-cover"
                        sizes="80px"
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-[hsl(var(--text-secondary))] opacity-40">
                        <Building2 size={24} />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 space-y-1.5">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={formData.image}
                        onChange={(e) => setFormData({ ...formData, image: e.target.value })}
                        placeholder="URL de la imagen o selecciona de la biblioteca..."
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
                      Recomendado: fotografía horizontal en alta calidad (mínimo 1000x600 px).
                    </p>
                  </div>
                </div>
              </div>

              {/* Pastor and Phone */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Pastor o Líder a Cargo
                  </label>
                  <input
                    type="text"
                    value={formData.pastor}
                    onChange={(e) => setFormData({ ...formData, pastor: e.target.value })}
                    placeholder="Ej: Pastor Luis Ricardo Meza G."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>

                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5">
                    Teléfono / WhatsApp de Contacto
                  </label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+57 300 000 0000"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Schedules */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1">
                    <Clock size={12} /> Horarios Dominicales / Principales
                  </label>
                  <input
                    type="text"
                    value={formData.schedule}
                    onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
                    placeholder="Ej: Domingos: 8:00 AM y 10:30 AM"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>

                <div>
                  <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1">
                    <Clock size={12} /> Reuniones Entre Semana
                  </label>
                  <input
                    type="text"
                    value={formData.midweek}
                    onChange={(e) => setFormData({ ...formData, midweek: e.target.value })}
                    placeholder="Ej: Miércoles: 7:00 PM • Viernes: 6:30 PM"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Coordinates and Maps URL */}
              <div className="p-4 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-3))/0.3] space-y-3">
                <span className="text-xs font-bold text-[hsl(var(--text-primary))] flex items-center gap-1.5">
                  <Navigation size={14} className="text-[hsl(var(--primary))]" />
                  Georreferenciación y Mapa Interactivo
                </span>
                <p className="text-3xs text-[hsl(var(--text-secondary))]">
                  Si no ingresas coordenadas, el mapa ubicará automáticamente la dirección física.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                      Latitud (Opcional)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.lat ?? ""}
                      onChange={(e) => setFormData({ ...formData, lat: e.target.value ? parseFloat(e.target.value) : null })}
                      placeholder="10.3997"
                      className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                    />
                  </div>

                  <div>
                    <label className="block text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                      Longitud (Opcional)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.lng ?? ""}
                      onChange={(e) => setFormData({ ...formData, lng: e.target.value ? parseFloat(e.target.value) : null })}
                      placeholder="-75.5144"
                      className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-3xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                    Enlace de Google Maps (Para botón &quot;Cómo llegar&quot;)
                  </label>
                  <input
                    type="text"
                    value={formData.maps_url}
                    onChange={(e) => setFormData({ ...formData, maps_url: e.target.value })}
                    placeholder="https://maps.app.goo.gl/... o https://google.com/maps?q=..."
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-transparent text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Status and Main HQ Toggles */}
              <div className="p-4 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-3))/0.3] space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-[hsl(var(--text-primary))]">Sede Principal</span>
                    <p className="text-3xs text-[hsl(var(--text-secondary))]">
                      Se destaca con insignia especial y es la primera que se enfoca en el mapa.
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.is_main}
                      onChange={(e) => setFormData({ ...formData, is_main: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-6 bg-zinc-300 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[hsl(var(--primary))]"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[hsl(var(--border))] dark:border-white/5">
                  <div>
                    <span className="text-xs font-bold text-[hsl(var(--text-primary))]">Publicar en la Web</span>
                    <p className="text-3xs text-[hsl(var(--text-secondary))]">
                      Si está activa, los visitantes podrán ver la sede en /sedes y en el mapa.
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-6 bg-zinc-300 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[hsl(var(--primary))]"></div>
                  </label>
                </div>
              </div>

              {/* Submit Buttons */}
              <div className="pt-4 border-t border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setCreateDrawerOpen(false);
                    setEditDrawerOpen(false);
                  }}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary))/0.9] disabled:opacity-50 transition-all uppercase tracking-wider flex items-center gap-1.5 shadow-sm"
                >
                  {saving && <Loader2 size={13} className="animate-spin" />}
                  {createDrawerOpen ? "Crear Sede" : "Guardar Cambios"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── DELETE CONFIRMATION DRAWER (SidePanel Sliding from Right) ── */}
      {deleteDrawerOpen && selectedLocation && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fadeIn"
            onClick={() => {
              setDeleteDrawerOpen(false);
              setSelectedLocation(null);
            }}
          />
          <div className="relative w-full max-w-md h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="px-6 py-4 border-b border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2 text-[hsl(var(--destructive))]">
                <AlertTriangle size={18} />
                <h3 className="font-bold text-sm uppercase tracking-wider">
                  Archivar Sede
                </h3>
              </div>
              <button
                type="button"
                onClick={() => {
                  setDeleteDrawerOpen(false);
                  setSelectedLocation(null);
                }}
                className="w-8 h-8 rounded-lg hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-secondary))]"
              >
                <X size={16} />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 flex-1 space-y-4">
              <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed">
                ¿Estás seguro de que deseas archivar la sede{" "}
                <strong className="text-[hsl(var(--text-primary))] font-bold">
                  &quot;{selectedLocation.name}&quot;
                </strong>
                ?
              </p>
              <div className="p-3 rounded-xl bg-[hsl(var(--destructive))/0.1] border border-[hsl(var(--destructive))/0.2] text-xs text-[hsl(var(--destructive))] leading-relaxed">
                La sede dejará de mostrarse en el listado y mapa público (<code className="font-mono text-2xs">/sedes</code>).
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-[hsl(var(--border))] dark:border-white/[0.06] flex items-center justify-end gap-2 bg-[hsl(var(--surface-3))/0.3]">
              <button
                type="button"
                onClick={() => {
                  setDeleteDrawerOpen(false);
                  setSelectedLocation(null);
                }}
                className="px-4 py-2 text-xs font-semibold rounded-xl border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={handleDeleteConfirm}
                className="px-5 py-2 text-xs font-bold rounded-xl bg-[hsl(var(--destructive))] text-white hover:bg-[hsl(var(--destructive))/0.9] disabled:opacity-50 transition-all uppercase tracking-wider flex items-center gap-1.5"
              >
                {saving && <Loader2 size={13} className="animate-spin" />}
                Confirmar y Archivar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MediaPicker Drawer ── */}
      <MediaPicker
        open={mediaPickerOpen}
        token={token}
        selectedUrl={mediaPickerTarget === "form" ? formData.image : undefined}
        onClose={() => {
          setMediaPickerOpen(false);
          setDirectPhotoLocationId(null);
        }}
        onSelect={handleMediaSelect}
      />
    </div>
  );
}
